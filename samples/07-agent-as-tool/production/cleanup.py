"""
Cleanup Module 7: Agent-as-Tool — delete all AgentCore Runtimes and IAM roles.

Deletes the 4 runtimes and 4 IAM roles created by deploy.py,
plus the S3 code objects for this module.

Usage:
    python cleanup.py --name-prefix m7
    python cleanup.py --name-prefix m7 --dry-run
"""
import argparse, sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = u.REGION
MODULE = "m7-agent-as-tool"


def main():
    parser = argparse.ArgumentParser(description="Delete Module 7 AgentCore Runtimes")
    parser.add_argument("--name-prefix", required=True,
                        help="Prefix used when deploying (e.g. m7)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()
    prefix = args.name_prefix[:8]

    runtime_names = [
        f"{prefix}_researcher",
        f"{prefix}_analyst",
        f"{prefix}_synthesizer",
        f"{prefix}_orchestrator",
    ]
    role_names = [
        f"workshop-agentcore-{prefix}-runtime-role",
        f"workshop-agentcore-{prefix}-orchestrator-role",
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
            rt_id = existing[name]
            print(f"  Deleting {name} ({rt_id})...")
            u.delete_runtime(ctl, rt_id)
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
    print(f"  Deleted all objects under s3://{bucket}/{MODULE}/")

    print("\nCleanup complete.")
    print(f"Verify: aws bedrock-agentcore-control list-agent-runtimes --region {REGION}")


if __name__ == "__main__":
    main()
