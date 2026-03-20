"""
urls.py — The central URL router for the entire project.

When a request comes in, Django checks this file first to decide
which app should handle it.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.views import LoginView

urlpatterns = [
    # ── Django Admin Panel ──────────────────────────────────────────
    # Visit /admin/ to manage data through Django's built-in interface
    path("admin/", admin.site.urls),

    # ── Authentication Endpoints ────────────────────────────────────
    # /api/auth/login/   → Get access + refresh tokens
    # /api/auth/refresh/ → Use refresh token to get a new access token
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ── App Endpoints ───────────────────────────────────────────────
    # All user-related routes (register, profile, etc.)
    path("api/users/", include("apps.users.urls")),

    # All quiz-related routes (create quiz, attempt quiz, etc.)
    path("api/quiz/", include("apps.quiz.urls")),

    # All analytics routes (results, history, leaderboard)
    path("api/analytics/", include("apps.analytics.urls")),
]
