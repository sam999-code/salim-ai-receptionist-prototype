"""Promptfoo provider that evaluates the real draft conversation code."""

import json

from smart_flow import SmartConversationManager


SCENARIOS = {
    "burger_price_barber": [
        "hi",
        "2 burger and on salat",
        "cool and how much",
        "i need a website and a reservation app for my barber shop",
        "ok thank you",
    ],
    "water_vague": ["hi", "i need to drink some water", "mai", "same", "a"],
    "clear_website": [
        "I need a restaurant website with an online table reservation form",
        "My name is Alex Morgan",
    ],
    "reservation_change_complaint": [
        "hi body",
        "i need a reservation app",
        "mo",
        "mo",
        "i need to change my mind",
        "this is not ok",
        "it is more worst than before",
    ],
}


def call_api(prompt, options, context):
    scenario = context.get("vars", {}).get("scenario")
    if scenario not in SCENARIOS:
        return {"error": "Unknown evaluation scenario"}
    manager = SmartConversationManager()
    replies = []
    summaries = []
    diagnostics = []
    for message in SCENARIOS[scenario]:
        turn = manager.accept("synthetic-customer", message)
        replies.append(turn.reply)
        if turn.summary:
            summaries.append(turn.summary)
        if manager.sessions["synthetic-customer"].last_error:
            diagnostics.append(manager.sessions["synthetic-customer"].last_error)
    session = manager.sessions["synthetic-customer"]
    return {"output": json.dumps({
        "replies": replies,
        "summaries": summaries,
        "diagnostics": diagnostics,
        "service": session.service,
        "details": session.details,
    })}
