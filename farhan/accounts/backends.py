# Farhan's part
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        User = get_user_model()
        # Reject ambiguous identifiers, including legacy duplicate emails.
        users = list(User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username))[:2])
        if len(users) == 1 and users[0].check_password(password) and self.user_can_authenticate(users[0]):
            return users[0]
        if len(users) != 1:
            User().set_password(password)
        return None
