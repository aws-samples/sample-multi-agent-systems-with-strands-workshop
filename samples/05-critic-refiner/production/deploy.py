"""
Deploy Module 5: Critic-Refiner — 2 A2A specialist runtimes.

Architecture:
  writer   — Generator: produces/revises the memo (A2A, port 9000)
  critic   — Evaluates the memo: APPROVED or REVISION NEEDED (A2A, port 9000)

The Generator↔Critic loop is coordinated locally by chain.py.
Context is passed explicitly in each A2A call — no shared in-process memory needed.

AWS AgentCore A2A: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html

IAM role (created once per prefix):
  workshop-agentcore-{prefix}-runtime-role  — A2A specialists (Bedrock, Logs, S3)

Override with env var:
  AGENTCORE_RUNTIME_ROLE_ARN

Usage: python deploy.py [--name-prefix m5] [--dry-run]
"""
import argparse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION = u.REGION
MODULE = "m5-critic-refiner"
HERE   = Path(__file__).parent


def _deploy_specialist(session, bucket, account, prefix, name, folder):
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam", region_name=REGION)
    s3  = session.client("s3",  region_name=REGION)
    role_arn = u.ensure_runtime_role(iam, f"workshop-agentcore-{prefix}-runtime-role", account, REGION, bucket)
    s3_key   = u.upload_code(s3, bucket, MODULE, name, u.zip_folder(folder))
    print(f"  [{name}] uploaded")
    runtime_id, _ = u.create_runtime(ctl, name, bucket, s3_key, role_arn, protocol="A2A")
    print(f"  [{name}] creating A2A runtime...")
    runtime_arn = u.wait_ready(ctl, runtime_id)
    print(f"  [{name}] READY: {runtime_arn}")
    return name, runtime_id, runtime_arn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name-prefix", default="m5", help="Runtime prefix, max 8 chars")
    parser.add_argument("--dry-run", action="store_true")
    args   = parser.parse_args()
    prefix = args.name_prefix[:8]

    specialists = {s: f"{prefix}_{s}" for s in ['writer', 'critic']}

    if args.dry_run:
        for n in specialists.values():
            print(f"  would create: {n:<25} protocol=A2A")
        return

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam", region_name=REGION)
    s3c = session.client("s3",  region_name=REGION)
    u.ensure_s3_bucket(s3c, bucket)
    print(f"Code bucket: s3://{bucket}\n")

    specialist_defs = [
        (specialists["writer"], HERE / "specialists/writer"),
        (specialists["critic"], HERE / "specialists/critic"),
    ]

    print("=== Deploy A2A specialists in parallel ===")
    arns: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_deploy_specialist, session, bucket, account, prefix, name, folder): name
                   for name, folder in specialist_defs}
        for future in as_completed(futures):
            name, _, arn = future.result()
            arns[name] = arn

    print(f"\n=== Deployment complete ===")
    print(f"Writer ARN: {arns[specialists['writer']]}")
    print(f"Critic ARN: {arns[specialists['critic']]}")

    env_block = (
        f"\nexport WRITER_RUNTIME_ARN={arns[specialists['writer']]}\n"
        f"export CRITIC_RUNTIME_ARN={arns[specialists['critic']]}\n"
    )
    with open(HERE / ".env_arns", "w", encoding="utf-8") as _f:
        _f.write(env_block)

    print(f"\nRun the chain:")
    print(f"  source .env_arns && python chain.py")
    print(f"Cleanup: python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
