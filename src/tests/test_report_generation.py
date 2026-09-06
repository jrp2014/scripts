"""Tests for report generation edge cases (empty input, all-failed results)."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import html
import io
import json
import logging
import re
from argparse import Namespace
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast, get_args
from unittest.mock import patch

import pytest
from PIL import Image

import check_models
from check_models import (
    DiagnosticsArtifacts,
    GenerationQualityAnalysis,
    PerformanceResult,
    RuntimeDiagnostics,
    _build_report_render_context,
    _generate_github_issue_reports,
    generate_diagnostics_report,
    generate_html_report,
    generate_markdown_gallery_report,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

type ExpectedUpstreamBoundary = Literal["not_started", "load_started", "generation_started"]

THINKING_START_TOKEN = "<think>"
THINKING_END_TOKEN = "</think>"
EOS_END_TOKEN = "</s>"
EOS_OVERRIDE_TOKEN = "<override-eos>"
CUSTOM_THINKING_END_TOKEN = "</done>"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _MockGeneration:
    """Minimal stand-in for GenerationResult used by report generators."""

    text: str | None = "output"
    token: object | None = None
    logprobs: object | None = None
    prompt_tokens: int | None = 10
    generation_tokens: int | None = 5
    total_tokens: int | None = 15
    prompt_tps: float | None = 1200.0
    generation_tps: float | None = 80.0
    peak_memory: float | None = 4.5
    time: float | None = None
    active_memory: float | None = None
    cache_memory: float | None = None


@dataclass
class _VerboseGeneration:
    """GenerationResult-like stand-in with upstream debug fields."""

    text: str | None = "output"
    token: object | None = None
    logprobs: object | None = None
    prompt_tokens: int | None = 10
    generation_tokens: int | None = 5
    total_tokens: int | None = 15
    prompt_tps: float | None = 1200.0
    generation_tps: float | None = 80.0
    peak_memory: float | None = 4.5
    cached_tokens: int | None = 0
    finish_reason: str | None = "stop"
    diffusion_canvas_tokens: int | None = 0
    diffusion_denoising_steps: int | None = 0
    diffusion_work_tokens: int | None = 0
    diffusion_canvas_tps: float | None = 0.0
    diffusion_work_tps: float | None = 0.0
    is_draft: bool = False
    draft_text: str | None = None
    text_already_printed: bool = False
    diffusion_step: int | None = 0
    diffusion_total_steps: int | None = 0
    diffusion_canvas_index: int | None = 0
    diffusion_block_complete: bool = False


def _stub_versions() -> dict[str, str | None]:
    return {
        "numpy": "1.0",
        "mlx": "0.1",
        "mlx-metal": None,
        "mlx-vlm": "0.1",
        "huggingface-hub": "0.1",
        "transformers": "4.0",
        "tokenizers": "0.1",
        "Pillow": "10.0",
    }


def _issue_summary_output_paths(output_dir: Path) -> check_models.ReportOutputPaths:
    """Return canonical retained paths for aggregate issue-summary tests."""
    return check_models.ReportOutputPaths(
        index=output_dir / "index.md",
        html=output_dir / "reports" / "results.html",
        gallery_markdown=output_dir / "reports" / "model_gallery.md",
        jsonl=output_dir / "results.jsonl",
        diagnostics=output_dir / "reports" / "diagnostics.md",
        log=output_dir / "check_models.log",
        environment=output_dir / "environment.log",
    )


def _issue_summary_result(
    model: str,
    *,
    execution: str = "completed",
    usability: str = "usable",
    maintainer_status: str = "none",
    observations: list[str] | None = None,
    details: dict[str, object] | None = None,
    stop_reason: str | None = None,
) -> dict[str, object]:
    """Build one literal schema-3.0 result without production serializers."""
    crashed = execution == "crashed"
    return {
        "_type": "result",
        "model": model,
        "timestamp": "2026-07-31 12:01:00 BST",
        "assessment": {
            "execution": execution,
            "usability": usability,
            "maintainer_status": maintainer_status,
            "observations": observations or [],
            **({"details": details} if details is not None else {}),
        },
        "generated_text": "generated output that must not be copied",
        "captured_output_on_fail": "captured output that must not be copied",
        "failure": (
            {
                "phase": "processor_load",
                "stage": "Processor Error",
                "message": "processor missing image support",
                "exception_type": "ValueError",
                "traceback": "Traceback (most recent call last):\nheavy evidence",
                "exception_chain": [
                    {
                        "type": "ValueError",
                        "module": "builtins",
                        "message": "processor missing image support",
                        "origin": "check_models.py",
                    }
                ],
            }
            if crashed
            else None
        ),
        "metrics": {},
        "timing": {"stop_reason": stop_reason} if stop_reason is not None else {},
        "model_provenance": {
            "model": model,
            "requested_revision": None,
            "resolved_revision": f"revision-{model.rsplit('/', maxsplit=1)[-1]}",
            "snapshot_path": None,
        },
        "prompt_diagnostics": None,
    }


def _issue_summary_counts(results: Sequence[dict[str, object]]) -> dict[str, int]:
    """Derive header counts from the fixture rows so the loader's cross-check holds.

    Unrecognised executions land in the indeterminate bucket so the header stays
    internally consistent even for malformed-row rejection fixtures (whose row
    error must fire first).
    """
    executions = [
        cast("dict[str, object]", row.get("assessment") or {}).get("execution") for row in results
    ]
    completed = sum(1 for execution in executions if execution == "completed")
    crashed = sum(1 for execution in executions if execution == "crashed")
    return {
        "models_attempted": len(results),
        "models_evaluated": completed + crashed,
        "models_completed": completed,
        "models_crashed": crashed,
        "models_indeterminate": len(results) - completed - crashed,
    }


def _issue_summary_metadata(
    results: Sequence[dict[str, object]],
    *,
    image_source_url: str | None = None,
    image_sha256: str | None = "a" * 64,
    trust_remote_code: bool = False,
    total_runtime_seconds: float | None = None,
    comparison: dict[str, object] | None = None,
    started_at: str | None = None,
) -> dict[str, object]:
    """Build one literal, loader-valid schema-3.0 header for the given rows."""
    image: dict[str, object] = {
        "name": "fixture.jpg",
        "sha256": image_sha256,
        "size_bytes": 12_345,
        "width": 640,
        "height": 480,
        "megapixels": 0.3072,
    }
    if image_source_url is not None:
        image["source_url"] = image_source_url
    return {
        "_type": "metadata",
        "format_version": "3.0",
        "prompt": "full prompt that must not be copied",
        "prompt_sha256": "9738fd5ba66bfe341bbb67bcceb15019aae20950b5f6ee44ef804236247ca5d3",
        "system": {
            "macOS Version": "26.6",
            "GPU/Chip": "Apple M5 Max",
            "Python Version": "3.13.13",
        },
        "timestamp": "2026-07-31 12:02:00 BST",
        "total_runtime_seconds": (
            total_runtime_seconds if total_runtime_seconds is not None else 0.0
        ),
        "counts": _issue_summary_counts(results),
        "artifacts": {"results_jsonl": "results.jsonl"},
        "producer": {
            "name": "check_models",
            "version": "0.8.9",
            "git_revision": "abc123",
            "install_type": "source-tree",
            "dirty": False,
        },
        "image": image,
        "generation_settings": {"max_tokens": 500, "temperature": 0.0},
        "trust_remote_code": trust_remote_code,
        "comparison": comparison,
        **({"started_at": started_at} if started_at is not None else {}),
        "eval_mode": "assisted",
        "metadata_exposed_to_prompt": True,
        "library_versions": {
            "mlx-vlm": "0.6.8",
            "mlx": "0.32.1",
            "transformers": "5.14.1",
        },
        "component_provenance": {},
        "runtime_fingerprint": {},
    }


def _write_issue_summary_fixture(
    output_paths: check_models.ReportOutputPaths,
    *,
    results: Sequence[dict[str, object]],
    image_source_url: str | None = None,
    image_sha256: str | None = "a" * 64,
    trust_remote_code: bool = False,
    total_runtime_seconds: float | None = None,
    comparison: dict[str, object] | None = None,
    started_at: str | None = None,
) -> None:
    """Write hand-authored retained input for issue-summary tests."""
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    metadata = _issue_summary_metadata(
        results,
        image_source_url=image_source_url,
        image_sha256=image_sha256,
        trust_remote_code=trust_remote_code,
        total_runtime_seconds=total_runtime_seconds,
        comparison=comparison,
        started_at=started_at,
    )
    rows = (metadata, *results)
    check_models._write_text_file(
        output_paths.jsonl,
        "".join(json.dumps(row) + "\n" for row in rows),
    )


def test_format_peak_memory_context_uses_significant_figures() -> None:
    """Human working-set context should follow project-wide significant figures."""
    assert check_models._format_peak_memory_context(18.2, 96 * 1024**3) == (
        "18 GB (17.7% of 96 GB recommended working set)"
    )
    assert check_models._format_peak_memory_context(120.0, 96 * 1024**3) == (
        "120 GB (116% of 96 GB recommended working set)"
    )


def test_format_peak_memory_context_preserves_bare_peak_without_denominator() -> None:
    """Missing capacity must preserve the established bare table value."""
    assert check_models._format_peak_memory_context(18.2, None) == "18"
    assert check_models._format_peak_memory_context(None, 96 * 1024**3) == ""


def test_human_observation_labels_are_readable_and_severity_ordered() -> None:
    labels = check_models._human_observation_labels(
        (
            "no_keyword_overlap",
            "missing_requested_sections",
            "unexpected_special_token",
            "repeated_output",
        ),
        details={"missing_sections": ["title", "keywords"]},
    )

    assert labels == (
        "Response repeats the same text; "
        "Unrecognised model control tokens remain visible; "
        "Required labelled fields not detected: title, keywords; "
        "Keywords do not overlap the supplied keyword hints"
    )


def test_catalog_constraint_label_names_only_breached_constraints() -> None:
    """In-range counts must not read as violations beside a real breach."""
    duplicates_only = check_models._human_observation_labels(
        ("catalog_constraint_violation",),
        details={
            "title_word_count": 5,
            "title_word_range": [5, 10],
            "keyword_count": 18,
            "keyword_count_range": [10, 18],
            "duplicate_keywords": ["action", "vehicles"],
        },
    )
    assert duplicates_only == "Duplicate keywords: action, vehicles"

    out_of_range = check_models._human_observation_labels(
        ("catalog_constraint_violation",),
        details={
            "title_word_count": 4,
            "title_word_range": [5, 10],
            "keyword_count": 3,
            "keyword_count_range": [10, 18],
        },
    )
    assert out_of_range == (
        "Title has 4 words (requested 5-10); Keyword list has 3 terms (requested 10-18)"
    )


def test_human_observation_labels_cover_every_stable_code() -> None:
    all_codes = get_args(check_models.ObservationCode.__value__)

    labels = check_models._human_observation_labels(all_codes)

    assert labels.count("; ") == len(all_codes) - 1
    assert "_" not in labels
    assert "catalogue instructions" not in labels.casefold()


def test_run_issue_summary_expands_crash_and_tables_other_findings(tmp_path: Path) -> None:  # noqa: PLR0915 - one end-to-end walk of every summary section
    """A paste-ready issue should prioritize crashes without copying heavy evidence."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/crash",
                execution="crashed",
                usability="not_evaluated",
                maintainer_status="actionable_failure",
            ),
            _issue_summary_result(
                "org/observed",
                usability="unusable",
                maintainer_status="observation_needs_reproduction",
                observations=["missing_requested_sections", "repeated_output"],
                details={"missing_sections": ["title", "keywords"]},
            ),
            _issue_summary_result(
                "org/crashed-observed",
                execution="crashed",
                usability="not_evaluated",
                maintainer_status="observation_needs_reproduction",
                observations=["unexpected_special_token"],
            ),
            _issue_summary_result(
                "org/indeterminate",
                execution="indeterminate",
                usability="not_evaluated",
                observations=["empty_output"],
            ),
            _issue_summary_result("org/clean"),
        ),
    )
    issue_draft = output_paths.index.parent / "issues" / "issue_org_crash.md"
    issue_draft.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(issue_draft, "# Exact crash draft\n")

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        summary = check_models.generate_run_issue_summary_report(
            output_paths,
            issue_reports={"org/crash": issue_draft},
        )

    assert summary == output_paths.index.parent / "issues" / "run_summary.md"
    if summary is None:
        pytest.fail("surfaced results must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert content.startswith(
        "# mlx-vlm compatibility findings across 5 cached vision-language models\n"
    )
    assert "## Run summary" in content
    assert "mechanical facts from one image" in content
    assert "## Crashes requiring action" in content
    assert "### org/crash" in content
    assert "processor_load" in content
    assert "ValueError: processor missing image support" in content
    assert "The original local input is not published" in content
    assert "JPEG" in content
    assert "640 x 480" in content
    assert "12,345 bytes" in content
    assert "a" * 64 in content
    assert "full prompt that must not be copied" in content
    assert "reproduce.py" not in content
    assert "prompt.txt" not in content
    assert "--image fixture.jpg" not in content
    assert "## Completed attempts requiring review" in content
    assert "## Crashed attempts requiring review" in content
    assert "## Indeterminate attempts requiring review" in content
    assert content.count("| Model | Mechanical checks | Observed result | Evidence |") == 3
    assert "| Model | Execution / usability | Observations | Full evidence |" not in content
    assert "## Observation clusters" in content
    # Clusters group by observation codes only (no per-model detail expansion).
    assert (
        "| Response repeats the same text; Required labelled fields not detected | 1 |"
    ) in content
    assert (
        "| org/observed | major concerns | Response repeats the same text; "
        "Required labelled fields not detected: title, keywords |"
    ) in content
    crashed_table = _extract_markdown_subsection(
        content,
        "## Crashed attempts requiring review",
        end_headings=("## Indeterminate attempts requiring review",),
    )
    assert "org/crashed-observed" in crashed_table
    assert "| org/crash |" not in crashed_table
    link_targets = _extract_markdown_link_targets(content)
    assert link_targets
    blob_prefix = (
        "https://github.com/jrp2014/check_models/blob/"
        f"{check_models._github_blob_ref()}/src/output/"
    )
    assert all(target.startswith(blob_prefix) for target in link_targets)
    assert (
        "1 completion without detected concerns (`org/clean`). See the [full model gallery]"
        in content
    )
    assert "Trust remote code" in content
    assert "check_models" in content
    assert "0.8.9" in content
    assert "abc123" in content
    assert "GitHub links" in content
    # The link caveat is dynamic: pinned wording for a clean-worktree SHA ref,
    # mutable-branch wording otherwise.
    if re.fullmatch(r"[0-9a-f]{40}", check_models._github_blob_ref()):
        assert "pinned to producer commit" in content
    else:
        assert "mutable" in content
    # Clean models appear only in the at-a-glance table and the named clean
    # completions, never in the review sections.
    review_sections = content[content.index("## Observation clusters") :]
    review_sections = review_sections[
        : review_sections.index("## Completions without detected concerns")
    ]
    assert "org/clean" not in review_sections
    assert "Traceback (most recent call last)" not in content
    assert "generated output that must not be copied" not in content


def test_run_issue_summary_uses_failure_reason_when_observations_are_empty(
    tmp_path: Path,
) -> None:
    """An indeterminate row should say what prevented evaluation."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/network",
        execution="indeterminate",
        usability="not_evaluated",
    )
    result["failure"] = {
        "phase": "model_load",
        "stage": "Network Error",
        "code": "UNKNOWN_MODEL_LOAD_NETWORK_ERROR",
        "message": "Model loading failed: [Errno 54] Connection reset by peer",
        "exception_type": "ReadError",
        "exception_module": "httpx",
        "package": "unknown",
        "traceback": "heavy evidence",
        "exception_chain": [],
    }
    _write_issue_summary_fixture(output_paths, results=(result,))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the indeterminate result must produce a summary")
    content = summary.read_text(encoding="utf-8")
    assert "Network connection reset during model loading" in content
    assert "| org/network | not evaluated | none |" not in content


def test_run_issue_summary_sorts_review_rows_by_observation_severity(tmp_path: Path) -> None:
    """Grossly unusable outputs should be visible before repairable caveats."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/count-caveat",
                usability="usable_with_caveats",
                maintainer_status="observation_needs_reproduction",
                observations=["catalog_constraint_violation"],
                details={"title_word_count": 4, "title_word_range": [5, 10]},
            ),
            _issue_summary_result(
                "org/missing",
                usability="unusable",
                maintainer_status="observation_needs_reproduction",
                observations=["missing_requested_sections"],
            ),
            _issue_summary_result(
                "org/repeated",
                usability="unusable",
                maintainer_status="observation_needs_reproduction",
                observations=["repeated_output"],
            ),
        ),
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the observed results must produce a summary")
    content = summary.read_text(encoding="utf-8")
    review = content[content.index("## Completed attempts requiring review") :]
    assert review.index("| org/repeated |") < review.index("| org/missing |")
    assert review.index("| org/missing |") < review.index("| org/count-caveat |")
    assert "Title has 4 words (requested 5-10)" in content


def test_diagnostics_sorts_triage_and_evidence_by_actionability(tmp_path: Path) -> None:
    """Grossly unusable output should precede less severe observations everywhere."""
    minimal = PerformanceResult(
        model_name="org/a-minimal",
        success=True,
        generation=_MockGeneration(
            text="Title: Cat\nDescription: A cat.\nKeywords: cat, cat", generation_tokens=12
        ),
        assessment_profile="metadata",
    )
    repeated = PerformanceResult(
        model_name="org/z-repeated",
        success=True,
        generation=_MockGeneration(text="word " * 100, generation_tokens=100),
    )
    results = [minimal, repeated]
    context = _build_report_render_context(
        results=results,
        prompt="Describe this image.",
        system_info={},
    )
    output = tmp_path / "diagnostics.md"

    generate_diagnostics_report(
        results,
        output,
        prompt="Describe this image.",
        library_versions=_stub_versions(),
        system_info={},
        report_context=context,
    )

    content = output.read_text(encoding="utf-8")
    triage = _extract_markdown_subsection(
        content,
        "## Triage",
        end_headings=("## Crashes requiring action",),
    )
    observations = _extract_markdown_subsection(
        content,
        "## Completed Runs with Observations",
        end_headings=("## Indeterminate Attempts",),
    )
    # Repetition is an integration signal; duplicate keywords are a
    # compliance-only note and stays out of the maintainer lane entirely.
    assert "org/z-repeated" in triage
    assert "org/a-minimal" not in triage
    assert "org/z-repeated" in observations
    assert "org/a-minimal" not in observations
    compliance = _extract_markdown_subsection(
        content,
        "## Model Compliance Notes (not maintainer issues)",
        end_headings=("## Context for completions without detected concerns",),
    )
    assert "org/a-minimal" in compliance
    assert "org/z-repeated" not in compliance


def test_run_issue_summary_builds_complete_public_image_reproduction(tmp_path: Path) -> None:
    """A public source should make the aggregate crash reproduction runnable."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    _write_issue_summary_fixture(
        output_paths,
        results=(result,),
        image_source_url="https://example.test/images/cats.jpg",
        trust_remote_code=True,
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert "https://example.test/images/cats.jpg" in content
    assert "curl --fail --location" in content
    assert "set -euo pipefail\ncurl --fail --location" in content
    assert "shasum -a 256 --check" in content
    assert "python -m mlx_vlm.generate" in content
    assert "--model org/crash" in content
    assert "--revision revision-crash" in content
    assert "--prompt 'full prompt that must not be copied'" in content
    assert "--image repro-image.jpg" in content
    assert "--trust-remote-code" in content
    assert "reproduce.py" not in content
    assert "prompt.txt" not in content


def test_run_issue_summary_load_crash_gets_native_repro_without_public_image(
    tmp_path: Path,
) -> None:
    """Model-load crashes reproduce with any image, so a command is always durable."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/load-crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    failure = result["failure"]
    assert isinstance(failure, dict)
    failure["phase"] = "model_load"
    _write_issue_summary_fixture(output_paths, results=(result,))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    prose = " ".join(content.split())
    assert "crash occurred during model load, before image decoding" in prose
    assert "python -m mlx_vlm.generate" in content
    assert "--model org/load-crash" in content
    assert "--image any-local-image.jpg" in content
    command_line = next(
        line for line in content.splitlines() if "python -m mlx_vlm.generate" in line
    )
    assert "--prompt x" in command_line
    assert "--max-tokens 8" in command_line
    assert "full prompt that must not be copied" not in command_line
    assert "does not claim a complete reproduction command" not in prose


