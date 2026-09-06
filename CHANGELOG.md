# Changelog

Notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- The quality gate runs sequentially again: the background Skylos and
  pytest lanes, the quiet-tree guard (`tools/quiet_tree.py`), its
  iCloud-sync detection and their tests are gone. Overlapping the two long
  stages required the whole source tree to stay provably quiet, and the
  machinery that demanded grew past what a ~15 s saving justified. Kept:
  `tmp_path`-only test outputs, the temporary wheel-build copy, the
  eight-worker cap, and the per-process application caches.
- Pytest's bytecode and result caches live in the tree again: the conftest
  `sys.pycache_prefix` override and the gate's `PYTHONPYCACHEPREFIX` /
  `cache_dir` relocation existed only to keep the tree quiet under a
  concurrent Skylos scan, and splitting the result cache meant a shell
  `pytest --lf` after a gate failure did not see the gate's last-failed set.
  The Pyrefly wrapper keeps writing its throwaway config under `$TMPDIR`, and
  the wheel test keeps building from a copy, because those reasons survive
  (an aborted run must leave nothing behind; a stale `*.egg-info` changes
  package metadata). The project instructions now distinguish generated
  output, which never lands under `src/`, from ordinary gitignored tool
  caches, which may.
- The pre-durability `reports/assets/source-image.jpg` is left frozen rather
  than deleted: retained diagnostics and pasted issues may still reference
  it, and it is simply never overwritten again.
- The retained run summary was regenerated with the fixed generator so its
  opening paragraph no longer claims range checks.
- Review follow-ups since 0.17.0: the run summary's opening paragraph no
  longer claims the output was checked "within the ranges the prompt
  states" (0.17 stopped enforcing them) and defers to the selected
  assessment profile's stated scope; the gallery preview asset is now named
  by the digest of its bytes (`source-image-<sha256 prefix>.jpg`) and
  retained across sweeps, so a reproduction command pasted into an issue
  keeps verifying after the input photograph changes, and the report calls
  it a "retained preview" that resolves once the run's artifacts are
  committed; the incomplete-cache warning for explicit `--models` states
  what the layout check actually knows (the cached *main* revision is
  absent or incomplete), says the run *may* need to download for the
  revision it will load, and its pre-fetch advice honours `--revision`; the
  obsolete `cleanup_test_outputs` fixture that deleted `test_*` files under
  `src/output/` after every test is gone; and the quiet-tree guard moved to
  `tools/quiet_tree.py`, now checks the package root itself so a file
  created and deleted directly under `src/` is caught, and is unit-tested.
  One caveat found while proving it: iCloud Drive's Desktop & Documents sync
  rewrites directory modification times a moment after any change, so on a
  tree under `~/Documents` a directory-only finding (no surviving file
  change) is reported as a warning naming the sync rather than failing the
  run; file-level findings always fail. Every pytest run (not only the gate)
  now redirects bytecode out of the tree, which removes the last in-tree
  write that triggered those touches.
  A directory bump explained solely by an ignored tool cache appearing for
  the first time (`.skylos` on a fresh CI checkout, created by the
  concurrent Skylos lane) is not a finding; a bump with no surviving new
  entry — a create-then-delete transient — still is.
- Markdown key/value rows that hold a bare URL (the new published-preview
  row, and the public-source row) now render as autolinks: the escaper used
  to wrap the URL in angle brackets and then HTML-escape them, which left a
  bare URL for markdownlint (MD034) and could mangle underscores in the
  path. Regenerated artifacts are lint-clean again.
- An explicitly requested `--models` entry whose cached snapshot is
  incomplete (a config or index present, weights still downloading) is now
  announced up front, in the run and in `--dry-run`, with the layout reasons
  and a note that the missing files will be fetched from the Hub during the
  run, bounded by `--timeout`. Default discovery already skipped such repos;
  explicit selection bypasses that check and previously said nothing.
- Cache discovery now flags, rather than runs and crashes, two kinds of
  cached repo that cannot serve the image-description task: speculative
  draft models (recognised from the installed mlx-vlm's
  `DRAFTER_KIND_BY_MODEL_TYPE` table and drafter packages — 19 types today —
  a `dflash_config.projector_type` of `dspark`, or a DSpark/DFlash/EAGLE-3
  architecture name) and image-producing families whose upstream loader
  declares `is_image_generation_model` or `is_image_edit_model` (bonsai,
  ernie_image, flux2, ideogram4, mage_flow, z_image today). Both lists are
  parsed from mlx-vlm's source without importing it, like the existing
  `MODEL_REMAPPING` alias table, so they track upstream automatically; the
  skip reason names the evidence. Adapted from Nativ's draft-model discovery
  and capability manifest.
- The test suite no longer writes anywhere under `src/` while the gate's
  Skylos lane scans it, closing the last race between the two lanes: the
  four CLI tests that wrote to gitignored `src/output/test_*` directories
  now use `tmp_path`, the wheel-build test builds from a copy of the package
  so setuptools's `build/` and `*.egg-info` never land in the tree, and the
  Pyrefly wrapper writes its generated config and output under `$TMPDIR`
  (with project includes, excludes and search path anchored to the package
  root). `conftest.py` now fails the session if any path under the package
  changed during the run, so the guarantee is enforced rather than assumed.
- The quality gate runs its two long poles — the three Skylos scans and the
  pytest suite — as background lanes while the quick static checks stream in
  the foreground, then prints each lane whole in a fixed order, so the log
  reads as before and the wall time drops from about 44 s to roughly the
  longest lane. A failing foreground step kills the lanes; a failing lane is
  reported after both have printed. Fast (push-hook) mode uses the same
  lanes with its smaller test set. The lanes fork only after the
  tree-writing static checks finish, and the pytest lane keeps its bytecode
  and result cache under `$TMPDIR`, because Skylos's dead-code grep
  verification aborts with `SKY-ANALYSIS-INCOMPLETE` when files appear or
  vanish under it (seen on a 3-core CI runner, never locally).
- The test suite runs in about half the wall time (roughly 35 s to 17 s on
  an 18-core M5 Max) with no test removed: `CHECK_MODELS_SKIP_IMPORT_PROBE=1`
  (new, documented) lets the suite skip the subprocess import probes that
  cost every xdist worker ~2 s of start-up, component provenance is memoised
  per process instead of re-running `git rev-parse` and metadata lookups for
  every report surface (a conftest fixture clears it between tests), the
  upstream CLI-parity test reads mlx-vlm's parser in-process instead of
  spawning a second interpreter, and pytest is capped at eight workers
  (`-n auto --maxprocesses=8`) because per-worker start-up made 18 workers
  slower than 6.
- A dependency import probe that merely times out is now inconclusive — a
  warning is logged and the in-process import proceeds — instead of marking
  mlx-vlm unavailable. Under load (the parallel test suite, a busy machine)
  the probe expired while the import would have succeeded, which skipped the
  four end-to-end tests on every gate run and could mark a real sweep's
  dependency missing.
- Reproduction inputs now name the committed gallery preview as a shareable,
  digest-verifiable stand-in when the original photograph is unpublished: its
  raw GitHub URL, dimensions, size and SHA-256 plus a download-verify-run
  command, explicitly labelled as reproducing on the preview rather than on
  the exact inference input. Diagnostics, the HTML report and crash drafts
  all carry it.
- File digests and the report image preview are cached per (path, size,
  mtime) for the run, so the input photograph is hashed and re-encoded once
  rather than once per report surface.
- The resolved prompt configuration is logged as one line — lane, prompt
  source (built-in with or without hints, brief triage caption, or custom),
  assessment profile and effective max tokens — so a run's effective settings
  are visible without inferring them from lane defaults. The `--prompt`,
  `--assessment-profile` and `--rerun-triage` help texts now state exactly
  what each option overrides and what it leaves in place.
- Cruft pass: archived the thinking-budget evidence note (upstream #1819 closed
  as completed), removed a stale 98 MB session worktree and empty `.cursor`,
  `.worktrees` and `docs/superpowers` directories, trimmed `src/.gitignore` to
  the entries the root ignore file does not cover, and refreshed the README
  analysis sample, "clean completion" wording and test-suite size figures.
  Everything shipped since 0.15.0 (0.16.0–0.17.0) is now recorded under the
  `[0.17.0]` heading below.

## [0.17.0] - 2026-09-05

### Assessment profiles (0.17.0)

- Clarified lane, custom-prompt, assessment-profile, and token-budget precedence
  with an interaction table and explicit triage-rerun overrides in CLI help and
  the README. Startup now logs the resolved lane, prompt source/hint exposure,
  assessment profile, and token budget together; execution behaviour is unchanged.
- Added `--assessment-profile general|metadata`, independent of prompt wording
  and the evaluation lane. Built-in metadata prompts select metadata checks;
  custom prompts and triage select general checks. Explicit selection overrides
  the default; differential triage reruns remain general. The profile is retained
  in the JSONL header and each result assessment.
- Reports state the assessment scope and use "no concerns detected" rather than
  implying that an arbitrary task or factual-accuracy check passed. Metadata
  checks retain required fields, duplicate keywords, and neutral title/keyword
  counts. Duplicate keywords have their own `duplicate_keywords` observation.
- Removed prompt-contract recognition, prose range parsing, sentence counting,
  hint-overlap and instruction-echo heuristics, their obsolete tests/thresholds,
  and `--context-marker`. Short answers, copied hints and prefaces no longer
  cause automatic downgrades. Cap hits without stronger evidence remain neutral;
  absence of final punctuation is not proof of truncation.
- General checks retain crashes, empty output, repetition, control-token evidence,
  incomplete thinking and runtime facts. Complete answers and raw output remain
  available for human review. Older retained assessments remain readable and
  are labelled as having no recorded profile; report regeneration does not
  silently reclassify them. Comparisons with different assessment profiles are
  withheld rather than reported as model regressions.

### Added

- Tests for eight live functions no test had exercised (`_model_burden_rows`,
  `_diagnostics_environment_section`, `_write_environment_failure_diagnostics`,
  `filter_and_format_tags`, `pretty_print_exif`, `_decode_iptc_keywords`,
  `_append_markdown_section`, `_parse_processor_kwargs_arg`).
