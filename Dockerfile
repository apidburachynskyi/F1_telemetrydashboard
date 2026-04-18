FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FF1_CACHE_DIR=/app/cache
RUN mkdir -p /app/cache

RUN chmod +x entrypoint.sh

EXPOSE 8050

CMD ["./entrypoint.sh"]