def test_run_issue_summary_withholds_command_for_post_load_crash(tmp_path: Path) -> None:
    """Crashes after model load still need the exact image, so no command is claimed."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/decode-crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    _write_issue_summary_fixture(output_paths, results=(result,))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert "does not claim a complete reproduction command" in " ".join(content.split())
    assert "any-local-image.jpg" not in content


def test_native_repro_preserves_every_supported_nondefault_argument() -> None:
    """The native command must retain every harness setting exposed by its CLI."""
    run_args = Namespace(
        max_tokens=321,
        temperature=0.25,
        top_p=0.81,
        min_p=0.12,
        top_k=7,
        logit_bias={42: -1.5},
        adapter_path="adapters/test",
        resize_shape=(64, 32),
        eos_tokens=(EOS_OVERRIDE_TOKEN,),
        seed=73,
        repetition_penalty=1.15,
        repetition_context_size=48,
        presence_penalty=0.3,
        presence_context_size=96,
        frequency_penalty=0.2,
        frequency_context_size=80,
        max_kv_size=4096,
        kv_bits=4,
        kv_quant_scheme="turboquant",
        kv_group_size=32,
        quantized_kv_start=128,
        skip_special_tokens=True,
        force_download=True,
        revision="requested-revision",
        trust_remote_code=True,
        quantize_activations=True,
        processor_kwargs={"cropping": False},
        prefill_step_size=512,
        enable_thinking=True,
        thinking_budget=24,
        thinking_mode="enabled",
        thinking_start_token=THINKING_START_TOKEN,
        thinking_end_token=CUSTOM_THINKING_END_TOKEN,
    )

    tokens = check_models._build_native_mlx_vlm_cli_tokens(
        model_name="org/model",
        prompt="Describe this image.",
        image_ref="image.jpg",
        run_args=run_args,
        resolved_revision="resolved-revision",
    )

    expected_pairs = {
        "--adapter-path": "adapters/test",
        "--seed": "73",
        "--repetition-penalty": "1.15",
        "--repetition-context-size": "48",
        "--presence-penalty": "0.3",
        "--presence-context-size": "96",
        "--frequency-penalty": "0.2",
        "--frequency-context-size": "80",
        "--max-kv-size": "4096",
        "--kv-bits": "4",
        "--kv-quant-scheme": "turboquant",
        "--kv-group-size": "32",
        "--quantized-kv-start": "128",
        "--revision": "resolved-revision",
        "--prefill-step-size": "512",
        "--thinking-budget": "24",
        "--thinking-mode": "enabled",
        "--thinking-start-token": THINKING_START_TOKEN,
        "--thinking-end-token": CUSTOM_THINKING_END_TOKEN,
    }
    for flag, value in expected_pairs.items():
        assert tokens[tokens.index(flag) + 1] == value
    assert tokens[tokens.index("--resize-shape") + 1 : tokens.index("--resize-shape") + 3] == [
        "64",
        "32",
    ]
    assert tokens[tokens.index("--eos-tokens") + 1] == EOS_OVERRIDE_TOKEN
    for flag in (
        "--skip-special-tokens",
        "--force-download",
        "--trust-remote-code",
        "--quantize-activations",
        "--enable-thinking",
    ):
        assert flag in tokens
    assert json.loads(tokens[tokens.index("--processor-kwargs") + 1]) == {"cropping": False}
    # Sampling settings are first-class upstream CLI flags since mlx-vlm #1994;
    # only logit_bias still needs the --gen-kwargs escape hatch.
    assert tokens[tokens.index("--top-p") + 1] == "0.81"
    assert tokens[tokens.index("--min-p") + 1] == "0.12"
    assert tokens[tokens.index("--top-k") + 1] == "7"
    assert json.loads(tokens[tokens.index("--gen-kwargs") + 1]) == {
        "logit_bias": {"42": -1.5},
    }


def test_run_issue_summary_withholds_stale_log_and_environment_links(tmp_path: Path) -> None:
    """Issue-ready evidence must not attribute prior-run logs to the current run."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/observed",
                usability="usable_with_caveats",
                maintainer_status="observation_needs_reproduction",
                observations=["minimal_output"],
            ),
        ),
        total_runtime_seconds=120.0,
    )
    check_models._write_text_file(
        output_paths.log,
        "2026-07-31 11:00:00 BST - INFO - prior run\n",
    )
    check_models._write_text_file(
        output_paths.environment,
        "FULL ENVIRONMENT DUMP - 2026-07-31 11:00:00 BST\n",
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "Stale retained artifacts omitted" in content
    assert "check_models.log" in content
    assert "environment.log" in content
    assert "src/output/check_models.log" not in content
    assert "src/output/environment.log" not in content
    assert "| Environment |" not in content
    assert "| Log |" not in content


def _observed_result() -> dict[str, object]:
    return _issue_summary_result(
        "org/observed",
        usability="usable_with_caveats",
        maintainer_status="observation_needs_reproduction",
        observations=["minimal_output"],
    )


def _write_logs_starting_at(output_paths: check_models.ReportOutputPaths, stamp: str) -> None:
    check_models._write_text_file(output_paths.log, f"{stamp} - INFO - run start\n")
    check_models._write_text_file(output_paths.environment, f"FULL ENVIRONMENT DUMP - {stamp}\n")


def test_run_issue_summary_trusts_started_at_over_runtime_arithmetic(tmp_path: Path) -> None:
    """The retained wall-clock start must keep the run's own early logs linked.

    A perf-counter runtime excludes system sleep, so end - runtime can land
    after the log's first line.
    """
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    # Header ends 12:02:00 with a 120 s runtime, so arithmetic says 12:00:00;
    # the machine slept, and the logs actually began at 11:56:00.
    _write_issue_summary_fixture(
        output_paths,
        results=(_observed_result(),),
        total_runtime_seconds=120.0,
        started_at="2026-07-31 11:55:30 BST",
    )
    _write_logs_starting_at(output_paths, "2026-07-31 11:56:00 BST")

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "Stale retained artifacts omitted" not in content
    assert "src/output/check_models.log" in content
    assert "src/output/environment.log" in content


def test_run_issue_summary_legacy_window_bounds_start_by_earliest_result(
    tmp_path: Path,
) -> None:
    """Headers without started_at fall back to the earliest result timestamp."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _observed_result()
    result["timestamp"] = "2026-07-31 11:56:30 BST"
    _write_issue_summary_fixture(output_paths, results=(result,), total_runtime_seconds=120.0)
    _write_logs_starting_at(output_paths, "2026-07-31 11:56:00 BST")

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "Stale retained artifacts omitted" not in content
    assert "src/output/check_models.log" in content


def test_run_summary_header_shows_start_finish_and_duration(tmp_path: Path) -> None:
    """A skimmer gets when the run started, when it finished, and how long it took."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(_observed_result(),),
        total_runtime_seconds=1201.0,
        started_at="2026-07-31 11:41:59 BST",
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "- *Run started:* 2026-07-31 11:41:59 BST" in content
    assert "- *Run finished:* 2026-07-31 12:02:00 BST" in content
    assert "- *Run duration:* 20m 01s" in content
    assert "Run timestamp" not in content


def test_every_summary_surface_leads_with_lane_and_input_image(tmp_path: Path) -> None:
    """Image size and evaluation lane explain long prefills, so they sit near the top."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(output_paths, results=(_observed_result(),))

    summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    lines = summary.read_text(encoding="utf-8").splitlines()
    finished = next(i for i, line in enumerate(lines) if line.startswith("- *Run finished:*"))
    assert lines[finished + 2] == "- *Evaluation lane:* assisted"
    assert lines[finished + 4] == "- *Input image:* JPEG, 640 x 480 pixels (0.3 MP), 0.0 MB"
    assert "Evaluation mode" not in "\n".join(lines)

    image = cast(
        "check_models.RunImageRecord",
        {
            "name": "big.jpg",
            "sha256": None,
            "size_bytes": 66_295_254,
            "width": 6656,
            "height": 9984,
            "megapixels": 66.453504,
        },
    )
    index_lines = check_models._output_index_dashboard_lines(
        [], 10.0, image=image, eval_mode="assisted"
    )
    assert index_lines[2:6] == [
        "- Run duration: 10.00s",
        "- Evaluation lane: assisted",
        "- Assessment: Legacy assessment; profile not recorded",
        "- Input image: JPEG, 6,656 x 9,984 pixels (66.5 MP), 66.3 MB",
    ]
    assert check_models._run_input_summary_rows(None, None) == (
        ("Evaluation lane", "unknown"),
        ("Assessment", "Legacy assessment; profile not recorded"),
        ("Input image", "unavailable"),
    )


def test_output_index_dashboard_leads_with_run_duration() -> None:
    lines = check_models._output_index_dashboard_lines([], 1201.0)
    assert lines[2] == "- Run duration: 20m 01s"
    assert check_models._output_index_dashboard_lines([])[2].startswith("- Models attempted")


def test_retained_run_window_prefers_started_at() -> None:
    parse = check_models._parse_local_timestamp
    metadata = cast(
        "check_models.JsonlMetadataRecord",
        {
            "timestamp": "2026-07-31 12:02:00 BST",
            "total_runtime_seconds": 120.0,
            "started_at": "2026-07-31 11:55:30 BST",
        },
    )
    assert check_models._retained_run_window(metadata) == (
        parse("2026-07-31 11:55:30 BST"),
        parse("2026-07-31 12:02:00 BST"),
    )
    # A malformed or future started_at falls back to the arithmetic window.
    metadata["started_at"] = "2026-07-31 12:03:00 BST"
    assert check_models._retained_run_window(metadata) == (
        parse("2026-07-31 12:00:00 BST"),
        parse("2026-07-31 12:02:00 BST"),
    )


def test_retained_loader_rejects_non_string_started_at(tmp_path: Path) -> None:
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    result = _issue_summary_result("org/model")
    metadata = _issue_summary_metadata((result,))
    metadata["started_at"] = 5
    check_models._write_text_file(
        output_paths.jsonl, json.dumps(metadata) + "\n" + json.dumps(result) + "\n"
    )

    with pytest.raises(ValueError, match="started_at must be a string"):
        check_models.generate_run_issue_summary_report(output_paths)


def test_run_issue_summary_keeps_current_log_and_environment_links(tmp_path: Path) -> None:
    """Artifacts beginning inside the retained run window should remain linked."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/observed",
                usability="usable_with_caveats",
                maintainer_status="observation_needs_reproduction",
                observations=["minimal_output"],
            ),
        ),
        total_runtime_seconds=120.0,
    )
    check_models._write_text_file(
        output_paths.log,
        "2026-07-31 12:00:00 BST - INFO - current run\n",
    )
    check_models._write_text_file(
        output_paths.environment,
        "FULL ENVIRONMENT DUMP - 2026-07-31 12:00:00 BST\n",
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "Stale retained artifacts omitted" not in content
    assert "src/output/check_models.log" in content
    assert "src/output/environment.log" in content
    assert "| Environment |" in content
    assert "| Log |" in content


def test_run_issue_summary_compacts_large_unexpected_parameter_errors(tmp_path: Path) -> None:
    """Aggregate crash evidence should group repeated parameter paths."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    parameters = [
        "audio_tower.encoder.biases",
        "audio_tower.encoder.scales",
        *(
            f"language_model.model.layers.{layer}.mlp.experts.down_proj.weight"
            for layer in range(10)
        ),
    ]
    message = "Received 12 parameters not in model: \n" + ",\n".join(parameters) + "."
    failure = result["failure"]
    assert isinstance(failure, dict)
    failure["message"] = message
    failure["exception_chain"] = [
        {
            "type": "ValueError",
            "module": "builtins",
            "message": message,
            "origin": "check_models.py",
        },
        {
            "type": "ValueError",
            "module": "builtins",
            "message": f"Model loading failed: {message}",
            "origin": "check_models.py",
        },
    ]
    _write_issue_summary_fixture(output_paths, results=(result,))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "ValueError: Received 12 parameters not in model" in content
    assert "audio_tower" in content
    assert "language_model" in content
    assert parameters[0] in content
    assert parameters[-1] not in content
    assert "model evidence" in content


def test_diagnostics_and_issue_draft_compact_large_unexpected_parameter_errors(
    tmp_path: Path,
) -> None:
    """Maintainer paste surfaces should compact large unexpected-parameter lists."""
    parameters = [
        "audio_tower.encoder.biases",
        "audio_tower.encoder.scales",
        *(
            f"language_model.model.layers.{layer}.mlp.experts.down_proj.weight"
            for layer in range(10)
        ),
    ]
    message = "Received 12 parameters not in model: \n" + ",\n".join(parameters) + "."
    crash = PerformanceResult(
        model_name="org/param-mismatch",
        generation=None,
        success=False,
        failure_phase="model_load",
        error_stage="Model Error",
        error_type="ValueError",
        error_message=message,
        root_error_type="ValueError",
        root_error_module="builtins",
        root_error_message=message,
        exception_chain=(check_models.FailureException("ValueError", "builtins", message),),
        error_package="mlx-vlm",
        error_traceback=f"Traceback (most recent call last):\nValueError: {message}",
    )
    context = _build_report_render_context(
        results=[crash],
        prompt="Describe the image.",
        system_info={"Python Version": "3.13.13"},
    )
    diagnostics = tmp_path / "diagnostics.md"
    generate_diagnostics_report(
        [crash],
        diagnostics,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={"Python Version": "3.13.13"},
        report_context=context,
    )
    generated = _generate_github_issue_reports(
        report_context=context,
        output_dir=tmp_path,
        library_versions=_stub_versions(),
        system_info={"Python Version": "3.13.13"},
        prompt="Describe the image.",
    )

    diagnostics_content = diagnostics.read_text(encoding="utf-8")
    issue_content = next(iter(generated.values())).read_text(encoding="utf-8")
    for content in (diagnostics_content, issue_content):
        assert "Received 12 parameters not in model" in content
        assert "families: audio_tower, language_model" in content
        assert "representative parameters:" in content
        # Compacted exception presentation keeps a short sample, not the full list.
        assert parameters[0] in content
    # Full traceback remains available for deep inspection.
    assert parameters[-1] in diagnostics_content
    assert parameters[-1] in issue_content


def test_github_blob_ref_never_pins_to_producer_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artifact links must not pin to producer HEAD, even for clean worktrees.

    The artifacts being generated cannot exist in any commit at generation
    time, so a HEAD pin would show the previous run while claiming the
    evidence is durable. Only an explicit override may pin.
    """
    monkeypatch.setattr(
        check_models,
        "_collect_check_models_provenance",
        lambda: {
            "name": "check_models",
            "version": "0.8.9",
            "git_revision": "deadbeefcafebabe",
            "install_type": "source-tree",
            "dirty": False,
        },
    )
    monkeypatch.setattr(check_models, "_GITHUB_REF_OVERRIDE", None)
    assert check_models._github_blob_ref() == check_models._GITHUB_DEFAULT_BRANCH
    monkeypatch.setattr(check_models, "_GITHUB_REF_OVERRIDE", "a" * 40)
    assert check_models._github_blob_ref() == "a" * 40


def test_observation_display_registry_covers_literal_codes() -> None:
    """Observation display metadata must stay aligned with ObservationCode."""
    codes = check_models._literal_values(check_models.ObservationCode)
    assert set(check_models._OBSERVATION_DISPLAY_BY_CODE) == codes
    assert codes == check_models._RUN_ISSUE_OBSERVATION_VALUES
    assert check_models._RUN_ISSUE_EXECUTION_VALUES == check_models._EXECUTION_STATUS_VALUES
    assert "empty_output" in check_models._UNUSABLE_OBSERVATIONS
    assert "thinking_trace_present" not in check_models._UNUSABLE_OBSERVATIONS
    assert (
        check_models._gallery_observation_labels(("token_cap_truncation", "repeated_output"))
        == "repeated text; cut off at token limit"
    )


@pytest.mark.parametrize("image_sha256", [None, "abc123"])
def test_run_issue_summary_withholds_command_without_valid_digest(
    tmp_path: Path,
    image_sha256: str | None,
) -> None:
    """A public URL alone must not be presented as a verified exact input."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    _write_issue_summary_fixture(
        output_paths,
        results=(result,),
        image_source_url="https://example.test/images/cats.jpg",
        image_sha256=image_sha256,
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert "A valid SHA-256 digest is unavailable" in content
    assert "python -m mlx_vlm.generate" not in content
    assert "shasum -a 256 --check" not in content


@pytest.mark.parametrize(
    ("trust_remote_code", "expected_flag"),
    [(True, True), (False, False)],
)
def test_run_issue_summary_preserves_remote_code_policy(
    tmp_path: Path,
    trust_remote_code: bool,
    expected_flag: bool,
) -> None:
    """A retained reproduction must not silently broaden remote-code trust."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    _write_issue_summary_fixture(
        output_paths,
        results=(result,),
        image_source_url="https://example.test/images/cats.jpg",
        trust_remote_code=trust_remote_code,
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert ("--trust-remote-code" in content) is expected_flag


def test_run_issue_summary_uses_cached_assessment_without_reclassification(
    tmp_path: Path,
) -> None:
    """Report-only rendering must preserve cached schema-3.0 assessment values."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/cached",
                usability="usable_with_caveats",
                maintainer_status="observation_needs_reproduction",
                observations=["minimal_output"],
            ),
        ),
    )

    with (
        patch.object(
            check_models,
            "_assess_result",
            side_effect=AssertionError("cached assessment was reclassified"),
        ),
        patch.object(check_models._LinkStyleState, "value", "relative"),
    ):
        summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "## Completed attempts requiring review" in content
    assert "| org/cached | concerns detected |" in content
    assert "Response is unusually short" in content


def test_run_issue_summary_repro_prefers_resolved_revision(tmp_path: Path) -> None:
    """Crash reproduction should pin the immutable resolved snapshot when available."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    provenance = result["model_provenance"]
    assert isinstance(provenance, dict)
    provenance["requested_revision"] = "moving-branch"
    provenance["resolved_revision"] = "immutable-commit"
    _write_issue_summary_fixture(
        output_paths,
        results=(result,),
        image_source_url="https://example.test/images/cats.jpg",
    )

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the crash must produce a run issue summary")
    content = summary.read_text(encoding="utf-8")
    assert "--revision immutable-commit" in content
    assert "--revision moving-branch" not in content


def test_run_issue_summary_written_for_clean_run(tmp_path: Path) -> None:
    """A run with no surfaced result still writes the quality entry point."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(_issue_summary_result("org/clean"),),
    )
    stale = output_paths.index.parent / "issues" / "run_summary.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(stale, "stale issue\n")

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("a clean run must still write the run summary entry point")
    content = summary.read_text(encoding="utf-8")
    assert "**What this run measures.**" in content
    assert "one shared image and prompt" in " ".join(content.split())
    assert "do not establish fitness for other tasks" in " ".join(content.split())
    assert "Exact prompt sent to every model" in content
    assert "full prompt that must not be copied" in content
    assert "No concerns detected is not a task-compliance or accuracy verdict" in " ".join(
        content.split()
    )
    assert "## Model quality at a glance" in content
    assert "org/clean" in content
    assert "## Crashes requiring action" not in content
    assert "`org/clean`" in content  # clean completions are named


def test_run_issue_summary_quality_table_ranks_all_models(tmp_path: Path) -> None:
    """The at-a-glance table lists every model sorted by usability rank."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    crash = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    caveat = _issue_summary_result(
        "org/caveat",
        usability="usable_with_caveats",
        maintainer_status="observation_needs_reproduction",
        observations=["unexpected_special_token"],
    )
    clean = _issue_summary_result("org/clean")
    clean["metrics"] = {
        "generation_tokens": 100,
        "generation_tps": 123.4,
        "peak_memory_gb": 7.5,
    }
    clean["timing"] = {"total_time_s": 12.5}
    _write_issue_summary_fixture(output_paths, results=(crash, caveat, clean))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    if summary is None:
        pytest.fail("the fixture run must produce a run summary")
    content = summary.read_text(encoding="utf-8")
    assert "## Model quality at a glance" in content
    # Sorted usable -> caveats -> crashed, and the crash names its phase.
    assert (
        content.index("org/clean")
        < content.index("org/caveat")
        < content.index("crashed during processor loading")
    )
    assert "control tokens visible" in content
    assert "123 tok/s" in content


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ((), "Missing JSONL metadata"),
        (({"_type": "metadata", "format_version": "2.0"},), "format_version must be 3.0"),
        (
            (
                _issue_summary_metadata(({"_type": "result", "model": "org/model"},)),
                {"_type": "result", "model": "org/model"},
            ),
            "cached assessment",
        ),
    ],
)
def test_run_issue_summary_rejects_invalid_jsonl_contract(
    tmp_path: Path,
    rows: tuple[dict[str, object], ...],
    expected: str,
) -> None:
    """Missing metadata, wrong schemas, and missing assessments must fail clearly."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(
        output_paths.jsonl,
        "".join(json.dumps(row) + "\n" for row in rows),
    )

    with pytest.raises(ValueError, match=expected):
        check_models.generate_run_issue_summary_report(output_paths)


def test_retained_loader_rejects_missing_image_key(tmp_path: Path) -> None:
    """Missing and explicit-null image must stay distinguishable in the header."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    result = _issue_summary_result("org/model")
    metadata = _issue_summary_metadata((result,))
    del metadata["image"]
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(metadata) + "\n" + json.dumps(result) + "\n",
    )

    with pytest.raises(ValueError, match="image field is missing"):
        check_models.generate_run_issue_summary_report(output_paths)


def test_retained_loader_rejects_counts_disagreeing_with_rows(tmp_path: Path) -> None:
    """A header claiming a completion over a crashed row must not load."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    crashed = _issue_summary_result(
        "org/crash",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    metadata = _issue_summary_metadata((_issue_summary_result("org/crash"),))
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(metadata) + "\n" + json.dumps(crashed) + "\n",
    )

    with pytest.raises(ValueError, match="disagree with the result rows"):
        check_models.generate_run_issue_summary_report(output_paths)


@pytest.mark.parametrize(
    "removed_field",
    ["timestamp", "generated_text", "captured_output_on_fail", "metrics", "timing"],
)
def test_retained_loader_rejects_rows_missing_required_fields(
    tmp_path: Path,
    removed_field: str,
) -> None:
    """Every retained row field the reports and comparison consume must exist."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    result = _issue_summary_result("org/model")
    del result[removed_field]
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(_issue_summary_metadata((result,))) + "\n" + json.dumps(result) + "\n",
    )

    with pytest.raises(ValueError, match="missing required retained fields"):
        check_models.generate_run_issue_summary_report(output_paths)


def test_retained_loader_rejects_rows_with_misshapen_fields(tmp_path: Path) -> None:
    """A non-mapping metrics blob must fail at the loader, not in a consumer."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    result = _issue_summary_result("org/model")
    result["metrics"] = "not a mapping"
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(_issue_summary_metadata((result,))) + "\n" + json.dumps(result) + "\n",
    )

    with pytest.raises(ValueError, match="invalid retained field shapes"):
        check_models.generate_run_issue_summary_report(output_paths)


def _retained_comparison_payload() -> dict[str, object]:
    """One serialized comparison exactly as the schema-3 metadata retains it."""
    return {
        "baseline": "results.jsonl @ HEAD",
        "baseline_timestamp": "2026-07-30 12:00:00 BST",
        "baseline_components": {"prompt": "identical"},
        "comparability": "comparable",
        "unverified_facts": [],
        "throughput_comparable": True,
        "revision_changes": [],
        "compared_models": 1,
        "models_added": [],
        "models_removed": [],
        "changes": [
            {
                "model": "org/clean",
                "execution": ["completed", "completed"],
                "usability": ["usable", "unusable"],
                "observations_added": ["repeated_output"],
                "observations_removed": [],
            }
        ],
        "identical_text_models": 0,
        "text_compared_models": 1,
        "generation_tps_ratio": {
            "median": 0.98,
            "min": 0.98,
            "max": 0.98,
            "compared_models": 1,
        },
        "throughput_flags": [],
        "memory_changes": [],
        "history_runs_used": 0,
        "execution_mode": {"baseline": "in_process", "current": "in_process"},
    }


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ({"throughput_comparable": "false"}, "not a boolean"),
        ({"comparability": "sideways"}, "not a known value"),
        ({"baseline_timestamp": 5}, "not a string or null"),
        ({"baseline_components": "bad"}, "not an object"),
        (
            {
                "throughput_flags": [
                    {
                        "model": "org/clean",
                        "baseline_tps": 10.0,
                        "current_tps": 5.0,
                        "ratio": 0.5,
                        "band": [0.9, 1.1],
                        "band_source": "guess",
                        "band_samples": 3,
                    }
                ]
            },
            "band_source",
        ),
    ],
)
def test_run_comparison_from_json_rejects_malformed_values(
    mutation: dict[str, object],
    match: str,
) -> None:
    """A damaged retained comparison must raise, never be coerced or misread."""
    payload = _retained_comparison_payload()
    payload.update(mutation)

    with pytest.raises((TypeError, ValueError), match=match):
        check_models._run_comparison_from_json(cast("dict[str, check_models.JsonLike]", payload))


def test_retained_loader_rejects_non_mapping_nested_structures(tmp_path: Path) -> None:
    """Nested objects the reports index into must be mappings at the loader."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)

    bad_details = _issue_summary_result("org/model", observations=["catalog_constraint_violation"])
    cast("dict[str, object]", bad_details["assessment"])["details"] = "bad"
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(_issue_summary_metadata((bad_details,))) + "\n" + json.dumps(bad_details) + "\n",
    )
    with pytest.raises(ValueError, match="non-mapping assessment details"):
        check_models.generate_run_issue_summary_report(output_paths)

    bad_kwargs = _issue_summary_result("org/model")
    bad_kwargs["prompt_diagnostics"] = {"generate_kwargs": "bad"}
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(_issue_summary_metadata((bad_kwargs,))) + "\n" + json.dumps(bad_kwargs) + "\n",
    )
    with pytest.raises(ValueError, match="non-mapping prompt generate_kwargs"):
        check_models.generate_run_issue_summary_report(output_paths)


@pytest.mark.parametrize(
    ("details", "field"),
    [
        ({"title_word_count": "five"}, "title_word_count"),
        ({"title_word_count": True}, "title_word_count"),
        ({"title_word_range": [5]}, "title_word_range"),
        ({"title_word_range": ["five", "ten"]}, "title_word_range"),
        ({"missing_sections": [1]}, "missing_sections"),
        ({"duplicate_keywords": [1]}, "duplicate_keywords"),
        ({"repeated_fragment": ["listed"]}, "repeated_fragment"),
    ],
)
def test_retained_loader_rejects_mistyped_observation_details(
    tmp_path: Path,
    details: dict[str, object],
    field: str,
) -> None:
    """Known detail keys must carry renderer-safe types at the loader."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    output_paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
    result = _issue_summary_result(
        "org/model",
        usability="usable_with_caveats",
        maintainer_status="observation_needs_reproduction",
        observations=["catalog_constraint_violation"],
        details=details,
    )
    check_models._write_text_file(
        output_paths.jsonl,
        json.dumps(_issue_summary_metadata((result,))) + "\n" + json.dumps(result) + "\n",
    )

    with pytest.raises(ValueError, match=f"invalid observation detail {field}"):
        check_models.generate_run_issue_summary_report(output_paths)


def test_retained_loader_permits_unknown_observation_detail_keys(tmp_path: Path) -> None:
    """Forward-compatible detail keys from newer producers must still load."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/model",
        usability="usable_with_caveats",
        maintainer_status="observation_needs_reproduction",
        observations=["catalog_constraint_violation"],
        details={"future_field": {"nested": 1}, "title_word_count": 5},
    )
    _write_issue_summary_fixture(output_paths, results=(result,))

    summary = check_models.generate_run_issue_summary_report(output_paths)

    assert summary is not None


def test_regenerated_summary_restores_baseline_comparison_section(tmp_path: Path) -> None:
    """Regeneration must rehydrate the retained comparison, not silently drop it."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    comparison_payload = _retained_comparison_payload()
    _write_issue_summary_fixture(
        output_paths,
        results=(_issue_summary_result("org/clean"),),
        comparison=comparison_payload,
    )

    generated = check_models.regenerate_run_issue_summary(output_paths.index.parent)

    if generated is None:
        pytest.fail("the retained run must regenerate an issue summary")
    content = generated.read_text(encoding="utf-8")
    assert "Since the baseline sweep" in content
    assert "results.jsonl @ HEAD" in content
    assert "org/clean" in content
    assert "0.980" in content


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        ({"model_provenance": "not a mapping"}, "model provenance"),
        ({"model_provenance": {"model": "org/model", "resolved_revision": []}}, "revision"),
        (
            {
                "model_provenance": {
                    "model": "org/different-model",
                    "requested_revision": None,
                    "resolved_revision": "commit",
                }
            },
            "does not match",
        ),
        ({"failure": "not a mapping"}, "failure"),
        (
            {
                "failure": {
                    "phase": "model_load",
                    "exception_chain": ["not a mapping"],
                }
            },
            "exception chain",
        ),
        (
            {
                "assessment": {
                    "execution": [],
                    "usability": "unusable",
                    "maintainer_status": "observation_needs_reproduction",
                    "observations": [],
                }
            },
            "cached assessment",
        ),
    ],
)
def test_run_issue_summary_rejects_malformed_consumed_result_structures(
    tmp_path: Path,
    replacement: dict[str, object],
    expected: str,
) -> None:
    """Every retained structure dereferenced by the renderer must be validated."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    result = _issue_summary_result(
        "org/model",
        execution="crashed",
        usability="not_evaluated",
        maintainer_status="actionable_failure",
    )
    result.update(replacement)
    _write_issue_summary_fixture(output_paths, results=(result,))

    with pytest.raises(ValueError, match=expected):
        check_models.generate_run_issue_summary_report(output_paths)


def test_run_issue_summary_never_reads_a_sibling_run_json(tmp_path: Path) -> None:
    """results.jsonl is the sole machine source; a stray run.json is inert."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/observed",
                maintainer_status="observation_needs_reproduction",
                observations=["minimal_output"],
            ),
        ),
    )
    stray = output_paths.jsonl.with_name("run.json")
    check_models._write_text_file(stray, '{"image": {"name": "stray-should-not-appear.jpg"}}\n')

    summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "org/observed" in content
    assert "stray-should-not-appear" not in content

    stray.unlink()
    regenerated = check_models.generate_run_issue_summary_report(output_paths)
    assert regenerated is not None
    assert regenerated.read_text(encoding="utf-8") == content


def test_regenerate_run_issue_summary_only_writes_derived_artifact(tmp_path: Path) -> None:
    """Report-only regeneration must leave every retained source byte-identical."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/crash",
                execution="crashed",
                usability="not_evaluated",
                maintainer_status="actionable_failure",
            ),
        ),
    )
    issue_draft = output_paths.index.parent / "issues" / "issue_org_crash.md"
    issue_draft.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(issue_draft, "# Existing crash draft\n")
    retained = {path: path.read_bytes() for path in (output_paths.jsonl, issue_draft)}

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        generated = check_models.regenerate_run_issue_summary(output_paths.index.parent)

    assert generated == output_paths.index.parent / "issues" / "run_summary.md"
    if generated is None:
        pytest.fail("the actionable retained run must regenerate an issue summary")
    assert {path: path.read_bytes() for path in retained} == retained
    crash_draft_url = (
        "https://github.com/jrp2014/check_models/blob/"
        f"{check_models._github_blob_ref()}/src/output/issues/issue_org_crash.md"
    )
    assert f"[crash draft]({crash_draft_url})" in generated.read_text(encoding="utf-8")


def test_html_and_gallery_render_same_captured_peak_memory(tmp_path: Path) -> None:
    """HTML should mirror the GalleryRow peak-memory fact without another projection."""
    result = PerformanceResult(
        model_name="test/model",
        generation=_MockGeneration(peak_memory=1.0),
        success=True,
    )
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
        recommended_working_set_bytes=2_000_000_000,
    )
    html_path = tmp_path / "results.html"
    gallery_path = tmp_path / "gallery.md"

    generate_html_report(
        [result],
        html_path,
        _stub_versions(),
        "Describe the image.",
        1.0,
        report_context=context,
    )
    generate_markdown_gallery_report(
        [result],
        gallery_path,
        "Describe the image.",
        report_context=context,
        versions=_stub_versions(),
    )

    html_text = html_path.read_text(encoding="utf-8")
    assert "<td>Peak memory</td>\n<td>1.0</td>" in html_text
    assert "recommended working set" not in html_text
    assert "*Peak memory:* 1.0" in gallery_path.read_text(encoding="utf-8")


def test_markdown_gallery_publishes_reference_image_beside_report(tmp_path: Path) -> None:
    image_path = tmp_path / "input.jpg"
    Image.new("RGB", (2048, 1024), color="purple").save(image_path)
    gallery_path = tmp_path / "reports" / "model_gallery.md"
    result = _make_success("org/model")
    context = _build_report_render_context(results=[result], prompt="Describe the image.")

    generate_markdown_gallery_report(
        [result],
        gallery_path,
        "Describe the image.",
        report_context=context,
        image_path=image_path,
    )

    # The asset is named by the digest of its bytes so later sweeps never
    # replace it (pasted reproduction commands keep verifying).
    raw_preview = check_models._report_image_preview(image_path)
    assert raw_preview is not None
    asset_name = check_models._preview_asset_name(raw_preview[0], raw_preview[2])
    assert asset_name.startswith("source-image-")
    assert f"![Reference image](assets/{asset_name})" in gallery_path.read_text(encoding="utf-8")
    with Image.open(gallery_path.parent / "assets" / asset_name) as preview:
        assert preview.size == (1024, 512)


def test_markdown_gallery_does_not_follow_reference_asset_symlink(tmp_path: Path) -> None:
    image_path = tmp_path / "input.jpg"
    Image.new("RGB", (16, 8), color="purple").save(image_path)
    gallery_path = tmp_path / "reports" / "model_gallery.md"
    raw_preview = check_models._report_image_preview(image_path)
    assert raw_preview is not None
    asset = (
        gallery_path.parent
        / "assets"
        / check_models._preview_asset_name(raw_preview[0], raw_preview[2])
    )
    asset.parent.mkdir(parents=True)
    victim = tmp_path / "victim.jpg"
    victim.write_bytes(b"keep-me")
    asset.symlink_to(victim)
    # A legacy un-suffixed asset that is a symlink is left alone, never
    # followed or unlinked on the writer's behalf.
    legacy = gallery_path.parent / "assets" / "source-image.jpg"
    legacy.symlink_to(victim)
    result = _make_success("org/model")

    generate_markdown_gallery_report(
        [result],
        gallery_path,
        "Describe the image.",
        report_context=_build_report_render_context(
            results=[result],
            prompt="Describe the image.",
        ),
        image_path=image_path,
    )

    assert victim.read_bytes() == b"keep-me"
    assert "![Reference image]" not in gallery_path.read_text(encoding="utf-8")
    assert legacy.is_symlink()


def _extract_markdown_subsection(
    content: str,
    heading: str,
    *,
    end_headings: Sequence[str],
) -> str:
    start = content.index(heading)
    end_positions = [
        content.find(candidate, start + len(heading))
        for candidate in end_headings
        if content.find(candidate, start + len(heading)) != -1
    ]
    end = min(end_positions) if end_positions else len(content)
    return content[start:end]


def _extract_markdown_model_section(content: str, model_name: str) -> str:
    """Return one model's heading-scoped section without crossing into another model."""
    match = re.search(
        rf"(?ms)^### {re.escape(model_name)}\n.*?(?=^### |^## |\Z)",
        content,
    )
    assert match is not None, f"Missing Markdown section for {model_name}"
    return match.group(0)


def _extract_markdown_diagnostic_entry(content: str, model_name: str) -> str:
    """Return one diagnostics entry through its triage-table evidence link."""
    link = re.search(rf"\[{re.escape(model_name)}\]\(#([^)]+)\)", content)
    assert link is not None, f"Missing diagnostics link for {model_name}"
    marker = f'<a id="{link.group(1)}"></a>'
    start = content.index(marker)
    tail = content[start + len(marker) :]
    boundaries = [
        index for token in ('<a id="diagnostic-', "\n## ") if (index := tail.find(token)) >= 0
    ]
    end = start + len(marker) + min(boundaries) if boundaries else len(content)
    return content[start:end]


_GENERATED_STAMP_EMPHASIS_HEADING_RE = re.compile(
    r"(?m)^_(?:Generated on|Report generated on).+_$",
)
_MARKDOWN_LINK_TARGET_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_URL_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_PUBLISHED_OUTPUT_GITHUB_TARGET_RE = re.compile(
    rf"^{re.escape(check_models._GITHUB_REPO_URL)}/(?:blob|tree)/"
    rf"(?:{re.escape(check_models._GITHUB_DEFAULT_BRANCH)}|[0-9a-f]{{7,40}})/"
    r"src/output(?:/|$)"
)


def _assert_no_generated_stamp_emphasis_headings(content: str) -> None:
    """Generated timestamp metadata should not trip markdownlint MD036."""
    assert _GENERATED_STAMP_EMPHASIS_HEADING_RE.search(content) is None


