# Workshop Fixes — Módulos 01-04

Source: test agents run 2026-08-20. All issues verified by running the code.

---

## STATUS KEY
- [ ] Pendiente
- [x] Resuelto
- [~] En progreso

---

## CRÍTICOS (rompen la experiencia del asistente)

### FIX-01 · Module 02 — `obs_result` NameError crashea el notebook
- **Archivo:** `samples/02-single-agent/module-02.ipynb` celda `9a9dc07e`
- **Problema:** `obs_result.metrics.get_summary()` — `obs_result` nunca se define. Variable correcta: `result`.
- **Fix:** Reemplazar `obs_result` por `result` en esa celda.
- [x] Resuelto

### FIX-02 · Módulos 01 y 02 — Métricas de tokens imprimen `n/a`
- **Archivos:**
  - `samples/01-foundations/module-01.ipynb` (celda de observabilidad)
  - `samples/02-single-agent/module-02.ipynb` (celda de métricas)
- **Problema:** El código usa `summary['input_tokens']` / `summary['output_tokens']` (claves planas inexistentes).
  La ruta correcta es `summary['accumulated_usage']['inputTokens']` / `['outputTokens']`.
- **Fix:** Actualizar las celdas para usar las claves correctas.
- [x] Resuelto

### FIX-03 · Module 01 — Loop inspector no muestra tool results
- **Archivo:** `samples/01-foundations/module-01.ipynb` (celda del loop inspector)
- **Problema:** El inspector solo maneja bloques `"text"` en user-role messages.
  Strands guarda los tool results como bloques `"toolResult"`, que quedan en blanco.
- **Fix:** Actualizar el inspector para manejar ambos tipos de bloque.
- [x] Resuelto

---

## DOCUMENTACIÓN (no rompen el código, pero confunden al asistente)

### FIX-04 · Module 02 — `chat.py` dice "Module 1"
- **Archivo:** `samples/02-single-agent/chat.py` línea 2
- **Problema:** Docstring dice `Interactive multi-turn chat for Module 1: Strands Foundations`
- **Fix:** Cambiar a `Module 2: Single Agent`
- [x] Resuelto

### FIX-05 · Module 02 — Notebook "What's Next" apunta a "Module 8"
- **Archivo:** `samples/02-single-agent/module-02.ipynb` celda `70fc0f7c`
- **Problema:** Dice "Module 8: Sequential Chain" — debe ser "Module 3"
- **Fix:** Corregir número de módulo.
- [x] Resuelto

### FIX-06 · Module 02 — Notebook companion cell usa `pip` en lugar de `uv`
- **Archivo:** `samples/02-single-agent/module-02.ipynb` celda `4c37518d`
- **Problema:** La celda al final del notebook dice `pip install` y `python chat.py` (no `uv`)
- **Fix:** Cambiar a `uv pip install` y `uv run python chat.py`
- [x] Resuelto

### FIX-07 · Module 03 — `cleanup.py` intenta borrar `_orchestrator` que no existe
- **Archivo:** `samples/03-sequential-chain/production/cleanup.py`
- **Problema:** `runtime_names` y `role_names` incluyen `_orchestrator` y `orchestrator-role`
  que `deploy.py` nunca crea.
- **Fix:** Eliminar esas entradas del listado.
- [x] Resuelto

### FIX-08 · Module 04 — `chat.py` header dice "Module 3"
- **Archivo:** `samples/04-parallel-fork-join/chat.py`
- **Problema:** Header dice "Module 3: Parallel / Fork-Join" y path `samples/03-parallel-fork-join`
- **Fix:** Corregir a Module 4 y `samples/04-parallel-fork-join`
- [x] Resuelto

### FIX-09 · Module 04 — `production/main.py` logger referencia `m3`
- **Archivo:** `samples/04-parallel-fork-join/production/main.py`
- **Problema:** `logger.info("session.id=%s module=m3-parallel-fork-join", ...)` — stale de M3
- **Fix:** Cambiar `m3` por `m4`
- [x] Resuelto

### FIX-10 · Module 04 — README menciona `nest-asyncio` que no está en requirements
- **Archivo:** `samples/04-parallel-fork-join/README.md`
- **Problema:** Sección Files dice `requirements.txt` contiene `nest-asyncio>=1.6.0` — no existe en el archivo
- **Fix:** Eliminar esa referencia del README.
- [x] Resuelto

### FIX-11 · Module 04 — `cleanup.py` intenta borrar 4 runtimes pero deploy crea 3
- **Archivo:** `samples/04-parallel-fork-join/production/cleanup.py`
- **Problema:** `runtime_names` incluye `_orchestrator`; `role_names` incluye `orchestrator-role`.
  `deploy.py` solo crea 3 runtimes y 1 role.
- **Fix:** Eliminar las entradas de orchestrator del listado.
- [x] Resuelto

---

## DEL CHAT MULTI-TURNO (módulos 01-04)

