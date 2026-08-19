"""
Deploy Module 5: Critic-Refiner — 1 AgentCore Runtime.

Pattern: Researcher → Writer ↔ Critic (GraphBuilder quality loop).
All agents run inside ONE Runtime container.

Usage:
    python deploy.py
    python deploy.py --name-prefix m5ws
    python deploy.py --dry-run
"""

import argparse
import sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = "us-east-1"
MODULE = "m5-critic-refiner"
HERE   = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Module 5 Critic-Refiner to AgentCore"
    )
    parser.add_argument("--name-prefix", default="m5",
                        help="Runtime name prefix, ≤20 chars (default: m5)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    prefix = args.name_prefix[:20]
    runtime_name = f"{prefix}_critic"

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    if args.dry_run:
        print(f"Dry run (prefix={prefix}, account={account})")
        print(f"  would create runtime: {runtime_name}  (len={len(runtime_name)})")
        return

    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    u.ensure_s3_bucket(s3, bucket)
    print(f"Code bucket: s3://{bucket}\n")

    role_name = f"agentcore-{prefix}-critic-role"
    role_arn  = u.ensure_runtime_role(iam, role_name, account, REGION, bucket)

    s3_key = u.upload_code(s3, bucket, MODULE, runtime_name, u.zip_folder(HERE))
    print(f"Uploaded: s3://{bucket}/{s3_key}")

    runtime_id, _ = u.create_runtime(ctl, runtime_name, bucket, s3_key, role_arn)
    print(f"Creating {runtime_id} ...")
    runtime_arn = u.wait_ready(ctl, runtime_id)
    print(f"READY: {runtime_arn}")

    print(f"\nInvoke:  python invoke.py {runtime_arn}")
    print(f"Cleanup: python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