def _extract_markdown_link_targets(content: str) -> list[str]:
    """Return Markdown link targets from one generated artifact."""
    return [match.group(1) for match in _MARKDOWN_LINK_TARGET_RE.finditer(content)]


def _is_relative_markdown_target(target: str) -> bool:
    """Return True for non-anchor Markdown targets without a URL scheme."""
    return not target.startswith("#") and _URL_SCHEME_RE.match(target) is None


def _is_published_output_github_target(target: str) -> bool:
    """Return True for canonical GitHub links into this repo's published output tree."""
    return _PUBLISHED_OUTPUT_GITHUB_TARGET_RE.match(target.split("#", 1)[0]) is not None


def test_custom_published_index_and_issue_drafts_use_distinct_repo_paths(
    tmp_path: Path,
) -> None:
    """A retained index must publish at the output root while drafts stay under issues."""
    custom_index = tmp_path / "custom-run" / "index.md"
    issue_draft = tmp_path / "custom-run" / "issues" / "issue_org_model.md"

    index_path = check_models._published_output_repo_path(custom_index)
    issue_path = check_models._published_output_repo_path(issue_draft)

    assert index_path is not None
    assert issue_path is not None
    assert index_path.as_posix() == "src/output/index.md"
    assert issue_path.as_posix() == "src/output/issues/issue_org_model.md"


def _all_artifacts(
    output_paths: check_models.ReportOutputPaths,
) -> tuple[check_models.ReportArtifact, ...]:
    """Return the full artifact plan for tests that assume a fully successful run."""
    inputs = check_models.ReportGenerationInputs(
        results=[],
        library_versions={},
        prompt="p",
        metadata=None,
        overall_time=0.0,
        image_path=None,
        system_info={},
        report_context=_build_report_render_context(results=[], prompt="p"),
        output_paths=output_paths,
    )
    return check_models._build_report_artifacts(inputs)


def _all_success_outcomes(
    artifacts: tuple[check_models.ReportArtifact, ...],
) -> tuple[check_models.ReportArtifactOutcome, ...]:
    return tuple(
        check_models.ReportArtifactOutcome(key=a.key, path=a.path, succeeded=True)
        for a in artifacts
    )


def test_output_index_links_only_current_run_artifacts(tmp_path: Path) -> None:
    """The tiny index should link current evidence, not history or retired reports."""
    output_dir = tmp_path / "output"
    output_paths = check_models.ReportOutputPaths(
        index=output_dir / "index.md",
        html=output_dir / "reports" / "results.html",
        gallery_markdown=output_dir / "reports" / "model_gallery.md",
        jsonl=output_dir / "results.jsonl",
        diagnostics=output_dir / "reports" / "diagnostics.md",
        log=output_dir / "check_models.log",
        environment=output_dir / "environment.log",
    )

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        check_models.generate_output_index_report(
            output_paths.index, artifacts=_all_artifacts(output_paths)
        )

    objective_lines = "".join(
        f"{line}\n"
        for line in check_models._wrap_markdown_text(check_models._run_objective_statement(None))
    )
    assert output_paths.index.read_text(encoding="utf-8") == (
        "# Check Models Output Index\n"
        "\n"
        "Assessment: Legacy assessment; profile not recorded\n\n"
        f"{objective_lines}"
        "\n"
        "- [results.html](reports/results.html)\n"
        "- [model_gallery.md](reports/model_gallery.md)\n"
        "- [diagnostics.md](reports/diagnostics.md)\n"
        "- [results.jsonl](results.jsonl)\n"
        "- [check_models.log](check_models.log)\n"
        "- [environment.log](environment.log)\n"
    )


def test_tracked_artifacts_publish_canonical_repo_paths(tmp_path: Path) -> None:
    """Every linked artifact resolves to its canonical tracked repo path."""
    for name in (
        "check_models.log",
        "reports/diagnostics.md",
        "reports/model_gallery.md",
        "reports/results.html",
    ):
        tracked = check_models._REPO_ROOT / "src" / "output" / name
        tracked_path = check_models._published_output_repo_path(tracked)
        assert tracked_path is not None
        assert tracked_path.as_posix() == f"src/output/{name}"
    # Unknown names outside the repo tree stay unpublished (relative links).
    assert check_models._published_output_repo_path(tmp_path / "scratch.txt") is None


def test_output_index_links_current_run_issue_drafts_in_model_order(tmp_path: Path) -> None:
    """The output index should expose only the issue paths produced for this run."""
    output_dir = tmp_path / "output"
    output_paths = check_models.ReportOutputPaths(
        index=output_dir / "index.md",
        html=output_dir / "reports" / "results.html",
        gallery_markdown=output_dir / "reports" / "model_gallery.md",
        jsonl=output_dir / "results.jsonl",
        diagnostics=output_dir / "reports" / "diagnostics.md",
        log=output_dir / "check_models.log",
        environment=output_dir / "environment.log",
    )
    issue_reports = {
        "org/z": output_dir / "issues" / "issue_org_z.md",
        "org/a": output_dir / "issues" / "issue_org_a.md",
    }

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        check_models.generate_output_index_report(
            output_paths.index,
            artifacts=_all_artifacts(output_paths),
            issue_reports=issue_reports,
        )

    content = output_paths.index.read_text(encoding="utf-8")
    assert "## Issue drafts" in content
    assert "[org/a](issues/issue_org_a.md)" in content
    assert "[org/z](issues/issue_org_z.md)" in content
    assert content.index("[org/a]") < content.index("[org/z]")


def test_output_index_renders_run_dashboard(tmp_path: Path) -> None:
    """The index should lead with run counts, usability, and top observations."""
    output_dir = tmp_path / "output"
    output_paths = check_models.ReportOutputPaths(
        index=output_dir / "index.md",
        html=output_dir / "reports" / "results.html",
        gallery_markdown=output_dir / "reports" / "model_gallery.md",
        jsonl=output_dir / "results.jsonl",
        diagnostics=output_dir / "reports" / "diagnostics.md",
        log=output_dir / "check_models.log",
        environment=output_dir / "environment.log",
    )
    assessments = (
        ("org/good", check_models.ResultAssessment("completed", "usable", "none", ())),
        (
            "org/warn",
            check_models.ResultAssessment(
                "completed",
                "usable_with_caveats",
                "observation_needs_reproduction",
                ("minimal_output",),
            ),
        ),
        (
            "org/crash",
            check_models.ResultAssessment("crashed", "not_evaluated", "actionable_failure", ()),
        ),
    )

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        check_models.generate_output_index_report(
            output_paths.index,
            artifacts=_all_artifacts(output_paths),
            assessments=assessments,
        )

    content = output_paths.index.read_text(encoding="utf-8")
    assert "## Run at a glance" in content
    assert "- Models attempted: 3 (completed 2, crashed 1, indeterminate 0)" in content
    assert (
        "- Mechanical checks: no concerns detected 1, concerns detected 1, major concerns 0, "
        "not assessed 1" in content
    )
    assert "- Usability:" not in content
    minimal_label = check_models._OBSERVATION_DISPLAY_LABELS["minimal_output"]
    assert f"- Top observations: {minimal_label} (1)" in content
    assert "## Artifacts" in content
    assert content.index("## Run at a glance") < content.index("## Artifacts")


def test_run_issue_summary_link_caveat_reflects_blob_ref(tmp_path: Path) -> None:
    """The link caveat must say pinned for SHA refs and mutable for branch refs."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/observed",
                usability="usable_with_caveats",
                maintainer_status="observation_needs_reproduction",
                observations=["minimal_output"],
            ),
        ),
        total_runtime_seconds=120.0,
    )

    pinned_sha = "a" * 40
    with patch.object(check_models, "_GITHUB_REF_OVERRIDE", pinned_sha):
        summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    pinned_content = summary.read_text(encoding="utf-8")
    assert f"pinned to producer commit `{pinned_sha[:12]}`" in pinned_content
    assert "mutable" not in pinned_content

    with patch.object(check_models, "_GITHUB_REF_OVERRIDE", "main"):
        summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    branch_content = summary.read_text(encoding="utf-8")
    assert "mutable main branch" in branch_content
    assert "pinned to producer commit" not in branch_content


def _report_outcome(
    outcomes: Sequence[check_models.ReportArtifactOutcome],
    key: str,
) -> check_models.ReportArtifactOutcome:
    """Return one named report outcome for concise orchestration assertions."""
    return next(outcome for outcome in outcomes if outcome.key == key)


def _report_generation_inputs(
    tmp_path: Path,
    *,
    result: check_models.PerformanceResult,
) -> check_models.ReportGenerationInputs:
    """Build minimal orchestration inputs writing under tmp_path only."""
    args = Namespace(
        output_dir=tmp_path / "output",
        compare_with="none",
    )
    context = _build_report_render_context(results=[result], prompt="Describe the image.")
    return check_models.ReportGenerationInputs(
        results=[result],
        library_versions=_stub_versions(),
        prompt="Describe the image.",
        metadata=None,
        overall_time=1.0,
        image_path=None,
        system_info={},
        report_context=context,
        output_paths=check_models._resolve_report_output_paths(args),
        run_args=args,
        runtime_fingerprint={},
    )


def test_report_artifact_key_error_is_contained(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unexpected renderer defect becomes a failed outcome, never an escape."""
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    with (
        patch.object(check_models._LinkStyleState, "value", "relative"),
        patch.object(
            check_models,
            "generate_html_report",
            side_effect=KeyError("unexpected renderer field"),
        ),
    ):
        outcomes = check_models._generate_reports_and_log_outputs(inputs)

    html_outcome = _report_outcome(outcomes, "html")
    assert html_outcome.succeeded is False
    assert "unexpected renderer field" in (html_outcome.error_message or "")
    assert _report_outcome(outcomes, "jsonl").succeeded is True
    assert inputs.output_paths.jsonl.is_file()
    assert "Failed to generate html report" in caplog.text


def test_report_diagnostics_and_summary_key_errors_are_contained(
    tmp_path: Path,
) -> None:
    """Diagnostics and summary boundaries also contain unexpected exceptions."""
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    with (
        patch.object(check_models._LinkStyleState, "value", "relative"),
        patch.object(
            check_models,
            "_write_diagnostics_artifacts",
            side_effect=KeyError("diagnostics defect"),
        ),
        patch.object(
            check_models,
            "generate_run_issue_summary_report",
            side_effect=KeyError("summary defect"),
        ),
    ):
        outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert _report_outcome(outcomes, "diagnostics").succeeded is False
    assert _report_outcome(outcomes, "jsonl").succeeded is True


def test_unexpected_comparison_error_degrades_to_no_comparison(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A comparison implementation defect skips comparison rather than the run."""
    report_inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    current = check_models.RetainedRun(
        metadata=cast("check_models.JsonlMetadataRecord", {}), results=()
    )
    with (
        patch.object(check_models, "_resolve_comparison_baseline", return_value=object()),
        patch.object(check_models, "compare_run_results", side_effect=KeyError("bad diff")),
    ):
        comparison = check_models._compute_run_comparison(report_inputs, current)

    assert comparison is None
    assert "Comparison skipped" in caplog.text


def test_comparison_rendering_failure_does_not_block_reports(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A crash while displaying the comparison degrades to no comparison."""
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    inputs = replace(inputs, run_args=replace_namespace(inputs.run_args, compare_with="auto"))
    with (
        patch.object(
            check_models,
            "_compute_run_comparison",
            return_value=check_models.RunComparison.__new__(check_models.RunComparison),
        ),
        patch.object(
            check_models,
            "_log_run_comparison",
            side_effect=KeyError("broken comparison view"),
        ),
    ):
        outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert _report_outcome(outcomes, "jsonl").succeeded is True
    assert inputs.output_paths.index.is_file()
    assert "Comparison skipped: unexpected comparison rendering failure" in caplog.text


def replace_namespace(args: object, **overrides: object) -> Namespace:
    """Copy a Namespace with overrides (argparse has no replace helper)."""
    merged = vars(args).copy()
    merged.update(overrides)
    return Namespace(**merged)


def test_stale_environment_log_is_not_presented_as_current(tmp_path: Path) -> None:
    """environment.log outcomes require this run's explicit write signal."""
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    inputs.output_paths.environment.parent.mkdir(parents=True, exist_ok=True)
    inputs.output_paths.environment.write_text("stale dump from an earlier run", encoding="utf-8")

    outcomes = check_models._generate_reports_and_log_outputs(inputs)
    assert all(outcome.key != "environment" for outcome in outcomes)

    inputs = replace(inputs, run_args=replace_namespace(inputs.run_args, environment_logged=True))
    outcomes = check_models._generate_reports_and_log_outputs(inputs)
    environment = next(outcome for outcome in outcomes if outcome.key == "environment")
    assert environment.succeeded is True


def test_failed_current_artifact_is_omitted_from_navigation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale file surviving a failed renderer is not current and is not linked."""
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    inputs.output_paths.html.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(inputs.output_paths.html, "stale html")

    with (
        patch.object(check_models._LinkStyleState, "value", "relative"),
        patch.object(check_models, "generate_html_report", side_effect=KeyError("html failed")),
    ):
        outcomes = check_models._generate_reports_and_log_outputs(inputs)

    index = inputs.output_paths.index.read_text(encoding="utf-8")
    assert "results.html" not in index
    assert "model_gallery.md" in index
    capsys.readouterr()  # drain orchestration logging before the dashboard
    check_models._print_reports_dashboard(
        check_models._build_report_artifacts(inputs),
        outcomes,
        history_path=None,
    )
    captured = capsys.readouterr()
    assert "HTML Report" not in captured.err + captured.out
    assert "Gallery Report" in captured.err + captured.out


def test_retained_manifest_reflects_report_outcomes_and_final_duration(tmp_path: Path) -> None:
    """The JSONL header lists only produced artifacts and an end-to-end duration.

    The pre-report header advertises every planned destination; after a
    renderer fails (leaving a stale file) the sole machine contract must agree
    with index.md, and its duration must include report generation.
    """
    inputs = _report_generation_inputs(tmp_path, result=_make_success("org/model"))
    start = 1_700_000_000.0
    inputs = replace(inputs, overall_start_time=start, overall_time=10.0)
    inputs.output_paths.html.parent.mkdir(parents=True, exist_ok=True)
    check_models._write_text_file(inputs.output_paths.html, "stale html")
    clock = {"now": start + 10.0}

    def slow_failing_html(*_args: object, **_kwargs: object) -> None:
        clock["now"] += 300.0
        message = "html failed"
        raise KeyError(message)

    with (
        patch.object(check_models.time, "time", lambda: clock["now"]),
        patch.object(check_models._LinkStyleState, "value", "relative"),
        patch.object(check_models, "generate_html_report", side_effect=slow_failing_html),
    ):
        check_models._generate_reports_and_log_outputs(inputs)

    header = json.loads(inputs.output_paths.jsonl.read_text(encoding="utf-8").splitlines()[0])
    # Outside the tracked src/output tree the manifest carries publication-safe
    # absolute text, so assert on the retained suffixes rather than exact paths.
    assert "results_html" not in header["artifacts"]
    assert header["artifacts"]["model_gallery"].endswith("reports/model_gallery.md")
    assert header["artifacts"]["results_jsonl"].endswith("results.jsonl")
    assert header["artifacts"]["output_index"].endswith("index.md")
    assert header["total_runtime_seconds"] >= 310.0


def test_report_orchestration_passes_generated_issue_drafts_to_index(tmp_path: Path) -> None:  # noqa: PLR0915 - exercises the full artifact fan-out twice
    """Final report orchestration should index the drafts generated by diagnostics."""
    args = Namespace(
        output_dir=tmp_path / "output",
    )
    result = _make_failure_with_details(
        "org/broken",
        error_msg="Model loading failed: boom",
        failure_phase="model_load",
        traceback_str="Traceback (most recent call last):\nValueError: boom",
    )
    context = _build_report_render_context(results=[result], prompt="Describe the image.")
    output_paths = check_models._resolve_report_output_paths(args)
    inputs = check_models.ReportGenerationInputs(
        results=[result],
        library_versions=_stub_versions(),
        prompt="Describe the image.",
        metadata=None,
        overall_time=1.0,
        image_path=None,
        system_info={},
        report_context=context,
        output_paths=output_paths,
        run_args=args,
        runtime_fingerprint={},
    )

    with patch.object(check_models._LinkStyleState, "value", "relative"):
        outcomes = check_models._generate_reports_and_log_outputs(inputs)

    index_content = output_paths.index.read_text(encoding="utf-8")
    summary_path = output_paths.index.parent / "issues" / "run_summary.md"
    assert "[Run summary](issues/run_summary.md)" in index_content
    assert "[org/broken](issues/issue_org_broken.md)" in index_content
    assert index_content.index("[Run summary]") < index_content.index("[org/broken]")
    assert _report_outcome(outcomes, "run_issue_summary").succeeded

    with patch.object(
        check_models,
        "generate_run_issue_summary_report",
        side_effect=ValueError("summary fixture failure"),
    ):
        failed_summary_outcomes = check_models._generate_reports_and_log_outputs(inputs)

    failed_summary = _report_outcome(failed_summary_outcomes, "run_issue_summary")
    assert not failed_summary.succeeded
    assert failed_summary.error_message == "summary fixture failure"
    assert all(
        path.exists()
        for path in (
            output_paths.index,
            output_paths.html,
            output_paths.gallery_markdown,
            output_paths.jsonl,
            output_paths.diagnostics,
        )
    )
    assert not summary_path.exists()

    check_models._write_text_file(summary_path, "stale prior-run summary\n")
    with (
        patch.object(
            check_models,
            "_write_retained_run",
            side_effect=OSError("current JSONL write failed"),
        ),
        patch.object(
            check_models,
            "generate_run_issue_summary_report",
            side_effect=AssertionError("summary must not read stale JSONL"),
        ),
    ):
        stale_jsonl_outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert not summary_path.exists()
    assert not _report_outcome(stale_jsonl_outcomes, "jsonl").succeeded

    check_models._write_text_file(summary_path, "undeletable stale summary\n")
    cleanup_error = PermissionError("summary cleanup denied")
    with (
        patch.object(
            check_models,
            "_write_retained_run",
            side_effect=OSError("current JSONL write failed"),
        ),
        patch.object(check_models, "_remove_run_issue_summary", return_value=cleanup_error),
    ):
        cleanup_failure_outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert summary_path.exists()
    assert "run_summary.md" not in output_paths.index.read_text(encoding="utf-8")
    cleanup_failure = _report_outcome(cleanup_failure_outcomes, "run_issue_summary")
    assert not cleanup_failure.succeeded
    assert "cleanup denied" in (cleanup_failure.error_message or "")

    check_models._write_text_file(summary_path, "stale prior-run summary\n")
    check_models._write_text_file(output_paths.diagnostics, "stale prior-run diagnostics\n")
    with (
        patch.object(
            check_models,
            "_write_diagnostics_artifacts",
            side_effect=OSError("current diagnostics write failed"),
        ),
        patch.object(
            check_models,
            "generate_run_issue_summary_report",
            side_effect=AssertionError("summary must not link stale diagnostics"),
        ),
    ):
        stale_diagnostics_outcomes = check_models._generate_reports_and_log_outputs(inputs)

    assert not summary_path.exists()
    assert "run_summary.md" not in output_paths.index.read_text(encoding="utf-8")
    assert not _report_outcome(stale_diagnostics_outcomes, "diagnostics").succeeded
    stale_diagnostics_summary = _report_outcome(
        stale_diagnostics_outcomes,
        "run_issue_summary",
    )
    assert not stale_diagnostics_summary.succeeded
    assert "diagnostics" in (stale_diagnostics_summary.error_message or "").lower()

    check_models._write_text_file(
        output_paths.gallery_markdown,
        "stale prior-run gallery\n",
    )
    with patch.object(
        check_models,
        "generate_markdown_gallery_report",
        side_effect=OSError("current gallery write failed"),
    ):
        stale_gallery_outcomes = check_models._generate_reports_and_log_outputs(inputs)

    stale_gallery_summary = summary_path.read_text(encoding="utf-8")
    assert "model_gallery.md" not in stale_gallery_summary
    assert "full model gallery" not in stale_gallery_summary
    assert not _report_outcome(stale_gallery_outcomes, "markdown_gallery").succeeded
    assert _report_outcome(stale_gallery_outcomes, "run_issue_summary").succeeded


def test_report_dashboard_only_shows_current_successful_run_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An existing stale summary must stay hidden unless this run produced it."""
    output_paths = _issue_summary_output_paths(tmp_path / "output")
    stale_summary = output_paths.index.parent / "issues" / "run_summary.md"
    check_models._write_text_file(stale_summary, "stale\n")

    artifacts = _all_artifacts(output_paths)
    outcomes = _all_success_outcomes(artifacts)
    check_models._print_reports_dashboard(artifacts, outcomes, run_issue_summary=None)
    without_summary = capsys.readouterr().err
    check_models._print_reports_dashboard(
        artifacts,
        outcomes,
        run_issue_summary=stale_summary,
    )
    with_summary = capsys.readouterr().err

    assert "Run Issue Summary" not in without_summary
    assert "Run Issue Summary" in with_summary


def _relative_output_artifact_map(
    output_dir: Path,
    output_paths: check_models.ReportOutputPaths,
) -> dict[str, str]:
    """Return the retained artifact manifest rooted at one output directory."""
    return {
        "output_index": output_paths.index.relative_to(output_dir).as_posix(),
        "results_html": output_paths.html.relative_to(output_dir).as_posix(),
        "model_gallery": output_paths.gallery_markdown.relative_to(output_dir).as_posix(),
        "diagnostics": output_paths.diagnostics.relative_to(output_dir).as_posix(),
        "results_jsonl": output_paths.jsonl.relative_to(output_dir).as_posix(),
        "log": output_paths.log.relative_to(output_dir).as_posix(),
        "environment": output_paths.environment.relative_to(output_dir).as_posix(),
    }


def _generate_output_artifacts_for_link_style(
    tmp_path: Path,
    *,
    link_style: str,
) -> tuple[Path, check_models.ReportOutputPaths, list[Path]]:
    """Generate the retained artifact set for one link style."""
    output_dir = tmp_path / link_style / "output"
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    prompt = "Describe this image briefly."
    versions = _stub_versions()
    system_info = {"Python Version": "3.13"}
    results = [
        _make_success("org/good"),
        _make_failure_with_details(
            "org/broken",
            error_msg="Model loading failed: boom",
            failure_phase="model_load",
            traceback_str="Traceback (most recent call last):\nValueError: boom",
        ),
    ]
    report_context = _build_report_render_context(results=results, prompt=prompt)
    output_paths = check_models.ReportOutputPaths(
        index=output_dir / "index.md",
        html=reports_dir / "results.html",
        gallery_markdown=reports_dir / "model_gallery.md",
        jsonl=output_dir / "results.jsonl",
        diagnostics=reports_dir / "diagnostics.md",
        log=output_dir / "check_models.log",
        environment=output_dir / "environment.log",
    )
    with patch.object(check_models._LinkStyleState, "value", link_style):
        generate_html_report(
            results=results,
            filename=output_paths.html,
            versions=versions,
            prompt=prompt,
            total_runtime_seconds=1.0,
            report_context=report_context,
        )
        generate_markdown_gallery_report(
            results=results,
            filename=output_paths.gallery_markdown,
            prompt=prompt,
            report_context=report_context,
        )
        generate_diagnostics_report(
            results,
            output_paths.diagnostics,
            prompt=prompt,
            library_versions=versions,
            system_info=system_info,
            report_context=report_context,
        )
        check_models.save_jsonl_report(
            results=results,
            filename=output_paths.jsonl,
            prompt=prompt,
            system_info=system_info,
            library_versions=versions,
            report_context=report_context,
            total_runtime_seconds=1.0,
            artifacts=_relative_output_artifact_map(output_dir, output_paths),
        )
        issue_reports = _generate_github_issue_reports(
            report_context=report_context,
            output_dir=output_dir,
            library_versions=versions,
            system_info=system_info,
            prompt=prompt,
        )
        check_models.generate_output_index_report(
            output_paths.index,
            artifacts=_all_artifacts(output_paths),
            issue_reports=issue_reports,
        )

    return output_dir, output_paths, sorted(output_dir.rglob("*.md"))


def _make_success(name: str = "org/model-ok") -> PerformanceResult:
    return PerformanceResult(
        model_name=name,
        success=True,
        generation=_MockGeneration(
            text=(
                "Title: Brick storefront with outdoor seating\n"
                "Description: A brick storefront has outdoor seating beside a sidewalk. "
                "People sit outside under clear daylight.\n"
                "Keywords: brick storefront, outdoor seating, sidewalk, people, daylight, "
                "sign, windows, street, town, facade"
            ),
            prompt_tokens=120,
            generation_tokens=48,
        ),
        total_time=1.0,
        generation_time=0.5,
        model_load_time=0.5,
    )


def _make_failure(
    name: str = "org/model-fail",
    error_type: str = "ValueError",
    error_package: str = "mlx-vlm",
) -> PerformanceResult:
    return PerformanceResult(
        model_name=name,
        success=False,
        generation=None,
        error_stage="load",
        error_message="boom",
        error_type=error_type,
        error_package=error_package,
        upstream_boundary="generation_started",
    )


def _make_failure_with_details(
    name: str = "org/model-fail",
    *,
    error_msg: str = "boom",
    error_type: str = "ValueError",
    error_package: str = "mlx-vlm",
    error_stage: str = "Model Error",
    failure_phase: str | None = None,
    traceback_str: str | None = None,
    captured_output: str | None = None,
    generated_text: str | None = None,
    upstream_boundary: ExpectedUpstreamBoundary = "generation_started",
) -> PerformanceResult:
    """Create a failure result with full error details for diagnostics tests."""
    generation = (
        _MockGeneration(text=generated_text, prompt_tokens=32, generation_tokens=16)
        if generated_text is not None
        else None
    )
    return PerformanceResult(
        model_name=name,
        success=False,
        generation=generation,
        error_stage=error_stage,
        failure_phase=failure_phase,
        error_message=error_msg,
        error_type=error_type,
        error_package=error_package,
        captured_output_on_fail=captured_output,
        error_traceback=traceback_str,
        upstream_boundary=upstream_boundary,
    )


def _make_quality_success(
    name: str,
    *,
    with_quality_issue: bool,
) -> PerformanceResult:
    """Create a successful result with explicit quality analysis state."""
    qa = GenerationQualityAnalysis(
        is_repetitive=False,
        repeated_token=None,
        word_count=20,
        prompt_checks_ran=True,
        unexpected_special_tokens=["<|unexpected|>"] if with_quality_issue else [],
    )
    return PerformanceResult(
        model_name=name,
        success=True,
        generation=_MockGeneration(
            text="quality output",
            prompt_tokens=120,
            generation_tokens=80,
        ),
        total_time=1.0,
        generation_time=0.6,
        model_load_time=0.4,
        quality_analysis=qa,
    )


def test_report_context_caches_only_live_cross_artifact_views() -> None:
    """The shared context should retain only current-run factual assessments."""
    failed = _make_failure("org/crashed")
    passed = _make_success("org/passed")

    context = _build_report_render_context(
        results=[failed, passed],
        prompt="Describe the image.",
        eval_mode="blind",
    )

    assert [model for model, _assessment in context.assessments] == [
        "org/crashed",
        "org/passed",
    ]
    assert not hasattr(context, "recommendations")
    assert not hasattr(context, "triage")
    assert not hasattr(context, "machine_facts")
    assert not hasattr(context, "diagnostics_snapshot")
    assert not hasattr(context, "issue_clusters")


def test_all_caveated_html_omits_cataloging_aggregates_and_winner(
    tmp_path: Path,
) -> None:
    """An all-caveat run should retain evidence without semantic aggregates."""
    warning = _make_harness_success(
        "org/warning-only",
        text=getattr(_make_success().generation, "text", "") or "",
        prompt_tokens=120,
        generation_tokens=48,
        harness_detail="token_leak:<|endoftext|>",
    )
    context = _build_report_render_context(
        results=[warning],
        prompt="Create title, description, and keywords.",
        metadata={"description": "Brick storefront", "keywords": "storefront"},
        eval_mode="blind",
    )
    html_path = tmp_path / "results.html"

    generate_html_report(
        [warning],
        html_path,
        versions={},
        prompt="Create title, description, and keywords.",
        total_runtime_seconds=1.0,
        report_context=context,
    )

    html_text = html_path.read_text(encoding="utf-8")
    assert "org/warning-only" in html_text
    assert "Cataloging Utility Summary" not in html_text
    assert "Best for cataloging" not in html_text


def test_chained_failure_retains_exact_exception_chain() -> None:
    failure = replace(
        _make_failure("org/chained", error_package="mlx"),
        exception_chain=(
            check_models.FailureException(
                "IndexError",
                "builtins",
                "token index outside detokenizer table",
                origin="mlx_vlm/tokenizer_utils.py",
            ),
            check_models.FailureException(
                "RuntimeError",
                "mlx.core",
                "kIOGPUCommandBufferCallbackErrorOutOfMemory",
                origin="mlx/core/metal.cpp",
            ),
        ),
    )

    assert [entry.exception_type for entry in failure.exception_chain] == [
        "IndexError",
        "RuntimeError",
    ]
    assert [entry.module for entry in failure.exception_chain] == ["builtins", "mlx.core"]


def test_published_failure_artifacts_do_not_disclose_home_paths() -> None:
    """Tracked human reports should not disclose publication-private home paths."""
    output_dir = Path(__file__).parents[1] / "output"
    tracked = (
        output_dir / "reports/diagnostics.md",
        output_dir / "reports/model_gallery.md",
        output_dir / "reports/results.html",
    )
    for artifact in tracked:
        assert str(Path.home()) not in artifact.read_text(encoding="utf-8"), artifact


def test_public_failure_evidence_sanitizes_paths_without_mutating_model_text(
    tmp_path: Path,
) -> None:
    """Public operational evidence is portable while generated text stays exact."""
    generated_text = "Model says /Users/alice/source and /private/cache exactly."
    success = replace(
        _make_success("org/generated-paths"),
        generation=_MockGeneration(text=generated_text, generation_tokens=20),
    )
    crash = replace(
        _make_failure_with_details(
            "org/crash-paths",
            error_msg="failed under /Users/alice/project/model.py using /private/tmp/cache",
            traceback_str=(
                "Traceback (most recent call last):\n"
                '  File "/Users/alice/project/model.py", line 7, in run\n'
                "RuntimeError: cache /private/tmp/cache failed"
            ),
            captured_output=(
                "stderr from /Users/alice/project/model.py\nprivate=/private/tmp/cache"
            ),
        ),
        root_error_message="root at /Users/alice/project/model.py",
        exception_chain=(
            check_models.FailureException(
                "RuntimeError",
                "builtins",
                "cache /private/tmp/cache failed",
                origin="/Users/alice/project/model.py",
            ),
        ),
    )
    results = [success, crash]
    provenance: dict[str, check_models.ModelProvenanceRecord] = {
        result.model_name: check_models.ModelProvenanceRecord(
            model=result.model_name,
            requested_revision=None,
            resolved_revision="sha",
            snapshot_path="/Users/alice/.cache/models/snapshots/sha",
        )
        for result in results
    }
    context = _build_report_render_context(
        results=results,
        prompt="Describe the image.",
        system_info={},
        model_provenance=provenance,
    )
    gallery_path = tmp_path / "model_gallery.md"
    diagnostics_path = tmp_path / "diagnostics.md"
    html_path = tmp_path / "results.html"
    jsonl_path = tmp_path / "results.jsonl"

    generate_markdown_gallery_report(
        results,
        gallery_path,
        prompt="Describe the image.",
        report_context=context,
    )
    generate_diagnostics_report(
        results,
        diagnostics_path,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={},
        report_context=context,
    )
    generate_html_report(
        results,
        html_path,
        _stub_versions(),
        "Describe the image.",
        1.0,
        report_context=context,
    )
    check_models.save_jsonl_report(
        results,
        jsonl_path,
        prompt="Describe the image.",
        system_info={},
        report_context=context,
        total_runtime_seconds=1.0,
        artifacts={
            "external": "/Users/alice/published/results.html",
            "private": "/private/tmp/results.jsonl",
        },
    )

    gallery = gallery_path.read_text(encoding="utf-8")
    diagnostics = diagnostics_path.read_text(encoding="utf-8")
    html_report = html.unescape(html_path.read_text(encoding="utf-8"))
    crash_gallery = _extract_markdown_model_section(gallery, crash.model_name)
    assert generated_text in gallery
    assert generated_text in html_report
    for crash_evidence in (crash_gallery, diagnostics):
        assert "/Users/alice/" not in crash_evidence
        assert "/private/" not in crash_evidence
        assert "~/project/model.py" in crash_evidence
        assert "<private>/tmp/cache" in crash_evidence
    crash_html_match = re.search(
        r'<article id="model-org-crash-paths".*?</article>',
        html_report,
        re.DOTALL,
    )
    assert crash_html_match is not None
    crash_html_articles = crash_html_match.group(0)
    assert "/Users/alice/" not in crash_html_articles
    assert "/private/" not in crash_html_articles

    records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    rows = {record["model"]: record for record in records if record.get("_type") == "result"}
    assert rows[success.model_name]["generated_text"] == generated_text
    crash_row = rows[crash.model_name]
    assert "/Users/alice/" not in json.dumps(crash_row)
    assert "/private/" not in json.dumps(crash_row)
    assert crash_row["failure"]["exception_chain"][0]["origin"] == "~/project/model.py"
    header = records[0]
    assert header["artifacts"] == {
        "external": "~/published/results.html",
        "private": "<private>/tmp/results.jsonl",
    }


def test_tabs_round_trip_across_every_public_model_evidence_artifact(tmp_path: Path) -> None:
    """Hard tabs in captured model output must survive JSON, Markdown, and HTML."""
    # The leaked control token keeps this an integration signal so diagnostics
    # carries the evidence block (compliance-only results no longer do).
    output = "left\tright<|end|>"
    result = replace(
        _make_success("org/tabbed"),
        generation=_MockGeneration(text=output, generation_tokens=2),
    )
    context = _build_report_render_context(results=[result], prompt="Describe the image.")
    jsonl_path = tmp_path / "results.jsonl"
    gallery_path = tmp_path / "model_gallery.md"
    diagnostics_path = tmp_path / "diagnostics.md"
    html_path = tmp_path / "results.html"

    check_models.save_jsonl_report(
        [result],
        jsonl_path,
        prompt="Describe the image.",
        system_info={},
        report_context=context,
    )
    generate_markdown_gallery_report(
        [result],
        gallery_path,
        prompt="Describe the image.",
        report_context=context,
    )
    generate_diagnostics_report(
        [result],
        diagnostics_path,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={},
        report_context=context,
    )
    generate_html_report(
        [result],
        html_path,
        _stub_versions(),
        "Describe the image.",
        1.0,
        report_context=context,
    )

    records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    row = next(record for record in records if record.get("_type") == "result")
    assert row["generated_text"] == output
    assert output in gallery_path.read_text(encoding="utf-8")
    assert output in diagnostics_path.read_text(encoding="utf-8")
    html_report = html_path.read_text(encoding="utf-8")
    match = re.search(
        r'<pre class="model-output-readable">(.*?)</pre>',
        html_report,
        re.DOTALL,
    )
    assert match is not None
    assert html.unescape(match.group(1)) == output


def test_direct_jsonl_serializer_builds_one_local_assessment_cache(tmp_path: Path) -> None:
    """Direct JSONL calls should build one context and classify each model once."""
    results = [_make_success("org/direct-a"), _make_success("org/direct-b")]

    with patch.object(
        check_models,
        "_assess_result",
        wraps=check_models._assess_result,
    ) as assessment_builder:
        check_models.save_jsonl_report(
            results,
            tmp_path / "direct.jsonl",
            prompt="Describe the image.",
            system_info={},
        )

    assert assessment_builder.call_count == len(results)


def test_machine_reports_share_the_cached_resolved_model_provenance(tmp_path: Path) -> None:
    """Every retained model artifact should serialize one exact snapshot identity."""
    result = _make_success("org/pinned")
    provenance: check_models.ModelProvenanceRecord = {
        "model": result.model_name,
        "requested_revision": "requested-tag",
        "resolved_revision": "abcdef0123456789abcdef0123456789abcdef01",
        "snapshot_path": "~/.cache/snapshots/abcdef0123456789abcdef0123456789abcdef01",
    }
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        model_provenance={result.model_name: provenance},
    )
    jsonl_path = tmp_path / "results.jsonl"
    gallery_path = tmp_path / "model_gallery.md"
    html_path = tmp_path / "results.html"

    with patch.object(check_models, "_collect_model_provenance", side_effect=AssertionError):
        check_models.save_jsonl_report(
            [result],
            jsonl_path,
            prompt="Describe the image.",
            system_info={},
            requested_revision="requested-tag",
            report_context=context,
        )
        generate_markdown_gallery_report(
            [result],
            gallery_path,
            prompt="Describe the image.",
            report_context=context,
        )
        generate_html_report(
            [result],
            html_path,
            _stub_versions(),
            "Describe the image.",
            1.0,
            report_context=context,
        )

    jsonl_record = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[1])
    assert jsonl_record["model_provenance"] == provenance
    gallery = gallery_path.read_text(encoding="utf-8")
    html_report = html.unescape(html_path.read_text(encoding="utf-8"))
    assert "*Requested model revision:* requested-tag" in gallery
    assert f"*Resolved model revision:* {provenance['resolved_revision']}" in gallery
    assert "<td>Requested model revision</td>\n<td>requested-tag</td>" in html_report
    assert (
        f"<td>Resolved model revision</td>\n<td>{provenance['resolved_revision']}</td>"
    ) in html_report


