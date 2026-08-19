# Module 8 Capstone — Production Deployment

Multi-runtime deployment of the Capstone pattern on Amazon Bedrock AgentCore Runtime.
Combines **Agent-as-Tool** (Module 7) orchestration with **AgentCore Memory** for
persistent, multi-turn conversations.

---

## Architecture

```
User
 │  actorId → custom header  X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id
 │  sessionId → runtimeSessionId parameter (becomes context.session_id in container)
 ▼
Orchestrator Runtime  ──── AgentCore Memory (STM + LTM)
   │  passes same actorId header + runtimeSessionId to each specialist
   ├──► Researcher Runtime        (stateless — SlidingWindowConversationManager)
   ├──► Analyzer Runtime ×3       (concurrent — stateless)
   └──► Critic-Refiner Runtime    (GraphBuilder Writer→Critic loop — stateless)
```

### Session identifiers

| Identifier | What it is | Pattern | Where it lives |
|-----------|-----------|---------|---------------|
| **actorId** | Permanent user identity. Scopes long-term memory records per user. Stays the same across all sessions for a given user. | `[a-zA-Z0-9][a-zA-Z0-9-_/]*` 1–255 chars | Custom HTTP header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id`, injected by the caller via the boto3 event system before request signing. |
| **sessionId** | Unique conversation ID. Groups short-term memory events for one conversation. Also controls container affinity (same ID → same container instance). | `[a-zA-Z0-9][a-zA-Z0-9-_]*` 33–256 chars (runtimeSessionId) | `runtimeSessionId` parameter in `invoke_agent_runtime`. Arrives at the container as `context.session_id` via the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header, injected automatically by the AgentCore service. |

### How identifiers propagate between runtimes

1. The caller (`chat.py`) creates a boto3 client with a `before-sign` event hook that injects the `actorId` header.
2. The caller passes `sessionId` as `runtimeSessionId`.
3. AgentCore routes the request to the Orchestrator container and injects both as HTTP headers.
4. The Orchestrator reads `context.session_id` and `context.request_headers.get(ACTOR_HEADER)`.
5. When the Orchestrator calls a specialist, it passes the **same `runtimeSessionId`** AND the **same actor header** using its own boto3 event hook.
6. Specialist containers receive the same identifiers → same container session affinity → same Memory namespace.

### Memory strategy

| Layer | What it stores | Scope |
|-------|---------------|-------|
| **Short-term (STM)** | Raw conversation events (user ↔ agent turns). Kept for `eventExpiryDuration` days (30 by default). | Per `actorId` + `sessionId` |
| **Long-term (LTM)** | Facts extracted by the SEMANTIC strategy from STM events. Persists across sessions. | Per `actorId` under `/facts/{actorId}` |

The Orchestrator retrieves LTM facts at the start of each user turn via `retrieval_config`, injecting them as context before calling Bedrock.

---

## Files

| File | Purpose |
|------|---------|
| `deploy.py` | Creates AgentCore Memory + deploys 4 runtimes in one command |
| `cleanup.py` | Deletes all resources (runtimes, IAM roles, Memory, S3 code) |
| `chat.py` | Interactive multi-turn CLI — pass `--actor-id` and optionally `--session-id` |
| `invoke.py` | Single-invocation script (no actorId, no Memory) — for quick tests |
| `orchestrator/main.py` | Orchestrator Runtime with AgentCore Memory |
| `specialists/researcher/main.py` | Researcher specialist (lazy singleton) |
| `specialists/analyzer/main.py` | Analyzer specialist (lazy singleton) |
| `specialists/critic_refiner/main.py` | Critic-Refiner specialist (GraphBuilder loop) |

---

## Deploy

```bash
cd samples/08-capstone/production

# Install dependencies
pip install -r requirements.txt   # or: uv pip install -r requirements.txt

# Deploy everything (Memory + 4 runtimes)
python deploy.py

# Deploy without Memory (uses in-container SlidingWindowConversationManager)
python deploy.py --skip-memory

# Custom name prefix (max 8 chars)
python deploy.py --name-prefix m8ws
```

Deploy takes ~3–5 minutes. Output includes the Orchestrator ARN and Memory ID.

---

## Chat (multi-turn)

```bash
# Start a new conversation
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/m8_orchestrator-XXXXX

# Resume a previous conversation (same actorId — LTM still applies across sessions)
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:... \
  --session-id 550e8400-e29b-41d4-a716-446655440000

# Non-interactive single prompt
python chat.py \
  --actor-id user-123 \
  --runtime-arn arn:aws:bedrock-agentcore:... \
  --prompt "Analyze NovaCart pricing options A, B, C"
```

### Session ID notes

- A UUID (36 chars) is generated automatically for each new conversation.
- Save the printed Session ID to resume the conversation and access its STM history.
- Starting a new session with the same `actorId` will retrieve LTM facts from previous sessions.

---

## Cleanup

```bash
# Delete everything (runtimes + IAM roles + Memory + S3 objects)
python cleanup.py --name-prefix m8

# Keep the Memory (useful if you want to preserve LTM across redeploys)
python cleanup.py --name-prefix m8 --skip-memory

# Preview what would be deleted
python cleanup.py --name-prefix m8 --dry-run
```

---

## IAM permissions

### Specialist runtimes
- `bedrock:InvokeModel` / `bedrock:InvokeModelWithResponseStream`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
- `s3:GetObject`, `s3:ListBucket` (code bundle)

### Orchestrator runtime (additional)
- `bedrock-agentcore:InvokeAgentRuntime` — to call specialist runtimes
- `bedrock-agentcore:CreateEvent`, `GetEvent`, `ListEvents`, `DeleteEvent` — STM operations
- `bedrock-agentcore:RetrieveMemoryRecords`, `ListMemoryRecords`, `GetMemoryRecord` — LTM retrieval

---

## References

- [AgentCore Runtime documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [AgentCore Memory documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [Strands Agents SDK](https://strandsagents.com)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
