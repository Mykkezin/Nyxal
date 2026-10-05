# Nyxal

> **Nyxal is a governed AI runtime evolving toward NyxOS.**

Nyxal is an experimental AI system built around a simple principle:

**autonomy can grow without giving up traceability, isolation, or explicit authority.**

The project currently runs as a Linux-first software habitat and is gradually evolving toward a deeper NyxOS architecture.

---

## What is Nyxal?

Nyxal is the AI.

**NyxOS** is the system/habitat that gives the AI a persistent operational environment.

**Delta (Δ)** is the project language for controlled change, evolution, evidence, and versioned transitions.

The long-term architectural direction is:

```
HARDWARE
   ↓
LINUX
   ↓
NYXOS
   ↓
Runtime / Corpo / Memória / Conhecimento
/ Ferramentas / Projetos / Processos / Experimentos
/ Interface / Delta
   ↓
NYXAL
```

The first NyxOS version does **not** require a custom kernel. The immediate goal is to build a reliable habitat over Linux before moving closer to native operating-system territory.

---

## Current state

### Stable foundations

- Nível 9 — controlled evolution
- Nível 10 — formal local cycle
- 56.5.5 — contextual conversation
- 56.5.6 — continuous voice interaction

### NyxOS Habitat

- **M5.1** — real host observability
- **M5.2** — process entities
- **M5.3** — operational persistence
- **M5.4** — Delta events
- **M5.5** — state-driven interface
- **M5.6** — habitat resources
- **M5.7** — resident operational cycle

### Governed auto-evolution

- **AE1** — discovery and opportunity registration
- **AE2** — isolated experiment under policy
- **AE3** — comparison and learning interpretation
- **AE4** — resident evolution-cycle orchestration
- **AE5** — continuous discovery with governed evidence accumulation

The current development line is validating AE5 evidence before defining the next evolution stage.

---

## Evolution pipeline

Nyxal does not jump directly from an idea to a stable system change.

The intended path is:

```
limitation
   ↓
hypothesis
   ↓
formal request
   ↓
experimental artifact
   ↓
baseline
   ↓
isolated experiment
   ↓
result
   ↓
comparison
   ↓
learning
   ↓
candidate
   ↓
proposal
   ↓
explicit authorization
   ↓
prepared integration
   ↓
external review / merge
   ↓
stable registration
   ↓
rollback registrable
```

This separation is intentional.

**Discovery is not authorization.**

**Experimentation is not integration.**

**A measured improvement is not permission to modify stable.**

---

## Architecture

Nyxal is being built as a set of explicit layers rather than one giant autonomous process.

```
                    ┌─────────────────────┐
                    │       NYXAL         │
                    │ conversation / AI   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │       NYXOS         │
                    │ habitat / runtime   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   Observation             Persistence             Delta
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Resident Cycle      │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
           AE1               AE2               AE3
        discovery         experiment       comparison /
                                             learning
             └─────────────────┼─────────────────┘
                               ▼
                              AE4
                    resident orchestration
                               │
                               ▼
                              AE5
                    continuous evidence
                               │
                               ▼
                       Governance / N9
                               │
                               ▼
                     explicit authorization
                               │
                               ▼
                           stable
```

---

## Design principles

### Governed autonomy

Nyxal can observe, evaluate, experiment, learn, and prepare proposals.

It does **not** receive implicit permission to alter stable architecture.

### Reversibility

Important transitions should be inspectable, versioned, and recoverable.

### Isolation

Experimental work stays outside stable until it passes the required gates.

### Explicit authority

Authorization remains a separate state from discovery, experimentation, comparison, and learning.

### Small reversible changes

The development protocol favors focused changes with tests and Git checkpoints rather than uncontrolled self-modification.

---

## NyxOS direction

The project is deliberately following a staged path:

```
Linux-first habitat
      ↓
operational persistence
      ↓
resident processes
      ↓
governed evolution
      ↓
deeper NyxOS system layer
      ↓
Nyx Runtime
      ↓
future native-system experiments
```

The custom kernel direction is a **later** milestone, not a shortcut around the current habitat and governance work.

---

## Repository structure

Some of the most important pieces currently include:

```
nixal_runtime.py
nixal_ciclo_residente.py
nixal_auto_evolucao.py
nixal_auto_experimento_ae2.py
nixal_auto_avaliacao_ae3.py
nixal_ciclo_evolucao_ae4.py

nixal_habitat.py
nixal_processos_habitat.py
nixal_persistencia_operacional.py
nixal_delta.py
nixal_recursos_habitat.py

nixal_evolucao_controlada.py
nixal_evolucao_remota.py
nixal_solicitacao_evolucao.py
nixal_governanca_evolucao.py
nixal_laboratorio_remoto.py

interface/
experimentos/
.github/workflows/
```

---

## Development protocol

Nyxal follows a supervised, versioned workflow:

```
plan
 ↓
record
 ↓
apply
 ↓
test
 ↓
checkpoint
 ↓
sync
 ↓
review
 ↓
stable integration
```

The stable branch is kept separate from active experimental development.

---

## Current development line

**Branch:** `feat/m5-habitat-nyxos`

**Current milestone:** M5 — Habitat NyxOS fechado (M5.8–M5.15)

**Validated before M5.14:** M5.8 dependency map, M5.9 Linux residence, M5.10 host action gateway, M5.11 process/application control, M5.12 thermal body/ventilation layer, M5.13 operational physiology, AE5 evidence checkpoint

**Next:** definir explicitamente a próxima linha de engenharia; nenhum M6 é criado automaticamente.

**Stable branch:** `main`

**Current integration state:** Draft / awaiting explicit authorization

## Vision

Nyxal is not being built as a chatbot with a few extra tools.

The goal is a **living software system** with:

- an operational habitat;
- persistent state;
- conversation and voice;
- observable processes and resources;
- explicit change semantics through Delta;
- controlled experimentation;
- reusable learning;
- governed evolution;
- and, much later, a native-system direction.

The core idea is simple:

> **More autonomy, without less accountability.**

---

## Project identity

**Nyxal** — the intelligence.

**NyxOS** — the habitat.

**Delta (Δ)** — controlled change.

**N9** — governance and evolution gates.

**AE1 → AE5** — the current governed auto-evolution pipeline.

---

## Status

This is an active experimental engineering project.

The repository's development line intentionally contains work that is not yet promoted to `main`.

