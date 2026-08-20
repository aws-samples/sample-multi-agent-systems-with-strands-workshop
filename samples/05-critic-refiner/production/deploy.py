"""
Deploy Module 5: Critic-Refiner — 1 A2A specialist runtime.

Architecture:
  critic_refiner  — A2A specialist (port 9000, serve_a2a)
                    Contains the Writer↔Critic GraphBuilder loop internally.

No orchestrator runtime is deployed. The specialist is called directly
by chain.py using A2AAgent.

AWS AgentCore A2A: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html

IAM role (created once per prefix):
  workshop-agentcore-{prefix}-runtime-role  — A2A specialist (Bedrock, Logs, S3)

Override with env var to skip role creation (workshop environments):
  AGENTCORE_RUNTIME_ROLE_ARN

Usage: python deploy.py [--name-prefix m5] [--dry-run]
"""
import argparse, sys
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = u.REGION
MODULE = "m5-critic-refiner"
HERE   = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name-prefix", default="m5", help="Runtime prefix, max 8 chars")
    parser.add_argument("--dry-run", action="store_true")
    args   = parser.parse_args()
    prefix = args.name_prefix[:8]

    cr_name = f"{prefix}_critic_refiner"

    if args.dry_run:
        print(f"  would create: {cr_name:<25} protocol=A2A")
        return

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam", region_name=REGION)
    s3c = session.client("s3",  region_name=REGION)

    u.ensure_s3_bucket(s3c, bucket)
    print(f"Code bucket: s3://{bucket}\n")

    role_arn = u.ensure_runtime_role(iam, f"workshop-agentcore-{prefix}-runtime-role", account, REGION, bucket)
    s3_key   = u.upload_code(s3c, bucket, MODULE, cr_name, u.zip_folder(HERE / "specialists/critic_refiner"))
    print(f"  [{cr_name}] uploaded")

    runtime_id, _ = u.create_runtime(ctl, cr_name, bucket, s3_key, role_arn, protocol="A2A")
    print(f"  [{cr_name}] creating A2A runtime...")
    cr_arn = u.wait_ready(ctl, runtime_id)
    print(f"  [{cr_name}] READY: {cr_arn}")

    print(f"\n=== Deployment complete ===")
    print(f"Critic-Refiner ARN: {cr_arn}")

    with open(".env_arns", "w", encoding="utf-8") as _f:
        _f.write(f"\nexport CRITIC_REFINER_RUNTIME_ARN={cr_arn}\n")

    print(f"\nRun the chain:")
    print(f"  source .env_arns && python chain.py")
    print(f"Cleanup: python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
