"""Local WhatsApp webhook receiver. It never sends a WhatsApp message."""

import hashlib
import hmac
import json
import os
import secrets
from collections import deque
from getpass import getpass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from chat_flow import ConversationManager


MAX_BODY_BYTES = 1_000_000


def verify_challenge(query: str, expected_token: str) -> str | None:
    params = parse_qs(query, keep_blank_values=True)
    mode = params.get("hub.mode", [""])[0]
    token = params.get("hub.verify_token", [""])[0]
    challenge = params.get("hub.challenge", [""])[0]
    if mode == "subscribe" and challenge and hmac.compare_digest(token, expected_token):
        return challenge
    return None


def verify_signature(body: bytes, supplied: str, app_secret: str) -> bool:
    if not supplied.startswith("sha256=") or not app_secret:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


def extract_inbound_messages(payload: object) -> list[tuple[str, str | None, str]]:
    """Return (message id, sender, text); ignore statuses and non-text events."""
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        return []
    found = []
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue
            for message in value.get("messages", []):
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                message_id = message.get("id")
                sender = message.get("from")
                text = message.get("text", {}).get("body") if isinstance(message.get("text"), dict) else None
                if isinstance(message_id, str) and isinstance(text, str):
                    found.append((message_id, sender if isinstance(sender, str) else None, text))
    return found


def extract_text_messages(payload: object) -> list[tuple[str, str]]:
    """Compatibility helper for the earlier webhook lesson."""
    return [(message_id, text) for message_id, _sender, text in extract_inbound_messages(payload)]


class SeenMessages:
    """Bounded in-memory duplicate guard for this one-process lesson."""

    def __init__(self, limit: int = 1000):
        self.limit = limit
        self.ids = set()
        self.order = deque()
        self.lock = Lock()

    def is_new(self, message_id: str) -> bool:
        with self.lock:
            if message_id in self.ids:
                return False
            if len(self.order) >= self.limit:
                self.ids.remove(self.order.popleft())
            self.order.append(message_id)
            self.ids.add(message_id)
            return True


class WebhookServer(ThreadingHTTPServer):
    def __init__(self, address, verify_token: str, app_secret: str):
        super().__init__(address, WebhookHandler)
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.seen = SeenMessages()
        self.received: list[str] = []  # Demo only; data stays in process memory.
        if os.getenv("ASSISTANT_MODE", "rules").lower() == "smart":
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("ASSISTANT_MODE=smart requires ANTHROPIC_API_KEY in this process")
            from smart_flow import SmartConversationManager
            self.conversations = SmartConversationManager()
        else:
            self.conversations = ConversationManager()


class WebhookHandler(BaseHTTPRequestHandler):
    def reply(self, status: int, content: bytes = b"") -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        if url.path == "/health":
            self.reply(200, b"OK")
            return
        if url.path != "/webhook":
            self.reply(404)
            return
        challenge = verify_challenge(url.query, self.server.verify_token)
        if challenge is None:
            self.reply(403)
        else:
            self.reply(200, challenge.encode("utf-8"))

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/webhook":
            self.reply(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.reply(400)
            return
        if not 0 < length <= MAX_BODY_BYTES:
            self.reply(413)
            return
        body = self.rfile.read(length)
        if not verify_signature(body, self.headers.get("X-Hub-Signature-256", ""), self.server.app_secret):
            self.reply(403)
            return
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.reply(400)
            return
        for message_id, sender, text in extract_inbound_messages(payload):
            if self.server.seen.is_new(message_id):
                self.server.received.append(text)
                print(f"Inbound text: {text}", flush=True)
                if sender:
                    turn = self.server.conversations.accept(sender, text)
                    print(f"Draft reply (not sent): {turn.reply}", flush=True)
                    if turn.summary:
                        print(f"Inquiry summary for Salim (local only):\n{turn.summary}", flush=True)
        self.reply(200, b"EVENT_RECEIVED")

    def log_message(self, format: str, *args) -> None:
        # Avoid logging URLs, phone numbers, headers, or payloads by default.
        pass


def main() -> None:
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN") or getpass(
        "Existing Verify Token (hidden; press Enter to generate a new one): "
    ).strip()
    if not verify_token:
        verify_token = secrets.token_urlsafe(32)
        print(f"Verify Token for Meta (save privately): {verify_token}")
    print("Paste the Meta App secret now. Input will be hidden; press Enter when done.")
    app_secret = os.environ.get("META_APP_SECRET") or getpass("Meta App secret (hidden): ").strip()
    if not app_secret:
        raise SystemExit("App secret is required. Nothing was started.")
    try:
        server = WebhookServer(("127.0.0.1", 8000), verify_token, app_secret)
    except OSError as exc:
        raise SystemExit(f"Could not start localhost server on port 8000: {exc}") from exc
    print("Listening locally at http://127.0.0.1:8000/webhook (no public HTTPS yet)")
    print("Keep this window open. Press Ctrl+C to stop. No WhatsApp replies are sent.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
