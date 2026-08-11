# Build a Production Multi-Agent System with Strands

Build, deploy, and scale agents with reusable multi-agent patterns using the [Strands Agents](https://strandsagents.com/latest/) SDK. Starting from a single orchestrator, you will progressively add specialized worker agents, cross-agent shared memory, quality guardrails, failure resilience, and production deployment to [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/).

![Strands Agents](https://img.shields.io/badge/Strands_Agents-SDK-FF9900?logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232F3E?logo=amazonaws&logoColor=white)
![re:Invent](https://img.shields.io/badge/AWS_re%3AInvent-2026-FF9900?logo=amazonaws&logoColor=white)
![License MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)

> This sample works with Strands Agents and Amazon Bedrock AgentCore. Code in this repository is provided "as is" and is not officially supported by Amazon.

---

## What you'll build

A multi-agent system composed of an orchestrator and specialized worker agents that solve a complex task together. Across 6 modules you will add one production capability per module — starting with task decomposition and worker delegation, and ending with a checkpointed, production-deployed system on AgentCore Runtime. Total time: about 95 minutes.

## Why multi-agent systems?

A single agent faces hard limits: a finite context window, a single model's reasoning ability, and no parallelism. Multi-agent systems solve this by decomposing complex tasks and delegating sub-tasks to specialized workers — each with its own context, tools, and model.

| Challenge | Single Agent | Multi-Agent System |
|-----------|-------------|-------------------|
| Complex tasks | Fits everything in one context | Decomposes into specialized sub-tasks |
| Parallelism | Sequential | Workers run concurrently |
| State across turns | Single session | Shared memory across agent boundaries |
| Failure scope | One failure = full failure | Isolated failure + graceful recovery |
| Observability | One trace | Per-agent traces + system-level view |

## Modules

| # | Module | Time | What you'll build |
|---|--------|------|-------------------|
| 1 | [Orchestrator + Worker Pattern](./samples/01-orchestrator-worker/) | 15 min | An orchestrator that decomposes tasks and delegates to specialized worker agents |
| 2 | [Shared State & Memory](./samples/02-shared-memory/) | 15 min | Cross-agent state passing and shared memory so workers collaborate without duplicating work |
| 3 | [Guardrails & Resilience](./samples/03-guardrails-resilience/) | 15 min | Quality guardrails and graceful failure handling at the multi-agent system level |
| 4 | [Deploy to AgentCore](./samples/04-deploy-agentcore/) | 20 min | Deploy the multi-agent system to Amazon Bedrock AgentCore Runtime |
| 5 | [Observability](./samples/05-observability/) | 15 min | Production traces, logs, and monitoring across all agent boundaries |
| 6 | [Checkpointing & Long-Running Workflows](./samples/06-checkpointing/) | 15 min | Checkpointing and resumable long-running multi-agent workflows |

Shared utilities and mock data used across modules live in [`samples/shared/`](./samples/shared/).

---

## How do I get started?

Open Module 1 and run the notebook cells from top to bottom. Each module's README explains the concept and links to the next.

```bash
# Clone the repo
git clone https://github.com/elizabethfuentes12/multi-agent-systems-with-strands-workshop.git
cd multi-agent-systems-with-strands-workshop
```

Then open [`samples/01-orchestrator-worker/`](./samples/01-orchestrator-worker/) in **VS Code** or **JupyterLab** and run the notebook.

## How do I set up the environment?

This workshop runs in a hosted VS Code environment with dependencies pre-installed. To run locally:

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (or use each module's requirements.txt)
pip install strands-agents bedrock-agentcore

# Configure AWS credentials (Strands uses Amazon Bedrock by default)
aws configure
```

Each module ships its own `requirements.txt` so you can install only what that module needs.

**Module 4 (Deploy) also needs the AgentCore CLI** (Node.js 20+):

```bash
sudo npm install -g @aws/agentcore
```

## What are the prerequisites?

| Requirement | Detail |
|-------------|--------|
| Python | 3.10 or higher |
| AWS credentials | Amazon Bedrock model access for Claude Sonnet 4 |
| Deploy module (Module 4) | Node.js 20+, the `@aws/agentcore` CLI, `uv`, and AWS CDK; provisions AgentCore Runtime + S3 via CloudFormation |

---

## How does multi-agent delegation work in Strands?

In Strands, an agent can call another agent as a tool. The orchestrator receives a task, decides which worker to delegate to, calls it like any other tool, and gets back the result — no manual routing wiring required.

```python
from strands import Agent, tool

# A specialized worker agent exposed as a tool
@tool
def research_worker(topic: str) -> str:
    """Research a topic in depth and return a structured summary."""
    worker = Agent(tools=[web_search, summarize], system_prompt=RESEARCH_PROMPT)
    return str(worker(topic))

# The orchestrator delegates to the worker
orchestrator = Agent(
    tools=[research_worker, analysis_worker, writer_worker],
    system_prompt=ORCHESTRATOR_PROMPT
)
orchestrator("Produce a technical brief on quantum error correction.")
```

See [Module 1](./samples/01-orchestrator-worker/) for the full pattern and a live trace of the delegation loop.

---

## Frequently asked questions

**Do I need to complete the modules in order?**
Yes — Modules 1 through 6 build on each other. Module 1 establishes the base multi-agent system; each subsequent module adds one production capability to the same system.

**Which Claude model does this use?**
The modules default to Claude Sonnet 4 via Amazon Bedrock. You need Bedrock model access enabled in your AWS account.

**Can I run this locally without AWS credentials, using Ollama?**
Yes. Install [Ollama](https://ollama.com/download), pull a model with tool use support, then pass `OllamaModel` to `Agent(...)`:

```python
from strands import Agent
from strands.models import OllamaModel

model = OllamaModel(host="http://localhost:11434", model_id="llama3.1")
agent = Agent(model=model, tools=[...], system_prompt=...)
```

Each notebook includes a commented Ollama example.

**I'm using AWS-provided credits from a sponsored event — how do I use them?**
AWS credits issued for workshops typically cover Amazon Nova models. To switch:

```python
from strands.models import BedrockModel

model = BedrockModel(model_id="amazon.nova-pro-v1:0")
agent = Agent(model=model, tools=[...], system_prompt=...)
```

**Can I apply these patterns to other agent frameworks?**
Yes. Orchestrator-worker delegation, cross-agent memory, guardrails, and checkpointing are general multi-agent design patterns. This workshop implements them with the Strands Agents SDK; the same concepts transfer to other frameworks.

**How long does the full workshop take?**
About 95 minutes for all 6 modules. Each module is self-contained and takes 15–20 minutes.

**What AWS services are used?**
- Amazon Bedrock (all modules) — model inference
- Amazon Bedrock AgentCore Runtime (Module 4+) — managed agent hosting
- Amazon S3 (Module 4+) — artifact staging and checkpoints
- Amazon CloudWatch (Module 5) — traces and logs

---

## Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [Strands Agents SDK on GitHub](https://github.com/strands-agents/sdk-python)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [Multi-Agent Patterns — Strands Docs](https://strandsagents.com/latest/user-guide/concepts/multi-agent/multi-agent-systems/)
- [Amazon Bedrock AgentCore Harness](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html)

---

## Contributing

Contributions are welcome! See [CONTRIBUTING](CONTRIBUTING.md) for more information.

---

## Security

If you discover a potential security issue in this project, notify AWS/Amazon Security via the [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

---

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.
