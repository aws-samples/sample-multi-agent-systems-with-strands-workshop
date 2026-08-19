"""
Deploy Module 8: Capstone — 4 AgentCore Runtimes + AgentCore Memory.

What this script creates:
  1. AgentCore Memory resource  (STM + LTM for multi-turn conversation state)
  2. Researcher Runtime          (specialist: market research)
  3. Analyzer Runtime            (specialist: option analysis — called ×3 in parallel)
  4. Critic-Refiner Runtime      (specialist: Writer→Critic quality loop)
  5. Orchestrator Runtime        (coordinates all three; has Memory + invoke permissions)

Architecture:
  User ──► Orchestrator ──► Researcher
                         ──► Analyzer ×3 (concurrent)
                         ──► Critic-Refiner

  actorId  (user identity) travels via custom header X-Amzn-...-Custom-Actor-Id.
  sessionId (conversation) = runtimeSessionId from invoke_agent_runtime, stable
             within a container session.

Usage:
    python deploy.py                        # default prefix m8
    python deploy.py --name-prefix m8demo  # custom prefix (max 8 chars)
    python deploy.py --skip-memory         # deploy without Memory (uses SlidingWindow)
    python deploy.py --dry-run             # show what would be created

Output:
    Prints all ARNs and the Memory ID.
    Save the output — you need the Orchestrator ARN + Memory ID to run chat.py.
"""

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_POLL = threading.Event()


def _wait(seconds: int) -> None:
    _POLL.wait(timeout=seconds)

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION  = "us-east-1"
MODULE  = "m8-capstone"
HERE    = Path(__file__).parent


# ── Memory helpers ─────────────────────────────────────────────────────────────

def create_memory(ctl, prefix: str) -> str:
    """Create an AgentCore Memory resource and wait for it to become ACTIVE.

    Memory name must match [a-zA-Z][a-zA-Z0-9_]{0,47}.
    eventExpiryDuration: STM events are kept for this many days before expiry.
    memoryStrategies: SEMANTIC strategy extracts facts into LTM under /facts/{actorId}.
    """
    memory_name = f"{prefix}CapstoneMemory"
    print(f"  Creating Memory: {memory_name} ...")
    resp = ctl.create_memory(
        name=memory_name,
        description=(
            "Multi-turn conversation memory for the Capstone multi-runtime demo. "
            "STM stores conversation events; SEMANTIC strategy extracts user facts into LTM."
        ),
        eventExpiryDuration=30,   # keep STM events for 30 days
        memoryStrategies=[
            {
                "semanticMemoryStrategy": {
                    "name": f"{prefix}UserFacts",
                    # {actorId} is resolved at runtime to the caller's actor ID
                    "namespaces": ["/facts/{actorId}"],
                }
            }
        ],
    )
    memory_id = resp["memory"]["id"]
    print(f"  Memory id: {memory_id}  (waiting for ACTIVE...)")

    # Poll until ACTIVE (typically < 60 s)
    for _ in range(30):
        status = ctl.get_memory(memoryId=memory_id)["memory"]["status"]
        if status == "ACTIVE":
            print(f"  Memory ACTIVE: {memory_id}")
            return memory_id
        if status in ("FAILED", "DELETE_FAILED"):
            raise RuntimeError(f"Memory reached terminal status: {status}")
        _wait(10)
    raise TimeoutError("Memory did not become ACTIVE in 5 minutes")


def delete_memory(ctl, memory_id: str):
    """Delete a Memory resource and wait until gone."""
    print(f"  Deleting Memory {memory_id} ...")
    try:
        ctl.delete_memory(memoryId=memory_id)
    except ctl.exceptions.ResourceNotFoundException:
        print(f"  Memory {memory_id} already deleted.")
        return
    for _ in range(30):
        try:
            ctl.get_memory(memoryId=memory_id)
            _wait(10)
        except ctl.exceptions.ResourceNotFoundException:
            print(f"  Memory {memory_id} deleted.")
            return
    print(f"  Warning: timed out waiting for Memory deletion.")


# ── Specialist deployment ──────────────────────────────────────────────────────

def _deploy_specialist(session, bucket, account, name, folder):
    """Deploy one specialist runtime (no Memory needed — stateless tools)."""
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    role_arn = u.ensure_runtime_role(
        iam, f"agentcore-{name.replace('_', '-')}-role", account, REGION, bucket
    )
    s3_key = u.upload_code(s3, bucket, MODULE, name, u.zip_folder(folder))
    print(f"  [{name}] uploaded → s3://{bucket}/{s3_key}")

    runtime_id, _ = u.create_runtime(ctl, name, bucket, s3_key, role_arn)
    print(f"  [{name}] creating {runtime_id} ...")
    runtime_arn = u.wait_ready(ctl, runtime_id)
    print(f"  [{name}] READY: {runtime_arn}")
    return name, runtime_id, runtime_arn


# ── Orchestrator IAM (needs Memory + InvokeAgentRuntime) ──────────────────────

