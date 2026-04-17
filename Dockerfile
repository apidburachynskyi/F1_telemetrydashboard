FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# FastF1 cache stored inside container (persists per container lifetime)
ENV FF1_CACHE_DIR=/app/cache
RUN mkdir -p /app/cache

EXPOSE 8050

CMD gunicorn app:server \
    --workers 1 \
    --timeout 180 \
    --bind 0.0.0.0:${PORT:-8050}
