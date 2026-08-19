# Pattern 5: Agent-as-Tool - Production Deployment

Deploy the Agent-as-Tool pattern to Amazon Bedrock AgentCore: 4 Runtimes coordinated by an Orchestrator.

![Agent-as-Tool architecture](./architecture.png)

**Pattern:** Orchestrator delegates to Researcher, Analyst, and Synthesizer specialist runtimes wrapped as `@tool` functions. The LLM decides routing and argument construction. No fixed pipeline.

---

## Why deploy.py is required (not the CLI)

The `agentcore configure` CLI configures a **single runtime** per project. This module deploys **4 runtimes** where the Orchestrator must know the ARNs of the three specialists at startup (passed as environment variables). The CLI cannot:

- Deploy multiple runtimes in one command
- Automatically pass specialist ARNs to the Orchestrator as env vars
- Coordinate the deployment order (specialists first, then Orchestrator)

`deploy.py` handles all of this with one command.

---

## Contents

- [Files](#files)
- [Architecture](#architecture)
- [Deploy](#deploy)
- [Invoke](#invoke)
- [Multi-turn chat](#multi-turn-chat)
- [Session continuity](#session-continuity)
- [Cleanup](#cleanup)
- [Observability](#observability)

---

## Files

| File | Purpose |
|------|---------|
| `deploy.py` | **boto3 deploy script** - deploys 3 specialists in parallel, then Orchestrator with specialist ARNs |
| `cleanup.py` | **boto3 cleanup script** - deletes all 4 runtimes, IAM roles, and S3 objects |
| `invoke.py` | Single-invocation script - pass Orchestrator Runtime ARN as argument |
| `chat.py` | **Interactive multi-turn chat** - maintains session across turns |
| `main.py` | Unused at production (root-level single-runtime variant - see `orchestrator/`) |
| `mock_tools.py` | Self-contained business intelligence tools |
| `orchestrator/main.py` | Orchestrator Runtime code - lazy singleton + SlidingWindowConversationManager |
| `specialists/researcher/main.py` | Researcher specialist - lazy singleton |
| `specialists/analyst/main.py` | Analyst specialist - lazy singleton |
| `specialists/synthesizer/main.py` | Synthesizer specialist - lazy singleton |

---

## Architecture

```
User
 |
 v  runtimeSessionId (routes to same container for session affinity)
Orchestrator Runtime  [SlidingWindowConversationManager, window=20]
  |                     (in-container history - persists while container is warm)
  +-- researcher_agent(@tool) --> Researcher Runtime
  +-- analyzer_agent(@tool)   --> Analyst Runtime
  +-- synthesizer_agent(@tool)--> Synthesizer Runtime
```

The Orchestrator passes the same `runtimeSessionId` to each specialist call so all requests within a session route to the same specialist container instance.

---

## Deploy

```bash
cd samples/07-agent-as-tool/production

python deploy.py                    # default prefix m7
python deploy.py --name-prefix m7ws # custom prefix (max 8 chars)
python deploy.py --dry-run          # preview without creating
```

What `deploy.py` does:

1. Creates/reuses the S3 code bucket
2. Deploys the 3 specialist runtimes **in parallel** (concurrent ThreadPoolExecutor)
3. Waits for all specialists to reach `READY` status
4. Deploys the Orchestrator with the specialist ARNs injected as environment variables:
   - `RESEARCHER_RUNTIME_ARN`
   - `ANALYZER_RUNTIME_ARN`
   - `SYNTHESIZER_RUNTIME_ARN`
5. Prints the Orchestrator ARN

**Output:**
```
=== Step 1: Deploy specialists in parallel ===
  [m7_researcher] READY: arn:aws:bedrock-agentcore:...
  [m7_analyst]    READY: arn:aws:bedrock-agentcore:...
  [m7_synthesizer] READY: arn:aws:bedrock-agentcore:...

=== Step 2: Deploy orchestrator ===
  [m7_orchestrator] READY: arn:aws:bedrock-agentcore:...

Orchestrator ARN (pass to chat.py or invoke.py):
  arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m7_orchestrator-XXXXX
```

---

## Invoke

Single invocation (no persistent session):

```bash
python invoke.py arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m7_orchestrator-XXXXX
```

---

## Multi-turn chat

`chat.py` maintains a session across turns using the same `runtimeSessionId`:

```bash
# New conversation
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m7_orchestrator-XXXXX

# Resume existing conversation
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:... \
  --session-id 550e8400-e29b-41d4-a716-446655440000

# Single prompt (non-interactive)
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:... \
  --prompt "Analyze NovaCart pricing options A, B, C"
```

---

## Session continuity

This module uses **in-container memory** only (no AgentCore Memory resource):

- The Orchestrator holds the full conversation history via `SlidingWindowConversationManager(window_size=20)`
- History persists while the container is warm (idle timeout: 15 minutes by default)
- If the container restarts, conversation history is lost - start a new session

For persistent cross-session memory, see Module 8 (Capstone) which uses AgentCore Memory (STM + LTM).

---

## Cleanup

```bash
python cleanup.py --name-prefix m7          # delete all 4 runtimes + IAM roles + S3
python cleanup.py --name-prefix m7 --dry-run
```

The script deletes all 4 runtimes and their IAM roles in sequence, then S3 code objects.

---

## Observability

AgentCore sends all telemetry to **Amazon CloudWatch**:

- **Logs:** one log group per runtime - `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`
- **Traces:** CloudWatch Transaction Search (X-Ray settings > GenAI Observability)

Each `invoke_agent_runtime` call produces a root trace. Nested specialist invocations appear as child spans, showing the tool call flow from Orchestrator to each specialist.

---

## References

- [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [Strands Agents SDK](https://strandsagents.com)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
