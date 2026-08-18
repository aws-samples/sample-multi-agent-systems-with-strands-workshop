"""Decision-Memo Agent — Amazon Bedrock AgentCore Runtime entry point.

This file is the agent that gets deployed. It wraps the full Decision Intelligence
pipeline (Modules 1-7) behind a BedrockAgentCoreApp entry point.

The pipeline:
  P1 Sequential → P2 Parallel Fork-Join → P3 Critic-Refiner
  All coordinated by a P5 Agent-as-Tool orchestrator.

Usage:
  Local test:  python main.py  (runs app.run() — starts local HTTP server)
  Deploy:      agentcore deploy
  Invoke CLI:  agentcore invoke "Brief: NovaCart Premium Tier..."
  Invoke SDK:  boto3.client("bedrock-agentcore").invoke_agent_runtime(...)
"""

import asyncio
import json
import logging
import os

from strands import Agent, tool
from strands.multiagent import GraphBuilder
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from decision_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

# ── System prompts ─────────────────────────────────────────────────────────

RESEARCHER_PROMPT = (
    "You are a market research specialist. Use your tools to gather relevant data. "
    "Return structured findings — data only, no recommendations."
)

ANALYZER_PROMPT = (
    "You are a business strategy analyst. Evaluate the ONE option you are given: "
    "strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. "
    "100 words max."
)

WRITER_PROMPT = (
    "You are an executive memo writer. Write a COMPLETE leadership memo with:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C)\n"
    "## Top 3 Risks with specific mitigations\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who approves)\n"
    "If you receive feedback, revise and include ALL sections."
)

CRITIC_PROMPT = (
    "You are a quality critic. Check ONLY these 5 criteria:\n"
    "1. ## Recommendation section with a clear option choice\n"
    "2. ## Options at a Glance table comparing A, B, C\n"
    "3. ## Top 3 Risks with at least 3 risks each with a mitigation\n"
    "4. ## Success Metrics with at least 2 KPIs that have numeric targets\n"
    "5. ## Decision Required with owner AND deadline\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers missing]"
)

ORCHESTRATOR_PROMPT = (
    "You are a strategic decision analyst coordinating the Decision Intelligence pipeline.\n"
    "Steps:\n"
    "1. Call researcher_agent to gather market data.\n"
    "2. Call parallel_analyzers with the brief and research findings.\n"
    "3. Call critic_refiner with the brief and combined analyses.\n"
    "Execute all three steps in order."
)


# ── Specialist tools ───────────────────────────────────────────────────────


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.

    Args:
        topic: The decision topic or brief to research
    """
    worker = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    return str(worker(topic))


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    """Run all three option analyzers (A, B, C) simultaneously and return combined assessments.

    Args:
        brief: The original decision brief
        research_context: Research findings from researcher_agent
    """
    a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    async def fork():
        return await asyncio.gather(
            a.invoke_async(f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}"),
            b.invoke_async(f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}"),
            c.invoke_async(f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}"),
        )

    ra, rb, rc = asyncio.run(fork())
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    """Draft and quality-check the memo through a critic feedback loop. Returns approved memo.

    Args:
        brief: The original decision brief
        analyses: Combined option analyses from parallel_analyzers
    """
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

    result = builder.build()(f"Brief:\n{brief}\n\nAnalyses:\n{analyses}")
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result)
    return str(result)


# ── AgentCore entry point ──────────────────────────────────────────────────


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entry point.

    Receives a payload with a "prompt" key containing the decision brief.
    Returns the final approved leadership memo as a string.
    """
    # Accept both dict payload and raw string
    if isinstance(payload, dict):
        prompt = payload.get("prompt", "")
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            prompt = parsed.get("prompt", payload)
        except (json.JSONDecodeError, TypeError):
            prompt = payload
    else:
        prompt = str(payload)

    if not prompt:
        raise ValueError("Missing required field: prompt")

    logger.info("Processing decision brief (%d chars)", len(prompt))

    orchestrator = Agent(
        tools=[researcher_agent, parallel_analyzers, critic_refiner],
        system_prompt=ORCHESTRATOR_PROMPT,
        callback_handler=None,
    )
    result = orchestrator(prompt)
    return str(result).strip()


if __name__ == "__main__":
    app.run()
