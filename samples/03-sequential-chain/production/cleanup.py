"""
Cleanup Module 3: Sequential Chain — delete AgentCore Runtime and IAM role.

Usage:
    python cleanup.py --name-prefix m3
    python cleanup.py --name-prefix m3 --dry-run
"""

import argparse
import sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = "us-east-1"
MODULE = "m3-sequential-chain"


def main():
    parser = argparse.ArgumentParser(description="Delete Module 3 AgentCore Runtime")
    parser.add_argument("--name-prefix", required=True,
                        help="Prefix used when deploying (e.g. m3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()
    prefix = args.name_prefix[:20]

    runtime_name = f"{prefix}_seqchain"
    role_name    = f"agentcore-{prefix}-seqchain-role"

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


# ── Multi-runtime cleanup (4-runtime A2A deployment) ──────────────────────────
# These names are created by the new deploy.py (A2A multi-runtime architecture).
# Run: python cleanup.py --name-prefix m3  (same command, extended to handle both)
# The block below runs after the single-runtime cleanup above.
def _cleanup_multi_runtime(prefix, ctl, iam, s3, bucket, dry_run=False):
    """Delete the 4-runtime A2A deployment created by the new deploy.py."""
    import sys
    from pathlib import Path
    SHARED = Path(__file__).parent.parent.parent / "shared"
    sys.path.insert(0, str(SHARED))
    import deploy_utils as u

    runtime_names = [
        f"{prefix}_researcher",
        f"{prefix}_analyst",
        f"{prefix}_synthesizer",
        f"{prefix}_orchestrator",
    ]
    role_names = [f"agentcore-{n.replace('_', '-')}-role" for n in runtime_names[:-1]]
    role_names.append(f"agentcore-{prefix}-orchestrator-role")

    if dry_run:
        for n in runtime_names:
            print(f"  [dry-run] would delete runtime: {n}")
        return

    existing = u.list_all_runtimes(ctl)
    for name in runtime_names:
        if name in existing:
            print(f"  Deleting {name}...")
            u.delete_runtime(ctl, existing[name])
            print(f"  Deleted: {name}")

    for role in role_names:
        u.delete_role(iam, role)

    for name in runtime_names:
        u.delete_s3_prefix(s3, bucket, f"m3-sequential-chain/{name}/")
    print("  S3 objects deleted.")
