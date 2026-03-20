"""
tests.py (analytics app)

Tests for analytics endpoints.

Run with: python manage.py test apps.analytics
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.quiz.models import Quiz, Question, QuizAttempt, UserAnswer


def make_completed_attempt(user, quiz, questions, score=3):
    """Helper that creates a completed attempt with given score."""
    attempt = QuizAttempt.objects.create(
        user=user, quiz=quiz,
        status=QuizAttempt.COMPLETED, total_questions=len(questions),
        score=score,
        score_percentage=(score / len(questions)) * 100,
    )
    from django.utils import timezone
    attempt.completed_at = timezone.now()
    attempt.save()

    for i, q in enumerate(questions):
        selected = "A" if i < score else "B"  # First 'score' answers are correct
        UserAnswer.objects.create(
            attempt=attempt, question=q, selected_option=selected,
        )
    return attempt


class MyStatsTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="tester", password="Test123!")
        self.client.force_authenticate(user=self.user)

        # Create a quiz with 3 questions
        self.quiz = Quiz.objects.create(
            title="Test Quiz", topic="Math", difficulty=Quiz.EASY,
            question_count=3, status=Quiz.READY, created_by=self.user,
        )
        self.questions = [
            Question.objects.create(
                quiz=self.quiz, question_text=f"Q{i}?",
                option_a="A", option_b="B", option_c="C", option_d="D",
                correct_option="A", order=i,
            )
            for i in range(1, 4)
        ]

    def test_stats_with_no_attempts(self):
        """New user with no attempts gets zero stats."""
        response = self.client.get(reverse("my-stats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["completed_attempts"], 0)
        self.assertEqual(response.data["average_score_percentage"], 0)

    def test_stats_after_completed_attempt(self):
        """Stats update correctly after a completed attempt."""
        make_completed_attempt(self.user, self.quiz, self.questions, score=3)

        response = self.client.get(reverse("my-stats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["completed_attempts"], 1)
        self.assertEqual(response.data["best_score_percentage"], 100.0)
        self.assertEqual(response.data["total_correct"], 3)


class LeaderboardTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", password="Test123!")
        self.client.force_authenticate(user=self.user)

    def test_leaderboard_accessible(self):
        """Leaderboard is accessible to authenticated users."""
        response = self.client.get(reverse("leaderboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("leaderboard", response.data)

    def test_leaderboard_requires_auth(self):
        """Unauthenticated users cannot access the leaderboard."""
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("leaderboard"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminDashboardTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.regular = User.objects.create_user(username="regular", password="Test123!")
        self.admin = User.objects.create_user(
            username="admin_u", password="Test123!", role=User.ROLE_ADMIN
        )

    def test_admin_dashboard_blocks_regular_users(self):
        self.client.force_authenticate(user=self.regular)
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_accessible_by_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_users", response.data)
        self.assertIn("total_quizzes", response.data)
