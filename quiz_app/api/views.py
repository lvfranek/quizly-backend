"""API views for quizzes."""

import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quiz_app.models import Quiz

from .permissions import IsQuizOwner
from .serializers import (
    QuizCreateInputSerializer,
    QuizCreateSerializer,
    QuizSerializer,
)
from .utils import create_quiz_from_url

logger = logging.getLogger(__name__)


class QuizListCreateView(generics.ListCreateAPIView):
    """List the user's quizzes or create a new one from a YouTube URL."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Return only the quizzes owned by the current user."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related('questions')

    def post(self, request):
        """Validate the URL and generate a new quiz from the video."""
        input_serializer = QuizCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        video_url = input_serializer.validated_data['url']
        return self.build_create_response(request.user, video_url)

    def build_create_response(self, user, video_url):
        """Create the quiz and map pipeline errors to error responses."""
        try:
            quiz = create_quiz_from_url(user, video_url)
        except DownloadError:
            return Response(
                {'detail': 'Could not download the video.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception('Quiz generation failed for %s', video_url)
            return Response(
                {'detail': 'Quiz generation failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        data = QuizCreateSerializer(quiz).data
        return Response(data, status=status.HTTP_201_CREATED)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update or delete a single quiz."""

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete']
