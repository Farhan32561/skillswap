# Farhan's part
from django.contrib.auth import BACKEND_SESSION_KEY


class PreserveLoginBackendMiddleware:
    """Keep existing signed login sessions valid after the Python package move."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get(BACKEND_SESSION_KEY) == 'accounts.backends.UsernameOrEmailBackend':
            request.session[BACKEND_SESSION_KEY] = 'farhan.accounts.backends.UsernameOrEmailBackend'
        return self.get_response(request)
