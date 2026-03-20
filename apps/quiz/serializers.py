"""
serializers.py (quiz app)

Converts Quiz, Question, QuizAttempt, and UserAnswer models
to/from JSON for the API.
"""

from rest_framework import serializers
from .models import Quiz, Question, QuizAttempt, UserAnswer


# ── Question Serializers ──────────────────────────────────────────────────────

class QuestionSerializer(serializers.ModelSerializer):
    """
    Question WITHOUT the correct answer — shown during the attempt.
    We never reveal the answer before the user submits.
    """
    class Meta:
        model = Question
        fields = [
            "id", "question_text",
            "option_a", "option_b", "option_c", "option_d",
            "order",
        ]
        # correct_option and explanation intentionally excluded here


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """
    Question WITH correct answer and explanation.
    Shown only AFTER the user submits the quiz.
    """
    class Meta:
        model = Question
        fields = [
            "id", "question_text",
            "option_a", "option_b", "option_c", "option_d",
            "correct_option", "explanation", "order",
        ]


# ── Quiz Serializers ──────────────────────────────────────────────────────────

class QuizCreateSerializer(serializers.ModelSerializer):
    """
    Input: what the user provides when creating a quiz.
    The API uses this to validate and save the quiz.
    """
    class Meta:
        model = Quiz
        fields = ["id", "title", "topic", "difficulty", "question_count"]

    def validate_question_count(self, value):
        if value < 3 or value > 20:
            raise serializers.ValidationError("Must be between 3 and 20.")
        return value


class QuizListSerializer(serializers.ModelSerializer):
    """
    Compact quiz info — used in list endpoints.
    No questions included (that would make the list huge).
    """
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    attempt_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id", "title", "topic", "difficulty",
            "question_count", "status",
            "created_by_username", "attempt_count", "created_at",
        ]

    def get_attempt_count(self, obj):
        return obj.attempts.count()


class QuizDetailSerializer(serializers.ModelSerializer):
    """
    Full quiz WITH questions — shown when user opens a quiz to take it.
    Correct answers are hidden (QuestionSerializer, not QuestionWithAnswerSerializer).
    """
    questions = QuestionSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = Quiz
        fields = [
            "id", "title", "topic", "difficulty",
            "question_count", "status",
            "created_by_username", "created_at", "questions",
        ]


# ── Attempt Serializers ───────────────────────────────────────────────────────

class UserAnswerSubmitSerializer(serializers.Serializer):
    """Validates a single answer submission."""
    question_id = serializers.IntegerField()
    selected_option = serializers.ChoiceField(choices=["A", "B", "C", "D"])


class AttemptSubmitSerializer(serializers.Serializer):
    """Validates all answers submitted at once."""
    answers = UserAnswerSubmitSerializer(many=True)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Provide at least one answer.")
        return value


class UserAnswerResultSerializer(serializers.ModelSerializer):
    """Result for one question — shown on the results page."""
    question = QuestionWithAnswerSerializer(read_only=True)

    class Meta:
        model = UserAnswer
        fields = ["question", "selected_option", "is_correct"]


class AttemptListSerializer(serializers.ModelSerializer):
    """Lightweight attempt info for listing."""
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_topic = serializers.CharField(source="quiz.topic", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id", "quiz_title", "quiz_topic",
            "status", "score", "score_percentage",
            "total_questions", "started_at", "completed_at",
        ]


class AttemptDetailSerializer(serializers.ModelSerializer):
    """Full attempt WITH all answers — used for results page."""
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    answers = UserAnswerResultSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id", "quiz_title", "status",
            "score", "score_percentage", "total_questions",
            "started_at", "completed_at", "answers",
        ]
