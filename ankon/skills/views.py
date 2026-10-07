# Ankon's part
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from farhan.accounts.presentation import person_card
from .forms import SkillForm
from .models import Skill, SkillOffer, SkillWanted

def filtered_memberships(request, model):
    records = model.objects.filter(user__is_active=True).select_related('user', 'skill', 'skill__category')
    q = request.GET.get('q', '').strip()[:200]
    if q:
        records = records.filter(Q(skill__name__icontains=q) | Q(skill__category__name__icontains=q)
                                 | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                                 | Q(user__username__icontains=q))
    for parameter, field in [('category', 'skill__category__slug'), ('level', 'experience_level'), ('location', 'user__profile__location__icontains')]:
        value = request.GET.get(parameter, '').strip()[:150]
        if value:
            records = records.filter(**{field: value})
    return records

def skills(request):
    model = SkillWanted if request.GET.get('skill_type') == 'learn' else SkillOffer
    page = Paginator(filtered_memberships(request, model), 12).get_page(request.GET.get('page'))
    return render(request, 'skills/skills.html', {'skills': page.object_list, 'page_obj': page})

@login_required
def my_skills(request):
    return render(request, 'skills/my_skills.html', {
        'teaching_skills': SkillOffer.objects.filter(user=request.user).select_related('skill', 'skill__category'),
        'learning_skills': SkillWanted.objects.filter(user=request.user).select_related('skill', 'skill__category'),
    })

def owned_skill(user, pk):
    for model in (SkillOffer, SkillWanted):
        obj = model.objects.filter(pk=pk, user=user).select_related('skill', 'skill__category').first()
        if obj:
            return obj
    raise Http404('Skill not found.')

def skill_form_page(request, instance=None):
    form = SkillForm(request.POST if request.method == 'POST' else None, user=request.user, instance=instance,
                     initial={'skill_type': request.GET.get('skill_type') if request.GET.get('skill_type') in ('teach', 'learn') else 'teach'})
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, 'This skill was just added. Refresh and try again.')
        except ValidationError as error:
            form.add_error(None, error.messages)
        else:
            messages.success(request, 'Your skill has been saved.')
            return redirect('my_skills')
    return render(request, 'skills/add_skill.html', {'form': form, 'editing': instance is not None})

@login_required
@require_http_methods(['GET', 'POST'])
def add_skill(request):
    return skill_form_page(request)

@login_required
@require_http_methods(['GET', 'POST'])
def edit_skill(request, pk):
    return skill_form_page(request, owned_skill(request.user, pk))

@login_required
@require_POST
def remove_skill(request, pk):
    owned_skill(request.user, pk).delete()
    messages.success(request, 'Skill removed from your profile. Past exchanges are preserved.')
    return redirect('my_skills')

def search_skills(request):
    skill_type = request.GET.get('skill_type')
    models = [SkillOffer] if skill_type == 'teach' else [SkillWanted] if skill_type == 'learn' else [SkillOffer, SkillWanted]
    ids = set()
    for model in models:
        ids.update(filtered_memberships(request, model).values_list('user_id', flat=True))
    users = get_user_model().objects.filter(is_active=True)
    q = request.GET.get('q', '').strip()[:200]
    if not any(request.GET.get(key) for key in ('category', 'level', 'skill_type')):
        if q:
            users = users.filter(Q(pk__in=list(ids)) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q))
    else:
        users = users.filter(pk__in=list(ids))
    location = request.GET.get('location', '').strip()[:150]
    if location:
        users = users.filter(profile__location__icontains=location)
    page = Paginator(users.order_by('username', 'pk'), 12).get_page(request.GET.get('page'))
    return render(request, 'skills/search_skills.html', {'people': [person_card(user) for user in page], 'page_obj': page})

def skill_detail(request, pk):
    skill = get_object_or_404(Skill.objects.select_related('category'), pk=pk)
    offers = SkillOffer.objects.filter(skill=skill, user__is_active=True).select_related('user')
    teachers = []
    for offer in offers:
        person = person_card(offer.user)
        person.offered_skill = skill.name
        teachers.append(person)
    return render(request, 'skills/skill_detail.html', {'skill': skill, 'teachers': teachers})
