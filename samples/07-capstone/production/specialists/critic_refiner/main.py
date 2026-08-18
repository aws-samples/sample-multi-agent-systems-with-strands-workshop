"""Critic-Refiner specialist Runtime.
Receives brief + analyses and runs the GraphBuilder Writer→Critic quality loop.
Returns the final approved memo. Deployed as single runtime — SDK manages cycle state.
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.multiagent import GraphBuilder

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

WRITER_PROMPT = (
    "Write a COMPLETE leadership memo with all 5 sections: "
    "## Recommendation, ## Options at a Glance (table A/B/C), ## Top 3 Risks+mitigations, "
    "## Success Metrics (numeric targets), ## Decision Required. Revise if given feedback."
)
CRITIC_PROMPT = (
    "Check: 1)Recommendation 2)Options table A/B/C 3)3 Risks+mitigations "
    "4)2+ Metrics with targets 5)Decision Required owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers missing]"
)


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not prompt:
        raise ValueError("Missing required field: prompt")

    writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None)
    critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None)

    def needs_revision(state):
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(writer, "writer")
    builder.add_node(critic, "critic")
    builder.set_entry_point("writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(120)
    builder.reset_on_revisit(True)

    result = builder.build()(prompt)
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result).strip()
    return str(result).strip()


if __name__ == "__main__":
    app.run()
