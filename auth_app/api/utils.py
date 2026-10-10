"""Helper functions for the JWT auth cookies and tokens."""

from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def set_cookie(response, key, value, lifetime):
    """Set an HttpOnly cookie that expires after the given lifetime."""
    response.set_cookie(
        key=key,
        value=value,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=False,
        samesite='Lax',
    )


def set_access_cookie(response, access_token):
    """Store the access token in the access_token cookie."""
    lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    set_cookie(response, 'access_token', str(access_token), lifetime)


def set_refresh_cookie(response, refresh_token):
    """Store the refresh token in the refresh_token cookie."""
    lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
    set_cookie(response, 'refresh_token', str(refresh_token), lifetime)


def delete_auth_cookies(response):
    """Remove both JWT cookies from the client."""
    response.delete_cookie('access_token', samesite='Lax')
    response.delete_cookie('refresh_token', samesite='Lax')


def get_valid_refresh_token(raw_token):
    """Return a RefreshToken if the raw token is valid, otherwise None."""
    if raw_token is None:
        return None
    try:
        return RefreshToken(raw_token)
    except TokenError:
        return None


def blacklist_refresh_token(raw_token):
    """Blacklist the refresh token; ignore missing or invalid tokens."""
    if raw_token is None:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        pass
