"""Tests for Markdown formatting utilities."""

import re
from dataclasses import dataclass
from pathlib import Path

import check_models


def test_escape_markdown_in_text_pipes() -> None:
    """Should escape pipe characters."""
    result = check_models.MARKDOWN_ESCAPER.escape("a|b|c")
    assert result == "a\\|b\\|c"


def test_escape_markdown_in_text_single_pipe() -> None:
    """Should escape single pipe."""
    result = check_models.MARKDOWN_ESCAPER.escape("before|after")
    assert result == "before\\|after"


def test_escape_markdown_in_text_no_pipes() -> None:
    """Should leave text without pipes unchanged."""
    text = "normal text without pipes"
    result = check_models.MARKDOWN_ESCAPER.escape(text)
    assert result == text


def test_escape_markdown_in_text_empty() -> None:
    """Should handle empty string."""
    result = check_models.MARKDOWN_ESCAPER.escape("")
    assert result == ""


def test_escape_markdown_in_text_only_pipes() -> None:
    """Should escape text with only pipes."""
    result = check_models.MARKDOWN_ESCAPER.escape("|||")
    assert result == "\\|\\|\\|"


def test_escape_markdown_in_text_mixed_content() -> None:
    """Should escape pipes in mixed content."""
    result = check_models.MARKDOWN_ESCAPER.escape("model|size|speed")
    assert result == "model\\|size\\|speed"


def test_escape_markdown_in_text_whitespace() -> None:
    """Should preserve whitespace around escaped pipes."""
    result = check_models.MARKDOWN_ESCAPER.escape("a | b | c")
    assert result == "a \\| b \\| c"


def test_table_escapers_preserve_their_whitespace_policies() -> None:
    """Regular tables normalize whitespace while diagnostics retain it."""
    text = "alpha  \n\n beta|gamma"

    assert check_models.MARKDOWN_ESCAPER.escape(text) == "alpha <br><br>beta\\|gamma"
    assert check_models.DIAGNOSTICS_ESCAPER.escape(text) == "alpha  <br><br> beta\\|gamma"


def test_complete_diagnostics_evidence_uses_a_non_truncating_safe_fence() -> None:
    """Embedded fences must not shorten complete traceback or output evidence."""
    evidence = "TRACE-BEGIN\n```text\ninner fence\n```\nTRACE-END"
    lines: list[str] = []

    check_models._append_markdown_code_block(lines, evidence, language="text")

    rendered = "\n".join(lines)
    assert evidence in rendered
    assert "TRACE-BEGIN" in rendered
    assert "TRACE-END" in rendered
    assert "truncated" not in rendered.casefold()


def test_shared_report_blocks_render_links_and_safe_model_output() -> None:
    """Shared reports should link internally and retain readable, inert model text."""
    captured = "## Heading\n\n- first\n- second\n\n@mlx-user <script>bad()</script>"
    blocks: tuple[check_models.ReportBlock, ...] = (
        check_models.ReportTable(
            headers=("Model",),
            rows=((check_models.ReportLink("org/model", "diagnostic-org-model"),),),
        ),
        check_models.ReportModelOutput(captured),
    )

    markdown = "\n".join(check_models.render_report_markdown(blocks))
    html_output = "\n".join(check_models.render_report_html(blocks))

    assert "[org/model](#diagnostic-org-model)" in markdown
    assert '<pre class="model-output-readable">' in markdown
    assert "## Heading\n\n- first\n- second" in markdown
    assert "@mlx-user" in markdown
    assert "&lt;script&gt;bad()&lt;/script&gt;" in markdown
    assert "<summary>Exact raw output</summary>" in markdown
    assert captured in markdown
    assert '<a href="#diagnostic-org-model">org/model</a>' in html_output
    assert "&lt;script&gt;bad()&lt;/script&gt;" in html_output


def test_model_output_raw_fence_preserves_difficult_text_exactly_once() -> None:
    """The exact view must preserve whitespace and outgrow nested backtick fences."""
    captured = "prefix\tvalue  \n````text\n`nested`\n````\ntrailing "

    markdown = "\n".join(
        check_models.render_report_markdown((check_models.ReportModelOutput(captured),))
    )

    assert markdown.count(captured) == 1
    assert "`````text\n" + captured + "\n`````" in markdown


