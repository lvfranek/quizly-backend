"""API views for quizzes."""

from rest_framework import generics

from quiz_app.models import Quiz

from .serializers import QuizSerializer


class QuizListView(generics.ListAPIView):
    """List all quizzes of the authenticated user."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Return only the quizzes owned by the current user."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related('questions')
