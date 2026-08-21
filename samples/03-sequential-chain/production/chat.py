"""
Multi-turn chat for Module 3 Production: Sequential Chain.

Each submission runs the full Researcher → Analyst → Synthesizer pipeline.
Multiple briefs are supported — each call to run_chain() is independent.

Usage:
  cd samples/03-sequential-chain/production
  source .env_arns
  python chat.py

Requires:
  RESEARCHER_RUNTIME_ARN  (from source .env_arns)
  ANALYST_RUNTIME_ARN     (from source .env_arns)
  SYNTHESIZER_RUNTIME_ARN (from source .env_arns)

Type 'quit' or Ctrl+C to stop.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chain import run_chain

DEFAULT_BRIEF = (
    "NovaCart Premium Tier: Options A ($19.99/mo invite-only), "
    "B ($14.99/mo 5% pilot), C ($12.99/mo full launch). "
    "Target: +15% CLV in 6 months. Budget: $2M."
)


def main():
    print("Sequential Chain Production | type 'quit' to exit")
    print(f"Researcher ARN: {os.environ.get('RESEARCHER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Analyst ARN   : {os.environ.get('ANALYST_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Synthesizer   : {os.environ.get('SYNTHESIZER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print()

    run_count = 0
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
        run_count += 1
        print(f"\n[Run {run_count}] Running Researcher → Analyst → Synthesizer...")
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
