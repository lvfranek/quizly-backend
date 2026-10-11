"""Admin configuration for quizzes and questions."""

from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.StackedInline):
    """Edit the questions of a quiz directly on the quiz page."""

    model = Question
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin view for quizzes including their questions."""

    list_display = ['title', 'user', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin view for editing single questions."""

    list_display = ['question_title', 'quiz', 'answer']
    list_filter = ['quiz']
    search_fields = ['question_title']
    readonly_fields = ['created_at', 'updated_at']
