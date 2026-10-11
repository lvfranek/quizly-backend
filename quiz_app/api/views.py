"""API views for quizzes."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.models import Quiz

from .permissions import IsQuizOwner
from .serializers import QuizSerializer


class QuizListView(generics.ListAPIView):
    """List all quizzes of the authenticated user."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Return only the quizzes owned by the current user."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related('questions')


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update or delete a single quiz."""

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete']
