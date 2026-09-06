---
name: benchmarking-mlx-vlm
description: >
  Measure mlx-vlm/MLX performance credibly for perf comparisons, regressions,
  or upstream PR evidence: median-of-N with warmup, mx.eval/mx.synchronize
  before stopping timers, peak-memory protocol, and A/B discipline across MLX
  versions. Use when timing model changes, comparing local MLX builds, or
  preparing perf numbers for maintainers. This repo uses conda + pip, never uv.
---

# Benchmarking mlx-vlm (conda + pip)

Adapted from the upstream mlx-vlm `benchmarking` skill
([`skills/skills/benchmarking`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/benchmarking), added by
[Blaizzy/mlx-vlm#1747](https://github.com/Blaizzy/mlx-vlm/pull/1747)),
rewritten for this repo's conda + pip workflow. The upstream fork-clone
`uv venv` A/B script is intentionally not carried over — comparative runs here
go through `check_models` itself or a single-env A/B (below).

## Non-negotiables for credible numbers

1. **MLX is lazy** — call `mx.eval(outputs)` (or `mx.synchronize()`) before
   stopping any timer, otherwise you time graph construction, not compute.
2. **Warmup then median-of-N** — discard at least one warmup iteration
   (kernel compilation, cache population), then report the **median** of ≥5
   timed runs, not the mean of everything.
3. **Peak memory** — `mx.reset_peak_memory()` before the timed region,
   `mx.get_peak_memory() / 1e9` (GB) after. Report latency *and* peak memory;
   a speedup that doubles memory is not a win.
4. **Inline correctness assertion** — every benchmark asserts its output
   matches a reference (e.g. `mx.allclose` against the baseline path, or a
   fixed expected generation for deterministic `--temperature 0.0` runs).
   A fast wrong kernel is worthless.
5. **One swept parameter per table** — print results as a Markdown table with
   `flush=True`; state chip and RAM (e.g. "M5 Max, 128 GB") with every table.
6. **One model per process** — Metal state does not reset reliably in-process;
   fresh `python -m …` invocations per configuration.

## Micro-benchmark helper

```python
import time
import mlx.core as mx

def bench(fn, *args, warmup=2, runs=7):
    """Median seconds for fn(*args) with lazy-eval flushing."""
    for _ in range(warmup):
        mx.eval(fn(*args))
    times = []
    for _ in range(runs):
        mx.synchronize()
        start = time.perf_counter()
        mx.eval(fn(*args))
        mx.synchronize()
        times.append(time.perf_counter() - start)
    return sorted(times)[len(times) // 2]
```

Use random-init tiny-config synthetic models where possible so no checkpoint
download is needed; keep repro scripts uncommitted (paste them into the PR or
issue instead).

## A/B across MLX versions (conda + pip)

```bash
conda activate mlx-vlm

# Baseline numbers on the current install
cd src && python -m check_models --models <model> --image <img> > /tmp/a.log

# Switch the candidate build (editable local repo or pinned wheel), then rerun
pip install -e ../../mlx   # or: pip install mlx==<version> mlx-metal==<version>
python -m check_models --models <model> --image <img> > /tmp/b.log
```

- `check_models` already reports generation TPS, prefill/first-token latency,
  and peak memory per model — prefer those captured metrics over ad-hoc
  timers for whole-model comparisons; `results.history.jsonl` retains prior
  runs for the same machine.
- Record `pip show mlx mlx-vlm` (version + editable origin) with every
  measurement; the `results.jsonl` metadata header captures this
  automatically for check_models runs (`library_versions`,
  `component_provenance`, `runtime_fingerprint`, `system`).
- `--compare-with` diffs a sweep against the retained baseline and withholds
  tok/s and peak-memory comparisons unless chip, execution mode (`--isolate`
  or not), prompt, image digest, and generation settings all match; a
  hand-rolled A/B must respect the same like-for-like rule.
- Restore the environment afterwards (`bash src/tools/update.sh` or
  `pip install -e .[dev,extras,torch]` from `src/`).

## Presentation rules (for upstream PRs/issues)

- Paste the exact benchmark script and the raw table — no prose-only claims.
- Report both latency and peak memory, plus the correctness assertion used.
- State the swept parameter, fixed parameters, chip, RAM, macOS, and the mlx /
  mlx-vlm versions (with commit SHAs for editable installs).

## Rules

- **Do not** use `uv run` / `uv venv`.
- **Do not** commit benchmark scripts or output logs to this repo.
- For upstream issue drafts built on these numbers, follow
  `upstream-mlx-vlm-issues`; for isolating failures first, follow
  `native-mlx-vlm-repro`.
