# Retail Token-Efficiency Lab

A deliberately small, standalone lab for learning AI-agent architecture and token efficiency from first principles.

The public τ²-bench retail domain is used only as a **source of realistic data**. This project does **not** import τ² agent classes, its registry, orchestrator, user simulator, or evaluator.

## What is ours vs. what comes from τ²

τ² supplies realistic source artifacts:

- retail `tasks.json`
- retail `db.json`
- retail `policy.md`

This repo supplies the architecture we want to study:

- a plain-Python retail world and tool executor
- explicit tool schemas
- our own agent loop
- our own raw conversation/tool history
- our own context construction
- our own token measurements
- a tiny user simulator used only to drive repeatable experiments

## V0 architecture

V0 is intentionally wasteful:

```text
observation
    ↓
append to raw history
    ↓
full retail policy
+ every tool schema
+ complete raw history
    ↓
LLM
    ↓
text or tool call
    ↓
execute tool against db.json
    ↓
raw tool result goes back into history
```

There is intentionally no planner, RAG, structured state, memory, tool router, summarizer, compaction layer, skill system, or policy retrieval.

The point is to create a measurable control condition before inventing improvements.

## Dataset

`scripts/bootstrap_data.py` downloads a pinned public τ²-bench retail snapshot and keeps five diverse tasks:

- `0` — delivered-item exchange with product-variant lookup
- `2` — product-count question plus multi-item return
- `38` — pending-order reasoning/cancellation path
- `59` — pending-order/address-change workflow
- `113` — cancel all pending orders

The full retail DB is kept locally because DB size is not model-context size: the model only sees records that tools return. The full policy is also kept intentionally so V0 pays its full context cost.

Generated upstream data is ignored by git; provenance is written to `data/source.json`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
python scripts/bootstrap_data.py
```

## Run one experiment

```bash
python run.py --task 0 --agent-model gpt-4.1-mini --user-model gpt-4.1-mini
```

The user simulator is deliberately outside the architecture under study. Token metrics reported by V0 are **agent-model tokens only**.

Results are written under `results/` and include:

- transcript
- observed tool calls
- expected tool calls from the selected τ² task
- expected-action coverage
- per-agent-call API input/output tokens
- estimated static-policy, tool-schema, and history token sizes
- final mutated DB snapshot

## What to look for first

Do not optimize yet. Run V0 and inspect context growth.

For each LLM call, ask:

1. How many tokens came from static policy?
2. How many came from tool schemas?
3. How much did raw history grow?
4. Which old tool outputs were still present but no longer needed?
5. Which tool definitions were irrelevant to this decision?
6. Did the agent succeed anyway?

Only introduce V1 after a concrete measured failure or inefficiency gives us a reason.

## Important limitation

This is a teaching lab, not a drop-in reimplementation of the τ² benchmark. Its lightweight action-coverage check is intentionally simpler than τ²'s full evaluator. When an architecture becomes interesting, we can later validate it again against the original benchmark.
