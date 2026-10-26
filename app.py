"""Interactive, offline role-play for a future phone assistant."""

from assistant_core import UNKNOWN, ClientInquiry, make_reservation_request, reservation_update


UNCLEAR_ANSWERS = {"", "i don't know", "i dont know", "not sure", "no idea", "unknown", "idk", "skip"}


def ask_once(prompt: str, clarification: str, input_fn=input, output_fn=print) -> str:
    """Ask at most one different follow-up, then move on without inventing an answer."""
    answer = input_fn(prompt).strip()
    if answer.lower().rstrip(".!?") not in UNCLEAR_ANSWERS:
        return answer
    output_fn("Assistant: No problem. Let me ask it another way.")
    answer = input_fn(clarification).strip()
    if answer.lower().rstrip(".!?") not in UNCLEAR_ANSWERS:
        return answer
    output_fn("Assistant: That's okay. I'll leave this open for Salim to clarify later.")
    return UNKNOWN


def required(prompt: str) -> str:
    while True:
        answer = input(prompt).strip()
        if answer:
            return answer
        print("Please enter a value.")


def receive_client_inquiry() -> None:
    print("\nAssistant: Hello, this is Salim's assistant. How may I help you?")
    inquiry = ClientInquiry(
        name=ask_once("Client name: ", "What name should Salim use when following up? "),
        contact=ask_once("Callback phone or email: ", "Is there a phone number or email Salim may use? "),
        service=ask_once("Service requested (website, app, other): ", "Is it a website, app, or something else? "),
        details=ask_once("What does the client need? ", "What is the main result you want from this project? "),
    )
    if inquiry.contact == UNKNOWN:
        print("\nAssistant: Thank you. I have noted the request, but Salim will need a phone number or email to follow up.")
    else:
        print("\nAssistant: Thank you. I have noted the request for Salim to review and follow up.")
    print("\nInquiry summary for Salim:\n" + inquiry.summary())


def request_restaurant_booking() -> None:
    print("\nCreate an outbound reservation request. This is a simulation; no call is placed.")
    while True:
        try:
            booking = make_reservation_request(
                restaurant=required("Restaurant name: "),
                date_text=required("Date (YYYY-MM-DD): "),
                time_text=required("Time (HH:MM, 24-hour): "),
                guests_text=required("Number of guests: "),
                seating_preference=input("Seating preference (optional): "),
            )
            break
        except ValueError as exc:
            print(f"Please correct the request: {exc}\n")
    print("\nStatus: REQUEST READY. No reservation exists yet.")
    print("What the assistant would say on the call:\n" + booking.spoken_request())
    print("\nNow play the restaurant's role. Choose only what it actually said:")
    print("1. Confirmed  2. Alternative offered  3. Unavailable  4. No answer")
    choices = {"1": "confirmed", "2": "alternative", "3": "unavailable", "4": "no_answer"}
    while True:
        choice = input("Restaurant outcome (1-4): ").strip()
        if choice in choices:
            break
        print("Choose 1, 2, 3, or 4.")
    outcome = choices[choice]
    if outcome in {"confirmed", "alternative"}:
        reply = ask_once(
            "Restaurant's exact response or confirmation detail: ",
            "Could you repeat the confirmed booking details or proposed alternative? ",
        )
        if reply == UNKNOWN:
            outcome, reply = "unverified", ""
    else:
        reply = input("Restaurant details (optional): ")
    print("\nUpdate to Salim:\n" + reservation_update(booking, outcome, reply))


def main() -> None:
    while True:
        print("\nPersonal Assistant — offline practice")
        print("1. Receive a development client inquiry")
        print("2. Prepare and simulate a restaurant reservation call")
        print("3. Exit")
        choice = input("Choose an option (1-3): ").strip()
        if choice == "1":
            receive_client_inquiry()
        elif choice == "2":
            request_restaurant_booking()
        elif choice == "3":
            print("Goodbye.")
            return
        else:
            print("Choose 1, 2, or 3.")


if __name__ == "__main__":
    main()
