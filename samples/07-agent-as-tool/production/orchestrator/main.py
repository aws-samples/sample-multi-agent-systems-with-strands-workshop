"""M6 Agent-as-Tool: Orchestrator Runtime.
Uses a Strands Agent that treats specialist Runtimes as callable @tool functions.
The LLM decides routing and argument construction: no explicit Python routing.

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
"""
import json, logging, os, uuid
import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

agentcore = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))

RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN    = os.environ["ANALYZER_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]

def call_runtime(arn: str, session_id: str, prompt: str) -> str:
    """Invoke a specialist AgentCore Runtime and return its text response."""
    resp = agentcore.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt, "session_id": session_id}).encode(),
        qualifier="DEFAULT",
    )
    raw = resp["response"].read()
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode()

# Runtime ARNs are captured in the closure below
_SESSION_ID = None


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitor intelligence.
    Args:
        topic: The decision topic to research
    """
    return call_runtime(RESEARCHER_ARN, _SESSION_ID, topic)


@tool
def analyzer_agent(option_name: str, option_description: str, research_context: str) -> str:
    """Analyze one specific decision option. Call once per option (A, B, C).
    Args:
        option_name: Short name (e.g. "Option A")
        option_description: Full description with price and approach
        research_context: Research findings from researcher_agent
    """
    return call_runtime(ANALYZER_ARN, _SESSION_ID,
                        f"Option: {option_name}\nDesc: {option_description}\nResearch: {research_context}")


@tool
def synthesizer_agent(decision_brief: str, all_analyses: str) -> str:
    """Synthesize all option analyses into a leadership memo. Call AFTER all three analyses.
    Args:
        decision_brief: The original brief
        all_analyses: Combined analyses of all three options
    """
    return call_runtime(SYNTHESIZER_ARN, _SESSION_ID,
                        f"Brief:\n{decision_brief}\n\nAnalyses:\n{all_analyses}")


ORCHESTRATOR_PROMPT = (
    "Coordinate: 1.Call researcher_agent. "
    "2.Call analyzer_agent three times (A, B, C) with research context. "
    "3.Call synthesizer_agent with all analyses. Execute all steps."
)

_orchestrator = None


def get_orchestrator() -> Agent:
    """Lazy singleton — created once per container lifetime.

    Uses SlidingWindowConversationManager (in-container, no external persistence).
    Multi-turn works while the container is warm (same runtimeSessionId).
    """
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
    # context.session_id = runtimeSessionId (injected as header by AgentCore service)
    # _SESSION_ID used by @tool functions to chain the same session to specialist runtimes
    global _SESSION_ID
    _SESSION_ID = context.session_id if context and hasattr(context, "session_id") else str(uuid.uuid4())
    return str(get_orchestrator()(brief)).strip()


if __name__ == "__main__":
    app.run()
