"""Helper functions for turning a YouTube video into a quiz."""

import re
from urllib.parse import parse_qs, urlparse

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