# ── Bare URL wrapping (MD034) tests ────────────────────────────────────────

_BARE_URL_RE = re.compile(r"(?<![<(])https?://")
"""Matches a bare URL not already wrapped in < > or ( )."""


@dataclass
class _GalleryGeneration:
    text: str | None = "output"
    prompt_tokens: int | None = 10
    generation_tokens: int | None = 5
    prompt_tps: float | None = 100.0
    generation_tps: float | None = 50.0


def _gallery_lines_for(result: check_models.PerformanceResult) -> str:
    """Return joined gallery markdown for a single result."""
    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
    )
    return "\n".join(check_models._generate_model_gallery_section(context))


def test_gallery_evidence_block_keeps_raw_timing_metrics() -> None:
    """Per-model evidence should retain raw timing even for short samples."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(
            prompt_tokens=1624,
            generation_tokens=9,
            prompt_tps=1551.0,
            generation_tps=5.51,
        ),
        success=True,
        model_load_time=3.29,
        generation_time=1.60,
        total_time=5.14,
    )

    md = _gallery_lines_for(result)

    assert "*Generation time:* 1.60s" in md
    assert "*Generation throughput (raw):* 5.51 tok/s" in md
    assert "<summary>Complete evidence: test/model</summary>" in md


def test_gallery_evidence_block_marks_missing_metrics() -> None:
    """Missing facts should remain explicit in the complete evidence block."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(
            prompt_tokens=None,
            generation_tokens=80,
            prompt_tps=None,
            generation_tps=29.7,
        ),
        success=True,
        model_load_time=None,
        generation_time=10.90,
        total_time=14.51,
    )

    md = _gallery_lines_for(result)

    assert "*Model load time:* -" in md
    assert "*Generation throughput (raw):* 29.7 tok/s" in md
    assert "<summary>Complete evidence: test/model</summary>" in md


def test_gallery_output_uses_expandable_fenced_evidence() -> None:
    """Plain output renders once as readable text without a redundant raw fence."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(text="alpha\n\nbeta"),
        success=True,
        model_load_time=1.0,
        generation_time=2.0,
        total_time=3.0,
    )

    md = _gallery_lines_for(result)

    assert "<summary>Complete evidence: test/model</summary>" in md
    assert '<pre class="model-output-readable">\nalpha\n\nbeta\n</pre>' in md
    # The readable view is byte-identical to the raw text here, so no
    # collapsed raw fence should be emitted.
    assert "```text\nalpha\n\nbeta\n```" not in md


def test_gallery_output_keeps_raw_fence_when_readable_view_differs() -> None:
    """Trailing whitespace or escaped markup must retain the exact raw fence."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(text="alpha  \n@user `tick`"),
        success=True,
        model_load_time=1.0,
        generation_time=2.0,
        total_time=3.0,
    )

    md = _gallery_lines_for(result)

    assert '<pre class="model-output-readable">' in md
    assert "```text\nalpha  \n@user `tick`\n```" in md


def test_gallery_anchor_and_heading_are_separated_by_blank_line() -> None:
    """Gallery anchors should not sit directly above headings."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(text="alpha"),
        success=True,
        model_load_time=1.0,
        generation_time=2.0,
        total_time=3.0,
    )

    md = _gallery_lines_for(result)

    assert '<a id="model-test-model"></a>\n\n### test/model' in md


def test_gallery_blockquote_escapes_full_multi_underscore_runs() -> None:
    """Wrapped blockquotes should escape full underscore runs without leftovers."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "_____ is _____")

    md = "\n".join(parts)
    assert r"\_\_\_\_\_ is \_\_\_\_\_" in md
    assert r"\_\_\_\__ is" not in md


def test_markdown_code_block_preserves_tabs_exactly() -> None:
    """Fenced evidence must retain hard tabs from the captured text."""
    parts: list[str] = []

    check_models._append_markdown_code_block(parts, "left\tright")

    md = "\n".join(parts)
    assert "left\tright" in md
    assert "left    right" not in md


