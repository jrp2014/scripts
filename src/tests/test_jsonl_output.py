"""Tests for JSONL output generation."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from PIL import Image

import check_models
from check_models import (
    JsonlMetadataRecord,
    JsonlResultRecord,
    PerformanceResult,
    RuntimeDiagnostics,
    _history_path_for_jsonl,
    append_history_record,
    save_jsonl_report,
)
from tools import safe_io


def _read_jsonl(path: Path) -> tuple[JsonlMetadataRecord, list[JsonlResultRecord]]:
    """Read JSONL file returning (metadata_header, result_rows)."""
    lines = safe_io.read_text_no_follow(path).strip().split("\n")
    header = cast("JsonlMetadataRecord", json.loads(lines[0]))
    results = [cast("JsonlResultRecord", json.loads(line)) for line in lines[1:]]
    return header, results


def _require_present[T](value: T | None, *, field_name: str) -> T:
    """Return an optional test payload after asserting that it exists."""
    if value is None:
        raise AssertionError(field_name)
    return value


@dataclass
class MockGeneration:
    """Mock generation result for testing."""

    text: str | None = "generated text"
    token: object | None = None
    logprobs: object | None = None
    prompt_tokens: int | None = 10
    generation_tokens: int | None = 20
    total_tokens: int | None = 30
    prompt_tps: float | None = 2.0
    generation_tps: float | None = 5.0
    peak_memory: float | None = 1.5
    time: float | None = None
    active_memory: float | None = None
    cache_memory: float | None = None
    quality_analysis: object | None = None


def test_save_jsonl_report_creates_file(tmp_path: Path) -> None:
    """Test that save_jsonl_report creates a file with metadata header."""
    output_file = tmp_path / "results.jsonl"
    results: list[PerformanceResult] = []
    save_jsonl_report(
        results,
        output_file,
        prompt="test",
        system_info={},
        mode_policy=check_models._build_report_mode_policy(eval_mode="blind"),
    )

    assert output_file.exists()
    header, rows = _read_jsonl(output_file)
    assert header["_type"] == "metadata"
    assert header["format_version"] == "3.0"
    assert header["prompt"] == "test"
    assert header["eval_mode"] == "blind"
    assert header["metadata_exposed_to_prompt"] is False
    assert rows == []


def test_jsonl_records_post_cleanup_memory_for_crashed_attempt(tmp_path: Path) -> None:
    """Allocator cleanup evidence must survive even when generation produced no result."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="org/crashed",
        generation=None,
        success=False,
        error_message="failed",
        runtime_diagnostics=RuntimeDiagnostics(
            post_cleanup_active_memory_gb=0.125,
            post_cleanup_cache_memory_gb=0.25,
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    assert rows[0]["metrics"]["post_cleanup_active_memory_gb"] == 0.125
    assert rows[0]["metrics"]["post_cleanup_cache_memory_gb"] == 0.25


def test_jsonl_records_architecture_precheck_when_determinate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Determinate arch pre-checks must land in the per-model record."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(model_name="org/aliased", generation=None, success=False)
    monkeypatch.setattr(
        check_models,
        "_arch_precheck_for_model",
        lambda _model: ("llava_qwen2", "fastvlm", True),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    assert rows[0]["architecture"] == {
        "model_type": "llava_qwen2",
        "resolved_model_type": "fastvlm",
        "supported_by_installed_mlx_vlm": True,
    }


def test_jsonl_omits_architecture_record_when_indeterminate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Indeterminate pre-checks must not fabricate an architecture verdict."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(model_name="org/unknown", generation=None, success=False)
    monkeypatch.setattr(
        check_models,
        "_arch_precheck_for_model",
        lambda _model: (None, None, None),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    assert "architecture" not in rows[0]


def test_jsonl_keeps_captured_upstream_output_for_successful_runs(
    tmp_path: Path,
) -> None:
    """Tee'd upstream console output must survive into records, home-sanitized."""
    output_file = tmp_path / "results.jsonl"
    home = str(Path.home())
    result = PerformanceResult(
        model_name="org/success",
        generation=MockGeneration(text="A caption."),
        success=True,
        captured_upstream_output=(
            f"Prompt: 100 tokens\n=== STDERR ===\nFetching {home}/cache/file"
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    captured = rows[0]["captured_upstream_output"]
    assert "Prompt: 100 tokens" in captured
    assert home not in captured

    quiet = PerformanceResult(
        model_name="org/quiet",
        generation=MockGeneration(text="A caption."),
        success=True,
    )
    save_jsonl_report([quiet], output_file, prompt="test", system_info={})
    _header, rows = _read_jsonl(output_file)
    assert "captured_upstream_output" not in rows[0]


def test_jsonl_prompt_diagnostics_keep_full_rendered_prompt(tmp_path: Path) -> None:
    """The complete rendered prompt must be recorded beside its bounded preview."""
    output_file = tmp_path / "results.jsonl"
    rendered = "<|im_start|>User:<image>" + ("describe " * 200) + "<|im_end|>"
    result = PerformanceResult(
        model_name="org/prompted",
        generation=MockGeneration(text="A caption."),
        success=True,
        prompt_diagnostics=check_models.PromptDiagnostics(
            rendered_prompt_preview=rendered[:100],
            rendered_prompt=rendered,
            rendered_prompt_chars=len(rendered),
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    diagnostics = rows[0]["prompt_diagnostics"]
    assert diagnostics is not None
    assert diagnostics["rendered_prompt"] == rendered
    preview = diagnostics["rendered_prompt_preview"]
    assert isinstance(preview, str)
    assert len(preview) == 100


def test_save_jsonl_report_includes_library_versions_in_metadata(tmp_path: Path) -> None:
    """Metadata header should preserve the shared library-version snapshot."""
    output_file = tmp_path / "results.jsonl"
    versions = cast(
        "check_models.LibraryVersionDict",
        {"mlx": "0.31.1", "mlx-vlm": "0.4.4", "transformers": "5.7.0"},
    )

    save_jsonl_report(
        [],
        output_file,
        prompt="test",
        system_info={},
        library_versions=versions,
    )

    header, rows = _read_jsonl(output_file)
    assert header.get("library_versions") == versions
    assert rows == []


def test_jsonl_system_provenance_is_public_safe_while_history_stays_raw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Published JSONL should redact local roots without changing raw history evidence."""
    monkeypatch.setattr(
        check_models.Path,
        "home",
        classmethod(lambda _cls: check_models.Path("/Users/alice")),
    )
    system_info = {
        "Home tool": "/Users/alice/projects/mlx/bin/tool",
        "Private cache": "/private/var/folders/build/cache",
        "OS": "Darwin 25.5.0",
    }
    output_file = tmp_path / "results.jsonl"

    save_jsonl_report([], output_file, prompt="test", system_info=system_info)
    header, rows = _read_jsonl(output_file)
    history = append_history_record(
        history_path=tmp_path / "results.history.jsonl",
        results=[],
        prompt="test",
        system_info=system_info,
        library_versions={},
        image_path=check_models.Path("/private/tmp/source.jpg"),
        eval_mode="blind",
    )
    assert history is not None

    assert header["system"] == {
        "Home tool": "~/projects/mlx/bin/tool",
        "Private cache": "<private>/var/folders/build/cache",
        "OS": "Darwin 25.5.0",
    }
    assert "/Users/alice" not in output_file.read_text(encoding="utf-8")
    assert "/private/" not in output_file.read_text(encoding="utf-8")
    assert rows == []
    assert history["system"] == system_info
    assert history["image_path"] == "/private/tmp/source.jpg"


def test_retained_metadata_captures_public_snapshot_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run JSON should capture stable public snapshot metadata."""
    analysis = dataclasses.replace(
        check_models.analyze_generation_text(
            "Two cats on a pink couch.",
            generated_tokens=7,
            prompt_tokens=80,
            prompt="Describe this image briefly.",
        ),
        prompt_tokens_total=80,
        prompt_tokens_text_est=12,
        prompt_tokens_nontext_est=68,
    )
    result = PerformanceResult(
        model_name="org/caption-model",
        generation=MockGeneration(
            text="Two cats on a pink couch.",
            generation_tps=12.0,
            prompt_tokens=8,
            generation_tokens=7,
            peak_memory=1.5,
        ),
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
        quality_analysis=analysis,
        prompt_diagnostics=check_models.PromptDiagnostics(
            processed_image_width=640,
            processed_image_height=480,
            image_patch_count=120,
            generate_kwargs={
                "max_tokens": 500,
                "temperature": 0.0,
                "prefill_step_size": 4096,
            },
        ),
    )
    out = tmp_path / "results.jsonl"
    image_path = tmp_path / "catalogue.jpg"
    Image.new("RGB", (12, 8), "blue").save(image_path)
    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image briefly.",
        image_path=image_path,
        metadata={"description": ""},
        eval_mode="triage",
    )
    monkeypatch.setattr(
        check_models,
        "_collect_model_provenance",
        lambda model, requested_revision=None: {
            "model": model,
            "requested_revision": requested_revision,
            "resolved_revision": "snapshot123",
            "snapshot_path": "~/.cache/snapshots/snapshot123",
        },
    )

    check_models.save_jsonl_report(
        [result],
        out,
        "Describe this image briefly.",
        {},
        library_versions={"mlx-vlm": "0.6.3"},
        total_runtime_seconds=3.0,
        report_context=context,
        image_path=image_path,
        image_source_url="https://example.test/images/catalogue.jpg",
        trust_remote_code=False,
        requested_revision="release-branch",
        artifacts={
            "output_index": "index.md",
            "results_html": "reports/results.html",
            "model_gallery": "reports/model_gallery.md",
            "diagnostics": "reports/diagnostics.md",
            "results_jsonl": "results.jsonl",
            "log": "check_models.log",
            "environment": "environment.log",
        },
        producer={
            "name": "check_models",
            "version": "0.8.6",
            "git_revision": "abc123",
            "install_type": "editable",
        },
    )

    metadata, result_rows = _read_jsonl(out)
    header: dict[str, object] = dict(metadata)
    # cache_discovery is optional: present only when a local HF cache scan
    # yields entries, so it is validated separately rather than required here.
    discovery = header.pop("cache_discovery", None)
    if discovery is not None:
        assert isinstance(discovery, list)
        assert {"repo_id", "selected", "capability_verdict", "skip_reasons"} <= set(discovery[0])
    assert set(header) == {
        "assessment_profile",
        "_type",
        "format_version",
        "timestamp",
        "system",
        "eval_mode",
        "prompt",
        "prompt_sha256",
        "metadata_exposed_to_prompt",
        "execution_mode",
        "total_runtime_seconds",
        "counts",
        "artifacts",
        "library_versions",
        "component_provenance",
        "producer",
        "image",
        "generation_settings",
        "trust_remote_code",
        "comparison",
    }
    assert header["format_version"] == "3.0"
    assert header["eval_mode"] == "triage"
    assert "semantic_rankings_grounded" not in header
    assert "selection_basis" not in header
    assert "has_descriptive_metadata" not in header
    assert header["metadata_exposed_to_prompt"] is False
    assert header["counts"] == {
        "models_attempted": 1,
        "models_evaluated": 1,
        "models_completed": 1,
        "models_crashed": 0,
        "models_indeterminate": 0,
    }
    assert header["artifacts"] == {
        "output_index": "index.md",
        "results_html": "reports/results.html",
        "model_gallery": "reports/model_gallery.md",
        "diagnostics": "reports/diagnostics.md",
        "results_jsonl": "results.jsonl",
        "log": "check_models.log",
        "environment": "environment.log",
    }
    versions = cast("dict[str, str]", header["library_versions"])
    assert versions["mlx-vlm"] == "0.6.3"
    image = cast("dict[str, object]", header["image"])
    assert image["name"] == "catalogue.jpg"
    assert image["source_url"] == "https://example.test/images/catalogue.jpg"
    assert image["width"] == 12
    assert image["height"] == 8
    assert image["sha256"]
    assert cast("int", image["size_bytes"]) > 0
    assert str(tmp_path) not in out.read_text(encoding="utf-8")
    assert header["generation_settings"] == {
        "max_tokens": 500,
        "prefill_step_size": 4096,
        "temperature": 0.0,
    }
    assert header["trust_remote_code"] is False
    assert header["prompt_sha256"] == check_models._sha256_text("Describe this image briefly.")
    row = result_rows[0]
    assert row["model_provenance"] == {
        "model": result.model_name,
        "requested_revision": "release-branch",
        "resolved_revision": "snapshot123",
        "snapshot_path": "~/.cache/snapshots/snapshot123",
    }
    assert row["prompt_burden"] == {
        "total_tokens": 80,
        "text_tokens_est": 12,
        "nontext_tokens_est": 68,
        "text_tokens_source": "heuristic",
        "nontext_ratio": 0.85,
        "kind": "normal",
        "processed_image_width": 640,
        "processed_image_height": 480,
        "image_patch_count": 120,
    }
    assert header["producer"] == {
        "name": "check_models",
        "version": "0.8.6",
        "git_revision": "abc123",
        "install_type": "editable",
    }


def test_retained_manifest_includes_summary_only_for_surfaced_results() -> None:
    """The optional paste-ready issue artifact should follow the cached assessment."""
    result = PerformanceResult(
        model_name="org/empty-output",
        generation=MockGeneration(text="", generation_tokens=0),
        success=True,
    )
    context = check_models._build_report_render_context(
        results=[result],
        prompt="Describe this image.",
    )
    retained = check_models._build_retained_run(
        [result],
        prompt="Describe this image.",
        system_info={},
        report_context=context,
        total_runtime_seconds=1.0,
        artifacts={"results_jsonl": "results.jsonl"},
        producer={
            "name": "check_models",
            "version": "test",
            "git_revision": None,
            "install_type": "unknown",
        },
    )

    assert retained.metadata["artifacts"] == {"results_jsonl": "results.jsonl"}
    # The orchestrator's manifest builder adds the conditional summary entry.
    inputs_manifest = {"results_jsonl": "results.jsonl"}
    if any(
        assessment.maintainer_status != "none" or assessment.execution == "indeterminate"
        for _model, assessment in context.assessments
    ):
        inputs_manifest["run_issue_summary"] = "issues/run_summary.md"
    assert "run_issue_summary" in inputs_manifest


def test_metadata_counts_completed_crashed_and_indeterminate_results_consistently(
    tmp_path: Path,
) -> None:
    """Run counts should partition attempts while evaluated outcomes remain conclusive."""
    completed = PerformanceResult(model_name="org/completed", generation=None, success=True)
    crashed = PerformanceResult(
        model_name="org/crashed",
        generation=None,
        success=False,
        error_stage="Generation",
        error_message="decode failed",
    )
    disconnected = PerformanceResult(
        model_name="org/not-reached",
        generation=None,
        success=False,
        error_stage="Network Error",
        error_message="Model loading failed: Server disconnected without sending a response.",
        error_package="unknown",
    )
    results = [completed, crashed, disconnected]
    context = check_models._build_report_render_context(results=results, prompt="Describe it.")
    out = tmp_path / "results.jsonl"

    check_models.save_jsonl_report(
        results,
        out,
        "Describe it.",
        {},
        report_context=context,
        total_runtime_seconds=2.0,
        producer={
            "name": "check_models",
            "version": "test",
            "git_revision": None,
            "install_type": "unknown",
        },
    )

    header, _rows = _read_jsonl(out)
    counts = header["counts"]
    assert counts == {
        "models_attempted": 3,
        "models_evaluated": 2,
        "models_completed": 1,
        "models_crashed": 1,
        "models_indeterminate": 1,
    }
    assert counts["models_attempted"] == (
        counts["models_completed"] + counts["models_crashed"] + counts["models_indeterminate"]
    )
    assert counts["models_evaluated"] == (counts["models_completed"] + counts["models_crashed"])


def test_check_models_provenance_degrades_without_install_or_git_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run metadata collection should remain usable outside an installed Git checkout."""

    def missing_version(_distribution_name: str) -> str:
        raise check_models.PackageNotFoundError

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(check_models, "version", missing_version)
    monkeypatch.setattr(check_models, "_distribution_is_editable", lambda _name: False)
    monkeypatch.setattr(check_models, "_run_macos_toolchain_command", lambda _cmd: None)

    assert check_models._collect_check_models_provenance() == {
        "name": "check_models",
        "version": "unknown",
        "git_revision": None,
        "install_type": "unknown",
        "dirty": None,
    }


def _declared_pyproject_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def test_check_models_provenance_reports_the_checkout_version_in_a_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inside a checkout the declared pyproject version wins over stale install metadata."""
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(check_models, "version", lambda _name: "0.0.1-stale-metadata")
    monkeypatch.setattr(check_models, "_distribution_is_editable", lambda _name: True)
    monkeypatch.setattr(
        check_models,
        "_run_macos_toolchain_command",
        lambda command, **_kw: "" if "status" in command else "abc123",
    )

    record = check_models._collect_check_models_provenance()

    assert record["install_type"] == "editable"
    assert record["version"] == _declared_pyproject_version()
    assert record["git_revision"] == "abc123"


def test_check_models_provenance_falls_back_to_install_metadata_outside_a_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a checkout the installed distribution's own version is all there is."""
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(check_models, "version", lambda _name: "0.9.0")
    monkeypatch.setattr(check_models, "_distribution_is_editable", lambda _name: False)
    monkeypatch.setattr(check_models, "_run_macos_toolchain_command", lambda _cmd, **_kw: None)

    record = check_models._collect_check_models_provenance()

    assert record["install_type"] == "installed"
    assert record["version"] == "0.9.0"


def test_check_models_provenance_records_dirty_source_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_models, "version", lambda _name: "0.9.0")
    monkeypatch.setattr(check_models, "_distribution_is_editable", lambda _name: True)

    def git_probe(command: tuple[str, ...], **_kwargs: object) -> str:
        return " M src/check_models.py" if "status" in command else "abc123"

    monkeypatch.setattr(check_models, "_run_macos_toolchain_command", git_probe)

    assert check_models._collect_check_models_provenance()["dirty"] is True


def test_check_models_provenance_ignores_generated_output_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Writing retained artifacts must not make the producer mark itself dirty."""
    monkeypatch.setattr(check_models, "version", lambda _name: "0.9.0")
    monkeypatch.setattr(check_models, "_distribution_is_editable", lambda _name: True)

    def git_probe(command: tuple[str, ...], **_kwargs: object) -> str:
        if "status" not in command:
            return "abc123"
        return "" if ":(exclude)src/output" in command else " M src/output/run.json"

    monkeypatch.setattr(check_models, "_run_macos_toolchain_command", git_probe)

    assert check_models._collect_check_models_provenance()["dirty"] is False


def test_component_provenance_captures_editable_source_without_home_disclosure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editable component metadata should retain source and revision safely."""
    monkeypatch.setattr(
        check_models,
        "_distribution_direct_url",
        lambda _name: {
            "url": "file:///Users/example/src/mlx-vlm",
            "dir_info": {"editable": True},
        },
    )
    monkeypatch.setattr(
        check_models,
        "_distribution_location",
        lambda _name: "/Users/example/miniconda/envs/mlx-vlm/lib/python3.13/site-packages",
    )
    monkeypatch.setattr(
        check_models,
        "_local_source_revision",
        lambda _path: "abc123",
    )
    monkeypatch.setattr(
        check_models.Path, "home", classmethod(lambda _cls: check_models.Path("/Users/example"))
    )

    provenance = check_models._collect_component_provenance({"mlx-vlm": "0.6.4"})

    assert provenance["mlx-vlm"] == {
        "version": "0.6.4",
        "install_type": "editable",
        "source_location": "~/src/mlx-vlm",
        "source_revision": "abc123",
        "direct_url": "file://~/src/mlx-vlm",
        "vcs_revision": None,
    }


def test_model_provenance_distinguishes_requested_and_resolved_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local snapshot identity should not be confused with the requested ref."""
    snapshot_sha = "0123456789abcdef"
    snapshot = check_models.Path(
        f"/Users/example/.cache/huggingface/hub/models--org--model/snapshots/{snapshot_sha}"
    )
    monkeypatch.setattr(
        check_models,
        "_resolve_model_snapshot",
        lambda _model, _revision=None: check_models.ResolvedSnapshot(
            snapshot, "requested-revision"
        ),
    )
    monkeypatch.setattr(
        check_models.Path, "home", classmethod(lambda _cls: check_models.Path("/Users/example"))
    )

    provenance = check_models._collect_model_provenance(
        "org/model",
        requested_revision="main",
    )

    assert provenance == {
        "model": "org/model",
        "requested_revision": "main",
        "resolved_revision": snapshot_sha,
        "snapshot_path": ("~/.cache/huggingface/hub/models--org--model/snapshots/" + snapshot_sha),
        "revision_source": "requested-revision",
    }


@pytest.mark.parametrize("profile", ["general", "metadata"])
def test_retained_profile_matches_the_executed_checks(
    tmp_path: Path, profile: check_models.AssessmentProfile
) -> None:
    """A header must not claim general-only checks for a metadata-assessed result."""
    result = PerformanceResult(
        model_name="org/m",
        generation=MockGeneration(text="Yes"),
        success=True,
        assessment_profile=profile,
    )
    output = tmp_path / "results.jsonl"
    save_jsonl_report([result], output, prompt="Please answer", system_info={})
    header, rows = _read_jsonl(output)
    assert header["assessment_profile"] == profile
    assert rows[0]["assessment"]["profile"] == profile
    assert rows[0]["assessment"]["observations"] == (
        ["missing_requested_sections"] if profile == "metadata" else []
    )
    assert rows[0]["generated_text"] == "Yes"


def test_metadata_counts_remain_evidence_even_without_a_violation() -> None:
    """Counts are neutral facts, not verdicts derived from prompt prose."""
    compliant = PerformanceResult(
        model_name="org/compliant",
        generation=MockGeneration(),
        success=True,
        quality_analysis=check_models.GenerationQualityAnalysis(
            is_repetitive=False,
            repeated_token=None,
            title_word_count=5,
            keyword_count=10,
        ),
    )
    violation = dataclasses.replace(
        compliant,
        model_name="org/violation",
        quality_analysis=dataclasses.replace(
            _require_present(compliant.quality_analysis, field_name="quality_analysis"),
            title_word_count=4,
            duplicate_keywords=["halesworth"],
        ),
    )

    assert check_models._observation_details(compliant) == {
        "title_word_count": 5,
        "keyword_count": 10,
    }
    assert check_models._observation_details(violation) == {
        "title_word_count": 4,
        "keyword_count": 10,
        "duplicate_keywords": ["halesworth"],
    }


def test_metadata_includes_component_and_model_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Primary machine artifacts should expose the same component identity payload."""
    components = {
        "mlx-vlm": {
            "version": "0.6.4",
            "install_type": "wheel",
            "source_location": "~/env/site-packages",
            "source_revision": None,
            "direct_url": None,
            "vcs_revision": None,
        }
    }
    monkeypatch.setattr(
        check_models, "_collect_component_provenance", lambda _versions=None: components
    )
    monkeypatch.setattr(
        check_models,
        "_collect_model_provenance",
        lambda model, requested_revision=None: {
            "model": model,
            "requested_revision": requested_revision,
            "resolved_revision": "snapshot123",
            "snapshot_path": "~/.cache/snapshots/snapshot123",
        },
    )
    result = PerformanceResult(model_name="org/model", generation=MockGeneration(), success=True)
    context = check_models._build_report_render_context(results=[result], prompt="describe")
    jsonl_path = tmp_path / "results.jsonl"

    save_jsonl_report(
        [result],
        jsonl_path,
        "describe",
        {},
        library_versions={"mlx-vlm": "0.6.4"},
        requested_revision="release-branch",
        report_context=context,
    )

    header, rows = _read_jsonl(jsonl_path)
    assert header["component_provenance"] == components
    assert rows[0]["model_provenance"]["resolved_revision"] == "snapshot123"
    assert rows[0]["model_provenance"]["requested_revision"] == "release-branch"


def test_jsonl_metrics_fall_back_to_generation_runtime_fields(tmp_path: Path) -> None:
    """JSONL metrics should use performance fields attached to GenerationResult."""
    result = PerformanceResult(
        model_name="fake/model",
        generation=MockGeneration(active_memory=0.75, cache_memory=0.25),
        success=True,
        active_memory=None,
        cache_memory=None,
        runtime_diagnostics=RuntimeDiagnostics(model_load_active_memory_gb=1.0),
    )
    output_file = tmp_path / "results.jsonl"
    save_jsonl_report([result], output_file, prompt="describe", system_info={})
    _header, rows = _read_jsonl(output_file)
    record = rows[0]

    metrics = record["metrics"]
    assert metrics["prompt_tokens"] == 10
    assert metrics["generation_tps"] == 5.0
    assert metrics["peak_memory_gb"] == 1.5
    assert metrics["active_memory_gb"] == 0.75
    assert metrics["cache_memory_gb"] == 0.25
    assert metrics["model_load_active_memory_gb"] == 1.0
    assert metrics["peak_memory_delta_gb"] == 0.5


def test_working_set_percentage_stays_in_current_run_jsonl(tmp_path: Path) -> None:
    """Derived working-set percentages belong in current-run JSONL, not raw history."""
    result = PerformanceResult(
        model_name="test-model",
        generation=MockGeneration(peak_memory=1.0),
        success=True,
    )
    context = check_models._build_report_render_context(
        results=[result],
        prompt="test",
        system_info={},
        recommended_working_set_bytes=2_000_000_000,
    )

    output_file = tmp_path / "working-set.jsonl"
    save_jsonl_report(
        [result],
        output_file,
        prompt="test",
        system_info={},
        report_context=context,
    )
    _header, rows = _read_jsonl(output_file)
    assert rows[0]["metrics"]["peak_memory_working_set_pct"] == 50.0

    history = append_history_record(
        history_path=tmp_path / "working-set.history.jsonl",
        results=[result],
        prompt="test",
        system_info={},
        library_versions={},
        eval_mode="blind",
    )
    assert history is not None
    assert "peak_memory_working_set_pct" not in history["model_results"]["test-model"]


def test_missing_working_set_omits_jsonl_percentage(tmp_path: Path) -> None:
    """An unavailable denominator should not create a guessed structured fact."""
    result = PerformanceResult(
        model_name="test-model",
        generation=MockGeneration(peak_memory=1.0),
        success=True,
    )
    context = check_models._build_report_render_context(
        results=[result],
        prompt="test",
        system_info={},
        recommended_working_set_bytes=None,
    )

    output_file = tmp_path / "no-working-set.jsonl"
    save_jsonl_report(
        [result],
        output_file,
        prompt="test",
        system_info={},
        report_context=context,
    )
    _header, rows = _read_jsonl(output_file)
    assert "peak_memory_working_set_pct" not in rows[0]["metrics"]


def test_save_jsonl_report_content(tmp_path: Path) -> None:
    """Test that save_jsonl_report writes correct content with generation."""
    output_file = tmp_path / "results.jsonl"

    gen = MockGeneration(
        text="A detailed image description with enough words to be useful without caveats."
    )
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
        generation_time=1.5,
        model_load_time=0.5,
        total_time=2.0,
        completed_at="2026-07-31 12:34:56 BST",
        runtime_diagnostics=RuntimeDiagnostics(
            input_validation_time_s=0.1,
            model_load_time_s=0.5,
            prompt_prep_time_s=0.2,
            decode_time_s=1.5,
            cleanup_time_s=0.05,
            first_token_latency_s=None,
            stop_reason="completed",
        ),
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    assert output_file.exists()
    header, rows = _read_jsonl(output_file)
    assert header["_type"] == "metadata"
    assert len(rows) == 1

    data = rows[0]
    assert set(data) == {
        "_type",
        "model",
        "timestamp",
        "assessment",
        "generated_text",
        "captured_output_on_fail",
        "failure",
        "metrics",
        "timing",
        "model_provenance",
        "prompt_diagnostics",
        "prompt_burden",
    }
    assert data["_type"] == "result"
    assert data["model"] == "test-model"
    assert data["timestamp"] == "2026-07-31 12:34:56 BST"
    assert data["assessment"] == {
        "profile": "general",
        "execution": "completed",
        "usability": "usable",
        "maintainer_status": "none",
        "observations": [],
    }
    assert data["generated_text"] == gen.text
    assert data["captured_output_on_fail"] == ""
    assert data["failure"] is None
    assert data["prompt_diagnostics"] is None
    metrics = data["metrics"]
    assert metrics.get("generation_tps") == 5.0
    assert metrics.get("prompt_tokens") == 10
    assert metrics.get("total_tokens") == 30
    assert metrics.get("prompt_tps") == 2.0
    timing = data["timing"]
    assert timing["input_validation_time_s"] == 0.1
    assert timing["prompt_prep_time_s"] == 0.2
    assert timing["cleanup_time_s"] == 0.05
    assert timing["stop_reason"] == "completed"


def test_jsonl_assessment_retains_factual_observation_evidence(tmp_path: Path) -> None:
    output_file = tmp_path / "results.jsonl"
    prompt = (
        "Return exactly these three sections, and nothing else:\n"
        "Title: 5-10 words.\nDescription: 1-2 sentences.\nKeywords: 10-18 terms."
    )
    text = "<think>inspect</think> <|im_user|> prompt instructions " + "cat " * 80
    analysis = check_models.analyze_generation_text(
        text,
        generated_tokens=80,
        prompt=prompt,
        assessment_profile="metadata",
        requested_max_tokens=80,
    )
    result = PerformanceResult(
        model_name="org/observed",
        generation=MockGeneration(text=text, generation_tokens=80),
        success=True,
        quality_analysis=analysis,
        assessment_profile="metadata",
        requested_max_tokens=80,
    )

    save_jsonl_report([result], output_file, prompt=prompt, system_info={})

    _header, rows = _read_jsonl(output_file)
    details = rows[0]["assessment"]["details"]
    assert details["missing_sections"] == ["title", "description", "keywords"]
    assert details["repeated_fragment"] == "cat"
    assert "instruction_echo_fragments" not in details
    assert details["unexpected_special_tokens"] == ["<|im_user|>"]
    assert details["thinking_trace_markers"] == ["<think>", "</think>"]
    assert "repetitive_tail" in details["token_cap_reasons"]


def test_jsonl_retains_neutral_thinking_markers_without_review_observation(
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "results.jsonl"
    text = "<think>inspect</think> Two cats sleep on a pink couch."
    result = PerformanceResult(
        model_name="org/neutral-thinking",
        generation=MockGeneration(text=text, generation_tokens=16),
        success=True,
        quality_analysis=check_models.analyze_generation_text(text, generated_tokens=16),
    )

    save_jsonl_report([result], output_file, prompt="Describe this image.", system_info={})

    _header, rows = _read_jsonl(output_file)
    assert rows[0]["assessment"] == {
        "profile": "general",
        "execution": "completed",
        "usability": "usable",
        "maintainer_status": "none",
        "observations": [],
        "details": {"thinking_trace_markers": ["<think>", "</think>"]},
    }


def test_save_jsonl_report_serializes_only_cached_result_assessment(tmp_path: Path) -> None:
    """Successful rows should expose one assessment without legacy status projections."""
    output_file = tmp_path / "results.jsonl"
    prompt = (
        "Analyze this image.\n"
        "Context: Existing metadata hints:\n"
        "- Title hint: Brick storefront with outdoor seating\n"
        "- Description hint: A brick storefront has outdoor seating beside a sidewalk.\n"
        "- Keyword hints: brick storefront, outdoor seating, sidewalk, people\n"
    )
    gen = MockGeneration(
        text=(
            "Title: Brick storefront seating beside the pavement\n"
            "Description: A brick storefront has outdoor seating beside a sidewalk.\n"
            "Keywords: brick storefront, outdoor seating, sidewalk, people"
        ),
        prompt_tokens=320,
        generation_tokens=64,
    )
    analysis = check_models.analyze_generation_text(
        gen.text or "",
        generated_tokens=64,
        prompt_tokens=320,
        prompt=prompt,
        requested_max_tokens=128,
    )
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
        quality_analysis=analysis,
        requested_max_tokens=128,
    )

    save_jsonl_report([result], output_file, prompt=prompt, system_info={})

    _header, rows = _read_jsonl(output_file)
    row = rows[0]
    assert row["assessment"] == {
        "profile": "general",
        "execution": "completed",
        "usability": "usable",
        "maintainer_status": "none",
        "observations": [],
    }
    assert "review" not in row
    assert "maintainer_triage" not in row
    assert "current_recommendation" not in row
    assert "compatibility_status" not in row


def test_save_jsonl_report_serializes_crash_assessment_and_failure(tmp_path: Path) -> None:
    """Failure rows should separate the assessment from raw failure evidence."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        upstream_boundary="generation_started",
        error_message="runtime error",
        error_stage="Model Error",
        error_code="MLX_VLM_DECODE_RUNTIME",
        error_package="mlx-vlm",
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    row = rows[0]
    assert row["assessment"] == {
        "profile": "general",
        "execution": "crashed",
        "usability": "not_evaluated",
        "maintainer_status": "actionable_failure",
        "observations": [],
    }
    assert row["failure"] == {
        "phase": None,
        "stage": "Model Error",
        "code": "MLX_VLM_DECODE_RUNTIME",
        "message": "runtime error",
        "exception_type": None,
        "exception_module": None,
        "package": "mlx-vlm",
        "traceback": None,
    }
    assert "review" not in row
    assert "maintainer_triage" not in row


def test_save_jsonl_report_omits_semantic_score_payloads(tmp_path: Path) -> None:
    """The narrow machine contract should not publish report-ranking scores."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="test-model",
        generation=MockGeneration(),
        success=True,
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    row = rows[0]
    assert "metadata_agreement" not in row
    assert "quality_analysis" not in row
    assert "context_integration_score" not in row
    assert "draft_improvement_score" not in row


def test_save_jsonl_report_marks_external_connectivity_as_indeterminate(tmp_path: Path) -> None:
    """Transport failures should be recorded as indeterminate attempts."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="Model loading failed: Server disconnected without sending a response.",
        error_stage="Model Error",
        error_code="HUGGINGFACE_HUB_MODEL_LOAD_MODEL",
        error_package="huggingface-hub",
        error_traceback=(
            "Traceback (most recent call last):\n"
            "httpx.RemoteProtocolError: Server disconnected without sending a response."
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    assert rows[0]["assessment"] == {
        "profile": "general",
        "execution": "indeterminate",
        "usability": "not_evaluated",
        "maintainer_status": "none",
        "observations": [],
    }


def test_save_jsonl_report_no_generation(tmp_path: Path) -> None:
    """Test that save_jsonl_report handles missing generation."""
    output_file = tmp_path / "results.jsonl"

    result = PerformanceResult(
        model_name="test-model",
        generation=None,
        success=True,
        generation_time=1.5,
        model_load_time=0.5,
        total_time=2.0,
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]

    assert data["model"] == "test-model"
    assert "metrics" in data
    assert data["metrics"] == {}


def test_save_jsonl_report_failed_model(tmp_path: Path) -> None:
    """Test that save_jsonl_report handles failed models correctly."""
    output_file = tmp_path / "results.jsonl"

    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="Something went wrong",
        error_stage="Model Load",
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]

    assert data["model"] == "failed-model"
    assert data["failure"] == {
        "phase": None,
        "stage": "Model Load",
        "code": None,
        "message": "Something went wrong",
        "exception_type": None,
        "exception_module": None,
        "package": None,
        "traceback": None,
    }


def test_save_jsonl_report_includes_failure_phase_and_code(tmp_path: Path) -> None:
    """Failure metadata should remain nested raw evidence."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        failure_phase="decode",
        error_stage="API Mismatch",
        error_code="TRANSFORMERS_DECODE_API_MISMATCH",
        error_signature="TRANSFORMERS_DECODE_API_MISMATCH:abc123",
        error_message="unexpected keyword argument",
    )
    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    failure = _require_present(rows[0]["failure"], field_name="failure")
    assert failure["phase"] == "decode"
    assert failure["code"] == "TRANSFORMERS_DECODE_API_MISMATCH"
    assert "error_signature" not in rows[0]


def test_save_jsonl_report_includes_traceback_and_type(tmp_path: Path) -> None:
    """Test that save_jsonl_report includes error_traceback and error_type for failures."""
    output_file = tmp_path / "results.jsonl"

    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="ValueError: Missing parameters",
        error_stage="Weight Mismatch",
        error_type="ValueError",
        error_package="mlx",
        error_traceback="Traceback (most recent call last):\n  File 'test.py', line 1\nValueError: Missing parameters",
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]

    assert data["model"] == "failed-model"
    failure = _require_present(data["failure"], field_name="failure")
    assert failure["exception_type"] == "ValueError"
    assert failure["package"] == "mlx"
    assert failure["traceback"] is not None
    assert "Traceback" in failure["traceback"]


def test_save_jsonl_report_includes_root_exception_fields(tmp_path: Path) -> None:
    """Optional root exception fields should serialize without changing error_type."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="Model loading failed: upstream shape mismatch",
        error_type="ValueError",
        root_error_type="RuntimeError",
        root_error_module="builtins",
        root_error_message="upstream shape mismatch",
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})
    _header, rows = _read_jsonl(output_file)

    failure = _require_present(rows[0]["failure"], field_name="failure")
    assert failure["exception_type"] == "RuntimeError"
    assert failure["exception_module"] == "builtins"
    assert failure["message"] == "Model loading failed: upstream shape mismatch"


def test_save_jsonl_report_includes_exception_chain_in_chronological_order(
    tmp_path: Path,
) -> None:
    """Exception chains serialize additively from root cause to outer wrapper."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="generation failed",
        exception_chain=(
            check_models.FailureException("IndexError", "builtins", "bad token"),
            check_models.FailureException("ValueError", "builtins", "generation failed"),
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})
    _header, rows = _read_jsonl(output_file)

    failure = _require_present(rows[0]["failure"], field_name="failure")
    assert failure.get("exception_chain") == [
        {"type": "IndexError", "module": "builtins", "message": "bad token"},
        {"type": "ValueError", "module": "builtins", "message": "generation failed"},
    ]


def test_save_jsonl_report_includes_prompt_diagnostics(tmp_path: Path) -> None:
    """Rendered prompt diagnostics should be optional JSONL metadata."""
    output_file = tmp_path / "results.jsonl"
    result = PerformanceResult(
        model_name="ok-model",
        generation=MockGeneration(),
        success=True,
        prompt_diagnostics=check_models.PromptDiagnostics(
            model_type="qwen2_vl",
            processor_class="transformers.AutoProcessor",
            tokenizer_class="transformers.PreTrainedTokenizerFast",
            rendered_prompt_hash_sha256="abc123",
            rendered_prompt_preview="<image> Describe this.",
            rendered_prompt_chars=22,
            image_placeholder_count=1,
            processed_image_width=512,
            processed_image_height=384,
            image_patch_count=4,
            eos_token_id=151645,
            special_token_ids=(151645,),
            special_tokens=("<|end|>",),
            generate_kwargs={
                "max_tokens": 500,
                "quantized_kv_start": check_models.DEFAULT_QUANTIZED_KV_START,
            },
        ),
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})
    _header, rows = _read_jsonl(output_file)

    prompt_diagnostics = _require_present(
        rows[0].get("prompt_diagnostics"),
        field_name="prompt_diagnostics",
    )
    assert prompt_diagnostics["rendered_prompt_hash_sha256"] == "abc123"
    assert prompt_diagnostics["image_placeholder_count"] == 1
    assert prompt_diagnostics["processed_image_width"] == 512
    assert prompt_diagnostics["processed_image_height"] == 384
    assert prompt_diagnostics["image_patch_count"] == 4
    assert prompt_diagnostics["special_tokens"] == ["<|end|>"]
    assert prompt_diagnostics["generate_kwargs"] == {
        "max_tokens": 500,
        "quantized_kv_start": check_models.DEFAULT_QUANTIZED_KV_START,
    }


def test_jsonl_does_not_back_project_legacy_machine_facts(tmp_path: Path) -> None:
    """Machine rows should expose the assessment without legacy report aliases."""
    output_file = tmp_path / "results.jsonl"
    prompt = "Create title, description, and keywords."
    analysis = check_models.analyze_generation_text(
        "Title: Cat\nDescription: A cat rests on a chair.\nKeywords: cat, chair",
        generated_tokens=18,
        prompt_tokens=4100,
        prompt=prompt,
    )
    result = PerformanceResult(
        model_name="org/enriched",
        generation=MockGeneration(
            text="Title: Cat\nDescription: A cat rests on a chair.\nKeywords: cat, chair",
            prompt_tokens=4100,
            generation_tokens=18,
        ),
        success=True,
        quality_analysis=analysis,
        prompt_diagnostics=check_models.PromptDiagnostics(image_placeholder_count=1),
    )
    context = check_models._build_report_render_context(
        results=[result],
        prompt=prompt,
        metadata={"description": "A cat rests on a chair."},
        eval_mode="assisted",
    )

    save_jsonl_report(
        [result],
        output_file,
        prompt=prompt,
        system_info={},
        mode_policy=check_models._build_report_mode_policy(
            eval_mode="assisted",
            metadata_exposed_to_prompt=True,
        ),
        report_context=context,
    )
    header, rows = _read_jsonl(output_file)
    row = rows[0]
    assert header["format_version"] == "3.0"
    assert row["assessment"]["execution"] == "completed"
    assert (
        not {
            "compatibility_status",
            "current_recommendation",
            "failure_origin",
            "maintainer_readiness",
            "reproduction_status",
            "keyword_overlap",
            "context_integration_score",
            "draft_improvement_score",
            "visual_description_score",
            "assisted_enrichment_score",
            "prompt_burden_kind",
            "prompt_burden_source",
            "owner_confidence",
        }
        & row.keys()
    )


def test_save_jsonl_report_includes_captured_output(tmp_path: Path) -> None:
    """Failure rows should retain captured stdout/stderr for diagnostics workflows."""
    output_file = tmp_path / "results.jsonl"

    result = PerformanceResult(
        model_name="failed-model",
        generation=None,
        success=False,
        error_message="runtime error",
        error_stage="Model Error",
        captured_output_on_fail="=== STDERR ===\nTokenizer warning",
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]
    assert data["captured_output_on_fail"] == "=== STDERR ===\nTokenizer warning"


def test_save_jsonl_report_includes_timing(tmp_path: Path) -> None:
    """Test that save_jsonl_report includes timing information."""
    output_file = tmp_path / "results.jsonl"

    gen = MockGeneration()
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
        generation_time=2.5,
        model_load_time=1.0,
        total_time=3.5,
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]

    assert "timing" in data
    assert data["timing"]["generation_time_s"] == 2.5
    assert data["timing"]["model_load_time_s"] == 1.0
    assert data["timing"]["total_time_s"] == 3.5


