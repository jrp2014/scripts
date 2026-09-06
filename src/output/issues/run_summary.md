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

- *Run started:* 2026-09-06 22:16:29 BST
- *Run finished:* 2026-09-06 22:21:22 BST
- *Run duration:* 4m 52s
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

- *Baseline:* 1ceac9f3:src/output/results.jsonl
- *Baseline run timestamp:* 2026-09-06 19:51:43 BST
- *Baseline check_models:* 0.17.13 @ 84dae61da
- *Baseline mlx:* 0.32.3.dev20260906+ce916dbbc @ ce916dbbc
- *Baseline mlx-vlm:* 0.7.0rc0 @ d5064772d
- *Baseline transformers:* 5.16.1
- *Baseline python:* 3.14.7
- *Baseline hardware:* Apple M5 Max, 40 GPU cores, 128.0 GB RAM
- *Models compared:* 34
- *Identical generated text:* 33 of 34 completed in both
- *Generation tok/s ratio (now/baseline):* 1.001 (range 0.91-1.03, 32 models)
- *Throughput noise band:* fixed ±15% fallback (insufficient history)

| Model | Execution | Usability | Observation delta |
| --- | --- | --- | --- |
| mlx-community/Step-3.7-Flash-oQ3e | completed | concerns detected → major concerns | +answer emitted twice |

Mechanical diff only: one image, temperature as configured; single-observation
flips on one model are usually run-to-run variance, broad shifts are not.

## Model quality at a glance

Every attempted model ranked by mechanical observations, with captured
resource facts. No concerns detected is not a task-compliance or accuracy
verdict. Consult the assessment scope above and inspect the final answers.
Crashes and integration signals have expanded maintainer evidence.

