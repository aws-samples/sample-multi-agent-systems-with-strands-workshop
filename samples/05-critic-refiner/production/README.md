# Pattern 3: Critic-Refiner — Production Deployment

Deploys two separate A2A specialist runtimes. `chain.py` coordinates the loop locally.

![Critic-Refiner production: two A2A specialist runtimes (Writer and Critic); chain.py manages the revision loop locally until the Critic returns APPROVED](./architecture.png)

**Pattern:** Writer produces a draft → Critic evaluates → feedback loops back until APPROVED.  
**Strands primitive:** `GraphBuilder + cycle`

---

## Architecture

```
chain.py (local)
  │
  ├──A2A──► Writer Runtime   ← Generator: produces / revises the memo
  │              ↑
  │         feedback (brief + draft + REVISION NEEDED)
  │              │
  └──A2A──► Critic Runtime   ← Evaluates: APPROVED or REVISION NEEDED: ...
```

**Writer** and **Critic** are separate A2A runtimes.  
`chain.py` manages the loop — context is passed explicitly in each A2A call:
1. `writer(brief)` → draft
2. `critic(draft)` → verdict
3. If `REVISION NEEDED`: `writer(brief + previous_draft + feedback)` → revised draft
4. Repeat until `APPROVED` or `max_cycles` reached

---

## Files

| File | Purpose |
|------|---------|
| `deploy.py` | Deploy 2 specialist runtimes (writer A2A + critic A2A) in parallel |
| `cleanup.py` | Delete all runtimes, IAM roles, S3 objects |
| `chain.py` | Coordinator — manages the Writer↔Critic loop locally |
| `chat.py` | Interactive multi-turn chat (multiple conversations supported) |
| `invoke.py` | Single invocation helper — wraps chain.py |
| `specialists/writer/main.py` | Writer A2A runtime |
| `specialists/critic/main.py` | Critic A2A runtime |

---

## Deploy

```bash
cd samples/05-*/production

python deploy.py                     # default prefix m5
python deploy.py --name-prefix m5ws  # custom prefix (max 8 chars)
python deploy.py --dry-run
```

Deploys **2 runtimes**: writer (A2A) + critic (A2A).  
Saves ARNs to `.env_arns`.

---

## Run

```bash
source .env_arns

# Single invocation
python invoke.py
python invoke.py "your brief here"

# Interactive multi-turn chat
python chat.py
```

---

## Sample brief

```
NovaCart Premium Tier: Options A ($19.99/mo invite-only), B ($14.99/mo 5% pilot),
C ($12.99/mo full launch). Target: +15% CLV in 6 months. Budget: $2M.
```

First call: 1-2 min (cold start).  
Subsequent calls: 15-30s (warm containers).

---

## Cleanup

```bash
python cleanup.py --name-prefix m5          # delete everything
python cleanup.py --name-prefix m5 --dry-run
```

---

## Observability

AgentCore sends all telemetry to **Amazon CloudWatch**:

- **Logs:** `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT` (one per runtime)
- **Traces:** CloudWatch Transaction Search — Writer and Critic spans visible per cycle

---

## References

- [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [AgentCore A2A protocol](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html)
- [Strands GraphBuilder](https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/)
- [bedrock-agentcore Python SDK](https://pypi.org/project/bedrock-agentcore/)