def test_save_jsonl_report_round_trips_complete_generated_text(tmp_path: Path) -> None:
    """JSON escaping should preserve every captured output byte after decoding."""
    output_file = tmp_path / "results.jsonl"
    output = (
        "Title:\tCafé 雪\n"
        "```markdown\n**unchanged**\n```\n"
        "<think>HTML-looking, not markup</think>\n"
        "Final line\n"
    )
    gen = MockGeneration(text=output)
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
        generation_time=1.5,
        model_load_time=0.5,
        total_time=2.0,
    )

    results = [result]
    save_jsonl_report(results, output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]

    assert "generated_text" in data
    assert data["generated_text"] == output


def test_save_jsonl_report_preserves_empty_generated_text(tmp_path: Path) -> None:
    """Empty generated text should still be serialized for diagnostics triage."""
    output_file = tmp_path / "results.jsonl"

    gen = MockGeneration(text="")
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
    )

    save_jsonl_report([result], output_file, prompt="test", system_info={})

    _header, rows = _read_jsonl(output_file)
    data = rows[0]
    assert "generated_text" in data
    assert data["generated_text"] == ""


def test_append_history_record_creates_file(tmp_path: Path) -> None:
    """Test that append_history_record writes a per-run history entry."""
    history_file = tmp_path / "results.history.jsonl"
    result = PerformanceResult(
        model_name="test-model",
        generation=None,
        success=True,
        generation_time=1.0,
        model_load_time=0.5,
        total_time=1.5,
    )

    append_history_record(
        history_path=history_file,
        results=[result],
        prompt="test prompt",
        system_info={"OS": "test"},
        library_versions={},
        image_path=None,
        eval_mode="blind",
    )

    assert history_file.exists()
    lines = history_file.read_text().strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["_type"] == "run"
    assert record["model_results"]["test-model"]["success"] is True


