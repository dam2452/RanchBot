FROM python:3.13-alpine AS builder

WORKDIR /app

RUN apk add --no-cache \
    postgresql-dev \
    gcc \
    musl-dev \
    libffi-dev

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.13-alpine

WORKDIR /app

RUN apk add --no-cache \
    ffmpeg \
    libpq \
    curl \
    && adduser -D -u 1000 -s /bin/sh ranczo-klipy \
    && chown -R ranczo-klipy:ranczo-klipy /app

COPY --from=builder --chown=ranczo-klipy:ranczo-klipy /root/.local /home/ranczo-klipy/.local
COPY --chown=ranczo-klipy:ranczo-klipy . .

USER ranczo-klipy

ENV PYTHONUNBUFFERED=1 \
    PATH=/home/ranczo-klipy/.local/bin:$PATH

CMD ["python", "-m", "bot.main"]
