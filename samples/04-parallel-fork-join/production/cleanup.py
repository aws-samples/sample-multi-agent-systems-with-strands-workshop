"""
Cleanup Module 4: Parallel Fork-Join — delete all AgentCore resources.

Deletes:
  - 3 runtimes: {prefix}_researcher, _analyzer, _synthesizer
  - 1 IAM role: workshop-agentcore-{prefix}-runtime-role
  - S3 objects under m4-parallel-fork-join/

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

REGION = u.REGION
MODULE = "m4-parallel-fork-join"


def main():
    parser = argparse.ArgumentParser(description="Delete Module 4 AgentCore resources")
    parser.add_argument("--name-prefix", required=True,
                        help="Prefix used when deploying (e.g. m4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()
    prefix = args.name_prefix[:8]

    runtime_names = [
        f"{prefix}_researcher",
        f"{prefix}_analyzer",
        f"{prefix}_synthesizer",
    ]
    role_names = [
        f"workshop-agentcore-{prefix}-runtime-role",
    ]

    if args.dry_run:
        print("[DRY RUN] Would delete:")
        for name in runtime_names:
            print(f"  runtime:  {name}")
        for role in role_names:
            print(f"  IAM role: {role}")
        print(f"  S3:       s3://bedrock-agentcore-deploy-<ACCOUNT>-{REGION}/{MODULE}/")
        return

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    print(f"\nCleanup for prefix '{prefix}' in account {account}")
    print("=" * 60)

    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    existing = u.list_all_runtimes(ctl)

    print("\n--- Runtimes ---")
    for name in runtime_names:
        if name in existing:
            print(f"  Deleting {name} ({existing[name]})...")
            u.delete_runtime(ctl, existing[name])
            print(f"  Deleted: {name}")
        else:
            print(f"  Not found (already deleted?): {name}")

    print("\n--- IAM roles ---")
    for role in role_names:
        print(f"  Deleting {role}...")
        u.delete_role(iam, role)
        print(f"  Deleted: {role}")

    print("\n--- S3 objects ---")
    for name in runtime_names:
        u.delete_s3_prefix(s3, bucket, f"{MODULE}/{name}/")
    print(f"  Deleted objects under s3://{bucket}/{MODULE}/")

    print("\nCleanup complete.")
    print(f"Verify: aws bedrock-agentcore-control list-agent-runtimes --region {REGION}")


if __name__ == "__main__":
    main()
