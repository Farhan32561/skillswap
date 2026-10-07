# Farhan's part
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_mongodb_backend.transaction import atomic
from ankon.skills.models import CATEGORIES, SkillCategory, Skill, SkillOffer, SkillWanted, normalize_name
from pranay.exchanges.models import ExchangeRequest, Review
from pranay.exchanges.services import send_request, transition, write_review


class Command(BaseCommand):
    help = 'Create opt-in demo accounts and complementary skills; safe to rerun.'

    def add_arguments(self, parser):
        parser.add_argument('--allow-production', action='store_true', help='Explicitly allow seeding when DEBUG is false.')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError('Demo seeding is disabled with DEBUG=False. Use --allow-production only intentionally.')
        users, credentials = {}, []
        with atomic():
            categories = {}
            for slug, name in CATEGORIES:
                categories[slug], _ = SkillCategory.objects.get_or_create(slug=slug, defaults={'name': name})
            for name in ('farhan', 'ankon', 'pranay'):
                user, created = get_user_model().objects.get_or_create(username=f'{name}_demo', defaults={
                    'first_name': name.title(), 'last_name': 'Demo', 'email': f'{name}_demo@example.test',
                })
                if created:
                    password = secrets.token_urlsafe(18)
                    user.set_password(password)
                    user.save(update_fields=['password'])
                    user.profile.location = 'Dhaka, Bangladesh'
                    user.profile.bio = 'Demo member for exploring skill exchanges.'
                    user.profile.save()
                    credentials.append((user.username, password))
                users[name] = user
            catalog = {}
            for name, category in [('Django', 'programming'), ('Python', 'programming'), ('Photoshop', 'design'),
                                   ('Graphic Design', 'design'), ('English', 'language'), ('Photography', 'photography')]:
                catalog[name], _ = Skill.objects.get_or_create(normalized_name=normalize_name(name), defaults={
                    'name': name, 'category': categories[category], 'description': f'Learn {name} through practical exercises.',
                })
            for person, taught, wanted in [('farhan', ['Django', 'Python'], ['Photoshop', 'English']),
                                          ('ankon', ['Photoshop', 'Graphic Design'], ['Django']),
                                          ('pranay', ['English', 'Photography'], ['Python'])]:
                for model, names, level in [(SkillOffer, taught, 'advanced'), (SkillWanted, wanted, 'beginner')]:
                    for name in names:
                        model.objects.get_or_create(user=users[person], skill=catalog[name], defaults={
                            'experience_level': level, 'description': f'Practical {name} learning sessions.',
                        })
            # A recognizable marker makes this history item idempotent.
            marker = 'SkillSwap seed_demo completed example'
            exchange = ExchangeRequest.objects.filter(sender=users['farhan'], receiver=users['ankon'], message=marker).first()
            if exchange is None and not ExchangeRequest.objects.filter(active_key=ExchangeRequest.pair_key(users['farhan'].pk, users['ankon'].pk)).exists():
                exchange = send_request(users['farhan'], users['ankon'], catalog['Django'], catalog['Photoshop'], marker)
                transition(exchange, users['ankon'], 'accept')
                exchange.refresh_from_db()
                transition(exchange, users['farhan'], 'complete')
                exchange.refresh_from_db()
                write_review(exchange, users['farhan'], 5, 'Clear explanations and helpful practical examples.')
        for username, password in credentials:
            self.stdout.write(f'{username} — new demo password: {password}')
        self.stdout.write(self.style.SUCCESS('Demo data ready. Existing accounts and passwords were preserved.'))
