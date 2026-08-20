"""
Deploy Module 5: critic-refiner — 3 AgentCore Runtimes with A2A.
Specialists: A2A protocol (port 9000). Orchestrator: HTTP (port 8080).

IAM roles (created once per prefix, reused by all specialists):
  workshop-workshop-agentcore-{prefix}-runtime-role      — A2A specialists
  workshop-agentcore-{prefix}-orchestrator-role — HTTP orchestrator (+ InvokeAgentRuntime)

Override with env vars to skip role creation (workshop environments):
  AGENTCORE_RUNTIME_ROLE_ARN
  AGENTCORE_ORCHESTRATOR_ROLE_ARN

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

    m5_names = {s: f"{prefix}_{s}" for s in ['researcher', 'critic_refiner']}
    orch_name  = f"{prefix}_orchestrator"

    if args.dry_run:
        for n in list(m5_names.values()) + [orch_name]:
            print(f"  would create: {n:<25} protocol={'HTTP' if n == orch_name else 'A2A'}")
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
        (m5_names["researcher"],    HERE / "specialists/researcher"),
        (m5_names["critic_refiner"], HERE / "specialists/critic_refiner"),
    ]

    print("=== Step 1: Deploy A2A specialists in parallel ===")
    arns: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_deploy_specialist, session, bucket, account, prefix, name, folder): name
                   for name, folder in specialist_defs}
        for future in as_completed(futures):
            name, _, arn = future.result()
            arns[name] = arn

    print("\n=== Step 2: Deploy HTTP orchestrator ===")
    orch_role = u.ensure_runtime_role(iam, f"workshop-agentcore-{prefix}-orchestrator-role",
                                       account, REGION, bucket, can_invoke_runtimes=True)
    orch_zip  = u.zip_folder(HERE / "orchestrator")
    orch_key  = u.upload_code(s3c, bucket, MODULE, orch_name, orch_zip)
    print(f"  [{orch_name}] uploaded")
    orch_id, _ = u.create_runtime(ctl, orch_name, bucket, orch_key, orch_role, env_vars={
        "RESEARCHER_RUNTIME_ARN":     arns[m5_names["researcher"]],
        "CRITIC_REFINER_RUNTIME_ARN": arns[m5_names["critic_refiner"]],
    })
    print(f"  [{orch_name}] creating HTTP runtime...")
    orch_arn = u.wait_ready(ctl, orch_id)
    print(f"  [{orch_name}] READY: {orch_arn}")

    print(f"\n=== Deployment complete ===")
    print(f"Orchestrator ARN: {orch_arn}")
    print(f"Invoke:  python invoke.py {orch_arn}")
    print(f"Chat:    python chat.py --actor-id <id> --runtime-arn {orch_arn}")
    print(f"Cleanup: python cleanup.py --name-prefix {prefix}")


if __name__ == "__main__":
    main()