def ensure_orchestrator_role(iam, role_name: str, account: str, bucket: str,
                              memory_id: str = None) -> str:
    """Create IAM role for the Orchestrator runtime.

    Permissions beyond the default specialist role:
      - bedrock-agentcore:InvokeAgentRuntime  — to call specialist runtimes
      - bedrock-agentcore Memory data-plane    — to read/write conversation events
    """
    import json

    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    })
    try:
        return iam.get_role(RoleName=role_name)["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    role_arn = iam.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=trust,
        Description="Orchestrator runtime role: Bedrock inference + invoke specialists + Memory",
    )["Role"]["Arn"]

    statements = [
        # Bedrock model inference
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                f"arn:aws:bedrock:*:{account}:inference-profile/*",
                "arn:aws:bedrock:*::inference-profile/*",
            ],
        },
        # CloudWatch Logs
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                       "logs:DescribeLogGroups", "logs:PutLogEvents"],
            "Resource": f"arn:aws:logs:{REGION}:{account}:log-group:/aws/bedrock-agentcore/*",
        },
        # S3 — code bundle
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
        },
        # Call specialist runtimes
        {
            "Effect": "Allow",
            "Action": "bedrock-agentcore:InvokeAgentRuntime",
            "Resource": f"arn:aws:bedrock-agentcore:{REGION}:{account}:runtime/*",
        },
    ]

    if memory_id:
        # AgentCore Memory data-plane permissions for STM + LTM operations
        statements.append({
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:GetEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:DeleteEvent",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:ListMemoryRecords",
                "bedrock-agentcore:GetMemoryRecord",
            ],
            "Resource": f"arn:aws:bedrock-agentcore:{REGION}:{account}:memory/{memory_id}",
        })

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="orchestrator-runtime-policy",
        PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}),
    )
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
    )
    _wait(12)
    return role_arn


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Capstone multi-runtime app to AgentCore"
    )
    parser.add_argument("--name-prefix", default="m8",
                        help="Short prefix for runtime/memory names, ≤8 chars (default: m8)")
    parser.add_argument("--skip-memory", action="store_true",
                        help="Deploy without AgentCore Memory (uses in-container SlidingWindow)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created without creating anything")
    args = parser.parse_args()
    prefix = args.name_prefix[:8]

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    if args.dry_run:
        print(f"Dry run (prefix={prefix}, account={account})")
        if not args.skip_memory:
            print(f"  would create Memory: {prefix}CapstoneMemory")
        for name in [f"{prefix}_researcher", f"{prefix}_analyzer",
                     f"{prefix}_criticref", f"{prefix}_orchestrator"]:
            print(f"  would create runtime: {name}  (len={len(name)})")
        return

    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3c = session.client("s3",                        region_name=REGION)

    u.ensure_s3_bucket(s3c, bucket)
    print(f"Code bucket: s3://{bucket}\n")

    # ── Step 1: AgentCore Memory ───────────────────────────────────────────────
    memory_id = None
    if not args.skip_memory:
        print("=== Step 1: Create AgentCore Memory ===")
        memory_id = create_memory(ctl, prefix)
        print()

    # ── Step 2: Specialist runtimes (parallel) ────────────────────────────────
    print("=== Step 2: Deploy specialists in parallel ===")
    specialists_root = HERE / "specialists"
    critic_name = f"{prefix}_criticref"
    specialist_defs = [
        (f"{prefix}_researcher", specialists_root / "researcher"),
        (f"{prefix}_analyzer",   specialists_root / "analyzer"),
        (critic_name,            specialists_root / "critic_refiner"),
    ]
    arns: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_deploy_specialist, session, bucket, account, name, folder): name
            for name, folder in specialist_defs
        }
        for future in as_completed(futures):
            name, _, runtime_arn = future.result()
            arns[name] = runtime_arn
    print()

    # ── Step 3: Orchestrator runtime ──────────────────────────────────────────
    print("=== Step 3: Deploy orchestrator ===")
    orch_name     = f"{prefix}_orchestrator"
    orch_role_name = f"agentcore-{prefix}-orchestrator-role"
    orch_role_arn  = ensure_orchestrator_role(iam, orch_role_name, account, bucket, memory_id)

    orch_zip = u.zip_folder(HERE / "orchestrator")
    orch_key = u.upload_code(s3c, bucket, MODULE, orch_name, orch_zip)
    print(f"  [{orch_name}] uploaded → s3://{bucket}/{orch_key}")

    env_vars = {
        "RESEARCHER_RUNTIME_ARN":     arns[f"{prefix}_researcher"],
        "ANALYZER_RUNTIME_ARN":       arns[f"{prefix}_analyzer"],
        "CRITIC_REFINER_RUNTIME_ARN": arns[critic_name],
    }
    if memory_id:
        env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] = memory_id

    orch_id, _ = u.create_runtime(ctl, orch_name, bucket, orch_key, orch_role_arn,
                                   env_vars=env_vars)
    print(f"  [{orch_name}] creating {orch_id} ...")
    orch_arn = u.wait_ready(ctl, orch_id)
    print(f"  [{orch_name}] READY: {orch_arn}")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=" * 60)
    print("Deployment complete!")
    print()
    if memory_id:
        print(f"Memory ID:        {memory_id}")
    print(f"Orchestrator ARN: {orch_arn}")
    print()
    print("Specialist ARNs:")
    for name, arn in arns.items():
        print(f"  {name}: {arn}")
    print()
    print("To start a multi-turn conversation:")
    print(f"  python chat.py --actor-id <your-user-id> --runtime-arn {orch_arn}")
    print()
    print("To clean up all resources:")
    print(f"  python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
