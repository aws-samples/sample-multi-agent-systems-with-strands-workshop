"""
Interactive multi-turn chat with the Capstone AgentCore Runtime.

Passes actorId and sessionId correctly so AgentCore Memory can maintain
conversation state across turns and across sessions.

Identifiers:
  actorId   — Your permanent user identity. Used to scope long-term memory
               records. Must be consistent across sessions for the same user.
               Pattern: [a-zA-Z0-9][a-zA-Z0-9-_/]* (1-255 chars)
               Examples: user-123, customer-abc, org/dept/user-456

  sessionId — Unique conversation ID. Determines which container instance
               handles your requests (session affinity). Also used as the
               Memory session namespace for short-term events.
               Pattern: [a-zA-Z0-9][a-zA-Z0-9-_]* (1-100 chars)
               Generated automatically per conversation; pass --session-id
               to resume a previous conversation.

How identifiers travel:
  actorId   → custom HTTP header injected by the boto3 event system BEFORE signing
               Header: X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id
  sessionId → runtimeSessionId parameter in invoke_agent_runtime
               Arrives at the container as context.session_id

Usage:
    # New conversation
    python chat.py --actor-id user-123 --runtime-arn arn:aws:bedrock-agentcore:...

    # Resume existing conversation
    python chat.py --actor-id user-123 --runtime-arn arn:... --session-id sess-abc123

    # Non-interactive (single prompt)
    python chat.py --actor-id user-123 --runtime-arn arn:... --prompt "Analyze NovaCart options"
"""

import argparse
import json
import re
import sys
import uuid

import boto3
from botocore.config import Config

# Custom header used by AgentCore to carry actor identity into the runtime container.
# Must use the X-Amzn-Bedrock-AgentCore-Runtime-Custom- prefix to pass AgentCore's
# header allowlist (other custom headers are blocked for security).
ACTOR_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id"

# Validation patterns per AWS documentation
_ACTOR_ID_RE  = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_/]*(?::[a-zA-Z0-9\-_/]+)*[a-zA-Z0-9\-_/]*$')
_SESSION_ID_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*$')


def _validate_actor_id(value: str) -> str:
    if not value or len(value) > 255:
        raise ValueError(f"actorId must be 1-255 chars, got {len(value)}")
    if not _ACTOR_ID_RE.match(value):
        raise ValueError(
            f"Invalid actorId '{value}'. "
            "Must match [a-zA-Z0-9][a-zA-Z0-9-_/]* (examples: user-123, org/team/user)"
        )
    return value


def _validate_session_id(value: str) -> str:
    if not value or len(value) > 100:
        raise ValueError(f"sessionId must be 1-100 chars, got {len(value)}")
    if not _SESSION_ID_RE.match(value):
        raise ValueError(
            f"Invalid sessionId '{value}'. "
            "Must match [a-zA-Z0-9][a-zA-Z0-9-_]* (example: sess-abc123)"
        )
    return value


def _new_session_id() -> str:
    """Generate a valid sessionId.

    runtimeSessionId requirements: 33-256 chars.
    Memory sessionId requirements: 1-100 chars, [a-zA-Z0-9][a-zA-Z0-9-_]*.
    A standard UUID (36 chars, e.g. '550e8400-e29b-41d4-a716-446655440000') satisfies both.
    """
    return str(uuid.uuid4())


def _make_client(actor_id: str) -> boto3.client:
    """Create a boto3 agentcore client that injects the actor_id custom header
    before every request is signed.

    The header is added via the boto3 event system (before-sign hook) so it is
    included in the SigV4 signature, preventing tampering in transit.
    """
    client = boto3.client(
        "bedrock-agentcore",
        region_name="us-east-1",
        config=Config(read_timeout=300),
    )

    def _inject(request, **kwargs):
        """Called by botocore just before signing — adds the actor header."""
        request.headers[ACTOR_HEADER] = actor_id

    client.meta.events.register_first(
        "before-sign.bedrock-agentcore.InvokeAgentRuntime",
        _inject,
    )
    return client


def _invoke(client, runtime_arn: str, session_id: str, prompt: str) -> str:
    """Send one message to the runtime and return the text response."""
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt}).encode(),
        qualifier="DEFAULT",
    )
    raw = resp["response"].read()
    try:
        result = json.loads(raw)
        return result.get("response", result) if isinstance(result, dict) else str(result)
    except Exception:
        return raw.decode()


def main():
    parser = argparse.ArgumentParser(
        description="Multi-turn chat with the Capstone AgentCore Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--actor-id", required=True,
        help="Your user identity (e.g. user-123). Consistent per person across sessions.",
    )
    parser.add_argument(
        "--runtime-arn", required=True,
        help="Orchestrator Runtime ARN (from deploy.py output).",
    )
    parser.add_argument(
        "--session-id", default=None,
        help="Resume an existing conversation. Omit to start a new one.",
    )
    parser.add_argument(
        "--prompt", default=None,
        help="Non-interactive: send a single prompt and exit.",
    )
    args = parser.parse_args()

    # Validate identifiers
    try:
        actor_id  = _validate_actor_id(args.actor_id)
        session_id = _validate_session_id(args.session_id) if args.session_id \
                     else _new_session_id()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = _make_client(actor_id)

    # ── Non-interactive mode ──────────────────────────────────────────────────
    if args.prompt:
        response = _invoke(client, args.runtime_arn, session_id, args.prompt)
        print(response)
        return

    # ── Interactive multi-turn loop ───────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  AgentCore Capstone — Multi-turn Chat")
    print(f"{'='*60}")
    print(f"  Actor ID  : {actor_id}")
    print(f"  Session ID: {session_id}")
    print(f"    ↑ Save this to resume the conversation later with --session-id")
    print(f"  Runtime   : {args.runtime_arn}")
    print(f"{'='*60}")
    print(f"  Type your message. Press Ctrl+C or Enter on an empty line to exit.")
    print()

    turn = 0
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            break

        turn += 1
        print(f"Agent: ", end="", flush=True)
        try:
            response = _invoke(client, args.runtime_arn, session_id, user_input)
            print(response)
        except Exception as exc:
            print(f"\n[Error invoking runtime: {exc}]", file=sys.stderr)
        print()

    print(f"\nSession ended ({turn} turns).")
    print(f"To resume this conversation:")
    print(f"  python chat.py --actor-id {actor_id} --runtime-arn {args.runtime_arn} "
          f"--session-id {session_id}")


if __name__ == "__main__":
    main()
