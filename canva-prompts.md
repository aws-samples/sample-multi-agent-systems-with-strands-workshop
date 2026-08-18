# Canva AI Prompts — Multi-Agent Workshop Diagrams

Prompts optimizados para **Canva AI Magic Design**. Cada prompt sigue la fórmula: `[TYPE] [LAYOUT] in [STYLE], [COLOR]. Content: [FLAT LIST]. [ONE visual detail].`

> **Post-generación (siempre):** Canva AI genera portrait. Para convertir a landscape 16:9:
> Resize → Custom → **1920 × 1080** → "Resize" (no "Copy & resize") → **Cmd+A** → stretch todos los elementos horizontalmente.

---

## Prompt 1 — Strands Agent Loop

**Dónde va:** `samples/01-strands-foundations/` — explica el loop agéntico antes del primer ejercicio.

```
Horizontal process flow diagram, 5 steps, modern dark style, dark navy and teal theme.
Steps: "Input & Context" → "Reasoning LLM" → "Tool Selection" → "Tool Execution" → "Response"
Subtitles: "prompt + history", "plans next step", "picks the right tool", "runs it, gets result", "goal met → stop"
Add a curved teal back-arrow below steps 2-3-4 labeled "repeat until done"
Bold white labels, dark navy background, teal animated arrows.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 2 — Pattern 1: Sequential Chain

**Dónde va:** `samples/02-sequential-chain/` — muestra la cadena lineal antes del notebook.

```
Horizontal process flow diagram, 5 steps, modern minimalist style, dark navy and teal theme.
Steps: "Decision Brief" → "Researcher" → "Analyst" → "Synthesizer" → "Leadership Memo"
Subtitles: "", "gathers data with tools", "evaluates all options", "writes the memo", ""
Bold white labels, teal right-pointing arrows, dark navy background, professional workshop style.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 3 — Pattern 2: Parallel Fork-Join

**Dónde va:** `samples/03-parallel-fork-join/` — muestra el fork antes del notebook.

```
Horizontal process flow diagram with fork and merge sections, dark navy and cobalt blue theme.
Steps: "Decision Brief" → "Researcher" → fork to "Analyzer A", "Analyzer B", "Analyzer C" → merge to "Synthesizer" → "Leadership Memo"
Add label "asyncio.gather — run simultaneously" across the parallel section.
Bold white labels, cobalt blue parallel arrows, teal main flow arrows, dark navy background.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 4 — Pattern 3: Critic-Refiner

**Dónde va:** `samples/04-critic-refiner/` — muestra el ciclo de calidad antes del notebook.

```
Horizontal process flow diagram with feedback loop, dark navy and red-teal theme.
Steps left to right: "Brief + Research" → "Writer" → "Critic" → "Approved Memo"
Add green label "APPROVED" on the forward arrow from Critic to Approved Memo.
Add a curved red back-arrow below returning from Critic to Writer labeled "REVISION NEEDED"
Bold white labels, dark navy background, teal forward arrows, red feedback arrow.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 5 — Pattern 4: Dynamic Swarm

**Dónde va:** `samples/05-dynamic-swarm/` — muestra el routing autónomo antes del notebook.

```
Network diagram, 4 outer nodes around a center node, dark navy and teal theme.
Center node label: "Shared Working Memory"
Outer nodes: "Researcher", "Analyst", "Writer", "Task Input"
Bidirectional teal arrows connecting each outer node to the center node.
Add curved arrows between outer nodes to show agent-to-agent handoffs.
Bold white labels, dark navy background, title text "No fixed path — emergent routing".
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 6 — Pattern 5: Agent-as-Tool

**Dónde va:** `samples/06-agent-as-tool/` — muestra la jerarquía antes del notebook.

```
Hierarchical diagram top to bottom, dark navy and green theme.
Top center node: "Orchestrator — LLM routing"
Three nodes below in a row: "@tool researcher_agent", "@tool analyzer_agent", "@tool synthesizer_agent"
Downward green arrows from Orchestrator to each specialist node.
Subtitles below each specialist: "Docstring = routing logic", "callback_handler=None", "streams to user"
Bold white labels, dark navy background, green delegation arrows.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Prompt 7 — Decision-Memo Capstone

**Dónde va:** `samples/07-capstone/` — muestra el sistema completo antes del notebook.

> ⚠️ Este diagrama tiene 3+ niveles de anidamiento — si Canva AI no lo logra bien, construirlo manualmente usando el diagrama draw.io como referencia visual.

```
Horizontal roadmap slide, 4 equal columns left to right, dark navy and teal theme.
Title: "Decision-Memo System"
Subtitle: "Parallel heads · Critic-Refiner review · Agent-as-Tool specialists · Sequential synthesis"
Column 1 "Step 1" (teal border): "Decision Brief", "NovaCart Premium Tier"
Column 2 "Step 2" (blue border): "Researcher", "Analyzer A · B · C parallel"
Column 3 "Step 3" (red border): "Writer", "Critic loop — APPROVED"
Column 4 "Step 4" (green border): "Synthesizer", "Leadership Memo"
Teal arrows between columns. Dark navy background.
```

**Post-generación:** Resize → Custom → 1920 × 1080 → Resize → Cmd+A → stretch horizontal.

---

## Referencia rápida de fixes en Canva

| Problema | Solución |
|----------|----------|
| Layout portrait en lugar de landscape | Normal — resize manual: 1920×1080 → Cmd+A → stretch |
| Contenido duplicado en columna | Cada columna necesita mínimo 2 ítems |
| Texto cortado | Doble click en el text box → agrandar → bajar font size |
| Color incorrecto | Seleccionar elemento → Colors panel → cambiar fill |
| Flecha faltante | Elements → buscar "arrow" → drag entre nodos |
| Subtítulos no alineados | Seleccionar todos → Arrange → "Tidy up" |