def test_run_context_validator_accepts_exact_mixed_partition() -> None:
    """One validated context must partition every attempted model exactly once."""
    results = [
        _make_success("org/usable"),
        replace(
            _make_success("org/caveat"),
            generation=_MockGeneration(text="Brief reply", generation_tokens=2),
        ),
        replace(
            _make_success("org/unusable"),
            generation=_MockGeneration(text="", generation_tokens=0),
        ),
        _make_failure_with_details("org/crashed", error_msg="decode crashed"),
        _make_failure_with_details(
            "org/indeterminate",
            error_msg="Server disconnected without sending a response.",
        ),
    ]
    provenance: dict[str, check_models.ModelProvenanceRecord] = {
        result.model_name: {
            "model": result.model_name,
            "requested_revision": None,
            "resolved_revision": f"sha-{index}",
            "snapshot_path": f"~/.cache/snapshots/sha-{index}",
        }
        for index, result in enumerate(results)
    }
    context = _build_report_render_context(
        results=results,
        prompt="Describe the image.",
        system_info={},
        model_provenance=provenance,
    )

    check_models._validate_report_render_context(context)

    assert check_models._run_outcome_counts(context.assessments) == {
        "models_attempted": 5,
        "models_evaluated": 4,
        "models_completed": 3,
        "models_crashed": 1,
        "models_indeterminate": 1,
    }


def test_run_context_validator_rejects_duplicate_result_identity() -> None:
    """Duplicate result keys must fail before tuple-to-dict conversion can hide them."""
    result = _make_success("org/duplicate")
    provenance: check_models.ModelProvenanceRecord = {
        "model": result.model_name,
        "requested_revision": None,
        "resolved_revision": "sha",
        "snapshot_path": "~/.cache/snapshots/sha",
    }
    context = _build_report_render_context(
        results=[result, result],
        prompt="Describe the image.",
        system_info={},
        model_provenance={result.model_name: provenance},
    )

    with pytest.raises(ValueError, match="duplicate"):
        check_models._validate_report_render_context(context)


def test_run_context_validator_rejects_key_misalignment() -> None:
    """Result, assessment, and provenance identities must align exactly."""
    result = _make_success("org/model")
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
    )

    with pytest.raises(ValueError, match="provenance"):
        check_models._validate_report_render_context(context)


def test_run_context_validator_rejects_illegal_axis_combination() -> None:
    """Completed results cannot carry the not-evaluated usability axis."""
    result = _make_success("org/model")
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        system_info={},
        model_provenance={
            result.model_name: {
                "model": result.model_name,
                "requested_revision": None,
                "resolved_revision": "sha",
                "snapshot_path": "~/.cache/snapshots/sha",
            }
        },
    )
    context = replace(
        context,
        assessments=(
            (
                result.model_name,
                check_models.ResultAssessment("completed", "not_evaluated", "none", ()),
            ),
        ),
    )

    with pytest.raises(ValueError, match="illegal"):
        check_models._validate_report_render_context(context)


def _make_harness_success(
    name: str = "org/model-harness",
    *,
    text: str = "",
    prompt_tokens: int = 4000,
    generation_tokens: int = 0,
    harness_detail: str = "output:zero_tokens",
) -> PerformanceResult:
    qa = GenerationQualityAnalysis(
        is_repetitive=False,
        repeated_token=None,
        word_count=0,
        prompt_checks_ran=True,
        unexpected_special_tokens=(
            [harness_detail.split(":", maxsplit=1)[-1]]
            if harness_detail.startswith("token_leak:")
            else []
        ),
    )
    return PerformanceResult(
        model_name=name,
        success=True,
        generation=_MockGeneration(
            text=text,
            prompt_tokens=prompt_tokens,
            generation_tokens=generation_tokens,
        ),
        total_time=1.0,
        generation_time=0.5,
        model_load_time=0.5,
        quality_analysis=qa,
    )


def test_simplified_diagnostics_partitions_cached_assessments_in_evidence_order(
    tmp_path: Path,
) -> None:
    """Diagnostics should expose the four current-run sections before provenance."""
    crash = replace(
        _make_failure_with_details(
            "org/crash",
            error_msg="decoder failed",
            failure_phase="decode",
            traceback_str="Traceback (most recent call last):\nRuntimeError: decoder failed",
        ),
        upstream_boundary="generation_started",
    )
    observation = PerformanceResult(
        model_name="org/odd-output",
        success=True,
        generation=_MockGeneration(
            text="bizarre-loop " * 180,
            prompt_tokens=33,
            generation_tokens=180,
        ),
        runtime_diagnostics=RuntimeDiagnostics(stop_reason="completed"),
        requested_max_tokens=500,
    )
    indeterminate = PerformanceResult(
        model_name="org/network",
        success=False,
        generation=None,
        error_message="503 Service Unavailable",
    )
    clean = _make_success("org/clean")
    results = [clean, crash, observation, indeterminate]
    context = _build_report_render_context(
        results=results,
        prompt="Describe the image.",
        system_info={"GPU/Chip": "Apple M5"},
    )
    output = tmp_path / "diagnostics.md"

    generate_diagnostics_report(
        results,
        output,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={"GPU/Chip": "Apple M5"},
        report_context=context,
    )

    content = output.read_text(encoding="utf-8")
    headings = (
        "## Run Summary",
        "## Triage",
        "## Crashes requiring action",
        "## Completed Runs with Observations",
        "## Indeterminate Attempts",
        "## Context for completions without detected concerns",
    )
    assert all(heading in content for heading in headings)
    assert content.index(headings[0]) < content.index(headings[1])
    assert content.index(headings[1]) < content.index(headings[2])
    assert content.index(headings[2]) < content.index(headings[3])
    assert content.index(headings[-1]) < content.index("## Shared Reproduction and Provenance")
    assert "actionable_failure" in content
    assert "observation_needs_reproduction" in content
    assert "indeterminate" in content


def test_diagnostics_facts_surface_exact_observation_evidence_without_empty_noise() -> None:
    repeated_fragment = 'keyword: "remote control"'
    analysis = check_models.GenerationQualityAnalysis(
        is_repetitive=True,
        repeated_token=repeated_fragment,
        missing_sections=["title"],
        unexpected_special_tokens=["<|im_user|>"],
    )
    result = PerformanceResult(
        model_name="org/observed",
        success=True,
        generation=_MockGeneration(text="output", generation_tokens=20),
        quality_analysis=analysis,
    )
    assessment = check_models.ResultAssessment(
        "completed",
        "unusable",
        "observation_needs_reproduction",
        ("repeated_output", "missing_requested_sections", "prompt_instruction_echo"),
    )

    facts = dict(
        check_models._diagnostics_result_facts(
            result,
            assessment,
            run_args=None,
            model_provenance=None,
        )
    )

    assert facts["Labelled fields not detected"] == '["title"]'
    assert facts["Repeated fragment"] == 'keyword: "remote control"'
    assert facts["Unexpected special tokens"] == '["<|im_user|>"]'
    assert "Error type" not in facts
    assert "Configured EOS token" not in facts


def test_diagnostics_facts_render_catalog_constraint_evidence() -> None:
    analysis = check_models.GenerationQualityAnalysis(
        is_repetitive=False,
        repeated_token=None,
        title_word_count=4,
        keyword_count=10,
        duplicate_keywords=["building"],
    )
    result = PerformanceResult(
        model_name="org/catalog-constraint",
        success=True,
        generation=_MockGeneration(text="catalogue output", generation_tokens=20),
        quality_analysis=analysis,
    )
    assessment = check_models.ResultAssessment(
        "completed",
        "usable_with_caveats",
        "observation_needs_reproduction",
        ("catalog_constraint_violation",),
    )

    facts = dict(
        check_models._diagnostics_result_facts(
            result,
            assessment,
            run_args=None,
            model_provenance=None,
        )
    )

    assert facts["Title word count"] == "4"
    assert facts["Keyword count"] == "10"
    assert facts["Duplicate keywords"] == '["building"]'


def test_diagnostics_are_skim_first_and_share_reproduction_context_once(  # noqa: PLR0915 - asserts every diagnostics section in order
    tmp_path: Path,
) -> None:
    """Issue-ready diagnostics should expand faults, collapse context, and avoid repetition."""
    prompt = "Exact multiline prompt.\nSecond distinctive line."
    crash = replace(
        _make_failure_with_details(
            "org/crash",
            error_msg="decoder failed",
            generated_text="CRASH-PARTIAL",
            traceback_str="TRACEBACK-FIRST\nRuntimeError: decoder failed",
            captured_output="CAPTURED-AFTER-PARTIAL",
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="mlx_vlm.processors.CrashProcessor",
            tokenizer_class="transformers.CrashTokenizer",
        ),
    )
    repeated_fragment = 'phrase: "OBSERVED-OUTPUT-MUST-APPEAR"'
    observed = PerformanceResult(
        model_name="org/observed",
        success=True,
        generation=_MockGeneration(
            text="OBSERVED-OUTPUT-MUST-APPEAR",
            prompt_tokens=30,
            generation_tokens=80,
            generation_tps=20.0,
            peak_memory=2.0,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="mlx_vlm.processors.ObservedProcessor",
        ),
        runtime_diagnostics=RuntimeDiagnostics(stop_reason="eos"),
        quality_analysis=check_models.GenerationQualityAnalysis(
            is_repetitive=True,
            repeated_token=repeated_fragment,
            prompt_checks_ran=True,
        ),
    )
    indeterminate = PerformanceResult(
        model_name="org/network",
        success=False,
        generation=None,
        error_message="503 Service Unavailable — INDETERMINATE-EVIDENCE",
        captured_output_on_fail="SERVER-COULD-NOT-BE-CONTACTED",
    )
    clean_one = replace(
        _make_success("org/clean-one"),
        generation=_MockGeneration(
            text="CLEAN-OUTPUT-MUST-NOT-APPEAR",
            prompt_tokens=44,
            generation_tokens=40,
            generation_tps=16.5,
            peak_memory=1.5,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="mlx_vlm.processors.CleanProcessor",
        ),
        runtime_diagnostics=RuntimeDiagnostics(stop_reason="eos"),
    )
    clean_two = replace(
        _make_success("org/clean-two"),
        generation=_MockGeneration(
            text="SECOND-CLEAN-OUTPUT-MUST-NOT-APPEAR",
            prompt_tokens=50,
            generation_tokens=8,
            generation_tps=999.0,
            peak_memory=3.0,
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="OtherProcessor",
        ),
        runtime_diagnostics=RuntimeDiagnostics(stop_reason="length"),
    )
    results = [crash, observed, indeterminate, clean_one, clean_two]
    assessments = {
        "org/crash": check_models.ResultAssessment(
            "crashed", "not_evaluated", "actionable_failure", ()
        ),
        "org/observed": check_models.ResultAssessment(
            "completed", "unusable", "observation_needs_reproduction", ("repeated_output",)
        ),
        "org/network": check_models.ResultAssessment("indeterminate", "not_evaluated", "none", ()),
        "org/clean-one": check_models.ResultAssessment("completed", "usable", "none", ()),
        "org/clean-two": check_models.ResultAssessment("completed", "usable", "none", ()),
    }
    revisions: dict[str, check_models.ModelProvenanceRecord] = {
        result.model_name: {
            "model": result.model_name,
            "requested_revision": None,
            "resolved_revision": f"{index:012d}full-revision",
            "snapshot_path": None,
        }
        for index, result in enumerate(results, start=1)
    }
    context = _build_report_render_context(
        results=results,
        prompt=prompt,
        system_info={"GPU/Chip": "Apple M5"},
        model_provenance=revisions,
    )
    context = replace(context, assessments=tuple(assessments.items()))
    markdown_path = tmp_path / "diagnostics.md"
    html_path = tmp_path / "results.html"

    generate_diagnostics_report(
        results,
        markdown_path,
        prompt=prompt,
        library_versions=_stub_versions(),
        system_info=context.system_info,
        report_context=context,
    )
    generate_html_report(
        results,
        html_path,
        _stub_versions(),
        prompt,
        5.0,
        report_context=context,
    )

    diagnostics = markdown_path.read_text(encoding="utf-8")
    html_report = html_path.read_text(encoding="utf-8")
    assert all(
        label in diagnostics
        for label in (
            "Outcome counts",
            "Maintainer status counts",
            "Mechanical-check counts",
            "Observation counts",
        )
    )
    assert "[org/crash](#diagnostic-org-crash)" in diagnostics
    assert "[org/observed](#diagnostic-org-observed)" in diagnostics
    assert "[org/network](#diagnostic-org-network)" in diagnostics
    triage = _extract_markdown_subsection(
        diagnostics,
        "## Triage",
        end_headings=("## Crashes requiring action",),
    )
    assert "org/clean-one" not in triage
    assert "org/clean-two" not in triage
    assert diagnostics.index("TRACEBACK-FIRST") < diagnostics.index("CRASH-PARTIAL")
    assert "<summary>org/observed" in diagnostics
    assert "<summary>org/network" in diagnostics
    assert re.search(
        r"\| Response repeats the same text\s+\|\s+1\s+\|\n\n## Triage",
        diagnostics,
    )
    assert re.search(
        r"\| \[org/network\].*\|\n\n## Crashes requiring action",
        diagnostics,
    )
    assert "OBSERVED-OUTPUT-MUST-APPEAR" in diagnostics
    assert diagnostics.count("#### Complete output") == 1
    assert "Repeated fragment" in diagnostics
    assert "SERVER-COULD-NOT-BE-CONTACTED" in diagnostics
    assert "<summary>Completions without detected concerns</summary>" in diagnostics
    assert "000000000004" in diagnostics
    assert "CleanProcessor" in diagnostics
    assert "eos" in diagnostics
    assert "44 prompt / 40 generated" in diagnostics
    assert "16.5 tok/s" in diagnostics
    assert "1.5 GB" in diagnostics
    assert "insufficient sample" in diagnostics
    assert "CLEAN-OUTPUT-MUST-NOT-APPEAR" not in diagnostics
    assert "SECOND-CLEAN-OUTPUT-MUST-NOT-APPEAR" not in diagnostics
    assert diagnostics.count(prompt) == 1
    assert diagnostics.count("The original local input is not published") == 1
    assert diagnostics.count("Exact prompt") == 1
    assert all(
        unavailable_ref not in diagnostics
        for unavailable_ref in ("reproduce.py", "prompt.txt", "python -m mlx_vlm.generate")
    )
    for model in ("org/crash", "org/observed", "org/network"):
        assert model in diagnostics
        revision = revisions[model]["resolved_revision"]
        assert revision is not None
        assert revision in diagnostics
    maintainer_html = html_report.split('<section id="maintainer-diagnostics">', maxsplit=1)[1]
    maintainer_html = maintainer_html.split("</section>", maxsplit=1)[0]
    assert "CLEAN-OUTPUT-MUST-NOT-APPEAR" not in maintainer_html
    assert "OBSERVED-OUTPUT-MUST-APPEAR" in maintainer_html
    assert 'href="#diagnostic-org-crash"' in maintainer_html
    assert html_report.count("The original local input is not published") == 1
    assert all(
        unavailable_ref not in html_report for unavailable_ref in ("reproduce.py", "prompt.txt")
    )


def test_html_chooser_is_sortable_and_surfaces_prefill_first_token_time(
    tmp_path: Path,
) -> None:
    """HTML alone should expose sortable per-model prefill/first-token latency."""
    result = replace(
        _make_success("org/timed"),
        runtime_diagnostics=RuntimeDiagnostics(first_token_latency_s=0.375),
    )
    html_path = tmp_path / "results.html"

    generate_html_report(
        [result],
        html_path,
        _stub_versions(),
        "Describe the image.",
        1.0,
    )

    content = html_path.read_text(encoding="utf-8")
    chooser = content.split('<section id="current-run-chooser">', maxsplit=1)[1]
    chooser = chooser.split("</section>", maxsplit=1)[0]
    assert "Prefill/first s" in chooser
    assert 'data-sort-column="6"' in chooser
    assert 'data-sort-value="0.375"' in chooser
    assert "sortChooserColumn" in chooser


def test_markdown_and_html_choosers_share_metric_explanations(tmp_path: Path) -> None:
    """Both chooser formats must explain timing and cross-attention token burden."""
    result = _make_success("org/chooser-copy")
    markdown_path = tmp_path / "gallery.md"
    html_path = tmp_path / "results.html"
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
    )

    generate_markdown_gallery_report(
        [result],
        markdown_path,
        prompt="Describe the image.",
        report_context=context,
    )
    generate_html_report(
        [result],
        html_path,
        _stub_versions(),
        "Describe the image.",
        1.0,
        report_context=context,
    )

    explanations = (
        "Prefill/first is first-token latency when captured",
        "For cross-attention architectures the token count reflects the tokenised text burden",
    )
    for report in (markdown_path.read_text(), html.unescape(html_path.read_text())):
        for explanation in explanations:
            assert explanation in report


