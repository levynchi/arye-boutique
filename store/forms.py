from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """
    טופס צור קשר
    """
    class Meta:
        model = ContactMessage
        fields = ['full_name', 'phone', 'email', 'order_number', 'inquiry']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'שם מלא',
                'required': True,
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'טלפון',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'כתובת אימייל',
                'required': True,
            }),
            'order_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'מספר הזמנה (אופציונלי)',
            }),
            'inquiry': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'מהות הפנייה',
                'rows': 5,
                'required': True,
            }),
        }
        labels = {
            'full_name': 'שם מלא*',
            'phone': 'טלפון*',
            'email': 'כתובת אימייל*',
            'order_number': 'מספר הזמנה',
            'inquiry': 'מהות הפנייה*',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True
        self.fields['phone'].required = True
        self.fields['email'].required = True
        self.fields['inquiry'].required = True
        self.fields['order_number'].required = False

