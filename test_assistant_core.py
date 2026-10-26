import unittest
from datetime import date

from assistant_core import ClientInquiry, make_reservation_request, reservation_update
from app import ask_once


class AssistantCoreTests(unittest.TestCase):
    def setUp(self):
        self.booking = make_reservation_request(
            "Riviera Royal", "2026-10-30", "20:00", "3", today=date(2026, 10, 26)
        )

    def test_confirmed_requires_restaurant_reply(self):
        with self.assertRaisesRegex(ValueError, "Record what the restaurant said"):
            reservation_update(self.booking, "confirmed")
        self.assertIn("CONFIRMED", reservation_update(self.booking, "confirmed", "Table confirmed under Salim."))

    def test_alternative_and_no_answer_are_not_confirmations(self):
        self.assertIn("not confirmed", reservation_update(self.booking, "alternative", "Only 21:00 is available."))
        self.assertIn("No reservation has been made", reservation_update(self.booking, "no_answer"))
        self.assertIn("No reservation has been confirmed", reservation_update(self.booking, "unverified"))

    def test_invalid_date_and_guest_count(self):
        with self.assertRaises(ValueError):
            make_reservation_request("Riviera Royal", "2026-10-25", "20:00", "3", today=date(2026, 10, 26))
        with self.assertRaises(ValueError):
            make_reservation_request("Riviera Royal", "2026-10-30", "20:00", "0", today=date(2026, 10, 26))

    def test_client_summary_does_not_promise_price_or_timeline(self):
        summary = ClientInquiry("Alex", "alex@example.com", "website", "Booking page").summary()
        self.assertIn("Salim reviews this inquiry", summary)
        self.assertIn("provided contact", summary)
        self.assertNotIn("calls the client back", summary)
        self.assertNotIn("price", summary.lower())

    def test_unknown_answer_gets_one_new_question_then_moves_on(self):
        prompts = []
        replies = iter(["I don't know", "not sure"])

        def respond(prompt):
            prompts.append(prompt)
            return next(replies)

        self.assertEqual("Not provided", ask_once("What do you need? ", "What result do you want? ", respond, lambda _: None))
        self.assertEqual(["What do you need? ", "What result do you want? "], prompts)

    def test_unknown_contact_is_not_reported_as_follow_up_ready(self):
        summary = ClientInquiry("Alex", "Not provided", "website", "Not provided").summary()
        self.assertIn("Ask the client for a contact method", summary)
        self.assertNotIn("follows up using the provided contact", summary)


if __name__ == "__main__":
    unittest.main()
