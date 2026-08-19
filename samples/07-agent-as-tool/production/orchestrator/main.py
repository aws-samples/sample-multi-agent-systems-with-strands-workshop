"""M6 Agent-as-Tool: Orchestrator Runtime.
Uses a Strands Agent that treats specialist Runtimes as callable @tool functions.
The LLM decides routing and argument construction: no explicit Python routing.

Session management:
  - actorId  : arrives as custom HTTP header
                X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id
  - sessionId: = runtimeSessionId, arrives as context.session_id

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
"""
import json, logging, os, uuid
import boto3
from botocore.config import Config as BotocoreConfig

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

REGION          = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN    = os.environ["ANALYZER_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]

ACTOR_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

ORCHESTRATOR_PROMPT = (
    "Coordinate: 1.Call researcher_agent. "
    "2.Call analyzer_agent three times (A, B, C) with research context. "
    "3.Call synthesizer_agent with all analyses. Execute all steps."
)

# ── Singletons (one per container lifetime) ───────────────────────────────────
_orchestrator   = None
_runtime_client = None
_actor_id: str  = None


def _get_runtime_client():
    """Lazily create a boto3 client that injects actorId header on every call."""
    global _runtime_client, _actor_id
    if _runtime_client is None:
        headers  = BedrockAgentCoreContext.get_request_headers() or {}
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

        def _inject_actor_header(request, **kwargs):
            request.headers["X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id"] = _actor_id

        _runtime_client.meta.events.register_first(
            "before-sign.bedrock-agentcore.InvokeAgentRuntime",
            _inject_actor_header,
        )
    return _runtime_client


def _call_runtime(arn: str, session_id: str, prompt: str) -> str:
    """Invoke a specialist Runtime via boto3. session_id travels only as runtimeSessionId."""
    client = _get_runtime_client()
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt}).encode(),
        qualifier="DEFAULT",
    )
    raw = resp["response"].read()
    try:
        result = json.loads(raw)
        return result.get("response", result) if isinstance(result, dict) else str(result)
    except Exception:
        return raw.decode()


# ── Tool definitions ──────────────────────────────────────────────────────────

@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.
    Args:
        topic: The decision topic to research.
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return _call_runtime(RESEARCHER_ARN, session_id, topic)


@tool
def analyzer_agent(option_name: str, option_description: str, research_context: str) -> str:
    """Analyze one specific decision option. Call once per option (A, B, C).
    Args:
        option_name: Short name (e.g. "Option A")
        option_description: Full description with price and approach
        research_context: Research findings from researcher_agent
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return _call_runtime(
        ANALYZER_ARN, session_id,
        f"Option: {option_name}\nDesc: {option_description}\nResearch: {research_context}",
    )


@tool
def synthesizer_agent(decision_brief: str, all_analyses: str) -> str:
    """Synthesize all option analyses into a leadership memo. Call AFTER all three analyses.
    Args:
        decision_brief: The original brief
        all_analyses: Combined analyses of all three options
    """
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return _call_runtime(
        SYNTHESIZER_ARN, session_id,
        f"Brief:\n{decision_brief}\n\nAnalyses:\n{all_analyses}",
    )


# ── Orchestrator singleton ────────────────────────────────────────────────────

def _get_orchestrator() -> Agent:
    """Lazy singleton — created once per container lifetime with SlidingWindowConversationManager."""
    global _orchestrator
    if _orchestrator is None:
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        _orchestrator = Agent(
            tools=[researcher_agent, analyzer_agent, synthesizer_agent],
            system_prompt=ORCHESTRATOR_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=20),
            callback_handler=None,
        )
    return _orchestrator


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    _get_runtime_client()   # captures actor_id from request headers on first call
    result = _get_orchestrator()(brief)
    return str(result).strip()


if __name__ == "__main__":
    app.run()
