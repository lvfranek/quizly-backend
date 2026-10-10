"""Serializers for user registration."""

from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates registration data and creates a new user."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Ensure the email address is not used by another account."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email is already in use.')
        return value

    def validate(self, data):
        """Ensure both password fields match."""
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError(
                {'password': 'Passwords do not match.'}
            )
        return data

    def create(self, validated_data):
        """Create the user with a hashed password."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)
