"""M2 Sequential Chain: Orchestrator Runtime.
Calls Researcher → Analyst → Synthesizer Runtimes in sequence.
Each specialist Runtime is deployed separately and its ARN is injected via env vars.

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYST_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
"""
import json, logging, os, uuid
import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

agentcore = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))

RESEARCHER_ARN   = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYST_ARN      = os.environ["ANALYST_RUNTIME_ARN"]
SYNTHESIZER_ARN  = os.environ["SYNTHESIZER_RUNTIME_ARN"]

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


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    session_id = (context.session_id if context and hasattr(context, "session_id") else None) or str(uuid.uuid4())

    logger.info("session=%s | step=research", session_id)
    research = call_runtime(RESEARCHER_ARN, session_id,
                            f"Gather market data for this decision:\n{brief}")

    logger.info("session=%s | step=analyze", session_id)
    analysis = call_runtime(ANALYST_ARN, session_id,
                            f"Brief:\n{brief}\n\nResearch findings:\n{research}")

    logger.info("session=%s | step=synthesize", session_id)
    memo = call_runtime(SYNTHESIZER_ARN, session_id,
                        f"Brief:\n{brief}\n\nResearch:\n{research}\n\nAnalysis:\n{analysis}")

    return memo


if __name__ == "__main__":
    app.run()
