"""API views for user authentication."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegistrationSerializer
from .utils import set_access_cookie, set_refresh_cookie


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
