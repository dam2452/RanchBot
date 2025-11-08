FROM python:3.13-slim

WORKDIR /app

RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 -ms /bin/bash ranczo-klipy && \
    chown -R ranczo-klipy:ranczo-klipy /app

COPY --chown=ranczo-klipy:ranczo-klipy requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=ranczo-klipy:ranczo-klipy . .

USER ranczo-klipy

ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8077/health || exit 1

CMD ["python", "-m", "bot.main"]
