"""Shared demo account: reset on login and a daily quiz limit."""

import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from quiz_app.models import Question, Quiz

SAMPLE_QUIZZES_FILE = Path(__file__).resolve().parent / 'demo_quizzes.json'
COUNTER_TIMEOUT = 60 * 60 * 48


def is_demo_user(user):
    """Return True if the user is the shared demo account."""
    return user.is_authenticated and user.username == settings.DEMO_USERNAME


@transaction.atomic
def reset_demo_account(user):
    """Delete all quizzes of the demo user and recreate the sample quizzes."""
    Quiz.objects.filter(user=user).delete()
    samples = json.loads(SAMPLE_QUIZZES_FILE.read_text(encoding='utf-8'))
    # Reversed, so the first sample in the file is the newest quiz in the list
    for sample in reversed(samples):
        create_sample_quiz(user, sample)


def create_sample_quiz(user, sample):
    """Create one quiz with its questions from the sample data."""
    quiz = Quiz.objects.create(
        user=user,
        title=sample['title'],
        description=sample['description'],
        video_url=sample['video_url'],
    )
    Question.objects.bulk_create(
        Question(quiz=quiz, **question) for question in sample['questions']
    )


def get_counter_key():
    """Return the cache key for today's demo quiz counter."""
    return f'demo-quiz-count-{timezone.localdate().isoformat()}'


def demo_limit_reached():
    """Return True if the demo account created its daily maximum of quizzes."""
    count = cache.get(get_counter_key(), 0)
    return count >= settings.DEMO_DAILY_QUIZ_LIMIT


def count_demo_quiz():
    """Count one more quiz created by the demo account today."""
    key = get_counter_key()
    cache.add(key, 0, COUNTER_TIMEOUT)
    cache.incr(key)
