"""
admin.py (users app)

Registers our models with Django's admin panel.
Visit /admin/ to manage users through a nice UI.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Customizes how User appears in /admin/.
    We extend Django's built-in UserAdmin to add our custom fields.
    """

    # Columns shown in the user list
    list_display = ["username", "email", "role", "is_active", "date_joined"]

    # Filters on the right sidebar
    list_filter = ["role", "is_active", "is_staff"]

    # Which fields to search by in the search bar
    search_fields = ["username", "email"]

    # Add our custom fields to the edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Quiz App Fields", {"fields": ("role", "bio")}),
    )
