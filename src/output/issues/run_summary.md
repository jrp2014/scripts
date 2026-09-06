# mlx-vlm compatibility findings across 34 cached vision-language models

**What this run measures.** This run records model responses to one shared
image and prompt (evaluation lane: blind). Mechanical checks are not
factual-accuracy judgments; inspect the image, prompt and final answers before
choosing a model. Results do not establish fitness for other tasks.
check_models gave every locally cached MLX vision-language model the same
image and the same prompt (reproduced below), through mlx-vlm's generation
pipeline, and recorded mechanical facts about each attempt: whether it ran,
what the selected assessment profile checked (stated under *Assessment*
below), and its speed and memory. There is no semantic quality scoring; every
observation is a reproducible mechanical fact from this one image and prompt.

## Run summary

- *Run started:* 2026-09-06 19:46:45 BST
- *Run finished:* 2026-09-06 19:51:42 BST
- *Run duration:* 4m 56s
- *Evaluation lane:* blind
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Input image:* JPEG, 640 x 480 pixels (0.3 MP), 0.2 MB
- *Models attempted:* 34
- *Completed:* 34
- *Crashed:* 0
- *Indeterminate:* 0
- *Crashes requiring action:* 0
- *Other results requiring review:* 5
- *Reached token limit:* 1
- *Incomplete output at token limit:* 1
- *Stopped early for repetition:* 2

Observations are mechanical facts from one image, not general model-quality
judgements.

<details>
<summary>Exact prompt sent to every model</summary>

```text
Create British-English catalogue metadata using only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

Write:
- a concrete 5-10-word title;
- a 1-2-sentence factual description of the main subject, setting, action, lighting, and distinctive details;
- 10-18 unique, comma-separated keywords.

Return exactly these three sections and nothing else:
Title:
Description:
Keywords:
```

</details>

## Since the baseline sweep

**Not directly comparable** — the per-model diff is withheld because the runs
differ in: prompt differs; evaluation lane differs (assisted → blind); image
differs (sha256 7e999a8e5f2d… → dea9e7ef9738…). Treat any difference against
this baseline as a change of inputs, not a change of model or runtime
behaviour.

- *Baseline:* 84dae61d:src/output/results.jsonl
- *Baseline run timestamp:* 2026-09-06 00:37:14 BST
- *Baseline check_models:* 0.17.7 @ 968e70359
- *Baseline mlx:* 0.32.3.dev20260905+2d27ab05f @ 2d27ab05f
- *Baseline mlx-vlm:* 0.7.0rc0 @ d5064772d
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
| mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit | no concerns detected | 6.25s | 31.3 tok/s | 20 | none |
| mlx-community/diffusiongemma-26B-A4B-it-mxfp8 | no concerns detected | 5.16s | 56.5 tok/s | 28 | none |
| mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit | no concerns detected | 4.98s | 139 tok/s | 18 | none |
| mlx-community/gemma-3-27b-it-qat-4bit | no concerns detected | 5.98s | 31.9 tok/s | 17 | none |
| mlx-community/gemma-4-26b-a4b-it-4bit | no concerns detected | 3.38s | 132 tok/s | 16 | none |
| mlx-community/gemma-4-31b-it-4bit | no concerns detected | 6.28s | 28.1 tok/s | 19 | none |
| mlx-community/GLM-4.6V-Flash-4bit | no concerns detected | 2.11s | 89.3 tok/s | 8.0 | none |
| mlx-community/granite-4.0-3b-vision-4bit | no concerns detected | 1.29s | 191 tok/s | 4.7 | none |
| mlx-community/InternVL3-8B-bf16 | no concerns detected | 4.57s | 35.1 tok/s | 17 | none |
| mlx-community/Kimi-VL-A3B-Thinking-2506-8bit | no concerns detected | 7.53s | 73.9 tok/s | 20 | none |
| mlx-community/LFM2.5-VL-1.6B-bf16 | no concerns detected | 1.34s | 191 tok/s | 4.0 | none |
| mlx-community/LFM2.5-VL-3B-OptiQ-4bit | no concerns detected | 1.32s | 218 tok/s | 3.6 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-mxfp4 | no concerns detected | 3.17s | 70.0 tok/s | 9.8 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-nvfp4 | no concerns detected | 3.61s | 67.0 tok/s | 10 | none |
| mlx-community/Ministral-3-3B-Instruct-2512-4bit | no concerns detected | 1.71s | 205 tok/s | 4.5 | none |
| mlx-community/Molmo2-8B-4bit | no concerns detected | 2.86s | 73.6 tok/s | 8.0 | none |
| mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit | no concerns detected | 4.02s | 108 tok/s | 24 | none |
| mlx-community/Phi-3.5-vision-instruct-bf16 | no concerns detected | 2.84s | 58.3 tok/s | 9.3 | none |
| mlx-community/pixtral-12b-8bit | no concerns detected | 4.76s | 40.5 tok/s | 15 | none |
| mlx-community/Qwen3.5-35B-A3B-4bit | no concerns detected | 3.62s | 123 tok/s | 21 | none |
| mlx-community/Qwen3.5-9B-MLX-4bit | no concerns detected | 2.32s | 101 tok/s | 7.0 | none |
| mlx-community/Qwen3.8-27B-4bit | no concerns detected | 5.59s | 33.0 tok/s | 17 | none |
| mlx-community/Qwen3.8-Flash-Next-4bit | no concerns detected | 111.83s | 31.9 tok/s | 113 | none |
| mlx-community/SmolVLM2-2.2B-Instruct-mlx | no concerns detected | 1.48s | 129 tok/s | 5.4 | none |
| LiquidAI/LFM2.5-VL-450M-MLX-bf16 | concerns detected | 0.79s | 530 tok/s | 1.2 | duplicate keywords |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | 9.33s | 53.1 tok/s | 63 | control tokens visible |
| mlx-community/North-Micro-Vision-Instruct-4bit | concerns detected | 1.68s | 269 tok/s | 3.3 | duplicate keywords |
| mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit | concerns detected | 3.00s | 131 tok/s | 19 | duplicate keywords |
| mlx-community/Step-3.7-Flash-oQ3e | concerns detected | 18.38s | 54.1 tok/s | 87 | control tokens visible |
| mlx-community/Idefics3-8B-Llama3-bf16 | major concerns | 3.32s | insufficient sample | 18 | labelled fields not detected |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | major concerns | 42.34s | 26.0 tok/s | 25 | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords |
| mlx-community/nanoLLaVA-1.5-4bit | major concerns | 0.90s | 396 tok/s | 1.5 | labelled fields not detected |
| mlx-community/Qwen3-VL-2B-Thinking-bf16 | major concerns | 3.83s | 134 tok/s | 5.3 | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| mlx-community/X-Reasoner-7B-8bit | major concerns | 8.16s | 65.7 tok/s | 10 | repeated text; stopped early: repeating; duplicate keywords |

