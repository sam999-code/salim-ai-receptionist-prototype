"""Demonstrate the webhook rules offline, without opening a network port."""

import hashlib
import hmac
import json
from webhook_receiver import SeenMessages, extract_text_messages, verify_challenge, verify_signature


def run_demo() -> None:
    verify_token = "local-demo-verify-token"
    app_secret = "local-demo-app-secret"
    query = "hub.mode=subscribe&hub.verify_token=local-demo-verify-token&hub.challenge=12345"
    assert verify_challenge(query, verify_token) == "12345"
    print("GET verification logic: PASS")

    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{
        "field": "messages", "value": {"messages": [{"id": "demo-message-1", "type": "text", "text": {"body": "Hi from the demo"}}]}
    }]}]}
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, signature, app_secret)
    print("Signed POST payload logic: PASS")

    seen = SeenMessages()
    received = []
    for _ in range(2):  # Meta may deliver the same event again.
        for message_id, text in extract_text_messages(json.loads(body)):
            if seen.is_new(message_id):
                received.append(text)
                print(f"Inbound text: {text}")
    assert received == ["Hi from the demo"]
    print("Duplicate handling: PASS (processed once)")

    assert not verify_signature(body, "sha256=wrong", app_secret)
    print("Invalid signature rejected: PASS")


if __name__ == "__main__":
    run_demo()
