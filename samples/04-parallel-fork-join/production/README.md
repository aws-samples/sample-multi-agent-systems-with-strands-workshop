# Pattern 2: Parallel Fork-Join - Production Deployment

Deploy Pattern 2 (Parallel Fork-Join) to Amazon Bedrock AgentCore Runtime using the A2A protocol.

![Pattern 2: Parallel Fork-Join architecture](./architecture.png)

**Pattern:** Researcher gathers data → 3 Analyzers run in parallel (Options A, B, C) → Synthesizer joins results.  
**Strands primitive:** `GraphBuilder` (Workflow / DAG)

---

## Architecture

![Pattern 2: Parallel Fork-Join architecture](./architecture.png)

**Specialists** run as AgentCore Runtimes on port 9000 using the A2A protocol.  
**Coordination** is handled by `chain.py` — a local Python script using `GraphBuilder` with `A2AAgent` nodes.

No orchestrator runtime is deployed. Pattern 2 is a deterministic DAG with no LLM routing decisions,
so a lightweight coordinator script is enough.

> **Production alternatives for the coordination layer:**  
> - AWS Lambda — stateless, event-driven, no servers  
> - AWS Step Functions — durable parallel branches with Map state  
> The specialist runtimes stay unchanged in all cases.

---

## Files

| File | Purpose |
|------|---------|
| `deploy.py` | Deploy 3 specialist runtimes (A2A) in parallel |
| `cleanup.py` | Delete all runtimes, IAM roles, S3 objects |
| `chain.py` | Fork-join coordinator — runs locally via GraphBuilder |
| `a2a_utils.py` | SigV4 auth and A2A utilities for chain.py |
| `invoke.py` | Single invocation helper — wraps chain.py |
| `specialists/researcher/main.py` | Researcher A2A runtime |
| `specialists/analyzer/main.py` | Analyzer A2A runtime (called 3× in parallel) |
| `specialists/synthesizer/main.py` | Synthesizer A2A runtime |

---

## Deploy

```bash
cd samples/04-*/production

python deploy.py                     # default prefix m4
python deploy.py --name-prefix m4ws  # custom prefix (max 8 chars)
python deploy.py --dry-run
```

Deploys **3 runtimes**: researcher (A2A), analyzer (A2A, called 3× in parallel), synthesizer (A2A).  
Saves ARNs to `.env_arns`.

---

## Run the chain

```bash
source .env_arns
python chain.py                         # default brief
python chain.py "your brief here"       # custom brief
```

---

## Sample brief

```
NovaCart Premium Tier: Options A ($19.99/mo invite-only), B ($14.99/mo 5% pilot),
C ($12.99/mo full launch). Target: +15% CLV in 6 months. Budget: $2M.
```

First call: 5-10 min (cold start across 3 specialist runtimes).  
Subsequent calls: 2-4 min (warm containers).

---

## Cleanup

```bash
python cleanup.py --name-prefix m4          # delete everything
python cleanup.py --name-prefix m4 --dry-run
```

---

## Observability

AgentCore sends all telemetry to **Amazon CloudWatch**:

- **Logs:** `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT` (one per runtime)
- **Traces:** CloudWatch Transaction Search — the three Analyzer spans appear in parallel in the timeline

---

## References

- [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [AgentCore A2A protocol](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html)
- [Strands GraphBuilder](https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/)
- [Strands A2AAgent](https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
