from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from .forms import RegisterForm, LoginForm, PasswordResetRequestForm, CustomSetPasswordForm


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
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'שלום {user.first_name or user.username}! התחברת בהצלחה.')
                
                # חזרה לדף שממנו בא (אם קיים)
                next_page = request.GET.get('next')
                if next_page:
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
    
    def dispatch(self, request, *args, **kwargs):
        print("\n" + "=" * 80)
        print("PASSWORD RESET VIEW - DISPATCH")
        print(f"Method: {request.method}")
        print(f"Path: {request.path}")
        print("=" * 80)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        print("\n" + "=" * 80)
        print("POST REQUEST RECEIVED")
        print(f"POST Data: {request.POST}")
        print(f"Email from POST: {request.POST.get('email')}")
        print("=" * 80)
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        print("\n" + "=" * 80)
        print("FORM IS VALID!")
        print(f"Email: {form.cleaned_data.get('email')}")
        print("Attempting to send email...")
        print("=" * 80)
        
        result = super().form_valid(form)
        
        print("\n" + "=" * 80)
        print("EMAIL SHOULD BE SENT NOW - CHECK CONSOLE OUTPUT ABOVE")
        print("=" * 80 + "\n")
        
        messages.success(self.request, 'אם כתובת המייל קיימת במערכת, נשלח אליך קישור לאיפוס הסיסמה.')
        return result
    
    def form_invalid(self, form):
        print("\n" + "=" * 80)
        print("FORM IS INVALID!")
        print(f"Errors: {form.errors}")
        print("=" * 80 + "\n")
        return super().form_invalid(form)


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
