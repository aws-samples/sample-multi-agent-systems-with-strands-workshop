"""M7 Capstone — Orchestrator Runtime.
Coordinates the full Decision-Memo pipeline across specialist Runtimes:
  1. Researcher Runtime (sequential)
  2. Analyzer Runtime × 3 in PARALLEL (fork-join)
  3. Critic-Refiner Runtime (quality gate — single runtime, GraphBuilder cycle inside)

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  CRITIC_REFINER_RUNTIME_ARN
"""
import asyncio, json, logging, os, uuid
import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

agentcore = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))

RESEARCHER_ARN     = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN       = os.environ["ANALYZER_RUNTIME_ARN"]
CRITIC_REFINER_ARN = os.environ["CRITIC_REFINER_RUNTIME_ARN"]

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


async def call_runtime_async(arn, session_id, prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_runtime, arn, session_id, prompt)

_SESSION_ID = None


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.
    Args:
        topic: The decision topic to research
    """
    return call_runtime(RESEARCHER_ARN, _SESSION_ID, topic)


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    """Run all three option analyzers (A, B, C) simultaneously using the Analyzer Runtime.
    Returns combined analyses. Use AFTER researcher_agent.
    Args:
        brief: The original decision brief
        research_context: Research findings from researcher_agent
    """
    async def fork():
        return await asyncio.gather(
            call_runtime_async(ANALYZER_ARN, _SESSION_ID,
                f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}"),
            call_runtime_async(ANALYZER_ARN, _SESSION_ID,
                f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}"),
            call_runtime_async(ANALYZER_ARN, _SESSION_ID,
                f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}"),
        )
    ra, rb, rc = asyncio.run(fork())
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    """Draft and quality-check memo through Critic-Refiner Runtime (GraphBuilder cycle).
    Returns the final approved memo. Use AFTER parallel_analyzers.
    Args:
        brief: The original brief
        analyses: Combined analyses from parallel_analyzers
    """
    return call_runtime(CRITIC_REFINER_ARN, _SESSION_ID,
                        f"Brief:\n{brief}\n\nAnalyses:\n{analyses}")


ORCHESTRATOR_PROMPT = (
    "Coordinate: 1.Call researcher_agent. "
    "2.Call parallel_analyzers with brief and research. "
    "3.Call critic_refiner with brief and analyses. Execute all three steps."
)


@app.entrypoint
def invoke(payload, context):
    global _SESSION_ID
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    _SESSION_ID = payload.get("session_id", str(uuid.uuid4())) if isinstance(payload, dict) else str(uuid.uuid4())

    orchestrator = Agent(
        tools=[researcher_agent, parallel_analyzers, critic_refiner],
        system_prompt=ORCHESTRATOR_PROMPT,
        callback_handler=None,
    )
    return str(orchestrator(brief)).strip()


if __name__ == "__main__":
    app.run()
