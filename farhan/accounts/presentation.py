# Farhan's part
from types import SimpleNamespace
from ankon.skills.models import SkillOffer, SkillWanted


def person_card(user):
    profile = getattr(user, 'profile', None)
    offered = SkillOffer.objects.filter(user=user).select_related('skill').first()
    wanted = SkillWanted.objects.filter(user=user).select_related('skill').first()
    return SimpleNamespace(
        pk=user.pk, first_name=user.first_name or user.username,
        get_full_name=user.get_full_name() or user.username,
        location=profile.location if profile and profile.location else 'Location not set',
        rating=profile.rating if profile and profile.rating is not None else '—',
        offered_skill=offered.skill.name if offered else 'No teaching skills yet',
        wanted_skill=wanted.skill.name if wanted else 'No learning skills yet',
    )
