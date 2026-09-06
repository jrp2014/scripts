"""Contract tests for retained mechanical generation observations."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from typing import Literal

import pytest

import check_models

type ExpectedExecutionStatus = Literal["completed", "crashed", "indeterminate"]


@dataclass
class _Generation:
    text: str
    generation_tokens: int | None = 24
    prompt_tokens: int | None = None


def _result(
    text: str,
    *,
    generated_tokens: int = 24,
    prompt: str | None = None,
    requested_max_tokens: int | None = None,
    model_name: str = "example/model",
    known_special_tokens: tuple[str, ...] = (),
    assessment_profile: check_models.AssessmentProfile = "general",
) -> check_models.PerformanceResult:
    analysis = check_models.analyze_generation_text(
        text,
        generated_tokens=generated_tokens,
        prompt=prompt,
        requested_max_tokens=requested_max_tokens,
        known_special_tokens=known_special_tokens,
        assessment_profile=assessment_profile,
    )
    return check_models.PerformanceResult(
        model_name=model_name,
        success=True,
        generation=_Generation(text, generated_tokens),
        requested_max_tokens=requested_max_tokens,
        quality_analysis=analysis,
        assessment_profile=assessment_profile,
    )


CATALOG_PROMPT = (
    "Return exactly these three sections, and nothing else:\n"
    "Title: 5-10 words.\nDescription: 1-2 factual sentences.\n"
    "Keywords: 10-18 terms."
)


def test_general_profile_does_not_infer_a_contract_from_prompt_words() -> None:
    """An arbitrary short answer must not inherit the built-in metadata contract."""
    analysis = check_models.analyze_generation_text(
        "Yes", 1, prompt=CATALOG_PROMPT, requested_max_tokens=1
    )
    result = check_models.PerformanceResult(
        model_name="org/m",
        success=True,
        generation=_Generation("Yes", 1),
        quality_analysis=analysis,
    )
    assert check_models._assess_result(result).observations == ()
    assert analysis.assessment_profile == "general"


def test_empty_thinking_wrapper_still_requires_a_final_answer() -> None:
    """Removing short-answer judgments must not hide a protocol-only response."""
    result = _result("<think></think>", generated_tokens=2)
    assert check_models._assess_result(result).observations == ("missing_final_answer",)


def test_metadata_profile_checks_fields_without_parsing_the_prompt() -> None:
    """Explicit metadata checks work on paraphrased prompts and ignore prose limits."""
    analysis = check_models.analyze_generation_text(
        "Title: Mill\nDescription: A mill. People walk. Water flows.\nKeywords: mill, river, mill",
        30,
        prompt="Please tag this picture however you think best.",
        assessment_profile="metadata",
    )
    assert analysis.missing_sections == []
    assert analysis.title_word_count == 1
    assert analysis.keyword_count == 3
    assert analysis.duplicate_keywords == ["mill"]
    assert check_models._quality_observations(text="answer", analysis=analysis) == (
        "duplicate_keywords",
    )
    missing = check_models.analyze_generation_text(
        "A mill by a river.", 10, assessment_profile="metadata"
    )
    assert missing.missing_sections == ["title", "description", "keywords"]


@pytest.mark.parametrize(
    ("prompt", "lane", "override", "expected"),
    [
        (None, "blind", None, "metadata"),
        (CATALOG_PROMPT, "blind", None, "general"),
        (None, "triage", None, "general"),
        ("Tag it", "blind", "metadata", "metadata"),
        (None, "blind", "general", "general"),
    ],
)
def test_profile_selection_uses_prompt_origin_not_its_contents(
    prompt: str | None, lane: str, override: str | None, expected: str
) -> None:
    args = Namespace(prompt=prompt, eval_mode=lane, assessment_profile=override, max_tokens=50)
    check_models._apply_eval_mode_defaults(args, {})
    assert args.assessment_profile == expected


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(
            _result(""),
            check_models.ResultAssessment(
                "completed", "unusable", "observation_needs_reproduction", ("empty_output",)
            ),
            id="empty-output",
        ),
        pytest.param(
            _result("Brief reply", generated_tokens=2),
            check_models.ResultAssessment(
                "completed",
                "usable",
                "none",
                (),
            ),
            id="minimal-output",
        ),
        pytest.param(
            _result("word " * 100, generated_tokens=100),
            check_models.ResultAssessment(
                "completed", "unusable", "observation_needs_reproduction", ("repeated_output",)
            ),
            id="contiguous-repetition",
        ),
        pytest.param(
            _result(
                "A misty lakeshore with trees and power lines.",
                prompt=CATALOG_PROMPT,
                assessment_profile="metadata",
            ),
            check_models.ResultAssessment(
                "completed",
                "unusable",
                "none",
                ("missing_requested_sections",),
            ),
            id="missing-requested-sections",
        ),
        pytest.param(
            _result("word " * 100, generated_tokens=100, requested_max_tokens=100),
            check_models.ResultAssessment(
                "completed",
                "unusable",
                "observation_needs_reproduction",
                ("repeated_output", "token_cap_truncation"),
            ),
            id="degraded-token-cap",
        ),
        pytest.param(
            _result(
                "Return exactly these three sections, and nothing else: "
                "Title, Description, Keywords."
            ),
            check_models.ResultAssessment(
                "completed",
                "usable",
                "none",
                (),
            ),
            id="instruction-echo",
        ),
        pytest.param(
            _result("A caption.<|end|>"),
            check_models.ResultAssessment(
                "completed",
                "usable_with_caveats",
                "observation_needs_reproduction",
                ("unexpected_special_token",),
            ),
            id="unexpected-special-token",
        ),
        pytest.param(
            _result(
                "<think>Inspect the scene.</think> A blue boat rests on calm water.",
                model_name="example/thinking-model",
            ),
            check_models.ResultAssessment("completed", "usable", "none", ()),
            id="thinking-trace",
        ),
        pytest.param(
            _result(
                "<think>Inspect the scene carefully",
                model_name="example/thinking-model",
            ),
            check_models.ResultAssessment(
                "completed",
                "unusable",
                "observation_needs_reproduction",
                ("thinking_trace_incomplete",),
            ),
            id="incomplete-thinking-trace",
        ),
        pytest.param(
            _result(
                "Title: A blue boat\nDescription: A blue boat rests on calm water.\n"
                "Keywords: boat, water, blue, calm, lake, reflection, sky, shore, travel, vessel",
                prompt="Context: Existing metadata hints:\n- Keyword hints: mountain, forest, snow\n",
            ),
            check_models.ResultAssessment(
                "completed",
                "usable",
                "none",
                (),
            ),
            id="no-keyword-overlap",
        ),
    ],
)
def test_result_assessment_projects_only_ordered_mechanical_observations(
    result: check_models.PerformanceResult,
    expected: check_models.ResultAssessment,
) -> None:
    assert check_models._assess_result(result) == expected


def test_token_cap_alone_is_neutral() -> None:
    result = _result(
        "A complete response with a finished sentence.",
        generated_tokens=80,
        requested_max_tokens=80,
    )

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )


@pytest.mark.parametrize(
    ("title", "keywords", "expected_title_words", "expected_keyword_count", "duplicates"),
    [
        (
            "Four Word Title Here",
            "one, two, three, four, five, six, seven, eight, nine, ten",
            4,
            10,
            [],
        ),
        (
            "Five Word Catalogue Title Here",
            (
                "one, two, three, four, five, six, seven, eight, nine, ten, eleven, "
                "twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen"
            ),
            5,
            19,
            [],
        ),
        (
            "Five Word Catalogue Title Here",
            "Halesworth, sky, brick, windows, sign, gravel, clouds, arts, building, halesworth",
            5,
            10,
            ["halesworth"],
        ),
    ],
)
def test_metadata_counts_are_facts_and_duplicates_are_caveats(
    title: str,
    keywords: str,
    expected_title_words: int,
    expected_keyword_count: int,
    duplicates: list[str],
) -> None:
    """Prose-derived limits are ignored; duplicate keywords remain a repairable caveat."""
    result = _result(
        f"Title: {title}\n"
        "Description: A factual description of the visible building.\n"
        f"Keywords: {keywords}",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.title_word_count == expected_title_words
    assert result.quality_analysis.keyword_count == expected_keyword_count
    assert result.quality_analysis.duplicate_keywords == duplicates
    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed",
        "usable_with_caveats" if duplicates else "usable",
        "none",
        ("duplicate_keywords",) if duplicates else (),
    )


def test_compliant_catalog_constraints_remain_clean() -> None:
    result = _result(
        "Title: Five Word Catalogue Title Here\n"
        "Description: A factual description of the visible building.\n"
        "Keywords: one, two, three, four, five, six, seven, eight, nine, ten",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )


def test_catalog_constraints_are_not_inferred_for_an_unrelated_prompt() -> None:
    result = _result(
        "Title: Brief title\nDescription: A factual description.\nKeywords: repeated, repeated",
        prompt="Describe the response format used in this example.",
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.title_word_count is None
    assert result.quality_analysis.keyword_count is None
    assert result.quality_analysis.duplicate_keywords == []
    assert "catalog_constraint_violation" not in check_models._assess_result(result).observations


def test_configured_utterance_boundary_is_reported_when_visible() -> None:
    text = (
        "Title: Five Word Catalogue Title Here\n"
        "Description: A factual description of the visible building.\n"
        "Keywords: one, two, three, four, five, six, seven, eight, nine, ten"
        "<end_of_utterance>"
    )
    result = _result(
        text,
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
        known_special_tokens=("<end_of_utterance>",),
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.role_boundary_tokens == ["<end_of_utterance>"]
    assert check_models._assess_result(result).observations == ("role_boundary_token_present",)


def test_missing_generation_count_does_not_make_complete_output_minimal() -> None:
    result = check_models.PerformanceResult(
        model_name="example/model",
        success=True,
        generation=_Generation(
            "A complete description of a quiet lake beneath a clear evening sky.",
            generation_tokens=None,
            prompt_tokens=900,
        ),
    )

    assert "minimal_output" not in check_models._assess_result(result).observations


def test_concise_complete_output_is_not_minimal_relative_to_prompt_length() -> None:
    result = check_models.PerformanceResult(
        model_name="example/model",
        success=True,
        generation=_Generation(
            "A concise but complete description of the visible landscape.",
            generation_tokens=10,
            prompt_tokens=1_000,
        ),
    )

    assert "minimal_output" not in check_models._assess_result(result).observations


def test_complete_image_phrase_is_not_semantic_minimal_output() -> None:
    result = check_models.PerformanceResult(
        model_name="example/model",
        success=True,
        generation=_Generation(
            "The image is a photograph of two cats sleeping on a couch.",
            generation_tokens=4,
        ),
    )

    assert "minimal_output" not in check_models._assess_result(result).observations


def test_missing_token_counts_do_not_enable_ratio_inference() -> None:
    result = check_models.PerformanceResult(
        model_name="example/model",
        success=True,
        generation=_Generation(
            "A concise but complete description of the visible landscape.",
            generation_tokens=None,
            prompt_tokens=None,
        ),
    )

    assert "minimal_output" not in check_models._assess_result(result).observations


def test_empty_thinking_wrapper_is_neutral() -> None:
    result = _result("<think></think> A complete response.", model_name="example/thinking-model")

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )


@pytest.mark.parametrize(
    "text",
    [
        "<|START_THINKING|><|END_THINKING|> A complete response.",
        "◁think▷◁/think▷ A complete response.",
    ],
)
def test_empty_wrappers_of_every_recognised_pair_are_neutral(text: str) -> None:
    """Empty thinking wrappers stay neutral for every non-channel delimiter pair."""
    result = _result(text)

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )


def test_generated_empty_channel_wrapper_is_control_token_leakage() -> None:
    result = _result("<|channel>thought\n<channel|>Title: A complete response.")

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed",
        "usable_with_caveats",
        "observation_needs_reproduction",
        ("unexpected_special_token",),
    )
    assert check_models._observation_details(result)["unexpected_special_tokens"] == [
        "<|channel>thought",
        "<channel|>",
    ]


def test_closed_thinking_trace_is_neutral_and_model_name_invariant() -> None:
    text = "<think>Inspect the scene.</think> A blue boat rests on calm water."
    plain = _result(text, model_name="example/plain-model")
    named = _result(text, model_name="example/thinking-model")

    assert check_models._assess_result(plain) == check_models._assess_result(named)
    assert check_models._assess_result(plain) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )
    assert check_models._observation_details(plain)["thinking_trace_markers"] == [
        "<think>",
        "</think>",
    ]


@pytest.mark.parametrize(
    ("start_marker", "end_marker"),
    [
        ("<|channel>thought", "<channel|>"),
        ("<|START_THINKING|>", "<|END_THINKING|>"),
    ],
)
def test_upstream_server_thinking_marker_pairs_are_recognised(
    start_marker: str,
    end_marker: str,
) -> None:
    """mlx-vlm server marker pairs must behave exactly like <think></think>."""
    closed = _result(
        f"{start_marker}Inspect the scene.{end_marker} A blue boat rests on calm water."
    )
    assert check_models._assess_result(closed) == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )
    # The trace's own delimiters must not be double-flagged as leaked control
    # tokens by the generic <|...|> pattern.
    details = check_models._observation_details(closed)
    assert "unexpected_special_tokens" not in details
    assert details["thinking_trace_markers"] == [start_marker, end_marker]

    unclosed = _result(f"{start_marker}Inspect the scene forever...")
    analysis = unclosed.quality_analysis
    assert analysis is not None
    assert analysis.thinking_trace_incomplete


def test_closed_thinking_trace_without_final_answer_is_unusable() -> None:
    result = _result("<think>Inspect the scene.</think>")

    assert check_models._assess_result(result) == check_models.ResultAssessment(
        "completed",
        "unusable",
        "observation_needs_reproduction",
        ("missing_final_answer",),
    )


def test_prompt_seeded_thinking_open_is_closed_by_generated_marker() -> None:
    result = check_models.PerformanceResult(
        model_name="example/seeded-thinking",
        success=True,
        generation=_Generation(
            "Inspect the scene.</done> Two cats sleep on a pink couch.",
            generation_tokens=18,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_preview="<image>Describe this image.<reason>",
            generate_kwargs={
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            },
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
        system_info={},
    )
    enriched = context.result_set.results[0]
    assert dict(context.assessments)[result.model_name] == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )
    assert check_models._observation_details(enriched)["thinking_trace_markers"] == [
        "<reason>",
        "</done>",
    ]


def test_prompt_seeded_thinking_uses_full_prompt_when_preview_is_truncated() -> None:
    result = check_models.PerformanceResult(
        model_name="example/long-seeded-thinking",
        success=True,
        generation=_Generation(
            "Inspect the scene.</done> Two cats sleep on a pink couch.",
            generation_tokens=18,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_preview="<image>Long catalogue prompt truncated before the assistant suffix...",
            rendered_prompt="<image>Long catalogue prompt.<reason>",
            generate_kwargs={
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            },
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
        system_info={},
    )
    enriched = context.result_set.results[0]

    assert dict(context.assessments)[result.model_name] == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )
    assert check_models._observation_details(enriched)["thinking_trace_markers"] == [
        "<reason>",
        "</done>",
    ]


def test_complete_prompt_seeded_empty_thinking_wrapper_is_neutral() -> None:
    result = check_models.PerformanceResult(
        model_name="example/seeded-no-thinking",
        success=True,
        generation=_Generation(
            "Two cats sleep on a pink couch beside two remote controls.",
            generation_tokens=14,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_preview="<image>Describe this image.<reason></done>",
            generate_kwargs={
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            },
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
        system_info={},
    )

    assert dict(context.assessments)[result.model_name] == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )


def test_prompt_seeded_thinking_open_without_generated_close_is_unusable() -> None:
    result = check_models.PerformanceResult(
        model_name="example/seeded-unclosed-thinking",
        success=True,
        generation=_Generation(
            "Inspecting the scene without ever ending the reasoning trace.",
            generation_tokens=12,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_preview="<image>Describe this image.<reason>",
            generate_kwargs={
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            },
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
        system_info={},
    )
    assessment = dict(context.assessments)[result.model_name]

    assert assessment.usability == "unusable"
    assert assessment.observations == ("thinking_trace_incomplete",)


@pytest.mark.parametrize(
    "text",
    [
        "The image contains two resting cats, and the next detail is The",
        "Based on the image, here is the requested description:\n\n*   **",
    ],
)
def test_general_cap_does_not_infer_truncation_from_prose(text: str) -> None:
    result = _result(text, generated_tokens=500, requested_max_tokens=500)

    assert result.quality_analysis is not None
    assert result.quality_analysis.likely_capped
    assert "token_cap_truncation" not in check_models._assess_result(result).observations


def test_configured_thinking_delimiters_are_observed_without_model_name_policy() -> None:
    result = check_models.PerformanceResult(
        model_name="example/plain-model",
        success=True,
        generation=_Generation(
            "<reason>Inspect the scene.</done> A blue boat rests on calm water.",
            generation_tokens=18,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            generate_kwargs={
                "enable_thinking": True,
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            }
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
    )

    assessment = dict(context.assessments)[result.model_name]
    assert assessment == check_models.ResultAssessment("completed", "usable", "none", ())


def test_configured_empty_thinking_wrapper_is_neutral_evidence() -> None:
    result = check_models.PerformanceResult(
        model_name="example/plain-model",
        success=True,
        generation=_Generation(
            "<reason></done> Two cats sleep on a pink couch.",
            generation_tokens=14,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            generate_kwargs={
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            }
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
        system_info={},
    )
    enriched = context.result_set.results[0]

    assert dict(context.assessments)[result.model_name] == check_models.ResultAssessment(
        "completed", "usable", "none", ()
    )
    assert check_models._observation_details(enriched)["thinking_trace_markers"] == [
        "<reason>",
        "</done>",
    ]


def test_configured_special_token_is_not_unexpected() -> None:
    result = _result(
        "A complete response.<|custom_end|>",
        known_special_tokens=("<|custom_end|>",),
    )

    assert "unexpected_special_token" not in check_models._assess_result(result).observations


@pytest.mark.parametrize(
    "wrapper",
    ["<|im_start|>", "<|begin_of_box|>", "<|channel>", "<channel|>"],
)
def test_undeclared_control_wrapper_is_observed_generically(wrapper: str) -> None:
    result = _result(f"{wrapper} A complete response.")

    assert result.quality_analysis is not None
    assert wrapper in result.quality_analysis.unexpected_special_tokens
    assert "unexpected_special_token" in check_models._assess_result(result).observations


def test_declared_generation_wrappers_are_neutral_without_model_name_policy() -> None:
    wrappers = ("<|custom_eos|>", "<|custom_stop|>")
    result = check_models.PerformanceResult(
        model_name="example/plain-model",
        success=True,
        generation=_Generation(
            f"{wrappers[0]}{wrappers[1]}<reason>Inspect the scene.</done> A complete response.",
            generation_tokens=18,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            eos_token=wrappers[0],
            generate_kwargs={
                "eos_tokens": [wrappers[1]],
                "enable_thinking": True,
                "thinking_start_token": "<reason>",
                "thinking_end_token": "</done>",
            },
        ),
    )

    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
    )

    enriched = context.result_set.results[0]
    assert enriched.quality_analysis is not None
    assert enriched.quality_analysis.unexpected_special_tokens == []
    assert enriched.quality_analysis.configured_generation_wrappers == [
        "<|custom_eos|>",
        "<|custom_stop|>",
        "<reason>",
        "</done>",
    ]
    assert dict(context.assessments)[result.model_name].observations == (
        "configured_wrapper_present",
    )


def test_configured_user_role_token_mid_output_is_observed_as_a_boundary() -> None:
    result = _result(
        "Title: Two cats\nDescription: Two cats rest indoors.\n"
        "Keywords: cats, indoor, resting, sofa, pets, home, tabby, fur, furniture, calm"
        "<|im_user|>Solve an unrelated equation.",
        known_special_tokens=("<|im_user|>",),
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.role_boundary_tokens == ["<|im_user|>"]
    assert "role_boundary_token_present" in check_models._assess_result(result).observations


def test_partial_keyword_overlap_is_neutral() -> None:
    result = _result(
        "Title: A blue boat at dawn\n"
        "Description: A blue boat rests on calm water at dawn.\n"
        "Keywords: boat, water, blue, calm, dawn, lake, reflection, sky, shore, vessel",
        prompt="Context: Existing metadata hints:\n- Keyword hints: boat, mountain, forest\n",
    )

    assert "no_keyword_overlap" not in check_models._assess_result(result).observations


def test_draft_metadata_keywords_do_not_become_output_requirements() -> None:
    result = _result(
        "Title: Boats at dusk\n"
        "Description: Two boats rest on reflective water at dusk.\n"
        "Keywords: boats, water, dusk, reflection, sky, shore, calm, travel, vessel, evening",
        prompt=(
            "Context: Draft descriptive metadata:\n"
            "- Existing keywords: Example Harbour, Sample Village\n"
        ),
    )

    assert "no_keyword_overlap" not in check_models._assess_result(result).observations


def test_requested_section_parser_is_profile_gated() -> None:
    plain = check_models.analyze_generation_text("A plain caption.", 12)
    requested = check_models.analyze_generation_text(
        "A plain caption.",
        12,
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert plain.missing_sections == []
    assert requested.missing_sections == ["title", "description", "keywords"]


def test_short_catalog_response_still_has_to_satisfy_requested_sections() -> None:
    result = _result(
        "Do not output the prompt instructions.",
        generated_tokens=8,
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert check_models._assess_result(result).usability == "unusable"
    assert check_models._assess_result(result).observations == ("missing_requested_sections",)


def test_multiline_title_is_present_without_an_inferred_single_line_contract() -> None:
    result = _result(
        "Title:\n- remote control\n- cat\n- sofa\n"
        "Description: A cat sits beside a remote control.\n"
        "Keywords: cat, sofa, remote, indoor, pet, furniture, resting, home, animal, room",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.missing_sections == []
    assert check_models._assess_result(result).usability == "usable"


def test_markdown_bold_catalog_labels_satisfy_requested_sections() -> None:
    result = _result(
        "**Title:**\nViking Bay Beach, Broadstairs, Kent\n\n"
        "**Description:**\nA sunny beach scene with people and colourful huts.\n\n"
        "**Keywords:**\nbeach, Broadstairs, Kent, coast, sand, sea, people, sky, "
        "buildings, summer",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.missing_sections == []
    assert check_models._assess_result(result).usability == "usable"


@pytest.mark.parametrize("heading", ["#", "###", "######"])
def test_markdown_heading_catalog_labels_satisfy_requested_sections(heading: str) -> None:
    result = _result(
        f"{heading} Title:\nTwo Cats Lounging on Red Couch\n\n"
        f"{heading} Description:\nTwo cats relax together on a red couch.\n\n"
        f"{heading} Keywords:\n"
        "cats, lounging, red couch, remote controls, relaxed, indoor, comfort, "
        "feline, domestic, resting",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.missing_sections == []
    assert check_models._assess_result(result).usability == "usable"


def test_text_before_catalog_sections_does_not_infer_an_exact_output_contract() -> None:
    result = _result(
        "Remove non-visual information.\n\n"
        "Title: Viking Bay Beach, Broadstairs, Kent\n"
        "Description: A sunny beach scene with people and colourful huts.\n"
        "Keywords: beach, Broadstairs, Kent, coast, sand, sea, people, sky, "
        "buildings, summer",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert check_models._assess_result(result).observations == ()
    assert check_models._assess_result(result).usability == "usable"


def test_empty_thinking_wrapper_before_catalog_sections_is_neutral() -> None:
    result = _result(
        "<think></think>\n"
        "Title: Viking Bay Beach, Broadstairs, Kent\n"
        "Description: A sunny beach scene with people and colourful huts.\n"
        "Keywords: beach, Broadstairs, Kent, coast, sand, sea, people, sky, "
        "buildings, summer",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
    )

    assert result.quality_analysis is not None
    assert check_models._assess_result(result).usability == "usable"


def test_repeated_keyword_cycle_is_repetitive_output() -> None:
    cycle = "cat, sofa, indoor, pet, resting, animal, home, furniture, whiskers, fur"
    result = _result(
        "Title: Two cats resting indoors\n"
        "Description: Two cats rest on a sofa.\n"
        f"Keywords: {cycle}, {cycle}, {cycle}",
        prompt=CATALOG_PROMPT,
        assessment_profile="metadata",
        generated_tokens=80,
    )

    assert result.quality_analysis is not None
    assert result.quality_analysis.is_repetitive is True
    assert check_models._assess_result(result).usability == "unusable"


def test_contiguous_repetition_detector_ignores_distributed_reuse() -> None:
    repeated, token = check_models._detect_repetitive_output("blue boat " * 60)
    distributed, _ = check_models._detect_repetitive_output(
        "A blue boat crosses the lake while another boat rests near a blue pier."
    )

    assert repeated is True
    assert token is not None
    assert distributed is False


@pytest.mark.parametrize(
    ("success", "error_message", "expected"),
    [
        (True, None, "completed"),
        (False, "boom", "crashed"),
        (False, "server disconnected without sending a response", "indeterminate"),
    ],
)
def test_result_assessment_execution_statuses(
    success: bool,
    error_message: str | None,
    expected: ExpectedExecutionStatus,
) -> None:
    result = check_models.PerformanceResult(
        model_name="example/model",
        success=success,
        generation=_Generation("Complete response.") if success else None,
        error_message=error_message,
    )

    assert check_models._assess_result(result).execution == expected


def test_empty_wrapper_reporting_policy_is_explicit_per_pair() -> None:
    """Every delimiter pair must carry an explicit empty-wrapper policy.

    Template-seeded pairs stay neutral when empty; channel transport syntax
    reports as control-token leakage. A new pair must opt in deliberately.
    """
    reporting = [
        (pair.start, pair.end)
        for pair in check_models.THINKING_TRACE_DELIMITERS
        if pair.reports_when_empty
    ]
    assert reporting == [("<|channel>thought", "<channel|>")]
    # The legacy pair table and default end marker stay derived, not re-spelled.
    assert (
        tuple((pair.start, pair.end) for pair in check_models.THINKING_TRACE_DELIMITERS)
        == check_models.THINKING_TRACE_DELIMITER_PAIRS
    )
    assert check_models.THINKING_TRACE_DELIMITERS[0].end == check_models.DEFAULT_THINKING_END_MARKER
    leak_labels = {label for _, label in check_models.SPECIAL_TOKEN_LEAK_PATTERNS}
    assert check_models.DEFAULT_THINKING_END_MARKER in leak_labels


def test_failure_phase_labels_cover_the_full_vocabulary() -> None:
    """Every FailurePhaseName renders a deliberate human label."""
    phase_values = check_models._literal_values(check_models.FailurePhaseName)
    assert set(check_models._FAILURE_PHASE_HUMAN_LABELS) == phase_values
    assert phase_values == check_models._FAILURE_PHASE_VALUES
    # Runtime-attribution phases overlap the failure vocabulary only on the
    # phases both track; the two extra runtime keys are synthetic splits.
    runtime_values = check_models._literal_values(check_models.RuntimePhaseName)
    assert runtime_values - phase_values == {
        "upstream_prefill_first_token",
        "input_preparation_and_decode",
    }


class TestFinalAnswerView:
    """Complete thinking traces must not count as unwanted final-answer text."""

    GOOD_ANSWER = (
        "Title: Dover Castle Exterior on a Grassy Hill\n\n"
        "Description: An exterior view of the historic stone castle under a cloudy sky.\n\n"
        "Keywords: Dover, Castle, England, Historic, Medieval, Stone, Tower, Arch, "
        "Hill, Sky, Fortress, Kent"
    )

    def test_view_strips_emitted_complete_trace(self) -> None:
        """An emitted <think>...</think> block is removed; the answer remains."""
        text = "<think>Let me look at the image carefully.</think>\n" + self.GOOD_ANSWER

        assert check_models._final_answer_view(text) == self.GOOD_ANSWER

    def test_view_strips_prompt_seeded_trace(self) -> None:
        """A closing marker whose opener lives in the prompt removes the seeded tail."""
        text = "Reasoning that continues the seeded block.\n</think>\n" + self.GOOD_ANSWER

        view = check_models._final_answer_view(text, seeded_text="assistant\n<think>")

        assert view == self.GOOD_ANSWER

    def test_view_keeps_incomplete_trace(self) -> None:
        """An unclosed trace is left intact so the incomplete-trace signal still fires."""
        text = "<think>Still reasoning with no end marker"

        assert check_models._final_answer_view(text) == text

    def test_view_keeps_prompt_seeded_open_without_end_marker(self) -> None:
        """A seeded opener with no emitted end marker leaves the text untouched."""
        text = "Reasoning that never closes"

        assert check_models._final_answer_view(text, seeded_text="assistant\n<think>") == text

    def test_completed_trace_then_answer_is_not_preamble(self) -> None:
        """Regression: Qwen3-VL-Thinking shape — reasoning, close, then all three fields."""
        text = (
            "Got it, let's tackle this step by step. The title should be specific.\n"
            "</think>\n\n" + self.GOOD_ANSWER
        )

        analysis = check_models.analyze_generation_text(
            text,
            generated_tokens=400,
            requested_max_tokens=1000,
            prompt=CATALOG_PROMPT,
            assessment_profile="metadata",
            seeded_thinking_text="assistant\n<think>",
        )

        assert analysis.has_thinking_trace is True
        assert analysis.thinking_trace_incomplete is False
        assert analysis.missing_sections == []

    def test_capped_comma_tail_reports_unfinished_list(self) -> None:
        """Regression: ERNIE shape — capped answer ending mid keyword list."""
        text = (
            "Title: Dover Castle Exterior on a Grassy Hill\n\n"
            "Description: An exterior view of the historic castle.\n\n"
            "Keywords: Dover, Castle, England, Historic, Medieval, Stone, Sky, Clouds,"
        )

        analysis = check_models.analyze_generation_text(
            text,
            generated_tokens=1000,
            requested_max_tokens=1000,
            prompt=CATALOG_PROMPT,
            assessment_profile="metadata",
        )

        assert analysis.likely_capped is True
        assert "unfinished_list" in analysis.token_cap_reasons


def test_configured_thinking_markers_are_not_prestripped_from_analysis() -> None:
    """Regression: with a thinking budget configured, the </think> closure must survive.

    ``_configured_output_wrappers`` used to include the configured thinking
    start/end tokens, so ``_normalize_output_for_analysis`` stripped ``</think>``
    before ``_final_answer_view`` ran; the seeded trace could then never be
    recognised as complete and the reasoning was flagged as preamble.
    """
    diagnostics = check_models.PromptDiagnostics(
        rendered_prompt="<|im_start|>assistant\n<think>\n",
        generate_kwargs={
            "enable_thinking": True,
            "thinking_budget": 800,
            "thinking_start_token": "<think>",
            "thinking_end_token": "</think>",
        },
    )

    wrappers = check_models._configured_output_wrappers(diagnostics)
    assert "<think>" not in wrappers
    assert "</think>" not in wrappers
    # ...but they are still reported as configured generation wrappers.
    assert "</think>" in check_models._configured_generation_wrappers(diagnostics)

    class _Gen:
        text = (
            "Let me think about the title first, it should be 5-10 words.\n"
            "</think>\n\n"
            "Title: Two Tabby Cats Resting on a Pink Couch\n\n"
            "Description: Two tabby cats rest on a pink couch with remotes nearby.\n\n"
            "Keywords: cats, tabby, couch, pink, remote, resting, indoor, pets, fur, "
            "sofa, cushion, home"
        )
        generation_tokens = 300
        prompt_tokens = 900

    result = check_models.PerformanceResult(
        model_name="org/thinker",
        generation=_Gen(),
        success=True,
        requested_max_tokens=1000,
        prompt_diagnostics=diagnostics,
    )

    populated = check_models._populate_result_quality_analysis(
        result, prompt=CATALOG_PROMPT, requested_max_tokens=1000
    )

    analysis = populated.quality_analysis
    assert analysis is not None
    assert analysis.has_thinking_trace is True
    assert check_models._assess_result(populated).usability == "usable"


def test_tokenizer_special_thinking_tokens_survive_without_configured_budget() -> None:
    """Regression: <think>/</think> declared as tokenizer special tokens, no budget.

    With no thinking flags configured, ``_configured_output_wrappers`` had
    nothing to protect and the tokenizer's own special-token list stripped
    the delimiters before ``_final_answer_view`` ran, so a completed trace was
    again read as preamble. Protection now covers every recognised delimiter
    pair regardless of configuration.
    """
    diagnostics = check_models.PromptDiagnostics(
        rendered_prompt="<|im_start|>assistant\n",
        special_tokens=("<think>", "</think>", "<|im_end|>"),
        generate_kwargs={},  # no thinking budget or flags at all
    )

    class _Gen:
        text = (
            "<think>Consider the scene: two cats, a couch, remotes.</think>\n\n"
            "Title: Two Tabby Cats Resting on a Pink Couch\n\n"
            "Description: Two tabby cats rest on a pink couch with remotes nearby.\n\n"
            "Keywords: cats, tabby, couch, pink, remote, resting, indoor, pets, fur, "
            "sofa, cushion, home"
        )
        generation_tokens = 120
        prompt_tokens = 900

    result = check_models.PerformanceResult(
        model_name="org/special-token-thinker",
        generation=_Gen(),
        success=True,
        requested_max_tokens=1000,
        prompt_diagnostics=diagnostics,
    )

    populated = check_models._populate_result_quality_analysis(
        result, prompt=CATALOG_PROMPT, requested_max_tokens=1000
    )

    analysis = populated.quality_analysis
    assert analysis is not None
    assert analysis.has_thinking_trace is True
    assert check_models._assess_result(populated).usability == "usable"


class TestDownloadTimeoutClassification:
    """A per-model timeout that fires mid-download is indeterminate, not a crash."""

    DOWNLOAD_CAPTURE = (
        "Downloading bytes: #########7| 15.7GB, 32.9MB/s\n"
        "Reconstructing (incomplete total...): 100%|##########| 16.1GB / 16.1GB\n"
        "Fetching 13 files:  77%|#######6  | 10/13 [07:37<02:17, 45.70s/it]\n"
        "[21:00:52] DEBUG    Model org/big not found in HF cache (may need to download)"
    )

    def _timeout_result(self, *, phase: str, captured: str) -> check_models.PerformanceResult:
        chain = (
            check_models.FailureException(
                exception_type="TimeoutError",
                module="builtins",
                message="Operation timed out after 300.0 seconds",
                origin="check_models.py",
            ),
        )
        return check_models.PerformanceResult(
            model_name="org/big",
            generation=None,
            success=False,
            failure_phase=phase,
            error_type="ValueError",
            root_error_type="TimeoutError",
            exception_chain=chain,
            error_message="Model loading failed: Operation timed out after 300.0 seconds",
            captured_output_on_fail=captured,
        )

    def test_download_timeout_is_indeterminate_and_not_maintainer_actionable(self) -> None:
        """The model was never loaded: indeterminate, not evaluated, no issue draft."""
        result = self._timeout_result(phase="model_load", captured=self.DOWNLOAD_CAPTURE)

        assert check_models._is_download_timeout_failure(result) is True
        assessment = check_models._assess_result(result)
        assert assessment.execution == "indeterminate"
        assert assessment.usability == "not_evaluated"
        assert assessment.maintainer_status == "none"

    def test_download_timeout_reason_names_root_cause_and_remedy(self) -> None:
        """The outcome is user-actionable: the reason says exactly what to do."""
        result = self._timeout_result(phase="model_load", captured=self.DOWNLOAD_CAPTURE)

        reason = check_models._indeterminate_reason(result)

        assert reason.startswith("download timeout:")
        assert "never loaded" in reason
        assert "re-run" in reason
        assert "hf download" in reason
        assert "--timeout" in reason

    def test_hung_decode_timeout_stays_an_actionable_crash(self) -> None:
        """A timeout during inference is what the timeout exists for: still a crash."""
        result = self._timeout_result(phase="decode", captured="Fetching 13 files: 100%")

        assert check_models._is_download_timeout_failure(result) is False
        assessment = check_models._assess_result(result)
        assert assessment.execution == "crashed"
        assert assessment.maintainer_status == "actionable_failure"

    def test_load_timeout_without_download_evidence_stays_a_crash(self) -> None:
        """A load-phase timeout on a fully cached model is not a download problem."""
        result = self._timeout_result(phase="model_load", captured="")

        assert check_models._is_download_timeout_failure(result) is False
        assert check_models._assess_result(result).execution == "crashed"

    def test_run_summary_row_states_download_timeout_remedy(self) -> None:
        """The paste-ready review table carries the root cause, not a bare stage."""
        failure: check_models.JsonlFailureRecord = {
            "phase": "model_load",
            "stage": "Model Error",
            "message": "Model loading failed: Operation timed out after 300.0 seconds",
            "exception_type": "ValueError",
        }

        cell = check_models._run_issue_failure_observed_result(
            failure, self.DOWNLOAD_CAPTURE.casefold()
        )

        assert cell.startswith("Download timeout:")
        assert "hf download" in cell

        # Without download evidence the same failure falls back to its stage.
        assert (
            check_models._run_issue_failure_observed_result(failure, "")
            == "Model Error during model loading"
        )


# ── Exact prompt token accounting ────────────────────────────────────────────


class TestExactPromptTokenAccounting:
    """A tokenizer count of the rendered prompt replaces the word-ratio heuristic."""

    def test_analysis_prefers_exact_text_tokens(self) -> None:
        """An exact count wins and is labelled as tokenizer-sourced."""
        analysis = check_models.analyze_generation_text(
            "Title: A\nDescription: B\nKeywords: c, d",
            generated_tokens=20,
            prompt_tokens=16467,
            prompt="some prompt words here",
            prompt_text_tokens=298,
        )
        assert analysis.prompt_tokens_text_est == 298
        assert analysis.prompt_tokens_nontext_est == 16169
        assert analysis.prompt_tokens_text_source == "tokenizer"

    def test_analysis_falls_back_to_heuristic(self) -> None:
        """Without an exact count the word-ratio heuristic is used and labelled."""
        analysis = check_models.analyze_generation_text(
            "Title: A", generated_tokens=3, prompt_tokens=100, prompt="four words of prompt"
        )
        assert analysis.prompt_tokens_text_source == "heuristic"
        assert analysis.prompt_tokens_text_est == check_models._estimate_prompt_tokens_from_text(
            "four words of prompt"
        )

    def test_count_rendered_prompt_tokens_uses_encode_and_tolerates_signatures(self) -> None:
        """Counting duck-types encode and copes with older encode signatures."""

        class _Tok:
            def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
                return [1] * (len(text.split()) + (1 if add_special_tokens else 0))

        class _OldTok:
            def encode(self, text: str) -> list[int]:  # no add_special_tokens kwarg
                return [1] * len(text.split())

        prompt = "a b c"
        # Without upstream's helper resolvable for a None model_type, markers are off.
        assert check_models._count_rendered_prompt_tokens(_Tok(), prompt, None, object()) == 3
        assert check_models._count_rendered_prompt_tokens(_OldTok(), prompt, None, object()) == 3
        assert check_models._count_rendered_prompt_tokens(object(), prompt, None, object()) is None

    def test_exact_split_classifies_visual_burden_without_placeholder_regex(self) -> None:
        """With exact text tokens the ratio alone classifies visual burden."""
        kind, _ = check_models._classify_prompt_burden(
            total=16467, text_est=298, nontext_est=16169, ratio=0.98, placeholders=0
        )
        assert kind == "mixed"
        kind, _ = check_models._classify_prompt_burden(
            total=16467,
            text_est=298,
            nontext_est=16169,
            ratio=0.98,
            placeholders=0,
            exact_text_tokens=True,
        )
        assert kind == "visual_input"

    def test_inconsistent_exact_count_is_rejected_and_recorded(self) -> None:
        """An exact count above the total is kept as evidence, not used for the split."""
        analysis = check_models.analyze_generation_text(
            "Title: A",
            generated_tokens=3,
            prompt_tokens=5,
            prompt="one two three four five six seven",  # heuristic ~10 > total 5
            prompt_text_tokens=7,
        )
        assert analysis.prompt_tokens_text_exact_rejected == 7
        # The heuristic is bound by the same invariant; here it also exceeds the
        # 5-token total, so the split is unavailable rather than impossible.
        assert analysis.prompt_tokens_text_source is None
        assert analysis.prompt_tokens_text_est is None
        assert analysis.prompt_tokens_nontext_est is None

    def test_heuristic_fallback_within_total_is_used(self) -> None:
        """A rejected exact count falls back to the heuristic when it fits the total."""
        analysis = check_models.analyze_generation_text(
            "Title: A",
            generated_tokens=3,
            prompt_tokens=100,
            prompt="four words of prompt",
            prompt_text_tokens=250,
        )
        assert analysis.prompt_tokens_text_exact_rejected == 250
        assert analysis.prompt_tokens_text_source == "heuristic"
        assert analysis.prompt_tokens_text_est is not None
        assert 0 <= analysis.prompt_tokens_text_est <= 100

    def test_composition_row_surfaces_rejected_count_when_split_unavailable(self) -> None:
        """The rejected exact count is reported even when no split survived."""
        analysis = check_models.analyze_generation_text(
            "Title: A",
            generated_tokens=3,
            prompt_tokens=5,
            prompt="one two three four five six seven",
            prompt_text_tokens=7,
        )
        result = check_models.PerformanceResult(
            model_name="org/m", success=True, generation=None, quality_analysis=analysis
        )
        fact = check_models._prompt_composition_fact(result)
        assert fact is not None
        assert fact.startswith("unavailable")
        assert "tokenizer count 7 rejected as inconsistent with total 5" in fact


_STEP_STYLE_ANSWER = (
    "Title:\nTwo cats sleeping on a pink blanket\nDescription:\nTwo tabby cats are lying on a "
    "bright pink blanket on a red sofa; both appear to be asleep near two remote controls.\n"
    "Keywords:\ncats, sleeping, pink blanket, red sofa, tabby cats, remote controls, pets\n"
)


def test_duplicated_answer_detector_returns_the_separator_between_verbatim_copies() -> None:
    """Two whitespace-normalised copies of one answer are reported with what sat between."""
    detect = check_models._detect_duplicated_answer
    assert detect(f"{_STEP_STYLE_ANSWER}</think>\n{_STEP_STYLE_ANSWER}") == "</think>"
    assert detect(f"{_STEP_STYLE_ANSWER}\n\n{_STEP_STYLE_ANSWER}") == ""
    # Second copy differs by one word: not a duplicate.
    assert (
        detect(f"{_STEP_STYLE_ANSWER}</think>\n{_STEP_STYLE_ANSWER.replace('pets', 'cat')}") is None
    )
    # Too short to be a duplicated *answer*; a repeated sentence in prose is not flagged.
    assert detect("The cat sat. The cat sat.") is None
    # A long separator is not a duplicate straddling a marker.
    assert detect(f"{_STEP_STYLE_ANSWER}{'x' * 200}{_STEP_STYLE_ANSWER}") is None


def test_duplicated_answer_becomes_an_unusable_observation_with_its_separator() -> None:
    """Step's leaked </think> case: the observation names the marker and keeps the first copy."""
    analysis = check_models.analyze_generation_text(
        f"{_STEP_STYLE_ANSWER}</think>\n{_STEP_STYLE_ANSWER}",
        generated_tokens=236,
        assessment_profile="metadata",
    )
    assert analysis.duplicated_answer_separator == "</think>"
    assert analysis.missing_sections == []
    observations = check_models._quality_observations(
        text=f"{_STEP_STYLE_ANSWER}</think>\n{_STEP_STYLE_ANSWER}", analysis=analysis
    )
    assert "final_answer_duplicated" in observations
    assert "unexpected_special_token" in observations
    assert check_models._completed_assessment(observations).usability == "unusable"
    label = check_models._human_observation_labels(
        ("final_answer_duplicated",), details={"duplicated_answer_separator": "</think>"}
    )
    assert "Final answer emitted twice, around </think>" in label
    assert "answer emitted twice" in check_models._gallery_observation_labels(observations)


def test_duplicated_answer_is_not_flagged_for_a_removed_thinking_draft_or_repetition() -> None:
    """A draft inside a complete <think> block is reasoning, and looping stays repetition."""
    drafted = check_models.analyze_generation_text(
        f"<think>{_STEP_STYLE_ANSWER}</think>\n{_STEP_STYLE_ANSWER}",
        generated_tokens=236,
        assessment_profile="metadata",
    )
    assert drafted.duplicated_answer_separator is None
    looping = check_models.analyze_generation_text(
        "keyword, boathouse, pond, " * 80, generated_tokens=400, assessment_profile="metadata"
    )
    assert looping.is_repetitive is True
    assert looping.duplicated_answer_separator is None
