"""Helper functions for turning a YouTube video into a quiz."""

import json
import re
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp
from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from yt_dlp.utils import DownloadError

from quiz_app.models import Question, Quiz

AUDIO_DIR = settings.BASE_DIR / 'tmp_audio'
VIDEO_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{11}')
YOUTUBE_HOSTS = ('youtube.com', 'music.youtube.com')
PATH_PREFIXES = ('shorts', 'embed', 'live')
QUESTION_COUNT = 10
OPTION_COUNT = 4

TRANSCRIPT_PROMPT = (
    'Transcribe the spoken words of this video. '
    'Return only the transcript text.'
)

QUIZ_PROMPT = """Based on the following transcript, generate a quiz in valid \
JSON format.

The quiz must follow this exact structure:

{{
  "title": "Create a concise quiz title based on the topic of the \
transcript.",
  "description": "Summarize the transcript in no more than 150 \
characters. Do not include any quiz questions or answers.",
  "questions": [
    {{
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer from the above options"
    }},
    ...
    (exactly 10 questions)
  ]
}}

Requirements:
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present \
in 'question_options'.
- The output must be valid JSON and parsable as-is (e.g., using Python's \
json.loads).
- Do not include explanations, comments, or any text outside the JSON.

Transcript:
{transcript}
"""


def parse_url(url):
    """Parse the URL and add a scheme if the user left it out."""
    url = url.strip()
    if '://' not in url:
        url = f'https://{url}'
    return urlparse(url)


def get_id_from_youtube_path(parsed_url):
    """Read the video ID from a youtube.com watch, shorts or embed URL."""
    if parsed_url.path == '/watch':
        return parse_qs(parsed_url.query).get('v', [None])[0]
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) == 2 and path_parts[0] in PATH_PREFIXES:
        return path_parts[1]
    return None


def extract_video_id(url):
    """Return the 11 character video ID of a YouTube URL, or None."""
    parsed_url = parse_url(url)
    host = parsed_url.netloc.lower().removeprefix('www.').removeprefix('m.')
    if host == 'youtu.be':
        video_id = parsed_url.path.strip('/')
    elif host in YOUTUBE_HOSTS:
        video_id = get_id_from_youtube_path(parsed_url)
    else:
        return None
    if video_id and VIDEO_ID_PATTERN.fullmatch(video_id):
        return video_id
    return None


def build_video_url(video_id):
    """Build the normalized watch URL that is stored in the database."""
    return f'https://www.youtube.com/watch?v={video_id}'


def build_download_options():
    """Return yt_dlp options that save the audio under a unique name."""
    AUDIO_DIR.mkdir(exist_ok=True)
    tmp_filename = str(AUDIO_DIR / f'{uuid.uuid4()}.%(ext)s')
    return {
        'format': 'bestaudio/best',
        'outtmpl': tmp_filename,
        'quiet': True,
        'noplaylist': True,
    }


def download_audio(video_url):
    """Download the audio track of a YouTube video and return its path."""
    with yt_dlp.YoutubeDL(build_download_options()) as ydl:
        info = ydl.extract_info(video_url, download=True)
        return ydl.prepare_filename(info)


def delete_audio(audio_path):
    """Delete a temporary audio file if it exists."""
    if audio_path:
        Path(audio_path).unlink(missing_ok=True)


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load the Whisper model once and reuse it for later requests."""
    return whisper.load_model(settings.WHISPER_MODEL)


def transcribe_audio(audio_path):
    """Transcribe an audio file to text with Whisper."""
    result = get_whisper_model().transcribe(audio_path, fp16=False)
    return result['text'].strip()


def build_quiz_prompt(transcript):
    """Insert the transcript into the quiz generation prompt."""
    return QUIZ_PROMPT.format(transcript=transcript)


def request_quiz_from_gemini(prompt):
    """Send the prompt to Gemini Flash and return the raw text answer."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL, contents=prompt
    )
    return response.text


def clean_ai_response(text):
    """Remove markdown code fences like ``` or ```json from the answer."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def validate_question(question):
    """Raise ValueError if a question does not have the expected shape."""
    options = question.get('question_options')
    if not question.get('question_title'):
        raise ValueError('A question has no title.')
    if not isinstance(options, list) or len(set(options)) != OPTION_COUNT:
        raise ValueError('A question needs exactly 4 distinct options.')
    if question.get('answer') not in options:
        raise ValueError('The answer must be one of the options.')


def parse_quiz_data(text):
    """Parse the AI answer into a dict and validate the quiz structure."""
    quiz_data = json.loads(clean_ai_response(text))
    if not isinstance(quiz_data, dict):
        raise ValueError('The quiz must be a JSON object.')
    if not quiz_data.get('title') or 'description' not in quiz_data:
        raise ValueError('The quiz needs a title and a description.')
    questions = quiz_data.get('questions')
    if not isinstance(questions, list) or len(questions) != QUESTION_COUNT:
        raise ValueError('The quiz needs exactly 10 questions.')
    for question in questions:
        validate_question(question)
    return quiz_data


def generate_quiz_data(transcript):
    """Create validated quiz data from a video transcript with Gemini."""
    answer = request_quiz_from_gemini(build_quiz_prompt(transcript))
    return parse_quiz_data(answer)


def build_question(quiz, question_data):
    """Create an unsaved Question object from the AI question data."""
    return Question(
        quiz=quiz,
        question_title=question_data['question_title'],
        question_options=question_data['question_options'],
        answer=question_data['answer'],
    )


def save_quiz(user, video_url, quiz_data):
    """Save the quiz and all its questions in a single transaction."""
    with transaction.atomic():
        quiz = Quiz.objects.create(
            user=user,
            title=quiz_data['title'],
            description=quiz_data['description'],
            video_url=video_url,
        )
        Question.objects.bulk_create(
            [build_question(quiz, data) for data in quiz_data['questions']]
        )
    return quiz


def transcribe_downloaded_audio(video_url):
    """Download the audio, transcribe it and always delete the file."""
    audio_path = None
    try:
        audio_path = download_audio(video_url)
        return transcribe_audio(audio_path)
    finally:
        delete_audio(audio_path)


def request_transcript_from_gemini(video_url):
    """Let Gemini watch the YouTube video and return its transcript."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    video = genai_types.FileData(file_uri=video_url)
    contents = genai_types.Content(parts=[
        genai_types.Part(file_data=video),
        genai_types.Part(text=TRANSCRIPT_PROMPT),
    ])
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL, contents=contents
    )
    return response.text.strip()


def transcribe_with_gemini(video_url, download_error):
    """Use Gemini as fallback; re-raise the download error if it fails."""
    try:
        return request_transcript_from_gemini(video_url)
    except genai_errors.APIError:
        raise download_error


def get_transcript(video_url):
    """
    Transcribe the video with Whisper. Servers in data centers are often
    blocked by YouTube, so Gemini watches the video directly instead.
    """
    try:
        return transcribe_downloaded_audio(video_url)
    except DownloadError as download_error:
        return transcribe_with_gemini(video_url, download_error)


def create_quiz_from_url(user, video_url):
    """Run the full pipeline from YouTube URL to saved quiz."""
    transcript = get_transcript(video_url)
    quiz_data = generate_quiz_data(transcript)
    return save_quiz(user, video_url, quiz_data)
