# Diagnostics

<!-- markdownlint-disable MD004 MD037 -->

This run records model responses to one shared image and prompt (evaluation
lane: assisted). Mechanical checks are not factual-accuracy judgments; inspect
the image, prompt and final answers before choosing a model. Results do not
establish fitness for other tasks.

## Run Summary

- *Evaluation lane:* assisted
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Input image:* JPEG, 9,984 x 5,616 pixels (56.1 MP), 39.4 MB

Outcome counts

| Outcome             | Count |
|---------------------|-------|
| Attempted           | 33    |
| Conclusive outcomes | 33    |
| Completed           | 33    |
| Crashed             | 0     |
| Indeterminate       | 0     |

Maintainer status counts

| Maintainer status              | Count |
|--------------------------------|-------|
| none                           | 30    |
| observation needs reproduction | 3     |

Usability counts

| Usability           | Count |
|---------------------|-------|
| unusable            | 3     |
| usable              | 29    |
| usable with caveats | 1     |

Observation counts

| Observation                                                  | Count |
|--------------------------------------------------------------|-------|
| Response repeats the same text                               | 1     |
| Generation was stopped early after sustained repeated output | 1     |
| Unrecognised model control tokens remain visible             | 1     |
| Required fields are missing or empty                         | 2     |
| Response appears cut off at the token limit                  | 1     |
| Conversation-role control tokens remain visible              | 1     |
| Repeated keyword entries                                     | 1     |

## Triage