def test_append_history_record_contains_only_raw_execution_and_resource_facts(
    tmp_path: Path,
) -> None:
    """History rows must not persist current semantic fields or recommendations."""
    history_file = tmp_path / "results.history.jsonl"
    prompt = (
        "Analyze this image.\n"
        "Context: Existing metadata hints:\n"
        "- Title hint: Brick storefront with outdoor seating\n"
        "- Description hint: A brick storefront has outdoor seating beside a sidewalk.\n"
        "- Keyword hints: brick storefront, outdoor seating, sidewalk, people\n"
    )
    gen = MockGeneration(
        text=(
            "Title: Brick storefront with outdoor seating\n"
            "Description: A brick storefront has outdoor seating beside a sidewalk.\n"
            "Keywords: brick storefront, outdoor seating, sidewalk, people"
        ),
        prompt_tokens=320,
        generation_tokens=64,
    )
    result = PerformanceResult(
        model_name="test-model",
        generation=gen,
        success=True,
        generation_time=1.25,
        model_load_time=0.5,
        total_time=1.75,
        requested_max_tokens=128,
    )

    record = append_history_record(
        history_path=history_file,
        results=[result],
        prompt=prompt,
        system_info={},
        library_versions={},
        image_path=None,
        eval_mode="blind",
    )
    assert record is not None

    model_results = _require_present(record.get("model_results"), field_name="model_results")
    model_record = model_results["test-model"]
    assert model_record == {
        "success": True,
        "resolved_revision": None,
        "failure_phase": None,
        "error_stage": None,
        "error_type": None,
        "error_package": None,
        "error_code": None,
        "error_signature": None,
        "generation_time_s": 1.25,
        "model_load_time_s": 0.5,
        "total_time_s": 1.75,
        "prompt_tokens": 320,
        "generation_tokens": 64,
        "total_tokens": 30,
        "generation_tps": 5.0,
        "peak_memory_gb": 1.5,
        "active_memory_gb": 0.0,
        "cache_memory_gb": 0.0,
    }


