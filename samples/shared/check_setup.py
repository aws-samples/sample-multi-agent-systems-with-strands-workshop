"""Check that this machine is ready for the workshop.

Run from the repository root before module 02 (or module 01, the optional primer):

    python samples/shared/check_setup.py
    python samples/shared/check_setup.py --model <MODEL_ID>   # if your event enables a different model

Read-only: it checks Python, the Strands SDK, your AWS region and credentials,
and makes one tiny Amazon Bedrock call to the model the samples use.
Exits 0 when everything passes, 1 otherwise.
"""

import argparse
import os
import sys
from importlib import metadata

MIN_PYTHON = (3, 10)
MIN_STRANDS = (1, 65)
SUPPORTED_REGIONS = {"us-east-1", "us-east-2", "us-west-2"}


def ok(msg):
    print(f"  [PASS] {msg}")


def warn(msg):
    print(f"  [WARN] {msg}")


def fail(msg, fix):
    print(f"  [FAIL] {msg}")
    print(f"         Fix: {fix}")
    sys.exit(1)


def check_python():
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Python {sys.version.split()[0]} is too old.",
            "Install Python 3.10 or higher (3.13 recommended).",
        )
    ok(f"Python {sys.version.split()[0]}")


def check_strands():
    install = "pip install -r samples/02-single-agent/requirements.txt"
    try:
        version = metadata.version("strands-agents")
    except metadata.PackageNotFoundError:
        fail("strands-agents is not installed in this Python environment.", install)
    parts = tuple(int(p) for p in version.split(".")[:2] if p.isdigit())
    if parts < MIN_STRANDS:
        fail(f"strands-agents {version} is older than 1.65.", install.replace("-r", "-U -r"))
    ok(f"strands-agents {version}")


def check_region(session):
    region = os.environ.get("AWS_REGION") or session.region_name
    if not region:
        fail(
            "No AWS region set.",
            "export AWS_REGION=<region>   (e.g. us-west-2), or set a region in your AWS CLI profile.",
        )
    if region in SUPPORTED_REGIONS:
        ok(f"Region {region}")
    else:
        warn(
            f"Region {region} is not one the workshop is tested in "
            f"({', '.join(sorted(SUPPORTED_REGIONS))}). Local modules may still work."
        )
    return region


def check_credentials(session, region):
    from botocore.exceptions import ClientError, NoCredentialsError

    try:
        arn = session.client("sts", region_name=region).get_caller_identity()["Arn"]
    except NoCredentialsError:
        fail(
            "No AWS credentials found.",
            "Run `aws configure` or `aws sso login --profile <profile>`, then set AWS_PROFILE, "
            "or export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN.",
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if "Expired" in code:
            fail("Your AWS credentials have expired.", "Refresh them (e.g. `aws sso login`) and retry.")
        fail(f"AWS rejected your credentials ({code}).", "Check AWS_PROFILE and your credential source.")
    # Show only the principal name; no account ID.
    ok(f"AWS credentials: {arn.split(':', 5)[-1]}")


def check_bedrock(session, region, model_id):
    from botocore.exceptions import ClientError

    client = session.client("bedrock-runtime", region_name=region)
    try:
        client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 1},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        detail = e.response["Error"].get("Message", "")
        if code == "ThrottlingException":
            ok(f"Bedrock model {model_id} (throttled, but access works)")
            return
        if code == "AccessDeniedException":
            fail(
                f"Access denied to {model_id}: {detail}",
                "Enable the model in the Bedrock console (Model access), accept any Marketplace "
                "subscription, and make sure your role allows bedrock:InvokeModel.",
            )
        if code in ("ValidationException", "ResourceNotFoundException"):
            fail(
                f"{model_id} is not available in {region}: {detail}",
                "Use a supported region, or pass --model <MODEL_ID> for a model your event enables.",
            )
        fail(f"Bedrock call failed ({code}): {detail}", "See the message above.")
    ok(f"Bedrock model {model_id}")


def main():
    check_python()
    check_strands()

    import boto3
    from botocore.exceptions import ProfileNotFound
    from strands.models.bedrock import DEFAULT_BEDROCK_MODEL_ID

    parser = argparse.ArgumentParser(description="Check your workshop setup.")
    parser.add_argument(
        "--model",
        default=DEFAULT_BEDROCK_MODEL_ID,
        help=f"Bedrock model ID to test (default: Strands default, {DEFAULT_BEDROCK_MODEL_ID})",
    )
    args = parser.parse_args()

    try:
        session = boto3.Session()
    except ProfileNotFound as e:
        fail(str(e), "Check AWS_PROFILE matches a profile in ~/.aws/config, or unset it.")

    region = check_region(session)
    check_credentials(session, region)
    check_bedrock(session, region, args.model)
    print("\nAll checks passed. You're ready for module 02 (or the optional module 01 primer).")


if __name__ == "__main__":
    main()
