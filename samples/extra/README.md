# Optional workshop modules

These modules extend the core workshop. Their original module numbers, notebooks,
interactive chats, diagrams, and production deployments are preserved.

The core path is [02 Single Agent](../02-single-agent/) →
[03 Sequential Chain](../03-sequential-chain/) →
[04 Agent-as-Tool](../04-agent-as-tool/), with
[01 Foundations](../01-foundations/) as an optional primer. The optional modules
here keep their original numbers, so `04-parallel-fork-join` is separate from core
module 04.

| Module | Focus |
|--------|-------|
| [04 Parallel Fork-Join](./04-parallel-fork-join/) | Concurrent graph branches and result aggregation |
| [05 Critic-Refiner](./05-critic-refiner/) | Bounded graph cycles for review and revision |
| [06 Dynamic Swarm](./06-dynamic-swarm/) | Autonomous specialist handoffs |
| [08 Capstone](./08-capstone/) | Combined patterns and AgentCore Memory |

Run each module from its own directory, for example:

```bash
cd samples/extra/04-parallel-fork-join
pip install -r requirements.txt
python chat.py
```

Deployment helpers remain in `samples/shared/`, and the fork-join module imports
its mock data tools from `samples/02-single-agent/`. Keep the repository together
when running these examples. See each module's `production/README.md` for deployment
and cleanup instructions.
