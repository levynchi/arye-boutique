from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from .forms import RegisterForm, LoginForm, PasswordResetRequestForm, CustomSetPasswordForm, ProfileEditForm
from store.models import Order
from store.ratelimit import is_rate_limited

LOGIN_WINDOW = 15 * 60
TOO_MANY_ATTEMPTS = 'יותר מדי ניסיונות. אנא נסו שוב בעוד כמה דקות.'


def register_view(request):
    """
    דף רישום משתמש חדש
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # התחבר אוטומטית לאחר הרישום
            login(request, user)
            messages.success(request, 'הרישום בוצע בהצלחה! ברוך הבא לבוטיק אריה.')
            return redirect('home')
    else:
        form = RegisterForm()
    
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    """
    דף התחברות משתמש
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # מגבלה גם לפי כתובת הגולש וגם לפי החשבון שמנסים להיכנס אליו
        limited = is_rate_limited(request, 'login-ip', limit=20, window=LOGIN_WINDOW)
        username = request.POST.get('username', '')
        if username:
            limited = is_rate_limited(request, 'login-user', limit=10, window=LOGIN_WINDOW, identity=username) or limited
        if limited:
            messages.error(request, TOO_MANY_ATTEMPTS)
            return render(request, 'users/login.html', {'form': LoginForm()}, status=429)

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            # הטופס כבר אימת את שם המשתמש והסיסמה
            user = form.get_user()
            login(request, user)
            messages.success(request, f'שלום {user.first_name or user.username}! התחברת בהצלחה.')
            
            # חזרה לדף שממנו בא (אם קיים) - רק לכתובת בתוך האתר
            next_page = request.GET.get('next')
            if next_page and url_has_allowed_host_and_scheme(
                next_page,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_page)
            return redirect('home')
        else:
            messages.error(request, 'שם משתמש או סיסמה שגויים.')
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """
    התנתקות משתמש
    """
    logout(request)
    messages.success(request, 'התנתקת בהצלחה.')
    return redirect('home')


# Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    """
    דף בקשת שחזור סיסמה - הזנת מייל
    """
    form_class = PasswordResetRequestForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def post(self, request, *args, **kwargs):
        if is_rate_limited(request, 'password-reset', limit=5, window=60 * 60):
            messages.error(request, TOO_MANY_ATTEMPTS)
            return self.render_to_response(self.get_context_data(), status=429)
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        result = super().form_valid(form)
        messages.success(self.request, 'אם כתובת המייל קיימת במערכת, נשלח אליך קישור לאיפוס הסיסמה.')
        return result


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    דף אישור שחזור סיסמה - הגדרת סיסמה חדשה
    """
    form_class = CustomSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')
    
    def form_valid(self, form):
        messages.success(self.request, 'הסיסמה שונתה בהצלחה!')
        return super().form_valid(form)


def password_reset_done(request):
    """
    דף אישור ששליחת המייל בוצעה
    """
    return render(request, 'users/password_reset_done.html')


def password_reset_complete(request):
    """
    דף אישור שהסיסמה שונתה בהצלחה
    """
    return render(request, 'users/password_reset_complete.html')


@login_required
def profile_view(request):
    """
    דף האזור האישי של המשתמש
    מציג מידע אישי, טופס עריכה והיסטוריית הזמנות
    """
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'הפרטים האישיים עודכנו בהצלחה!')
            return redirect('users:profile')
    else:
        form = ProfileEditForm(instance=request.user, user=request.user)
    
    # שליפת כל ההזמנות של המשתמש עם הפריטים
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    
    context = {
        'form': form,
        'orders': orders,
    }
    
    return render(request, 'users/profile.html', context)
