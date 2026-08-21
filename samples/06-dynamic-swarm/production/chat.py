"""
Multi-turn production chat for AgentCore Dynamic Swarm.

Usage:
  python chat.py --actor-id workshop-user-01 --runtime-arn $(cat .runtime_arn)
  python chat.py --actor-id workshop-user-01 --runtime-arn $(cat .runtime_arn) --session-id <id>

Press Enter on an empty line or Ctrl+C to exit.
Each session is identified by a session-id — save it to resume the conversation.
"""
import argparse
import json
import os
import uuid

import boto3
from botocore.config import Config

ACTOR_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-id",    required=True,  help="Your user alias (scopes conversation memory per user)")
    parser.add_argument("--runtime-arn", required=True,  help="Orchestrator ARN from .runtime_arn or deploy output")
    parser.add_argument("--session-id",  default=None,   help="Resume a previous session (optional)")
    parser.add_argument("--region",      default=os.environ.get("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    session_id = args.session_id or str(uuid.uuid4())
    client = boto3.client(
        "bedrock-agentcore",
        region_name=args.region,
        config=Config(read_timeout=600),
    )

    sep = "=" * 60
    print(sep)
    print("  AgentCore Dynamic Swarm — Multi-turn Chat")
    print(sep)
    print(f"  Actor ID  : {args.actor_id}")
    print(f"  Session ID: {session_id}")
    print( "    ↑ Save this to resume the conversation later with --session-id")
    print(f"  Runtime   : {args.runtime_arn}")
    print(sep)
    print("  Type your message. Press Ctrl+C or Enter on an empty line to exit.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            print("Goodbye!")
            break

        try:
            response = client.invoke_agent_runtime(
                agentRuntimeArn=args.runtime_arn,
                runtimeSessionId=session_id,
                payload=json.dumps({"prompt": user_input}).encode(),
                qualifier="DEFAULT",
                requestMetadata={ACTOR_HEADER: args.actor_id},
            )
            raw = response["response"].read()
            try:
                result = json.loads(raw)
                reply = result.get("response", result) if isinstance(result, dict) else result
            except Exception:
                reply = raw.decode()
            print(f"\nAgent: {reply}\n")
        except Exception as e:
            print(f"\n[Error invoking runtime: {e}]\n")


if __name__ == "__main__":
    main()
