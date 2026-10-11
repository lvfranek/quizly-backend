"""Serializers for quizzes and their questions."""

from rest_framework import serializers

from quiz_app.models import Question, Quiz

from .utils import build_video_url, extract_video_id


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


class QuizCreateInputSerializer(serializers.Serializer):
    """Validates the YouTube URL sent to create a new quiz."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Return the normalized watch URL or reject non YouTube URLs."""
        video_id = extract_video_id(value)
        if video_id is None:
            raise serializers.ValidationError(
                'Please provide a valid YouTube video URL.'
            )
        return build_video_url(video_id)
