"""Interactive multi-turn chat for Module 1: Strands Foundations.

The notebook runs the agent one cell at a time. This script wraps the same
agent in a loop so you can hold a real multi-turn conversation in the terminal —
the agent keeps its context across turns.

From the cloned repo root:

    cd samples/01-strands-foundations
    pip install -r requirements.txt
    python chat.py

Type 'quit', 'exit', or Ctrl+C to stop.

Model options
─────────────
Claude Sonnet 4 (default — requires Bedrock model access enabled):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

Claude Haiku 4.5 (faster, lower cost):
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")

AWS-sponsored events / credits only cover Amazon Nova models:
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # recommended
    model = BedrockModel(model_id="amazon.nova-lite-v1:0")  # cheapest

Pass model= to Agent(...) to switch.
"""

from strands import Agent
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

SYSTEM_PROMPT = """You are a Decision Intelligence Analyst for a technology company.
You help business leaders gather data and context before making strategic decisions.
Use your available tools to look up company data, market benchmarks, and competitor information.

Guidelines:
- Always use tools to answer questions — never guess when real data is available.
- Be concise and data-driven.
- Surface the most relevant numbers for the decision at hand.
- If asked about a company or competitor not in your tools, say so clearly."""


def main():
    # One Agent instance reused across all turns — its conversation history
    # lives in agent.messages, which is what makes it multi-turn.
    agent = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=SYSTEM_PROMPT,
    )

    print("Decision Intelligence Agent  |  type 'quit' to exit")
    print('Try: "What is NovaCart\'s current CLV and churn rate?"\n')

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        # The agent streams its response via the default callback handler.
        print("\nAgent: ", end="")
        agent(user_input)
        print()


if __name__ == "__main__":
    main()
