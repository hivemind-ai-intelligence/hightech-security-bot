#!/bin/bash
# 🦇 Hi-Tech Security Bot — Render Start Script

echo "🦇 Starting Hi-Tech Security Bot..."

# Install system deps if missing
if ! command -v ffmpeg &>/dev/null; then
    echo "📦 Installing FFmpeg..."
    apt-get update -qq && apt-get install -y -qq ffmpeg 2>/dev/null || true
fi

# Check libsodium (needed for davey/voice)
python3 -c "import ctypes; ctypes.cdll.LoadLibrary('libsodium.so.23')" 2>/dev/null || {
    echo "📦 Installing libsodium..."
    apt-get install -y -qq libsodium23 libsodium-dev 2>/dev/null || true
}

echo "✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1 || echo 'MISSING')"
echo "✅ Python: $(python3 --version)"

# Check voice support
python3 -c "import davey; print('✅ davey OK')" 2>/dev/null || echo "⚠️ davey missing"
python3 -c "import PyNaCl; print('✅ PyNaCl OK')" 2>/dev/null || echo "⚠️ PyNaCl missing"

echo "🚀 Launching bot..."
exec python3 bot.py
