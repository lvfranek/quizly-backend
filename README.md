# Quizly Backend

> **This is the backend repository.** The user interface lives in the frontend repository:
> **[Developer-Akademie-Backendkurs/project.Quizly](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)** (HTML, CSS, JavaScript).
> This API is meant to be used together with that app.

REST API for **Quizly**, an app that turns YouTube videos into quizzes. A user pastes a YouTube link, the backend downloads the audio, transcribes it locally with Whisper and lets Gemini Flash write a quiz with 10 questions. Built with Django and Django REST Framework.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Features](#features)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Settings](#settings)
- [API Endpoints](#api-endpoints)
- [How a Quiz Is Generated](#how-a-quiz-is-generated)
- [Project Structure](#project-structure)
- [Data Model](#data-model)

## Tech Stack

- `Python` 3.14
- `Django` 6.1
- `Django REST Framework` 3.18
- `djangorestframework-simplejwt` for JWT authentication with a token blacklist
- `django-cors-headers` to allow requests from the frontend
- `python-dotenv` for configuration via `.env`
- `yt-dlp` to download the audio of YouTube videos
- `openai-whisper` to transcribe the audio locally
- `google-genai` to generate the quiz with Gemini Flash
- `SQLite` as the database

## Features

- **Registration and login** with username, email and password. Passwords are stored hashed and an email can only be used once.
- **JWT in HttpOnly cookies**: login sets an `access_token` and a `refresh_token` cookie. The frontend never sees the tokens, and every protected request is authenticated through the cookie.
- **Token refresh**: when the access token expires, the frontend gets a new one through the refresh cookie.
- **Logout with blacklist**: the refresh token is put on a blacklist and both cookies are deleted, so old tokens can never be used again.
- **Quiz generation** from any YouTube URL format (`watch`, `youtu.be`, `shorts`, `embed`, with or without extra parameters). The stored URL is always normalized to `https://www.youtube.com/watch?v=<ID>`.
- **Quiz management**: list, view, rename and delete quizzes. Users can only access their own quizzes. Requests for another user's quiz return `403`.
- **Django admin** to edit quizzes and every single question.

## Installation

**Prerequisites:** Python 3.12+, Git and **FFmpeg**.

> ⚠️ **FFmpeg must be installed globally.** Whisper needs it to read the audio files. Without it, quiz generation fails.
>
> - **macOS:** `brew install ffmpeg`
> - **Windows:** `winget install --id Gyan.FFmpeg -e --source winget`, or download a build from [ffmpeg.org](https://ffmpeg.org/download.html) and add its `bin` folder to `Path`
> - **Linux:** `sudo apt install ffmpeg`
>
> Check it with `ffmpeg -version`.
>
> **Recommended:** install [Deno](https://deno.com/) as well (`brew install deno` on macOS). Newer versions of yt-dlp use a JavaScript runtime for YouTube. Without one, some videos may fail to download.

1. Clone the repository:

   ```bash
   git clone https://github.com/lvfranek/quizly-backend.git
   cd quizly-backend
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows use `.venv\Scripts\activate`.

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   This also installs PyTorch for Whisper, so the download is about 1 GB.

4. Create your environment file:

   ```bash
   cp .env.example .env
   ```

   Generate a secret key and paste it as `SECRET_KEY` in `.env`:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Get a free Gemini API key at [ai.google.dev](https://ai.google.dev/) and paste it as `GEMINI_API_KEY`.

5. Create the database tables:

   ```bash
   python manage.py migrate
   ```

6. Optional: create an admin user for the Django admin at `/admin/`:

   ```bash
   python manage.py createsuperuser
   ```

7. Start the server:

   ```bash
   python manage.py runserver
   ```

   The API now runs on `http://127.0.0.1:8000/api/`.

8. Start the [frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly) with Live Server and open it at **`http://127.0.0.1:5500`**. Use `127.0.0.1`, not `localhost`: the frontend calls the API on `127.0.0.1`, and the browser only sends the auth cookies when both use the same host.

The first quiz after a server start takes a bit longer, because Whisper downloads (only once) and loads its model.

## Environment Variables

All variables live in `.env` in the project root (see `.env.example`).

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key. Required. | a long random string |
| `GEMINI_API_KEY` | API key for Google Gemini. Required to generate quizzes. | `AIza...` |

## Settings

These values are set in `core/settings.py`.

| Setting | Description | Default |
|---|---|---|
| `GEMINI_MODEL` | Gemini model used to write the quiz. `gemini-flash-latest` always points to the current Flash model. | `gemini-flash-latest` |
| `WHISPER_MODEL` | Whisper model size. `small` or `medium` are more accurate but slower. | `base` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins allowed to call the API with cookies | `http://127.0.0.1:5500`, `http://localhost:5500` |
| `SIMPLE_JWT` | Token lifetimes | access: 5 minutes, refresh: 1 day |

The auth cookies are set with `secure=False` so they work over plain `http` locally. Set it to `True` in `auth_app/api/utils.py` when the API runs on HTTPS.

## API Endpoints

All endpoints except registration, login and token refresh need a valid `access_token` cookie. The cookies are set by the login endpoint.

**Auth**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/register/` | Create an account (`username`, `email`, `password`, `confirmed_password`) |
| `POST` | `/api/login/` | Log in with `username` and `password`, sets the `access_token` and `refresh_token` cookies |
| `POST` | `/api/logout/` | Blacklist the refresh token and delete both cookies |
| `POST` | `/api/token/refresh/` | Set a new `access_token` cookie using the `refresh_token` cookie |

Login returns:

```json
{
  "detail": "Login successfully!",
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "your_email@example.com"
  }
}
```

**Quizzes**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/quizzes/` | List your quizzes, newest first |
| `POST` | `/api/quizzes/` | Create a quiz from a YouTube URL (`{"url": "..."}`) |
| `GET` | `/api/quizzes/<id>/` | Get one quiz with its questions |
| `PATCH` | `/api/quizzes/<id>/` | Update `title` and/or `description` |
| `DELETE` | `/api/quizzes/<id>/` | Delete a quiz and all its questions |

Example quiz:

```json
{
  "id": 1,
  "title": "Elephant Trunks Quiz",
  "description": "A quick look at a brief statement about elephants and their long trunks.",
  "created_at": "2026-10-11T12:34:56.789Z",
  "updated_at": "2026-10-11T12:34:56.789Z",
  "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
  "questions": [
    {
      "id": 1,
      "question_title": "Which animal is mentioned in the video?",
      "question_options": ["Elephants", "Giraffes", "Lions", "Bears"],
      "answer": "Elephants"
    }
  ]
}
```

**Status codes for `POST /api/quizzes/`**

| Code | When |
|---|---|
| `201` | Quiz created |
| `400` | The URL is not a YouTube video, or the video cannot be downloaded (private, deleted, ...) |
| `401` | Not logged in |
| `500` | Transcription or quiz generation failed. The error is written to the server log. |

## How a Quiz Is Generated

`POST /api/quizzes/` runs these steps (all helpers live in `quiz_app/api/utils.py`):

```
YouTube URL ── normalize ── yt-dlp (audio) ── Whisper (text) ── Gemini Flash (quiz JSON) ── validate ── save
```

1. **Normalize the URL**: extract the 11-character video ID and build `https://www.youtube.com/watch?v=<ID>`.
2. **Download the audio** with yt-dlp into `tmp_audio/` under a unique file name.
3. **Transcribe** the audio locally with Whisper. The audio file is deleted afterwards, even if a step fails.
4. **Generate the quiz**: the transcript is inserted into a prompt that asks Gemini Flash for a JSON quiz with a title, a description of at most 150 characters and exactly 10 questions.
5. **Clean and validate**: markdown fences like ` ```json ` are removed, then the JSON is parsed and checked. Every question needs 4 distinct options, and the answer must be one of them.
6. **Save** the quiz and its questions in a single database transaction, so a quiz is never saved half-finished.

Depending on the video length, one request takes about 20 to 60 seconds.

## Project Structure

```
quizly-backend/
├── core/              # Project settings and root URLs
├── auth_app/          # Registration, login, logout, token refresh
│   ├── authentication.py   # Reads the JWT from the access_token cookie
│   └── api/
└── quiz_app/          # Quiz and question models, admin and API
    └── api/
        ├── permissions.py  # Only the owner can access a quiz
        └── utils.py        # YouTube, Whisper and Gemini helpers
```

Each app keeps its API code in an `api/` folder with `serializers.py`, `views.py`, `urls.py` and `utils.py`. Views only build responses; all helper functions live in `utils.py`.

## Data Model

- **User**: Django's built-in user.
- **Quiz**: `title`, `description`, `video_url`, `user` (owner), `created_at`, `updated_at`.
- **Question**: `quiz`, `question_title`, `question_options` (JSON list of 4 strings), `answer`, `created_at`, `updated_at`.

Deleting a user also deletes their quizzes, and deleting a quiz deletes its questions.
