## Copilot / AI Agent Instructions — check_models

Benchmarking tool for MLX Vision Language Models on Apple Silicon. macOS-only, Python 3.13+, conda `mlx-vlm` environment required.

---

### 1. Environment — always do this first

```bash
conda activate mlx-vlm          # REQUIRED before any python/make command
cd src && python -m tools.validate_env && cd ..   # quick sanity check
```

If the environment doesn't exist: `bash src/tools/setup_conda_env.sh`.
For one-off commands without activating: `conda run -n mlx-vlm python ...`.
**Never run bare `python` without the conda environment active.**

For every fresh Git worktree, also bootstrap the ignored repo-local Node lockfile
before running the quality gate:

```bash
npm install --ignore-scripts --prefix src
```

`src/package-lock.json` is deliberately untracked, but dependency-policy and
Markdown-lint tests require a local copy. A missing lockfile in a fresh worktree
is a setup failure, not a product regression.

### 2. Key files (read before editing)

| File | Purpose | Size |
| ------ | --------- | ------ |
| `src/check_models.py` | **Single-file CLI monolith** (~23,000 lines). All logic lives here. | ★ primary edit target |
| `src/check_models_data/quality_config.yaml` | Runtime thresholds loaded by `load_quality_config()` | Edit thresholds here, not in Python |
| `src/pyproject.toml` | Packaging, dependencies, tool config (ruff, mypy, pytest) | Update when adding imports |
| `src/tests/conftest.py` | Shared fixtures: `test_image`, `minimal_test_image`, `realistic_test_image`, `folder_with_images`, etc. | Use existing fixtures |
| `src/tests/test_*.py` | ~23,900 lines across 34 test files | Add tests to existing files |
| `docs/IMPLEMENTATION_GUIDE.md` | Detailed coding standards and architecture decisions | Reference for conventions |
| `src/README.md` | Full CLI docs, all flags, usage examples (~1,600 lines) | Reference for CLI behavior |

### 3. Navigating `src/check_models.py` (section map)

The file is organized in this order — search for these exact landmark headers (formatted as comment blocks) to jump directly to the target area instead of relying on line numbers:

| Section | Key contents | Landmark Header / Search Tag |
| --------- | ------------- | ---------------------------- |
| Imports, config & optional dependency guards | `MISSING_DEPENDENCIES`, `QualityThresholds`, `load_quality_config()` | `SECTION: IMPORTS, CONFIG & OPTIONAL DEPENDENCY GUARDS` |
| Type aliases, protocols & JSONL records | `SupportsGenerationResult`, `SupportsExifIfd`, `JsonlResultRecord` | `SECTION: TYPE ALIASES, PROTOCOLS & JSONL RECORDS` |
| App constants & core result types | `PerformanceResult`, `ResultSet`, `ProcessImageParams`, report block primitives | `SECTION: APP CONSTANTS & CORE RESULT TYPES` |
| Timing, logging & Rich console plumbing | `PerfCounterTimer`, `TimeoutManager`, `LogStyles`, `StyleAwareRichHandler` | `SECTION: TIMING, LOGGING & RICH CONSOLE PLUMBING` |
| Formatting, escaping & detector helpers | `fmt_num`, report escapers, `_detect_repetitive_output`, harness detectors | `SECTION: FORMATTING, ESCAPING & DETECTOR HELPERS` |
| Metrics and field formatting | `analyze_generation_text`, mechanical observation helpers, `format_field_value` | `SECTION: METRICS, SCORING & FIELD FORMATTING` |
| Console, system & image metadata helpers | CLI Rich helpers, library/system info, EXIF/XMP extraction | `SECTION: CONSOLE, SYSTEM & IMAGE METADATA HELPERS` |
| Diagnostics/report context builders | `DiagnosticsConfig`, `ReportRenderContext`, native repro command specs | `SECTION: DIAGNOSTICS/REPORT CONTEXT BUILDERS` |
| Report generators & runtime fingerprints | `generate_diagnostics_report`, `generate_html_report`, `generate_markdown_gallery_report`, `collect_runtime_fingerprint()` | `SECTION: REPORT GENERATORS & RUNTIME FINGERPRINTS` |
| Model processing | CLI argument validation, cache scan, `_load_model`, `process_image_with_model` | `SECTION: MODEL PROCESSING` |
| Isolated model execution | `--isolate` child-interpreter worker: `_run_model_isolated`, `_run_isolated_worker`, JSON round-trip of `PerformanceResult` | `SECTION: ISOLATED MODEL EXECUTION (one child interpreter per model)` |
| CLI run helpers & logging | `setup_environment`, `find_and_validate_image`, `process_models`, result logging | `SECTION: CLI RUN HELPERS & LOGGING` |
| Result enrichment/history/finalization | quality enrichment, JSONL/history, issue drafts, `finalize_execution` | `SECTION: RESULT ENRICHMENT/HISTORY/FINALIZATION` |
| Run comparison | `--compare-with` baseline resolution, `compare_run_results`, history noise bands, summary section | `SECTION: RUN COMPARISON (current sweep vs a retained baseline)` |
| Main orchestration & argparse | `main()`, `main_cli()`, `_build_cli_parser()` | `SECTION: MAIN ORCHESTRATION & ARGPARSE` |

