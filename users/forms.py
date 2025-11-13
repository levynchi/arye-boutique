from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from .models import CustomUser


class RegisterForm(UserCreationForm):
    """
    טופס רישום משתמש חדש
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם פרטי',
        }),
        label='שם פרטי*'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם משפחה',
        }),
        label='שם משפחה*'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'כתובת מייל',
        }),
        label='כתובת מייל*'
    )
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
    
    def clean_email(self):
        """
        בדיקה שהמייל לא קיים כבר במערכת
        """
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('כתובת המייל הזו כבר רשומה במערכת. אנא השתמש במייל אחר או התחבר לחשבון הקיים.')
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # עיצוב שדות הסיסמה
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'סיסמה',
        })
        self.fields['password1'].label = 'סיסמה*'
        self.fields['password1'].help_text = 'הסיסמה חייבת להכיל לפחות 8 תווים ולא יכולה להיות רק מספרים'
        
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'אימות סיסמה',
        })
        self.fields['password2'].label = 'אימות סיסמה*'
        self.fields['password2'].help_text = None
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # יצירת שם משתמש אוטומטית מכתובת המייל
        email = self.cleaned_data['email']
        base_username = email.split('@')[0]
        username = base_username
        
        # אם שם המשתמש כבר קיים, הוסף מספר
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user.username = username
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """
    טופס התחברות משתמש
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם משתמש',
        }),
        label='שם משתמש*'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'סיסמה',
        }),
        label='סיסמה*'
    )


class PasswordResetRequestForm(PasswordResetForm):
    """
    טופס בקשת איפוס סיסמה - הזנת כתובת מייל
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'כתובת מייל',
        }),
        label='כתובת מייל*'
    )


class CustomSetPasswordForm(SetPasswordForm):
    """
    טופס הגדרת סיסמה חדשה
    """
    new_password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'סיסמה חדשה',
        }),
        label='סיסמה חדשה*'
    )
    
    new_password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'אימות סיסמה',
        }),
        label='אימות סיסמה*'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # הסרת הודעות עזרה ברירת מחדל
        self.fields['new_password1'].help_text = None
        self.fields['new_password2'].help_text = None


class ProfileEditForm(forms.ModelForm):
    """
    טופס עריכת פרטים אישיים של משתמש
    """
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם פרטי',
        }),
        label='שם פרטי'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם משפחה',
        }),
        label='שם משפחה'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'כתובת מייל',
        }),
        label='כתובת מייל*'
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'מספר טלפון',
        }),
        label='מספר טלפון'
    )
    
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'כתובת',
        }),
        label='כתובת'
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'עיר',
        }),
        label='עיר'
    )
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'city']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        """
        בדיקה שהמייל לא קיים כבר במערכת (אלא אם זה המייל של המשתמש הנוכחי)
        """
        email = self.cleaned_data.get('email')
        if self.user and CustomUser.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise forms.ValidationError('כתובת המייל הזו כבר רשומה במערכת.')
        return email
