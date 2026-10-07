# Ankon's part
from django import forms
from django_mongodb_backend.transaction import atomic
from .models import CATEGORIES, LEVELS, SkillCategory, Skill, SkillOffer, SkillWanted, normalize_name


class SkillForm(forms.Form):
    name = forms.CharField(max_length=100)
    skill_type = forms.ChoiceField(choices=[('teach', 'I Can Teach'), ('learn', 'I Want to Learn')])
    category = forms.ChoiceField(choices=CATEGORIES)
    level = forms.ChoiceField(choices=LEVELS)
    description = forms.CharField(max_length=2000)

    def __init__(self, *args, user, instance=None, **kwargs):
        self.user, self.instance = user, instance
        if instance:
            kwargs['initial'] = {'name': instance.skill.name, 'skill_type': 'teach' if isinstance(instance, SkillOffer) else 'learn',
                                 'category': instance.skill.category.slug, 'level': instance.experience_level, 'description': instance.description}
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if not all(key in data for key in ('name', 'skill_type', 'category')):
            return data
        if self.instance and data['skill_type'] != self.initial['skill_type']:
            self.add_error('skill_type', 'Keep this skill type when editing. Add a separate skill to change type.')
        skill = Skill.objects.filter(normalized_name=normalize_name(data['name'])).first()
        if skill:
            if skill.category.slug != data['category']:
                self.add_error('category', f'This skill already belongs to {skill.category.name}.')
            model = SkillOffer if data['skill_type'] == 'teach' else SkillWanted
            existing = model.objects.filter(user=self.user, skill=skill)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error('name', 'You already added this skill with this type.')
        return data

    def save(self):
        data = self.cleaned_data
        model = SkillOffer if data['skill_type'] == 'teach' else SkillWanted
        with atomic():
            category, _ = SkillCategory.objects.get_or_create(slug=data['category'], defaults={'name': dict(CATEGORIES)[data['category']]})
            skill, _ = Skill.objects.get_or_create(normalized_name=normalize_name(data['name']), defaults={'name': ' '.join(data['name'].split()), 'category': category, 'description': data['description']})
            if skill.category_id != category.pk:
                raise forms.ValidationError('The skill category changed. Please reload and try again.')
            obj = self.instance or model(user=self.user)
            obj.skill, obj.experience_level, obj.description = skill, data['level'], data['description']
            obj.full_clean()
            obj.save()
            return obj
