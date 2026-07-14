#!/bin/bash
# 🦇 Hi-Tech Security Bot Start Script
# Installs FFmpeg if missing, then starts the bot

echo "🦇 Hi-Tech Security Bot — Starting..."

# Install FFmpeg if not present
if ! command -v ffmpeg &> /dev/null; then
    echo "📦 Installing FFmpeg..."
    apt-get update -qq && apt-get install -y -qq ffmpeg 2>/dev/null || {
        # Fallback: download static build
        echo "⚠️ apt-get failed, downloading static FFmpeg..."
        curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz
        cd /tmp && tar -xf ffmpeg.tar.xz
        cp ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe /usr/local/bin/ 2>/dev/null
    }
    echo "✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "✅ FFmpeg found: $(ffmpeg -version 2>&1 | head -1)"
fi

# Start the bot
echo "🚀 Starting bot..."
exec python bot.py
