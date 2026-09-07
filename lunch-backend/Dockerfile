FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic

# media/ will be a mounted volume in docker-compose, but create it
# so the app doesn't crash if it's ever run without one
RUN mkdir -p media/profile_pictures

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]