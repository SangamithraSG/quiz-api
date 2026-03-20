"""
models.py (quiz app)

Database schema for the quiz system.

Tables / Models:
  Quiz         — A quiz with a topic, difficulty, and list of questions
  Question     — A single question belonging to a quiz (with 4 choices + answer)
  QuizAttempt  — One user's attempt at a quiz (started, in-progress, completed)
  UserAnswer   — The answer a user gave for one question in an attempt

Relationships:
  Quiz         1─── many ─── Question
  Quiz         1─── many ─── QuizAttempt
  QuizAttempt  1─── many ─── UserAnswer
  Question     1─── many ─── UserAnswer
  User         1─── many ─── QuizAttempt
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Quiz(models.Model):
    """
    Represents a quiz.

    A quiz is created by a user (or admin) with a topic and difficulty.
    The AI then generates questions for it.
    """

    # ── Difficulty levels ────────────────────────────────────────────
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DIFFICULTY_CHOICES = [
        (EASY, "Easy"),
        (MEDIUM, "Medium"),
        (HARD, "Hard"),
    ]

    # ── Status of the quiz ───────────────────────────────────────────
    DRAFT = "draft"            # Questions are being generated
    READY = "ready"            # Questions are ready, users can attempt
    FAILED = "failed"          # AI generation failed

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (READY, "Ready"),
        (FAILED, "Failed"),
    ]

    # ── Fields ───────────────────────────────────────────────────────
    title = models.CharField(max_length=255)

    topic = models.CharField(
        max_length=200,
        help_text="E.g. 'Python basics', 'World War 2', 'Photosynthesis'"
    )

    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default=MEDIUM,
    )

    # How many questions to generate (between 3 and 20)
    question_count = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(20)],
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=DRAFT,
    )

    # The user who created this quiz
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,      # If user is deleted, delete their quizzes
        related_name="created_quizzes",
    )

    created_at = models.DateTimeField(auto_now_add=True)  # Set once on creation
    updated_at = models.DateTimeField(auto_now=True)       # Updated on every save

    def __str__(self):
        return f"[{self.difficulty}] {self.title}"

    class Meta:
        db_table = "quizzes"
        ordering = ["-created_at"]  # Newest quizzes first

        # Database index on topic — speeds up filtering quizzes by topic
        indexes = [
            models.Index(fields=["topic"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["status"]),
        ]


class Question(models.Model):
    """
    A single multiple-choice question in a quiz.

    Each question has:
      - The question text
      - 4 answer options (option_a through option_d)
      - The correct answer (which option is right)
      - An optional explanation shown after the quiz
    """

    OPTION_A = "A"
    OPTION_B = "B"
    OPTION_C = "C"
    OPTION_D = "D"

    OPTION_CHOICES = [
        (OPTION_A, "A"),
        (OPTION_B, "B"),
        (OPTION_C, "C"),
        (OPTION_D, "D"),
    ]

    # Which quiz this question belongs to
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",  # Allows quiz.questions.all()
    )

    question_text = models.TextField()

    # The 4 answer choices
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)

    # Which option is the correct answer
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)

    # Optional explanation shown after the quiz ends
    explanation = models.TextField(blank=True, default="")

    # Position of this question in the quiz (1, 2, 3, ...)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}..."

    class Meta:
        db_table = "questions"
        ordering = ["order"]  # Return questions in order


class QuizAttempt(models.Model):
    """
    One user's attempt at a quiz.

    Tracks:
      - Which user is attempting
      - Which quiz they're attempting
      - When they started and finished
      - Their final score
      - Whether it's in progress or completed
    """

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

    STATUS_CHOICES = [
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
        (ABANDONED, "Abandoned"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=IN_PROGRESS)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Score = number of correct answers
    score = models.PositiveIntegerField(default=0)

    # Score as a percentage (0-100), calculated when quiz is submitted
    score_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
    )

    # Total questions in this quiz at time of attempt
    total_questions = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} → {self.quiz.title} ({self.status})"

    class Meta:
        db_table = "quiz_attempts"
        ordering = ["-started_at"]  # Most recent attempts first

        # A user should only have one in-progress attempt per quiz at a time.
        # We enforce this in the view logic, not at DB level (for flexibility).
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["quiz"]),
        ]


class UserAnswer(models.Model):
    """
    The answer a user gave for a specific question during an attempt.

    One UserAnswer is created for each question the user answers.
    This lets us track which questions they got right/wrong.
    """

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_answers",
    )

    # Which option the user chose (A, B, C, or D)
    selected_option = models.CharField(max_length=1)

    # Was it correct? Stored for fast analytics queries.
    is_correct = models.BooleanField(default=False)

    answered_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Before saving, automatically determine if the answer is correct.
        This way we don't have to calculate it every time we need it.
        """
        self.is_correct = (self.selected_option == self.question.correct_option)
        super().save(*args, **kwargs)

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.attempt.user.username} answered {self.selected_option}"

    class Meta:
        db_table = "user_answers"

        # A user can only answer each question once per attempt
        unique_together = [["attempt", "question"]]
