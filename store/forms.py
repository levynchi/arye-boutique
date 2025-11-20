from django import forms
from .models import ContactMessage, Order, Size, SizeGroup, FabricType, ProductVariant, Product


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


class CheckoutForm(forms.Form):
    """
    טופס פרטים להזמנה
    """
    guest_name = forms.CharField(
        max_length=100,
        required=True,
        label='שם מלא*',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'שם מלא',
        })
    )
    guest_phone = forms.CharField(
        max_length=20,
        required=True,
        label='טלפון*',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'טלפון',
        })
    )
    guest_email = forms.EmailField(
        required=True,
        label='אימייל*',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'דוא״ל',
        })
    )
    guest_address = forms.CharField(
        max_length=255,
        required=True,
        label='כתובת*',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'רחוב ומספר בית',
        })
    )
    guest_city = forms.CharField(
        max_length=100,
        required=True,
        label='עיר*',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'עיר',
        })
    )
    notes = forms.CharField(
        required=False,
        label='הערות',
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'הערות להזמנה (אופציונלי)',
            'rows': 4,
        })
    )


class BulkVariantCreationForm(forms.Form):
    """
    טופס ליצירת וריאנטים אוטומטית - בד + מידות/קבוצת מידות
    """
    SIZE_CHOICE_TYPES = [
        ('single', 'מידות בודדות'),
        ('group', 'קבוצת מידות'),
    ]
    
    choice_type = forms.ChoiceField(
        choices=SIZE_CHOICE_TYPES,
        widget=forms.RadioSelect,
        label='סוג בחירה',
        initial='single'
    )
    
    sizes = forms.ModelMultipleChoiceField(
        queryset=Size.objects.filter(is_active=True),
        required=False,
        label='בחר מידות',
        widget=forms.CheckboxSelectMultiple,
        help_text='בחר מידה אחת או יותר'
    )
    
    size_group = forms.ModelChoiceField(
        queryset=SizeGroup.objects.filter(is_active=True),
        required=False,
        label='בחר קבוצת מידות',
        help_text='קבוצת מידות תוסיף את כל המידות שבה'
    )
    
    fabric_types = forms.ModelMultipleChoiceField(
        queryset=FabricType.objects.filter(is_active=True),
        required=True,
        label='בחר סוגי בד',
        widget=forms.CheckboxSelectMultiple,
        help_text='בחר בד אחד או יותר'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        choice_type = cleaned_data.get('choice_type')
        sizes = cleaned_data.get('sizes')
        size_group = cleaned_data.get('size_group')
        fabric_types = cleaned_data.get('fabric_types')
        
        # וידוא שנבחרה לפחות מידה אחת או קבוצה אחת
        if choice_type == 'single' and not sizes:
            raise forms.ValidationError('יש לבחור לפחות מידה אחת')
        
        if choice_type == 'group' and not size_group:
            raise forms.ValidationError('יש לבחור קבוצת מידות')
        
        if not fabric_types:
            raise forms.ValidationError('יש לבחור לפחות סוג בד אחד')
        
        return cleaned_data
    
    def get_sizes_list(self):
        """החזרת רשימת המידות לפי הבחירה"""
        choice_type = self.cleaned_data.get('choice_type')
        
        if choice_type == 'single':
            return list(self.cleaned_data.get('sizes', []))
        elif choice_type == 'group':
            size_group = self.cleaned_data.get('size_group')
            if size_group:
                return list(size_group.sizes.all())
        
        return []


class ProductAdminForm(forms.ModelForm):
    """
    טופס מותאם למוצר בממשק Admin עם אפשרות ליצור וריאנטים ישירות
    """
    SIZE_CHOICE_TYPES = [
        ('single', 'מידות בודדות'),
        ('group', 'קבוצת מידות'),
    ]
    
    # שדות נוספים ליצירת וריאנטים (לא חובה)
    variant_choice_type = forms.ChoiceField(
        choices=SIZE_CHOICE_TYPES,
        widget=forms.RadioSelect,
        label='סוג בחירה',
        initial='single',
        required=False,
        help_text='בחר איך להוסיף מידות'
    )
    
    variant_sizes = forms.ModelMultipleChoiceField(
        queryset=Size.objects.filter(is_active=True),
        required=False,
        label='בחר מידות',
        widget=forms.CheckboxSelectMultiple,
        help_text='בחר מידה אחת או יותר (אופציונלי)'
    )
    
    variant_size_group = forms.ModelChoiceField(
        queryset=SizeGroup.objects.filter(is_active=True),
        required=False,
        label='בחר קבוצת מידות',
        help_text='קבוצת מידות תוסיף את כל המידות שבה (אופציונלי)'
    )
    
    variant_fabric_types = forms.ModelMultipleChoiceField(
        queryset=FabricType.objects.filter(is_active=True),
        required=False,
        label='בחר סוגי בד',
        widget=forms.CheckboxSelectMultiple,
        help_text='בחר בד אחד או יותר ליצירת וריאנטים (אופציונלי)'
    )
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # הוספת מחלקות CSS לשדות הוריאנטים
        self.fields['variant_choice_type'].widget.attrs.update({'class': 'variant-choice-type'})
        self.fields['variant_sizes'].widget.attrs.update({'class': 'variant-sizes'})
        self.fields['variant_size_group'].widget.attrs.update({'class': 'variant-size-group'})
        self.fields['variant_fabric_types'].widget.attrs.update({'class': 'variant-fabrics'})
    
    def save(self, commit=True):
        """שמירת המוצר ויצירת וריאנטים אם נבחרו"""
        product = super().save(commit=commit)
        
        if commit:
            # בדיקה אם נבחרו מידות ובדים ליצירת וריאנטים
            fabric_types = self.cleaned_data.get('variant_fabric_types')
            choice_type = self.cleaned_data.get('variant_choice_type')
            
            if fabric_types:
                sizes_list = self._get_sizes_list()
                
                if sizes_list:
                    # יצירת וריאנטים עבור כל שילוב של בד + מידה
                    created_count = 0
                    for fabric in fabric_types:
                        for size in sizes_list:
                            # יצירה רק אם לא קיים
                            variant, created = ProductVariant.objects.get_or_create(
                                product=product,
                                fabric_type=fabric,
                                size=size,
                                defaults={
                                    'is_available': True,
                                    'warehouse_location': ''
                                }
                            )
                            if created:
                                created_count += 1
        
        return product
    
    def _get_sizes_list(self):
        """החזרת רשימת המידות לפי הבחירה"""
        choice_type = self.cleaned_data.get('variant_choice_type')
        
        if choice_type == 'single':
            return list(self.cleaned_data.get('variant_sizes', []))
        elif choice_type == 'group':
            size_group = self.cleaned_data.get('variant_size_group')
            if size_group:
                return list(size_group.sizes.all())
        
        return []
