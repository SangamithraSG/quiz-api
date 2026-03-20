"""
Migration: Create quiz, question, quiz_attempts, and user_answers tables.
"""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Users must be created before quizzes (foreign key dependency)
        ("users", "0001_initial"),
    ]

    operations = [
        # ── Quiz table ─────────────────────────────────────────────
        migrations.CreateModel(
            name="Quiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("topic", models.CharField(max_length=200)),
                ("difficulty", models.CharField(
                    choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
                    default="medium", max_length=10,
                )),
                ("question_count", models.PositiveIntegerField(
                    default=5,
                    validators=[
                        django.core.validators.MinValueValidator(3),
                        django.core.validators.MaxValueValidator(20),
                    ],
                )),
                ("status", models.CharField(
                    choices=[("draft", "Draft"), ("ready", "Ready"), ("failed", "Failed")],
                    default="draft", max_length=10,
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="created_quizzes",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "quizzes", "ordering": ["-created_at"]},
        ),

        # ── Question table ─────────────────────────────────────────
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("quiz", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="questions",
                    to="quiz.quiz",
                )),
                ("question_text", models.TextField()),
                ("option_a", models.CharField(max_length=500)),
                ("option_b", models.CharField(max_length=500)),
                ("option_c", models.CharField(max_length=500)),
                ("option_d", models.CharField(max_length=500)),
                ("correct_option", models.CharField(
                    choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                    max_length=1,
                )),
                ("explanation", models.TextField(blank=True, default="")),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"db_table": "questions", "ordering": ["order"]},
        ),

        # ── QuizAttempt table ──────────────────────────────────────
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="quiz_attempts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("quiz", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="attempts",
                    to="quiz.quiz",
                )),
                ("status", models.CharField(
                    choices=[("in_progress", "In Progress"), ("completed", "Completed"), ("abandoned", "Abandoned")],
                    default="in_progress", max_length=15,
                )),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("score", models.PositiveIntegerField(default=0)),
                ("score_percentage", models.FloatField(
                    default=0.0,
                    validators=[
                        django.core.validators.MinValueValidator(0.0),
                        django.core.validators.MaxValueValidator(100.0),
                    ],
                )),
                ("total_questions", models.PositiveIntegerField(default=0)),
            ],
            options={"db_table": "quiz_attempts", "ordering": ["-started_at"]},
        ),

        # ── UserAnswer table ───────────────────────────────────────
        migrations.CreateModel(
            name="UserAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("attempt", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="answers",
                    to="quiz.quizattempt",
                )),
                ("question", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="user_answers",
                    to="quiz.question",
                )),
                ("selected_option", models.CharField(max_length=1)),
                ("is_correct", models.BooleanField(default=False)),
                ("answered_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "user_answers"},
        ),

        # ── Indexes ────────────────────────────────────────────────
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(fields=["topic"], name="quiz_topic_idx"),
        ),
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(fields=["difficulty"], name="quiz_difficulty_idx"),
        ),
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(fields=["status"], name="quiz_status_idx"),
        ),
        migrations.AddIndex(
            model_name="quizattempt",
            index=models.Index(fields=["user", "status"], name="attempt_user_status_idx"),
        ),

        # ── Unique constraint ──────────────────────────────────────
        migrations.AlterUniqueTogether(
            name="useranswer",
            unique_together={("attempt", "question")},  # One answer per question per attempt
        ),
    ]
