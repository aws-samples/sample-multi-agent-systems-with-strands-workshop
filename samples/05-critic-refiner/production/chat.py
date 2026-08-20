"""
Multi-turn chat for Module 5 Production: Critic-Refiner.

Each submission runs the full Writer↔Critic loop against the deployed runtimes.
Multiple conversations are supported — each call to run_chain() is independent.

Usage:
  cd samples/05-critic-refiner/production
  source .env_arns
  python chat.py

Requires:
  WRITER_RUNTIME_ARN  (from source .env_arns)
  CRITIC_RUNTIME_ARN  (from source .env_arns)

Type 'quit' or Ctrl+C to stop.
"""
import sys
import os

# chain.py and a2a_utils.py are in the same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chain import run_chain, MAX_CYCLES

DEFAULT_BRIEF = """
DECISION BRIEF: NovaCart Premium Tier Launch
Options: A (Exclusive $19.99/mo) | B (5% pilot $14.99/mo) | C (Full launch $12.99/mo)
Success target: +15% CLV in 6 months | Budget: $2M | Deadline: 2027-01-31
"""


def main():
    print("Critic-Refiner Production | type 'quit' to exit")
    print(f"Writer ARN: {os.environ.get('WRITER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Critic ARN: {os.environ.get('CRITIC_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Max revision cycles: {MAX_CYCLES}\n")

    conversation = 0
    while True:
        try:
            user_input = input("Brief (Enter for default): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        brief = user_input if user_input else DEFAULT_BRIEF
        conversation += 1
        print(f"\n[Conversation {conversation}] Running Writer↔Critic loop...")
        print("─" * 60)
        try:
            memo = run_chain(brief)
            print(memo)
        except Exception as e:
            print(f"Error: {e}")
        print("─" * 60)
        print()


if __name__ == "__main__":
    main()
