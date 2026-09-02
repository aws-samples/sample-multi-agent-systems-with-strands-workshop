"""
Multi-turn production chat for AgentCore Dynamic Swarm.

Usage (interactive):
  python chat.py --actor-id workshop-user-01 --runtime-arn $(cat .runtime_arn)
  python chat.py --actor-id workshop-user-01 --runtime-arn $(cat .runtime_arn) --session-id <id>

Usage (single prompt):
  python chat.py --actor-id workshop-user-01 --runtime-arn $(cat .runtime_arn) --prompt "your brief here"

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


def _register_actor_header(client, actor_id):
    # invoke_agent_runtime has no API parameter for custom runtime headers - the
    # actor id must travel as an HTTP header injected via the boto3 event system.
    def add_actor_header(request, **kwargs):
        request.headers.add_header(ACTOR_HEADER, actor_id)
    client.meta.events.register_first(
        "before-sign.bedrock-agentcore.InvokeAgentRuntime", add_actor_header
    )


def _invoke(client, runtime_arn, actor_id, session_id, user_input):
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": user_input}).encode(),
        qualifier="DEFAULT",
    )
    raw = response["response"].read()
    try:
        result = json.loads(raw)
        return result.get("response", result) if isinstance(result, dict) else result
    except Exception:
        return raw.decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-id",    required=True,  help="Your user alias (scopes conversation memory per user)")
    parser.add_argument("--runtime-arn", required=True,  help="Orchestrator ARN from .runtime_arn or deploy output")
    parser.add_argument("--session-id",  default=None,   help="Resume a previous session (optional)")
    parser.add_argument("--prompt",      default=None,   help="Single prompt — submit once and exit (non-interactive)")
    parser.add_argument("--region",      default=os.environ.get("AWS_REGION") or boto3.Session().region_name)
    args = parser.parse_args()
    if not args.region:
        args.region = args.runtime_arn.split(":")[3]

    session_id = args.session_id or str(uuid.uuid4())
    client = boto3.client(
        "bedrock-agentcore",
        region_name=args.region,
        config=Config(read_timeout=600),
    )
    _register_actor_header(client, args.actor_id)

    sep = "=" * 60
    print(sep)
    print("  AgentCore Dynamic Swarm — Multi-turn Chat")
    print(sep)
    print(f"  Actor ID  : {args.actor_id}")
    print(f"  Session ID: {session_id}")
    print( "    ↑ Save this to resume the conversation later with --session-id")
    print(f"  Runtime   : {args.runtime_arn}")
    print(sep)

    if args.prompt:
        print(f"You: {args.prompt}\n")
        try:
            print(f"Agent: {_invoke(client, args.runtime_arn, args.actor_id, session_id, args.prompt)}\n")
        except Exception as e:
            print(f"[Error: {e}]\n")
        return

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
            print(f"\nAgent: {_invoke(client, args.runtime_arn, args.actor_id, session_id, user_input)}\n")
        except Exception as e:
            print(f"\n[Error invoking runtime: {e}]\n")


if __name__ == "__main__":
    main()
