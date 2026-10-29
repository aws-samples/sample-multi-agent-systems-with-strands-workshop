# AGENTS.md

Guidance for AI coding agents working in this repository. Human contributors should
read `README.md` and `CONTRIBUTING.md` first.

## What this repo is

Sample code for the **Multi-Agent Systems with Strands** workshop. It teaches how to
build multi-agent systems with the [Strands Agents SDK](https://strandsagents.com) on
Amazon Bedrock, progressing from a single agent to five orchestration patterns and a
capstone that combines them.

Each module has a local version (notebook + `chat.py`) and a `production/` version that
deploys to Amazon Bedrock AgentCore Runtime over the A2A protocol.

```
samples/
  01-foundations/         Agent primitives + the agent loop
  02-single-agent/        One agent with tools; the single-agent ceiling
  03-sequential-chain/    Pattern 1 — Researcher → Analyst → Synthesizer
  04-parallel-fork-join/  Pattern 2 — fan out to analyzers, then join
  05-critic-refiner/      Pattern 3 — writer ↔ critic cycle
  06-dynamic-swarm/        Pattern 4 — autonomous handoffs
  07-agent-as-tool/       Pattern 5 — orchestrator delegates to specialist tools
  08-capstone/            All patterns combined
  shared/                 prompts, decision brief, A2A + deploy helpers
```

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
   `Workflow` class; do not label `GraphBuilder` as a "Workflow". For conversation
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
- **Model choice** is left to the Bedrock default; alternatives are shown in comments so
  the samples run at events that only enable specific models. If you pin a model, pin it
  everywhere consistently and say why.
- Specialists set `callback_handler=None` so only the final result is printed.
- Local `chat.py` (modules 02–08) is the notebook in script form: same prompts, agents,
  topology and limits. It waits for the user (no default prompt, an empty line is
  ignored, `quit`/`exit`/`q` or Ctrl+C exit). `read_message()` sends a multi-line paste
  as ONE message (Windows falls back to `input()`).
- Chat memory. 02 and 07 keep one `Agent` for the session. 03–06 and 08 build the
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

## Local vs production

- **Local** (`module-0X.ipynb`, `chat.py`): everything runs in one process; the
  `GraphBuilder`/`Swarm`/`@tool` primitives coordinate agents directly.
- **Production** (`production/`): specialists are separate AgentCore Runtimes reached
  over A2A. A coordinator threads context between them. When agents live in different
  runtimes, an in-process graph cannot span them — an explicit A2A coordination loop is
  the correct trade-off there, and the code says so in comments. Do not "fix" it into a
  single-process graph.

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