def test_history_path_for_jsonl_derives_name(tmp_path: Path) -> None:
    """Test that history path inserts '.history' before '.jsonl'."""
    result = _history_path_for_jsonl(tmp_path / "results.jsonl")
    assert result == tmp_path / "results.history.jsonl"


def test_history_path_for_jsonl_custom_stem(tmp_path: Path) -> None:
    """Test history path derivation with a non-default stem."""
    result = _history_path_for_jsonl(tmp_path / "my_output.jsonl")
    assert result == tmp_path / "my_output.history.jsonl"


# ---------------------------------------------------------------------------
# --- Runtime Fingerprint Canary Tests ---


class TestRuntimeFingerprint:
    """Mock canary tests for runtime capability fingerprint collection."""

    def test_collect_runtime_fingerprint_returns_all_probes(self) -> None:
        """Fingerprint must include every probe key (G2: never silently omit)."""
        fingerprint = check_models.collect_runtime_fingerprint()
        expected_probes = {
            "metal_gpu",
            "mlx_framework",
            "mlx_vlm",
            "gpu_memory",
            "fused_attention",
        }
        assert set(fingerprint.keys()) == expected_probes

    def test_each_probe_has_valid_status(self) -> None:
        """Every probe result must have a status in the allowed set."""
        fingerprint = check_models.collect_runtime_fingerprint()
        valid_statuses = {"ok", "unavailable", "errored", "timed_out"}
        for probe_name, result in fingerprint.items():
            assert result["status"] in valid_statuses, (
                f"Probe '{probe_name}' has invalid status: {result['status']}"
            )

    def test_collect_runtime_fingerprint_reports_mlx_vlm_available(self) -> None:
        """An imported mlx-vlm runtime should be recorded as available."""
        with patch.dict(check_models.MISSING_DEPENDENCIES, {}, clear=True):
            fingerprint = check_models.collect_runtime_fingerprint()

        assert fingerprint["mlx_vlm"] == {"status": "ok"}

    def test_collect_runtime_fingerprint_reports_mlx_vlm_unavailable(self) -> None:
        """A captured mlx-vlm import failure should remain actionable."""
        with patch.dict(
            check_models.MISSING_DEPENDENCIES,
            {"mlx-vlm": "not imported"},
            clear=True,
        ):
            fingerprint = check_models.collect_runtime_fingerprint()

        assert fingerprint["mlx_vlm"] == {
            "status": "unavailable",
            "detail": "not imported",
        }

    def test_collect_runtime_fingerprint_uses_top_level_mlx_memory_probe(self) -> None:
        """GPU memory probe should use the current top-level MLX memory API."""

        class _FakeMxRuntime:
            @staticmethod
            def get_active_memory() -> float:
                return 2 * check_models.DECIMAL_GB

        with patch.object(check_models, "mx", _FakeMxRuntime()):
            fingerprint = check_models.collect_runtime_fingerprint()

        assert fingerprint["gpu_memory"]["status"] == "ok"
        assert fingerprint["gpu_memory"].get("detail") == "active=2.00GB"

    def test_collect_runtime_fingerprint_reports_fused_attention_available(self) -> None:
        """Callable MLX fused attention should be recorded as available."""
        runtime = SimpleNamespace(
            fast=SimpleNamespace(scaled_dot_product_attention=lambda: None),
        )
        with patch.object(check_models, "mx", runtime):
            fingerprint = check_models.collect_runtime_fingerprint()

        assert fingerprint["fused_attention"] == {"status": "ok"}

    def test_collect_runtime_fingerprint_reports_fused_attention_unavailable(self) -> None:
        """A missing fused-attention surface should remain explicit."""
        with patch.object(check_models, "mx", SimpleNamespace()):
            fingerprint = check_models.collect_runtime_fingerprint()

        assert fingerprint["fused_attention"]["status"] == "unavailable"

    def test_probe_fused_attention_reports_attribute_error(self) -> None:
        """Runtime attribute errors should become bounded probe state."""

        class RaisingRuntime:
            @property
            def fast(self) -> object:
                message = "runtime unavailable"
                raise RuntimeError(message)

        with patch.object(check_models, "mx", RaisingRuntime()):
            result = check_models._probe_fused_attention()

        assert result == {"status": "errored", "detail": "runtime unavailable"}

    def test_jsonl_metadata_includes_fingerprint(self) -> None:
        """JSONL metadata record includes runtime_fingerprint when provided."""
        fingerprint = {"metal_gpu": check_models.RuntimeProbeResult(status="ok")}
        record = check_models._build_jsonl_metadata_record(
            prompt="test",
            system_info={},
            runtime_fingerprint=fingerprint,
            mode_policy=check_models._default_report_mode_policy(),
            counts=check_models._run_outcome_counts(()),
            generation_settings={},
            image=None,
        )
        assert "runtime_fingerprint" in record
        runtime_fingerprint = _require_present(
            record.get("runtime_fingerprint"),
            field_name="runtime_fingerprint",
        )
        assert runtime_fingerprint["metal_gpu"]["status"] == "ok"

    def test_jsonl_metadata_omits_fingerprint_when_none(self) -> None:
        """JSONL metadata record omits runtime_fingerprint when not provided."""
        record = check_models._build_jsonl_metadata_record(
            prompt="test",
            system_info={},
            mode_policy=check_models._default_report_mode_policy(),
            counts=check_models._run_outcome_counts(()),
            generation_settings={},
            image=None,
        )
        assert "runtime_fingerprint" not in record

    def test_history_record_includes_fingerprint(self, tmp_path: Path) -> None:
        """History record includes runtime_fingerprint when provided."""
        fingerprint = {"mlx_vlm": check_models.RuntimeProbeResult(status="ok")}
        history_path = tmp_path / "test.history.jsonl"
        record = check_models.append_history_record(
            history_path=history_path,
            results=[],
            prompt="test prompt",
            system_info={},
            library_versions=cast("check_models.LibraryVersionDict", {}),
            runtime_fingerprint=fingerprint,
            eval_mode="blind",
        )
        assert record is not None
        assert record.get("runtime_fingerprint") == fingerprint
        # Verify it's persisted to disk
        lines = history_path.read_text().strip().splitlines()
        assert len(lines) == 1
        persisted = json.loads(lines[0])
        assert persisted["runtime_fingerprint"]["mlx_vlm"]["status"] == "ok"

    def test_save_jsonl_includes_fingerprint(self, tmp_path: Path) -> None:
        """save_jsonl_report includes fingerprint in metadata header."""
        fingerprint = {"metal_gpu": check_models.RuntimeProbeResult(status="ok")}
        out_path = tmp_path / "results.jsonl"
        check_models.save_jsonl_report(
            [],
            out_path,
            prompt="test",
            system_info={},
            runtime_fingerprint=fingerprint,
        )
        lines = out_path.read_text().strip().splitlines()
        header = json.loads(lines[0])
        assert header["_type"] == "metadata"
        assert header["runtime_fingerprint"]["metal_gpu"]["status"] == "ok"


