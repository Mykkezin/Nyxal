# Nyxal

> **Nyxal is a governed AI runtime evolving toward NyxOS.**

Nyxal is an experimental AI system built around a simple principle:

**autonomy can grow without giving up traceability, isolation, or explicit authority.**

## Current state

### Stable foundations
- Nível 9 — controlled evolution
- Nível 10 — formal local cycle
- 56.5.5 — contextual conversation

### NyxOS Habitat
- **M5.1 → M5.24** — habitat, persistence, Delta, control, physiology, machine presence, atuação supervisionada, áudio e voz supervisionada
- **M5.23** — STT/TTS reais na borda (`faster-whisper` + `Kokoro`)
- **M5.24** — ciclo supervisionado explícito STT → TTS

### Governed auto-evolution
- **AE1** — discovery
- **AE2** — isolated experiment
- **AE3** — comparison and learning
- **AE4** — resident orchestration
- **AE5** — continuous economic/evidence discovery

AE1 → AE5 remain governed capabilities. They do not grant automatic integration authority.

### Learning Loop Causal
- **LLC.1** — deterministic influence of prior learning on decision
- **LLC.2** — operational feedback and transition closure
- **LLC.3** — controlled causal-evidence protocol
- **LLC.4** — real habitat environmental observation
- **LLC.5** — longitudinal controlled evidence
- **LLC.6** — evidence provenance integrity
- **LLC.7** — distinct verifiable replication
- **LLC.8** — scope limitation
- **LLC.9** — auditable learning
- **LLC.10** — loop closure

The complete LLC chain is implemented and validated according to its respective gates. It does not authorize automatic architectural integration, universal causality or unrestricted autonomy.

## Architecture
```
HARDWARE
   ↓
LINUX
   ↓
NYXOS
   ↓
Runtime / Corpo / Memória / Conhecimento / Ferramentas
/ Processos / Experimentos / Interface / Delta
   ↓
NYXAL
```

The current NyxOS line remains a Linux-first habitat. A custom kernel is a later direction, not a shortcut around the current architecture and governance work.

## Agent integrations (experimental)

The agent integration branch adds optional routing across the local Nyxal/Qwen core, Gemini, Hermes Agent and Letta, plus read-only host observability, Gmail OAuth and Gemini image creation/editing. Versioned skills cover design, image editing, audio/video, development, email triage, system observability, NyxOS operation and safe messaging.

These integrations are **not connected until credentials, OAuth consent, local services and account pairing are configured and verified on the machine**. API keys, OAuth files and WhatsApp sessions remain outside Git. Gmail access is read-only in this phase. Host observation is read-only; actions with side effects require separate authorization.

See [docs/NYXAL_AGENT_STACK.md](docs/NYXAL_AGENT_STACK.md) for setup and security boundaries.

## Evolution pipeline
```
limitation → hypothesis → formal request → experimental artifact
→ baseline → isolated experiment → result → comparison
→ learning → candidate/proposal → explicit authorization
→ prepared integration → review/merge → stable
```

**Discovery is not authorization.**

**Experimentation is not integration.**

**A measured improvement is not permission to modify stable.**

## Development line
**Stable:** `main`.

The current main line contains the validated Nível 9/10, M5.1→M5.24 and LLC.1→LLC.10 architecture.
Historical references to pending LLC stages or pre-M5.24 states are not current architectural status.

## Governance
- Automatic voice remains disabled.
- Continuous capture and wake word remain disabled.
- Automatic physical execution remains disabled.
- Proposal, candidate or experimental result is not integration authorization.
- M6 and AE6 are not created automatically.

## Vision
Nyxal is not being built as a chatbot with a few extra tools.

The goal is a **living software system** with an operational habitat, persistent state, observable processes and resources, controlled experimentation, reusable learning and governed evolution.

> **More autonomy, without less accountability.**

## Status
This is an active experimental engineering project.
The current architectural phase is closed at M5.24. The next phase must be derived from a new architectural review and measurable operational need rather than from an automatically incremented milestone.