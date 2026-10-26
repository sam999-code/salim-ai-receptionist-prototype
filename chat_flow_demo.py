"""Try the WhatsApp conversation locally without sending any messages."""

import argparse
import os
from chat_flow import ConversationManager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smart", action="store_true", help="Use ANTHROPIC_API_KEY for AI-assisted drafts")
    args = parser.parse_args()
    if args.smart:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY is missing from this PowerShell session. No AI request was made.")
        from smart_flow import SmartConversationManager
        manager = SmartConversationManager()
        print("AI-assisted WhatsApp draft practice. Type /exit to stop. No message is sent.")
    else:
        manager = ConversationManager()
        print("Offline WhatsApp conversation practice. Type /exit to stop.")
    while True:
        text = input("Customer: ")
        if text.strip().lower() == "/exit":
            return
        turn = manager.accept("practice-customer", text)
        print(f"Draft reply (not sent): {turn.reply}")
        if args.smart:
            diagnostic = manager.sessions["practice-customer"].last_error
            if diagnostic:
                print(f"Local diagnostic: {diagnostic}")
        if turn.summary:
            print(f"\nInquiry summary for Salim (local only):\n{turn.summary}\n")


if __name__ == "__main__":
    main()
