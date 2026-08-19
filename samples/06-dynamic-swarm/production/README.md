# M6: Dynamic Swarm: Production Runtime

![Dynamic Swarm Runtime on Amazon Bedrock AgentCore: Client invokes the Runtime which runs the Swarm with autonomous agent handoffs](./architecture.png)

Deploy this module as an Amazon Bedrock AgentCore Runtime.

## Files

| File | Purpose |
|------|---------|
| `main.py` | AgentCore entry point: `@app.entrypoint` wrapping the pattern |
| `mock_tools.py` | Self-contained business intelligence tools (no external deps) |
| `requirements.txt` | Runtime dependencies including OTEL instrumentation |

## Deploy

Run these commands from the `production/` folder.

```bash
# Navigate to this folder
cd samples/06-dynamic-swarm/production

# Configure the agent for deployment
agentcore configure -e main.py
# When prompted for a name, enter one <= 23 characters, e.g.: swarm

# Deploy (packages code to S3, provisions Runtime via CloudFormation: ~3-5 min)
agentcore deploy

# Invoke from terminal (pass the Runtime ARN printed by deploy)
python invoke.py arn:aws:bedrock-agentcore:us-east-1:ACCOUNT_ID:agentRuntime/RUNTIME_ID
```

When the deploy finishes, the output includes the **Runtime ARN**. Copy it and pass it to `invoke.py`.

## Test

```bash
# CLI
agentcore invoke "NovaCart Premium Tier: Options A ($19.99), B ($14.99), C ($12.99). Target +15% CLV."

# With session ID (for multi-turn context, must be 33+ chars):
agentcore invoke --session-id decision-memo-session-000001-abc "NovaCart Premium Tier: Options A ($19.99), B ($14.99), C ($12.99). Target +15% CLV."
```

```python
# boto3: production invocation pattern
import json, uuid, boto3

from botocore.config import Config
client = boto3.client("bedrock-agentcore", region_name="us-east-1",
    config=Config(read_timeout=300))  # pipelines can take 60-180s
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/<ARN-suffix>",
    runtimeSessionId=str(uuid.uuid4()),   # 33+ chars; uuid4 satisfies this
    payload=json.dumps({
        "prompt": "NovaCart Premium Tier: Options A ($19.99), B ($14.99), C ($12.99). Target +15% CLV.",
        "session_id": str(uuid.uuid4()),  # used by OTEL to group spans
    }).encode(),
    qualifier="DEFAULT",
)
result = json.loads(response["response"].read())
print(result)
```

## Observability

### Enable CloudWatch Transaction Search (one-time per account)

```python
import boto3
logs = boto3.client("logs", region_name="us-east-1")
xray = boto3.client("xray", region_name="us-east-1")

# Enable OTEL trace indexing
xray.update_trace_segment_destination(destination="CloudWatchLogs")
logs.create_log_group(logGroupName="aws/spans")
```

### Add OTEL to uv dependencies (already in requirements.txt)

`aws-opentelemetry-distro` is included. When `agentcore deploy` builds the container,
it installs OTEL automatically. No extra config needed.

### What you'll see in CloudWatch

Navigate to **CloudWatch → X-Ray → Traces** or **GenAI Observability**:

- **Per-invocation trace**: one root span per `invoke_agent_runtime` call
- **Per-agent spans**: each `Agent()` call creates a child span tagged with `session.id`
- **Tool call spans**: each tool call (researcher, analyzer, etc.) is a nested span
- **Duration breakdown**: see exactly where time is spent across the pipeline

Session ID is propagated via OTEL baggage so all spans from the same invocation
are grouped together, even across nested agent calls.

### Check traces

```bash
# View recent invocations
agentcore status

# CloudWatch Logs Insights query for your Runtime
aws logs start-query \
  --log-group-name /aws/bedrock-agentcore/swarm \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | sort @timestamp desc | limit 20'
```

## Cleanup

**Two steps: both required:**

```bash
# Step 1: Reset local config (does NOT touch AWS)
agentcore remove all -y

# Step 2: Apply teardown — removes the Runtime and ECR image from AWS
agentcore deploy
```

> `agentcore remove all -y` only resets the local `agentcore/agentcore.json`.
> The follow-up `agentcore deploy` is what actually deletes the CloudFormation stack
> and the AgentCore Runtime endpoint from your account.

To verify cleanup is complete:

```bash
# Check no Runtimes remain
aws bedrock-agentcore list-agent-runtimes --region us-east-1

# Verify Runtime is gone
aws bedrock-agentcore list-agent-runtimes --region us-east-1
```