def test_crash_diagnostics_and_issue_draft_keep_complete_primary_evidence_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crash draft should repeat complete diagnostics evidence without truncation."""
    monkeypatch.setattr(
        check_models,
        "_collect_check_models_provenance",
        lambda: {
            "name": "check_models",
            "version": "0.8.9",
            "git_revision": "abc123def456",
            "install_type": "source-tree",
            "dirty": False,
        },
    )
    system_info = {
        "Python Version": "3.13.13",
        "macOS Version": "26.6",
        "GPU/Chip": "Apple M5 Max",
        "SDK Version": "26.0",
        "Apple Clang Version": "17.0.0",
    }
    traceback_text = "\n".join(
        (
            "Traceback (most recent call last):",
            *(f'  File "frame_{index}.py", line {index}, in decode' for index in range(30)),
            "RuntimeError: decoder exploded at the root",
        )
    )
    partial_output = "BEGIN-PARTIAL " + ("decoded fragment " * 80) + "END-PARTIAL"
    captured_stream = "=== STDERR ===\nBEGIN-STDERR\nupstream warning\nEND-STDERR"
    crash = PerformanceResult(
        model_name="org/crash-evidence",
        generation=_MockGeneration(text=partial_output, prompt_tokens=91, generation_tokens=17),
        success=False,
        upstream_boundary="generation_started",
        failure_phase="decode",
        error_stage="Model Error",
        error_type="RuntimeError",
        root_error_type="RuntimeError",
        root_error_module="mlx_vlm.generate",
        root_error_message="decoder exploded at the root",
        exception_chain=(
            check_models.FailureException(
                "RuntimeError",
                "mlx_vlm.generate",
                "decoder exploded at the root",
            ),
        ),
        error_package="mlx-vlm",
        error_traceback=traceback_text,
        captured_output_on_fail=captured_stream,
        requested_max_tokens=500,
        runtime_diagnostics=RuntimeDiagnostics(stop_reason="error"),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="LlavaProcessor",
            tokenizer_class="LlamaTokenizerFast",
            eos_token_id=2,
            eos_token=EOS_END_TOKEN,
            generate_kwargs={
                "thinking_start_token": "<think>",
                "thinking_end_token": "</think>",
            },
        ),
    )
    context = _build_report_render_context(
        results=[crash],
        prompt="Describe the image.",
        system_info=system_info,
    )
    diagnostics = tmp_path / "diagnostics.md"
    generate_diagnostics_report(
        [crash],
        diagnostics,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info=system_info,
        report_context=context,
    )
    generated = _generate_github_issue_reports(
        report_context=context,
        output_dir=tmp_path,
        library_versions=_stub_versions(),
        system_info=system_info,
        prompt="Describe the image.",
    )

    assert len(generated) == 1
    diagnostics_content = diagnostics.read_text(encoding="utf-8")
    issue_content = next(iter(generated.values())).read_text(encoding="utf-8")
    for content in (diagnostics_content, issue_content):
        assert "RuntimeError: decoder exploded at the root" in content
        assert traceback_text in content
        assert partial_output in content
        assert captured_stream in content
        assert "truncated" not in content.casefold()
        assert content.index(traceback_text) < content.index(partial_output)
        assert content.index(traceback_text) < content.index(captured_stream)
        assert "mlx_vlm.generate" in content
        assert "LlavaProcessor" in content
        assert "LlamaTokenizerFast" in content
    assert "python -m mlx_vlm.generate" not in diagnostics_content
    assert "The original local input is not published" in diagnostics_content
    assert "reproduce.py" not in diagnostics_content
    assert "prompt.txt" not in diagnostics_content
    for content in (diagnostics_content, issue_content):
        assert content.index("#### Root exception and chain") < content.index(
            "#### Execution and provenance"
        )
        assert content.index("#### Execution and provenance") < content.index("Complete traceback")
    assert "<summary>Complete traceback</summary>" in issue_content
    # Diagnostics folds the complete traceback too, so one crash's dump cannot
    # bury the triage tables; the exact evidence stays inside the details block.
    assert "<summary>Complete traceback</summary>" in diagnostics_content
    assert "The original local input is not published" in issue_content
    assert "python -m mlx_vlm.generate" not in issue_content
    assert issue_content.index("## Reproduction inputs") < issue_content.index(
        "## Provenance and Environment"
    )
    environment_url = (
        "https://github.com/jrp2014/check_models/blob/"
        f"{check_models._github_blob_ref()}/src/output/environment.log"
    )
    for expected in (
        "mlx-vlm",
        "mlx",
        "transformers",
        "tokenizers",
        "Python Version",
        "macOS Version",
        "GPU/Chip",
        "abc123def456",
        environment_url,
    ):
        assert expected in issue_content
    assert "SDK Version" not in issue_content
    assert "Apple Clang Version" not in issue_content
    assert not (tmp_path / "issues" / "index.md").exists()


def test_successful_anomaly_and_indeterminate_attempt_create_no_issue_draft(
    tmp_path: Path,
) -> None:
    """Suspicious prose remains an unowned observation and never becomes a draft."""
    complete_output = "STRANGE-BEGIN " + ("odd-loop " * 220) + " STRANGE-END"
    observation = PerformanceResult(
        model_name="org/strange",
        success=True,
        generation=_MockGeneration(
            text=complete_output,
            prompt_tokens=40,
            generation_tokens=220,
        ),
        requested_max_tokens=500,
    )
    indeterminate = PerformanceResult(
        model_name="org/network",
        success=False,
        generation=None,
        error_message="server disconnected without sending a response",
    )
    context = _build_report_render_context(
        results=[observation, indeterminate],
        prompt="Describe the image.",
        system_info={},
    )
    diagnostics = tmp_path / "diagnostics.md"

    generate_diagnostics_report(
        [observation, indeterminate],
        diagnostics,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={},
        report_context=context,
    )
    generated = _generate_github_issue_reports(
        report_context=context,
        output_dir=tmp_path,
        library_versions=_stub_versions(),
        system_info={},
        prompt="Describe the image.",
    )

    content = diagnostics.read_text(encoding="utf-8")
    assert "observation_needs_reproduction" in content
    assert complete_output in content
    assert "suspected owner" not in content.casefold()
    assert "owner confidence" not in content.casefold()
    assert generated == {}
    assert not list((tmp_path / "issues").glob("issue_*.md"))


def test_issue_generation_writes_exactly_one_draft_per_crash(tmp_path: Path) -> None:
    """Only crashed actionable attempts should become individual issue drafts."""
    crashes = [
        _make_failure_with_details("org/crash-one", error_msg="decoder one failed"),
        _make_failure_with_details("org/crash-two", error_msg="decoder two failed"),
    ]
    completed = _make_success("org/completed")
    indeterminate = PerformanceResult(
        model_name="org/network",
        success=False,
        generation=None,
        error_message="503 Service Unavailable",
    )
    results = [*crashes, completed, indeterminate]
    context = _build_report_render_context(results=results, prompt="Describe the image.")

    generated = _generate_github_issue_reports(
        report_context=context,
        output_dir=tmp_path,
        library_versions=_stub_versions(),
        system_info={},
        prompt="Describe the image.",
    )

    assert set(generated) == {"org/crash-one", "org/crash-two"}
    assert len(list((tmp_path / "issues").glob("issue_*.md"))) == 2


def test_diagnostics_distinguish_empty_output_from_unavailable_evidence(tmp_path: Path) -> None:
    """Recorded empty output and evidence that was never captured are different facts."""
    empty_output = _make_failure_with_details(
        "org/empty-output",
        error_msg="generation stopped",
        generated_text="",
    )
    unavailable = _make_failure_with_details(
        "org/no-evidence",
        error_msg="generation failed before output",
        traceback_str=None,
        captured_output=None,
        generated_text=None,
    )
    results = [empty_output, unavailable]
    context = _build_report_render_context(results=results, prompt="Describe the image.")
    output = tmp_path / "diagnostics.md"

    generate_diagnostics_report(
        results,
        output,
        prompt="Describe the image.",
        library_versions=_stub_versions(),
        system_info={},
        report_context=context,
    )

    content = output.read_text(encoding="utf-8")
    empty_entry = _extract_markdown_subsection(
        content,
        "### org/empty-output",
        end_headings=("### org/no-evidence",),
    )
    missing_entry = _extract_markdown_subsection(
        content,
        "### org/no-evidence",
        end_headings=("## Completed Runs with Observations",),
    )
    assert "Complete partial output\n\n```text\n(empty)" in empty_entry
    assert "generation failed before output" in missing_entry
    assert "Complete traceback" not in missing_entry
    assert "Complete partial output" not in missing_entry
    assert "Captured stdout/stderr" not in missing_entry


def test_diagnostics_describe_local_reproduction_input_without_fake_command(
    tmp_path: Path,
) -> None:
    """Diagnostics should preserve local input facts without inventing a runnable command."""
    result = replace(
        _make_failure_with_details("org/repro", error_msg="decode failed"),
        prompt_diagnostics=check_models.PromptDiagnostics(
            eos_token_id=2,
            eos_token=EOS_END_TOKEN,
            generate_kwargs={"eos_tokens": [EOS_OVERRIDE_TOKEN]},
        ),
    )
    resolved_revision = "0123456789abcdef0123456789abcdef01234567"
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image.",
        model_provenance={
            result.model_name: {
                "model": result.model_name,
                "requested_revision": "run-revision",
                "resolved_revision": resolved_revision,
                "snapshot_path": f"~/.cache/snapshots/{resolved_revision}",
            }
        },
    )
    output = tmp_path / "diagnostics.md"
    image_path = Path(__file__).parent / "fixtures/check_models-task9-fixture.jpg"
    assert image_path.is_file()
    assert (
        check_models._sha256_file(image_path)
        == "251712968e443405f6e1ff145de15a91a082dc073209938c5305db0e8e80134c"
    )
    run_args = Namespace(
        max_tokens=321,
        temperature=0.25,
        top_p=0.81,
        min_p=0.12,
        top_k=7,
        seed=73,
        repetition_penalty=1.15,
        repetition_context_size=48,
        presence_penalty=0.3,
        presence_context_size=96,
        frequency_penalty=0.2,
        frequency_context_size=80,
        max_kv_size=4096,
        kv_bits=4,
        kv_quant_scheme="turboquant",
        kv_group_size=32,
        quantized_kv_start=128,
        prefill_step_size=512,
        resize_shape=(64, 32),
        eos_tokens=[EOS_OVERRIDE_TOKEN],
        skip_special_tokens=True,
        revision="run-revision",
        trust_remote_code=True,
        force_download=True,
        quantize_activations=True,
        processor_kwargs={"cropping": False},
        enable_thinking=True,
        thinking_budget=24,
        thinking_start_token=THINKING_START_TOKEN,
        thinking_end_token=CUSTOM_THINKING_END_TOKEN,
        logit_bias={42: -1.5},
        adapter_path=None,
        lazy_load=False,
    )

    with patch.object(check_models, "_collect_model_provenance", side_effect=AssertionError):
        generate_diagnostics_report(
            [result],
            output,
            prompt="Describe the image.",
            library_versions=_stub_versions(),
            system_info={},
            report_context=context,
            image_path=image_path,
            run_args=run_args,
        )
        issue_reports = _generate_github_issue_reports(
            report_context=context,
            output_dir=tmp_path,
            library_versions=_stub_versions(),
            system_info={},
            prompt="Describe the image.",
            image_path=image_path,
            run_args=run_args,
        )

    diagnostics_content = output.read_text(encoding="utf-8")
    issue_content = next(iter(issue_reports.values())).read_text(encoding="utf-8")
    for content in (diagnostics_content, issue_content):
        assert f"- *Resolved model revision:* {resolved_revision}" in content
        assert "- *Requested model revision:* run-revision" in content
        assert '- *Configured EOS token override:* ["&lt;override-eos&gt;"]' in content
    assert "Supplemental CLI reproduction" not in diagnostics_content
    assert "The original local input is not published" in diagnostics_content
    assert "reproduce.py" not in diagnostics_content
    assert "prompt.txt" not in diagnostics_content
    # The only runnable command is the clearly labelled stand-in against the
    # committed preview, never a command that pretends to use the local file.
    stand_in = diagnostics_content.index("Shareable stand-in")
    assert diagnostics_content.index("mlx_vlm.generate") > stand_in
    assert diagnostics_content.count("mlx_vlm.generate") == 1
    assert (
        "raw.githubusercontent.com/jrp2014/check_models/main/src/output/reports/assets/source-image-"
        in diagnostics_content
    )
    assert "Retained preview" in diagnostics_content
    assert "Published preview" not in diagnostics_content
    assert "repro-image.jpg" in diagnostics_content
    assert resolved_revision in diagnostics_content
    assert "Reproduction inputs" in diagnostics_content
    assert "JPEG" in diagnostics_content
    assert "17,235 bytes" in diagnostics_content
    assert "251712968e443405f6e1ff145de15a91a082dc073209938c5305db0e8e80134c" in diagnostics_content
    assert "check_models-task9-fixture.jpg" not in diagnostics_content
    assert "Reproduction inputs" in issue_content
    assert "The original local input is not published" in issue_content
    assert "JPEG" in issue_content
    assert "17,235 bytes" in issue_content
    assert "251712968e443405f6e1ff145de15a91a082dc073209938c5305db0e8e80134c" in issue_content
    assert "Supplemental CLI reproduction" not in issue_content
    assert "Canonical Python reproduction script" not in issue_content
    assert "check_models-task9-fixture.jpg" not in issue_content


def test_crash_issue_draft_builds_complete_public_image_reproduction(tmp_path: Path) -> None:
    """A direct crash draft should fetch, verify, and use a public exact input."""
    result = _make_failure_with_details("org/public-repro", error_msg="decode failed")
    resolved_revision = "0123456789abcdef0123456789abcdef01234567"
    image_path = Path(__file__).parent / "fixtures/check_models-task9-fixture.jpg"
    context = _build_report_render_context(
        results=[result],
        prompt="Describe the image exactly.",
        image_path=image_path,
        model_provenance={
            result.model_name: {
                "model": result.model_name,
                "requested_revision": "main",
                "resolved_revision": resolved_revision,
                "snapshot_path": None,
            }
        },
    )
    run_args = Namespace(
        image_source_url="https://example.test/images/cats.jpg",
        max_tokens=321,
        temperature=0.0,
        revision="main",
        trust_remote_code=True,
    )

    issue_reports = _generate_github_issue_reports(
        report_context=context,
        output_dir=tmp_path,
        library_versions=_stub_versions(),
        system_info={},
        prompt="Describe the image exactly.",
        image_path=image_path,
        run_args=run_args,
    )

    content = next(iter(issue_reports.values())).read_text(encoding="utf-8")
    assert "https://example.test/images/cats.jpg" in content
    assert "curl --fail --location" in content
    assert "set -euo pipefail\ncurl --fail --location" in content
    assert "shasum -a 256 --check" in content
    assert "python -m mlx_vlm.generate" in content
    assert "--model org/public-repro" in content
    assert f"--revision {resolved_revision}" in content
    assert "--prompt 'Describe the image exactly.'" in content
    assert "--image repro-image.jpg" in content
    assert "reproduce.py" not in content
    assert "prompt.txt" not in content


def test_maintainer_summary_logs_only_counts_and_direct_draft_paths(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Console diagnostics should report cached facts without inferred ownership."""
    diagnostics_path = tmp_path / "diagnostics.md"
    diagnostics_path.write_text("diagnostics\n", encoding="utf-8")
    issue_one = tmp_path / "issues" / "issue_one.md"
    issue_two = tmp_path / "issues" / "issue_two.md"
    issue_one.parent.mkdir()
    issue_one.write_text("one\n", encoding="utf-8")
    issue_two.write_text("two\n", encoding="utf-8")
    artifacts = DiagnosticsArtifacts(
        outcome_counts={
            "models_attempted": 4,
            "models_evaluated": 3,
            "models_completed": 1,
            "models_crashed": 2,
            "models_indeterminate": 1,
        },
        diagnostics_written=True,
        issue_reports={"org/one": issue_one, "org/two": issue_two},
    )

    caplog.set_level("INFO")
    check_models._log_maintainer_summary(
        artifacts=artifacts,
        diagnostics_path=diagnostics_path,
    )

    messages = caplog.text
    assert "attempted=4" in messages
    assert "completed=1" in messages
    assert "crashed=2" in messages
    assert "indeterminate=1" in messages
    assert str(issue_one) in messages
    assert str(issue_two) in messages
    assert "owner" not in messages.casefold()
    assert "cluster" not in messages.casefold()


