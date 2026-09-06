"""Tests for metrics mode selection output paths."""

from __future__ import annotations

import argparse
import io
import json
import logging
import time
from contextlib import ExitStack
from typing import TYPE_CHECKING, Literal
from unittest.mock import patch

import pytest
from rich.console import Console

import check_models
from check_models import (
    FileSafeFormatter,
    GenerationQualityAnalysis,
    PerformanceResult,
    RuntimeDiagnostics,
    StyleAwareRichHandler,
    finalize_execution,
    log_summary,
    print_model_result,
)

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from pathlib import Path

    from rich.panel import Panel

type ExpectedObservationCode = Literal[
    "empty_output",
    "minimal_output",
    "repeated_output",
    "missing_requested_sections",
    "token_cap_truncation",
    "prompt_instruction_echo",
    "unexpected_special_token",
    "thinking_trace_present",
    "thinking_trace_incomplete",
    "no_keyword_overlap",
]


class _StubGeneration:
    """Lightweight object matching attributes used by print_model_result."""

    prompt_tokens: int | None
    prompt_tps: float | None
    generation_tokens: int | None
    generation_tps: float | None
    peak_memory: float | None
    active_memory: float | None
    cache_memory: float | None
    time: float | None
    text: str | None

    def __init__(
        self,
        *,
        prompt_tokens: int = 10,
        prompt_tps: float = 100.0,
        generation_tokens: int = 20,
        generation_tps: float = 50.0,
        peak_memory: float = 0.25,
        text: str = "hello",
    ) -> None:
        self.prompt_tokens = prompt_tokens
        self.prompt_tps = prompt_tps
        self.generation_tokens = generation_tokens
        self.generation_tps = generation_tps
        self.peak_memory = peak_memory
        self.active_memory = None
        self.cache_memory = None
        self.time = 1.0
        self.text = text


def _build_perf() -> PerformanceResult:
    return PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )


_FINALIZE_REPORT_PATCHES = (
    "check_models.print_cli_section",
    "check_models.print_version_info",
    "check_models.generate_html_report",
    "check_models.generate_markdown_gallery_report",
    "check_models.save_jsonl_report",
)

_EXPECTED_REPORT_ARTIFACT_LOG_LABELS = (
    "Output Index:",
    "HTML Report:",
    "Gallery Report:",
    "Diagnostics:",
    "JSONL Report:",
)


def _finalize_history_stub() -> dict[str, object]:
    return {
        "_type": "run",
        "timestamp": "2026-02-13 00:00:00",
        "model_results": {},
    }


def _run_finalize_with_report_patches(
    *,
    args: argparse.Namespace,
    results: list[PerformanceResult],
    overall_start_time: float,
) -> None:
    """Run finalization with report writers patched out for path/log assertions."""
    with ExitStack() as stack:
        for patch_target in _FINALIZE_REPORT_PATCHES:
            stack.enter_context(patch(patch_target))
        stack.enter_context(patch("check_models.get_system_characteristics", return_value={}))
        stack.enter_context(
            patch("check_models.append_history_record", return_value=_finalize_history_stub())
        )
        stack.enter_context(patch("check_models.generate_diagnostics_report", return_value=False))
        stack.enter_context(
            patch("check_models.generate_run_issue_summary_report", return_value=None)
        )
        finalize_execution(
            args=args,
            results=results,
            library_versions={"mlx": "0.0.0", "mlx-vlm": "0.0.0"},
            overall_start_time=overall_start_time,
            prompt="test prompt",
            image_path=None,
            metadata=None,
        )


def _assert_logged_paths(messages: list[str], *paths: Path) -> None:
    for path in paths:
        assert any(str(path.resolve()) in message for message in messages)


def _message_index(messages: list[str], label: str) -> int:
    return next(index for index, message in enumerate(messages) if label in message)


def _assert_report_artifact_log_order(messages: list[str]) -> None:
    report_start = _message_index(messages, "Reports successfully generated:")
    report_messages = messages[report_start:]
    positions = [
        _message_index(report_messages, label) for label in _EXPECTED_REPORT_ARTIFACT_LOG_LABELS
    ]
    assert positions == sorted(positions)


def test_console_handler_keeps_repeated_timestamps_visible() -> None:
    """Console logs should timestamp every record, including same-second records."""
    stream = io.StringIO()
    console = Console(
        file=stream,
        width=100,
        no_color=True,
        force_terminal=False,
        markup=False,
        highlight=False,
    )
    with patch.object(check_models, "_make_rich_console", return_value=console):
        handler = check_models._make_console_log_handler(
            level=logging.INFO,
            verbose=False,
            width=100,
        )

    test_logger = logging.getLogger("check-models-rich-timestamp-test")
    old_handlers = test_logger.handlers[:]
    old_level = test_logger.level
    old_propagate = test_logger.propagate
    try:
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)
        test_logger.propagate = False
        test_logger.info("first")
        test_logger.info("second")
    finally:
        test_logger.handlers[:] = old_handlers
        test_logger.setLevel(old_level)
        test_logger.propagate = old_propagate

    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("[")
    assert lines[1].startswith("[")
    assert "first" in lines[0]
    assert "second" in lines[1]


def test_console_handler_hides_file_only_records() -> None:
    """Console handler should suppress records tagged for the file log only."""
    stream = io.StringIO()
    console = Console(
        file=stream,
        width=100,
        no_color=True,
        force_terminal=False,
        markup=False,
        highlight=False,
    )
    with patch.object(check_models, "_make_rich_console", return_value=console):
        handler = check_models._make_console_log_handler(
            level=logging.DEBUG,
            verbose=True,
            width=100,
        )

    test_logger = logging.getLogger("check-models-file-only-filter-test")
    old_handlers = test_logger.handlers[:]
    old_level = test_logger.level
    old_propagate = test_logger.propagate
    try:
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = False
        test_logger.debug("file-only message", extra={"log_destination": "file"})
        test_logger.info("console message")
    finally:
        test_logger.handlers[:] = old_handlers
        test_logger.setLevel(old_level)
        test_logger.propagate = old_propagate

    output = stream.getvalue()
    assert "file-only message" not in output
    assert "console message" in output