## Constraint-failure breakdown

How the fleet failed the catalogue constraints — a skew toward one constraint
suggests prompt difficulty rather than individual model faults.

- Duplicate keywords: 6 model(s)

## Observation clusters

Repeated mechanical observation signatures among results requiring review.

| Observed result | Models |
| --- | --- |
| Response repeats the same text; Generation was stopped early after sustained repeated output; Required labelled fields not detected; Internal reasoning block appears incomplete; Repeated keyword entries | 1 |
| Response repeats the same text; Generation was stopped early after sustained repeated output; Repeated keyword entries | 1 |
| Unrecognised model control tokens remain visible | 2 |
| Required labelled fields not detected; Response appears cut off at the token limit; Conversation-role control tokens remain visible; Repeated keyword entries | 1 |

## Completed attempts requiring review

| Model | Mechanical checks | Observed result | Evidence |
| --- | --- | --- | --- |
| mlx-community/Qwen3-VL-2B-Thinking-bf16 | major concerns | Response repeats the same text; Generation was stopped early after sustained repeated output; Required labelled fields not detected: title, description; Internal reasoning block appears incomplete; Duplicate keywords: resting, couch, cat, tabby, pink, remote | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-qwen3-vl-2b-thinking-bf16) |
| mlx-community/X-Reasoner-7B-8bit | major concerns | Response repeats the same text; Generation was stopped early after sustained repeated output; Duplicate keywords: feline pink couch with remote control, feline rest on pink couch with remote control, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-x-reasoner-7b-8bit) |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | Unrecognised model control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-glm-46v-nvfp4) |
| mlx-community/Step-3.7-Flash-oQ3e | concerns detected | Unrecognised model control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-step-37-flash-oq3e) |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | major concerns | Required labelled fields not detected: title, description; Response appears cut off at the token limit; Conversation-role control tokens remain visible; Duplicate keywords: location, event, brand, species, period, or intent | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit) |

## Completions without detected concerns

24 completions without detected concerns (`mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`, `mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`, `mlx-community/GLM-4.6V-Flash-4bit`, `mlx-community/InternVL3-8B-bf16`, `mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`, `mlx-community/LFM2.5-VL-1.6B-bf16`, `mlx-community/LFM2.5-VL-3B-OptiQ-4bit`, `mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`, `mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`, `mlx-community/Ministral-3-3B-Instruct-2512-4bit`, `mlx-community/Molmo2-8B-4bit`, `mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`, `mlx-community/Phi-3.5-vision-instruct-bf16`, `mlx-community/Qwen3.5-35B-A3B-4bit`, `mlx-community/Qwen3.5-9B-MLX-4bit`, `mlx-community/Qwen3.8-27B-4bit`, `mlx-community/Qwen3.8-Flash-Next-4bit`, `mlx-community/SmolVLM2-2.2B-Instruct-mlx`, `mlx-community/diffusiongemma-26B-A4B-it-mxfp8`, `mlx-community/gemma-3-27b-it-qat-4bit`, `mlx-community/gemma-4-26b-a4b-it-4bit`, `mlx-community/gemma-4-31b-it-4bit`, `mlx-community/granite-4.0-3b-vision-4bit`, `mlx-community/pixtral-12b-8bit`); 5 more completed with prompt-compliance observations only (not maintainer issues). See the [full model gallery](https://github.com/jrp2014/check_models/blob/main/src/output/reports/model_gallery.md).

## Run context

- *Image:* JPEG, 640 x 480 pixels, 173,131 bytes
- *Generation: max_tokens:* 1000
- *Generation: prefill_step_size:* 2048
- *Generation: temperature:* 0.0
- *Generation: top_p:* 1.0
- *Trust remote code:* true
- *check_models version:* 0.17.13
- *check_models revision:* 84dae61da09eabb4ae492c6dc5f66e87a90eedb7
- *check_models source dirty:* false
- *mlx-vlm:* 0.7.0rc0
- *mlx-vlm source revision:* d5064772dcd1e31704604f93a873323505ae70d5
- *mlx:* 0.32.3.dev20260906+ce916dbbc
- *mlx source revision:* ce916dbbcaa88e433b6fd1e60a17f766d49c27fe
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