class TestSchemaVersioning:
    """Tests for JSONL schema versioning and round-trip integrity."""

    def test_metadata_format_version_is_2_0(self, tmp_path: Path) -> None:
        """Current JSONL output uses the narrow 2.0 machine contract."""
        out = tmp_path / "results.jsonl"
        check_models.save_jsonl_report([], out, prompt="test", system_info={})
        header, _ = _read_jsonl(out)
        assert header["format_version"] == "3.0"

    def test_round_trip_metadata_keys(self, tmp_path: Path) -> None:
        """Metadata record round-trips through JSON with expected keys."""
        fingerprint = {"metal_gpu": check_models.RuntimeProbeResult(status="ok")}
        out = tmp_path / "results.jsonl"
        check_models.save_jsonl_report(
            [],
            out,
            prompt="hello",
            system_info={"os": "macOS"},
            runtime_fingerprint=fingerprint,
        )
        header, _ = _read_jsonl(out)
        assert header["_type"] == "metadata"
        assert header["prompt"] == "hello"
        assert header["system"]["os"] == "macOS"
        assert "timestamp" in header
        runtime_fingerprint = _require_present(
            header.get("runtime_fingerprint"),
            field_name="runtime_fingerprint",
        )
        assert runtime_fingerprint["metal_gpu"]["status"] == "ok"

    def test_round_trip_result_record_success(self, tmp_path: Path) -> None:
        """Successful result record round-trips with all required keys."""
        result = PerformanceResult(
            model_name="org/good",
            generation=MockGeneration(),
            success=True,
        )
        out = tmp_path / "results.jsonl"
        check_models.save_jsonl_report([result], out, prompt="t", system_info={})
        _, rows = _read_jsonl(out)
        row = rows[0]
        assert row["_type"] == "result"
        assert row["model"] == "org/good"
        assert row["assessment"]["execution"] == "completed"
        assert row["failure"] is None

    def test_round_trip_result_record_failure(self, tmp_path: Path) -> None:
        """Failed result record round-trips with nested raw failure evidence."""
        result = PerformanceResult(
            model_name="org/bad",
            generation=None,
            success=False,
            error_message="ValueError: bad shape",
            error_code="DECODE_ERR",
            error_traceback="File x.py line 1\n  raise ValueError",
        )
        out = tmp_path / "results.jsonl"
        check_models.save_jsonl_report([result], out, prompt="t", system_info={})
        _, rows = _read_jsonl(out)
        row = rows[0]
        assert row["assessment"]["execution"] == "crashed"
        failure = _require_present(row["failure"], field_name="failure")
        assert failure["code"] == "DECODE_ERR"
        assert failure["traceback"] == "File x.py line 1\n  raise ValueError"

    def test_round_trip_all_fields_json_serializable(self, tmp_path: Path) -> None:
        """Every field in the JSONL output is JSON-serializable (no crash)."""
        result = PerformanceResult(
            model_name="org/model",
            generation=MockGeneration(),
            success=True,
            runtime_diagnostics=RuntimeDiagnostics(),
        )
        out = tmp_path / "results.jsonl"
        check_models.save_jsonl_report([result], out, prompt="p", system_info={})
        # Re-parse every line — will raise if any field isn't serializable
        for line in out.read_text().strip().splitlines():
            parsed = json.loads(line)
            json.dumps(parsed)  # round-trip back to string

    def test_history_format_version_unchanged(self, tmp_path: Path) -> None:
        """History records keep format_version 1.0 (separate schema)."""
        hist = tmp_path / "results.history.jsonl"
        check_models.append_history_record(
            results=[],
            prompt="t",
            image_path=None,
            system_info={},
            library_versions={},
            history_path=hist,
            eval_mode="blind",
        )
        data = json.loads(hist.read_text().strip())
        assert data["format_version"] == "1.0"
        assert data["eval_mode"] == "blind"

    @pytest.mark.parametrize("lane", ["triage", "blind", "assisted"])
    def test_history_stores_the_caller_resolved_lane_verbatim(
        self,
        tmp_path: Path,
        lane: check_models.EvaluationLane,
    ) -> None:
        """History persists resolved lanes as given and never re-resolves.

        Aliases are resolved at the ``_resolve_eval_mode`` funnel before
        persistence; a silent re-resolution here (with no metadata available)
        would record ``blind`` for an assisted run if an unresolved mode ever
        leaked through, so the parameter is typed ``EvaluationLane``.
        """
        hist = tmp_path / "results.history.jsonl"

        check_models.append_history_record(
            results=[],
            prompt="t",
            image_path=None,
            system_info={},
            library_versions={},
            history_path=hist,
            eval_mode=lane,
        )

        data = json.loads(hist.read_text().strip())
        assert data["eval_mode"] == lane


