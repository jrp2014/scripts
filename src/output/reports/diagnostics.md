# Diagnostics

<!-- markdownlint-disable MD004 MD037 -->

This run records model responses to one shared image and prompt (evaluation
lane: blind). Mechanical checks are not factual-accuracy judgments; inspect
the image, prompt and final answers before choosing a model. Results do not
establish fitness for other tasks.

## Run Summary

- *Evaluation lane:* blind
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Input image:* JPEG, 640 x 480 pixels (0.3 MP), 0.2 MB

Outcome counts

| Outcome             | Count |
|---------------------|-------|
| Attempted           | 34    |
| Conclusive outcomes | 34    |
| Completed           | 34    |
| Crashed             | 0     |
| Indeterminate       | 0     |

Maintainer status counts

| Maintainer status              | Count |
|--------------------------------|-------|
| none                           | 29    |
| observation needs reproduction | 5     |

Usability counts

| Usability           | Count |
|---------------------|-------|
| unusable            | 5     |
| usable              | 24    |
| usable with caveats | 5     |

Observation counts

| Observation                                                  | Count |
|--------------------------------------------------------------|-------|
| Response repeats the same text                               | 2     |
| Generation was stopped early after sustained repeated output | 2     |
| Unrecognised model control tokens remain visible             | 2     |
| Required labelled fields not detected                        | 4     |
| Response appears cut off at the token limit                  | 1     |
| Internal reasoning block appears incomplete                  | 1     |
| Conversation-role control tokens remain visible              | 1     |
| Repeated keyword entries                                     | 6     |

## Triage

