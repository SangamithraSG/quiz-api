"""
views.py (analytics app)

Provides performance data and statistics.

Endpoints:
  GET /api/analytics/me/              → My overall performance stats
  GET /api/analytics/quiz/<id>/       → Stats for a specific quiz (admin or creator)
  GET /api/analytics/leaderboard/     → Top scorers across all quizzes
  GET /api/analytics/history/         → My quiz history with scores
"""

from django.db.models import Avg, Count, Max, Min, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser, IsOwnerOrAdmin
from apps.quiz.models import Quiz, QuizAttempt, UserAnswer


class MyStatsView(APIView):
    """
    GET /api/analytics/me/

    Returns the logged-in user's overall quiz performance statistics.

    Example response:
    {
      "total_attempts": 12,
      "completed_attempts": 10,
      "average_score_percentage": 72.5,
      "best_score_percentage": 100.0,
      "total_questions_answered": 85,
      "total_correct": 61,
      "accuracy_percentage": 71.8,
      "quizzes_by_difficulty": { "easy": 3, "medium": 5, "hard": 2 }
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get all completed attempts for this user
        # select_related("quiz") avoids extra DB queries when accessing attempt.quiz
        completed = QuizAttempt.objects.filter(
            user=user,
            status=QuizAttempt.COMPLETED,
        ).select_related("quiz")

        total_attempts = QuizAttempt.objects.filter(user=user).count()
        completed_count = completed.count()

        if completed_count == 0:
            return Response({
                "total_attempts": total_attempts,
                "completed_attempts": 0,
                "average_score_percentage": 0,
                "best_score_percentage": 0,
                "total_questions_answered": 0,
                "total_correct": 0,
                "accuracy_percentage": 0,
                "quizzes_by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
            })

        # Django aggregate functions run as a single SQL query
        aggregates = completed.aggregate(
            avg_score=Avg("score_percentage"),
            best_score=Max("score_percentage"),
        )

        # Count all answers across all completed attempts
        all_answers = UserAnswer.objects.filter(attempt__in=completed)
        total_answered = all_answers.count()
        total_correct = all_answers.filter(is_correct=True).count()
        accuracy = round((total_correct / total_answered) * 100, 2) if total_answered > 0 else 0

        # Break down attempts by difficulty
        by_difficulty = {
            "easy": completed.filter(quiz__difficulty=Quiz.EASY).count(),
            "medium": completed.filter(quiz__difficulty=Quiz.MEDIUM).count(),
            "hard": completed.filter(quiz__difficulty=Quiz.HARD).count(),
        }

        return Response({
            "total_attempts": total_attempts,
            "completed_attempts": completed_count,
            "average_score_percentage": round(aggregates["avg_score"] or 0, 2),
            "best_score_percentage": aggregates["best_score"] or 0,
            "total_questions_answered": total_answered,
            "total_correct": total_correct,
            "accuracy_percentage": accuracy,
            "quizzes_by_difficulty": by_difficulty,
        })


class QuizStatsView(APIView):
    """
    GET /api/analytics/quiz/<id>/

    Returns statistics for a specific quiz.
    Only accessible by the quiz creator or admin.

    Example response:
    {
      "quiz_title": "Python Basics",
      "total_attempts": 45,
      "completed_attempts": 40,
      "average_score_percentage": 68.0,
      "highest_score": 100.0,
      "lowest_score": 20.0,
      "question_difficulty": [
        { "question_id": 1, "correct_rate": 0.85, "question_text": "..." },
        ...
      ]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            quiz = Quiz.objects.get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=404)

        # Only creator or admin can see quiz-level stats
        if quiz.created_by != request.user and not request.user.is_admin_user:
            return Response({"error": "Permission denied."}, status=403)

        completed = QuizAttempt.objects.filter(quiz=quiz, status=QuizAttempt.COMPLETED)
        total_attempts = QuizAttempt.objects.filter(quiz=quiz).count()
        completed_count = completed.count()

        if completed_count == 0:
            return Response({
                "quiz_title": quiz.title,
                "total_attempts": total_attempts,
                "completed_attempts": 0,
                "average_score_percentage": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "question_difficulty": [],
            })

        aggregates = completed.aggregate(
            avg=Avg("score_percentage"),
            high=Max("score_percentage"),
            low=Min("score_percentage"),
        )

        # Per-question analysis: what % of users got each question right?
        question_stats = []
        for question in quiz.questions.all():
            answers = UserAnswer.objects.filter(question=question, attempt__in=completed)
            total = answers.count()
            correct = answers.filter(is_correct=True).count()
            correct_rate = round(correct / total, 2) if total > 0 else 0

            question_stats.append({
                "question_id": question.id,
                "question_text": question.question_text[:80],
                "correct_rate": correct_rate,        # e.g. 0.75 = 75% got it right
                "times_answered": total,
            })

        return Response({
            "quiz_title": quiz.title,
            "topic": quiz.topic,
            "difficulty": quiz.difficulty,
            "total_attempts": total_attempts,
            "completed_attempts": completed_count,
            "average_score_percentage": round(aggregates["avg"] or 0, 2),
            "highest_score": aggregates["high"] or 0,
            "lowest_score": aggregates["low"] or 0,
            "question_difficulty": question_stats,
        })


