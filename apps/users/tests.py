"""
tests.py (users app)

Basic tests for user registration and authentication.

Run with: python manage.py test apps.users
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import User


class UserRegistrationTest(TestCase):
    """Tests for the POST /api/users/register/ endpoint."""

    def setUp(self):
        # APIClient is a test HTTP client that knows about DRF auth
        self.client = APIClient()
        self.register_url = reverse("register")  # Matches name="register" in urls.py

    def test_register_success(self):
        """A new user can register with valid data."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Should return 201 Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # User should be in the database
        self.assertTrue(User.objects.filter(username="newuser").exists())
        # Password should NOT appear in the response
        self.assertNotIn("password", response.data["user"])
        # Default role should be "user"
        self.assertEqual(response.data["user"]["role"], "user")

    def test_register_passwords_dont_match(self):
        """Registration fails if passwords don't match."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Registration fails if username is already taken."""
        User.objects.create_user(username="existing", password="Test123!")
        data = {
            "username": "existing",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """Registration fails if required fields are missing."""
        response = self.client.post(self.register_url, {"username": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserAuthTest(TestCase):
    """Tests for login and profile access."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com",
        )
        self.login_url = reverse("login")

    def test_login_success(self):
        """A registered user can log in and get JWT tokens."""
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):
        """Login fails with wrong password."""
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "WrongPass!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth(self):
        """Profile endpoint requires authentication."""
        response = self.client.get(reverse("my-profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_authenticated(self):
        """Authenticated user can view their profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("my-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")


class AdminPermissionTest(TestCase):
    """Tests for role-based access control."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(username="regular", password="Test123!")
        self.admin_user = User.objects.create_user(
            username="admin_u", password="Test123!", role=User.ROLE_ADMIN
        )

    def test_regular_user_cannot_list_users(self):
        """Regular users cannot access the admin user list."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        """Admin users can access the user list."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
