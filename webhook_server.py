"""
Hi-Tech Security Discord Bot — Webhook Server
HTTP server for external alert intake (SIEM, IDS/IPS, monitoring tools).
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

logger = logging.getLogger("webhook-server")

# These are imported lazily to avoid circular imports
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_ALERT_WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "")
WEBHOOK_BIND_ADDR = os.getenv("WEBHOOK_BIND_ADDR", "0.0.0.0")


SEVERITY_COLORS = {
    "critical": 0xFF0000,   # Blood Red
    "high": 0xB22222,        # Firebrick
    "medium": 0x8B0000,      # Dark Red
    "low": 0x4A0000,         # Deep Maroon
    "info": 0x2D0000,        # Near-Black Red
}


class AlertHandler(BaseHTTPRequestHandler):
    """HTTP handler for incoming security alerts."""

    def do_POST(self):
        # Authenticate
        api_key = self.headers.get("X-API-Key", "")
        if WEBHOOK_API_KEY and not self._verify_key(api_key):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error": "Forbidden: invalid API key"}')
            return

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            alert = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        # Validate required fields
        if not alert.get("title"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Missing required field: title"}')
            return

        # Send to Discord webhook
        success = self._send_to_discord(alert)

        if success:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            logger.info(f"Alert forwarded: {alert.get('title')}")
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Failed to forward alert"}')

    def do_GET(self):
        """Health check."""
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def _verify_key(self, provided_key: str) -> bool:
        """Constant-time API key comparison."""
        return hmac.compare_digest(provided_key, WEBHOOK_API_KEY)

    def _send_to_discord(self, alert: dict) -> bool:
        """Forward the alert to a Discord webhook as an embed."""
        if not DISCORD_WEBHOOK_URL:
            logger.warning("DISCORD_ALERT_WEBHOOK_URL not configured")
            return False

        severity = alert.get("severity", "medium").lower()
        color = SEVERITY_COLORS.get(severity, 0xFFA500)

        embed = {
            "title": f"🚨 {alert.get('title', 'Security Alert')}",
            "description": alert.get("details", alert.get("description", ""))[:4096],
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [],
            "footer": {"text": f"Source: {alert.get('source', 'External')} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞"},
        }

        if alert.get("source_ip"):
            embed["fields"].append({"name": "Source IP", "value": alert["source_ip"], "inline": True})
        if alert.get("target"):
            embed["fields"].append({"name": "Target", "value": alert["target"], "inline": True})
        if alert.get("severity"):
            embed["fields"].append({"name": "Severity", "value": severity.upper(), "inline": True})

        try:
            payload = {"embeds": [embed]}
            if alert.get("mention"):
                payload["content"] = alert["mention"]

            resp = requests.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=10,
            )
            return resp.status_code == 204 or resp.status_code == 200
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"Webhook: {args[0]}")


def run_webhook_server():
    """Start the webhook alert intake server."""
    if not WEBHOOK_API_KEY:
        logger.warning("WEBHOOK_API_KEY not set — webhook server will accept unauthenticated requests!")

    server = HTTPServer((WEBHOOK_BIND_ADDR, WEBHOOK_PORT), AlertHandler)
    logger.info(f"🪝 Webhook server listening on {WEBHOOK_BIND_ADDR}:{WEBHOOK_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_webhook_server()
