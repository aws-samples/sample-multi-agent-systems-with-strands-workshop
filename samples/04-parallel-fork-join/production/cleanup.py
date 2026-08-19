"""
Cleanup Module 04: Parallel Fork-Join — delete AgentCore Runtime and IAM role.

Usage:
    python cleanup.py --name-prefix m4
    python cleanup.py --name-prefix m4 --dry-run
"""

import argparse
import sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = "us-east-1"
MODULE = "m4-parallel-fork-join"


def main():
    parser = argparse.ArgumentParser(description="Delete Module 04 AgentCore Runtime")
    parser.add_argument("--name-prefix", required=True,
                        help="Prefix used when deploying (e.g. m4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()
    prefix = args.name_prefix[:20]

    runtime_name = f"{prefix}_parallel"
    role_name    = f"agentcore-{prefix}-parallel-role"

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    print(f"\nCleanup for prefix '{prefix}' in account {account}")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN] Would delete:")
        print(f"  runtime:  {runtime_name}")
        print(f"  IAM role: {role_name}")
        print(f"  S3:       s3://{bucket}/{MODULE}/")
        return

    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    existing = u.list_all_runtimes(ctl)

    print("\n--- Runtime ---")
    if runtime_name in existing:
        rt_id = existing[runtime_name]
        print(f"  Deleting {runtime_name} ({rt_id}) ...")
        u.delete_runtime(ctl, rt_id)
        print(f"  Deleted.")
    else:
        print(f"  Not found (already deleted?): {runtime_name}")

    print("\n--- IAM role ---")
    print(f"  Deleting {role_name} ...")
    u.delete_role(iam, role_name)
    print(f"  Deleted.")

    print("\n--- S3 objects ---")
    u.delete_s3_prefix(s3, bucket, f"{MODULE}/{runtime_name}/")
    print(f"  Deleted s3://{bucket}/{MODULE}/{runtime_name}/")

    print("\nCleanup complete.")
    print(f"Verify: aws bedrock-agentcore-control list-agent-runtimes --region {REGION}")


if __name__ == "__main__":
    main()