### 4. Architecture & patterns

- **Assessment profiles (0.17+)**: `general` performs task-independent checks;
  `metadata` adds required Title/Description/Keywords fields and duplicate
  keywords. Select by prompt origin or explicit `--assessment-profile`, never by
  parsing prompt prose. Custom prompts and differential triage default to general.
  Short answers, copied hints and length counts are not automatic faults. Reports
  must say when task compliance is unassessed. Keep profile provenance through
  isolated workers and retained JSON. Legacy observation codes remain readable,
  but do not revive their retired detectors merely to satisfy old fixture tests.
- **Single CLI runner**: discovers models (HF cache scan), runs each with per-model
  isolation (timeouts, try/except), and generates retained HTML, gallery Markdown,
  diagnostics Markdown, schema-3 JSONL, index, log, environment, and raw history
  artifacts.
- **Configuration hierarchy**: `src/check_models_data/quality_config.yaml` → `QualityThresholds` / `FormattingThresholds` dataclasses. Never sprinkle magic numbers.
- **Dependencies**: optional packages are guarded with `try/except ImportError` → populate `MISSING_DEPENDENCIES`; core runtime deps (`mlx`, `mlx-vlm`, `transformers`) hard-fail before inference in `_raise_for_missing_runtime_dependencies`. `mlx-lm` is not a dependency at all (mlx-vlm dropped it in 0.6.14 and nothing here imports it) — do not reintroduce it as a floor, an extra, or a report row.
- **Generation seam**: every inference goes through `_generate_with_repetition_guard`, a loop over upstream `mlx_vlm.generate.stream_generate` that mirrors upstream `generate()` (custom EOS registration, draft-chunk skipping, final-chunk metrics) and adds the tail-cycle abort. There is no direct `generate()` call, so nothing upstream prints for us: verbose echo of non-draft chunks, `text_already_printed` handling, and `processor.clean_output` all live at that seam and must be covered by tests there.
- **Isolation**: `--isolate` (opt-in) runs one child interpreter per model. The parent writes the child spec with `_isolated_worker_spec` and the child reads it with `_isolated_params_from_spec`; keep them a matched pair and remember that tests with a mocked subprocess never exercise the child parser — the round-trip test does.
- **Display normalization**: ALL metric formatting goes through `format_field_value(field_name, value)`. Do not format metrics inline.
- **Type aliases**: `MetricValue = int | float | str | bool | None` is the value type for metrics.
- **Protocols over ABCs**: typing for optional deps uses `Protocol` classes (e.g., `SupportsGenerationResult`).
- **Reports write to** `src/output/reports/` (`results.html`,
  `model_gallery.md`, and `diagnostics.md`) and `src/output/` (`index.md`,
  `results.jsonl`, `check_models.log`, `environment.log`, and append-only
  `results.history.jsonl`); relocate the whole layout with `--output-dir`,
  the only output-location control. `results.jsonl` (schema 3.0) is the sole
  current-run machine contract: its metadata header carries the run-level
  context (image, generation settings, cache discovery, component
  provenance, comparison, counts, wall-clock runtime, artifact manifest);
  there is no separate `run.json` any more. `src/output/issues/run_summary.md`
  is the primary skim surface for a sweep (objective statement, timing,
  comparison against the retained baseline, per-model transitions).
  Navigation surfaces (`index.md`, terminal artifact log) list only artifacts
  whose `ReportArtifactOutcome` succeeded this run — never stale files found
  on disk. Hard actionable crashes additionally create factual
  `issue_*.md` drafts under `src/output/issues/`. The final rewrite of
  `results.jsonl` (manifest reconciliation) is atomic, so a failure leaves
  the pre-report file intact.
