"""Interactive chat for Module 6: Agent-as-Tool.

The orchestrator delegates to three specialist agents (researcher, analyzer, synthesizer)
as callable tools. The LLM decides routing and argument construction.

    cd samples/06-agent-as-tool
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
    model = BedrockModel(model_id="amazon.nova-lite-v1:0")  # cheapest
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-strands-foundations"))

from strands import Agent, tool
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT = (
    "You are a market research specialist. Use your tools to gather relevant data. "
    "Return structured findings — data only."
)
ANALYZER_PROMPT = (
    "You are a business strategy analyst. Evaluate the ONE option you are given: "
    "strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. "
    "150 words max."
)
SYNTHESIZER_PROMPT = (
    "Write a leadership memo: ## Recommendation, ## Options at a Glance (table), "
    "## Top 3 Risks, ## Success Metrics, ## Decision Required. Under 400 words."
)
ORCHESTRATOR_PROMPT = (
    "You are a strategic decision analyst. Steps:\n"
    "1. Call researcher_agent to gather market data.\n"
    "2. Call analyzer_agent three times (Option A, B, C) with the research context.\n"
    "3. Call synthesizer_agent with all three analyses.\n"
    "Do not skip any step."
)


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.

    Args:
        topic: The decision topic or brief to research
    """
    worker = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    return str(worker(topic))


@tool
def analyzer_agent(option_name: str, option_description: str, research_context: str) -> str:
    """Analyze one specific decision option. Call once per option (A, B, C).

    Args:
        option_name: Short name (e.g., 'Option A — Exclusive Premium')
        option_description: Full description with price and approach
        research_context: Research findings from researcher_agent
    """
    worker = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    return str(worker(
        f"Option: {option_name}\nDescription: {option_description}\nResearch: {research_context}"
    ))


@tool
def synthesizer_agent(decision_brief: str, all_analyses: str) -> str:
    """Synthesize all option analyses into a leadership memo. Call AFTER all three analyses.

    Args:
        decision_brief: The original decision brief
        all_analyses: Combined analyses of all three options
    """
    worker = Agent(system_prompt=SYNTHESIZER_PROMPT)
    return str(worker(f"Brief:\n{decision_brief}\n\nAnalyses:\n{all_analyses}"))


def main():
    print("Agent-as-Tool Orchestrator | type 'quit' to exit\n")
    DEFAULT_BRIEF = """
DECISION BRIEF: NovaCart Premium Tier Launch
Options: A (Exclusive $19.99/mo) | B (5% pilot $14.99/mo) | C (Full launch $12.99/mo)
Success target: +15% CLV in 6 months | Budget: $2M | Deadline: 2027-01-31
"""
    while True:
        try:
            user_input = input("Brief (Enter for default): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        brief = user_input if user_input else DEFAULT_BRIEF
        orchestrator = Agent(
            tools=[researcher_agent, analyzer_agent, synthesizer_agent],
            system_prompt=ORCHESTRATOR_PROMPT,
        )
        print("\nOrchestrator running (LLM decides routing)...")
        t0 = time.time()
        orchestrator(brief)
        elapsed = time.time() - t0

        tool_calls = sum(
            1 for msg in orchestrator.messages
            for block in msg.get("content", [])
            if "toolUse" in block
        )
        print(f"\n⏱️  {elapsed:.1f}s | 🔧 {tool_calls} tool calls")
        print()


if __name__ == "__main__":
    main()
