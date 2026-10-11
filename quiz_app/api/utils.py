"""Helper functions for turning a YouTube video into a quiz."""

import re
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp
from django.conf import settings

AUDIO_DIR = settings.BASE_DIR / 'tmp_audio'
VIDEO_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{11}')
YOUTUBE_HOSTS = ('youtube.com', 'music.youtube.com')
PATH_PREFIXES = ('shorts', 'embed', 'live')


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