class TestRerunEvidence:
    """Tests for differential rerun evidence in JSONL output."""

    def test_select_rerun_candidates_picks_failures(self) -> None:
        """Crashed models are selected from their current-run assessment."""
        ok = PerformanceResult(model_name="ok", generation=MockGeneration(), success=True)
        fail = PerformanceResult(model_name="fail", generation=None, success=False)
        candidates = check_models._select_rerun_candidates([ok, fail])
        assert len(candidates) == 1
        assert candidates[0].model_name == "fail"

    def test_select_rerun_candidates_uses_typed_mechanical_observations(self) -> None:
        """Completed observations, but not clean completions, merit a rerun."""
        repeated_phrase = "loop"
        observed = PerformanceResult(
            model_name="observed-model",
            generation=MockGeneration(text=f"{repeated_phrase} " * 100, generation_tokens=100),
            success=True,
            quality_analysis=check_models.GenerationQualityAnalysis(
                is_repetitive=True,
                repeated_token=repeated_phrase,
                word_count=100,
            ),
        )
        clean = PerformanceResult(
            model_name="clean-model",
            generation=MockGeneration(
                text="A complete description of the visible scene.",
                generation_tokens=20,
            ),
            success=True,
            quality_analysis=check_models.GenerationQualityAnalysis(
                is_repetitive=False,
                repeated_token=None,
                word_count=8,
            ),
        )

        candidates = check_models._select_rerun_candidates([observed, clean])

        assert [candidate.model_name for candidate in candidates] == ["observed-model"]

    def test_differential_rerun_preserves_inference_configuration(
        self,
        tmp_path: Path,
    ) -> None:
        """Triage overrides must not silently discard model/template configuration."""
        captured: list[check_models.ProcessImageParams] = []
        rerun_result = PerformanceResult(
            model_name="org/model",
            generation=MockGeneration(text="rerun output"),
            success=True,
        )
        args = argparse.Namespace(
            trust_remote_code=False,
            top_p=0.8,
            min_p=0.1,
            top_k=12,
            repetition_penalty=1.1,
            repetition_context_size=48,
            seed=7,
            presence_penalty=0.2,
            presence_context_size=64,
            frequency_penalty=0.3,
            frequency_context_size=96,
            logit_bias={42: -1.0},
            lazy_load=True,
            max_kv_size=2048,
            kv_bits=4,
            kv_quant_scheme="turboquant",
            kv_group_size=32,
            quantized_kv_start=128,
            kv_key_bits=8,
            kv_value_bits=4,
            kv_key_scheme="uniform",
            kv_value_scheme="turboquant",
            force_download=True,
            quantize_activations=True,
            revision="model-revision",
            adapter_path="adapter/path",
            prefill_step_size=512,
            resize_shape=(64, 32),
            eos_tokens=("<eos>",),
            skip_special_tokens=True,
            processor_kwargs={"crop": False},
            enable_thinking=True,
            thinking_budget=24,
            thinking_mode="budget",
            thinking_start_token="<think>",  # noqa: S106 - protocol delimiter, not a credential
            thinking_end_token="</think>",  # noqa: S106 - protocol delimiter, not a credential
            assessment_profile="metadata",
        )

        def capture(params: check_models.ProcessImageParams) -> PerformanceResult:
            captured.append(params)
            return rerun_result

        with patch.object(check_models, "process_image_with_model", side_effect=capture):
            check_models._run_differential_reruns(
                [PerformanceResult(model_name="org/model", generation=None, success=False)],
                args,
                tmp_path / "image.jpg",
            )

        assert len(captured) == 1
        params = captured[0]
        assert (
            params.prompt,
            params.max_tokens,
            params.temperature,
            params.timeout,
            params.verbose,
        ) == (
            check_models.TRIAGE_PROMPT,
            check_models.RERUN_TRIAGE_MAX_TOKENS,
            0.0,
            check_models.RERUN_TRIAGE_TIMEOUT,
            False,
        )
        assert params.revision == "model-revision"
        assert params.adapter_path == "adapter/path"
        assert params.kv_key_bits == 8
        assert params.kv_value_bits == 4
        assert params.kv_key_scheme == "uniform"
        assert params.kv_value_scheme == "turboquant"
        assert params.prefill_step_size == 512
        assert params.resize_shape == (64, 32)
        assert params.eos_tokens == ("<eos>",)
        assert params.skip_special_tokens is True
        assert params.processor_kwargs == {"crop": False}
        assert params.enable_thinking is True
        assert params.thinking_budget == 24
        assert params.thinking_mode == "budget"
        assert params.thinking_start_token == "<think>"
        assert params.thinking_end_token == "</think>"
        assert params.assessment_profile == "general"  # Triage overrides the metadata first pass.


