"""M3 Parallel Fork-Join: Orchestrator Runtime.
1. Calls Researcher Runtime (sequential)
2. Calls Analyzer Runtime 3 times in PARALLEL for Options A, B, C
3. Calls Synthesizer Runtime with merged analyses

One Analyzer Runtime is deployed and invoked 3 times concurrently.

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
"""
import asyncio, json, logging, os, uuid
import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp

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
        payload=json.dumps({"prompt": prompt}).encode(),
        qualifier="DEFAULT",
    )
    raw = resp["response"].read()
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode()


async def call_runtime_async(arn: str, session_id: str, prompt: str) -> str:
    """Non-blocking wrapper: runs invoke_agent_runtime in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_runtime, arn, session_id, prompt)


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    session_id = (context.session_id if context and hasattr(context, "session_id") else None) or str(uuid.uuid4())

    logger.info("session=%s | step=research", session_id)
    research = call_runtime(RESEARCHER_ARN, session_id,
                            f"Gather market data for this decision:\n{brief}")

    logger.info("session=%s | step=fork: 3 analyzers in parallel", session_id)

    async def fork():
        return await asyncio.gather(
            call_runtime_async(ANALYZER_ARN, session_id,
                f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research}"),
            call_runtime_async(ANALYZER_ARN, session_id,
                f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research}"),
            call_runtime_async(ANALYZER_ARN, session_id,
                f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research}"),
        )

    ra, rb, rc = asyncio.run(fork())
    all_analyses = f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"

    logger.info("session=%s | step=synthesize", session_id)
    memo = call_runtime(SYNTHESIZER_ARN, session_id,
                        f"Brief:\n{brief}\n\nResearch:\n{research}\n\nAnalyses:\n{all_analyses}")
    return memo


if __name__ == "__main__":
    app.run()