def test_metrics_mode_compact_smoke(caplog: pytest.LogCaptureFixture) -> None:
    """Compact mode should emit Timing and Tokens lines."""
    caplog.set_level(logging.INFO)
    res = _build_perf()
    print_model_result(res, verbose=True)
    # New format uses "Timing:" (line 1) and "Tokens:" (line 2)
    timing_lines = [r.message for r in caplog.records if "Timing:" in r.message]
    assert timing_lines, "Expected Timing line in compact mode logs"


def test_metrics_mode_compact_shows_working_set_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Compact memory output should include the detected Metal denominator."""
    caplog.set_level(logging.INFO)
    res = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(peak_memory=1.0),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    with patch("check_models._get_recommended_working_set_bytes", return_value=2_000_000_000):
        print_model_result(res, verbose=True)

    messages = "\n".join(record.message for record in caplog.records)
    assert "1.0 GB (50% of 1.86 GB recommended working set)" in messages


def test_metrics_mode_verbose_does_not_repeat_generated_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verbose mode should keep streamed output out of the post-run summary block."""
    caplog.set_level(logging.INFO)
    res = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(text="Distinct streamed output", generation_tokens=5),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    print_model_result(res, verbose=True)

    messages = [record.message for record in caplog.records]
    assert not any("Generated Text:" in message for message in messages)
    assert not any("Distinct streamed output" in message for message in messages)
    assert any("Timing:" in message for message in messages)


def test_verbose_metrics_show_phase_timings_and_stop_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verbose always renders the detailed phase tree — no second flag needed."""
    caplog.set_level(logging.INFO)
    res = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.8,
        runtime_diagnostics=RuntimeDiagnostics(
            input_validation_time_s=0.05,
            model_load_time_s=0.5,
            prompt_prep_time_s=0.15,
            decode_time_s=1.0,
            cleanup_time_s=0.1,
            first_token_latency_s=0.3,
            stop_reason="timeout",
        ),
    )

    print_model_result(res, verbose=True)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Prompt prep:    0.15s" in messages
    assert "first token:    0.30s" in messages
    assert "Stop reason: timeout" in messages


def test_metrics_mode_detailed_smoke(caplog: pytest.LogCaptureFixture) -> None:
    """Detailed mode should emit token lines plus Performance Metrics header."""
    caplog.set_level(logging.INFO)
    res = _build_perf()
    print_model_result(res, verbose=True)
    # Detailed mode uses "Performance Metrics:" header and separate "Tokens:" section
    perf_lines = [r.message for r in caplog.records if "Performance Metrics:" in r.message]
    token_lines = [r.message for r in caplog.records if "Tokens:" in r.message]
    assert token_lines, "Expected token summary lines in detailed mode"
    assert perf_lines, "Expected Performance Metrics header in detailed mode"


def test_metrics_mode_detailed_shows_working_set_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Detailed peak-memory rows should include the same Metal context."""
    caplog.set_level(logging.INFO)
    res = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(peak_memory=1.0),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    with patch("check_models._get_recommended_working_set_bytes", return_value=2_000_000_000):
        print_model_result(res, verbose=True)

    messages = "\n".join(record.message for record in caplog.records)
    assert "1.0 GB (50% of 1.86 GB recommended working set)" in messages


def test_metrics_mode_detailed_logs_runtime_phase_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Detailed mode should surface extra runtime phases and stop reason."""
    caplog.set_level(logging.INFO)
    res = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.8,
        runtime_diagnostics=RuntimeDiagnostics(
            input_validation_time_s=0.05,
            model_load_time_s=0.5,
            prompt_prep_time_s=0.15,
            decode_time_s=1.0,
            cleanup_time_s=0.1,
            first_token_latency_s=0.3,
            stop_reason="completed",
        ),
    )

    print_model_result(res, verbose=True)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Validation:" in messages
    assert "Prompt prep:" in messages
    assert "Cleanup:" in messages
    assert "Upstream model prefill / first token:" in messages
    assert "Stop reason:" in messages


def test_print_model_result_non_verbose_labels_generated_text_preview(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-verbose preview mode should still label the emitted model output block."""
    caplog.set_level(logging.INFO)
    preview_text = (
        "- Keywords hint: St Pancras, clock tower, Victorian Gothic\n"
        "architecture, public square, urban space"
    )
    analysis = GenerationQualityAnalysis(
        is_repetitive=False,
        repeated_token=None,
        missing_sections=["title", "description", "keywords"],
    )
    result = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(text=preview_text, generation_tokens=32),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
        quality_analysis=analysis,
    )

    print_model_result(result, verbose=False)

    messages = [record.message for record in caplog.records]
    assert any("Labelled fields not detected:" in message for message in messages)
    label_index = next(i for i, message in enumerate(messages) if "Generated Text:" in message)
    output_index = next(
        i for i, message in enumerate(messages) if "- Keywords hint: St Pancras" in message
    )
    assert label_index < output_index