class TestModelBurdenRecord:
    """model_burden serialization drops None fields and is omitted when absent."""

    def test_record_carries_populated_burden_fields_only(self) -> None:
        """Present facts serialize; None-valued facts are dropped from the payload."""
        result = PerformanceResult(
            model_name="org/burden",
            generation=None,
            success=False,
            model_burden=check_models.ModelBurdenFacts(
                weight_bytes=5_000_000_000,
                parameter_count=8_000_000_000,
                parameter_count_source="num_parameters",
                context_length=32_768,
                context_length_source="max_position_embeddings",
            ),
        )
        assessment = check_models._assess_result(result)
        record = check_models._build_jsonl_result_record(
            result,
            assessment,
            requested_revision=None,
            model_provenance={
                "model": "org/burden",
                "requested_revision": None,
                "resolved_revision": "rev",
                "snapshot_path": None,
            },
        )
        assert record["model_burden"] == {
            "weight_bytes": 5_000_000_000,
            "parameter_count": 8_000_000_000,
            "parameter_count_source": "num_parameters",
            "context_length": 32_768,
            "context_length_source": "max_position_embeddings",
        }

    def test_record_omits_burden_key_when_facts_unavailable(self) -> None:
        """A result with no burden facts writes no model_burden key at all."""
        result = PerformanceResult(model_name="org/none", generation=None, success=False)
        assessment = check_models._assess_result(result)
        record = check_models._build_jsonl_result_record(
            result,
            assessment,
            requested_revision=None,
            model_provenance={
                "model": "org/none",
                "requested_revision": None,
                "resolved_revision": "rev",
                "snapshot_path": None,
            },
        )
        assert "model_burden" not in record


