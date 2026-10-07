# Pranay's part
from collections import defaultdict
from types import SimpleNamespace
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from ankon.skills.models import SkillOffer, SkillWanted, LEVELS
from .models import ExchangeRequest, Review

LEVEL_RANK = {name: i for i, (name, _) in enumerate(LEVELS)}


def score_match(my_offers, my_wants, their_offers, their_wants, same_location=False):
    """40 per compatible direction, 10 for reciprocity, 5 location, 5 levels."""
    teach = set(my_offers) & set(their_wants)
    learn = set(their_offers) & set(my_wants)
    if not teach and not learn:
        return 0, teach, learn
    score = 40 * bool(teach) + 40 * bool(learn) + 10 * bool(teach and learn)
    score += 5 * bool(same_location)
    qualified = (
        any(LEVEL_RANK[my_offers[s]] >= LEVEL_RANK[their_wants[s]] for s in teach)
        or any(LEVEL_RANK[their_offers[s]] >= LEVEL_RANK[my_wants[s]] for s in learn)
    )
    return min(100, score + 5 * qualified), teach, learn


def find_matches(user):
    from farhan.accounts.presentation import person_card
    my_offers = {s.skill_id: s.experience_level for s in SkillOffer.objects.filter(user=user)}
    my_wants = {s.skill_id: s.experience_level for s in SkillWanted.objects.filter(user=user)}
    candidate_ids = set(SkillOffer.objects.filter(skill_id__in=list(my_wants), user__is_active=True).exclude(user=user).values_list('user_id', flat=True))
    candidate_ids.update(SkillWanted.objects.filter(skill_id__in=list(my_offers), user__is_active=True).exclude(user=user).values_list('user_id', flat=True))
    offers, wants, people, names = defaultdict(dict), defaultdict(dict), {}, {}
    for model, target in ((SkillOffer, offers), (SkillWanted, wants)):
        for item in model.objects.filter(user_id__in=list(candidate_ids)).select_related('user', 'skill'):
            target[item.user_id][item.skill_id] = item.experience_level
            people[item.user_id] = item.user
            names[item.skill_id] = item.skill.name
    my_location = getattr(getattr(user, 'profile', None), 'location', '').strip().casefold()
    result = []
    for pk, candidate in people.items():
        location = getattr(getattr(candidate, 'profile', None), 'location', '').strip().casefold()
        score, teach, learn = score_match(my_offers, my_wants, offers[pk], wants[pk], bool(my_location and my_location == location))
        if score:
            result.append(SimpleNamespace(
                pk=pk, person=person_card(candidate), percentage=score,
                you_teach=', '.join(sorted(names[s] for s in teach)) or 'No shared skill yet',
                you_learn=', '.join(sorted(names[s] for s in learn)) or 'No shared skill yet',
            ))
    return sorted(result, key=lambda m: (-m.percentage, m.person.get_full_name.casefold(), str(m.pk)))


def validate_pair(sender, receiver, sender_skill, receiver_skill):
    if sender.pk == receiver.pk:
        raise ValidationError('You cannot exchange skills with yourself.')
    if not sender.is_active or not receiver.is_active:
        raise ValidationError('Both accounts must be active.')
    if not (SkillOffer.objects.filter(user=sender, skill=sender_skill).exists()
            and SkillWanted.objects.filter(user=receiver, skill=sender_skill).exists()
            and SkillOffer.objects.filter(user=receiver, skill=receiver_skill).exists()
            and SkillWanted.objects.filter(user=sender, skill=receiver_skill).exists()):
        raise ValidationError('Choose skills that each participant teaches and the other wants to learn.')


def send_request(sender, receiver, sender_skill, receiver_skill, message=''):
    validate_pair(sender, receiver, sender_skill, receiver_skill)
    key = ExchangeRequest.pair_key(sender.pk, receiver.pk)
    if ExchangeRequest.objects.filter(active_key=key).exists():
        raise ValidationError('You already have a pending or accepted exchange with this person.')
    exchange = ExchangeRequest(sender=sender, receiver=receiver, sender_skill=sender_skill,
                               receiver_skill=receiver_skill, message=message, active_key=key)
    exchange.full_clean(validate_unique=False)
    try:
        exchange.save(force_insert=True)
    except IntegrityError as exc:
        raise ValidationError('An active exchange with this person already exists.') from exc
    return exchange


def transition(exchange, actor, action):
    """Validate role/state, then atomically update only the expected old state."""
    if actor.pk not in (exchange.sender_id, exchange.receiver_id):
        raise PermissionDenied('This exchange belongs to other users.')
    if action in ('accept', 'reject'):
        if actor.pk != exchange.receiver_id:
            raise PermissionDenied('Only the recipient may respond.')
        if exchange.status != 'pending':
            raise ValidationError('Only pending requests can be accepted or rejected.')
        new_status = 'accepted' if action == 'accept' else 'rejected'
    elif action == 'cancel':
        if exchange.status == 'pending' and actor.pk != exchange.sender_id:
            raise PermissionDenied('Only the sender may cancel a pending request.')
        if exchange.status not in ('pending', 'accepted'):
            raise ValidationError('This exchange can no longer be cancelled.')
        new_status = 'cancelled'
    elif action == 'complete':
        if exchange.status != 'accepted':
            raise ValidationError('Only accepted exchanges can be completed.')
        new_status = 'completed'
    else:
        raise ValidationError('Unknown exchange action.')
    now = timezone.now()
    updated = ExchangeRequest.objects.filter(pk=exchange.pk, status=exchange.status).update(
        status=new_status, updated_at=now,
        active_key=exchange.active_key if new_status == 'accepted' else None,
        completed_at=now if new_status == 'completed' else None,
    )
    if not updated:
        raise ValidationError('This exchange changed. Refresh the page before trying again.')
    return new_status


def write_review(exchange, reviewer, rating, comment):
    if reviewer.pk not in (exchange.sender_id, exchange.receiver_id):
        raise PermissionDenied('Only participants may review this exchange.')
    partner = exchange.receiver if reviewer.pk == exchange.sender_id else exchange.sender
    review = Review(exchange=exchange, reviewer=reviewer, reviewed_user=partner, rating=rating, comment=comment)
    review.full_clean(validate_constraints=False)
    try:
        review.save(force_insert=True)
    except IntegrityError as exc:
        raise ValidationError('You have already reviewed this exchange.') from exc
    return review


def for_participant(user):
    return ExchangeRequest.objects.filter(Q(sender=user) | Q(receiver=user)).select_related('sender', 'receiver', 'sender_skill', 'receiver_skill')


def present_exchange(exchange, viewer):
    sent = exchange.sender_id == viewer.pk
    exchange.partner = exchange.receiver if sent else exchange.sender
    exchange.you_teach = exchange.sender_skill if sent else exchange.receiver_skill
    exchange.you_learn = exchange.receiver_skill if sent else exchange.sender_skill
    exchange.offered_skill, exchange.wanted_skill = exchange.sender_skill, exchange.receiver_skill
    exchange.review = exchange.reviews.filter(reviewer=viewer).first()
    exchange.can_respond = not sent and exchange.status == 'pending'
    exchange.can_cancel = (sent and exchange.status == 'pending') or exchange.status == 'accepted'
    return exchange
