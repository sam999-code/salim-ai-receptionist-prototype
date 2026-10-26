"""Small, predictable inquiry dialogue for the WhatsApp learning exercise.

This module drafts replies only. It does not call the WhatsApp API.
"""

from dataclasses import dataclass, field
import re
from threading import Lock

from assistant_core import UNKNOWN, ClientInquiry


FIELDS = ("name", "service", "details")
QUESTIONS = {
    "name": "Hello, this is Salim's assistant. What name should Salim use when following up?",
    "service": "What kind of development project do you need: a website, an app, or something else?",
    "details": "What would you like the project to do? A short description is enough.",
}
CLARIFICATIONS = {
    "name": "No problem. What should I call you?",
    "service": "No problem. Is your idea closer to a website, an app, or another service?",
    "details": "No problem. What is the main result you would like from it?",
}
UNCLEAR = {
    "", "i don't know", "i dont know", "not sure", "no idea", "unknown",
    "idk", "skip", "unsure", "لا أعرف", "مش عارف", "لا ادري",
}


def is_unclear(text: str) -> bool:
    return text.strip().lower().rstrip(".!?؟ ") in UNCLEAR


def is_courtesy(text: str) -> bool:
    cleaned = text.strip().lower().rstrip(".!?؟ ")
    return bool(re.fullmatch(r"(?:thanks|thx|thank\w* you(?: so much| very much)?|شكرا|شكراً)", cleaned))


def is_food_order(text: str) -> bool:
    """Catch obvious food orders; never infer that an order was placed."""
    lower = text.lower()
    food = re.search(r"\b(?:burgers?|burgere|fries|friss|pizza|sandwiches?|food|meal)\b", lower)
    order = re.search(r"\b(?:order|takeaway|delivery)\b", lower)
    development = re.search(r"\b(?:web|website|app|software|development)\b", lower)
    return bool(food and order and not development)


def is_not_a_name(text: str) -> bool:
    lower = text.strip().lower().rstrip(".!?؟ ")
    return bool(
        lower in {"web", "website", "app", "reservation", "reservations", "booking", "table", "order"}
        or re.search(r"\b(?:i need|i want|looking for|book a table)\b", lower)
        or any(char.isdigit() for char in lower)
    )


@dataclass(frozen=True)
class AssistantTurn:
    reply: str
    summary: str | None = None


@dataclass
class InquirySession:
    opening_message: str = ""
    answers: dict[str, str] = field(default_factory=dict)
    follow_ups: list[str] = field(default_factory=list)
    field_index: int = 0
    clarification_used: bool = False
    food_joke_used: bool = False
    finished: bool = False

    def accept(self, text: str) -> AssistantTurn:
        """Advance once per message; ask no more than one clarification per field."""
        text = text.strip()
        if is_courtesy(text):
            return AssistantTurn("You're welcome. Salim's assistant is here if you need anything else.")
        if is_food_order(text):
            if not self.food_joke_used:
                self.food_joke_used = True
                return AssistantTurn(
                    "That sounds delicious! 🍔🍟 We don't sell burgers here, so I can't place "
                    "that order. Salim builds websites and apps, though—perhaps your favorite "
                    "burger place could use a great ordering website. Did you mean a website "
                    "project, or were you trying to reach a restaurant?"
                )
            return AssistantTurn(
                "I still can't place food orders in this chat. Please contact the restaurant "
                "directly if you want to order."
            )
        if self.finished:
            if text:
                self.follow_ups.append(text)
            return AssistantTurn(
                "Thank you. I've noted that additional detail for Salim.",
                self._summary(),
            )
        if not self.opening_message:
            self.opening_message = text or "No opening message"
            return AssistantTurn(QUESTIONS[FIELDS[0]])

        current = FIELDS[self.field_index]
        if current == "name" and text.lower() in {"web", "website", "app", "software"}:
            self.answers["service"] = "website" if text.lower() in {"web", "website"} else text.lower()
            return AssistantTurn(
                f"I can help with a {self.answers['service']} inquiry. "
                "What name should Salim use when following up?"
            )

        unclear = is_unclear(text) or (current == "name" and is_not_a_name(text))
        if unclear and not self.clarification_used:
            self.clarification_used = True
            return AssistantTurn(CLARIFICATIONS[current])

        self.answers[current] = UNKNOWN if unclear else text
        self.clarification_used = False
        self.field_index += 1
        while self.field_index < len(FIELDS) and FIELDS[self.field_index] in self.answers:
            self.field_index += 1
        if self.field_index < len(FIELDS):
            return AssistantTurn(QUESTIONS[FIELDS[self.field_index]])

        self.finished = True
        return AssistantTurn(
            "Thank you. I've noted your request for Salim to review and follow up.",
            self._summary(),
        )

    def _summary(self) -> str:
        inquiry = ClientInquiry(
            name=self.answers["name"],
            contact="WhatsApp chat (sender available in webhook)",
            service=self.answers["service"],
            details=self.answers["details"],
        )
        notes = "\nAdditional details: " + " | ".join(self.follow_ups) if self.follow_ups else ""
        return f"Opening message: {self.opening_message}\n{inquiry.summary()}{notes}"


class ConversationManager:
    """Keep separate, in-memory practice sessions for different senders."""

    def __init__(self) -> None:
        self.sessions: dict[str, InquirySession] = {}
        self.lock = Lock()

    def accept(self, sender: str, text: str) -> AssistantTurn:
        with self.lock:
            session = self.sessions.setdefault(sender, InquirySession())
            return session.accept(text)
