# Model Output Gallery

Generated on: 2026-09-06 22:21:23 BST

- *Evaluation lane:* blind
- *Assessment:* General checks + metadata fields and duplicate keywords; length limits and factual accuracy not assessed
- *Input image:* JPEG, 640 x 480 pixels (0.3 MP), 0.2 MB

This run records model responses to one shared image and prompt (evaluation
lane: blind). Mechanical checks are not factual-accuracy judgments; inspect
the image, prompt and final answers before choosing a model. Results do not
establish fitness for other tasks.

Complete per-model evidence artifact with image metadata, the source prompt, a
facts-only chooser, and full generated or crash output for every attempted
model.

## Reference Image

![Reference image](assets/source-image-c4aeb8d18432656f.jpg)

## Current-run Chooser

Mechanical observations and captured resource facts for this run only. No concerns detected does not mean the response fulfilled an arbitrary prompt or described the image accurately. Consult the assessment scope above. Total time is end-to-end; throughput covers generation only and requires at least 16 generated tokens. Prefill/first is first-token latency when captured; Prompt tok is the full rendered prompt including image tokens, which drives prefill cost. For cross-attention architectures the token count reflects the tokenised text burden only, not total vision prefill compute.

<!-- markdownlint-disable MD034 MD037 MD049 -->