def test_diagnostics_writer_never_exports_repro_bundles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finalization diagnostics should create reports and drafts without bundle artifacts."""
    crash = _make_failure_with_details("org/crash", error_msg="decode failed")
    context = _build_report_render_context(results=[crash], prompt="Describe the image.")

    def fail_if_called(**_kwargs: object) -> None:
        pytest.fail("retired repro-bundle exporter was called")

    monkeypatch.setattr(
        check_models,
        "export_failure_repro_bundles",
        fail_if_called,
        raising=False,
    )
    artifacts = check_models._write_diagnostics_artifacts(
        args=Namespace(
            max_tokens=32,
            temperature=0.0,
            trust_remote_code=False,
            revision=None,
        ),
        library_versions=_stub_versions(),
        system_info={},
        prompt="Describe the image.",
        image_path=None,
        diagnostics_path=tmp_path / "reports" / "diagnostics.md",
        report_context=context,
    )

    assert artifacts.diagnostics_written is True
    assert len(artifacts.issue_reports) == 1
    assert not hasattr(artifacts, "repro_bundles")
    assert not (tmp_path / "repro_bundles").exists()


class TestHtmlReportEdgeCases:
    """Edge-case coverage for generate_html_report."""

    def test_html_mirrors_cached_assessments_across_retained_artifacts(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Every retained consumer should expose one exact cached status vocabulary."""
        caplog.set_level(logging.INFO)
        prompt = "Describe the image."
        results = [
            _make_success("org/usable"),
            _make_success("org/caveat"),
            replace(
                _make_success("org/unusable"),
                generation=_MockGeneration(text="", generation_tokens=0),
            ),
            _make_failure_with_details(
                "org/crashed",
                traceback_str="Traceback:\nRuntimeError: crashed",
            ),
            _make_failure_with_details(
                "org/indeterminate",
                error_msg="Server disconnected without sending a response.",
                error_stage="Network Error",
                error_package="unknown",
            ),
        ]
        context = _build_report_render_context(results=results, prompt=prompt, system_info={})
        expected = {
            "org/usable": check_models.ResultAssessment("completed", "usable", "none", ()),
            "org/caveat": check_models.ResultAssessment(
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
                "crashed",
                "not_evaluated",
                "actionable_failure",
                (),
            ),
            "org/indeterminate": check_models.ResultAssessment(
                "indeterminate",
                "not_evaluated",
                "none",
                (),
            ),
        }
        context = replace(context, assessments=tuple(expected.items()))
        jsonl_path = tmp_path / "results.jsonl"
        diagnostics_path = tmp_path / "diagnostics.md"
        gallery_path = tmp_path / "model_gallery.md"
        html_path = tmp_path / "results.html"

        with patch.object(check_models, "_assess_result", side_effect=AssertionError):
            check_models.save_jsonl_report(
                results,
                jsonl_path,
                prompt,
                {},
                report_context=context,
            )
            generate_diagnostics_report(
                results,
                diagnostics_path,
                prompt=prompt,
                library_versions=_stub_versions(),
                system_info={},
                report_context=context,
            )
            generate_markdown_gallery_report(
                results,
                gallery_path,
                prompt,
                report_context=context,
            )
            generate_html_report(
                results,
                html_path,
                _stub_versions(),
                prompt,
                5.0,
                report_context=context,
            )
            check_models.log_summary(results, assessments=expected)

        records = {
            record["model"]: record
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if (record := json.loads(line)).get("_type") == "result"
        }
        diagnostics = diagnostics_path.read_text(encoding="utf-8")
        gallery = gallery_path.read_text(encoding="utf-8")
        html_report = html_path.read_text(encoding="utf-8")
        header = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
        assert header["counts"] == {
            "models_attempted": 5,
            "models_evaluated": 4,
            "models_completed": 3,
            "models_crashed": 1,
            "models_indeterminate": 1,
        }
        log_text = "\n".join(record.message for record in caplog.records)
        assert "status=OK" not in log_text
        assert "Successful Models" not in log_text
        assert "Execution outcomes: completed=3, crashed=1, indeterminate=1" in log_text
        # The one canonical guard against the retired semantic-scoring
        # vocabulary, replacing the per-artifact absence tests.
        jsonl_text = jsonl_path.read_text(encoding="utf-8")
        retired_terms = ("quality score", "semantic winner", "owner_confidence", "suspected_owner")
        for artifact_text in (jsonl_text, gallery, html_report, diagnostics, log_text):
            lowered = artifact_text.casefold()
            assert all(term not in lowered for term in retired_terms)
        for model, assessment in expected.items():
            serialized = records[model]["assessment"]
            assert serialized["execution"] == assessment.execution
            assert serialized["usability"] == assessment.usability
            assert serialized["maintainer_status"] == assessment.maintainer_status
            gallery_entry = _extract_markdown_model_section(gallery, model)
            assert f"*Execution:* {assessment.execution}" in gallery_entry
            assert (
                f"*Mechanical checks:* {check_models._human_status_label(assessment.usability)}"
                in gallery_entry
            )
            assert f"*Maintainer status:* {assessment.maintainer_status}" in gallery_entry
            escaped_model = html.escape(model, quote=True)
            row_pattern = (
                rf'data-model="{re.escape(escaped_model)}"[^>]*'
                rf'data-execution="{assessment.execution}"[^>]*'
                rf'data-usability="{assessment.usability}"[^>]*'
                rf'data-maintainer-status="{assessment.maintainer_status}"'
            )
            assert re.search(row_pattern, html_report) is not None
            if assessment.maintainer_status != "none" or assessment.execution == "indeterminate":
                diagnostics_entry = _extract_markdown_diagnostic_entry(diagnostics, model)
                assert f"*Execution:* {assessment.execution}" in diagnostics_entry
                assert (
                    f"*Mechanical checks:* {check_models._human_status_label(assessment.usability)}"
                    in diagnostics_entry
                )
                assert f"*Maintainer status:* {assessment.maintainer_status}" in diagnostics_entry

    def test_standalone_html_does_not_build_legacy_semantic_context(
        self,
        tmp_path: Path,
    ) -> None:
        """Standalone HTML should build only its canonical gallery/diagnostic context."""
        result = _make_success("org/standalone")
        out = tmp_path / "standalone.html"

        with patch.object(
            check_models,
            "_build_report_render_context",
            side_effect=AssertionError,
        ):
            generate_html_report(
                [result],
                out,
                _stub_versions(),
                "Describe.",
                1.0,
            )

        content = out.read_text(encoding="utf-8")
        assert 'data-execution="completed"' in content
        assert 'data-usability="usable"' in content
        assert 'data-maintainer-status="none"' in content

    def test_html_diagnostics_preserve_nondefault_run_arguments(
        self,
        tmp_path: Path,
    ) -> None:
        """HTML maintainer facts and shared repro should retain the run configuration."""
        result = _make_failure_with_details("org/repro", error_msg="decode failed")
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        output = tmp_path / "results.html"
        image_path = tmp_path / "sample image.jpg"
        Image.new("RGB", (12, 8), "blue").save(image_path)
        run_args = Namespace(
            adapter_path=tmp_path / "adapter",
            revision="refs/pr/42",
            trust_remote_code=False,
            enable_thinking=True,
            thinking_budget=19,
            thinking_start_token=THINKING_START_TOKEN,
            thinking_end_token=CUSTOM_THINKING_END_TOKEN,
            max_tokens=321,
            temperature=0.42,
            processor_kwargs={"cropping": False},
            image_source_url="https://example.test/images/cats.jpg",
        )

        generate_html_report(
            [result],
            output,
            _stub_versions(),
            "Describe the image.",
            1.0,
            image_path=image_path,
            report_context=context,
            run_args=run_args,
        )

        content = html.unescape(output.read_text(encoding="utf-8"))
        assert "<li><b>Requested model revision:</b> refs/pr/42</li>" in content
        assert "curl --fail --location" in content
        assert "shasum -a 256 --check" in content
        assert "python -m mlx_vlm.generate" in content
        assert "MODEL_ID" in content
        assert "RESOLVED_REVISION" in content
        assert "reproduce.py" not in content
        assert "prompt.txt" not in content

    def test_html_preserves_complete_escaped_output_in_expandable_evidence(
        self,
        tmp_path: Path,
    ) -> None:
        """Complete generated text should survive HTML escaping and round-trip exactly."""
        output = (
            'literal <thinking> & "quotes" — café 雪\n'
            + ("complete evidence segment " * 40)
            + "END"
        )
        result = replace(
            _make_success("org/evidence"),
            generation=_MockGeneration(text=output, generation_tokens=80),
        )
        context = _build_report_render_context(results=[result], prompt="Describe.")
        context = replace(
            context,
            assessments=(
                (
                    result.model_name,
                    check_models.ResultAssessment("completed", "usable", "none", ()),
                ),
            ),
        )
        out = tmp_path / "evidence.html"

        generate_html_report(
            [result],
            out,
            _stub_versions(),
            "Describe.",
            1.0,
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        escaped = html.escape(output, quote=True)
        # HTML escaping is lossless, so the readable pre block is the single
        # exact copy; a second collapsed raw copy would always be identical.
        assert content.count(escaped) == 1
        match = re.search(
            r"<details><summary>Complete evidence: org/evidence</summary>.*?"
            r'<pre class="model-output-readable">(.*?)</pre>',
            content,
            flags=re.DOTALL,
        )
        assert match is not None
        assert html.unescape(match.group(1)) == output

    def test_html_gallery_renders_readable_and_exact_escaped_model_output(
        self,
        tmp_path: Path,
    ) -> None:
        """HTML should expose both readable preformatted text and collapsed exact evidence."""
        output = "## Title\n\n- cat\n\n@maintainer <details>unsafe</details>"
        result = replace(
            _make_success("org/formatted"),
            generation=_MockGeneration(text=output, generation_tokens=80),
        )
        context = _build_report_render_context(results=[result], prompt="Describe.")
        out = tmp_path / "formatted.html"

        generate_html_report(
            [result],
            out,
            _stub_versions(),
            "Describe.",
            1.0,
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        escaped = html.escape(output, quote=True)
        model_entry = re.search(
            r'<article id="model-org-formatted">.*?</article>',
            content,
            flags=re.DOTALL,
        )
        assert model_entry is not None
        assert f'<pre class="model-output-readable">{escaped}</pre>' in model_entry.group(0)
        # The readable pre already carries the exact escaped bytes; no second
        # collapsed raw copy is emitted.
        assert "<summary>Exact raw output</summary>" not in model_entry.group(0)
        assert model_entry.group(0).count(escaped) == 1

    def test_html_report_preview_applies_exif_orientation(self, tmp_path: Path) -> None:
        """The embedded preview should match mlx-vlm's orientation-corrected input."""
        image_path = tmp_path / "rotated.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (40, 20), color="purple").save(image_path, exif=exif)
        out = tmp_path / "oriented.html"

        generate_html_report(
            results=[_make_success("org/model")],
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=1.0,
            image_path=image_path,
        )

        content = out.read_text(encoding="utf-8")
        encoded_match = re.search(r"data:image/jpeg;base64,([^\"]+)", content)
        assert encoded_match is not None
        with Image.open(io.BytesIO(base64.b64decode(encoded_match.group(1)))) as preview:
            assert preview.size == (20, 40)

    def test_html_report_includes_gallery_and_diagnostic_sections(self, tmp_path: Path) -> None:
        """HTML should mirror the current Gallery and Diagnostics structure."""
        out = tmp_path / "triage.html"
        results = [
            _make_success("org/good"),
            _make_harness_success("org/risky"),
            _make_failure("org/bad", error_package="transformers"),
        ]
        report_context = _build_report_render_context(results=results, prompt="describe")

        generate_html_report(
            results=results,
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=3.0,
            report_context=report_context,
        )

        content = out.read_text(encoding="utf-8")
        assert "Current-run Chooser" in content
        assert "Complete Per-model Evidence" in content
        assert "Maintainer Diagnostics" in content
        assert "Crashes requiring action" in content
        assert "Completed Runs with Observations" in content
        assert "org/risky" in content
        assert "transformers" in content

    def test_html_report_adds_exact_filterable_assessment_attributes(self, tmp_path: Path) -> None:
        """HTML chooser rows should filter only on the three canonical status strings."""
        out = tmp_path / "filterable.html"
        results = [_make_success("org/good"), _make_failure("org/bad", error_package="mlx-vlm")]

        generate_html_report(
            results=results,
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=2.0,
        )

        content = out.read_text(encoding="utf-8")
        assert content.count('data-execution="completed"') == 1
        assert content.count('data-execution="crashed"') == 1
        assert 'data-usability="usable"' in content
        assert 'data-usability="not_evaluated"' in content
        assert 'data-maintainer-status="none"' in content
        assert 'data-maintainer-status="actionable_failure"' in content
        assert "<caption>Current-run model chooser</caption>" in content
        assert 'scope="col"' in content
        assert 'role="status" aria-live="polite"' in content
        assert "data-recommendation=" not in content
        assert "data-failure-origin=" not in content

    def test_html_report_uses_compact_caption_columns_and_interactive_controls(
        self, tmp_path: Path
    ) -> None:
        """HTML filtering should remain presentation-only over canonical statuses."""
        out = tmp_path / "interactive.html"
        result = _make_success("org/caption-model")

        generate_html_report(
            results=[result],
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=1.0,
        )

        content = out.read_text(encoding="utf-8")
        assert 'id="model-search"' in content
        assert 'id="execution-filter"' in content
        assert 'id="usability-filter"' in content
        assert 'id="maintainer-status-filter"' in content
        assert 'data-model="org/caption-model"' in content
        assert '<option value="completed">completed</option>' in content
        assert '<option value="usable_with_caveats">concerns detected</option>' in content
        assert '<option value="not_evaluated">not assessed</option>' in content
        assert '<option value="observation_needs_reproduction">' in content
        assert "compatibility-filter" not in content
        assert "recommendation-filter" not in content
        assert "Diffusion Canvas Tokens" not in content
        assert "Diffusion Denoising Steps" not in content
        assert "Text Already Printed" not in content

    def test_html_report_escapes_filter_metadata(self, tmp_path: Path) -> None:
        """Model-controlled row metadata must remain safe in HTML attributes."""
        out = tmp_path / "metadata-escaped.html"
        model_name = 'org/model" onmouseover="alert(1)'

        generate_html_report(
            results=[_make_success(model_name)],
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=1.0,
        )

        content = out.read_text(encoding="utf-8")
        assert f'data-model="{model_name}"' not in content
        assert 'data-model="org/model&quot; onmouseover=&quot;alert(1)"' in content

    def test_html_report_marks_connectivity_disconnect_as_indeterminate(
        self, tmp_path: Path
    ) -> None:
        """Unreachable model files should not appear as conclusive crashes."""
        out = tmp_path / "indeterminate.html"
        result = replace(
            _make_failure("org/not-reached", error_package="unknown"),
            error_stage="Network Error",
            error_message="Model loading failed: Server disconnected without sending a response.",
        )

        generate_html_report(
            results=[result],
            filename=out,
            versions=_stub_versions(),
            prompt="describe",
            total_runtime_seconds=1.0,
        )

        content = out.read_text(encoding="utf-8")
        assert 'data-execution="indeterminate"' in content
        assert 'data-usability="not_evaluated"' in content
        assert 'data-maintainer-status="none"' in content

    def test_connectivity_disconnect_is_retained_but_not_filed_as_upstream_issue(
        self, tmp_path: Path
    ) -> None:
        """Diagnostics should show the attempt without producing an upstream issue draft."""
        result = _make_failure_with_details(
            "org/not-reached",
            error_msg="Model loading failed: Server disconnected without sending a response.",
            error_stage="Network Error",
            error_package="unknown",
            traceback_str="httpcore.RemoteProtocolError: Server disconnected without a response",
        )
        context = _build_report_render_context(
            results=[result],
            prompt="Describe it.",
            system_info={},
        )

        assert dict(context.assessments)[result.model_name].execution == "indeterminate"
        generated = _generate_github_issue_reports(
            report_context=context,
            output_dir=tmp_path,
            library_versions=_stub_versions(),
            system_info={},
            prompt="Describe it.",
        )
        assert generated == {}
        assert not list((tmp_path / "issues").glob("issue_*.md"))

    def test_reports_separate_attempted_evaluated_and_indeterminate_counts(
        self, tmp_path: Path
    ) -> None:
        """Human summaries should not inflate tested or hard-failure totals."""
        completed = _make_success("org/completed")
        disconnected = _make_failure_with_details(
            "org/not-reached",
            error_msg="Model loading failed: Server disconnected without sending a response.",
            error_stage="Network Error",
            error_package="unknown",
            traceback_str="httpcore.RemoteProtocolError: Server disconnected without a response",
        )
        results = [completed, disconnected]
        diagnostics = tmp_path / "diagnostics.md"

        context = _build_report_render_context(
            results=results,
            prompt="Describe it.",
            system_info={},
        )
        generate_diagnostics_report(
            results,
            diagnostics,
            prompt="Describe it.",
            library_versions=_stub_versions(),
            system_info={},
            report_context=context,
        )

        diagnostics_text = diagnostics.read_text(encoding="utf-8")
        assert re.search(r"\|\s*Attempted\s*\|\s*2\s*\|", diagnostics_text)
        assert re.search(r"\|\s*Conclusive outcomes\s*\|\s*1\s*\|", diagnostics_text)
        assert re.search(r"\|\s*Indeterminate\s*\|\s*1\s*\|", diagnostics_text)
        assert re.search(r"\|\s*Crashed\s*\|\s*0\s*\|", diagnostics_text)

    def test_html_report_escapes_untrusted_table_values(self, tmp_path: Path) -> None:
        """HTML reports should render model-controlled text as escaped table content."""
        out = tmp_path / "escaped.html"
        results = [
            PerformanceResult(
                model_name='org/<script>alert("model")</script>',
                success=True,
                generation=_MockGeneration(
                    text='<img src=x onerror="alert(1)">\n<script>alert("output")</script>',
                ),
                total_time=1.0,
                generation_time=0.5,
                model_load_time=0.5,
            ),
        ]

        generate_html_report(
            results=results,
            filename=out,
            versions=_stub_versions(),
            prompt='<script>alert("prompt")</script>',
            total_runtime_seconds=1.0,
        )

        content = out.read_text(encoding="utf-8")
        assert '<script>alert("model")</script>' not in content
        assert '<script>alert("output")</script>' not in content
        assert '<img src=x onerror="alert(1)">' not in content
        assert "&lt;script&gt;alert(&quot;model&quot;)&lt;/script&gt;" in content
        assert "&lt;script&gt;alert(&quot;output&quot;)&lt;/script&gt;" in content
        assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in content
        assert (
            '<pre><code class="language-text">'
            "&lt;script&gt;alert(&quot;prompt&quot;)&lt;/script&gt;</code></pre>"
        ) in content


# ===================================================================
# Retained Markdown artifacts
# ===================================================================


class TestRetainedMarkdownArtifactEdges:
    """Cross-artifact coverage for the retained Markdown surfaces."""

    def test_generated_report_stamps_do_not_use_emphasis_only_lines(
        self,
        tmp_path: Path,
    ) -> None:
        """Generated Markdown timestamp stamps should not look like headings."""
        success = _make_success("org/good")
        failure = _make_failure("org/bad")
        prompt = "Describe this image briefly."
        context = _build_report_render_context(results=[success, failure], prompt=prompt)

        generated_paths = [tmp_path / "model_gallery.md", tmp_path / "diagnostics.md"]

        generate_markdown_gallery_report(
            results=[success, failure],
            filename=generated_paths[0],
            prompt=prompt,
            report_context=context,
        )
        generate_diagnostics_report(
            [failure],
            generated_paths[1],
            prompt=prompt,
            library_versions=_stub_versions(),
            system_info={},
            report_context=context,
        )

        for path in generated_paths:
            _assert_no_generated_stamp_emphasis_headings(path.read_text(encoding="utf-8"))

    def test_generated_markdown_artifacts_keep_selected_output_link_style(
        self,
        tmp_path: Path,
    ) -> None:
        """Generated artifacts should keep link-style rules while non-Markdown outputs stay stable."""
        expected_markdown_artifacts = {
            "index.md",
            "issues/issue_org_broken.md",
            "reports/diagnostics.md",
            "reports/model_gallery.md",
        }
        expected_non_markdown_artifacts = {
            "reports/results.html",
            "results.jsonl",
        }
        mode_summaries: dict[str, dict[str, object]] = {}

        for link_style in ("github", "relative"):
            output_dir, output_paths, markdown_paths = _generate_output_artifacts_for_link_style(
                tmp_path,
                link_style=link_style,
            )
            file_paths = {
                path.relative_to(output_dir).as_posix()
                for path in output_dir.rglob("*")
                if path.is_file()
            }
            relative_paths = {path.relative_to(output_dir).as_posix() for path in markdown_paths}
            assert expected_markdown_artifacts.issubset(relative_paths)
            assert expected_non_markdown_artifacts.issubset(file_paths)
            assert any(path.startswith("issues/issue_") for path in relative_paths)

            link_targets = [
                target
                for path in markdown_paths
                for target in _extract_markdown_link_targets(path.read_text(encoding="utf-8"))
            ]
            relative_targets = [
                target for target in link_targets if _is_relative_markdown_target(target)
            ]
            github_output_targets = [
                target for target in link_targets if _is_published_output_github_target(target)
            ]

            if link_style == "github":
                assert github_output_targets
                assert relative_targets == []
            else:
                assert relative_targets
                environment_url = (
                    "https://github.com/jrp2014/check_models/blob/"
                    f"{check_models._github_blob_ref()}/src/output/environment.log"
                )
                assert github_output_targets == [environment_url]

            html_content = output_paths.html.read_text(encoding="utf-8")
            jsonl_records = [
                json.loads(line)
                for line in output_paths.jsonl.read_text(encoding="utf-8").splitlines()
            ]
            run_payload = jsonl_records[0]
            mode_summaries[link_style] = {
                "html_markers": (
                    "Action Snapshot" in html_content,
                    "org/good" in html_content,
                    "org/broken" in html_content,
                ),
                "jsonl_header": jsonl_records[0]["_type"],
                "jsonl_models": [record["model"] for record in jsonl_records[1:]],
                "metadata_counts": run_payload["counts"],
                "metadata_artifacts": sorted(run_payload["artifacts"]),
            }

            assert jsonl_records[0]["_type"] == "metadata"
            assert len(jsonl_records[1:]) == 2
            assert run_payload["format_version"] == "3.0"
            assert run_payload["producer"]["name"] == "check_models"
            assert run_payload["counts"] == {
                "models_attempted": 2,
                "models_evaluated": 2,
                "models_completed": 1,
                "models_crashed": 1,
                "models_indeterminate": 0,
            }

        assert mode_summaries["github"] == mode_summaries["relative"]


class TestMarkdownGalleryReport:
    """Coverage for the standalone markdown gallery artifact."""

    def test_empty_results_does_not_write(self, tmp_path: Path) -> None:
        """Empty result list should produce no gallery file."""
        out = tmp_path / "model_gallery.md"
        generate_markdown_gallery_report(
            results=[],
            filename=out,
            prompt="unused",
        )
        assert not out.exists()

    def test_gallery_includes_metadata_prompt_and_models(self, tmp_path: Path) -> None:
        """Gallery artifact should include selected metadata, prompt, and model sections."""
        out = tmp_path / "model_gallery.md"
        results = [_make_success("org/good"), _make_failure("org/bad")]
        context = _build_report_render_context(results=results, prompt="Describe this image fully.")
        generate_markdown_gallery_report(
            results=results,
            filename=out,
            prompt="Describe this image fully.",
            metadata={
                "title": "Harbor Sunset",
                "description": "Fishing boats at dusk.",
                "keywords": "harbor, boats, sunset",
                "date": "2026-03-08",
                "time": "18:42:00",
                "gps": "51.5000, -0.1200",
                "exif": "ignored raw blob",
            },
            report_context=context,
        )
        content = out.read_text(encoding="utf-8")
        assert "# Model Output Gallery" in content
        assert "## Image Metadata" in content
        assert "*Title:* Harbor Sunset" in content
        assert "*Description:* Fishing boats at dusk." in content
        assert "*Keywords:* harbor, boats, sunset" in content
        assert "*Date:* 2026-03-08" in content
        assert "*Time:* 18:42:00" in content
        assert "*GPS:* 51.5000, -0.1200" in content
        assert "ignored raw blob" not in content
        assert "## Prompt" in content
        assert "## Current-run Chooser" in content
        assert "## Avoid for This Run" in content
        assert "## Resource Highlights" in content
        assert "## Lowest-memory Usable Models (Including Caveats)" not in content
        assert "## Fastest Usable Models (Including Caveats)" not in content
        assert "> [!NOTE]" not in content
        assert "Describe this image fully." in content
        assert "```text\nDescribe this image fully." not in content
        assert "<summary>Complete evidence: org/good</summary>" in content
        assert '<pre class="model-output-readable">' in content
        assert '<a id="model-org-good"></a>' in content
        assert "*Mechanical checks:*" in content
        assert "*Observations:*" in content
        assert "*Verdict:*" not in content
        assert "*Maintainer:*" not in content
        assert "*Next action:*" not in content
        assert "### org/good" in content
        assert "### org/bad" in content

    def test_gallery_uses_cached_usability_not_recommendation_icons(self, tmp_path: Path) -> None:
        """Completed output should expose cached usability without recommendation policy."""
        text = "<think>Inspect.</think> A useful final caption."
        result = _make_success("org/thinking")
        analysis = check_models.analyze_generation_text(
            text,
            generated_tokens=12,
            prompt="Describe this image.",
        )
        result = replace(
            result,
            generation=_MockGeneration(text=text, generation_tokens=12),
            quality_analysis=analysis,
        )
        out = tmp_path / "model_gallery.md"
        context = _build_report_render_context(results=[result], prompt="Describe this image.")

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe this image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        chooser_row = next(line for line in content.splitlines() if "org/thinking" in line)
        assert "`no concerns detected`" in chooser_row
        assert "none" in chooser_row
        assert "### org/thinking" in content
        assert "### ⚠\ufe0f org/thinking" not in content

    def test_gallery_is_evidence_only_without_scoreboard_duplication(
        self,
        tmp_path: Path,
    ) -> None:
        """Gallery should keep output evidence without duplicating selection scoreboards."""
        result = PerformanceResult(
            model_name="org/evidence-model",
            success=True,
            generation=_MockGeneration(
                text="Two cats resting on a pink couch.",
                generation_tps=50.0,
                prompt_tokens=12,
                generation_tokens=8,
                peak_memory=2.0,
            ),
            total_time=1.0,
            generation_time=0.5,
            model_load_time=0.5,
        )
        out = tmp_path / "model_gallery.md"
        context = check_models._build_report_render_context(
            results=[result],
            prompt="Describe this image briefly.",
            eval_mode="triage",
        )

        generate_markdown_gallery_report(
            [result],
            out,
            prompt="Describe this image briefly.",
            metadata={"description": ""},
            report_context=context,
            versions={},
        )

        content = out.read_text(encoding="utf-8")
        assert "# Model Output Gallery" in content
        assert "Complete generated or crash evidence for every attempted model" in content
        assert "Review Shortlist" not in content
        assert "Failures by Package" not in content
        assert "Best keywording" not in content

    def test_gallery_suppresses_cataloging_score_rows_in_triage(
        self,
        tmp_path: Path,
    ) -> None:
        """Triage gallery output should not leak cataloging or keyword score rows."""
        result = PerformanceResult(
            model_name="org/brief-caption",
            success=True,
            generation=_MockGeneration(
                text=(
                    "Title: Two cats on a couch\n"
                    "Description: Two cats rest on a bright pink couch beside remote controls.\n"
                    "Keywords: cats, cats, cats, cats"
                ),
                prompt_tokens=12,
                generation_tokens=28,
            ),
            total_time=1.0,
            generation_time=0.5,
            model_load_time=0.5,
        )
        out = tmp_path / "model_gallery.md"
        context = check_models._build_report_render_context(
            results=[result],
            prompt="Describe this image briefly.",
            eval_mode="triage",
        )

        generate_markdown_gallery_report(
            [result],
            out,
            prompt="Describe this image briefly.",
            metadata={"description": ""},
            report_context=context,
            versions={},
        )

        content = out.read_text(encoding="utf-8")
        assert "*Score:*" not in content
        assert "Keywords are not specific" not in content
        assert "*Review focus:*" not in content

    def test_gallery_includes_consolidated_summary_and_version_stamps(
        self,
        tmp_path: Path,
    ) -> None:
        """Gallery should provide a pasteable run summary with package version stamps."""
        out = tmp_path / "model_gallery.md"
        results = [
            _make_quality_success("org/good", with_quality_issue=False),
            _make_harness_success(
                "org/risky",
                text="answer with | pipe and <think>leaked marker</think>",
                harness_detail="token_leak:<|end|>",
            ),
            _make_failure("org/bad", error_package="mlx-vlm"),
        ]
        context = _build_report_render_context(
            results=results,
            prompt="Describe this image briefly.",
            system_info={
                "GPU Architecture": "applegpu_g17s",
                "Recommended Working Set": "96 GB",
                "Fused Attention": "available",
            },
        )
        generate_markdown_gallery_report(
            results=results,
            filename=out,
            prompt="Describe this image briefly.",
            versions=_stub_versions(),
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        assert "## Run Stamps" in content
        assert "- `mlx-vlm`: `0.1`" in content
        assert "- `mlx`: `0.1`" in content
        assert "- *GPU Architecture:* applegpu_g17s" in content
        assert "- *Recommended Working Set:* 96 GB" in content
        assert "- *Fused Attention:* available" in content
        assert "## Current-run Chooser" in content
        assert "## Model Quality Summary" not in content
        assert "## All Model Output and Cost Summary" not in content
        assert "<!-- markdownlint-disable MD034 MD037 MD049 -->" in content
        assert "<!-- markdownlint-enable MD034 MD037 MD049 -->" in content
        assert "<!-- markdownlint-disable MD013 MD034 -->" not in content
        assert "<!-- markdownlint-enable MD013" not in content

        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        assert "Output preview" not in chooser
        assert "[`org/good`](#model-org-good)" in chooser
        assert "quality output" not in chooser
        assert "[`org/risky`](#model-org-risky)" in chooser
        assert "control tokens visible" in chooser
        assert "Prefill/first s" in chooser
        assert r"answer with \| pipe" not in chooser
        assert "&lt;think&gt;leaked marker&lt;/think&gt;" not in chooser
        assert "[`org/bad`](#model-org-bad)" in chooser
        assert "not assessed" in chooser
        assert "boom" not in chooser
        avoid = _extract_markdown_subsection(
            content,
            "## Avoid for This Run",
            end_headings=("## Output at a Glance",),
        )
        assert "Output preview" not in avoid
        assert "boom" not in avoid

    def test_gallery_keeps_exact_output_in_expandable_code_block(
        self,
        tmp_path: Path,
    ) -> None:
        """The gallery should keep exact evidence without making the chooser unwieldy."""
        complete_text = (
            "**BEGIN:** *model emphasis* " + ("distinct middle evidence " * 30) + "END-SENTINEL"
        )
        result = PerformanceResult(
            model_name="org/complete-output",
            success=True,
            generation=_MockGeneration(
                text=complete_text,
                prompt_tokens=18,
                generation_tokens=200,
                generation_tps=42.0,
                peak_memory=2.5,
            ),
            total_time=1.25,
            generation_time=0.75,
            model_load_time=0.50,
        )
        out = tmp_path / "model_gallery.md"
        context = _build_report_render_context(
            results=[result],
            prompt="Describe this image briefly.",
        )

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe this image briefly.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        assert "## Model Quality Summary" not in content
        assert "## All Model Output and Cost Summary" not in content
        assert "Output preview" not in chooser
        assert "BEGIN" not in chooser
        assert "END-SENTINEL" not in chooser
        assert "<!-- markdownlint-disable MD034 MD037 MD049 -->" in chooser
        assert chooser.index("Total s") < chooser.index("Gen TPS")
        assert "Gen tok" in chooser
        assert "Peak GB" in chooser
        assert "Observations" in chooser
        assert "<summary>Complete evidence: org/complete-output</summary>" in content
        # Plain text renders once as the readable view; the raw fence would be
        # byte-identical, so exactly one exact copy is retained.
        assert f"```text\n{complete_text}\n```" not in content
        assert complete_text in content
        assert content.count("END-SENTINEL") == 1

    def test_gallery_includes_all_model_output_and_cost_summary(
        self,
        tmp_path: Path,
    ) -> None:
        """Gallery should summarize every model's output beside runtime and memory cost."""
        success = PerformanceResult(
            model_name="org/full-caption",
            success=True,
            generation=_MockGeneration(
                text=(
                    "Title: Two cats on a sofa\n"
                    "Description: Two cats sit together on a pink sofa beside remote controls.\n"
                    "Keywords: cats, sofa, remote controls, indoor, pet portrait"
                ),
                prompt_tokens=18,
                generation_tokens=24,
                generation_tps=42.0,
                peak_memory=2.5,
            ),
            total_time=1.25,
            generation_time=0.75,
            model_load_time=0.50,
        )
        failure = replace(
            _make_failure("org/crashed", error_package="transformers"),
            total_time=0.33,
        )
        harness = _make_harness_success(
            "org/risky-output",
            text="cats",
            generation_tokens=3,
        )
        out = tmp_path / "model_gallery.md"
        context = _build_report_render_context(
            results=[success, failure, harness],
            prompt="Describe this image briefly.",
        )

        generate_markdown_gallery_report(
            results=[success, failure, harness],
            filename=out,
            prompt="Describe this image briefly.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        assert "Output preview" not in chooser
        assert "Peak GB" in chooser
        assert "Prefill/first s" in chooser
        assert "Observations" in chooser
        assert "[`org/full-caption`](#model-org-full-caption)" in chooser
        assert "Two cats sit together on a pink sofa" not in chooser
        assert "24" in chooser
        assert "42.0" in chooser
        assert "2.5" in chooser
        risky_row = next(line for line in chooser.splitlines() if "org/risky-output" in line)
        assert "| cats " not in risky_row
        assert "insufficient sample" in risky_row
        assert "[`org/crashed`](#model-org-crashed)" in chooser
        assert "boom" not in chooser
        crashed_evidence = _extract_markdown_subsection(
            content,
            "### org/crashed",
            end_headings=("### org/full-caption", "### org/risky-output"),
        )
        assert "*Total time:* 0.33s" in crashed_evidence

    def test_gallery_uses_skim_first_chooser_order_and_cached_assessments(
        self,
        tmp_path: Path,
    ) -> None:
        """Gallery order should move from chooser policy to complete evidence."""
        results = [
            _make_success("org/usable"),
            _make_success("org/caveated"),
            _make_success("org/unusable"),
            _make_failure("org/not-evaluated"),
        ]
        context = _build_report_render_context(results=results, prompt="Describe the image.")
        context = replace(
            context,
            assessments=(
                (
                    "org/usable",
                    check_models.ResultAssessment("completed", "usable", "none", ()),
                ),
                (
                    "org/caveated",
                    check_models.ResultAssessment("completed", "usable_with_caveats", "none", ()),
                ),
                (
                    "org/unusable",
                    check_models.ResultAssessment(
                        "completed",
                        "unusable",
                        "observation_needs_reproduction",
                        ("repeated_output",),
                    ),
                ),
                (
                    "org/not-evaluated",
                    check_models.ResultAssessment(
                        "crashed",
                        "not_evaluated",
                        "actionable_failure",
                        (),
                    ),
                ),
            ),
        )
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=results,
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        headings = [
            "## Current-run Chooser",
            "## Resource Highlights",
            "## Avoid for This Run",
            "## Complete Per-model Evidence",
        ]
        assert [content.index(heading) for heading in headings] == sorted(
            content.index(heading) for heading in headings
        )
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Resource Highlights",),
        )
        expected_model_order = (
            "org/usable",
            "org/caveated",
            "org/unusable",
            "org/not-evaluated",
        )
        assert [chooser.index(model) for model in expected_model_order] == sorted(
            chooser.index(model) for model in expected_model_order
        )
        assert [content.index(f"### {model}") for model in expected_model_order] == sorted(
            content.index(f"### {model}") for model in expected_model_order
        )
        assert "`concerns detected`" in chooser
        assert "`usable_with_caveats`" not in chooser
        assert "*Verdict:*" not in content
        assert "*Maintainer:*" not in content
        assert "*Next action:*" not in content
        assert "*Score:*" not in content

        html_out = tmp_path / "results.html"
        generate_html_report(
            results,
            html_out,
            versions={},
            prompt="Describe the image.",
            total_runtime_seconds=1.0,
            report_context=context,
        )
        html_content = html_out.read_text(encoding="utf-8")
        html_chooser = html_content[
            html_content.index('<div id="chooser-table">') : html_content.index(
                "</div>", html_content.index('<div id="chooser-table">')
            )
        ]
        assert [html_chooser.index(model) for model in expected_model_order] == sorted(
            html_chooser.index(model) for model in expected_model_order
        )
        assert "concerns detected" in html_chooser
        assert ">usable_with_caveats<" not in html_chooser
        html_complete_evidence = html_content[
            html_content.index('<section id="complete-model-evidence">') :
        ]
        assert [html_complete_evidence.index(model) for model in expected_model_order] == sorted(
            html_complete_evidence.index(model) for model in expected_model_order
        )

    def test_gallery_complete_output_uses_safe_fence_without_shortening(
        self,
        tmp_path: Path,
    ) -> None:
        """Complete output should survive prior limits and nested Markdown fences."""
        complete_text = (
            "BEGIN-COMPLETE\n```python\nprint('nested')\n```\n"
            + ("evidence-line-0123456789\n" * 600)
            + "END-COMPLETE"
        )
        result = replace(
            _make_success("org/complete"),
            generation=_MockGeneration(
                text=complete_text,
                prompt_tokens=32,
                generation_tokens=500,
                generation_tps=25.0,
            ),
        )
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        evidence = _extract_markdown_subsection(
            content,
            "### org/complete",
            end_headings=("<!-- markdownlint-enable",),
        )
        assert "<details>" in evidence
        assert "````text\n" in evidence
        assert complete_text in evidence
        assert content.count(complete_text) == 1

    def test_gallery_omits_preview_but_preserves_readable_model_formatting(
        self,
        tmp_path: Path,
    ) -> None:
        """Complete evidence should retain useful formatting without chooser duplication."""
        formatted_output = (
            "## Title\n\n"
            "Two cats resting\n\n"
            "- pink sofa\n"
            "- remote control\n\n"
            "@maintainer <details>unsafe</details>\n"
            "```text\nnested\n```"
        )
        result = replace(
            _make_success("org/formatted"),
            generation=_MockGeneration(text=formatted_output, generation_tokens=80),
        )
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        assert "## Title<br><br>Two cats resting" not in chooser
        assert '<pre class="model-output-readable">' in content
        assert "## Title\n\nTwo cats resting\n\n- pink sofa" in content
        assert "&#96;&#96;&#96;text" in content
        assert "&#64;maintainer &lt;details&gt;unsafe&lt;/details&gt;" in content
        assert "<summary>Exact raw output</summary>" in content
        assert content.count(formatted_output) == 1

    def test_short_generation_is_not_valid_throughput_but_keeps_raw_metrics(
        self,
        tmp_path: Path,
    ) -> None:
        """A short sample should affect throughput validity, not model usability."""
        short = replace(
            _make_success("org/short"),
            generation=_MockGeneration(
                text="A usable short response.",
                prompt_tokens=20,
                generation_tokens=8,
                generation_tps=999.0,
                peak_memory=1.0,
            ),
            generation_time=0.25,
        )
        valid = replace(
            _make_success("org/valid"),
            generation=_MockGeneration(
                text="A sufficiently measured response.",
                prompt_tokens=20,
                generation_tokens=20,
                generation_tps=40.0,
                peak_memory=2.0,
            ),
        )
        context = _build_report_render_context(results=[short, valid], prompt="Describe the image.")
        context = replace(
            context,
            assessments=tuple(
                (
                    result.model_name,
                    check_models.ResultAssessment("completed", "usable", "none", ()),
                )
                for result in (short, valid)
            ),
        )
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[short, valid],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        short_row = next(line for line in chooser.splitlines() if "org/short" in line)
        assert "no concerns detected" in short_row
        assert "insufficient sample" in short_row
        assert "999" not in short_row
        # Both clean rows share total_time=1.0; the tie resolves alphabetically.
        assert (
            "Quickest completion without detected concerns (end-to-end, including model load): "
            "`org/short` at 1.00s" in content
        )
        assert "Average clean-completion throughput" not in content
        assert "Decode tok/s stays per model in the chooser" in content
        evidence = _extract_markdown_subsection(
            content,
            "### org/short",
            end_headings=("### org/valid", "<!-- markdownlint-enable"),
        )
        assert "*Generation time:* 0.25s" in evidence
        assert "*Generation throughput (raw):* 999 tok/s" in evidence
        assert "*Generation tokens:* 8" in evidence

    def test_gallery_chooser_data_is_the_single_shared_dataset(self) -> None:
        """Markdown and HTML choosers must derive ordering and highlights here."""

        def gallery_row(
            model: str,
            usability: str,
            *,
            tps: float | None = None,
            memory: float | None = None,
        ) -> check_models.GalleryRow:
            return check_models.GalleryRow(
                model=model,
                usability=cast("check_models.ModelUsability", usability),
                observations=(),
                total_time_s=1.0,
                generation_tps=tps,
                first_token_latency_s=None,
                peak_memory_gb=memory,
                prompt_tokens=200,
                generation_tokens=100,
                output_preview="",
            )

        rows = [
            gallery_row("org/b-usable", "usable", tps=30.0, memory=2.0),
            gallery_row("org/a-usable", "usable", tps=30.0, memory=1.5),
            gallery_row("org/caveats", "usable_with_caveats", tps=10.0, memory=None),
            gallery_row("org/bad", "unusable"),
        ]

        data = check_models._gallery_chooser_data(rows)

        assert [row.model for row in data.ordered] == [
            "org/a-usable",
            "org/b-usable",
            "org/caveats",
            "org/bad",
        ]
        assert [row.model for row in data.avoided] == ["org/bad"]
        # End-to-end tie at 1.0 s resolves alphabetically; org/caveats is
        # excluded because highlights consider clean completions only.
        assert data.quickest is not None
        assert data.quickest.model == "org/a-usable"
        assert not hasattr(data, "average_tps")
        assert data.lowest_memory is not None
        assert data.lowest_memory.model == "org/a-usable"

    def test_gallery_output_glance_tables_actual_output_in_chooser_order(
        self,
        tmp_path: Path,
    ) -> None:
        """A skimmable table must show what each model actually said."""
        good = replace(
            _make_success("org/good"),
            generation=_MockGeneration(
                text="Title: Two cats on a sofa\nKeywords: cats, sofa", generation_tokens=20
            ),
        )
        bad = replace(_make_failure("org/bad"), error_message="load exploded")
        context = _build_report_render_context(results=[good, bad], prompt="Describe.")
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[good, bad],
            filename=out,
            prompt="Describe.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        glance = _extract_markdown_subsection(
            content,
            "## Output at a Glance",
            end_headings=("## Complete Per-model Evidence",),
        )
        # Actual output text, newline-collapsed, with links in chooser order.
        assert "Title: Two cats on a sofa<br>Keywords: cats, sofa" in glance
        assert "load exploded" in glance
        assert glance.index("org/good") < glance.index("org/bad")
        # The judgement-focused chooser stays free of output previews.
        chooser = _extract_markdown_subsection(
            content,
            "## Current-run Chooser",
            end_headings=("## Avoid for This Run",),
        )
        assert "Output preview" not in chooser
        assert content.index("## Avoid for This Run") < content.index("## Output at a Glance")

    def test_gallery_resource_policies_are_deterministic(self, tmp_path: Path) -> None:
        """Avoid, memory, and speed policies should have explicit stable ordering."""

        def result(
            name: str,
            *,
            memory: float | None,
            tokens: int,
            throughput: float | None,
        ) -> PerformanceResult:
            return PerformanceResult(
                model_name=name,
                success=True,
                generation=_MockGeneration(
                    text=f"output for {name}",
                    prompt_tokens=20,
                    generation_tokens=tokens,
                    generation_tps=throughput,
                    peak_memory=memory,
                ),
                total_time=1.0,
            )

        usable_results = [
            result("org/zeta", memory=None, tokens=8, throughput=900.0),
            result("org/beta", memory=2.0, tokens=20, throughput=30.0),
            result("org/alpha", memory=2.0, tokens=20, throughput=30.0),
            result("org/gamma", memory=1.0, tokens=20, throughput=10.0),
        ]
        avoided_results = [
            _make_success("org/z-unusable"),
            _make_success("org/a-unusable"),
            _make_failure("org/a-not-evaluated"),
        ]
        results = [*usable_results, *avoided_results]
        context = _build_report_render_context(results=results, prompt="Describe the image.")
        assessments = {
            result.model_name: check_models.ResultAssessment(
                "completed",
                "usable_with_caveats" if result.model_name == "org/beta" else "usable",
                "none",
                (),
            )
            for result in usable_results
        }
        assessments.update(
            {
                "org/z-unusable": check_models.ResultAssessment(
                    "completed", "unusable", "observation_needs_reproduction", ("empty_output",)
                ),
                "org/a-unusable": check_models.ResultAssessment(
                    "completed", "unusable", "observation_needs_reproduction", ("empty_output",)
                ),
                "org/a-not-evaluated": check_models.ResultAssessment(
                    "crashed", "not_evaluated", "actionable_failure", ()
                ),
            }
        )
        context = replace(context, assessments=tuple(assessments.items()))
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=results,
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        avoid = _extract_markdown_subsection(
            content,
            "## Avoid for This Run",
            end_headings=("## Output at a Glance",),
        )
        highlights = _extract_markdown_subsection(
            content,
            "## Resource Highlights",
            end_headings=("## Avoid for This Run",),
        )
        assert avoid.index("org/a-unusable") < avoid.index("org/z-unusable")
        assert avoid.index("org/z-unusable") < avoid.index("org/a-not-evaluated")
        # Highlights consider only clean completions (usable, no observations);
        # ties on end-to-end time resolve alphabetically.
        assert (
            "Quickest completion without detected concerns (end-to-end, including model load): "
            "`org/alpha` at " in highlights
        )
        assert "Fastest clean completion" not in highlights
        assert "Average clean-completion throughput" not in highlights
        # gamma has the lowest captured peak memory (1.0 GB) among clean rows.
        assert (
            "Lowest peak memory among completions without detected concerns: `org/gamma` at "
            in highlights
        )

    def test_gallery_crash_evidence_keeps_traceback_before_captured_output(
        self,
        tmp_path: Path,
    ) -> None:
        """Crash evidence should retain factual context and complete evidence priority."""
        result = replace(
            _make_failure("org/crashed", error_package="mlx-vlm"),
            failure_phase="decode",
            error_code="generation-failed",
            error_traceback="Traceback (most recent call last):\nRuntimeError: complete trace",
            captured_output_on_fail="complete captured stderr",
        )
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        evidence = _extract_markdown_subsection(
            content,
            "### org/crashed",
            end_headings=("<!-- markdownlint-enable",),
        )
        assert "*Failure phase:* decode" in evidence
        assert "*Error code:* generation-failed" in evidence
        assert "*Error package:* mlx-vlm" in evidence
        assert evidence.index("RuntimeError: complete trace") < evidence.index(
            "complete captured stderr"
        )

    def test_gallery_uses_cached_indeterminate_execution(self, tmp_path: Path) -> None:
        """Per-model evidence should not turn indeterminate attempts into crashes."""
        result = _make_failure("org/indeterminate", error_package="huggingface-hub")
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        context = replace(
            context,
            assessments=(
                (
                    result.model_name,
                    check_models.ResultAssessment(
                        "indeterminate",
                        "not_evaluated",
                        "observation_needs_reproduction",
                        (),
                    ),
                ),
            ),
        )
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        assert "*Execution:* indeterminate" in content
        assert "*Execution:* crashed" not in content

    def test_gallery_marks_missing_nested_diagnostic_fields_not_captured(
        self,
        tmp_path: Path,
    ) -> None:
        """Present diagnostic objects should not make absent nested facts disappear."""
        result = replace(
            _make_success("org/missing-nested"),
            runtime_diagnostics=RuntimeDiagnostics(stop_reason=None),
            prompt_diagnostics=check_models.PromptDiagnostics(
                processor_class=None,
                tokenizer_class=None,
            ),
        )
        context = _build_report_render_context(results=[result], prompt="Describe the image.")
        out = tmp_path / "model_gallery.md"

        generate_markdown_gallery_report(
            results=[result],
            filename=out,
            prompt="Describe the image.",
            report_context=context,
        )

        content = out.read_text(encoding="utf-8")
        evidence = _extract_markdown_subsection(
            content,
            "### org/missing-nested",
            end_headings=("<!-- markdownlint-enable",),
        )
        assert "*Stop reason:* not captured" in evidence
        assert "*Processor:* not captured" in evidence
        assert "*Tokenizer:* not captured" in evidence

    def test_gallery_keeps_chooser_and_per_model_factual_status(
        self,
        tmp_path: Path,
    ) -> None:
        """Gallery should keep cached status without legacy review projections."""
        out = tmp_path / "triage_gallery.md"
        results = [
            _make_success("org/good"),
            _make_harness_success("org/risky"),
            _make_failure("org/bad", error_package="mlx-vlm"),
        ]
        report_context = _build_report_render_context(results=results, prompt="describe")

        generate_markdown_gallery_report(
            results=results,
            filename=out,
            prompt="Describe this image fully.",
            report_context=report_context,
        )

        content = out.read_text(encoding="utf-8")
        assert "## Current-run Chooser" in content
        assert "Action Snapshot" not in content
        assert "## 🧭 Review Shortlist" not in content
        assert "## 🚨 Failures by Package (Actionable)" not in content
        assert "*Review focus:*" not in content
        assert "*Score:*" not in content
        assert "*Mechanical checks:*" in content
        assert "*Execution:*" in content
        assert "*Next action:*" not in content


class TestGithubIssueReportsCleanup:
    """Regression coverage for live stale crash-draft cleanup."""

    def test_stale_issue_files_removed(self, tmp_path: Path) -> None:
        """Old issue_*.md files are removed even when the next run has no crashes."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        stale_crash = issues_dir / "issue_001_crash.md"
        stale_harness = issues_dir / "issue_002_harness.md"
        stale_index = issues_dir / "index.md"
        readme = issues_dir / "README.md"
        stale_crash.write_text("stale crash report", encoding="utf-8")
        stale_harness.write_text("stale harness report", encoding="utf-8")
        stale_index.write_text("stale index", encoding="utf-8")
        readme.write_text("keep me", encoding="utf-8")
        context = _build_report_render_context(results=[], prompt="Describe the image.")

        generated = _generate_github_issue_reports(
            report_context=context,
            output_dir=tmp_path,
            library_versions=_stub_versions(),
            system_info={"Python Version": "3.13"},
            prompt="Describe the image.",
        )

        assert generated == {}
        assert not stale_crash.exists()
        assert not stale_harness.exists()
        assert not stale_index.exists()
        assert readme.exists()


class TestEmptyRecommendedBucketExplanation:
    """Regression coverage for the empty recommended bucket explanation."""


def test_repro_args_overlay_auto_applied_thinking_kwargs() -> None:
    """Per-model effective thinking kwargs must reach the native repro command."""
    run_args = Namespace(
        max_tokens=1000,
        temperature=0.0,
        enable_thinking=False,
        thinking_budget=None,
        thinking_start_token=None,
        thinking_end_token=check_models.DEFAULT_THINKING_END_MARKER,
        trust_remote_code=True,
    )
    effective = {
        "enable_thinking": True,
        "thinking_budget": 800,
        "thinking_start_token": "<think>",
        "thinking_end_token": "</think>",
        "max_tokens": 1000,  # non-thinking keys must not leak into the overlay
    }

    merged = check_models._effective_repro_args(run_args, effective)

    assert merged is not None
    assert merged is not run_args  # the global namespace is never mutated
    assert run_args.enable_thinking is False
    assert merged.enable_thinking is True
    assert merged.thinking_budget == 800

    tokens = check_models._build_native_mlx_vlm_cli_tokens(
        model_name="org/thinker",
        prompt="p",
        image_ref="img.jpg",
        run_args=merged,
    )
    command = " ".join(tokens)
    assert "--enable-thinking" in command
    assert "--thinking-budget 800" in command
    assert "--thinking-start-token <think>" in command


def test_repro_args_overlay_is_identity_without_thinking_kwargs() -> None:
    """No effective thinking kwargs means the global args pass through as-is."""
    run_args = Namespace(max_tokens=1000)

    assert check_models._effective_repro_args(run_args, None) is run_args
    assert check_models._effective_repro_args(run_args, {"max_tokens": 500}) is run_args
    assert check_models._effective_repro_args(None, {"enable_thinking": True}) is None


def test_shared_repro_caveat_lists_auto_thinking_models() -> None:
    """The shared MODEL_ID command must disclose per-model auto thinking flags."""
    run_args = Namespace(
        enable_thinking=False,
        thinking_budget=None,
        thinking_start_token=None,
        thinking_end_token=check_models.DEFAULT_THINKING_END_MARKER,
    )
    auto_result = check_models.PerformanceResult(
        model_name="org/auto-thinker",
        generation=None,
        success=True,
        prompt_diagnostics=check_models.PromptDiagnostics(
            generate_kwargs={
                "enable_thinking": True,
                "thinking_budget": 800,
                "thinking_start_token": "<think>",
                "thinking_end_token": "</think>",
            }
        ),
    )
    plain_result = check_models.PerformanceResult(
        model_name="org/plain",
        generation=None,
        success=True,
        prompt_diagnostics=check_models.PromptDiagnostics(generate_kwargs={}),
    )

    caveat = check_models._shared_repro_thinking_caveat([auto_result, plain_result], run_args)

    assert caveat is not None
    text = caveat.text
    assert "org/auto-thinker" in text
    assert "--thinking-budget 800" in text
    assert "org/plain" not in text

    assert check_models._shared_repro_thinking_caveat([plain_result], run_args) is None


def test_repro_overrides_require_value_difference() -> None:
    """Kwargs equal to the global args are not treated as per-model overrides."""
    run_args = Namespace(
        enable_thinking=True,
        thinking_budget=500,
        thinking_start_token=None,
        thinking_end_token=check_models.DEFAULT_THINKING_END_MARKER,
    )
    same = {
        "enable_thinking": True,
        "thinking_budget": 500,
        "thinking_end_token": check_models.DEFAULT_THINKING_END_MARKER,
    }

    assert check_models._repro_thinking_overrides(run_args, same) == {}
    assert check_models._effective_repro_args(run_args, same) is run_args


def test_component_rows_surface_editable_source_revision() -> None:
    """Editable/git installs list their exact revision beside the version.

    A version string such as 0.6.14 spans many upstream commits (including
    numerics fixes), so the revision is what pins a run's behaviour; installed
    (non-git) packages must not gain a spurious row.
    """
    provenance = {
        "mlx-vlm": {
            "version": "0.6.14",
            "install_type": "editable",
            "source_revision": "edf7b77f0000000000000000000000000000abcd",
            "vcs_revision": None,
        },
        "mlx": {
            "version": "0.32.1",
            "install_type": "installed",
            "source_revision": None,
            "vcs_revision": None,
        },
    }

    rows = check_models._collect_report_component_rows(
        versions={"mlx-vlm": "0.6.14", "mlx": "0.32.1"},
        system_info={},
        provenance=provenance,
    )

    assert rows == [
        ("mlx-vlm", "0.6.14"),
        ("mlx-vlm source revision", "edf7b77f0000000000000000000000000000abcd"),
        ("mlx", "0.32.1"),
    ]
    # Without provenance the rows are unchanged from before.
    assert check_models._collect_report_component_rows(
        versions={"mlx-vlm": "0.6.14"}, system_info={}
    ) == [("mlx-vlm", "0.6.14")]


def test_component_source_revision_prefers_source_then_vcs() -> None:
    """The helper reads source_revision first, falls back to vcs_revision, else None."""
    assert (
        check_models._component_source_revision(
            {"x": {"source_revision": "aaa", "vcs_revision": "bbb"}}, "x"
        )
        == "aaa"
    )
    assert (
        check_models._component_source_revision(
            {"x": {"source_revision": None, "vcs_revision": "bbb"}}, "x"
        )
        == "bbb"
    )
    assert check_models._component_source_revision({"x": {"source_revision": None}}, "x") is None
    assert check_models._component_source_revision(None, "x") is None
    assert check_models._component_source_revision({}, "missing") is None


# ── Run comparison (current sweep vs retained baseline) ─────────────────────


def _comparison_record(
    model: str,
    *,
    usability: str = "usable",
    observations: list[str] | None = None,
    text: str = "same text",
    tps: float | None = 100.0,
    peak_gb: float | None = 10.0,
    execution: str = "completed",
) -> dict[str, object]:
    record = _issue_summary_result(
        model, execution=execution, usability=usability, observations=observations
    )
    record["generated_text"] = text
    record["metrics"] = {
        **({"generation_tps": tps} if tps is not None else {}),
        **({"peak_memory_gb": peak_gb} if peak_gb is not None else {}),
    }
    return record


def _verified_comparison_kwargs(
    baseline: check_models.ComparisonBaseline,
) -> dict[str, object]:
    """Current-run facts that make the fixture baseline fully verified."""
    return {
        "current_metadata": baseline.metadata,
        "current_image": cast("check_models.RunImageRecord", {"sha256": "a" * 64}),
        "current_generation_settings": (("max_tokens", "1000"),),
    }


def _comparison_baseline(records: list[dict[str, object]]) -> check_models.ComparisonBaseline:
    metadata = cast(
        "check_models.JsonlMetadataRecord",
        {
            "_type": "metadata",
            "format_version": "2.0",
            "prompt": "p",
            "system": {"Python Version": "3.13.14", "GPU/Chip": "Apple M5 Max"},
            "timestamp": "2026-08-01 10:00:00 BST",
            "eval_mode": "assisted",
            "library_versions": {"mlx": "0.32.1", "mlx-vlm": "0.6.15"},
            "component_provenance": {
                "mlx": {"version": "0.32.1", "source_revision": "abcdef1234567890"},
            },
        },
    )
    return check_models.ComparisonBaseline(
        label="HEAD:src/output/results.jsonl",
        metadata=metadata,
        results=tuple(cast("check_models.JsonlResultRecord", r) for r in records),
        image=cast("check_models.RunImageRecord", {"sha256": "a" * 64}),
        generation_settings=(("max_tokens", "1000"),),
    )


def test_compare_run_results_reports_transitions_text_tps_and_memory() -> None:
    """The diff must surface exactly the mechanical changes and nothing else."""
    baseline = _comparison_baseline(
        [
            _comparison_record("org/steady"),
            _comparison_record("org/flipped", usability="usable", observations=[]),
            _comparison_record("org/faster", tps=100.0),
            _comparison_record("org/bigger", peak_gb=10.0),
            _comparison_record("org/gone"),
        ]
    )
    current = [
        _comparison_record("org/steady"),
        _comparison_record(
            "org/flipped",
            usability="usable_with_caveats",
            observations=["catalog_constraint_violation"],
            text="different",
        ),
        _comparison_record("org/faster", tps=130.0),  # +30% with no history -> fallback flag
        _comparison_record("org/bigger", peak_gb=12.0),  # +2 GB, +20%
        _comparison_record("org/new"),
    ]
    comparison = check_models.compare_run_results(
        [cast("check_models.JsonlResultRecord", r) for r in current],
        baseline,
        **cast("dict[str, Any]", _verified_comparison_kwargs(baseline)),
    )

    assert comparison.comparability == "comparable"
    assert comparison.throughput_comparable is True
    assert comparison.compared_models == 4
    assert comparison.models_added == ("org/new",)
    assert comparison.models_removed == ("org/gone",)
    assert [c.model for c in comparison.changes] == ["org/flipped"]
    change = comparison.changes[0]
    assert (change.baseline_usability, change.current_usability) == (
        "usable",
        "usable_with_caveats",
    )
    assert change.observations_added == ("catalog_constraint_violation",)
    assert comparison.identical_text_models == 3
    assert comparison.text_compared_models == 4
    assert comparison.tps_ratio_median == 1.0
    assert comparison.tps_ratio_max == 1.3
    assert [f.model for f in comparison.throughput_flags] == ["org/faster"]
    assert comparison.throughput_flags[0].band_source == "fallback"
    assert [m.model for m in comparison.memory_changes] == ["org/bigger"]
    assert comparison.baseline_components == (
        ("mlx", "0.32.1 @ abcdef123"),
        ("mlx-vlm", "0.6.15"),
        ("python", "3.13.14"),
        ("hardware", "Apple M5 Max"),
    )
    assert comparison.has_changes

    payload = check_models._run_comparison_to_json(comparison)
    assert payload is not None
    assert payload["comparability"] == "comparable"
    assert payload["throughput_comparable"] is True
    assert payload["execution_mode"] == {"baseline": "in_process", "current": "in_process"}
    assert payload["identical_text_models"] == 3
    changes = payload["changes"]
    assert isinstance(changes, list)
    first_change = changes[0]
    assert isinstance(first_change, dict)
    assert first_change["usability"] == ["usable", "usable_with_caveats"]


def test_compare_run_results_uses_history_bands_and_excludes_current_run(tmp_path: Path) -> None:
    """A per-model Tukey band from history wins over the fixed fallback band."""
    history = tmp_path / "results.history.jsonl"
    runs = [
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "h",
                # The fixture's current row resolves to revision-m; history
                # samples from any other revision would be excluded.
                "model_results": {
                    "org/m": {"generation_tps": tps, "resolved_revision": "revision-m"}
                },
            }
        )
        for tps in (100.0, 102.0, 98.0, 101.0, 99.0)
    ]
    # The record appended for the current run must not vouch for itself.
    runs.append(
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "h",
                "model_results": {
                    "org/m": {"generation_tps": 130.0, "resolved_revision": "revision-m"}
                },
            }
        )
    )
    history.write_text("\n".join(runs) + "\n", encoding="utf-8")

    baseline = _comparison_baseline([_comparison_record("org/m", tps=100.0)])
    # ±10% of the ~100 tok/s median is the floor; 115 sits outside both the
    # floor and the Tukey fence, 101 sits inside both.
    current = [cast("check_models.JsonlResultRecord", _comparison_record("org/m", tps=115.0))]
    comparison = check_models.compare_run_results(
        current,
        baseline,
        history_path=history,
        comparison_fingerprint="h",
        history_excludes_current=True,
        **cast("dict[str, Any]", _verified_comparison_kwargs(baseline)),
    )
    assert comparison.history_runs_used == 5
    assert [f.model for f in comparison.throughput_flags] == ["org/m"]
    flag = comparison.throughput_flags[0]
    assert flag.band_source == "history"
    assert flag.band_samples == 5
    assert flag.band_high < 115.0
    assert flag.band_high >= 110.0  # floor applied

    steady = [cast("check_models.JsonlResultRecord", _comparison_record("org/m", tps=101.0))]
    assert not check_models.compare_run_results(
        steady,
        baseline,
        history_path=history,
        comparison_fingerprint="h",
        **cast("dict[str, Any]", _verified_comparison_kwargs(baseline)),
    ).throughput_flags


def test_resolve_comparison_baseline_handles_none_path_and_missing(tmp_path: Path) -> None:
    """'none' disables, a file is read directly, garbage degrades to no comparison."""
    jsonl = tmp_path / "results.jsonl"
    assert check_models._resolve_comparison_baseline("none", jsonl) is None
    baseline_file = tmp_path / "baseline.jsonl"
    baseline_row = _comparison_record("org/m")
    baseline_file.write_text(
        json.dumps(_issue_summary_metadata((baseline_row,)))
        + "\n"
        + json.dumps(baseline_row)
        + "\n",
        encoding="utf-8",
    )
    loaded = check_models._resolve_comparison_baseline(str(baseline_file), jsonl)
    assert loaded is not None
    assert loaded.label == str(baseline_file)
    assert [r["model"] for r in loaded.results] == ["org/m"]

    # A schema-2 baseline is rejected by the single loader (no adapter): the
    # one-time incomparability is logged and no comparison is produced.
    schema2 = tmp_path / "schema2.jsonl"
    schema2.write_text(
        json.dumps(
            {
                "_type": "metadata",
                "format_version": "2.0",
                "prompt": "p",
                "system": {},
                "timestamp": "t",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert check_models._resolve_comparison_baseline(str(schema2), jsonl) is None
    # An untracked temp path under 'auto' yields no baseline rather than an error.
    assert check_models._resolve_comparison_baseline("auto", jsonl) is None


def test_run_issue_summary_comparison_section_renders_tables_and_collapses_long_lists() -> None:
    """The section names the baseline, shows transitions, and keeps targeted runs tidy."""
    baseline = _comparison_baseline([_comparison_record(f"org/m{i}") for i in range(12)])
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record("org/m0", usability="unusable", observations=["repeated_output"]),
        )
    ]
    comparison = check_models.compare_run_results(
        current, baseline, **cast("dict[str, Any]", _verified_comparison_kwargs(baseline))
    )
    section = check_models._run_issue_summary_comparison_section(comparison)
    rendered = "\n".join(check_models.render_report_markdown((section,)))
    assert "Since the baseline sweep" in rendered
    assert "HEAD:src/output/results.jsonl" in rendered
    assert "no concerns detected → major concerns" in rendered
    assert "+repeated text" in rendered
    assert "In baseline, not run this time: 11 models (targeted run" in rendered
    assert check_models._comparison_model_list(("org/a", "org/b")) == "`org/a`, `org/b`"


def test_compare_run_results_withholds_diff_when_inputs_differ() -> None:
    """A prompt/image/settings change is reported as such, never as a model regression."""
    baseline = _comparison_baseline([_comparison_record("org/m", usability="usable")])
    baseline = replace(
        baseline,
        image=cast("check_models.RunImageRecord", {"sha256": "a" * 64}),
        generation_settings=(("max_tokens", "1000"),),
    )
    current = [
        cast("check_models.JsonlResultRecord", _comparison_record("org/m", usability="unusable"))
    ]
    metadata = cast(
        "check_models.JsonlMetadataRecord",
        {**baseline.metadata, "prompt": "a different prompt", "eval_mode": "blind"},
    )
    comparison = check_models.compare_run_results(
        current,
        baseline,
        current_metadata=metadata,
        current_image=cast("check_models.RunImageRecord", {"sha256": "b" * 64}),
        current_generation_settings=(("max_tokens", "500"),),
    )
    assert comparison.comparability == "incomparable"
    assert "prompt differs" in comparison.incomparable_reasons
    assert any(r.startswith("image differs") for r in comparison.incomparable_reasons)
    assert any(
        r.startswith("generation settings differ: max_tokens")
        for r in comparison.incomparable_reasons
    )
    assert any("evaluation lane differs" in r for r in comparison.incomparable_reasons)

    payload = check_models._run_comparison_to_json(comparison)
    assert payload is not None
    assert payload["comparability"] == "incomparable"
    assert payload["execution_mode"] == {"baseline": "in_process", "current": "in_process"}
    assert "changes" not in payload
    rendered = "\n".join(
        check_models.render_report_markdown(
            (check_models._run_issue_summary_comparison_section(comparison),)
        )
    )
    assert "Not directly comparable" in rendered
    assert "no concerns detected → major concerns" not in rendered

    # Same inputs -> comparable, and a revision change is reported alongside the diff.
    same_metadata = cast("check_models.JsonlMetadataRecord", dict(baseline.metadata))
    moved = _comparison_record("org/m", usability="unusable")
    provenance = moved["model_provenance"]
    assert isinstance(provenance, dict)
    provenance["resolved_revision"] = "newrev123456"
    comparison = check_models.compare_run_results(
        [cast("check_models.JsonlResultRecord", moved)],
        baseline,
        current_metadata=same_metadata,
        current_image=cast("check_models.RunImageRecord", {"sha256": "a" * 64}),
        current_generation_settings=(("max_tokens", "1000"),),
    )
    assert comparison.comparability == "comparable"
    assert comparison.revision_changes == (("org/m", "revision-m", "newrev123456"),)


def test_history_bands_ignore_hashless_rows_and_respect_confirmed_append(tmp_path: Path) -> None:
    """Legacy rows without a comparison fingerprint cannot vouch for the current workload."""
    history = tmp_path / "results.history.jsonl"
    rows = [
        json.dumps({"_type": "run", "model_results": {"org/m": {"generation_tps": t}}})
        for t in (100.0, 101.0, 99.0, 100.5)
    ]
    history.write_text("\n".join(rows) + "\n", encoding="utf-8")
    bands, runs = check_models._history_tps_bands(history, fingerprint="h", exclude_last=False)
    assert bands == {}
    assert runs == 0
    # Without a current hash, legacy rows are usable.
    bands, runs = check_models._history_tps_bands(history, fingerprint=None, exclude_last=False)
    assert "org/m" in bands
    assert runs == 4
    # exclude_last only when the caller confirmed the append.
    _, runs_excl = check_models._history_tps_bands(history, fingerprint=None, exclude_last=True)
    assert runs_excl == 3


def test_throughput_withheld_when_execution_modes_differ() -> None:
    """Isolated vs in-process runs keep quality transitions but not tok/s ratios."""
    baseline = _comparison_baseline([_comparison_record("org/m", tps=100.0)])
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record("org/m", usability="unusable", tps=50.0),
        )
    ]
    comparison = check_models.compare_run_results(
        current,
        baseline,
        current_execution_mode="isolated",
        **cast("dict[str, Any]", _verified_comparison_kwargs(baseline)),
    )
    assert comparison.comparability == "comparable"
    assert comparison.throughput_comparable is False
    assert comparison.tps_ratio_median is None
    assert comparison.throughput_flags == ()
    assert comparison.memory_changes == ()
    assert [c.model for c in comparison.changes] == ["org/m"]
    payload = check_models._run_comparison_to_json(comparison)
    assert payload is not None
    assert payload["throughput_comparable"] is False
    assert payload["execution_mode"] == {"baseline": "in_process", "current": "isolated"}
    rendered = "\n".join(
        check_models.render_report_markdown(
            (check_models._run_issue_summary_comparison_section(comparison),)
        )
    )
    assert "withheld" in rendered


def test_throughput_withheld_when_hardware_differs() -> None:
    """A different chip keeps quality transitions but withholds tok/s and memory."""
    baseline = _comparison_baseline([_comparison_record("org/m", tps=100.0)])
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record("org/m", usability="unusable", tps=50.0),
        )
    ]
    kwargs = _verified_comparison_kwargs(baseline)
    kwargs["current_metadata"] = {
        **cast("dict[str, object]", baseline.metadata),
        "system": {"Python Version": "3.13.14", "GPU/Chip": "Apple M2 Ultra"},
    }
    comparison = check_models.compare_run_results(
        current, baseline, **cast("dict[str, Any]", kwargs)
    )
    assert comparison.comparability == "comparable"
    assert (comparison.baseline_hardware, comparison.current_hardware) == (
        "Apple M5 Max",
        "Apple M2 Ultra",
    )
    assert comparison.throughput_comparable is False
    assert comparison.tps_ratio_median is None
    assert comparison.throughput_flags == ()
    assert comparison.memory_changes == ()
    assert [c.model for c in comparison.changes] == ["org/m"]
    assert ("hardware", "Apple M5 Max") in comparison.baseline_components

    payload = check_models._run_comparison_to_json(comparison)
    assert payload is not None
    assert payload["throughput_comparable"] is False
    assert payload["hardware"] == {"baseline": "Apple M5 Max", "current": "Apple M2 Ultra"}
    assert check_models._run_comparison_from_json(payload) == comparison

    rendered = "\n".join(
        check_models.render_report_markdown(
            (check_models._run_issue_summary_comparison_section(comparison),)
        )
    )
    assert "Apple M2 Ultra now vs Apple M5 Max in the baseline" in rendered
    assert "withheld" in rendered


def test_missing_hardware_identity_is_unverified_not_comparable() -> None:
    """A header without a chip cannot vouch for like-for-like throughput."""
    baseline = _comparison_baseline([_comparison_record("org/m", tps=100.0)])
    kwargs = _verified_comparison_kwargs(baseline)
    kwargs["current_metadata"] = {
        **cast("dict[str, object]", baseline.metadata),
        "system": {"Python Version": "3.13.14"},
    }
    comparison = check_models.compare_run_results(
        [cast("check_models.JsonlResultRecord", _comparison_record("org/m", tps=100.0))],
        baseline,
        **cast("dict[str, Any]", kwargs),
    )
    assert comparison.comparability == "unknown"
    assert "hardware identity" in comparison.unverified_facts
    assert comparison.throughput_comparable is False
    assert comparison.current_hardware is None


def test_unknown_comparability_withholds_performance_but_keeps_transitions() -> None:
    """A baseline without run.json facts is 'unknown', never silently comparable."""
    baseline = replace(
        _comparison_baseline([_comparison_record("org/m", tps=100.0)]),
        image=None,
        generation_settings=(),
    )
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record("org/m", usability="unusable", tps=50.0),
        )
    ]
    comparison = check_models.compare_run_results(
        current, baseline, current_metadata=baseline.metadata
    )
    assert comparison.comparability == "unknown"
    assert "image identity" in comparison.unverified_facts
    assert "generation settings" in comparison.unverified_facts
    assert comparison.throughput_comparable is False
    assert comparison.throughput_flags == ()
    assert [c.model for c in comparison.changes] == ["org/m"]
    payload = check_models._run_comparison_to_json(comparison)
    assert payload is not None
    assert payload["comparability"] == "unknown"
    rendered = "\n".join(
        check_models.render_report_markdown(
            (check_models._run_issue_summary_comparison_section(comparison),)
        )
    )
    assert "Comparability unknown" in rendered


def test_oom_crash_gets_a_capacity_context_block_beside_the_exception() -> None:
    """An OOM draft gathers the recorded capacity facts and calls itself informational."""
    crash = PerformanceResult(
        model_name="org/oom",
        generation=None,
        success=False,
        upstream_boundary="generation_started",
        failure_phase="generation_before_first_token",
        error_stage="Model Error",
        error_type="RuntimeError",
        root_error_type="RuntimeError",
        root_error_module="mlx.core",
        root_error_message=(
            "[METAL] Command buffer execution failed: Insufficient Memory "
            "(00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)."
        ),
        error_message=(
            "Model runtime error during generation for org/oom: [METAL] Command buffer "
            "execution failed: Insufficient Memory."
        ),
        error_traceback="Traceback (most recent call last):\nRuntimeError: Insufficient Memory",
        captured_output_on_fail=(
            "=== STDOUT ===\n[WARNING] Generating with a model that requires 106352 MB which "
            "is close to the maximum recommended size of 110100 MB. This can be slow.\n"
        ),
        model_burden=check_models.ModelBurdenFacts(
            weight_bytes=111_519_423_247, quantization_bits=4
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_token_count=346, image_placeholder_count=0
        ),
    )
    assessment = check_models._assess_result(crash)
    assert assessment.execution == "crashed"
    blocks = check_models._diagnostics_model_blocks(
        crash,
        assessment,
        run_args=None,
        model_provenance=None,
        system_info={"RAM": "128.0 GB", "Recommended Working Set": "110.1 GB"},
        image_profile=check_models.ImageInputProfile(width=8693, height=5796, megapixels=50.4),
    )
    rendered = "\n".join(check_models.render_report_markdown(blocks))
    assert rendered.index("Root exception and chain") < rendered.index(
        "Memory capacity context (informational)"
    )
    assert rendered.index("Memory capacity context (informational)") < rendered.index(
        "Execution and provenance"
    )
    for fact in (
        "Checkpoint weights on disk:* 111.5 GB, 4-bit",
        "Machine RAM:* 128.0 GB",
        "Recommended working set:* 110.1 GB",
        "Input image:* 8693 x 5796 pixels (50.4 MP)",
        "346 text tokens in the rendered template; image tokens not counted",
        "requires 106352 MB which is close to the maximum recommended size of 110100 MB",
        "not by itself evidence of a defect",
        "does not predict peak memory reliably enough to skip models automatically",
    ):
        assert fact in " ".join(rendered.split()), fact

    plain = dataclasses.replace(
        crash,
        error_stage="Model Error",
        error_message="decoder exploded",
        root_error_message="decoder exploded",
        captured_output_on_fail="",
    )
    assert check_models._is_oom_failure(plain) is False
    assert check_models._is_oom_failure(crash) is True


def test_run_summary_counts_cap_hits_and_renders_constraint_breakdown(
    tmp_path: Path,
) -> None:
    """The header separates reaching the cap from demonstrably incomplete output.

    A model that supplies a usable answer exactly at the limit is counted as
    having reached it and nothing more; only degradation evidence makes it
    incomplete. Constraint failures aggregate with medians.
    """
    output_paths = _issue_summary_output_paths(tmp_path)
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result("org/neutral-at-cap", stop_reason="max_tokens"),
            _issue_summary_result(
                "org/capped",
                usability="unusable",
                stop_reason="max_tokens",
                observations=["token_cap_truncation", "catalog_constraint_violation"],
                details={
                    "title_word_count": 4,
                    "title_word_range": [5, 10],
                    "keyword_count": 380,
                    "keyword_count_range": [10, 18],
                    "duplicate_keywords": ["pond"],
                },
            ),
            _issue_summary_result(
                "org/aborted",
                usability="unusable",
                observations=["repetition_abort", "catalog_constraint_violation"],
                details={
                    "keyword_count": 40,
                    "keyword_count_range": [10, 18],
                },
            ),
            _issue_summary_result("org/clean"),
        ),
    )
    summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "- *Reached token limit:* 2" in content
    assert "- *Incomplete output at token limit:* 1" in content
    assert "Hit the token cap" not in content
    assert "- *Stopped early for repetition:* 1" in content
    assert "## Constraint-failure breakdown" in content
    # The renderer wraps bullet lines; compare against whitespace-normalized text.
    normalized = " ".join(content.split())
    assert (
        "Title length: 1 model(s) outside 5-10 words (1 below, 0 above; median observed 4)"
        in normalized
    )
    assert (
        "Keyword count: 2 model(s) outside 10-18 (0 below, 2 above; median observed 210)"
        in normalized
    )
    assert "Duplicate keywords: 1 model(s)" in normalized


def test_constraint_breakdown_keeps_each_declared_range() -> None:
    """Mixed declared ranges aggregate per-range, not against the last seen."""
    first = _issue_summary_result(
        "org/above",
        observations=["catalog_constraint_violation"],
        details={"title_word_count": 6, "title_word_range": [2, 4]},
    )
    second = _issue_summary_result(
        "org/below",
        observations=["catalog_constraint_violation"],
        details={"title_word_count": 5, "title_word_range": [6, 8]},
    )

    section = check_models._run_issue_summary_constraint_breakdown(
        [
            cast("check_models.JsonlResultRecord", first),
            cast("check_models.JsonlResultRecord", second),
        ]
    )
    assert section is not None
    rendered = " ".join("\n".join(check_models.render_report_markdown((section,))).split())
    assert "outside 2-4 words (0 below, 1 above" in rendered
    assert "outside 6-8 words (1 below, 0 above" in rendered


def test_run_summary_omits_constraint_breakdown_without_violations(tmp_path: Path) -> None:
    """No constraint violations means no breakdown section at all."""
    output_paths = _issue_summary_output_paths(tmp_path)
    _write_issue_summary_fixture(
        output_paths,
        results=(
            _issue_summary_result(
                "org/plain",
                usability="unusable",
                observations=["missing_requested_sections"],
            ),
        ),
    )
    summary = check_models.generate_run_issue_summary_report(output_paths)
    assert summary is not None
    content = summary.read_text(encoding="utf-8")
    assert "Constraint-failure breakdown" not in content


def test_comparison_excludes_repetition_aborted_generations_from_throughput() -> None:
    """A rate over an aborted (truncated) generation never enters ratios or flags."""
    baseline = _comparison_baseline(
        [
            _comparison_record("org/aborted", tps=100.0),
            _comparison_record("org/steady", tps=50.0),
        ]
    )
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record(
                "org/aborted",
                usability="unusable",
                observations=["repetition_abort", "repeated_output"],
                tps=400.0,
            ),
        ),
        cast("check_models.JsonlResultRecord", _comparison_record("org/steady", tps=55.0)),
    ]
    comparison = check_models.compare_run_results(
        current, baseline, **cast("dict[str, Any]", _verified_comparison_kwargs(baseline))
    )
    assert comparison is not None
    # Only the steady model contributes a ratio; the aborted 4x never appears.
    assert comparison.tps_ratio_median == pytest.approx(55.0 / 50.0)
    assert all(flag.model != "org/aborted" for flag in comparison.throughput_flags)


def test_history_bands_skip_repetition_aborted_samples(tmp_path: Path) -> None:
    """History rows from aborted generations must not shape the noise band."""
    aborted = {"generation_tps": 400.0, "stop_reason": "repetition_abort"}
    steady = {"generation_tps": 50.0, "stop_reason": "stop"}
    history = tmp_path / "results.history.jsonl"
    rows = [
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "h" * 8,
                "model_results": {"org/m": aborted if i % 2 else steady},
            }
        )
        for i in range(6)
    ]
    check_models._write_text_file(history, "\n".join(rows) + "\n")

    bands, runs = check_models._history_tps_bands(history, fingerprint="h" * 8, exclude_last=False)
    assert runs == 6
    # Only the three steady samples qualify; if that is below the minimum
    # sample count the band is absent — either way the 400 tok/s aborts
    # never widen the fence.
    band = bands.get("org/m")
    if band is not None:
        _low, high, samples = band
        assert samples == 3
        assert high < 400.0


def test_observation_delta_falls_back_to_raw_code_for_unknown_baseline_codes() -> None:
    """A baseline written by an older harness may carry retired observation codes."""
    change = check_models.RunComparisonModelChange(
        model="org/m",
        baseline_execution="completed",
        current_execution="completed",
        baseline_usability="usable",
        current_usability="usable",
        observations_added=("repeated_output",),
        observations_removed=("legacy_retired_code",),
    )
    rendered = check_models._format_observation_delta(change)
    assert "+repeated text" in rendered
    assert "-legacy_retired_code" in rendered


def test_comparison_surfaces_render_from_one_view(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Markdown tables and terminal lines must show the same derived cells."""
    baseline = _comparison_baseline(
        [_comparison_record("org/m", tps=100.0), _comparison_record("org/n", tps=50.0)]
    )
    current = [
        cast(
            "check_models.JsonlResultRecord",
            _comparison_record(
                "org/m", usability="unusable", observations=["repeated_output"], tps=130.0
            ),
        ),
        cast("check_models.JsonlResultRecord", _comparison_record("org/n", tps=50.0)),
    ]
    comparison = check_models.compare_run_results(
        current, baseline, **cast("dict[str, Any]", _verified_comparison_kwargs(baseline))
    )
    view = check_models._comparison_view(comparison)
    assert view.change_rows == (
        ("org/m", "completed", "no concerns detected → major concerns", "+repeated text"),
    )
    assert [row[0] for row in view.flag_rows] == ["org/m"]

    rendered = "\n".join(
        check_models.render_report_markdown(
            (check_models._run_issue_summary_comparison_section(comparison),)
        )
    )
    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        check_models._log_run_comparison(comparison)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for cell in ("no concerns detected → major concerns", "+repeated text"):
        assert cell in rendered
        assert cell in logged
    ratio_cell = view.flag_rows[0][3]
    assert ratio_cell in rendered
    assert ratio_cell in logged


def test_model_burden_rows_render_every_source_labelled_fact() -> None:
    """Every retained burden fact becomes a labelled diagnostics row, facts only."""
    result = PerformanceResult(
        model_name="org/m",
        generation=None,
        success=True,
        model_burden=check_models.ModelBurdenFacts(
            weight_bytes=4_000_000_000,
            parameter_count=7_000_000_000,
            parameter_count_source="config",
            quantization_bits=4,
            quantization_group_size=64,
            quantization_mode="affine",
            context_length=32_768,
            context_length_source="text_config.max_position_embeddings",
        ),
        runtime_diagnostics=check_models.RuntimeDiagnostics(model_load_active_memory_gb=6.0),
    )

    rows = dict(check_models._model_burden_rows(result))

    assert rows["Checkpoint weights (GB)"] == "4.00"
    assert rows["Parameter count"] == "7.00B (config)"
    assert rows["Quantization"] == "4-bit, group 64, affine"
    assert rows["Declared context length"] == "32,768 (text_config.max_position_embeddings)"
    assert rows["Load active memory vs checkpoint"] == "1.50x (6.00 GB vs 4.00 GB on disk)"


def test_model_burden_rows_are_empty_without_burden_facts() -> None:
    result = PerformanceResult(model_name="org/m", generation=None, success=True)
    assert check_models._model_burden_rows(result) == ()


def test_diagnostics_environment_section_lists_components_and_provenance() -> None:
    """The footer environment table names the tracked libraries and system keys."""
    parts = check_models._diagnostics_environment_section(
        versions={"mlx-vlm": "0.7.0", "mlx": "0.32.3", "transformers": "5.16.1"},
        system_info={"Python Version": "3.14.7", "OS": "Darwin 25.6.0"},
    )
    text = "\n".join(parts)
    # Table cells are column-aligned; compare with collapsed whitespace.
    rows = [" ".join(line.split()) for line in parts]

    assert "## Environment" in text
    assert "| mlx-vlm | 0.7.0 |" in rows
    assert "| Python Version | 3.14.7 |" in rows
    assert any("provenance" in row for row in rows)  # installed-distribution rows follow


def test_write_environment_failure_diagnostics_writes_report(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A missing-runtime failure still leaves a diagnostics report on disk."""
    args = argparse.Namespace(output_dir=tmp_path / "out")
    caplog.set_level(logging.INFO)

    check_models._write_environment_failure_diagnostics(
        args=args, library_versions={"mlx": "0.32.3"}, error_message="mlx_vlm is not importable"
    )

    diagnostics = check_models.ReportOutputPaths.from_root(args.output_dir).diagnostics
    assert "mlx_vlm is not importable" in diagnostics.read_text(encoding="utf-8")
    assert "Diagnostics:" in "\n".join(record.message for record in caplog.records)


def test_write_environment_failure_diagnostics_contains_write_errors(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    args = argparse.Namespace(output_dir=tmp_path / "out")
    caplog.set_level(logging.ERROR)

    with patch.object(check_models, "_write_text_file", side_effect=OSError("disk full")):
        check_models._write_environment_failure_diagnostics(
            args=args, library_versions={}, error_message="boom"
        )

    assert "Failed to write environment diagnostics report" in caplog.text


@pytest.mark.parametrize("profile", ["general", "metadata"])
def test_standalone_html_states_the_executed_assessment_scope(
    profile: check_models.AssessmentProfile,
) -> None:
    result = replace(_make_success(), assessment_profile=profile)
    context = check_models._build_html_report_context(
        results=[result], prompt="Any wording", system_info={}
    )
    scope = check_models._html_run_inputs(None, context)
    assert ("task compliance not assessed" in scope) == (profile == "general")
    assert ("metadata fields and duplicate keywords" in scope) == (profile == "metadata")


def test_gallery_preview_shows_the_final_answer_with_reasoning_under_disclosure() -> None:
    """A thinking model's preview is its answer; the trace is counted, not shown."""
    reasoning = "Let me reason about the picture at some length. " * 3
    answer = "Title: Stone mill by a river\nDescription: A mill.\nKeywords: mill, river"
    thinking = PerformanceResult(
        model_name="org/thinker",
        success=True,
        generation=_MockGeneration(
            text=f"<think>{reasoning}</think>\n{answer}", prompt_tokens=10, generation_tokens=40
        ),
        total_time=2.0,
    )
    assessment = check_models.ResultAssessment("completed", "usable", "none", ())
    row = check_models._gallery_row(thinking, assessment)
    assert row.output_preview.startswith("Title: Stone mill by a river")
    assert "reason about" not in row.output_preview
    assert row.reasoning_chars == len(f"<think>{reasoning}</think>")
    assert row.reasoning_preview.startswith("<think>Let me reason")

    markdown_cell = check_models._gallery_preview_cell_markdown(row)
    assert markdown_cell.startswith("Title: Stone mill by a river")
    assert "characters of reasoning omitted; complete output in the evidence block" in markdown_cell
    html_cell = check_models._gallery_preview_cell_html(row)
    assert html_cell.startswith("Title: Stone mill by a river")
    assert "<details><summary>" in html_cell
    assert "characters of reasoning omitted</summary><pre>&lt;think&gt;Let me reason" in html_cell

    # An unclosed trace is not reasoning yet: the preview keeps the raw text so
    # the incomplete-trace observation stays visible.
    unclosed = replace(
        thinking, generation=_MockGeneration(text="<think>still going", generation_tokens=5)
    )
    plain = check_models._gallery_row(unclosed, assessment)
    assert plain.output_preview == "<think>still going"
    assert plain.reasoning_chars == 0
    assert "reasoning omitted" not in check_models._gallery_preview_cell_markdown(plain)


def test_prompt_seeded_thinking_close_is_treated_as_reasoning() -> None:
    """A template-opened block the model merely closes counts as reasoning too."""
    result = PerformanceResult(
        model_name="org/seeded",
        success=True,
        generation=_MockGeneration(
            text="thinking continues here</think>Title: A title", generation_tokens=12
        ),
        prompt_diagnostics=check_models.PromptDiagnostics(
            processor_class="p",
            tokenizer_class="t",
            rendered_prompt="<|im_start|>assistant\n<think>\n",
        ),
        total_time=1.0,
    )
    answer, reasoning = check_models._final_answer_text(result)
    assert answer == "Title: A title"
    assert reasoning == "thinking continues here</think>"


def test_hardware_identity_includes_gpu_cores_and_ram() -> None:
    """The same chip with a different core count or memory is different hardware."""
    identity = check_models._hardware_identity
    assert identity({"GPU/Chip": "Apple M5 Max", "GPU Cores": "40", "RAM": "128.0 GB"}) == (
        "Apple M5 Max, 40 GPU cores, 128.0 GB RAM"
    )
    assert identity({"GPU/Chip": "Apple M5 Max"}) == "Apple M5 Max"
    assert identity({"GPU Cores": "40"}) is None
    assert identity(None) is None

    baseline = _comparison_baseline([_comparison_record("org/m", tps=100.0)])
    kwargs = _verified_comparison_kwargs(baseline)
    kwargs["current_metadata"] = {
        **cast("dict[str, object]", baseline.metadata),
        "system": {"Python Version": "3.13.14", "GPU/Chip": "Apple M5 Max", "GPU Cores": "32"},
    }
    comparison = check_models.compare_run_results(
        [cast("check_models.JsonlResultRecord", _comparison_record("org/m", tps=100.0))],
        baseline,
        **cast("dict[str, Any]", kwargs),
    )
    assert comparison.current_hardware == "Apple M5 Max, 32 GPU cores"
    assert comparison.throughput_comparable is False


def test_comparison_fingerprint_separates_workloads() -> None:
    """Prompt, image, settings, lane, execution mode and hardware all shape the identity."""
    base = {
        "prompt": "p",
        "image_sha256": "a" * 64,
        "generation_settings": {"max_tokens": 500, "temperature": 0.0},
        "execution_mode": "in_process",
        "eval_mode": "assisted",
        "system_info": {"GPU/Chip": "Apple M5 Max", "GPU Cores": "40", "RAM": "128.0 GB"},
    }
    fingerprint = check_models._comparison_fingerprint(**cast("dict[str, Any]", base))
    assert fingerprint == check_models._comparison_fingerprint(**cast("dict[str, Any]", base))
    for key, value in (
        ("prompt", "q"),
        ("image_sha256", "b" * 64),
        ("generation_settings", {"max_tokens": 500, "temperature": 0.2}),
        ("execution_mode", "isolated"),
        ("eval_mode", "blind"),
        ("system_info", {"GPU/Chip": "Apple M5 Max", "GPU Cores": "32", "RAM": "128.0 GB"}),
    ):
        changed = check_models._comparison_fingerprint(
            **cast("dict[str, Any]", {**base, key: value})
        )
        assert changed != fingerprint, key

    metadata = _issue_summary_metadata((_observed_result(),))
    from_header = check_models._comparison_fingerprint_from_metadata(
        cast("check_models.JsonlMetadataRecord", metadata)
    )
    assert from_header == check_models._comparison_fingerprint(
        prompt=str(metadata["prompt"]),
        image_sha256="a" * 64,
        generation_settings={"max_tokens": 500, "temperature": 0.0},
        execution_mode="in_process",
        eval_mode="assisted",
        system_info=cast("dict[str, object]", metadata["system"]),
    )


def test_history_bands_require_the_current_model_revision(tmp_path: Path) -> None:
    """Samples from another revision of the same model must not shape its band."""
    history = tmp_path / "results.history.jsonl"
    rows = [
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "f",
                "model_results": {
                    "org/m": {"generation_tps": 100.0 + i, "resolved_revision": "old"}
                },
            }
        )
        for i in range(5)
    ]
    check_models._write_text_file(history, "\n".join(rows) + "\n")
    with_old = check_models._history_tps_bands(
        history, fingerprint="f", exclude_last=False, current_revisions={"org/m": "old"}
    )[0]
    assert "org/m" in with_old
    with_new = check_models._history_tps_bands(
        history, fingerprint="f", exclude_last=False, current_revisions={"org/m": "new"}
    )[0]
    assert with_new == {}
    # An unknown current revision cannot exclude anything.
    assert (
        "org/m"
        in check_models._history_tps_bands(
            history, fingerprint="f", exclude_last=False, current_revisions={"org/m": None}
        )[0]
    )


def test_history_record_carries_fingerprint_and_model_revision() -> None:
    """The history row records the workload fingerprint and each model's revision."""
    record = check_models._build_history_run_record(
        results=[_make_success("org/m")],
        prompt="p",
        system_info={"GPU/Chip": "Apple M5 Max"},
        library_versions={},
        image_path=None,
        eval_mode="assisted",
        comparison_fingerprint="f" * 64,
        model_provenance={
            "org/m": {
                "model": "org/m",
                "requested_revision": None,
                "resolved_revision": "rev-m",
                "snapshot_path": None,
            }
        },
    )
    assert record["comparison_fingerprint"] == "f" * 64
    assert record["model_results"]["org/m"]["resolved_revision"] == "rev-m"


def test_reasoning_disclosure_keeps_the_whole_trace_when_the_answer_is_drafted_inside() -> None:
    """The omitted span comes from the delimiter processing, not from text matching."""
    answer = "Title: Stone mill by a river\nDescription: A mill.\nKeywords: mill, river"
    trace = f"<think>Let me draft it first.\n{answer}\nThat looks right, I will emit it.</think>"
    result = PerformanceResult(
        model_name="org/drafter",
        success=True,
        generation=_MockGeneration(
            text=f"{trace}\n{answer}", prompt_tokens=10, generation_tokens=40
        ),
        total_time=2.0,
    )
    final, reasoning = check_models._final_answer_text(result)
    assert final == answer
    assert reasoning == trace
    row = check_models._gallery_row(
        result, check_models.ResultAssessment("completed", "usable", "none", ())
    )
    assert row.reasoning_chars == len(trace)


def test_history_bands_require_matching_per_model_settings(tmp_path: Path) -> None:
    """A thinking budget change on one model must not blend into that model's band."""
    history = tmp_path / "results.history.jsonl"
    budget_100 = {"max_tokens": 500, "thinking_budget": 100}
    budget_800 = {"max_tokens": 500, "thinking_budget": 800}
    rows = [
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "f",
                "model_results": {
                    "org/m": {"generation_tps": 100.0 + i, "generation_settings": budget_100}
                },
            }
        )
        for i in range(5)
    ]
    check_models._write_text_file(history, "\n".join(rows) + "\n")
    canonical = check_models._canonical_generation_settings
    assert canonical(budget_100) != canonical(budget_800)
    assert canonical({}) is None
    same = check_models._history_tps_bands(
        history,
        fingerprint="f",
        exclude_last=False,
        current_settings={"org/m": canonical(budget_100)},
    )[0]
    assert "org/m" in same
    changed = check_models._history_tps_bands(
        history,
        fingerprint="f",
        exclude_last=False,
        current_settings={"org/m": canonical(budget_800)},
    )[0]
    assert changed == {}
    # History rows without per-model settings cannot vouch for a known current setting.
    bare = [
        json.dumps(
            {
                "_type": "run",
                "comparison_fingerprint": "f",
                "model_results": {"org/m": {"generation_tps": 100.0}},
            }
        )
    ] * 5
    check_models._write_text_file(history, "\n".join(bare) + "\n")
    assert (
        check_models._history_tps_bands(
            history,
            fingerprint="f",
            exclude_last=False,
            current_settings={"org/m": canonical(budget_100)},
        )[0]
        == {}
    )
    assert (
        "org/m"
        in check_models._history_tps_bands(
            history, fingerprint="f", exclude_last=False, current_settings={"org/m": None}
        )[0]
    )


