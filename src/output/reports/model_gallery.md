# Model Output Gallery

Generated on: 2026-09-06 19:51:43 BST

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
| [`mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`](#model-mlx-community-devstral-small-2-24b-instruct-2512-5bit) | `no concerns detected` | 6.25s   | 31.3 tok/s          | 0.98            | 20      | 537        | 98      | none                                                                                                                 |
| [`mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`](#model-mlx-community-ernie-45-vl-28b-a3b-thinking-4bit)            | `no concerns detected` | 4.98s   | 139 tok/s           | 0.37            | 18      | 545        | 411     | none                                                                                                                 |
| [`mlx-community/GLM-4.6V-Flash-4bit`](#model-mlx-community-glm-46v-flash-4bit)                                          | `no concerns detected` | 2.11s   | 89.3 tok/s          | 0.34            | 8.0     | 499        | 48      | none                                                                                                                 |
| [`mlx-community/InternVL3-8B-bf16`](#model-mlx-community-internvl3-8b-bf16)                                             | `no concerns detected` | 4.57s   | 35.1 tok/s          | 1.19            | 17      | 3,435      | 60      | none                                                                                                                 |
| [`mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`](#model-mlx-community-kimi-vl-a3b-thinking-2506-8bit)                   | `no concerns detected` | 7.53s   | 73.9 tok/s          | 0.58            | 20      | 489        | 346     | none                                                                                                                 |
| [`mlx-community/LFM2.5-VL-1.6B-bf16`](#model-mlx-community-lfm25-vl-16b-bf16)                                           | `no concerns detected` | 1.34s   | 191 tok/s           | 0.18            | 4.0     | 350        | 100     | none                                                                                                                 |
| [`mlx-community/LFM2.5-VL-3B-OptiQ-4bit`](#model-mlx-community-lfm25-vl-3b-optiq-4bit)                                  | `no concerns detected` | 1.32s   | 218 tok/s           | 0.10            | 3.6     | 344        | 61      | none                                                                                                                 |
| [`mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-mxfp4)         | `no concerns detected` | 3.17s   | 70.0 tok/s          | 0.63            | 9.8     | 1,070      | 81      | none                                                                                                                 |
| [`mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-nvfp4)         | `no concerns detected` | 3.61s   | 67.0 tok/s          | 0.67            | 10      | 1,070      | 106     | none                                                                                                                 |
| [`mlx-community/Ministral-3-3B-Instruct-2512-4bit`](#model-mlx-community-ministral-3-3b-instruct-2512-4bit)             | `no concerns detected` | 1.71s   | 205 tok/s           | 0.23            | 4.5     | 1,069      | 97      | none                                                                                                                 |
| [`mlx-community/Molmo2-8B-4bit`](#model-mlx-community-molmo2-8b-4bit)                                                   | `no concerns detected` | 2.86s   | 73.6 tok/s          | 0.49            | 8.0     | 873        | 95      | none                                                                                                                 |
| [`mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`](#model-mlx-community-ornith-15-35b-a3b-optiq-4bit)                      | `no concerns detected` | 4.02s   | 108 tok/s           | 0.39            | 24      | 421        | 114     | none                                                                                                                 |
| [`mlx-community/Phi-3.5-vision-instruct-bf16`](#model-mlx-community-phi-35-vision-instruct-bf16)                        | `no concerns detected` | 2.84s   | 58.3 tok/s          | 0.23            | 9.3     | 883        | 96      | none                                                                                                                 |
| [`mlx-community/Qwen3.5-35B-A3B-4bit`](#model-mlx-community-qwen35-35b-a3b-4bit)                                        | `no concerns detected` | 3.62s   | 123 tok/s           | 0.37            | 21      | 421        | 89      | none                                                                                                                 |
| [`mlx-community/Qwen3.5-9B-MLX-4bit`](#model-mlx-community-qwen35-9b-mlx-4bit)                                          | `no concerns detected` | 2.32s   | 101 tok/s           | 0.28            | 7.0     | 421        | 71      | none                                                                                                                 |
| [`mlx-community/Qwen3.8-27B-4bit`](#model-mlx-community-qwen38-27b-4bit)                                                | `no concerns detected` | 5.59s   | 33.0 tok/s          | 0.70            | 17      | 421        | 86      | none                                                                                                                 |
| [`mlx-community/Qwen3.8-Flash-Next-4bit`](#model-mlx-community-qwen38-flash-next-4bit)                                  | `no concerns detected` | 111.83s | 31.9 tok/s          | 83.57           | 113     | 421        | 80      | none                                                                                                                 |
| [`mlx-community/SmolVLM2-2.2B-Instruct-mlx`](#model-mlx-community-smolvlm2-22b-instruct-mlx)                            | `no concerns detected` | 1.48s   | 129 tok/s           | 0.35            | 5.4     | 1,204      | 31      | none                                                                                                                 |
| [`mlx-community/diffusiongemma-26B-A4B-it-mxfp8`](#model-mlx-community-diffusiongemma-26b-a4b-it-mxfp8)                 | `no concerns detected` | 5.16s   | 56.5 tok/s          | 0.30            | 28      | 386        | 74      | none                                                                                                                 |
| [`mlx-community/gemma-3-27b-it-qat-4bit`](#model-mlx-community-gemma-3-27b-it-qat-4bit)                                 | `no concerns detected` | 5.98s   | 31.9 tok/s          | 0.78            | 17      | 379        | 89      | none                                                                                                                 |
| [`mlx-community/gemma-4-26b-a4b-it-4bit`](#model-mlx-community-gemma-4-26b-a4b-it-4bit)                                 | `no concerns detected` | 3.38s   | 132 tok/s           | 0.36            | 16      | 390        | 73      | none                                                                                                                 |
| [`mlx-community/gemma-4-31b-it-4bit`](#model-mlx-community-gemma-4-31b-it-4bit)                                         | `no concerns detected` | 6.28s   | 28.1 tok/s          | 0.84            | 19      | 390        | 80      | none                                                                                                                 |
| [`mlx-community/granite-4.0-3b-vision-4bit`](#model-mlx-community-granite-40-3b-vision-4bit)                            | `no concerns detected` | 1.29s   | 191 tok/s           | 0.25            | 4.7     | 734        | 64      | none                                                                                                                 |
| [`mlx-community/pixtral-12b-8bit`](#model-mlx-community-pixtral-12b-8bit)                                               | `no concerns detected` | 4.76s   | 40.5 tok/s          | 0.80            | 15      | 1,335      | 89      | none                                                                                                                 |
| [`LiquidAI/LFM2.5-VL-450M-MLX-bf16`](#model-liquidai-lfm25-vl-450m-mlx-bf16)                                            | `concerns detected`    | 0.79s   | 530 tok/s           | 0.06            | 1.2     | 350        | 77      | duplicate keywords                                                                                                   |
| [`mlx-community/GLM-4.6V-nvfp4`](#model-mlx-community-glm-46v-nvfp4)                                                    | `concerns detected`    | 9.33s   | 53.1 tok/s          | 1.41            | 63      | 499        | 84      | control tokens visible                                                                                               |
| [`mlx-community/North-Micro-Vision-Instruct-4bit`](#model-mlx-community-north-micro-vision-instruct-4bit)               | `concerns detected`    | 1.68s   | 269 tok/s           | 0.15            | 3.3     | 418        | 130     | duplicate keywords                                                                                                   |
| [`mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit`](#model-mlx-community-qwen3-vl-30b-a3b-instruct-4bit)                   | `concerns detected`    | 3.00s   | 131 tok/s           | 0.35            | 19      | 409        | 101     | duplicate keywords                                                                                                   |
| [`mlx-community/Step-3.7-Flash-oQ3e`](#model-mlx-community-step-37-flash-oq3e)                                          | `concerns detected`    | 18.38s  | 54.1 tok/s          | 4.93            | 87      | 286        | 236     | control tokens visible                                                                                               |
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)                                 | `major concerns`       | 3.32s   | insufficient sample | 1.04            | 18      | 2,418      | 12      | labelled fields not detected                                                                                         |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit)                         | `major concerns`       | 42.34s  | 26.0 tok/s          | 0.99            | 25      | 545        | 1,000   | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords                        |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)                             | `major concerns`       | 3.83s   | 134 tok/s           | 0.10            | 5.3     | 411        | 400     | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                                           | `major concerns`       | 8.16s   | 65.7 tok/s          | 0.49            | 10      | 511        | 375     | repeated text; stopped early: repeating; duplicate keywords                                                          |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                                            | `major concerns`       | 0.90s   | 396 tok/s           | 0.08            | 1.5     | 116        | 97      | labelled fields not detected                                                                                         |
<!-- markdownlint-enable MD034 MD037 MD049 -->

## Resource Highlights

Quickest completion without detected concerns (end-to-end, including model load): `mlx-community/granite-4.0-3b-vision-4bit` at 1.29s

Lowest peak memory among completions without detected concerns: `mlx-community/LFM2.5-VL-3B-OptiQ-4bit` at 3.6 GB

Decode tok/s stays per model in the chooser and is not averaged across models: tokenizers, image-token expansion and reasoning lengths differ too much for a cross-model mean to guide a choice.

## Avoid for This Run

<!-- markdownlint-disable MD034 MD037 MD049 -->

| Model                                                                                           | Mechanical checks | Observations                                                                                                         |
|-------------------------------------------------------------------------------------------------|-------------------|----------------------------------------------------------------------------------------------------------------------|
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)         | `major concerns`  | labelled fields not detected                                                                                         |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit) | `major concerns`  | labelled fields not detected; cut off at token limit; role tokens visible; duplicate keywords                        |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)     | `major concerns`  | repeated text; stopped early: repeating; labelled fields not detected; incomplete thinking block; duplicate keywords |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                   | `major concerns`  | repeated text; stopped early: repeating; duplicate keywords                                                          |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                    | `major concerns`  | labelled fields not detected                                                                                         |
<!-- markdownlint-enable MD034 MD037 MD049 -->

## Output at a Glance

The first 280 characters of each model's final answer (or failure evidence for crashes), in chooser order. A closed reasoning trace is left out of the preview and reported as an omitted-character count; the complete output, trace included, is in the model's evidence block below.

<!-- markdownlint-disable MD034 MD037 MD049 -->

| Model                                                                                                                   | Mechanical checks      | Output preview                                                                                                                                                                                                                                                                                                                                                               |
|-------------------------------------------------------------------------------------------------------------------------|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`mlx-community/Devstral-Small-2-24B-Instruct-2512-5bit`](#model-mlx-community-devstral-small-2-24b-instruct-2512-5bit) | `no concerns detected` | Title:<br>Two cats resting on a pink sofa<br><br>Description:<br>Two tabby cats are lying on a pink sofa, one on its back and the other on its side, with a remote control nearby. The lighting is natural, and the cats have distinctive striped fur patterns.<br><br>Keywords: cats, tabby, sofa, pin...                                                                   |
| [`mlx-community/ERNIE-4.5-VL-28B-A3B-Thinking-4bit`](#model-mlx-community-ernie-45-vl-28b-a3b-thinking-4bit)            | `no concerns detected` | Title: Two cats sleeping on a red couch<br><br>Description: Two cats, one calico and one tiger-striped, are sleeping on a red couch. A remote control lies nearby.<br><br>Keywords: cat, cats, sleeping, couch, red, remote control, calico, tiger-striped, pet, animal[1,266 characters of reasoning omitted; complete output in the evidence block]                        |
| [`mlx-community/GLM-4.6V-Flash-4bit`](#model-mlx-community-glm-46v-flash-4bit)                                          | `no concerns detected` | Title: Two tabby cats on pink fabric.<br>Description: Two tabby cats rest on a pink fabric surface, with remote controls nearby.<br>Keywords: tabby cats, pink fabric, remote controls, resting, domestic cats.                                                                                                                                                              |
| [`mlx-community/InternVL3-8B-bf16`](#model-mlx-community-internvl3-8b-bf16)                                             | `no concerns detected` | Title: Two Cats Sleeping on Pink Blanket<br>Description: Two tabby cats are lying on a pink blanket with remote controls nearby, in a relaxed sleeping position.<br>Keywords: cats, sleeping, pink blanket, remote controls, tabby, relaxed, blanket, resting, pets, cozy, indoor                                                                                            |
| [`mlx-community/Kimi-VL-A3B-Thinking-2506-8bit`](#model-mlx-community-kimi-vl-a3b-thinking-2506-8bit)                   | `no concerns detected` | Title: Two tabby cats resting on pink fabric with remote controls<br>Description: Two tabby cats lie on a pink fabric surface, each near a remote control, under bright lighting.<br>Keywords: tabby cats, pink fabric, remote controls, resting, relaxed posture, domestic setting, domest...[1,182 characters of reasoning omitted; complete output in the evidence block] |
| [`mlx-community/LFM2.5-VL-1.6B-bf16`](#model-mlx-community-lfm25-vl-16b-bf16)                                           | `no concerns detected` | Title: Two Cats Resting on a Pink Blanket<br><br>Description: Two cats are lying on a pink blanket, one is stretched out while the other is curled up. The cats appear to be sleeping peacefully, with one having a green collar. The lighting is soft and warm, highlighting the relaxed p...                                                                               |
| [`mlx-community/LFM2.5-VL-3B-OptiQ-4bit`](#model-mlx-community-lfm25-vl-3b-optiq-4bit)                                  | `no concerns detected` | Title: Two cats sleeping on pink couch with remotes<br>Description: Two tabby cats are lying on a pink couch, one with a green collar, next to two remote controls.<br>Keywords: cats, sleeping, couch, pink, remotes, tabby, pets, furniture, relaxation, indoor                                                                                                            |
| [`mlx-community/Ministral-3-14B-Instruct-2512-mxfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-mxfp4)         | `no concerns detected` | Title:<br>Two Cats Relaxing on Pink Cushioned Surface<br><br>Description:<br>Two cats lie stretched out on a pink cushioned surface, positioned near remote controls. The lighting is natural, and the cats appear calm and at ease.<br><br>Keywords:<br>cats, pink cushioned surface, remote controls, re...                                                                |
| [`mlx-community/Ministral-3-14B-Instruct-2512-nvfp4`](#model-mlx-community-ministral-3-14b-instruct-2512-nvfp4)         | `no concerns detected` | **Title:**<br>Relaxed Tabby Kittens on Pink Cushion<br><br>**Description:**<br>Two tabby kittens lie stretched out on a pink cushion, positioned near remote controls. Their relaxed postures and soft fur highlight a calm, indoor setting with natural lighting.<br><br>**Keywords:**<br>kittens, tabby,...                                                                |
| [`mlx-community/Ministral-3-3B-Instruct-2512-4bit`](#model-mlx-community-ministral-3-3b-instruct-2512-4bit)             | `no concerns detected` | Title:<br>Two Kitten Friends on a Pink Couch<br><br>Description:<br>Two striped kittens lie relaxed on a bright pink cushion, each with a remote control beside them. The larger kitten is curled, while the smaller one stretches out, bathed in soft indoor lighting.<br><br>Keywords:<br>kitten, domest...                                                                |
| [`mlx-community/Molmo2-8B-4bit`](#model-mlx-community-molmo2-8b-4bit)                                                   | `no concerns detected` | Title: Two Calico Cats Sleeping on Pink Bedding<br><br>Description: Two calico cats are sleeping side by side on pink bedding. They are positioned with their heads facing each other and their tails touching. The cats have white, black, and brown fur. Two white remote controls are vi...                                                                               |
| [`mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit`](#model-mlx-community-ornith-15-35b-a3b-optiq-4bit)                      | `no concerns detected` | Title: Two Tabby Cats Sleeping on Pink Sofa With Remotes<br><br>Description: Two striped tabby cats lie asleep on a bright pink sofa, one curled on its side and the other stretched out, with two white television remote controls resting nearby. The scene is evenly lit, showing their...                                                                                |
| [`mlx-community/Phi-3.5-vision-instruct-bf16`](#model-mlx-community-phi-35-vision-instruct-bf16)                        | `no concerns detected` | Title: Two Cats Sleeping on Sofa<br><br>Description: Two cats are sleeping on a pink sofa with remote controls beside them.<br><br>Keywords: cats, sleeping, sofa, remote controls, pink, relaxed, comfortable, domestic, indoor, pet, animal, resting, tranquil, domesticated, feline, fur, rela...                                                                         |
| [`mlx-community/Qwen3.5-35B-A3B-4bit`](#model-mlx-community-qwen35-35b-a3b-4bit)                                        | `no concerns detected` | Title: Two Tabby Cats Sleeping on Pink Sofa<br><br>Description: Two tabby cats lie asleep on a bright pink sofa, each positioned near a white remote control. The scene is lit by even indoor lighting, highlighting the cats’ striped fur and relaxed postures.<br><br>Keywords: tabby cats, pin...                                                                         |
| [`mlx-community/Qwen3.5-9B-MLX-4bit`](#model-mlx-community-qwen35-9b-mlx-4bit)                                          | `no concerns detected` | Title: Two Cats Sleeping on Pink Couch with Remotes<br><br>Description: Two tabby cats are lying on a pink couch, each near a remote control, in a relaxed and comfortable setting.<br><br>Keywords: cats, tabby, pink couch, remote control, sleeping, relaxed, comfortable, striped fur, cozy,...                                                                          |
| [`mlx-community/Qwen3.8-27B-4bit`](#model-mlx-community-qwen38-27b-4bit)                                                | `no concerns detected` | Title: Two Cats Sleeping on Pink Couch with Remotes<br><br>Description: Two tabby cats are lying on their sides on a bright pink couch, with two white remote controls placed nearby. The scene is evenly lit, highlighting the cats' striped fur and relaxed postures.<br><br>Keywords: cats, ta...                                                                         |
| [`mlx-community/Qwen3.8-Flash-Next-4bit`](#model-mlx-community-qwen38-flash-next-4bit)                                  | `no concerns detected` | Title: Two Tabby Cats Resting on Pink Fabric<br><br>Description: Two tabby cats are lying on a pink blanket, with two white remote controls placed nearby on the fabric.<br><br>Keywords: cat, feline, pet, animal, tabby, sleeping, resting, pink, blanket, remote control, electronics, mammal,...                                                                         |
| [`mlx-community/SmolVLM2-2.2B-Instruct-mlx`](#model-mlx-community-smolvlm2-22b-instruct-mlx)                            | `no concerns detected` | Title: Two Cats on a Couch<br>Description: Two cats are sleeping on a pink couch.<br>Keywords: cats, couch, sleeping, pink                                                                                                                                                                                                                                                   |
| [`mlx-community/diffusiongemma-26B-A4B-it-mxfp8`](#model-mlx-community-diffusiongemma-26b-a4b-it-mxfp8)                 | `no concerns detected` | Title: Two tabby cats sleeping on a pink blanket<br>Description: Two tabby patterned cats are lying on a pink fabric surface on a sofa. Two television remote controls are visible near them.<br>Keywords: cats, tabby, sleeping, resting, pink, blanket, sofa, remote, indoor, domestic, f...                                                                               |
| [`mlx-community/gemma-3-27b-it-qat-4bit`](#model-mlx-community-gemma-3-27b-it-qat-4bit)                                 | `no concerns detected` | Title: Two Tabby Cats Resting on Pink Fabric<br><br>Description: Two tabby cats lie prone on a pink fabric surface, each with a remote control nearby. Both cats are asleep, exhibiting striped fur patterns and relaxed postures.<br><br>Keywords: cats, tabby, pink, fabric, remote controls, s...                                                                         |
| [`mlx-community/gemma-4-26b-a4b-it-4bit`](#model-mlx-community-gemma-4-26b-a4b-it-4bit)                                 | `no concerns detected` | Title: Two tabby cats lying on a pink surface<br><br>Description: Two tabby cats lie on a bright pink fabric surface next to two remote controls. The cats are positioned with their heads facing in opposite directions.<br><br>Keywords: tabby, cats, pink, fabric, remote control, lying, indo...                                                                         |
| [`mlx-community/gemma-4-31b-it-4bit`](#model-mlx-community-gemma-4-31b-it-4bit)                                         | `no concerns detected` | Title: Two tabby cats lying on a pink blanket<br>Description: Two tabby cats lie on a pink blanket atop a red sofa next to two remote controls. The scene is captured under bright, direct lighting.<br>Keywords: cats, tabby, pink blanket, red sofa, remote controls, lying down, pets, i...                                                                               |
| [`mlx-community/granite-4.0-3b-vision-4bit`](#model-mlx-community-granite-40-3b-vision-4bit)                            | `no concerns detected` | Title: "Cats at Rest on a Vibrant Red Sofa"<br>Description: Two cats are peacefully sleeping on a bright red sofa, with a remote control nearby, suggesting a domestic setting.<br>Keywords: cats, rest, red sofa, remote control, domestic, comfort, striped, white, relaxed, home                                                                                          |
| [`mlx-community/pixtral-12b-8bit`](#model-mlx-community-pixtral-12b-8bit)                                               | `no concerns detected` | ### Title:<br>Two Cats Lounging on Red Couch<br><br>### Description:<br>Two cats, one lying on its back and the other on its side, relax on a red couch. Remote controls are placed nearby.<br><br>### Keywords:<br>cats, lounging, red couch, remote controls, relaxed, indoor, comfort, feline, domestic...                                                                |
| [`LiquidAI/LFM2.5-VL-450M-MLX-bf16`](#model-liquidai-lfm25-vl-450m-mlx-bf16)                                            | `concerns detected`    | Title:<br>Cats on a Pink Couch<br><br>Description:<br>Two cats are lying on a pink couch, one is stretched out with its paws extended, while the other is curled up with its head resting on the couch.<br><br>Keywords:<br>cats, pink couch, cats, relaxation, comfortable, lounging, striped pattern, fu...                                                                |
| [`mlx-community/GLM-4.6V-nvfp4`](#model-mlx-community-glm-46v-nvfp4)                                                    | `concerns detected`    | <\|begin_of_box\|>Title: Two cats on a pink couch<br>Description: Two cats lie on a pink couch, each near a remote control, with one cat’s head resting on the fabric and the other stretched out with eyes closed.<br>Keywords: cats, pink couch, remote controls, sleeping, relaxed, stripe...                                                                             |
| [`mlx-community/North-Micro-Vision-Instruct-4bit`](#model-mlx-community-north-micro-vision-instruct-4bit)               | `concerns detected`    | Title: "Cats Resting on a Pink Couch"<br><br>Description: "Two cats are comfortably sprawled on a vibrant pink couch, basking in the soft glow of natural light. One cat is lying on its side, while the other is curled up, both appearing to be in a state of peaceful slumber. The remot...                                                                               |
| [`mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit`](#model-mlx-community-qwen3-vl-30b-a3b-instruct-4bit)                   | `concerns detected`    | Title:<br>Two cats sleeping on pink fabric<br><br>Description:<br>Two cats are lying on a bright pink fabric surface. One cat is curled up on the left, while the other is stretched out on the right. A remote control is visible near each cat.<br><br>Keywords:<br>cat, cats, pink, fabric, remote cont...                                                                |
| [`mlx-community/Step-3.7-Flash-oQ3e`](#model-mlx-community-step-37-flash-oq3e)                                          | `concerns detected`    | Title:<br>Two cats sleeping on a pink blanket<br>Description:<br>Two tabby cats are lying on a bright pink blanket on a red sofa. Both cats appear to be asleep, with one cat on the left having a green collar and the other cat on the right being larger. Two remote controls are placed ne...                                                                            |
| [`mlx-community/Idefics3-8B-Llama3-bf16`](#model-mlx-community-idefics3-8b-llama3-bf16)                                 | `major concerns`       | Two cats sleeping on a pink blanket with remotes.                                                                                                                                                                                                                                                                                                                            |
| [`mlx-community/Muse-Glimmer-30B-OptiQ-4bit`](#model-mlx-community-muse-glimmer-30b-optiq-4bit)                         | `major concerns`       | to=self<\|message\|>Create British-English catalogue metadata using only clearly visible facts. Omit uncertain details and unsupported identity, location, event, brand, species, period, or intent.<br><br>Write:<br>- a concrete 5-10-word title;<br>- a 1-2-sentence factual description of the...                                                                        |
| [`mlx-community/Qwen3-VL-2B-Thinking-bf16`](#model-mlx-community-qwen3-vl-2b-thinking-bf16)                             | `major concerns`       | Got it, let's tackle this. First, the title needs to be concrete and 5-10 words. The image has two cats on a pink couch with remotes. So maybe "Two tabby cats resting on pink couch with remotes" but that's 10 words. Wait, "Two tabby cats resting on pink couch with remote contr...                                                                                     |
| [`mlx-community/X-Reasoner-7B-8bit`](#model-mlx-community-x-reasoner-7b-8bit)                                           | `major concerns`       | Title: Cats Sleeping on Pink Couch with Remotes<br><br>Description: Two tabby cats rest on a pink couch, one curled up with a remote, the other stretched out. The setting is indoors, with soft lighting highlighting their striped fur and relaxed postures. A second remote lies between...                                                                               |
| [`mlx-community/nanoLLaVA-1.5-4bit`](#model-mlx-community-nanollava-15-4bit)                                            | `major concerns`       | Title: "A Study in Stripes"<br>Description: A close-up of a person wearing a striped shirt, with a focus on the pattern and color of the fabric. The image is set against a pink background, and the person is lying on a bed covered with a pink blanket. The lighting is soft, and the...                                                                                  |
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
- *Model load time:* 2.04s
- *Generation time:* 4.19s
- *Total time:* 6.25s
- *Input validation time:* 5.5e-05
- *Prompt preparation time:* 0.00697
- *First-token latency:* 0.975
- *Cleanup time:* 0.098
- *Prompt tokens:* 537
- *Generation tokens:* 98
- *Total tokens:* 635
- *Prompt throughput (raw):* 550 tok/s
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
- *Model load time:* 1.64s
- *Generation time:* 3.33s
- *Total time:* 4.98s
- *Input validation time:* 7.12e-05
- *Prompt preparation time:* 0.00817
- *First-token latency:* 0.366
- *Cleanup time:* 0.103
- *Prompt tokens:* 545
- *Generation tokens:* 411
- *Total tokens:* 956
- *Prompt throughput (raw):* 1,490 tok/s
- *Generation throughput (raw):* 139 tok/s
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
- *Model load time:* 1.20s
- *Generation time:* 0.90s
- *Total time:* 2.11s
- *Input validation time:* 5.58e-05
- *Prompt preparation time:* 0.00743
- *First-token latency:* 0.335
- *Cleanup time:* 0.0767
- *Prompt tokens:* 499
- *Generation tokens:* 48
- *Total tokens:* 547
- *Prompt throughput (raw):* 1,488 tok/s
- *Generation throughput (raw):* 89.3 tok/s
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
- *Model load time:* 1.63s
- *Generation time:* 2.93s
- *Total time:* 4.57s
- *Input validation time:* 6.02e-05
- *Prompt preparation time:* 0.0027
- *First-token latency:* 1.19
- *Cleanup time:* 0.0932
- *Prompt tokens:* 3,435
- *Generation tokens:* 60
- *Total tokens:* 3,495
- *Prompt throughput (raw):* 2,883 tok/s
- *Generation throughput (raw):* 35.1 tok/s
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
- *Model load time:* 2.13s
- *Generation time:* 5.39s
- *Total time:* 7.53s
- *Input validation time:* 6.01e-05
- *Prompt preparation time:* 0.00359
- *First-token latency:* 0.578
- *Cleanup time:* 0.1
- *Prompt tokens:* 489
- *Generation tokens:* 346
- *Total tokens:* 835
- *Prompt throughput (raw):* 846 tok/s
- *Generation throughput (raw):* 73.9 tok/s
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
- *Model load time:* 0.60s
- *Generation time:* 0.73s
- *Total time:* 1.34s
- *Input validation time:* 5.37e-05
- *Prompt preparation time:* 0.00408
- *First-token latency:* 0.181
- *Cleanup time:* 0.0696
- *Prompt tokens:* 350
- *Generation tokens:* 100
- *Total tokens:* 450
- *Prompt throughput (raw):* 1,933 tok/s
- *Generation throughput (raw):* 191 tok/s
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
- *Model load time:* 0.89s
- *Generation time:* 0.41s
- *Total time:* 1.32s
- *Input validation time:* 5.68e-05
- *Prompt preparation time:* 0.00885
- *First-token latency:* 0.0997
- *Cleanup time:* 0.0707
- *Prompt tokens:* 344
- *Generation tokens:* 61
- *Total tokens:* 405
- *Prompt throughput (raw):* 3,451 tok/s
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
- *Model load time:* 1.32s
- *Generation time:* 1.84s
- *Total time:* 3.17s
- *Input validation time:* 5.17e-05
- *Prompt preparation time:* 0.00727
- *First-token latency:* 0.632
- *Cleanup time:* 0.0816
- *Prompt tokens:* 1,070
- *Generation tokens:* 81
- *Total tokens:* 1,151
- *Prompt throughput (raw):* 1,692 tok/s
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
- *Model load time:* 1.34s
- *Generation time:* 2.27s
- *Total time:* 3.61s
- *Input validation time:* 7.37e-05
- *Prompt preparation time:* 0.000998
- *First-token latency:* 0.671
- *Cleanup time:* 0.0857
- *Prompt tokens:* 1,070
- *Generation tokens:* 106
- *Total tokens:* 1,176
- *Prompt throughput (raw):* 1,594 tok/s
- *Generation throughput (raw):* 67.0 tok/s
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
- *Model load time:* 0.96s
- *Generation time:* 0.74s
- *Total time:* 1.71s
- *Input validation time:* 5.24e-05
- *Prompt preparation time:* 0.00709
- *First-token latency:* 0.235
- *Cleanup time:* 0.0737
- *Prompt tokens:* 1,069
- *Generation tokens:* 97
- *Total tokens:* 1,166
- *Prompt throughput (raw):* 4,552 tok/s
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
- *Model load time:* 1.04s
- *Generation time:* 1.80s
- *Total time:* 2.86s
- *Input validation time:* 5.27e-05
- *Prompt preparation time:* 0.00569
- *First-token latency:* 0.493
- *Cleanup time:* 0.079
- *Prompt tokens:* 873
- *Generation tokens:* 95
- *Total tokens:* 968
- *Prompt throughput (raw):* 1,770 tok/s
- *Generation throughput (raw):* 73.6 tok/s
- *Peak memory:* 8.0
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
- *Model load time:* 2.53s
- *Generation time:* 1.46s
- *Total time:* 4.02s
- *Input validation time:* 4.66e-05
- *Prompt preparation time:* 0.0154
- *First-token latency:* 0.386
- *Cleanup time:* 0.121
- *Prompt tokens:* 421
- *Generation tokens:* 114
- *Total tokens:* 535
- *Prompt throughput (raw):* 1,089 tok/s
- *Generation throughput (raw):* 108 tok/s
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
- *Model load time:* 0.89s
- *Generation time:* 1.94s
- *Total time:* 2.84s
- *Input validation time:* 6.36e-05
- *Prompt preparation time:* 0.00162
- *First-token latency:* 0.23
- *Cleanup time:* 0.0829
- *Prompt tokens:* 883
- *Generation tokens:* 96
- *Total tokens:* 979
- *Prompt throughput (raw):* 3,840 tok/s
- *Generation throughput (raw):* 58.3 tok/s
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
- *Model load time:* 2.50s
- *Generation time:* 1.10s
- *Total time:* 3.62s
- *Input validation time:* 6.5e-05
- *Prompt preparation time:* 0.0158
- *First-token latency:* 0.368
- *Cleanup time:* 0.12
- *Prompt tokens:* 421
- *Generation tokens:* 89
- *Total tokens:* 510
- *Prompt throughput (raw):* 1,145 tok/s
- *Generation throughput (raw):* 123 tok/s
- *Peak memory:* 21
- *Active memory:* 20
- *Cache memory:* 0.10
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
- *Model load time:* 1.32s
- *Generation time:* 0.99s
- *Total time:* 2.32s
- *Input validation time:* 6.79e-05
- *Prompt preparation time:* 0.0013
- *First-token latency:* 0.275
- *Cleanup time:* 0.0839
- *Prompt tokens:* 421
- *Generation tokens:* 71
- *Total tokens:* 492
- *Prompt throughput (raw):* 1,529 tok/s
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
- *Model load time:* 2.24s
- *Generation time:* 3.32s
- *Total time:* 5.59s
- *Input validation time:* 5.58e-05
- *Prompt preparation time:* 0.0165
- *First-token latency:* 0.697
- *Cleanup time:* 0.117
- *Prompt tokens:* 421
- *Generation tokens:* 86
- *Total tokens:* 507
- *Prompt throughput (raw):* 604 tok/s
- *Generation throughput (raw):* 33.0 tok/s
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
- *Model load time:* 18.44s
- *Generation time:* 93.38s
- *Total time:* 111.83s
- *Input validation time:* 6.64e-05
- *Prompt preparation time:* 0.00731
- *First-token latency:* 83.6
- *Cleanup time:* 0.441
- *Prompt tokens:* 421
- *Generation tokens:* 80
- *Total tokens:* 501
- *Prompt throughput (raw):* 5.04 tok/s
- *Generation throughput (raw):* 31.9 tok/s
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
- *Model load time:* 0.79s
- *Generation time:* 0.68s
- *Total time:* 1.48s
- *Input validation time:* 0.00213
- *Prompt preparation time:* 0.00311
- *First-token latency:* 0.354
- *Cleanup time:* 0.074
- *Prompt tokens:* 1,204
- *Generation tokens:* 31
- *Total tokens:* 1,235
- *Prompt throughput (raw):* 3,398 tok/s
- *Generation throughput (raw):* 129 tok/s
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
- *Model load time:* 3.37s
- *Generation time:* 1.76s
- *Total time:* 5.16s
- *Input validation time:* 5.65e-05
- *Prompt preparation time:* 0.0218
- *First-token latency:* 0.303
- *Cleanup time:* 0.117
- *Prompt tokens:* 386
- *Generation tokens:* 74
- *Total tokens:* 460
- *Prompt throughput (raw):* 1,273 tok/s
- *Generation throughput (raw):* 56.5 tok/s
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
Description: Two tabby patterned cats are lying on a pink fabric surface on a sofa. Two television remote controls are visible near them.
Keywords: cats, tabby, sleeping, resting, pink, blanket, sofa, remote, indoor, domestic, fur, patterned, lounging, feline, pets
</pre>

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
- *Model load time:* 2.37s
- *Generation time:* 3.59s
- *Total time:* 5.98s
- *Input validation time:* 6.36e-05
- *Prompt preparation time:* 0.00369
- *First-token latency:* 0.779
- *Cleanup time:* 0.12
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
- *Model load time:* 2.43s
- *Generation time:* 0.92s
- *Total time:* 3.38s
- *Input validation time:* 5.7e-05
- *Prompt preparation time:* 0.022
- *First-token latency:* 0.356
- *Cleanup time:* 0.109
- *Prompt tokens:* 390
- *Generation tokens:* 73
- *Total tokens:* 463
- *Prompt throughput (raw):* 1,097 tok/s
- *Generation throughput (raw):* 132 tok/s
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
- *Model load time:* 2.56s
- *Generation time:* 3.70s
- *Total time:* 6.28s
- *Input validation time:* 5.29e-05
- *Prompt preparation time:* 0.00101
- *First-token latency:* 0.841
- *Cleanup time:* 0.132
- *Prompt tokens:* 390
- *Generation tokens:* 80
- *Total tokens:* 470
- *Prompt throughput (raw):* 464 tok/s
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
- *Model load time:* 0.64s
- *Generation time:* 0.63s
- *Total time:* 1.29s
- *Input validation time:* 6.2e-05
- *Prompt preparation time:* 0.01
- *First-token latency:* 0.251
- *Cleanup time:* 0.0849
- *Prompt tokens:* 734
- *Generation tokens:* 64
- *Total tokens:* 798
- *Prompt throughput (raw):* 2,930 tok/s
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
- *Model load time:* 1.74s
- *Generation time:* 3.01s
- *Total time:* 4.76s
- *Input validation time:* 5.54e-05
- *Prompt preparation time:* 0.0032
- *First-token latency:* 0.797
- *Cleanup time:* 0.101
- *Prompt tokens:* 1,335
- *Generation tokens:* 89
- *Total tokens:* 1,424
- *Prompt throughput (raw):* 1,675 tok/s
- *Generation throughput (raw):* 40.5 tok/s
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
- *Model load time:* 0.56s
- *Generation time:* 0.21s
- *Total time:* 0.79s
- *Input validation time:* 0.0041
- *Prompt preparation time:* 0.00685
- *First-token latency:* 0.0597
- *Cleanup time:* 0.062
- *Prompt tokens:* 350
- *Generation tokens:* 77
- *Total tokens:* 427
- *Prompt throughput (raw):* 5,862 tok/s
- *Generation throughput (raw):* 530 tok/s
- *Peak memory:* 1.2
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
- *Model load time:* 5.80s
- *Generation time:* 3.52s
- *Total time:* 9.33s
- *Input validation time:* 5.18e-05
- *Prompt preparation time:* 0.00829
- *First-token latency:* 1.41
- *Cleanup time:* 0.231
- *Prompt tokens:* 499
- *Generation tokens:* 84
- *Total tokens:* 583
- *Prompt throughput (raw):* 353 tok/s
- *Generation throughput (raw):* 53.1 tok/s
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
- *Model load time:* 1.00s
- *Generation time:* 0.67s
- *Total time:* 1.68s
- *Input validation time:* 6.88e-05
- *Prompt preparation time:* 0.00427
- *First-token latency:* 0.152
- *Cleanup time:* 0.0799
- *Prompt tokens:* 418
- *Generation tokens:* 130
- *Total tokens:* 548
- *Prompt throughput (raw):* 2,741 tok/s
- *Generation throughput (raw):* 269 tok/s
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
- *Model load time:* 1.85s
- *Generation time:* 1.13s
- *Total time:* 3.00s
- *Input validation time:* 5.45e-05
- *Prompt preparation time:* 0.0111
- *First-token latency:* 0.347
- *Cleanup time:* 0.115
- *Prompt tokens:* 409
- *Generation tokens:* 101
- *Total tokens:* 510
- *Prompt throughput (raw):* 1,179 tok/s
- *Generation throughput (raw):* 131 tok/s
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

<a id="model-mlx-community-step-37-flash-oq3e"></a>

### mlx-community/Step-3.7-Flash-oQ3e

<details>
<summary>Complete evidence: mlx-community/Step-3.7-Flash-oQ3e</summary>

- *Execution:* completed
- *Mechanical checks:* concerns detected
- *Assessment:* General checks + metadata fields and duplicate keywords;
  length limits and factual accuracy not assessed
- *Maintainer status:* observation_needs_reproduction
- *Observations:* Unrecognised model control tokens remain visible
- *Arch supported by installed mlx-vlm:* yes (model_type step3p7)
- *Model load time:* 9.02s
- *Generation time:* 9.34s
- *Total time:* 18.38s
- *Input validation time:* 5.74e-05
- *Prompt preparation time:* 0.017
- *First-token latency:* 4.93
- *Cleanup time:* 0.267
- *Prompt tokens:* 286
- *Generation tokens:* 236
- *Total tokens:* 522
- *Prompt throughput (raw):* 58.1 tok/s
- *Generation throughput (raw):* 54.1 tok/s
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
- *Model load time:* 1.89s
- *Generation time:* 1.42s
- *Total time:* 3.32s
- *Input validation time:* 6.26e-05
- *Prompt preparation time:* 0.00193
- *First-token latency:* 1.04
- *Cleanup time:* 0.0959
- *Prompt tokens:* 2,418
- *Generation tokens:* 12
- *Total tokens:* 2,430
- *Prompt throughput (raw):* 2,334 tok/s
- *Generation throughput (raw):* 36.2 tok/s
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
- *Model load time:* 2.85s
- *Generation time:* 39.46s
- *Total time:* 42.34s
- *Input validation time:* 5.93e-05
- *Prompt preparation time:* 0.0198
- *First-token latency:* 0.992
- *Cleanup time:* 0.128
- *Prompt tokens:* 545
- *Generation tokens:* 1,000
- *Total tokens:* 1,545
- *Prompt throughput (raw):* 550 tok/s
- *Generation throughput (raw):* 26.0 tok/s
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
- *Model load time:* 0.70s
- *Generation time:* 3.12s
- *Total time:* 3.83s
- *Input validation time:* 5.62e-05
- *Prompt preparation time:* 0.012
- *First-token latency:* 0.0987
- *Cleanup time:* 0.0838
- *Prompt tokens:* 411
- *Generation tokens:* 400
- *Total tokens:* 811
- *Prompt throughput (raw):* 4,165 tok/s
- *Generation throughput (raw):* 134 tok/s
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
- *Model load time:* 1.88s
- *Generation time:* 6.26s
- *Total time:* 8.16s
- *Input validation time:* 6.18e-05
- *Prompt preparation time:* 0.0045
- *First-token latency:* 0.491
- *Cleanup time:* 0.0968
- *Prompt tokens:* 511
- *Generation tokens:* 375
- *Total tokens:* 886
- *Prompt throughput (raw):* 1,042 tok/s
- *Generation throughput (raw):* 65.7 tok/s
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
- *Model load time:* 0.55s
- *Generation time:* 0.35s
- *Total time:* 0.90s
- *Input validation time:* 6.16e-05
- *Prompt preparation time:* 0.00213
- *First-token latency:* 0.0833
- *Cleanup time:* 0.0854
- *Prompt tokens:* 116
- *Generation tokens:* 97
- *Total tokens:* 213
- *Prompt throughput (raw):* 1,392 tok/s
- *Generation throughput (raw):* 396 tok/s
- *Peak memory:* 1.5
- *Active memory:* 0.61
- *Cache memory:* 0.25
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
