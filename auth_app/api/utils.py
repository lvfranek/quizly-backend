"""Helper functions for setting the JWT auth cookies."""

from django.conf import settings


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
