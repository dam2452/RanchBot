FROM python:3.13-slim

WORKDIR /app

RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -ms /bin/bash ranczo-klipy
USER ranczo-klipy

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "bot.main"]
