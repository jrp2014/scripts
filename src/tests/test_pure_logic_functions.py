"""Unit tests for pure-logic functions that require no mlx-vlm runtime.

Covers model selection, prompt construction, threshold loading, and retained
mechanical helper behavior.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import logging
import subprocess
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never, cast
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:  # pragma: no cover
    import types

import pytest
import yaml


@pytest.fixture(scope="module")
def mod() -> types.ModuleType:
    """Import check_models module once for all tests."""
    return importlib.import_module("check_models")


# ── validate_model_identifier ──────────────────────────────────────────────


class TestValidateModelIdentifier:
    """Tests for validate_model_identifier()."""

    def test_valid_hub_id(self, mod: types.ModuleType) -> None:
        """Standard org/name format should pass."""
        mod.validate_model_identifier("mlx-community/nanoLLaVA")

    def test_valid_single_name(self, mod: types.ModuleType) -> None:
        """Single name without slash is valid for hub IDs."""
        mod.validate_model_identifier("nanoLLaVA")

    def test_empty_string_raises(self, mod: types.ModuleType) -> None:
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            mod.validate_model_identifier("")

    def test_whitespace_only_raises(self, mod: types.ModuleType) -> None:
        """Whitespace-only string should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            mod.validate_model_identifier("   ")

    def test_spaces_in_hub_id_raises(self, mod: types.ModuleType) -> None:
        """Spaces in hub ID should raise ValueError."""
        with pytest.raises(ValueError, match="contains spaces"):
            mod.validate_model_identifier("mlx community/nanoLLaVA")

    def test_local_path_nonexistent_raises(self, mod: types.ModuleType) -> None:
        """Non-existent local path should raise ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            mod.validate_model_identifier("/nonexistent/model/path")

    def test_local_path_file_raises(self, mod: types.ModuleType, tmp_path: Path) -> None:
        """File path (not directory) should raise ValueError."""
        f = tmp_path / "not_a_dir.txt"
        f.write_text("hello")
        with pytest.raises(ValueError, match="not a directory"):
            mod.validate_model_identifier(str(f))

    def test_local_path_valid_dir(self, mod: types.ModuleType, tmp_path: Path) -> None:
        """Existing directory should pass."""
        mod.validate_model_identifier(str(tmp_path))


class TestToolchainHelpers:
    """Tests for local toolchain probe helpers."""

    def test_run_toolchain_command_returns_stripped_stdout(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Toolchain command helper should normalize successful stdout."""

        def fake_run(
            cmd: list[str],
            *,
            capture_output: bool,
            text: bool,
            timeout: int,
            check: bool,
        ) -> subprocess.CompletedProcess[str]:
            assert cmd == ["/usr/bin/example", "--version"]
            assert capture_output is True
            assert text is True
            assert timeout == 2
            assert check is False
            return subprocess.CompletedProcess(cmd, 0, stdout="  value\n", stderr="")

        monkeypatch.setattr(mod.subprocess, "run", fake_run)

        assert mod._run_macos_toolchain_command(["/usr/bin/example", "--version"]) == "value"

    def test_run_toolchain_command_returns_none_on_os_error(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Toolchain command helper should hide unavailable command probes."""

        def fake_run(
            cmd: list[str],
            *,
            capture_output: bool,
            text: bool,
            timeout: int,
            check: bool,
        ) -> subprocess.CompletedProcess[str]:
            _ = (cmd, capture_output, text, timeout, check)
            msg = "missing"
            raise OSError(msg)

        monkeypatch.setattr(mod.subprocess, "run", fake_run)

        assert mod._run_macos_toolchain_command(["/usr/bin/missing"]) is None


class TestDistributionMetadataHelpers:
    """Tests for installed distribution metadata helpers."""

    def test_distribution_text_file_rejects_unknown_metadata_filename_before_lookup(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unknown metadata filenames should not reach importlib.metadata."""

        def fail_distribution(_distribution_name: str) -> Never:
            raise AssertionError

        monkeypatch.setattr(mod, "distribution", fail_distribution)

        assert mod._distribution_text_file("example-package", "METADATA") is None
        assert mod._distribution_text_file("example-package", "../direct_url.json") is None

    def test_distribution_text_file_allows_direct_url_metadata(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """direct_url.json should remain readable for editable-install detection."""
        metadata_file = tmp_path / "direct_url.json"
        metadata_file.write_text('{"dir_info": {"editable": true}}', encoding="utf-8")

        class FakeDistribution:
            files = (Path("example-1.0.dist-info") / "direct_url.json",)

            def locate_file(self, filename: Path) -> Path:
                assert filename == Path("example-1.0.dist-info") / "direct_url.json"
                return metadata_file

            def read_text(self, _filename: str) -> Never:
                raise AssertionError

        monkeypatch.setattr(mod, "distribution", lambda _distribution_name: FakeDistribution())

        assert mod._distribution_text_file("example-package", "direct_url.json") == (
            '{"dir_info": {"editable": true}}'
        )

    def test_distribution_direct_url_validates_narrow_pep610_fields(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Untrusted direct-URL JSON should be narrowed before internal use."""
        payload = {
            "url": "file:///tmp/mlx-vlm",
            "dir_info": {"editable": "yes", "unexpected": True},
            "vcs_info": {"vcs": "git", "commit_id": "abc123", "requested_revision": 7},
            "subdirectory": "python",
        }
        monkeypatch.setattr(
            mod,
            "_distribution_text_file",
            lambda _name, _filename: json.dumps(payload),
        )

        assert mod._distribution_direct_url("mlx-vlm") == {
            "url": "file:///tmp/mlx-vlm",
            "dir_info": {},
            "vcs_info": {"vcs": "git", "commit_id": "abc123"},
            "subdirectory": "python",
        }


class TestSafeTextFileIO:
    """Tests for symlink-resistant text file helpers."""

    def test_write_text_file_rejects_symlink_target(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
    ) -> None:
        """Generated artifacts should not follow a symlink target."""
        target = tmp_path / "target.txt"
        link = tmp_path / "artifact.txt"
        link.symlink_to(target)

        with pytest.raises(OSError, match="symlink"):
            mod._write_text_file(link, "unsafe")

        assert not target.exists()

    def test_read_text_file_rejects_symlink_target(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
    ) -> None:
        """History reads should not follow a symlink target."""
        target = tmp_path / "target.txt"
        target.write_text("payload", encoding="utf-8")
        link = tmp_path / "history.jsonl"
        link.symlink_to(target)

        with pytest.raises(OSError, match="symlink"):
            mod._read_text_file(link)

    def test_write_text_file_rejects_symlink_parent(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
    ) -> None:
        """Generated artifacts should not follow a symlinked parent."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link_dir = tmp_path / "linked"
        link_dir.symlink_to(real_dir, target_is_directory=True)

        with pytest.raises(OSError, match="symlinked directory"):
            mod._write_text_file(link_dir / "artifact.txt", "unsafe")

        assert not (real_dir / "artifact.txt").exists()

    def test_read_text_file_enforces_size_cap(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
    ) -> None:
        """History reads should reject oversized files before decoding."""
        path = tmp_path / "history.jsonl"
        path.write_text("abcdef", encoding="utf-8")

        with pytest.raises(OSError, match="exceeds"):
            mod._read_text_file(path, max_bytes=3)


# ── apply_exclusions ───────────────────────────────────────────────────────


class TestApplyExclusions:
    """Tests for apply_exclusions()."""

    def test_empty_exclusion_list(self, mod: types.ModuleType) -> None:
        """Empty exclusion list should return all models."""
        models = ["a", "b", "c"]
        result = mod.apply_exclusions(models, [], "test")
        assert result == ["a", "b", "c"]

    def test_excludes_matching_models(self, mod: types.ModuleType) -> None:
        """Matching models should be excluded."""
        models = ["model-a", "model-b", "model-c"]
        result = mod.apply_exclusions(models, ["model-b"], "test")
        assert result == ["model-a", "model-c"]

    def test_excludes_multiple(self, mod: types.ModuleType) -> None:
        """Multiple exclusions should all be applied."""
        models = ["a", "b", "c", "d"]
        result = mod.apply_exclusions(models, ["b", "d"], "test")
        assert result == ["a", "c"]

    def test_no_matches_returns_all(self, mod: types.ModuleType) -> None:
        """Non-matching exclusions should leave list intact."""
        models = ["a", "b"]
        result = mod.apply_exclusions(models, ["z"], "test")
        assert result == ["a", "b"]

    def test_preserves_order(self, mod: types.ModuleType) -> None:
        """Original order should be preserved after exclusion."""
        models = ["z", "a", "m"]
        result = mod.apply_exclusions(models, ["a"], "test")
        assert result == ["z", "m"]


class TestValidateAndWarnModelSelection:
    """Tests for validate_and_warn_model_selection()."""

    @staticmethod
    def _make_args(
        *,
        exclude: list[str] | None,
        models: list[str] | None,
        verbose: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(exclude=exclude, models=models, verbose=verbose)

    def test_warns_when_excluded_model_is_not_cached(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Excluded models missing from cache should emit a warning."""
        args = self._make_args(exclude=["missing-model"], models=["selected-model"])

        with (
            patch.object(mod, "_all_cached_repo_ids", return_value=["cached-model"]),
            caplog.at_level(logging.WARNING, logger=mod.LOGGER_NAME),
        ):
            mod.validate_and_warn_model_selection(args)

        assert (
            "The following excluded models are not in the local cache and will have no effect: "
            "missing-model"
        ) in caplog.messages

    def test_does_not_warn_for_cached_exclusion_outside_selection(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Cached exclusions should not warn just because they are not in --models."""
        args = self._make_args(exclude=["cached-model"], models=["selected-model"])

        with (
            patch.object(mod, "_all_cached_repo_ids", return_value=["cached-model"]),
            caplog.at_level(logging.WARNING, logger=mod.LOGGER_NAME),
        ):
            mod.validate_and_warn_model_selection(args)

        assert not caplog.messages

    def test_dry_run_uses_real_selection_warnings(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Dry-run selection should warn exactly as an executable selection would."""
        args = self._make_args(exclude=["missing-model"], models=["selected-model"])
        image_path = tmp_path / "image.jpg"

        with (
            patch.object(mod, "_all_cached_repo_ids", return_value=["selected-model"]),
            patch.object(mod, "_arch_precheck_for_model", return_value=(None, None, None)),
            caplog.at_level(logging.INFO, logger=mod.LOGGER_NAME),
        ):
            mod._handle_dry_run(args, image_path, "Describe this image.", {})

        assert any(
            "missing-model" in message and "will have no effect" in message
            for message in caplog.messages
        )
        assert any("Would process 1 model(s)" in message for message in caplog.messages)

    def test_dry_run_warns_when_an_explicit_model_is_partially_cached(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """A partially downloaded --models entry is announced, not silently fetched later."""
        args = self._make_args(exclude=[], models=["org/partial"])
        partial = mod.CachedModelEligibility(
            "org/partial", supported=False, reasons=("missing safetensors weights",)
        )

        with (
            patch.object(mod, "_all_cached_repo_ids", return_value=["org/partial"]),
            patch.object(mod, "get_cached_model_eligibility", return_value=(partial,)),
            patch.object(mod, "_arch_precheck_for_model", return_value=(None, None, None)),
            caplog.at_level(logging.INFO, logger=mod.LOGGER_NAME),
        ):
            mod._handle_dry_run(args, tmp_path / "image.jpg", "Describe this image.", {})

        assert any(
            "org/partial: its cached main revision fails the default-discovery layout check"
            in message
            and "missing safetensors weights" in message
            for message in caplog.messages
        )


# ── prepare_prompt ─────────────────────────────────────────────────────────


class TestPreparePrompt:
    """Tests for prepare_prompt()."""

    @pytest.mark.parametrize(
        ("cli", "expected"),
        [
            (
                [],
                "Lane: assisted | Prompt: built-in (metadata hints) | Assessment: metadata | Max tokens: 1000",
            ),
            (
                ["--eval-mode", "blind"],
                "Lane: blind | Prompt: built-in (no hints) | Assessment: metadata | Max tokens: 1000",
            ),
            (
                ["--eval-mode", "triage"],
                "Lane: triage | Prompt: brief caption (no hints) | Assessment: general | Max tokens: 200",
            ),
            (
                ["--prompt", "Caption."],
                "Lane: assisted | Prompt: custom (no automatic hints) | Assessment: general | Max tokens: 1000",
            ),
            (
                ["--eval-mode", "triage", "--prompt", "Caption."],
                "Lane: triage | Prompt: custom (no automatic hints) | Assessment: general | Max tokens: 200",
            ),
            (
                [
                    "--prompt",
                    "Metadata.",
                    "--assessment-profile",
                    "metadata",
                    "--max-tokens",
                    "350",
                ],
                "Lane: assisted | Prompt: custom (no automatic hints) | Assessment: metadata | Max tokens: 350",
            ),
            (
                ["--assessment-profile", "general"],
                "Lane: assisted | Prompt: built-in (metadata hints) | Assessment: general | Max tokens: 1000",
            ),
        ],
    )
    def test_resolved_configuration_is_logged(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
        cli: list[str],
        expected: str,
    ) -> None:
        """Log effective settings, not lane defaults or assumed hint exposure."""
        args = mod._build_cli_parser().parse_args(cli)
        metadata = {"description": "Reference hint"}
        with caplog.at_level(logging.INFO, logger=mod.LOGGER_NAME):
            mod._apply_eval_mode_defaults(args, metadata)
            prompt = mod.prepare_prompt(args, metadata)
        assert expected in caplog.messages
        if args.prompt:
            assert prompt == args.prompt

    @staticmethod
    def _make_args(
        prompt: str | None = None,
        *,
        eval_mode: str = "auto",
    ) -> argparse.Namespace:
        return argparse.Namespace(prompt=prompt, eval_mode=eval_mode)

    def test_user_provided_prompt(self, mod: types.ModuleType) -> None:
        """User-provided prompt should be returned verbatim."""
        args = self._make_args(prompt="Describe this photo.")
        result = mod.prepare_prompt(args, {})
        assert result == "Describe this photo."

    def test_user_provided_prompt_is_logged(
        self, mod: types.ModuleType, caplog: pytest.LogCaptureFixture
    ) -> None:
        """User-provided prompt should be visible in the info log."""
        args = self._make_args(prompt="Describe this photo.")

        with caplog.at_level(logging.INFO, logger=mod.LOGGER_NAME):
            result = mod.prepare_prompt(args, {})

        assert result == "Describe this photo."
        assert "Using user-provided prompt from --prompt." in caplog.messages
        assert "User-provided prompt (--prompt): Describe this photo." in caplog.messages

    def test_generated_prompt_with_metadata(self, mod: types.ModuleType) -> None:
        """Generated prompt should incorporate metadata fields."""
        metadata = {
            "description": "Sunset over cliffs",
            "date": "2025-10-01",
            "time": "18:30",
            "gps": "51.0N, 0.9W",
        }
        args = self._make_args()
        result = mod.prepare_prompt(args, metadata)
        assert "Sunset over cliffs" in result
        assert "2025-10-01" in result
        assert "18:30" in result
        assert "51.0N, 0.9W" in result

    def test_generated_prompt_empty_metadata_uses_blind_cataloguing_prompt(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Auto mode should benchmark structured cataloguing without metadata leakage."""
        args = self._make_args()
        result = mod.prepare_prompt(args, {})
        assert "Return exactly these three sections" in result
        assert "Title:" in result
        assert "Keywords:" in result
        assert "metadata hints" not in result.casefold()
        assert "Context:" not in result

    def test_blind_prompt_withholds_available_metadata(self, mod: types.ModuleType) -> None:
        """Blind lane should not expose descriptive or capture metadata to the model."""
        args = self._make_args(eval_mode="blind")
        result = mod.prepare_prompt(
            args,
            {
                "title": "Private reference title",
                "description": "Private reference description",
                "keywords": "private, reference",
                "date": "2026-07-10",
                "gps": "51.5,-0.1",
            },
        )

        assert "Private reference" not in result
        assert "2026-07-10" not in result
        assert "51.5,-0.1" not in result
        assert "Context:" not in result

    def test_resolve_eval_mode_rejects_unsupported_values(self, mod: types.ModuleType) -> None:
        """Resolved report lanes should remain a closed, precisely typed set."""
        with pytest.raises(ValueError, match="Unsupported evaluation mode"):
            mod._resolve_eval_mode("experimental", None)

    def test_assisted_prompt_exposes_descriptive_metadata(self, mod: types.ModuleType) -> None:
        """Assisted lane should expose reference metadata for visual verification."""
        args = self._make_args(eval_mode="assisted")
        result = mod.prepare_prompt(
            args,
            {
                "title": "Brick storefront",
                "description": "Outdoor seating beside a pavement.",
                "keywords": "brick, storefront, seating",
            },
        )

        assert "Context: Descriptive hints:" in result
        assert "Title hint: Brick storefront" in result
        assert "Brick storefront" in result
        assert "Outdoor seating" in result

    def test_assisted_prompt_separates_authoritative_context_from_draft(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Assisted prompts should label factual context separately from draft text."""
        args = argparse.Namespace(prompt=None, eval_mode="assisted")
        prompt = mod.prepare_prompt(
            args,
            {
                "title": "Deben Estuary at Woodbridge",
                "description": "Two boats on a river.",
                "keywords": "Deben Estuary, Woodbridge, boats, river",
                "date": "2026-07-04",
                "time": "19:10:04",
                "gps": "52.0,-1.0",
            },
        )

        assert "Authoritative context:" in prompt
        assert "Capture date/time: 2026-07-04 19:10:04" in prompt
        assert "Descriptive hints:" in prompt
        assert "Description hint: Two boats on a river." in prompt
        assert "Keyword hints: Deben Estuary, Woodbridge, boats, river" in prompt
        assert "hints may be incomplete or wrong" in prompt

    def test_assisted_prompt_does_not_duplicate_time_embedded_in_capture_date(
        self,
        mod: types.ModuleType,
    ) -> None:
        """The full localized EXIF datetime should appear once in assisted context."""
        prompt = mod.prepare_prompt(
            argparse.Namespace(prompt=None, eval_mode="assisted"),
            {
                "date": "2026-07-25 18:33:16 UTC+01:00",
                "time": "18:33:16",
            },
        )

        assert "Capture date/time: 2026-07-25 18:33:16 UTC+01:00" in prompt
        assert prompt.count("18:33:16") == 1

    def test_assisted_prompt_does_not_promote_keyword_names_to_authoritative_context(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Arbitrary metadata keywords remain fallible draft text."""
        prompt = mod.prepare_prompt(
            argparse.Namespace(prompt=None, eval_mode="assisted"),
            {"keywords": "Example Harbour, Sample Village, boats"},
        )

        assert "Authoritative context:" not in prompt
        assert "Keyword hints: Example Harbour, Sample Village, boats" in prompt


# ── compute_vocabulary_diversity ───────────────────────────────────────────


# ── compute_efficiency_metrics ─────────────────────────────────────────────


# ── detect_response_structure ──────────────────────────────────────────────


# ── compute_confidence_indicators ──────────────────────────────────────────


class TestDisplayWidthUtilities:
    """Tests for display-width-aware terminal helpers."""

    def test_display_width_ignores_ansi_escape_sequences(self, mod: types.ModuleType) -> None:
        """ANSI color wrappers should not count toward rendered width."""
        colored = "\033[91mabc\033[0m"
        assert mod._display_width(colored) == 3

    def test_display_align_targets_display_width(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Display alignment should honor display width even with wide glyphs."""
        wide_char = "界"
        padded = mod._display_align(wide_char, 4, alignment="left")
        centered = mod._display_align(wide_char, 5, alignment="center")
        assert mod._display_width(padded) == 4
        assert mod._display_width(centered) == 5

    def test_display_width_counts_wide_glyphs_as_two_columns(self, mod: types.ModuleType) -> None:
        """A full-width glyph occupies two terminal cells (rich.cells.cell_len)."""
        assert mod._display_width("界") == 2


# ── QualityThresholds.from_config (YAML schema validation) ────────────────


class TestQualityThresholdsFromConfig:
    """Tests for QualityThresholds.from_config() including unknown key warnings."""

    def test_valid_config(self, mod: types.ModuleType) -> None:
        """Valid config should set the specified threshold."""
        expected_ratio = 0.9
        config = {"thresholds": {"repetition_ratio": expected_ratio}}
        qt = mod.QualityThresholds.from_config(config)
        assert qt.repetition_ratio == expected_ratio

    def test_unknown_threshold_key_warns(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Unknown threshold key should emit a warning."""
        config = {
            "thresholds": {"repetition_ration": 0.9, "repetition_ratio": 0.5},
        }
        with caplog.at_level(logging.WARNING):
            qt = mod.QualityThresholds.from_config(config)
        assert "repetition_ration" in caplog.text
        # The valid key should still be applied
        expected_ratio = 0.5
        assert qt.repetition_ratio == expected_ratio

    def test_unknown_top_level_section_warns(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Unknown top-level config section should emit a warning."""
        config: dict[str, object] = {"thresholds": {}, "extra_section": {}}
        with caplog.at_level(logging.WARNING):
            mod.QualityThresholds.from_config(config)
        assert "extra_section" in caplog.text

    def test_empty_config(self, mod: types.ModuleType) -> None:
        """Empty config should use all defaults."""
        config: dict[str, object] = {}
        qt = mod.QualityThresholds.from_config(config)
        # Should use all defaults
        default_ratio = 0.9
        assert qt.repetition_ratio == default_ratio

    def test_python_defaults_match_packaged_yaml_thresholds(self, mod: types.ModuleType) -> None:
        """Fallback dataclass thresholds should not drift from packaged YAML defaults."""
        config_path = (
            Path(__file__).resolve().parents[1] / "check_models_data" / "quality_config.yaml"
        )
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        configured = mod.QualityThresholds.from_config({"thresholds": config["thresholds"]})
        fallback = mod.QualityThresholds()

        for field in fields(fallback):
            assert getattr(fallback, field.name) == getattr(configured, field.name), field.name

    def test_non_mapping_threshold_section_raises(self, mod: types.ModuleType) -> None:
        """Non-mapping threshold sections should fail with a clear schema error."""
        config: dict[str, object] = {"thresholds": []}

        with pytest.raises(TypeError, match="thresholds section must be a mapping"):
            mod.QualityThresholds.from_config(config)

    def test_invalid_threshold_bounds_raise(self, mod: types.ModuleType) -> None:
        """Inverted threshold bounds should fail fast instead of weakening checks."""
        config = {
            "thresholds": {"min_phrase_repetitions": 9, "max_phrase_repetitions": 4},
        }

        with pytest.raises(ValueError, match="invalid phrase repetitions bounds"):
            mod.QualityThresholds.from_config(config)


# ── load_quality_config ───────────────────────────────────────────────────


class TestLoadQualityConfig:
    """Tests for load_quality_config()."""

    def test_nonexistent_path_warns(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Non-existent config path should warn."""
        with caplog.at_level(logging.WARNING):
            mod.load_quality_config(Path("/nonexistent/quality_config.yaml"))
        assert "not found" in caplog.text

    def test_valid_yaml_loads(self, mod: types.ModuleType, tmp_path: Path) -> None:
        """Valid YAML config should update thresholds."""
        yaml_content = "thresholds:\n  repetition_ratio: 0.95\n"
        config_file = tmp_path / "quality_config.yaml"
        config_file.write_text(yaml_content)
        original_quality = mod.QUALITY
        try:
            mod.load_quality_config(config_file)
            expected_ratio = 0.95
            assert mod.QUALITY.repetition_ratio == expected_ratio
        finally:
            cast("Any", mod).QUALITY = original_quality

    def test_invalid_yaml_warns(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Invalid YAML should warn instead of crashing."""
        config_file = tmp_path / "quality_config.yaml"
        config_file.write_text("{{{{invalid yaml")
        with caplog.at_level(logging.WARNING):
            mod.load_quality_config(config_file)
        assert "Failed to load" in caplog.text

    def test_non_mapping_yaml_warns(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Non-mapping YAML content should warn instead of crashing."""
        config_file = tmp_path / "quality_config.yaml"
        config_file.write_text("- unexpected\n- list\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            mod.load_quality_config(config_file)

        assert "top-level document must be a mapping" in caplog.text

    def test_invalid_threshold_config_warns_and_preserves_defaults(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Invalid threshold bounds should warn and leave the existing config intact."""
        original_ratio = mod.QUALITY.repetition_ratio
        config_file = tmp_path / "quality_config.yaml"
        config_file.write_text(
            "thresholds:\n  min_phrase_repetitions: 8\n  max_phrase_repetitions: 3\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            mod.load_quality_config(config_file)

        assert "Failed to load" in caplog.text
        assert mod.QUALITY.repetition_ratio == original_ratio

    def test_default_load_uses_packaged_resource(
        self,
        mod: types.ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default loading should use the packaged config resource."""
        packaged_config = tmp_path / "quality_config.yaml"
        packaged_config.write_text(
            "thresholds:\n  repetition_ratio: 0.91\n",
            encoding="utf-8",
        )
        original_quality = mod.QUALITY

        def fake_files(package: str) -> Path:
            assert package == "check_models_data"
            return tmp_path

        monkeypatch.setattr(mod, "files", fake_files)
        monkeypatch.setattr(mod, "as_file", contextlib.nullcontext)

        try:
            mod.load_quality_config()
            assert mod.QUALITY.repetition_ratio == 0.91
        finally:
            cast("Any", mod).QUALITY = original_quality


class TestSystemProfilerParsing:
    """Tests for typed normalization of macOS system_profiler JSON output."""

    def test_get_device_info_filters_non_mapping_entries(self, mod: types.ModuleType) -> None:
        """Only mapping entries should survive normalization of system_profiler lists."""
        payload = json.dumps(
            {
                "SPDisplaysDataType": [
                    {"sppci_model": "Apple M4", "sppci_cores": 10},
                    "skip-me",
                    5,
                ],
                "SPAudioDataType": [{"_name": "MacBook Speakers"}],
                "_ignored": "scalar",
            }
        )

        mod.get_device_info.cache_clear()
        with (
            patch.object(mod.platform, "system", return_value="Darwin"),
            patch.object(mod.subprocess, "check_output", return_value=payload),
        ):
            info = mod.get_device_info()
        mod.get_device_info.cache_clear()

        assert info == {
            "SPDisplaysDataType": [{"sppci_model": "Apple M4", "sppci_cores": 10}],
            "SPAudioDataType": [{"_name": "MacBook Speakers"}],
        }

    def test_get_device_info_is_cached(self, mod: types.ModuleType) -> None:
        """Repeated device-info reads should reuse the cached system_profiler payload."""
        payload = json.dumps({"SPDisplaysDataType": [{"sppci_model": "Apple M4"}]})

        mod.get_device_info.cache_clear()
        with (
            patch.object(mod.platform, "system", return_value="Darwin"),
            patch.object(mod.subprocess, "check_output", return_value=payload) as check_output,
        ):
            first = mod.get_device_info()
            second = mod.get_device_info()
        mod.get_device_info.cache_clear()

        assert first == second
        assert check_output.call_count == 1

    def test_get_system_info_uses_first_string_gpu_name(self, mod: types.ModuleType) -> None:
        """GPU info should come from the first usable string field in display data."""
        payload = json.dumps(
            {
                "SPDisplaysDataType": [
                    {"sppci_model": "Apple M4 Max", "_name": "Fallback Name"},
                ]
            }
        )

        mod.get_device_info.cache_clear()
        mod.get_system_info.cache_clear()
        with (
            patch.object(mod.platform, "system", return_value="Darwin"),
            patch.object(mod.platform, "machine", return_value="arm64"),
            patch.object(mod.subprocess, "check_output", return_value=payload),
        ):
            arch, gpu_info = mod.get_system_info()
        mod.get_device_info.cache_clear()
        mod.get_system_info.cache_clear()

        assert arch == "arm64"
        assert gpu_info == "Apple M4 Max"


class TestHardwareFacts:
    """Tests for dependency-free MLX and macOS hardware fact collection."""

    def test_get_mlx_device_info_normalizes_and_caches(
        self,
        mod: types.ModuleType,
    ) -> None:
        """The report-facing MLX subset should be validated and cached."""
        runtime = MagicMock()
        runtime.device_info.return_value = {
            "device_name": " Apple M5 Max ",
            "architecture": " applegpu_g17s ",
            "memory_size": 128 * 1024**3,
            "max_recommended_working_set_size": 96 * 1024**3,
            "ignored": "value",
        }
        mod._get_mlx_device_info.cache_clear()
        with patch.object(mod, "mx", runtime):
            first = mod._get_mlx_device_info()
            second = mod._get_mlx_device_info()
        mod._get_mlx_device_info.cache_clear()

        assert (
            first
            == second
            == {
                "device_name": "Apple M5 Max",
                "architecture": "applegpu_g17s",
                "memory_size": 128 * 1024**3,
                "max_recommended_working_set_size": 96 * 1024**3,
            }
        )
        runtime.device_info.assert_called_once_with()

    @pytest.mark.parametrize(
        "payload",
        [
            {"memory_size": True},
            {"memory_size": 0},
            {"memory_size": -1},
            {"memory_size": "128 GB"},
            {"device_name": "  ", "architecture": 17},
        ],
    )
    def test_get_mlx_device_info_rejects_invalid_values(
        self,
        mod: types.ModuleType,
        payload: dict[str, object],
    ) -> None:
        """Invalid MLX values should never become report facts."""
        runtime = MagicMock()
        runtime.device_info.return_value = payload
        mod._get_mlx_device_info.cache_clear()
        with patch.object(mod, "mx", runtime):
            assert mod._get_mlx_device_info() == {}
        mod._get_mlx_device_info.cache_clear()

    def test_get_mlx_device_info_handles_missing_and_errored_runtime(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Missing or errored MLX probes should return an empty fact set."""
        mod._get_mlx_device_info.cache_clear()
        with patch.object(mod, "mx", None):
            assert mod._get_mlx_device_info() == {}
        mod._get_mlx_device_info.cache_clear()

        runtime = MagicMock()
        runtime.device_info.side_effect = RuntimeError("Metal unavailable")
        with patch.object(mod, "mx", runtime):
            assert mod._get_mlx_device_info() == {}
        mod._get_mlx_device_info.cache_clear()

    def test_get_total_memory_bytes_prefers_psutil(self, mod: types.ModuleType) -> None:
        """The established psutil total remains the primary memory source."""
        fake_psutil = MagicMock()
        fake_psutil.virtual_memory.return_value.total = 64 * 1024**3
        with (
            patch.object(mod, "psutil", fake_psutil),
            patch.object(mod, "_get_macos_sysctl_value") as sysctl_value,
            patch.object(mod, "_get_mlx_device_info") as mlx_info,
        ):
            assert mod._get_total_memory_bytes() == 64 * 1024**3
        sysctl_value.assert_not_called()
        mlx_info.assert_not_called()

    def test_get_total_memory_bytes_uses_sysctl_without_psutil(
        self,
        mod: types.ModuleType,
    ) -> None:
        """A valid macOS hw.memsize value should fill the optional-dependency gap."""
        with (
            patch.object(mod, "psutil", None),
            patch.object(mod, "_get_macos_sysctl_value", return_value=str(48 * 1024**3)),
            patch.object(mod, "_get_mlx_device_info") as mlx_info,
        ):
            assert mod._get_total_memory_bytes() == 48 * 1024**3
        mlx_info.assert_not_called()

    def test_get_total_memory_bytes_falls_back_from_sysctl_to_mlx(
        self,
        mod: types.ModuleType,
    ) -> None:
        """MLX memory should be used after unavailable sysctl data."""
        with (
            patch.object(mod, "psutil", None),
            patch.object(mod, "_get_macos_sysctl_value", return_value=None),
            patch.object(
                mod,
                "_get_mlx_device_info",
                return_value={"memory_size": 32 * 1024**3},
            ),
        ):
            assert mod._get_total_memory_bytes() == 32 * 1024**3

    def test_get_total_memory_bytes_returns_none_without_valid_source(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Failed probes must not turn into a guessed memory amount."""
        with (
            patch.object(mod, "psutil", None),
            patch.object(mod, "_get_macos_sysctl_value", return_value="not-an-int"),
            patch.object(mod, "_get_mlx_device_info", return_value={}),
        ):
            assert mod._get_total_memory_bytes() is None

    def test_get_recommended_working_set_bytes_requires_positive_mlx_value(
        self,
        mod: types.ModuleType,
    ) -> None:
        """The working-set ceiling should come only from normalized MLX facts."""
        with patch.object(
            mod,
            "_get_mlx_device_info",
            return_value={"max_recommended_working_set_size": 24 * 1024**3},
        ):
            assert mod._get_recommended_working_set_bytes() == 24 * 1024**3
        with patch.object(mod, "_get_mlx_device_info", return_value={}):
            assert mod._get_recommended_working_set_bytes() is None

    def test_get_system_characteristics_surfaces_mlx_hardware_facts(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Human system information should include every normalized MLX fact."""
        with (
            patch.object(mod.platform, "system", return_value="Darwin"),
            patch.object(mod.platform, "machine", return_value="arm64"),
            patch.object(mod, "_get_macos_toolchain_info", return_value={}),
            patch.object(mod, "get_system_info", return_value=("arm64", None)),
            patch.object(mod, "_get_apple_silicon_info", return_value={}),
            patch.object(
                mod,
                "_get_macos_sysctl_value",
                side_effect=lambda name: (
                    "Apple M5 Max" if name == "machdep.cpu.brand_string" else None
                ),
            ),
            patch.object(mod, "_get_total_memory_bytes", return_value=128 * 1024**3),
            patch.object(
                mod,
                "_get_mlx_device_info",
                return_value={
                    "device_name": "Apple M5 Max",
                    "architecture": "applegpu_g17s",
                    "max_recommended_working_set_size": 96 * 1024**3,
                },
            ),
            patch.object(mod, "_get_mlx_backend_artifact_info", return_value={}),
            patch.object(mod, "_probe_fused_attention", return_value={"status": "ok"}),
            patch.object(mod, "psutil", None),
        ):
            info = mod.get_system_characteristics()

        assert info["GPU/Chip"] == "Apple M5 Max"
        assert info["MLX Device"] == "Apple M5 Max"
        assert info["GPU Architecture"] == "applegpu_g17s"
        assert info["RAM"] == "128.0 GB"
        assert info["Recommended Working Set"] == "96 GB"
        assert info["Fused Attention"] == "Available"

    @pytest.mark.parametrize(
        ("profiler_name", "sysctl_name", "mlx_name", "expected"),
        [
            ("Apple M4 Max", "Apple M5 Max", "MLX Device", "Apple M4 Max"),
            (None, "Apple M5 Max", "MLX Device", "Apple M5 Max"),
            (None, None, "MLX Device", "MLX Device"),
        ],
    )
    def test_get_system_characteristics_chip_fallback_order(
        self,
        mod: types.ModuleType,
        profiler_name: str | None,
        sysctl_name: str | None,
        mlx_name: str,
        expected: str,
    ) -> None:
        """Chip identity should retain profiler priority and degrade gracefully."""
        with (
            patch.object(mod.platform, "system", return_value="Darwin"),
            patch.object(mod, "_get_macos_toolchain_info", return_value={}),
            patch.object(mod, "get_system_info", return_value=("arm64", profiler_name)),
            patch.object(mod, "_get_apple_silicon_info", return_value={}),
            patch.object(mod, "_get_macos_sysctl_value", return_value=sysctl_name),
            patch.object(mod, "_get_total_memory_bytes", return_value=None),
            patch.object(
                mod,
                "_get_mlx_device_info",
                return_value={"device_name": mlx_name},
            ),
            patch.object(mod, "_get_mlx_backend_artifact_info", return_value={}),
            patch.object(
                mod,
                "_probe_fused_attention",
                return_value={"status": "unavailable"},
            ),
            patch.object(mod, "psutil", None),
        ):
            info = mod.get_system_characteristics()

        assert info["GPU/Chip"] == expected

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("ok", "Available"),
            ("unavailable", "Unavailable"),
            ("errored", "Error"),
            ("timed_out", "Timed out"),
        ],
    )
    def test_get_system_characteristics_maps_fused_attention_state(
        self,
        mod: types.ModuleType,
        status: str,
        expected: str,
    ) -> None:
        """Human capability state should map from the shared structured probe."""
        with (
            patch.object(mod.platform, "system", return_value="Other"),
            patch.object(mod, "get_system_info", return_value=("arm64", None)),
            patch.object(mod, "_get_apple_silicon_info", return_value={}),
            patch.object(mod, "_get_total_memory_bytes", return_value=None),
            patch.object(mod, "_get_mlx_device_info", return_value={}),
            patch.object(mod, "_get_mlx_backend_artifact_info", return_value={}),
            patch.object(mod, "_probe_fused_attention", return_value={"status": status}),
            patch.object(mod, "psutil", None),
        ):
            info = mod.get_system_characteristics()

        assert info["Fused Attention"] == expected


@pytest.mark.parametrize(
    ("peak_gb", "working_set_bytes", "expected"),
    [
        (18.2, 96 * 1024**3, pytest.approx(17.6563238104)),
        (120.0, 96 * 1024**3, pytest.approx(116.4153218269)),
        (0.0, 96 * 1024**3, 0.0),
        (None, 96 * 1024**3, None),
        (float("nan"), 96 * 1024**3, None),
        (1.0, None, None),
        (1.0, 0, None),
        (-1.0, 96 * 1024**3, None),
    ],
)
def test_peak_memory_working_set_pct(
    mod: types.ModuleType,
    peak_gb: float | None,
    working_set_bytes: int | None,
    expected: object,
) -> None:
    """Working-set context should use MLX's decimal-GB allocator convention."""
    assert mod._peak_memory_working_set_pct(peak_gb, working_set_bytes) == expected


class TestPreflightDependencyDiagnostics:
    """Tests for upstream version-floor and source-pattern diagnostics."""

    def test_is_version_at_least_handles_dev_builds(self, mod: types.ModuleType) -> None:
        """Dev build strings should compare correctly against floor versions."""
        assert mod._is_version_at_least("0.30.7.dev20260214+c184262d", "0.30.4")
        assert mod._is_version_at_least("5.7.0+local", "5.7.0")
        assert not mod._is_version_at_least("5.7.0rc1", "5.7.0")
        # An unparseable installed version can never be shown to satisfy a floor.
        assert not mod._is_version_at_least("not-a-version", "1.0")

    def test_collect_upstream_requirements_tracks_strictest_floor(
        self,
        mod: types.ModuleType,
    ) -> None:
        """When multiple stacks are installed, stricter floor should win."""
        requirements = mod._collect_upstream_requirements(
            {
                "mlx-vlm": "0.4.1",
                "mlx": "0.31.1",
                "transformers": "5.4.0",
                "huggingface-hub": "1.10.1",
            },
        )
        # The project floor (0.32.1, first wheel with mlx/core/*.pyi) is now
        # stricter than upstream mlx-vlm's own mlx minimum.
        assert requirements["mlx"][0] == mod.PROJECT_RUNTIME_STACK_MINIMUMS["mlx"]
        assert requirements["mlx-vlm"][0] == mod.PROJECT_RUNTIME_STACK_MINIMUMS["mlx-vlm"]
        assert requirements["transformers"][0] == mod.PROJECT_MIN_TRANSFORMERS_VERSION
        assert (
            requirements["huggingface-hub"][0]
            == mod.PROJECT_RUNTIME_STACK_MINIMUMS["huggingface-hub"]
        )

    def test_detect_upstream_version_issues_reports_below_floor(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Installed versions below upstream floors should be surfaced."""
        issues = mod._detect_upstream_version_issues(
            {
                "mlx-vlm": "0.4.1",
                "mlx": "0.29.9",
                "transformers": "5.3.9",
                "huggingface-hub": "1.9.9",
            },
        )
        assert any(
            "mlx==0.29.9" in issue and mod.PROJECT_RUNTIME_STACK_MINIMUMS["mlx"] in issue
            for issue in issues
        )
        assert any(
            "mlx-vlm==0.4.1" in issue and mod.PROJECT_RUNTIME_STACK_MINIMUMS["mlx-vlm"] in issue
            for issue in issues
        )
        assert any("transformers==5.3.9" in issue and "5.14.0" in issue for issue in issues)
        assert any("huggingface-hub==1.9.9" in issue and "1.10.1" in issue for issue in issues)

    def test_detect_upstream_version_issues_accepts_transformers_without_upper_cap(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Transformers releases above 5.12 should be accepted after the MLX fix."""
        issues = mod._detect_upstream_version_issues(
            {
                "mlx-vlm": "0.6.16",
                "mlx": "0.32.1",
                "mlx-audio": "0.4.3",
                "transformers": "5.15.0",
                "huggingface-hub": "1.10.1",
            },
        )

        assert issues == []

    def test_get_callable_contract_issues_reports_keyword_drift(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Callable contract helper should flag missing keyword params we rely on."""

        def _fake_generate(model: object, processor: object, prompt: str) -> object:
            return (model, processor, prompt)

        issues = mod._get_callable_contract_issues(
            qualified_name="mlx_vlm.generate.stream_generate",
            symbol_value=_fake_generate,
            required_keyword_params=("model", "processor", "prompt", "verbose", "temperature"),
        )

        assert issues == [
            "mlx_vlm.generate.stream_generate is missing required keyword parameter(s): verbose, temperature.",
        ]

    def test_import_probe_excerpt_preserves_actionable_import_error_tail(
        self,
        mod: types.ModuleType,
    ) -> None:
        """Import probe summaries should keep the terminal ImportError visible."""
        probe_output = """
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import mlx_vlm
  File "/Users/jrp/Documents/AI/mlx/mlx-vlm/mlx_vlm/__init__.py", line 6, in <module>
    from .convert import convert
  File "/Users/jrp/Documents/AI/mlx/mlx-vlm/mlx_vlm/convert.py", line 11, in <module>
    from .utils import load
  File "/Users/jrp/Documents/AI/mlx/mlx-vlm/mlx_vlm/utils.py", line 21, in <module>
    from transformers import AutoProcessor
  File "/Users/jrp/miniconda3/envs/mlx-vlm/lib/python3.13/site-packages/transformers/utils/versions.py", line 43, in _compare_versions
    raise ImportError(
ImportError: tokenizers>=0.22.0,<=0.23.0 is required for a normal functioning of this module, but found tokenizers==0.23.1.
Try: `pip install transformers -U` or `pip install -e '.[dev]'` if you're working with git main
"""

        excerpt = mod._format_import_probe_output_excerpt(
            probe_output,
            max_output_excerpt_chars=220,
        )

        assert "Traceback (most recent call last)" in excerpt
        assert "..." in excerpt
        assert "ImportError: tokenizers>=0.22.0,<=0.23.0 is required" in excerpt
        assert "found tokenizers==0.23.1" in excerpt

    def test_runtime_api_drift_groups_missing_mlx_vlm_placeholders(
        self,
        mod: types.ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A failed mlx-vlm import should be one preflight issue, not four symbol warnings."""
        dependency_message = (
            "Core dependency initialization failed: mlx-vlm could not be imported safely. "
            "Import probe exited with code 1. Probe output: Traceback (most recent call last): "
            "ImportError: tokenizers>=0.22.0,<=0.23.0 is required, but found tokenizers==0.23.1."
        )
        monkeypatch.setitem(mod.MISSING_DEPENDENCIES, "mlx-vlm", dependency_message)
        for symbol_name in ("load", "apply_chat_template", "stream_generate", "load_image"):
            monkeypatch.setattr(mod, symbol_name, mod._raise_mlx_vlm_missing)

        issues = mod._detect_runtime_api_drift_issues()

        assert issues == (
            (
                "mlx-vlm import unavailable; affected API surfaces: "
                "mlx_vlm.utils.load, mlx_vlm.prompt_utils.apply_chat_template, "
                "mlx_vlm.generate.stream_generate, mlx_vlm.utils.load_image. "
                f"Root cause: {dependency_message}"
            ),
        )
        assert "missing-dependency placeholder" not in issues[0]

    def test_get_generation_result_contract_issues_reports_missing_fields(
        self,
        mod: types.ModuleType,
    ) -> None:
        """GenerationResult shape checks should surface missing upstream fields clearly."""

        @dataclass
        class _IncompleteGenerationResult:
            text: str = ""
            prompt_tokens: int = 0

        issues = mod._get_generation_result_contract_issues(_IncompleteGenerationResult)

        assert len(issues) == 1
        assert "generation_tokens" in issues[0]
        assert "total_tokens" in issues[0]
        assert "prompt_tps" in issues[0]

    def test_validate_model_artifact_layout_demotes_legacy_snapshot_notes(
        self,
        mod: types.ModuleType,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Legacy snapshot-layout notes should stay out of warning-level logs."""
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")

        with caplog.at_level(logging.DEBUG, logger=mod.LOGGER_NAME):
            mod._validate_model_artifact_layout(
                model_identifier="org/model",
                snapshot_path=tmp_path,
                tokenizer=object(),
            )

        assert (
            "Legacy snapshot note for org/model: tokenizer artifacts missing from snapshot"
            in caplog.text
        )
        assert (
            "Legacy snapshot note for org/model: processor config missing from snapshot"
            in caplog.text
        )
        assert "snapshot missing config.json" not in caplog.text
        assert "loaded processor has no image_processor" not in caplog.text
        assert not any(record.levelno >= logging.WARNING for record in caplog.records)


class TestSnapshotNotes:
    """Legacy file-layout facts are recorded as neutral per-model evidence."""

    def test_layout_validator_returns_missing_artifact_notes(
        self, mod: types.ModuleType, tmp_path: Path
    ) -> None:
        """A snapshot lacking processor config yields a note (and no exception)."""
        snapshot = tmp_path / "snapshot"
        snapshot.mkdir()
        (snapshot / "config.json").write_text("{}")
        (snapshot / "tokenizer_config.json").write_text("{}")

        notes = mod._validate_model_artifact_layout(
            model_identifier="org/legacy",
            snapshot_path=snapshot,
            tokenizer=object(),  # any non-None tokenizer enables the tokenizer check
        )

        expected = (
            "processor config missing from snapshot "
            "(preprocessor_config.json, processor_config.json)"
        )
        assert notes == (expected,)

    def test_layout_validator_reports_tokenizer_and_processor_gaps(
        self, mod: types.ModuleType, tmp_path: Path
    ) -> None:
        """Both artifact families are reported when both are absent."""
        snapshot = tmp_path / "snapshot"
        snapshot.mkdir()

        notes = mod._validate_model_artifact_layout(
            model_identifier="org/bare",
            snapshot_path=snapshot,
            tokenizer=object(),
        )

        assert len(notes) == 2
        assert notes[0].startswith("tokenizer artifacts missing from snapshot")
        assert notes[1].startswith("processor config missing from snapshot")

    def test_layout_validator_is_silent_for_complete_snapshot(
        self, mod: types.ModuleType, tmp_path: Path
    ) -> None:
        """A snapshot with a processor config and tokenizer yields no notes."""
        snapshot = tmp_path / "snapshot"
        snapshot.mkdir()
        (snapshot / "tokenizer.json").write_text("{}")
        (snapshot / "preprocessor_config.json").write_text("{}")

        assert (
            mod._validate_model_artifact_layout(
                model_identifier="org/modern",
                snapshot_path=snapshot,
                tokenizer=object(),
            )
            == ()
        )

    def test_layout_validator_returns_empty_without_snapshot(self, mod: types.ModuleType) -> None:
        """No snapshot on disk means nothing to note."""
        assert (
            mod._validate_model_artifact_layout(
                model_identifier="org/uncached",
                snapshot_path=None,
                tokenizer=None,
            )
            == ()
        )

    def test_snapshot_notes_round_trip_prompt_diagnostics_json(self, mod: types.ModuleType) -> None:
        """Notes are serialised into the per-model JSONL prompt diagnostics."""
        diagnostics = mod.PromptDiagnostics(
            snapshot_notes=("processor config missing from snapshot (x.json)",),
        )

        payload = mod._prompt_diagnostics_to_json(diagnostics)

        assert payload["snapshot_notes"] == ["processor config missing from snapshot (x.json)"]
        assert "snapshot_notes" not in mod._prompt_diagnostics_to_json(mod.PromptDiagnostics())

    def test_snapshot_notes_never_become_observations(self, mod: types.ModuleType) -> None:
        """Notes are evidence only: a clean answer with notes stays usable."""
        diagnostics = mod.PromptDiagnostics(
            snapshot_notes=("processor config missing from snapshot (x.json)",),
        )

        class _Gen:
            text = "A cat sits on a wall under a clear sky."
            generation_tokens = 40
            prompt_tokens = 300

        result = mod.PerformanceResult(
            model_name="org/legacy",
            generation=_Gen(),
            success=True,
            prompt_diagnostics=diagnostics,
        )
        result = mod._populate_result_quality_analysis(result, prompt=None)

        assessment = mod._assess_result(result)

        assert assessment.observations == ()
        assert assessment.usability == "usable"
