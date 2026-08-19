"""
Deploy Module 8: Capstone — 4 AgentCore Runtimes.

Architecture:
  researcher    ─┐
  analyzer      ─┤ (deployed in parallel, independent)
  critic_refiner─┘
        ↓  ARNs injected as env vars
  orchestrator   (deployed after specialists are READY)

The orchestrator reads RESEARCHER_RUNTIME_ARN, ANALYZER_RUNTIME_ARN,
CRITIC_REFINER_RUNTIME_ARN from its environment at startup.

Usage:
    python deploy.py
    python deploy.py --name-prefix m8ws
    python deploy.py --dry-run
"""
import argparse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SHARED = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED))
import deploy_utils as u

REGION  = "us-east-1"
MODULE  = "m8-capstone"
HERE    = Path(__file__).parent


def _deploy_one_specialist(session, bucket, account, name, folder):
    """Deploy a single specialist runtime. Runs concurrently with others."""
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3  = session.client("s3",                        region_name=REGION)

    role_arn = u.ensure_runtime_role(iam, f"agentcore-{name.replace('_', '-')}-role", account, REGION, bucket)
    s3_key   = u.upload_code(s3, bucket, MODULE, name, u.zip_folder(folder))
    print(f"  [{name}] uploaded → s3://{bucket}/{s3_key}")

    runtime_id, _ = u.create_runtime(ctl, name, bucket, s3_key, role_arn)
    print(f"  [{name}] creating {runtime_id}...")
    runtime_arn = u.wait_ready(ctl, runtime_id)
    print(f"  [{name}] READY: {runtime_arn}")
    return name, runtime_id, runtime_arn


def main():
    parser = argparse.ArgumentParser(description="Deploy Module 8 Capstone to AgentCore")
    parser.add_argument("--name-prefix", default="m8",
                        help="Short prefix for runtime names, ≤8 chars (default: m8)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deployed without creating anything")
    args = parser.parse_args()
    prefix = args.name_prefix[:8]

    session = u.get_session()
    account = u.get_account(session)
    bucket  = u.code_bucket_name(account, REGION)

    if args.dry_run:
        print(f"Dry run (prefix={prefix}, account={account})")
        names = [f"{prefix}-researcher", f"{prefix}-analyzer",
                 f"{prefix}-criticref", f"{prefix}-orchestrator"]
        for n in names:
            print(f"  would create runtime: {n}  (len={len(n)})")
        return

    s3_client = session.client("s3", region_name=REGION)
    u.ensure_s3_bucket(s3_client, bucket)
    print(f"Code bucket: s3://{bucket}\n")

    specialists_root = HERE / "specialists"
    # Runtime names: only [a-zA-Z][a-zA-Z0-9_] allowed — use underscores, not dashes
    researcher_name   = f"{prefix}_researcher"
    analyzer_name     = f"{prefix}_analyzer"
    # critic_refiner truncated to fit within 23-char AgentCore name limit
    critic_name       = f"{prefix}_criticref"
    orch_name         = f"{prefix}_orchestrator"

    specialist_defs = [
        (researcher_name, specialists_root / "researcher"),
        (analyzer_name,   specialists_root / "analyzer"),
        (critic_name,     specialists_root / "critic_refiner"),
    ]

    print("=== Step 1: Deploy specialists in parallel ===")
    arns: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_deploy_one_specialist, session, bucket, account, name, folder): name
            for name, folder in specialist_defs
        }
        for future in as_completed(futures):
            name, _, runtime_arn = future.result()
            arns[name] = runtime_arn

    print("\n=== Step 2: Deploy orchestrator ===")
    ctl = session.client("bedrock-agentcore-control", region_name=REGION)
    iam = session.client("iam",                       region_name=REGION)
    s3c = session.client("s3",                        region_name=REGION)

    orch_role = u.ensure_runtime_role(
        iam, f"agentcore-{prefix}-orchestrator-role", account, REGION, bucket,
        can_invoke_runtimes=True,   # orchestrator calls specialist runtimes
    )
    orch_key = u.upload_code(s3c, bucket, MODULE, orch_name, u.zip_folder(HERE / "orchestrator"))
    print(f"  [{orch_name}] uploaded → s3://{bucket}/{orch_key}")

    orch_id, _ = u.create_runtime(
        ctl, orch_name, bucket, orch_key, orch_role,
        env_vars={
            "RESEARCHER_RUNTIME_ARN":     arns[researcher_name],
            "ANALYZER_RUNTIME_ARN":       arns[analyzer_name],
            "CRITIC_REFINER_RUNTIME_ARN": arns[critic_name],
        },
    )
    print(f"  [{orch_name}] creating {orch_id}...")
    orch_arn = u.wait_ready(ctl, orch_id)
    print(f"  [{orch_name}] READY: {orch_arn}")

    print("\n=== Deployment complete ===")
    print(f"Orchestrator ARN (pass to invoke.py):")
    print(f"  {orch_arn}")
    print(f"\nAll runtimes:")
    for n, a in arns.items():
        print(f"  {n}: {a}")
    print(f"  {orch_name}: {orch_arn}")
    print(f"\nInvoke:  python invoke.py {orch_arn}")
    print(f"Cleanup: python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
