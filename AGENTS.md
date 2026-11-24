# AGENTS.md

Guidance for AI coding agents working in this repository. Human contributors should
read `README.md` and `CONTRIBUTING.md` first.

## What this repo is

Sample code for the **Multi-Agent Systems with Strands** workshop. It teaches how to
build multi-agent systems with the [Strands Agents SDK](https://strandsagents.com) on
Amazon Bedrock. The core workshop follows modules **02 → 03 → 04**: a single agent,
graph-based orchestration, and agents as tools. Module **01 Foundations** (the agent
loop) is an optional primer. Additional patterns and the capstone are optional modules
in `samples/extra/`; they keep their original numbers, so `extra/04-parallel-fork-join`
is not core module 04.

Each module has a local version (notebook + `chat.py`) and a `production/` version that
deploys to Amazon Bedrock AgentCore Runtime over the A2A protocol.

```
samples/
  01-foundations/         Agent primitives + the agent loop (optional primer)
  02-single-agent/        One agent with tools; the single-agent ceiling
  03-sequential-chain/    Pattern 1 — Researcher → Analyst → Synthesizer
  04-agent-as-tool/       Pattern 5 — orchestrator delegates to specialist tools
  shared/                 prompts, decision brief, A2A + deploy helpers
  extra/
    04-parallel-fork-join/  Pattern 2 — fan out to analyzers, then join
    05-critic-refiner/      Pattern 3 — writer ↔ critic cycle
    06-dynamic-swarm/        Pattern 4 — autonomous handoffs
    08-capstone/            All patterns combined
```

Keep the original module numbers. References below to modules 04–06 and 08 apply
to their locations in `samples/extra/`. Shared deployment helpers remain in `samples/shared/`,
and the mock data tools remain in `samples/02-single-agent/decision_brief_tools.py`.

## Golden rules

1. **Use Strands primitives, not hand-rolled Python glue.** Express orchestration with
   the SDK's primitives — do not reinvent them with plain loops, manual string
   threading, or ad-hoc concurrency:
   - Sequential and parallel topologies → `GraphBuilder` (`strands.multiagent`).
   - Reflection / revision loops → `GraphBuilder` with a conditional cycle edge.
   - Autonomous handoffs → `Swarm`.
   - Hierarchical delegation → agents wrapped as `@tool`.
   Interactive terminal loops (`while True: input()`) and result printing are fine — they
   are not orchestration.
2. **Match the official docs.** Follow [strandsagents.com](https://strandsagents.com).
   The installed multi-agent primitives are `GraphBuilder` and `Swarm` — there is no
   `Workflow` class; do not label `GraphBuilder` as a "Workflow". (The docs' "workflow"
   page means plain function calls in application code; module 03 says why it uses a
   graph instead.) For conversation
   context use `Agent(context_manager="auto")`, not the legacy
   `SlidingWindowConversationManager` / `conversation_manager`.
3. **Keep each module focused on its pattern.** Do not add memory, extra tools, or
   configurability a module does not need to teach its point.
4. **Verify against Amazon Bedrock before claiming done.** Compile changed files, and
   run affected samples end-to-end against a real Bedrock endpoint. Use your own AWS
   credentials/profile; never hardcode credentials or account IDs.

## Conventions

- **Region is never hardcoded.** Read it from the environment
  (`os.environ.get("AWS_REGION") or boto3.Session().region_name`), or derive it from a
  runtime ARN (`arn.split(":")[3]`). A silent `"us-east-1"` fallback is a bug.
- **Model choice** is left to the Strands Bedrock default (Claude Sonnet 4.6,
  `global.anthropic.claude-sonnet-4-6`, in strands-agents 1.65); alternatives are shown in comments so
  the samples run at events that only enable specific models. If you pin a model, pin it
  everywhere consistently and say why. Exception: module 03 deliberately runs its Analyst
  and Synthesizer on Claude Haiku 4.5 (`global.anthropic.claude-haiku-4-5-20251001-v1:0`)
  to teach right-sizing per stage; Amazon Nova is not used because the Workshop Studio participant
  policy only allows Anthropic inference profiles; notebook, `chat.py` and `production/` all match.
- **Model IDs must pass the Workshop Studio policy.** Notebooks and `chat.py` run on the Code Editor
  instance, whose role (like the participant role) allows only `foundation-model/anthropic.*`,
  `foundation-model/amazon.*` and `inference-profile/*.anthropic.*`. So use Anthropic models (bare
  or `us.`/`global.` profiles) or bare Amazon IDs; an Amazon inference profile such as
  `us.amazon.nova-pro-v1:0` is denied. Bare `amazon.nova-pro-v1:0` is on-demand only in us-east-1;
  bare `amazon.nova-lite-v1:0` works in all three supported regions. The AgentCore runtime roles
  (`ws-agentcore-*-exec`) allow every model, so a model can work when deployed and still fail in the
  notebook. Check a new ID with `python samples/shared/check_setup.py --model <ID>` and with
  `aws iam simulate-custom-policy` against the Workshop Studio `static/iam_policy.json`.
- Specialists set `callback_handler=None` so only the final result is printed.
- Local `chat.py` (modules 02–08) is the notebook in script form: same prompts, agents,
  topology and limits. It waits for the user (no default prompt, an empty line is
  ignored, `quit`/`exit`/`q` or Ctrl+C exit). `read_message()` sends a multi-line paste
  as ONE message (Windows falls back to `input()`).
- **One scenario.** Modules 02, 03 and 04 run the same `DECISION_BRIEF` from
  `shared/decision_brief.py` (04 appends an investment-committee request) over the mock
  data in `02-single-agent/decision_brief_tools.py`. Keep their numbers consistent.
- Chat memory. 02 and 04 keep one `Agent` for the session. 03 and the `extra/` modules build the
  Graph/Swarm fresh every turn, like the notebook, and share one
  `TestMemoryStore(persist=False)`. Each agent gets its own
  `MemoryManager(stores=[MEMORY], search_tool_config=False)` and reads only through
  injection. After each turn `remember()` stores exactly two entries: the user's message
  and the system's final answer. Do not add automatic extraction (it would store the
  agents' internal work). Do not reuse a graph across turns or wrap a pattern in another
  pattern to get memory.
- `production/` layout per module: `deploy.py`, `cleanup.py`, `chat.py`, `invoke.py`,
  `main.py` (single-runtime variant), `chain.py` or `orchestrator/` (coordinator), and
  `specialists/<name>/main.py` (one A2A runtime each).
- A2A helpers live in `shared/a2a_utils.py` and each `production/` tree.
- `shared/deploy_utils.ensure_runtime_role()` creates execution roles with the AgentCore
  devguide trust policy (`aws:SourceAccount` + `aws:SourceArn`). If
  `AGENTCORE_PERMISSIONS_BOUNDARY_ARN` is set (the Workshop Studio Kiro IDE exports it), the
  role is created with that permissions boundary; the workshop participant policy rejects
  roles without it. Leave it unset in your own account.

## Local vs production

- **Local** (`module-0X.ipynb`, `chat.py`): everything runs in one process; the
  `GraphBuilder`/`Swarm`/`@tool` primitives coordinate agents directly.
- **Production** (`production/`): specialists are separate AgentCore Runtimes reached
  over A2A. Reach them with Strands primitives, as locally: `GraphBuilder` accepts
  `A2AAgent` nodes (03 `chain.py`), and an orchestrator `Agent` calls `A2AAgent`s from
  `@tool` functions (04 `orchestrator/`). `A2AAgent` has no `as_tool()`, so
  `delegate=True` is local-only; the production prompt asks the orchestrator to return the
  writer's memo unchanged instead. Specialists use the same system prompts as the
  notebook. `production/main.py` is an optional single-runtime variant of the notebook
  (not deployed by `deploy.py`). Agent-as-Tool keeps its `m7` deploy prefix and
  `m7-agent-as-tool` resource names: `m4` belongs to the optional Parallel Fork-Join, and
  sharing a prefix would make their IAM roles collide.

## Running a sample

```bash
cd samples/02-single-agent
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
python chat.py
```

Requires AWS credentials with Amazon Bedrock model access in your region.

## Do not

- Do not commit credentials, account IDs, ARNs containing account numbers, personal
  names/aliases, emails, or internal-only URLs.
- Do not add generated artifacts (`.venv/`, `__pycache__/`, `.ipynb_checkpoints/`).
- Do not remove a requested feature to make a change compile; fix the root cause.
