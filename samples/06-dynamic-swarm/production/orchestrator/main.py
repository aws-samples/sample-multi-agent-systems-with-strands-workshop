"""
Dynamic Swarm Orchestrator (Pattern 4) — A2AAgent as tools.
A2AAgent not supported in Strands Swarm yet; Agent(tools=[]) achieves same semantics.
https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/#as-a-tool
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
Per-session isolation prevents history leaks across users.
"""
import asyncio, logging, os, threading
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

REGION         = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYST_ARN    = os.environ["ANALYST_RUNTIME_ARN"]
WRITER_ARN     = os.environ["WRITER_RUNTIME_ARN"]
ACTOR_HEADER   = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

ORCHESTRATOR_PROMPT = (
    "You coordinate a Dynamic Swarm. Agents hand off autonomously based on context.\n"
    "Typically: researcher_agent first for market data, then analyst_agent for evaluation, "
    "then writer_agent for the final memo. Adapt routing based on what each agent returns."
)

_researchers:   dict = {}
_analysts:      dict = {}
_writers:       dict = {}
_orchestrators: dict = {}


def _current_session() -> tuple:
    import uuid
    headers = BedrockAgentCoreContext.get_request_headers() or {}
    return (BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4()),
            headers.get(ACTOR_HEADER) or "default-user")


def _call_a2a(agent, prompt: str, timeout: int = 600) -> str:
    from a2a_utils import extract_a2a_text
    result_holder: list = [None, None]
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_holder[0] = loop.run_until_complete(agent.invoke_async(prompt))
        except Exception as exc:
            result_holder[1] = exc
        finally:
            loop.close()
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        raise TimeoutError(f"A2A call timed out after {timeout}s")
    if result_holder[1] is not None:
        raise result_holder[1]
    return extract_a2a_text(result_holder[0])


def _get_a2a(cache, arn, name, desc, aid):
    if aid not in cache:
        from strands.agent.a2a_agent import A2AAgent
        from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config
        a = A2AAgent(endpoint=a2a_endpoint(arn, REGION), client_config=make_a2a_config(aid, REGION),
                     name=name, description=desc)
        a._agent_card = build_agent_card(arn, name, desc, REGION)
        cache[aid] = a
    return cache[aid]


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, data, benchmarks, competitor intelligence. Call first.
    Args: topic: the decision topic."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_researchers, RESEARCHER_ARN, "researcher",
                               "Market research specialist.", aid), topic)


@tool
def analyst_agent(brief: str, research_context: str) -> str:
    """Analyze options A/B/C using research findings.
    Args: brief: decision brief. research_context: from researcher_agent."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_analysts, ANALYST_ARN, "analyst",
                               "Business strategy analyst.", aid),
                     f"Brief:\n{brief}\n\nResearch:\n{research_context}")


@tool
def writer_agent(brief: str, analyses: str) -> str:
    """Write the final leadership memo.
    Args: brief: decision brief. analyses: from analyst_agent."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_writers, WRITER_ARN, "writer",
                               "Executive memo writer.", aid),
                     f"Brief:\n{brief}\n\nAnalyses:\n{analyses}")


def _get_orchestrator(sid: str) -> Agent:
    if sid not in _orchestrators:
        _orchestrators[sid] = Agent(
            tools=[researcher_agent, analyst_agent, writer_agent],
            system_prompt=ORCHESTRATOR_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=20),
            callback_handler=None,
        )
    return _orchestrators[sid]


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    sid, _ = _current_session()
    return str(_get_orchestrator(sid)(brief)).strip()

if __name__ == "__main__":
    app.run()
