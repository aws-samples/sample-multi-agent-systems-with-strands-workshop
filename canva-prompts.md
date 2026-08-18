# Canva AI Prompts: Multi-Agent Workshop Diagrams

Prompts para **Canva AI Magic Design**. Copiar el bloque de código y pegarlo en Canva AI.


---

## Prompt 1: Strands Agent Loop

**Dónde va:** `samples/01-strands-foundations/`

```
Wide landscape slide, horizontal process flow diagram, 5 steps, dark navy and teal theme.
Steps: "Input & Context" → "Reasoning LLM" → "Tool Selection" → "Tool Execution" → "Response"
Subtitles: "prompt + history", "plans next step", "picks the right tool", "runs it, gets result", "goal met: stop"
Add a curved teal back-arrow below steps 2-3-4 labeled "repeat until done"
Bold white labels, dark navy background, teal arrows, 16:9 wide format.
```

---

## Prompt 2: Pattern 1: Sequential Chain

**Dónde va:** `samples/02-sequential-chain/`

```
Wide landscape slide, horizontal process flow diagram, 5 steps, dark navy and teal theme.
Steps: "Decision Brief" → "Researcher" → "Analyst" → "Synthesizer" → "Leadership Memo"
Subtitles: "", "gathers data with tools", "evaluates all options", "writes the memo", ""
Note below Researcher and Analyst: "callback_handler=None (silent)"
Bold white labels, teal arrows, dark navy background, 16:9 wide format.
```

---

## Prompt 3: Pattern 2: Parallel Fork-Join

**Dónde va:** `samples/03-parallel-fork-join/`

```
Wide landscape slide, horizontal process flow with fork and merge, dark navy and cobalt blue theme.
Steps: "Decision Brief" → "Researcher" → fork to "Analyzer A", "Analyzer B", "Analyzer C" → merge to "Synthesizer" → "Leadership Memo"
Label across parallel section: "asyncio.gather: all 3 run simultaneously"
Bold white labels, cobalt blue parallel arrows, teal main arrows, dark navy background, 16:9 wide format.
```

---

## Prompt 4: Pattern 3: Critic-Refiner

**Dónde va:** `samples/04-critic-refiner/`

```
Wide landscape slide, horizontal process flow with feedback loop, dark navy and red-teal theme.
Steps left to right: "Brief + Research" → "Writer" → "Critic" → "Approved Memo"
Green label "APPROVED" on forward arrow from Critic to Approved Memo.
Curved red back-arrow below the flow from Critic to Writer labeled "REVISION NEEDED"
Bold white labels, dark navy background, teal forward arrows, red feedback arrow, 16:9 wide format.
```

---

## Prompt 5: Pattern 4: Dynamic Swarm

**Dónde va:** `samples/05-dynamic-swarm/`

```
Wide landscape slide, network diagram, 4 outer nodes around a center node, dark navy and teal theme.
Center node: "Shared Working Memory"
Outer nodes: "Researcher", "Analyst", "Writer", "Task Input"
Bidirectional teal arrows connecting each outer node to the center.
Curved arrows between outer nodes showing agent-to-agent handoffs.
Title: "No fixed path: emergent routing"
Bold white labels, dark navy background, 16:9 wide format.
```

---

## Prompt 6: Pattern 5: Agent-as-Tool

**Dónde va:** `samples/06-agent-as-tool/`

```
Wide landscape slide, hierarchical diagram top to bottom, dark navy and green theme.
Top center node: "Orchestrator: LLM routing"
Three nodes below in a row: "@tool researcher_agent", "@tool analyzer_agent", "@tool synthesizer_agent"
Subtitles below each: "Docstring = routing logic", "callback_handler=None", "streams to user"
Downward green arrows from Orchestrator to each specialist.
Bold white labels, dark navy background, 16:9 wide format.
```

---

## Prompt 7: Decision-Memo Capstone

**Dónde va:** `samples/07-capstone/`

> ⚠️ Si Canva AI no respeta el layout, construirlo manualmente usando el diagrama draw.io como base.

```
Wide landscape slide, horizontal roadmap, 4 equal columns left to right, dark navy and teal theme.
Title: "Decision-Memo System"
Subtitle: "Sequential · Parallel · Critic-Refiner · Agent-as-Tool"
Column 1 "Input" (teal border): "Decision Brief", "NovaCart Premium Tier"
Column 2 "Research + Analyze" (cobalt blue border): "Researcher", "Analyzer A · B · C parallel"
Column 3 "Quality Gate" (red border): "Writer", "Critic: APPROVED loop"
Column 4 "Output" (green border): "Synthesizer", "Leadership Memo"
Teal arrows between columns, dark navy background, 16:9 wide format.
```
