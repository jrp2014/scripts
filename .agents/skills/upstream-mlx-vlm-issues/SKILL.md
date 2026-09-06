---
name: upstream-mlx-vlm-issues
description: >
  Create or improve reproducible, maintainer-ready GitHub issue drafts for
  upstream mlx-vlm from check_models failures or native repros. Use for crashes,
  load/processor failures, wrong outputs, media-input bugs, and regressions.
  Prefer existing diagnostics and issue_*.md artifacts. Do not open a GitHub
  issue unless the user explicitly asks. This repo uses conda + pip, never uv.
---

# Upstream mlx-vlm Issue Drafts

Turn a failure into concise, actionable **mlx-vlm** issue Markdown. Default
output is issue-ready text or an improved local draft under `src/output/issues/`.
**Do not** run `gh issue create` or open a PR against upstream unless the user
explicitly requests filing.

Adapted from the upstream `reproducible-github-issues` skill
([`skills/skills/reproducible-github-issues`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/reproducible-github-issues),
added by [Blaizzy/mlx-vlm#1747](https://github.com/Blaizzy/mlx-vlm/pull/1747)), aligned
with this repo’s retained artifacts and pip/conda workflow.

## When to use which artifact

| Situation | Start here |
| --------- | ---------- |
| Hard crash already drafted | `src/output/issues/issue_*.md` |
| Aggregate run / observations | `src/output/reports/diagnostics.md` |
| Sweep overview | `src/output/issues/run_summary.md` |
| Exact machine facts | `src/output/results.jsonl` (metadata header + per-model rows) |
| Environment stamp | `src/output/environment.log`, report provenance blocks |
| Need a minimal native command first | `native-mlx-vlm-repro` skill |

Issue drafts are created only for **hard actionable crashes** by default.
Completed-but-unusable observations stay in diagnostics unless the user asks for
a separate upstream write-up.

## Required information

Collect or infer:

- mlx-vlm version **or** git commit; install method (PyPI, editable, branch).
- Python version, macOS version, chip (for example M-series), Metal vs CUDA.
- Exact model ID or local path and **resolved revision** when known.
- Model source: HF cache, local conversion, or custom checkpoint.
- Exact native CLI command and/or Python `load` → `apply_chat_template` →
  `generate` script (from the draft when available).
- For server-only surfaces: startup command **and** `curl` request body
  (see server section below). Prefer `curl` over client SDKs.
- Input media facts: image dimensions; whether the input can be shared.
- Expected vs actual behavior; full root exception + relevant traceback.
- Whether the failure reproduces **outside** `check_models` with native mlx-vlm.

## Repro minimization

1. Reduce to the smallest native command or request that still fails.
2. Remove private paths, tokens, and unrelated environment variables.
3. Prefer public models and small/synthetic media when possible.
4. One image before multi-input; one model per process.
5. State clearly if it only fails with a private checkpoint.
6. Lead with **root exception + first frames inside mlx-vlm / transformers /
   model code**; keep long harness stacks under an optional details block.
7. Commands use `python -m …` under conda/`pip` — **never** `uv run`.

## Maintainer quality bar

Ready when an mlx-vlm maintainer can run **one** native command (or one server
start + one `curl`) and see the same failure without asking for basic
environment or model details.

Prefer factual language:

- Record phase, package tag, revision, and exact error text.
- Do not invent semantic quality scores or blame narratives.
- Distinguish harness preflight failures from native generate failures.
- Neutral observations (declared EOS/thinking wrappers, unchanged draft fields)
  are reproduction facts, not automatic bug claims.
- A properly closed thinking block followed by substantive final text is neutral,
  including when the rendered prompt seeded its opening delimiter. File only the
  independently reproduced defect: an incomplete block, exhausted token budget,
  absent final answer, or undeclared control/role token.
- Do not use a sanitised gallery preview as the exact media input unless its
  digest matches the retained run manifest. With local-only media, include its
  characteristics and say that the exact input is not published.

## Issue template

Use this shape when authoring or rewriting paste-ready Markdown. Fill from
existing artifacts rather than paraphrasing away exact errors.

````markdown
### Summary

<One sentence describing the failure.>

### Environment

- MLX-VLM:
- mlx:
- Python:
- OS / macOS:
- Hardware / MLX device:
- Install method: <PyPI | editable path | branch>
- check_models (optional context): <version/revision if relevant>

### Model

- Model:
- Resolved revision:
- Source: <HF cache | local path | converted checkpoint>
- Trust remote code: <yes/no>

### Reproduction

```bash
python -m mlx_vlm.generate \
  --model <model> \
  --image <image> \
  --prompt '…' \
  --max-tokens 128 \
  --temperature 0.0
```

Optional Python (when CLI cannot express the failing kwargs):

```python
# load → apply_chat_template → generate; one model per process
```

### Expected behavior

<What should have happened.>

### Actual behavior

<What happened instead.>

### Logs / traceback

```text
<root exception and trimmed upstream frames>
```

### Inputs

<Shareable media description; dimensions; note if synthetic repro works.>
````

## Server-only failures

`check_models` benchmarks by looping over `mlx_vlm.generate.stream_generate`
(the same path upstream `generate()` wraps) and does **not** cover HTTP server
behavior. For `/v1/chat/completions`, `/v1/responses`, streaming,
structured outputs, tools, continuous batching, or `/v1/models` mismatches:

```bash
python -m mlx_vlm.server --model <model-or-path> --port 8080
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/v1/models
```

Capture startup command, server logs, request JSON, status code, and body.
Keep streaming and non-streaming repros separate. Still use conda + pip, not uv.

## Classification hints

| Bucket | Typical signals |
| ------ | --------------- |
| Model / config | missing `image_processor`, bad `config.json`, chat template unset |
| mlx-vlm runtime | failure inside generate / apply_chat_template / processor path |
| Harness preflight | check_models validator before native generate |
| Environment | Metal OOM, disk, permissions |
| Connectivity | download / hub disconnect — usually indeterminate, not a model crash |

## After drafting

- If the user only wanted local improvement: leave the Markdown in chat or under
  `src/output/issues/` without filing.
- If the user asks to file upstream: use their account/process; keep the body
  GitHub-sized; link or attach diagnostics only when needed.
- Do not treat observation-only gallery rows as automatic upstream bugs without
  a minimized native repro and expected/actual behavior.
