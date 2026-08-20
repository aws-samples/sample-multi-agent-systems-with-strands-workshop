"""
Shared utilities for boto3-based AgentCore Runtime deployment.

Used by deploy.py and cleanup.py in multi-runtime modules (03-08).
API-verified: create_agent_runtime with codeConfiguration, PYTHON_3_13, PUBLIC network.

IAM role resolution order (for ensure_runtime_role):
  1. AGENTCORE_RUNTIME_ROLE_ARN / AGENTCORE_ORCHESTRATOR_ROLE_ARN env var
  2. iam:GetRole by role_name (role pre-exists from workshop setup or prior run)
  3. iam:CreateRole (requires iam:CreateRole — works in self-paced / full-permission accounts)

Workshop Studio: set AGENTCORE_RUNTIME_ROLE_ARN and AGENTCORE_ORCHESTRATOR_ROLE_ARN
to pre-created role ARNs so deploy.py never needs iam:CreateRole.
"""
import io, json, os, tempfile, threading, time, zipfile
from pathlib import Path

import boto3
import botocore.exceptions

# Serialize pip calls across threads — pip._internal is not thread-safe
_PIP_LOCK = threading.Lock()

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Threading event used only as a timeout-based wait primitive in polling loops.
# It is never set, so wait() always blocks until the timeout expires.
_POLL = threading.Event()


def _wait(seconds: int) -> None:
    _POLL.wait(timeout=seconds)


def get_session() -> boto3.Session:
    profile = os.environ.get("AWS_PROFILE")
    kwargs = {"region_name": REGION}
    if profile:
        kwargs["profile_name"] = profile
    return boto3.Session(**kwargs)


def get_account(session: boto3.Session) -> str:
    return session.client("sts").get_caller_identity()["Account"]


def code_bucket_name(account: str, region: str = REGION) -> str:
    return f"bedrock-agentcore-deploy-{account}-{region}"


def ensure_s3_bucket(s3_client, bucket: str) -> str:
    """Get or create the code bucket. Block-public-access and SSE-S3 are AWS
    defaults for all new buckets since 2023 — no explicit calls needed."""
    try:
        s3_client.head_bucket(Bucket=bucket)
    except Exception:
        s3_client.create_bucket(Bucket=bucket)
        print(f"  Created S3 bucket: {bucket}")
    return bucket


def zip_folder(folder: Path) -> bytes:
    """Zip folder + bundle requirements.txt dependencies for codeConfiguration deploy.

    codeConfiguration does not install requirements at runtime — all packages must be
    bundled in the ZIP. Packages are installed into a temp dir and placed at the ZIP root
    so they are importable from /var/task/ (the Lambda-style working directory).
    Source files overwrite any conflicting package files.
    """
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmpdir:
        req = folder / "requirements.txt"
        if req.exists():
            from pip._internal.cli.main import main as _pip_main
            with _PIP_LOCK:
                exit_code = _pip_main([
                    "install", "-r", str(req),
                    "-t", tmpdir,
                    "--platform", "manylinux2014_aarch64",
                    "--python-version", "3.13",
                    "--only-binary=:all:",
                    "--quiet", "--no-warn-script-location",
                ])
            if exit_code != 0:
                raise RuntimeError(f"pip install (Linux ARM64) failed for {folder}")

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            # Add installed packages first
            for f in sorted(Path(tmpdir).rglob("*")):
                if f.is_file() and "__pycache__" not in str(f) and not f.name.endswith(".pyc"):
                    z.write(f, f.relative_to(tmpdir))
            # Source files go last (overwrite any collisions)
            for f in sorted(folder.rglob("*")):
                if f.is_file() and "__pycache__" not in str(f) and not f.name.endswith(".pyc"):
                    z.write(f, f.relative_to(folder))

    buf.seek(0)
    return buf.getvalue()


def upload_code(s3_client, bucket: str, module: str, runtime_name: str, zip_bytes: bytes) -> str:
    """Upload ZIP to S3, return the full object key (used as prefix in codeConfiguration)."""
    key = f"{module}/{runtime_name}/code.zip"
    s3_client.put_object(Bucket=bucket, Key=key, Body=zip_bytes)
    return key


