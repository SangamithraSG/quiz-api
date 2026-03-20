"""
urls.py (analytics app)

All analytics URL patterns.
Prefixed with /api/analytics/ from main urls.py.
"""

from django.urls import path
from .views import (
    MyStatsView,
    QuizStatsView,
    LeaderboardView,
    MyHistoryView,
    AdminDashboardView,
)

urlpatterns = [
    # GET /api/analytics/me/               → My overall performance stats
    path("me/", MyStatsView.as_view(), name="my-stats"),

    # GET /api/analytics/quiz/<id>/        → Stats for a specific quiz
    path("quiz/<int:pk>/", QuizStatsView.as_view(), name="quiz-stats"),

    # GET /api/analytics/leaderboard/      → Top 10 users by score
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),

    # GET /api/analytics/history/          → My quiz attempt history
    path("history/", MyHistoryView.as_view(), name="history"),

    # GET /api/analytics/admin/dashboard/  → Platform-wide stats (admin only)
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
]
