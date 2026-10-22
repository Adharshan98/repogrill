# Stage 1: build the React website into static files
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python server that serves the API and the built website
FROM python:3.10-slim
# git is needed to clone the repos we interview people about
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_DIR=/app/models \
    STATIC_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:////app/data/repogrill.db

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Download the embedding model now, so the first request doesn't wait for it
RUN python -c "from app.services.embedder import get_model; get_model()"

COPY --from=frontend /frontend/dist /app/frontend/dist
RUN mkdir -p /app/data

# Hosting platforms like Render set $PORT; default to 8000 locally
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