def _retained_run_fixture(tmp_path: Path) -> check_models.RetainedRun:
    """Build one synthetic retained run entirely under tmp_path."""
    image = tmp_path / "img.jpg"
    safe_io.write_text_no_follow(image, "not-really-a-jpeg")
    result = PerformanceResult(
        model_name="org/m",
        generation=None,
        success=False,
        prompt_diagnostics=check_models.PromptDiagnostics(
            generate_kwargs={"max_tokens": 32, "temperature": 0.0}
        ),
    )
    return check_models._build_retained_run(
        [result],
        prompt="Describe the image.",
        system_info={"OS": "test"},
        total_runtime_seconds=1.5,
        artifacts={"results_jsonl": "results.jsonl"},
        image_path=image,
        trust_remote_code=True,
    )


def test_schema_3_header_retains_wall_clock_start(tmp_path: Path) -> None:
    """started_at is retained verbatim when the orchestrator supplies it."""
    result = PerformanceResult(model_name="org/m", generation=None, success=False)
    retained = check_models._build_retained_run(
        [result],
        prompt="Describe the image.",
        system_info={"OS": "test"},
        total_runtime_seconds=1.5,
        started_at="2026-07-31 11:00:00 BST",
    )
    assert retained.metadata.get("started_at") == "2026-07-31 11:00:00 BST"
    # Absent by default so older consumers see an unchanged header.
    assert "started_at" not in _retained_run_fixture(tmp_path).metadata


def test_schema_3_metadata_contains_complete_run_context(tmp_path: Path) -> None:
    """The single retained artifact's header carries the whole run context."""
    retained = _retained_run_fixture(tmp_path)
    path = tmp_path / "results.jsonl"
    check_models._write_retained_run(retained, path)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    header = rows[0]
    assert header["format_version"] == "3.0"
    assert header["prompt_sha256"] == hashlib.sha256(header["prompt"].encode("utf-8")).hexdigest()
    assert header["counts"]["models_attempted"] == len(rows) - 1
    assert header["producer"]["name"] == "check_models"
    assert header["image"]["sha256"]
    assert header["generation_settings"]
    assert "comparison" in header
    assert "run.json" not in json.dumps(header)


def test_failed_retained_run_rewrite_leaves_the_previous_file_intact(tmp_path: Path) -> None:
    """The final manifest rewrite must not truncate the pre-report file on failure."""
    retained = _retained_run_fixture(tmp_path)
    path = tmp_path / "results.jsonl"
    check_models._write_retained_run(retained, path)
    before = path.read_bytes()

    def _explode(target: Path, content: str, *, append: bool = False) -> None:
        del content, append
        safe_io.write_text_no_follow(target, "partial")
        msg = "disk full"
        raise OSError(msg)

    with (
        patch.object(check_models, "_write_text_file", _explode),
        pytest.raises(OSError, match="disk full"),
    ):
        check_models._write_retained_run(retained, path)

    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".results")) == []

    # A successful rewrite replaces the file in place and leaves no staging file.
    updated = check_models.RetainedRun(
        metadata=cast(
            "check_models.JsonlMetadataRecord", {**retained.metadata, "artifacts": {"x": "y"}}
        ),
        results=retained.results,
    )
    check_models._write_retained_run(updated, path)
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["artifacts"] == {"x": "y"}
    assert [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []


def test_retained_run_round_trips_through_the_single_loader(tmp_path: Path) -> None:
    """One loader owns decoding and validation for every consumer."""
    retained = _retained_run_fixture(tmp_path)
    path = tmp_path / "results.jsonl"
    check_models._write_retained_run(retained, path)

    loaded = check_models._load_retained_run(path)
    assert loaded.metadata["format_version"] == "3.0"
    assert [record["model"] for record in loaded.results] == ["org/m"]

    schema2 = json.dumps({"_type": "metadata", "format_version": "2.0", "prompt": "x"}) + "\n"
    with pytest.raises(ValueError, match="format_version"):
        check_models._load_retained_run_text(schema2, "baseline")
