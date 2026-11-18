"""Module 4 production, single-runtime variant: Agent-as-Tool on AgentCore Runtime.

Pattern: an LLM orchestrator delegates to Research, Finance, Legal and Writer specialists
used as tools: the same prompts and tools as module-04.ipynb, served as ONE AgentCore
HTTP runtime. All agents run in this process. The LLM decides the routing.

deploy.py does not deploy this file: it deploys each specialist as its own A2A runtime
plus orchestrator/main.py. Use this file when you want everything behind one endpoint.

Local test:  python main.py   (serves the AgentCore HTTP contract on port 8080)
"""
import logging
import threading
import uuid

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from opentelemetry import baggage, context as otel_context
from strands import Agent, tool

# Mock business intelligence tools (a copy of ../../02-single-agent/decision_brief_tools.py,
# so the container is self-contained). Replace with a live data source, for example
# AgentCore Gateway with the Web Search connector:
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html
from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

RESEARCH_PROMPT = (
    "You are a market research specialist. Use your tools to gather company data, "
    "industry benchmarks, and competitive intelligence. Return structured findings: data only."
)

FINANCE_PROMPT = (
    "You are a financial analyst. Analyze the investment brief and market data provided. "
    "Return: revenue projections, unit economics (CAC, LTV, payback period), "
    "ROI estimate, capital efficiency, and a financial verdict (Invest / Invest with conditions / Pass). "
    "Be specific with numbers. 200 words max."
)

LEGAL_PROMPT = (
    "You are a legal and compliance reviewer. Review the investment brief for: "
    "regulatory risks, data privacy concerns (GDPR, CCPA), contractual obligations, "
    "IP considerations, and any red flags for due diligence. "
    "Return a bullet-point list of legal risks with severity (High/Medium/Low). 150 words max."
)

WRITER_PROMPT = (
    "You are an investment memo writer. You receive the brief, research findings, financial "
    "analysis, and legal review. Produce a professional investment analysis memo:\n"
    "## Executive Summary (recommendation in one sentence)\n"
    "## Market Opportunity (size, growth, competitive position)\n"
    "## Financial Highlights (key metrics, ROI, projections)\n"
    "## Risk Assessment (top 3 risks with mitigations)\n"
    "## Recommendation (Invest / Invest with conditions / Pass, terms, conditions)\n"
    "Under 450 words. Be direct."
)

ORCHESTRATOR_PROMPT = (
    "You are an investment committee coordinator. For each investment request:\n"
    "1. Call research_agent to gather company and market data.\n"
    "2. Call finance_agent with the brief and research findings to get financial analysis.\n"
    "3. Call legal_agent with the brief to identify legal and compliance risks.\n"
    "4. Call writer_agent LAST, on its own, with one input that contains the brief, the research "
    "findings, the financial analysis, and the legal review. Its memo goes to the user as-is.\n"
    "For a follow-up question you can answer from the conversation so far, answer directly "
    "without calling the specialists again."
)


@tool
def research_agent(topic: str) -> str:
    """Gather market data, company metrics, and competitive intelligence for an investment topic.

    Args:
        topic: The company or investment topic to research
    """
    worker = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCH_PROMPT,
        callback_handler=None,
    )
    return str(worker(topic))


@tool
def finance_agent(brief: str, research_context: str) -> str:
    """Analyze financial viability: ROI, unit economics, projections, and investment verdict.

    Args:
        brief: The original investment brief
        research_context: Market and company data from research_agent
    """
    worker = Agent(system_prompt=FINANCE_PROMPT, callback_handler=None)
    return str(worker(f"Investment brief:\n{brief}\n\nMarket research:\n{research_context}"))


@tool
def legal_agent(brief: str) -> str:
    """Review legal and compliance risks: regulatory exposure, data privacy, IP, due diligence flags.

    Args:
        brief: The investment brief to review
    """
    worker = Agent(system_prompt=LEGAL_PROMPT, callback_handler=None)
    return str(worker(brief))


# The writer is an Agent turned into a tool with .as_tool(). delegate=True makes its memo
# the orchestrator's final answer: no extra orchestrator model call rewrites it, and the
# memo streams once through the orchestrator. preserve_context=False (the default) resets
# the writer before every call, like the fresh workers above.
writer = Agent(
    name="writer_agent",
    system_prompt=WRITER_PROMPT,
    callback_handler=None,
)
writer_agent = writer.as_tool(
    description=(
        "Write the final investment memo from the brief, research findings, financial analysis, "
        "and legal review. Call this LAST, after research_agent, finance_agent, and legal_agent."
    ),
    delegate=True,
)


# One orchestrator per session, so different users never share conversation history.
_session_agents: dict = {}
_session_lock = threading.Lock()


def _get_session_agent(session_id: str) -> Agent:
    with _session_lock:
        if session_id not in _session_agents:
            _session_agents[session_id] = Agent(
                tools=[research_agent, finance_agent, legal_agent, writer_agent],
                system_prompt=ORCHESTRATOR_PROMPT,
                context_manager="auto",
                callback_handler=None,
            )
        return _session_agents[session_id]


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt") if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # OTEL: propagate the session ID across all spans.
    session_id = getattr(context, "session_id", None) or str(uuid.uuid4())
    token = otel_context.attach(baggage.set_baggage("session.id", session_id))
    logger.info("session.id=%s module=m7-agent-as-tool", session_id)
    try:
        return str(_get_session_agent(session_id)(brief)).strip()
    finally:
        otel_context.detach(token)


if __name__ == "__main__":
    app.run()
