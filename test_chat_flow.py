import unittest

from assistant_core import UNKNOWN
from chat_flow import ConversationManager, InquirySession


class InquiryDialogueTests(unittest.TestCase):
    def test_one_clarification_then_moves_on_without_loop(self):
        session = InquirySession()
        self.assertIn("name", session.accept("Hi").reply.lower())
        self.assertIn("call you", session.accept("not sure").reply.lower())
        self.assertIn("development project", session.accept("I don't know").reply.lower())
        self.assertEqual(UNKNOWN, session.answers["name"])
        self.assertIn("project to do", session.accept("website").reply.lower())
        done = session.accept("A table reservation form")
        self.assertIn("follow up", done.reply.lower())
        self.assertIn("Service: website", done.summary)
        self.assertIn("Client: Not provided", done.summary)
        self.assertTrue(session.finished)

    def test_separate_senders_and_no_repeated_questions_after_finish(self):
        manager = ConversationManager()
        self.assertIn("name", manager.accept("sender-a", "Hi").reply.lower())
        self.assertIn("name", manager.accept("sender-b", "Hello").reply.lower())
        manager.accept("sender-a", "Alex")
        manager.accept("sender-a", "website")
        done = manager.accept("sender-a", "A booking form")
        self.assertIn("Alex", done.summary)
        self.assertIsNone(manager.accept("sender-b", "Sam").summary)
        follow_up = manager.accept("sender-a", "It should work on mobile")
        self.assertNotIn("?", follow_up.reply)
        self.assertIn("It should work on mobile", follow_up.summary)

    def test_food_order_is_not_recorded_as_name_and_thanks_is_not_a_note(self):
        session = InquirySession()
        session.accept("hi")
        order_reply = session.accept("i need to order 2 burgere and 1 french friss")
        self.assertIn("That sounds delicious", order_reply.reply)
        self.assertIn("I can't place that order", order_reply.reply)
        self.assertIn("websites and apps", order_reply.reply)
        self.assertNotIn("name", session.answers)
        self.assertIsNone(order_reply.summary)

        repeated_order = session.accept("Please order two burgers and fries")
        self.assertNotIn("delicious", repeated_order.reply)
        self.assertNotIn("?", repeated_order.reply)
        self.assertNotIn("name", session.answers)

        service_reply = session.accept("web")
        self.assertIn("What name", service_reply.reply)
        self.assertEqual("website", session.answers["service"])
        topic_reply = session.accept("reservation")
        self.assertIn("What should I call you", topic_reply.reply)
        self.assertNotIn("name", session.answers)
        thanks_reply = session.accept("thanke you")
        self.assertIn("You're welcome", thanks_reply.reply)
        self.assertIsNone(thanks_reply.summary)
        self.assertFalse(session.finished)

    def test_service_given_before_name_skips_repeated_service_question(self):
        session = InquirySession()
        session.accept("Hello")
        session.accept("website")
        next_turn = session.accept("Alex Morgan")
        self.assertIn("project to do", next_turn.reply)
        summary = session.accept("An online table reservation form").summary
        self.assertIn("Client: Alex Morgan", summary)
        self.assertIn("Service: website", summary)

    def test_thanks_after_completion_does_not_become_project_detail(self):
        session = InquirySession()
        for message in ("Hi", "Alex", "website", "A booking form"):
            session.accept(message)
        thanks = session.accept("thank you")
        self.assertIsNone(thanks.summary)
        self.assertEqual([], session.follow_ups)


if __name__ == "__main__":
    unittest.main()
