"""Interactive chat for Module 8: Capstone - Strategy Recommendation Engine.

This is the notebook's multi-agent system in script form. One Graph runs:

    planner -> analysis_team (Swarm) -> evaluator -> writer

The analysis_team Swarm holds the researcher, risk_analyzer, demand_analyzer,
synthesizer and reviewer, which hand off to each other autonomously until the
reviewer approves.

    cd samples/08-capstone
    pip install -r requirements.txt
    python chat.py

Type or paste a Situation Summary and press Enter. A multi-line summary pasted at
once (like SITUATION_SUMMARY in the notebook) is sent as ONE message.
Type 'quit', 'exit', or Ctrl+C to stop.

Model: same as the notebook (set in MODEL below). To switch, change the model_id to
another Amazon Bedrock model id.
"""

# The ONLY third-party dependency in this workshop is the Strands Agents SDK:
#     pip install strands-agents
# Swarm and GraphBuilder ship inside it, so no other external library is needed.
# Every agent reasons purely over the text we hand it (no web/tool calls), which is
# also our strongest guardrail against hallucinated facts.
import asyncio
import os
import select
import sys

from strands import Agent
from strands.memory import MemoryManager
from strands.models import BedrockModel
from strands.multiagent import Swarm, GraphBuilder
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.vended_memory_stores.test_memory_store import TestMemoryStore

# --- Model + shared configuration ----------------------------------------
# Claude profile enabled in your account (e.g. a Haiku profile for cheaper demos).
MODEL = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    max_tokens=16384,        # was defaulting low — this is what truncated the handoff
)

# Conversation memory for this chat session (Strands memory: TestMemoryStore + MemoryManager).
# Only two things are saved per turn: what the user said and the system's final answer,
# written with the store's documented add() once the turn ends. Nothing the agents say to
# each other is stored. Every turn builds fresh agents, exactly like the notebook, and each
# agent reads this memory through its own MemoryManager: injection adds the relevant
# entries to its model input before each call. Inside a turn the agents still pass work
# only through the pattern itself. persist=False: nothing is written to disk.
MEMORY = TestMemoryStore(name="conversation", persist=False)


def remember(user_message: str, final_answer: str) -> None:
    """Save one turn of the conversation: the user's message and the final answer."""
    async def save():
        await MEMORY.add(f"User: {user_message}", {"role": "user"})
        await MEMORY.add(f"Final answer: {final_answer}", {"role": "final_answer"})
    asyncio.run(save())

# --- PLANNER -------------------------------------------------------------
PLANNER_PROMPT = f"""
Role: Planner Agent for the MarketNest strategy team.

Input: Situation Summary.

Output: Exactly three sections:
• TASK_DECOMPOSITION (5-8 bullets) - each bullet is a concrete sub-task a strategy analyst would do, and names the teammate who owns it (researcher, risk_analyzer, demand_analyzer, synthesizer).
• MISSING_INFO (2-3 bullets) - inputs missing from the Situation Summary that are needed to decide responsibly.
• DECISION_CRITERIA (3-5 bullets) - criteria the recommendation should optimise for (e.g., conversion lift, unit economics, operational feasibility, customer trust).

Rules:
- In the output, each bullet point having 1 sentence with max 15 words.
- Do NOT recommend an option yet.
- No invented metrics; if a value is absent, note it under MISSING_INFO.
- Use crisp bullets, not paragraphs.
- After emitting the three sections, hand off to the 'researcher'.
"""

