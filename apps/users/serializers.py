"""
serializers.py (users app)

Serializers do two things:
1. Convert a model object → Python dict → JSON (for API responses)
2. Convert incoming JSON → validate it → save to database

Think of them as "forms" for your API.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Used when a new user signs up.
    Accepts: username, email, password, password_confirm, role (optional)
    """

    # Extra field not on the model — used only to confirm password matches
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password_confirm", "role", "bio"]
        extra_kwargs = {
            "password": {"write_only": True},  # Never return password in responses
            "role": {"required": False},        # Role is optional on signup
        }

    def validate(self, data):
        """
        Called automatically before saving.
        Checks that both passwords match and meet Django's password rules.
        """
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Validate against Django's built-in password strength rules
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        """
        After validation, this creates the actual User in the database.
        We remove password_confirm since it's not a model field.
        We use create_user() so Django hashes the password properly.
        """
        validated_data.pop("password_confirm")  # Remove the extra field
        password = validated_data.pop("password")

        # create_user() hashes the password — NEVER store plain text passwords!
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    """
    A read-only view of a user — used when returning user info in responses.
    Does NOT include password or sensitive fields.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "bio", "date_joined"]
        read_only_fields = fields  # All fields are read-only in this serializer


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Used when a user wants to update their own profile (bio, email).
    They cannot change their role through this — only admins can do that.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "bio", "role", "date_joined"]
        read_only_fields = ["id", "username", "role", "date_joined"]  # Can't change these
