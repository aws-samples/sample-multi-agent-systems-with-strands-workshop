"""
M7 Capstone: Orchestrator Runtime — with AgentCore Memory.

Architecture:
  User ──► Orchestrator (this runtime)
              ├── researcher_agent  → Researcher Runtime
              ├── parallel_analyzers → Analyzer Runtime ×3 (concurrent)
              └── critic_refiner    → Critic-Refiner Runtime

Session management:
  - actorId  : permanent user identity, arrives as custom HTTP header
                X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id
  - sessionId: unique conversation ID = runtimeSessionId from invoke_agent_runtime,
                arrives as context.session_id (injected by AgentCore service as
                X-Amzn-Bedrock-AgentCore-Runtime-Session-Id header)

Memory strategy:
  - MEMORY_ID set  → AgentCoreMemorySessionManager (STM + LTM, persists across sessions)
  - MEMORY_ID unset → SlidingWindowConversationManager (in-container only, no persistence)

The singleton is initialized on the FIRST call and reused for the container lifetime.
AgentCore routes all calls with the same runtimeSessionId to the same container,
so actor_id and session_id are stable for the container's lifetime.

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  CRITIC_REFINER_RUNTIME_ARN

Optional:
  BEDROCK_AGENTCORE_MEMORY_ID   — enables AgentCore Memory (STM + LTM)
  AWS_REGION                    — defaults to us-east-1
"""

import asyncio
import json
import logging
import os
import uuid

import boto3
from botocore.config import Config as BotocoreConfig

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

# ── Environment ───────────────────────────────────────────────────────────────
REGION             = os.environ.get("AWS_REGION", "us-east-1")
MEMORY_ID          = os.environ.get("BEDROCK_AGENTCORE_MEMORY_ID")   # optional
RESEARCHER_ARN     = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN       = os.environ["ANALYZER_RUNTIME_ARN"]
CRITIC_REFINER_ARN = os.environ["CRITIC_REFINER_RUNTIME_ARN"]

# The custom header name that carries the actorId into this container.
# Normalized to lowercase by AgentCore (HTTP/2 convention).
ACTOR_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

ORCHESTRATOR_PROMPT = (
    "Coordinate: 1.Call researcher_agent. "
    "2.Call parallel_analyzers with brief and research. "
    "3.Call critic_refiner with brief and analyses. Execute all three steps."
)

# ── Singletons (one per container lifetime) ───────────────────────────────────
_orchestrator = None     # Strands Agent — holds conversation history
_runtime_client = None   # boto3 client pre-wired with actor_id header
_actor_id: str = None    # captured on first invocation, stable for container lifetime


def _get_runtime_client():
    """Lazily create a boto3 bedrock-agentcore client that injects the actor_id
    custom header on every invoke_agent_runtime call.

    The header propagates the caller's identity to specialist runtimes so they
    can scope their own Memory operations to the same actor.
    """
    global _runtime_client, _actor_id
    if _runtime_client is None:
        # Capture actor_id from the current request context.
        # BedrockAgentCoreContext is a ContextVar set before the entrypoint runs.
        headers = BedrockAgentCoreContext.get_request_headers() or {}
        _actor_id = (
            headers.get(ACTOR_HEADER)
            or headers.get(ACTOR_HEADER.upper())
            or "default-user"
        )
        logger.info("actor_id captured for container lifetime: %s", _actor_id)

        _runtime_client = boto3.client(
            "bedrock-agentcore",
            region_name=REGION,
            config=BotocoreConfig(read_timeout=300),
        )
        # Register a hook that fires before each request is signed.
        # This injects X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id into
        # every invoke_agent_runtime call so specialist containers see the same actor_id.
        def _inject_actor_header(request, **kwargs):
            request.headers["X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id"] = _actor_id

        _runtime_client.meta.events.register_first(
            "before-sign.bedrock-agentcore.InvokeAgentRuntime",
            _inject_actor_header,
        )
    return _runtime_client


# ── Specialist invocation helpers ─────────────────────────────────────────────

def _call_runtime(arn: str, session_id: str, prompt: str) -> str:
    """Invoke a specialist AgentCore Runtime synchronously.

    Uses the same runtimeSessionId so the specialist container is kept warm
    for this session and the actor_id header flows to it.
    """
    client = _get_runtime_client()
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,       # routes to same specialist container
        payload=json.dumps({"prompt": prompt}).encode(),
        qualifier="DEFAULT",
    )
    raw = resp["response"].read()
    try:
        result = json.loads(raw)
        return result.get("response", result) if isinstance(result, dict) else str(result)
    except Exception:
        return raw.decode()