- Streaming repetition guard: generation now runs through a thin accumulator
  over upstream `stream_generate` (reproducing `generate()` semantics — joined
  chunk text, final-chunk metrics) that stops decoding once the output tail is
  four exact repeats of a substantial unit past a 200-token floor. An abort
  sets `finish_reason="repetition_abort"`, which flows into the runtime stop
  reason and a new `repetition_abort` observation ("stopped early:
  repeating"); aborted generations are excluded from cross-run throughput
  comparisons and history bands (see Fixed below). The token-cap observation
  no longer conflates degenerate loops with genuinely long answers.
- Failures inside a repository's `trust_remote_code` modules now attribute to
  a dedicated `model-repo-code` owner instead of the library whose message
  they resemble: a `transformers_modules` frame (the dynamic-module cache) is
  checked before the message-first attribution flow, so e.g. a repo's fast
  image processor importing a symbol transformers removed routes the issue to
  the model repository rather than to transformers or mlx-vlm.
- The run issue summary counts "Hit the token cap" and "Stopped early for
  repetition" in its header, and renders a "Constraint-failure breakdown"
  section aggregating fleet-wide catalogue-constraint failures (title-length,
  keyword-count with medians, duplicate keywords) — separating "the prompt is
  hard for everyone" from "individual models are sloppy" at a glance.

### Fixed

- The description sentence counter no longer raises on a terminator with
  nothing before it (`Description: ... The mill spans a river.` crashed
  inside successful-result construction) and no longer splits after an
  abbreviation followed by a number (`Built approx. 1750, ...` counted as
  three sentences): a boundary now needs a capital letter after the
  whitespace, more abbreviations are known, and the docstring states the
  residual over-count risk instead of claiming none. Both cases are
  regression-tested through the assessment path.
- History noise bands additionally match each model's effective generation
  settings (`generation_settings` is now recorded per model in
  `results.history.jsonl`), so a thinking-budget change that the run-level
  fingerprint cannot see — it keeps only settings common to the whole sweep
  — no longer blends two workloads into one band.
- The reasoning disclosure and omitted-character count now come from the
  spans the delimiter processing actually removed, not from re-finding the
  answer's first characters in the raw output; a model that drafts its final
  answer inside the thinking block previously had most of its trace
  mis-attributed to the answer.
- Baseline comparisons no longer treat runs on different hardware as
  like-for-like for performance: the chip (`system["GPU/Chip"]`) is now a
  comparison fact, so a differing chip withholds the tok/s ratio, throughput
  flags and peak-memory moves (quality transitions still show), a missing chip
  on either side is reported as an unverified fact, the baseline's hardware
  appears in the component rows, and the retained `comparison` block carries
  a `hardware` pair alongside `execution_mode`.
- The retained `results.jsonl` is now rewritten atomically (staged next to
  the target and renamed into place), so a failure during the final manifest
  reconciliation leaves the pre-report file intact instead of truncated, as
  the failure message already promised.
- `--isolate` works again: the parent wrote the child spec with keys such
  as `params.model_identifier` (a mechanical rename had rewritten the JSON
  key strings too) while the child still read `model_identifier`, so every
  isolated model failed with `KeyError` before inference. The spec writer
  and the child parser are now adjacent functions with a round-trip test
  that runs both for real; the existing isolation tests mock the subprocess
  and could not see the drift.
- The pre-push quality gate no longer misfires from a linked git worktree.
  Git exports `GIT_DIR` into hook processes; with `GIT_WORK_TREE` unset,
  git then treats the current directory as the work tree, so every
  `git diff` run from `src/` reported the whole repository as deleted and
  Skylos `SKY-L021` flagged every validation call as "removed" (it also
  scanned the excluded `src/output/` log). `run_quality_checks.sh` now
  unsets `GIT_DIR` so git rediscovers the repository normally; the
  short-lived `SKY-L021` ignore is gone and the upstream bug is reported.

- `update.sh` no longer skips rebuilding a local MLX checkout that has
  uncommitted or untracked changes: an unchanged HEAD with modified C++,
  Metal, or packaging inputs left an older compiled extension, metallib, or
  dylib in use under a provenance claiming the current source. The
  decision is a pure shell function with a behavioural test over the
  unchanged-clean, dirty, changed-HEAD, wrong-editable-origin, and
  FORCE_REINSTALL cases.
- The schema-3 `results.jsonl` header is rewritten last, after every
  report outcome is known: its `artifacts` manifest lists only artifacts
  this run produced (matching `index.md`, never a failed renderer's stale
  file), and its `total_runtime_seconds` / `timestamp` are end-to-end.
  The HTML runtime row, rendered before reports finish, is labelled
  "Model sweep runtime"; the console line is computed at exit.
- `validate_env`'s no-pyproject fallback tracks the declared runtime set
  again (it still required the retired `wcwidth` and omitted `numpy` and
  `rich`); a test now holds the two name sets equal. The implementation
  guide's runtime list matches `pyproject.toml`.
- `validate_env --fix` installs the pre-commit hooks once, interpreter-
  qualified, instead of a second time via whatever `pre-commit` is on PATH.
- `update.sh` no longer advertises or detects `uv`; `common_quality.sh`
  drops a no-op `quality_activate_conda` shim.
- The packaged-wheel test builds through standard PEP 517 isolation from
  the declared `[build-system]` instead of `--no-build-isolation`: it had
  only ever passed on CI because `huggingface-hub[torch]` dragged `torch`
  and, transitively, `setuptools` into the environment, and it broke the
  moment that unrelated extra was removed.
- Skylos no longer overwrites the user's clipboard from the quality gate:
  every Skylos invocation goes through `quality_run_skylos`, which puts a
  throwaway `pyperclip` stub (raising `PyperclipException`) first on
  `PYTHONPATH` so the grade renderer's unconditional badge copy takes its
  quiet no-clipboard branch. No Skylos pin or dependency change.
- Run timing is one wall-clock concept a skimmer can read: the overall
  runtime is now measured on the wall clock (it previously used a perf
  counter that stops during system sleep, so a sweep that slept mid-run
  reported 15 minutes for a 20-minute run), the schema-3 header retains
  the run's `started_at` (optional, so existing files load unchanged),
  `run_summary.md` opens with *Run started / Run finished / Run duration*,
  `index.md`'s dashboard leads with the duration, and long durations render
  as `15m 26s` / `1h 05m 12s` instead of `925.55s`. The retained-run window
  prefers `started_at`; older headers bound the start by the earliest
  retained result timestamp, which fixes the summary omitting the run's own
  `check_models.log` and `environment.log` as "stale" while `index.md`
  still linked them.
- Every scripted `npm install` (`update.sh`, `setup_conda_env.sh`, the
  Makefile's lazy tooling installs, and the CI static-quality job) passes
  `--no-audit --no-fund`: nothing consumes the audit or funding output, and
  a degraded npm advisory endpoint (registry ping 0.3 s, bulk-advisories
  POST timing out with zero bytes) left every `npm install` hanging in its
  final audit phase on multiple consecutive runs — on CI that would hold a
  runner until the job timeout.
- The repetition guard mirrors two upstream `generate()` behaviours added
  for diffusion_gemma (mlx-vlm #2101): the joined text passes through the
  processor's optional `clean_output` hook (stripping leaked
  `<|channel>` scaffolding that plain mlx-vlm users no longer see), and
  the verbose echo skips chunks upstream marks `text_already_printed`.
  Without the hook, stream-based results would report artifacts as
  maintainer observations that upstream's own path already removes.
- Every report surface now opens with one canonical scope statement
  (`_run_objective_statement`): the run probes exactly one narrow task —
  catalogue metadata for a single photograph (in the assisted lane, aided
  by camera capture context and draft hints from a more capable model) —
  and says nothing about fitness for other uses. Shared verbatim by
  run_summary.md, the model gallery, diagnostics.md, results.html, and
  index.md so the framing cannot drift between surfaces.
- `run_summary.md` now explains itself to a first-time reader: an opening
  paragraph states the narrow objective under test (catalogue metadata for
  one photograph, in the assisted lane aided by camera capture context and
  draft hints from a more capable model — not general model quality), the
  exact prompt is embedded collapsed at run level, and the at-a-glance
  section defines the usability vocabulary and the Total / Gen tok/s /
  Peak GB columns.
- Verbose sweeps stream generated text live again: the repetition guard now
  echoes each retained (non-draft) chunk to stdout as it arrives, restoring
  the ergonomics lost when guarded generation replaced upstream
  `generate(verbose=True)` (which echoed) with `stream_generate` (which does
  not). The echo runs inside the tee capture, so the live console and the
  retained upstream-output capture both keep the text; draft chunks are
  neither echoed nor retained, and non-verbose runs are unchanged.
- Observation `details` contents are validated at the loader against their
  declared shapes (string lists of strings, non-bool integer counts,
  exactly-two-int ranges, plain-string fragments; unknown keys stay
  permitted for forward compatibility), so a mistyped retained value like
  `"title_word_count": "five"` is rejected before a renderer compares it.
- The schema-3 loader also validates the nested structures reports index
  into (`assessment.details`, `prompt_diagnostics.generate_kwargs` must be
  mappings when present), and comparison rehydration is strictly typed: a
  JSON string where a boolean/enum/timestamp belongs raises into the
  degrade-to-no-baseline path instead of being truthiness-coerced (e.g.
  `"false"` no longer reads as `True` for `throughput_comparable`).
- Remaining `run.json` descriptions in the root README, feature lists, the
  monolith's architecture header, and internal docstrings now describe the
  schema-3 `results.jsonl` contract.
- Report, diagnostics, summary, and comparison rendering are contained at
  their orchestration boundaries: an unexpected exception in one renderer
  degrades that artifact (and logs it) instead of terminating finalisation,
  and a comparison render crash degrades the comparison to "none" rather
  than losing the remaining artifacts. `KeyboardInterrupt`/`SystemExit`
  still propagate.
- Navigation surfaces (`index.md`, the terminal artifact log) list only
  artifacts whose generation outcome succeeded this run; a stale file left
  on disk by an earlier sweep is never presented as current, and
  `environment.log` is reported from an explicit success signal instead of
  `Path.exists()`.
- The whole-run constraint-failure aggregate groups observations by their
  actual `(min, max)` bounds instead of assuming one fleet-wide range, so
  mixed-prompt retained artifacts aggregate correctly; medians stay
  fractional and below-range is separated from above-range.

- The upstream-parity tests no longer import `mlx_vlm` in the pytest
  interpreter: importing any submodule executes the package root, which
  initializes `mlx.core`'s native Metal backend and can abort the whole
  process (not raise) when Metal is unavailable — `pytest.importorskip`
  cannot catch a native abort. The GenerateKwargs parity test now reads the
  installed `types.py` as source (AST), and the CLI-defaults parity test
  captures upstream argparse defaults in a subprocess probe that skips
  cleanly when the child dies. Retiring the in-process capture also removes
  the suite's last `type: ignore` monkeypatch suppression.
- Review fixes on the repetition guard: the streaming wrapper now performs
  upstream `generate()`'s stopping-criteria setup (custom `--eos-tokens`
  register on the tokenizer, and reset to the model default otherwise, so a
  prior model's registration cannot leak) and skips speculative/diffusion
  draft chunks, whose text upstream excludes from the final answer.
  Repetition-aborted generations are excluded from cross-run throughput
  comparisons and history noise bands (a rate over a few hundred tokens is
  not comparable with a full-length run). The runtime API drift check now
  validates `stream_generate` — the call the harness actually makes — and
  the unused `generate` module symbol is removed. The constraint-failure
  aggregate validates retained `details` ranges before indexing (stale or
  malformed artifacts degrade instead of crashing summary regeneration),
  keeps fractional medians, and splits below-range from above-range counts.
- The e2e smoke tests' fixture model is now `LiquidAI/LFM2.5-VL-450M-MLX-bf16`
  (the smallest usable model in the standing suite); they previously targeted
  the retired `nanoLLaVA-1.5-4bit` and silently skipped their two
  real-inference cases once that cache entry was removed.
- Name-based parameter estimates use `Decimal` arithmetic:
  `int(float("4.1") * 1e9)` truncates to 4,099,999,999 because 4.1 is
  inexact in binary — the same defect mlx-lm fixed in its `_parse_size`
  (ml-explore/mlx-lm#1726).

- CodeQL can analyze the monolith again: GitHub's Python extractor
  (tsg-python) mis-slices the U+FE0F emoji variation selector while
  evaluating string literals in any file containing PEP 695 syntax, and when
  the same literal carries a %-format directive its error reporter crashes
  ("not enough arguments for format string"), silently dropping the whole
  file from security analysis — `src/check_models.py` had been unanalyzable
  since at least 2026-03 (when the first `type` alias landed). All `⚠️`
  glyphs in Python sources are now written with the selector escaped
  (`⚠\ufe0f`), which renders identically and keeps the source ASCII at
  that position; a source-hygiene test guards the invariant, and the root
  cause was bisected to a three-line reproducer with a local CodeQL CLI.

### Removed

- `_parameter_count_from_name` compatibility wrapper; callers and tests use
  `_parameter_counts_from_name` (total, active) directly.
- `mlx-lm` is gone from the project entirely: nothing imports it and
  mlx-vlm has not depended on it since 0.6.14, so the `extras` entry, the
  legacy mlx-vlm < 0.6.14 floor logic and its policy constants, the report
  version rows, the error-attribution and traceback markers, the mypy
  override, and the local-build/verify/clean stages in `update.sh`,
  `setup_conda_env.sh`, `probe_python_next.sh` and `clean_builds.sh` no
  longer mention it. A sibling `mlx-lm` checkout is simply ignored.
- Tooling cruft found in the maintainability review: `bugtest.py` and
  `update.sh`'s Metal-regression reminder (the M5 NAX matmul regression it
  probed for is long fixed, and the runtime smoke already catches a broken
  backend), the custom `install_precommit_hook.py` (the checked-in
  `.pre-commit-config.yaml` installs the same two hooks via
  `pre-commit install`, which `make dev`, `setup_conda_env.sh`, and
  `validate_env`'s auto-fix now run), the `update-env` / `update-full` /
  `check_models-demo` alias targets, and the never-filed workflow-hardening
  PR draft (archived). `make probe-python-next` is now listed with the
  other maintenance targets. All three type checkers (mypy, ty, pyrefly)
  stay in the gate.
- Dead code and rolled-our-own utilities found in a maintainability
  review: `ResultSet.get_fields` / `_get_available_fields` (never used by
  the harness), the `_version_components` fallback (PEP 440 parsing via
  `packaging` already sorts dev, rc, and local versions; an unparseable
  installed version now simply fails the floor check), and the optional
  `wcwidth` dependency — terminal display width now comes from
  `rich.cells.cell_len`, since `rich` is already a hard dependency.
- Unused dependency declarations: `pydantic` (no consumer anywhere in the
  tree), `types-tqdm` (no `tqdm`), and the `torch` extra on
  `huggingface-hub`, which pulled `torch` into the base install and
  silently defeated the opt-in `torch` group.
- The `run.json` artifact and its writer (`save_run_json_report`,
  `RunJsonReportRecord`, `--output-run-json`): the schema-3 `results.jsonl`
  metadata header now carries the complete run-level contract. A schema-2
  retained baseline is rejected by the single loader (no adapter), so the
  first `--compare-with` against an old sweep is skipped with a logged
  reason and the next schema-3 run establishes the new baseline.
- The seven per-artifact output flags (`--output-html`,
  `--output-gallery-markdown`, `--output-jsonl`, `--output-run-json`,
  `--output-log`, `--output-env`, `--output-diagnostics`), replaced by the
  single `--output-dir` root; retired flags are rejected with an actionable
  error.
- The retired `stress`/`quality` evaluation-mode aliases (now rejected at
  parsing), `--detailed-metrics`, and `--open-report`; verbose mode always
  renders the full detailed metrics tree, and the unreachable compact
  verbose renderer and legend branch are deleted.
- Dead definitions with no reference sites (`FLOAT_ZERO_EPSILON`,
  `ERROR_MESSAGE_TRUNCATE_LEN`, `BPE_BYTE_ARTIFACTS`, `_html_code_block`,
  and the test-only `_public_output_artifact_map`), plus a duplicate
  `--output-dir` parsing test already covered by the layout-derivation test.
- Reporting-archaeology tests asserting the absence of long-retired
  surfaces, replaced by one canonical retired-terms guard across every
  rendered artifact (test count 903 → 896 before the new schema-3 loader
  regressions).

- The mlx-vlm stub-generation subsystem is fully retired: mlx-vlm 0.6.16+
  ships a PEP 561 `py.typed` marker on PyPI (from our Blaizzy/mlx-vlm#1985),
  so every dependency in the typed surface now provides its own types.
  Deleted `src/tools/generate_stubs.py` with its patches/contracts/manifest
  handling, the `stubs`/`stubs-clear`/`clean-stubs` Make targets, the
  update.sh and quality-gate stub steps, the `../typings` search paths in
  mypy/ty/pyrefly/vulture configuration, and the stub contract tests. The
  mlx-vlm floor rises to 0.6.16 (first release shipping `py.typed`) so the
  guarantee holds by construction.

### Changed

- Format compliance is no longer confusable with accuracy on the influential
  surfaces: chooser, output-at-a-glance and run-summary tables head their
  axis "Format/structural usability", resource highlights and the
  run-summary/diagnostics sections say "passing mechanical checks" instead of
  "clean", and the chooser explanation states outright that a model can pass
  every check while copying hint keywords or misidentifying the subject.
  Machine codes (`usable`, `usable_with_caveats`, observation codes) are
  unchanged.
- The description part of the catalogue contract is now assessed, conservatively:
  a description with more sentences than the prompt's requested range is a
  `catalog_constraint_violation` with `description_sentence_count` and
  `description_sentence_range` evidence, surfaced in the per-model label,
  the constraint-failure breakdown and the details table. The sentence
  counter only splits on a terminator followed by whitespace and a capital
  or digit, ignores abbreviations, initials, dotted acronyms and decimals,
  and checks the upper bound only, so it can under-count but never invent a
  violation. The observation label reads "Title, description or keywords do
  not meet requested constraints".
- Performance comparability uses a fuller identity. Hardware identity is
  now chip plus GPU core count plus RAM, so the same chip with fewer cores
  or less memory withholds throughput. History noise bands are grouped by a
  comparison fingerprint (prompt, image digest, generation settings, lane,
  execution mode, hardware) that `results.history.jsonl` now records as
  `comparison_fingerprint`, and a model's samples must come from the
  revision under test (`resolved_revision` is now stored per model);
  older history rows without those facts fall back to the fixed ±15% band.
- Parameter estimates from model names distinguish active from total: an
  `A3B`-style token is an active-parameter designation, so
  `Kimi-VL-A3B` reports "Active parameter count: 3.00B (name-estimate; total
  not stated in the name)" instead of a 3B checkpoint, and `30B-A3B` names
  report "30.00B total, 3.00B active".
- Chooser and output-at-a-glance previews now show each model's final
  answer: a closed thinking trace (emitted or prompt-seeded, the same rule
  the assessment uses) is left out of the preview, reported as an
  omitted-character count in Markdown, and opened under a `<details>`
  disclosure in the HTML chooser. Thinking models such as ERNIE and
  Qwen3-VL-Thinking no longer spend their preview on scratch work.
- Every summary surface — run summary, output index, gallery, HTML report,
  and diagnostics — now leads with the evaluation lane and the input image
  (format, dimensions with megapixels, size), so a 66-megapixel input is
  visible before any per-model prefill timing. The run summary's
  "Evaluation mode" row became "Evaluation lane" within that block.
- Resource highlights rank by time to complete the task end-to-end instead
  of decode tok/s: the gallery and HTML "Fastest clean completion" and
  "Average clean-completion throughput" lines became "Quickest clean
  completion (end-to-end, including model load)" plus an explicit caveat
  that tok/s is not averaged across models; the terminal summary's
  "Fastest (tps)", "Average TPS", and "Memory efficiency: tokens/GB" lines
  are replaced by "Quickest completion". Per-model tok/s stays in the
  chooser.
- Project instructions and adapted skills no longer describe removed
  machinery: `run.json` references now point at the `results.jsonl`
  metadata header (and `issues/run_summary.md` as the skim surface), the
  native-repro Python shape loops over `stream_generate` the way the harness
  does instead of calling upstream `generate()`, `mlx-lm` is stated as not a
  dependency, and the generation seam, `--isolate` spec pairing, and atomic
  final rewrite are documented so future changes start from the real code.
- Suppression review: configuration-wide suppressions that suppressed
  nothing or hid real findings are gone. Ruff `S311` (no `random` use) and
  the `tests.*` mypy override are removed (markdownlint `MD041` stays off,
  now with a rationale naming the two deliberately H1-less files); the
  argument ceiling is enforced again (`PLR0913` and Skylos `SKY-C303` are
  no longer ignored globally — the four builders that exceed it carry
  individually justified suppressions); `ANN401` applies everywhere except
  argparse's keyword protocol, and `_open_image_for_exif` is typed as
  returning `Image.Image`; the blanket test `ARG001`/`PLR0915` exclusions
  are replaced by removing five dead parameters (including an unused
  `harness_type` on a test helper) and three targeted long-test
  suppressions; the `tools/**` `S603`/`S607`/`BLE001` exclusions are
  replaced by narrowed exception types in `validate_env`, a resolved
  shellcheck path, per-call rationales, and removal of a duplicate
  `pre-commit install` subprocess. `tools.check_suppressions` now states
  that it audits inline suppressions only.
- The test suite runs in parallel (`pytest -n auto`) from `make test`,
  `make test-cov`, and both gate invocations — pytest-xdist was already a
  dev dependency that nothing used; wall clock drops from ~61 s to ~34 s
  locally. A suite-wide `MLX_VLM_WIDTH` pin in `conftest.py` makes console
  rendering deterministic: under xdist a worker's stdout is a pipe, the
  width fallback was narrower, and two working-set assertions failed on
  truncated tree rows.
- `_run_model_isolated` takes the already-built `ProcessImageParams` from
  `_run_one_model` instead of re-threading the same eight keyword
  arguments through a third signature.
- Output-quality observation is a single canonical projection
  (`_quality_observations` + `_completed_assessment`) shared by the main
  harness and `tools/analyze_output_quality.py`, which now emits the same
  `assessment` block as the reports and exits non-zero only for unusable
  output. The legacy per-result quality-issue strings are deleted.
- `results.jsonl` is schema `3.0` and the sole current-run machine
  contract: the metadata header adds the prompt SHA-256, total runtime,
  outcome counts, artifact paths, producer identity, source-image facts,
  common generation settings, remote-code policy, and the embedded baseline
  comparison; per-model rows add their prompt-token burden. The single
  loader validates every required header field (including counts
  consistency against the loaded rows) and every consumed row field, and
  summary regeneration rehydrates the retained comparison.
- `--output-dir` is the only output-location control; the canonical layout
  (`index.md`, `results.jsonl`, logs at the root; HTML/gallery/diagnostics
  under `reports/`; conditional `issues/`) is derived from that root.

- Skylos quality findings now gate: `max_quality` drops from 10000 to 0 in
  both the package and root configurations, so "quality passed" means no
  quality warnings, not merely none blocking. The per-model comparison's
  throughput/memory accumulation moved into `_compare_model_performance`,
  bringing `compare_run_results` back under the configured complexity
  ceiling; the repository scan is clean at the zero budget. Version-drift
  noise remains absorbed by the per-rule ignore list, not a numeric
  allowance.
- `update.sh` skips a local MLX repo's rebuild when `git pull` brought no
  new commits **and** the installed package verifies as the editable from
  that checkout — the verification is the dependency-change guard, so a
  PyPI release that clobbered the editable, a rebuilt environment, or a
  missing install still forces the full rebuild, `FORCE_REINSTALL=1`
  still rebuilds unconditionally, and a skipped mlx build still applies
  its pin against PyPI releases.
- The `tokenizers` ceiling is widened to `<0.24.0` (from `<0.23.0`) in both
  `src/pyproject.toml` and the dependency policy: transformers 5.16.0
  requires `tokenizers>=0.23.1,<0.24.0`, so the old ceiling would have made
  transformers unresolvable past 5.15.1. This lifts the long-standing hold
  on the Dependabot tokenizers bump, which proposed exactly this range.
- The stale-index glob-fallback rescue is aligned with Nativ's merged fix for
  the same snapshot class (Blaizzy/nativ#370): the rescuing weight set must
  stand on its own — exactly one loose full-checkpoint file, or exactly the
  complete 1..N of one `model`-stem shard series. Mixed series, an adapter,
  or a stray loose file beside the series would be merged into the blind
  glob load and no longer rescue. One deliberate divergence remains: a
  malformed or empty index beside a self-standing weight set still rescues
  here, because mlx-vlm's Python loader swallows index errors and globs,
  while Nativ's pre-flight hides that case.

## [0.15.0] - 2026-08-26

### Added

- Nativ-informed discovery hardening (with review):
  - Snapshot resolution now mirrors the loader instead of picking the newest
    snapshot by mtime: an explicit `--revision` (commit hash, >=7-char prefix,
    or cached ref name) resolves to its own snapshot, otherwise the cached
    `main` ref wins, and only then does a recency fallback apply — labelled,
    and recorded as `revision_source` in `model_provenance`. A requested
    revision absent from the cache resolves to nothing rather than
    misreporting another snapshot, fixing baseline comparisons attributing
    changes to the wrong revision.
  - Sharded checkpoints are validated against their safetensors index: every
    referenced shard must exist inside the repo's cache directory as a
    non-empty regular file. Default discovery skips incomplete snapshots with
    `cache layout: N of M weight shards missing (e.g. …)`; explicit selection
    retains the attempt and records the fact as a snapshot note; a
    `model_load` failure on such a snapshot is classified indeterminate
    (environmental, like a download timeout) with a resume/re-fetch remedy.
  - Discovery and prompt diagnostics record whether a model's chat template
    declares thinking markers (`thinking_template` in `cache_discovery`,
    `template_thinking_markers` in prompt diagnostics; tri-state, `null` when
    no template exists) — the self-opening thinkers declare markers without
    pre-opening a block, which render-time checks cannot see.
  - Sentence-transformers layouts (`modules.json`, `1_Pooling/config.json`,
    `sentence_bert_config.json`) classify as embeddings during discovery even
    without an `mlx_embeddings` stamp.
  - Raw, source-labelled model-burden facts per result: checkpoint weight
    bytes (containment-checked sum of the snapshot's safetensors shards),
    parameter count with its source (the exact config key —
    `num_parameters`/`total_params`/`n_params` — or `name-estimate`),
    quantization bits/group size/mode, and declared
    context length with the config key it came from (including
    `text_config` nesting). Serialized as `model_burden` in
    `results.jsonl` (None-valued facts dropped, key omitted when the
    snapshot is unresolvable) and rendered as diagnostics rows, including
    a measured "Load active memory vs checkpoint" ratio built from the
    existing MLX load-time active-memory sample.
  Deliberately not adopted from Nativ: its fixed memory-headroom fit verdict
  and 20 %/6 GB activation-reserve heuristics — this harness measures actual
  MLX memory and reports facts, not a coarse fit estimate.


- Built-in run comparison (`--compare-with`, default `auto`): every sweep now
  diffs itself against a baseline — by default the retained `results.jsonl` at
  git `HEAD`, i.e. the last committed sweep — and reports a `comparison` block
  in `run.json`, a terminal summary, and a "Since the baseline sweep" section in
  `run_summary.md` whenever that summary is produced (it remains conditional on
  there being something to report, as before). It records per-model execution/usability/observation-set
  transitions, the count of byte-identical generated texts, generation tok/s
  ratios (median/min/max) with per-model noise bands derived from
  `results.history.jsonl` (Tukey fence over the last 10 same-prompt runs,
  excluding the run being judged; a fixed ±15% band when history is thin), and
  peak-memory moves beyond 0.5 GB and 10%. Models added/removed between runs
  are listed (collapsed to a count for targeted runs). `none` disables; a path
  or any git ref selects another baseline. Everything is model-agnostic and
  degrades to "no comparison" rather than failing a run.
- Isolated execution (`--isolate`): each model runs in a fresh child
  interpreter that hands its full `PerformanceResult` back as JSON (nested
  dataclasses and the upstream generation metrics round-trip exactly, so
  reports are identical to in-process runs). A child that dies natively —
  segfault, abort, interpreter-finalization fault — becomes that model's
  phase-tagged crash record (signal name, phase reached via a progress file,
  stderr tail) built through the same failure path as an in-process
  exception, instead of ending the sweep. Verified live with a forced
  `SIGABRT` in one child of a three-model run. The in-process boundary is
  unchanged and remains the default.
- Exact prompt token accounting: prompt diagnostics now record
  `rendered_prompt_token_count`, the tokenizer's count of the rendered chat
  template (mirroring upstream's `should_add_special_tokens`, duck-typed so
  every family takes the same path). Quality analysis and `run.json`
  `prompt_burden` use it as the text/template share — `text_tokens_source`
  says `tokenizer` or `heuristic` — so the non-text (image/audio expansion)
  share is exact for every model, and a new "Prompt composition" diagnostics
  row states it (e.g. Qwen3-VL-2B: 16,467 = 298 text + 16,169 non-text,
  98%). With an exact split, `visual_input` classification no longer depends
  on the placeholder regex recognising a family's image token. The word-ratio
  heuristic remains the fallback when a tokenizer cannot count.

### Changed

- Human-facing gallery and baseline-comparison status cells now use readable
  labels (`usable with caveats`, `title/keyword constraints failed`) while
  machine artifacts retain their stable underscore-delimited codes.

- `check_outdated.py` annotates local dev/editable builds in its outdated
  list — `mlx 0.32.2.dev… -> 0.32.2  (local dev build; PEP 440 ranks the
  final release above it)` — so the permanent ordering artefact reads as
  informational rather than as an upgrade prompt.

- mlx-vlm stub generation now retires itself: upstream ships a PEP 561
  `py.typed` marker since Blaizzy/mlx-vlm#1985 (the packaging half included),
  so `tools/generate_stubs.py` skips any package whose *installed* copy
  carries the marker and purges previously generated stubs, which would
  otherwise shadow the inline annotations. `update.sh` installs the mlx-lm
  and mlx-vlm editables in setuptools compat mode (a plain `.pth` path) so
  static checkers can traverse them — the `__editable__` finder hooks were
  the real blocker, not missing types. Verified: with no `typings/mlx_vlm`,
  mypy, pyrefly, and ty all pass and resolve `load`/`generate`/
  `GenerateKwargs` at full fidelity from upstream's own annotations. CI on
  PyPI mlx-vlm 0.6.15 (which predates the marker) keeps generating stubs
  unchanged and stands down automatically at the next release; the remaining
  stub machinery can be deleted outright once that happens.

- The baseline-comparison Markdown section and the terminal summary now render
  from one shared `_ComparisonView` derived once per comparison (identity and
  summary rows, banners, revision note, membership items, and the
  change/throughput/memory cells), so wording and withholding rules cannot
  drift between surfaces; a test asserts both surfaces show the same cells.
  `run.json` keeps its own raw-number serialization.

- CI now rehearses the next Python: the static-quality job runs a matrix of
  the floor (3.13) and 3.14, while the runtime-smoke and Skylos jobs move to
  3.14, and `Programming Language :: Python :: 3.14` is declared. The floor
  (`requires-python >= 3.13`, the checker targets, `validate_env`,
  `setup_conda_env.sh`) is unchanged — the working env stays on 3.13 until a
  deliberate rebuild — and `test_python_floor_is_single_sourced` now requires
  every CI Python to be >= the floor with the floor itself still exercised.
  Motivated by `make probe-python-next` on 3.14.7 passing every check with
  no friction: PyPI wheels (mlx 0.32.1, mlx-vlm 0.6.15, transformers 5.15.1,
  Metal available), the local mlx source build, the full test suite, mypy,
  pyrefly, ty, ruff, and the torch extra (2.13.0).

### Fixed

- The terminal model-comparison table reserves enough width for three-digit
  durations, preventing values such as `133.22` from folding their final digit
  onto a continuation row.

- Comparison observation deltas fall back to the raw code when a baseline
  carries an observation the current glossary does not know (older harness
  baselines must render, not crash), matching the existing fallback on the
  issue-summary surface.
- Weight-file selection is shared and loader-exact: a single helper returns
  the containment-checked files mlx-vlm's `load_model` would actually select
  (existing indexed shards first, the glob fallback minus
  `consolidated.safetensors` otherwise), and both shard validation and the
  burden facts consume it. Checkpoint weight bytes therefore no longer count
  adapters beside an indexed checkpoint, stale extra shard families, or
  consolidated files; and auxiliary safetensors (e.g. a LoRA
  `adapter_model.safetensors`) can no longer vouch for a full checkpoint
  when rescuing a broken or wholly stale index — only a full-checkpoint
  loose name (`model.safetensors`/`weights.safetensors`) or a complete
  `model`-stem family does.
- `_TeeCaptureStream.flush()` suppresses only the racing-close case (the
  stream reports closed after the `ValueError`); a genuine `ValueError`
  from an open sink propagates again instead of being hidden.
- `_TeeCaptureStream.flush()` tolerates an already-closed underlying stream:
  interpreter finalization closes the wrapper after the harness (or pytest's
  capture teardown) has closed the target, and the late flush raised
  `ValueError: I/O operation on closed file` into the unraisable hook,
  surfacing as `PytestUnraisableExceptionWarning` noise in test runs.
- Snapshot metadata readers now handle the real HF cache layout, where every
  snapshot file is a symlink into the repo's `blobs/` store: a shared
  containment-checked reader (`_resolve_snapshot_file` and its text/JSON
  wrappers, extracted from the capability classifier's existing pattern)
  follows the link but requires the target to stay inside the repo's cache
  directory. This fixes two real-cache failures the synthetic fixtures
  missed — shard validation failed closed on every ordinary sharded cache
  entry (the no-follow reader could not open the symlinked index, so
  discovery would have skipped all of them), and the burden collector
  dropped config-sourced facts (the cached Qwen/Qwen3-VL-2B-Instruct
  config declares `text_config.max_position_embeddings = 262144`, which
  now reports with its source key). The thinking-template scan and
  weight-byte sum read through the same helper, and the best-effort
  snapshot reader also absorbs invalid UTF-8 (`UnicodeDecodeError` is a
  `ValueError`, which only the JSON layer caught) instead of aborting
  discovery or result finalization on a corrupt cached file. Also fixed
  alongside: shard validation mirrors the mlx-vlm loader's index handling
  exactly — the loader keeps whichever indexed shards exist and falls
  back to globbing `*.safetensors` (excluding `consolidated.safetensors`)
  only when none exist or the index is malformed, so a wholly stale or
  broken index beside a complete weight set (a loose `model.safetensors`
  or a `model`-stem family with the exact 1..N part set, e.g. the cached
  re-sharded Apriel-1.5-15b-Thinker) validates as runnable, while a
  partial indexed subset or an unrelated-stem family never rescues; the
  name-based parameter estimate takes the largest size token so MoE
  names ("30B-A3B") report total rather than activated parameters; and
  the burden collector retries once with a refreshed cache scan so
  models cold-downloaded during the run are not invisible to the run's
  earlier cache snapshot.
- Review fixes on the discovery hardening: the offline-retry path accepts a
  resolver-verified requested revision (branch/tag names could never equal
  the snapshot's hash-named directory, so the legacy equality check rejected
  every resolved ref); the incomplete-cache classifier inspects the snapshot
  the run actually requested; an existing-but-invalid safetensors index
  fails closed (`index_error`) across discovery, snapshot notes, and the
  indeterminate classification; and the shard skip reason no longer
  duplicates the `cache layout:` prefix.

- `update.sh` can no longer lose the local mlx build to a PyPI release: the
  moment upstream published mlx 0.32.2, the eager-upgrade installs of
  mlx-lm/mlx-vlm replaced the editable `0.32.2.dev…` build with the wheel
  (PEP 440 ranks a final release above any `.devN` of the same version), the
  Stage 4b verification failure was non-fatal, and the script then removed
  `mlx-metal` on the false premise that mlx was still local. After a
  successful local mlx build its exact version is now pinned as a *private*
  `--constraint` argument injected by the pip wrappers — caller-supplied
  `PIP_CONSTRAINT` passes through untouched, and the temp file is removed by
  an `EXIT` trap. Local-source preservation outranks `FORCE_REINSTALL`: once
  the pin is active the flag is suppressed (and logged) instead of producing
  `ResolutionImpossible` against a dev version PyPI cannot supply. Repo
  detection is separated from the mutating updater, which now runs as an
  ordinary command so `set -e` makes any failure — including editable
  verification — abort the run instead of degrading into a half-local
  environment; `mlx-metal` removal is guarded on mlx actually being an
  editable/dev install. A local build whose version cannot be read is fatal
  rather than continuing unpinned (the unprotected state was the original
  bug), and the two eager wrappers share one argument-construction helper.
  Fake-pip regression tests cover the normal, forced, pinned, forced+pinned,
  caller-constraint, cleanup, and unpinnable-fatal cases. The `pip show`
  helpers no longer early-exit awk over a pipe: the old
  `pip show | awk '{…; exit}'` form raced SIGPIPE, harmless while the
  updater body ran with `set -e` suspended, but fatal-and-silent once it ran
  as an ordinary command — the script died with no output right after
  "mlx installed successfully". The shared `pip_show_field` now lets awk
  read all input (fields are unique, so at most one line prints) with
  `|| true` absorbing pip's status for absent packages; no suppression
  machinery needed. A chatty-pip harness test pins the behaviour under
  `set -euo pipefail`.


- Comparability is now three-state (`comparable` / `unknown` / `incomparable`):
  facts that cannot be verified (a baseline without `run.json`, missing image
  sha or settings) are named as `unverified_facts` and mark the comparison
  `unknown` instead of silently counting as comparable. Quality transitions
  stay visible under `unknown`; throughput and memory comparisons are
  withheld. Throughput is also withheld whenever the execution modes differ
  (isolated vs in-process — cold per-process caches make tok/s a different
  population); `run.json` records `comparability`, `throughput_comparable`,
  and both execution modes on every path, and the terminal warns.
- The heuristic fallback is bound by the same `0 <= text <= total` invariant
  as the exact count: when both are impossible the split is reported
  unavailable (the rejected exact count stays recorded), instead of
  publishing e.g. `5 = 130 text + 0 non-text`. The "Prompt composition"
  diagnostics row still surfaces the rejected count in that case
  ("unavailable; tokenizer count 7 rejected as inconsistent with total 5…").
- Download-timeout classification recognises the `TimeoutError` family by
  suffix (so `IsolatedWorkerTimeoutError` from a worker deadline counts) and
  the retained `stop_reason == "timeout"`, and the HF progress needles now
  include the per-file tqdm rate suffix (`…MB/s]`) so a cold download that
  outlives an isolated worker's deadline stays an environmental,
  indeterminate outcome rather than an actionable crash.
- Comparisons are like-for-like or withheld: the baseline's `run.json` is read
  from the same source as its `results.jsonl` (sibling file, or the same git
  ref), and the prompt, image sha256, evaluation lane, and shared generation
  settings are checked before any per-model diff. A mismatch marks the
  comparison "not directly comparable", lists the reasons, and suppresses the
  transition/text/throughput/memory tables in `run_summary.md` and `run.json`
  (`comparable: false`), so a prompt or image change can never read as a
  model regression. Per-model resolved-revision changes are reported alongside
  the diff. Facts missing on either side count as unknown, not as a mismatch.
- `--isolate` children are now bounded by the parent: `subprocess.run` gets a
  deadline of the model timeout plus 120 s start-up/cleanup grace; on expiry
  the child is terminated and the model is recorded as an
  `IsolatedWorkerTimeoutError` (a `TimeoutError`) tagged with the phase the
  child had reached. Previously a child stuck in import, setup, a deadlock, or
  finalization could stall the sweep indefinitely.
- `--rerun-triage` now runs its differential reruns through the same
  execution boundary as the first pass (`_run_one_model`), so `--isolate
  --rerun-triage` no longer loses the sweep when reproducing a crash
  in-process; the worker accepts the rerun's prompt/max_tokens/temperature/
  timeout overrides.
- History throughput bands only use rows whose recorded `prompt_hash` matches
  the current prompt (legacy hashless rows are excluded rather than treated as
  matching everything), and the current run's row is excluded only after a
  confirmed append — `append_history_record` returns `None` when the write
  failed and the comparison no longer blindly drops the last retained row.
- Exact prompt token counts must satisfy `0 <= text <= total`; a count outside
  that range is kept as diagnostic evidence (`prompt_tokens_text_exact_rejected`,
  and named in the "Prompt composition" row) while the split and burden
  classification fall back to the heuristic, so impossible evidence such as
  `5 = 7 text + 0 non-text` is never published.
- The isolation serializer now captures attributes check_models attaches to
  the upstream generation object dynamically (`active_memory`,
  `cache_memory`, `model_load_active_memory`), not only declared dataclass
  fields, so the terminal memory tree after an isolated run matches an
  in-process one. The round-trip test uses an upstream-like dataclass without
  those fields declared.
- `_count_rendered_prompt_tokens` only consults `mlx_vlm.utils` when a model
  type is known, which also keeps its unit test free of any Metal/mlx
  initialisation.
- `--isolate` workers no longer run the module-level subprocess import probes
  (the 8 s `import mlx_vlm` guard that protects the long-lived parent); a
  child is already the crash boundary, and the probe timing out once under
  transient load had marked one model's mlx-vlm as "unavailable" in a 42-model
  isolated sweep.
- Comparison throughput bands now have a floor of ±10% of the history median:
  a handful of near-identical samples produced Tukey fences a couple of percent
  wide, which flagged ordinary run-to-run variance (27 of 41 models in one
  sweep). The JSONL metadata now records `execution_mode` (`in_process` /
  `isolated`) and the comparison caveats throughput when the current and
  baseline modes differ.
- `_is_generation_processor` is a `TypeIs` (PEP 742) rather than a
  `TypeGuard`: with `TypeGuard` the positive branch replaced the declared
  `ProcessorMixin` with the guarded union, so after the `if`/`else` rejoin
  pyright widened `processor` to `ProcessorLike | PreTrainedTokenizer |
  ProcessorMixin` and reported the later `_prepare_generation_prompt` /
  `_build_prompt_diagnostics` calls as argument-type errors (visible in
  Pylance; mypy, pyrefly and ty accepted it). `TypeIs` intersects, so the
  variable is a `ProcessorMixin` again after the rejoin. Pyright: 0 errors.

- The CLI parser now pins `prog` to `basename(sys.argv[0])` (the Python 3.13
  default) instead of relying on argparse's heuristic. Python 3.14 derives
  `prog` from the `-m` invocation, and the exact rule differs between point
  releases — under a patched `sys.argv` 3.14.6 renders
  `usage: python3 -m pytest …` while 3.14.7 does not — which the new CI
  matrix caught on its first run (3.14.6 on the runner vs 3.14.7 in the local
  probe env). The usage line is now interpreter-independent.

## [0.14.1] - 2026-08-23

### Removed

- Retired migration cruft: placeholder quality tools under
  `src/tools/.archived`, their Ruff exclusions, the completed MLX-integration
  prompt, obsolete `.ci_*` cache cleanup, and automatic deletion of report
  copies from the pre-`output/reports/` layout.

- The `atexit` `mx.clear_streams()` exit hook in `main_cli()` and the
  `update.sh` smoke bootstrap. Both were workarounds for the mlx
  `#4248..#4373` dev-build window in which the runtime dropped its own
  compile-cache teardown; mlx `1038679aa` (ml-explore/mlx#4373) restores it
  and mlx-vlm 0.6.15 registers `clear_streams` itself (#1949). Verified on
  `1038679aa`: a real `generate()` followed by interpreter exit, with mlx-vlm's
  own hook unregistered and no bootstrap, exits 0. No released mlx was ever
  affected (0.32.1 predates #4248; the next release carries #4373), so no
  supported configuration needs the workaround.

### Changed

- Recorded that upstream closed the exit-crash gap from both sides: mlx
  `1038679aa` (ml-explore/mlx#4373) re-registers an `atexit` compile-cache
  cleanup on the main thread, and mlx-vlm 0.6.15 registers `clear_streams`
  itself (#1949). Verified a compile-then-exit and a compiled decode-style
  loop both exit 0 on mlx `1038679aa` with no manual cleanup (see
  "Removed" above for the consequence).

## [0.14.0] - 2026-08-22

### Changed

- Native repro commands now emit `--top-p`, `--min-p`, and `--top-k` as
  first-class `mlx_vlm.generate` CLI flags (upstream added them in
  Blaizzy/mlx-vlm#1994; previously they could only travel in the
  `--gen-kwargs` JSON blob, which is now reserved for `logit_bias`). The
  flags are emitted only when non-default, so repro commands remain valid on
  releases predating #1994 unless the run actually used the setting — the
  same policy as the per-tensor KV flags. Verified against the installed
  upstream CLI (`18e9b979`), which also landed the suggested
  `math.prod` fix for the `grid_sample` Metal launch grid (#2006), so the
  local mlx-vlm checkout patch is retired.

- Raised the `mlx` floor to `>=0.32.1`: the 0.32.0 wheels shipped `py.typed`
  without the `mlx/core/*.pyi` stubs (ml-explore/mlx#3916), so 0.32.1 is the
  first release whose wheel guarantees the upstream-shipped typing the gate
  now relies on. The transformers (>=5.14.0), tokenizers (>=0.22.0), and
  mlx-lm (>=0.31.3) floors already sit far above the versions that introduced
  their shipped types; the typing guarantees are now documented alongside the
  floors in `dependency_policy.py`.

### Removed

- `mlx_lm` from local type-stub generation (now `mlx_vlm` only). The monolith
  never imports `mlx_lm` — its sole reference is a failure-attribution string
  needle — mlx-lm ships `py.typed`, and CI never had the stubs anyway (PyPI
  mlx-vlm 0.6.14 does not install mlx-lm, so its stub generation was always
  skipped there). mypy, pyrefly, and ty verified clean without them.

## [0.13.0] - 2026-08-20

### Removed

- Local type-stub generation for `transformers` and `tokenizers`.
  `transformers` ships `py.typed` with inline annotations and `tokenizers`
  ships its own `.pyi` files, and mypy, pyrefly, and ty all pass against them
  directly. A `reveal_type` probe of every transformers touchpoint the
  monolith uses showed no load-bearing inference change (the two attributes
  that degrade to `Any` — `ProcessorMixin.tokenizer` and
  `PreTrainedTokenizer.encode` — are only accessed via `getattr` +
  `cast`/TypeGuard, or not at all). This removes the transformers stubgen
  run (~10 of the ~13 minutes of CI's Static Quality job) and all of the
  patch-and-audit machinery that existed solely to repair its broken output
  (`glue.pyi`/`squad.pyi` syntax fixes, the `ProcessorMixin` runtime-attribute
  patch and its contract check, stubgen noise suppression). Stub generation
  now covers `mlx_lm` and `mlx_vlm` only — the packages that genuinely lack
  shipped types.


- The CI "Generate MLX stubs for mypy" step and the `nanobind` dev dependency.
  The step had been a silent no-op (it looked for `mlx/core.pyi` while every
  nanobind version writes `core/__init__.pyi`), and had it worked it would
  have broken the gate: recursive `nanobind.stubgen -m mlx.core -r` emits
  submodule stubs without imports (392 mypy errors, identical on 2.14 and
  2.15). Both the PyPI wheel and an editable build ship correct
  `mlx/core/*.pyi` generated by mlx's own `nanobind_add_stub`, which is what
  the type checkers were already using. `probe_python_next.sh` no longer
  installs nanobind either (mlx's CMake fetches its own). A test now guards
  against reintroducing it.

### Fixed

- `tools/generate_stubs.py` now treats packages whose distribution is not
  installed as optional: they are skipped up front (logged), and generation
  still patches, syntax-validates and records the manifest for the installed
  subset instead of returning early. This unblocks CI on PyPI mlx-vlm 0.6.14,
  which no longer depends on mlx-lm — the previous early return left
  transformers' known-broken `glue.pyi`/`squad.pyi`/`processing_utils.pyi`
  unpatched and the stub contract check failed.
- Clean process exit on current mlx `main`: since mlx `8e00a2d9d` (#4248) the
  runtime no longer tears down its streams/compile cache at exit, and the
  maintainers' position (ml-explore/mlx#4327) is that the embedding process
  must call `mx.clear_streams()` on every thread that used MLX. `main_cli()`
  now registers an idempotent `atexit` hook (`_mlx_shutdown_cleanup`:
  `mx.synchronize()` then `mx.clear_streams()`, best-effort) so a run that
  generated with any model exits 0 instead of aborting with
  `PyThreadState_Get` (exit 134) after all reports were written. The
  `update.sh` local-MLX smoke runs the upstream `mlx_vlm generate` CLI through
  a bootstrap that registers the same hook, since the upstream CLI does no
  teardown of its own. The local mlx checkout is no longer pinned to
  `d9e2b0d40`. (Upstream mlx-vlm registers the same cleanup from 0.6.15,
  Blaizzy/mlx-vlm#1949; ours stays for released 0.6.14 wheels.)

### Changed

- Documentation housekeeping: archived the two superseded 2026-08-09 thinking
  issue drafts (both replaced by the posted upstream issue #1819 and the
  current evidence file), and the completed pip-metadata-quarantine plan/spec
  and the fully implemented mlx-vlm upstream alignment design spec (now under
  `docs/notes/archive/superpowers/`; the empty `docs/superpowers/` tree is
  removed, matching the notes README's stated convention). The notes README
  index no longer lists archived files as active and now describes the
  lifecycle of upstream issue drafts. The emitted-start thinking-budget
  evidence file is updated with the 2026-08-17 `625f71fa` re-verification
  (budget now fires but the model resumes reasoning past the forced close;
  Idefics3 leak fixed upstream in #1936; Kimi-VL leak traced to
  `generation_config.json` overriding `config.json` EOS ids).

## [0.12.0] - 2026-08-16

### Added

- Legacy snapshot notes are now recorded as structured, neutral per-model
  evidence instead of a debug log line. The preflight file-layout check
  (missing tokenizer artifacts, missing `preprocessor_config.json` /
  `processor_config.json`) returns its findings, which are stored on
  `PromptDiagnostics.snapshot_notes`, serialised into `results.jsonl` under
  `prompt_diagnostics.snapshot_notes`, and shown as a "Snapshot notes
  (neutral)" row in each model's diagnostics facts. They are evidence only:
  never an observation and never affecting usability (many community repos
  rely on legacy layouts that run correctly). Previously the note reached
  `results.jsonl` only incidentally, as log text embedded verbatim in
  `captured_upstream_output`, and was absent from every other artefact —
  so tracing a later failure on a newer mlx-vlm back to a snapshot that
  always lacked the artifact required grepping run logs.

- Human-facing reports now surface each editable/git-installed component's
  exact source revision beside its version — `run_summary.md` "Run context"
  and the diagnostics "Components and system" table gain e.g.
  `mlx-vlm source revision: 0558cbee…` (and likewise for an editable `mlx`).
  The value was already recorded machine-readably in `run.json` and the JSONL
  header under `component_provenance.<name>.source_revision`; it just was not
  visible where a reader compares runs. A version string such as 0.6.14 spans
  many upstream commits, including numerics changes (e.g. the RoPE-scaling
  correction in mlx-vlm #1927), so the revision is what pins a run's model
  behaviour and explains cross-run deltas that are not due to the image,
  prompt, or harness. Installed (non-git) packages gain no row.

### Changed

- Tighten the ruff quality ceilings to measured maxima so they guard against
  regression instead of sitting far above real usage: `max-complexity`
  75 → 15 (the previous ceiling was ~4× the most complex function) and
  `max-statements` 60 → 50. The one production function over both new
  limits, the report orchestrator `_generate_reports_and_log_outputs`, is
  split along its two natural seams (`_run_diagnostics_artifact` and
  `_log_report_generation_outcomes`) and now sits exactly at the ceiling.
  Long scenario tests are exempt from the statement count (they read better
  whole than fragmented). Argument ceilings are unchanged: they reflect the
  keyword-only, typed report-builder signatures, and folding those into
  parameter objects would add code without removing complexity.
- Evaluated enabling the preview rule `RUF069` (float-equality-comparison)
  and deliberately did not: individual preview rules require global
  `preview = true`, which silently changes the behaviour of *stable* rules
  (S603/S106 stop firing on this codebase, breaking the suppression audit).
  The monolith already has zero exact float comparisons — the 47 hits are
  all correct round-trip assertions in tests — so the rule would guard
  against nothing today at the cost of altering the whole ruleset. The
  decision and its reason are recorded in `pyproject.toml`; revisit when
  the rule stabilises.

## [0.11.0] - 2026-08-16

### Added


- mlx-vlm coverage matrix (upstream alignment design §6): an authoritative
  table in `src/README.md` recording which upstream surfaces this project
  exercises (direct load / image / chat-template / generate APIs, sampling,
  thinking, KV-cache controls, harness-side measurement), deliberately leaves
  unexercised (multi-image/audio/video, speculative decoding, prompt/vision
  cache reuse, image generation), treats as server-only (protocol routes,
  batching, APC, embeddings/reranking, structured outputs), or regards as
  separate workflows (conversion, fine-tuning, distributed). It records why
  mlx-vlm PR #1713's APC prefix-reuse fix cannot affect direct, isolated,
  cold-start benchmark runs. `docs/IMPLEMENTATION_GUIDE.md` points at it.
- Capability-aware default discovery (upstream alignment design §1–3). Cache
  discovery now has two independent layers: the existing mlx-vlm server-style
  cache-layout filter, plus a tri-state image-capability classification
  (`ImageCapability(verdict, purpose, evidence)`) read from bounded snapshot
  metadata (`config.json`, `model_index.json`). `yes` (positive image-input
  evidence such as `vision_config`/`image_token_id`) and `unknown`
  (insufficient evidence — still selected, with a warning naming the
  evidence) both run; only confident `no` is skipped, with a specific reason
  per model kind: text-only generation (mirrors upstream
  `_is_text_only_config`), embedding (`mlx_embeddings.kind`),
  sequence-classifier reranker, speculative drafter
  (`speculators_model_type`), image/video generation pipeline
  (`model_index.json` / pipeline config keys), or audio-only generation.
  Every skipped repo is named with `cache layout: …` and/or
  `model purpose: …` reasons in console and `--dry-run` output; explicit
  `--models` overrides the capability filter but logs the classification;
  and `run.json` retains a `cache_discovery` record (verdict, purpose,
  evidence, decision) for every cached repo so an intentional non-test is
  distinguishable from a crash. Validated against the full local cache: all
  41 real VLMs classify `yes` with zero false negatives. `id2label` alone is
  deliberately not a reranker signal (real VLM configs carry it). Docs, the
  `hf-cache-mlx-vlm-models` skill, and copilot instructions stop describing
  the layout filter as VLM proof.
- `make probe-python-next` / `tools/probe_python_next.sh`: check whether a
  newer Python (default 3.14, `PROBE_PYTHON=3.15` for later) is viable for the
  MLX stack in a throwaway, minor-pinned conda env (`mlx-vlm-314`) that never
  touches the working `mlx-vlm` env. It verifies the PyPI stack installs and
  imports (including Metal availability), runs the fast pytest lane against
  it, and with `PROBE_SOURCE_BUILD=1` compiles the local mlx source tree — the
  signal PyPI wheels cannot provide and the thing that would actually break
  `tools/update.sh` after a switch. The working env stays on the tested 3.13
  baseline until that probe is green.
- Begin implementing the accepted mlx-vlm upstream alignment design
  (docs/superpowers/specs/2026-08-14-mlx-vlm-upstream-alignment-design.md):
  raise runtime floors to the released mlx-vlm 0.6.13 stack (`mlx>=0.32.0`,
  `mlx-vlm>=0.6.13`, `transformers>=5.14.0`; mlx-lm keeps its own 5.7.0
  Transformers floor as a separate upstream fact), remove the last `tabulate`
  references from the validation fallback and docs, and record concise psutil
  available-memory and swap-use context facts in the system evidence when
  psutil is present. Capability-aware discovery and the coverage matrix
  remain to follow.
- Make the upstream thinking-budget issue draft maintainer-ready: regenerable
  test image script, pinned model revisions, and observed side-by-side native
  output showing Qwen3-VL-2B-Thinking force-closed at a 20-token budget while
  GLM-4.1V-9B-Thinking ignores the same flag.

- Automatic thinking budget (`--auto-thinking-budget`, default on): when no
  explicit thinking flags and no `--thinking-mode` are given and a model's
  chat template leaves a thinking block open (final start marker unmatched,
  mirroring mlx-vlm's server-side open-block logic — closed blocks and
  literal marker mentions are ignored), the run passes upstream's
  `thinking_budget` / `enable_thinking` generate kwargs with budget =
  max-tokens − 200 (skipped when that leaves under 128). Upstream then
  force-closes the thinking block at the budget so the model must produce
  the requested fields instead of truncating mid-reasoning at the token cap.
  Chat-template kwargs are never altered, so hybrid models keep their
  default non-thinking behaviour. The effective per-model budget is
  recorded in prompt diagnostics, shown in the diagnostics report, and
  overlaid onto native repro commands so issue drafts reproduce the
  recorded output. Disable with `--no-auto-thinking-budget`.
- Per-model system-pressure telemetry (darwin only, read-only `pmset -g` /
  `sysctl -n` probes, sudo-free; no macOS settings are modified). Default:
  one snapshot probe pair per model (before load and after cleanup, outside
  timed inference) so performance comparability is unaffected;
  `--system-telemetry` opts into continuous 2s background sampling and
  `--no-system-telemetry` disables telemetry entirely. Aggregates (min CPU
  speed limit, throttled samples, max memory-pressure level) are stored per
  model in `results.jsonl` as `system_telemetry` with separate per-probe
  sample counts, surfaced in the diagnostics provenance block (unavailable
  probes are reported as unavailable, never as clean), and logged as a
  warning when a run was throttled or under memory pressure.

### Fixed

- `--image` given a URL now fails immediately with guidance instead of a
  mangled-path ENOENT: argparse wraps the value in a `Path`, so a URL used to
  surface only as "No such file: .../src/https:/github.com/...". The error
  states that `--image` expects a local file path, points at the `/raw/`
  form for GitHub links, and mentions `--image-source-url` for recording
  provenance so issue drafts get a complete reproduction command. A
  single-letter drive spec such as `C:/` is never mistaken for a scheme.
- A per-model timeout that expires while a checkpoint is still downloading
  is now classified `indeterminate` (not evaluated, no maintainer action)
  rather than a `crashed` / `actionable_failure` with a maintainer-facing
  issue draft: the model was never loaded, let alone run, so it is a local
  environment condition, not an mlx-vlm or model defect. Detected from the
  recorded facts (load phase, `TimeoutError`, Hugging Face Hub download
  progress in the captured output); a hung *inference* timeout and a load
  timeout on a cached model remain crashes. Because the outcome is still
  user-actionable, every surface — console summary, diagnostics summary line
  and facts, and the run-summary review table — states the root cause and
  the remedy explicitly: re-run (Hub resumes partial downloads), pre-fetch
  with `hf download <model>`, or raise `--timeout` for the cold run.

- Thinking delimiters are protected from the generic special-token strip for
  every recognised `THINKING_TRACE_DELIMITER_PAIRS` marker plus any custom
  configured pair, at the `analyze_generation_text` layer. The previous fix
  protected only markers present in generation kwargs, so when a tokenizer
  declares `<think>`/`</think>` as special tokens and no thinking budget or
  flags are configured, the delimiters were still stripped and a completed
  trace read as preamble (reproduced through the production analysis path;
  now regression-tested).
- Image-capability classification requires meaningful evidence: image-input
  keys count only when they carry real values (`"vision_config": null` and
  FastVLM's `"image_grid_pinpoints": null` are not evidence), and a positive
  `yes` also requires a text-generating architecture. Image evidence without
  one is `unknown` (still run, with the reason), while known image-consuming
  non-generative architectures (classification, detection, segmentation,
  multimodal embedding such as CLIP/SigLIP) are a confident `no` with the new
  `image_understanding_non_generative` purpose. Re-validated on the full
  local cache: all 41 real VLMs remain `yes`.
- The upstream `mlx-lm` requirement is version-sensitive: mlx-vlm required
  mlx-lm only through the 0.6.13 release (0.6.14 / `738e4406` vendored the
  ported models), so the documented minimal install on a current mlx-vlm no
  longer reports a false "mlx-lm is missing; mlx-vlm expects mlx-lm>=0.31.3"
  warning, while a genuine 0.6.13 install still does.
- System telemetry is best-effort end to end: start and finish are guarded
  so a sampler, thread, or probe error is logged and telemetry is simply
  absent — it can never become a model failure or escape the isolation
  boundary from the per-model `finally`.
- Generation-processor resolution now happens under the `processor_load`
  phase before the prompt render, so a missing generation-compatible
  tokenizer is attributed to processor preparation rather than `prefill`.
- Cache eligibility (layout + capability + arch pre-check) is memoised per
  cache scan and keyed on the scan's identity, removing repeated per-model
  config.json reads and O(n²) reporting work.
- Docs: the coverage matrix no longer claims models run in isolated
  processes (they run sequentially in one interpreter with per-model
  exception isolation and cleanup), no longer names a non-existent
  `mlx_vlm.video_generate` command, and distinguishes direct embedding /
  reranker loaders from the server endpoints; `mlx-lm` is no longer described
  as core in the README install snippet, dependency table, or implementation
  guide.
- **Retained-run note:** the published 2026-08-16 18:47 artefacts (producer
  `519ba509`, blind lane, 41 models) are the first set produced entirely by
  the fixed analyser and supersede the earlier pre-fix snapshot; the only
  changes versus that snapshot are the two thinker rows regrading exactly as
  the fixed analyser predicted (Qwen3-VL-2B-Thinking → `usable`,
  ERNIE-4.5-VL-Thinking → `usable with caveats`).

- Configured thinking start/end markers are no longer pre-stripped from the
  analysis copy as generic control-token wrappers. Whenever a thinking budget
  was configured (auto or explicit), `_configured_output_wrappers` fed
  `</think>` into `_normalize_output_for_analysis`, which removed the closure
  before `_final_answer_view` ran; a seeded trace could then never be
  recognised as complete, so a model that reasoned and then answered was
  judged on its reasoning as "extra text before Title" (and quoted phrases
  inside the reasoning read as instruction echo). The markers stay reported
  as configured generation wrappers. Regression-tested on the exact
  `_populate_result_quality_analysis` path; on the 2026-08-16 run's real
  outputs Qwen3-VL-2B-Thinking regrades unusable → usable and
  ERNIE-4.5-VL-Thinking unusable → usable with caveats.

- Completed thinking traces no longer make a good answer "unusable". A new
  final-answer view (`_final_answer_view`) removes every *complete* recognised
  thinking trace — emitted `<start>…<end>` blocks and prompt-seeded blocks the
  model merely closed — before catalogue parsing, repetition, instruction-echo,
  preamble, and constraint checks run; the raw text and markers stay as
  neutral evidence and incomplete traces are still flagged. Replaying the
  2026-08-16 run: Qwen3-VL-2B-Thinking loses its false "extra text before
  Title" and regrades to usable-with-caveats on its genuine 11-word title;
  ERNIE-4.5-VL-Thinking likewise loses the false preamble.
- Decode timing now synchronises MLX *before* stopping the decode-phase and
  local generation timers, so `decode_time_s` includes all pending lazy GPU
  work and agrees with the attached generation duration; the `finally` only
  closes the phase timer when an exception escaped first.
- The per-model isolation boundary in `process_image_with_model` now catches
  any `Exception` (recording it as a phase-tagged failure with traceback)
  while letting `KeyboardInterrupt` and `SystemExit` propagate — an
  unexpected `TypeError` from a processor or upstream API can no longer abort
  the whole model sweep.
- Capped catalogue answers that end mid-list (`Keywords: …, Clouds,`) now
  record an `unfinished_list` token-cap reason instead of being missed as
  truncation evidence.
- Auto thinking budget detection now requires the rendered prompt to
  *terminate* with an open thinking marker, so closed `<think></think>`
  no-think stubs, few-shot examples, and literal marker mentions in user text
  no longer activate budgeting (regression-tested against the real rendered
  prompts of ERNIE, Qwen3-VL-Thinking, MiniCPM, and GLM-4.6V).
- The shared diagnostics `MODEL_ID` reproduction command now discloses when
  per-model automatic thinking flags diverge from the global arguments,
  listing each affected model with the exact flags to append; per-model
  overlays now trigger only on real value differences.
- Total telemetry probe failure now retains a zero-count record instead of
  silently omitting telemetry, so "both probes unavailable" is
  distinguishable from "telemetry disabled"; the snapshot-mode diagnostics
  label states that before/after snapshots cannot rule out transient
  pressure during inference.
- `tools/run_skylos_danger_advisory.sh` no longer ends a failing gate on a
  half-drawn "Continue anyway? [y/n]:" prompt. Skylos 4.33.x decides whether
  to offer that prompt from `stdout.isatty()` rather than stdin, so the
  existing `</dev/null` guard stopped suppressing it and the EOF aborted the
  script before it could print its own verdict. The gate's stdout is now
  piped, its exit code is read from `PIPESTATUS`, and an exit code above 1
  (analysis incomplete) is reported as an operational failure rather than a
  gate verdict.
- Extracted `_run_issue_summary_clean_completions_section()` from
  `generate_run_issue_summary_report()`, dropping the latter's cyclomatic
  complexity from 25 to 13 and clearing the `SKY-Q301` audit finding
  (repo threshold 24). Report output is unchanged.

### Changed


- `_run_model_generation` is split at one seam: `_prepare_generation`
  (prompt, processor, kwargs, diagnostics) and `_execute_prepared_generation`
  (upstream call, decode timing, synchronisation, exception tagging), joined
  by a small `_PreparedGeneration` NamedTuple.
- Telemetry mode is an explicit `SystemTelemetryMode`
  (`"snapshot" | "continuous" | "off"`) on `ProcessImageParams` and
  `SystemTelemetryRecord`, translated once from the `--system-telemetry`
  BooleanOptionalAction value.
- `ThinkingDelimiterPair` gains `auto_budget_eligible`; the transport-syntax
  `<|channel>thought` pair is evidence-only and never handed to automatic
  budgeting. Prompt diagnostics record `thinking_budget_source`
  (`"auto"` / `"explicit"`).
- `mlx-lm` is optional ecosystem provenance rather than a hard runtime
  dependency: this project has no direct `mlx_lm` import and upstream mlx-vlm
  dropped its own mlx-lm dependency (738e4406). It moves from core
  `dependencies` to the `extras` group, its absence no longer aborts a run,
  and the stale `SKY-U005` suppression is removed. Stale README references
  to mlx-vlm 0.6.2 / transformers 5.7.0 are corrected.

## [0.10.0] - 2026-08-14

### Added

- Promote `issues/run_summary.md` to the run's primary entry point. It now
  opens with a "Model quality at a glance" table ranking every attempted
  model by current-run usability with captured facts (total time, generation
  throughput, peak memory, short observation glosses, crash phase), names the
  clean completions, and is written on every run — including fully clean runs
  that previously removed it. `index.md` links it first under a "Start here"
  heading and the console dashboard labels it accordingly. The crash triage,
  observation clusters, review tables, and paste-ready issue framing are
  unchanged, and the table stays well under GitHub's 65,536-character issue
  limit.
- Wire the per-tensor KV cache quantization controls added in upstream
  mlx-vlm PR #1807 (`kv_key_bits`, `kv_value_bits`, `kv_key_scheme`,
  `kv_value_scheme`): new `--kv-key-bits`/`--kv-value-bits`/
  `--kv-key-scheme`/`--kv-value-scheme` CLI flags flow through
  `ProcessImageParams` into `generate()` only when set (PyPI releases
  predating the fields never receive them), are validated up front
  (per-tensor overrides require `--kv-bits`; uniform-scheme bit widths stay
  in the `mx.quantize` set), mirror into native-CLI issue repros, and are
  documented in the README KV-cache reference. The upstream-contract test is
  gated so it skips on PyPI installs that predate the fields.

### Changed

- `make bootstrap-dev` and `make update-quick` now upgrade pip through
  whichever manager owns it: in conda environments a runtime check
  (`conda list --no-pip`) detects a conda-owned pip and routes the upgrade
  through `conda update pip`; otherwise (pip-owned pip, venvs) the usual
  `pip install --upgrade pip` runs. A pip self-upgrade over a conda-owned
  pip leaves two pip versions interleaved in site-packages (both dist-infos
  present, `ImportError: cannot import name 'get_runnable_pip'` on launch),
  while `conda update pip` over a pip-owned pip reintroduces the second
  owner.
- Double the default generation token cap (`DEFAULT_MAX_TOKENS`) from 500 to
  1000 for the `blind` and `assisted` lanes. In the 2026-08-12 run, 10 of 16
  unusable results were truncated at the 500-token cap — 5 with incomplete
  thinking traces — so the old cap largely predetermined the usability verdict
  for thinking models. The `triage` (200) and deprecated `quality` alias
  (1000) caps are unchanged; the lane help text now interpolates the
  constants instead of hard-coding values.
- Update the development-time nanobind stub generator to 2.14.0 after verifying
  that it emits byte-identical `mlx.core` stubs against the current MLX build;
  MLX's separate build-time nanobind pin remains unchanged.
- Eval-mode hardening from a feature review: `--max-tokens` now defaults to an
  explicit unset sentinel so an explicit value always wins over the lane
  default — previously `--max-tokens 500` with `--eval-mode triage` was
  indistinguishable from "unset" and silently became 200. The
  `--prompt`/`--eval-mode` interaction is now stated explicitly in the help
  text, README, and run logs (a custom prompt overrides the lane prompt only;
  the lane still governs the default token cap and report labeling, and
  `assisted` still requires descriptive metadata). The exposed-and-assisted
  disclosure rule is single-sourced through `ReportModePolicy` (the JSONL
  header builder takes the policy instead of duplicating the AND),
  history/JSONL serialization requires an already-resolved `EvaluationLane`
  instead of silently re-resolving with no metadata, and the triage prompt
  constant is renamed `TRIAGE_PROMPT` (shared by the triage lane and
  differential reruns, which keep their tighter cap).

### Fixed

- Harden `src/tools/update.sh` against mixed conda/pip metadata damage: before
  upgrading its five core packaging tools, it now moves only malformed matching
  `.dist-info` directories to a reported temporary quarantine. This recovers
  from pip's `uninstall-no-record-file` failure without deleting metadata or
  touching unrelated distributions.
- Split `_prompt_burden_for_result` into a pure classifier
  (`_classify_prompt_burden`) plus a processed-dimension merge helper,
  clearing the Skylos SKY-Q301 cyclomatic-complexity advisory (28 over the
  threshold of 24) without behavior change; a redundant re-check of
  `text_est` inside an already-guarded branch was dropped.
- The environment report's package dump reads distribution Name/Version via
  `metadata.get` with an unknown-placeholder fallback, so a dist-info husk
  with no `METADATA` file (for example a leftover from a partial uninstall)
  no longer triggers Python 3.13 `importlib.metadata` DeprecationWarnings
  in every test run that exercises the dump; broken distributions now render
  as `<unknown>==<unknown>` instead of warning.

## [0.9.1] - 2026-08-11

### Changed

- Preserve every applicable inference setting in automatic differential reruns
  while overriding only the deliberately minimal triage prompt, token limit,
  temperature, timeout, and verbosity. Console preview and verbose modes now
  also render quality warnings from one shared decision path.
- Generate native mlx-vlm reproductions from declarative CLI mappings, including
  retained sampling, processor, adapter, revision, thinking, and KV settings;
  model-load crashes use a compact `--prompt x --max-tokens 8` reproduction.
- Keep Markdown and HTML chooser explanations in sync, including first-token and
  cross-attention caveats, and make dry runs apply the same exclusion validation
  as real model selection.
- Compact the monolith by removing unused numeric-format and injected-timer APIs,
  and single-source image verification, logging, triage prompt text, and Markdown
  ampersand escaping without changing retained output schemas.
- The suppression audit now requires every `noqa`/`type: ignore`/shellcheck
  suppression to carry a human justification (`- <why>` after the codes, or a
  second `# <why>` comment for `type: ignore`), and all fourteen previously
  bare suppressions gained one. Agent worktrees under `.claude/` are excluded
  from the audit, the Skylos configs, the danger post-filter, markdownlint,
  and commit hygiene, matching the existing `.worktrees/` policy (stale repo
  copies in agent worktrees were inflating the audit and could re-leak into
  gates).
- Single-source the two structurally drift-prone vocabularies: thinking
  delimiter pairs become a `ThinkingDelimiterPair` table carrying an explicit
  `reports_when_empty` policy flag (regexes, the legacy pair tuple,
  `DEFAULT_THINKING_END_MARKER`, and the empty-wrapper leakage branch all
  derive from it; the policy is pinned by test), and failure phases gain a
  `FailurePhaseName` Literal typing `PhaseTimer`, exception phase tags, and
  preflight raisers, with a complete human-label map asserted against the
  vocabulary. A misspelled phase or an unclassified new delimiter pair is now
  a type/test error instead of a silent misclassification.
- Add a sync-guard test pack so single facts can no longer drift silently
  across files: hook types single-sourced from `install_precommit_hook.py`
  and asserted against `.pre-commit-config.yaml`; the stub package list
  derived from `generate_stubs.DEFAULT_PACKAGES`; the Python floor asserted
  across pyproject, type-checker configs, `validate_env`, the conda setup
  script, and every workflow; workflow files enumerated by glob in both the
  YAML-validation step and the actions-pinning test; `SECTION:` banners
  asserted against copilot-instructions §3; smoke-test model/expected-output
  docs asserted against `update.sh` defaults; `.worktrees` added to the
  skylos mirror assertion; artifact schema versions extracted to constants
  matched against their TypedDict Literals; `make format` coverage asserted
  against the gate's formatter scope (and `check_models_data` added to
  `FMT_PATHS`); the Skylos danger worktree post-filter extracted to
  `tools/filter_danger_report.py` (safe-io hardened) with a unit test.
- Fix eight live cross-file drifts found by a coupling audit: danger-gate
  docs now state the gate is blocking (and the test guard asserts the real
  wrapper invocation instead of a vacuously absent flag); `update.sh` honours
  the `CONDA_ENV` override; `bootstrap-dev` stops installing the removed
  `huggingface_hub[cli]` extra; ruff/mypy `tools/.archived` excludes are
  spelled relative to their actual project root (they were silent no-ops);
  index.md artifact labels derive from real paths so custom `--output-*`
  names stay honest; `run_summary.md` and `reports/assets/source-image.jpg`
  resolve canonical GitHub URLs from out-of-repo output dirs; the commit
  hygiene hook never `--fix`es staged Markdown under third-party
  `.worktrees/`; the orphan `lint:md` npm script (a third, drifted
  markdownlint spelling) is removed; the markdownlint sync test no longer
  fails on fresh clones without the untracked lockfile; `.vscode` pyright
  severity and `.editorconfig` shell indentation match the enforced configs.
- Use the cached `mlx-community/nanoLLaVA-1.5-4bit` conversion for end-to-end
  smoke inference instead of the removed `qnguyen3/nanoLLaVA` fixture, so the
  full local quality gate exercises rather than skips both inference tests.
- Fix `validate_env`'s pre-commit framework check: it ran
  `pre-commit run --all-files --dry-run` (no such flag), which always failed
  and reported "hooks not installed" even when the framework hooks were in
  place. It now checks `.git/hooks` for the framework's generated pre-commit
  and pre-push scripts via the installer's own detection helper, and never
  executes the hook suite just to probe installation.
- Validate the input image once per run instead of once per model:
  successful validations are cached against the file's size and mtime (URLs
  cache for the process lifetime), failures are never cached. Saves the
  repeated full decode of large inputs (~15 s across 42 models on a 45 MB
  image) without weakening direct-caller validation.
- Crash issue drafts for model-load failures now render a durable native
  one-command repro (`python -m mlx_vlm.generate … --image any-local-image.jpg`)
  even when the run's image is unpublished, since load crashes occur before
  image decoding; post-load crashes still withhold the command rather than
  claim an unverifiable reproduction.
- Chooser preambles (Markdown and HTML) now caveat the Prompt tok column: for
  cross-attention architectures the token count reflects tokenised text burden
  only, not total vision prefill compute.
- Classify an empty `<|channel>thought` / `<channel|>` pair emitted by the
  model as visible control-token leakage while still ignoring it for catalogue
  field parsing; semantic thinking delimiters remain neutral when complete.
- Make the Skylos danger gate immune to two Skylos 4.33.x behaviors: findings
  from third-party checkouts under `.worktrees/` are now filtered out of the
  danger report (with a visible drop notice) before annotate/gate, because the
  scanner intermittently ignores both `--exclude .worktrees` and the config
  exclude for workflow files; and every skylos invocation in the quality
  scripts runs with stdin from `/dev/null`, since a failing gate on a TTY now
  launches an interactive "continue anyway?" prompt and a deployment wizard
  that offers to push commits.
- Fix a false durability claim in generated reports: GitHub artifact links
  were pinned to the producer's HEAD commit when the worktree was clean, but
  that commit predates the run and can only contain the *previous* run's
  artifacts. Artifact links now always target the default branch (valid once
  the run is committed; superseded by later runs), the run-summary caveat
  states that honestly, and SHA pinning is reserved for an explicit ref
  override during post-commit regeneration.
- Thinking-output analysis now uses the complete rendered prompt when deciding
  whether generation closes a prompt-seeded block, and records configured empty
  delimiter pairs as neutral evidence instead of wrapper leakage.
- The blocking Skylos danger scan now passes its `.worktrees` exclusion directly
  to the scanner, preventing third-party checkouts from failing this repository's
  quality gate.
- Uncap `markdownlint-cli2`: the npm spec is now a caret range (currently
  `^0.23.2`) with the untracked repo-local lockfile recording the resolved
  version, and
  `UPDATE_NODE_TOOLING=1` updates without `--save-exact`; the sync test
  asserts the uncapped policy instead of exact versions.
- End the git-hook installer tug-of-war: `tools/install_precommit_hook.py`
  now leaves pre-commit-framework-managed hooks in place (they run the same
  repo scripts via `.pre-commit-config.yaml`) instead of overwriting them —
  overwriting is why `validate_env` kept reporting the framework as not
  installed, and the framework then re-ran the overwritten script as a
  migrated `.legacy` hook, executing every check twice.

- Stub generation no longer imports pure-Python target packages: stubgen runs
  in source-tree (filesystem) discovery mode for mlx_lm/mlx_vlm, falling back
  to import mode only for C-extension packages (tokenizers) and lazy-module
  packages whose API exists only at runtime (transformers). This fixes the
  `RuntimeError: Timeout waiting for subprocess` failures from update.sh —
  mlx-vlm's package tree had outgrown mypy's fixed 30s inspection budget, and
  `mlx_vlm.chat_ui` raises SystemExit at import without gradio (upstream
  63c41804) — and cuts generation time from ~7 minutes to under a minute.
  Packages now run individually with one retry, and the dispatch.pyi
  re-export contract check is AST-based instead of exact-text. Two targeted
  Skylos suppressions document new-in-4.33.2 false positives (a snake_case
  phase key flagged as a high-entropy secret; a find_spec-derived path
  flagged as tainted).

- Separate model prompt compliance from maintainer-worthy observations: each
  observation in the display registry now declares whether it is an
  integration signal (repetition, empty output, control-token/role leakage,
  incomplete or unanswered thinking) or a compliance note (missing fields,
  constraint counts, hint copying, instruction echo, minimal output, cap
  hits). Only integration signals place a completed model in the maintainer
  lane; compliance-only results keep their usability impact and move to a new
  "Model Compliance Notes (not maintainer issues)" diagnostics section, and
  the run summary reports them beside the strictly observation-free clean
  count.
- Rank observation summaries by integration importance (registry order)
  instead of frequency in the index dashboard, diagnostics counts, and
  run-summary clusters, so e.g. repetition outranks a frequent constraint
  miss.
- Wrapper-aware structural parsing: generic control-token wrappers and empty
  thinking wrappers are stripped from the semantic analysis copy before
  section/preamble/cutoff detection, so a model that produced the requested
  fields inside a leaked wrapper (e.g. "<|begin_of_box|>Title: ...") is
  assessed on those fields while the leak itself is still reported.
- Resource highlights now consider only clean completions ("Fastest clean
  completion", "Lowest peak memory among clean completions") and the average
  throughput line carries an explicit cross-model comparability caveat.
- The choosers gain a "Prompt tok" column (full rendered prompt including
  image tokens) so prefill cost is attributable at a glance.
- Load failures reporting parameters the architecture does not expect
  ("Received N parameters not in model") now attribute to mlx-vlm
  (architecture/conversion mismatch) instead of mlx; genuinely missing
  weights stay with the model-config owner.

- Diagnostics per-model facts now include the "Arch supported by installed
  mlx-vlm" pre-check verdict (previously gallery-only), so the maintainer
  surface carries the architecture context directly.

- `--dry-run` no longer writes `check_models.log` or `environment.log`: no
  models are invoked, and overwriting the retained artifacts of a real run
  would desynchronize them from the run's other tracked outputs.
- Console token-cap note now uses the same gate as the
  `token_cap_truncation` observation: a cap hit with degradation evidence
  still warns, while a structurally sound response that merely used its full
  budget logs as neutral information.
- Documentation drift fixes: `IMPLEMENTATION_GUIDE.md` no longer claims
  generated reports are gitignored (all current-run artifacts are tracked
  except the append-only history), and the 0.9.0 changelog entry now states
  the final output-tracking policy once instead of recording the
  intermediate decisions separately.
- Test durability: the Skylos dev-dependency sync check derives the spec
  from `pyproject.toml` instead of hardcoding it, and the markdownlint
  rule-set guard asserts the live constant values rather than exact source
  spelling.

### Fixed

- The Pyrefly quality gate now works from linked worktrees under hidden
  directories (for example `.claude/worktrees/*`): the generated config
  disables ignore-file collection (the parent repo's `.git/info/exclude`
  ignores `.claude/worktrees/`, which made project discovery match zero
  files) and Pyrefly's hidden-directory exclude heuristic, restoring the
  dropped default excludes explicitly plus gitignore-parity ones
  (`build/`, `dist/`, egg-info, `output/test*`) so the primary-checkout
  gate covers the same files as before. Relative `search-path` entries
  missing from the current checkout (worktrees do not carry the
  gitignored `typings/`) now resolve against the primary checkout so both
  consume the same stubs. Guarded by a sync test on the generated config.
- As a second layer of the same defense, the gate now passes explicit file
  targets (enumerated via `git ls-files`, minus `tools/.archived/`) instead
  of relying on project discovery at all: single-file checking mode skips
  filesystem discovery entirely, so the checked file set cannot be eaten by
  parent-repo ignore files or future Pyrefly discovery heuristics, and
  gitignore semantics come from git itself rather than hand-mirrored
  excludes. A sync-guard test pins the single-file-mode invocation.
- The commit hygiene hook no longer crashes on a commit that stages
  `src/pyproject.toml` without any Markdown files: the README-sync path
  expanded the empty `markdown_files` array unguarded, which macOS
  bash 3.2 under `set -u` rejects as an unbound variable.

## [0.9.0] - 2026-08-08

### Added

- Add an "Output at a Glance" table to the Markdown gallery (after "Avoid for
  This Run"): every model's actual output preview (first 280 characters, or
  failure evidence for crashes) in chooser order, so a reader can get a feel
  for what each model said without expanding per-model evidence blocks. The
  judgement-focused chooser table stays preview-free; the HTML report already
  carried this as its sortable "Output preview" column.
- Add a `benchmarking-mlx-vlm` agent skill (conda+pip adaptation of the
  upstream mlx-vlm benchmarking methodology: warmup + median-of-N,
  `mx.eval`/`mx.synchronize` before timers, peak-memory protocol, single-env
  A/B discipline), document the architecture pre-check in the
  `hf-cache-mlx-vlm-models` skill, and note which upstream skills are
  deliberately not adapted.
- Port upstream mlx-vlm's `--check-arch` compatibility tier into discovery
  diagnostics: cached `config.json` `model_type` (with `MODEL_REMAPPING`
  aliases parsed from the installed mlx-vlm source via `ast`, never importing
  mlx) is compared against installed `mlx_vlm/models` packages. Surfaced as
  `--dry-run` annotations with an unsupported-architecture count, a per-model
  "Arch supported by installed mlx-vlm" gallery fact, and an optional
  `architecture` record in `results.jsonl`. Models with unsupported
  architectures are still attempted so real crash evidence is captured, and
  upstream's "Model type {x} not supported." crash now classifies as a
  dedicated `Unsupported Arch`/`UNSUPPORTED_ARCH` category instead of a
  generic Model Error.
- Recognise mlx-vlm's server-side thinking marker pairs
  (`<|channel>thought`/`<channel|>` and `<|START_THINKING|>`/`<|END_THINKING|>`)
  as first-class thinking-trace delimiters, with the trace's own delimiters
  excluded from control-token leakage flags (including prefix captures of the
  generic `<|...|>` pattern). Empty-wrapper neutrality now also derives from
  the full delimiter-pair table instead of matching only `<think></think>`,
  so e.g. an empty `<|channel>thought<channel|>` wrapper before a substantive
  answer no longer downgrades the result to "control tokens visible".
- Add a conditional, paste-ready whole-run GitHub issue summary with expanded
  crashes, a compact table of other surfaced results, clean-completion counts,
  and links to full retained evidence. Generate it during normal finalization,
  link it before individual crash drafts, and support report-only regeneration
  from schema-2.0 JSONL and optional run JSON without rerunning models.
- Document product recommendations for issue-ready diagnostics and model-selection
  galleries aimed at mlx-vlm maintainers and image-description users
  (`docs/notes/archive/DIAGNOSTICS_USEFULNESS_RECOMMENDATIONS.md`).
- Add agent skills for native mlx-vlm reproduction, HF cache discovery alignment,
  and upstream issue drafting (pip/conda adaptations of Blaizzy/mlx-vlm#1343
  support workflows) under `.agents/skills/`, with pointers in contributor and
  implementation docs.
- Capture a human review of `src/check_models.py` compression, robustness, and
  analyzer-friendly structure options
  (`docs/notes/archive/CHECK_MODELS_MONOLITH_COMPRESSION_REVIEW.md`).

### Changed

- Structural compression follow-up: the run-issue JSONL validators now share
  one `_require_optional_str_fields` helper, a table-driven assessment
  vocabulary check, and a `_json_int_or_none` narrower (the unused
  `RunIssueSummaryValidationError` subclass is removed); the generate() drift
  detector derives its parameter contract from `_SENT_GENERATE_KEYWORDS` —
  exactly the keywords the kwargs builders send, locked by a builder-parity
  test — so upstream parameters this harness never passes (e.g. audio/video)
  can no longer raise false drift; and `getattr` probes on the module's own
  frozen dataclasses and fully-parsed CLI namespace are converted to direct
  attribute access so typos fail loudly (probes on upstream objects, partial
  regeneration namespaces, and exceptions remain deliberately defensive).
- Retire three now-inert compatibility fiddles (~350 lines): the local-only
  artifact link machinery (every linked artifact is tracked, so the
  relative-link special cases were unreachable); the `load_image` source-grep
  preflight shim (upstream guarded the URL branch in mlx-vlm 0.4.0, below the
  project floor); and the lossy-BPE detokenizer monkeypatch + retry wrapper
  (upstream fixed the UTF-8 flush in 0.6.9 — the `mlx-vlm` floor is raised to
  `>=0.6.9` accordingly and generation now fails fast with decode-phase
  tagging instead of monkeypatching upstream internals).
- Align the CLI with mlx-vlm's `generate` CLI where they overlap:
  `--prefill-step-size` default drops from 4096 to upstream's 2048, and a new
  `--thinking-mode` flag passes through to chat templates that support it
  (independent of `--enable-thinking`, matching upstream). A new
  `TestUpstreamCliParity` guard asserts shared-flag defaults match upstream,
  with an explicit allowlist documenting the deliberate divergences
  (`--max-tokens` 500, harness-built `--prompt`, `--revision` None,
  `--thinking-start-token` None, `--trust-remote-code` on-with-warning).
- Promote two log-only facts into `results.jsonl`: the complete rendered
  chat-template prompt (`prompt_diagnostics.rendered_prompt`, beside the
  bounded preview) and the tee'd upstream console output for **successful**
  runs (`captured_upstream_output`, bounded/deduplicated like the file-log
  copy; failures already kept `captured_output_on_fail`). Both are
  home-path-sanitized before serialization.
- Exclude agent-managed `.worktrees/` checkouts from the repo-root Skylos
  danger gate: they hold third-party repositories (e.g. an upstream mlx-vlm
  checkout) whose GitHub workflows are not this repository's to gate, and
  their findings were failing `make quality` as false alarms.
- Catalog-constraint observation labels now name only the constraints that
  were actually breached: an in-range title or keyword count no longer reads
  as a second failure beside a real violation such as duplicate keywords
  (seen live when a model produced valid counts but repeated two keywords).
- `make update` now runs the full `tools/update.sh` orchestration
  (conda/Homebrew refresh, local MLX repo pulls and source builds, stub
  regeneration, runtime smoke); the previous lightweight pip refresh moved to
  `make update-quick`, and `make update-full` remains as a compatibility
  alias. Contributor docs updated to match.
- Promote the Skylos `--danger` scan into the blocking quality gate: the
  repo-root scan is clean, so `make quality` (full mode) now fails on any
  danger finding via a new "Skylos Danger Gate" step
  (`run_skylos_danger_advisory.sh --full --gate`). `make skylos-danger`
  keeps the advisory, diff-aware form for PR triage; the fast gate
  (pre-push) is unchanged.
- Harden the new file reads/writes flagged by the advisory Skylos danger
  scan: the architecture pre-check resolves the HF-cache `config.json`
  symlink but requires containment inside the repo's cache directory and a
  regular, size-capped file (via `_read_text_file`); test helpers use
  `safe_io.write_text_no_follow`/`read_text_no_follow` instead of raw
  `Path.read_text`/`write_text`.
- Docs/Makefile/packaging hygiene: root `README.md` output list now matches
  the real artifact set (removed nonexistent `results.md`/`results.tsv`,
  annotated tracked vs local-only); root `make help` is auto-generated from
  `##` comments (11 previously invisible targets now listed); `stubs-clear`
  aliases `clean-stubs`; `check_models-demo` actually differs from
  `check_models`; `validate-env` delegates to `tools.validate_env` instead of
  duplicating its probes; the previously make-unreachable `tools/update.sh`
  is now wired into make (see the `make update` entry below); the
  `subprocess` pytest marker is
  declared in `pyproject.toml`; `pip-audit` ships in the dev extras so
  `make audit` stops installing at runtime; `AGENTS.md`/`CLAUDE.md` parity is
  guarded by a test; duplicated dependency/make-target doc sections in
  `CONTRIBUTING.md`/`IMPLEMENTATION_GUIDE.md` now carry canonical-source
  pointers; `check_models.py` gains an architectural module docstring
  (report-block AST, observation registry, artifact fan-out, discovery) and
  three drifted sub-banners are renamed to match their contents (the 13
  `SECTION:` landmarks are unchanged).
- Merge the gallery's three redundant chooser tables into one: the sortable
  Current-run Chooser remains the single row set, and the former
  "Lowest-memory"/"Fastest Usable Models" re-listing tables collapse into a
  "Resource Highlights" section (fastest model, average valid throughput,
  lowest captured peak memory). Both renderers now derive ordering and
  highlights from one shared `_gallery_chooser_data` dataset, and per-model
  gallery evidence bodies (output/traceback/captured-output branches) render
  through one shared report-block builder instead of parallel Markdown and
  HTML implementations. Failure evidence labels are now `####` headings in
  Markdown (previously emphasis lines) to match the HTML structure.
- Drop the `tabulate` dependency: report tables render through a small
  built-in padded pipe-table emitter (numeric columns are now left-aligned
  like text). Runtime-fact producers return `(label, value)` pairs directly,
  removing the HTML renderer's markdown-bullet re-parsing.
- Improve report skimmability for 60+ model runs: the output index now leads
  with a "Run at a glance" dashboard (outcome counts, usability breakdown, top
  observations) before the artifact links; the collapsed "Exact raw output"
  copy is emitted only when it would differ from the readable view (markdown:
  trailing whitespace or escaped markup; HTML: never, since escaping is
  lossless); diagnostics folds every complete traceback in a `<details>` block
  so one crash's multi-hundred-line dump cannot bury the triage tables; and the
  run-issue-summary link caveat is now dynamic — pinned-commit wording when
  artifact links carry a clean-worktree SHA, mutable-branch wording otherwise.
- Consolidate duplicate and dead code in `check_models.py` (net −132 lines,
  behavior-preserving): delete the unused `_native_mlx_vlm_*_kwargs` repro trio
  superseded by the CLI-token builder; drop vestigial `artifact_name`/`prompt`
  parameters; collapse the byte-identical timed/untimed branches of
  `_prepare_generation_prompt` with `nullcontext`; share one memory-delta
  fallback helper between history and JSONL records; share one failure-outcome
  helper across run-issue-summary skip paths; route the styled log wrappers
  through one `_log_styled` helper; extract the repeated relative-target
  builder inside `_markdown_artifact_target`; reuse `_make_rich_console` for
  the reports dashboard console; and hoist an O(n²) per-result provenance
  rebuild out of `save_run_json_report`. Reviewed-and-rejected merges (accessor
  chain, escaper classes, lib-name tuple derivation, 4-site metric-record
  unification) are documented inline where relevant.
- Output-tracking policy (final state after intermediate iterations during
  this release cycle): every current-run artifact — `index.md`,
  `reports/results.html`, `reports/model_gallery.md`,
  `reports/diagnostics.md`, `results.jsonl`, `run.json`, `check_models.log`,
  `environment.log`, `issues/`, and `reports/assets/` — is tracked in git and
  browsable on GitHub via SHA-pinned links. Only the append-only
  `results.history.jsonl` is gitignored/local-only, and no report links to
  it. Existing git history is unchanged by design.
- Persist tee'd live mlx-vlm console output (prompt, generated text, and upstream
  timing/memory lines) into `check_models.log` for every model attempt, success
  or failure, as a file-only log record so the durable log keeps the model text
  that already appears on the terminal without a second console echo. Bound very
  large captures and keep this independent of `--verbose`.
- Consolidate mechanical observation metadata into one display registry, derive
  run-issue assessment vocabularies from the canonical Literals, compact large
  unexpected-parameter lists in diagnostics and crash drafts as well as the
  paste-ready run summary, pin clean-worktree GitHub artifact links to the
  producer commit SHA, add observation cluster counts above review tables, and
  give Markdown choosers short selector glosses plus a Prefill/first-token column.
- Keep prompt-seeded, already-closed empty thinking wrappers as neutral evidence;
  omit conclusively stale logs from paste-ready issue summaries; compact large
  unexpected-parameter lists there; and narrow Markdown chooser tables by
  removing duplicated output previews while retaining complete model evidence.
- Reuse a fresh full-gate result when a branch integration is a clean
  fast-forward to the exact tested commit, while retaining revalidation for every
  integration that produces or exposes a different tree.
- Treat a properly closed configured thinking block followed by substantive final
  text as neutral machine evidence, while classifying incomplete thinking,
  thinking-only output, and credible token-cap truncation as unusable incomplete
  responses. Prompt-seeded and custom thinking delimiters use the run parameters.
- Consolidate diagnostics and crash-report reproduction around one
  publication-safe builder: local inputs expose exact characteristics without a
  fake command, while public digest-verified inputs receive a native one-process
  mlx-vlm command. Advertise the paste-ready run summary in `run.json` only when
  cached assessments surface a result.
- Render comparison and completed-model terminal summaries with compact Rich
  tables, use one severity-first ordering across terminal and retained reports,
  and clarify crash and usable-with-caveats headings.
- Replace the final pipe-delimited completed-model list with compact Rich tables
  grouped by usability and ordered by likely actionability, and separate replayed
  per-model result blocks so warnings and metrics remain visibly associated with
  the correct model.
- Prevent diagnostics finalization from crashing when catalogue constraint
  observations include structured title, keyword-count, or duplicate evidence.
- Ignore numeric ranges in descriptive metadata hints when validating catalogue
  title and keyword constraints against their prompt requirements.
- Make run issue summaries more actionable by sorting each execution table by
  likely output impact, spelling out structured failures when no observation is
  available, recording remote-code and producer provenance, and ignoring generated
  `src/output/` changes when calculating producer dirtiness. Detailed crash drafts
  now keep only runtime-relevant environment facts and link to the complete
  repository environment artifact.
- Record out-of-range catalogue title/keyword counts and duplicate keywords as
  structured repairable caveats, and recognise configured turn, message, and
  utterance delimiters as visible role-boundary tokens.
- Make paste-ready crash reproductions self-contained when the exact input image
  has a recorded public HTTP(S) source: include download and SHA-256 verification
  commands plus a native mlx-vlm invocation with the exact prompt. For unpublished
  local images, report format, dimensions, byte size, and digest while explicitly
  withholding a misleading command that refers to private or synthetic files.
  Gate inference on successful download and digest verification, and preserve the
  run's remote-code trust policy conservatively in regenerated summaries.
- Make human-facing observation labels explanatory and severity-ordered, split the
  compact run issue summary into completed, crashed, and indeterminate review
  tables while keeping actionable crashes expanded, and preserve canonical GitHub
  evidence links when issue-ready Markdown is pasted outside the repository.
- Keep HTML complete model evidence in the same usable-first order as the Markdown
  gallery, and preserve seed and repetition settings in supplemental native mlx-vlm
  CLI reproduction commands.
- Document Ruff's unsafe fixes as an optional, preview-first shortcut only when
  they are faster than manual lint correction, with critical diff review and
  targeted verification required before retaining any semantic change.
- Archive completed Superpowers plans and designs for issue-ready reporting,
  Skylos cleanup, and diagnostics usability quick wins under
  `docs/notes/archive/superpowers/`, and remove the empty active
  `docs/superpowers/` tree.
- Shorten the default blind and assisted catalogue prompts, present existing title,
  description, and keyword metadata explicitly as fallible hints, and keep prompt-aware
  diagnostics compatible with retained prompts that use the former draft labels.
- Present usable and caveated models before unusable or unevaluated attempts in
  Markdown and HTML galleries; keep crash facts above collapsible exact traceback
  detail in direct issue drafts, link those drafts from the current-run output
  index, and document `triage` as the plain-caption comparison lane.
- Record active and cache allocator residue after every model cleanup, including
  crashed attempts, in human and machine evidence so gradual cross-model memory
  growth can be investigated. Add sortable HTML chooser columns, including the
  upstream prefill/first-token interval, without widening the Markdown chooser.
- Surface exact, neutral observations when a model returns every supplied draft
  metadata field unchanged or emits EOS/thinking wrappers declared by current
  mlx-vlm generation types. Keep those facts separate from semantic scoring,
  unexpected-token leakage, and unusable-output classification.
- Preserve the deliberately conservative repetition detector while ensuring
  duplicate-dominated or repeated output remains highlighted with its repeated
  fragment and complete model output in issue-ready diagnostics.
- Make current-run usability reject copied prompt instructions, structurally
  invalid catalog sections, unexpected text before the requested Title, and
  duplicate-dominated keyword output; accept conventional bold Markdown labels
  and exclude reusable context values from instruction-echo matching. Retain exact
  observation evidence without introducing semantic caption scoring.
- Make diagnostics smaller and more actionable by omitting empty per-model facts
  and duplicate readable/raw output, while the gallery gains a publishable source
  image preview bounded to 1024 pixels, lint-safe preformatted model text, and
  end-to-end time ahead of decode throughput. Keep crash issue-draft section
  boundaries Markdown-lint safe.
- Record producer worktree dirtiness and per-model completion timestamps, label
  conclusive outcomes unambiguously in human reports, and distinguish configured
  role-boundary tokens from unknown special-token leakage.
- Widen the configured thinking-delimiter collection explicitly and narrow
  validated memory samples before construction so Pylance agrees with the mypy,
  ty, and Pyrefly contracts without casts or suppressions.
- Make the gallery preserve line breaks and present model-authored formatting while
  retaining exact raw output, and make diagnostics a skim-first mlx-vlm issue body
  with expanded crashes, collapsed highlighted evidence, compact clean-run context,
  and one shared parameterised reproduction and provenance section.
- Render Markdown and HTML diagnostics from one narrowly typed recursive report
  representation, tighten table/link/output block annotations, and remove
  superseded helpers without weakening types or adding lint suppressions.
- Preserve the production PEP 695 aliases while using equally narrow test-local
  types that Skylos can resolve, and simplify four gallery, console-summary, and
  JSONL builders below the configured complexity threshold without suppressions
  or output-contract changes.
- Document the ignored repo-local Node lockfile bootstrap required in fresh Git
  worktrees before running dependency-policy or Markdown-lint checks.

### Fixed

- Accept callable custom mlx-vlm processors that support images without exposing
  Transformers' optional `image_processor` attribute, and retry connectivity-only
  Hub load failures from a matching resolved local snapshot when downloads were
  not forced.
- Exclude ignored `.worktrees/` checkouts from suppression and Markdown audits so
  an isolated upstream checkout cannot contaminate check_models quality results.
- Preserve `ObservationCode` key typing while building diagnostics counts so
  Pylance agrees with the other supported type checkers at the label-rendering
  boundary.
- Recognise conventional one-to-six-hash Markdown headings such as `### Title:` as
  valid structured catalogue fields instead of incorrectly reporting their Title,
  Description, and Keywords sections as missing.

### Removed

- Remove superseded definition-only report-stanza, detection, metric, metadata,
  runtime-prose, diagnostics-framing, and quality-label helpers and their obsolete
  cache-only test, plus the unused duplicate quality-issue regex registry.
- Archive the hazardous one-off Qwen3-VL sequential Metal probe and completed
  development plans, specifications, and Skylos backlog so active tooling and
  guidance describe only maintained workflows.

## [0.8.9] - 2026-07-26

### Changed

- Require deterministic focused/static/full quality gates before costly model
  matrices, including fixture-rendered Markdown preflights, and a repaired,
  re-audited Run 1 before any comparative Run 2.
- Make one validated current-run assessment/provenance context authoritative for
  console summaries and every retained artifact; write canonical JSONL first and
  isolate optional renderer failures without corrupting machine evidence.
- Restrict minimal-output observations to recorded empty or one/two-word evidence,
  detect explicit default and configured thinking delimiters independently of
  model names, and preserve generated text (including tabs) byte-for-byte.
- Replace the score-, grade-, winner-, and history-derived reporting pipeline with
  a facts-first current-run assessment shared by the retained HTML, gallery,
  diagnostics, JSONL, and run JSON artifacts. The assessment now exposes only exact
  execution, usability, maintainer-status, and mechanical-observation facts.
- Introduce breaking JSONL and run JSON schema `2.0` contracts with complete model
  output or crash evidence, normalized tracebacks, exact run arguments, and
  publication-safe component, model, prompt, and source-image provenance.
- Retire the duplicate Markdown index, selection, review, TSV, capability-scorecard,
  inferred queue, and reproduction-bundle outputs. Keep a tiny artifact index, raw
  append-only history as secondary data, and conditional factual issue drafts only
  for hard actionable crashes.
- Treat token caps, long complete output, partial keyword overlap, configured
  thinking tokens, and connectivity interruptions according to their captured
  evidence rather than inferred quality or ownership; zero keyword overlap remains
  only a weak caveat and disconnected attempts remain indeterminate.
- Preserve complete factual evidence across reports while restoring the static
  quality baseline through current mlx-vlm generation types, narrower annotations,
  Ruff-compatible formatting/lint cleanup, and generated-stub integrity checks.
- Cap the optional `tokenizers` extra to the validated `0.22.x` line and retain the
  package/runtime provenance, Apple Silicon hardware context, dependency checks, and
  CLI validation hardening accumulated since `0.8.0`.
- Make retained public run evidence publication-safe and exact by sanitizing JSONL
  system paths, preserving explicit generation settings such as `--seed 0`, and
  labeling logged output checks as mechanical observations rather than quality.
- Make generated reproduction commands checkout-runnable by retaining their exact
  source-image fixture, and pin them to the same resolved model revision recorded
  across diagnostics, JSONL, and run JSON while keeping requested revisions distinct.

### Fixed

- Preserve EXIF capture wall clocks with their declared UTC offsets and avoid
  repeating the extracted time in assisted prompts; recognise Pillow's
  `DateTimeDigitized` tag and omit unknown dates instead of substituting filesystem
  modification time.
- Preserve trailing whitespace inside fenced generated output, flag generic
  undeclared control wrappers while accepting tokenizer/EOS/thinking metadata,
  use repository-style Markdown emphasis, and keep compact run summaries
  readable without dropping outcome counts.
- Keep completed-unusable runs neutral and out of performance rankings, distinguish
  requested from resolved revisions in human reports, and sanitize operational paths
  in public failures, provenance, captured streams, and artifact manifests while
  retaining exact raw logs and model-generated text.

### Tooling

- Require Ruff 0.16 or newer and keep `select = ["ALL"]`, so every stable rule in
  the supported Ruff release—and newly stabilised rules in later releases—is
  enabled automatically.

## [0.8.0] - 2026-06-06

### Added

- Add an upstream-only Qwen3-VL Metal fault probe for comparing single-model,
  reversed-order, repeated-model, and sequential in-process failures.
- Expose MLX-VLM 0.6.2 server-shared generation controls in the CLI:
  `--seed`, presence/frequency penalties, and `--logit-bias`, with passthrough
  coverage in native Python repro snippets.

### Changed

- Remove definition-only private helpers from the diagnostics and review-report
  paths to keep the single-file CLI smaller without changing generated output.
- Improve `--help` readability with a concise usage line and grouped CLI
  sections.
- Raise the project `mlx-vlm` floor to `>=0.6.2` and document which current
  server API surfaces remain `mlx_vlm.server`-only.

### Fixed

- Make generated upstream Python repro snippets apply the `mlx-vlm` chat
  template before calling `generate()`, matching the harness prompt path.
- Accept the current package-layout `mlx_vlm.generate` stubs by patching and
  verifying `generate/dispatch.pyi`, widening `generate/ar.pyi` batch inputs,
  and removing stale legacy `generate.pyi` files when present.
- Keep generated Transformers `ProcessorMixin` stubs compatible with current
  stubgen output by widening its existing tokenizer and image-processor runtime
  attributes before enforcing project stub integrity.
- Target the host macOS version during local `mlx` builds when
  `MACOSX_DEPLOYMENT_TARGET` is unset, avoiding setuptools' macOS 26.0 default
  while preserving explicit caller targets.
- Export the host macOS deployment target before dependency installation in
  both macOS CI jobs, matching the local MLX-build workaround and upstream fix.
- Restore the prompt-preparation phase in detailed runtime timing logs so
  verbose metrics output and regression coverage stay aligned.

## [0.7.3] - 2026-05-29

### Changed

- Keep the full Ruff gate green by documenting `analyze_model_issues()` image
  profile handling and extracting its recommendation highlight bookkeeping into
  a small private helper.
- Tighten diagnostic quality analysis by adding unstructured metadata alignment,
  text-sanity/generation-loop labels, and 21-day history-window regression
  context so mechanically clean gibberish is no longer promoted as usable.
- Refresh the AI-agent navigation line map for the current `src/check_models.py`
  layout and test-suite size.
- Add the calibrated Skylos quality gate to the local quality script and manage
  Skylos as a dev dependency.
- Default generated Markdown/report artifact links to absolute GitHub URLs so
  pasted diagnostics and issue drafts keep working outside the local checkout,
  while preserving `--link-style relative` for offline/local paths.
- Keep generated `issues/index.md` lint-clean under GitHub link output by
  wrapping the run summary text and bracketing the wide issue queue table with
  markdownlint guards.
- Narrow generated `diagnostics.md` markdownlint suppressions to line length,
  scope table-column guards around generated tables, and re-enable useful
  duplicate-heading, excess-blank-line, and limited inline-HTML checks.
- Mark generated issue drafts as exempt from issue-body markdownlint rules,
  disable `MD012`/`MD013` for generated review digests, and bracket the wide
  generated Affected Models and review Maintainer Escalations tables so
  GitHub-link output stays clean under `MD060/table-column-style`.
- Route generated text artifacts through symlink-resistant file helpers.
- Calibrate Skylos quality thresholds and advisory ignores for the intentional
  single-file CLI, behavior-grouped tests, and package-local scan layout.
- Add package-local Skylos gate/exclusion config for `src` scans and reduce the
  remaining critical complexity hotspots in review verdicts, diagnostics
  runtime coverage, compact metrics, model comparison, utility triage, and
  history comparison without splitting the monolith.
- Remove resolved one-off planning docs from `docs/notes/` and
  `docs/superpowers/`, keeping the in-tree docs set focused on current
  contributor guidance and active reference notes.
- Refactor targeted Skylos warning hotspots in report rendering, image metadata
  extraction, macOS toolchain probing, history JSONL parsing, and stub patching
  without changing public output contracts.
- Exclude generated `src/build` artifacts from the suppression audit so it
  reports only maintained source suppressions instead of duplicate build-copy
  findings.
- Stop tracking generated suppression-audit snapshots, ignore future
  `*.suppression-audit.*` artifacts, and avoid a test-only `S106` false
  positive in quality-analysis coverage.
- Harden generated Markdown escaping by normalizing hard tabs in fenced code
  blocks and fully escaping multi-underscore runs in diagnostics/gallery text.
- Reduce Skylos scan noise by excluding generated suppression-audit snapshots,
  and flatten two report/history log helpers into smaller private builders
  without changing output contracts.
- Calibrate repo-root Skylos scans to ignore generated output and lockfile
  noise, document the quality-diagnostic backlog, and raise the Pillow floor to
  `>=12.2.0`.
- Streamlined report finalization by driving report generation and artifact
  logging from one internal artifact list, reducing duplicated output-path
  handling without changing report formats.
- Fail the shared quality hooks when Pyrefly emits warnings so non-blocking
  type-cleanup regressions do not slip past `make quality` and pre-push checks.
- Refactor report assembly toward shared Markdown/HTML section primitives and
  normalized repro command specs so diagnostics, issue drafts, review queues,
  and summary reports reuse the same rendering and command-token paths.
- Make generated upstream issue drafts more maintainer-focused by replacing
  `check_models` repro commands with native `mlx_vlm.generate` CLI and Python
  repro snippets, inlining prompt/config details, framing JSON bundles as
  optional context, and removing raw cluster/error-code jargon from pasteable
  issue bodies.
- Make `diagnostics.md` a compact pasteable run-level issue body by enriching
  the issue queue with inline evidence snapshots while moving verbose trace,
  prompt, and portable-probe detail to issue drafts and repro bundles.
- Remove the separate `Upstream Filing Notes` block from `diagnostics.md` so
  the diagnostics artifact itself can be handed to upstream maintainers
  directly without extra filing guidance.
- Focus diagnostics and issue-draft triage rows by preserving multiline
  runtime error details and rendering evidence as concrete supporting facts
  instead of repeating summary prose.
- Add run-context headers to `issues/index.md` so the issue queue is useful as
  a standalone launchpad.
- Align the MLX-VLM integration with `mlx-vlm` 0.5.0 by exposing the image-relevant
  `load()` flags, refreshing generated `generate()` stubs for `video` and KV
  quantization kwargs, and raising the runtime `mlx-vlm` floor to `>=0.5.0`.
- Extract performance data from upstream `GenerationResult` fields for JSONL and
  runtime diagnostics, while keeping local allocator snapshots as supplemental
  active/cache memory fields.
- Update local MLX repository installs to use upstream's editable dev install
  guidance for `mlx`.
- Harden local MLX setup/update tooling by checking current Xcode/SDK/Metal
  build prerequisites, verifying the `mlx`/`mlx-metal` backend pair during
  fresh conda setup, logging `mlx.metallib` provenance, and adding an automatic
  cached-model smoke test for local MLX builds.
- Make `src/tools/bugtest.py` a lint-clean importable CLI probe and call it from
  `src/tools/update.sh` as a non-blocking reminder when the installed MLX Metal
  backend still shows the M5 NAX matmul regression.
- Include `mlx-metal`, Xcode/SDK/Metal compiler details, and MLX backend
  artifact fingerprints in diagnostics and issue-draft environment tables so
  Metal build regressions are reproducible from pasted reports.

### Fixed

- Avoid flagging valid Markdown emphasis endings such as `**Keywords:**` as
  repeated-punctuation output degeneration.
- Repair common UTF-8-as-Latin-1/CP1252 mojibake in decoded EXIF display text
  so metadata such as `Copyright © ...` no longer prints as `Copyright Â© ...`.
- Preserve the `recommended` user bucket for benign token-cap results when
  trusted metadata alignment passes.
- Keep Ty green against current generated `mlx_vlm.generate` stubs by casting
  the optional `mlx-vlm` import boundary to the local generation callable
  protocol.
- Remove stale backend-import feature-flag documentation for the previously
  deleted `MLX_VLM_ALLOW_TF` / `TRANSFORMERS_NO_*` guard path.
- Restore the Skylos quality-gate terminal/color guard so terminal capability
  probe bytes do not leak into local `make quality` output.
- Remove the stale `tzlocal` import from the fresh conda setup verifier and
  replace the removed `huggingface_hub[cli]` extra install with a current CLI
  availability check.
- Add `.python-version` and update `.vscode/settings.json` to help IDE static
  analysis extensions (like Pyright) automatically discover and resolve the
  `mlx-vlm` Conda environment.
- Remove the unused `check_conda_env()` validation wrapper while keeping the
  strict expected-environment check used by the validation entrypoint.
- Escape lone ordered-list markers in generated Markdown blockquotes so model
  outputs like `11)` no longer trip markdownlint `MD029`.
- Escape attributes on otherwise allowed HTML formatting tags, render HTML
  result tables from explicitly escaped cells, remove stale archived Python
  quality scripts from scan scope, and declare the direct `numpy` runtime
  dependency to address security-scan findings.
- Render cross-artifact links in generated Markdown outputs as GitHub blob/tree URLs instead of local relative paths so `results.md`, `review.md`, `diagnostics.md`, and generated issue drafts can be pasted directly into GitHub issues without breaking their companion links.
- Keep best-effort MLX cleanup from masking model-run failures when headless
  runtimes raise `IndexError` during synchronization.

## [0.7.2] - 2026-05-04

### Fixed

- Stop verbose console output from duplicating per-model generated text by keeping
  the canonical review block in the file log only and suppressing the extra
  post-run text replay when upstream `mlx-vlm.generate(verbose=True)` already
  streamed the response.

## [0.7.1] - 2026-05-04

### Changed

- Replace the diagnostics appendix's old import-only portable triage block with
  portable upstream probes that separate environment sanity checks,
  `mlx_vlm.utils.load()` model/config probing, and synthetic-image reruns
  without requiring the original local image.
- Render issue queue subtypes with human-readable maintainer labels while
  preserving the raw subtype codes for traceability.
- Make generated issue queues and issue drafts use filing-ready problem
  summaries, clearer composite-owner targets, runtime-failure-specific fix
  guidance, and explicit notes that local repro JSON links must be attached or
  published when filing upstream.
- Remove the remaining legacy ANSI color bridge from console logging in favor
  of direct Rich styles, while trimming stale wrapper comments.
- Report upstream prefill / first-token timing as its own derived runtime phase
  so diagnostics distinguish prefill latency from post-prefill decode time.
- Update `make ci` in `src/Makefile` to invoke `run_quality_checks.sh` directly
  for stricter local-to-remote parity with GitHub Actions CI.
- Freeze the `QualityThresholds` configuration dataclass and refactor tests to
  inject overrides via mocking, preventing unsafe global singleton mutations.

### Fixed

- Restore the HTML results table's row filter metadata and numeric alignment
  classes so the built-in filter controls and cell styling work again.
- Repoint the root `make dev` target at the full bootstrap workflow so fresh
  contributors get hook installation and environment validation instead of only
  dependency installation.

## [0.7.0] - 2026-05-03

### Added

- Add a metadata-agreement benchmark score for successful generations, comparing
  generated title/description/keyword fields against trusted image metadata,
  penalizing echoed nonvisual metadata such as date/time/GPS values, and
  emitting the structured score in `results.jsonl` for downstream triage.

### Changed

- Consolidate inline magic numbers (e.g., repetition bounds and truncation counts)
  from output-quality detection heuristics into `quality_config.yaml` and
  `FormattingThresholds` to ensure all thresholds are entirely data-driven.
- Replace per-model generated GitHub issue drafts with root-cause clustered
  issue queues under `output/issues/`, including stable cluster IDs, acceptance
  signals, subtype-specific fix checklists, and JSONL/repro metadata linking
  affected models to their issue cluster.
- Remove priority labels from diagnostics, review, issue, and JSONL triage
  outputs, and route maintainer reports through owner/subtype/action summaries
  instead.
- Exclude harness/avoid models from user-facing best description, best
  keywording, and balanced recommendation picks.
- Share the issue queue table renderer across diagnostics, review, and
  `output/issues/index.md` so maintainer queue columns stay in sync without
  duplicate row-building code.
- Use Rich for console rendering, replacing the custom ANSI log formatter and
  upgrading live summary tables, charts, and EXIF display while keeping
  persisted report artifacts unchanged.
- Reuse the shared Rich table renderer for console statistics, version/system
  summaries, and history comparison output, removing legacy ANSI/table
  normalization paths now handled by Rich.
- Extend Rich to detailed metric trees and replace remaining hand-rolled
  dependency/table parsing with `packaging.Requirement` and `tabulate` where
  practical.
- Trim unused review/utility helper code from `check_models.py` while preserving
  public report schemas and runtime diagnostics.

### Fixed

- Install `packaging>=26.0` in the dependency-sync GitHub Actions job before
  running `tools.update_readme_deps`, so the README/pyproject sync guard no
  longer fails on fresh Ubuntu runners with `ModuleNotFoundError`.
- Align MLX stack integration with current upstream sources by raising the
  project `mlx` floor to `0.31.2`, accepting fractional TurboQuant
  `--kv-bits` values such as `3.5`, and routing generated `mlx-vlm` issue
  links to `Blaizzy/mlx-vlm`.
- Prune stale repro bundles from the canonical `output/repro_bundles/`
  directory after the report layout moved human-readable artifacts under
  `output/reports/`, and refresh maintenance cleanup/check targets that still
  referenced old paths or duplicate checks.
- Promote `mlx-lm` into the core runtime dependency set and have
  `setup_conda_env.sh` install `.[extras,torch]` by default so fresh
  environments include both MLX-LM and the torch-backed model stack used by
  this repo's wider benchmark coverage.
- Render maintainer triage blocks in generated diagnostics and issue markdown as
  actual bullet lists so the sections no longer collapse into a single wrapped
  paragraph.
- Rewrite the per-model review block in `model_gallery.md` with clearer labels
  and human-readable wording so recommendations, token summaries, and owner
  routing are easier to scan.
- Reuse shared compact "at a glance" row builders across diagnostics,
  `review.md`, and generated issue markdown so failure, harness, and next-step
  summaries stay consistent when the human-facing reports are regenerated.
- Compact the generated report first screens and harness issue titles so
  `results.md`, `model_gallery.md`, `review.md`, `diagnostics.md`, and issue
  markdown surface maintainer actions before verbose evidence.
- Preserve mlx-vlm's upstream KV-cache quantization start default, retain root
  exception type/module/message fields in JSONL and issue evidence, and add
  rendered prompt diagnostics plus repro bundles for issue-clustered harness
  anomalies.
- Remove the Rich live progress wrapper around model execution and differential
  reruns so mlx-vlm/tqdm output and Ctrl-C handling are not trapped behind an
  always-live progress display.
- Render the console DEBUG level label in dim gray while preserving the normal
  styling of the debug message body.
- Allow `tools.update_readme_deps` to run before project dependencies are
  installed by falling back to a stdlib parser when `packaging` is unavailable.

## [0.6.0] - 2026-04-26

### Added

- Document the manual version-bump and release workflow in
  `docs/CONTRIBUTING.md`.
- Surface maintainer triage summaries in `diagnostics.md` and generated GitHub
  issue templates so the human-readable artifacts match the richer JSONL
  payloads.
- Sync `check_models.py` with the current mlx-vlm `GenerationResult` shape,
  persist `total_tokens` and `prompt_tps` in JSONL metrics, and expose
  `--kv-quant-scheme` for upstream KV-cache backend selection.

### Changed

- Stop locally backfilling `GenerationResult.peak_memory` from MLX allocator
  probes now that mlx-vlm populates that field directly; keep local timing plus
  active/cache memory snapshots and the per-run peak reset between models.
- Trim preflight diagnostic noise by removing the obsolete Transformers
  TensorFlow/Flax/JAX backend-guard warning path, demoting legacy snapshot-file
  notes for still-working community repos, and refreshing upstream MLX stack
  version floors to match current `mlx-vlm` / `mlx-lm` metadata.

### Fixed

- Keep unknown-tag quality warnings readable in CLI logs by preserving raw tag
  text in analysis output and escaping it only when Markdown/HTML reports are
  rendered.
- Warn exclusions against local Hugging Face cache membership even when
  `--models` is used, so cached-but-unselected models no longer trigger a
  false warning while truly uncached exclusions still do.
- Fix repeated `-e/--exclude` CLI flags to accumulate all exclusions instead of
  silently keeping only the last group, so cache-scan runs honor commands like
  `-e model-a -e model-b`.
- Clarify in CLI help and `src/README.md` that repeated `-e/--exclude` flags
  accumulate, while other list-valued options should be supplied after a single
  flag occurrence.
- Extend the same additive repeated-flag behavior to `-m/--models` and
  `--eos-tokens`, and document that these list-valued options now accumulate
  across repeated occurrences as well.

## [0.5.0] - 2026-04-19

### Added

- Enrich JSONL and history artifacts with shared library-version metadata,
  per-result maintainer triage payloads, and run-over-run quality/harness
  change tracking so smoke-test output is more actionable for MLX and
  transformers maintainers.

### Fixed

- Fix generated GitHub issue and report markdown to pass markdownlint (MD022,
  MD031, MD032, MD036): add blank lines around headings, fenced code blocks,
  and lists; replace bold emphasis with proper `###` subheadings in action
  snapshot.
- Add markdownlint to `--fast` quality checks so the pre-push hook catches
  markdown lint errors before they reach CI.
- Fix harness issue title generator to flatten multiline model output and strip
  trailing punctuation, preventing MD022/MD026 in generated issue templates.
- Escape `*` in repeated-token review text to prevent MD037 (spaces inside
  emphasis markers) when model output contains `*/` sequences.
- Pre-escape HTML tags in quality warning issue text to prevent MD045 (images
  without alt text) when model output contains `<img>` tags.
- Add MD045 to blockquote markdownlint-disable comments since model output can
  contain HTML img tags split across wrapped lines.
- Update the runtime fingerprint GPU-memory probe to use the current MLX
  top-level `get_active_memory()` API instead of the removed `mx.metal`
  accessor.
- Remove duplicated helper logic around generation metric extraction and EXIF
  date/time fallback formatting.

## [0.4.0] - 2026-04-19

### Added

- Added `unknown_runtime_anomaly` verdict for near-empty outputs that pass all
  quality checks but score grade F, signalling unexplained failures that need
  manual triage.
- Added `needs_triage` user bucket for classifier uncertainty, mapped from
  `unknown_runtime_anomaly` verdict. Review reports now render four buckets:
  recommended, caveat, needs_triage, avoid.
- Added `anomaly_min_output_chars` threshold to `quality_config.yaml` (default
  20) controlling the near-empty output threshold for anomaly promotion.
- Added `unknown_runtime_anomaly` to `QUALITY_BREAKING_LABELS` so anomalous
  outputs are excluded from recommendation candidate rows.
- Added property-style invariant tests (`TestClassificationInvariants`) covering
  hint relationship, truncation severity, bucket monotonicity, clean evidence,
  unknown anomaly triage, and history forward-compat invariants (93 new test
  cases).
- Added `TestIssueDirectoryInvariants` verifying issue directory reflects exactly
  the current run output.
- Added `--eval-mode` CLI flag with three evaluation lanes: `stress` (default,
  current behavior), `triage` (short prompt, 200 token cap, pass/fail only),
  and `quality` (cataloguing prompt with generous 1000 token cap).
- Added `--prune-repro-days N` CLI flag to automatically clean up repro bundles
  older than N days (default: 90). Set to 0 to disable.
- Added `Critical` severity tier in diagnostics for error clusters affecting
  ≥5 models, above the existing `High` threshold.
- Added `nonvisual_location_terms` config list in `quality_config.yaml` for
  maintainer-tunable nonvisual metadata terms.
- Added `penalized_echo_ratio` metric to `compute_information_gain()` that
  excludes visual hint term reuse from echo penalties.
- Added `add-or-fix-type-checking` agentic skill
  (`.agents/skills/add-or-fix-type-checking/SKILL.md`) providing a structured
  workflow for diagnosing and fixing typing errors from mypy, ty, and pyrefly.
  Adapted from the Hugging Face transformers skill to this project's three-checker
  pipeline, stub management, and coding conventions.
- Added automatic generation of standalone GitHub issue reports for clustered
  runtime failures and harness issues, placing ready-to-file markdown documents
  in `output/issues/`.
- Added `JsonlSignatureComponents` TypedDict exposing structured error signature
  fields (`error_code`, `normalized_message`, `traceback_signature`) in JSONL
  result records for failed models, enabling precise cross-run clustering without
  re-parsing raw messages.
- Bumped JSONL `format_version` from `"1.4"` to `"2.0"` to reflect the addition
  of `runtime_fingerprint` (metadata) and `signature_components` (results).
- Added round-trip schema tests (`TestSchemaVersioning`) verifying JSONL metadata
  and result records survive JSON serialization with correct format versions.
- Added `collect_runtime_fingerprint()` emitting per-probe `RuntimeProbeResult`
  records (metal_gpu, mlx_framework, mlx_vlm, gpu_memory) into JSONL metadata
  and history records for runtime environment attestation.
- Added `TestRuntimeFingerprint` canary tests (6 cases) verifying fingerprint
  probes, JSONL metadata integration, and history record integration.
- Added `--rerun-triage` CLI flag for automatic differential reruns of
  triage-worthy models (runtime failures and unknown anomalies) with a simple
  prompt. First-pass results are never overwritten (G3). Rerun evidence is
  emitted as `rerun_summary` in JSONL result records.
- Added `RerunEvidence` dataclass and `_select_rerun_candidates()` selection
  logic for identifying models that merit a secondary evidence pass.

### Changed

- Fixed `_classify_hint_relationship` regression: metadata-only trusted hints
  (e.g. GPS, timestamps) no longer mis-trigger `ignores_trusted_hints` when
  there are no visual terms to match against.
- Fixed `_classify_review_verdict` omitting `abrupt_tail` from degradation
  reasons, which caused clearly cut-off outputs to be classified as benign
  `token_cap` instead of `cutoff_degraded`.
- Fixed `_generate_github_issue_reports` not cleaning stale `issue_*.md` files
  before writing new ones, leaving outdated reports from larger previous runs.
- Changed mypy `follow_imports` for mlx_lm/mlx_vlm from `"silent"` to `"normal"`
  so mypy actively type-checks call sites against auto-generated stub signatures.
  transformers/tokenizers remain on `"silent"` to avoid noise from generated stubs.
- `_prune_repro_bundles` now handles `.json` bundle files (not just directories)
  and supports run-count retention via `max_runs` parameter. Empty directories
  are cleaned up automatically.
- Harness issue titles in generated GitHub issue reports now sanitize BPE byte
  artifacts (Ġ, Ċ) into readable text via `_sanitize_bpe_display`.
- TSV report cells are hard-capped at `MAX_TSV_CELL_CHARS` (200) to prevent
  oversized rows from CJK or verbose model output.
- Empty "recommended" user bucket in review.md now includes an explanation
  rather than bare "None.".
- Action Snapshot in results.md restructured from flat bullet list into three
  sub-groups: Failures & Triage, Quality & Metadata, Runtime.
- `finalize_execution` now calls `_clean_stale_toplevel_reports` to remove
  old top-level report files superseded by `output/reports/` copies.
- Fixed issue template writer to emit real newlines instead of literal `\n`
  strings, resolving MD047 lint failures on generated issue files.
- Fixed emphasis style in gallery cross-reference line (asterisks → underscores)
  to match markdownlint MD049 config.
- Updated `src/README.md` CLI reference: added 12 missing flags (`--resize-shape`,
  `--eos-tokens`, `--skip-special-tokens`, `--processor-kwargs`, `--enable-thinking`,
  `--thinking-budget`, `--thinking-start-token`, `--thinking-end-token`,
  `--eval-mode`, `--min-p`, `--top-k`, `--prune-repro-days`), fixed output paths
  from flat `output/` to `output/reports/`, documented `issues/` and
  `repro_bundles/` subdirectories, updated Project Structure tree.
- Updated `src/output/README.md` with directory structure diagram, `reports/`
  hierarchy, and conditional `issues/` and `repro_bundles/` subdirectories.
- Updated `.github/copilot-instructions.md`: refreshed section map line numbers
  (~20,100 lines), key files table sizes, output path descriptions, and all
  common edit recipe line references.

- Inlined `_process_ifd0`, `_coerce_exif_tag_id`, and `_process_gps_ifd` into
  `get_exif_data` — three-pass Pillow EXIF extraction is now direct code in the
  single function, removing ~40 lines of indirection.
- Replaced `_append_markdown_table` and custom Markdown table formatting with
  `tabulate(tablefmt="github")` across all diagnostics and review sections.
- Simplified `_sha256_file` to use `hashlib.file_digest()` (Python 3.11+),
  removing the custom chunked-read loop.
- Inlined `_escape_markdown_in_text`, `_escape_markdown_diagnostics`, and
  `_escape_markdown_gallery_warning` — thin escape-delegate wrappers replaced
  by direct `MARKDOWN_ESCAPER.escape()` / `DIAGNOSTICS_ESCAPER.escape()` calls
  at each call site.
- Split `cutoff` verdict into `token_cap` (benign cap hit, structurally sound
  output) and `cutoff_degraded` (cap hit with quality degradation). Token-capped
  A/B-grade models now reach `recommended` or `caveat` instead of `avoid`.
- Added `runtime_failure` verdict for models that crash (exception, OOM, timeout),
  distinct from `harness` verdict which is reserved for successful runs with
  template/encoding leaks.
- Improved failure clustering with message-only merge pass that collapses
  variants differing only in stack traces (e.g. broadcast_shapes dimensions).
- Reconciled utility grade with user bucket: A/B-grade clean or token-capped
  models can now reach `recommended`; C-or-below capped models go to `caveat`.
- Excluded nonvisual metadata terms from hint overlap ratio denominator so
  models are not penalized for omitting non-verifiable location metadata.
- Removed Action Snapshot duplication from review.md (now cross-references
  results.md).
- Expanded `NONVISUAL_CONTEXT_TERMS` with generic location descriptors (town,
  village, parish, county, borough, district, municipality, province, region).
- Hardened Markdown gallery blockquote rendering so label-only model-output
  lines such as `Description:` and stray lone `-` markers are neutralized
  before markdownlint can misread them as headings.
- Hardened Markdown artifact normalization so trailing BOM and zero-width
  format characters are stripped before write-out, preventing hidden
  `MD009/no-trailing-spaces` failures in generated gallery output.
- Updated workspace file associations so generated `PKG-INFO` package-metadata
  files open as properties instead of Markdown, avoiding editor-only
  markdownlint noise on `.egg-info` metadata.

## [0.3.3] - 2026-04-12

### Changed

- Reduced avoidable MLX teardown overhead after successful model runs by
  keeping the post-decode synchronize needed for accurate timing and memory
  sampling, but no longer forcing a second parameter-evaluation step before
  cleanup and skipping the cleanup-side synchronize when the run has already
  crossed the success-path barrier.
- Updated the Pyrefly quality gate so `make quality` now runs in project mode,
  prints warning-level diagnostics during the check, ships
  `types-defusedxml` in the dev toolchain, and declares `defusedxml` as an
  explicit runtime dependency instead of relying on Pillow's transitive graph.
- Aligned the fast pre-push quality script with the full quality gate so its
  Pyrefly step now also runs in project mode instead of only checking
  `check_models.py`.
- Consolidated the duplicated fast and full quality-script logic so
  `src/tools/check_quality_simple.sh` now delegates to a parameterized
  `src/tools/run_quality_checks.sh --fast` path, reducing drift between the
  pre-push hook and the full local/CI quality gate.
- Made image-metadata evaluation more decision-ready by adding separate
  description and keyword quality scorecards, surfacing those scores in the
  cataloging logs and recommendation summaries, and highlighting the best
  models for end-to-end cataloging, description quality, and keywording
  instead of relying on a single blended utility rank alone.
- Replaced the last direct `requests` and `tzlocal` runtime usage with stdlib
  `urllib` and local-time conversion via `datetime.astimezone()`, trimming the
  runtime dependency surface while preserving URL EXIF extraction and localized
  timestamp behavior.
- Hardened the `compute_task_compliance` metrics to strictly enforce the exact
  prompt constraints. Instead of awarding points merely for implicit or fuzzy section presence,
  the tool now parses output into explicit sections and awards passing compliance scores only
  when the model's word counts, sentence lengths, and keyword counts meet the respective
  bounds defined in `quality_config.yaml`.
- Hardened the MLX stack compatibility policy and diagnostics by centralizing
  shared version floors, raising the validated `mlx-vlm`, `mlx-lm`,
  `transformers`, and `huggingface-hub` minimums, switching runtime version
  comparisons to PEP 440 semantics, and adding always-on preflight checks for
  the exact `mlx_vlm` call surfaces and `GenerationResult` fields used by
  `src/check_models.py`.
- Tightened the local maintenance workflow so `src/tools/generate_stubs.py`
  now exposes a strict `--check` mode, fails loudly when required
  `mlx_vlm`/`transformers` stub patches drift, `src/tools/run_quality_checks.sh`
  treats stub-integrity failures as blocking, and `src/tools/update.sh` logs
  local editable MLX repo provenance before verifying checked-in stubs.
- Expanded the repo-level recommended VS Code extensions in
  `.vscode/extensions.json` to include YAML, GitHub Actions, and ShellCheck
  support, matching the checked-in workflow YAML, shell quality gates, and
  pre-push tooling used by this project.
- Removed the Jupyter VS Code extension from the repo-level recommended
  extension list in `.vscode/extensions.json`, keeping the workspace defaults
  focused on the Python CLI and quality-tooling workflow used in this project.
- Added an explicit `Generated Text:` label to the non-verbose per-model preview
  path in `src/check_models.py`, so emitted model output is clearly identified
  even when the run stays in compact summary mode.
- Replaced the hardcoded Pyrefly `conda-environment` setting with shared
  quality-script injection of `python-interpreter-path`, so local checks still
  target the resolved repo Python while GitHub Actions no longer fails the
  Pyrefly step on runners without `conda`.
- Clarified CLI help and README wording for `--folder`, `--image`, and `--prompt`
  so omitted flags describe their fallback behavior without implying the flags
  themselves accept empty values.
- Removed stale static-analysis downgrades in `src/pyproject.toml` by dropping
  unused Ruff tool-file `D`/`ANN` ignores, the unused Ty
  `unresolved-import=warn` downgrade, and a Pyrefly `ignore-missing-imports`
  list; Pyrefly now resolves imports against the `mlx-vlm` conda environment
  directly instead of masking system-interpreter drift.
- Made the packaged `quality_config.yaml` the single canonical default source,
  taught `load_quality_config()` to read the bundled resource by default, and
  added wheel-content plus anti-duplication regression tests so future
  packaging changes cannot silently drop or reintroduce split runtime-default
  copies.
- Reworked the automated review payload and `src/output/review.md` generation to
  carry concrete prompt/output evidence, show `review.md` as a user-first digest
  with review priorities and compact bucket tables, and replace the most
  repetitive owner-level next-action prose with evidence-aware guidance.
- Tightened several noisy quality heuristics in
  `src/check_models_data/quality_config.yaml` by
  requiring stronger evidence for repetition, context ignorance, context echo,
  genericity, and verbosity before flagging outputs, while keeping harness and
  contract failures visible in maintainer-facing diagnostics.
- Added Vulture to the managed `dev` dependency set, wired it into the full
  and fast quality scripts plus `make quality` / `make vulture`, and added a
  checked-in VS Code task/problem matcher so dead-code findings can surface as
  Problems warnings before commit-time checks. Expanded the checked-in Vulture
  scope to cover the Python utilities under `src/tools/` as well, while still
  excluding the archived tool stash. Tightened the task matcher to only catch
  real Vulture diagnostics with confidence suffixes, avoiding bogus Problems
  entries from unrelated `file:line:` output emitted by other quality steps,
  and limited Problems publishing to the dedicated `Make: vulture` task so the
  broader mixed-output quality task no longer leaves stale warnings behind.
  Aligned the `make vulture` and quality-script invocations with the checked-in
  `[tool.vulture]` config as well, so the broadened `src/tools/` scan actually
  runs instead of being overridden by an old explicit `check_models.py` path.
- Bumped the repo-local `markdownlint-cli2` npm tooling in `src/package.json`
  and `src/package-lock.json` to `0.22.0`, and changed `src/tools/update.sh`
  to refresh that tool from npm's `latest` tag on each update run so Markdown
  lint tooling stays current automatically. Added an npm override for
  `smol-toml@1.6.1` as well, so the current latest `markdownlint-cli2`
  dependency tree is patched against the published moderate-severity TOML
  parser DoS advisory without downgrading the linter.
- Made protocol method bodies in `src/check_models.py` explicit stub
  implementations (`...`) instead of docstring-only placeholders so Pylance and
  other control-flow checkers no longer misread those type-only call surfaces
  as returning `None`.
- Added `pydantic` to the managed `dev` dependency group in
  `src/pyproject.toml` and aligned the `src/tools/setup_conda_env.sh`
  fallback installer so repo update/bootstrap flows keep it current through the
  existing dependency-management path.
- Tightened external-library typing in `src/check_models.py` by giving the
  imported `mlx_vlm` callables explicit local protocol signatures, narrowing
  loaded processor/config annotations toward `transformers` types, extending
  generation-result protocols with upstream throughput fields, and replacing
  broad kwargs bags with typed helper shapes while keeping missing third-party
  stubs as soft warnings via best-effort local stub refreshes in
  `src/tools/run_quality_checks.sh`.
- Tightened several remaining metadata and EXIF typing surfaces in
  `src/check_models.py` by replacing broad `dict[str, Any]` helper returns
  with explicit IPTC/XMP typed shapes, narrowing Pillow tag lookups, and
  adding small protocol-based annotations around EXIF and GPS helper usage.
- Tightened additional low-risk helper typing in `src/check_models.py` by
  validating quality-config sections as string-keyed mappings and normalizing
  macOS `system_profiler` JSON into typed helper shapes before GPU/tooling
  extraction.
- Removed redundant config and hardware-probe logic in `src/check_models.py`
  by centralizing string-keyed mapping validation and reusing a cached
  `get_device_info()` path for both generic GPU info and Apple Silicon details.
- Removed a few dead or single-use wrapper helpers in `src/check_models.py`
  by deleting unused display helpers and inlining thin markdown/probe wrappers
  that only obscured one call site each.
- Further shortened `src/check_models.py` by inlining single-use prompt,
  runtime-formatting, chat-kwargs, and traceback-cleanup helpers in place
  where the surrounding call site was clearer than the extra wrapper.
- Fixed Ty invocation in `src/tools/run_quality_checks.sh` and
  `src/tools/check_quality_simple.sh` to pass the resolved repo Python
  explicitly, eliminating false `unresolved-import` warnings when Ty fell back
  to the wrong Conda site-packages instead of the `mlx-vlm` environment.
- Added a dedicated `make ty` / `src/tools/run_ty_check.sh` path plus
  explicit Ty environment diagnostics so local runs report the target conda
  env, active env, resolved Python, resolved Ty binary, and any fallback use
  instead of silently relying on ambiguous environment auto-detection.
- Removed several dead or redundant helper layers in `src/check_models.py`,
  including unused diagnostics/runtime helpers, now-unused protocol
  definitions, a duplicate quality-analysis accessor, and a few thin
  report/context wrappers, to shrink the monolith without changing report
  behavior.
- Compacted harness/review ownership routing in `src/check_models.py` by
  centralizing repeated owner maps and composite next-action rules, removing
  unused review-owner inputs, and collapsing one verbose quality-signal
  summary ladder into table-driven logic without loosening diagnostics or type
  checking.
- Redirected the E2E smoke test helper in `src/tests/test_e2e_smoke.py` to
  send standalone gallery and review artifacts to the test temp output
  directory as well, so `make quality` no longer rewrites tracked
  `src/output/model_gallery.md` and `src/output/review.md` during pytest runs.
- Hardened `src/tools/update.sh` so local MLX refreshes now fail fast when the
  active macOS toolchain does not expose `metal` and `metallib` via `xcrun`,
  and so editable-install origin checks cover `mlx` in addition to `mlx-lm`
  and `mlx-vlm`.
- Switched the local `mlx` editable install path in `src/tools/update.sh` to
  invoke `pip install -v -e .` so MLX builds emit full pip build logs during
  updates.
- Improved canonical review and diagnostics wording for `huggingface-hub`
  model-load failures so transient Hub disconnects are attributed to cache /
  network / Hub availability issues instead of falling through to a generic
  `model` owner diagnosis.
- Raised the declared `huggingface-hub` runtime floor to `>=1.8.0` in the
  project metadata, environment validator, and synced install docs so the repo
  matches the current active MLX environment and no longer advertises the old
  pre-1.0 Hub client baseline.

## [0.3.2] - 2026-03-27

### Changed

- Escaped inline emphasis markers in model-gallery quality warning bullets so
  arbitrary model output like `*/` sequences no longer trips markdownlint
  `MD049` in `src/output/model_gallery.md` after report generation.
- Stripped trailing non-breaking spaces from wrapped Markdown blockquotes and
  broadened trailing-whitespace normalization so generated gallery output no
  longer trips markdownlint `MD009` on model lines that end with `U+00A0`.
- Escaped square-bracket syntax in wrapped Markdown blockquote output so raw
  model text such as Python indexing expressions no longer trips markdownlint
  `MD052` in generated review artifacts under `src/output/`.
- Narrowed Markdown generator suppressions by wrapping more formatter-owned
  prose to the configured width, switching generator-emitted labels from `**`
  to repo-preferred underscore emphasis, and updating the manual failures table
  to spaced pipe separators so generated reports rely less on `MD013`, `MD049`,
  and `MD060` disables.
- Refreshed the MLX stack compatibility policy to track current upstream stable
  releases more closely: `mlx>=0.31.1`, `mlx-vlm>=0.4.1`, `mlx-lm>=0.31.1`,
  and `transformers>=5.4.0`, and aligned preflight diagnostics and fallback
  environment validation tables with current upstream minimum requirements.
- Dropped TensorFlow from packaged optional dependencies, since `check_models`
  does not import it directly, and added `timm` to the `torch` extra so
  FastVLM-style remote-code models install their required vision backbone.
- Updated `src/tools/update.sh` to keep Markdown lint tooling repo-local via
  `npm install --prefix src` instead of globally mutating npm packages, while
  preserving the default MLX build path with `MLX_METAL_JIT` unset/off unless
  a user explicitly opts in.
- Tightened the staged Markdown pre-commit hook so committed report artifacts
  under `src/output/` are no longer excluded from markdownlint fixing, which
  lets commit-time hygiene catch lint regressions in generated Markdown such as
  `review.md` before CI does.
- Made `check_models.log` the canonical full-fidelity run artifact by adding a
  fixed per-model review block with verdict, trusted-hint handling, contract
  and utility summaries, ownership hints, token accounting, next actions, and
  full generated or captured failure output even when console logging stays
  concise.
- Reworked trusted-hint quality analysis so only prompt title/description/
  keyword hints are treated as reusable draft content, while capture metadata,
  GPS, timestamps, source labels, and explicit location labels are stripped out
  of hint-usage scoring and can instead be flagged separately as nonvisual
  metadata borrowing.
- Added ordered automated review verdicts (`clean`, `harness`, `cutoff`,
  `context_budget`, `model_shortcoming`), surfaced them in `results.jsonl`
  review payloads and the new `output/review.md` digest, and wired the same
  review data into gallery/report output so users and maintainers see one
  consistent judgment across artifacts.
- Tightened MLX runtime metric capture so compact logging now reads the
  stored `cache_memory` field consistently, and generation results backfill
  peak memory from `mx.get_peak_memory()` when upstream results omit it.
- Added a narrow one-shot retry for known upstream `mlx-vlm` BPE streaming
  detokenizer UTF-8 decode failures, temporarily switching the retry attempt
  to lossy byte flushing so intermittent `UnicodeDecodeError` crashes can be
  worked around locally while the upstream bug is fixed.
- Added first-token latency capture to runtime diagnostics by deriving it from
  upstream `mlx_vlm.generate` prompt-throughput metrics, and preserved that
  signal through final result finalization so reports and compact logs can show
  real latency data instead of an always-empty field.
- Exposed upstream `mlx_vlm.generate` sampling controls for `min_p` and `top_k`
  through CLI validation, repro-command generation, and runtime parameter
  forwarding, and corrected the local `mlx_vlm` stub so `stream_generate()` is
  typed as yielding `GenerationResult` objects instead of plain strings.
- Hardened quality-analysis propagation in `src/check_models.py` so successful
  runs cache structured quality results at result-construction time, report
  generation backfills missing quality analysis for synthetic success rows, and
  failed runs can retain quality flags from captured stdout instead of dropping
  those signals on exception paths.
- Tightened `quality_config.yaml` loading so invalid threshold bounds or
  malformed detector regex patterns fail closed with a warning instead of
  silently weakening output-quality checks.
- Tightened diagnostics snapshot generation so Markdown diagnostics backfill
  missing success-side quality analysis before harness/stack classification,
  preventing clean or unflagged buckets from hiding reportable issues when the
  report is built from minimally populated `PerformanceResult` rows.
- Marked prompt-less cached quality analysis as incomplete and refreshed it
  when the original prompt becomes available again, so report rendering and
  diagnostics do not label those runs as fully clean while context-sensitive
  checks remain unavailable.
- Expanded long-context stack-signal heuristics so successful runs with extreme
  prompt lengths can also be surfaced for context-echo and degeneration
  symptoms, instead of only empty-output and low-ratio cases.
- Tightened diagnostics owner attribution so stack-signal anomalies can reuse
  matching preflight compatibility hints and point at narrower likely owners
  such as `transformers / mlx-vlm` instead of always collapsing into the broad
  `mlx-vlm / mlx` bucket.
- Tightened failed-run package attribution so chained tracebacks now prefer the
  deeper upstream owner, avoiding `mlx-vlm` wrapper attribution when the root
  failure actually comes from packages such as `transformers`.
- Tightened harness diagnostics owner attribution so prompt-template successes
  no longer collapse into generic runtime ownership, and maintainer summaries
  now distinguish model-config style harness issues from long-context runtime
  anomalies.
- Tightened harness maintainer triage so mixed harness-owner runs now render as
  separate action-summary and priority-table rows instead of collapsing config
  and runtime signals into one generic maintainer bucket.
- Tightened diagnostics maintainer triage so mixed stack-signal and preflight
  owner classes also render as separate action-summary and priority-table rows,
  instead of collapsing upstream compatibility and runtime issues into one
  merged owner bucket.
- Tightened the CLI maintainer summary so mixed harness, stack-signal, and
  preflight owner classes are logged as separate owner-specific lines with next
  actions, instead of collapsing them into one broad summary sentence.
- Tightened the detailed preflight diagnostics section so mixed owner classes
  render as separate owner buckets with owner-specific trackers and next
  actions, instead of one flat mixed warning list.
- Added an env-aware `make analyze-quality` workflow plus a standalone
  `tools.analyze_output_quality` CLI so quality and harness heuristics can be
  exercised directly against arbitrary text or saved outputs without running a
  model.
- Tightened `tools.analyze_output_quality` argument validation so conflicting
  `--prompt` and `--prompt-file` sources now fail fast instead of silently
  allowing ambiguous prompt context.
- Added a machine-readable `--json` mode to `tools.analyze_output_quality` so
  quality-analysis results can be consumed directly by scripts and triage
  tooling without scraping the human report output.
- Tightened clean-machine environment setup so the bootstrap script now prints
  repo-root-safe usage commands, probes common Miniforge/Mambaforge conda
  locations, and `tools.validate_env` no longer falsely rejects custom active
  conda env names unless strict matching is explicitly requested.
- Tightened report-generation typing in `src/check_models.py` by replacing broad
  `getattr`/cast access in gallery helpers with narrower protocol-based checks
  for throughput and cached quality-analysis fields.
- Optimized model generation prefill time by changing the default
  `--prefill-step-size` from `None` (which deferred to mlx-lm's conservative 512
  token default) to `4096`, significantly speeding up context evaluation on Mac
  GPUs for long prompts.
- Realigned contributor and user-facing documentation so the root README,
  `src/README.md`, and workflow docs consistently describe the standalone
  `model_gallery.md` artifact, the recommended conda bootstrap path, and the
  current split quality/runtime CI behavior.
- Made the repo-root `Makefile` delegate to the env-aware `src/Makefile` so
  common install/test/format/typecheck commands respect the intended Python
  environment instead of invoking bare `python`/`pip`/tool binaries.
- Expanded markdown quality coverage to include committed Markdown under
  `src/output/`, and updated bot guidance files so `MetricValue`, report
  artifact lists, and `make quality` expectations match the current codebase.
- Hardened local git-hook environment bootstrap so pre-commit and pre-push can
  locate and activate the intended conda env even when git launches hooks
  without `conda` on `PATH`, and YAML validation failures now print an explicit
  PyYAML/environment setup hint instead of a raw traceback.
- Made `tools/setup_conda_env.sh` install the repo's custom git hooks whenever
  development dependencies are selected, and updated contributor docs to treat
  that env-aware hook installer as the default local workflow.
- Extended `tools/setup_conda_env.sh` so dev setup also installs the repo-local
  `markdownlint-cli2` dependency when `npm` is available, and now warns
  explicitly when Node.js tooling is still missing for staged Markdown hooks.
- Hardened pre-push and full quality scripts so env-installed tools such as
  `ty` and `pyrefly` are resolved from the selected Python environment instead
  of relying on shell `PATH`, avoiding false "command not found" failures when
  git launches hooks from a reduced environment.
- Tightened clean-machine bootstrap so `tools/setup_conda_env.sh` now installs
  `cmake` from `conda-forge` explicitly and falls back to `pip` if needed,
  instead of assuming the user's existing conda channel configuration exposes a
  usable `cmake` package for the target platform.
- Narrowed the preflight `transformers` backend-guard warning so it now refers
  specifically to the TF/FLAX/JAX guard env vars used by `check_models`, rather
  than implying that all upstream `USE_*` backend toggles disappeared.
- Documented preflight compatibility warnings in `src/README.md` and tightened
  the shared HTML/Markdown action snapshot plus diagnostics report wording so
  those warnings are clearly framed as informational by default, with explicit
  guidance on when users should and should not escalate them.

## [0.3.1] - 2026-03-14

### Added

- Added a standalone GitHub-compatible Markdown gallery artifact for model-output
  review, with populated image metadata, the full prompt, and one easy-to-scan
  section per model output.

### Changed

- Made the human-facing report artifacts more actionable and consistent by
  reusing shared triage/rendering helpers for HTML, Markdown, and the standalone
  gallery, adding maintainer-oriented failure ownership summaries plus reviewer
  shortlists and per-model assessment cues.
- Reduced internal redundancy in `src/check_models.py` by merging HTML and Markdown
  cataloging summary rendering paths into a single `_format_cataloging_summary` function.
- Added lazily-evaluated `.successful` and `.failed` cached properties to `ResultSet`
  to optimize repeat list comprehensions during report generation.
- Cleaned up the quality-analysis detector subsystem in `src/check_models.py`
  by reusing the shared configured-pattern lookup path across more detectors,
  tightening non-trivial local annotations, and centralizing repeated
  context-stopword filtering used by prompt-context analysis.
- Expanded `src/tools/check_suppressions.py` into a stricter repo-wide
  suppression audit and wired it into the fast/full quality scripts so stale
  `noqa`, `type: ignore[...]`, and `shellcheck disable=` comments are flagged
  automatically.

- Narrowed legacy Transformers backend guard exports so `check_models` now sets
  only `TRANSFORMERS_NO_*` / `USE_*` variables still referenced by the
  installed `transformers` version, instead of exporting the full legacy set
  unconditionally.
- Tightened the default cataloguing prompt again to separate section labels from
  instruction text, reducing the chance that weaker models copy prompt
  instructions into the generated `Title:` field.
- Made captured timing data easier to see in default outputs by adding compact
  per-model runtime hints to `check_models.log` and a short aggregate timing
  snapshot to the Markdown/HTML/diagnostics report summaries.
- Clarified `--detailed-metrics` behavior in CLI/docs and now warn when it is
  provided without `--verbose`, since that combination otherwise falls back to
  compact output.

## [0.3.0] - 2026-03-07

- Hardened local hook and CI quality workflows:
  - split shared gates into commit hygiene, pre-push fast checks, full static
    quality, and separate runtime smoke probing;
  - removed tool-install side effects from quality enforcement scripts and made
    the full quality gate non-mutating;
  - aligned the checked-in `pre-commit` config, custom git-hook installer,
    workflow docs, and environment validation around the same commit/push
    behavior;
  - simplified ancillary Node tooling around `npm install`, moved dependency-sync
    CI to Ubuntu with path filters, and split GitHub Actions into
    `static-quality` and `runtime-smoke` jobs;
  - ensured the static-quality path creates a repo-root `typings/` directory so
    `ty` can consume the configured extra search path on fresh CI checkouts;
  - aligned active contributor/implementation documentation with the split
    commit/push hooks, static-vs-runtime CI separation, stub preflight, and
    current markdownlint enforcement behavior.
- Expanded verbose CLI detailed metrics output to include additional runtime
  phase timings (`input_validation`, `prompt_prep`, `cleanup`,
  `first_token_latency`) plus `stop_reason` when that metadata is available.

- Reduced redundant internal formatting and diagnostics code in `src/check_models.py`:
  - inlined a few single-use helpers in import-probe, diagnostics, and failure-capture paths;
  - centralized numeric-string coercion used by field formatting and numeric stats aggregation;
  - deduplicated the shared EXIF datetime parsing path while preserving existing helper behavior.

- Began expanding `src/check_models.py` generation parity with upstream `mlx_vlm.generate`:
  - added CLI/runtime support for `resize_shape`, `eos_tokens`, `skip_special_tokens`, and JSON `processor_kwargs` passthrough;
  - added opt-in thinking-mode support via `enable_thinking`, `thinking_budget`, `thinking_start_token`, and `thinking_end_token`;
  - normalizes these values centrally during CLI validation so model runs receive consistent typed kwargs.

- Refactored `diagnostics.md` output structure for improved issue triage utility:
  - merged 'Potential Stack Issues' into a sub-section of 'Harness/Integration
    Issues' to reduce redundancy;
  - replaced the generic attachment guidance for JSON repro bundles with explicit
    direct GitHub repository links to the `output/repro_bundles/` directory.
- Tightened default cataloging prompt generation in `src/check_models.py`:
  - now requires strict three-section output with explicit anti-CoT and
    anti-verbatim-copy rules;
  - keeps `Context:` metadata hints concise and tagged as high-confidence
    hints rather than instruction text.
- Revised the default cataloging prompt toward non-speculative, visibility-only
  output:
  - metadata hints are now framed as a draft record to verify against the
    image, not a source to elaborate from;
  - prompt wording now explicitly prefers omission over guessing and forbids
    inferred identity/location/event/brand/species/time-period details unless
    visually obvious;
  - title/keyword quality thresholds now align with the stricter prompt
    contract (`Title: 5-10 words`, `Keywords: 10-18 terms`).
- Strengthened output-quality heuristics for prompt-contract enforcement:
  - added explicit flags for missing sections, title length, description
    sentence count, keyword count, and keyword-duplication violations;
  - added reasoning/prompt-echo leakage detection and context-regurgitation
    (`context-echo`) detection;
  - improved context-ignorance matching with alias support (for example
    `UK` vs `United Kingdom`) and filtering of non-semantic prompt-label terms.
- Improved quality-issue serialization robustness: JSONL list conversion now
  preserves single issue items that contain commas inside parenthesized detail
  payloads (for example repetitive phrase previews).
-- Polished generated report outputs for faster maintainer triage without
  changing core runtime behavior:
  - added a compact `Action Summary` near the top of `diagnostics.md` with
    explicit owner labels and next actions;
  - expanded diagnostics reproducibility guidance to include both exact rerun
    commands and portable dependency/import probes that do not require local
    image assets (now centralized in a single portable triage section instead
    of repeated per failure cluster);
  - added a concise `Action Snapshot` near the top of `results.md` to separate
    framework/runtime failures from low-utility model watchlist signals.
- Updated local MLX build integration in `src/tools/update.sh` to support
  explicit `MLX_METAL_JIT` pass-through via `-DMLX_METAL_JIT=<ON|OFF>` when
  requested, while leaving MLX's default behavior untouched when unset; also
  refreshed docs that previously referenced the older
  `MLX_BUILD_METAL_KERNELS` mapping.
- Hardened local-build detection in `src/tools/update.sh` for `mlx-lm` and
  `mlx-vlm`:
  - verifies editable install origin paths against local repo paths after local
    rebuilds (instead of relying on version strings);
  - preserves editable installs when deciding whether to skip PyPI MLX
    ecosystem upgrades, even when package versions look like release versions.
- Expanded local stub generation defaults to include `transformers` alongside
  `mlx_lm`, `mlx_vlm`, and `tokenizers` (`tools/generate_stubs.py`,
  `tools/update.sh`, and README command docs).
- Tightened type-checker stub integration:
  - mypy now prefers following generated stubs for `mlx_lm`, `mlx_vlm`,
    `transformers`, and `tokenizers` (`follow_imports = "silent"` override);
  - quality checks now emit explicit warnings when expected stub packages are
    missing or contain invalid syntax.
- Reduced upstream stubgen noise during `transformers` stub generation:
  known non-actionable `auto_docstring` diagnostics are now suppressed and
  replaced with a concise suppression count, while actionable/non-zero-exit
  stubgen output is still surfaced.
- Improved failed-model summary lines in `check_models.log` to include decoded
  maintainer hints (`owner≈... | component=... | likely=...`) plus a compact
  normalized symptom excerpt, making canonical error codes actionable without
  consulting internal token mappings.
- Tightened local type-check tooling integration:
  - `ty` now searches repo-local generated stubs via
    `tool.ty.environment.extra-paths`, which resolves `mlx_vlm.*`
    submodules during `ty check`;
  - `src/tools/run_quality_checks.sh` now calls stub generation in a
    skip-if-fresh mode backed by a `typings/.stub_manifest.json` cache, so
    stubs are regenerated only when installed package versions change or the
    cache is missing.
- Compressed `src/check_models.py` with low-risk internal cleanup:
  - removed stale private dead code and one unused lint-suppression path;
  - merged duplicated HTML/Markdown issue-summary rendering around shared
    summary collectors and aggregate-stat rows;
  - standardized diagnostics section assembly around the existing Markdown
    section helpers to reduce repeated divider/heading boilerplate.
- Raised the project Transformers floor to `>=5.2.0` and aligned packaging,
  runtime checks, and docs/tests to that policy.
- Aligned preflight package-floor diagnostics in `src/check_models.py` with
  current upstream dependency declarations from `mlx-vlm` and `mlx-lm`
  repositories (instead of stricter ad-hoc floors), reducing false-positive
  compatibility warnings.
- Updated backend-guard behavior for Transformers integration: when
  `MLX_VLM_ALLOW_TF` is not set, `check_models.py` now applies both legacy
  `TRANSFORMERS_NO_*` and compatibility `USE_*` env guards, and diagnostics now
  explicitly report when newer Transformers versions ignore both families.
- Updated `src/tools/update.sh` so local MLX builds apply `MLX_METAL_JIT`
  through MLX's current CMake build flag
  (`CMAKE_ARGS=-DMLX_METAL_JIT=<ON|OFF>`), ensuring the selected
  kernel mode is honored during `pip install -e .`.
- Audited inline comments in `src/check_models.py` and removed stale
  refactor-history notes that no longer describe current behavior, while
  keeping explanatory comments for runtime/error-handling decisions.
- Updated maintainer map in `.github/copilot-instructions.md` to reflect the
  current monolith/test sizes and refreshed function line anchors.
- Normalized `src/README.md` command examples to use
  `python -m check_models`, matching the documented package entrypoint.
- Further compressed `src/check_models.py` (about 200 lines) by deduplicating
  EXIF date/time extraction paths, centralizing special-token leak pattern
  tables, and trimming verbose internal docstrings while preserving behavior.
- Diagnostics report generation now emits clearer issue-facing sections:
  `To reproduce` uses a single repro bullet, model output is shown inline when
  available, and technical traceback/captured logs are grouped in one
  collapsible `Detailed trace logs` section.
- Diagnostics report layout now surfaces `Priority Summary` near the top for
  faster triage, while moving the full `Environment` table near the bottom
  (just before reproducibility details).
- Terminal alignment now manages Unicode display width via `wcwidth` with
  safe fallback behavior, improving centered headers and metric-label padding
  when wide glyphs/emoji appear in output.
- Tightened model-generation typing in `src/check_models.py` by reducing
  ambiguous `Any` usage in `_load_model` / `_run_model_generation` where
  upstream function signatures allow safe narrowing.
- Terminal `Model Comparison (current run)` table now explicitly right-aligns
  numeric columns (TPS/timing/memory) and left-aligns text columns for easier
  visual scanning.
- Improved dependency-management tooling:
  - `src/tools/check_outdated.py` now uses JSON output with timeout/network-aware
    handling, and groups results into pyproject-managed vs unmanaged packages.
  - `src/tools/validate_env.py` now parses dependency specs robustly (including
    extras syntax) and validates installed versions against declared constraints.
- Stub generation now targets a broader default set (`mlx-lm`, `mlx-vlm`,
  `tokenizers`) and the quality gate runs a stub preflight before type checks.
- CI MLX core stubs are now written to repo-local `typings/` instead of
  mutating `site-packages`, improving reproducibility across runs.
- Refactored diagnostics/reporting internals for readability and lower
  duplication without intended behavioral changes:
  - removed single-use diagnostics wrappers and unused model cleanup state;
  - deduplicated diagnostics list + traceback normalization paths;
  - centralized diagnostics prose mappings;
  - simplified repro command assembly.
- Simplified diagnostics failure-cluster filing guidance so it only includes
  the repro command bullet; full traceback/captured-output diagnostics remain
  available in the existing collapsible sections.
- Aligned runtime-dependency preflight behavior between CLI and diagnostics:
  when core runtime packages are unavailable, the CLI now logs a structured
  environment-failure message and writes a minimal `diagnostics.md` focused on
  the missing dependencies and environment fingerprint instead of per-model
  failures.
- Centralized diagnostics configuration (history depth, snippet lengths,
  traceback tail lines, and cluster thresholds) into a single
  `DiagnosticsConfig` struct near the diagnostics helpers to make future tuning
  easier.
- Added concise one-line micro-summaries at the top of the Harness/Integration
  Issues and Long-Context/Stack Issues sections in `diagnostics.md` to improve
  scanability in large reports.
- Updated the `Models Not Flagged` diagnostics subsection for successful models
  with non-fatal quality issues:
  - renamed the warnings bucket to `Ran, but with quality warnings`;
  - added a per-model one-line warning summary derived from already captured
    quality-analysis signals.
- Added diagnostics completeness/runtime verification near the report footer:
  - explicit `Coverage & Runtime Metrics` section validates that each model run
    appears exactly once across detailed vs summary diagnostics buckets;
  - added aggregate runtime metrics (total model-runtime sum and average per
    model), with a clear fallback note when per-model timing fields are
    missing.
- Optimized hot paths in `src/check_models.py`:
  - Hugging Face cache scans are now reused via a per-run cache helper.
  - Quality analysis is reused when `PerformanceResult.quality_analysis`
    already exists, avoiding repeated `analyze_generation_text()` calls.
  - Diagnostics generation now computes failure clusters once and reuses them
    across sections.

### Fixed

- Fixed Markdown report generation so `results.md` avoids markdownlint
  violations from prompt/error rendering:
  - prompt output now uses a plain fenced code block (not blockquote-wrapped)
    to prevent `MD028/no-blanks-blockquote` when prompt text contains blank
    lines;
  - gallery error prose now escapes emphasis markers in non-URL segments so
    identifiers like `LanguageModel.__call__()` do not trigger
    `MD050/strong-style`.

- Replaced a brittle type-only dependency on internal Transformers module
  `transformers.tokenization_python.PythonBackend` with a stable `Any` cast at
  the mlx-vlm call boundary, avoiding reliance on non-public import paths.
- Fixed `src/Makefile` `ci` target to use available commands (ruff + mypy +
  dependency sync check) instead of referencing removed tooling.
- Added `--check` mode to `src/tools/update_readme_deps.py` so CI/developers can
  verify README dependency block sync without rewriting files.
- Fixed noisy accidental pasted output in `src/tools/update.sh` banner section.
- `tools.validate_env` now treats the known `pip check` Torch
  "not supported on this platform" message as a warning (non-fatal), while still
  failing on real dependency inconsistencies.
- Fixed `_load_model` return typing to align with runtime processor type,
  eliminating `ty` `invalid-return-type` failures in CI/local quality checks.
- Improved diagnostics issue-report readability/safety by using clearer prose and
  escaping token-leak snippets for Markdown/HTML-safe rendering.
- Stabilized terminal summary-table alignment by sanitizing non-ASCII note
  glyphs (for example warning emoji) in the model comparison table output.

## [0.2.0] - 2026-02-15

### Added

- New preflight package-risk diagnostics in `check_models.py` to surface common
  upstream compatibility issues early (MLX/MLX-VLM/MLX-LM/Transformers version
  mismatches and known problematic package states).
- End-of-run model comparison summary in `check_models.log` now includes a
  compact per-model table plus ASCII charts (TPS, overall efficiency, failure
  stage frequency) to make same-run model triage faster.
- History comparison output now includes run-over-run tabular deltas and
  transition-oriented ASCII charts to highlight regressions/recoveries/new or
  missing models across successive runs.
- Additional diagnostics stack-signal and long-context-breakdown analysis
  sections to better triage quality and failure patterns.
- Phase-aware failure attribution in model execution (`import`, `model_load`,
  `tokenizer_load`, `processor_load`, `model_preflight`, `prefill`, `decode`)
  so reports can identify the first failing runtime stage.
- Canonical failure metadata for each failed model:
  machine-readable `error_code` plus stable `error_signature` for clustering
  related failures across models/runs.
- Per-failure reproducibility bundle export (`output/repro_bundles/*.json`)
  with args, environment fingerprint, prompt/image hashes, traceback, captured
  output, and exact rerun command.
- Diagnostics report now emits copy/paste-ready issue templates per failure
  cluster, including canonical signature, minimal repro command, environment
  fingerprint, and likely upstream issue tracker.
- Model preflight validators for tokenizer/processor/config/snapshot layout to
  detect packaging and compatibility defects before generation begins.

### Changed

- Hardened runtime dependency handling for core MLX stack:
  `mlx`, `mlx-vlm`, and `mlx-lm` are now treated as required for model execution.
- Added explicit early package/runtime preflight in
  `src/tools/run_quality_checks.sh` to fail fast when required runtime deps are
  missing or broken.
- Updated CLI execution flow so argument/path validation and `--dry-run`
  behavior are evaluated before runtime dependency hard-fail, while still
  enforcing a hard stop before any model inference starts.
- Improved type-checking signal quality without globally hiding import/stub
  issues:
  - `pyright` missing import/stub diagnostics now emit warnings.
  - `mypy` uses targeted third-party overrides instead of global
    `ignore_missing_imports`.
  - `pyrefly` no longer uses wildcard missing-import ignore.
  - `ty` unresolved-import is now warning-level (visible, non-blocking).
- Strengthened E2E runtime gating to require usable `mlx` + `mlx-vlm` +
  `mlx-lm` for inference smoke tests.
- Improved CI MLX stub-generation step robustness to tolerate missing/generated
  stub-path variance as a non-fatal warning (typing-accuracy degradation only).
- Improved prompt-context compaction and keyword-hint summarization for long
  metadata inputs to reduce prompt bloat while preserving useful grounding.
- Improved diagnostics report reproducibility command construction and captured
  output sanitization for cleaner issue filing.
- Diagnostics reports now include preflight compatibility warnings in
  `diagnostics.md` (with likely package ownership and suggested issue trackers),
  and surface those warnings in the priority summary.
- Refactored portions of `check_models.py` for readability/maintainability
  without intended behavioral change.
- Tightened report/summary typing with explicit TypedDict/type-alias structures
  for model issue summaries and aggregate performance statistics.
- Failure clustering in diagnostics now keys off canonical signatures instead of
  raw message text heuristics, improving cross-model bucketing stability.
- JSONL result rows now include `failure_phase`, `error_code`, and
  `error_signature` fields (metadata format version bumped to `1.2`).
- Reduced `check_models.py` redundancy in model-issue summarization by removing
  dead `context_ignored` summary output paths and consolidating quality/delta
  bucketing flow while preserving report/log semantics.
- Added maintainer-oriented monolith guidance to
  `docs/IMPLEMENTATION_GUIDE.md` describing refactor order, correctness-vs-
  performance boundaries, and practical navigation/checklist steps for
  `check_models.py`.
- Further reduced duplicated summary-rendering logic by introducing shared
  top-performer/resource metric collectors reused by both HTML and Markdown
  issue summaries, keeping output semantics unchanged while trimming repeated
  key checks/formatting branches.
- Reused a shared quality-issue section collector for HTML and Markdown
  summaries, reducing duplicate failed/repetitive/hallucination/formatting
  extraction logic while preserving section content and emphasis.

### Fixed

- Fixed CI regression where runtime dependency hard-fail masked CLI argument and
  folder validation tests by firing too early in startup.
- Fixed diagnostics markdown formatting/lint edge cases in generated reports.
- Fixed `reportTypedDictNotRequiredAccess` lint failures by replacing direct
  optional-key TypedDict indexing with safe `.get(..., default)` patterns in
  summary formatters and JSONL tests.
- Fixed remaining `ModelIssueSummary` optional-key TypedDict access warnings in
  analysis helpers by replacing `setdefault(...)` read-path usage with explicit
  `get(...)` plus guarded initialization, preserving runtime behavior while
  satisfying strict Pylance/Pyright checks.
- Removed weak/avoidable lint suppressions by:
  - replacing shell word-splitting patterns with array-safe handling in quality
    and hook scripts;
  - replacing unnecessary test `type: ignore` usage with explicit type asserts.

## [0.1.1] - 2026-02-15

### Changed

- Compressed `src/check_models.py` logic (~45 lines removed) by deduplicating EXIF time extraction, quality-issue formatting, and token-leakage pattern data.
- Refactored `src/tools/check_outdated.py` to remove redundant string parsing logic and improve table detection.
- Improved test robustness by replacing flaky `time.sleep()` calls with deterministic `os.utime()` timestamp updates in `conftest.py` and image workflow tests.
- Reverted CI test skips for missing dependencies; the suite now enforces a hard failure if `mlx-vlm` is missing, ensuring environment integrity.
- Final run summary now reports configured `--output-log` and `--output-env` paths
  instead of always showing default log file locations.
- Synced documentation with current CLI behavior and outputs, including:
  `--output-diagnostics`, `--revision`, `--adapter-path`, and
  `--prefill-step-size`, plus `results.history.jsonl` / `diagnostics.md`.
- Updated quality and bot guidance docs (`AGENTS.md`, Copilot instructions,
  contributing docs, and pre-commit hook naming) to match the current CI gate.
- Improved `src/tools/run_quality_checks.sh` conda initialization by resolving
  the base path via `conda info --base` before fallback probe paths.

### Fixed

- Fixed `check_outdated.py` logic to correctly identify outdated package tables.

## [0.1.0] - 2026-02-08

### Added

- `--revision` CLI flag for pinning model versions (branch, tag, or commit hash)
- `--adapter-path` CLI flag for applying LoRA adapter weights
- `--prefill-step-size` CLI flag wired through to `generate()`
- TSV metadata comment line (`# generated_at: <timestamp>`) at top of output
- `error_type` and `error_package` columns in TSV reports for programmatic triage
- Warning when the default image folder (`~/Pictures/Processed`) does not exist
- JSONL v1.1 format with shared metadata header (prompt, system info, timestamp)
- 37 unit tests for pure-logic functions (`test_pure_logic_functions.py`)
- 11 report-generation edge-case tests (`test_report_generation.py`)
- 4 mock-based `process_image_with_model` tests (`test_process_image_mock.py`)
- Append-only history JSONL (`results.history.jsonl`) with per-run regression/recovery
  comparison summary (always prints "Regressions" and "Recoveries" sections)
- IPTC/IIM metadata extraction (keywords, caption) via Pillow `IptcImagePlugin`
- XMP metadata extraction (dc:subject, dc:title, dc:description) via `Image.getxmp()`
- Windows EXIF XPKeywords extraction (UTF-16LE semicolon-delimited)
- Keyword merging across IPTC, XMP, and XP sources (deduplicated, order-preserved)
- Structured stock-photo cataloguing prompt with Title/Description/Keywords sections
  and keyword taxonomy guidance (subjects, concepts, mood, style, colors, use-case)
- Existing metadata seeded into prompt (description, title, keywords, GPS, date)
- `Pillow[xmp]` extra for XMP metadata support (pulls in `defusedxml` transitively)
- Diagnostics report (`output/diagnostics.md`) auto-generated when failures or
  harness issues are detected — structured for filing upstream GitHub issues
  against mlx-vlm / mlx / transformers with error-pattern clustering, full
  error messages, traceback excerpts, environment table, and priority summary
- `--output-diagnostics` CLI flag for specifying diagnostics report path
- YAML config schema validation — warns on unknown threshold keys
- `CHANGELOG.md` (this file)
- `quality-strict` and `install-markdownlint` targets in root Makefile
- local npm-based markdownlint-cli2 tooling for CI/dev setup
...existing code...

### Changed

- `DEFAULT_TEMPERATURE` set to `0.0` (greedy/deterministic, matching mlx-vlm upstream)
- `--folder` and `--image` are now a mutually exclusive group in argparse
- Renamed `_apply_exclusions` → `apply_exclusions` (public API for testability)
- Bare URLs in generated Markdown reports are now auto-wrapped as `<URL>`
- Fixed `KeyboardInterrupt` / `SystemExit` / fatal exception handlers
- Unified CI action versions (`checkout@v4`, `setup-python@v5`, `setup-node@v4`)
  with concurrency groups and artifact upload on failure
- Added npm caching to CI quality workflow
- Fixed `setup_conda_env.sh` path references in documentation
  (was `./setup_conda_env.sh`, now `bash src/tools/setup_conda_env.sh`)
- Cleaned up VS Code settings (removed deprecated Python linting settings,
  aligned `typeCheckingMode`, fixed `launch.json` and `tasks.json`)
- Removed duplicated HF cache setup from `test_model_discovery.py` (now in `conftest.py`)
- Documented TSV and JSONL output format details in `src/README.md`
- Updated `QUALITY_IMPROVEMENT_PLAN_2026_02.md` — all items resolved

### Removed

- Duplicated sections in `IMPLEMENTATION_GUIDE.md` (Error Handling, Markdown Linting)
- 30 stale files archived from `docs/notes/` to `docs/notes/archive/`


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
