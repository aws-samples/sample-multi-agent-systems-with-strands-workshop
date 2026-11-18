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
    region_name=os.environ.get("AWS_REGION") or RUNTIME_ARN.split(":")[3],
    config=Config(read_timeout=300),
)

response = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": "INCIDENT: E-Commerce Checkout Degradation. Checkout API latency 8200ms (baseline 450ms), error rate 12% (HTTP 5xx on /api/checkout), DB connection pool 95% utilized (baseline 40%). Affected: checkout-service, order-api. Started 15 minutes after deployment v2.4.1. Investigate root cause and produce a resolution plan."}).encode(),
    qualifier="DEFAULT",
)

raw = response["response"].read()
try:
    result = json.loads(raw)
    print(result.get("response", result) if isinstance(result, dict) else result)
except Exception:
    print(raw.decode())
