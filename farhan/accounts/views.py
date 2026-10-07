# Farhan's part
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from .forms import RegistrationForm, LoginForm, ProfileForm
from .models import Profile
from ankon.skills.models import SkillOffer, SkillWanted

@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error(None, 'This account already exists. Please choose another username or log in.')
        else:
            auth_login(request, user, backend='farhan.accounts.backends.UsernameOrEmailBackend')
            messages.success(request, 'Welcome to SkillSwap! Add your first skills to find a match.')
            return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})

@require_http_methods(['GET', 'POST'])
def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        auth_login(request, form.get_user())
        request.session.set_expiry(1209600 if form.cleaned_data['remember_me'] else 0)
        return redirect('dashboard')
    return render(request, 'accounts/login.html', {'form': form})

@require_POST
def logout(request):
    auth_logout(request)
    return redirect('home')

def profile_context(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return {'profile': profile,
            'teaching_skills': SkillOffer.objects.filter(user=user).select_related('skill', 'skill__category'),
            'learning_skills': SkillWanted.objects.filter(user=user).select_related('skill', 'skill__category')}

@login_required
def profile(request):
    return render(request, 'accounts/profile.html', profile_context(request.user))

def user_profile(request, pk):
    person = get_object_or_404(get_user_model(), pk=pk, is_active=True)
    if request.user.is_authenticated and person.pk == request.user.pk:
        return redirect('profile')
    return render(request, 'accounts/user_profile.html', profile_context(person))

@login_required
@require_http_methods(['GET', 'POST'])
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST if request.method == 'POST' else None,
                       request.FILES if request.method == 'POST' else None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except (IntegrityError, ValidationError):
            form.add_error(None, 'Your profile could not be saved. Check your details and try again.')
        else:
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    return render(request, 'accounts/edit_profile.html', {'form': form})
