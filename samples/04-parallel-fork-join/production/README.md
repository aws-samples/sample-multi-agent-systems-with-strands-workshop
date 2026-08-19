# Module 4 - Parallel Fork-Join: Production Deployment

Deploy the Parallel Fork-Join pattern to Amazon Bedrock AgentCore Runtime.

![Parallel Fork-Join architecture](./architecture.png)

**Pattern:** Researcher -> [Analyzer A || B || C via GraphBuilder] -> Synthesizer. The three analyzers run in parallel inside one Runtime container using Strands `GraphBuilder`.

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
| `main.py` | AgentCore entry point - `@app.entrypoint` wrapping the parallel GraphBuilder pipeline |
| `mock_tools.py` | Self-contained business intelligence tools (no external dependencies) |
| `requirements.txt` | Runtime dependencies: strands-agents, bedrock-agentcore, OTEL |
| `deploy.py` | **boto3 deploy script** - creates IAM role, uploads code, provisions Runtime |
| `cleanup.py` | **boto3 cleanup script** - deletes Runtime, role, and S3 objects |
| `invoke.py` | Single-invocation script - pass Runtime ARN as argument |

---

## Deploy

```bash
cd samples/04-parallel-fork-join/production

python deploy.py                    # default prefix m4
python deploy.py --name-prefix m4ws # custom prefix (max 20 chars)
python deploy.py --dry-run          # preview without creating
```

The script:
1. Creates an S3 bucket for code bundles (reused across modules)
2. Packages code with all dependencies for Linux ARM64
3. Creates an IAM execution role with least-privilege Bedrock + CloudWatch permissions
4. Creates the AgentCore Runtime (`codeConfiguration`, `PYTHON_3_13`)
5. Waits for `READY` status and prints the Runtime ARN

---

## Invoke

```bash
python invoke.py arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m4_parallel-XXXXX
```

Or with boto3:

```python
import json, uuid, boto3
from botocore.config import Config

client = boto3.client(
    "bedrock-agentcore",
    region_name="us-east-1",
    config=Config(read_timeout=300),
)
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m4_parallel-XXXXX",
    runtimeSessionId=str(uuid.uuid4()),  # 33-256 chars
    payload=json.dumps({
        "prompt": "NovaCart Premium Tier: Options A ($19.99), B ($14.99), C ($12.99). Target +15% CLV."
    }).encode(),
    qualifier="DEFAULT",
)
raw = response["response"].read()
result = json.loads(raw)
print(result.get("response", result) if isinstance(result, dict) else result)
```

---

## Multi-turn chat

Reuse the same `runtimeSessionId` across calls to route requests to the same container. The agent uses `SlidingWindowConversationManager(window_size=20)` to keep conversation history in the container.

---

## Cleanup

```bash
python cleanup.py --name-prefix m4          # delete Runtime + IAM role + S3
python cleanup.py --name-prefix m4 --dry-run
```

---

## Observability

AgentCore sends all telemetry to **Amazon CloudWatch**:

- **Logs:** `/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT`
- **Traces:** CloudWatch Transaction Search (under X-Ray settings > GenAI Observability)

GraphBuilder parallel execution produces child spans for each analyzer node, visible in the trace view.

---

## References

- [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [Strands Agents GraphBuilder](https://strandsagents.com)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
