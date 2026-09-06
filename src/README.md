# MLX Vision Language Model Checker (`check_models.py`)

`check_models.py` is a comprehensive benchmarking and inspection tool designed for MLX-compatible Vision Language Models (VLMs) on Apple Silicon. It streamlines the process of validating model performance, quality, and resource usage across your local model collection.

> [!NOTE]
> This tool runs MLX-format Vision-Language Models hosted on the [Hugging Face Hub](https://huggingface.co). By default, it discovers and runs locally cached models that pass the `mlx-vlm` server-style cache-layout filter *and* classify as image-consuming text generators, making it effortless to benchmark the local models that actually fit an image-description benchmark.

## Who is this for?

- **Users & Researchers**: Quickly benchmark models on your own images, compare performance (TPS, memory), and verify output quality without writing code.
- **Developers**: Validate model conversions, debug quantization issues, and ensure regression testing for MLX/MLX-VLM improvements.

## Quick Start

Get up and running immediately with your cached models.

### 1. Installation

The fastest way to start is using the automated setup script (requires Conda):

```bash
# Sets up a 'mlx-vlm' environment with Python 3.13 and all dependencies
bash tools/setup_conda_env.sh
conda activate mlx-vlm
```

*(See [Installation Details](#installation-and-environment-setup) for manual pip setup)*

### 2. Run Your First Check

By default, the tool scans your Hugging Face cache for `mlx-vlm` server-supported models and runs them against the most recently modified image in `~/Pictures/Processed`. Cached repos that are not included are reported with a skip reason when `--models` is omitted.

```bash
# Run supported cached models against the most recent image in your folder
python -m check_models --folder ~/Pictures/Processed --prompt "Describe this image."

# Run against a specific image file
python -m check_models --image ~/Pictures/Processed/sample.jpg
```

### 3. Common Commands

```bash
# Test specific models (downloads them if needed)
python -m check_models --models mlx-community/nanoLLaVA mlx-community/llava-1.5-7b-hf

# Exclude a problematic model from the batch
python -m check_models --exclude "microsoft/Phi-3-vision-128k-instruct"

# Run with detailed debug logging
python -m check_models --verbose

# Dry run: validate setup and show what would run without invoking models
python -m check_models --dry-run
```

**Python Version**: 3.13+ is recommended and tested.

## Capabilities

- **Model Discovery**: Auto-discovers locally cached MLX VLMs using the `mlx-vlm` server-style cache-layout filter plus an image-capability classification (confident non-image repos — text-only, embedding, reranker, drafter, image/audio generation — are skipped with an explicit reason; unknown ones still run with a warning), or processes an explicit model list with `--models`
- **Selection Control**: Use `--exclude` to filter models from cache scan or explicit list
- **Folder Mode**: Automatically selects most recently modified image from specified folder
- **Metadata Extraction**: Multi-source metadata: EXIF + GPS + IPTC keywords/caption + XMP (dc:subject, dc:title) + Windows XP keywords, with fail-soft strategy for partially corrupt data
- **Capture Time Fidelity**: EXIF wall-clock values retain their declared UTC
  offset (or the system-local zone when no offset is recorded), and assisted
  prompts include the resulting capture time only once
- **Smart Prompting**: Generates structured cataloguing prompts (Title/Description/Keywords) that verify metadata against clearly visible image content, avoid speculation, and compact long metadata fields/keyword lists to keep prompt size manageable; `--prompt` overrides
- **Performance Metrics**:
  - Timing: generation_time, model_load_time, total_time
  - Detailed verbose timing: input validation, prompt prep, cleanup, upstream
    model prefill/first-token time (excluding input preparation), and stop reason
  - Tokens: total, prompt, generated with tokens/sec
  - Memory: peak, active/cache snapshots, and post-cleanup active/cache residue (GB)
- **Structured Logging**: Formatter-driven styling with LogStyles for consistent CLI output
- **Multiple Output Formats**:
  - **CLI**: Colorized; `--verbose` adds the detailed metrics tree
  - **HTML**: Standalone report with inline CSS, failed row highlighting
  - **Markdown**: Tiny run index, evidence gallery, and conditional diagnostics
  - **JSONL**: The sole schema-3 machine contract — run-level metadata header
    plus per-result records — for downstream analysis and public snapshots
- **Error Handling**: Per-model isolation with detailed diagnostics; graceful timeout/failure handling
- **Machine Parsable**: SUMMARY lines with `key=value` format for automation
- **Visual Hierarchy**: Emoji prefixes, tree-structured metrics, wrapped text output

## Feature Highlights

| Area | Notes |
| ---- | ----- |
| Model discovery | Scans the Hugging Face cache with two layers: the `mlx-vlm` server-style cache-layout filter plus a tri-state image-capability classification (`yes`/`unknown` run, confident `no` is skipped with an explicit `model purpose:` reason). Explicit `--models` overrides. |
| Selection control | `--exclude` works with cache scan or explicit list. |
| Prompting | `--prompt` overrides; otherwise structured cataloguing prompt with IPTC/XMP keyword seeding. |
| Performance | generation_time, model_load_time, total_time, token counts, TPS, peak memory. |
| Reporting | CLI (color), HTML (standalone), Markdown (GitHub). |
| Robustness | Per‑model isolation; failures logged; SUMMARY lines for automation. |
| Timeout | Signal‑based (UNIX) manager; configurable per run. |
| Output preview | Non‑verbose mode still shows wrapped generated text (80 cols). |
| Metrics modes | `--verbose` shows the full detailed metrics tree, including phase timings and stop reason when available. |

## Installation and Environment Setup

### Automated Setup (Recommended)

For the easiest setup, use the provided shell script that automates the entire conda environment creation:

```bash
# Create environment with default name 'mlx-vlm'
bash tools/setup_conda_env.sh

# Activate
conda activate mlx-vlm
```

The script handles Python 3.13 setup, dependencies, and optional PyTorch support.

For clean machines and normal project use, this conda workflow is the supported path.

### Manual Installation

If you prefer to create the environment manually, use conda and run the package
install commands from the `src/` directory.

<details>
<summary>Click to view manual conda setup</summary>

```bash
cd src
conda create -n mlx-vlm python=3.13
conda activate mlx-vlm
pip install -e .
```

</details>

### Optional Dependencies

Unless noted otherwise, the `pip install -e ...` commands below assume you are
running them from `src/`. From the repository root, prefer `make install`,
`make dev`, or `make -C src install-torch`.

Install the core runtime or add optional model coverage as needed:

```bash
# Runtime only (includes mlx and mlx-vlm)
pip install -e .

# Add optional extras and torch-backed loaders for broader model coverage
pip install -e ".[extras,torch]"

# Install only the PyTorch subset if you do not need the other extras
pip install -e ".[torch]"

# Install everything for development
pip install -e ".[dev,extras,torch]"
```

## Usage Guide

### Basic Execution

The tool is flexible: it can scan your cache, run specific models, or process single images.

```bash
# 1. Run supported cached models against a folder
python -m check_models --folder ~/Pictures/Processed

# 2. Run a specific model against a single image
python -m check_models --image test.jpg --models mlx-community/nanoLLaVA

# 3. Run with a custom prompt
python -m check_models --image test.jpg --prompt "Detailed caption."
```

### Advanced Examples

```bash
# Run across supported cached models with a custom prompt
python -m check_models -f ~/Pictures/Processed -p "What is the main object in this image?"

# Explicit model list (skips cache discovery)
python -m check_models -f ~/Pictures/Processed -m mlx-community/nanoLLaVA mlx-community/llava-1.5-7b-hf

# Repeated -m/--models flags also accumulate model IDs
python -m check_models -f ~/Pictures/Processed \
  -m mlx-community/nanoLLaVA \
  -m mlx-community/llava-1.5-7b-hf mlx-community/Qwen2-VL-2B-Instruct

# Exclude specific models from the automatic cache scan
python -m check_models -f ~/Pictures/Processed -e mlx-community/problematic-model other/model

# Repeated -e/--exclude flags accumulate exclusions
python -m check_models -f ~/Pictures/Processed \
  -e Qwen/Qwen3-VL-2B-Instruct \
  -e mlx-community/Qwen3-VL-2B-Thinking-bf16

# Repeated --eos-tokens flags accumulate stop tokens
python -m check_models --image test.jpg --models mlx-community/nanoLLaVA \
  --eos-tokens '</think>' \
  --eos-tokens '\n' '<END>'

# Combine explicit list with exclusions
python -m check_models -f ~/Pictures/Processed -m model1 model2 model3 -e model2

# Verbose (debug) mode for detailed logs
python -m check_models -f ~/Pictures/Processed -v
```

<details>
<summary>Click for more complex examples</summary>

```bash
# Full benchmark run with HTML/Markdown reports
python -m check_models \
  --folder ~/Pictures/TestImages \
  --exclude "microsoft/Phi-3-vision-128k-instruct" \
  --prompt "Provide a detailed caption for this image" \
  --max-tokens 200 \
  --temperature 0.1 \
  --timeout 600 \
  --output-dir ~/reports/vlm_benchmark \
  --verbose

# Memory optimization for large models (4-bit KV cache)
python -m check_models \
  --folder ~/Pictures \
  --lazy-load \
  --max-kv-size 4096 \
  --kv-bits 4

# Sampling control (Nucleus sampling + Repetition penalty)
python -m check_models \
  --folder ~/Pictures \
  --top-p 0.9 \
  --repetition-penalty 1.2 \
  --repetition-context-size 50
```

</details>

### Understanding the Output

The tool generates a deliberately small artifact set in `output/` by default:

- **CLI**: Real-time colorized progress and metrics.
- **HTML** (`reports/results.html`): Retained complete, self-contained report with
  a sortable current-run chooser, exact assessment filters, per-model
  prefill/first-token timing, captured performance facts,
  expandable complete output, maintainer diagnostics, and full run context.
- **Gallery Markdown** (`reports/model_gallery.md`): Model-comparison artifact with
  a bounded, orientation-corrected reference-image preview, image metadata, the
  full prompt, a usable-first facts-only chooser, a Resource Highlights section
  (fastest model, average throughput, lowest peak memory), an Output-at-a-Glance
  table previewing every model's actual output, and complete readable output per
  model (an exact-raw copy appears only when it differs from the readable view).
  End-to-end time precedes decode-only throughput.
- **JSONL** (`results.jsonl`): The sole schema `3.0` machine contract. The
  metadata header carries the complete run-level context — prompt plus its
  SHA-256 digest, execution mode and outcome counts, artifact paths,
  check_models producer version/revision and dirty-worktree state, source-image
  identity and dimensions, common generation settings, remote-code policy,
  component install/source provenance, and the baseline comparison — followed
  by exhaustive per-model rows: assessments, complete captured evidence,
  per-model completion time, exact observation evidence, per-prompt token
  burden, each model's requested versus resolved cache revision, the complete
  rendered chat-template prompt, captured upstream console output for
  successful runs, and the architecture pre-check verdict against the
  installed mlx-vlm.
- **Diagnostics** (`reports/diagnostics.md`): Self-contained, issue-ready mlx-vlm
  report with a triage table, expanded crashes, collapsed complete evidence for
  observations and indeterminate attempts, compact clean-run context, and one
  shared parameterised native reproduction. Definite crashes are outcomes;
  external-connectivity interruptions remain indeterminate.
  Human-facing observations use explanatory wording and list likely output-breaking
  symptoms first. Conservative repetition observations include the repeated
  fragment and complete output. Declared EOS/thinking wrappers and wholly unchanged
  draft metadata are neutral reproduction facts rather than inferred faults or
  quality scores.
- **Run issue summary** (`issues/run_summary.md`): Conditional compact whole-run
  GitHub issue body. It expands crashes with root exceptions and a parameterised
  reproduction command, separates completed, crashed, and indeterminate attempts
  requiring review into severity-ordered compact tables, explains structured
  failures even when no output observation exists, counts completions passing
  mechanical checks, and
  records remote-code and producer provenance. It links to complete retained
  evidence without copying full prompts, outputs, tracebacks, or scripts. Its
  cross-file links always use canonical GitHub repository URLs so they still work
  when the report is pasted into an issue.
- **Index** (`index.md`): Run dashboard — outcome counts, usability breakdown,
  and top observations at a glance — followed by links to the current-run files
  and, when generated, the run issue summary before individual crash drafts.
- **Log** (`check_models.log`): Canonical comprehensive run trace, including complete
  generated or captured failure output.
- **Environment** (`environment.log`): Full package and Conda environment capture.
- **History** (`results.history.jsonl`): Append-only raw history for optional
  out-of-band analysis. Current reports do not read it or derive advice from it.
- **Issue drafts** (`issues/issue_*.md`): Conditional factual drafts, not a standing
  report surface. Issue drafts are created only for hard actionable crashes. Their
  inline environment table is limited to runtime-relevant components and links to
  the complete retained `environment.log` inventory.

Regenerate only the compact issue body from an existing retained run — the
output root containing `results.jsonl` is the only input — without model
discovery or inference:

```bash
PYTHONPATH=src python -c 'from pathlib import Path; from check_models import regenerate_run_issue_summary; print(regenerate_run_issue_summary(Path("src/output")))'
```

#### Decision semantics and evidence scope

Every current-run row uses one immutable assessment with three independent fields:

- `execution`: `completed`, `crashed`, or `indeterminate`
- `usability`: `usable`, `usable_with_caveats`, `unusable`, or `not_evaluated`
- `maintainer_status`: `actionable_failure`, `observation_needs_reproduction`, or `none`

These machine codes are retained for compatibility. Human reports describe them as
"no concerns detected", "concerns detected", "major concerns", and "not assessed";
none is a semantic accuracy score. The selected assessment profile is recorded in
the JSONL header and each result's assessment.

Assessment is independent of the evaluation lane and prompt wording:

- **General** is the default for custom `--prompt` text and triage runs. It checks
  empty output, repetition, incomplete thinking and visible control tokens. Reports
  explicitly state **task compliance not assessed**.
- **Metadata** is the default for the built-in blind/assisted metadata prompt.
  It adds missing/empty Title, Description and Keywords fields and duplicate
  keywords. Markdown-labelled fields are accepted. Title word count and keyword
  count are evidence, not length-limit verdicts.
- Use `--assessment-profile metadata` with a custom metadata prompt, or
  `--assessment-profile general` to disable field checks for a built-in prompt.
  Differential triage reruns always use general checks.

Length ranges are no longer inferred from prose, and sentence counting, hint-overlap
and instruction-echo heuristics have been removed. Short answers, copied hints,
prefaces and lack of final punctuation are not automatically faults. Inspect the
image, exact prompt and visible final answer to judge suitability. Complete raw
output, including thinking, remains available. Older retained runs keep their
original verdicts and are labelled as having no recorded assessment profile.

Complete model output is retained as evidence for every attempt.
Crashes prioritize the complete traceback, followed by captured partial output and
exact factual provenance. Reaching the configured token cap alone is neutral.
Long complete output is not a fault. A cap becomes an observation only when mechanical evidence
also shows repetition, missing requested sections, or an incomplete thinking trace.

External connectivity failures are `indeterminate`, so they are retained without being counted as model crashes.
Configured thinking tokens are not automatically faults; observed or incomplete
thinking traces remain factual observations that may need controlled reproduction.
Likewise, tokenizer special-token metadata, tokenizer EOS, explicit `eos_tokens`,
and configured thinking start/end wrappers are treated as declared protocol.
Configured conversation-role tokens remain declared rather than “unknown”; when a
new user/assistant/system/turn/message/utterance boundary occurs inside generated
content, its exact token is retained as a separate role-boundary observation.
Control-wrapper syntax that appears in output without any of those declarations is
retained as an `unexpected_special_token` observation; no model-name allowlist is
used.
The chooser reports `insufficient sample` when throughput lacks enough generated
tokens for a meaningful comparison.

EXIF timestamps are interpreted as capture wall clocks rather than as UTC instants.
When `OffsetTimeOriginal`, `OffsetTimeDigitized`, or `OffsetTime` accompanies the
selected EXIF date field, that offset is retained. Pillow's `DateTimeDigitized` name
and the `CreateDate` alias are both recognised. If no valid EXIF date is available,
the prompt omits the date rather than treating filesystem modification time as
capture metadata. Complete generated output in the Markdown evidence artifacts is
fenced and preserves tabs and trailing spaces.

Use `reports/model_gallery.md` to choose models and compare complete readable and
exact output; paste `issues/run_summary.md` for a compact whole-run issue, and use
`reports/diagnostics.md` when complete maintainer evidence is needed.
`check_models.log` retains the full operational trace, while `results.jsonl`
retains exhaustive machine-readable evidence, provenance, and arguments.

Avoid lint/type suppressions wherever possible. Any unavoidable suppression must
have a documented purpose and pass the repository suppression audit.

Before a costly real-model matrix, run deterministic focused tests followed by
`make format`, `make -C src lint-fix`, `make lint`, and `make quality`. Real-model
runs are acceptance tests for runtime integration, report utility, exact evidence,
cross-artifact consistency, memory, and performance; they do not replace ordinary
tests. If Run 1 reveals a harness/report defect, fix and revalidate it, then rerun
and audit Run 1 before beginning comparative Run 2.

Generated Markdown should already satisfy the repository's markdownlint style:
blank lines around headings, lists, and ordinary fences; unique headings; asterisk
emphasis; language-tagged fences; and escaped table cells. Evidence fences retain
captured model tabs and trailing spaces under only the narrow lint configuration
needed for exact preservation. Render representative reports from fixtures into
temporary or `test_*` paths and lint them before the model matrix; use shared render
helpers and focused tests so production outputs never need hand editing.

### Metrics Explained

- **TPS (Tokens/Sec)**: Speed of generation. Higher is better.
- **Peak Memory**: Maximum RAM used. Critical for hardware sizing.
- **Load Time**: Time to load weights into memory.
- **Tokens**: Breakdown of Prompt (input) vs Generated (output) counts.


> [!TIP]
> **Memory Units**: All memory metrics are normalized to GB (decimal).
> **Token Counts**: `tokens(total/prompt/gen)` shows the full breakdown.
> [!IMPORTANT]
> **Image Resolution vs Vision Encoder Input**: VLMs **never see your full-resolution image**. Every model downsamples the input to fit its vision encoder's fixed size before processing. A 50 MP image (8627×5760) becomes a ~0.2 MP thumbnail at 448×448 — a 250× reduction. This means fine details (text, small objects, texture) are lost before the model even starts.
> Typical input resolutions by model family:

| Resolution | Models |
| --- | --- |
| 224×224 | nanoLLaVA |
| 384–448 | PaliGemma2-448, Phi-3.5, FastVLM, LFM2 |
| 560–768 | SmolVLM, Idefics3, Molmo |
| 896–1344 | PaliGemma2-896, Qwen2-VL, Qwen3-VL (dynamic tiling) |

> The Qwen VL family uses **dynamic resolution** with tile-based encoding, processing the image in multiple patches at higher fidelity — which is why their prompt token counts are much larger (~16,000 vs ~500 for PaliGemma2). If a model reports "image too small to see," it is being honest about what it actually received.


### Configuration & Parameters

#### Controlling Repetitive Output

While MLX-VLM doesn't explicitly document these in all examples, the underlying `generate()` function (inherited from MLX-LM) supports **repetition penalty** parameters that can significantly reduce or eliminate repetitive text generation. These parameters work by penalizing tokens that have already appeared in recent context:

- `--repetition-penalty <float>`: Penalty factor for repeating tokens (must be ≥ 1.0). Higher values more strongly discourage repetition. Common range: 1.0-1.2. Default: `None` (no penalty).
- `--repetition-context-size <int>`: Number of recent tokens to check for repetition. Smaller values (10-20) only penalize immediate loops; larger values (50-100) prevent long-range repetition. Default: 20.

**Example usage**:

```bash
# Moderate penalty to reduce repetition
python -m check_models --image photo.jpg \
  --repetition-penalty 1.1 \
  --repetition-context-size 64

# Strong penalty with larger context window
python -m check_models --image photo.jpg --repetition-penalty 1.15 --repetition-context-size 50
```

**How it works** (from MLX source): During generation, the model maintains a sliding window of the last N tokens (`repetition_context_size`). For each new token prediction, logits of tokens that appear in this window are divided by the `repetition_penalty` factor, making them less likely to be selected. This mechanism operates at the token level during sampling, before temperature is applied.

**Trade-offs**:

- ✅ **Benefit**: Dramatically reduces repetitive loops, hallucinated lists, and redundant output
- ⚠️ **Risk**: Overly aggressive penalties (>1.2) may harm output quality, forcing the model to use awkward synonyms or break natural repetition (e.g., proper nouns, technical terms)
- 💡 **Tip**: Start with 1.05-1.1 and increase gradually while monitoring quality flags in the output

The `check_models` tool's quality analysis detects repetition post-generation and flags it in reports. Using these parameters proactively can prevent repetitive output before it occurs, saving generation time and improving results.

Keep the neutral defaults for comparable baseline runs. When one model loops, first
rerun only that model with `--repetition-penalty 1.1 --repetition-context-size 64`.
If the loop disappears, report both attempts; do not silently mix penalized and
unpenalized results in one ranking. Repetition penalties do not correct irrelevant
reasoning traces or a chat template that inserts thinking tokens.

#### Server-Shared Request Controls

`mlx-vlm` exposes additional OpenAI-style request controls through its
FastAPI server. Where those controls map directly to `mlx_vlm.generate()`,
`check_models` forwards them too:

- `--seed <int>`: Seed forwarded to upstream sampling.
- `--presence-penalty <float>` and `--presence-context-size <int>`: Apply an
  additive penalty to tokens that have already appeared in recent generated
  context.
- `--frequency-penalty <float>` and `--frequency-context-size <int>`: Apply an
  additive penalty scaled by token frequency in recent generated context.
- `--logit-bias '{"token_id": bias}'`: Forward an OpenAI-style token-id bias
  object to generation, with JSON object keys normalized to integer token IDs.

#### mlx-vlm coverage matrix

`check_models` is a focused single-image benchmark that calls the direct
`mlx_vlm` load, chat-template, image-loading, and generation APIs, one model at
a time — sequentially in one interpreter, with per-model exception isolation and
resource cleanup between models. As mlx-vlm has grown into a serving
runtime, this table is the authoritative statement of which upstream surfaces
this project exercises and which it deliberately leaves to native mlx-vlm
tools. (The upstream contract this project validates against is
`_RUNTIME_API_CALL_CONTRACTS` in `check_models.py`; the direct calls are
`mlx_vlm.utils.load`, `mlx_vlm.utils.load_image`,
`mlx_vlm.prompt_utils.apply_chat_template`, and `mlx_vlm.generate.generate`.)

| Surface | Status | Notes |
| ------- | ------ | ----- |
| Model loading (`load`), `--revision`, `--adapter-path`, `--trust-remote-code`, `--lazy-load`, `--force-download` | **Exercised** | Direct API; load failures are phase-tagged and classified. |
| Still-image input (`load_image`), one image per run | **Exercised** | Always exactly one image; the chat template is applied with `num_images=1`. |
| Chat templates (`apply_chat_template`), `--processor-kwargs` passthrough | **Exercised** | Template kwargs are recorded in prompt diagnostics. |
| Text generation (`generate`), sampling and penalty controls, `--seed`, `--logit-bias` | **Exercised** | Everything sent is listed in `_SENT_GENERATE_KEYWORDS` and drift-checked against the installed `GenerateKwargs`. |
| Thinking controls (`--enable-thinking`, `--thinking-budget`, start/end tokens, `--thinking-mode`, automatic budget) | **Exercised** | See the `--enable-thinking`, `--thinking-budget`, and `--auto-thinking-budget` entries in the Command Line Reference. |
| KV-cache controls (`--max-kv-size`, uniform and per-tensor `--kv-*-bits`/`--kv-*-scheme`, `--quantized-kv-start`) | **Exercised** | Per-tensor fields are sent only when set, so PyPI releases predating them are unaffected. |
| Timing, throughput, MLX peak/active/cache memory, allocator evidence, system-pressure telemetry | **Exercised** | Harness-side measurement around the direct call, not an upstream surface. |
| Multi-image, audio, and video inputs | Deliberately unexercised | Out of scope for a single-image description benchmark; use `python -m mlx_vlm.generate` (which accepts multi-image, audio, and video inputs) natively. |
| Speculative decoding (draft models, DFlash) | Deliberately unexercised | A drafter is a second model and changes timing, memory, provenance, and failure attribution; it belongs in a future explicit benchmark lane, never the baseline. |
| Prompt cache / vision-feature cache reuse across calls | Deliberately unexercised | Each model runs cold, once, with cleanup between models; no `prompt_cache`, `vision_cache`, or `prompt_cache_state` is constructed or reused. |
| Image/video generation and image editing pipelines | Deliberately unexercised | Different model kind; cached generation pipelines classify as non-image and are skipped by default discovery with an explicit reason. |
| OpenAI / Anthropic / Responses / realtime protocols, streaming envelopes, top-logprobs | Server-only | `python -m mlx_vlm.server`; not a per-model benchmark kwarg. |
| Continuous batching, request queues, `/v1/cache/*`, `/unload`, `/health`, `/metrics` | Server-only | Serving-runtime concerns with no direct-API equivalent. |
| Automatic prefix caching (APC), including PR #1713 | Server-only | See the note below. |
| Embedding and reranker models (direct loaders `mlx_vlm.embeddings` / `mlx_vlm.reranker`, and the server endpoints) | Deliberately unexercised / Server-only | Different model kinds; their cached repos classify as non-image and are skipped by default discovery with an explicit reason. |
| Structured outputs, tool calling, MCP | Server-only | Protocol features layered on the server, not on `generate()`. |
| Model conversion / quantisation, fine-tuning (LoRA), evaluation suites, distributed inference | Separate workflows | Native mlx-vlm CLIs; this project only consumes already-converted cached repos. |

**Why mlx-vlm PR #1713 does not affect normal `check_models` runs.** That PR
fixes automatic-prefix-cache reuse for growing prepared prompts. APC prefix
reuse only engages when a caller supplies an `apc_manager` and reuses server
prompt caches across requests. `check_models` never constructs an APC manager,
never passes `prompt_cache`/`prompt_cache_state`, and runs each model exactly
once from a cold state, so there is no prefix to reuse and the changed code
path is never entered. The same reasoning applies to any future server-cache
fix: it can only matter here if this project starts reusing caches, which the
baseline deliberately does not.

Use `mlx_vlm.server` directly for the server-only surfaces; `check_models`
uses direct generation for benchmark isolation.

When filing or debugging upstream server-only behavior, start the server with
`python -m mlx_vlm.server` under the conda `mlx-vlm` environment, prefer `curl`
over client SDKs for minimal repros, and keep streaming vs non-streaming cases
separate. This project documents **pip/conda** commands only (not `uv`). See
`.agents/skills/native-mlx-vlm-repro/SKILL.md` and
`.agents/skills/upstream-mlx-vlm-issues/SKILL.md`.

#### Processor Passthrough and Generation Diagnostics

`mlx-vlm` keeps processor options and generation options distinct. Use
`--processor-kwargs` for model/processor preprocessing options such as
`{"cropping": false, "max_patches": 3}`. Generation behavior is controlled by
the named generation flags in this reference, including sampling, penalty,
thinking, KV-cache, and token-budget options.

Diagnostics and repro artifacts preserve the effective generation kwargs that
the `mlx_vlm.generate.stream_generate` call receives.

#### KV Cache Quantization (Memory Optimization)

Vision-language models maintain a **key-value (KV) cache** during text generation to avoid recomputing attention for previous tokens. For long sequences or large models, this cache can consume significant memory. MLX-VLM supports KV cache quantization to reduce memory usage with minimal impact on output quality.

### Parameters

- `--max-kv-size <int>`: Maximum number of tokens to store in KV cache. Limits memory for very long sequences. Default: `None` (unlimited).
- `--kv-bits <number>`: Quantize KV cache instead of using full precision (typically 16-bit). Uniform quantization supports `2`, `3`, `4`, `5`, `6`, or `8`; fractional values such as `3.5` use upstream TurboQuant automatically. Default: `None` (no quantization).
- `--kv-quant-scheme <uniform|turboquant>`: Select the upstream KV quantization backend. Default: `uniform`.
- `--kv-key-bits <number>`: Override the bit-width for cached keys only (requires `--kv-bits`; under TurboQuant defaults to `floor(--kv-bits)`). Default: `None`.
- `--kv-value-bits <number>`: Override the bit-width for cached values only (requires `--kv-bits`; under TurboQuant defaults to `ceil(--kv-bits)`). Default: `None`.
- `--kv-key-scheme <uniform|turboquant>`: Override the quantization backend for keys only (requires `--kv-bits`). Default: `None` (follow `--kv-quant-scheme`).
- `--kv-value-scheme <uniform|turboquant>`: Override the quantization backend for values only (requires `--kv-bits`). Default: `None` (follow `--kv-quant-scheme`).
- `--kv-group-size <int>`: Group size for quantization (larger = more compression, less accuracy). Default: `64`.
- `--quantized-kv-start <int>`: Token position to start quantization. Use `0` to quantize from the beginning, or a larger value to keep early tokens (e.g., system prompts) at full precision. Default: `5000`.

### How It Works

From the MLX and MLX-VLM sources: uniform KV quantization uses MLX affine bit widths (`2`, `3`, `4`, `5`, `6`, or `8`) with `kv_group_size` token groups, while TurboQuant supports integer and `.5` bit widths and automatically handles fractional values such as `3.5` as lower-bit keys plus higher-bit values. Both reduce memory while maintaining most of the model's generation quality.

### Example Usage

```bash
# Moderate 8-bit quantization for 2× memory savings
python -m check_models --image photo.jpg --kv-bits 8

# Match upstream TurboQuant KV-cache handling
python -m check_models --image photo.jpg --kv-bits 3.5 --kv-quant-scheme turboquant

# Per-tensor override: 8-bit keys, 3-bit TurboQuant values
python -m check_models --image photo.jpg --kv-bits 8 --kv-value-bits 3 --kv-value-scheme turboquant

# Aggressive 4-bit quantization with larger groups (4× compression)
python -m check_models --image photo.jpg --kv-bits 4 --kv-group-size 128

# Quantize only after first 512 tokens (preserve system prompt precision)
python -m check_models --image photo.jpg --kv-bits 8 --quantized-kv-start 512

# Cap cache size for extremely long outputs
python -m check_models --image photo.jpg --max-kv-size 4096 --kv-bits 8
```

### When to Use

**Use KV quantization if:**

- ✅ Testing large models (>10B parameters) on limited RAM
- ✅ Generating long sequences (>1000 tokens)
- ✅ Running multiple models in parallel
- ✅ Encountering OOM (out of memory) errors

**Skip quantization if:**

- ❌ Models are small (<7B parameters)
- ❌ Sequences are short (<500 tokens)
- ❌ You need maximum quality for critical tasks

### Trade-offs

- **4-bit**: 75% memory reduction, slight quality degradation (noticeable in complex reasoning)
- **8-bit**: 50% memory reduction, minimal quality impact (recommended starting point)
- **Group size**: Larger groups save more memory but reduce precision; 64-128 is optimal for most cases

#### Temperature and Sampling

- `--temperature <float>`: Controls randomness in generation. `0.0` = deterministic (argmax), `1.0` = high diversity, `>1.0` = more random. Default: `0.0`.
- `--top-p <float>`: Nucleus sampling threshold. Only considers tokens whose cumulative probability is ≤ `top_p`. Range: `0.0-1.0`. Default: `1.0` (disabled).

These control the sampling strategy during generation. Higher temperature increases variety but can produce less coherent outputs. Top-p sampling (nucleus sampling) focuses on the most probable tokens.

**Example**:

```bash
# Deterministic output (default)
python -m check_models --image photo.jpg --temperature 0.0

# Balanced creativity
python -m check_models --image photo.jpg --temperature 0.7 --top-p 0.9

# Maximum diversity (risky)
python -m check_models --image photo.jpg --temperature 1.5 --top-p 0.95
```

#### Generation Control

- `--max-tokens <int>`: Maximum number of tokens to generate. Prevents runaway generation. When omitted, the resolved evaluation lane supplies the default (`1000`; `triage` `200`); an explicit value always wins over the lane default.
- `--timeout <float>`: Timeout in seconds for each model's generation. Useful for identifying slow/hanging models. Default: `300.0` (5 minutes).

**Example**:

```bash
# Short captions only
python -m check_models --image photo.jpg --max-tokens 100

# Strict timeout for batch testing
python -m check_models --folder ~/images --timeout 120
```

#### Trust Remote Code

- `--trust-remote-code` (default): Allow execution of custom modeling code from Hugging Face repos. **Security risk** - only use with trusted models.
- `--no-trust-remote-code`: Disable custom code execution for maximum security.

Some models require custom Python code for their architecture. This flag enables loading that code.

**Examples**:

```bash
# Enable for models like Qwen or custom architectures (default behavior)
python -m check_models --image photo.jpg --models mlx-community/Qwen2-VL-7B-Instruct --trust-remote-code

# Disable for security (may cause some models to fail)
python -m check_models --image photo.jpg --no-trust-remote-code
```

> [!WARNING]
> **Security Risk**: `--trust-remote-code` (the default) executes arbitrary Python from the model repo. Use `--no-trust-remote-code` when running untrusted models.

#### Model Version & Adapter

- `--revision <str>`: Pin the model to a specific branch, tag, or commit SHA from the Hugging Face repo. Useful for reproducing results or avoiding regressions when a model updates. Default: `None` (latest revision on main/default branch).
- `--adapter-path <str>`: Path to a LoRA adapter directory to apply on top of the base model. Passed through to `mlx_vlm.utils.load(adapter_path=...)`. Default: `None` (no adapter).

**Examples**:

```bash
# Pin to a specific commit for reproducibility
python -m check_models --image photo.jpg --models mlx-community/Qwen2-VL-7B-Instruct \
  --revision abc1234

# Apply a LoRA fine-tune
python -m check_models --image photo.jpg --models mlx-community/nanoLLaVA \
  --adapter-path ~/adapters/my-lora

# Combine: specific revision + LoRA adapter
python -m check_models --image photo.jpg --models mlx-community/nanoLLaVA \
  --revision v1.0 --adapter-path ~/adapters/my-lora
```

### Environment Variables

Several behaviors can be customized via environment variables (useful for CI/automation):

| Variable | Purpose | Default | Example |
| -------- | ------- | ------- | ------- |
| `MLX_VLM_WIDTH` | Force CLI output width (columns) | Auto-detect terminal | `MLX_VLM_WIDTH=120` |
| `CHECK_MODELS_SKIP_IMPORT_PROBE` | Skip the subprocess import probes that shield a long-lived run from a hard-crashing dependency import (the test suite sets it; each worker already imports mlx-vlm in-process) | Not set (probes run) | `CHECK_MODELS_SKIP_IMPORT_PROBE=1` |
| `NO_COLOR` | Disable ANSI colors in output | Not set (colors enabled) | `NO_COLOR=1` |
| `FORCE_COLOR` | Force ANSI colors even in non-TTY | Not set | `FORCE_COLOR=1` |
| `TOKENIZERS_PARALLELISM` | Disable tokenizer parallelism warnings | `false` | `TOKENIZERS_PARALLELISM=true` |
| `UPDATE_SYSTEM_PACKAGES` | `tools/update.sh` conda base/env and Homebrew updates | `1` (run system updates) | `UPDATE_SYSTEM_PACKAGES=0` to skip |
| `UPDATE_NODE_TOOLING` | Optional `tools/update.sh` npm latest upgrade for markdownlint tooling | `0` (install from lockfile) | `UPDATE_NODE_TOOLING=1` |
| `MLX_METAL_JIT` | Optional `tools/update.sh` override (`MLX_METAL_JIT`) | Unset (uses MLX default `OFF`, pre-built kernels) | `MLX_METAL_JIT=ON` for runtime JIT |
| `MLX_LOCAL_BUILD_SMOKE` | Optional `tools/update.sh` local-MLX smoke control | `auto` (cached model only) | `MLX_LOCAL_BUILD_SMOKE=1` to force |
| `MLX_LOCAL_BUILD_SMOKE_MODEL` | Model used by the local-MLX smoke test | `mlx-community/MiniCPM-V-4.6-8bit` | Any cached HF model |
| `MLX_LOCAL_BUILD_SMOKE_EXPECTED` | Expected deterministic smoke output substring | `Hello! How can I help you today?` | Override for a custom model |

**Examples**:

```bash
# Force wider output for CI logs
MLX_VLM_WIDTH=120 python -m check_models --folder ~/Pictures

# Disable colors for log file capture
NO_COLOR=1 python -m check_models > output.log 2>&1
```

## Git Hygiene and Caches

This repo excludes ephemeral caches and local environments via `.gitignore`. Common exclusions include `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.venv/`, and editor folders like `.vscode/`. Do not commit large model caches (e.g., Hugging Face) to the repository.

## Pre-commit (Optional)

Recommended workflow:

```bash
pre-commit install
```

`pre-commit` ships with the dev extras; the checked-in
`.pre-commit-config.yaml` installs both the `pre-commit` (staged hygiene) and
`pre-push` (fast static gate) hooks, and `make dev` / `tools/setup_conda_env.sh`
run this for you.

  This installs both commit-stage and pre-push hooks from the checked-in
  `.pre-commit-config.yaml`. The commit hook runs staged-file hygiene only; the
  push hook runs fast static checks plus the non-slow/non-e2e pytest subset.
  If you switch between workflows, rerun your preferred installer because both
  write to `.git/hooks/`.

Run the push-stage gate manually with:

```bash
pre-commit run --hook-stage pre-push --all-files
```

The commit-stage hook is intentionally staged-file based; run it by making a
normal commit, or call `bash src/tools/run_commit_hygiene.sh` directly after
staging files.


### Manual Installation

If you prefer to install dependencies manually (ensure these match `pyproject.toml`):

<!-- MANUAL_INSTALL_START -->
```bash
pip install "defusedxml>=0.7.1" "huggingface-hub[typing]>=1.10.1" "mlx>=0.32.1" "mlx-vlm>=0.6.16" "numpy>=2.1.0" "packaging>=26.0" "Pillow[xmp]>=12.3.0" "PyYAML>=6.0" "rich>=14.1.0" "transformers>=5.14.0"
```
<!-- MANUAL_INSTALL_END -->

## Requirements

- **Python**: 3.13+ (3.13 is the tested baseline)
- **Operating System**: macOS with Apple Silicon (MLX is Apple‑Silicon specific)

The working `mlx-vlm` env stays on the tested baseline. To see whether a newer
Python has become viable without touching that env, run
`make probe-python-next` (defaults to 3.14): it installs the PyPI stack into a
throwaway `mlx-vlm-314` conda env, verifies imports and the fast test lane, and
optionally (`PROBE_SOURCE_BUILD=1`) compiles the local mlx source tree — the one
signal PyPI wheels cannot give and the thing that would actually break
`tools/update.sh` after a switch. `PROBE_PYTHON=3.15` targets a later version.

### Advanced Configuration

The tool uses a YAML configuration file for retained mechanical observation
thresholds and prompt-size limits.

- **Default Config**: The tool ships with a bundled default `quality_config.yaml`. In this source tree, the canonical copy lives at `src/check_models_data/quality_config.yaml`.
- **Custom Config**: You can provide your own config file via `--quality-config path/to/config.yaml`.

**Key Configurable Areas:**

- **Repetition**: Thresholds for token and phrase repetition.
- **Prompt burden**: Recorded and estimated prompt-size thresholds.
- **Prompt compaction**: Limits for metadata hints injected into the default prompt
  (`prompt_title_max_chars`, `prompt_description_max_chars`,
  `prompt_keyword_max_items`).

See `src/check_models_data/quality_config.yaml` for the full schema and default values.

### Development Tools

The `src/tools/` directory contains scripts useful for development and verification:

- **Smoke Testing**: For quick verification, you can use the standard `mlx-vlm` CLI:

  ```bash
  python -m mlx_vlm.generate --model mlx-community/nanoLLaVA --image test.jpg
  ```

  Or refer to the official [test_smoke.py](https://github.com/Blaizzy/mlx-vlm/blob/main/mlx_vlm/tests/test_smoke.py) script.

- **E2E Smoke Tests**: The test suite includes end-to-end tests that run actual model inference:

  ```bash
  # Run E2E tests (requires cached model: mlx-community/nanoLLaVA-1.5-4bit)
  pytest tests/test_e2e_smoke.py -v

  # Skip slow tests for quick iteration
  pytest -m "not slow"

  # Run all tests including E2E
  pytest tests/ -v
  ```

  > [!NOTE]
  > E2E tests require `mlx-community/nanoLLaVA-1.5-4bit` to be cached. Run a quick inference first to download it:
  > `python -m check_models --models mlx-community/nanoLLaVA-1.5-4bit --max-tokens 10`

- **`validate_env.py`**: Checks your environment for required dependencies and configuration.

  ```bash
  python -m tools.validate_env
  ```

- **`run_quality_checks.sh`**: Unified quality gate used by local dev and CI.

  ```bash
  # Run from repo root (recommended)
  make quality

  # Or run the script directly
  bash src/tools/run_quality_checks.sh
  ```

- **`run_skylos_danger_advisory.sh`**: Advisory Skylos `--danger` scan for
  workflow/security findings, with an optional LLM-friendly report for agent
  triage.

  > [!IMPORTANT]
  > This path stays advisory for now, but the current repo-root `--danger` scan
  > is clean. If the project wants stricter enforcement later, this is the most
  > obvious candidate to promote into the blocking gate.

  ```bash
  # Run from repo root (recommended)
  make skylos-danger

  # Add an LLM-oriented report for agent review
  make skylos-danger-llm

  # Or run the script directly
  bash src/tools/run_skylos_danger_advisory.sh --llm
  ```

- **`run_skylos_verify.sh`**: Narrow Skylos verifier wrapper for post-edit
  agent checks, always with repo project context.

  ```bash
  # Run from repo root (recommended)
  make skylos-verify ARGS='--file src/check_models.py --range 100:130'

  # Allow findings without failing the command
  make skylos-verify ARGS='--file src/check_models.py --range 100:130 --no-fail'

  # Or run the script directly
  bash src/tools/run_skylos_verify.sh --file src/check_models.py --range 100:130
  ```

- **`run_ty_check.sh`**: Dedicated Ty entrypoint with explicit interpreter
  resolution for this repo.

  ```bash
  # Run from repo root (recommended)
  make ty

  # Or run the script directly
  bash src/tools/run_ty_check.sh
  ```

  This wrapper is the supported way to run Ty locally. It resolves the
  expected `mlx-vlm` conda interpreter and prints the target env, active env,
  resolved Python path, and resolved Ty binary before checking. Avoid relying
  on raw `ty check ...` environment auto-detection for this repo.

## Appendix: Dependencies

Why so slim? The runtime dependency set is intentionally minimized to only the
packages directly imported by `check_models.py`. Everything else that might
inference helpers, PyTorch stack) lives in optional extras. Benefits:

- Faster cold installs / CI setup
- Smaller transitive surface → fewer unexpected resolver conflicts
- Clearer signal when a new import is introduced (you must add it to
  `[project.dependencies]` or tests + sync tooling will fail)
If you add a new top‑level import in `check_models.py`, promote its package
from an optional group (or add it fresh) into the runtime `dependencies` array
and re-run the sync helper.

Runtime (installed automatically via `pip install -e .` when executed inside `src/`, or via `make install` from repo root):

| Purpose | Package | Version spec |
| ------- | ------- | ------- |
| Core tensor/runtime | `mlx` | `>=0.32.0` |
| Vision‑language utilities | `mlx-vlm` | `>=0.6.13` |
| Transformer compatibility surface | `transformers` | `>=5.14.0` |
| Image processing & loading | `Pillow[xmp]` | `>=12.3.0` |
| Safe XMP/XML parsing | `defusedxml` | `>=0.7.1` |
| Model cache / discovery | `huggingface-hub` | `>=1.10.1` |
| PEP 440 version parsing | `packaging` | `>=26.0` |
| Console rendering | `rich` | `>=14.1.0` |
| Configuration loading | `PyYAML` | `>=6.0` |

Optional (enable additional features):

| Feature | Package | Source | Install Command |
| ------- | ------- | ------ | --------------- |
| Extended system metrics (RAM/CPU) | `psutil` | `extras` | `pip install -e "src/[extras]"` |
| Fast tokenizer backends | `tokenizers>=0.22.0,<0.23.0` | `extras` | `pip install -e "src/[extras]"` |
| Tensor operations (for some models) | `einops` | `extras` | `pip install -e "src/[extras]"` |
| Number-to-words conversion (for some models) | `num2words` | `extras` | `pip install -e "src/[extras]"` |
| SentencePiece tokenizers | `sentencepiece!=0.1.92,>=0.1.91` | `extras` | `pip install -e "src/[extras]"` |
| Transformer model support | `transformers` | core runtime | Installed by `make install` / `pip install -e src/` |
| PyTorch stack (needed for some models) | `torch>=2.4.0`, `torchvision>=0.17.0`, `torchaudio>=2.2.0` | `torch` | `pip install -e "src/[torch]"` or `make -C src install-torch` |
| Vision backbones for FastVLM-style models | `timm>=1.0.23` | `torch` | `pip install -e "src/[torch]"` or `make -C src install-torch` |

**Note**: Some models (e.g., Phi-3-vision, certain Florence2 variants) require PyTorch. If you encounter import errors for `torch`, `torchvision`, or `torchaudio`, install with:

```bash
# From root directory:
pip install -e "src/[torch]"
make -C src install-torch

# Or from src/ directory:
pip install -e ".[torch]"

# Install everything (extras + torch + dev):
make dev
make -C src install-all
pip install -e ".[extras,torch,dev]"  # from src/
```

Development / QA:

| Purpose | Package |
| ------- | ------- |
| Linting & formatting checks | `ruff` |
| Static type checking | `mypy` |
| Testing | `pytest`, `pytest-cov` |

### Minimal Install (runtime only)

<!-- MINIMAL_INSTALL_START -->
```bash
pip install "defusedxml>=0.7.1" "huggingface-hub[typing]>=1.10.1" "mlx>=0.32.1" "mlx-vlm>=0.6.16" "numpy>=2.1.0" "packaging>=26.0" "Pillow[xmp]>=12.3.0" "PyYAML>=6.0" "rich>=14.1.0" "transformers>=5.14.0"
```
<!-- MINIMAL_INSTALL_END -->

### With Optional Extras

The `extras` group in `pyproject.toml` pulls in `psutil`, `tokenizers`, `einops`, `num2words`, and `sentencepiece`. The tokenizer specs follow the `transformers>=5.14.0` compatibility floor:

```bash
pip install -e ".[extras,torch]"  # recommended for the widest optional feature/model coverage
```

If you only need the lighter optional extras without PyTorch, you can still install them separately:

```bash
pip install -e ".[extras]"
```

To include only the optional PyTorch stack when needed (macOS wheels include MPS acceleration):

```bash
pip install -e ".[torch]"
```

That `torch` extra also installs `timm`; the `torch` and `timm` floors follow Transformers optional-extra metadata and support FastVLM remote-code model loaders.

### Full Development Environment

```bash
pip install -e ".[dev,extras,torch]"  # dev tools + optional model/runtime deps
```


<!-- markdownlint-disable MD028 -->

> [!NOTE]
> `psutil` is optional (installed with `extras`); if absent the extended Apple Silicon hardware section omits RAM/cores.

> [!NOTE]
> The `extras` group adds psutil, tokenizers, einops, num2words, and sentencepiece; tokenizers and sentencepiece follow the `transformers>=5.14.0` compatibility floor. For the widest model coverage, pair extras with `.[torch]` or install `.[extras,torch]` directly.

> [!NOTE]
> Project policy requires `transformers>=5.14.0` and validates the live
> `mlx_vlm` runtime contract during preflight so upstream API drift is surfaced
> before generation starts.

> [!NOTE]
> `system_profiler` is a macOS built-in (no install needed) used for GPU name / core info.

> [!NOTE]
> Torch is supported and can be installed when you need it for specific models; the script does not block Torch.

> [!NOTE]
> The `tools/update.sh` helper is for local MLX ecosystem development when
> sibling `mlx` and `mlx-vlm` repositories are present. It builds
> `mlx` with upstream's editable dev install (`pip install -e ".[dev]"`), checks
> the local Xcode/SDK/Metal toolchain before building, logs the `mlx.metallib`
> backend artifact, reinstalls this project from `pyproject.toml` after MLX
> updates to reconcile shared dependencies, and runs a cached-model smoke test
> in auto mode. Use `make update` for normal PyPI package updates.

> [!NOTE]
> Installing `sentence-transformers` isn't necessary for this tool and may pull heavy backends into import paths; `check_models` ignores it in the normal execution path.

> [!NOTE]
> Long embedded CSS / HTML lines are intentional (readability > artificial wrapping).

> [!NOTE]
> To update dependency versions in this README:
>
> 1. Edit versions only in `pyproject.toml` (authoritative source).
> 2. Run the sync helper: `python -m tools.update_readme_deps` to regenerate the blocks between:
>    - `<!-- MANUAL_INSTALL_START -->` / `<!-- MANUAL_INSTALL_END -->`
>    - `<!-- MINIMAL_INSTALL_START -->` / `<!-- MINIMAL_INSTALL_END -->`
> 3. Commit both changed files together.

> [!NOTE]
> To clean build artifacts: `make clean` (project), `make clean-mlx` (local MLX repos), or `bash tools/clean_builds.sh`.

<!-- markdownlint-enable MD028 -->

## Python API

The package exports a clean public API for programmatic use:

### Mechanical Output Analysis

```python
from check_models import analyze_generation_text, GenerationQualityAnalysis

# Analyze generated text for mechanical observations
text = "Model output goes here..."
analysis = analyze_generation_text(text, generated_tokens=50)

# Access directly observed results
if analysis.is_repetitive:
    print(f"Repetitive token: {analysis.repeated_token}")
if analysis.missing_sections:
    print(f"Missing requested sections: {analysis.missing_sections}")
if analysis.thinking_trace_incomplete:
    print("A thinking trace opened but never closed")
if analysis.likely_capped:
    print("The recorded output token count reached the requested cap")
if analysis.unexpected_special_tokens:
    print(f"Unexpected special tokens: {analysis.unexpected_special_tokens}")
```

The analysis records narrow evidence; it does not infer semantic quality, a
likely cause, or an owning package. Missing token counts remain unknown. The
current thresholds are configurable in the bundled `quality_config.yaml`
(`src/check_models_data/quality_config.yaml` in this repo):

```yaml
thresholds:
  min_tokens_for_substantial: 10
  max_words_for_minimal_output: 2
  long_prompt_tokens_threshold: 3000

  # Default prompt compaction thresholds
  prompt_title_max_chars: 120
  prompt_description_max_chars: 420
  prompt_keyword_max_items: 20
```

### Core Functions

```python
from check_models import (
    process_image_with_model,  # Process single image with a model
    generate_diagnostics_report,  # Create diagnostics Markdown
    generate_html_report,  # Create HTML report
    get_system_info,  # Get system information dict
    format_field_value,  # Format metric values consistently
    format_overall_runtime,  # Format duration strings
)
```

See module docstrings and `__all__` exports for complete API reference.


## Evaluation lanes

Each invocation runs exactly one resolved evaluation lane. Reports, JSONL headers,
run metadata, and append-only history rows record that resolved lane. Raw history
is secondary data and does not alter current-run assessment or report guidance.

| Lane | Prompt input | Default token cap | Intended use |
| ---- | ------------ | ----------------- | ------------ |
| `triage` | Image only; brief caption request | 200 | Compares plain image-caption output while providing a fast MLX-VLM compatibility and mechanical output check. |
| `blind` | Image only; structured title, description, and keywords request | 1000 | Exercises unaided visual cataloguing. Existing metadata, including EXIF capture date and GPS, is withheld from the model and current-run assessment. |
| `assisted` | Image plus descriptive title, description, or keyword hints | 1000 | Measures metadata-assisted visual verification and correction. Explicit selection requires descriptive metadata. |

`--eval-mode auto` selects `assisted` when descriptive title, description, or
keywords are available and `blind` otherwise. The retired `stress` and
`quality` aliases are rejected with an actionable error naming the current
lanes.

Blind and assisted lanes expose different prompt context. Blind runs exercise
unaided cataloguing; assisted runs ask a model to verify and improve fallible draft
metadata while retaining authoritative location and capture context when present.
Existing title, description, and keywords are editable hints, not ground truth.
Literal omission of an optional hint term is evidence, not by itself a fault.

A custom `--prompt` overrides the lane prompt only. The resolved lane still
governs the default `--max-tokens` cap and how the run is labeled in reports
and JSONL, and `--eval-mode assisted` still requires descriptive metadata even
when `--prompt` is supplied; the run logs this interaction explicitly.

### How prompt, lane, and assessment interact

`--eval-mode` chooses the built-in prompt and default token budget. `--prompt`
replaces that prompt completely: metadata hints are **not automatically appended**.
`--assessment-profile` chooses how the answer is checked; it does not change what
the model is asked. `--max-tokens` overrides the lane's default budget.

| Options | Prompt sent | Default assessment | Default token cap |
| ------- | ----------- | ------------------ | ----------------- |
| `--eval-mode blind` | Built-in metadata request, no hints | metadata | 1000 |
| `--eval-mode assisted` | Built-in metadata request with hints | metadata | 1000 |
| `--eval-mode triage` | Brief caption request | general | 200 |
| `--prompt "…"` | Exactly your custom prompt | general | 1000 |
| `--eval-mode triage --prompt "…"` | Exactly your custom prompt | general | 200 |
| `--prompt "…" --assessment-profile metadata` | Exactly your custom prompt | metadata (explicit) | Lane default |

An explicit profile wins over the defaults above, independently of the lane.
Metadata assessment expects nonempty Title, Description, and Keywords fields;
it does not infer your requested format from the prompt. For example,
`--eval-mode triage --assessment-profile metadata` is allowed, but asks for a
caption while checking for metadata fields. Supply a suitable custom prompt if
you want that combination. Conversely, `--assessment-profile general` with a
built-in metadata prompt keeps the metadata request but disables field checks.
Neither profile assesses factual accuracy or enforces prose length limits.

With a custom prompt, `auto` still selects and labels the lane based on image
metadata, even though that metadata is not automatically sent to the model.
Explicit `assisted` still rejects images without descriptive metadata. The startup
log makes the effective choices visible, for example:

```text
Lane: assisted | Prompt: custom (no automatic hints) | Assessment: general | Max tokens: 1000
```

### Triage lane versus triage reruns

`--eval-mode triage` selects the first-pass lane for every model, with a default
200-token cap; explicit prompt, profile, and token-cap options still win.

`--rerun-triage` instead adds secondary attempts for selected problematic models
after the first pass. Those attempts **override** the first-pass prompt with the
brief caption request, assessment with **general**, token cap with **100**,
temperature with **0**, timeout with **60 seconds**, and verbose output with
**off**. Other settings, including `--isolate`, are retained. Original results
are never overwritten; the reruns supply additional evidence. These overrides
apply even when the first pass explicitly selected a different profile or budget.

### Prompt burden

Prompt burden is reported independently from quality as `visual input` (image or
estimated non-text tokens dominate), `text` (text tokens dominate), `mixed`
(both materially contribute), `normal`, or `unavailable` when the upstream stack
does not expose enough component measurements. Estimates stay labelled as
estimates; missing components remain `null` rather than being inferred as normal.

```bash
# Compare models as plain image captioners
python -m check_models --image photo.jpg --eval-mode triage

# Compare models without exposing any existing metadata to them
python -m check_models --image photo.jpg --eval-mode blind

# Verify and improve existing descriptive metadata
python -m check_models --image photo.jpg --eval-mode assisted
```

## Command Line Reference

| Flag | Type | Default | Description |
| ---- | ---- | ------- | ----------- |
| `-f`, `--folder` | Path | omitted | Folder to scan (non-recursive); the most recently modified image in that folder is used. If both `--folder` and `--image` are omitted, the most recently modified image in `~/Pictures/Processed` is used. |
| `-i`, `--image` | Path | omitted | Path to a specific image file to process directly. Requires a value when provided. |
| `--image-source-url` | URL | omitted | Public HTTP(S) location of the exact local image used by the run; recorded for issue reproduction only and never downloaded as the inference input. |
| `--output-dir` | Path | `output/` | Root directory for the canonical artifact layout: `index.md`, `results.jsonl`, `results.history.jsonl`, `check_models.log`, and `environment.log` at the root; `results.html`, `model_gallery.md`, and `diagnostics.md` under `reports/`; conditional issue drafts under `issues/`. |
| `--compare-with` | str | `auto` | Baseline sweep to diff this run against, as a `comparison` block in the retained `results.jsonl` metadata, a terminal summary, and a "Since the baseline sweep" section in `run_summary.md` (whenever that summary is produced). Runs must be like-for-like — same prompt, image, evaluation lane, and generation settings, checked against the baseline's retained metadata from the same source — otherwise the per-model diff is withheld and the reasons are listed; model revision changes are reported alongside the diff. Contents: per-model execution/usability/observation transitions, byte-identical generated text count, generation tok/s ratios with per-model noise bands from `results.history.jsonl` (Tukey fence over the last 10 same-prompt runs; fixed ±15% when history is thin), and peak-memory moves beyond 0.5 GB and 10%. `auto` uses the retained `results.jsonl` at git `HEAD` when the output path is tracked (the last committed sweep) and silently does nothing otherwise; `none` disables; a path reads that `results.jsonl`; any other value is a git ref for the same repo-relative path. A schema-2 baseline is rejected by the single schema-3 loader: that first comparison is skipped with a logged reason and the next schema-3 run establishes the new baseline. |
| `--link-style` | str | `github` | Link format for local-navigation Markdown artifacts: `github` uses canonical repository URLs; `relative` uses offline-friendly local paths. Issue-ready cross-file links remain canonical GitHub URLs in either mode so pasted issue text keeps working. |
| `-m`, `--models` | list[str] | (none) | Explicit model IDs/paths; disables cache discovery. May be repeated; model lists accumulate across occurrences. |
| `-e`, `--exclude` | list[str] | (none) | Models to exclude (applies to cache scan or explicit list). May be repeated; exclusions accumulate across occurrences. |
| `--trust-remote-code` / `--no-trust-remote-code` | flag | `True` | Allow/disallow custom code from Hub models. Use `--no-trust-remote-code` for security. |
| `--revision` | str | (none) | Model revision (branch, tag, or commit) for reproducible runs. |
| `--adapter-path` | str | (none) | Path to LoRA adapter weights to apply on top of the base model. |
| `-p`, `--prompt` | str | omitted | Custom prompt text. Requires a value when provided; if omitted, the `--eval-mode` lane supplies the prompt. When provided, it overrides the lane prompt only: the lane still governs the default token cap and report labeling, and `assisted` still requires descriptive metadata. |
| `--resize-shape` | int(s) | (none) | Resize image input before processor handling. Provide 1 integer for square resize or 2 for height width after one flag occurrence. |
| `--eos-tokens` | list[str] | (none) | Additional EOS tokens to stop on. Supports escaped values like `\n`. May be repeated; token lists accumulate across occurrences. |
| `--skip-special-tokens` | flag | `False` | Skip tokenizer special tokens in the detokenized output. |
| `--processor-kwargs` | JSON | (none) | Extra processor kwargs as a JSON object. Example: `'{"cropping": false, "max_patches": 3}'`. |
| `--enable-thinking` | flag | `False` | Enable thinking mode in the upstream chat template and generation flow. |
| `--thinking-budget` | int | (none) | Maximum number of thinking tokens before forcing the end token. |
| `--thinking-start-token` | str | (none) | Token marking the start of a thinking block, such as `<think>`. |
| `--thinking-end-token` | str | `</think>` | Token marking the end of a thinking block when thinking mode is enabled. |
| `--auto-thinking-budget` | flag | `True` | When no explicit thinking flags and no `--thinking-mode` are given, cap thinking for models whose chat template leaves a thinking block open (final start marker unmatched — closed blocks and literal mentions are ignored): budget = max-tokens − 200 (skipped when that leaves under 128). Other models are unaffected and the chat template itself is never altered. The effective per-model budget is recorded in prompt diagnostics and native repro commands. Disable with `--no-auto-thinking-budget`. |
| `--system-telemetry` | flag | snapshot | macOS thermal/memory-pressure telemetry via read-only `pmset -g` / `sysctl -n` probes (sudo-free, no system settings changed). Default: one snapshot probe pair per model taken outside timed inference. Pass `--system-telemetry` for opt-in continuous background sampling (subprocesses overlap timed inference), or `--no-system-telemetry` to disable entirely. Per-probe sample counts are recorded so an unavailable probe is reported as unavailable, never as clean. |
| `--eval-mode` | str | `auto` | One resolved lane per run: `auto` selects `assisted` when descriptive metadata exists and `blind` otherwise; `triage` requests a brief compatibility caption; `blind` requests structured cataloguing without metadata hints; `assisted` supplies descriptive metadata for visual verification. The retired `stress`/`quality` inputs are rejected. |
| `-x`, `--max-tokens` | int | lane default | Max new tokens to generate. When omitted, the resolved evaluation lane supplies the default (1000; `triage` 200); an explicit value always wins over the lane default. |
| `-t`, `--temperature` | float | 0.0 | Sampling temperature. |
| `--top-p` | float | 1.0 | Nucleus sampling parameter (0.0-1.0); lower = more focused. |
| `--min-p` | float | 0.0 | Minimum-probability sampling floor (0.0-1.0). 0.0 disables min-p filtering. |
| `--top-k` | int | 0 | Top-k sampling limit. 0 disables top-k filtering. |
| `--seed` | int | (none) | Seed forwarded to upstream generation sampling. |
| `-r`, `--repetition-penalty` | float | (none) | Penalize repeated tokens (>1.0 discourages repetition). |
| `--repetition-context-size` | int | 20 | Context window size for repetition penalty. |
| `--presence-penalty` | float | (none) | Additive penalty for tokens that already appeared in generated context. |
| `--presence-context-size` | int | 20 | Context window size for presence penalty. |
| `--frequency-penalty` | float | (none) | Additive penalty scaled by token frequency in generated context. |
| `--frequency-context-size` | int | 20 | Context window size for frequency penalty. |
| `--logit-bias` | JSON | (none) | OpenAI-style token-id bias object, for example `'{"42": -1.5}'`. |
| `-L`, `--lazy-load` | flag | `False` | Use lazy loading (loads weights on-demand, reduces memory). |
| `--force-download` | flag | `False` | Force mlx-vlm/Hugging Face Hub to download model files instead of using cache. |
| `--quantize-activations` | flag | `False` | Enable mlx-vlm activation quantization during model loading when supported. |
| `--max-kv-size` | int | (none) | Maximum KV cache size (limits memory for long sequences). |
| `-b`, `--kv-bits` | number | (none) | Quantize KV cache to N bits; uniform supports `2`, `3`, `4`, `5`, `6`, or `8`, and fractional values use TurboQuant. |
| `--kv-quant-scheme` | str | `uniform` | KV cache quantization backend: `uniform` or `turboquant`. |
| `-g`, `--kv-group-size` | int | 64 | Quantization group size for KV cache. |
| `--quantized-kv-start` | int | 5000 | Start position for KV cache quantization. |
| `--prefill-step-size` | int | 4096 | Step size for prompt prefill. |
| `-T`, `--timeout` | float | 300 | Operation timeout (seconds) for model execution. |
| `-v`, `--verbose` | flag | `False` | Enable verbose + debug logging. |
| `--no-color` | flag | `False` | Disable ANSI colors in the CLI output. |
| `--force-color` | flag | `False` | Force-enable ANSI colors even if stderr is not a TTY. |
| `--width` | int | (auto) | Force a fixed output width (columns) for separators and wrapping. |
| `-c`, `--quality-config` | Path | (none) | Path to custom quality configuration YAML file. |
| `--assessment-profile` | str | By prompt origin | Checks the answer, not a prompt change: `metadata` for built-in metadata prompts; `general` for custom and triage prompts. Explicit selection overrides this default, independently of `--eval-mode`; secondary `--rerun-triage` attempts always use general. See [option interactions](#how-prompt-lane-and-assessment-interact). |
| `--isolate` | flag | `False` | Run each model in a fresh child interpreter. A native crash (segfault, abort, interpreter-finalization fault) in one model is then recorded as that model's phase-tagged failure — with the signal name and the phase the child reached — instead of ending the sweep. The parent bounds each child by the model timeout plus 120 s start-up/cleanup grace and records an expiry as a phase-tagged timeout, and `--rerun-triage` reruns go through the same boundary. Costs a few seconds of import time per model and frees GPU memory between models; results round-trip through JSON so outputs and reports are identical to in-process runs. Each child starts with cold per-process caches, so treat throughput from isolated and in-process sweeps as separate populations — the JSONL metadata records `execution_mode`, and `--compare-with` says so when the two differ. Like any sweep, keep the machine otherwise idle: concurrent CPU-heavy work (a test suite, type checkers) measurably slows prefill. |
| `--rerun-triage` | flag | `False` | Add secondary attempts for crashed models and completed models with recorded mechanical observations. Overrides prompt (brief caption), assessment (general), token cap (100), temperature (0), timeout (60 s), and verbose output (off); other settings, including `--isolate`, are retained. First-pass results are never overwritten. See [triage versus reruns](#triage-lane-versus-triage-reruns). |
| `-n`, `--dry-run` | flag | `False` | Validate arguments and show what would run without invoking models. |

### Selection Logic

Image selection logic:

1. If neither `--folder` nor `--image` is specified, the script uses the most recently modified image in the default folder (`~/Pictures/Processed`) and logs a diagnostic message.
2. If `--image` is provided, that image is processed directly.
3. If `--folder` is provided, the most recently modified image in the folder is used.

When the selected image is already public, pass its stable URL with
`--image-source-url`. Paste-ready crash reports can then download the exact
input, verify its SHA-256 digest, and run a native mlx-vlm command with the exact
prompt. If the flag is omitted, reports publish the local image's format,
dimensions, byte size, and digest, state that the original is unavailable, and
do not present a misleading runnable command.

Model selection logic:

1. No model selection flags: run cached repos that match the `mlx-vlm` server-supported cache filter.
2. `--models` only: run exactly that list.
3. `--exclude` only: run supported cached repos minus excluded.
4. `--models` + `--exclude`: intersect explicit list then subtract exclusions.

The cache filter requires repo type `model`, a cached `main` revision,
`config.json`, `tokenizer_config.json`, and safetensors weights. When
`--models` is omitted, local cached repos skipped by that filter are highlighted
with the reason before the run list. The script also warns about exclusions that
don't match any local cached repo. Use `--dry-run` or `get_cached_model_ids()` to
inspect the filtered set without generation; do not reimplement the scanner.
Agent guidance: `.agents/skills/hf-cache-mlx-vlm-models/SKILL.md`.

List-valued CLI flag semantics:

1. `--models`, `--exclude`, and `--eos-tokens` may be repeated; repeated occurrences accumulate values in order.
2. `--resize-shape` remains a single structured value; provide it after one flag occurrence.

## Output Formats

### CLI Output

Real-time colorized output showing:

- Model processing progress with success/failure indicators
- Performance metrics (tokens/second, memory usage, timing)
- Generated text preview
- Error diagnostics for failed models
- Final one-model-per-row performance summary table

The compact performance header is `#`, `Model`, `E/U`, `Val`, `Load`, `Prep`,
`First`, `Remain`, `Clean`, `Total`, `TPS`, and `GB`. `E/U` abbreviates the
execution/usability axes using the legend printed above the table. Timing columns
are seconds: `Val` is local input validation, `Load` is model load, `Prep` is local
preflight/chat-template preparation, and `First` is mlx-vlm's model-loop
prefill/first-token timing (which excludes `prepare_inputs()`). `Remain` is the rest
of the measured generation call after `First`, so it deliberately combines image
and other input preparation with token decoding rather than attributing that time
to either one without a dedicated upstream measurement. `Clean` and `Total` are
cleanup and end-to-end time; `TPS` is generation throughput and `GB` is peak memory.

Color conventions:

- Identifiers (file/folder paths and model names) are shown in magenta for quick scanning.
- Failures are shown in red; the compact CLI table also highlights failed model names in red.

Width and color controls:

- Colors are enabled by default on TTYs. You can override with flags or environment variables:
  - Disable colors: `--no-color` or set `NO_COLOR=1`
  - Force-enable colors (even when not a TTY): `--force-color` or set `FORCE_COLOR=1`
- Output width is auto-detected and clamped for readability. You can force a specific width:
  - Use `--width 100` to render at 100 columns
  - Or set `MLX_VLM_WIDTH=100`
  These affect separator lengths and line wrapping for previews and summaries.

### HTML Report

Report featuring:

- Executive summary with test parameters
- Compact performance table with expandable complete output
- Model search plus exact execution, usability, and maintainer-status filters
- Model outputs and diagnostics
- System information and library versions
- Failed rows are highlighted in red for quick identification
- Assessment values use the same three status vocabularies as the Markdown and
  machine-readable artifacts.
- Responsive design for mobile viewing

### Gallery Markdown Report

GitHub-compatible evidence artifact with:

- Populated image metadata fields when present (title, description, keywords, date, time, GPS)
- The full prompt in a fenced `text` block
- One facts-only current-run chooser with concise output previews
- An orientation-corrected reference preview, bounded to 1024 pixels, beside the
  report for portable side-by-side review without copying a large source image
- One easy-to-scan section per model with inert preformatted readable output and the exact
  captured text in an expandable, dynamically fenced raw block
- The exact execution, usability, maintainer status, observations, timing, memory,
  and token facts used by the HTML report

### JSONL Report

Line-delimited JSON for streaming ingestion:

- **Metadata header**: The first record (line 1) carries the complete run-level
  contract — prompt plus its SHA-256 digest, system info, timestamp, total
  runtime, outcome counts, artifact paths, producer identity, source-image
  facts, common generation settings, remote-code policy, versions, component
  install/source provenance, and the baseline comparison — JSONL `3.0` format.
- **Per-model records**: One JSON object per model with schema `3.0` assessment,
  exact observation details, actual completion timestamp, complete evidence, raw
  timing/resource facts (including allocator state after cleanup even for crashes),
  per-prompt token burden, run arguments, error details, and
  requested/resolved model snapshot provenance when locally available.


### Diagnostics Report

A comprehensive Markdown report focused on upstream debugging and issue reporting:

- **Generation**: Created automatically when crashes, mechanical observations,
  indeterminate attempts, or preflight compatibility warnings are detected.
- **Hard crashes**: Expands each actionable crash with traceback-first complete evidence.
- **Other evidence**: Collapses complete observed and indeterminate evidence, with
  generated output included once as exact code evidence; completions passing
  mechanical checks contribute only compact runtime and performance context.
- **Neutral observations**: Records declared EOS/thinking wrappers and draft fields
  returned unchanged exactly as captured, without assigning fault or a quality score.
- **Reproducibility**: Records the prompt, highlighted model revisions, common
  settings, environment, and one parameterised single-model reproduction once.
- **Issue readiness**: Successful thinking-token or context-boundary observations
  remain visible with complete evidence but require controlled reproduction.
- **Ready-to-file**: Each actionable hard crash gets a factual draft that can be
  copied directly into a GitHub issue.

### Preflight Compatibility Warnings

Some runs emit preflight compatibility warnings before inference starts. These warnings are informational by default.

- **What they mean**: `check_models` detected an upstream package or API-compatibility pattern that may matter for this environment or version combination.
- **What you should do**: keep running if outputs look healthy; investigate when the same run also shows API mismatches, startup hangs, or backend/runtime crashes.
- **What you should not do**: do not treat the warning alone as a failed benchmark.
- **When filing issues**: include the warning text and reported library versions so upstream maintainers can match it to the correct compatibility window.

## Metrics Tracked

The script tracks and reports:

- **Token Metrics**: Prompt tokens, generation tokens, total processing
- **Speed Metrics**: Tokens per second for prompt processing and generation
- **Memory Usage**: Peak memory consumption during processing
- **Timing**: Total processing time per model
- **Success Rate**: Model success/failure statistics
- **Error Analysis**: Detailed error reporting and diagnostics

## Troubleshooting

### Diagnostics

If neither `--folder` nor `--image` is specified, the script logs a diagnostic message indicating that it is using the most recently modified image in the default folder. This makes the omission behavior explicit without implying that `--folder` or `--image` can be passed without values.

### Common Issues

**No models found**: Ensure MLX-compatible VLMs are downloaded to your Hugging Face cache

```bash
# Download a model explicitly
huggingface-cli download microsoft/Phi-3-vision-128k-instruct
```

**Import errors**: Verify MLX installation on Apple Silicon Mac

```bash
pip install --upgrade mlx mlx-vlm
```

**Timeout errors**: Increase timeout for large models

```bash
python -m check_models --timeout 600  # 10 minutes
```

**Memory errors**: Test models individually or exclude large models

```bash
python -m check_models --exclude "meta-llama/Llama-3.2-90B-Vision-Instruct"
```

**Script crashes with mutex error**: If you see `libc++abi: terminating due to uncaught exception of type std::__1::system_error: mutex lock failed: Invalid argument`, TensorFlow is installed and conflicting with MLX.

Uninstall TensorFlow completely in MLX-only environments:

```bash
pip uninstall -y tensorflow tensorboard keras absl-py astunparse flatbuffers gast google_pasta grpcio h5py libclang ml_dtypes opt_einsum termcolor wrapt tensorboard-data-server
```

### Debug Mode

Use `--verbose` for detailed diagnostics:

```bash
python -m check_models --verbose
```

This provides:

- Detailed model loading information
- EXIF metadata extraction details
- Performance metric breakdowns
- Error stack traces
- Library version information

### Framework Detection Notes

- PyTorch is allowed by default; some models require it.
- `sentence-transformers` is not part of the normal `check_models` path.
- TensorFlow is not managed by `check_models`; if it is installed and you hit
  Apple Silicon mutex crashes, remove TensorFlow from the environment.

**Why this matters**: TensorFlow's Abseil mutex implementation can conflict with
MLX on macOS/ARM, causing crashes. Most MLX VLM workflows do not need
TensorFlow.

## Notes

- **Platform**: Requires macOS with Apple Silicon for MLX support
- **Colors**: Uses ANSI color codes for CLI output (may not display correctly in all terminals)
- **Timeout**: Unix-only functionality (not available on Windows)
- **Security**: The `--trust-remote-code` flag allows arbitrary code execution from models
- **Performance**: First run may be slower due to model compilation and caching

## Project Structure

```text
check_models/
├── src/
│   ├── check_models.py      # Main script
│   ├── Makefile             # Package-local automation targets
│   ├── pyproject.toml       # Project configuration and dependencies
│   ├── tools/               # Helper scripts
│   ├── tests/               # PyTest test suite
│   └── output/              # Versioned benchmark snapshots
│       ├── index.md          # Tiny current-run artifact index
│       ├── reports/
│       │   ├── results.html
│       │   ├── model_gallery.md
│       │   └── diagnostics.md
│       ├── results.jsonl
│       ├── results.history.jsonl
│       ├── check_models.log
│       ├── environment.log
│       └── issues/
│           ├── run_summary.md # Conditional paste-ready whole-run issue
│           └── issue_*.md     # Conditional hard-crash drafts
├── docs/                    # Documentation
└── Makefile                 # Root orchestration
```

**Output behaviour**: By default, production outputs are written to `src/output/`
and committed as public benchmark snapshots. Manual validation and debug runs
use the `test_*` prefix under `src/output/` (for example
`--output-dir output/test_probe`), which is git-ignored. Tracked
production Markdown reports are linted by the quality gate; use the `test_` prefix
for local validation and do not commit ad-hoc debug output.
Validation tests must not rewrite tracked `src/output/` assets; pytest writes
report and log paths to a temp directory (`tmp_path`) so verification does not
require restoring benchmark snapshots.
Relocate the whole layout with `--output-dir`. The tiny `index.md` and
append-only raw history are derived inside the same root. HTML, gallery
Markdown, and diagnostics live in `<output-dir>/reports/`; JSONL, history,
logs, and the index remain at the root.

## Contributing

**For detailed contribution guidelines, coding standards, and project conventions, see:**

- [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) - Setup, workflow, and PR process
- [docs/IMPLEMENTATION_GUIDE.md](../docs/IMPLEMENTATION_GUIDE.md) - Coding standards and architecture

### Developer Workflow (Makefile)

Use the root `Makefile` from the repository root and activate the conda env first:

```bash
conda activate mlx-vlm
```

Key commands:

- `make install` — install runtime package (`pip install -e src/`)
- `make dev` — install dev setup (`pip install -e "src/[dev,extras,torch]"`)
- `make test` — run pytest only; useful for a faster test loop before the full gate
- `make vulture` — run the configured dead-code scan for `src/check_models.py` and `src/tools/`
- `make probe-python-next` — check whether the next Python release is viable for the MLX stack in a throwaway conda env
- `make quality` — full gate (ruff format+lint, mypy, ty, pyrefly, vulture, Skylos quality/secrets/SCA plus `-a` audit, full pytest, shellcheck, markdownlint)
- `make skylos-danger` — advisory Skylos `--danger` scan for workflow and security findings
- `make skylos-danger-llm` — advisory Skylos `--danger` scan with LLM-oriented output for agent triage
- `make skylos-verify` — narrow `skylos verify` wrapper for file/range agent checks
- `make ci` — strict CI-style pipeline
- `make deps-sync` — sync dependency blocks in docs from `pyproject.toml`
- `python -m tools.update_readme_deps --check` — verify dependency blocks are already synced (no writes)

In VS Code, run the checked-in `Make: vulture` task to map Vulture findings
into `warning` entries in the Problems panel. The repo does not attach the
matcher to the broader `Make: quality` task, because mixed tool output can
create noisy or stale Problems entries. The repo does not auto-run Vulture on
save; rerun it after larger refactors or deletions.

For package-local targets (for example `install-dev`, `bootstrap-dev`, `lint-fix`), run:

```bash
make -C src help
```

### Git Hooks and Pre-Commit

Recommended workflow:


Alternative workflow:

- `pre-commit` framework:

  ```bash
  pre-commit install
  pre-commit run --hook-stage pre-push --all-files
  ```

Both workflows call the same shared scripts:

- commit stage: staged-file hygiene only
- push stage: fast static checks, Vulture, plus `pytest -m "not slow and not e2e"`

The push-stage gate also validates the checked-in GitHub workflow YAML and
keeps the CI/static tooling path aligned with the checked-in scripts.

### Markdown Linting (Optional)

`make quality` runs markdownlint via local install, global install, or `npx` fallback.
If you want a local install:

```bash
cd src
npm install
```

### Contribution Guidelines

- Keep patches focused; separate mechanical formatting changes from functional changes.
- Run `make quality` before opening a PR. It already includes the full pytest
  suite; use `make test` separately only for a pytest-only local loop.
- Run `make skylos-danger` when a change touches GitHub Actions, shell helpers,
  or other repo-controlled security surfaces. Use `make skylos-danger-llm` when
  an AI/code-review agent should consume the same findings with nearby code
  context.
- Run `make skylos-verify ARGS='--file ... --range ...'` for the cheapest
  post-edit AI-defect verification pass before falling back to broader scans.
- Add or update tests when changing output formatting or public CLI flags.
- Prefer small helper functions over adding more branching to large blocks in `check_models.py`.
- Document new flags or output changes in this README (search for an existing section to extend rather than creating duplicates).
- For full conventions (naming, imports, dependency policy, quality gates), see `IMPLEMENTATION_GUIDE.md` in `docs/`.

## Important Notes

- Timeout functionality requires UNIX (not available on Windows).
- For best results, ensure all dependencies are installed and models are downloaded/cached.

## License

MIT License: See the [LICENSE](../LICENSE) file for details.
