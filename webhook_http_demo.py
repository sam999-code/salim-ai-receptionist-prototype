"""Optional localhost-only HTTP test; uses fake tokens and a random port."""

import hashlib
import hmac
import http.client
import json
from threading import Thread
from urllib.parse import urlencode

from webhook_receiver import WebhookServer


def run_demo() -> None:
    token = "local-http-demo-token"
    secret = "local-http-demo-secret"
    server = WebhookServer(("127.0.0.1", 0), token, secret)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200 and response.read() == b"OK"
        print("HTTP health check: PASS")

        query = urlencode({"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": "54321"})
        connection.request("GET", f"/webhook?{query}")
        response = connection.getresponse()
        assert response.status == 200 and response.read() == b"54321"
        print("HTTP GET verification: PASS")

        payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{
            "field": "messages", "value": {"messages": [{"id": "http-demo-1", "from": "demo-sender", "type": "text", "text": {"body": "Hi over localhost"}}]}
        }]}]}
        body = json.dumps(payload).encode("utf-8")
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        for _ in range(2):
            connection.request("POST", "/webhook", body, {"Content-Type": "application/json", "X-Hub-Signature-256": signature})
            response = connection.getresponse()
            assert response.status == 200 and response.read() == b"EVENT_RECEIVED"
        assert server.received == ["Hi over localhost"]
        assert server.conversations.sessions["demo-sender"].opening_message == "Hi over localhost"
        print("HTTP signed POST and duplicate handling: PASS")

        connection.request("POST", "/webhook", body, {"X-Hub-Signature-256": "sha256=wrong"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        print("HTTP invalid signature rejection: PASS")
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    run_demo()
