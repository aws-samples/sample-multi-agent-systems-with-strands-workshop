# Build Production Multi-Agent Systems with Strands Agents and Amazon Bedrock AgentCore

Build, deploy, and scale multi-agent systems using reusable patterns with the [Strands Agents SDK](https://strandsagents.com/latest/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el). Progress from a single-agent ceiling through five production patterns - Sequential Chain, Parallel Fork-Join, Critic-Refiner, Dynamic Swarm, and Agent-as-Tool - finishing with a deployed Decision-Memo system on [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el).

![Strands Agents](https://img.shields.io/badge/Strands_Agents-SDK-FF9900?logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232F3E?logo=amazonaws&logoColor=white)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Patterns-01A88D?logo=amazonaws&logoColor=white)
![License MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)

## Modules

| Module | Description | Pattern | Stack |
|--------|-------------|---------|-------|
| [01 Strands Foundations](./samples/01-strands-foundations/) | Single agent with tools, loop inspection, and the single-agent ceiling | Foundations | ![Strands](https://img.shields.io/badge/Strands-Agent-FF9900) |
| [02 Sequential Chain](./samples/02-sequential-chain/) | Research → Analyst → Synthesizer pipeline; each stage passes output to the next | Pattern 1 | ![Strands](https://img.shields.io/badge/Strands-Sequential-FF9900) |
| [03 Parallel Fork-Join](./samples/03-parallel-fork-join/) | Three option analyzers run simultaneously via `asyncio.gather`; results merged | Pattern 2 | ![Strands](https://img.shields.io/badge/Strands-Parallel-FF9900) |
| [04 Critic-Refiner](./samples/04-critic-refiner/) | Writer drafts, Critic evaluates, memo cycles back until approved - `GraphBuilder` cycle | Pattern 3 | ![Strands](https://img.shields.io/badge/Strands-GraphBuilder-FF9900) |
| [05 Dynamic Swarm](./samples/05-dynamic-swarm/) | Agents hand off autonomously; routing emerges at runtime - no fixed path | Pattern 4 | ![Strands](https://img.shields.io/badge/Strands-Swarm-FF9900) |
| [06 Agent-as-Tool](./samples/06-agent-as-tool/) | LLM orchestrator delegates to specialist agents wrapped as `@tool` functions | Pattern 5 | ![Strands](https://img.shields.io/badge/Strands-AgentTool-FF9900) |
| [07 Capstone](./samples/07-capstone/) | Decision-Memo System combining all four patterns; deploys to AgentCore Runtime | P1+P2+P3+P5 | ![AgentCore](https://img.shields.io/badge/AgentCore-Runtime-01A88D) |

Each module from **02 to 07** includes a `production/` subfolder - a self-contained AgentCore Runtime ready for `agentcore deploy`.

---

## What you'll build

The **Decision-Memo System** - a multi-agent pipeline that takes a decision brief (company, options, constraints) and produces an approved leadership memo with options A/B/C, risks, success metrics, and a recommendation.

```
Decision Brief (input)
  "Evaluate NovaCart Premium Tier. Target: +15% CLV."
         │
         ▼ Orchestrator (P5: Agent-as-Tool)
  ┌─────────────┐
  │  Researcher │  P1 Sequential - gathers data with tools
  └──────┬──────┘
         │
   ┌─────┴─────┬──────────┐
   ▼           ▼          ▼    P2 Fork-Join - all 3 run in parallel
 Analyzer A  Analyzer B  Analyzer C
   └─────┬─────┴──────────┘
         │
  ┌──────▼──────┐
  │   Writer    │  P3 Critic-Refiner - cycles until APPROVED
  │   Critic    │
  └──────┬──────┘
         ▼
   Leadership Memo (output)
```

---

## Why multi-agent systems?

A single agent faces hard limits: a finite context window, one model's reasoning, and no parallelism. Multi-agent systems decompose complex tasks and delegate to specialists.

| Challenge | Single Agent | Multi-Agent System |
|-----------|-------------|-------------------|
| Complex tasks | One context for everything | Decomposes into focused sub-tasks |
| Parallelism | Sequential only | Workers run concurrently |
| Quality control | Hope the output is good | Critic enforces a quality gate |
| Failure scope | One failure = full failure | Isolated failure, graceful recovery |
| Observability | One trace | Per-agent OTEL traces + system view |

> The same patterns - Sequential Chain, Fork-Join, Critic-Refiner, Swarm, and Agent-as-Tool - are general multi-agent design concepts and apply to other agent frameworks.

---

## How do I get started?

Open Module 1 in VS Code or JupyterLab and run cells top to bottom. Each module's README explains the concept and links to the next.

```bash
git clone https://github.com/elizabethfuentes12/multi-agent-systems-with-strands-workshop.git
cd multi-agent-systems-with-strands-workshop
```

Then open `samples/01-strands-foundations/` and run `module-01.ipynb`.

---

## Which Amazon Bedrock model does this use?

This workshop uses **[Amazon Bedrock](https://aws.amazon.com/bedrock/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)** as the model provider. The default model is Claude Sonnet 4.
To change the model ID, pass `model=BedrockModel(model_id="<MODEL_ID>")` to `Agent(...)`.
See all available model IDs: [Amazon Bedrock model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)
See pricing: [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)

---

## How do I set up the environment?

This workshop runs in a hosted VS Code environment (AWS Workshop Studio) with all dependencies pre-installed. To run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install strands-agents bedrock-agentcore nest-asyncio
aws configure   # Strands uses Amazon Bedrock by default
```

Each module has its own `requirements.txt`. Install only what you need:

```bash
cd samples/02-sequential-chain
pip install -r requirements.txt
```

### Deploy modules require the AgentCore CLI (Node.js 20+)

```bash
sudo npm install -g @aws/agentcore
```

---

## What are the prerequisites?

| Requirement | Detail |
|-------------|--------|
| Python | 3.10 or higher (3.13 recommended) |
| AWS credentials | Amazon Bedrock access - see [model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el) for the full list |
| Modules 02–07 production | `@aws/agentcore` CLI (npm), `uv`, AWS CDK |

---

## How does multi-agent delegation work in Strands?

In Strands, an agent wrapped as a `@tool` can be called by an orchestrator like any other function. The LLM reads the docstring to decide when to call it and what arguments to pass.

```python
from strands import Agent, tool

@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, and competitor intelligence.
    Args:
        topic: The decision topic to research
    """
    worker = Agent(tools=[get_company_data, get_benchmarks], system_prompt=RESEARCHER_PROMPT,
                   callback_handler=None)
    return str(worker(topic))

orchestrator = Agent(
    tools=[researcher_agent, analyzer_agent, synthesizer_agent],
    system_prompt=ORCHESTRATOR_PROMPT,
)
orchestrator("Evaluate NovaCart Premium Tier launch - brief attached.")
```

---

## How do I deploy a module to Amazon Bedrock AgentCore?

Each module from 02 to 07 has a `production/` subfolder - a self-contained AgentCore Runtime. Deploy any of them:

```bash
cd samples/02-sequential-chain/production/

agentcore create                  # name the project
cd <project-name>
agentcore add                     # Bring my own code → entrypoint: main.py

cp ../main.py ../mock_tools.py ../requirements.txt app/<AgentName>/
cd app/<AgentName>
uv init --bare --python 3.13
uv add strands-agents bedrock-agentcore aws-opentelemetry-distro boto3
cd ../..

agentcore deploy
agentcore invoke "Evaluate NovaCart Premium Tier..."
```

### How do I clean up AWS resources after the workshop?

```bash
# Inside the project folder:
agentcore remove all -y   # resets local config
agentcore deploy          # removes the Runtime and CDK stack from AWS
```

---

## Frequently asked questions

**Do I need to complete the modules in order?**
Yes - modules build progressively. Module 1 covers Strands foundations; each subsequent module adds one pattern. The Capstone (Module 7) combines all four patterns.

**How long does the full workshop take?**
About 90 minutes for all seven modules. Each module runs 15–20 minutes. Module 1 (foundations) and Module 7 (capstone) are essential; the pattern modules (02–06) can be explored in any order after Module 1.

**What AWS services does this use?**
Amazon Bedrock (model inference), Amazon Bedrock AgentCore Runtime (managed agent hosting), Amazon CloudWatch (OTEL traces and logs), and AWS CDK (infrastructure provisioning for production modules).

**Do I need AgentCore to run the notebooks?**
No. Modules 01–07 notebooks and `chat.py` scripts run locally with only `strands-agents` and AWS Bedrock credentials. AgentCore Runtime is used only in the `production/` deploy folders.

**Can these patterns be used with other agent frameworks?**
Yes. Sequential Chain, Fork-Join, Critic-Refiner, Swarm, and Agent-as-Tool are general multi-agent design patterns. This workshop implements them with the Strands Agents SDK; the same concepts apply to other frameworks.

---

## Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)
- [Strands Agents SDK on GitHub](https://github.com/strands-agents/sdk-python)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)
- [Multi-Agent Patterns - Strands Docs](https://strandsagents.com/latest/user-guide/concepts/multi-agent/multi-agent-systems/?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)
- [AgentCore Web Search Connector](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html?trk=87c4c426-cddf-4799-a299-273337552ad8&sc_channel=el)

---

## Contributing

Contributions are welcome! See [CONTRIBUTING](CONTRIBUTING.md) for more information.

---

## Security

If you discover a potential security issue in this project, notify AWS/Amazon Security via the [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

---

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.
