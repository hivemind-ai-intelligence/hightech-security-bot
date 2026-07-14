FROM python:3.12-slim

LABEL org.opencontainers.image.title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 Discord Bot"
LABEL org.opencontainers.image.description="Enterprise-grade Discord bot — 64+ global commands + 29 music commands, vampire edition"

WORKDIR /app

# Install FFmpeg + system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Data dir
RUN mkdir -p /app/data

# Start
CMD ["python", "bot.py"]
