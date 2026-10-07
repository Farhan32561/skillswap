# Farhan's part
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.shortcuts import render
from ankon.skills.models import Skill, SkillOffer
from pranay.exchanges.models import ExchangeRequest, Review

def home(request):
    popular = SkillOffer.objects.filter(user__is_active=True).values('skill').annotate(total=Count('pk')).order_by('-total', 'skill')[:6]
    cards = [SkillOffer.objects.filter(skill_id=row['skill'], user__is_active=True).select_related('user', 'skill', 'skill__category').first() for row in popular]
    rating = Review.objects.aggregate(value=Avg('rating'))['value']
    return render(request, 'home.html', {'popular_skills': cards, 'community': {
        'members': get_user_model().objects.filter(is_active=True).count(),
        'skills': Skill.objects.count(),
        'exchanges': ExchangeRequest.objects.filter(status='completed').count(),
        'rating': f'{rating:.1f}/5' if rating is not None else 'Not rated yet',
    }})
