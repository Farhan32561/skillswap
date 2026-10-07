# Farhan's part
"""Offline checks: no database URI required."""
from types import SimpleNamespace
from unittest.mock import patch
from bson import ObjectId
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from farhan.config.converters import ObjectIdConverter
from pranay.exchanges.services import score_match, transition
from ankon.skills.models import normalize_name

class BackendUnitTests(SimpleTestCase):
    def test_two_way_score_and_one_way_score(self):
        self.assertEqual(score_match({'django':'advanced'}, {'photoshop':'beginner'}, {'photoshop':'advanced'}, {'django':'beginner'}, True)[0], 100)
        self.assertEqual(score_match({}, {'python':'beginner'}, {'python':'advanced'}, {}, False)[0], 45)
        self.assertEqual(score_match({}, {}, {}, {}, True)[0], 0)

    def test_location_bonus_requires_compatible_skills(self):
        self.assertEqual(score_match({'a':'beginner'}, {}, {}, {'a':'expert'}, False)[0], 40)
        self.assertEqual(score_match({'a':'beginner'}, {}, {}, {'a':'expert'}, True)[0], 45)

    def test_names_are_normalized(self):
        self.assertEqual(normalize_name('  DjAnGo   REST  '), 'django rest')

    def test_objectid_routes(self):
        pk=ObjectId()
        for name in ('user_profile','skill_detail','edit_skill','remove_skill','exchange_detail','review','send_exchange_request','accept_exchange','reject_exchange','cancel_exchange','complete_exchange'):
            with self.subTest(route=name):
                match=resolve(reverse(name,args=[pk]))
                self.assertEqual(match.kwargs['pk'],pk)
        self.assertEqual(ObjectIdConverter().to_python(str(pk)),pk)

    def test_templates_compile(self):
        from django.conf import settings
        from django.apps import apps
        from pathlib import Path
        directories = [settings.BASE_DIR/'templates'] + [Path(app.path)/'templates' for app in apps.get_app_configs()]
        for directory in directories:
            for path in directory.rglob('*.html'):
                get_template(path.relative_to(directory).as_posix())

    def test_team_paths_preserve_app_labels_and_database_tables(self):
        from django.apps import apps
        from django.conf import settings
        self.assertTrue((settings.BASE_DIR/'manage.py').is_file())
        for label, package in [('accounts','farhan.accounts'),('skills','ankon.skills'),('exchanges','pranay.exchanges')]:
            self.assertEqual(apps.get_app_config(label).name,package)
        self.assertEqual(apps.get_model('accounts.Profile')._meta.db_table,'accounts_profile')
        self.assertEqual(apps.get_model('skills.Skill')._meta.db_table,'skills_skill')
        self.assertEqual(apps.get_model('exchanges.ExchangeRequest')._meta.db_table,'exchanges_exchangerequest')

    def test_existing_login_session_backend_is_preserved(self):
        from farhan.accounts.middleware import PreserveLoginBackendMiddleware
        request=SimpleNamespace(session={'_auth_user_backend':'accounts.backends.UsernameOrEmailBackend','_auth_user_id':'unchanged'})
        middleware=PreserveLoginBackendMiddleware(lambda request: request.session)
        result=middleware(request)
        self.assertEqual(result['_auth_user_backend'],'farhan.accounts.backends.UsernameOrEmailBackend')
        self.assertEqual(result['_auth_user_id'],'unchanged')

    def test_protected_pages_redirect_anonymous_users(self):
        for name in ('profile','edit_profile','my_skills','add_skill','dashboard','matches','exchange_requests','exchange_history'):
            response=self.client.get(reverse(name))
            self.assertEqual(response.status_code,302)
            self.assertTrue(response.url.startswith(reverse('login')))

    def test_invalid_objectid_is_404(self):
        self.assertEqual(self.client.get('/skills/not-an-object-id/').status_code,404)

    def test_transition_role_and_state_validation(self):
        item=SimpleNamespace(pk=ObjectId(),sender_id='a',receiver_id='b',status='pending',active_key='a:b')
        with self.assertRaises(PermissionDenied): transition(item,SimpleNamespace(pk='x'),'accept')
        with self.assertRaises(PermissionDenied): transition(item,SimpleNamespace(pk='a'),'accept')
        with self.assertRaises(PermissionDenied): transition(item,SimpleNamespace(pk='b'),'cancel')
        with self.assertRaises(ValidationError): transition(item,SimpleNamespace(pk='a'),'complete')
        with patch('pranay.exchanges.services.ExchangeRequest.objects.filter') as query:
            query.return_value.update.return_value=0
            with self.assertRaises(ValidationError): transition(item,SimpleNamespace(pk='b'),'accept')
            self.assertEqual(query.call_args.kwargs['status'],'pending')

    def test_csrf_blocks_mutations(self):
        from django.test import Client
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('register'),{}).status_code,403)
