"""M6 Production: Dynamic Swarm on AgentCore Runtime.
Pattern: Swarm with autonomous handoffs — IT incident response.
Agents: Monitor, Network Specialist, DB Admin, Resolver.
Entry point: Monitor (triages and routes to specialists based on findings).

Local test:  python main.py
Deploy:      python deploy.py → python invoke.py <ARN>
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.multiagent import Swarm

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

monitor = Agent(
    name="monitor",
    description=(
        "Entry point for all incidents. Detects symptoms, assesses impact, and classifies "
        "the incident type (network, database, or mixed). Routes to the right specialist first."
    ),
    system_prompt=(
        "You are a site reliability monitor. Analyze the incident report: identify symptoms, "
        "assess severity, classify whether this looks like a network/infrastructure issue, a database issue, "
        "or both. Provide a clear triage summary with your assessment of the root cause category. "
        "Hand off to network_specialist, db_admin, or both based on your findings."
    ),
    callback_handler=None,
)

network_specialist = Agent(
    name="network_specialist",
    description=(
        "Investigates network and infrastructure root causes — load balancer health, CDN, "
        "DNS resolution, inter-service connectivity, TLS/cert issues. Consult me when the "
        "incident might be caused by network or infrastructure problems."
    ),
    system_prompt=(
        "You are a network specialist. Investigate the incident from a network and "
        "infrastructure angle: load balancer configuration, CDN cache behavior, DNS resolution, "
        "inter-service connectivity, TLS/certificate issues, firewall rules. "
        "Analyze the provided context and report your findings. "
        "Indicate whether database involvement is also suspected. "
        "Hand off to db_admin if needed, or to resolver when investigation is complete."
    ),
    callback_handler=None,
)

db_admin = Agent(
    name="db_admin",
    description=(
        "Investigates database root causes — slow queries, connection pool exhaustion, "
        "lock contention, index degradation, schema migration side effects. Consult me when "
        "DB metrics (connection pool, query latency, lock waits) are abnormal."
    ),
    system_prompt=(
        "You are a database administrator. Investigate the incident from a database angle: "
        "connection pool exhaustion, slow query patterns, lock contention, deadlocks, "
        "index degradation, schema migration side effects from recent deployments. "
        "Analyze the provided context and report your findings with specific DB-level root cause hypotheses. "
        "Hand off to resolver when done."
    ),
    callback_handler=None,
)

resolver = Agent(
    name="resolver",
    description=(
        "Synthesizes all specialist findings and produces the incident resolution plan with "
        "immediate actions, root cause summary, and prevention steps. Use me last."
    ),
    system_prompt=(
        "You are an incident resolver. Synthesize all specialist findings into a resolution plan:\n"
        "## Root Cause\n"
        "(one-paragraph summary of the confirmed root cause)\n\n"
        "## Immediate Actions\n"
        "(ordered list of steps to resolve the incident right now)\n\n"
        "## Verification Steps\n"
        "(how to confirm the incident is resolved)\n\n"
        "## Prevention\n"
        "(what to change in the deployment process to prevent recurrence)\n"
        "This is the FINAL step. Do NOT hand off to anyone else."
    ),
    callback_handler=None,
)


@app.entrypoint
def invoke(payload, context):
    incident = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not incident:
        raise ValueError("Missing required field: prompt")

    import uuid as _uuid
    from opentelemetry import baggage as _baggage, context as _ctx
    _session_id = (context.session_id if context and hasattr(context, "session_id") else None) or str(_uuid.uuid4())
    _otel_ctx = _baggage.set_baggage("session.id", _session_id)
    _ctx.attach(_otel_ctx)
    logger.info("session.id=%s module=m6-dynamic-swarm", _session_id)

    swarm = Swarm(
        [monitor, network_specialist, db_admin, resolver],
        entry_point=monitor,
        max_handoffs=8,
        max_iterations=12,
        execution_timeout=300.0,
    )
    result = swarm(incident)
    return str(result.results.get("resolver", result)).strip()


if __name__ == "__main__":
    app.run()