def test_gallery_error_block_does_not_emit_extra_blank_lines_before_separator() -> None:
    """Error entries should not produce MD012-triggering triple blank lines."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="Model Error",
        error_message="generation failed",
        error_traceback="Traceback (most recent call last):\nValueError: boom",
    )

    md = _gallery_lines_for(result)

    assert "<summary>Full Traceback (click to expand)</summary>\n\n\n```python" not in md
    assert "</details>\n\n\n---" not in md


def test_multiline_metadata_renders_as_single_list_item() -> None:
    """Multiline metadata values should stay within the same list item."""
    parts: list[str] = []

    check_models._append_markdown_image_metadata_section(
        parts,
        {
            "description": "First line\nSecond line\n\nThird paragraph.",
        },
    )

    md = "\n".join(parts)
    assert "- *Description:* First line" in md
    assert "\n\n    Second line" in md
    assert "\n\n    Third paragraph." in md


def test_wrapped_blockquote_neutralizes_leading_markdown_syntax() -> None:
    """Wrapped blockquote lines should keep leading Markdown control syntax readable."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(
        parts,
        "# heading\n2. numbered\n- bullet\n[!NOTE] alert",
    )

    md = "\n".join(parts)
    assert "> &#35; heading" in md
    assert "> 2&#46; numbered" in md
    assert "> &#45; bullet" in md
    assert "> &#91;!NOTE] alert" in md


def test_wrapped_blockquote_neutralizes_lone_ordered_list_markers() -> None:
    """Wrapped blockquote lines should keep lone ordered markers out of list parsing."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "11)\n1.\n1)")

    lines = "\n".join(parts).splitlines()
    assert "> 11&#41;" in lines
    assert "> 1&#46;" in lines
    assert "> 1&#41;" in lines
    assert "> 11)" not in lines
    assert "> 1." not in lines
    assert "> 1)" not in lines


def test_wrapped_blockquote_neutralizes_inline_asterisk_emphasis() -> None:
    """Wrapped blockquote lines should render raw asterisk emphasis literally."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "*italic*\n**bold**")

    md = "\n".join(parts)
    assert "> &#42;italic&#42;" in md
    assert "> &#42;&#42;bold&#42;&#42;" in md
    assert "> *italic*" not in md
    assert "> **bold**" not in md


def test_wrapped_blockquote_neutralizes_setext_heading_underline() -> None:
    """Wrapped blockquote lines should not emit setext headings from raw model output."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "Title\n------\nKeywords\n======")

    md = "\n".join(parts)
    assert "> Title" in md
    assert "> &#45;-----" in md
    assert "> Keywords" in md
    assert "> &#61;=====" in md


def test_wrapped_blockquote_neutralizes_label_only_lines_and_lone_markers() -> None:
    """Wrapped blockquotes should keep label lines and stray markers out of heading parsing."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(
        parts,
        "Description:\n- A large white butterfly\n\n**Title:**\n- Concrete and factual.\n-",
    )

    md = "\n".join(parts)
    assert "> &#8203;Description:" in md
    assert "> &#45; A large white butterfly" in md
    assert "> &#8203;&#42;&#42;Title:&#42;&#42;" in md
    assert "> &#45; Concrete and factual." in md
    assert "> &#45;" in md
    assert "> Description:" not in md
    assert "> &#42;&#42;Title:&#42;&#42;" not in md
    assert "> -" not in md


