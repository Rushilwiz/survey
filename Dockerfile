FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The SQLite file lives on a volume, not in the image layer. /data is created
# with app ownership so an empty named volume inherits it (Docker copies the
# image's ownership on first mount) and the non-root user can write there.
RUN useradd --create-home --uid 10001 survey \
    && mkdir -p /data \
    && chown -R survey:survey /data /app
USER survey

ENV SURVEY_DB=/data/survey.db

EXPOSE 8000

# One worker, many threads: SQLite has a single writer, so threads inside one
# process avoid cross-process lock contention. Plenty for a classroom.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", \
     "--access-logfile", "-", "app:app"]