- **Tracked vs local-only outputs**: every run artifact — the human reports
  (`results.html`, `model_gallery.md`), decision artifacts (`index.md`,
  `diagnostics.md`, `results.jsonl`, `environment.log`,
  `issues/run_summary.md`, `issues/issue_*.md`, `reports/assets/`), and the run log (`check_models.log`) — is
  committed each run so it is browsable on GitHub. Only the append-only
  `results.history.jsonl` is gitignored and local-only; no report links to
  it, so no special link handling exists for it.
- **Security**: defaults to `--trust-remote-code` and warns when enabled. The CLI no longer mutates `transformers` backend-selection environment variables at startup.

### 5. Make targets (all run from repo root)

| Target | What it does |
| -------- | ------------- |
| `make quality` | **Primary gate**: checks Ruff formatting + lint, mypy, ty, pyrefly, vulture, Skylos quality/secrets/SCA plus `-a` audit and the blocking `--danger` gate, full pytest, shellcheck, markdownlint. Steps run sequentially; Skylos scans before pytest. |
| `make skylos-danger` | Advisory Skylos `--danger` scan (diff-aware on PRs) for triage; the same scan runs blocking inside `make quality` full mode |
| `make skylos-danger-llm` | Advisory Skylos `--danger` scan with LLM-optimized output for agent triage |
| `make skylos-verify` | Run `skylos verify` with repo project context for narrow post-edit agent checks |
| `make vulture` | Run Vulture dead-code scan for `src/check_models.py` and `src/tools/`. *Note: Vulture commonly flags `TypedDict` keys and `Protocol` signatures as "unused" because they are evaluated statically and not tracked natively in runtime logic flows. Treat these as false positives.* |
| `make test` | Pytest-only shortcut for faster local test loops. Do not run it again after a successful `make quality`; `make quality` already runs the full pytest suite. |
| `make dev` | Install editable with `[dev,extras,torch]` |
| `make install` | Install editable (runtime only) |
| `make format` | Apply `ruff format src/` before running the full quality gate |
| `make -C src lint-fix` | Apply safe Ruff lint fixes (`ruff check --fix`) before running the full quality gate |
| `make lint` | Run Ruff lint early so lint errors are cleared before the full quality gate |
| `make ci` | Full strict CI pipeline |
| `make deps-sync` | Sync README dependency blocks with pyproject.toml |
| `make update` | Full updater via `src/tools/update.sh`: conda/brew refresh, local MLX repo builds, stubs, runtime smoke |
| `make update-quick` | Quick in-env refresh: pip upgrade + editable reinstall with `[dev,extras,torch]` |
| `make clean` | Remove caches and generated outputs |

### 6. Testing guidance

- **Test markers**: `@pytest.mark.slow`, `@pytest.mark.e2e`, `@pytest.mark.subprocess`. Tests in `test_e2e_smoke.py` are auto-marked `slow` + `e2e`.
- **Run a single test file**: `pytest src/tests/test_parameter_validation.py -q`
- **Run with filter**: `pytest src/tests/test_html_formatting.py -k "specific_case" -vv --maxfail=1`
- **Fixtures** (from `conftest.py`): `test_image` (100×100), `minimal_test_image` (10×10), `realistic_test_image` (640×480 with shapes), `folder_with_images`, `empty_folder`, `mlx_vlm_available`, `fixture_model_cached`.
- **Many tests assert exact strings** — if you change report formats or CLI output, update `src/output/` fixtures and check formatting tests.
- **Upstream-version skew**: this project targets the bleeding edge — local development typically runs git-HEAD mlx/mlx-vlm (editable installs), while CI installs the latest PyPI releases. Any test that inspects or compares against the installed upstream (CLI parity, API drift, version floors) must pass against **both**; never assert upstream behavior that differs between release and HEAD (e.g. display-flag defaults), and never assume a finding reproduces in the other environment.
- **Add tests to existing files** (e.g., `test_parameter_validation.py` for new CLI flags, `test_html_formatting.py` for report changes). Do not create standalone test scripts.
- **Validation artifact hygiene**: Validation tests must not rewrite tracked `src/output/` assets, and must not write anywhere under `src/` at all. Route every generated output to a temp directory (`tmp_path`); pytest's own caches are kept out of the tree.
- **Generated Markdown style**: Emit generated Markdown in the repository's markdownlint style directly: keep blank lines around headings and lists; use unique headings or an explicitly configured sibling-heading structure; use asterisks rather than underscores for emphasis; give ordinary fenced blocks proper blank-line spacing and a language identifier; and escape table-cell content. Exact evidence fences must preserve model text, tabs, and trailing spaces byte-for-byte, using only narrow report-local markdownlint configuration where a rule conflicts with that evidence contract.
- **Issue-ready report assembly**: Build aggregate diagnostics from the existing
  typed report blocks and render that same hierarchy to Markdown and HTML. Do not
  create parallel format-specific diagnostic builders or repeat run-wide prompt,
  reproduction, settings, or environment context for every highlighted model.
  Completed observed output appears once as exact code evidence; do not duplicate
  the gallery's readable/raw pair or emit empty `unavailable` fact rows. Keep
  assessment rules mechanical and image-independent, and preserve the exact facts
  behind each observation code in machine and maintainer artifacts.
