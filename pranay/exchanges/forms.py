# Pranay's part
from django import forms
from ankon.skills.models import Skill, SkillOffer, SkillWanted
from .models import Review
from .services import validate_pair


class ExchangeRequestForm(forms.Form):
    sender_skill = forms.ModelChoiceField(queryset=Skill.objects.none(), label='You teach')
    receiver_skill = forms.ModelChoiceField(queryset=Skill.objects.none(), label='You learn')
    message = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 4}))

    def __init__(self, *args, sender, receiver, **kwargs):
        self.sender, self.receiver = sender, receiver
        super().__init__(*args, **kwargs)
        offered = set(SkillOffer.objects.filter(user=sender).values_list('skill_id', flat=True))
        wanted = set(SkillWanted.objects.filter(user=receiver).values_list('skill_id', flat=True))
        theirs = set(SkillOffer.objects.filter(user=receiver).values_list('skill_id', flat=True))
        mine = set(SkillWanted.objects.filter(user=sender).values_list('skill_id', flat=True))
        self.fields['sender_skill'].queryset = Skill.objects.filter(pk__in=list(offered & wanted))
        self.fields['receiver_skill'].queryset = Skill.objects.filter(pk__in=list(theirs & mine))
        for field in self.fields.values():
            field.widget.attrs['id'] = field.label.lower().replace(' ', '_') if field.label else 'message'
        self.fields['sender_skill'].widget.attrs['id'] = 'sender_skill'
        self.fields['receiver_skill'].widget.attrs['id'] = 'receiver_skill'

    def clean(self):
        data = super().clean()
        if data.get('sender_skill') and data.get('receiver_skill'):
            validate_pair(self.sender, self.receiver, data['sender_skill'], data['receiver_skill'])
        return data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