def test_log_summary_uses_model_load_time_for_fastest_load(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Fastest-load metric should use model_load_time (not legacy load_time attr)."""
    caplog.set_level(logging.INFO)
    results = [
        PerformanceResult(
            model_name="model/slow-load",
            generation=_StubGeneration(generation_tps=10.0, peak_memory=2.0, text="good output"),
            success=True,
            generation_time=1.0,
            model_load_time=3.0,
            total_time=4.0,
        ),
        PerformanceResult(
            model_name="model/fast-load",
            generation=_StubGeneration(generation_tps=9.0, peak_memory=2.2, text="good output"),
            success=True,
            generation_time=1.1,
            model_load_time=0.5,
            total_time=1.6,
        ),
    ]

    log_summary(results)

    assert any(
        "Fastest load: model/fast-load (0.50s)" in record.message for record in caplog.records
    )


def test_log_summary_emits_comparison_table_and_ascii_charts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Summary should include tabulated model comparison and compact metric charts."""
    caplog.set_level(logging.INFO)
    results = [
        PerformanceResult(
            model_name="org/model-a",
            generation=_StubGeneration(generation_tps=35.0, peak_memory=1.2, text="clean output"),
            success=True,
            generation_time=1.0,
            model_load_time=0.4,
            total_time=1.4,
        ),
        PerformanceResult(
            model_name="org/model-b",
            generation=_StubGeneration(generation_tps=20.0, peak_memory=1.5, text="clean output"),
            success=True,
            generation_time=1.3,
            model_load_time=0.7,
            total_time=2.0,
        ),
        PerformanceResult(
            model_name="org/model-c",
            generation=None,
            success=False,
            error_stage="Generation Error",
            error_message="timeout",
            generation_time=0.5,
            model_load_time=0.2,
            total_time=0.7,
        ),
    ]

    with patch.object(check_models, "_log_rich_table") as rich_table:
        log_summary(results)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Model Comparison (current run):" in messages
    assert any(
        call.kwargs["headers"]
        == (
            "#",
            "Model",
            "E/U",
            "Val",
            "Load",
            "Prep",
            "First",
            "Remain",
            "Clean",
            "Total",
            "TPS",
            "GB",
        )
        for call in rich_table.call_args_list
    )
    assert "execution C=completed" in messages
    assert "completed" in messages
    assert "usable" in messages
    assert "TPS comparison chart:" in messages
    assert "Efficiency chart (higher is faster overall):" in messages
    assert "Failure stage frequency:" in messages


def test_log_summary_contextualizes_comparison_and_average_peak_memory(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Summary memory values should use the same detected Metal denominator."""
    caplog.set_level(logging.INFO)
    results = [
        PerformanceResult(
            model_name="org/model-a",
            generation=_StubGeneration(generation_tps=35.0, peak_memory=1.2, text="clean"),
            success=True,
            generation_time=1.0,
            model_load_time=0.4,
            total_time=1.4,
        ),
        PerformanceResult(
            model_name="org/model-b",
            generation=_StubGeneration(generation_tps=20.0, peak_memory=1.5, text="clean"),
            success=True,
            generation_time=1.3,
            model_load_time=0.7,
            total_time=2.0,
        ),
    ]

    with patch("check_models._get_recommended_working_set_bytes", return_value=2_000_000_000):
        log_summary(results)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Recommended working set: 1.86 GB" in messages
    assert "67.5% of 1.86 GB recommended working set" in messages


def test_log_summary_single_model_omits_efficiency_chart(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Single-model runs should still show comparison table without cross-model efficiency chart."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/single-model",
        generation=_StubGeneration(generation_tps=15.0, peak_memory=1.1, text="good output"),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    log_summary([result])

    messages = "\n".join(record.message for record in caplog.records)
    assert "Model Comparison (current run):" in messages
    assert "TPS comparison chart:" in messages
    assert "Efficiency chart (higher is faster overall):" not in messages


def test_log_summary_comparison_table_is_one_row_per_model_at_realistic_width(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The persisted performance table should not fold cells into character rows."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/a-realistically-long-model-name-for-width-testing",
        generation=_StubGeneration(generation_tps=15.0, peak_memory=1.1, text="good output"),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
        runtime_diagnostics=RuntimeDiagnostics(
            input_validation_time_s=0.12,
            model_load_time_s=0.5,
            prompt_prep_time_s=0.03,
            decode_time_s=1.0,
            cleanup_time_s=0.04,
            first_token_latency_s=0.6,
        ),
    )

    with (
        patch("check_models.get_terminal_width", return_value=100),
        patch.object(check_models, "_log_rich_table") as rich_table,
    ):
        log_summary([result])

    comparison = next(
        call
        for call in rich_table.call_args_list
        if call.kwargs["headers"][0:3] == ("#", "Model", "E/U")
    )
    row = comparison.kwargs["rows"][0]
    assert "a-realistically-lo..." in row
    assert all(value in row for value in ("0.12", "0.50", "0.03", "0.60", "0.40", "0.04"))


def test_log_summary_comparison_table_keeps_long_total_on_one_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A three-digit duration must not fold its final digit onto another row."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/slow-model",
        generation=_StubGeneration(generation_tps=4.8, peak_memory=39.94, text="clean output"),
        success=True,
        generation_time=127.88,
        model_load_time=3.49,
        total_time=133.22,
    )

    with patch("check_models.get_terminal_width", return_value=120):
        log_summary([result])

    comparison_lines = [record.getMessage() for record in caplog.records]
    assert any("133.22" in line for line in comparison_lines)


def test_log_summary_reports_execution_and_mechanical_observations(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Run summaries should emit facts without semantic scorecards."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/caption-model",
        generation=_StubGeneration(
            generation_tps=42.0,
            peak_memory=1.2,
            text="Two cats resting on a bright pink couch.",
        ),
        success=True,
        generation_time=1.0,
        model_load_time=0.4,
        total_time=1.4,
    )

    log_summary([result])

    messages = "\n".join(record.message for record in caplog.records)
    assert "Execution outcomes: completed=1" in messages
    assert "Mechanical observations: none" in messages
    assert "Cataloging Utility Snapshot:" not in messages
    assert "Metadata baseline:" not in messages
    assert "Best description:" not in messages
    assert "Best keywording:" not in messages


def test_log_summary_uses_cached_axes_and_excludes_unusable_from_highlights(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Completed-unusable output must stay neutral and outside resource rankings."""
    caplog.set_level(logging.INFO)
    usable = PerformanceResult(
        model_name="org/usable",
        generation=_StubGeneration(
            text="A complete usable caption with enough detail.",
            generation_tokens=20,
            generation_tps=20.0,
            peak_memory=2.0,
        ),
        success=True,
        model_load_time=0.5,
        total_time=1.5,
    )
    caveated = PerformanceResult(
        model_name="org/caveated",
        generation=_StubGeneration(
            text="Brief reply",
            generation_tokens=20,
            generation_tps=30.0,
            peak_memory=1.5,
        ),
        success=True,
        model_load_time=0.4,
        total_time=1.2,
    )
    unusable = PerformanceResult(
        model_name="org/unusable",
        generation=_StubGeneration(
            text="",
            generation_tokens=0,
            generation_tps=999.0,
            peak_memory=0.1,
        ),
        success=True,
        model_load_time=0.1,
        total_time=0.2,
    )
    crashed = PerformanceResult(
        model_name="org/crashed",
        generation=None,
        success=False,
        error_message="boom",
    )
    indeterminate = PerformanceResult(
        model_name="org/indeterminate",
        generation=None,
        success=False,
        error_message="Server disconnected without sending a response.",
    )
    results = [usable, caveated, unusable, crashed, indeterminate]
    assessments = {
        "org/usable": check_models.ResultAssessment("completed", "usable", "none", ()),
        "org/caveated": check_models.ResultAssessment(
            "completed",
            "usable_with_caveats",
            "observation_needs_reproduction",
            ("minimal_output",),
        ),
        "org/unusable": check_models.ResultAssessment(
            "completed",
            "unusable",
            "observation_needs_reproduction",
            ("empty_output",),
        ),
        "org/crashed": check_models.ResultAssessment(
            "crashed", "not_evaluated", "actionable_failure", ()
        ),
        "org/indeterminate": check_models.ResultAssessment(
            "indeterminate", "not_evaluated", "none", ()
        ),
    }

    with patch.object(check_models, "_assess_result", side_effect=AssertionError):
        log_summary(results, assessments=assessments)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Execution outcomes: completed=3, crashed=1, indeterminate=1" in messages
    usability_summary = next(
        record.message
        for record in caplog.records
        if record.message.startswith("Usability outcomes:")
    )
    assert all(
        item in usability_summary
        for item in (
            "usable=1",
            "usable_with_caveats=1",
            "unusable=1",
            "not_evaluated=2",
        )
    )
    assert "Maintainer outcomes:" in messages
    # Time to complete the task ranks models; caveated (1.2 s) beats usable
    # (1.5 s) while the unusable row stays out of the highlights entirely.
    assert "Quickest completion: org/caveated (1.20s end-to-end)" in messages
    assert "org/unusable" not in next(m for m in messages.splitlines() if "Quickest" in m)
    assert "Average TPS" not in messages
    assert "tokens/GB" not in messages
    assert "Successful Models" not in messages
    assert "status=OK" not in messages
    assert "org/unusable" in messages
    assert "unusable" in messages


def test_log_summary_lists_every_observation_kind(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Observation summaries must not silently drop lower-frequency kinds."""
    caplog.set_level(logging.INFO)
    observations: tuple[ExpectedObservationCode, ...] = (
        "minimal_output",
        "missing_requested_sections",
        "prompt_instruction_echo",
        "repeated_output",
        "thinking_trace_incomplete",
        "thinking_trace_present",
        "token_cap_truncation",
    )
    results = [
        PerformanceResult(
            model_name=f"org/model-{index}",
            generation=_StubGeneration(text="complete output"),
            success=True,
        )
        for index, _observation in enumerate(observations)
    ]
    assessments = {
        result.model_name: check_models.ResultAssessment(
            "completed",
            "usable_with_caveats",
            "observation_needs_reproduction",
            (observation,),
        )
        for result, observation in zip(results, observations, strict=True)
    }

    log_summary(results, assessments=assessments)

    summary = next(
        record.message
        for record in caplog.records
        if record.message.startswith("Mechanical observations:")
    )
    assert all(f"{observation}=1" in summary for observation in observations)


def test_completed_model_summary_uses_actionability_ordered_tables(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    results = [
        PerformanceResult(
            model_name=model_name,
            generation=_StubGeneration(text="complete output"),
            success=True,
        )
        for model_name in (
            "org/usable",
            "org/z-caveat",
            "org/z-repeated",
            "org/a-missing",
            "org/a-caveat",
        )
    ]
    assessments = {
        "org/usable": check_models.ResultAssessment("completed", "usable", "none", ()),
        "org/z-caveat": check_models.ResultAssessment(
            "completed",
            "usable_with_caveats",
            "observation_needs_reproduction",
            ("minimal_output",),
        ),
        "org/z-repeated": check_models.ResultAssessment(
            "completed",
            "unusable",
            "observation_needs_reproduction",
            ("repeated_output",),
        ),
        "org/a-missing": check_models.ResultAssessment(
            "completed",
            "unusable",
            "observation_needs_reproduction",
            ("missing_requested_sections",),
        ),
        "org/a-caveat": check_models.ResultAssessment(
            "completed",
            "usable_with_caveats",
            "observation_needs_reproduction",
            ("minimal_output",),
        ),
    }

    with patch.object(check_models, "get_terminal_width", return_value=180):
        check_models._log_completed_models_list(results, assessments)

    messages = "\n".join(record.message for record in caplog.records)
    assert "Completed Models (5):" in messages
    assert messages.index("Major concerns (2):") < messages.index("Concerns detected (2):")
    assert messages.index("Concerns detected (2):") < messages.index("No concerns detected (1):")
    # Console summary uses short selector glosses in actionability order.
    assert messages.index("repeated text") < messages.index("labelled fields not detected")
    assert messages.index("org/z-repeated") < messages.index("org/a-missing")
    assert messages.index("org/a-caveat") < messages.index("org/z-caveat")
    assert "very short response" in messages
    assert "| usability=" not in messages
    assert "Maintainer" not in messages
    clean_group = messages[messages.index("No concerns detected (1):") :]
    assert "Observations" not in clean_group


def test_print_model_result_uses_neutral_cached_unusable_assessment(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A completed unusable result must not receive generic success styling or OK copy."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/unusable",
        generation=_StubGeneration(text="", generation_tokens=0),
        success=True,
    )
    assessment = check_models.ResultAssessment(
        "completed",
        "unusable",
        "observation_needs_reproduction",
        ("empty_output",),
    )

    print_model_result(result, assessment=assessment, verbose=False)

    summary_records = [
        record
        for record in caplog.records
        if "SUMMARY" in record.message or "maintainer=" in record.message
    ]
    summary = " ".join(record.message for record in summary_records)
    assert "execution=completed" in summary
    assert "usability=unusable" in summary
    assert "maintainer=observation_needs_reproduction" in summary
    assert "status=OK" not in summary
    assert all(
        getattr(record, "style_hint", None) != check_models.LogStyles.SUCCESS
        for record in summary_records
    )


def test_raw_log_keeps_unsanitized_operational_failure_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Publication sanitization must not rewrite the maximalist raw log."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="org/crashed",
        generation=None,
        success=False,
        error_message="failed at /Users/alice/project/model.py",
    )
    assessment = check_models.ResultAssessment("crashed", "not_evaluated", "actionable_failure", ())

    log_summary([result], assessments={result.model_name: assessment})

    assert "/Users/alice/project/model.py" in "\n".join(record.message for record in caplog.records)


def test_machine_summary_uses_observation_vocabulary() -> None:
    """Automation summaries should label mechanical facts without grading output."""
    result = PerformanceResult(
        model_name="org/caption-model",
        generation=_StubGeneration(),
        success=True,
    )

    assessment = check_models.ResultAssessment(
        "completed",
        "usable_with_caveats",
        "observation_needs_reproduction",
        ("repeated_output", "token_cap_truncation"),
    )
    parts = check_models._summary_parts(result, "caption-model", assessment)

    assert "observations=repeated_output+token_cap_truncation" in parts
    assert not any(part.startswith("quality=") for part in parts)


def test_metrics_legend_names_only_retained_mechanical_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI legend should not claim that the harness detects hallucinations."""
    panels: list[Panel] = []
    monkeypatch.setattr(
        check_models,
        "_log_rich_renderable",
        lambda panel, **_kwargs: panels.append(panel),
    )
    monkeypatch.setattr(check_models, "log_blank", lambda: None)

    check_models.log_metrics_legend()

    assert len(panels) == 1
    legend = str(panels[0].renderable)
    assert "repetitive output and token-cap truncation" in legend
    assert "hallucinated" not in legend


def test_log_summary_failure_uses_only_recorded_failure_facts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failure summaries must not infer an owner or likely cause."""
    caplog.set_level(logging.INFO)
    result = PerformanceResult(
        model_name="broken/model",
        generation=None,
        success=False,
        failure_phase="decode",
        error_stage="Model Error",
        error_code="MODEL_MLX_VLM_DECODE",
        error_message="generation failed",
        error_type="ValueError",
        root_error_module="builtins",
        error_package="mlx-vlm",
        error_traceback="Traceback (most recent call last):\nValueError: generation failed",
    )

    log_summary([result])

    messages = "\n".join(record.message for record in caplog.records)
    assert (
        "broken/model | phase=decode | stage=Model Error | module=builtins | "
        "package=mlx-vlm | code=MODEL_MLX_VLM_DECODE | traceback=available"
    ) in messages
    assert "module=builtins" in messages
    assert "error=ValueError: generation failed" in messages
    assert "traceback=available" in messages
    assert "owner≈" not in messages
    assert "likely=" not in messages
    assert "generation/integration path" not in messages
    assert "model runtime failure" not in messages


def test_print_model_result_failure_logs_actionable_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failure output should include package/type and traceback/captured-output sections."""
    caplog.set_level(logging.INFO)
    tb_lines = "\n".join(f"line{i}" for i in range(1, 10))
    result = PerformanceResult(
        model_name="broken/model",
        generation=None,
        success=False,
        error_stage="Model Error",
        error_message="Model loading failed",
        error_type="ValueError",
        error_package="mlx-vlm",
        error_traceback=tb_lines,
        captured_output_on_fail="stdout sample\nstderr sample",
    )

    print_model_result(result, verbose=True, run_index=1, total_runs=1)

    assert any("Error package: mlx-vlm" in record.message for record in caplog.records)
    assert any("Error type: ValueError" in record.message for record in caplog.records)
    assert any("Traceback tail:" in record.message for record in caplog.records)
    assert any("Captured output:" in record.message for record in caplog.records)


def test_file_safe_formatter_strips_ansi() -> None:
    """File formatter should remove ANSI escapes from persisted logs."""
    formatter = FileSafeFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="\x1b[91mred text\x1b[0m",
        args=(),
        exc_info=None,
    )

    assert formatter.format(record) == "red text"


def test_file_safe_formatter_uses_project_timestamp_shape() -> None:
    """File formatter should use stable second-resolution local timestamps."""
    formatter = FileSafeFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt=check_models.LOCAL_TIMESTAMP_FORMAT,
    )
    formatter.converter = time.gmtime
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="plain text",
        args=(),
        exc_info=None,
    )
    record.created = 0.0
    record.msecs = 321.0

    formatted = formatter.format(record)

    assert formatted in {
        "1970-01-01 00:00:00 GMT - INFO - plain text",
        "1970-01-01 00:00:00 UTC - INFO - plain text",
    }


