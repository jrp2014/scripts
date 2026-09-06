---
name: upstream-mlx-vlm-contributing
description: >
  Shape a change to upstream mlx-vlm so it lands cleanly, working from the
  editable checkout this project already installs: where processor, model and
  test code go, backward-compatible config args, running the focused upstream
  tests, matching upstream's black/isort/autoflake hooks with the ruff already
  installed here, and PR expectations (tests, review, perf evidence). Use when
  a check_models finding
  turns into an upstream fix rather than an issue. This repo uses conda + pip,
  never uv.
---

# Contributing to upstream mlx-vlm (conda + pip)

Adapted from the upstream `contributing` skill
(`skills/skills/contributing/SKILL.md` in
[Blaizzy/mlx-vlm](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/contributing),
added by [#1747](https://github.com/Blaizzy/mlx-vlm/pull/1747)), rewritten
for this project's conda + pip workflow and for the usual route here: a
harness finding, confirmed natively, becomes a small upstream fix. Read the
upstream skill for the full text; this page keeps only what differs or what
this project needs most often.

## Where the checkout is

This environment already has mlx-vlm installed editable from a sibling
checkout; do not clone a second copy:

```bash
conda activate mlx-vlm
pip show mlx-vlm | grep -i "editable project location"   # the checkout to work in
cd "$(pip show mlx-vlm | sed -n 's/^Editable project location: //p')"
git status -sb && git log --oneline -1                     # clean, on main, note the SHA
```

Work on a branch in that checkout. Keep this repository's `update.sh`
expectations in mind: a dirty or non-main mlx-vlm checkout changes what the
next `check_models` run reports as component provenance, so finish or stash
the branch before the next sweep.

## Where things go

- **Model code:** `mlx_vlm/models/<model_type>/`; the main file is named after
  the `config.json` `model_type`. Related variants are separate packages
  (`glm4v` and `glm4v_moe` are different directories with their own
  `processing.py`), so a fix to one family's processor does **not** reach its
  siblings; check every directory that serves the affected checkpoints.
- **Processor output handling:** `processing*.py` in the model directory.
  Post-generation cleanup lives in the processor's optional `clean_output()`
  hook (upstream `generate()` and this harness both call it); special tokens
  such as answer delimiters are registered there too.
- **Config args:** the model's `ModelConfig` in `<model>/config.py`, with an
  inline comment and a backward-compatible default (`None`/`0`/`False`) so
  existing checkpoints load unchanged.
- **Tests:** model tests as a class per feature in `mlx_vlm/tests/test_models.py`;
  processor and output-handling tests in `mlx_vlm/tests/test_processors.py`
  (see `TestOutputControlTokens` from #2170 for the shape: construct the
  processor with `object.__new__`, stub the tokenizer, assert on the hook).
  Prefer tiny synthetic inputs; never a standalone `test_<feature>.py`.

## Run the focused tests (pip, not uv)

```bash
conda activate mlx-vlm
cd "$(pip show mlx-vlm | sed -n 's/^Editable project location: //p')"
python -m pytest mlx_vlm/tests/test_processors.py -q -k "<ClassName>"
python -m pytest mlx_vlm/tests/test_models.py -q -k "<ClassName>"
```

Then prove the change on the real checkpoint with one native command
(`native-mlx-vlm-repro` skill), pinned to the revision the harness resolved.

## Formatting: upstream's hooks are a subset of this repository's rules

Upstream's `.pre-commit-config.yaml` runs **black** (defaults, 88 columns),
**isort** (`--profile=black`) and **autoflake** (unused imports). This
repository's ruff rule set is strictly wider: code that passes `ruff check`
under `src/pyproject.toml` already has isort-clean imports and no unused
imports, so write the upstream change to this repository's standard and do
not install black, isort or autoflake. The one thing to match deliberately is
black's layout, because this repository formats at 100 columns and upstream
at 88. Check it with ruff run in isolation from this repository's config:

```bash
cd "$(pip show mlx-vlm | sed -n 's/^Editable project location: //p')"
ruff format --isolated --line-length 88 --diff <changed files>   # review, then apply your hunks
ruff check  --isolated --line-length 88 --select I,F401 <changed files>
```

Apply only the hunks inside your change: ruff joins implicit string
concatenations that black leaves alone, so a whole-file apply can touch lines
you did not write (upstream's `test_processors.py` has several). If upstream
CI's black still objects, the hook run is
`pip install pre-commit && pre-commit run --files <changed files>` in the
upstream checkout; that is the only place black is needed, never this
repository's hook set. Conversely this repository's gate (its ruff config,
mypy, ty, pyrefly, Skylos) does not apply to upstream code; do not run
`make quality` against the mlx-vlm checkout.

## PR expectations

1. Fork, branch, open the PR against upstream `main`; keep the change scoped
   and opt-in, never regressing existing checkpoints.
2. Tests accompany any code that should be tested (above).
3. Performance-sensitive changes need self-contained perf evidence: follow
   `benchmarking-mlx-vlm` for the protocol and table format.
4. Link the issue the change closes; if a check_models artifact motivated it,
   paste the minimal native repro, not the harness report.
5. Hook-clean diff as the last step before pushing.

## Upstream-only skills (reference, not replicated)

These target work inside an mlx-vlm checkout that this project does not do,
so they are not adapted here. Read them upstream when needed, remembering
that every `uv run …` there is `python -m …` under conda + pip here:

- [`add-new-model`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/add-new-model)
  for porting an architecture.
- [`convert-quantize`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/convert-quantize)
  for `mlx_vlm.convert`, quant modes and calibration.
- [`server-inference`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/server-inference)
  for `mlx_vlm.server` and the OpenAI-compatible endpoints.

Upstream also publishes the whole bundle as a Claude Code plugin
(`.claude-plugin/marketplace.json` at the repository root, plugin name
`mlx-vlm-skills`), which is the cleanest way to use those skills verbatim
without copying them into this tree.

## Rules

- **Do not** use `uv run` / `uv pip`; **do not** commit upstream repro or
  benchmark scripts to this repository.
- Do not open the PR or push to the fork unless the user asks; prepare the
  branch, tests and PR text and stop.
- Filing an issue instead: `upstream-mlx-vlm-issues`.
