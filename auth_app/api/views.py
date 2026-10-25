"""API views for user authentication."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from quiz_app.demo.service import is_demo_user, reset_demo_account

from .serializers import RegistrationSerializer
from .utils import (
    blacklist_refresh_token,
    delete_auth_cookies,
    get_valid_refresh_token,
    set_access_cookie,
    set_refresh_cookie,
)


class RegistrationView(APIView):
    """Register a new user account."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the data and create the user."""
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Log a user in and set the JWT cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Check the credentials and return the user with auth cookies."""
        user = authenticate(
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if user is None:
            return Response(
                {'detail': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if is_demo_user(user):
            reset_demo_account(user)
        return self.build_login_response(user)

    def build_login_response(self, user):
        """Create tokens for the user and attach them as cookies."""
        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successfully!',
            'user': {'id': user.id, 'username': user.username,
                     'email': user.email},
        })
        set_access_cookie(response, refresh.access_token)
        set_refresh_cookie(response, refresh)
        return response


class LogoutView(APIView):
    """Log the user out by blacklisting the token and removing cookies."""

    def post(self, request):
        """Invalidate the refresh token and delete both auth cookies."""
        blacklist_refresh_token(request.COOKIES.get('refresh_token'))
        response = Response({
            'detail': 'Log-Out successfully! All Tokens will be deleted. '
                      'Refresh token is now invalid.'
        })
        delete_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Issue a new access token using the refresh_token cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Set a new access_token cookie if the refresh token is valid."""
        refresh = get_valid_refresh_token(request.COOKIES.get('refresh_token'))
        if refresh is None:
            return Response(
                {'detail': 'Refresh token invalid or missing.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token refreshed'})
        set_access_cookie(response, refresh.access_token)
        return response