| Model | Mechanical checks | Total | Gen tok/s | Peak GB | Observed |
| --- | --- | --- | --- | --- | --- |
| mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit | no concerns detected | 6.01s | 31.3 tok/s | 20 | none |
| mlx-community/diffusiongemma-26B-A4B-it-mxfp8 | no concerns detected | 5.01s | 51.2 tok/s | 28 | none |
| mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit | no concerns detected | 4.91s | 141 tok/s | 18 | none |
| mlx-community/gemma-3-27b-it-qat-4bit | no concerns detected | 5.84s | 31.9 tok/s | 17 | none |
| mlx-community/gemma-4-26b-a4b-it-4bit | no concerns detected | 3.28s | 131 tok/s | 16 | none |
| mlx-community/gemma-4-31b-it-4bit | no concerns detected | 6.32s | 28.1 tok/s | 19 | none |
| mlx-community/GLM-4.6V-Flash-4bit | no concerns detected | 2.06s | 89.5 tok/s | 8.0 | none |
| mlx-community/granite-4.0-3b-vision-4bit | no concerns detected | 1.25s | 191 tok/s | 4.7 | none |
| mlx-community/InternVL3-8B-bf16 | no concerns detected | 4.54s | 34.4 tok/s | 17 | none |
| mlx-community/Kimi-VL-A3B-Thinking-2506-8bit | no concerns detected | 7.22s | 73.8 tok/s | 20 | none |
| mlx-community/LFM2.5-VL-1.6B-bf16 | no concerns detected | 1.21s | 190 tok/s | 4.0 | none |
| mlx-community/LFM2.5-VL-3B-OptiQ-4bit | no concerns detected | 1.30s | 218 tok/s | 3.6 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-mxfp4 | no concerns detected | 3.23s | 70.0 tok/s | 9.8 | none |
| mlx-community/Ministral-3-14B-Instruct-2512-nvfp4 | no concerns detected | 3.71s | 67.3 tok/s | 10 | none |
| mlx-community/Ministral-3-3B-Instruct-2512-4bit | no concerns detected | 1.66s | 205 tok/s | 4.5 | none |
| mlx-community/Molmo2-8B-4bit | no concerns detected | 2.83s | 74.2 tok/s | 8.5 | none |
| mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit | no concerns detected | 3.97s | 109 tok/s | 24 | none |
| mlx-community/Phi-3.5-vision-instruct-bf16 | no concerns detected | 2.75s | 59.7 tok/s | 9.3 | none |
| mlx-community/pixtral-12b-8bit | no concerns detected | 4.66s | 40.4 tok/s | 15 | none |
| mlx-community/Qwen3.5-35B-A3B-4bit | no concerns detected | 3.60s | 127 tok/s | 21 | none |
| mlx-community/Qwen3.5-9B-MLX-4bit | no concerns detected | 2.30s | 101 tok/s | 7.0 | none |
| mlx-community/Qwen3.8-27B-4bit | no concerns detected | 5.38s | 33.3 tok/s | 17 | none |
| mlx-community/Qwen3.8-Flash-Next-4bit | no concerns detected | 111.61s | 32.5 tok/s | 113 | none |
| mlx-community/SmolVLM2-2.2B-Instruct-mlx | no concerns detected | 1.33s | 127 tok/s | 5.4 | none |
| LiquidAI/LFM2.5-VL-450M-MLX-bf16 | concerns detected | 0.65s | 520 tok/s | 1.3 | duplicate keywords |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | 8.88s | 53.6 tok/s | 63 | control tokens visible |
| mlx-community/North-Micro-Vision-Instruct-4bit | concerns detected | 1.61s | 276 tok/s | 3.3 | duplicate keywords |
| mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit | concerns detected | 2.96s | 130 tok/s | 19 | duplicate keywords |
| mlx-community/Idefics3-8B-Llama3-bf16 | major concerns | 3.30s | insufficient sample | 18 | labelled fields not detected |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | major concerns | 42.23s | 26.1 tok/s | 25 | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords |
| mlx-community/nanoLLaVA-1.5-4bit | major concerns | 0.79s | 397 tok/s | 1.5 | labelled fields not detected |
| mlx-community/Qwen3-VL-2B-Thinking-bf16 | major concerns | 3.93s | 135 tok/s | 5.3 | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| mlx-community/Step-3.7-Flash-oQ3e | major concerns | 18.42s | 54.3 tok/s | 87 | answer emitted twice; control tokens visible |
| mlx-community/X-Reasoner-7B-8bit | major concerns | 7.23s | 65.6 tok/s | 10 | repeated text; stopped early: repeating; duplicate keywords |

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
| Final answer emitted twice; Unrecognised model control tokens remain visible | 1 |
| Unrecognised model control tokens remain visible | 1 |
| Required labelled fields not detected; Response appears cut off at the token limit; Conversation-role control tokens remain visible; Repeated keyword entries | 1 |

## Completed attempts requiring review

| Model | Mechanical checks | Observed result | Evidence |
| --- | --- | --- | --- |
| mlx-community/Qwen3-VL-2B-Thinking-bf16 | major concerns | Response repeats the same text; Generation was stopped early after sustained repeated output; Required labelled fields not detected: title, description; Internal reasoning block appears incomplete; Duplicate keywords: resting, couch, cat, tabby, pink, remote | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-qwen3-vl-2b-thinking-bf16) |
| mlx-community/X-Reasoner-7B-8bit | major concerns | Response repeats the same text; Generation was stopped early after sustained repeated output; Duplicate keywords: feline pink couch with remote control, feline rest on pink couch with remote control, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-x-reasoner-7b-8bit) |
| mlx-community/Step-3.7-Flash-oQ3e | major concerns | Final answer emitted twice, around &lt;/think&gt;; Unrecognised model control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-step-37-flash-oq3e) |
| mlx-community/GLM-4.6V-nvfp4 | concerns detected | Unrecognised model control tokens remain visible | [diagnostics](https://github.com/jrp2014/check_models/blob/main/src/output/reports/diagnostics.md#diagnostic-mlx-community-glm-46v-nvfp4) |
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
- *check_models version:* 0.17.15
- *check_models revision:* 1ceac9f361ec6d8513562746fbc24dd2c11ec335
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
