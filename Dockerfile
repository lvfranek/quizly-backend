FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CPU-only torch keeps the image a few GB smaller than the CUDA build
RUN TORCH_VERSION=$(grep '^torch==' requirements.txt | cut -d= -f3) \
    && pip install "torch==${TORCH_VERSION}" \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --worker-class gthread --workers 2 --threads 4 --timeout 300"]
