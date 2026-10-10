"""Authentication backend that reads the JWT from an HttpOnly cookie."""

from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate requests with the access token stored in a cookie."""

    def authenticate(self, request):
        """Return (user, token) from the access_token cookie, or None."""
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
