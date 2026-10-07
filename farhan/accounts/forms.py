# Farhan's part
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Q
from django_mongodb_backend.transaction import atomic
from .models import Profile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def clean_username(self):
        value = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value)).exists():
            raise forms.ValidationError('This username is already in use.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(Q(email__iexact=value) | Q(username__iexact=value)).exists():
            raise forms.ValidationError('This email is already in use.')
        return value

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        with atomic():
            return super().save(commit=True)


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ('first_name', 'last_name', 'email', 'location', 'bio', 'image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('first_name', 'last_name', 'email'):
            self.fields[field].initial = getattr(self.instance.user, field)

    def clean_email(self):
        value = self.cleaned_data['email'].strip().lower()
        if User.objects.exclude(pk=self.instance.user_id).filter(Q(email__iexact=value) | Q(username__iexact=value)).exists():
            raise forms.ValidationError('This email is already in use.')
        return value

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Choose an image smaller than 5 MB.')
            if image.image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise forms.ValidationError('Use a JPG, PNG or WebP image.')
        return image

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        with atomic():
            user = self.instance.user
            for field in ('first_name', 'last_name', 'email'):
                setattr(user, field, self.cleaned_data[field])
            user.save(update_fields=['first_name', 'last_name', 'email'])
            return super().save()