def test_reproduction_inputs_offer_the_published_preview_as_a_stand_in() -> None:
    """An unpublished original still yields a verifiable command against the committed preview."""
    image_path = Path(__file__).parent / "fixtures/check_models-task9-fixture.jpg"
    preview = check_models._published_preview_record(image_path)
    assert preview is not None
    raw_preview = check_models._report_image_preview(image_path)
    assert raw_preview is not None
    asset_name = check_models._preview_asset_name(raw_preview[0], raw_preview[2])
    assert preview["name"] == asset_name
    assert preview["source_url"] == (
        "https://raw.githubusercontent.com/jrp2014/check_models/main/"
        f"src/output/reports/assets/{asset_name}"
    )
    preview_sha256 = preview["sha256"]
    assert preview_sha256 is not None
    assert asset_name == f"source-image-{preview_sha256[:16]}.jpg"
    width, height = preview["width"], preview["height"]
    assert width is not None
    assert height is not None
    assert max(width, height) <= 1024
    raw_preview = check_models._report_image_preview(image_path)
    assert raw_preview is not None
    assert preview["sha256"] == hashlib.sha256(raw_preview[2]).hexdigest()
    assert preview["size_bytes"] == len(raw_preview[2])

    original = check_models._run_image_record(image_path, None)
    blocks = check_models._reproduction_input_blocks(
        model_name="org/m",
        prompt="p",
        image=original,
        run_args=None,
        resolved_revision="rev",
        published_preview=preview,
    )
    rendered = "\n".join(check_models.render_report_markdown(blocks))
    assert "The original local input is not published" in rendered
    assert preview["source_url"] in rendered
    assert "Shareable stand-in" in rendered
    assert "not on the exact inference input" in rendered
    assert f"{preview['sha256']}  repro-image.jpg" in rendered
    assert "mlx_vlm.generate" in rendered

    plain = "\n".join(
        check_models.render_report_markdown(
            check_models._reproduction_input_blocks(
                model_name="org/m",
                prompt="p",
                image=original,
                run_args=None,
                resolved_revision="rev",
            )
        )
    )
    assert "Shareable stand-in" not in plain
    assert check_models._published_preview_record(None) is None


