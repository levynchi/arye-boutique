from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    מודל משתמש מותאם עם שדות נוספים עבור החנות
    """
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='מספר טלפון')
    address = models.CharField(max_length=255, blank=True, verbose_name='כתובת')
    city = models.CharField(max_length=100, blank=True, verbose_name='עיר')
    email = models.EmailField(unique=True, verbose_name='כתובת מייל')  # הוספת unique constraint
    
    class Meta:
        verbose_name = 'משתמש'
        verbose_name_plural = 'משתמשים'
    
    def __str__(self):
        return self.username
