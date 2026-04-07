FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy everything and install
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