### FIX-12 · Module 03 — `chat.py` no llama `set_execution_timeout()` → warning en stdout
- **Archivo:** `samples/03-sequential-chain/chat.py` función `run_chain()` línea ~78
- **Problema:** `GraphBuilder` se construye sin `set_execution_timeout()`. El SDK imprime en stdout:
  `"Graph without execution limits may run indefinitely if cycles exist"`
  Esto aparece antes de cada resultado y confunde a los asistentes del workshop.
  Module 04 chat.py ya lo tiene correcto (`set_execution_timeout(300)`).
- **Fix:** Agregar `builder.set_execution_timeout(300)` antes de `builder.build()`.
- [x] Resuelto

---

## MÓDULO 06 — Dynamic Swarm (IT Incident Response)

### FIX-13 · M06 — `cleanup.py` borra nombres equivocados (researcher/analyst/writer)
- **Archivo:** `samples/06-dynamic-swarm/production/cleanup.py`
- **Problema:** `runtime_names` lista researcher/analyst/writer/orchestrator. `deploy.py` crea monitor/network_specialist/db_admin/resolver/orchestrator. Cleanup nunca borra los 4 specialists reales.
- [x] Resuelto

### FIX-14 · M06 — `invoke.py` envía brief de NovaCart (dominio incorrecto)
- **Archivo:** `samples/06-dynamic-swarm/production/invoke.py`
- **Problema:** Payload es el brief de decisión de negocio NovaCart. M06 es IT incident response. Causa HTTP 500/424 en los specialists.
- [x] Resuelto

### FIX-15 · M06 — `production/main.py` es código del M05 (agentes y dominio incorrectos)
- **Archivo:** `samples/06-dynamic-swarm/production/main.py`
- **Problema:** Docstring "M5 Production", logger `m5-dynamic-swarm`, usa researcher/analyst/writer con mock_tools NovaCart. Artefacto stale del M05.
- [x] Resuelto — reescrito como IT incident response Swarm (monitor/network_specialist/db_admin/resolver)

### FIX-16 · M06 — Notebook celda `255048da`: `node_timeout=90s` demasiado agresivo
- **Archivo:** `samples/06-dynamic-swarm/module-06.ipynb` celda `255048da`
- **Problema:** `node_timeout=90.0` provoca FAILED en cold start (db_admin tardó 108s). El mismo swarm completa OK por chat.py.
- [x] Resuelto — aumentado a `node_timeout=180.0`

### FIX-17 · M06 — `production/README.md` referencias a specialists del M05
- **Archivo:** `samples/06-dynamic-swarm/production/README.md`
- **Problema:** Files table y sección Deploy listan researcher/analyst/writer y "4 runtimes".
- [x] Resuelto — corregido a monitor/network_specialist/db_admin/resolver y "5 runtimes"

### FIX-18 · M06 — `README.md` usa `pip` en lugar de `uv`
- **Archivo:** `samples/06-dynamic-swarm/README.md` línea 75
- [x] Resuelto

---

## MÓDULO 07 — Agent-as-Tool (Investment Analysis)

### FIX-19 · M07 — `orchestrator/main.py` NameError: `sys` antes de `import sys`
- **Archivo:** `samples/07-agent-as-tool/production/orchestrator/main.py` línea 31
- **Problema:** `sys.path = ...` antes de `import sys` → NameError en startup. Invoke falla al 100%.
- [x] Resuelto — movido `import sys` antes de la asignación

### FIX-20 · M07 — `cleanup.py` borra nombres equivocados (researcher/analyst/synthesizer)
- **Archivo:** `samples/07-agent-as-tool/production/cleanup.py`
- **Problema:** `runtime_names` lista researcher/analyst/synthesizer/orchestrator. `deploy.py` crea research/finance/legal/writer/orchestrator. 4 specialists leaked en cada cleanup.
- [x] Resuelto

### FIX-21 · M07 — `production/main.py` dice "M6 Production" y logger `m6-agent-as-tool`
- **Archivo:** `samples/07-agent-as-tool/production/main.py`
- [x] Resuelto — M6 → M7

### FIX-22 · M07 — `README.md` alt-text con nombres del refactor anterior
- **Archivo:** `samples/07-agent-as-tool/README.md` línea 7
- **Problema:** researcher_agent/analyzer_agent/synthesizer_agent → research_agent/finance_agent/legal_agent/writer_agent
- [x] Resuelto

### FIX-23 · M07 — `production/README.md` specialist paths y conteo incorrectos
- **Archivo:** `samples/07-agent-as-tool/production/README.md`
- **Problema:** Files table lista researcher/analyst/synthesizer. Dice "4 Runtimes" y "3 A2A specialists". Deploy crea 5 runtimes y 4 specialists.
- [x] Resuelto

### FIX-24 · M07 — `production/chat.py` `import os` antes del docstring + "Capstone" en descripción
- **Archivo:** `samples/07-agent-as-tool/production/chat.py`
- [x] Resuelto — `import os` movido al bloque de imports; descripción corregida