class LeaderboardView(APIView):
    """
    GET /api/analytics/leaderboard/

    Returns the top 10 users ranked by average score percentage.
    Anyone logged in can see this.

    Optional query param:
      ?quiz_id=5  → leaderboard for a specific quiz only
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quiz_id = request.query_params.get("quiz_id")

        # Filter by specific quiz if requested
        filters = {"status": QuizAttempt.COMPLETED}
        if quiz_id:
            filters["quiz_id"] = quiz_id

        # Group by user, calculate their average score
        # values("user__username") = group by this field
        # annotate() = add calculated fields
        leaderboard = (
            QuizAttempt.objects.filter(**filters)
            .values("user__id", "user__username")
            .annotate(
                avg_score=Avg("score_percentage"),
                total_attempts=Count("id"),
                best_score=Max("score_percentage"),
            )
            .order_by("-avg_score")  # Highest average first
            [:10]                    # Top 10 only
        )

        results = []
        for rank, entry in enumerate(leaderboard, start=1):
            results.append({
                "rank": rank,
                "username": entry["user__username"],
                "average_score": round(entry["avg_score"], 2),
                "best_score": entry["best_score"],
                "total_attempts": entry["total_attempts"],
            })

        return Response({"leaderboard": results})


class MyHistoryView(APIView):
    """
    GET /api/analytics/history/

    Returns the logged-in user's quiz attempt history,
    newest first, with scores for each attempt.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        attempts = QuizAttempt.objects.filter(
            user=request.user,
            status=QuizAttempt.COMPLETED,
        ).select_related("quiz").order_by("-completed_at")

        history = []
        for attempt in attempts:
            history.append({
                "attempt_id": attempt.id,
                "quiz_id": attempt.quiz.id,
                "quiz_title": attempt.quiz.title,
                "topic": attempt.quiz.topic,
                "difficulty": attempt.quiz.difficulty,
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "score_percentage": attempt.score_percentage,
                "completed_at": attempt.completed_at,
            })

        return Response({"history": history, "total": len(history)})


class AdminDashboardView(APIView):
    """
    GET /api/analytics/admin/dashboard/

    Admin only: overall platform statistics.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import User

        return Response({
            "total_users": User.objects.count(),
            "total_quizzes": Quiz.objects.count(),
            "ready_quizzes": Quiz.objects.filter(status=Quiz.READY).count(),
            "total_attempts": QuizAttempt.objects.count(),
            "completed_attempts": QuizAttempt.objects.filter(status=QuizAttempt.COMPLETED).count(),
            "platform_avg_score": round(
                QuizAttempt.objects.filter(
                    status=QuizAttempt.COMPLETED
                ).aggregate(avg=Avg("score_percentage"))["avg"] or 0,
                2
            ),
        })