def test_gallery_uses_short_observation_labels_without_review_prose(tmp_path: Path) -> None:
    """Gallery chooser should project cached observation codes as short labels."""
    prompt = (
        "Analyze this image for cataloguing metadata.\n"
        "Return exactly these three sections, and nothing else:\n"
        "Title: 5-10 words.\nDescription: 1-2 factual sentences.\nKeywords: 10-18 terms."
    )
    text = (
        "Title: Brick storefront with outdoor seating\n"
        "Description: A brick storefront has outdoor seating beside a sidewalk.\n"
        "Keywords: brick storefront, sidewalk, brick storefront,"
    )
    analysis = check_models.analyze_generation_text(
        text,
        generated_tokens=60,
        requested_max_tokens=60,
        assessment_profile="metadata",
        prompt=prompt,
    )
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=_GalleryGeneration(
            text=text,
            prompt_tokens=320,
            generation_tokens=60,
        ),
        success=True,
        model_load_time=1.0,
        generation_time=2.0,
        total_time=3.0,
        quality_analysis=analysis,
        assessment_profile="metadata",
        requested_max_tokens=60,
    )

    out = tmp_path / "gallery.md"
    context = check_models._build_report_render_context(
        results=[result],
        prompt=prompt,
        system_info={},
    )
    check_models.generate_markdown_gallery_report(
        results=[result],
        filename=out,
        prompt=prompt,
        report_context=context,
    )
    md = out.read_text(encoding="utf-8")

    assert "*Why:*" not in md
    assert "*Next action:*" not in md
    # Chooser uses short selector glosses; complete evidence keeps maintainer labels.
    assert "cut off at token limit" in md
    assert "duplicate keywords" in md
    assert "Prefill/first s" in md
    assert "*Observations:* Response appears cut off at the token limit" in md
    # Wrapped bullet lines may break inside the label; compare space-normalized.
    normalized = " ".join(md.split())
    assert "Duplicate keywords: brick storefront" in normalized
    # The in-range title count must not be presented as a violation.
    assert "Title has 5 words" not in normalized
    assert "Keyword count violation" not in md


def test_wrapped_blockquote_strips_trailing_nonbreaking_spaces() -> None:
    """Wrapped blockquote lines should not preserve trailing NBSP or single spaces."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "alpha\u00a0\nbeta ")

    md = "\n".join(parts)
    assert "> alpha\u00a0" not in md
    assert "> beta " not in md
    assert "> alpha" in md
    assert "> beta" in md


def test_normalize_markdown_trailing_spaces_strips_nonbreaking_spaces() -> None:
    """Markdown trailing-space normalization should strip NBSP endings."""
    md = "alpha\u00a0\nbeta  \ngamma "

    normalized = check_models.normalize_markdown_trailing_spaces(md)

    assert normalized.splitlines() == ["alpha", "beta  ", "gamma"]


def test_normalize_markdown_trailing_spaces_strips_trailing_bom_and_zero_width() -> None:
    """Markdown trailing-space normalization should strip BOM and zero-width endings."""
    md = "alpha\ufeff\nbeta\u200b\ngamma\u2060\ndelta  "

    normalized = check_models.normalize_markdown_trailing_spaces(md)

    assert normalized.splitlines() == ["alpha", "beta", "gamma", "delta  "]


def test_normalize_markdown_trailing_spaces_preserves_fenced_output_exactly() -> None:
    """Generated output in a code fence must retain trailing spaces and tabs."""
    md = "outside \n```text\nfirst  \nsecond \t\n```\nafter\u00a0"

    normalized = check_models.normalize_markdown_trailing_spaces(md)

    assert normalized.splitlines() == [
        "outside",
        "```text",
        "first  ",
        "second \t",
        "```",
        "after",
    ]


def test_wrapped_blockquote_preserves_plain_bracket_text() -> None:
    """Wrapped blockquote lines should leave ordinary bracket text readable."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "decade_data[decade]['count'] += 1")

    md = "\n".join(parts)
    assert "> decade_data[decade]['count'] += 1" in md


