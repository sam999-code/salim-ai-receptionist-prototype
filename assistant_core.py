"""Small, offline building blocks for a personal receptionist lesson."""

from dataclasses import dataclass
from datetime import date, datetime

UNKNOWN = "Not provided"


@dataclass(frozen=True)
class ClientInquiry:
    name: str
    contact: str
    service: str
    details: str

    def summary(self) -> str:
        next_step = (
            "Suggested next step: Ask the client for a contact method before follow-up."
            if self.contact == UNKNOWN
            else "Suggested next step: Salim reviews this inquiry and follows up using the provided contact."
        )
        return (
            f"Client: {self.name}\nContact: {self.contact}\n"
            f"Service: {self.service}\nNeeds: {self.details}\n"
            f"{next_step}"
        )


@dataclass(frozen=True)
class ReservationRequest:
    restaurant: str
    visit_date: date
    visit_time: str
    guests: int
    seating_preference: str = ""

    def spoken_request(self) -> str:
        seat = (
            f" If possible, our seating preference is {self.seating_preference}."
            if self.seating_preference else ""
        )
        return (
            f"Hello, I would like to book a table for {self.guests} people "
            f"on {self.visit_date:%A, %B %d, %Y} at {self.visit_time}."
            f"{seat} Is that available?"
        )


def make_reservation_request(
    restaurant: str, date_text: str, time_text: str, guests_text: str,
    seating_preference: str = "", *, today: date | None = None,
) -> ReservationRequest:
    restaurant = restaurant.strip()
    if not restaurant:
        raise ValueError("Restaurant name is required.")
    try:
        visit_date = date.fromisoformat(date_text.strip())
    except ValueError as exc:
        raise ValueError("Use a real date in YYYY-MM-DD format.") from exc
    if visit_date < (today or date.today()):
        raise ValueError("The reservation date cannot be in the past.")
    try:
        visit_time = datetime.strptime(time_text.strip(), "%H:%M").strftime("%H:%M")
    except ValueError as exc:
        raise ValueError("Use 24-hour time in HH:MM format, for example 20:00.") from exc
    try:
        guests = int(guests_text.strip())
    except ValueError as exc:
        raise ValueError("Guest count must be a whole number.") from exc
    if guests < 1:
        raise ValueError("Guest count must be at least one.")
    return ReservationRequest(
        restaurant, visit_date, visit_time, guests, seating_preference.strip()
    )


def reservation_update(request: ReservationRequest, outcome: str, reply: str = "") -> str:
    """Report only the outcome supplied by the simulated restaurant."""
    outcome = outcome.strip().lower()
    reply = reply.strip()
    visit = f"{request.restaurant} on {request.visit_date:%A, %B %d} at {request.visit_time} for {request.guests}"
    if outcome == "confirmed":
        if not reply:
            raise ValueError("Record what the restaurant said before marking it confirmed.")
        return f"CONFIRMED: The restaurant confirmed a table at {visit}. Restaurant reply: {reply}"
    if outcome == "alternative":
        if not reply:
            raise ValueError("Record the alternative offered by the restaurant.")
        return f"ALTERNATIVE OFFERED: Your requested table at {visit} is not confirmed. Restaurant reply: {reply}"
    if outcome == "unavailable":
        return f"UNAVAILABLE: The restaurant could not accommodate the request at {visit}. Restaurant reply: {reply or 'No further details.'}"
    if outcome == "no_answer":
        return f"NO ANSWER: I could not reach {request.restaurant}. No reservation has been made."
    if outcome == "unverified":
        return f"UNVERIFIED: I could not obtain clear booking details from {request.restaurant}. No reservation has been confirmed."
    raise ValueError("Outcome must be confirmed, alternative, unavailable, no_answer, or unverified.")
