FROM python:3.12-slim

LABEL org.opencontainers.image.title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 Discord Bot"
LABEL org.opencontainers.image.description="Enterprise-grade Discord security bot — 64+ global slash commands, vampire edition"

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source
COPY . .

# Create data dir
RUN mkdir -p /app/data

# Start bot
CMD ["python", "bot.py"]
