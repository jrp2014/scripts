---
name: hf-cache-mlx-vlm-models
description: >
  List or reason about local Hugging Face cache models under check_models
  default discovery: the mlx-vlm server-style cache-layout filter plus a
  second image-capability classification. Use for cache-dir questions,
  skipped-repo reasons, dry-run model lists, or aligning discovery with
  /v1/models. Neither layer is a generation proof. This repo uses conda + pip,
  never uv.
---

# HF Cache Models (layout filter + image capability)

Default `check_models` discovery has **two independent layers**:

1. the **mlx-vlm server cache-layout filter** (files present), which tracks
   the server's opt-in `--model-discovery hf-cache` mode for `/v1/models`
   (upstream #2076; the default `served` listing does not scan the cache); and
2. an **image-capability classification** of what the cached repo *is*, which
   is the benchmark's actual requirement.

The layout filter alone is no longer proof of VLM suitability: mlx-vlm now
also hosts text-only, embedding, reranking, drafter, and image/audio
generation models whose repos pass the file test. A repo is **selected** only
when it passes the layout filter **and** its capability is not a confident
`no`.

Adapted from the upstream `hf-cache-models` skill
([`skills/skills/hf-cache-models`](https://github.com/Blaizzy/mlx-vlm/tree/main/skills/skills/hf-cache-models), added by
[Blaizzy/mlx-vlm#1747](https://github.com/Blaizzy/mlx-vlm/pull/1747); its bundled
`list_supported_hf_cache_models.py` is not copied here because
`get_cached_model_ids()` / `--dry-run` encode the same contract).

## Layer 1: cache-layout rule (server-style)

A cached repo passes the layout filter when **all** of the following hold:

- repo type is `model`
- a `main` revision exists in the cache
- `config.json` is present on that revision
- `tokenizer_config.json` is present
- weights exist as `model.safetensors.index.json` **or** at least one
  `*.safetensors` file

This is a **cache/file-presence** check. It does not load the model or prove
generation works. Layout failures are reported as `cache layout: <reason>`.

## Layer 2: image-capability classification (tri-state)

`_classify_image_capability` reads only bounded snapshot metadata
(`config.json`, and `model_index.json` when present) and returns an
`ImageCapability(verdict, purpose, evidence)`:

- `yes` — positive image-input evidence (`vision_config`, `image_token_id`,
  `image_token_index`, `vision_start_token_id`, … — the keys surveyed across
  every cached VLM family). Purpose `image_to_text`.
- `no` — positive evidence of a different model kind, most specific first:
  `speculators_model_type`, a `model_type` in the installed mlx-vlm's
  `DRAFTER_KIND_BY_MODEL_TYPE` table (unless it is also a full model family,
  as `laguna` is), a `dflash_config.projector_type` of `dspark`, or a
  `dspark`/`dflash`/`eagle3` architecture → speculative drafter; a
  `model_type` whose upstream loader class sets `is_image_generation_model`
  or `is_image_edit_model` (flux2, ideogram4, mage_flow, z_image, …; parsed
  from `models/*/model.py`, adapted from Nativ's capability manifest) →
  image/video generation; `mlx_embeddings.kind=
  embedding` → embedding; sequence-classifier model type/architecture
  (`bert`, `modernbert`, `xlm_roberta`, `*ForSequenceClassification`) →
  reranker; `model_index.json` or pipeline config keys without image keys →
  image/video generation; `audio_config` without image keys → audio-only
  generation; generative architecture with no vision/audio/dflash config →
  text-only (mirrors upstream `_is_text_only_config`).
- `unknown` — insufficient or contradictory evidence (e.g. no readable
  config, unfamiliar layout). **Still selected**, with a warning that names
  the evidence, so a new VLM is tried rather than silently excluded.

`id2label`/`num_labels` alone are **not** reranker signals — real VLM configs
carry them. Repo names are never used as evidence.

Skips are reported as `model purpose: <label> (<evidence>)`. Explicit
`--models` overrides the capability filter (the model runs) but logs the
classification so the result is interpreted correctly.

Every cached repo's classification, evidence, and decision is retained in
the `results.jsonl` metadata header under `cache_discovery`, so downstream
tools can distinguish an
intentional non-test from a crash. Skipped non-image models never enter the
per-model results, quality tables, or mlx-vlm failure counts.

Live sites: `ImageCapability`, `_classify_image_capability`,
`_capability_negative_signal`, `CachedModelEligibility.selected` /
`.skip_reasons`, `_cache_discovery_records` in `src/check_models.py`; locked
by `TestImageCapabilityClassifier` / `TestCapabilityAwareSelection` in
`src/tests/test_model_discovery.py`.

## Architecture pre-check (upstream `--check-arch` tier)

`check_models` also mirrors the upstream `hf-cache-models --check-arch` tier:
each cached repo's `config.json` `model_type` (falling back to
`speculators_model_type`, lowercased, with `MODEL_REMAPPING` aliases parsed
from the installed mlx-vlm source — never importing mlx) is compared against
the package directories under the installed `mlx_vlm/models/`.

- `--dry-run` annotates models whose architecture is not supported and prints
  an unsupported-architecture count.
- The per-model gallery/diagnostics fact "Arch supported by installed
  mlx-vlm" and the optional `architecture` record in `results.jsonl` carry the
  same verdict (`model_type`, `resolved_model_type`,
  `supported_by_installed_mlx_vlm`).
- This is a **folder-name check only**: "unsupported" means "probably not
  loadable", never proof. Unsupported models are still attempted so real
  crash evidence is captured; a resulting `Model type {x} not supported.`
  crash classifies as `UNSUPPORTED_ARCH`.

Live sites: `_installed_mlx_vlm_model_types`, `_mlx_vlm_model_remapping`,
`_model_arch_precheck`, `_arch_precheck_for_model` in `src/check_models.py`;
locked by `src/tests/test_model_discovery.py`.

## Prefer in-repo tools (do not fork cache logic)

```bash
conda activate mlx-vlm

# What default discovery would run (no generation)
cd src && python -m check_models --dry-run

# Or call the same filter helpers used in production/tests
python - <<'PY'
from check_models import get_cached_model_ids
for model_id in get_cached_model_ids():
    print(model_id)
print(f"\n{len(get_cached_model_ids())} supported model(s)")
PY
```

Implementation live site: `get_cached_model_ids` / eligibility helpers in
`src/check_models.py` under model processing / cache scan. Tests that lock the
filter: `src/tests/test_model_discovery.py`.

When `--models` is omitted, unsupported cached repos should be reported with
skip reasons (for example missing `tokenizer_config.json` or safetensors).

## Optional server cross-check

Only when validating server visibility (not needed for ordinary benchmarks):

```bash
python -m mlx_vlm.server --port 8080 --model-discovery hf-cache
curl -s http://127.0.0.1:8080/v1/models
```

Compare IDs to `get_cached_model_ids()` / `--dry-run`. Do not start the server
for routine `check_models` runs; the harness uses direct generation for
isolation.

## Reporting checklist

When reporting cache contents, include:

- cache directory if non-default (`HF_HOME` / `HUGGINGFACE_HUB_CACHE`)
- count of supported models
- exact model IDs
- whether the list came from `check_models` discovery or from
  `curl …/v1/models`
- skip reasons for excluded cached repos when relevant

## Rules

- **Do not** reimplement `scan_cache_dir` filters in ad-hoc scripts when
  `get_cached_model_ids` already encodes the contract.
- **Do not** use `uv run`.
- Explicit `--models` bypasses the filter and may include unsupported layouts;
  say so when diagnosing “works with --models but not default scan”.
- Cache presence ≠ VLM success; use `native-mlx-vlm-repro` after discovery.