def ensure_runtime_role(
    iam_client,
    role_name: str,
    account: str,
    region: str,
    bucket: str,
    can_invoke_runtimes: bool = False,
    specialist_arns: list = None,
    memory_id: str = None,
) -> str:
    """Get or create an IAM execution role for an AgentCore runtime.

    Resolution order:
      1. AGENTCORE_ORCHESTRATOR_ROLE_ARN / AGENTCORE_RUNTIME_ROLE_ARN env var
         (workshop pre-created role — no IAM calls needed)
      2. iam:GetRole by role_name (role already exists from a previous run)
      3. iam:CreateRole (requires iam:CreateRole permission)

    can_invoke_runtimes=True adds bedrock-agentcore:InvokeAgentRuntime.
    memory_id adds AgentCore Memory data-plane permissions for that memory resource.
    """
    # 1. Env var override — no IAM calls needed (workshop pre-created roles)
    env_var = "AGENTCORE_ORCHESTRATOR_ROLE_ARN" if can_invoke_runtimes else "AGENTCORE_RUNTIME_ROLE_ARN"
    env_arn = os.environ.get(env_var)
    if env_arn:
        return env_arn

    # 2. Role may already exist (workshop setup or prior deploy run)
    try:
        return iam_client.get_role(RoleName=role_name)["Role"]["Arn"]
    except iam_client.exceptions.NoSuchEntityException:
        pass

    # 3. Create the role
    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    })
    try:
        role_arn = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust,
            Description="Execution role for AgentCore Runtime",
        )["Role"]["Arn"]
    except botocore.exceptions.ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied" or "iam:CreateRole" in str(e):
            raise RuntimeError(
                f"\nCannot create IAM role '{role_name}': permission denied.\n\n"
                f"To fix this, set the {env_var} environment variable to a pre-existing\n"
                f"role ARN that trusts bedrock-agentcore.amazonaws.com:\n\n"
                f"  export {env_var}=arn:aws:iam::{account}:role/YOUR_ROLE_NAME\n\n"
                f"The role needs these permissions:\n"
                f"  bedrock:InvokeModel, bedrock:InvokeModelWithResponseStream\n"
                f"  logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents\n"
                f"  s3:GetObject, s3:ListBucket on {bucket}\n"
                + ("  bedrock-agentcore:InvokeAgentRuntime\n" if can_invoke_runtimes else "")
            ) from e
        raise

    statements = [
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                f"arn:aws:bedrock:*:{account}:inference-profile/*",
                "arn:aws:bedrock:*::inference-profile/*",
            ],
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup", "logs:CreateLogStream",
                "logs:DescribeLogGroups", "logs:PutLogEvents",
            ],
            "Resource": f"arn:aws:logs:{region}:{account}:log-group:/aws/bedrock-agentcore/*",
        },
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
        },
    ]
    if can_invoke_runtimes:
        resource = specialist_arns if specialist_arns else f"arn:aws:bedrock-agentcore:{region}:{account}:runtime/*"
        statements.append({
            "Effect": "Allow",
            "Action": "bedrock-agentcore:InvokeAgentRuntime",
            "Resource": resource,
        })
    if memory_id:
        statements.append({
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:GetEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:DeleteEvent",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:ListMemoryRecords",
                "bedrock-agentcore:GetMemoryRecord",
            ],
            "Resource": f"arn:aws:bedrock-agentcore:{region}:{account}:memory/{memory_id}",
        })

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="agentcore-runtime-policy",
        PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}),
    )
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
    )

    _wait(12)
    return role_arn


def create_runtime(
    ctl_client,
    name: str,
    bucket: str,
    s3_key: str,
    role_arn: str,
    env_vars: dict = None,
    protocol: str = "HTTP",
) -> tuple:
    """Create an AgentCore runtime. Returns (runtime_id, runtime_arn).

    Args:
        protocol: "HTTP" (default, port 8080, BedrockAgentCoreApp) or
                  "A2A"  (port 9000, serve_a2a, JSON-RPC 2.0).
        See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
    """
    kwargs = dict(
        agentRuntimeName=name,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": bucket, "prefix": s3_key}},
                "runtime": "PYTHON_3_13",
                "entryPoint": ["main.py"],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
    )
    if env_vars:
        kwargs["environmentVariables"] = env_vars
    if protocol != "HTTP":
        kwargs["protocolConfiguration"] = {"serverProtocol": protocol}
    resp = ctl_client.create_agent_runtime(**kwargs)
    return resp["agentRuntimeId"], resp["agentRuntimeArn"]


def wait_ready(ctl_client, runtime_id: str, timeout: int = 600) -> str:
    """Poll until runtime status is READY. Returns runtime ARN."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = ctl_client.get_agent_runtime(agentRuntimeId=runtime_id)
        status = info["status"]
        if status == "READY":
            return info["agentRuntimeArn"]
        if status in ("FAILED", "DELETE_FAILED", "CREATE_FAILED"):
            reason = info.get("failureReason", "")
            raise RuntimeError(f"Runtime {runtime_id} status={status}. {reason}")
        _wait(10)
    raise TimeoutError(f"Runtime {runtime_id} did not reach READY in {timeout}s")


def list_all_runtimes(ctl_client) -> dict:
    """Return {name: id} for all runtimes, handling pagination."""
    result = {}
    kwargs = {}
    while True:
        resp = ctl_client.list_agent_runtimes(**kwargs)
        for rt in resp.get("agentRuntimes", []):
            result[rt["agentRuntimeName"]] = rt["agentRuntimeId"]
        token = resp.get("nextToken")
        if not token:
            break
        kwargs = {"nextToken": token}
    return result


def delete_runtime(ctl_client, runtime_id: str):
    """Delete a runtime (the service cleans up its endpoint automatically)."""
    try:
        ctl_client.delete_agent_runtime(agentRuntimeId=runtime_id)
    except ctl_client.exceptions.ResourceNotFoundException:
        pass


def delete_role(iam_client, role_name: str):
    """Detach all policies and delete an IAM role."""
    try:
        for p in iam_client.list_role_policies(RoleName=role_name)["PolicyNames"]:
            iam_client.delete_role_policy(RoleName=role_name, PolicyName=p)
        for p in iam_client.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]:
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=p["PolicyArn"])
        iam_client.delete_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException:
        pass


def delete_s3_prefix(s3_client, bucket: str, prefix: str):
    """Delete all S3 objects under a prefix."""
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            s3_client.delete_object(Bucket=bucket, Key=obj["Key"])
