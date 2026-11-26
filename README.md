> **Demo project:** these samples teach multi-agent architecture and integration patterns. They have not been through a production readiness review or a load test. Review security, cost and operations before you adapt them.

# Build Production Multi-Agent Systems with Strands Agents and Amazon Bedrock AgentCore

Build, deploy, and scale multi-agent systems using reusable patterns with the [Strands Agents SDK](https://strandsagents.com/docs/). Follow the core path **02 Single Agent → 03 Sequential Chain → 04 Agent-as-Tool** to explore graph-based orchestration and specialist delegation. [01 Foundations](./samples/01-foundations/) is an optional primer on Strands agent primitives and the agent loop. Modules 03 and 04 include deployments to [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/). Additional patterns and the capstone are available in [`samples/extra/`](./samples/extra/).

![Strands Agents](https://img.shields.io/badge/Strands_Agents-SDK-FF9900?logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232F3E?logo=amazonaws&logoColor=white)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Patterns-01A88D?logo=amazonaws&logoColor=white)
![License MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)

---

## Modules

Work through the core modules in order.

| Module | Description | Strands Pattern | Production Protocol |
|--------|-------------|-----------------|---------------------|
| [02 Single Agent](./samples/02-single-agent/) | One Strategy Advisor agent with three business intelligence tools on the MarketNest decision brief; inspect the loop and hit the single-agent ceiling | `Agent(tools=[...], system_prompt=...)` · `chat.py` keeps one agent with `context_manager="auto"` | n/a |
| [03 Sequential Chain](./samples/03-sequential-chain/) | Break the single-agent ceiling: the same brief through Researcher → Analyst → Synthesizer in a fixed order set by graph edges | [`GraphBuilder`](https://strandsagents.com/docs/user-guide/sdk/multi-agent/graph/) · `A2AAgent` nodes (prod) | `chain.py` local · Specialists: **A2A** |
| [04 Agent-as-Tool](./samples/04-agent-as-tool/) | Investment analysis of the same brief: an LLM orchestrator delegates to Research, Finance, Legal and Writer specialists used as tools; the model picks the order | `@tool` wrapping `Agent` · `as_tool(delegate=True)` · `A2AAgent` (prod) | Orchestrator: **HTTP** · Specialists: **A2A** |

Modules **03 and 04** include a `production/` subfolder.

### Optional modules

[01 Foundations](./samples/01-foundations/) is an optional primer on Strands agent primitives, a first tool, inspecting the agent loop, metrics, and multi-turn. The remaining optional modules keep their original numbers, so the optional Parallel Fork-Join is `extra/04-parallel-fork-join`, separate from core module 04.

| Module | Description | Strands Pattern | Production Protocol |
|--------|-------------|-----------------|---------------------|
| [01 Foundations](./samples/01-foundations/) | Strands agent primitives, a first tool, inspecting the agent loop, metrics, multi-turn | `Agent(tools=[...])` | n/a |
| [04 Parallel Fork-Join](./samples/extra/04-parallel-fork-join/) | Researcher feeds three analyzers running simultaneously; results merged at the synthesizer | `GraphBuilder` DAG + parallel edges | `chain.py` local · Specialists: **A2A** |
| [05 Critic-Refiner](./samples/extra/05-critic-refiner/) | Writer drafts, Critic evaluates, memo cycles back until `APPROVED` | `GraphBuilder` cycle + `set_max_node_executions` | `chain.py` local · Specialists: **A2A** |
| [06 Dynamic Swarm](./samples/extra/06-dynamic-swarm/) | Incident response: Monitor → Network Specialist / DB Admin → Resolver; path emerges at runtime | `Swarm` (local) · `Agent(tools=[...])` (prod) | Orchestrator: **HTTP** · Specialists: **A2A** |
| [08 Capstone](./samples/extra/08-capstone/) | Strategy Recommendation Engine: planner → analysis team Swarm (researcher, risk and demand analyzers, synthesizer ↔ reviewer) → evaluator → writer | `GraphBuilder` with a nested `Swarm` node (P1 + P2 + P3 + P4) | Orchestrator: **HTTP** · Specialists: **A2A** (different design, see its README) |

Each optional module includes its own `production/` deployment. See [`samples/extra/`](./samples/extra/).

---

## What you'll build

A decision-memo system for one MarketNest decision brief: start with one agent using business intelligence tools, split the work into a Researcher → Analyst → Synthesizer pipeline with `GraphBuilder`, then let an orchestrator agent delegate to specialist agents used as tools.

The optional [capstone](./samples/extra/08-capstone/) combines additional patterns into a Strategy Recommendation Engine.

---

## Why multi-agent systems?

A single agent faces hard limits: one context window, one model's reasoning, and no parallelism. Multi-agent systems decompose complex tasks and delegate to specialists.

| Challenge | Single Agent | Multi-Agent System |
|-----------|-------------|-------------------|
| Complex tasks | One context for everything | Decomposes into focused sub-tasks |
| Parallelism | Sequential only | Specialists run concurrently |
| Quality control | Hope the output is good | Critic enforces a quality gate |
| Failure scope | One failure = full failure | Isolated failure, graceful recovery |
| Observability | One trace | Per-agent OTEL traces + system view |

> The same patterns (Sequential Chain, Fork-Join, Critic-Refiner, Swarm, Agent-as-Tool) are general multi-agent design concepts that apply to other agent frameworks.

---

## How the production protocols work

Core modules 03 and 04, and optional modules in `samples/extra/`, deploy **multiple AgentCore Runtimes**. Module 03 coordinates its A2A specialists locally with `chain.py`; module 04 uses an HTTP orchestrator runtime. The deployments use these protocols:

### HTTP protocol: Orchestrator Runtime

The entry point for user requests. The orchestrator runs [`BedrockAgentCoreApp`](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-getting-started.html) on **port 8080** at path `/invocations`. Users call it via `invoke_agent_runtime` (boto3) or `chat.py`.

The orchestrator coordinates specialists by calling them via A2A using [`A2AAgent`](https://strandsagents.com/docs/api/python/strands.agent.a2a_agent/index.md) from the Strands SDK, with SigV4 authentication handled automatically by AgentCore.

### A2A protocol: Specialist Runtimes

Each specialist runs [`serve_a2a(StrandsA2AExecutor(agent))`](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html) on **port 9000** at path `/`. The A2A protocol uses JSON-RPC 2.0 for agent-to-agent communication and provides automatic agent discovery via an agent card at `/.well-known/agent-card.json`.

Key differences:

| | HTTP (Orchestrator) | A2A (Specialists) |
|-|--------------------|--------------------|
| Port | 8080 | 9000 |
| Path | `/invocations` | `/` |
| Protocol | HTTP + JSON | JSON-RPC 2.0 |
| Authentication | SigV4 / OAuth 2.0 | SigV4 / OAuth 2.0 |
| Discovery | n/a | `/.well-known/agent-card.json` |
| Strands class | `BedrockAgentCoreApp` | `serve_a2a` + `StrandsA2AExecutor` |
| Invoked by | Users via boto3 | Orchestrator via `A2AAgent` |

References: [AgentCore A2A](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html) · [Strands A2AAgent](https://strandsagents.com/docs/api/python/strands.agent.a2a_agent/index.md) · [Deploy to AgentCore](https://strandsagents.com/docs/user-guide/sdk/deploy/deploy_to_bedrock_agentcore/)

---

## How to get started

### In AWS Workshop Studio

Open the workshop environment. All dependencies are pre-installed. From the repository root, run `python samples/shared/check_setup.py` to confirm your region, credentials, and Bedrock model access, then open any module notebook and run cells top to bottom.

### Locally

Clone this repository and navigate to any module:

```bash
cd samples/02-single-agent
pip install -r requirements.txt
python ../shared/check_setup.py     # checks Python, Strands, region, credentials, and Bedrock model access
jupyter notebook module-02.ipynb
```

### Chat with a module from the terminal

Core modules 02, 03 and 04, and all optional modules, include a `chat.py` that runs the same agents as the notebook in an interactive loop:

```bash
cd samples/03-sequential-chain
pip install -r requirements.txt
python chat.py
```

- The chat waits for you. It never sends a prompt on its own, and an empty line is ignored.
- Type or paste your message. A multi-line brief pasted at once (like the `DECISION_BRIEF` in a notebook) is sent as one message.
- Ask follow-ups in the same session: every chat remembers the conversation. Modules 02 and 04 keep one agent for the whole session. Module 03 and the optional Parallel Fork-Join, Critic-Refiner, Dynamic Swarm and Capstone modules build the multi-agent system fresh on every turn, as the notebook does, and share a [Strands memory](https://strandsagents.com/docs/user-guide/sdk/memory/overview/) that holds only your messages and the final answers.
- Type `quit` (or press Ctrl+C) to exit.

For module 04 with deployed runtimes (also available in the optional Dynamic Swarm and Capstone modules):

```bash
cd samples/04-agent-as-tool/production
python chat.py --actor-id <your-id> --runtime-arn <RUNTIME_ARN>
```

---

## How to deploy a production module

Core modules 03 and 04 and all optional modules have a `production/` subfolder. The deployment uses boto3 directly, no CLI required.

```bash
cd samples/04-agent-as-tool/production

# Step 1: Open the notebook and run all cells (installs deps, creates IAM roles, deploys)
jupyter notebook production-deploy.ipynb

# Or deploy from the terminal:
python deploy.py --name-prefix m7       # deploys all runtimes (m7 is this module's prefix; m4 is taken by the optional Parallel Fork-Join)
python invoke.py <RUNTIME_ARN>          # single invocation (module 04; optional Dynamic Swarm and Capstone)

# Cleanup:
python cleanup.py --name-prefix m7 --dry-run   # preview
python cleanup.py --name-prefix m7             # delete all resources
```

For module 03, deploy from `samples/03-sequential-chain/production`, then run
`source .env_arns && python chain.py` there to coordinate its specialists locally.

What `deploy.py` creates per module:

| Resource | Detail |
|----------|--------|
| S3 bucket | `bedrock-agentcore-deploy-<account>-<region>` (stores code ZIPs) |
| IAM roles | `workshop-agentcore-<prefix>-runtime-role` and `workshop-agentcore-<prefix>-orchestrator-role` |
| AgentCore Runtimes | Module 03 and optional Parallel Fork-Join and Critic-Refiner: 2–3 A2A specialists (no HTTP orchestrator; `chain.py` coordinates locally) · Module 04 and optional Dynamic Swarm and Capstone: 1 HTTP orchestrator + A2A specialists |

---

## Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python | 3.10 or higher (3.13 recommended) |
| AWS credentials | Amazon Bedrock access. Enable models at [Bedrock console](https://console.aws.amazon.com/bedrock/). |
| Region | Read from `AWS_REGION` (falls back to your AWS CLI config region) - one region for all services, never hardcoded. Supported: us-east-1, us-east-2, us-west-2. |
| Core and optional production deployments | AWS credentials with AgentCore, IAM, and S3 permissions |
| Setup check | `python samples/shared/check_setup.py` verifies the local prerequisites above and makes one Bedrock call (`--model <MODEL_ID>` to test a different model) |

The core modules (02–04) pass no model, so they use the Strands SDK default on Amazon Bedrock: Claude Sonnet 4.6 through the global inference profile `global.anthropic.claude-sonnet-4-6` (strands-agents 1.65). The exception is module 03, which runs all three agents on Amazon Nova Lite (`amazon.nova-lite-v1:0`) on purpose: its graph fixes the routing, so a smaller model is enough. Each module's model cell or docstring shows how to switch to another model enabled in your account. The optional capstone (08) pins `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. See [available model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html).

---

## Frequently asked questions

**Do I need to complete the modules in order?**
Yes. Follow **02 → 03 → 04** for the core workshop: each module reuses the tools and decision brief from Module 2 and builds on the one before it. [01 Foundations](./samples/01-foundations/) is an optional primer on agent primitives, and the modules in [`samples/extra/`](./samples/extra/) are optional extensions; their READMEs list prerequisites.

**How long does the full workshop take?**
The core workshop targets 50 minutes. Optional modules in `samples/extra/` are outside that time budget; deploying resources and running all optional exercises requires additional time.

**What AWS services does this use?**
Amazon Bedrock (model inference), Amazon Bedrock AgentCore Runtime (managed agent hosting), Amazon S3 (code bundles), AWS IAM (execution roles), and Amazon CloudWatch (OTEL traces and logs).

**Do I need AgentCore to run the notebooks?**
No. The core and optional notebooks and `chat.py` scripts run locally with their module requirements and AWS Bedrock credentials. AgentCore Runtime is used only in the `production/` deploy folders.

**Can these patterns be used with other agent frameworks?**
Yes. Sequential Chain, Fork-Join, Critic-Refiner, Swarm, and Agent-as-Tool are general multi-agent design patterns. This workshop implements them with the Strands Agents SDK; the same concepts apply to other frameworks.

**Why do the specialists use A2A instead of HTTP?**
A2A (Agent-to-Agent) provides built-in agent discovery via agent cards, standard JSON-RPC communication, and session isolation, making it the right protocol for agent-to-agent calls. HTTP is used for the orchestrator because it receives plain JSON payloads from user-facing clients (boto3, chat.py). See [AgentCore A2A documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html).

---

## Resources

- [Strands Agents Documentation](https://strandsagents.com/docs/)
- [Strands Agents SDK on GitHub](https://github.com/strands-agents/sdk-python)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AgentCore Runtime A2A Protocol](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html)
- [Strands A2AAgent API Reference](https://strandsagents.com/docs/api/python/strands.agent.a2a_agent/index.md)
- [Strands GraphBuilder](https://strandsagents.com/docs/user-guide/sdk/multi-agent/graph/)
- [Deploy Strands Agents to AgentCore](https://strandsagents.com/docs/user-guide/sdk/deploy/deploy_to_bedrock_agentcore/)
- [Amazon Bedrock Model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)

---

## Contributing

Contributions are welcome! See [CONTRIBUTING](CONTRIBUTING.md) for more information.

---

## Security

If you discover a potential security issue in this project, notify AWS/Amazon Security via the [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

---

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.
