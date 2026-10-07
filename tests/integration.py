"""Run explicitly against MongoDB: python manage.py test tests.integration.

Django creates and destroys a separate test_<MONGODB_NAME> database.
The account must have permission to create/drop that test database.
"""
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from farhan.accounts.forms import ProfileForm, RegistrationForm
from ankon.skills.forms import SkillForm
from ankon.skills.models import SkillCategory, Skill, SkillOffer, SkillWanted
from pranay.exchanges.models import ExchangeRequest, Review
from pranay.exchanges.services import find_matches, send_request, transition, write_review


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BackendIntegrationTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user('farhan', 'farhan@example.test', 'test-password', first_name='Farhan')
        self.b = User.objects.create_user('ankon', 'ankon@example.test', 'test-password', first_name='Ankon')
        self.c = User.objects.create_user('pranay', 'pranay@example.test', 'test-password', first_name='Pranay')
        for user in (self.a, self.b):
            user.profile.location = 'Dhaka'
            user.profile.save()
        category = SkillCategory.objects.create(name='Programming', slug='programming')
        self.django = Skill.objects.create(name='Django', category=category)
        self.python = Skill.objects.create(name='Python', category=category)
        self.offer_a = SkillOffer.objects.create(user=self.a, skill=self.django, experience_level='advanced', description='Django projects')
        self.offer_b = SkillOffer.objects.create(user=self.b, skill=self.python, experience_level='advanced', description='Python projects')
        SkillWanted.objects.create(user=self.a, skill=self.python, experience_level='beginner', description='Learn Python')
        SkillWanted.objects.create(user=self.b, skill=self.django, experience_level='beginner', description='Learn Django')

    def request_exchange(self):
        return send_request(self.a, self.b, self.django, self.python)

    def complete(self):
        exchange = self.request_exchange()
        transition(exchange, self.b, 'accept')
        exchange.refresh_from_db()
        transition(exchange, self.a, 'complete')
        exchange.refresh_from_db()
        return exchange

    def test_registration_password_validation_profile_and_email_login(self):
        invalid = RegistrationForm({'first_name':'New','last_name':'User','username':'new','email':'bad', 'password1':'123','password2':'456'})
        self.assertFalse(invalid.is_valid())
        response = self.client.post(reverse('register'), {'first_name':'New','last_name':'Member','username':'new_member',
            'email':'new@example.test','password1':'A-long-secret-934!','password2':'A-long-secret-934!'})
        self.assertRedirects(response, reverse('dashboard'))
        user = get_user_model().objects.get(username='new_member')
        self.assertTrue(user.check_password('A-long-secret-934!'))
        self.assertEqual(user.profile.user_id, user.pk)
        self.client.post(reverse('logout'))
        response = self.client.post(reverse('login'), {'username':'NEW@example.test','password':'A-long-secret-934!'})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        duplicate = RegistrationForm({'first_name':'New','last_name':'Member','username':'NEW_MEMBER','email':'other@example.test',
            'password1':'A-long-secret-934!','password2':'A-long-secret-934!'})
        self.assertFalse(duplicate.is_valid())

    def test_profile_edits_only_current_user_and_validates_upload(self):
        self.client.force_login(self.a)
        response = self.client.post(reverse('edit_profile'), {'first_name':'Edited','last_name':'Member','email':'edited@example.test','location':'Sylhet','bio':'Learner', 'user':str(self.b.pk)})
        self.assertRedirects(response, reverse('profile'))
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertEqual(self.a.first_name, 'Edited')
        self.assertEqual(self.b.first_name, 'Ankon')
        self.assertEqual(self.a.profile.location, 'Sylhet')
        from django.core.files.uploadedfile import SimpleUploadedFile
        form = ProfileForm({'first_name':'F','last_name':'A','email':'farhan@example.test'}, {'image':SimpleUploadedFile('bad.png',b'not an image',content_type='image/png')},instance=self.a.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('image',form.errors)

    def test_skill_crud_duplicate_and_ownership(self):
        self.client.force_login(self.a)
        data={'name':'Excel','category':'business','skill_type':'teach','level':'intermediate','description':'Spreadsheets'}
        self.assertRedirects(self.client.post(reverse('add_skill'),data),reverse('my_skills'))
        added=SkillOffer.objects.get(user=self.a,skill__name='Excel')
        form=SkillForm(dict(data,name='  EXCEL  '),user=self.a)
        self.assertFalse(form.is_valid())
        data['description']='Updated description'
        self.assertRedirects(self.client.post(reverse('edit_skill',args=[added.pk]),data),reverse('my_skills'))
        added.refresh_from_db(); self.assertEqual(added.description,'Updated description')
        self.assertEqual(self.client.post(reverse('remove_skill',args=[self.offer_b.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('edit_skill',args=[self.offer_b.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('remove_skill',args=[added.pk])).status_code,405)
        self.assertRedirects(self.client.post(reverse('remove_skill',args=[added.pk])),reverse('my_skills'))
        self.assertTrue(Skill.objects.filter(name='Excel').exists())

    def test_search_filters_and_real_home_counts(self):
        response=self.client.get(reverse('search_skills'), {'q':'Django','category':'programming','level':'advanced','skill_type':'teach','location':'Dhaka'})
        self.assertEqual([p.pk for p in response.context['people']],[self.a.pk])
        response=self.client.get(reverse('search_skills'), {'q':'Pranay'})
        self.assertEqual([p.pk for p in response.context['people']],[self.c.pk])
        response=self.client.get(reverse('skills'), {'q':'unfindable'})
        self.assertContains(response,'No skills found.')
        response=self.client.get(reverse('home'))
        self.assertEqual(response.context['community']['members'],3)
        self.assertEqual(response.context['community']['exchanges'],0)
        self.assertNotContains(response,'2,100+')

    def test_matching_is_reciprocal_sorted_and_unique(self):
        matches=find_matches(self.a)
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0].person.pk,self.b.pk)
        self.assertEqual(matches[0].percentage,100)
        SkillOffer.objects.create(user=self.c,skill=self.python,experience_level='intermediate',description='Python')
        matches=find_matches(self.a)
        self.assertEqual([m.percentage for m in matches],[100,45])
        self.assertNotIn(self.a.pk,[m.person.pk for m in matches])

    def test_requests_reject_self_invalid_skills_and_reverse_duplicates(self):
        with self.assertRaises(ValidationError): send_request(self.a,self.a,self.django,self.python)
        with self.assertRaises(ValidationError): send_request(self.a,self.c,self.django,self.python)
        self.request_exchange()
        with self.assertRaises(ValidationError): send_request(self.b,self.a,self.python,self.django)
        # Database constraint also guards concurrent submissions after pre-checks.
        with self.assertRaises(IntegrityError):
            ExchangeRequest.objects.create(sender=self.b,receiver=self.a,sender_skill=self.python,receiver_skill=self.django)

    def test_workflow_roles_and_completion(self):
        exchange=self.request_exchange()
        self.client.force_login(self.c)
        self.assertEqual(self.client.get(reverse('exchange_detail',args=[exchange.pk])).status_code,404)
        self.assertEqual(self.client.post(reverse('complete_exchange',args=[exchange.pk])).status_code,404)
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(reverse('accept_exchange',args=[exchange.pk])).status_code,403)
        self.client.post(reverse('complete_exchange',args=[exchange.pk]))
        exchange.refresh_from_db(); self.assertEqual(exchange.status,'pending')
        self.client.force_login(self.b)
        self.client.post(reverse('accept_exchange',args=[exchange.pk]))
        exchange.refresh_from_db(); self.assertEqual(exchange.status,'accepted')
        self.client.post(reverse('complete_exchange',args=[exchange.pk]))
        exchange.refresh_from_db(); self.assertEqual(exchange.status,'completed')
        self.assertIsNotNone(exchange.completed_at)
        self.assertIsNone(exchange.active_key)
        self.client.post(reverse('cancel_exchange',args=[exchange.pk]))
        exchange.refresh_from_db(); self.assertEqual(exchange.status,'completed')

    def test_cancel_and_reject_release_active_pair(self):
        exchange=self.request_exchange()
        transition(exchange,self.a,'cancel')
        exchange=self.request_exchange()
        transition(exchange,self.b,'reject')
        self.assertEqual(self.request_exchange().status,'pending')

    def test_request_form_rejects_tampered_choices(self):
        self.client.force_login(self.a)
        response=self.client.post(reverse('send_exchange_request',args=[self.b.pk]))
        self.assertTemplateUsed(response,'exchanges/send_request.html')
        response=self.client.post(reverse('send_exchange_request',args=[self.b.pk]),{'sender_skill':str(self.python.pk),'receiver_skill':str(self.django.pk)})
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(ExchangeRequest.objects.count(),0)
        response=self.client.post(reverse('send_exchange_request',args=[self.b.pk]),{'sender_skill':str(self.django.pk),'receiver_skill':str(self.python.pk),'message':'Let us learn'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(ExchangeRequest.objects.count(),1)

    def test_reviews_permissions_range_uniqueness_and_averages(self):
        exchange=self.request_exchange()
        with self.assertRaises(ValidationError): write_review(exchange,self.a,5,'Too early')
        transition(exchange,self.b,'accept'); exchange.refresh_from_db()
        transition(exchange,self.a,'complete'); exchange.refresh_from_db()
        for rating in (0,6):
            with self.assertRaises(ValidationError): write_review(exchange,self.a,rating,'Bad rating')
        write_review(exchange,self.a,4,'Helpful <script>alert(1)</script>')
        with self.assertRaises(ValidationError): write_review(exchange,self.a,5,'Duplicate')
        self.assertEqual(self.b.profile.rating,4)
        self.assertEqual(self.b.profile.review_count,1)
        self.assertEqual(self.a.profile.completed_exchanges,1)
        self.client.force_login(self.a)
        self.assertContains(self.client.get(reverse('review',args=[exchange.pk])),'&lt;script&gt;')
        self.client.force_login(self.c)
        self.assertEqual(self.client.post(reverse('review',args=[exchange.pk]),{'rating':5,'comment':'No'}).status_code,404)
        own=Review(exchange=exchange,reviewer=self.b,reviewed_user=self.b,rating=5,comment='Self')
        with self.assertRaises(ValidationError): own.clean()

    def test_all_existing_pages_render_with_real_objects(self):
        exchange=self.complete()
        self.client.force_login(self.a)
        routes={'home':(), 'profile':(), 'edit_profile':(), 'user_profile':(self.b.pk,), 'skills':(), 'my_skills':(),
                'add_skill':(), 'edit_skill':(self.offer_a.pk,), 'skill_detail':(self.django.pk,), 'search_skills':(),
                'dashboard':(), 'matches':(), 'exchange_requests':(), 'exchange_detail':(exchange.pk,),
                'exchange_history':(), 'review':(exchange.pk,), 'send_exchange_request':(self.b.pk,)}
        for name,args in routes.items():
            with self.subTest(route=name):
                response=self.client.get(reverse(name,args=args))
                self.assertEqual(response.status_code,200)
                self.assertContains(response,'/static/css/style.css')
                self.assertNotContains(response,'Design preview')

    @override_settings(DEBUG=True)
    def test_seed_is_idempotent(self):
        call_command('seed_demo',stdout=StringIO())
        counts=(get_user_model().objects.count(),SkillOffer.objects.count(),ExchangeRequest.objects.count())
        password=get_user_model().objects.get(username='farhan_demo').password
        call_command('seed_demo',stdout=StringIO())
        self.assertEqual(counts,(get_user_model().objects.count(),SkillOffer.objects.count(),ExchangeRequest.objects.count()))
        self.assertEqual(password,get_user_model().objects.get(username='farhan_demo').password)

    def test_review_post_form_saves_and_second_participant_can_review(self):
        exchange=self.complete()
        self.client.force_login(self.a)
        url=reverse('review',args=[exchange.pk])
        response=self.client.post(url,{'rating':'6','comment':'Invalid'})
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Review.objects.count(),0)
        self.assertRedirects(self.client.post(url,{'rating':'5','comment':'Helpful'}),url)
        self.assertRedirects(self.client.post(url,{'rating':'3','comment':'Duplicate'}),url)
        self.assertEqual(Review.objects.count(),1)
        self.client.force_login(self.b)
        self.assertRedirects(self.client.post(url,{'rating':'4','comment':'Great partner'}),url)
        self.assertEqual(Review.objects.count(),2)

    def test_empty_home_has_real_zeroes_and_empty_lists(self):
        SkillOffer.objects.all().delete()
        response=self.client.get(reverse('home'))
        self.assertEqual(response.context['popular_skills'],[])
        self.assertEqual(response.context['community']['exchanges'],0)
        self.assertContains(response,'New skills are on the way.')
        self.assertNotContains(response,'2,100+')

    def test_readonly_admin_workflow_and_builtin_admin_render(self):
        self.a.is_staff=True
        self.a.is_superuser=True
        self.a.save()
        self.client.force_login(self.a)
        for name in ('admin:index','admin:auth_user_changelist','admin:skills_skill_changelist','admin:exchanges_exchangerequest_changelist'):
            self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertEqual(self.client.get(reverse('admin:exchanges_exchangerequest_add')).status_code,403)
