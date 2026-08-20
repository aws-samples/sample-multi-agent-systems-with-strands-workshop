"""
Invoke the Sequential Chain against deployed specialist runtimes.

Reads ARNs from env vars (set them via: source .env_arns).

Usage:
  source .env_arns
  python invoke.py
  python invoke.py "your brief here"
"""
import sys
from chain import run_chain, DEFAULT_BRIEF

brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
print(run_chain(brief))
