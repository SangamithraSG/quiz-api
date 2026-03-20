"""
urls.py (users app)

Maps URL paths to view classes.
These are all prefixed with /api/users/ from the main urls.py.
"""

from django.urls import path
from .views import (
    RegisterView,
    MyProfileView,
    UserListView,
    UserDetailView,
    PromoteUserView,
)

urlpatterns = [
    # POST /api/users/register/   → Create a new account
    path("register/", RegisterView.as_view(), name="register"),

    # GET/PUT/PATCH /api/users/me/ → View or update your own profile
    path("me/", MyProfileView.as_view(), name="my-profile"),

    # GET /api/users/              → List all users (admin only)
    path("", UserListView.as_view(), name="user-list"),

    # GET/PUT/DELETE /api/users/<id>/ → Manage a specific user (admin only)
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),

    # POST /api/users/<id>/promote/ → Change a user's role (admin only)
    path("<int:pk>/promote/", PromoteUserView.as_view(), name="user-promote"),
]
