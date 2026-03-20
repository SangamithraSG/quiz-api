"""
tests.py (quiz app)

Tests for quiz creation, attempts, and answer submission.

Run with: python manage.py test apps.quiz
"""

from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from .models import Quiz, Question, QuizAttempt, UserAnswer


# ── Shared test data setup ──────────────────────────────────────────────────

def make_user(username="tester", role=User.ROLE_USER):
    return User.objects.create_user(username=username, password="Test123!", role=role)


def make_quiz(user, title="Test Quiz", topic="Python", difficulty=Quiz.EASY, status=Quiz.READY):
    return Quiz.objects.create(
        title=title, topic=topic, difficulty=difficulty,
        question_count=3, status=status, created_by=user,
    )


def add_questions(quiz):
    """Creates 3 sample questions for a quiz."""
    questions = []
    for i in range(1, 4):
        q = Question.objects.create(
            quiz=quiz,
            question_text=f"Question {i}?",
            option_a="Option A",
            option_b="Option B",
            option_c="Option C",
            option_d="Option D",
            correct_option="A",   # All correct answers are "A" for easy testing
            order=i,
        )
        questions.append(q)
    return questions


# ── Quiz Tests ────────────────────────────────────────────────────────────────

# Fake AI response — we don't want to call the real API during tests
MOCK_AI_QUESTIONS = [
    {
        "question_text": f"Test question {i}?",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "A",
        "explanation": "Because A is correct.",
    }
    for i in range(1, 4)
]


class QuizCreateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("quiz-list-create")

    # patch() replaces the real generate_questions function with a fake one
    # during the test, so we don't call the actual Gemini API
    @patch("apps.quiz.views.generate_questions", return_value=MOCK_AI_QUESTIONS)
    def test_create_quiz_success(self, mock_ai):
        """Quiz creation succeeds and saves questions from AI."""
        data = {
            "title": "Python Quiz",
            "topic": "Python basics",
            "difficulty": "easy",
            "question_count": 3,
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "ready")
        self.assertEqual(len(response.data["questions"]), 3)

        # Questions should be in the database
        self.assertEqual(Question.objects.filter(quiz_id=response.data["id"]).count(), 3)

    @patch("apps.quiz.views.generate_questions", side_effect=Exception("API down"))
    def test_create_quiz_ai_failure(self, mock_ai):
        """If AI fails, quiz is marked as 'failed' and error is returned."""
        data = {
            "title": "Bad Quiz",
            "topic": "Anything",
            "difficulty": "medium",
            "question_count": 3,
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        # Quiz should exist but be marked as failed
        quiz = Quiz.objects.get(title="Bad Quiz")
        self.assertEqual(quiz.status, Quiz.FAILED)

    def test_create_quiz_invalid_count(self):
        """question_count outside 3-20 range is rejected."""
        data = {"title": "Bad", "topic": "x", "difficulty": "easy", "question_count": 100}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_quiz_requires_auth(self):
        """Unauthenticated users cannot create quizzes."""
        self.client.force_authenticate(user=None)
        data = {"title": "x", "topic": "x", "difficulty": "easy", "question_count": 5}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_correct_option_not_in_list_response(self):
        """Correct answers should not appear in the quiz list/detail before submission."""
        quiz = make_quiz(self.user)
        questions = add_questions(quiz)

        response = self.client.get(reverse("quiz-detail", kwargs={"pk": quiz.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for q in response.data["questions"]:
            self.assertNotIn("correct_option", q)
            self.assertNotIn("explanation", q)


# ── Attempt Tests ─────────────────────────────────────────────────────────────

class AttemptTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.quiz = make_quiz(self.user)
        self.questions = add_questions(self.quiz)

    def test_start_attempt_success(self):
        """User can start a new attempt for a ready quiz."""
        url = reverse("start-attempt", kwargs={"pk": self.quiz.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attempt_id", response.data)
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_start_attempt_returns_existing(self):
        """Starting an attempt twice returns the existing in-progress attempt."""
        url = reverse("start-attempt", kwargs={"pk": self.quiz.id})
        r1 = self.client.post(url)
        r2 = self.client.post(url)

        self.assertEqual(r1.data["attempt_id"], r2.data["attempt_id"])
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_start_attempt_draft_quiz_fails(self):
        """Users cannot attempt a quiz that isn't ready yet."""
        draft_quiz = make_quiz(self.user, status=Quiz.DRAFT)
        url = reverse("start-attempt", kwargs={"pk": draft_quiz.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_correct_answers_score(self):
        """Submitting all correct answers gives 100% score."""
        # Start attempt
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.IN_PROGRESS, total_questions=3,
        )
        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        # All correct answers are "A" (set in add_questions)
        payload = {
            "answers": [
                {"question_id": q.id, "selected_option": "A"}
                for q in self.questions
            ]
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 3)
        self.assertEqual(response.data["score_percentage"], 100.0)
        self.assertEqual(response.data["status"], "completed")

    def test_submit_wrong_answers_score(self):
        """Submitting all wrong answers gives 0% score."""
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.IN_PROGRESS, total_questions=3,
        )
        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        payload = {
            "answers": [
                {"question_id": q.id, "selected_option": "B"}  # B is wrong (correct is A)
                for q in self.questions
            ]
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 0)
        self.assertEqual(response.data["score_percentage"], 0.0)

    def test_submit_reveals_correct_answers(self):
        """After submission, correct_option and explanation are included."""
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.IN_PROGRESS, total_questions=3,
        )
        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        payload = {
            "answers": [
                {"question_id": q.id, "selected_option": "A"}
                for q in self.questions
            ]
        }
        response = self.client.post(url, payload, format="json")

        # After submission, the correct answers should be in the response
        for answer in response.data["answers"]:
            self.assertIn("correct_option", answer["question"])

    def test_cannot_submit_twice(self):
        """A completed attempt cannot be submitted again."""
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.COMPLETED, total_questions=3,
        )
        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        payload = {"answers": [{"question_id": self.questions[0].id, "selected_option": "A"}]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_submit_wrong_question_id(self):
        """Submitting a question_id that doesn't belong to the quiz fails."""
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.IN_PROGRESS, total_questions=3,
        )
        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        payload = {"answers": [{"question_id": 99999, "selected_option": "A"}]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_cannot_submit_attempt(self):
        """A user cannot submit another user's attempt."""
        attempt = QuizAttempt.objects.create(
            user=self.user, quiz=self.quiz,
            status=QuizAttempt.IN_PROGRESS, total_questions=3,
        )
        other = make_user("other")
        self.client.force_authenticate(user=other)

        url = reverse("submit-attempt", kwargs={"pk": attempt.id})
        payload = {"answers": [{"question_id": self.questions[0].id, "selected_option": "A"}]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
