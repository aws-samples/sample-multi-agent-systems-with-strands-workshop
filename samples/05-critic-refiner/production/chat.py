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

A multi-line brief pasted at once is sent as ONE message.
Type 'quit' or Ctrl+C to stop.
"""
import select
import sys
import os

# chain.py and a2a_utils.py are in the same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chain import run_chain, MAX_CYCLES


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
    print("Critic-Refiner Production | type 'quit' to exit")
    print(f"Writer ARN: {os.environ.get('WRITER_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Critic ARN: {os.environ.get('CRITIC_RUNTIME_ARN', 'NOT SET')[:60]}...")
    print(f"Max revision cycles: {MAX_CYCLES}\n")

    conversation = 0
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
