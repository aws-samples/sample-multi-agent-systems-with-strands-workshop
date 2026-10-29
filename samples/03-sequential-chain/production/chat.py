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

A multi-line brief pasted at once is sent as ONE message.
Type 'quit' or Ctrl+C to stop.
"""
import os
import select
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chain import run_chain


def read_message(prompt: str) -> str:
    """Read one user message from the terminal.

    input() stops at the first newline, so a pasted multi-line brief would be
    sent as many separate requests. Pasted text arrives all at once, so every
    line already waiting on stdin is joined into the same message.
    Raises EOFError when stdin is closed.
    """
    if sys.platform == "win32":
        # select() only works on sockets on Windows: fall back to one line.
        return input(prompt).strip()
    print(prompt, end="", flush=True)
    fd = sys.stdin.fileno()
    data = os.read(fd, 65536)
    if not data:
        raise EOFError
    while select.select([fd], [], [], 0.1)[0]:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()


def main():
    print("Sequential Chain Production | type 'quit' to exit")
    print(f"Researcher ARN: {os.environ.get('RESEARCHER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Analyst ARN   : {os.environ.get('ANALYST_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Synthesizer   : {os.environ.get('SYNTHESIZER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print()

    run_count = 0
    while True:
        try:
            user_input = read_message("Brief: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        brief = user_input
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
