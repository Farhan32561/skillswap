"""Frontend-only verification and static preview export; no application backend.

Run: python tools/check_templates.py [--preview-dir PATH]
Requires Django >= 5.1. Preview forms are intentionally disabled.
"""
import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import django
from django.conf import settings
from django.template.loader import get_template
from django.urls import path
from django.core.paginator import Paginator
from django.http import QueryDict

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOTS = [ROOT / 'templates', ROOT / 'farhan/accounts/templates', ROOT / 'ankon/skills/templates', ROOT / 'pranay/exchanges/templates']
PAGES = {
    'home': 'home.html',
    **{name: f'accounts/{name}.html' for name in ['login', 'register', 'profile', 'edit_profile', 'user_profile']},
    **{name: f'skills/{name}.html' for name in ['skills', 'add_skill', 'skill_detail', 'search_skills', 'my_skills']},
    **{name: f'exchanges/{name}.html' for name in ['dashboard', 'matches', 'exchange_requests', 'exchange_detail', 'exchange_history', 'review']},
}
URLS_WITH_ID = {'user_profile', 'skill_detail', 'edit_skill', 'remove_skill', 'send_exchange_request', 'respond_exchange', 'complete_exchange', 'cancel_exchange', 'exchange_detail', 'review'}
ALL_NAMES = set(PAGES) | {'logout', 'edit_skill', 'remove_skill', 'send_exchange_request', 'respond_exchange', 'complete_exchange', 'cancel_exchange'}
# These URL objects only exercise {% url %}; no views or request handling exist.
urlpatterns = [path(f'{name}/' + ('<int:pk>/' if name in URLS_WITH_ID else ''), lambda request: None, name=name) for name in sorted(ALL_NAMES)]
settings.configure(
    DEBUG=True, SECRET_KEY='template-check-only', ROOT_URLCONF=__name__,
    STATIC_URL='/static/',
    TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': TEMPLATE_ROOTS}],
)
django.setup()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir', type=Path)
    args = parser.parse_args()
    for directory in TEMPLATE_ROOTS:
        for template in directory.rglob('*.html'):
            get_template(template.relative_to(directory).as_posix())
    rendered_count = 0
    for name, template in PAGES.items():
        for demo in [False, True]:
            for authenticated in [False, True]:
                context = {'demo_mode': demo, 'user': SimpleNamespace(is_authenticated=authenticated, first_name='Farhan', username='farhan'), 'request': SimpleNamespace(GET={}, resolver_match=SimpleNamespace(url_name=name)), 'csrf_token': 'preview-only'}
                if demo:
                    context['profile'] = SimpleNamespace(user=SimpleNamespace(pk=1, first_name='Farhan', username='farhan', get_full_name='Farhan Ahmed'), location='Dhaka, Bangladesh', bio='Learning and sharing together.', completed_exchanges=8, rating=4.8, review_count=5)
                html = get_template(template).render(context)
                assert '<main ' in html and '<footer ' in html, template
                assert '{%' not in html and '{{' not in html, template
                assert '<script' not in html.lower(), template
                assert ' style=' not in html.lower(), template
                rendered_count += 1
                if args.preview_dir and demo and not authenticated:
                    out = args.preview_dir / (name + '.html')
                    out.parent.mkdir(parents=True, exist_ok=True)
                    # Convert Django route output to the corresponding static preview page.
                    for route in sorted(ALL_NAMES, key=len, reverse=True):
                        target = 'add_skill' if route == 'edit_skill' else route
                        html = re.sub(r'(?<=href=")/' + route + r'/(?:\d+/)?', f'/{target}.html', html)
                    out.write_text(html, encoding='utf-8')
    member = {'pk': 42, 'first_name': 'Taylor', 'get_full_name': 'Taylor Example', 'username': 'taylor', 'date_joined': datetime(2026, 9, 1, tzinfo=timezone.utc), 'location': 'Dhaka', 'rating': 4.5, 'offered_skill': 'Drawing', 'wanted_skill': 'Python'}
    skill = {'pk': 9, 'name': 'Drawing', 'description': 'Practice observational drawing.', 'get_category_display': 'Design', 'get_level_display': 'Beginner', 'get_skill_type_display': 'Can Teach', 'owner': member, 'successful_exchanges': 0}
    review = {'rating': 4, 'comment': 'Helpful & encouraging <teacher>', 'created_at': datetime.now(timezone.utc)}
    exchange = {'pk': 7, 'partner': member, 'status': 'pending', 'get_status_display': 'Pending', 'you_teach': 'Python', 'you_learn': 'Drawing', 'offered_skill': 'Drawing', 'wanted_skill': 'Python', 'completed_at': datetime.now(timezone.utc), 'review': review}
    match = {'pk': 8, 'person': member, 'percentage': 0, 'you_teach': 'Python', 'you_learn': 'Drawing'}
    populated = {'user': SimpleNamespace(is_authenticated=True, first_name='Taylor', username='taylor'), 'request': SimpleNamespace(GET=QueryDict('q=Drawing&category=design')), 'csrf_token': 'test-token', 'profile': dict(user=member, bio='I enjoy drawing.', location='Dhaka', completed_exchanges=0, rating=4.5, review_count=1), 'skill': skill, 'exchange': exchange, 'review': review, 'page_obj': Paginator([skill] * 3, 1).page(2)}
    for key in ['popular_skills', 'skills', 'teaching_skills', 'learning_skills']:
        populated[key] = [skill]
    for key in ['people', 'teachers']:
        populated[key] = [member]
    for key in ['matches', 'recommended_matches']:
        populated[key] = [match]
    for key in ['recent_requests', 'received_requests', 'sent_requests', 'completed_exchanges']:
        populated[key] = [exchange]
    for name, template in PAGES.items():
        html = get_template(template).render(populated)
        assert 'preview-only' not in html
        if name == 'matches':
            assert '0% match' in html and 'value="0"' in html
        if name == 'review':
            assert '&lt;teacher&gt;' in html
        if name == 'skills':
            assert 'page=3' in html and 'category=design' in html
        rendered_count += 1
    if args.preview_dir:
        shutil.copytree(ROOT / 'static', args.preview_dir / 'static', dirs_exist_ok=True)
        shutil.copyfile(args.preview_dir / 'home.html', args.preview_dir / 'index.html')
    print(f'PASS: all templates compiled; {rendered_count} renders across {len(PAGES)} pages, demo/empty, authentication and populated states.')
    print('PASS: real object IDs, zero match score, escaped review text and filter-preserving pagination.')
    print('PASS: shared layout, URL reversal, no JavaScript and no inline styles.')

if __name__ == '__main__':
    main()