- **Thinking-output semantics**: A properly closed thinking block followed by a
  substantive final answer is neutral machine evidence, not a usability caveat.
  Downgrade incomplete, truncated, or thinking-only output instead. Account for
  opening delimiters seeded by the rendered prompt before calling a generated
  closing delimiter an unexpected token.
- **Reproduction media**: A sanitised gallery preview is not automatically the
  exact inference input. Emit a runnable media reproduction only for a public URL
  whose bytes match the retained SHA-256. For local-only inputs, publish the exact
  prompt plus format, dimensions, byte size, and digest without inventing a local
  filename an issue reader cannot obtain.
- **Report ergonomics**: Prefer shared Rich/Markdown renderers, shared
  actionability ordering, and existing report blocks over fixed-width strings or
  format-specific builders. Remove redundant columns before adding width logic.
- **Generated-report preflight**: Render representative reports from fixtures into temporary or `test_*` output paths and run markdownlint before the expensive matrix. Generated outputs must not need post-run hand editing. Prefer shared render helpers and focused tests over cleanup passes. If the checkout provides a supported report-only regeneration path, use existing canonical JSONL to repair stale tracked reports before Run 1; do not rerun models merely to reformat captured evidence.
- **Acceptance order**: Before a costly real-model matrix, pass deterministic
  focused tests and the prescribed format, lint-fix/lint, and full `make quality`
  gates. Treat real-model runs as acceptance tests for runtime integration,
  output/report utility, exact evidence preservation, cross-artifact consistency,
  memory, and performance—not as substitutes for ordinary tests.
- **Integration verification reuse**: Record the commit SHA that passed the full
  gate. After a true fast-forward, do not rerun that gate when `HEAD` is exactly
  the already-tested commit and both index and worktree are clean. Rerun whenever
  the target moved, Git created a merge commit, conflicts were resolved, the tree
  changed, or the earlier result did not cover the commit now being integrated.
- **Comparative runs**: If Run 1 exposes a harness or report defect, add a focused
  regression test, fix it, repeat the static/full gates, then rerun and audit Run 1
  before starting comparative Run 2. Never compare a known-invalid baseline.

### 7. CI and hooks

- **Skylos danger scan**: full-mode quality runs (`make quality`, the `static-quality` CI job) execute `bash src/tools/run_skylos_danger_advisory.sh --full --gate`, so danger findings in this repository's own files are **blocking**. Findings under third-party `.worktrees/` checkouts are filtered out of the report with a visible drop notice. The separate GitHub Actions `skylos-advisory` job on `ubuntu-latest` additionally runs the scan in advisory mode for annotation-style surfacing.
- **Static CI job**: GitHub Actions `static-quality` on `macos-15`, a Python matrix of the floor (3.13) plus the next candidate (3.14), Node.js 22. It installs `src/.[dev]`, runs `npm install --ignore-scripts --prefix src`, then runs `bash src/tools/run_quality_checks.sh`, including Skylos quality/secrets/SCA and `-a` audit checks.
- **Runtime CI job**: separate `runtime-smoke` job runs `bash src/tools/run_runtime_smoke.sh` so Metal/runtime failures do not mask static quality results.
- **Dependency sync CI job**: `.github/workflows/dependency-sync.yml` runs on `ubuntu-latest` with path filters and verifies `python -m tools.update_readme_deps --check`.
- **Pre-commit hooks**: `pre-commit install` (from the checked-in `.pre-commit-config.yaml`; `make dev` runs it). Two stages:
  - commit stage: `bash src/tools/run_commit_hygiene.sh`
  - push stage: `bash src/tools/check_quality_simple.sh`
