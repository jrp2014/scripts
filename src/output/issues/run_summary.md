# mlx-vlm compatibility findings across 33 cached vision-language models

**What this run measures.** This run records model responses to one shared
image and prompt (evaluation lane: assisted). Mechanical checks are not
factual-accuracy judgments; inspect the image, prompt and final answers before
choosing a model. Results do not establish fitness for other tasks.
check_models gave every locally cached MLX vision-language model the same
image and the same prompt (reproduced below), through mlx-vlm's generation
pipeline, and recorded mechanical facts about each attempt: whether it ran,
what the selected assessment profile checked (stated under *Assessment*
below), and its speed and memory. There is no semantic quality scoring; every
observation is a reproducible mechanical fact from this one image and prompt.

## Run summary

- *Run started:* 2026-09-06 00:27:13 BST
- *Run finished:* 2026-09-06 00:37:14 BST
- *Run duration:* 10m 01s
- *Evaluation lane:* assisted
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Input image:* JPEG, 9,984 x 5,616 pixels (56.1 MP), 39.4 MB
- *Models attempted:* 33
- *Completed:* 33
- *Crashed:* 0
- *Indeterminate:* 0
- *Crashes requiring action:* 0
- *Other results requiring review:* 3
- *Hit the token cap:* 1
- *Stopped early for repetition:* 1

Observations are mechanical facts from one image, not general model-quality
judgements.

<details>
<summary>Exact prompt sent to every model</summary>

```text
Create British-English catalogue metadata from the image and supplied context.

Treat any capture date/time and GPS as authoritative facts, but do not claim they are visible. Descriptive hints may be incomplete or wrong: retain details supported by the image, correct conflicts, and add important visible details. Prefer image evidence when a hint conflicts, and omit uncertain details.

Context: Authoritative context:
- Capture date/time: 2026-09-01 15:04:11 UTC+01:00
- GPS: 51.380931°N, 2.359317°W

Descriptive hints:
- Description hint: Tourists and visitors sit on benches and stroll through the Abbey Churchyard outside the historic Roman Baths and Grand Pump Room complex in Bath, Somerset, England, on a cloudy day.
- Keyword hints: Abbey Church Yard, Abbey Churchyard, Balustrades, Bath, Bath England, Bath Somerset, Bath stone, Bath stone buildings, Benches, Dome, England, Georgian architecture, Grand Pump Room, Heritage site, Historic architecture, Neoclassical Architecture, Overcast Sky, Pedestrians, Plaza, Public Square

Write:
- a concrete 5-10-word title;
- a 1-2-sentence factual description combining relevant context with the main visible subject, setting, action, lighting, and distinctive details;
- 10-18 unique, comma-separated keywords covering relevant context and visible details.

Return exactly these three sections and nothing else:
Title:
Description:
Keywords:
```

</details>

## Since the baseline sweep

**Not directly comparable** — the per-model diff is withheld because the runs
differ in: prompt differs; image differs (sha256 168b4850b142… →
7e999a8e5f2d…); assessment profile differs (or was not recorded in the
baseline). Treat any difference against this baseline as a change of inputs,
not a change of model or runtime behaviour.

- *Baseline:* 968e7035:src/output/results.jsonl
- *Baseline run timestamp:* 2026-09-04 19:33:10 BST
- *Baseline check_models:* 0.16.8 @ cf87381f7
- *Baseline mlx:* 0.32.3.dev20260904+b6368984b @ b6368984b
- *Baseline mlx-vlm:* 0.7.0rc0 @ 5c9b5f52a
- *Baseline transformers:* 5.16.1
- *Baseline python:* 3.14.7
- *Baseline hardware:* Apple M5 Max, 40 GPU cores, 128.0 GB RAM

## Model quality at a glance

Every attempted model ranked by mechanical observations, with captured
resource facts. No concerns detected is not a task-compliance or accuracy
verdict. Consult the assessment scope above and inspect the final answers.
Crashes and integration signals have expanded maintainer evidence.

