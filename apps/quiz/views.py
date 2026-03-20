"""
views.py (quiz app)

All API endpoints for quizzes and attempts.

Permissions:
  - CREATE quiz  → Admin only
  - VIEW quizzes → Anyone logged in
  - DELETE quiz  → Admin or creator
  - ATTEMPT quiz → Regular users only (not admins)
  - SUBMIT/VIEW attempt → Owner only
"""

import logging
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser, IsOwnerOrAdmin
from .ai_service import generate_questions
from .models import Quiz, Question, QuizAttempt, UserAnswer
from .serializers import (
    AttemptDetailSerializer,
    AttemptListSerializer,
    AttemptSubmitSerializer,
    QuizCreateSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
)

logger = logging.getLogger(__name__)


# ── Quiz CRUD ─────────────────────────────────────────────────────────────────

class QuizListCreateView(APIView):
    """
    GET  /api/quiz/  → List all 'ready' quizzes (any logged-in user)
    POST /api/quiz/  → Create a new quiz — ADMIN ONLY
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns all quizzes with status='ready'.
        Supports filtering by topic and difficulty via query params.
        Example: GET /api/quiz/?topic=python&difficulty=easy
        """
        quizzes = Quiz.objects.filter(status=Quiz.READY).select_related("created_by")

        topic = request.query_params.get("topic")
        difficulty = request.query_params.get("difficulty")

        if topic:
            quizzes = quizzes.filter(topic__icontains=topic)
        if difficulty and difficulty in [Quiz.EASY, Quiz.MEDIUM, Quiz.HARD]:
            quizzes = quizzes.filter(difficulty=difficulty)

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(quizzes, request)
        serializer = QuizListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """
        Creates a quiz — ADMIN ONLY.
        Regular users will get a 403 Forbidden error.
        """
        # Check if user is admin
        if not request.user.is_admin_user:
            return Response(
                {"error": "Only admins can create quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = QuizCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        quiz = serializer.save(created_by=request.user, status=Quiz.DRAFT)

        try:
            questions_data = generate_questions(
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                count=quiz.question_count,
            )
        except Exception as e:
            quiz.status = Quiz.FAILED
            quiz.save()
            logger.error(f"AI generation failed for quiz {quiz.id}: {e}")
            return Response(
                {"error": f"Failed to generate questions: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        question_objects = []
        for i, q_data in enumerate(questions_data):
            question_objects.append(
                Question(
                    quiz=quiz,
                    question_text=q_data["question_text"],
                    option_a=q_data["option_a"],
                    option_b=q_data["option_b"],
                    option_c=q_data["option_c"],
                    option_d=q_data["option_d"],
                    correct_option=q_data["correct_option"],
                    explanation=q_data.get("explanation", ""),
                    order=i + 1,
                )
            )

        Question.objects.bulk_create(question_objects)

        quiz.status = Quiz.READY
        quiz.question_count = len(question_objects)
        quiz.save()

        return Response(
            QuizDetailSerializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )


class QuizDetailView(APIView):
    """
    GET    /api/quiz/<id>/  → Get quiz details (any logged-in user)
    DELETE /api/quiz/<id>/  → Delete quiz (admin only)
    """
    permission_classes = [IsAuthenticated]

    def _get_quiz(self, pk):
        try:
            return Quiz.objects.prefetch_related("questions").get(pk=pk)
        except Quiz.DoesNotExist:
            return None

    def get(self, request, pk):
        quiz = self._get_quiz(pk)
        if not quiz:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

        if quiz.status != Quiz.READY and not request.user.is_admin_user:
            return Response(
                {"error": "This quiz is not available yet."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = QuizDetailSerializer(quiz)
        return Response(serializer.data)

    def delete(self, request, pk):
        # Only admins can delete quizzes
        if not request.user.is_admin_user:
            return Response(
                {"error": "Only admins can delete quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        quiz = self._get_quiz(pk)
        if not quiz:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

        quiz.delete()
        return Response({"message": "Quiz deleted."}, status=status.HTTP_200_OK)


class MyQuizzesView(generics.ListAPIView):
    """
    GET /api/quiz/my-quizzes/
    Admin only — quizzes created by this admin.
    """
    serializer_class = QuizListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user).select_related("created_by")


# ── Quiz Attempts ─────────────────────────────────────────────────────────────

class StartAttemptView(APIView):
    """
    POST /api/quiz/<id>/attempt/

    Start a new quiz attempt — REGULAR USERS ONLY.
    Admins cannot attempt quizzes (they create them).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Admins cannot attempt quizzes
        if request.user.is_admin_user:
            return Response(
                {"error": "Admins cannot attempt quizzes. Only regular users can."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            quiz = Quiz.objects.get(pk=pk, status=Quiz.READY)
        except Quiz.DoesNotExist:
            return Response(
                {"error": "Quiz not found or not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user already has an in-progress attempt
        existing = QuizAttempt.objects.filter(
            user=request.user,
            quiz=quiz,
            status=QuizAttempt.IN_PROGRESS,
        ).first()

        if existing:
            return Response(
                {
                    "message": "You already have an in-progress attempt for this quiz.",
                    "attempt_id": existing.id,
                },
                status=status.HTTP_200_OK,
            )

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            status=QuizAttempt.IN_PROGRESS,
            total_questions=quiz.question_count,
        )

        return Response(
            {
                "message": "Attempt started.",
                "attempt_id": attempt.id,
                "total_questions": quiz.question_count,
                "quiz_title": quiz.title,
            },
            status=status.HTTP_201_CREATED,
        )


class SubmitAttemptView(APIView):
    """
    POST /api/quiz/attempts/<id>/submit/
    Submit all answers — attempt owner only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            attempt = QuizAttempt.objects.select_related("quiz", "user").get(pk=pk)
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)

        if attempt.user != request.user:
            return Response({"error": "Not your attempt."}, status=status.HTTP_403_FORBIDDEN)

        if attempt.status == QuizAttempt.COMPLETED:
            return Response(
                {"error": "This attempt has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AttemptSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        answers_data = serializer.validated_data["answers"]
        questions = {q.id: q for q in attempt.quiz.questions.all()}

        user_answers = []
        for answer in answers_data:
            q_id = answer["question_id"]
            option = answer["selected_option"]

            if q_id not in questions:
                return Response(
                    {"error": f"Question ID {q_id} does not belong to this quiz."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not UserAnswer.objects.filter(attempt=attempt, question_id=q_id).exists():
                user_answers.append(
                    UserAnswer(
                        attempt=attempt,
                        question_id=q_id,
                        selected_option=option,
                    )
                )

        for ua in user_answers:
            ua.save()

        total = attempt.total_questions
        correct = UserAnswer.objects.filter(attempt=attempt, is_correct=True).count()
        percentage = round((correct / total) * 100, 2) if total > 0 else 0

        attempt.score = correct
        attempt.score_percentage = percentage
        attempt.status = QuizAttempt.COMPLETED
        attempt.completed_at = timezone.now()
        attempt.save()

        return Response(
            AttemptDetailSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )


class AttemptDetailView(generics.RetrieveAPIView):
    """
    GET /api/quiz/attempts/<id>/
    View attempt results — owner or admin only.
    """
    serializer_class = AttemptDetailSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return QuizAttempt.objects.select_related("quiz", "user").prefetch_related(
            "answers__question"
        )


class MyAttemptsView(generics.ListAPIView):
    """
    GET /api/quiz/my-attempts/
    All attempts by the logged-in user — regular users only.
    """
    serializer_class = AttemptListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QuizAttempt.objects.filter(
            user=self.request.user
        ).select_related("quiz").order_by("-started_at")


class AllAttemptsView(generics.ListAPIView):
    """
    GET /api/quiz/all-attempts/
    All attempts by all users — admin only.
    """
    serializer_class = AttemptListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return QuizAttempt.objects.select_related("quiz", "user").order_by("-started_at")