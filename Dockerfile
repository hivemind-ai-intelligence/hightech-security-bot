FROM python:3.12-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsodium23 \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
