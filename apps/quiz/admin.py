"""
admin.py (quiz app)

Register quiz models with the Django admin panel.
"""

from django.contrib import admin
from .models import Quiz, Question, QuizAttempt, UserAnswer


class QuestionInline(admin.TabularInline):
    """
    Shows questions directly inside the Quiz edit page.
    TabularInline = compact table layout.
    """
    model = Question
    extra = 0                          # Don't show empty extra rows
    readonly_fields = ["order"]        # Can't reorder from admin
    fields = ["order", "question_text", "correct_option", "option_a",
              "option_b", "option_c", "option_d", "explanation"]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "topic", "difficulty", "status", "created_by", "created_at"]
    list_filter = ["difficulty", "status"]
    search_fields = ["title", "topic"]
    inlines = [QuestionInline]    # Show questions inside quiz
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["quiz", "order", "question_text", "correct_option"]
    list_filter = ["quiz__difficulty"]
    search_fields = ["question_text"]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "quiz", "status", "score", "score_percentage", "started_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "quiz__title"]
    readonly_fields = ["started_at", "completed_at", "score", "score_percentage"]


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ["attempt", "question", "selected_option", "is_correct"]
    list_filter = ["is_correct"]