def test_file_digest_and_preview_are_cached_per_file_identity(tmp_path: Path) -> None:
    """The same bytes are hashed and re-encoded once per run, never per report."""
    target = tmp_path / "blob.bin"
    check_models._write_text_file(target, "one")
    first = check_models._sha256_file(target)
    with patch.object(check_models.hashlib, "file_digest", side_effect=AssertionError("re-hashed")):
        assert check_models._sha256_file(target) == first
    check_models._write_text_file(target, "two, longer")
    assert check_models._sha256_file(target) != first

    image_path = Path(__file__).parent / "fixtures/check_models-task9-fixture.jpg"
    assert check_models._report_image_preview(image_path) is check_models._report_image_preview(
        image_path
    )


def test_field_aware_preview_shows_a_little_of_each_catalogue_field() -> None:
    """The keywords, usually the weakest field, are visible instead of hidden by the description."""
    description = "A long factual description of the scene. " * 12
    keywords = ", ".join(f"keyword{i}" for i in range(18))
    answer = (
        f"Title: Georgian terrace on Gay Street\nDescription: {description}\nKeywords: {keywords}"
    )
    preview = check_models._field_aware_preview(answer, max_chars=280)
    assert preview is not None
    assert preview.startswith("Title: Georgian terrace on Gay Street | Description: A long factual")
    assert "Keywords (18): keyword0, keyword1" in preview
    assert preview.endswith(", ...")
    assert "keyword17" not in preview
    assert len(preview) <= 280 + 40  # the keyword tail has its own small budget

    partial = check_models._field_aware_preview(
        "Title: Only a title\nDescription: Short.", max_chars=280
    )
    assert partial == "Title: Only a title | Description: Short. | Keywords: (not detected)"
    assert (
        check_models._field_aware_preview("No labelled fields here at all.", max_chars=280) is None
    )


def test_gallery_row_uses_the_field_aware_preview_only_for_the_metadata_profile() -> None:
    """General-profile answers keep the head preview; metadata answers get the field view."""
    description = "A long factual description of the scene. " * 12
    answer = f"Title: Stone mill\nDescription: {description}\nKeywords: mill, river, water"
    assessment = check_models.ResultAssessment("completed", "usable", "none", ())
    metadata_row = check_models._gallery_row(
        replace(
            _make_success(),
            assessment_profile="metadata",
            generation=_MockGeneration(text=answer, prompt_tokens=10, generation_tokens=40),
        ),
        assessment,
    )
    assert "Keywords (3): mill, river, water" in metadata_row.output_preview
    general_row = check_models._gallery_row(
        replace(
            _make_success(),
            assessment_profile="general",
            generation=_MockGeneration(text=answer, prompt_tokens=10, generation_tokens=40),
        ),
        assessment,
    )
    assert "Keywords (3)" not in general_row.output_preview
    assert general_row.output_preview.startswith("Title: Stone mill\nDescription: A long")
