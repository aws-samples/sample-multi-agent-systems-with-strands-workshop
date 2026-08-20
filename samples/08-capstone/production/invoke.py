import os
import boto3, json, sys, uuid
from botocore.config import Config

RUNTIME_ARN = sys.argv[1] if len(sys.argv) > 1 else None
if not RUNTIME_ARN:
    print("Usage: python invoke.py <RUNTIME_ARN>")
    print("  Get the ARN from: agentcore deploy output, or run list_runtimes.py")
    sys.exit(1)

client = boto3.client(
    "bedrock-agentcore",
    region_name=os.environ.get("AWS_REGION","us-east-1"),
    config=Config(read_timeout=300),
)

response = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": "NovaCart Premium Tier: Options A ($19.99/mo invite-only), B ($14.99/mo 5% pilot), C ($12.99/mo full launch). Target: +15% CLV in 6 months. Budget: $2M."}).encode(),
    qualifier="DEFAULT",
)

raw = response["response"].read()
try:
    result = json.loads(raw)
    print(result.get("response", result) if isinstance(result, dict) else result)
except Exception:
    print(raw.decode())
