import json
import unittest
from types import SimpleNamespace

from smart_flow import AnthropicClassifier, SmartConversationManager


def result(intent="unclear", name="", service="", service_quote="", details=""):
    return {"intent": intent, "name_quote": name, "service": service,
            "service_quote": service_quote, "details_quote": details}


class FakeClassifier:
    def __init__(self, answers):
        self.answers = iter(answers)

    def classify(self, message, last_question):
        return next(self.answers)


class SmartFlowTests(unittest.TestCase):
    def test_anthropic_request_uses_structured_output(self):
        class FakeMessages:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(stop_reason="end_turn", content=[
                    SimpleNamespace(type="thinking", thinking=""),
                    SimpleNamespace(type="text", text=json.dumps(result("development", service="website", service_quote="website")))])

        messages = FakeMessages()
        classifier = AnthropicClassifier(SimpleNamespace(messages=messages))
        self.assertEqual("website", classifier.classify("website", "What do you need?")["service"])
        self.assertEqual("json_schema", messages.kwargs["output_config"]["format"]["type"])
        self.assertEqual("user", messages.kwargs["messages"][0]["role"])
        self.assertGreaterEqual(messages.kwargs["max_tokens"], 1024)

    def test_customer_transcript_keeps_price_and_barber_context(self):
        manager = SmartConversationManager(FakeClassifier([
            result("greeting"),
            result("food_order"),
            result("pricing"),
            result("development", service="website_and_app", service_quote="website and a reservation app",
                   details="i need a website and a reservation app for my barber shop"),
            result("courtesy"),
        ]))
        turns = [manager.accept("customer", message) for message in (
            "hi", "2 burger and on salat", "cool and how much",
            "i need a website and a reservation app for my barber shop", "ok thank you")]
        self.assertIn("price depends", turns[2].reply)
        self.assertIn("name", turns[3].reply.lower())
        self.assertEqual("website and app", manager.sessions["customer"].service)
        self.assertIn("barber shop", manager.sessions["customer"].details)
        self.assertTrue(all(turn.summary is None for turn in turns))
        self.assertIn("You're welcome", turns[4].reply)

    def test_reservation_app_name_change_and_complaint_transcript(self):
        manager = SmartConversationManager(FakeClassifier([
            result("greeting"),
            result("development", service="app", service_quote="app",
                   details="i need a reservation app"),
            result("unclear"),
        ]))
        turns = [manager.accept("customer", message) for message in (
            "hi body", "i need a reservation app", "mo", "mo",
            "i need to change my mind", "this is not ok", "it is more worst than before")]
        self.assertIn("name", turns[1].reply.lower())
        self.assertEqual("mo", manager.sessions["customer"].name)
        self.assertIn("what would people reserve", turns[2].reply.lower())
        self.assertNotIn("What should I call you", turns[2].reply)
        self.assertIn("What would you like instead", turns[4].reply)
        self.assertIn("notes may be wrong", turns[5].reply)
        self.assertIn("stop asking", turns[6].reply)
        self.assertTrue(all(turn.summary is None for turn in turns))
        self.assertEqual("", manager.sessions["customer"].service)

    def test_generic_reservation_app_waits_for_concrete_purpose(self):
        manager = SmartConversationManager(FakeClassifier([
            result("development", service="app", service_quote="app",
                   details="I need a reservation app"),
            result("development", details="Customers reserve haircuts for my barber shop"),
        ]))
        first = manager.accept("customer", "I need a reservation app")
        self.assertIsNone(first.summary)
        self.assertIn("name", first.reply.lower())
        second = manager.accept("customer", "Mo")
        self.assertIn("what would people reserve", second.reply.lower())
        third = manager.accept("customer", "Customers reserve haircuts for my barber shop")
        self.assertIn("barber shop", third.summary)
        self.assertIn("Client: Mo", third.summary)

    def test_incomplete_model_response_has_safe_diagnostic(self):
        class FakeMessages:
            def create(self, **kwargs):
                return SimpleNamespace(stop_reason="max_tokens", content=[SimpleNamespace(type="thinking")])

        manager = SmartConversationManager(AnthropicClassifier(SimpleNamespace(messages=FakeMessages())))
        turn = manager.accept("customer", "i need a website")
        self.assertIsNone(turn.summary)
        self.assertEqual("Incomplete response (max_tokens)", manager.sessions["customer"].last_error)

    def test_off_topic_and_vague_answers_do_not_make_a_lead(self):
        manager = SmartConversationManager(FakeClassifier([
            result("greeting"), result("off_topic"), result(), result(), result(),
        ]))
        turns = [manager.accept("one", text) for text in
                 ("hi", "i need to drink some water", "mai", "same", "a")]
        self.assertTrue(all(turn.summary is None for turn in turns))
        session = manager.sessions["one"]
        self.assertEqual(("", "", ""), (session.name, session.service, session.details))
        self.assertNotIn("?", turns[-1].reply)

    def test_explicit_development_inquiry_makes_summary(self):
        manager = SmartConversationManager(FakeClassifier([
            result("development", service="website", service_quote="website",
                   details="A restaurant website with an online reservation form"),
            result("development", name="Alex Morgan"),
        ]))
        first = manager.accept("two", "A restaurant website with an online reservation form")
        self.assertIn("name", first.reply.lower())
        done = manager.accept("two", "Alex Morgan")
        self.assertIn("Client: Alex Morgan", done.summary)
        self.assertIn("Service: website", done.summary)

    def test_model_cannot_invent_slots(self):
        manager = SmartConversationManager(FakeClassifier([
            result("development", service="website", service_quote="website",
                   details="A complex restaurant reservation website"),
        ]))
        turn = manager.accept("three", "same")
        self.assertIsNone(turn.summary)
        self.assertEqual("", manager.sessions["three"].service)

    def test_food_joke_once_and_no_order(self):
        manager = SmartConversationManager(FakeClassifier([result("food_order"), result("food_order")]))
        first = manager.accept("four", "two burgers and fries")
        second = manager.accept("four", "two burgers")
        self.assertIn("website", first.reply)
        self.assertNotIn("website", second.reply)
        self.assertIsNone(first.summary)

    def test_api_failure_is_safe(self):
        manager = SmartConversationManager(FakeClassifier([]))
        turn = manager.accept("five", "I need a website")
        self.assertIsNone(turn.summary)
        self.assertIn("trouble", turn.reply)


if __name__ == "__main__":
    unittest.main()
