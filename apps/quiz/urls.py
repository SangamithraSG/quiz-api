"""
urls.py (quiz app)

All quiz-related URL patterns.
These are prefixed with /api/quiz/ from the main urls.py.
"""

from django.urls import path
from .views import (
    QuizListCreateView,
    QuizDetailView,
    MyQuizzesView,
    StartAttemptView,
    SubmitAttemptView,
    AttemptDetailView,
    MyAttemptsView,
    AllAttemptsView,
)

urlpatterns = [
    # ── Quiz endpoints ──────────────────────────────────────────────
    # GET  /api/quiz/           → List all available quizzes
    # POST /api/quiz/           → Create a new quiz (AI generates questions)
    path("", QuizListCreateView.as_view(), name="quiz-list-create"),

    # GET    /api/quiz/<id>/    → Get quiz + questions (no answers)
    # DELETE /api/quiz/<id>/    → Delete quiz (owner or admin)
    path("<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),

    # GET /api/quiz/my-quizzes/ → Quizzes I created
    path("my-quizzes/", MyQuizzesView.as_view(), name="my-quizzes"),

    # ── Attempt endpoints ───────────────────────────────────────────
    # POST /api/quiz/<id>/attempt/ → Start a new attempt for this quiz
    path("<int:pk>/attempt/", StartAttemptView.as_view(), name="start-attempt"),

    # POST /api/quiz/attempts/<id>/submit/ → Submit answers
    path("attempts/<int:pk>/submit/", SubmitAttemptView.as_view(), name="submit-attempt"),

    # GET /api/quiz/attempts/<id>/ → View attempt results
    path("attempts/<int:pk>/", AttemptDetailView.as_view(), name="attempt-detail"),

    # GET /api/quiz/my-attempts/   → All my past attempts
    path("my-attempts/", MyAttemptsView.as_view(), name="my-attempts"),

    # GET /api/quiz/all-attempts/  → All attempts (admin only)
    path("all-attempts/", AllAttemptsView.as_view(), name="all-attempts"),
]
