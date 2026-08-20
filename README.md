> **These are educational samples.** The code in this repository is designed for learning and experimentation. It is not intended for production use without additional hardening, security review, and adaptation to your specific requirements.

# Build Production Multi-Agent Systems with Strands Agents and Amazon Bedrock AgentCore

Build, deploy, and scale multi-agent systems using reusable patterns with the [Strands Agents SDK](https://strandsagents.com/docs/). Progress from a single-agent foundation through five production patterns: Sequential Chain, Parallel Fork-Join, Critic-Refiner, Dynamic Swarm, and Agent-as-Tool. Finish with a complete Decision-Memo system deployed on [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/).

![Strands Agents](https://img.shields.io/badge/Strands_Agents-SDK-FF9900?logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232F3E?logo=amazonaws&logoColor=white)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Patterns-01A88D?logo=amazonaws&logoColor=white)
![License MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)

---

## Modules

| Module | Description | Strands Pattern | Production Protocol |
|--------|-------------|-----------------|---------------------|
| [01 Foundations](./samples/01-foundations/) | Strands agent loop, tools, callback handlers, and the single-agent ceiling | `Agent(tools=[...])` | n/a |
| [02 Single Agent](./samples/02-single-agent/) | Multi-turn conversation with a single agent; session memory via `runtimeSessionId` | `Agent` + `SlidingWindowConversationManager` | n/a |
| [03 Sequential Chain](./samples/03-sequential-chain/) | Researcher → Analyst → Synthesizer in fixed order; each stage passes output to the next | [`GraphBuilder`](https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/index.md) DAG | `chain.py` local · Specialists: **A2A** |
| [04 Parallel Fork-Join](./samples/04-parallel-fork-join/) | Researcher feeds three analyzers running simultaneously; results merged at the synthesizer | `GraphBuilder` DAG + parallel edges | `chain.py` local · Specialists: **A2A** |
| [05 Critic-Refiner](./samples/05-critic-refiner/) | Writer drafts, Critic evaluates, memo cycles back until `APPROVED` | `GraphBuilder` cycle + `set_max_node_executions` | `chain.py` local · Specialists: **A2A** |
| [06 Dynamic Swarm](./samples/06-dynamic-swarm/) | Incident response: Monitor → Network Specialist / DB Admin → Resolver; path emerges at runtime | `Swarm` (local) · `Agent(tools=[...])` (prod) | Orchestrator: **HTTP** · Specialists: **A2A** |
| [07 Agent-as-Tool](./samples/07-agent-as-tool/) | Investment analysis: LLM orchestrator delegates to Research, Finance, Legal, Writer specialists as `@tool` | `@tool` wrapping `Agent` + `A2AAgent` | Orchestrator: **HTTP** · Specialists: **A2A** |
| [08 Capstone](./samples/08-capstone/) | All four patterns combined: 4 parallel heads → Program Revisor↔Critic loop → Leadership Memo | P2 + P3 + P5 + P1 | Orchestrator: **HTTP** · Specialists: **A2A** |

Each module from **03 to 08** includes a `production/` subfolder with a complete, deployable AgentCore Runtime architecture.

---

## What you'll build

The **Decision-Memo System**: a multi-agent pipeline that takes a decision brief (company, options, constraints) and produces an approved leadership memo covering options A/B/C, risks, success metrics, and a recommendation.

![Decision-Memo System: all four patterns combined](./samples/08-capstone/architecture.png)

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

Modules 03–08 each deploy **multiple AgentCore Runtimes** that communicate over two protocols:

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

References: [AgentCore A2A](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html) · [Strands A2AAgent](https://strandsagents.com/docs/api/python/strands.agent.a2a_agent/index.md) · [Deploy to AgentCore](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/)

---

## How to get started

### In AWS Workshop Studio

Open the workshop environment. All dependencies are pre-installed. Open any module notebook and run cells top to bottom.

### Locally

Clone this repository and navigate to any module:

```bash
cd samples/01-foundations
pip install -r requirements.txt
jupyter notebook module-01.ipynb
```

For production modules with deployed runtimes (06–08):

```bash
cd samples/06-dynamic-swarm/production
python chat.py --actor-id <your-id> --runtime-arn <RUNTIME_ARN>
```

---

## How to deploy a production module

Each module from 03 to 08 has a `production/` subfolder. The deployment uses boto3 directly, no CLI required.

```bash
cd samples/06-dynamic-swarm/production   # or 07, 08

# Step 1: Open the notebook and run all cells (installs deps, creates IAM roles, deploys)
jupyter notebook production-deploy.ipynb

# Or deploy from the terminal:
python deploy.py --name-prefix m6       # deploys all runtimes
python invoke.py <RUNTIME_ARN>          # single invocation (modules 06–08)

# Modules 03–05: chain.py coordinates locally after deploy
source .env_arns && python chain.py

# Cleanup:
python cleanup.py --name-prefix m6 --dry-run   # preview
python cleanup.py --name-prefix m6             # delete all resources
```

What `deploy.py` creates per module:

| Resource | Detail |
|----------|--------|
| S3 bucket | `bedrock-agentcore-deploy-<account>-<region>` (stores code ZIPs) |
| IAM roles | `workshop-agentcore-<prefix>-runtime-role` and `workshop-agentcore-<prefix>-orchestrator-role` |
| AgentCore Runtimes | Modules 03–05: 2–3 A2A specialists (no HTTP orchestrator — chain.py coordinates locally) · Modules 06–08: 1 HTTP orchestrator + A2A specialists |

---

## Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python | 3.10 or higher (3.13 recommended) |
| AWS credentials | Amazon Bedrock access. Enable models at [Bedrock console](https://console.aws.amazon.com/bedrock/). |
| Region | `us-east-1` (default). Set `AWS_REGION` env var to change. |
| Modules 03–08 production | AWS credentials with AgentCore, IAM, and S3 permissions |

The default model is **Claude Sonnet 4** via Amazon Bedrock cross-region inference. See [available model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html).

---

## Frequently asked questions

**Do I need to complete the modules in order?**
Yes. Modules build progressively. Module 01 covers Strands foundations; each subsequent module adds one pattern. The Capstone (Module 08) combines all patterns. Modules 03–07 can be explored in any order after Module 01.

**How long does the full workshop take?**
About 2 hours for all eight modules. Modules 01–02 (foundations) are 15 minutes each; pattern modules 03–07 are 20 minutes each; the Capstone (08) is 30 minutes.

**What AWS services does this use?**
Amazon Bedrock (model inference), Amazon Bedrock AgentCore Runtime (managed agent hosting), Amazon S3 (code bundles), AWS IAM (execution roles), and Amazon CloudWatch (OTEL traces and logs).

**Do I need AgentCore to run the notebooks?**
No. Modules 01–08 notebooks and `chat.py` scripts run locally with only `strands-agents` and AWS Bedrock credentials. AgentCore Runtime is used only in the `production/` deploy folders.

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
- [Strands GraphBuilder](https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/index.md)
- [Deploy Strands Agents to AgentCore](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/)
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
