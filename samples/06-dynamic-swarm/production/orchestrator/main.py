"""
Dynamic Swarm Orchestrator (Pattern 4) — production implementation.

The Strands Swarm class requires local agent objects sharing tool_registry.
In production with separate AgentCore Runtimes, each specialist runs in its
own container and communicates via A2A — A2AAgent does not expose tool_registry,
so it cannot be used directly with the Swarm class.

This implementation achieves equivalent autonomous-routing semantics using
Agent(tools=[monitor_tool, network_specialist_tool, db_admin_tool, resolver_tool])
where each @tool wraps an A2A call. The orchestrator LLM decides which specialist
to call and in what order, producing the same emergent routing as a Swarm.

Agents: Monitor, Network Specialist, DB Admin, Resolver
Use case: IT incident response — path emerges based on findings.

References:
  Strands Swarm: https://strandsagents.com/docs/user-guide/concepts/multi-agent/swarm/
  Strands A2AAgent: https://strandsagents.com/docs/api/python/strands.agent.a2a_agent/
  AgentCore A2A: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import asyncio, logging, os, threading
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

REGION               = os.environ.get("AWS_REGION") or os.environ["MONITOR_RUNTIME_ARN"].split(":")[3]
MONITOR_ARN          = os.environ["MONITOR_RUNTIME_ARN"]
NETWORK_SPECIALIST_ARN = os.environ["NETWORK_SPECIALIST_RUNTIME_ARN"]
DB_ADMIN_ARN         = os.environ["DB_ADMIN_RUNTIME_ARN"]
RESOLVER_ARN         = os.environ["RESOLVER_RUNTIME_ARN"]
ACTOR_HEADER         = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

ORCHESTRATOR_PROMPT = (
    "You coordinate a Dynamic Swarm for IT incident response. "
    "Route autonomously based on what each specialist reports:\n"
    "1. Always call monitor_agent first to triage the incident.\n"
    "2. Based on monitor findings, call network_specialist_agent, db_admin_agent, or both.\n"
    "3. After all relevant specialists have reported, call resolver_agent to produce the resolution plan.\n"
    "Adapt routing based on what each agent returns."
)

_monitors:            dict = {}
_network_specialists: dict = {}
_db_admins:           dict = {}
_resolvers:           dict = {}
_orchestrators:       dict = {}


def _current_session() -> tuple:
    import uuid
    headers = BedrockAgentCoreContext.get_request_headers() or {}
    return (BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4()),
            headers.get(ACTOR_HEADER) or "default-user")


def _call_a2a(agent, prompt: str, timeout: int = 300) -> str:
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
def monitor_agent(incident_report: str) -> str:
    """Entry point for all incidents. Triages, assesses impact, classifies the incident type.
    Always call this first.
    Args: incident_report: the full incident description."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_monitors, MONITOR_ARN, "monitor",
                               "Entry point — triages and classifies incidents.", aid),
                     incident_report)


@tool
def network_specialist_agent(incident_context: str) -> str:
    """Investigates network and infrastructure root causes (load balancer, CDN, DNS, connectivity).
    Call when monitor suspects network/infra involvement.
    Args: incident_context: incident report plus monitor findings."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_network_specialists, NETWORK_SPECIALIST_ARN, "network_specialist",
                               "Network/infra root cause analysis.", aid), incident_context)


@tool
def db_admin_agent(incident_context: str) -> str:
    """Investigates database root causes (connection pool, slow queries, locks, schema changes).
    Call when DB metrics are abnormal.
    Args: incident_context: incident report plus prior findings."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_db_admins, DB_ADMIN_ARN, "db_admin",
                               "Database root cause analysis.", aid), incident_context)


@tool
def resolver_agent(all_findings: str) -> str:
    """Synthesizes all specialist findings into a resolution plan. Call this last.
    Args: all_findings: combined findings from all specialists."""
    sid, aid = _current_session()
    return _call_a2a(_get_a2a(_resolvers, RESOLVER_ARN, "resolver",
                               "Incident resolver — produces resolution plan.", aid), all_findings)


def _get_orchestrator(sid: str) -> Agent:
    if sid not in _orchestrators:
        _orchestrators[sid] = Agent(
            tools=[monitor_agent, network_specialist_agent, db_admin_agent, resolver_agent],
            system_prompt=ORCHESTRATOR_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=20),
            callback_handler=None,
        )
    return _orchestrators[sid]


@app.entrypoint
def invoke(payload, context):
    import time
    incident = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not incident:
        raise ValueError("Missing required field: prompt")
    sid, _ = _current_session()
    last_error = None
    for attempt in range(3):
        try:
            result_str = str(_get_orchestrator(sid)(incident)).strip()
            if "Agent execution failed" in result_str:
                raise RuntimeError(f"Agent failed (cold start?): {result_str[:200]}")
            return result_str
        except Exception as exc:
            last_error = exc
            _orchestrators.pop(sid, None)
            logger.warning("Attempt %d failed: %s — retrying in %ds", attempt+1, exc, 10*(attempt+1))
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
    raise last_error

if __name__ == "__main__":
    app.run()