async def _call_runtime_async(arn: str, session_id: str, prompt: str) -> str:
    """Async wrapper — runs _call_runtime in a thread to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_runtime, arn, session_id, prompt)


# ── Tool definitions (module-level, stable references for Strands) ─────────────

@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.

    Args:
        topic: The decision topic to research.
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return _call_runtime(RESEARCHER_ARN, session_id, topic)


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    """Run all three option analyzers (A, B, C) simultaneously.

    Calls the Analyzer Runtime three times in parallel — one per pricing option.
    Returns combined analyses. Use AFTER researcher_agent.

    Args:
        brief:            The original decision brief.
        research_context: Research findings from researcher_agent.
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())

    async def _fork():
        return await asyncio.gather(
            _call_runtime_async(ANALYZER_ARN, session_id,
                f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}"),
            _call_runtime_async(ANALYZER_ARN, session_id,
                f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}"),
            _call_runtime_async(ANALYZER_ARN, session_id,
                f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}"),
        )

    ra, rb, rc = asyncio.run(_fork())
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    """Draft and quality-check the memo through the Critic-Refiner Runtime.

    Runs the Writer→Critic GraphBuilder loop. Returns the approved memo.
    Use AFTER parallel_analyzers.

    Args:
        brief:    The original brief.
        analyses: Combined analyses from parallel_analyzers.
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return _call_runtime(
        CRITIC_REFINER_ARN, session_id,
        f"Brief:\n{brief}\n\nAnalyses:\n{analyses}",
    )


# ── Orchestrator singleton ─────────────────────────────────────────────────────

def _get_orchestrator() -> Agent:
    """Lazily create the orchestrator Agent with the appropriate session manager.

    On first call:
    - actor_id is read from the custom header (via BedrockAgentCoreContext)
    - session_id is read from context.session_id (= runtimeSessionId)
    - AgentCoreMemorySessionManager or SlidingWindowConversationManager is configured
    - Agent is created and cached

    On subsequent calls in the same container: the cached Agent is returned.
    Its conversation history accumulates naturally — multi-turn just works.
    """
    global _orchestrator

    if _orchestrator is not None:
        return _orchestrator

    # Capture identifiers from the current request — stable for container lifetime.
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    # actor_id may not be set yet if _get_runtime_client() hasn't run — read it now.
    headers = BedrockAgentCoreContext.get_request_headers() or {}
    actor_id = (
        headers.get(ACTOR_HEADER)
        or headers.get(ACTOR_HEADER.upper())
        or "default-user"
    )
    logger.info("Initializing orchestrator: actor_id=%s session_id=%s memory_id=%s",
                actor_id, session_id, MEMORY_ID)

    if MEMORY_ID:
        # ── AgentCore Memory (STM + LTM) ──────────────────────────────────────
        # Conversation events are stored in short-term memory (STM) and
        # periodically extracted into long-term memory (LTM) by the Memory service.
        # Both the orchestrator and specialists use the same memory_id / actor_id /
        # session_id so they share the same conversation namespace.
        from bedrock_agentcore.memory.integrations.strands.config import (
            AgentCoreMemoryConfig,
            RetrievalConfig,
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager,
        )

        memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            # Retrieve facts about this actor from LTM before each user turn.
            retrieval_config={
                f"/facts/{actor_id}": RetrievalConfig(top_k=5, relevance_score=0.4),
            },
        )
        session_mgr = AgentCoreMemorySessionManager(memory_config, REGION)
        _orchestrator = Agent(
            tools=[researcher_agent, parallel_analyzers, critic_refiner],
            system_prompt=ORCHESTRATOR_PROMPT,
            session_manager=session_mgr,
            callback_handler=None,
        )
    else:
        # ── In-container sliding window (no external persistence) ──────────────
        # Keeps the last 20 turns in memory. History is lost when the container
        # spins down (after the idle session timeout). Sufficient for demos.
        from strands.agent.conversation_manager import SlidingWindowConversationManager

        _orchestrator = Agent(
            tools=[researcher_agent, parallel_analyzers, critic_refiner],
            system_prompt=ORCHESTRATOR_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=20),
            callback_handler=None,
        )

    return _orchestrator


# ── Entrypoint ─────────────────────────────────────────────────────────────────

@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # Ensure the runtime client is initialized (captures actor_id from headers).
    _get_runtime_client()

    # Get (or lazily create) the orchestrator and run the pipeline.
    result = _get_orchestrator()(brief)
    return str(result).strip()


if __name__ == "__main__":
    app.run()
