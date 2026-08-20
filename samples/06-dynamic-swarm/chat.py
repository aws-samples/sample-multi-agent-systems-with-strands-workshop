"""Interactive chat for Module 6: Dynamic Swarm.

Runs the 4-agent swarm (Monitor, Network Specialist, DB Admin, Resolver)
for IT incident response. Agents hand off autonomously — no fixed routing.

    cd samples/06-dynamic-swarm
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.
"""

import time
from strands import Agent
from strands.multiagent import Swarm


def build_swarm():
    monitor = Agent(
        name="monitor",
        description=(
            "Entry point for all incidents. Detects symptoms, assesses impact, and classifies "
            "the incident type (network, database, or mixed). Routes to the right specialist first."
        ),
        system_prompt=(
            "You are a site reliability monitor. Analyze the incident report: identify symptoms, "
            "assess severity, classify whether this looks like a network/infra issue, a database issue, "
            "or both. Hand off to the appropriate specialist (network_specialist or db_admin)."
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
            "You are a network specialist. Investigate the incident from a network and infrastructure "
            "angle: load balancer config, CDN cache, DNS, service mesh. Report your findings. "
            "If database involvement is suspected, hand off to db_admin. "
            "If investigation is complete, hand off to resolver."
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
            "connection pool usage, slow query patterns, locks, recent schema changes. "
            "Report your findings. Hand off to resolver when done."
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
            "You are an incident resolver. Synthesize all findings into a resolution plan:\n"
            "## Root Cause\n"
            "## Immediate Actions (ordered by priority)\n"
            "## Verification Steps\n"
            "## Prevention (what to change before next deployment)\n"
            "This is the FINAL step. Do NOT hand off."
        ),
        callback_handler=None,
    )
    return Swarm(
        [monitor, network_specialist, db_admin, resolver],
        entry_point=monitor,
        max_handoffs=8,
        max_iterations=12,
        execution_timeout=300.0,
        node_timeout=90.0,
    )


def main():
    print("Dynamic Swarm — Incident Response | type 'quit' to exit\n")
    DEFAULT_INCIDENT = """
INCIDENT REPORT: E-Commerce Checkout Degradation

Time detected: 03:42 UTC — 15 minutes after deployment v2.4.1
Symptoms:
  - Checkout API latency: 8,200ms (baseline: 450ms)
  - Error rate: 12% (HTTP 5xx on /api/checkout)
  - Database connection pool: 95% utilized (baseline: 40%)
Impact: ~320 failed checkouts/min | Revenue loss: ~$4.2k/min
Affected services: checkout-service, order-api

Investigate root cause and produce a resolution plan.
"""
    while True:
        try:
            user_input = input("Incident report (Enter for default): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        incident = user_input if user_input else DEFAULT_INCIDENT
        swarm = build_swarm()
        print("\nRunning (agents route autonomously based on findings)...")
        t0 = time.time()
        result = swarm(incident)
        elapsed = time.time() - t0

        path = " → ".join(n.node_id for n in result.node_history)
        usage = result.accumulated_usage
        print(f"\nStatus: {result.status} | {elapsed:.1f}s")
        print(f"Path emerged: {path}")
        print(f"Tokens: {usage.get('totalTokens', 0):,}")
        print()
        print("─" * 60)
        print(str(result.results.get("resolver", "No resolver output")))
        print("─" * 60)
        print()


if __name__ == "__main__":
    main()
