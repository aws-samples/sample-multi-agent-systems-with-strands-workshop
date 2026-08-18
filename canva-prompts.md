# Canva AI Prompts — Multi-Agent Workshop Diagrams

Prompts para Canva AI (Magic Design / AI image generation). Después de generar cada imagen: **Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch** para convertir de portrait a landscape.

---

## 1 — Strands Agent Loop

```
Horizontal process flow diagram with internal loop, dark navy background, teal accent theme.
Steps left to right: "Input & Context" → "Reasoning LLM" → "Tool Selection" → "Tool Execution" → "Response"
Add a curved back-arrow from "Tool Execution" returning to "Reasoning LLM" labeled "repeat until done"
Bold white labels inside rounded pill shapes, teal animated arrows, dark navy background, professional workshop style.
```

---

## 2 — Pattern 1: Sequential Chain

```
Horizontal process flow diagram, 4 steps, dark navy and teal theme.
Steps: "Intake" → "Extract" → "Analyse" → "Compose"
Subtitles: "normalize input", "pull key facts", "reason over data", "write the answer"
Bold white labels, clean right-pointing teal arrows, dark background, professional technical workshop style.
```

---

## 3 — Pattern 2: Parallel Fork-Join

```
Horizontal flowchart with fork and merge, dark navy and blue theme.
Left node: "Input"
Three parallel middle nodes stacked vertically: "Worker A", "Worker B", "Worker C"
Right node: "Aggregator"
Arrows fan out from Input to all three workers. Arrows converge from all three workers into Aggregator.
Add label "run simultaneously" across the parallel section.
White labels, blue arrows, dark navy background, clean workshop style.
```

---

## 4 — Pattern 3: Critic-Refiner

```
Horizontal flowchart with feedback loop, dark navy and red-teal theme.
Nodes left to right: "Generator" → "Critic" → "Final Output"
Add a curved red back-arrow below the main flow from "Critic" returning to "Generator" labeled "feedback: revise"
Add green label "passes" on the forward arrow from Critic to Final Output.
White labels, teal forward arrows, red feedback arrow, dark navy background, workshop style.
```

---

## 5 — Pattern 4: Dynamic Swarm

```
Network diagram, 4 agent nodes arranged around a center node, dark navy and teal theme.
Center node: "Shared Context"
Four outer nodes: "Monitor", "Network Specialist", "DB Admin", "Resolver"
Bidirectional teal arrows connecting each outer node to the center and to each other.
Add small curved arrows between outer nodes to suggest autonomous routing.
White labels, dark navy background, title text: "No fixed path — emergent routing"
```

---

## 6 — Pattern 5: Agent-as-Tool

```
Hierarchical diagram top to bottom, dark navy and green theme.
Top center node: "Orchestrator"
Four nodes in a row below: "Research Agent", "Finance Agent", "Writer Agent", "Legal Agent"
Downward arrows from Orchestrator to each specialist node.
Each specialist node has a small wrench or tool icon.
Bold white labels, green arrows, dark navy background, clean workshop style.
```

---

## 7 — Decision-Memo System (Capstone)

```
Wide horizontal process flow diagram with fork and merge, dark navy and teal theme.
Nodes left to right: "Decision Brief" → "Orchestrator" then fork to three parallel nodes "Researcher" and "Analyzer A" and "Analyzer B" and "Analyzer C" then merge into "Critic Loop" then "Synthesizer" → "Leadership Memo"
Show the parallel section with a bracket labeled "parallel"
Add a small cycle arrow inside the "Critic Loop" node.
Bold white labels, teal main flow arrows, blue parallel arrows, dark navy background, wide landscape layout.
```

---

## Notas de uso

- **No usar hex codes** — Canva AI los ignora. Usar nombres: "dark navy", "teal", "blue", "green", "red"
- **No especificar píxeles** — usar términos como "horizontal", "wide", "compact"
- **Después de generar:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontalmente
- **Si el layout es portrait:** normal — siempre pasa con Canva AI. El resize manual lo corrige
