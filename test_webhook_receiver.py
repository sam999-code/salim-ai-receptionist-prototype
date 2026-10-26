import hashlib
import hmac
import unittest

from webhook_receiver import SeenMessages, extract_inbound_messages, extract_text_messages, verify_challenge, verify_signature


class WebhookTests(unittest.TestCase):
    def test_challenge_requires_matching_token(self):
        query = "hub.mode=subscribe&hub.verify_token=my-token&hub.challenge=abc123"
        self.assertEqual("abc123", verify_challenge(query, "my-token"))
        self.assertIsNone(verify_challenge(query, "wrong-token"))

    def test_signature_checks_raw_body(self):
        body = b'{"message":"Hi"}'
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(body, signature, "secret"))
        self.assertFalse(verify_signature(body + b" ", signature, "secret"))
        self.assertFalse(verify_signature(body, "", "secret"))

    def test_only_inbound_text_is_processed(self):
        payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{
            "field": "messages", "value": {
                "statuses": [{"id": "status-1"}],
                "messages": [
                    {"id": "msg-1", "from": "sender-a", "type": "text", "text": {"body": "Hi"}},
                    {"id": "msg-2", "type": "image"},
                ],
            },
        }]}]}
        self.assertEqual([("msg-1", "Hi")], extract_text_messages(payload))
        self.assertEqual([("msg-1", "sender-a", "Hi")], extract_inbound_messages(payload))

    def test_duplicate_id_is_processed_once(self):
        seen = SeenMessages(limit=2)
        self.assertTrue(seen.is_new("a"))
        self.assertFalse(seen.is_new("a"))
        self.assertTrue(seen.is_new("b"))
        self.assertTrue(seen.is_new("c"))
        self.assertTrue(seen.is_new("a"))  # Oldest ID is evicted to bound memory.


if __name__ == "__main__":
    unittest.main()