| Model                                                                                              | Execution | Usability           | Maintainer status              | Observations                                                         |
|----------------------------------------------------------------------------------------------------|-----------|---------------------|--------------------------------|----------------------------------------------------------------------|
| [mlx-community/X-Reasoner-7B-8bit](#diagnostic-mlx-community-x-reasoner-7b-8bit)                   | completed | unusable            | observation_needs_reproduction | repeated text; stopped early: repeating; duplicate keywords          |
| [mlx-community/GLM-4.6V-nvfp4](#diagnostic-mlx-community-glm-46v-nvfp4)                            | completed | usable_with_caveats | observation_needs_reproduction | control tokens visible                                               |
| [mlx-community/Muse-Glimmer-30B-OptiQ-4bit](#diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit) | completed | unusable            | observation_needs_reproduction | missing required fields; cut off at token limit; role tokens visible |

## Crashes requiring action

None.

## Completed Runs with Observations

<a id="diagnostic-mlx-community-x-reasoner-7b-8bit"></a>

<details>
<summary>mlx-community/X-Reasoner-7B-8bit — unusable — repeated text; stopped early: repeating; duplicate keywords</summary>

### mlx-community/X-Reasoner-7B-8bit

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* repeated_output, repetition_abort, duplicate_keywords
- *Arch supported by installed mlx-vlm:* yes (model_type qwen2_5_vl)
- *Repeated fragment:* keyword: "balustrades"
- *Title word count:* 7
- *Keyword count:* 67
- *Duplicate keywords:* ["bath somerset", "bath stone", "georgian
  architecture", "heritage site", "balustrades", "dome", "overcast sky",
  "public square", "england", "bath england", "bath stone buildings"]
- *Resolved model revision:* 21732e74613b465bc98e9d5ec210aba5c7adbcc1
- *Processor class:* mlx_vlm.models.qwen2_5_vl.processing_qwen2_5_vl.Qwen2_5_VLProcessor
- *Tokenizer class:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Stop reason:* repetition_abort
- *Post-cleanup active memory (GB):* 0.008307986
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 16669
- *Prompt composition:* 16,669 = 350 text/template (tokenizer-exact) + 16,319
  non-text (98%, image/audio expansion)
- *Checkpoint weights (GB):* 9.45
- *Parameter count:* 7.00B (name-estimate)
- *Quantization:* 8-bit, group 64
- *Declared context length:* 128,000 (max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (9.46 GB vs 9.45 GB on disk)
- *Generation tokens:* 275
- *Configured EOS token ID:* 151645
- *Configured EOS token:* &lt;|im_end|&gt;
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
Title:
Bath Roman Baths and Grand Pump Room

Description:
Tourists and visitors gather outside the historic Roman Baths and Grand Pump Room complex in Bath, Somerset, under an overcast sky, with people strolling, sitting on benches, and enjoying the public square's Georgian architecture and Bath stone buildings.

Keywords: Bath, Roman Baths, Grand Pump Room, Bath Somerset, Bath stone, Georgian architecture, Neoclassical, Heritage site, Abbey Churchyard, Balustrades, Dome, Overcast Sky, Public Square, Pedestrians, Benches, Tourists, England, Historical, Tourism, Cloudy Day, England, Bath England, Bath stone buildings, Dome, Balustrades, Public Square, Overcast Sky, Bath Somerset, Bath England, Bath stone, Georgian architecture, Heritage site, Bath stone buildings, Dome, Balustrades, Public Square, Overcast Sky, Bath Somerset, Bath England, Bath stone, Georgian architecture, Heritage site, Bath stone buildings, Dome, Balustrades, Public Square, Overcast Sky, Bath Somerset, Bath England, Bath stone, Georgian architecture, Heritage site, Bath stone buildings, Dome, Balustrades, Public Square, Overcast Sky, Bath Somerset, Bath England, Bath stone, Georgian architecture, Heritage site, Bath stone buildings, Dome, Balustrades, Public Square, Overcast
```

</details>

<a id="diagnostic-mlx-community-glm-46v-nvfp4"></a>

<details>
<summary>mlx-community/GLM-4.6V-nvfp4 — usable_with_caveats — control tokens visible</summary>

### mlx-community/GLM-4.6V-nvfp4

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* unexpected_special_token
- *Arch supported by installed mlx-vlm:* yes (model_type glm4v_moe)
- *Unexpected special tokens:* ["&lt;|begin_of_box|&gt;",
  "&lt;|end_of_box|&gt;"]
- *Title word count:* 6
- *Keyword count:* 19
- *Resolved model revision:* 2da6855d4e28a0e61c84543262074bc17ac27d6e
- *Processor class:* mlx_vlm.models.glm4v_moe.processing.Glm46VMoEProcessor
- *Tokenizer class:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Stop reason:* completed
- *Post-cleanup active memory (GB):* 0.001229866
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 6354
- *Prompt composition:* 6,354 = 323 text/template (tokenizer-exact) + 6,031
  non-text (95%, image/audio expansion)
- *Checkpoint weights (GB):* 61.86
- *Quantization:* 4-bit, group 16, nvfp4
- *Declared context length:* 131,072 (text_config.max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (61.86 GB vs 61.86 GB on disk)
- *Generation tokens:* 119
- *Configured EOS token ID:* 151329
- *Configured EOS token:* &lt;|endoftext|&gt;
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
<|begin_of_box|>Title: Visitors at Bath's Roman Baths Plaza
Description: Tourists and visitors sit on benches and stroll through the plaza outside the historic Roman Baths and Grand Pump Room complex in Bath, Somerset, England, on a cloudy day with Georgian architecture and Bath stone buildings.
Keywords: Abbey Churchyard, Balustrades, Bath, Bath England, Bath Somerset, Bath stone, Bath stone buildings, Benches, Dome, England, Georgian architecture, Grand Pump Room, Heritage site, Historic architecture, Neoclassical Architecture, Overcast Sky, Pedestrians, Plaza, Public Square<|end_of_box|>
```

</details>

<a id="diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit"></a>

<details>
<summary>mlx-community/Muse-Glimmer-30B-OptiQ-4bit — unusable — missing required fields; cut off at token limit; role tokens visible</summary>

### mlx-community/Muse-Glimmer-30B-OptiQ-4bit

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* missing_requested_sections, token_cap_truncation,
  role_boundary_token_present
- *Arch supported by installed mlx-vlm:* yes (model_type muse_glimmer)
- *Missing sections:* ["title", "description"]
- *Role-boundary tokens in output:* ["&lt;|message|&gt;"]
- *Title word count:* 0
- *Keyword count:* 25
- *Token-cap degradation evidence:* ["missing_sections"]
- *Resolved model revision:* b4a74fa6001f1eca3b23eeeb702ffad2773a218f
- *Processor class:* mlx_vlm.models.muse_glimmer.processing_muse_glimmer.MuseGlimmerProcessor
- *Tokenizer class:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Stop reason:* max_tokens
- *Post-cleanup active memory (GB):* 0.004359386
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 4444
- *Prompt composition:* 4,444 = 363 text/template (tokenizer-exact) + 4,081
  non-text (92%, image/audio expansion)
- *Checkpoint weights (GB):* 23.85
- *Parameter count:* 30.00B (name-estimate)
- *Quantization:* 4-bit, group 64, affine
- *Declared context length:* 131,072 (text_config.max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (23.86 GB vs 23.85 GB on disk)
- *Generation tokens:* 1000
- *Configured EOS token ID:* 200001
- *Configured EOS token:* &lt;|end_of_text|&gt;
- *Snapshot notes (neutral):* processor config missing from snapshot
  (preprocessor_config.json, processor_config.json)
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
 to=self<|message|>Create British-English catalogue metadata from the image and supplied context.

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

We need title 5-10 words. Concrete.

Image shows Roman Baths? The building with dome is Grand Pump Room? Actually Grand Pump Room is with dome. The left building says ROMAN BATHS. The plaza with benches. The hint says Abbey Churchyard outside historic Roman Baths and Grand Pump Room complex in Bath, Somerset, England, on a cloudy day. Wait Abbey Churchyard? The location GPS 51.380931°N, 2.359317°W. That's Bath Abbey? Actually Roman Baths is at 51.381... 2.359... Yes. The area in front of Roman Baths is the... The Abbey Churchyard is nearby but this looks like the Roman Baths forecourt. The hint may be slightly off. The image shows the Roman Baths complex with the Pump Room dome, balustrades, Bath stone buildings, benches, pedestrians. The Abbey Churchyard is not visible? Might be the same area? Let's check: The Roman Baths forecourt is adjacent to Abbey Churchyard. The building on left with "ROMAN BATHS" sign. The dome is Grand Pump Room. So description should reflect visible subject: the Roman Baths and Grand Pump Room complex, forecourt with benches, people sitting/walking. Overcast sky.

We must not claim capture date/time visible. Can mention? It says treat as authoritative facts, but do not claim they are visible. So we can incorporate date? Probably not needed in description. Might be okay to not mention date. The description should combine relevant context with main visible subject, setting, action, lighting, distinctive details.

We should correct conflict: hint says Abbey Churchyard outside historic Roman Baths... The image shows the forecourt of Roman Baths, not Abbey Churchyard? Actually the Abbey Churchyard is to the north. The GPS matches Roman Baths. Might be the area is the Roman Baths forecourt, sometimes called Abbey Churchyard? Hmm. Might be the plaza in front of Roman Baths. Let's assume the hint is mostly correct but we can say the forecourt/plaza outside Roman Baths and Grand Pump Room. Avoid saying Abbey Churchyard if not visible. The image shows stone buildings, balustrade, tiled roof, dome. No church visible. So maybe omit Abbey Churchyard.

Prefer image evidence when hint conflicts. So we should not say Abbey Churchyard if not visible. The hint says tourists sit on benches and stroll through the Abbey Churchyard outside... The image shows a paved plaza with benches in front of the Roman Baths buildings. No churchyard visible. So we should describe as the forecourt/plaza of the Roman Baths.

Title: 5-10 words. e.g. "Visitors on Plaza Outside Roman Baths Bath Somerset". That's 7 words? Visitors(1) on2 Plaza3 Outside4 Roman5 Baths6 Bath7 Somerset8. Good.

Description: 1-2 sentences. Factual description combining relevant context with main visible subject, setting, action, lighting, distinctive details.

Maybe: People sit on black benches and walk across a paved forecourt in front of the Bath stone Roman Baths and Grand Pump Room complex, with its neoclassical façade, balustrades, tiled roof and domed roof under an overcast sky. The left
```

</details>

## Indeterminate Attempts

None.

## Model Compliance Notes (not maintainer issues)

Prompt-compliance observations (missing fields, constraint counts, hint
copying, instruction echo, cap hits) inform model selection; complete evidence
is in the model gallery.

| Model                            | Usability | Observations            |
|----------------------------------|-----------|-------------------------|
| mlx-community/nanoLLaVA-1.5-4bit | unusable  | missing required fields |

## Context for completions without detected concerns

<details>
<summary>Completions without detected concerns</summary>

| Model                                                 | Runtime identity                                           | Performance                                                                                |
|-------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| LiquidAI/LFM2.5-VL-450M-MLX-bf16                      | rev ed71acdae079; Lfm2VlProcessor; stop completed          | 2648 prompt / 110 generated; 472 tok/s; 1.7 GB peak; cleanup 0.000132/0.0 GB active/cache  |
| mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit | rev 0a970d20ad7d; Mistral3Processor; stop completed        | 2073 prompt / 124 generated; 30.5 tok/s; 22 GB peak; cleanup 0.000394/0.0 GB active/cache  |
| mlx-community/diffusiongemma-26B-A4B-it-mxfp8         | rev ded389e478f8; DiffusionGemma4Processor; stop completed | 615 prompt / 87 generated; 53.2 tok/s; 28 GB peak; cleanup 0.00831/0.0 GB active/cache     |
| mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit      | rev 846ea5576854; Ernie4_5_VLProcessor; stop completed     | 1625 prompt / 943 generated; 95.6 tok/s; 19 GB peak; cleanup 0.000607/0.0 GB active/cache  |
| mlx-community/gemma-3-27b-it-qat-4bit                 | rev fc4e000f32af; Gemma3Processor; stop completed          | 610 prompt / 141 generated; 30.4 tok/s; 17 GB peak; cleanup 0.00885/0.0 GB active/cache    |
| mlx-community/gemma-4-26b-a4b-it-4bit                 | rev 0d77464eeb23; Gemma4Processor; stop completed          | 619 prompt / 105 generated; 129 tok/s; 16 GB peak; cleanup 0.00937/0.0 GB active/cache     |
| mlx-community/gemma-4-31b-it-4bit                     | rev 696d436c4047; Gemma4Processor; stop completed          | 619 prompt / 90 generated; 26.8 tok/s; 20 GB peak; cleanup 0.0099/0.0 GB active/cache      |
| mlx-community/GLM-4.6V-Flash-4bit                     | rev bd7b20686e8c; Glm46VProcessor; stop completed          | 6354 prompt / 71 generated; 77.9 tok/s; 8.7 GB peak; cleanup 0.000919/0.0 GB active/cache  |
| mlx-community/granite-4.0-3b-vision-4bit              | rev 70fe1d89f42c; Granite4VisionProcessor; stop completed  | 1537 prompt / 100 generated; 175 tok/s; 4.8 GB peak; cleanup 0.0101/0.0 GB active/cache    |
| mlx-community/Idefics3-8B-Llama3-bf16                 | rev 8c2a30c48864; Idefics3Processor; stop completed        | 2628 prompt / 162 generated; 33.2 tok/s; 18 GB peak; cleanup 0.00149/0.0 GB active/cache   |
| mlx-community/InternVL3-8B-bf16                       | rev e0df3dd79263; InternVLChatProcessor; stop completed    | 2640 prompt / 96 generated; 34.8 tok/s; 17 GB peak; cleanup 0.0018/0.0 GB active/cache     |
| mlx-community/Kimi-VL-A3B-Thinking-2506-8bit          | rev e5abbe34cbfa; KimiVLProcessor; stop completed          | 1334 prompt / 527 generated; 66.8 tok/s; 20 GB peak; cleanup 0.00246/0.0 GB active/cache   |
| mlx-community/LFM2.5-VL-1.6B-bf16                     | rev 16a710cf8afc; Lfm2VlProcessor; stop completed          | 2648 prompt / 142 generated; 189 tok/s; 4.0 GB peak; cleanup 0.00259/0.0 GB active/cache   |
| mlx-community/LFM2.5-VL-3B-OptiQ-4bit                 | rev 12c5ae493041; Lfm2VlProcessor; stop completed          | 2640 prompt / 78 generated; 207 tok/s; 4.0 GB peak; cleanup 0.00285/0.0 GB active/cache    |
| mlx-community/Ministral-3-14B-Instruct-2512-mxfp4     | rev 7c992876448f; Mistral3Processor; stop completed        | 2606 prompt / 142 generated; 66.9 tok/s; 12 GB peak; cleanup 0.00311/0.0 GB active/cache   |
| mlx-community/Ministral-3-14B-Instruct-2512-nvfp4     | rev 28777b889d84; Mistral3Processor; stop completed        | 2606 prompt / 179 generated; 64.8 tok/s; 12 GB peak; cleanup 0.00338/0.0 GB active/cache   |
| mlx-community/Ministral-3-3B-Instruct-2512-4bit       | rev a962dcb09eee; Mistral3Processor; stop completed        | 2605 prompt / 146 generated; 192 tok/s; 6.4 GB peak; cleanup 0.00364/0.0 GB active/cache   |
| mlx-community/Molmo2-8B-4bit                          | rev 4fcbe9265776; Molmo2Processor; stop completed          | 1539 prompt / 155 generated; 72.5 tok/s; 8.1 GB peak; cleanup 0.00395/0.0 GB active/cache  |
| mlx-community/North-Micro-Vision-Instruct-4bit        | rev 87466363e6c5; CohereCompassProcessor; stop completed   | 4077 prompt / 129 generated; 217 tok/s; 3.9 GB peak; cleanup 0.00488/0.0 GB active/cache   |
| mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit           | rev 5f31fcd089ce; Qwen3VLProcessor; stop completed         | 1297 prompt / 134 generated; 104 tok/s; 24 GB peak; cleanup 0.00539/0.0 GB active/cache    |
| mlx-community/Phi-3.5-vision-instruct-bf16            | rev d8da684308c2; Phi3VProcessor; stop completed           | 1146 prompt / 137 generated; 56.0 tok/s; 9.3 GB peak; cleanup 0.00546/0.0 GB active/cache  |
| mlx-community/pixtral-12b-8bit                        | rev 79e24b66302d; PixtralProcessor; stop completed         | 2677 prompt / 117 generated; 39.6 tok/s; 15 GB peak; cleanup 0.011/0.0 GB active/cache     |
| mlx-community/Qwen3-VL-2B-Thinking-bf16               | rev c325e5ea14c2; Qwen3VLProcessor; stop completed         | 16660 prompt / 909 generated; 89.5 tok/s; 8.4 GB peak; cleanup 0.00577/0.0 GB active/cache |
| mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit          | rev 0555d34cb1ed; Qwen3VLProcessor; stop completed         | 16658 prompt / 136 generated; 87.1 tok/s; 23 GB peak; cleanup 0.00608/0.0 GB active/cache  |
| mlx-community/Qwen3.5-35B-A3B-4bit                    | rev 1e20fd8d4205; Qwen3VLProcessor; stop completed         | 16674 prompt / 135 generated; 109 tok/s; 24 GB peak; cleanup 0.00659/0.0 GB active/cache   |
| mlx-community/Qwen3.5-9B-MLX-4bit                     | rev 938d8919941c; Qwen3VLProcessor; stop completed         | 16674 prompt / 119 generated; 91.1 tok/s; 10 GB peak; cleanup 0.00711/0.0 GB active/cache  |
| mlx-community/Qwen3.8-27B-4bit                        | rev 3e6447f082e8; Qwen3VLProcessor; stop completed         | 16674 prompt / 130 generated; 30.6 tok/s; 21 GB peak; cleanup 0.00762/0.0 GB active/cache  |
| mlx-community/SmolVLM2-2.2B-Instruct-mlx              | rev 844516024a1c; SmolVLMProcessor; stop completed         | 1442 prompt / 101 generated; 125 tok/s; 5.4 GB peak; cleanup 0.00773/0.0 GB active/cache   |
| mlx-community/Step-3.7-Flash-oQ3e                     | rev 41d17ee00e16; Step3VLProcessor; stop completed         | 3505 prompt / 118 generated; 52.0 tok/s; 92 GB peak; cleanup 0.008/0.0 GB active/cache     |

</details>

## Shared Reproduction and Provenance

### Reproduction inputs

- *Image format:* JPEG
- *Image dimensions:* 9,984 x 5,616 pixels
- *Image size:* 39,377,657 bytes
- *Image SHA-256:* 7e999a8e5f2d850a42928baa7b522d02ae554489964592ca7c41d5d840f2eeea

<details>
<summary>Exact prompt</summary>

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

The original local input is not published, so this report does not claim a
complete reproduction command. Use a shareable equivalent image or add the
original image before filing.

- *Published preview:* &lt;https://raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image.jpg&gt;
- *Preview dimensions:* 1,024 x 576 pixels
- *Preview size:* 113,879 bytes
- *Preview SHA-256:* 79f74fb9cedc30db75a9cbfa99d9c71431933bab51255bf500879846baacaf33

Shareable stand-in: the committed gallery preview is a downscaled re-encoding
of the original, so an observation reproduced on it must be reported as
reproduced on the preview, not on the exact inference input. Download and
verify it, then run one native mlx-vlm process.

```bash
set -euo pipefail
curl --fail --location --output repro-image.jpg https://raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image.jpg
printf '%s\n' '79f74fb9cedc30db75a9cbfa99d9c71431933bab51255bf500879846baacaf33  repro-image.jpg' | shasum -a 256 --check
python -m mlx_vlm.generate --model MODEL_ID --image repro-image.jpg --prompt 'Create British-English catalogue metadata from the image and supplied context.

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
Keywords:' --max-tokens 1000 --temperature 0.0 --revision RESOLVED_REVISION --trust-remote-code --prefill-step-size 2048
```

### Highlighted model revisions

| Model                                     | Resolved revision                        |
|-------------------------------------------|------------------------------------------|
| mlx-community/X-Reasoner-7B-8bit          | 21732e74613b465bc98e9d5ec210aba5c7adbcc1 |
| mlx-community/GLM-4.6V-nvfp4              | 2da6855d4e28a0e61c84543262074bc17ac27d6e |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | b4a74fa6001f1eca3b23eeeb702ffad2773a218f |

### Components and system

| Component                  | Value                                                                                                                                           |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| mlx-vlm                    | 0.7.0rc0                                                                                                                                        |
| mlx-vlm source revision    | d5064772dcd1e31704604f93a873323505ae70d5                                                                                                        |
| mlx                        | 0.32.3.dev20260905+2d27ab05f                                                                                                                    |
| mlx source revision        | 2d27ab05fb7dcda69bb3c57abd74c0b3bc9a5a99                                                                                                        |
| mlx-audio                  | 0.5.1                                                                                                                                           |
| transformers               | 5.16.1                                                                                                                                          |
| tokenizers                 | 0.23.2                                                                                                                                          |
| huggingface-hub            | 1.30.0                                                                                                                                          |
| Python Version             | 3.14.7                                                                                                                                          |
| OS                         | Darwin 25.6.0                                                                                                                                   |
| macOS Version              | 26.6.2                                                                                                                                          |
| SDK Version                | 26.5                                                                                                                                            |
| SDK Path                   | /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk                                              |
| Xcode Version              | 26.6                                                                                                                                            |
| Xcode Build                | 17F113                                                                                                                                          |
| Active Developer Directory | /Applications/Xcode.app/Contents/Developer                                                                                                      |
| Metal SDK                  | MacOSX26.5.sdk                                                                                                                                  |
| Metal Compiler Version     | Apple metal version 32023.883 (metalfe-32023.883)                                                                                               |
| Metallib Linker Version    | AIR-LLD 32023.883 (metalfe-32023.883) (compatible with legacy metallib linker)                                                                  |
| Apple Clang Version        | Apple clang version 21.0.0 (clang-2100.1.1.101)                                                                                                 |
| GPU/Chip                   | Apple M5 Max                                                                                                                                    |
| GPU Cores                  | 40                                                                                                                                              |
| MLX Device                 | Apple M5 Max                                                                                                                                    |
| GPU Architecture           | applegpu_g17s                                                                                                                                   |
| Recommended Working Set    | 108 GB                                                                                                                                          |
| Fused Attention            | Available                                                                                                                                       |
| Metal Support              | Metal 4                                                                                                                                         |
| MLX Install Type           | editable local source                                                                                                                           |
| MLX Distribution Root      | ~/miniconda3/envs/mlx-vlm/lib/python3.14/site-packages                                                                                          |
| mlx-metal Distribution     | not installed; local editable mlx supplies backend                                                                                              |
| MLX Core Extension         | ~/Documents/AI/mlx/mlx/python/mlx/core.cpython-314-darwin.so                                                                                    |
| MLX Metallib               | ~/Documents/AI/mlx/mlx/python/mlx/lib/mlx.metallib (185,639,856 bytes, sha256=ec2b578e8ed0c5e85d220d869ab39bff8157c2de9152ee2d962174d58fc93d25) |
| MLX libmlx.dylib           | ~/Documents/AI/mlx/mlx/python/mlx/lib/libmlx.dylib (21,958,976 bytes, sha256=d08dcd8e2a50bf22ad7f17c0f483174dbf20eb13f7330188103f4a68b803d111)  |
| RAM                        | 128.0 GB                                                                                                                                        |
<!-- markdownlint-enable MD004 MD037 -->
