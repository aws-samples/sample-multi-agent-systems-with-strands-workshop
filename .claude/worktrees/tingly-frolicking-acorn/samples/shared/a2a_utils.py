"""
Shared utilities for A2A-based AgentCore Runtime communication.

Architecture:
  Specialists: serve_a2a(StrandsA2AExecutor(agent)) — port 9000, protocol A2A
  Orchestrators: A2AAgent with SigV4 auth calling specialist runtimes

References:
  AWS docs A2A: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
  Strands A2A:  https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/
  A2A protocol: https://a2aproject.github.io/A2A/latest/
"""
import os
from urllib.parse import quote

import boto3
import httpx
from a2a.client import ClientConfig
from bedrock_agentcore.runtime.a2a import build_runtime_url
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest as BotocoreRequest

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Headers injected by the orchestrator on every A2A call to a specialist.
# SESSION_HEADER is also set by the AgentCore platform automatically, but we
# set it explicitly so the specialist sees it in context.request_headers.
SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"
ACTOR_HEADER   = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"


def a2a_endpoint(arn: str, region: str = REGION) -> str:
    """Return the A2A invocation URL for an AgentCore Runtime.

    AgentCore proxies JSON-RPC 2.0 messages to the specialist container on
    port 9000. The agent card lives at <endpoint>/.well-known/agent-card.json.

    See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
    """
    return build_runtime_url(arn, region)


class AgentCoreA2AAuth(httpx.Auth):
    """SigV4 authentication for AgentCore A2A calls.

    Signs every outbound request with AWS SigV4 and propagates:
    - X-Amzn-Bedrock-AgentCore-Runtime-Session-Id  (session affinity)
    - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id  (Memory scoping)

    The session ID is read from BedrockAgentCoreContext (set per request by
    BedrockAgentCoreApp) so it is always the current runtimeSessionId without
    hardcoding or passing it through payloads.

    See SigV4 auth: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
    """

    def __init__(self, actor_id: str = "default-user", region: str = REGION):
        self.actor_id = actor_id
        self.region   = region

    def auth_flow(self, request: httpx.Request):
        # --- SigV4 signing -------------------------------------------------
        session     = boto3.Session()
        credentials = session.get_credentials().get_frozen_credentials()

        # Build a botocore request for signing (botocore handles canonical
        # request construction, date headers, and HMAC-SHA256 signing).
        aws_req = BotocoreRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers={
                k: v for k, v in request.headers.items()
                # botocore recalculates Host and content-length itself
                if k.lower() not in ("host", "content-length", "transfer-encoding")
            },
        )
        SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(aws_req)
        for k, v in aws_req.headers.items():
            request.headers[k] = v

        # --- Session ID propagation ----------------------------------------
        # Propagate the current runtimeSessionId so the specialist container
        # routes this A2A request to the same session instance.
        try:
            from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
            sid = BedrockAgentCoreContext.get_session_id()
            if sid:
                request.headers[SESSION_HEADER] = sid
        except Exception:
            pass

        # --- Actor ID propagation ------------------------------------------
        # Propagate the actor identity for specialists that use Memory.
        if self.actor_id:
            request.headers["X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id"] = self.actor_id

        yield request


def make_a2a_config(actor_id: str = "default-user", region: str = REGION) -> ClientConfig:
    """Create a Strands A2A ClientConfig with SigV4 auth for AgentCore calls.

    The returned config can be passed to A2AAgent(client_config=...) to
    authenticate calls to AgentCore Runtime A2A endpoints.

    Strands A2AAgent docs:
    https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/
    """
    auth   = AgentCoreA2AAuth(actor_id=actor_id, region=region)
    client = httpx.AsyncClient(auth=auth, timeout=300)
    return ClientConfig(httpx_client=client, streaming=True)


def extract_a2a_text(result) -> str:
    """Extract plain text from a Strands A2AAgent AgentResult.

    A2AAgent returns an AgentResult where result.message has the structure:
    {"role": "assistant", "content": [{"text": "..."}]}

    Ref: Strands AgentResult type.
    """
    try:
        content = result.message.get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", str(result))
    except Exception:
        pass
    return str(result)