- **PRs must pass**: workflow YAML validation, dependency sync check, type-stub contract check, ruff format + lint, mypy, suppression audit, ty, pyrefly, vulture, Skylos quality/secrets/SCA and `-a` audit, the blocking Skylos danger gate, pytest, shellcheck, markdownlint, plus the isolated runtime smoke probe.

### 8. Coding conventions (quick reference)

- `from __future__ import annotations` at top of every file
- Full type annotations: all parameters + return types. Use `| None`, `list[str]` (not `Optional`, `List`)
- Prefer explicit symbol imports when practical (e.g., `from check_models import foo`), especially in tests; avoid broad module imports when only a few symbols are used.
- `Final` for constants: `TIMEOUT: Final[float] = 5.0`
- `pathlib.Path` for all paths; convert to `str` only at library call boundaries
- `raise SystemExit(code)` instead of `sys.exit()` (better for type narrowing)
- Catch specific exceptions, not bare `except Exception`. Use `raise ... from e` for context
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`

### 9. Change workflow (single checklist)

1. `conda activate mlx-vlm`
2. `git checkout -b feature/your-change`
3. Edit `src/check_models.py` (and/or other files in `src/`)
4. Add/update tests in `src/tests/` for the change
5. If you added imports or updated package thresholds → update `src/pyproject.toml` or `src/check_models_data/dependency_policy.py`, then run `make deps-sync` to rebuild README dependencies
6. If you added/changed CLI flags → update the CLI reference table in `src/README.md` (§ Command Line Reference)
7. `make format` — apply Ruff formatting before the full quality gate
8. `make -C src lint-fix` — apply safe Ruff fixes when lint reports fixable issues
9. If manual correction would be slower, optionally preview Ruff's unsafe fixes
   with `cd src && ruff check --unsafe-fixes --diff check_models.py tests tools`.
   Apply them with `cd src && ruff check --fix --unsafe-fixes check_models.py tests tools`
   only after understanding every proposed semantic change. Critically inspect the
   resulting `git diff`, repair or revert questionable transformations, and run
   targeted tests. This is an escape hatch, not a routine extra workflow step or
   permission to accept unsafe fixes on the nod.
10. `make lint` — clear Ruff lint errors before running the full gate
11. `bash src/tools/run_commit_hygiene.sh` — verify local commit hygiene
12. `make quality` — run the full quality gate check, including the full pytest suite
13. If report formats changed → update `src/output/` fixtures intentionally; validation tests must not rewrite tracked `src/output/` assets just to prove a change
14. Update `CHANGELOG.md` under `[Unreleased]` for any maintainer-relevant change (features, fixes, refactors, tooling/docs workflow updates)
15. `git commit -m "feat: description"` and push

### 10. Agentic skills (`.agents/skills/`)

Skills provide structured, step-by-step workflows for recurring tasks. Read the
relevant `SKILL.md` **before** starting work of that kind.

| Skill | When to use | File |
| ----- | ----------- | ---- |
| `add-or-fix-type-checking` | Typing errors from mypy, ty, pyrefly, or `make quality` | `.agents/skills/add-or-fix-type-checking/SKILL.md` |
| `native-mlx-vlm-repro` | Isolate failures with native `python -m mlx_vlm.generate` / Python load→template→`stream_generate` outside the harness | `.agents/skills/native-mlx-vlm-repro/SKILL.md` |
| `upstream-mlx-vlm-issues` | Draft or improve maintainer-ready mlx-vlm GitHub issue Markdown from diagnostics or crash drafts (do not file unless asked) | `.agents/skills/upstream-mlx-vlm-issues/SKILL.md` |
| `hf-cache-mlx-vlm-models` | List or reason about HF cache models under default discovery: the mlx-vlm server-style layout filter plus the image-capability classification and architecture pre-check | `.agents/skills/hf-cache-mlx-vlm-models/SKILL.md` |
| `benchmarking-mlx-vlm` | Credible perf measurement: median-of-N with warmup, `mx.eval` before timers, peak-memory protocol, A/B across MLX versions | `.agents/skills/benchmarking-mlx-vlm/SKILL.md` |

Upstream mlx-vlm support skills (see Blaizzy/mlx-vlm#1343) are adapted here for
**conda + pip** only. Never document or run `uv run` in this repository. Prefer
existing `src/output/issues/`, `reports/diagnostics.md`, and
`get_cached_model_ids()` / `--dry-run` over inventing parallel tools. Upstream
also ships `server-inference`, `convert-quantize`, and `add-new-model` skills;
they target work inside an mlx-vlm checkout and are deliberately not adapted
here.

### 11. Common edit recipes

**Review workflow security or agent-generated changes:**

1. Run `make skylos-danger` for the advisory JSON/annotation-style scan
2. Run `make skylos-danger-llm` when you want the same findings with code context tuned for an AI/code-review agent
3. Run `make skylos-verify ARGS='--file path/to/file --range L1:L2'` for narrow post-edit AI-defect verification

**Add a CLI flag:**

1. Add `argparse` argument in `_build_cli_parser()` under `SECTION: MAIN ORCHESTRATION & ARGPARSE` in `src/check_models.py`
2. Wire it through `main()` → `process_image_with_model()` or relevant function
3. Add test in `src/tests/test_parameter_validation.py`
4. Update the CLI reference table in `src/README.md` (§ Command Line Reference)
5. Run `pytest src/tests/test_parameter_validation.py src/tests/test_cli_help_output.py -q`

**Change a quality threshold:**

1. Edit `src/check_models_data/quality_config.yaml` (preferred) or `QualityThresholds` dataclass in `SECTION: IMPORTS, CONFIG & OPTIONAL DEPENDENCY GUARDS`
2. Run `pytest src/tests/test_quality_analysis.py -q`

**Modify report output:**

1. Edit `generate_html_report` or `generate_markdown_gallery_report` under `SECTION: REPORT GENERATORS & RUNTIME FINGERPRINTS`
2. Update `src/output/` fixture files if test assertions reference them
3. Run `pytest src/tests/test_html_formatting.py src/tests/test_markdown_formatting.py -q`

**Add a new quality detector:**

1. Add `_detect_your_pattern(text: str) -> tuple[bool, str | None]` following existing patterns under `SECTION: METRICS, SCORING & FIELD FORMATTING`
2. Wire it into the quality analysis pipeline
3. Add thresholds to `src/check_models_data/quality_config.yaml` and `QualityThresholds`
4. Add test in `src/tests/test_quality_analysis.py`

### 12. What NOT to do

- **Don't split `check_models.py`** into multiple files — the monolith structure is intentional
- **Don't hardcode magic numbers** — use `quality_config.yaml` or dataclass fields
- **Don't suppress lints** (`# noqa`, `# type: ignore`) without a documented reason
- **Don't run `python` without conda** — always `conda activate mlx-vlm` first
- **Don't create ad-hoc test scripts** — add tests to existing `src/tests/test_*.py` files
- **Don't duplicate formatting logic** — extend `format_field_value` for new metrics
- **Don't over-extract helpers** — a single well-commented function is preferred over many tiny one-use helpers (see `docs/IMPLEMENTATION_GUIDE.md` § Philosophy)

### 13. Dependency Synchronization and Policy

This repository implements a strict dependency alignment and verification policy to ensure type safety and runtime compatibility across the MLX stack:

- **Dependency Policy Definitive Specs**: All package version floors and compatibility rules are declared in `src/check_models_data/dependency_policy.py`.
- **pyproject.toml Alignment**: When adding or updating third-party libraries, declare the dependency range in `src/pyproject.toml`.
- **Auto-Syncing README**: The CLI README documentation contains an auto-generated dependencies table block. After editing `pyproject.toml` or dependency policies, you must execute `make deps-sync` (which runs `python -m tools.update_readme_deps`) to rebuild the README alignment blocks.
- **CI Dependency Sync Check**: The CI pipeline runs `python -m tools.update_readme_deps --check` to verify that README markdown blocks match `pyproject.toml` exactly. Failures will block pull request approvals.
