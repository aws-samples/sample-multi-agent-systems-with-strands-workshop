"""
Deploy Module 3: Sequential Chain — 1 AgentCore Runtime.

Pattern: Researcher → Analyst → Synthesizer (Python passes strings).
All three agents run inside ONE Runtime container.

Usage:
    python deploy.py
    python deploy.py --name-prefix m3ws
    python deploy.py --dry-run

Output:
    Prints the Runtime ARN. Pass it to invoke.py.
"""

import argparse
import sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = "us-east-1"
MODULE = "m3-sequential-chain"
HERE   = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Module 3 Sequential Chain to AgentCore"
    )
    parser.add_argument("--name-prefix", default="m3",
                        help="Runtime name prefix, ≤23 chars (default: m3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created without creating anything")
    args = parser.parse_args()
    prefix = args.name_prefix[:20]
    runtime_name = f"{prefix}_seqchain"

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

    role_name = f"agentcore-{prefix}-seqchain-role"
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
