FROM python:3.11-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /app/Telethon-1 \
    && pip install --no-cache-dir .

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