def test_wrapped_blockquote_disables_reversed_link_lint_for_code_like_text() -> None:
    """Wrapped blockquotes should suppress MD011 for model text that looks like code."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(
        parts,
        "df.groupby('MarketingStrategy')['EngagementLevel'].mean()",
    )

    md = "\n".join(parts)
    assert "<!-- markdownlint-disable MD011 MD028 MD037 MD045 -->" in md
    assert "> df.groupby('MarketingStrategy')['EngagementLevel'].mean()" in md


def test_wrapped_blockquote_normalizes_wrapped_leading_spaces() -> None:
    """Wrapped continuation lines should not emit multiple spaces after '>'."""
    parts: list[str] = []

    check_models._append_markdown_wrapped_blockquote(parts, "alpha beta gamma", width=6)

    md = "\n".join(parts)
    assert ">  beta" not in md
    assert ">  gamma" not in md
    assert "> beta" in md
    assert "> gamma" in md


def test_bare_url_in_long_error_is_wrapped() -> None:
    """Error messages with bare URLs should get <angle brackets> in markdown."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="No Chat Template",
        error_message=(
            "Cannot use chat template because tokenizer.chat_template is not set. "
            "See https://huggingface.co/docs/transformers/main/en/chat_templating"
        ),
    )
    md = _gallery_lines_for(result)
    # The URL must be wrapped in angle brackets
    assert "<https://huggingface.co/docs/transformers/main/en/chat_templating>" in md
    # No bare URL should remain
    assert not _BARE_URL_RE.search(md), f"Bare URL found in:\n{md}"


def test_bare_url_in_short_error_is_wrapped() -> None:
    """Even short inline errors with URLs should be wrapped."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="Error",
        error_message="See https://example.com/help",
    )
    md = _gallery_lines_for(result)
    assert "<https://example.com/help>" in md
    assert not _BARE_URL_RE.search(md)


def test_already_wrapped_url_not_double_wrapped() -> None:
    """URLs already in angle brackets should not be double-wrapped."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="Error",
        error_message="See <https://example.com/help> for details",
    )
    md = _gallery_lines_for(result)
    assert "<https://example.com/help>" in md
    assert "<<https://" not in md


def test_error_without_url_unchanged() -> None:
    """Error messages without URLs should be unaffected."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="OOM",
        error_message="Out of memory during generation",
    )
    md = _gallery_lines_for(result)
    assert "Out of memory during generation" in md


def test_error_text_escapes_underscore_emphasis_markers() -> None:
    """Error prose should escape underscores to avoid unintended strong emphasis."""
    result = check_models.PerformanceResult(
        model_name="test/model",
        generation=None,
        success=False,
        error_stage="API Mismatch",
        error_message="LanguageModel.__call__() got an unexpected keyword argument",
    )
    md = _gallery_lines_for(result)
    assert "LanguageModel.\\_\\_call\\_\\_() got an unexpected keyword" in md
    assert "argument" in md


def test_formatter_owned_markdown_emphasis_uses_repo_style() -> None:
    """Generated labels should satisfy the repository's asterisk emphasis rule."""
    assert check_models._markdown_emphasis("Execution:") == "*Execution:*"


def test_append_markdown_section_honours_explicit_heading_and_verbatim_lines() -> None:
    """Explicit ``###`` titles set the level; structural lines pass through unwrapped."""
    parts: list[str] = []
    long_prose = "word " * 30
    check_models._append_markdown_section(
        parts,
        title="### Nested title",
        body_lines=[
            long_prose.strip(),
            "",
            "- bullet stays",
            "| a | b |",
            "1. numbered",
            "```",
            "code",
            "```",
        ],
    )
    text = "\n".join(parts)

    assert "### Nested title" in text
    assert "- bullet stays" in text
    assert "| a | b |" in text
    assert "1. numbered" in text
    assert all(len(line) <= 80 for line in parts if line.startswith("word"))
    assert parts[-1] == ""


def test_append_markdown_section_defaults_to_level_two_without_body() -> None:
    parts: list[str] = []
    check_models._append_markdown_section(parts, title="Plain title")
    assert "## Plain title" in "\n".join(parts)


def test_report_text_escaping_keeps_bare_urls_as_autolinks() -> None:
    """A URL in a key/value row must render as <url>, not HTML-escaped brackets (MD034)."""
    url = "https://raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image.jpg"
    escaped = check_models._escape_report_markdown_text(f"see {url} then <b>")
    assert escaped == f"see <{url}> then &lt;b&gt;"
    assert "&lt;https" not in escaped
    assert "check_models" in escaped  # underscores inside the URL stay intact

    lines = check_models.render_report_markdown(
        (check_models.ReportKeyValues((("Published preview", url),)),)
    )
    assert lines[0] == f"- *Published preview:* <{url}>"
