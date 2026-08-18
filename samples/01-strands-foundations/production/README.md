# M1: Decision Intelligence Agent — Production Deployment

Deploy this module to Amazon Bedrock AgentCore Runtime with **AgentCore Web Search** replacing the mock tools.

## Architecture

Single agent with AgentCore Web Search tools

## Setup

### 1. Configure AgentCore Web Search (one-time)

Create a Gateway with the Web Search connector:

```python
import boto3
agentcore = boto3.client("bedrock-agentcore", region_name="us-east-1")

# Create Gateway
gw = agentcore.create_gateway(
    name="decision-memo-gateway",
    protocolType="MCP",
    protocolConfiguration={"mcp": {"searchType": "SEMANTIC", "supportedVersions": ["2025-03-26"]}},
    authorizerType="NONE",
    roleArn="arn:aws:iam::<ACCOUNT>:role/workshop-gateway-role",
)
GATEWAY_URL = gw["gatewayUrl"]

# Add Web Search target
agentcore.create_gateway_target(
    gatewayIdentifier=gw["gatewayId"],
    name="web-search",
    targetConfiguration={"mcp": {"openApiSchema": {"inlinePayload": WEBSEARCH_SCHEMA}}},
    credentialProviderConfigurations=[{
        "credentialProviderType": "GATEWAY_IAM_ROLE"
    }],
)
```

See the [Web Search docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html) for the full schema.

### 2. Deploy

```bash
cd production/

agentcore create                    # name: decision-memo-01
cd decision-memo-01
agentcore add                       # type: Bring my own code | entrypoint: main.py

cp ../main.py app/<AgentName>/
cd app/<AgentName>
uv init --bare --python 3.13
uv add strands-agents bedrock-agentcore aws-opentelemetry-distro boto3 mcp
cd ../..

agentcore deploy
```

### 3. Invoke

```bash
# With web search (set GATEWAY_URL first):
export GATEWAY_URL="<gateway-url>"
agentcore invoke "DECISION BRIEF: NovaCart Premium Tier..."

# Local test (falls back to mock tools if GATEWAY_URL not set):
python main.py
```

```python
# boto3 invocation
import json, uuid, boto3
client = boto3.client("bedrock-agentcore", region_name="us-east-1")
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/...",
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": "DECISION BRIEF: ..."}).encode(),
    qualifier="DEFAULT",
)
result = json.loads(response["response"].read())
```

## Cleanup

```bash
agentcore remove all -y
agentcore deploy
```
