"""
models.py (users app)

Defines the database tables related to users.

We extend Django's built-in AbstractUser so we get username, password,
email, is_active, etc. for free — and then add our own fields on top.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Our custom User model.

    Inherits from AbstractUser which already has:
      - username, password, email
      - first_name, last_name
      - is_staff, is_active, is_superuser
      - date_joined, last_login

    We add:
      - role: is this user a regular user or an admin?
      - bio: optional short description
    """

    # ── Roles ──────────────────────────────────────────────────────
    # We use a simple string choice field for roles.
    # "user"  → normal quiz taker
    # "admin" → can manage quizzes, see all analytics
    ROLE_USER = "user"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ADMIN, "Admin"),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_USER,   # Everyone starts as a regular user
    )

    bio = models.TextField(blank=True, default="")  # Optional profile bio

    # ── Convenience properties ──────────────────────────────────────
    @property
    def is_admin_user(self):
        """Returns True if this user has the admin role."""
        return self.role == self.ROLE_ADMIN

    def __str__(self):
        # How this object appears in the Django admin and print()
        return f"{self.username} ({self.role})"

    class Meta:
        db_table = "users"        # Name of the table in PostgreSQL
        ordering = ["-date_joined"]  # Newest users first