| Model                                                                                                                   | Mechanical checks      | Total s | Gen TPS             | Prefill/first s | Peak GB | Prompt tok | Gen tok | Observations                                                                                                         |
|-------------------------------------------------------------------------------------------------------------------------|------------------------|---------|---------------------|-----------------|---------|------------|---------|----------------------------------------------------------------------------------------------------------------------|
| [`mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`](#model-mlx-community-devstral-small-2-24b-instruct-2512-5bit) | `no concerns detected` | 6.01s   | 31.3 tok/s          | 0.72            | 20      | 537        | 98      | none                                                                                                                 |
| [`mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`](#model-mlx-community-ernie-45-vl-28b-a3b-thinking-4bit)            | `no concerns detected` | 4.91s   | 141 tok/s           | 0.34            | 18      | 545        | 411     | none                                                                                                                 |
| [`mlx-community/GLM-4.6V-Flash-4bit`](#model-mlx-community-glm-46v-flash-4bit)                                          | `no concerns detected` | 2.06s   | 89.5 tok/s          | 0.33            | 8.0     | 499        | 48      | none                                                                                                                 |
| [`mlx-community/InternVL3-8B-bf16`](#model-mlx-community-internvl3-8b-bf16)                                             | `no concerns detected` | 4.54s   | 34.4 tok/s          | 1.19            | 17      | 3,435      | 60      | none                                                                                                                 |
| [`mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`](#model-mlx-community-kimi-vl-a3b-thinking-2506-8bit)                   | `no concerns detected` | 7.22s   | 73.8 tok/s          | 0.29            | 20      | 489        | 346     | none                                                                                                                 |
| [`mlx-community/LFM2.5-VL-1.6B-bf16`](#model-mlx-community-lfm25-vl-16b-bf16)                                           | `no concerns detected` | 1.21s   | 190 tok/s           | 0.08            | 4.0     | 350        | 100     | none                                                                                                                 |
| [`mlx-community/LFM2.5-VL-3B-OptiQ-4bit`](#model-mlx-community-lfm25-vl-3b-optiq-4bit)                                  | `no concerns detected` | 1.30s   | 218 tok/s           | 0.10            | 3.6     | 344        | 61      | none                                                                                                                 |
| [`mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-mxfp4)         | `no concerns detected` | 3.23s   | 70.0 tok/s          | 0.66            | 9.8     | 1,070      | 81      | none                                                                                                                 |
| [`mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-nvfp4)         | `no concerns detected` | 3.71s   | 67.3 tok/s          | 0.62            | 10      | 1,070      | 106     | none                                                                                                                 |
| [`mlx-community/Ministral-3-3B-Instruct-2512-4bit`](#model-mlx-community-ministral-3-3b-instruct-2512-4bit)             | `no concerns detected` | 1.66s   | 205 tok/s           | 0.24            | 4.5     | 1,069      | 97      | none                                                                                                                 |
| [`mlx-community/Molmo2-8B-4bit`](#model-mlx-community-molmo2-8b-4bit)                                                   | `no concerns detected` | 2.83s   | 74.2 tok/s          | 0.44            | 8.5     | 873        | 95      | none                                                                                                                 |
| [`mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`](#model-mlx-community-ornith-15-35b-a3b-optiq-4bit)                      | `no concerns detected` | 3.97s   | 109 tok/s           | 0.38            | 24      | 421        | 114     | none                                                                                                                 |
| [`mlx-community/Phi-3.5-vision-instruct-bf16`](#model-mlx-community-phi-35-vision-instruct-bf16)                        | `no concerns detected` | 2.75s   | 59.7 tok/s          | 0.22            | 9.3     | 883        | 96      | none                                                                                                                 |
| [`mlx-community/Qwen3.5-35B-A3B-4bit`](#model-mlx-community-qwen35-35b-a3b-4bit)                                        | `no concerns detected` | 3.60s   | 127 tok/s           | 0.36            | 21      | 421        | 89      | none                                                                                                                 |
| [`mlx-community/Qwen3.5-9B-MLX-4bit`](#model-mlx-community-qwen35-9b-mlx-4bit)                                          | `no concerns detected` | 2.30s   | 101 tok/s           | 0.27            | 7.0     | 421        | 71      | none                                                                                                                 |
| [`mlx-community/Qwen3.8-27B-4bit`](#model-mlx-community-qwen38-27b-4bit)                                                | `no concerns detected` | 5.38s   | 33.3 tok/s          | 0.70            | 17      | 421        | 86      | none                                                                                                                 |
| [`mlx-community/Qwen3.8-Flash-Next-4bit`](#model-mlx-community-qwen38-flash-next-4bit)                                  | `no concerns detected` | 111.61s | 32.5 tok/s          | 81.66           | 113     | 421        | 80      | none                                                                                                                 |
| [`mlx-community/SmolVLM2-2.2B-Instruct-mlx`](#model-mlx-community-smolvlm2-22b-instruct-mlx)                            | `no concerns detected` | 1.33s   | 127 tok/s           | 0.35            | 5.4     | 1,204      | 31      | none                                                                                                                 |
| [`mlx-community/diffusiongemma-26B-A4B-it-mxfp8`](#model-mlx-community-diffusiongemma-26b-a4b-it-mxfp8)                 | `no concerns detected` | 5.01s   | 51.2 tok/s          | 0.30            | 28      | 386        | 68      | none                                                                                                                 |
| [`mlx-community/gemma-3-27b-it-qat-4bit`](#model-mlx-community-gemma-3-27b-it-qat-4bit)                                 | `no concerns detected` | 5.84s   | 31.9 tok/s          | 0.78            | 17      | 379        | 89      | none                                                                                                                 |
| [`mlx-community/gemma-4-26b-a4b-it-4bit`](#model-mlx-community-gemma-4-26b-a4b-it-4bit)                                 | `no concerns detected` | 3.28s   | 131 tok/s           | 0.36            | 16      | 390        | 73      | none                                                                                                                 |
| [`mlx-community/gemma-4-31b-it-4bit`](#model-mlx-community-gemma-4-31b-it-4bit)                                         | `no concerns detected` | 6.32s   | 28.1 tok/s          | 0.83            | 19      | 390        | 80      | none                                                                                                                 |
| [`mlx-community/granite-4.0-3b-vision-4bit`](#model-mlx-community-granite-40-3b-vision-4bit)                            | `no concerns detected` | 1.25s   | 191 tok/s           | 0.25            | 4.7     | 734        | 64      | none                                                                                                                 |
| [`mlx-community/pixtral-12b-8bit`](#model-mlx-community-pixtral-12b-8bit)                                               | `no concerns detected` | 4.66s   | 40.4 tok/s          | 0.80            | 15      | 1,335      | 89      | none                                                                                                                 |
| [`LiquidAI/LFM2.5-VL-450M-MLX-bf16`](#model-liquidai-lfm25-vl-450m-mlx-bf16)                                            | `concerns detected`    | 0.65s   | 520 tok/s           | 0.05            | 1.3     | 350        | 77      | duplicate keywords                                                                                                   |
| [`mlx-community/GLM-4.6V-nvfp4`](#model-mlx-community-glm-46v-nvfp4)                                                    | `concerns detected`    | 8.88s   | 53.6 tok/s          | 1.34            | 63      | 499        | 84      | control tokens visible                                                                                               |
| [`mlx-community/North-Micro-Vision-Instruct-4bit`](#model-mlx-community-north-micro-vision-instruct-4bit)               | `concerns detected`    | 1.61s   | 276 tok/s           | 0.15            | 3.3     | 418        | 130     | duplicate keywords                                                                                                   |
| [`mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit`](#model-mlx-community-qwen3-vl-30b-a3b-instruct-4bit)                   | `concerns detected`    | 2.96s   | 130 tok/s           | 0.34            | 19      | 409        | 101     | duplicate keywords                                                                                                   |
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)                                 | `major concerns`       | 3.30s   | insufficient sample | 1.03            | 18      | 2,418      | 12      | labelled fields not detected                                                                                         |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit)                         | `major concerns`       | 42.23s  | 26.1 tok/s          | 0.96            | 25      | 545        | 1,000   | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords                        |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)                             | `major concerns`       | 3.93s   | 135 tok/s           | 0.10            | 5.3     | 411        | 400     | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| [`mlx-community/Step-3.7-Flash-oQ3e`](#model-mlx-community-step-37-flash-oq3e)                                          | `major concerns`       | 18.42s  | 54.3 tok/s          | 4.90            | 87      | 286        | 236     | answer emitted twice; control tokens visible                                                                         |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                                           | `major concerns`       | 7.23s   | 65.6 tok/s          | 0.26            | 10      | 511        | 375     | repeated text; stopped early: repeating; duplicate keywords                                                          |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                                            | `major concerns`       | 0.79s   | 397 tok/s           | 0.08            | 1.5     | 116        | 97      | labelled fields not detected                                                                                         |
<!-- markdownlint-enable MD034 MD037 MD049 -->

## Resource Highlights

Quickest completion without detected concerns (end-to-end, including model load): `mlx-community/LFM2.5-VL-1.6B-bf16` at 1.21s

Lowest peak memory among completions without detected concerns: `mlx-community/LFM2.5-VL-3B-OptiQ-4bit` at 3.6 GB

Decode tok/s stays per model in the chooser and is not averaged across models: tokenizers, image-token expansion and reasoning lengths differ too much for a cross-model mean to guide a choice.

## Avoid for This Run

<!-- markdownlint-disable MD034 MD037 MD049 -->

| Model                                                                                           | Mechanical checks | Observations                                                                                                         |
|-------------------------------------------------------------------------------------------------|-------------------|----------------------------------------------------------------------------------------------------------------------|
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)         | `major concerns`  | labelled fields not detected                                                                                         |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit) | `major concerns`  | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords                        |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)     | `major concerns`  | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| [`mlx-community/Step-3.7-Flash-oQ3e`](#model-mlx-community-step-37-flash-oq3e)                  | `major concerns`  | answer emitted twice; control tokens visible                                                                         |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                   | `major concerns`  | repeated text; stopped early: repeating; duplicate keywords                                                          |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                    | `major concerns`  | labelled fields not detected                                                                                         |
<!-- markdownlint-enable MD034 MD037 MD049 -->

## Output at a Glance

A compact preview of each model's final answer (or failure evidence for crashes), in chooser order. Where the requested catalogue fields were detected, the preview shows a little of each: the title, the start of the description, and the first keywords with their count, so the weakest field is not hidden behind a long description. Otherwise it is the first 280 characters. A closed reasoning trace is left out of the preview and reported as an omitted-character count; the complete output, trace included, is in the model's evidence block below.

<!-- markdownlint-disable MD034 MD037 MD049 -->

| Model                                                                                                                   | Mechanical checks      | Output preview                                                                                                                                                                                                                                                                                                                                                                        |
|-------------------------------------------------------------------------------------------------------------------------|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`](#model-mlx-community-devstral-small-2-24b-instruct-2512-5bit) | `no concerns detected` | Title: Two cats resting on a pink sofa \| Description: Two tabby cats are lying on a pink sofa, one on its back and the other on its side, with a remote contr... \| Keywords (18): cats, tabby, sofa, pink, remote control, resting, lying, natural lighting, striped fur, indoor, furniture, pet, ...                                                                               |
| [`mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`](#model-mlx-community-ernie-45-vl-28b-a3b-thinking-4bit)            | `no concerns detected` | Title: Two cats sleeping on a red couch \| Description: Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby. \| Keywords (10): cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal[1,266 characters of reasoning omitted; complete output in the evidence block]                                    |
| [`mlx-community/GLM-4.6V-Flash-4bit`](#model-mlx-community-glm-46v-flash-4bit)                                          | `no concerns detected` | Title: Two tabby cats on pink fabric. \| Description: Two tabby cats rest on a pink fabric surface, with remote controls nearby. \| Keywords (5): tabby cats, pink fabric, remote controls, resting, domestic cats.                                                                                                                                                                   |
| [`mlx-community/InternVL3-8B-bf16`](#model-mlx-community-internvl3-8b-bf16)                                             | `no concerns detected` | Title: Two Cats Sleeping on Pink Blanket \| Description: Two tabby cats are lying on a pink blanket with remote controls nearby, in a relaxed sleeping position. \| Keywords (11): cats, sleeping, pink blanket, remote controls, tabby, relaxed, blanket, resting, pets, cozy, indoor                                                                                                |
| [`mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`](#model-mlx-community-kimi-vl-a3b-thinking-2506-8bit)                   | `no concerns detected` | Title: Two tabby cats resting on pink fabric with remote controls \| Description: Two tabby cats lie on a pink fabric surface, each near a remote control, under brigh... \| Keywords (11): tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domestic animals, ...[1,182 characters of reasoning omitted; complete output in the evidence block] |
| [`mlx-community/LFM2.5-VL-1.6B-bf16`](#model-mlx-community-lfm25-vl-16b-bf16)                                           | `no concerns detected` | Title: Two Cats Resting on a Pink Blanket \| Description: Two cats are lying on a pink blanket, one is stretched out while the other is curled up. The cats ap... \| Keywords (11): cats, pink blanket, sleeping, green collar, relaxed posture, warm lighting, soft lighting, peaceful, curled up, ...                                                                               |
| [`mlx-community/LFM2.5-VL-3B-OptiQ-4bit`](#model-mlx-community-lfm25-vl-3b-optiq-4bit)                                  | `no concerns detected` | Title: Two cats sleeping on pink couch with remotes \| Description: Two tabby cats are lying on a pink couch, one with a green collar, next to two remote controls. \| Keywords (10): cats, sleeping, couch, pink, remotes, tabby, pets, furniture, relaxation, indoor                                                                                                                |
| [`mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-mxfp4)         | `no concerns detected` | Title: Two Cats Relaxing on Pink Cushioned Surface \| Description: Two cats lie stretched out on a pink cushioned surface, positioned near remote controls. The... \| Keywords (10): cats, pink cushioned surface, remote controls, relaxed posture, indoor setting, natural lighting, striped fur, ...                                                                               |
| [`mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-nvfp4)         | `no concerns detected` | Title: Relaxed Tabby Kittens on Pink Cushion \| Description: Two tabby kittens lie stretched out on a pink cushion, positioned near remote controls. Their relaxed... \| Keywords (15): kittens, tabby, pink cushion, remote controls, relaxed posture, indoor setting, soft fur, natural lighting, ...                                                                               |
| [`mlx-community/Ministral-3-3B-Instruct-2512-4bit`](#model-mlx-community-ministral-3-3b-instruct-2512-4bit)             | `no concerns detected` | Title: Two Kitten Friends on a Pink Couch \| Description: Two striped kittens lie relaxed on a bright pink cushion, each with a remote control beside them. The l... \| Keywords (11): kitten, domestic-cat, pink-cushion, remote-control, indoor-setting, relaxed, striped-fur, curled, stretched, ...                                                                               |
| [`mlx-community/Molmo2-8B-4bit`](#model-mlx-community-molmo2-8b-4bit)                                                   | `no concerns detected` | Title: Two Calico Cats Sleeping on Pink Bedding \| Description: Two calico cats are sleeping side by side on pink bedding. They are positioned with their heads facin... \| Keywords (10): calico cats, sleeping, pink bedding, white remotes, black and brown fur, white cats, striped cats, cozy, ...                                                                               |
| [`mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`](#model-mlx-community-ornith-15-35b-a3b-optiq-4bit)                      | `no concerns detected` | Title: Two Tabby Cats Sleeping on Pink Sofa With Remotes \| Description: Two striped tabby cats lie asleep on a bright pink sofa, one curled on its side and the ot... \| Keywords (15): tabby cats, pink sofa, sleeping cats, striped fur, television remotes, two cats, curled up, stretched out, ...                                                                               |
| [`mlx-community/Phi-3.5-vision-instruct-bf16`](#model-mlx-community-phi-35-vision-instruct-bf16)                        | `no concerns detected` | Title: Two Cats Sleeping on Sofa \| Description: Two cats are sleeping on a pink sofa with remote controls beside them. \| Keywords (21): cats, sleeping, sofa, remote controls, pink, relaxed, comfortable, domestic, indoor, pet, animal, resting, ...                                                                                                                              |
| [`mlx-community/Qwen3.5-35B-A3B-4bit`](#model-mlx-community-qwen35-35b-a3b-4bit)                                        | `no concerns detected` | Title: Two Tabby Cats Sleeping on Pink Sofa \| Description: Two tabby cats lie asleep on a bright pink sofa, each positioned near a white remote control. The scene is lit... \| Keywords (10): tabby cats, pink sofa, sleeping cats, remote controls, domestic interior, feline rest, striped fur, ...                                                                               |
| [`mlx-community/Qwen3.5-9B-MLX-4bit`](#model-mlx-community-qwen35-9b-mlx-4bit)                                          | `no concerns detected` | Title: Two Cats Sleeping on Pink Couch with Remotes \| Description: Two tabby cats are lying on a pink couch, each near a remote control, in a relaxed and comf... \| Keywords (12): cats, tabby, pink couch, remote control, sleeping, relaxed, comfortable, striped fur, cozy, domestic, restful, ...                                                                               |
| [`mlx-community/Qwen3.8-27B-4bit`](#model-mlx-community-qwen38-27b-4bit)                                                | `no concerns detected` | Title: Two Cats Sleeping on Pink Couch with Remotes \| Description: Two tabby cats are lying on their sides on a bright pink couch, with two white remote controls p... \| Keywords (12): cats, tabby, sleeping, pink couch, remote controls, striped fur, relaxed, indoor, pets, fabric, lounging, ...                                                                               |
| [`mlx-community/Qwen3.8-Flash-Next-4bit`](#model-mlx-community-qwen38-flash-next-4bit)                                  | `no concerns detected` | Title: Two Tabby Cats Resting on Pink Fabric \| Description: Two tabby cats are lying on a pink blanket, with two white remote controls placed nearby on the fabric. \| Keywords (18): cat, feline, pet, animal, tabby, sleeping, resting, pink, blanket, remote control, electronics, mammal, ...                                                                                    |
| [`mlx-community/SmolVLM2-2.2B-Instruct-mlx`](#model-mlx-community-smolvlm2-22b-instruct-mlx)                            | `no concerns detected` | Title: Two Cats on a Couch \| Description: Two cats are sleeping on a pink couch. \| Keywords (4): cats, couch, sleeping, pink                                                                                                                                                                                                                                                        |
| [`mlx-community/diffusiongemma-26B-A4B-it-mxfp8`](#model-mlx-community-diffusiongemma-26b-a4b-it-mxfp8)                 | `no concerns detected` | Title: Two tabby cats sleeping on a pink blanket \| Description: Two tabby cats lie curled up on a pink fabric surface next to two remote controls. \| Keywords (15): cats, tabby, sleeping, pink, blanket, sofa, couch, remote, controls, indoors, domestic, resting, fur, striped, ...                                                                                              |
| [`mlx-community/gemma-3-27b-it-qat-4bit`](#model-mlx-community-gemma-3-27b-it-qat-4bit)                                 | `no concerns detected` | Title: Two Tabby Cats Resting on Pink Fabric \| Description: Two tabby cats lie prone on a pink fabric surface, each with a remote control nearby. Both cats ar... \| Keywords (18): cats, tabby, pink, fabric, remote controls, sleeping, domestic animals, indoors, resting, lying down, striped, ...                                                                               |
| [`mlx-community/gemma-4-26b-a4b-it-4bit`](#model-mlx-community-gemma-4-26b-a4b-it-4bit)                                 | `no concerns detected` | Title: Two tabby cats lying on a pink surface \| Description: Two tabby cats lie on a bright pink fabric surface next to two remote controls. The cats are positione... \| Keywords (14): tabby, cats, pink, fabric, remote control, lying, indoor, domestic, striped, fur, two, pets, bright, daylight                                                                               |
| [`mlx-community/gemma-4-31b-it-4bit`](#model-mlx-community-gemma-4-31b-it-4bit)                                         | `no concerns detected` | Title: Two tabby cats lying on a pink blanket \| Description: Two tabby cats lie on a pink blanket atop a red sofa next to two remote controls. The scene is capture... \| Keywords (16): cats, tabby, pink blanket, red sofa, remote controls, lying down, pets, indoor, fabric, stripes, animals, ...                                                                               |
| [`mlx-community/granite-4.0-3b-vision-4bit`](#model-mlx-community-granite-40-3b-vision-4bit)                            | `no concerns detected` | Title: "Cats at Rest on a Vibrant Red Sofa" \| Description: Two cats are peacefully sleeping on a bright red sofa, with a remote control nearby, suggesting a domestic setting. \| Keywords (10): cats, rest, red sofa, remote control, domestic, comfort, striped, white, relaxed, home                                                                                              |
| [`mlx-community/pixtral-12b-8bit`](#model-mlx-community-pixtral-12b-8bit)                                               | `no concerns detected` | Title: Two Cats Lounging on Red Couch \| Description: Two cats, one lying on its back and the other on its side, relax on a red couch. Remote controls are plac... \| Keywords (17): cats, lounging, red couch, remote controls, relaxed, indoor, comfort, feline, domestic, paws, stretch, lounge, ...                                                                               |
| [`LiquidAI/LFM2.5-VL-450M-MLX-bf16`](#model-liquidai-lfm25-vl-450m-mlx-bf16)                                            | `concerns detected`    | Title: Cats on a Pink Couch \| Description: Two cats are lying on a pink couch, one is stretched out with its paws extended, while the other is curled up with its head restin... \| Keywords (11): cats, pink couch, cats, relaxation, comfortable, lounging, striped pattern, fur, cozy, indoor, pets                                                                               |
| [`mlx-community/GLM-4.6V-nvfp4`](#model-mlx-community-glm-46v-nvfp4)                                                    | `concerns detected`    | Title: (not detected) \| Description: Two cats lie on a pink couch, each near a remote control, with one cat’s head resting on the fabric and the other stretched... \| Keywords (15): cats, pink couch, remote controls, sleeping, relaxed, striped fur, feline, domestic, indoor, pets, lounging, ...                                                                               |
| [`mlx-community/North-Micro-Vision-Instruct-4bit`](#model-mlx-community-north-micro-vision-instruct-4bit)               | `concerns detected`    | Title: "Cats Resting on a Pink Couch" \| Description: "Two cats are comfortably sprawled on a vibrant pink couch, basking in the soft glow of natural light. One cat is... \| Keywords (18): cats, couch, sleeping, resting, relaxed, sleeping cats, couch scene, peaceful, lounging, cat sleeping, ...                                                                               |
| [`mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit`](#model-mlx-community-qwen3-vl-30b-a3b-instruct-4bit)                   | `concerns detected`    | Title: Two cats sleeping on pink fabric \| Description: Two cats are lying on a bright pink fabric surface. One cat is curled up on the left, while the other is... \| Keywords (20): cat, cats, pink, fabric, remote control, remote, sleeping, lying, curled, stretched, animal, domestic animal, ...                                                                               |
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)                                 | `major concerns`       | Two cats sleeping on a pink blanket with remotes.                                                                                                                                                                                                                                                                                                                                     |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit)                         | `major concerns`       | Title: (not detected) \| Description: (not detected) \| Keywords (20): We need British-English. Use only clearly visible facts. Omit uncertain details and unsupported identity, ...                                                                                                                                                                                                  |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)                             | `major concerns`       | Title: (not detected) \| Description: (not detected) \| Keywords (46): need 10-18 unique, comma-separated. Let's list: tabby cats, pink couch, resting, remote controls, two cats, ...                                                                                                                                                                                                |
| [`mlx-community/Step-3.7-Flash-oQ3e`](#model-mlx-community-step-37-flash-oq3e)                                          | `major concerns`       | Title: Two cats sleeping on a pink blanket \| Description: Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one c... \| Keywords (19): cats, sleeping, pink blanket, red sofa, tabby cats, remote controls, green collar, large cat, small cat, ...                                                                               |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                                           | `major concerns`       | Title: Cats Sleeping on Pink Couch with Remotes \| Description: Two tabby cats rest on a pink couch, one curled up with a remote, the other stretched out. The sett... \| Keywords (54): cats, sleeping, pink couch, tabby, striped, remote control, indoor, relaxation, feline, comfort, domestic, ...                                                                               |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                                            | `major concerns`       | Title: "A Study in Stripes" \| Description: A close-up of a person wearing a striped shirt, with a focus on the pattern and color of the fabric. The image is set against a pink background, and the person is lying on a bed covered with a pink blanket. The lighting... \| Keywords: (not detected)                                                                                |
<!-- markdownlint-enable MD034 MD037 MD049 -->

## Run Stamps

- `mlx-vlm`: `0.7.0rc0`
- `mlx`: `0.32.3.dev20260906+ce916dbbc`
- `transformers`: `5.16.1`
- `tokenizers`: `0.23.2`
- `huggingface-hub`: `1.30.0`
- *Python Version:* 3.14.7
- *OS:* Darwin 25.6.0
- *macOS Version:* 26.6.2
- *GPU/Chip:* Apple M5 Max
- *MLX Device:* Apple M5 Max
- *GPU Architecture:* applegpu_g17s
- *RAM:* 128.0 GB
- *Recommended Working Set:* 108 GB
- *Fused Attention:* Available

## Prompt

<!-- markdownlint-disable MD011 MD028 MD037 MD045 -->
>
> Create British-English catalogue metadata using only clearly visible facts.
> Omit uncertain details and unsupported identity, location, event, brand,
> species, period, or intent.
>
> &#8203;Write:
> &#45; a concrete 5-10-word title;
> &#45; a 1-2-sentence factual description of the main subject, setting, action,
> lighting, and distinctive details;
> &#45; 10-18 unique, comma-separated keywords.
>
> &#8203;Return exactly these three sections and nothing else:
> &#8203;Title:
> &#8203;Description:
> &#8203;Keywords:
<!-- markdownlint-enable MD011 MD028 MD037 MD045 -->

## Complete Per-model Evidence

Complete generated or crash evidence for every attempted model.

<a id="model-mlx-community-devstral-small-2-24b-instruct-2512-5bit"></a>

### mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit

<details>
<summary>Complete evidence: mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type mistral3)
- *Model load time:* 2.07s
- *Generation time:* 3.92s
- *Total time:* 6.01s
- *Input validation time:* 5.62e-05
- *Prompt preparation time:* 0.00704
- *First-token latency:* 0.719
- *Cleanup time:* 0.0949
- *Prompt tokens:* 537
- *Generation tokens:* 98
- *Total tokens:* 635
- *Prompt throughput (raw):* 746 tok/s
- *Generation throughput (raw):* 31.3 tok/s
- *Peak memory:* 20
- *Active memory:* 18
- *Cache memory:* 0.14
- *Model-load active memory:* 18
- *Post-cleanup active memory:* 0.000394
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 472
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.mistral3.processing_mistral3.Mistral3Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 0a970d20ad7da57b0e2accc35c5b8628f5d02063
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Devstral-Small-2-24B-Instruct-2512-5bit/snapshots/0a970d20ad7da57b0e2accc35c5b8628f5d02063
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
Title:
Two cats resting on a pink sofa

Description:
Two tabby cats are lying on a pink sofa, one on its back and the other on its side, with a remote control nearby. The lighting is natural, and the cats have distinctive striped fur patterns.

Keywords: cats, tabby, sofa, pink, remote control, resting, lying, natural lighting, striped fur, indoor, furniture, pet, relaxation, home, domestic, fur, pattern, leisure
</pre>

</details>

---

<a id="model-mlx-community-ernie-45-vl-28b-a3b-thinking-4bit"></a>

### mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit

<details>
<summary>Complete evidence: mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type ernie4_5_moe_vl)
- *Model load time:* 1.62s
- *Generation time:* 3.27s
- *Total time:* 4.91s
- *Input validation time:* 0.000112
- *Prompt preparation time:* 0.0082
- *First-token latency:* 0.336
- *Cleanup time:* 0.0977
- *Prompt tokens:* 545
- *Generation tokens:* 411
- *Total tokens:* 956
- *Prompt throughput (raw):* 1,621 tok/s
- *Generation throughput (raw):* 141 tok/s
- *Peak memory:* 18
- *Active memory:* 17
- *Cache memory:* 0.07
- *Model-load active memory:* 17.4
- *Post-cleanup active memory:* 0.000607
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 662
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.ernie4_5_moe_vl.processing_ernie4_5_moe_vl.Ernie4_5_VLProcessor
- *Tokenizer:* mlx_vlm.models.ernie4_5_moe_vl.processing_ernie4_5_moe_vl.Ernie4_5_VLTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 846ea5576854468f25af3767d769b0805b1b08b6
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--ERNIE-4.5-VL-28B-A3B-Thinking-4bit/snapshots/846ea5576854468f25af3767d769b0805b1b08b6
- *Generation settings:* {"enable_thinking": true, "max_tokens": 1000,
  "prefill_step_size": 2048, "temperature": 0.0, "thinking_budget": 800,
  "thinking_end_token": "&lt;/think&gt;", "thinking_start_token":
  "&lt;think&gt;", "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
Alright, here's what I'm thinking. I need to generate some metadata for this image, and it has to be in British English. First things first, I need to break down the image. It's a photo of two cats on a couch. One's a calico, the other a tiger-striped one. They're both sleeping. The couch is red, and there's a remote control nearby.

Now, for the title. I want something short and sweet. "Two cats sleeping on a red couch" seems perfect. Concise and descriptive.

Next, the description. I need to cover the main subject, setting, action, lighting, and any distinctive details. So, I'll say: "Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby." That covers everything.

Finally, the keywords. I need to be specific, but not too specific. I'll go with: "cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal." That should be a good mix of general and specific terms.

Okay, let's double-check. Title: "Two cats sleeping on a red couch." Description: "Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby." Keywords: "cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal." Yep, that's all I need.
&lt;/think&gt;

Title: Two cats sleeping on a red couch

Description: Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby.

Keywords: cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal
</pre>

<details>
<summary>Exact raw output</summary>

```text
Alright, here's what I'm thinking. I need to generate some metadata for this image, and it has to be in British English. First things first, I need to break down the image. It's a photo of two cats on a couch. One's a calico, the other a tiger-striped one. They're both sleeping. The couch is red, and there's a remote control nearby.

Now, for the title. I want something short and sweet. "Two cats sleeping on a red couch" seems perfect. Concise and descriptive.

Next, the description. I need to cover the main subject, setting, action, lighting, and any distinctive details. So, I'll say: "Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby." That covers everything.

Finally, the keywords. I need to be specific, but not too specific. I'll go with: "cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal." That should be a good mix of general and specific terms.

Okay, let's double-check. Title: "Two cats sleeping on a red couch." Description: "Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby." Keywords: "cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal." Yep, that's all I need.
</think>

Title: Two cats sleeping on a red couch

Description: Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby.

Keywords: cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal
```

</details>

</details>

---

<a id="model-mlx-community-glm-46v-flash-4bit"></a>

### mlx-community/GLM-4.6V-Flash-4bit

<details>
<summary>Complete evidence: mlx-community/GLM-4.6V-Flash-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type glm4v)
- *Model load time:* 1.17s
- *Generation time:* 0.88s
- *Total time:* 2.06s
- *Input validation time:* 7.5e-05
- *Prompt preparation time:* 0.00773
- *First-token latency:* 0.326
- *Cleanup time:* 0.0749
- *Prompt tokens:* 499
- *Generation tokens:* 48
- *Total tokens:* 547
- *Prompt throughput (raw):* 1,532 tok/s
- *Generation throughput (raw):* 89.5 tok/s
- *Peak memory:* 8.0
- *Active memory:* 7.1
- *Cache memory:* 0.05
- *Model-load active memory:* 7.07
- *Post-cleanup active memory:* 0.000919
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 553
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.glm4v.processing.Glm46VProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* bd7b20686e8cbf22ad221a3de8399cdc5a2a7e0e
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--GLM-4.6V-Flash-4bit/snapshots/bd7b20686e8cbf22ad221a3de8399cdc5a2a7e0e
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|endoftext\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two tabby cats on pink fabric.
Description: Two tabby cats rest on a pink fabric surface, with remote controls nearby.
Keywords: tabby cats, pink fabric, remote controls, resting, domestic cats.
</pre>

</details>

---

<a id="model-mlx-community-internvl3-8b-bf16"></a>

### mlx-community/InternVL3-8B-bf16

<details>
<summary>Complete evidence: mlx-community/InternVL3-8B-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type internvl_chat)
- *Model load time:* 1.56s
- *Generation time:* 2.97s
- *Total time:* 4.54s
- *Input validation time:* 5.77e-05
- *Prompt preparation time:* 0.00274
- *First-token latency:* 1.19
- *Cleanup time:* 0.0941
- *Prompt tokens:* 3,435
- *Generation tokens:* 60
- *Total tokens:* 3,495
- *Prompt throughput (raw):* 2,878 tok/s
- *Generation throughput (raw):* 34.4 tok/s
- *Peak memory:* 17
- *Active memory:* 16
- *Cache memory:* 0.27
- *Model-load active memory:* 15.9
- *Post-cleanup active memory:* 0.0018
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 477
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.internvl_chat.processor.InternVLChatProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* e0df3dd79263467173214b67ef6d6a0cc5a475fd
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--InternVL3-8B-bf16/snapshots/e0df3dd79263467173214b67ef6d6a0cc5a475fd
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Cats Sleeping on Pink Blanket
Description: Two tabby cats are lying on a pink blanket with remote controls nearby, in a relaxed sleeping position.
Keywords: cats, sleeping, pink blanket, remote controls, tabby, relaxed, blanket, resting, pets, cozy, indoor
</pre>

</details>

---

<a id="model-mlx-community-kimi-vl-a3b-thinking-2506-8bit"></a>

### mlx-community/Kimi-VL-A3B-Thinking-2506-8bit

<details>
<summary>Complete evidence: mlx-community/Kimi-VL-A3B-Thinking-2506-8bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type kimi_vl)
- *Model load time:* 2.10s
- *Generation time:* 5.10s
- *Total time:* 7.22s
- *Input validation time:* 5.72e-05
- *Prompt preparation time:* 0.00382
- *First-token latency:* 0.288
- *Cleanup time:* 0.101
- *Prompt tokens:* 489
- *Generation tokens:* 346
- *Total tokens:* 835
- *Prompt throughput (raw):* 1,698 tok/s
- *Generation throughput (raw):* 73.8 tok/s
- *Peak memory:* 20
- *Active memory:* 18
- *Cache memory:* 0.77
- *Model-load active memory:* 17.8
- *Post-cleanup active memory:* 0.00246
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 659
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.kimi_vl.processing_kimi_vl.KimiVLProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* e5abbe34cbfabd829fafd0362856e5b468d19f85
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Kimi-VL-A3B-Thinking-2506-8bit/snapshots/e5abbe34cbfabd829fafd0362856e5b468d19f85
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* [EOS]

*Readable output:*

<pre class="model-output-readable">
◁think▷Okay, let's tackle this query. The user wants a British-English catalogue metadata based on the image. First, I need to identify the main elements. The image shows two tabby cats on a pink fabric surface, likely a couch. There are two remote controls, one near each cat. The cats are lying down, one facing left, the other right. The lighting is bright, making the colors vivid. The style is high contrast with a pink background.

For the title, something concise: "Two tabby cats resting on pink fabric with remote controls." That's 10 words.

Description needs to be 1-2 sentences. Mention the cats, their position, the fabric, remotes, and the lighting. So: "Two tabby cats lie on a pink fabric surface, each near a remote control, under bright lighting."

Keywords: Need 10-18 unique terms. Let's list them: tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domestic animals, indoor scene, bright lighting, striped fur, relaxed cats. That's 10 keywords. Check if they are all visible and relevant. Yep, all are clear from the image. Make sure no unsupported details. No species, location, period, etc. All facts are visible.◁/think▷Title: Two tabby cats resting on pink fabric with remote controls
Description: Two tabby cats lie on a pink fabric surface, each near a remote control, under bright lighting.
Keywords: tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domestic animals, indoor scene, bright lighting, striped fur, relaxed cats
</pre>

<details>
<summary>Exact raw output</summary>

```text
◁think▷Okay, let's tackle this query. The user wants a British-English catalogue metadata based on the image. First, I need to identify the main elements. The image shows two tabby cats on a pink fabric surface, likely a couch. There are two remote controls, one near each cat. The cats are lying down, one facing left, the other right. The lighting is bright, making the colors vivid. The style is high contrast with a pink background. 

For the title, something concise: "Two tabby cats resting on pink fabric with remote controls." That's 10 words. 

Description needs to be 1-2 sentences. Mention the cats, their position, the fabric, remotes, and the lighting. So: "Two tabby cats lie on a pink fabric surface, each near a remote control, under bright lighting." 

Keywords: Need 10-18 unique terms. Let's list them: tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domestic animals, indoor scene, bright lighting, striped fur, relaxed cats. That's 10 keywords. Check if they are all visible and relevant. Yep, all are clear from the image. Make sure no unsupported details. No species, location, period, etc. All facts are visible.◁/think▷Title: Two tabby cats resting on pink fabric with remote controls  
Description: Two tabby cats lie on a pink fabric surface, each near a remote control, under bright lighting.  
Keywords: tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domestic animals, indoor scene, bright lighting, striped fur, relaxed cats
```

</details>

</details>

---

<a id="model-mlx-community-lfm25-vl-16b-bf16"></a>

### mlx-community/LFM2.5-VL-1.6B-bf16

<details>
<summary>Complete evidence: mlx-community/LFM2.5-VL-1.6B-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type lfm2_vl)
- *Model load time:* 0.56s
- *Generation time:* 0.64s
- *Total time:* 1.21s
- *Input validation time:* 5.64e-05
- *Prompt preparation time:* 0.00413
- *First-token latency:* 0.0842
- *Cleanup time:* 0.0702
- *Prompt tokens:* 350
- *Generation tokens:* 100
- *Total tokens:* 450
- *Prompt throughput (raw):* 4,157 tok/s
- *Generation throughput (raw):* 190 tok/s
- *Peak memory:* 4.0
- *Active memory:* 3.2
- *Cache memory:* 0.01
- *Model-load active memory:* 3.2
- *Post-cleanup active memory:* 0.00259
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 523
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* transformers.models.lfm2_vl.processing_lfm2_vl.Lfm2VlProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 16a710cf8afca206ff16a95a4ad6fe657f876ce1
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--LFM2.5-VL-1.6B-bf16/snapshots/16a710cf8afca206ff16a95a4ad6fe657f876ce1
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Cats Resting on a Pink Blanket

Description: Two cats are lying on a pink blanket, one is stretched out while the other is curled up. The cats appear to be sleeping peacefully, with one having a green collar. The lighting is soft and warm, highlighting the relaxed posture of the cats.

Keywords: cats, pink blanket, sleeping, green collar, relaxed posture, warm lighting, soft lighting, peaceful, curled up, stretched out, comfortable
</pre>

</details>

---

<a id="model-mlx-community-lfm25-vl-3b-optiq-4bit"></a>

### mlx-community/LFM2.5-VL-3B-OptiQ-4bit

<details>
<summary>Complete evidence: mlx-community/LFM2.5-VL-3B-OptiQ-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type lfm2_vl)
- *Model load time:* 0.88s
- *Generation time:* 0.41s
- *Total time:* 1.30s
- *Input validation time:* 5.27e-05
- *Prompt preparation time:* 0.00917
- *First-token latency:* 0.0997
- *Cleanup time:* 0.0706
- *Prompt tokens:* 344
- *Generation tokens:* 61
- *Total tokens:* 405
- *Prompt throughput (raw):* 3,450 tok/s
- *Generation throughput (raw):* 218 tok/s
- *Peak memory:* 3.6
- *Active memory:* 2.8
- *Cache memory:* 0.02
- *Model-load active memory:* 2.81
- *Post-cleanup active memory:* 0.00285
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 523
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* transformers.models.lfm2_vl.processing_lfm2_vl.Lfm2VlProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 12c5ae49304158b0a133fcea9ba4486a6d6c8cad
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--LFM2.5-VL-3B-OptiQ-4bit/snapshots/12c5ae49304158b0a133fcea9ba4486a6d6c8cad
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two cats sleeping on pink couch with remotes
Description: Two tabby cats are lying on a pink couch, one with a green collar, next to two remote controls.
Keywords: cats, sleeping, couch, pink, remotes, tabby, pets, furniture, relaxation, indoor
</pre>

</details>

---

<a id="model-mlx-community-ministral-3-14b-instruct-2512-mxfp4"></a>

### mlx-community/Ministral-3-14B-Instruct-2512-mxfp4

<details>
<summary>Complete evidence: mlx-community/Ministral-3-14B-Instruct-2512-mxfp4</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type mistral3)
- *Model load time:* 1.39s
- *Generation time:* 1.84s
- *Total time:* 3.23s
- *Input validation time:* 5.04e-05
- *Prompt preparation time:* 0.00756
- *First-token latency:* 0.663
- *Cleanup time:* 0.0812
- *Prompt tokens:* 1,070
- *Generation tokens:* 81
- *Total tokens:* 1,151
- *Prompt throughput (raw):* 1,613 tok/s
- *Generation throughput (raw):* 70.0 tok/s
- *Peak memory:* 9.8
- *Active memory:* 8.0
- *Cache memory:* 0.23
- *Model-load active memory:* 8
- *Post-cleanup active memory:* 0.00311
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 2910
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.mistral3.processing_mistral3.Mistral3Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 7c992876448fc5426841a85c6eb951b056fe38d2
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Ministral-3-14B-Instruct-2512-mxfp4/snapshots/7c992876448fc5426841a85c6eb951b056fe38d2
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
Title:
Two Cats Relaxing on Pink Cushioned Surface

Description:
Two cats lie stretched out on a pink cushioned surface, positioned near remote controls. The lighting is natural, and the cats appear calm and at ease.

Keywords:
cats, pink cushioned surface, remote controls, relaxed posture, indoor setting, natural lighting, striped fur, resting, cushioned fabric, domestic scene
</pre>

</details>

---

<a id="model-mlx-community-ministral-3-14b-instruct-2512-nvfp4"></a>

### mlx-community/Ministral-3-14B-Instruct-2512-nvfp4

<details>
<summary>Complete evidence: mlx-community/Ministral-3-14B-Instruct-2512-nvfp4</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type mistral3)
- *Model load time:* 1.44s
- *Generation time:* 2.26s
- *Total time:* 3.71s
- *Input validation time:* 5.83e-05
- *Prompt preparation time:* 0.000948
- *First-token latency:* 0.622
- *Cleanup time:* 0.0895
- *Prompt tokens:* 1,070
- *Generation tokens:* 106
- *Total tokens:* 1,176
- *Prompt throughput (raw):* 1,719 tok/s
- *Generation throughput (raw):* 67.3 tok/s
- *Peak memory:* 10
- *Active memory:* 8.4
- *Cache memory:* 0.23
- *Model-load active memory:* 8.43
- *Post-cleanup active memory:* 0.00338
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 2910
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.mistral3.processing_mistral3.Mistral3Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 28777b889d841a86369c736175cb77258c8134b2
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Ministral-3-14B-Instruct-2512-nvfp4/snapshots/28777b889d841a86369c736175cb77258c8134b2
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
**Title:**
Relaxed Tabby Kittens on Pink Cushion

**Description:**
Two tabby kittens lie stretched out on a pink cushion, positioned near remote controls. Their relaxed postures and soft fur highlight a calm, indoor setting with natural lighting.

**Keywords:**
kittens, tabby, pink cushion, remote controls, relaxed posture, indoor setting, soft fur, natural lighting, calm atmosphere, stretched out, pink fabric, domestic scene, fur patterns, resting pose, cushioned surface
</pre>

</details>

---

<a id="model-mlx-community-ministral-3-3b-instruct-2512-4bit"></a>

### mlx-community/Ministral-3-3B-Instruct-2512-4bit

<details>
<summary>Complete evidence: mlx-community/Ministral-3-3B-Instruct-2512-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type mistral3)
- *Model load time:* 0.91s
- *Generation time:* 0.74s
- *Total time:* 1.66s
- *Input validation time:* 6.68e-05
- *Prompt preparation time:* 0.00721
- *First-token latency:* 0.236
- *Cleanup time:* 0.0742
- *Prompt tokens:* 1,069
- *Generation tokens:* 97
- *Total tokens:* 1,166
- *Prompt throughput (raw):* 4,528 tok/s
- *Generation throughput (raw):* 205 tok/s
- *Peak memory:* 4.5
- *Active memory:* 2.8
- *Cache memory:* 0.16
- *Model-load active memory:* 2.75
- *Post-cleanup active memory:* 0.00364
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 2909
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.mistral3.processing_mistral3.Mistral3Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* a962dcb09eee4169c890e544c9eb938f1113fdee
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Ministral-3-3B-Instruct-2512-4bit/snapshots/a962dcb09eee4169c890e544c9eb938f1113fdee
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
Title:
Two Kitten Friends on a Pink Couch

Description:
Two striped kittens lie relaxed on a bright pink cushion, each with a remote control beside them. The larger kitten is curled, while the smaller one stretches out, bathed in soft indoor lighting.

Keywords:
kitten, domestic-cat, pink-cushion, remote-control, indoor-setting, relaxed, striped-fur, curled, stretched, domestic-interior, pet-portrait
</pre>

</details>

---

<a id="model-mlx-community-molmo2-8b-4bit"></a>

### mlx-community/Molmo2-8B-4bit

<details>
<summary>Complete evidence: mlx-community/Molmo2-8B-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type molmo2)
- *Model load time:* 1.05s
- *Generation time:* 1.77s
- *Total time:* 2.83s
- *Input validation time:* 4.57e-05
- *Prompt preparation time:* 0.00553
- *First-token latency:* 0.441
- *Cleanup time:* 0.0775
- *Prompt tokens:* 873
- *Generation tokens:* 95
- *Total tokens:* 968
- *Prompt throughput (raw):* 1,980 tok/s
- *Generation throughput (raw):* 74.2 tok/s
- *Peak memory:* 8.5
- *Active memory:* 6.4
- *Cache memory:* 0.17
- *Model-load active memory:* 6.45
- *Post-cleanup active memory:* 0.00395
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 510
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.molmo2.processing.Molmo2Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 4fcbe926577641af12aa5086cf5c292db9dd9730
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Molmo2-8B-4bit/snapshots/4fcbe926577641af12aa5086cf5c292db9dd9730
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Calico Cats Sleeping on Pink Bedding

Description: Two calico cats are sleeping side by side on pink bedding. They are positioned with their heads facing each other and their tails touching. The cats have white, black, and brown fur. Two white remote controls are visible behind the cats.

Keywords: calico cats, sleeping, pink bedding, white remotes, black and brown fur, white cats, striped cats, cozy, relaxed, feline
</pre>

</details>

---

<a id="model-mlx-community-ornith-15-35b-a3b-optiq-4bit"></a>

### mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit

<details>
<summary>Complete evidence: mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_5_moe)
- *Model load time:* 2.50s
- *Generation time:* 1.44s
- *Total time:* 3.97s
- *Input validation time:* 5.57e-05
- *Prompt preparation time:* 0.0161
- *First-token latency:* 0.378
- *Cleanup time:* 0.129
- *Prompt tokens:* 421
- *Generation tokens:* 114
- *Total tokens:* 535
- *Prompt throughput (raw):* 1,114 tok/s
- *Generation throughput (raw):* 109 tok/s
- *Peak memory:* 24
- *Active memory:* 23
- *Cache memory:* 0.10
- *Model-load active memory:* 23.1
- *Post-cleanup active memory:* 0.00539
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 563
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 5f31fcd089ce6f47f1073d3ae43dcb3a0bd1869f
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Ornith-1.5-35B-A3B-OptiQ-4bit/snapshots/5f31fcd089ce6f47f1073d3ae43dcb3a0bd1869f
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Tabby Cats Sleeping on Pink Sofa With Remotes

Description: Two striped tabby cats lie asleep on a bright pink sofa, one curled on its side and the other stretched out, with two white television remote controls resting nearby. The scene is evenly lit, showing their fur patterns and relaxed postures clearly.

Keywords: tabby cats, pink sofa, sleeping cats, striped fur, television remotes, two cats, curled up, stretched out, indoor scene, soft lighting, animal rest, domestic cats, furniture, cozy setting, pet photography
</pre>

</details>

---

<a id="model-mlx-community-phi-35-vision-instruct-bf16"></a>

### mlx-community/Phi-3.5-vision-instruct-bf16

<details>
<summary>Complete evidence: mlx-community/Phi-3.5-vision-instruct-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type phi3_v)
- *Model load time:* 0.86s
- *Generation time:* 1.89s
- *Total time:* 2.75s
- *Input validation time:* 6.73e-05
- *Prompt preparation time:* 0.0016
- *First-token latency:* 0.216
- *Cleanup time:* 0.0818
- *Prompt tokens:* 883
- *Generation tokens:* 96
- *Total tokens:* 979
- *Prompt throughput (raw):* 4,079 tok/s
- *Generation throughput (raw):* 59.7 tok/s
- *Peak memory:* 9.3
- *Active memory:* 8.3
- *Cache memory:* 0.42
- *Model-load active memory:* 8.3
- *Post-cleanup active memory:* 0.00546
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 493
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.phi3_v.processing_phi3_v.Phi3VProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* d8da684308c275a86659e2b36a9189b2f4aec8ea
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Phi-3.5-vision-instruct-bf16/snapshots/d8da684308c275a86659e2b36a9189b2f4aec8ea
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|endoftext\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Cats Sleeping on Sofa

Description: Two cats are sleeping on a pink sofa with remote controls beside them.

Keywords: cats, sleeping, sofa, remote controls, pink, relaxed, comfortable, domestic, indoor, pet, animal, resting, tranquil, domesticated, feline, fur, relaxation, peaceful, cozy, home, companionship
</pre>

</details>

---

<a id="model-mlx-community-qwen35-35b-a3b-4bit"></a>

### mlx-community/Qwen3.5-35B-A3B-4bit

<details>
<summary>Complete evidence: mlx-community/Qwen3.5-35B-A3B-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_5_moe)
- *Model load time:* 2.51s
- *Generation time:* 1.07s
- *Total time:* 3.60s
- *Input validation time:* 5.81e-05
- *Prompt preparation time:* 0.0156
- *First-token latency:* 0.356
- *Cleanup time:* 0.121
- *Prompt tokens:* 421
- *Generation tokens:* 89
- *Total tokens:* 510
- *Prompt throughput (raw):* 1,182 tok/s
- *Generation throughput (raw):* 127 tok/s
- *Peak memory:* 21
- *Active memory:* 20
- *Cache memory:* 0.09
- *Model-load active memory:* 20.4
- *Post-cleanup active memory:* 0.00659
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 563
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 1e20fd8d42056f870933bf98ca6211024744f7ec
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-35B-A3B-4bit/snapshots/1e20fd8d42056f870933bf98ca6211024744f7ec
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Tabby Cats Sleeping on Pink Sofa

Description: Two tabby cats lie asleep on a bright pink sofa, each positioned near a white remote control. The scene is lit by even indoor lighting, highlighting the cats’ striped fur and relaxed postures.

Keywords: tabby cats, pink sofa, sleeping cats, remote controls, domestic interior, feline rest, striped fur, pet relaxation, home setting, animal stillness
</pre>

</details>

---

<a id="model-mlx-community-qwen35-9b-mlx-4bit"></a>

### mlx-community/Qwen3.5-9B-MLX-4bit

<details>
<summary>Complete evidence: mlx-community/Qwen3.5-9B-MLX-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_5)
- *Model load time:* 1.31s
- *Generation time:* 0.98s
- *Total time:* 2.30s
- *Input validation time:* 7.34e-05
- *Prompt preparation time:* 0.00131
- *First-token latency:* 0.269
- *Cleanup time:* 0.0835
- *Prompt tokens:* 421
- *Generation tokens:* 71
- *Total tokens:* 492
- *Prompt throughput (raw):* 1,566 tok/s
- *Generation throughput (raw):* 101 tok/s
- *Peak memory:* 7.0
- *Active memory:* 6.0
- *Cache memory:* 0.11
- *Model-load active memory:* 5.96
- *Post-cleanup active memory:* 0.0071
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 563
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 938d8919941c6e7efd3c7150eff7fe9d12afa631
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-9B-MLX-4bit/snapshots/938d8919941c6e7efd3c7150eff7fe9d12afa631
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Cats Sleeping on Pink Couch with Remotes

Description: Two tabby cats are lying on a pink couch, each near a remote control, in a relaxed and comfortable setting.

Keywords: cats, tabby, pink couch, remote control, sleeping, relaxed, comfortable, striped fur, cozy, domestic, restful, soft lighting
</pre>

</details>

---

<a id="model-mlx-community-qwen38-27b-4bit"></a>

### mlx-community/Qwen3.8-27B-4bit

<details>
<summary>Complete evidence: mlx-community/Qwen3.8-27B-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_5)
- *Model load time:* 2.05s
- *Generation time:* 3.30s
- *Total time:* 5.38s
- *Input validation time:* 5.35e-05
- *Prompt preparation time:* 0.0165
- *First-token latency:* 0.698
- *Cleanup time:* 0.115
- *Prompt tokens:* 421
- *Generation tokens:* 86
- *Total tokens:* 507
- *Prompt throughput (raw):* 604 tok/s
- *Generation throughput (raw):* 33.3 tok/s
- *Peak memory:* 17
- *Active memory:* 16
- *Cache memory:* 0.22
- *Model-load active memory:* 16.1
- *Post-cleanup active memory:* 0.0076
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 563
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 3e6447f082e89cc7f0bc6e5441afd38dfce760ff
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3.8-27B-4bit/snapshots/3e6447f082e89cc7f0bc6e5441afd38dfce760ff
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Cats Sleeping on Pink Couch with Remotes

Description: Two tabby cats are lying on their sides on a bright pink couch, with two white remote controls placed nearby. The scene is evenly lit, highlighting the cats' striped fur and relaxed postures.

Keywords: cats, tabby, sleeping, pink couch, remote controls, striped fur, relaxed, indoor, pets, fabric, lounging, domestic
</pre>

</details>

---

<a id="model-mlx-community-qwen38-flash-next-4bit"></a>

### mlx-community/Qwen3.8-Flash-Next-4bit

<details>
<summary>Complete evidence: mlx-community/Qwen3.8-Flash-Next-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type qwen4_exp)
- *Model load time:* 17.72s
- *Generation time:* 93.88s
- *Total time:* 111.61s
- *Input validation time:* 6.13e-05
- *Prompt preparation time:* 0.00796
- *First-token latency:* 81.7
- *Cleanup time:* 0.427
- *Prompt tokens:* 421
- *Generation tokens:* 80
- *Total tokens:* 501
- *Prompt throughput (raw):* 5.16 tok/s
- *Generation throughput (raw):* 32.5 tok/s
- *Peak memory:* 113
- *Active memory:* 112
- *Cache memory:* 0.27
- *Model-load active memory:* 112
- *Post-cleanup active memory:* 0.00811
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 563
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 07b5dc6c54600a359b87f1e53e7adf6351c72a2c
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3.8-Flash-Next-4bit/snapshots/07b5dc6c54600a359b87f1e53e7adf6351c72a2c
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Two Tabby Cats Resting on Pink Fabric

Description: Two tabby cats are lying on a pink blanket, with two white remote controls placed nearby on the fabric.

Keywords: cat, feline, pet, animal, tabby, sleeping, resting, pink, blanket, remote control, electronics, mammal, striped, fur, paws, tail, indoor, domestic
</pre>

</details>

---

<a id="model-mlx-community-smolvlm2-22b-instruct-mlx"></a>

### mlx-community/SmolVLM2-2.2B-Instruct-mlx

<details>
<summary>Complete evidence: mlx-community/SmolVLM2-2.2B-Instruct-mlx</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type smolvlm)
- *Model load time:* 0.64s
- *Generation time:* 0.68s
- *Total time:* 1.33s
- *Input validation time:* 7.58e-05
- *Prompt preparation time:* 0.00277
- *First-token latency:* 0.349
- *Cleanup time:* 0.0798
- *Prompt tokens:* 1,204
- *Generation tokens:* 31
- *Total tokens:* 1,235
- *Prompt throughput (raw):* 3,446 tok/s
- *Generation throughput (raw):* 127 tok/s
- *Peak memory:* 5.4
- *Active memory:* 4.5
- *Cache memory:* 0.30
- *Model-load active memory:* 4.5
- *Post-cleanup active memory:* 0.00823
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 504
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.smolvlm.processing_smolvlm.SmolVLMProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 844516024a1c4400d34489b89ee067d794e432ed
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--SmolVLM2-2.2B-Instruct-mlx/snapshots/844516024a1c4400d34489b89ee067d794e432ed
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <end_of_utterance>

*Readable output:*

<pre class="model-output-readable">
 Title: Two Cats on a Couch
Description: Two cats are sleeping on a pink couch.
Keywords: cats, couch, sleeping, pink
</pre>

</details>

---

<a id="model-mlx-community-diffusiongemma-26b-a4b-it-mxfp8"></a>

### mlx-community/diffusiongemma-26B-A4B-it-mxfp8

<details>
<summary>Complete evidence: mlx-community/diffusiongemma-26B-A4B-it-mxfp8</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type diffusion_gemma)
- *Model load time:* 3.21s
- *Generation time:* 1.78s
- *Total time:* 5.01s
- *Input validation time:* 7.12e-05
- *Prompt preparation time:* 0.0223
- *First-token latency:* 0.302
- *Cleanup time:* 0.123
- *Prompt tokens:* 386
- *Generation tokens:* 68
- *Total tokens:* 454
- *Prompt throughput (raw):* 1,280 tok/s
- *Generation throughput (raw):* 51.2 tok/s
- *Peak memory:* 28
- *Active memory:* 27
- *Cache memory:* 0.01
- *Model-load active memory:* 27.2
- *Post-cleanup active memory:* 0.0088
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 498
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.diffusion_gemma.processing_diffusion_gemma.DiffusionGemma4Processor
- *Tokenizer:* transformers.models.gemma.tokenization_gemma.GemmaTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* ded389e478f86d498ad9e7f47666e83b166a28f1
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--diffusiongemma-26B-A4B-it-mxfp8/snapshots/ded389e478f86d498ad9e7f47666e83b166a28f1
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;eos&gt;

*Readable output:*

<pre class="model-output-readable">
Title: Two tabby cats sleeping on a pink blanket
Description: Two tabby cats lie curled up on a pink fabric surface next to two remote controls.
Keywords: cats, tabby, sleeping, pink, blanket, sofa, couch, remote, controls, indoors, domestic, resting, fur, striped, feline
</pre>

<details>
<summary>Exact raw output</summary>

```text
Title: Two tabby cats sleeping on a pink blanket
Description: Two tabby cats lie curled up on a pink fabric surface next to two remote controls. 
Keywords: cats, tabby, sleeping, pink, blanket, sofa, couch, remote, controls, indoors, domestic, resting, fur, striped, feline
```

</details>

</details>

---

<a id="model-mlx-community-gemma-3-27b-it-qat-4bit"></a>

### mlx-community/gemma-3-27b-it-qat-4bit

<details>
<summary>Complete evidence: mlx-community/gemma-3-27b-it-qat-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type gemma3)
- *Model load time:* 2.23s
- *Generation time:* 3.59s
- *Total time:* 5.84s
- *Input validation time:* 8.71e-05
- *Prompt preparation time:* 0.00401
- *First-token latency:* 0.779
- *Cleanup time:* 0.116
- *Prompt tokens:* 379
- *Generation tokens:* 89
- *Total tokens:* 468
- *Prompt throughput (raw):* 486 tok/s
- *Generation throughput (raw):* 31.9 tok/s
- *Peak memory:* 17
- *Active memory:* 16
- *Cache memory:* 0.33
- *Model-load active memory:* 16.1
- *Post-cleanup active memory:* 0.00934
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 527
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.gemma3.processing_gemma3.Gemma3Processor
- *Tokenizer:* transformers.models.gemma.tokenization_gemma.GemmaTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* fc4e000f32af1b7b6779294e490a7d2a80bac611
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--gemma-3-27b-it-qat-4bit/snapshots/fc4e000f32af1b7b6779294e490a7d2a80bac611
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;eos&gt;

*Readable output:*

<pre class="model-output-readable">
Title: Two Tabby Cats Resting on Pink Fabric

Description: Two tabby cats lie prone on a pink fabric surface, each with a remote control nearby. Both cats are asleep, exhibiting striped fur patterns and relaxed postures.

Keywords: cats, tabby, pink, fabric, remote controls, sleeping, domestic animals, indoors, resting, lying down, striped, feline, pets, cushions, horizontal, two animals, close-up, daylight
</pre>

</details>

---

<a id="model-mlx-community-gemma-4-26b-a4b-it-4bit"></a>

### mlx-community/gemma-4-26b-a4b-it-4bit

<details>
<summary>Complete evidence: mlx-community/gemma-4-26b-a4b-it-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type gemma4)
- *Model load time:* 2.33s
- *Generation time:* 0.92s
- *Total time:* 3.28s
- *Input validation time:* 6.31e-05
- *Prompt preparation time:* 0.022
- *First-token latency:* 0.357
- *Cleanup time:* 0.116
- *Prompt tokens:* 390
- *Generation tokens:* 73
- *Total tokens:* 463
- *Prompt throughput (raw):* 1,093 tok/s
- *Generation throughput (raw):* 131 tok/s
- *Peak memory:* 16
- *Active memory:* 15
- *Cache memory:* 0.16
- *Model-load active memory:* 15.4
- *Post-cleanup active memory:* 0.00986
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 526
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.gemma4.processing_gemma4.Gemma4Processor
- *Tokenizer:* transformers.models.gemma.tokenization_gemma.GemmaTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 0d77464eeb233a2da68ebf9d7dc4edaac7db956d
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--gemma-4-26b-a4b-it-4bit/snapshots/0d77464eeb233a2da68ebf9d7dc4edaac7db956d
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;eos&gt;

*Readable output:*

<pre class="model-output-readable">
Title: Two tabby cats lying on a pink surface

Description: Two tabby cats lie on a bright pink fabric surface next to two remote controls. The cats are positioned with their heads facing in opposite directions.

Keywords: tabby, cats, pink, fabric, remote control, lying, indoor, domestic, striped, fur, two, pets, bright, daylight
</pre>

</details>

---

<a id="model-mlx-community-gemma-4-31b-it-4bit"></a>

### mlx-community/gemma-4-31b-it-4bit

<details>
<summary>Complete evidence: mlx-community/gemma-4-31b-it-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type gemma4)
- *Model load time:* 2.62s
- *Generation time:* 3.69s
- *Total time:* 6.32s
- *Input validation time:* 6.08e-05
- *Prompt preparation time:* 0.00127
- *First-token latency:* 0.832
- *Cleanup time:* 0.132
- *Prompt tokens:* 390
- *Generation tokens:* 80
- *Total tokens:* 470
- *Prompt throughput (raw):* 469 tok/s
- *Generation throughput (raw):* 28.1 tok/s
- *Peak memory:* 19
- *Active memory:* 18
- *Cache memory:* 0.59
- *Model-load active memory:* 18.4
- *Post-cleanup active memory:* 0.0104
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 526
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.gemma4.processing_gemma4.Gemma4Processor
- *Tokenizer:* transformers.models.gemma.tokenization_gemma.GemmaTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 696d436c404745a59f30e4939a658162b0a9e57f
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--gemma-4-31b-it-4bit/snapshots/696d436c404745a59f30e4939a658162b0a9e57f
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;eos&gt;

*Readable output:*

<pre class="model-output-readable">
Title: Two tabby cats lying on a pink blanket
Description: Two tabby cats lie on a pink blanket atop a red sofa next to two remote controls. The scene is captured under bright, direct lighting.
Keywords: cats, tabby, pink blanket, red sofa, remote controls, lying down, pets, indoor, fabric, stripes, animals, furniture, home, resting, soft, textile
</pre>

</details>

---

<a id="model-mlx-community-granite-40-3b-vision-4bit"></a>

### mlx-community/granite-4.0-3b-vision-4bit

<details>
<summary>Complete evidence: mlx-community/granite-4.0-3b-vision-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type granite4_vision)
- *Model load time:* 0.60s
- *Generation time:* 0.63s
- *Total time:* 1.25s
- *Input validation time:* 6.48e-05
- *Prompt preparation time:* 0.0104
- *First-token latency:* 0.251
- *Cleanup time:* 0.0853
- *Prompt tokens:* 734
- *Generation tokens:* 64
- *Total tokens:* 798
- *Prompt throughput (raw):* 2,929 tok/s
- *Generation throughput (raw):* 191 tok/s
- *Peak memory:* 4.7
- *Active memory:* 3.0
- *Cache memory:* 0.13
- *Model-load active memory:* 3.03
- *Post-cleanup active memory:* 0.0106
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 696
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.granite4_vision.processing_granite4_vision.Granite4VisionProcessor
- *Tokenizer:* transformers.models.gpt2.tokenization_gpt2.GPT2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 70fe1d89f42c71b5635cd945ed304bed438fa1e3
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--granite-4.0-3b-vision-4bit/snapshots/70fe1d89f42c71b5635cd945ed304bed438fa1e3
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|end_of_text\|>

*Readable output:*

<pre class="model-output-readable">
Title: "Cats at Rest on a Vibrant Red Sofa"
Description: Two cats are peacefully sleeping on a bright red sofa, with a remote control nearby, suggesting a domestic setting.
Keywords: cats, rest, red sofa, remote control, domestic, comfort, striped, white, relaxed, home
</pre>

</details>

---

<a id="model-mlx-community-pixtral-12b-8bit"></a>

### mlx-community/pixtral-12b-8bit

<details>
<summary>Complete evidence: mlx-community/pixtral-12b-8bit</summary>

- *Execution:* completed
- *Mechanical checks:* no concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* none
- *Arch supported by installed mlx-vlm:* yes (model_type pixtral)
- *Model load time:* 1.64s
- *Generation time:* 3.02s
- *Total time:* 4.66s
- *Input validation time:* 5.65e-05
- *Prompt preparation time:* 0.00317
- *First-token latency:* 0.801
- *Cleanup time:* 0.097
- *Prompt tokens:* 1,335
- *Generation tokens:* 89
- *Total tokens:* 1,424
- *Prompt throughput (raw):* 1,668 tok/s
- *Generation throughput (raw):* 40.4 tok/s
- *Peak memory:* 15
- *Active memory:* 13
- *Cache memory:* 0.27
- *Model-load active memory:* 13.5
- *Post-cleanup active memory:* 0.0115
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 472
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.pixtral.processing_pixtral.PixtralProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 79e24b66302d4ac5e75491767f8914b2aa6ac1f8
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--pixtral-12b-8bit/snapshots/79e24b66302d4ac5e75491767f8914b2aa6ac1f8
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* &lt;/s&gt;

*Readable output:*

<pre class="model-output-readable">
### Title:
Two Cats Lounging on Red Couch

### Description:
Two cats, one lying on its back and the other on its side, relax on a red couch. Remote controls are placed nearby.

### Keywords:
cats, lounging, red couch, remote controls, relaxed, indoor, comfort, feline, domestic, paws, stretch, lounge, resting, home, soft, purring, peaceful
</pre>

</details>

---

<a id="model-liquidai-lfm25-vl-450m-mlx-bf16"></a>

### LiquidAI/LFM2.5-VL-450M-MLX-bf16

<details>
<summary>Complete evidence: LiquidAI/LFM2.5-VL-450M-MLX-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* Duplicate keywords: cats
- *Arch supported by installed mlx-vlm:* yes (model_type lfm2-vl via lfm2_vl)
- *Model load time:* 0.43s
- *Generation time:* 0.21s
- *Total time:* 0.65s
- *Input validation time:* 0.00456
- *Prompt preparation time:* 0.00676
- *First-token latency:* 0.0537
- *Cleanup time:* 0.0625
- *Prompt tokens:* 350
- *Generation tokens:* 77
- *Total tokens:* 427
- *Prompt throughput (raw):* 6,513 tok/s
- *Generation throughput (raw):* 520 tok/s
- *Peak memory:* 1.3
- *Active memory:* 0.90
- *Cache memory:* 0.02
- *Model-load active memory:* 0.897
- *Post-cleanup active memory:* 0.000132
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 523
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* transformers.models.lfm2_vl.processing_lfm2_vl.Lfm2VlProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* ed71acdae0799c98cb450787d049d1343b65cd52
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--LiquidAI--LFM2.5-VL-450M-MLX-bf16/snapshots/ed71acdae0799c98cb450787d049d1343b65cd52
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title:
Cats on a Pink Couch

Description:
Two cats are lying on a pink couch, one is stretched out with its paws extended, while the other is curled up with its head resting on the couch.

Keywords:
cats, pink couch, cats, relaxation, comfortable, lounging, striped pattern, fur, cozy, indoor, pets
</pre>

</details>

---

<a id="model-mlx-community-glm-46v-nvfp4"></a>

### mlx-community/GLM-4.6V-nvfp4

<details>
<summary>Complete evidence: mlx-community/GLM-4.6V-nvfp4</summary>

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Unrecognised model control tokens remain visible
- *Arch supported by installed mlx-vlm:* yes (model_type glm4v_moe)
- *Model load time:* 5.62s
- *Generation time:* 3.25s
- *Total time:* 8.88s
- *Input validation time:* 4.64e-05
- *Prompt preparation time:* 0.00842
- *First-token latency:* 1.34
- *Cleanup time:* 0.199
- *Prompt tokens:* 499
- *Generation tokens:* 84
- *Total tokens:* 583
- *Prompt throughput (raw):* 372 tok/s
- *Generation throughput (raw):* 53.6 tok/s
- *Peak memory:* 63
- *Active memory:* 62
- *Cache memory:* 0.16
- *Model-load active memory:* 61.9
- *Post-cleanup active memory:* 0.00123
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 553
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.glm4v_moe.processing.Glm46VMoEProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 2da6855d4e28a0e61c84543262074bc17ac27d6e
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--GLM-4.6V-nvfp4/snapshots/2da6855d4e28a0e61c84543262074bc17ac27d6e
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|endoftext\|>

*Readable output:*

<pre class="model-output-readable">
&lt;|begin_of_box|&gt;Title: Two cats on a pink couch
Description: Two cats lie on a pink couch, each near a remote control, with one cat’s head resting on the fabric and the other stretched out with eyes closed.
Keywords: cats, pink couch, remote controls, sleeping, relaxed, striped fur, feline, domestic, indoor, pets, lounging, two animals, soft fabric, calm, cozy&lt;|end_of_box|&gt;
</pre>

<details>
<summary>Exact raw output</summary>

```text
<|begin_of_box|>Title: Two cats on a pink couch
Description: Two cats lie on a pink couch, each near a remote control, with one cat’s head resting on the fabric and the other stretched out with eyes closed.
Keywords: cats, pink couch, remote controls, sleeping, relaxed, striped fur, feline, domestic, indoor, pets, lounging, two animals, soft fabric, calm, cozy<|end_of_box|>
```

</details>

</details>

---

<a id="model-mlx-community-north-micro-vision-instruct-4bit"></a>

### mlx-community/North-Micro-Vision-Instruct-4bit

<details>
<summary>Complete evidence: mlx-community/North-Micro-Vision-Instruct-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* Duplicate keywords: couch scene
- *Arch supported by installed mlx-vlm:* yes (model_type cohere_compass)
- *Model load time:* 0.94s
- *Generation time:* 0.65s
- *Total time:* 1.61s
- *Input validation time:* 6.37e-05
- *Prompt preparation time:* 0.00428
- *First-token latency:* 0.153
- *Cleanup time:* 0.0796
- *Prompt tokens:* 418
- *Generation tokens:* 130
- *Total tokens:* 548
- *Prompt throughput (raw):* 2,739 tok/s
- *Generation throughput (raw):* 276 tok/s
- *Peak memory:* 3.3
- *Active memory:* 2.2
- *Cache memory:* 0.10
- *Model-load active memory:* 2.18
- *Post-cleanup active memory:* 0.00488
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 603
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.cohere_compass.processing_cohere_compass.CohereCompassProcessor
- *Tokenizer:* transformers.models.cohere.tokenization_cohere.CohereTokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 87466363e6c5f57adf91c18c3a62c3c74765f8df
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--North-Micro-Vision-Instruct-4bit/snapshots/87466363e6c5f57adf91c18c3a62c3c74765f8df
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|END_OF_TURN_TOKEN\|>

*Readable output:*

<pre class="model-output-readable">
Title: "Cats Resting on a Pink Couch"

Description: "Two cats are comfortably sprawled on a vibrant pink couch, basking in the soft glow of natural light. One cat is lying on its side, while the other is curled up, both appearing to be in a state of peaceful slumber. The remote controls are casually placed on the couch, adding a touch of everyday life to the scene."

Keywords: cats, couch, sleeping, resting, relaxed, sleeping cats, couch scene, peaceful, lounging, cat sleeping, remote controls, soft glow, natural light, comfortable, vibrant pink, lounging cats, couch scene, everyday life.
</pre>

</details>

---

<a id="model-mlx-community-qwen3-vl-30b-a3b-instruct-4bit"></a>

### mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit

<details>
<summary>Complete evidence: mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* Duplicate keywords: animal care, animal health, animal
  welfare
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_vl_moe)
- *Model load time:* 1.81s
- *Generation time:* 1.13s
- *Total time:* 2.96s
- *Input validation time:* 5.35e-05
- *Prompt preparation time:* 0.0111
- *First-token latency:* 0.342
- *Cleanup time:* 0.114
- *Prompt tokens:* 409
- *Generation tokens:* 101
- *Total tokens:* 510
- *Prompt throughput (raw):* 1,198 tok/s
- *Generation throughput (raw):* 130 tok/s
- *Peak memory:* 19
- *Active memory:* 18
- *Cache memory:* 0.06
- *Model-load active memory:* 18.3
- *Post-cleanup active memory:* 0.00608
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 544
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 0555d34cb1ed80c0e61a5635194c70027b4c2ff3
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3-VL-30B-A3B-Instruct-4bit/snapshots/0555d34cb1ed80c0e61a5635194c70027b4c2ff3
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title:
Two cats sleeping on pink fabric

Description:
Two cats are lying on a bright pink fabric surface. One cat is curled up on the left, while the other is stretched out on the right. A remote control is visible near each cat.

Keywords:
cat, cats, pink, fabric, remote control, remote, sleeping, lying, curled, stretched, animal, domestic animal, pet, animal care, animal health, animal welfare, animal behavior, animal care, animal health, animal welfare
</pre>

</details>

---

<a id="model-mlx-community-idefics3-8b-llama3-bf16"></a>

### mlx-community/Idefics3-8B-Llama3-bf16

<details>
<summary>Complete evidence: mlx-community/Idefics3-8B-Llama3-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* Required labelled fields not detected: title, description,
  keywords
- *Arch supported by installed mlx-vlm:* yes (model_type idefics3)
- *Model load time:* 1.87s
- *Generation time:* 1.42s
- *Total time:* 3.30s
- *Input validation time:* 6.73e-05
- *Prompt preparation time:* 0.00208
- *First-token latency:* 1.03
- *Cleanup time:* 0.0971
- *Prompt tokens:* 2,418
- *Generation tokens:* 12
- *Total tokens:* 2,430
- *Prompt throughput (raw):* 2,355 tok/s
- *Generation throughput (raw):* 35.4 tok/s
- *Peak memory:* 18
- *Active memory:* 17
- *Cache memory:* 0.39
- *Model-load active memory:* 16.9
- *Post-cleanup active memory:* 0.00149
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 509
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.idefics3.processing_idefics3.Idefics3Processor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 8c2a30c48864f3251701b7bde40f601d25535098
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Idefics3-8B-Llama3-bf16/snapshots/8c2a30c48864f3251701b7bde40f601d25535098
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|end_of_text\|>

*Readable output:*

<pre class="model-output-readable">
 Two cats sleeping on a pink blanket with remotes.
</pre>

</details>

---

<a id="model-mlx-community-muse-glimmer-30b-optiq-4bit"></a>

### mlx-community/Muse-Glimmer-30B-OptiQ-4bit

<details>
<summary>Complete evidence: mlx-community/Muse-Glimmer-30B-OptiQ-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Required labelled fields not detected: title, description;
  Response appears cut off at the token limit; Conversation-role control
  tokens remain visible; Duplicate keywords: location, event, brand, species,
  period, or intent
- *Arch supported by installed mlx-vlm:* yes (model_type muse_glimmer)
- *Model load time:* 2.87s
- *Generation time:* 39.33s
- *Total time:* 42.23s
- *Input validation time:* 5.17e-05
- *Prompt preparation time:* 0.0202
- *First-token latency:* 0.964
- *Cleanup time:* 0.125
- *Prompt tokens:* 545
- *Generation tokens:* 1,000
- *Total tokens:* 1,545
- *Prompt throughput (raw):* 565 tok/s
- *Generation throughput (raw):* 26.1 tok/s
- *Peak memory:* 25
- *Active memory:* 24
- *Cache memory:* 0.10
- *Model-load active memory:* 23.9
- *Post-cleanup active memory:* 0.00436
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* max_tokens
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 710
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.muse_glimmer.processing_muse_glimmer.MuseGlimmerProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* b4a74fa6001f1eca3b23eeeb702ffad2773a218f
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Muse-Glimmer-30B-OptiQ-4bit/snapshots/b4a74fa6001f1eca3b23eeeb702ffad2773a218f
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|end_of_text\|>

*Readable output:*

<pre class="model-output-readable">
 to=self&lt;|message|&gt;Create British-English catalogue metadata using only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.

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
</pre>

<details>
<summary>Exact raw output</summary>

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

</details>

---

<a id="model-mlx-community-qwen3-vl-2b-thinking-bf16"></a>

### mlx-community/Qwen3-VL-2B-Thinking-bf16

<details>
<summary>Complete evidence: mlx-community/Qwen3-VL-2B-Thinking-bf16</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Response repeats the same text; Generation was stopped early
  after sustained repeated output; Required labelled fields not detected:
  title, description; Internal reasoning block appears incomplete; Duplicate
  keywords: resting, couch, cat, tabby, pink, remote
- *Arch supported by installed mlx-vlm:* yes (model_type qwen3_vl)
- *Model load time:* 0.82s
- *Generation time:* 3.09s
- *Total time:* 3.93s
- *Input validation time:* 6.69e-05
- *Prompt preparation time:* 0.0121
- *First-token latency:* 0.0994
- *Cleanup time:* 0.0842
- *Prompt tokens:* 411
- *Generation tokens:* 400
- *Total tokens:* 811
- *Prompt throughput (raw):* 4,137 tok/s
- *Generation throughput (raw):* 135 tok/s
- *Peak memory:* 5.3
- *Active memory:* 4.3
- *Cache memory:* 0.23
- *Model-load active memory:* 4.26
- *Post-cleanup active memory:* 0.00577
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* repetition_abort
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 552
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen3_vl.processing_qwen3_vl.Qwen3VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* c325e5ea14c215bb08fa0d668c81fa2581f9050b
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Qwen3-VL-2B-Thinking-bf16/snapshots/c325e5ea14c215bb08fa0d668c81fa2581f9050b
- *Generation settings:* {"enable_thinking": true, "max_tokens": 1000,
  "prefill_step_size": 2048, "temperature": 0.0, "thinking_budget": 800,
  "thinking_end_token": "&lt;/think&gt;", "thinking_start_token":
  "&lt;think&gt;", "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Got it, let's tackle this. First, the title needs to be concrete and 5-10 words. The image has two cats on a pink couch with remotes. So maybe "Two tabby cats resting on pink couch with remotes" but that's 10 words. Wait, "Two tabby cats resting on pink couch with remote controls" but need to check. Wait, the problem says "British-English catalogue metadata", so maybe "Two tabby cats resting on pink couch with remote controls" but let's count: Two tabby cats resting on pink couch with remote controls is 10 words. That's good.

Next, the description. Need 1-2 sentences. Main subject: two cats. Setting: pink couch. Action: resting. Lighting: bright (since it's a photo, probably natural light). Distinctive details: tabby patterns, remotes. So "Two tabby cats rest on a bright pink couch, one with a green collar, while two remote controls lie nearby."

Wait, check the facts. The remotes are visible, one is gray with buttons, the other is white with blue. But the problem says omit uncertain details. So "Two tabby cats rest on a bright pink couch, one with a green collar, while two remote controls lie nearby." That's 1-2 sentences.

Keywords: need 10-18 unique, comma-separated. Let's list: tabby cats, pink couch, resting, remote controls, two cats, bright, natural light, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting, tabby, pink, remote, cat, couch, cat, resting,
</pre>

</details>

---

<a id="model-mlx-community-step-37-flash-oq3e"></a>

### mlx-community/Step-3.7-Flash-oQ3e

<details>
<summary>Complete evidence: mlx-community/Step-3.7-Flash-oQ3e</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Final answer emitted twice, around &lt;/think&gt;;
  Unrecognised model control tokens remain visible
- *Arch supported by installed mlx-vlm:* yes (model_type step3p7)
- *Model load time:* 9.06s
- *Generation time:* 9.33s
- *Total time:* 18.42s
- *Input validation time:* 5.75e-05
- *Prompt preparation time:* 0.0173
- *First-token latency:* 4.9
- *Cleanup time:* 0.261
- *Prompt tokens:* 286
- *Generation tokens:* 236
- *Total tokens:* 522
- *Prompt throughput (raw):* 58.3 tok/s
- *Generation throughput (raw):* 54.3 tok/s
- *Peak memory:* 87
- *Active memory:* 85
- *Cache memory:* 0.12
- *Model-load active memory:* 85
- *Post-cleanup active memory:* 0.00849
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 550
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.step3p7.processing_step3p7.Step3VLProcessor
- *Tokenizer:* transformers.tokenization_utils_tokenizers.TokenizersBackend
- *Requested model revision:* not requested
- *Resolved model revision:* 41d17ee00e168a2918bb839e4a7b6e445c6f03f1
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--Step-3.7-Flash-oQ3e/snapshots/41d17ee00e168a2918bb839e4a7b6e445c6f03f1
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title:
Two cats sleeping on a pink blanket
Description:
Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one cat on the left having a green collar and the other cat on the right being larger. Two remote controls are placed near the cats on the blanket.
Keywords:
cats, sleeping, pink blanket, red sofa, tabby cats, remote controls, green collar, large cat, small cat, relaxed, pets, home interior, soft fabric, lying down, close-up, daytime, comfortable, cozy
&lt;/think&gt;
Title:
Two cats sleeping on a pink blanket
Description:
Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one cat on the left having a green collar and the other cat on the right being larger. Two remote controls are placed near the cats on the blanket.
Keywords:
cats, sleeping, pink blanket, red sofa, tabby cats, remote controls, green collar, large cat, small cat, relaxed, pets, home interior, soft fabric, lying down, close-up, daytime, comfortable, cozy
</pre>

<details>
<summary>Exact raw output</summary>

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

</details>

---

<a id="model-mlx-community-x-reasoner-7b-8bit"></a>

### mlx-community/X-Reasoner-7B-8bit

<details>
<summary>Complete evidence: mlx-community/X-Reasoner-7B-8bit</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Response repeats the same text; Generation was stopped early
  after sustained repeated output; Duplicate keywords: feline pink couch with
  remote control, feline rest on pink couch with remote control, feline pink
  couch with remote control and cat, feline rest on pink couch with remote
  control and cat
- *Arch supported by installed mlx-vlm:* yes (model_type qwen2_5_vl)
- *Model load time:* 1.17s
- *Generation time:* 6.05s
- *Total time:* 7.23s
- *Input validation time:* 7.95e-05
- *Prompt preparation time:* 0.0047
- *First-token latency:* 0.262
- *Cleanup time:* 0.106
- *Prompt tokens:* 511
- *Generation tokens:* 375
- *Total tokens:* 886
- *Prompt throughput (raw):* 1,953 tok/s
- *Generation throughput (raw):* 65.6 tok/s
- *Peak memory:* 10
- *Active memory:* 9.5
- *Cache memory:* 0.12
- *Model-load active memory:* 9.46
- *Post-cleanup active memory:* 0.0088
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* repetition_abort
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 602
- *Image placeholders:* 0
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* mlx_vlm.models.qwen2_5_vl.processing_qwen2_5_vl.Qwen2_5_VLProcessor
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 21732e74613b465bc98e9d5ec210aba5c7adbcc1
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--X-Reasoner-7B-8bit/snapshots/21732e74613b465bc98e9d5ec210aba5c7adbcc1
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: Cats Sleeping on Pink Couch with Remotes

Description: Two tabby cats rest on a pink couch, one curled up with a remote, the other stretched out. The setting is indoors, with soft lighting highlighting their striped fur and relaxed postures. A second remote lies between them.

Keywords: cats, sleeping, pink couch, tabby, striped, remote control, indoor, relaxation, feline, comfort, domestic, home, rest, feline behavior, cozy, feline friends, feline companions, feline relaxation, feline comfort, feline rest, feline home life, feline behavior study, feline sleep patterns, feline remote control, feline pink couch, feline comfort zone, feline home environment, feline rest period, feline remote control use, feline pink couch setup, feline home setup, feline remote control placement, feline pink couch arrangement, feline rest on remote, feline pink couch with remote, feline comfort with remote, feline pink couch with remote control, feline rest on pink couch, feline remote control on pink couch, feline pink couch with remote control, feline rest on pink couch with remote, feline pink couch setup with remote, feline rest on pink couch with remote control, feline pink couch with remote control, feline rest on pink couch with remote control, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with remote control and cat, feline rest on pink couch with remote control and cat, feline pink couch with
</pre>

</details>

---

<a id="model-mlx-community-nanollava-15-4bit"></a>

### mlx-community/nanoLLaVA-1.5-4bit

<details>
<summary>Complete evidence: mlx-community/nanoLLaVA-1.5-4bit</summary>

- *Execution:* completed
- *Mechanical checks:* major concerns
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* none
- *Observations:* Required labelled fields not detected: keywords
- *Arch supported by installed mlx-vlm:* yes (model_type llava-qwen2 via
  llava_bunny)
- *Model load time:* 0.44s
- *Generation time:* 0.35s
- *Total time:* 0.79s
- *Input validation time:* 5.45e-05
- *Prompt preparation time:* 0.00243
- *First-token latency:* 0.0828
- *Cleanup time:* 0.0867
- *Prompt tokens:* 116
- *Generation tokens:* 97
- *Total tokens:* 213
- *Prompt throughput (raw):* 1,400 tok/s
- *Generation throughput (raw):* 397 tok/s
- *Peak memory:* 1.5
- *Active memory:* 0.61
- *Cache memory:* 0.24
- *Model-load active memory:* 0.609
- *Post-cleanup active memory:* 0.0112
- *Post-cleanup cache memory:* 0.0
- *Stop reason:* completed
- *Requested maximum tokens:* 1000
- *Rendered prompt characters:* 558
- *Image placeholders:* 1
- *Processed image:* not captured
- *Image patch count:* not captured
- *Processor:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Tokenizer:* transformers.models.qwen2.tokenization_qwen2.Qwen2Tokenizer
- *Requested model revision:* not requested
- *Resolved model revision:* 5240204744963d72823e5de933c528c4aa82dfca
- *Resolved snapshot path:* ~/.cache/huggingface/hub/models--mlx-community--nanoLLaVA-1.5-4bit/snapshots/5240204744963d72823e5de933c528c4aa82dfca
- *Generation settings:* {"max_tokens": 1000, "prefill_step_size": 2048,
  "temperature": 0.0, "top_p": 1.0}
- *EOS token:* <\|im_end\|>

*Readable output:*

<pre class="model-output-readable">
Title: "A Study in Stripes"
Description: A close-up of a person wearing a striped shirt, with a focus on the pattern and color of the fabric. The image is set against a pink background, and the person is lying on a bed covered with a pink blanket. The lighting is soft, and the person is facing away from the camera, giving a sense of intimacy. The image is a straightforward representation of the subject, with no additional details or context provided.
</pre>

</details>

---