def build_planner():
    # search_tool_config=False (here and in every builder below): memory is recalled
    # through injection only, so each agent keeps exactly the tools it has in the notebook.
    return Agent(model=MODEL, name="planner", system_prompt=PLANNER_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- RESEARCHER ----------------------------------------------------------
RESEARCHER_PROMPT = f"""
Role: Researcher Agent for the MarketNest strategy team.

Inputs: Situation Summary; Planner output.

Output: Four sections:
• FACTS (top 2 bullets) - only facts explicitly stated in the Situation Summary.
• ASSUMPTIONS (top 2 bullets) - list assumptions separately (anything inferred, not stated).
• UNKNOWNS / QUESTIONS (top 2 bullets) - what must be answered to proceed.
• RISK_TRIGGERS (top 2 bullets) - conditions that would make this decision unsafe (e.g., fulfillment SLA unmet, unit economics negative, required approvals missing).

Rules:
- Each bullet is 1 sentence with max 15 words.
- If it is not explicitly stated in the Situation Summary, it cannot be a FACT.
- Do NOT recommend an option.
- No invented numbers.

HANDOFF (mandatory): You are one member of a team and you NEVER finish the team's
work. After emitting the four sections you MUST hand off by CALLING the handoff
tool - do not merely write that you are handing off. Hand off to 'risk_analyzer'
(the analysts will cover the risk and demand lenses before the synthesizer drafts).
Only the reviewer may end the team's turn.
"""

def build_researcher():
    return Agent(model=MODEL, name="researcher", system_prompt=RESEARCHER_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- RISK ANALYZER (runs in parallel with the demand analyzer) -----------
RISK_PROMPT = f"""
Role: Risk Analyzer Agent (specialist in the shared analyzer role).

Inputs: Situation Summary; Planner output; Researcher output.

Output: Risk Analysis with sections:
• Risk Summary (1-2 lines): the most decision-relevant risk theme.
• Risks by Option A/B (Max 2 options) - for each option, highlight (in 1 sentence, max 15 words) the material operational/fulfillment, financial/unit-economics, execution/timeline, and exit-criteria risks.
• Mitigations (2 bullets, mapped to the risks above).
• Risk Triggers (2 bullets) - conditions that would make the decision unsafe or trip the exit/kill criteria.
• Assumptions & Unknowns (2 bullets).

Rules:
- Each bullet is 1 sentence with max 15 words.
- Do not invent metrics or facts.
- If information is missing, say what you would measure/confirm (do not guess a number).
- Make trade-offs explicit ("We gain X; we risk Y").
- Do NOT recommend an option; provide the risk view only.

HANDOFF (mandatory): You are one member of a team and you NEVER finish the team's
work. When your risk analysis is done you MUST hand off by CALLING the handoff tool
- do not merely write that you are handing off. If the demand lens has not yet been
covered, hand off to 'demand_analyzer'; otherwise hand off to 'synthesizer'.
Only the reviewer may end the team's turn.
"""

def build_risk_analyzer():
    return Agent(model=MODEL, name="risk_analyzer", system_prompt=RISK_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- MARKET DEMAND ANALYZER (runs in parallel with the risk analyzer) ----
DEMAND_PROMPT = f"""
Role: Market Demand Analyzer Agent (specialist in the shared analyzer role).

Inputs: Situation Summary; Planner output; Researcher output.

Output: Demand Analysis with sections:
• Demand Summary (1-2 lines): the most decision-relevant demand signal.
• Demand by Option A/B (Max 2 options) - for each option, highlight (in 1 sentence, max 15 words) customer-segment fit, conversion potential against the stated success criteria, and market timing.
• Supporting Signals (2 bullets) - facts from the inputs that raise or lower demand confidence.
• Demand Risks (2 bullets) - where demand could fall short of the success criteria.
• Assumptions & Unknowns (2 bullets).

Rules:
- Each bullet is 1 sentence with max 15 words.
- Do not invent metrics or facts.
- If information is missing, say what you would measure/confirm (do not guess a number).
- Make trade-offs explicit ("We gain X; we risk Y").
- Do NOT recommend an option; provide the demand view only.

HANDOFF (mandatory): You are one member of a team and you NEVER finish the team's
work. When your demand analysis is done you MUST hand off by CALLING the handoff
tool - do not merely write that you are handing off. If the risk lens has not yet
been covered, hand off to 'risk_analyzer'; otherwise hand off to 'synthesizer'.
Only the reviewer may end the team's turn.
"""

def build_demand_analyzer():
    return Agent(model=MODEL, name="demand_analyzer", system_prompt=DEMAND_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- SYNTHESIZER ---------------------------------------------------------
SYNTHESIZER_PROMPT = f"""
Role: Synthesizer Agent - synthesize the Risk and Demand analyses into one
Strategy Recommendation for the MarketNest strategy team.

Inputs: Market Demand Analysis (market/customer lens); Risk Analysis (risk lens);
Planner outputs; Researcher outputs.

Output: a single Strategy Recommendation with these sections:
- Recommendation (1-2 lines)
- Options Considered A/B/C (3 Max)
- Trade offs (2 bullets)
- Risks & Mitigations (2 bullets)
- Assumptions & Unknowns (2 bullets)
- Escalate? (Yes/No + reason)
- Next Steps (owner + timeline - 2 bullets)

Rules:
- Each bullet is 1 sentence with max 15 words.
- Do NOT concatenate the two analyses; synthesise them and resolve conflicts.
- Resolve every demand-vs-risk conflict inline (>=2x): "Demand says ___. Risk says ___. We choose ___ because ___."
- Do not invent facts or metrics; use "Unknown" where data is missing.
- If the reviewer returns gaps, revise ONLY the flagged parts, keep everything else intact.

ARTIFACT RULE (you are the SOLE author of the recommendation):
- You are the ONLY agent that may write the recommendation. Emit it in full inside
  these exact markers, every time you draft or revise:
  <CURRENT_STRATEGY_RECOMMENDATION>
  ...the complete recommendation - ALL sections above, in full, no summary...
  </CURRENT_STRATEGY_RECOMMENDATION>
- Never compact it into key:value form, never drop a section, never write "see above".
- Do NOT author a <LATEST_REVIEW> block - that belongs to the reviewer only.

HANDOFF RULE (mandatory - you never finish the team's work):
- After drafting OR revising, you MUST hand off to 'reviewer' by CALLING the handoff
  tool - do not merely write that you are handing off, and never end the team's turn.
- Your handoff message to the reviewer MUST contain the COMPLETE recommendation text
  in full - the entire <CURRENT_STRATEGY_RECOMMENDATION> block, verbatim. The reviewer
  can only critique what is inside your handoff, so a summary or "see above" makes the
  review worthless. Always inline the full block in the handoff itself.
- Only the reviewer may end the team's turn.
"""

def build_synthesizer():
    return Agent(model=MODEL, name="synthesizer", system_prompt=SYNTHESIZER_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- REVIEWER (the critic that gates quality) ----------------------------
REVIEWER_PROMPT = f"""
Role: Critic (red-team reviewer) for the MarketNest strategy team.

Input: the latest draft Strategy Recommendation from the synthesizer, visible in
the shared team conversation.

Output (while gaps remain):
• CRITIQUES (top 2 bullets) - specific correctness/logic gaps.
• MISSING_INFO (top 2 bullets) - inputs needed but absent from the Situation Summary.
• HALLUCINATION_RISKS (top 2 bullets) - claims/metrics not traceable to the Situation Summary or an analyst's output.
• GROUNDEDNESS (top 2 bullets) - conclusions that outrun their evidence.
• ESCALATE (Yes/No + reason).
• EVIDENCE_TO_RESOLVE (1-2 bullets).

Rules:
- Each bullet is 1 sentence, max 15 words.
- Be tough and specific; assume the briefing is wrong until proven otherwise.
- Identify at least five specific issues while any gap remains.
- If exit/kill criteria, unit economics, or required approvals are not addressed, set Escalate=Yes.
- Do NOT rewrite the briefing yourself; only critique it.

ROUTING (you are in a team - route by HANDING OFF, not by writing phrases):
- If the briefing is NOT good enough, hand off to the teammate best able to fix it:
    • hand off to the SYNTHESIZER when the gap is LOGIC, WORDING, STRUCTURE, or an
      unresolved demand-vs-risk conflict - the evidence on hand is enough to rework the argument.
    • hand off to the RESEARCHER when the blocking gap is MISSING FACTS/EVIDENCE that
      no amount of re-synthesis can close.
- If the briefing is complete, grounded, and hallucination-free, do NOT hand off -
  end your turn so the team's work is finalized.

VERDICT RULE (mandatory): EVERY response MUST end with a standalone final line that is
EXACTLY "REVISION NEEDED" (when you are handing off for rework) or "APPROVED" (when you
are finalizing) - nothing after it. This line is a verdict for the downstream evaluator,
not a routing command. Never write "approved" or "revision needed" anywhere else in your prose.
"""

def build_reviewer():
    return Agent(model=MODEL, name="reviewer", system_prompt=REVIEWER_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

EVALUATOR_PROMPT = f"""
Role: Confidence Scorer for the MarketNest strategy team.

Input: your context contains the MarketNest Situation Summary / planner brief AND
the analysis team's output. That output is a multi-agent transcript and may include:
handoff notes, agent chatter, several <CURRENT_STRATEGY_RECOMMENDATION> blocks
(draft + revisions), one or more <LATEST_REVIEW> blocks, and control words like
"REVISION NEEDED". Most of this is noise; extract only what the rules below name.

WHAT TO SCORE:
- Among ALL <CURRENT_STRATEGY_RECOMMENDATION> blocks in the input, select the MOST
  COMPLETE one - the block with the full section structure (Recommendation, Options,
  Trade-offs / Conflict Resolutions, Risks & Mitigations, Assumptions & Unknowns,
  Escalate?, Next Steps). If several are equally complete, use the LAST one.
- IGNORE any block that is a metadata/key:value summary, is truncated, or says the
  text is "not reproduced" - those are degraded copies, never scored.
- Use the LAST <LATEST_REVIEW> block (CRITIQUES, MISSING_INFO, HALLUCINATION_RISKS,
  GROUNDEDNESS, ESCALATE, EVIDENCE_TO_RESOLVE) as evidence of remaining weaknesses.
  If it conflicts with the recommendation, trust the reviewer's flagged gaps.

WHAT TO IGNORE:
- The Situation Summary / planner brief is CONTEXT ONLY. It is NOT a recommendation
  and must NEVER be output or scored as one.
- Ignore handoff notes, "no strategy recommendation exists yet" lines, and control
  words ("REVISION NEEDED", "APPROVED", routing text). They are signals, not content.

MISSING RULE (read carefully):
- Output MISSING ONLY when the literal characters "<CURRENT_STRATEGY_RECOMMENDATION>"
  do NOT appear anywhere in your input.
- MISSING is NOT triggered by: a recommendation that relies on "Unknown" values, a
  "REVISION NEEDED" verdict, the reviewer citing missing evidence, or agents saying a
  block was "omitted". If the marker is present, a draft WAS received - score it.
  A recommendation built on unknowns is a LOW-CONFIDENCE recommendation, not a missing
  one, and must be scored (typically low), never reported as MISSING.
- Only if truly no marker exists, output exactly and stop:
      CURRENT_STRATEGY_RECOMMENDATION: MISSING - no recommendation block in input.
      CONFIDENCE_SCORE: 0

Output - produce these in order:

1. CURRENT_STRATEGY_RECOMMENDATION - reproduce the selected MOST COMPLETE block,
   wrapped in the same markers:

   <CURRENT_STRATEGY_RECOMMENDATION>
   ...the recommendation, copied verbatim...
   </CURRENT_STRATEGY_RECOMMENDATION>

   VERBATIM RULE (mandatory): This is a passthrough, not your writing. Do NOT edit,
   summarize, shorten, reword, reformat, re-order, correct, compact into key:value,
   or drop any section. Reproduce every section and bullet in full.

2. CONFIDENCE_SCORE (0-100) - how defensible and well-grounded the recommendation is
   given the available evidence.

3. WHY (3 bullets) - the drivers behind the score, both strengths and weaknesses.

4. WHAT_WOULD_INCREASE_CONFIDENCE (3 bullets) - ranked by impact.

Rules:
- Each bullet is 1 sentence, max 15 words.
- Lower the score whenever a key constraint (exit/kill criteria, unit economics,
  fulfillment SLA, required approvals) lacks supporting evidence, or the reviewer
  flagged an unresolved gap. Many "Unknown" values means a LOW score, not MISSING.
- Each "increase confidence" item must be concrete and actionable (e.g., run a
  metro-zone pricing test, confirm next-day-delivery capacity at pilot volume,
  secure Finance sign-off on unit economics, size the pilot cohort for power).
- Score the recommendation; do not rewrite or re-argue it.
"""

def build_evaluator():
    return Agent(model=MODEL, name="evaluator", system_prompt=EVALUATOR_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

# --- WRITER (final professional output, sequential stage) ----------------
WRITER_PROMPT = f"""
Role: Professional Writer for the MarketNest strategy team.

Input: the Evaluator's Confidence Report. It contains the latest strategy
recommendation inside <CURRENT_STRATEGY_RECOMMENDATION>...</CURRENT_STRATEGY_RECOMMENDATION>
markers, followed by the confidence assessment (CONFIDENCE_SCORE, WHY,
WHAT_WOULD_INCREASE_CONFIDENCE).

Your job:
- Take the text INSIDE the <CURRENT_STRATEGY_RECOMMENDATION> markers as the
  authoritative, latest strategy recommendation, and write it up professionally.
- Preserve every section, decision, number, option, and caveat exactly as given;
  improve ONLY clarity, flow, and formatting. Do NOT re-argue, re-score, add,
  drop, summarize, or compress any content.
- Then append the confidence assessment from the evaluator, unchanged in substance.
- If the evaluator reports "CURRENT_STRATEGY_RECOMMENDATION: MISSING", output exactly:
      === EXECUTIVE STRATEGY RECOMMENDATION ===
      No strategy recommendation was produced by the analysis team.
      === CONFIDENCE ===
      - CONFIDENCE_SCORE: 0
  and stop. Never fabricate a recommendation or substitute the Situation Summary.

Output: one final, paste-ready markdown artefact with these exact markers:
=== EXECUTIVE STRATEGY RECOMMENDATION ===
<the polished recommendation - reproduce ALL of its sections, none dropped>

=== CONFIDENCE ===
- CONFIDENCE_SCORE (0-100)
- WHY (3 bullets)
- WHAT_WOULD_INCREASE_CONFIDENCE (3 bullets)

Rules:
- Each bullet is 1-2 sentences, each sentence max 15 words.
- No extra sections beyond the two marked blocks; no preamble, no sign-off.
- Do NOT emit the <CURRENT_STRATEGY_RECOMMENDATION> markers themselves - present the
  content under the "=== EXECUTIVE STRATEGY RECOMMENDATION ===" heading instead.
- Strip any workflow control lines that leaked through ("REVISION NEEDED",
  "APPROVED", "RETURN TO RESEARCH", "RETURN TO SYNTHESIS") - they must never appear.
- Clean, executive-ready markdown that pastes into a doc without fixup (consistent
  headers, tight bullets, no stray characters).
"""

def build_writer():
    return Agent(model=MODEL, name="writer", system_prompt=WRITER_PROMPT,
                 memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

def build_swarm_agents():

    # Build the agents
    researcher = build_researcher()
    risk_analyzer = build_risk_analyzer()
    demand_analyzer = build_demand_analyzer()
    synthesizer = build_synthesizer()
    reviewer = build_reviewer()

    # Set the Contract to pass the latest Strategy Recommendation produced by 
    # the Synthesizer agent to the next agent in a hand_off.
    CARRY_FORWARD_CONTRACT = """
    --- SHARED OUTPUT CONTRACT (applies to every agent in this team) ---
    The team maintains one living artifact: the CURRENT STRATEGY RECOMMENDATION,
    first produced by the synthesizer.

    RULE: Once a strategy recommendation exists in the shared conversation, EVERY
    response you produce — no matter your role — MUST end with the latest full
    version of it, reproduced verbatim, inside these exact markers:

    <CURRENT_STRATEGY_RECOMMENDATION>
    ...the most recent complete strategy recommendation, copied exactly...
    </CURRENT_STRATEGY_RECOMMENDATION>

    - If you are the synthesizer and you just revised it, emit YOUR new version.
    - If you are any other agent, copy the most recent version you can see from the
      conversation UNCHANGED — do not edit, summarize, or truncate it.
    - If no strategy recommendation exists yet (early research turns), omit the
      block entirely.
    Put your own role-specific output (findings, critique, verdict) ABOVE the block.
    """

    # Set the Contract to pass the latest Reviews produced by 
    # the Reviewer agent to the next agent in a hand_off.
    CARRY_FORWARD_CONTRACT += """
    The team also maintains the LATEST REVIEW. Once the reviewer has produced a
    verdict, EVERY response — regardless of role — MUST also carry forward the most
    recent reviewer output verbatim, inside these exact markers:

    <LATEST_REVIEW>
    ...the most recent reviewer critique + verdict, copied exactly...
    </LATEST_REVIEW>

    - If you are the reviewer, emit YOUR current critique + verdict here.
    - Otherwise, copy the most recent <LATEST_REVIEW> from the conversation unchanged.
    - Omit the block if the reviewer has not yet produced a verdict.
    Order per response: role output, then <CURRENT_STRATEGY_RECOMMENDATION>, then
    <LATEST_REVIEW>, then (reviewer only) the standalone verdict line.
    """

    # --- Apply the contract to every agent that participates in the swarm -------
    # Guarded so re-running the cell doesn't stack the contract repeatedly.
    for _agent in (researcher, risk_analyzer, demand_analyzer, synthesizer, reviewer):
        if CARRY_FORWARD_CONTRACT not in _agent.system_prompt:
            _agent.system_prompt = _agent.system_prompt + CARRY_FORWARD_CONTRACT
    

    return researcher, risk_analyzer, demand_analyzer, synthesizer, reviewer

# --- The swarm: research + synthesis + review, all autonomous ---------------
def build_analysis_swarm():
    """researcher explores, pulls in risk/demand, synthesizer drafts,
    reviewer critiques and hands back or approves — all via handoffs.
    Every agent carries the latest strategy draft forward per the contract,
    so whichever agent terminates, the draft survives to the terminal output."""
    researcher, risk_analyzer, demand_analyzer, synthesizer, reviewer = build_swarm_agents()
    return Swarm(
        [researcher, risk_analyzer, demand_analyzer, synthesizer, reviewer],
        entry_point=researcher,
        max_handoffs=9,
        max_iterations=9,
        execution_timeout=1500.0,
        node_timeout=300.0,
        repetitive_handoff_detection_window=4,   # guard against ping-pong
        repetitive_handoff_min_unique_agents=3,
    )

class AnalysisSwarmNode(MultiAgentBase):
    """A single Graph node that runs the analysis Swarm and controls exactly what
    it forwards to the next stage (evaluator).

    Why it exists: a raw Swarm graph node (a) floods the next node with every
    agent's chatter and duplicate draft blocks, and (b) returns FAILED when it
    hits its handoff cap — which makes the graph feed the evaluator only the
    original task. This wrapper fixes both: it emits one clean payload and always
    reports COMPLETED so downstream never starves.
    """

    def __init__(self, name="analysis_team"):
        super().__init__(); self.name = name; self._swarm = build_analysis_swarm()

    async def invoke_async(self, task, invocation_state=None, **kw):
        res = await self._swarm.invoke_async(task, invocation_state, **kw)
        text = "\n\n".join(f"[{name}]\n{nr.result}" for name, nr in res.results.items())
        ar = list(res.results.values())[-1].result          # reuse a real AgentResult
        ar.message = {"role": "assistant", "content": [{"text": text}]}
        return MultiAgentResult(status=Status.COMPLETED,
            results={self.name: NodeResult(result=ar, status=Status.COMPLETED)})

def build_system():
    b = GraphBuilder()

    b.add_node(build_planner(),          "planner")
    b.add_node(AnalysisSwarmNode(),      "analysis_team")   # research → analysis → draft → review
    b.add_node(build_evaluator(),        "evaluator")
    b.add_node(build_writer(),           "writer")

    b.add_edge("planner", "analysis_team")
    b.add_edge("analysis_team", "evaluator")
    b.add_edge("evaluator", "writer")

    b.set_entry_point("planner")

    # The reviewer↔synthesizer revision happens inside the swarm, bounded by
    # max_handoffs; these caps just stop a runaway graph.
    b.set_max_node_executions(20)
    b.set_execution_timeout(1800)
    b.set_node_timeout(1500)

    return b.build()



def read_message(prompt: str) -> str:
    """Read one user message from the terminal.

    input() stops at the first newline, so a pasted multi-line summary would be
    sent as many separate runs. Pasted text arrives all at once, so every line
    already waiting on stdin is joined into the same message.
    Raises EOFError when stdin is closed.
    """
    if sys.platform == "win32":
        # select() only works on sockets on Windows: fall back to one line.
        return input(prompt).strip()
    print(prompt, end="", flush=True)
    fd = sys.stdin.fileno()
    data = os.read(fd, 65536)
    if not data:
        raise EOFError
    while select.select([fd], [], [], 0.1)[0]:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()


def main():
    print("Strategy Recommendation Engine")
    print("Type or paste a Situation Summary (multi-line paste is one message) and press Enter, then ask follow-ups.")
    print("The agents share a conversation memory. Type 'quit' to exit.")
    print("Example: MarketNest is considering a Premium Subscription Tier for repeat buyers in metro zones. A: paid Premium tier on top SKUs, B: lower-priced Plus tier, C: convert loyalty members first. Decision in 2 weeks; success is +10% checkout conversion in 3 months.\n")
    while True:
        try:
            user_input = read_message("Situation Summary: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        summary = user_input

        print("\nRunning planner → analysis_team (Swarm) → evaluator → writer (several minutes)...")
        # Build fresh, then run the full multi-agent system on the situation summary.
        system = build_system()
        final = system(summary)   # analysis_team (swarm) -> evaluator -> writer

        print("\n\n")
        print("========================================================")
        print("\n\n")

        print("===== FINAL EXECUTIVE STRATEGY RECOMMENDATION =====\n")
        print(final.results["writer"].result)
        remember(user_input, str(final.results["writer"].result).strip())

        sw = system.nodes["analysis_team"].executor._swarm   # the Swarm inside the custom node
        print("\nhops:", len(sw.state.node_history))
        print("order:", [n.node_id for n in sw.state.node_history])
        print("status:", sw.state.completion_status)          # COMPLETED = clean, FAILED = cap/early stop
        print()


if __name__ == "__main__":
    main()
