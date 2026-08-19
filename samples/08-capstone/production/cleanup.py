"""
Cleanup Module 8: Capstone — delete all AgentCore resources.

Deletes (in order):
  1. 4 AgentCore Runtimes (researcher, analyzer, criticref, orchestrator)
  2. 4 IAM roles
  3. AgentCore Memory resource (if it exists)
  4. S3 code objects for this module

Usage:
    python cleanup.py --name-prefix m8
    python cleanup.py --name-prefix m8 --dry-run
    python cleanup.py --name-prefix m8 --skip-memory   # keep Memory for reuse
"""

import argparse
import sys
import time
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = "us-east-1"
MODULE = "m8-capstone"


def _delete_memory(ctl, memory_name_prefix: str):
    """Find and delete Memory resources whose id starts with memory_name_prefix.

    Note: list_memories does NOT return 'name' — only 'id', 'arn', 'status'.
    Memory IDs follow the pattern <name>-<random> so we match on the id prefix.
    """
    paginator_kwargs = {}
    while True:
        resp = ctl.list_memories(**paginator_kwargs)
        for mem in resp.get("memories", []):
            # id format: "<memoryName>-<10-char-suffix>", e.g. "m8CapstoneMemory-Rql8phGFkO"
            if mem.get("id", "").startswith(memory_name_prefix):
                mid = mem["id"]
                print(f"  Deleting Memory {mid} ...")
                try:
                    ctl.delete_memory(memoryId=mid)
                    # Wait for deletion
                    for _ in range(30):
                        try:
                            ctl.get_memory(memoryId=mid)
                            time.sleep(10)
                        except ctl.exceptions.ResourceNotFoundException:
                            print(f"  Memory {mid} deleted.")
                            break
                except ctl.exceptions.ResourceNotFoundException:
                    print(f"  Memory {mid} already deleted.")
        token = resp.get("nextToken")
        if not token:
            break
        paginator_kwargs = {"nextToken": token}


def main():
    parser = argparse.ArgumentParser(description="Delete Module 8 AgentCore resources")
    parser.add_argument("--name-prefix", required=True,
                        help="Prefix used when deploying (e.g. m8)")
    parser.add_argument("--skip-memory", action="store_true",
                        help="Keep the AgentCore Memory resource (useful if reusing across deployments)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()
    prefix = args.name_prefix[:8]

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    # Runtime names use underscores; IAM names use dashes
    runtime_names = [
        f"{prefix}_researcher",
        f"{prefix}_analyzer",
        f"{prefix}_criticref",
        f"{prefix}_orchestrator",
    ]
    role_names = [f"agentcore-{n.replace('_', '-')}-role" for n in runtime_names[:-1]]
    role_names.append(f"agentcore-{prefix}-orchestrator-role")

    print(f"\nCleanup for prefix '{prefix}' in account {account}")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN] Would delete:")
        for name in runtime_names:
            print(f"  runtime:  {name}")
        for role in role_names:
            print(f"  IAM role: {role}")
        if not args.skip_memory:
            print(f"  Memory:   name starts with '{prefix}CapstoneMemory'")
        print(f"  S3:       s3://{bucket}/{MODULE}/")
        return

    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    existing = u.list_all_runtimes(ctl)

    print("\n--- Runtimes ---")
    for name in runtime_names:
        if name in existing:
            rt_id = existing[name]
            print(f"  Deleting {name} ({rt_id}) ...")
            u.delete_runtime(ctl, rt_id)
            print(f"  Deleted: {name}")
        else:
            print(f"  Not found (already deleted?): {name}")

    print("\n--- IAM roles ---")
    for role in role_names:
        print(f"  Deleting {role} ...")
        u.delete_role(iam, role)
        print(f"  Deleted: {role}")

    if not args.skip_memory:
        print("\n--- AgentCore Memory ---")
        _delete_memory(ctl, f"{prefix}CapstoneMemory")
    else:
        print("\n--- AgentCore Memory (skipped — --skip-memory) ---")

    print("\n--- S3 objects ---")
    for name in runtime_names:
        u.delete_s3_prefix(s3, bucket, f"{MODULE}/{name}/")
    print(f"  Deleted all objects under s3://{bucket}/{MODULE}/")

    print("\nCleanup complete.")
    print(f"Verify: aws bedrock-agentcore-control list-agent-runtimes --region {REGION}")
    if not args.skip_memory:
        print(f"        aws bedrock-agentcore-control list-memories --region {REGION}")


if __name__ == "__main__":
    main()
