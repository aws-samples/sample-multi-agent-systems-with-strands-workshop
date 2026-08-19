# Pattern 1: Sequential Chain - Production Deployment

Deploy the Sequential Chain pattern to Amazon Bedrock AgentCore Runtime.

![Sequential Chain architecture](./architecture.png)

**Pattern:** Researcher -> Analyst -> Synthesizer. Each stage passes its output as a string to the next. All three agents run inside one Runtime container.

---

## Contents

- [Files](#files)
- [Deploy](#deploy)
- [Invoke](#invoke)
- [Multi-turn chat](#multi-turn-chat)
- [Cleanup](#cleanup)
- [Observability](#observability)

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | AgentCore entry point - `@app.entrypoint` wrapping the sequential pipeline |
| `mock_tools.py` | Self-contained business intelligence tools (no external dependencies) |
| `requirements.txt` | Runtime dependencies: strands-agents, bedrock-agentcore, OTEL |
| `deploy.py` | **boto3 deploy script** - creates IAM role, uploads code, provisions Runtime |
| `cleanup.py` | **boto3 cleanup script** - deletes Runtime, role, and S3 objects |
| `invoke.py` | Single-invocation script - pass Runtime ARN as argument |

---

## Deploy

```bash
cd samples/03-sequential-chain/production

python deploy.py                    # default prefix m3
python deploy.py --name-prefix m3ws # custom prefix (max 20 chars)
python deploy.py --dry-run          # preview without creating
```

The script:
1. Creates an S3 bucket for code bundles (reused across modules)
2. Packages `main.py`, `mock_tools.py`, `requirements.txt` with all dependencies for Linux ARM64
3. Creates an IAM execution role with least-privilege Bedrock + CloudWatch permissions
4. Creates the AgentCore Runtime (`codeConfiguration`, `PYTHON_3_13`)
5. Waits for `READY` status and prints the Runtime ARN

**Output:**
```
READY: arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m3_seqchain-XXXXX

Invoke:  python invoke.py arn:aws:...
Cleanup: python cleanup.py --name-prefix m3
```

---

## Invoke

```bash
# Single invocation
python invoke.py arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m3_seqchain-XXXXX
```

Or with boto3 directly:

```python
import json, uuid, boto3
from botocore.config import Config

client = boto3.client(
    "bedrock-agentcore",
    region_name="us-east-1",
    config=Config(read_timeout=300),
)
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m3_seqchain-XXXXX",
    runtimeSessionId=str(uuid.uuid4()),  # 33-256 chars; UUID satisfies this
    payload=json.dumps({
        "prompt": "NovaCart Premium Tier: Options A ($19.99), B ($14.99), C ($12.99). Target +15% CLV."
    }).encode(),
    qualifier="DEFAULT",
)
raw = response["response"].read()
result = json.loads(raw)
print(result.get("response", result) if isinstance(result, dict) else result)
```

**Note on `runtimeSessionId`:** minimum 33 characters. Pass the same ID on subsequent calls to route all requests to the same container instance (session affinity).

---

## Multi-turn chat

For multi-turn conversations within the same container session, reuse the same `runtimeSessionId`. The Orchestrator uses `SlidingWindowConversationManager(window_size=20)` to keep conversation history in the container.

```python
session_id = str(uuid.uuid4())   # generate once, reuse for all turns

# Turn 1
response1 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    runtimeSessionId=session_id,
    payload=json.dumps({"prompt": "Analyze NovaCart pricing options."}).encode(),
    qualifier="DEFAULT",
)

# Turn 2 - agent remembers Turn 1
response2 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    runtimeSessionId=session_id,
    payload=json.dumps({"prompt": "What was your main recommendation?"}).encode(),
    qualifier="DEFAULT",
)
```

---

## Cleanup

```bash
python cleanup.py --name-prefix m3          # delete Runtime + IAM role + S3
python cleanup.py --name-prefix m3 --dry-run
```

The script deletes:
- AgentCore Runtime
- IAM execution role and all attached policies
- S3 code objects for this module

---

## Observability

AgentCore sends all telemetry to **Amazon CloudWatch**:

- **Logs:** `/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT`
- **Traces:** CloudWatch Transaction Search (under X-Ray settings > GenAI Observability)
- **Metrics:** `bedrock-agentcore` namespace

Enable CloudWatch Transaction Search once per account:

```python
import boto3
xray = boto3.client("xray", region_name="us-east-1")
logs = boto3.client("logs", region_name="us-east-1")

xray.update_trace_segment_destination(destination="CloudWatchLogs")
try:
    logs.create_log_group(logGroupName="aws/spans")
except logs.exceptions.ResourceAlreadyExistsException:
    pass
```

---

## References

- [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [Strands Agents SDK](https://strandsagents.com)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