| Model | Mechanical checks | Total | Gen tok/s | Peak GB | Observed |
| --- | --- | --- | --- | --- | --- |
| LiquidAI/LFM2.5-VL-450M-MLX-bf16 | no concerns detected | 1.79s | 472 tok/s | 1.7 | none |
| mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit | no concerns detected | 10.86s | 30.5 tok/s | 22 | none |
| mlx-community/diffusiongemma-26B-A4B-it-mxfp8 | no concerns detected | 6.97s | 53.2 tok/s | 28 | none |
| mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit | no concerns detected | 13.54s | 95.6 tok/s | 19 | none |
| mlx-community/gemma-3-27b-it-qat-4bit | no concerns detected | 8.98s | 30.4 tok/s | 17 | none |
| mlx-community/gemma-4-26b-a4b-it-4bit | no concerns detected | 4.34s | 129 tok/s | 16 | none |
| mlx-community/gemma-4-31b-it-4bit | no concerns detected | 7.65s | 26.8 tok/s | 20 | none |
| mlx-community/GLM-4.6V-Flash-4bit | no concerns detected | 8.05s | 77.9 tok/s | 8.7 | none |
| mlx-community/granite-4.0-3b-vision-4bit | no concerns detected | 2.56s | 175 tok/s | 4.8 | none |
| mlx-community/Idefics3-8B-Llama3-bf16 | no concerns detected | 9.49s | 33.2 tok/s | 18 | none |
| mlx-community/InternVL3-8B-bf16 | no concerns detected | 6.36s | 34.8 tok/s | 17 | none |
| mlx-community/Kimi-VL-A3B-Thinking-2506-8bit | no concerns detected | 11.64s | 66.8 tok/s | 20 | none |
| mlx-community/LFM2.5-VL-1.6B-bf16 | no concerns detected | 2.76s | 189 tok/s | 4.0 | none |
| mlx-community/LFM2.5-VL-3B-OptiQ-4bit | no concerns detected | 2.38s | 207 tok/s | 4.0 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-mxfp4 | no concerns detected | 5.94s | 66.9 tok/s | 12 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-nvfp4 | no concerns detected | 6.59s | 64.8 tok/s | 12 | none |
| mlx-community/Ministral-3-3B-Instruct-2512-4bit | no concerns detected | 3.93s | 192 tok/s | 6.4 | none |
| mlx-community/Molmo2-8B-4bit | no concerns detected | 6.62s | 72.5 tok/s | 8.1 | none |
| mlx-community/North-Micro-Vision-Instruct-4bit | no concerns detected | 5.92s | 217 tok/s | 3.9 | none |
| mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit | no concerns detected | 5.50s | 104 tok/s | 24 | none |
| mlx-community/Phi-3.5-vision-instruct-bf16 | no concerns detected | 4.45s | 56.0 tok/s | 9.3 | none |
| mlx-community/pixtral-12b-8bit | no concerns detected | 6.76s | 39.6 tok/s | 15 | none |
| mlx-community/Qwen3-VL-2B-Thinking-bf16 | no concerns detected | 30.27s | 89.5 tok/s | 8.4 | none |
| mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit | no concerns detected | 63.27s | 87.1 tok/s | 23 | none |
| mlx-community/Qwen3.5-35B-A3B-4bit | no concerns detected | 58.66s | 109 tok/s | 24 | none |
| mlx-community/Qwen3.5-9B-MLX-4bit | no concerns detected | 60.12s | 91.1 tok/s | 10 | none |
| mlx-community/Qwen3.8-27B-4bit | no concerns detected | 80.22s | 30.6 tok/s | 21 | none |
| mlx-community/SmolVLM2-2.2B-Instruct-mlx | no concerns detected | 9.40s | 125 tok/s | 5.4 | none |
| mlx-community/Step-3.7-Flash-oQ3e | no concerns detected | 38.78s | 52.0 tok/s | 92 | none |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | 30.56s | 43.3 tok/s | 78 | control tokens visible |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | major concerns | 53.05s | 24.9 tok/s | 25 | missing required fields; cut off at token limit; role tokens visible |
| mlx-community/nanoLLaVA-1.5-4bit | major concerns | 1.59s | 360 tok/s | 1.7 | missing required fields |
| mlx-community/X-Reasoner-7B-8bit | major concerns | 23.68s | 58.2 tok/s | 14 | repeated text; stopped early: repeating; duplicate keywords |

## Constraint-failure breakdown

How the fleet failed the catalogue constraints — a skew toward one constraint
suggests prompt difficulty rather than individual model faults.

- Duplicate keywords: 1 model(s)

## Observation clusters

Repeated mechanical observation signatures among results requiring review.