| Model                                                                                              | Execution | Usability           | Maintainer status              | Observations                                                                                                         |
|----------------------------------------------------------------------------------------------------|-----------|---------------------|--------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [mlx-community/Qwen3-VL-2B-Thinking-bf16](#diagnostic-mlx-community-qwen3-vl-2b-thinking-bf16)     | completed | unusable            | observation_needs_reproduction | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| [mlx-community/X-Reasoner-7B-8bit](#diagnostic-mlx-community-x-reasoner-7b-8bit)                   | completed | unusable            | observation_needs_reproduction | repeated text; stopped early: repeating; duplicate keywords                                                          |
| [mlx-community/GLM-4.6V-nvfp4](#diagnostic-mlx-community-glm-46v-nvfp4)                            | completed | usable_with_caveats | observation_needs_reproduction | control tokens visible                                                                                               |
| [mlx-community/Step-3.7-Flash-oQ3e](#diagnostic-mlx-community-step-37-flash-oq3e)                  | completed | usable_with_caveats | observation_needs_reproduction | control tokens visible                                                                                               |
| [mlx-community/Muse-Glimmer-30B-OptiQ-4bit](#diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit) | completed | unusable            | observation_needs_reproduction | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords                        |

## Crashes requiring action

None.

## Completed Runs with Observations

<a id="diagnostic-mlx-community-qwen3-vl-2b-thinking-bf16"></a>

<details>
<summary>mlx-community/Qwen3-VL-2B-Thinking-bf16 — unusable — repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords</summary>

### mlx-community/Qwen3-VL-2B-Thinking-bf16

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* repeated_output, repetition_abort,
  missing_requested_sections, thinking_trace_incomplete, duplicate_keywords
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_vl)
- *Labelled fields not detected:* ["title", "description"]
- *Repeated fragment:* keyword: "cat"
- *Thinking trace markers:* ["&lt;think&gt;"]
- *Keyword count:* 46
- *Duplicate keywords:* ["resting", "couch", "cat", "tabby", "pink", "remote"]
- *Resolved model revision:* c325e5ea14c215bb08fa0d668c81fa2581f9050b
- *Processor class:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer class:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Stop reason:* repetition_abort
- *Post-cleanup active memory (GB):* 0.005768386
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 411
- *Prompt composition:* 411 = 112 text/template (tokenizer-exact) + 299
  non-text (73%, image/audio expansion)
- *Checkpoint weights (GB):* 4.26
- *Parameter count:* 2.00B (name-estimate)
- *Declared context length:* 262,144 (text_config.max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (4.26 GB vs 4.26 GB on disk)
- *Generation tokens:* 400
- *Configured EOS token ID:* 151645
- *Configured EOS token:* &lt;|im_end|&gt;
- *Configured thinking start token:* &lt;think&gt;
- *Configured thinking end token:* &lt;/think&gt;
- *Configured thinking budget:* 800
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
Got it, let's tackle this. First, the title needs to be concrete and 5-10 words. The image has two cats on a pink couch with remotes. So maybe "Two tabby cats resting on pink couch with remotes" but that's 10 words. Wait, "Two tabby cats resting on pink couch with remote controls" but need to check. Wait, the problem says "British-English catalogue metadata", so maybe "Two tabby cats resting on pink couch with remote controls" but let's count: Two tabby cats resting on pink couch with remote controls is 10 words. That's good.

Next, the description. Need 1-2 sentences. Main subject: two cats. Setting: pink couch. Action: resting. Lighting: bright (since it's a photo, probably natural light). Distinctive details: tabby patterns, remotes. So "Two tabby cats rest on a bright pink couch, one with a green collar, while two remote controls lie nearby."

Wait, check the facts. The remotes are visible, one is gray with buttons, the other is white with blue. But the problem says omit uncertain details. So "Two tabby cats rest on a bright pink couch, one with a green collar, while two remote controls lie nearby." That's 1-2 sentences.

Keywords: need 10-18 unique, comma-separated. Let's list: tabby cats, pink couch, resting, remote controls, two cats, bright, natural light, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting,
```

</details>

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
- *Repeated fragment:* phrase: "pink couch with remote..."
- *Title word count:* 7
- *Keyword count:* 54
- *Duplicate keywords:* ["feline pink couch with remote control", "feline rest
  on pink couch with remote control", "feline pink couch with remote control
  and cat", "feline rest on pink couch with remote control and cat"]
- *Resolved model revision:* 21732e74613b465bc98e9d5ec210aba5c7adbcc1
- *Processor class:* mlx_vlm.models.qwen2_5_vl.processing_qwen2_5_vl.Qwen2_5_VLProcessor
- *Tokenizer class:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Stop reason:* repetition_abort
- *Post-cleanup active memory (GB):* 0.008799456
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 511
- *Prompt composition:* 511 = 121 text/template (tokenizer-exact) + 390
  non-text (76%, image/audio expansion)
- *Checkpoint weights (GB):* 9.45
- *Parameter count:* 7.00B (name-estimate)
- *Quantization:* 8-bit, group 64
- *Declared context length:* 128,000 (max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (9.46 GB vs 9.45 GB on disk)
- *Generation tokens:* 375
- *Configured EOS token ID:* 151645
- *Configured EOS token:* &lt;|im_end|&gt;
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
Title: Cats Sleeping on Pink Couch with Remotes

Description: Two tabby cats rest on a pink couch, one curled up with a remote, the other stretched out. The setting is indoors, with soft lighting highlighting their striped fur and relaxed postures. A second remote lies between them.

Keywords: cats, sleeping, pink couch, tabby, striped, remote control, indoor, relaxation, feline, comfort, domestic, home, rest, feline behavior, cozy, feline friends, feline companions, feline relaxation, feline comfort, feline rest, feline home life, feline behavior study, feline sleep patterns, feline remote control, feline pink couch, feline comfort zone, feline home environment, feline rest period, feline remote control use, feline pink couch setup, feline home setup, feline remote control placement, feline pink couch arrangement, feline rest on remote, feline pink couch with remote, feline comfort with remote, feline pink couch with remote control, feline rest on pink couch, feline remote control on pink couch, feline pink couch with remote control, feline rest on pink couch with remote, feline pink couch setup with remote, feline rest on pink couch with remote control, feline pink couch with remote control, feline rest on pink couch with remote control, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with
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
- *Keyword count:* 15
- *Resolved model revision:* 2da6855d4e28a0e61c84543262074bc17ac27d6e
- *Processor class:* mlx_vlm.models.glm4v_moe.processing.Glm46VMoEProcessor
- *Tokenizer class:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Stop reason:* completed
- *Post-cleanup active memory (GB):* 0.001229862
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 499
- *Prompt composition:* 499 = 109 text/template (tokenizer-exact) + 390
  non-text (78%, image/audio expansion)
- *Checkpoint weights (GB):* 61.86
- *Quantization:* 4-bit, group 16, nvfp4
- *Declared context length:* 131,072 (text_config.max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (61.86 GB vs 61.86 GB on disk)
- *Generation tokens:* 84
- *Configured EOS token ID:* 151329
- *Configured EOS token:* &lt;|endoftext|&gt;
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
<|begin_of_box|>Title: Two cats on a pink couch
Description: Two cats lie on a pink couch, each near a remote control, with one cat’s head resting on the fabric and the other stretched out with eyes closed.
Keywords: cats, pink couch, remote controls, sleeping, relaxed, striped fur, feline, domestic, indoor, pets, lounging, two animals, soft fabric, calm, cozy<|end_of_box|>
```

</details>

<a id="diagnostic-mlx-community-step-37-flash-oq3e"></a>

<details>
<summary>mlx-community/Step-3.7-Flash-oQ3e — usable_with_caveats — control tokens visible</summary>

### mlx-community/Step-3.7-Flash-oQ3e

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* unexpected_special_token
- *Arch supported by installed mlx-vlm:* yes (model_type step3p7)
- *Unexpected special tokens:* ["&lt;/think&gt;"]
- *Title word count:* 7
- *Keyword count:* 19
- *Resolved model revision:* 41d17ee00e168a2918bb839e4a7b6e445c6f03f1
- *Processor class:* mlx_vlm.models.step3p7.processing_step3p7.Step3VLProcessor
- *Tokenizer class:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Stop reason:* completed
- *Post-cleanup active memory (GB):* 0.00848816
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 286
- *Prompt composition:* 286 = 117 text/template (tokenizer-exact) + 169
  non-text (59%, image/audio expansion)
- *Checkpoint weights (GB):* 84.95
- *Quantization:* 3-bit, group 128, affine
- *Declared context length:* 262,144 (text_config.max_position_embeddings)
- *Load active memory vs checkpoint:* 1.00x (84.96 GB vs 84.95 GB on disk)
- *Generation tokens:* 236
- *Configured EOS token ID:* 128007
- *Configured EOS token:* &lt;|im_end|&gt;
- *Snapshot notes (neutral):* processor config missing from snapshot
  (preprocessor_config.json, processor_config.json)
- *System pressure snapshots (before/after; cannot rule out transient pressure during inference):* CPU
  speed limit min 100% over 2 sample(s); memory pressure max level 1 over 2
  sample(s); mode snapshot

#### Complete output

```text
Title:
Two cats sleeping on a pink blanket
Description:
Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one cat on the left having a green collar and the other cat on the right being larger. Two remote controls are placed near the cats on the blanket.
Keywords:
cats, sleeping, pink blanket, red sofa, tabby cats, remote controls, green collar, large cat, small cat, relaxed, pets, home interior, soft fabric, lying down, close-up, daytime, comfortable, cozy
</think>
Title:
Two cats sleeping on a pink blanket
Description:
Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one cat on the left having a green collar and the other cat on the right being larger. Two remote controls are placed near the cats on the blanket.
Keywords:
cats, sleeping, pink blanket, red sofa, tabby cats, remote controls, green collar, large cat, small cat, relaxed, pets, home interior, soft fabric, lying down, close-up, daytime, comfortable, cozy
```

</details>

<a id="diagnostic-mlx-community-muse-glimmer-30b-optiq-4bit"></a>

<details>
<summary>mlx-community/Muse-Glimmer-30B-OptiQ-4bit — unusable — labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords</summary>

### mlx-community/Muse-Glimmer-30B-OptiQ-4bit

#### Execution and provenance

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* missing_requested_sections, token_cap_truncation,
  role_boundary_token_present, duplicate_keywords
- *Arch supported by installed mlx-vlm:* yes (model_type muse_glimmer)
- *Labelled fields not detected:* ["title", "description"]
- *Role-boundary tokens in output:* ["&lt;|message|&gt;"]
- *Title word count:* 0
- *Keyword count:* 20
- *Duplicate keywords:* ["location", "event", "brand", "species", "period",
  "or intent"]
- *Token-cap degradation evidence:* ["missing_sections"]
- *Resolved model revision:* b4a74fa6001f1eca3b23eeeb702ffad2773a218f
- *Processor class:* mlx_vlm.models.muse_glimmer.processing_muse_glimmer.MuseGlimmerProcessor
- *Tokenizer class:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Stop reason:* max_tokens
- *Post-cleanup active memory (GB):* 0.004359346
- *Post-cleanup cache memory (GB):* 0.0
- *Prompt tokens:* 545
- *Prompt composition:* 545 = 153 text/template (tokenizer-exact) + 392
  non-text (72%, image/audio expansion)
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
 to=self<|message|>Create British-English catalogue metadata using only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

Write:
- a concrete 5-10-word title;
- a 1-2-sentence factual description of the main subject, setting, action, lighting, and distinctive details;
- 10-18 unique, comma-separated keywords.

Return exactly these three sections and nothing else:
Title:
Description:
Keywords:

We need British-English. Use only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

We have two cats? The image shows two tabby cats on pink fabric. Two remote controls. One cat sleeping? One appears sleeping on left, head down. Right cat appears awake? Head down looking? Maybe sleeping? Might be resting. Can't assume species? Cat is visible. Probably cat is okay. Species is cat, visible. Might be tabby cats. Tabby is pattern. Could be safe.

We must omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

Species: cat is visible. Is it safe to say cat? Probably yes, clearly visible. Might be "two cats". Could be "two felines". Use cat.

No brand. No location. No event. No period.

Title: concrete 5-10 words. e.g., "Two Tabby Cats Resting On Pink Fabric". That's 7 words? Two(1) Tabby(2) Cats(3) Resting(4) On(5) Pink(6) Fabric(7). Good.

Description: 1-2 sentence factual description of main subject, setting, action, lighting, and distinctive details.

Main subject: two tabby cats on pink blanket on red sofa? The background is red cushion. Setting: pink fabric surface with red upholstery. Action: one cat lying on side with eyes closed, the other lying with head down. Two remote controls nearby. Lighting appears bright daylight? Maybe indoor lighting. Distinctive details: one cat has green collar? There's a green collar on left cat. Remote controls white with buttons. Pink blanket wrinkled.

We must omit uncertain details. Lighting: maybe bright, natural? Could say bright lighting. Might be safe.

Don't assume intent.

Description: Two tabby cats lie on a bright pink fabric surface with red upholstery behind. One cat rests on its side with eyes closed, the other lies with its head lowered; two white remote controls are placed nearby.

That's one sentence? It's two sentences. Might be okay 1-2 sentence.

Keywords: 10-18 unique comma-separated keywords.

Keywords: cats, tabby, pink blanket, red sofa, remote controls, resting, sleeping, indoor, fabric, fur pattern, green collar, white remotes, wrinkled textile, domestic

Need 10-18. Let's count. cats(1), tabby(2), pink blanket(3), red sofa(4), remote controls(5), resting(6), sleeping(7), indoor(8), fabric(9), fur pattern(10), green collar(11), white remotes(12), wrinkled textile(13), domestic(14). That's 14.

Make sure British English spelling: catalogue, colour? Keywords maybe colour? Use British spelling? Probably okay. "colour" vs "color". Use British English. Maybe "colour". But keywords maybe not need spelling.

Ensure title 5-10 words. Good.

Return exactly these three sections and nothing else:
Title:
Description:
Keywords:

Make sure format exactly.

No extra text.

Let's output.

Potential issue: "species" maybe uncertain? Cat is clearly cat. Should be fine.

Omit unsupported identity, location, event, brand, species, period, or intent. Species is cat, visible. Might be okay.

Don't say "sofa" maybe uncertain? It's a red upholstered surface, could be sofa. Might be couch. Could say "red upholstery". Safer.

Title: Two Tabby Cats Resting On Pink Fabric

Description: Two tabby cats lie on a bright pink fabric surface with red upholstery behind. One cat rests on its side with eyes closed, the other lies with its head lowered; two white remote controls are placed nearby on the fabric.

Keywords: cats, tabby, pink blanket, red upholstery, remote controls, resting, sleeping, indoor, fabric, fur pattern, green collar, white remotes, wrinkled textile, domestic

Check word count title: Two(1) Tabby(2) Cats(3) Resting(4) On(5) Pink(6) Fabric(7). Good.

Description is two sentences. Good.

Make sure British English: "colour"? Not
```

</details>

## Indeterminate Attempts

None.

## Model Compliance Notes (not maintainer issues)

Prompt-compliance observations (missing fields, constraint counts, hint
copying, instruction echo, cap hits) inform model selection; complete evidence
is in the model gallery.

| Model                                          | Usability           | Observations                 |
|------------------------------------------------|---------------------|------------------------------|
| mlx-community/Idefics3-8B-Llama3-bf16          | unusable            | labelled fields not detected |
| mlx-community/nanoLLaVA-1.5-4bit               | unusable            | labelled fields not detected |
| LiquidAI/LFM2.5-VL-450M-MLX-bf16               | usable_with_caveats | duplicate keywords           |
| mlx-community/North-Micro-Vision-Instruct-4bit | usable_with_caveats | duplicate keywords           |
| mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit   | usable_with_caveats | duplicate keywords           |

## Context for completions without detected concerns

<details>
<summary>Completions without detected concerns</summary>

| Model                                                 | Runtime identity                                           | Performance                                                                              |
|-------------------------------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------|
| mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit | rev 0a970d20ad7d; Mistral3Processor; stop completed        | 537 prompt / 98 generated; 31.3 tok/s; 20 GB peak; cleanup 0.000394/0.0 GB active/cache  |
| mlx-community/diffusiongemma-26B-A4B-it-mxfp8         | rev ded389e478f8; DiffusionGemma4Processor; stop completed | 386 prompt / 74 generated; 56.5 tok/s; 28 GB peak; cleanup 0.0088/0.0 GB active/cache    |
| mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit      | rev 846ea5576854; Ernie4_5_VLProcessor; stop completed     | 545 prompt / 411 generated; 139 tok/s; 18 GB peak; cleanup 0.000607/0.0 GB active/cache  |
| mlx-community/gemma-3-27b-it-qat-4bit                 | rev fc4e000f32af; Gemma3Processor; stop completed          | 379 prompt / 89 generated; 31.9 tok/s; 17 GB peak; cleanup 0.00934/0.0 GB active/cache   |
| mlx-community/gemma-4-26b-a4b-it-4bit                 | rev 0d77464eeb23; Gemma4Processor; stop completed          | 390 prompt / 73 generated; 132 tok/s; 16 GB peak; cleanup 0.00986/0.0 GB active/cache    |
| mlx-community/gemma-4-31b-it-4bit                     | rev 696d436c4047; Gemma4Processor; stop completed          | 390 prompt / 80 generated; 28.1 tok/s; 19 GB peak; cleanup 0.0104/0.0 GB active/cache    |
| mlx-community/GLM-4.6V-Flash-4bit                     | rev bd7b20686e8c; Glm46VProcessor; stop completed          | 499 prompt / 48 generated; 89.3 tok/s; 8.0 GB peak; cleanup 0.000919/0.0 GB active/cache |
| mlx-community/granite-4.0-3b-vision-4bit              | rev 70fe1d89f42c; Granite4VisionProcessor; stop completed  | 734 prompt / 64 generated; 191 tok/s; 4.7 GB peak; cleanup 0.0106/0.0 GB active/cache    |
| mlx-community/InternVL3-8B-bf16                       | rev e0df3dd79263; InternVLChatProcessor; stop completed    | 3435 prompt / 60 generated; 35.1 tok/s; 17 GB peak; cleanup 0.0018/0.0 GB active/cache   |
| mlx-community/Kimi-VL-A3B-Thinking-2506-8bit          | rev e5abbe34cbfa; KimiVLProcessor; stop completed          | 489 prompt / 346 generated; 73.9 tok/s; 20 GB peak; cleanup 0.00246/0.0 GB active/cache  |
| mlx-community/LFM2.5-VL-1.6B-bf16                     | rev 16a710cf8afc; Lfm2VlProcessor; stop completed          | 350 prompt / 100 generated; 191 tok/s; 4.0 GB peak; cleanup 0.00259/0.0 GB active/cache  |
| mlx-community/LFM2.5-VL-3B-OptiQ-4bit                 | rev 12c5ae493041; Lfm2VlProcessor; stop completed          | 344 prompt / 61 generated; 218 tok/s; 3.6 GB peak; cleanup 0.00285/0.0 GB active/cache   |
| mlx-community/Ministral-3-14B-Instruct-2512-mxfp4     | rev 7c992876448f; Mistral3Processor; stop completed        | 1070 prompt / 81 generated; 70.0 tok/s; 9.8 GB peak; cleanup 0.00311/0.0 GB active/cache |
| mlx-community/Ministral-3-14B-Instruct-2512-nvfp4     | rev 28777b889d84; Mistral3Processor; stop completed        | 1070 prompt / 106 generated; 67.0 tok/s; 10 GB peak; cleanup 0.00338/0.0 GB active/cache |
| mlx-community/Ministral-3-3B-Instruct-2512-4bit       | rev a962dcb09eee; Mistral3Processor; stop completed        | 1069 prompt / 97 generated; 205 tok/s; 4.5 GB peak; cleanup 0.00364/0.0 GB active/cache  |
| mlx-community/Molmo2-8B-4bit                          | rev 4fcbe9265776; Molmo2Processor; stop completed          | 873 prompt / 95 generated; 73.6 tok/s; 8.0 GB peak; cleanup 0.00395/0.0 GB active/cache  |
| mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit           | rev 5f31fcd089ce; Qwen3VLProcessor; stop completed         | 421 prompt / 114 generated; 108 tok/s; 24 GB peak; cleanup 0.00539/0.0 GB active/cache   |
| mlx-community/Phi-3.5-vision-instruct-bf16            | rev d8da684308c2; Phi3VProcessor; stop completed           | 883 prompt / 96 generated; 58.3 tok/s; 9.3 GB peak; cleanup 0.00546/0.0 GB active/cache  |
| mlx-community/pixtral-12b-8bit                        | rev 79e24b66302d; PixtralProcessor; stop completed         | 1335 prompt / 89 generated; 40.5 tok/s; 15 GB peak; cleanup 0.0115/0.0 GB active/cache   |
| mlx-community/Qwen3.5-35B-A3B-4bit                    | rev 1e20fd8d4205; Qwen3VLProcessor; stop completed         | 421 prompt / 89 generated; 123 tok/s; 21 GB peak; cleanup 0.00659/0.0 GB active/cache    |
| mlx-community/Qwen3.5-9B-MLX-4bit                     | rev 938d8919941c; Qwen3VLProcessor; stop completed         | 421 prompt / 71 generated; 101 tok/s; 7.0 GB peak; cleanup 0.0071/0.0 GB active/cache    |
| mlx-community/Qwen3.8-27B-4bit                        | rev 3e6447f082e8; Qwen3VLProcessor; stop completed         | 421 prompt / 86 generated; 33.0 tok/s; 17 GB peak; cleanup 0.0076/0.0 GB active/cache    |
| mlx-community/Qwen3.8-Flash-Next-4bit                 | rev 07b5dc6c5460; Qwen3VLProcessor; stop completed         | 421 prompt / 80 generated; 31.9 tok/s; 113 GB peak; cleanup 0.00811/0.0 GB active/cache  |
| mlx-community/SmolVLM2-2.2B-Instruct-mlx              | rev 844516024a1c; SmolVLMProcessor; stop completed         | 1204 prompt / 31 generated; 129 tok/s; 5.4 GB peak; cleanup 0.00823/0.0 GB active/cache  |

</details>

## Shared Reproduction and Provenance

### Reproduction inputs

- *Image format:* JPEG
- *Image dimensions:* 640 x 480 pixels
- *Image size:* 173,131 bytes
- *Image SHA-256:* dea9e7ef97386345f7cff32f9055da4982da5471c48d575146c796ab4563b04e

<details>
<summary>Exact prompt</summary>

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

The original local input is not published, so this report does not claim a
complete reproduction command. Use a shareable equivalent image or add the
original image before filing.

- *Retained preview:* <https://raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image-c4aeb8d18432656f.jpg>
- *Preview dimensions:* 640 x 480 pixels
- *Preview size:* 63,187 bytes
- *Preview SHA-256:* c4aeb8d18432656f38f690facffbfa90ad3966dc2113a675025d1231a7c5747b

Shareable stand-in: the retained gallery preview is a downscaled re-encoding
of the original, so an observation reproduced on it must be reported as
reproduced on the preview, not on the exact inference input. The asset is
named by its digest, so later sweeps never replace it; the URL resolves once
this run's artifacts are committed. Download and verify it, then run one
native mlx-vlm process.

```bash
set -euo pipefail
curl --fail --location --output repro-image.jpg https://raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image-c4aeb8d18432656f.jpg
printf '%s\n' 'c4aeb8d18432656f38f690facffbfa90ad3966dc2113a675025d1231a7c5747b  repro-image.jpg' | shasum -a 256 --check
python -m mlx_vlm.generate --model MODEL_ID --image repro-image.jpg --prompt 'Create British-English catalogue metadata using only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

Write:
- a concrete 5-10-word title;
- a 1-2-sentence factual description of the main subject, setting, action, lighting, and distinctive details;
- 10-18 unique, comma-separated keywords.

Return exactly these three sections and nothing else:
Title:
Description:
Keywords:' --max-tokens 1000 --temperature 0.0 --revision RESOLVED_REVISION --trust-remote-code --prefill-step-size 2048
```

The shared command omits per-model automatic thinking flags. When substituting
these models, append the flags recorded in their diagnostics blocks:
`mlx-community/Qwen3-VL-2B-Thinking-bf16` (--enable-thinking --thinking-budget
800).

### Highlighted model revisions

| Model                                     | Resolved revision                        |
|-------------------------------------------|------------------------------------------|
| mlx-community/Qwen3-VL-2B-Thinking-bf16   | c325e5ea14c215bb08fa0d668c81fa2581f9050b |
| mlx-community/X-Reasoner-7B-8bit          | 21732e74613b465bc98e9d5ec210aba5c7adbcc1 |
| mlx-community/GLM-4.6V-nvfp4              | 2da6855d4e28a0e61c84543262074bc17ac27d6e |
| mlx-community/Step-3.7-Flash-oQ3e         | 41d17ee00e168a2918bb839e4a7b6e445c6f03f1 |
| mlx-community/Muse-Glimmer-30B-OptiQ-4bit | b4a74fa6001f1eca3b23eeeb702ffad2773a218f |

### Components and system

| Component                  | Value                                                                                                                                           |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| mlx-vlm                    | 0.7.0rc0                                                                                                                                        |
| mlx-vlm source revision    | d5064772dcd1e31704604f93a873323505ae70d5                                                                                                        |
| mlx                        | 0.32.3.dev20260906+ce916dbbc                                                                                                                    |
| mlx source revision        | ce916dbbcaa88e433b6fd1e60a17f766d49c27fe                                                                                                        |
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
| MLX libmlx.dylib           | ~/Documents/AI/mlx/mlx/python/mlx/lib/libmlx.dylib (21,958,976 bytes, sha256=fd694605212d77bba7548b83708f16e4a4f69b3a1f9605e546008b8360afce91)  |
| RAM                        | 128.0 GB                                                                                                                                        |
<!-- markdownlint-enable MD004 MD037 -->
