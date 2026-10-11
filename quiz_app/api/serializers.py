"""Serializers for quizzes and their questions."""

from rest_framework import serializers

from quiz_app.models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    """Question data as returned by the list, detail and update views."""

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuestionDetailSerializer(QuestionSerializer):
    """Question data including timestamps, used after quiz creation."""

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + [
            'created_at', 'updated_at'
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Quiz with nested questions; only title and description editable."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'video_url']


class QuizCreateSerializer(QuizSerializer):
    """Quiz representation returned after a new quiz was created."""

    questions = QuestionDetailSerializer(many=True, read_only=True)