| Observed result | Models |
| --- | --- |
| Response repeats the same text; Generation was stopped early after sustained repeated output; Repeated keyword entries | 1 |
| Unrecognised model control tokens remain visible | 1 |
| Required fields are missing or empty; Response appears cut off at the token limit; Conversation-role control tokens remain visible | 1 |

## Completed attempts requiring review

| Model | Mechanical checks | Observed result | Evidence |
| --- | --- | --- | --- |
| mlx-community/X-Reasoner-7B-8bit | major concerns | Response repeats the same text; Generation was stopped early after sustained repeated output; Duplicate keywords: bath somerset, bath stone, georgian architecture, heritage site, balustrades, dome, overcast sky, public square, england, bath england, bath stone buildings | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-x-reasoner-7b-8bit) |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | Unrecognised model control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-glm-46v-nvfp4) |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | major concerns | Missing or empty fields: Title, Description; Response appears cut off at the token limit; Conversation-role control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit) |

## Completions without detected concerns

29 completions without detected concerns (`LiquidAI/LFM2.5-VL-450M-MLX-bf16`, `mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`, `mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`, `mlx-community/GLM-4.6V-Flash-4bit`, `mlx-community/Idefics3-8B-Llama3-bf16`, `mlx-community/InternVL3-8B-bf16`, `mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`, `mlx-community/LFM2.5-VL-1.6B-bf16`, `mlx-community/LFM2.5-VL-3B-OptiQ-4bit`, `mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`, `mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`, `mlx-community/Ministral-3-3B-Instruct-2512-4bit`, `mlx-community/Molmo2-8B-4bit`, `mlx-community/North-Micro-Vision-Instruct-4bit`, `mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`, `mlx-community/Phi-3.5-vision-instruct-bf16`, `mlx-community/Qwen3-VL-2B-Thinking-bf16`, `mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit`, `mlx-community/Qwen3.5-35B-A3B-4bit`, `mlx-community/Qwen3.5-9B-MLX-4bit`, `mlx-community/Qwen3.8-27B-4bit`, `mlx-community/SmolVLM2-2.2B-Instruct-mlx`, `mlx-community/Step-3.7-Flash-oQ3e`, `mlx-community/diffusiongemma-26B-A4B-it-mxfp8`, `mlx-community/gemma-3-27b-it-qat-4bit`, `mlx-community/gemma-4-26b-a4b-it-4bit`, `mlx-community/gemma-4-31b-it-4bit`, `mlx-community/granite-4.0-3b-vision-4bit`, `mlx-community/pixtral-12b-8bit`); 1 more completed with prompt-compliance observations only (not maintainer issues). See the [full model gallery](https://github.com/jrp2014/check_models/blob/main/src/output/reports/model_gallery.md).

## Run context

- *Image:* JPEG, 9,984 x 5,616 pixels, 39,377,657 bytes
- *Generation: max_tokens:* 1000
- *Generation: prefill_step_size:* 2048
- *Generation: temperature:* 0.0
- *Generation: top_p:* 1.0
- *Trust remote code:* true
- *check_models version:* 0.17.7
- *check_models revision:* 968e70359e8423204611a80d4fbc5d41550abc42
- *check_models source dirty:* false
- *mlx-vlm:* 0.7.0rc0
- *mlx-vlm source revision:* d5064772dcd1e31704604f93a873323505ae70d5
- *mlx:* 0.32.3.dev20260905+2d27ab05f
- *mlx source revision:* 2d27ab05fb7dcda69bb3c57abd74c0b3bc9a5a99
- *transformers:* 5.16.1
- *macOS Version:* 26.6.2
- *GPU/Chip:* Apple M5 Max
- *Python Version:* 3.14.7

GitHub links target the repository's mutable main branch; they resolve to this
run's evidence only once these artifacts are committed, and a later run's
commit supersedes them. Pin links to that artifact commit when durable issue
evidence is required.

## Full artifacts

| Artifact | Link |
| --- | --- |
| Diagnostics | [diagnostics.md](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md) |
| Model gallery | [model_gallery.md](https://github.com/jrp2014/check_models/blob/main/src/output/reports/model_gallery.md) |
| Results JSONL | [results.jsonl](https://github.com/jrp2014/check_models/blob/main/src/output/results.jsonl) |
| Environment | [environment.log](https://github.com/jrp2014/check_models/blob/main/src/output/environment.log) |
| Log | [check_models.log](https://github.com/jrp2014/check_models/blob/main/src/output/check_models.log) |