def test_rich_debug_level_label_is_dim() -> None:
    """Only the DEBUG level label should render dim/gray."""
    handler = StyleAwareRichHandler(
        console=Console(file=io.StringIO(), force_terminal=True),
        show_level=True,
        show_time=False,
        show_path=False,
    )
    record = logging.LogRecord(
        name="check_models",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="debug details",
        args=(),
        exc_info=None,
    )

    level_text = handler.get_level_text(record)

    assert level_text.plain == "DEBUG   "
    assert level_text.spans
    assert str(level_text.spans[0].style) == "dim"


def test_finalize_execution_logs_configured_log_and_env_paths(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Final summary should report the output root's derived log/env paths."""
    caplog.set_level(logging.INFO)
    derived = check_models.ReportOutputPaths.from_root(tmp_path)
    derived.environment.write_text("env", encoding="utf-8")

    args = argparse.Namespace(
        output_dir=tmp_path,
        # This run "wrote" the env log; mere pre-existence no longer counts.
        environment_logged=True,
    )
    result = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    _run_finalize_with_report_patches(
        args=args,
        results=[result],
        overall_start_time=time.time() - 0.5,
    )

    messages = [record.message for record in caplog.records]
    _assert_logged_paths(
        messages,
        derived.log,
        derived.environment,
        derived.gallery_markdown,
        derived.diagnostics,
    )
    _assert_report_artifact_log_order(messages)


def test_finalize_execution_separates_each_model_result_block(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A model's metrics should end before the next model summary begins."""
    caplog.set_level(logging.INFO)
    args = argparse.Namespace(
        verbose=True,
        output_dir=tmp_path,
    )
    results = [
        PerformanceResult(
            model_name="dummy/first",
            generation=_StubGeneration(text="first result"),
            success=True,
        ),
        PerformanceResult(
            model_name="dummy/second",
            generation=_StubGeneration(text="second result"),
            success=True,
        ),
    ]

    _run_finalize_with_report_patches(
        args=args,
        results=results,
        overall_start_time=time.time() - 0.5,
    )

    messages = [record.message for record in caplog.records]
    first_summary = _message_index(messages, "[RUN 1/2] SUMMARY model=dummy/first")
    second_summary = _message_index(messages, "[RUN 2/2] SUMMARY model=dummy/second")
    first_timing = next(
        index
        for index, message in enumerate(messages[first_summary:second_summary], first_summary)
        if "Tokens:" in message
    )
    separators = [
        index
        for index, message in enumerate(messages[first_summary:second_summary], first_summary)
        if message and set(message) == {"─"}
    ]

    assert len(separators) == 1
    assert first_timing < separators[0] < second_summary


def test_report_generation_uses_single_artifact_plan(tmp_path: Path) -> None:
    """Report generation should expose one ordered artifact plan for jobs and logs."""
    args = argparse.Namespace(
        output_dir=tmp_path,
    )
    inputs = check_models.ReportGenerationInputs(
        results=[],
        library_versions={"mlx": "0.0.0"},
        prompt="prompt",
        metadata=None,
        overall_time=1.0,
        image_path=None,
        system_info={},
        report_context=check_models._build_report_render_context(results=[], prompt="prompt"),
        output_paths=check_models._resolve_report_output_paths(args),
        runtime_fingerprint={},
    )

    artifacts = check_models._build_report_artifacts(inputs)

    assert [artifact.key for artifact in artifacts] == [
        "output_index",
        "html",
        "markdown_gallery",
        "diagnostics",
        "jsonl",
        "log",
        "environment",
    ]
    assert [artifact.label.strip() for artifact in artifacts] == [
        "Output Index:",
        "HTML Report:",
        "Gallery Report:",
        "Diagnostics:",
        "JSONL Report:",
        "Log File:",
        "Environment:",
    ]
    assert all(artifact.path.is_absolute() for artifact in artifacts)
    # diagnostics runs via its dedicated runner; log/environment are produced
    # by the run itself; the jsonl job is supplied by the orchestrator from
    # the in-memory retained run.
    joblessly_produced = {"diagnostics", "log", "environment", "jsonl"}
    assert all(
        artifact.job is not None for artifact in artifacts if artifact.key not in joblessly_produced
    )
    assert all(artifact.job is None for artifact in artifacts if artifact.key in joblessly_produced)


@pytest.mark.parametrize("failing_renderer", ["html", "diagnostics"])
def test_canonical_jsonl_precedes_and_survives_optional_renderer_failure(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    failing_renderer: str,
) -> None:
    """Optional presentation failures must leave canonical JSONL valid and report partial."""
    caplog.set_level(logging.INFO)
    args = argparse.Namespace(
        output_dir=tmp_path,
    )
    result = PerformanceResult(
        model_name="org/model",
        generation=_StubGeneration(
            text="A complete response with enough captured evidence.",
            generation_tokens=20,
        ),
        success=True,
    )
    provenance: check_models.ModelProvenanceRecord = {
        "model": result.model_name,
        "requested_revision": None,
        "resolved_revision": "sha",
        "snapshot_path": "~/.cache/snapshots/sha",
    }
    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
        model_provenance={result.model_name: provenance},
    )
    paths = check_models._resolve_report_output_paths(args)
    for path in (
        paths.index,
        paths.html,
        paths.gallery_markdown,
        paths.jsonl,
        paths.diagnostics,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    inputs = check_models.ReportGenerationInputs(
        results=[result],
        library_versions={"mlx": "0.0.0"},
        prompt="Describe the image.",
        metadata=None,
        overall_time=1.0,
        image_path=None,
        system_info={},
        report_context=context,
        output_paths=paths,
        run_args=args,
        runtime_fingerprint={},
    )
    events: list[str] = []
    real_write_text = check_models._write_text_file

    def record_writes(path: Path, content: str, *, append: bool = False) -> None:
        # The retained run is staged beside its target and renamed into place.
        staged_jsonl = path.parent == paths.jsonl.parent and paths.jsonl.name in path.name
        if staged_jsonl and '"_type": "metadata"' in content:
            events.append("jsonl")
        real_write_text(path, content, append=append)

    def fail_renderer(*_args: object, **_kwargs: object) -> None:
        events.append(failing_renderer)
        message = f"synthetic {failing_renderer} failure"
        raise ValueError(message)

    monkeypatch.setattr(check_models, "_write_text_file", record_writes)
    monkeypatch.setattr(
        check_models,
        "generate_html_report" if failing_renderer == "html" else "generate_diagnostics_report",
        fail_renderer,
    )

    outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert events[0] == "jsonl"
    assert failing_renderer in events
    records = [json.loads(line) for line in paths.jsonl.read_text(encoding="utf-8").splitlines()]
    assert records[0]["_type"] == "metadata"
    assert records[1]["_type"] == "result"
    assert records[1]["model"] == result.model_name
    by_key = {outcome.key: outcome for outcome in outcomes}
    assert by_key["jsonl"].succeeded is True
    assert by_key[failing_renderer].succeeded is False
    messages = "\n".join(record.message for record in caplog.records)
    assert "Reports successfully generated" not in messages
    assert "Reports generated with 1 failure" in messages


def test_report_artifact_specs_are_the_metadata_source(tmp_path: Path) -> None:
    """Generated report path, run-json, and dashboard metadata should share specs."""
    args = argparse.Namespace(
        output_dir=tmp_path,
    )
    paths = check_models._resolve_report_output_paths(args)

    inputs = check_models.ReportGenerationInputs(
        results=[],
        library_versions={},
        prompt="p",
        metadata=None,
        overall_time=0.0,
        image_path=None,
        system_info={},
        report_context=check_models._build_report_render_context(results=[], prompt="p"),
        output_paths=paths,
    )
    artifacts = check_models._build_report_artifacts(inputs)

    assert tuple(artifact.key for artifact in artifacts) == (
        "output_index",
        "html",
        "markdown_gallery",
        "diagnostics",
        "jsonl",
        "log",
        "environment",
    )
    assert {artifact.public_key for artifact in artifacts} == {
        "output_index",
        "results_html",
        "model_gallery",
        "diagnostics",
        "results_jsonl",
        "log",
        "environment",
    }


def test_output_index_links_only_retained_artifacts(tmp_path: Path) -> None:
    """The navigation index must not reintroduce retired or conditional artifacts."""
    reports_dir = tmp_path / "reports"
    paths = check_models.ReportOutputPaths(
        index=tmp_path / "index.md",
        html=reports_dir / "results.html",
        gallery_markdown=reports_dir / "model_gallery.md",
        diagnostics=reports_dir / "diagnostics.md",
        jsonl=tmp_path / "results.jsonl",
        log=tmp_path / "check_models.log",
        environment=tmp_path / "environment.log",
    )

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        check_models.generate_output_index_report(
            paths.index,
            artifacts=check_models._build_report_artifacts(
                check_models.ReportGenerationInputs(
                    results=[],
                    library_versions={},
                    prompt="p",
                    metadata=None,
                    overall_time=0.0,
                    image_path=None,
                    system_info={},
                    report_context=check_models._build_report_render_context(
                        results=[], prompt="p"
                    ),
                    output_paths=paths,
                )
            ),
        )

    objective_lines = check_models._wrap_markdown_text(check_models._run_objective_statement(None))
    assert paths.index.read_text(encoding="utf-8").splitlines() == [
        "# Check Models Output Index",
        "",
        "Assessment: Legacy assessment; profile not recorded",
        "",
        *objective_lines,
        "",
        "- [results.html](reports/results.html)",
        "- [model_gallery.md](reports/model_gallery.md)",
        "- [diagnostics.md](reports/diagnostics.md)",
        "- [results.jsonl](results.jsonl)",
        "- [check_models.log](check_models.log)",
        "- [environment.log](environment.log)",
    ]


def test_finalize_execution_does_not_read_history_for_current_reports(tmp_path: Path) -> None:
    """Current report statuses must not depend on append-only history."""
    args = argparse.Namespace(
        output_dir=tmp_path,
    )
    result = PerformanceResult(
        model_name="dummy/model",
        generation=_StubGeneration(text="A complete response."),
        success=True,
    )
    expected = check_models._assess_result(result)

    with patch.object(
        check_models,
        "_load_history_run_records",
        side_effect=AssertionError("current reports must not read history"),
        create=True,
    ):
        _run_finalize_with_report_patches(
            args=args,
            results=[result],
            overall_start_time=time.time() - 0.5,
        )

    assert check_models._assess_result(result) == expected


def test_console_cap_note_is_neutral_without_degradation_evidence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A cap hit warns only when the assessment would also flag truncation."""
    clean_text = "Title: Two boats\n\nDescription: Two boats at sea.\n\nKeywords: boats, sea, sky."
    clean_cap = check_models.analyze_generation_text(
        clean_text,
        generated_tokens=500,
        requested_max_tokens=500,
    )
    assert clean_cap.likely_capped
    assert not clean_cap.token_cap_reasons

    generation = _StubGeneration(text=clean_text, generation_tokens=500)
    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        check_models._preview_generation(generation, analysis=clean_cap)

    assert "Output used the full requested token budget" in caplog.text
    assert "reached requested token limit" not in caplog.text

    degraded = check_models.analyze_generation_text(
        "boats boats boats boats boats boats boats boats boats boats boats boats",
        generated_tokens=500,
        requested_max_tokens=500,
    )
    assert degraded.likely_capped
    assert degraded.token_cap_reasons
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        check_models._preview_generation(
            _StubGeneration(text="boats boats", generation_tokens=500),
            analysis=degraded,
        )
    assert "reached requested token limit" in caplog.text


def test_preview_and_verbose_modes_log_the_same_quality_warnings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Changing verbosity must not hide actionable mechanical observations."""
    analysis = GenerationQualityAnalysis(
        is_repetitive=True,
        repeated_token="loop",  # noqa: S106 - generated-text fixture, not a credential
        missing_sections=["keywords"],
        thinking_trace_incomplete=True,
        likely_capped=True,
        token_cap_reasons=["repetition"],
        unexpected_special_tokens=["<bad>"],
    )
    generation = _StubGeneration(text="loop", generation_tokens=500)
    result = PerformanceResult(
        model_name="dummy/model",
        generation=generation,
        success=True,
    )
    expected = (
        "Repetitive: 'loop'",
        "Labelled fields not detected: keywords",
        "Expected thinking trace did not reach a final answer",
        "Output reached requested token limit (500 tokens)",
        "Unexpected special token wrappers: <bad>",
    )

    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        check_models._preview_generation(generation, analysis=analysis)
    preview_messages = "\n".join(record.message for record in caplog.records)
    caplog.clear()

    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        check_models._log_verbose_success_details(
            result,
            analysis=analysis,
        )
    verbose_messages = "\n".join(record.message for record in caplog.records)

    for message in expected:
        assert message in preview_messages
        assert message in verbose_messages


class TestSystemTelemetry:
    """System-pressure telemetry must aggregate per-probe and expose gaps."""

    def test_total_probe_failure_yields_zero_count_record(self) -> None:
        """All-None probes still produce a record so the gap is visible."""
        record = check_models._system_telemetry_record_from_probes(
            [(None, None), (None, None)], mode="snapshot"
        )

        assert record == {"mode": "snapshot", "cpu_samples": 0, "memory_samples": 0}
        status = check_models._telemetry_status_line(record)
        assert "thermal probe unavailable" in status
        assert "memory-pressure probe unavailable" in status

    def test_record_aggregates_min_max_and_per_probe_counts(self) -> None:
        """Aggregates keep the throttling floor, pressure ceiling, and counts."""
        record = check_models._system_telemetry_record_from_probes(
            [(100.0, 1), (62.0, 2), (100.0, None)],
            mode="continuous",
            interval_s=1.5,
        )

        assert record == {
            "mode": "continuous",
            "interval_s": 1.5,
            "cpu_samples": 3,
            "memory_samples": 2,
            "cpu_speed_limit_min_pct": 62.0,
            "cpu_throttled_samples": 1,
            "memory_pressure_level_max": 2,
            "memory_pressure_elevated_samples": 1,
        }

    def test_partial_probe_failure_stays_visible(self) -> None:
        """A missing probe is reported as unavailable, never as clean."""
        record = check_models._system_telemetry_record_from_probes(
            [(100.0, None), (100.0, None)], mode="snapshot"
        )

        assert record is not None
        assert record["cpu_samples"] == 2
        assert record["memory_samples"] == 0
        status = check_models._telemetry_status_line(record)
        assert "memory-pressure probe unavailable" in status
        assert "CPU speed limit min 100% over 2 sample(s)" in status
        assert "mode snapshot" in status

    def test_degradation_note_reports_throttle_and_pressure(self) -> None:
        """Throttled CPU and elevated pressure both appear in the note."""
        note = check_models._telemetry_degradation_note(
            {
                "mode": "continuous",
                "cpu_samples": 4,
                "cpu_speed_limit_min_pct": 62.0,
                "cpu_throttled_samples": 2,
                "memory_samples": 4,
                "memory_pressure_level_max": 4,
                "memory_pressure_elevated_samples": 1,
            }
        )

        assert note is not None
        assert "CPU speed limited to 62%" in note
        assert "critical" in note

    def test_degradation_note_none_when_clean(self) -> None:
        """An unthrottled, normal-pressure run produces no note."""
        note = check_models._telemetry_degradation_note(
            {
                "mode": "snapshot",
                "cpu_samples": 2,
                "cpu_speed_limit_min_pct": 100.0,
                "cpu_throttled_samples": 0,
                "memory_samples": 2,
                "memory_pressure_level_max": 1,
                "memory_pressure_elevated_samples": 0,
            }
        )

        assert note is None

    def test_sampler_snapshot_delegates_to_probe_aggregation(self) -> None:
        """The continuous sampler aggregates its probe list with its interval."""
        sampler = check_models._SystemTelemetrySampler(interval_s=1.5)
        sampler._probes.extend([(100.0, 1), (80.0, 2)])

        snapshot = sampler.snapshot()

        assert snapshot is not None
        assert snapshot["mode"] == "continuous"
        assert snapshot["interval_s"] == 1.5
        assert snapshot["cpu_speed_limit_min_pct"] == 80.0

    def test_thermal_sample_parses_pmset_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CPU_Speed_Limit is extracted from pmset -g therm output."""
        monkeypatch.setattr(
            check_models,
            "_run_macos_toolchain_command",
            lambda *_args, **_kwargs: "CPU_Speed_Limit \t= 62\nCPU_Available_CPUs \t= 14",
        )

        assert check_models._sample_thermal_cpu_speed_limit_pct() == 62.0

    def test_thermal_sample_treats_no_power_status_as_unthrottled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nominal Apple Silicon thermals report as an unthrottled 100%."""
        monkeypatch.setattr(
            check_models,
            "_run_macos_toolchain_command",
            lambda *_args, **_kwargs: (
                "Note: No thermal warning level has been recorded\n"
                "Note: No performance warning level has been recorded\n"
                "Note: No CPU power status has been recorded"
            ),
        )

        assert check_models._sample_thermal_cpu_speed_limit_pct() == 100.0

    def test_pressure_sample_rejects_non_numeric_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unexpected sysctl output degrades to None instead of raising."""
        monkeypatch.setattr(
            check_models,
            "_run_macos_toolchain_command",
            lambda *_args, **_kwargs: "not-a-number",
        )

        assert check_models._sample_memory_pressure_level() is None

    def test_jsonl_record_carries_system_telemetry(self) -> None:
        """Per-model telemetry lands in the results.jsonl record when present."""
        telemetry: check_models.SystemTelemetryRecord = {
            "mode": "snapshot",
            "cpu_samples": 2,
            "memory_samples": 2,
            "cpu_speed_limit_min_pct": 100.0,
            "cpu_throttled_samples": 0,
        }
        result = check_models.PerformanceResult(
            model_name="org/telemetry",
            generation=None,
            success=False,
            system_telemetry=telemetry,
        )
        assessment = check_models._assess_result(result)

        record = check_models._build_jsonl_result_record(
            result,
            assessment,
            requested_revision=None,
            model_provenance={
                "model": "org/telemetry",
                "requested_revision": None,
                "resolved_revision": "rev",
                "snapshot_path": None,
            },
        )

        assert record["system_telemetry"] == telemetry
