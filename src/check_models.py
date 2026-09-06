#!/usr/bin/env python3
"""Image analysis and caption generation using MLX Vision Language Models.

Assesses locally-cached Hugging Face VLMs (via mlx-vlm) for image-metadata
generation quality and produces maintainer-ready diagnostics for mlx-vlm,
mlx, and transformers. Intentionally a single-file monolith; navigate with
the ``SECTION:`` banner landmarks (documented in
``.github/copilot-instructions.md`` §3).

Architecture at a glance:

- **Report-block AST** (``ReportSection``/``ReportTable``/``ReportDetails``/
  ``ReportModelOutput`` etc., near ``render_report_markdown`` /
  ``render_report_html``): one typed block tree rendered to both Markdown and
  HTML so paired report surfaces cannot drift.
- **Observation registry** (``_OBSERVATION_DISPLAY_SPECS``): every mechanical
  output observation (repetition, thinking-trace issues, token leakage,
  catalog-contract violations, ...) is declared once with its code, label,
  and usability impact; ``_assess_result`` projects results onto it. There is
  deliberately no semantic scoring — only reproducible mechanical facts.
- **Artifact fan-out** (``_build_report_artifacts`` /
  ``finalize_execution``): one run emits the console dashboard plus
  ``index.md`` (dashboard + links), ``reports/results.html``,
  ``reports/model_gallery.md``, ``reports/diagnostics.md``,
  ``results.jsonl`` (the sole machine contract, schema 3.0: run-level
  metadata header plus per-model rows), append-only
  ``results.history.jsonl``, and paste-ready issue drafts under ``issues/``.
  The run-issue summary re-reads validated ``results.jsonl`` rather than
  trusting in-memory state.
- **Discovery** mirrors mlx-vlm's server ``/v1/models`` cache filter
  (``get_cached_model_ids``) and adds an architecture pre-check against the
  installed ``mlx_vlm/models`` packages (``_model_arch_precheck``).
"""

from __future__ import annotations

# =============================================================================
# SECTION: IMPORTS, CONFIG & OPTIONAL DEPENDENCY GUARDS
# =============================================================================
import argparse
import ast
import base64
import codecs
import functools
import gc
import hashlib
import html
import inspect
import io
import json
import logging
import math
import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import tomllib
import traceback
import types
from collections import Counter
from collections.abc import Callable, Generator, Iterable, Iterator, Mapping, Sequence, Sized
from contextlib import (
    ContextDecorator,
    ExitStack,
    contextmanager,
    nullcontext,
    redirect_stderr,
    redirect_stdout,
    suppress,
)
from dataclasses import dataclass, fields, is_dataclass, replace
from dataclasses import field as dataclass_field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import lru_cache, partial
from importlib import import_module
from importlib.metadata import (
    Distribution,
    PackageNotFoundError,
    distribution,
    distributions,
    version,
)
from importlib.resources import as_file, files
from importlib.util import find_spec
from pathlib import Path, PurePosixPath
from shlex import join as shlex_join
from statistics import median
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal,
    NamedTuple,
    NoReturn,
    NotRequired,
    Protocol,
    Required,
    Self,
    TextIO,
    TypedDict,
    TypeGuard,
    TypeIs,
    Union,
    Unpack,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)
from urllib.error import URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

import yaml
from huggingface_hub import HFCacheInfo, scan_cache_dir
from huggingface_hub import __version__ as hf_version
from huggingface_hub.errors import HFValidationError
from packaging.version import InvalidVersion, Version
from rich import box
from rich.bar import Bar
from rich.cells import cell_len
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from check_models_data.dependency_policy import (
    PROJECT_MIN_TRANSFORMERS_VERSION,
    PROJECT_RUNTIME_STACK_MINIMUMS,
    UPSTREAM_MLX_VLM_MINIMUMS,
)

# Optional dependency: psutil for system info; degrade gracefully if missing.
# Keep a nullable module binding so downstream checks can stay simple.
psutil: Any | None
try:
    import psutil as _psutil_runtime
except ImportError:  # pragma: no cover - optional
    psutil = None
else:
    psutil = _psutil_runtime


if TYPE_CHECKING:
    from mlx import nn
    from mlx_vlm.generate import GenerationResult
    from mlx_vlm.generate.types import GenerateKwargs, ProcessorLike
    from PIL.Image import Image as PILImage
    from transformers import PreTrainedTokenizer
    from transformers.configuration_utils import PreTrainedConfig
    from transformers.processing_utils import ProcessorMixin
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase

# Public API (PEP 8 / PEP 561 best practice)
__all__ = [
    "EXIF_NOT_EXTRACTED",
    "GenerationQualityAnalysis",
    "PerformanceResult",
    "ProcessImageParams",
    "ResultSet",
    "analyze_generation_text",
    "append_history_record",
    "exit_with_cli_error",
    "extract_image_metadata",
    "find_most_recent_file",
    "format_field_label",
    "format_field_value",
    "format_overall_runtime",
    "generate_diagnostics_report",
    "generate_html_report",
    "generate_output_index_report",
    "get_device_info",
    "get_exif_data",
    "get_library_versions",
    "get_system_characteristics",
    "get_system_info",
    "get_terminal_width",
    "log_blank",
    "log_failure",
    "log_file_path",
    "log_generated_text",
    "log_metric_label",
    "log_model_name",
    "log_success",
    "log_warning_note",
    "main",
    "main_cli",
    "pretty_print_exif",
    "print_cli_error",
    "print_cli_header",
    "print_cli_section",
    "print_model_result",
    "print_version_info",
    "process_image_with_model",
    "validate_cli_arguments",
    "validate_image_accessible",
    "validate_inputs",
    "validate_kv_params",
    "validate_sampling_params",
    "validate_temperature",
]

# =============================================================================
# MODULE CONSTANTS
# =============================================================================

LOGGER_NAME: Final[str] = "mlx-vlm-check"
logger: logging.Logger = logging.getLogger(LOGGER_NAME)
NOT_AVAILABLE: Final[str] = "N/A"
# Shared by the triage evaluation lane and differential reruns; the rerun path
# applies its own tighter RERUN_TRIAGE_MAX_TOKENS cap.
TRIAGE_PROMPT: Final[str] = "Describe this image briefly."
HTML_UNESCAPED_AMPERSAND_RE: Final[re.Pattern[str]] = re.compile(
    r"&(?!lt;|gt;|amp;|#)",
)
# MD037 included: verbatim model-output previews may contain emphasis-like
# sequences (e.g. "*   bullet" reasoning text) that must not be edited.
MARKDOWNLINT_GALLERY_SUMMARY_RULES: Final[str] = "MD034 MD037 MD049"
MARKDOWNLINT_TABLE_PIPE_RULES: Final[str] = "MD060"

MISSING_DEPENDENCIES: dict[str, str] = {}

ERROR_MLX_MISSING: Final[str] = "Core dependency missing: mlx. Please install it."
ERROR_MLX_RUNTIME_INIT: Final[str] = (
    "Core dependency initialization failed: mlx runtime could not initialize Metal."
)
ERROR_PILLOW_MISSING: Final[str] = (
    "Error: Pillow not found. Please install it (`pip install Pillow`)."
)
ERROR_MLX_VLM_MISSING: Final[str] = (
    "Error: mlx-vlm not found. Please install it (`pip install mlx-vlm`)."
)
ERROR_MLX_VLM_RUNTIME_INIT: Final[str] = (
    "Core dependency initialization failed: mlx-vlm could not be imported safely."
)
ISOLATED_WORKER_FLAG: Final[str] = "--isolated-worker"
ISOLATION_CRASH_TEST_ENV: Final[str] = "CHECK_MODELS_ISOLATION_CRASH_MODEL"
# Set to "1" to skip the subprocess import probes that shield a long-lived
# parent from a hard-crashing dependency import. The test suite sets it: every
# worker already imports mlx-vlm in-process, so the probe only adds ~2 s of
# start-up per worker (and contention-driven timeouts) without protecting it.
IMPORT_PROBE_SKIP_ENV: Final[str] = "CHECK_MODELS_SKIP_IMPORT_PROBE"
MLX_IMPORT_PROBE_TIMEOUT_SECONDS: Final[float] = 8.0
IMPORT_PROBE_OUTPUT_EXCERPT_CHARS: Final[int] = 220
IMPORT_PROBE_MIN_TAIL_CHARS: Final[int] = 10
DEFAULT_KV_QUANT_SCHEME: Final = "uniform"
DEFAULT_KV_GROUP_SIZE: Final[int] = 64
DEFAULT_QUANTIZED_KV_START: Final[int] = 5000
UNIFORM_KV_BITS: Final[frozenset[int]] = frozenset({2, 3, 4, 5, 6, 8})
DEFAULT_PENALTY_CONTEXT_SIZE: Final[int] = 20


class ThinkingDelimiterPair(NamedTuple):
    """One recognised thinking-trace wrapper and its empty-wrapper policy.

    ``reports_when_empty`` decides what an *empty* generated wrapper means:
    ``False`` for pairs that chat templates legitimately seed when thinking is
    disabled (flagging them would false-positive every non-thinking run), and
    ``True`` for transport syntax that has no business in final text, where an
    empty wrapper is still unconsumed control-token leakage. Every pair added
    here must choose explicitly; the policy is asserted in tests.
    """

    start: str
    end: str
    reports_when_empty: bool = False
    # ``auto_budget_eligible`` separates pairs that are safe to hand to
    # upstream's ThinkingBudgetCriteria for automatic budgeting (single-token
    # start/end markers that templates open) from pairs recognised only as
    # output evidence. Transport-syntax pairs stay evidence-only: forcing a
    # closing sequence there would inject control tokens into final text.
    auto_budget_eligible: bool = True


THINKING_TRACE_DELIMITERS: Final[tuple[ThinkingDelimiterPair, ...]] = (
    ThinkingDelimiterPair("<think>", "</think>"),
    ThinkingDelimiterPair("◁think▷", "◁/think▷"),
    # Marker pairs recognised by mlx-vlm's server-side thinking splitter
    # (mlx_vlm/server/responses_state.py ThinkingStreamState defaults).
    ThinkingDelimiterPair(
        "<|channel>thought",
        "<channel|>",
        reports_when_empty=True,
        auto_budget_eligible=False,
    ),
    ThinkingDelimiterPair("<|START_THINKING|>", "<|END_THINKING|>"),
)
DEFAULT_THINKING_END_MARKER: Final[str] = THINKING_TRACE_DELIMITERS[0].end
# Auto thinking budget: reserve answer headroom below the token cap, and skip
# the mechanism entirely when the cap leaves too little room to think at all.
AUTO_THINKING_ANSWER_RESERVE_TOKENS: Final[int] = 200
AUTO_THINKING_BUDGET_MIN_TOKENS: Final[int] = 128
THINKING_TRACE_DELIMITER_PAIRS: Final[tuple[tuple[str, str], ...]] = tuple(
    (pair.start, pair.end) for pair in THINKING_TRACE_DELIMITERS
)
_REPORTING_EMPTY_WRAPPER_PATTERNS: Final[
    tuple[tuple[ThinkingDelimiterPair, re.Pattern[str]], ...]
] = tuple(
    (pair, re.compile(rf"{re.escape(pair.start)}\s*{re.escape(pair.end)}", re.IGNORECASE))
    for pair in THINKING_TRACE_DELIMITERS
    if pair.reports_when_empty
)
MAX_SAFE_TEXT_FILE_BYTES: Final[int] = 16 * 1024 * 1024
# Artifact schema versions. Three distinct schemas; writers and readers must
# reference these constants, never bare "2.0"/"1.0" literals.
JSONL_FORMAT_VERSION: Final = "3.0"
HISTORY_FORMAT_VERSION: Final = "1.0"
SAFE_TEXT_FILE_READ_CHUNK_BYTES: Final[int] = 64 * 1024
MAX_DISTRIBUTION_TEXT_FILE_BYTES: Final[int] = 64 * 1024
ROOT_PATH: Final[Path] = Path(os.sep)
ALLOWED_SYSTEM_SYMLINK_PARENTS: Final[dict[Path, Path]] = {
    ROOT_PATH / "tmp": ROOT_PATH / "private" / "tmp",
    ROOT_PATH / "var": ROOT_PATH / "private" / "var",
}
DISTRIBUTION_DIRECT_URL_METADATA_FILE: Final[str] = "direct_url.json"
ALLOWED_DISTRIBUTION_TEXT_FILES: Final[frozenset[str]] = frozenset(
    {DISTRIBUTION_DIRECT_URL_METADATA_FILE},
)


def _is_allowed_system_symlink_parent(path: Path) -> bool:
    """Return true for trusted macOS root aliases such as /var."""
    expected_target = ALLOWED_SYSTEM_SYMLINK_PARENTS.get(path)
    if expected_target is None:
        return False
    try:
        return path.resolve(strict=True) == expected_target
    except OSError:
        return False


def _reject_symlink_parent(path: Path) -> None:
    """Reject symlinked parent directories before artifact file I/O."""
    for parent in (path.parent, *path.parent.parents):
        if parent.is_symlink() and not _is_allowed_system_symlink_parent(parent):
            msg = f"Refusing to access file through symlinked directory: {parent}"
            raise OSError(msg)


def _canonical_file_path(path: Path) -> Path:
    """Resolve existing parent links without following the final artifact path."""
    return path.parent.resolve(strict=False) / path.name


def _open_regular_file_no_symlink(path: Path, flags: int, mode: int = 0o666) -> int:
    """Open a regular file descriptor without following final symlinks."""
    if path.is_symlink():
        msg = f"Refusing to follow symlink: {path}"
        raise OSError(msg)

    fd = os.open(  # skylos: ignore[SKY-D215] local CLI output path, guarded below.
        path,
        flags | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        file_stat = os.fstat(fd)
    except OSError:
        os.close(fd)
        raise
    if not stat.S_ISREG(file_stat.st_mode):
        os.close(fd)
        msg = f"Refusing to access non-regular file: {path}"
        raise OSError(msg)
    return fd


def _write_bytes_file(path: Path, content: bytes, *, append: bool = False) -> None:
    """Write bytes to a regular file without following symlinks."""
    _reject_symlink_parent(path)
    path = _canonical_file_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_parent(path)

    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
    fd = _open_regular_file_no_symlink(path, flags)
    with os.fdopen(fd, "ab") as handle:
        handle.write(content)


def _write_text_file(path: Path, content: str, *, append: bool = False) -> None:
    """Write UTF-8 text to a regular file without following symlinks."""
    _write_bytes_file(path, content.encode("utf-8"), append=append)


def _read_text_file(path: Path, *, max_bytes: int = MAX_SAFE_TEXT_FILE_BYTES) -> str:
    """Read UTF-8 text from a regular file with a byte-size cap."""
    _reject_symlink_parent(path)
    path = _canonical_file_path(path)
    _reject_symlink_parent(path)
    fd = _open_regular_file_no_symlink(path, os.O_RDONLY)
    try:
        file_size = os.fstat(fd).st_size
    except OSError:
        os.close(fd)
        raise
    if file_size > max_bytes:
        os.close(fd)
        msg = f"Refusing to read {path}: file size {file_size} exceeds {max_bytes} bytes"
        raise OSError(msg)

    chunks: list[bytes] = []
    remaining = max_bytes + 1
    try:
        while remaining > 0:
            chunk = os.read(  # skylos: ignore[SKY-P401] bounded by max_bytes.
                fd,
                min(remaining, SAFE_TEXT_FILE_READ_CHUNK_BYTES),
            )
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(fd)
    data = b"".join(chunks)
    if len(data) > max_bytes:
        msg = f"Refusing to read {path}: content exceeds {max_bytes} bytes"
        raise OSError(msg)
    return data.decode("utf-8")


# =============================================================================
# CONFIGURATION DATACLASSES - Centralized thresholds and constants
# =============================================================================


@dataclass(frozen=True)
class FormattingThresholds:
    """Centralized thresholds for number/memory/token formatting.

    Consolidates magic numbers used throughout formatting functions to
    improve maintainability and make threshold tuning easier.
    """

    # Number formatting thresholds
    large_number: float = 100.0  # Format as integer with commas
    medium_number: float = 10.0  # One decimal place for TPS
    thousand_separator: int = 1_000  # Add comma separators

    # Memory formatting thresholds
    memory_gb_integer: float = 10.0  # Show GB as integer (no decimals)

    # Time formatting thresholds

    # Dry-run output thresholds
    max_prompt_preview_lines: int = 10  # Max lines to show in prompt preview

    # Layout constants
    min_separator_chars: int = 50
    markdown_hard_break_spaces: int = 2
    markdown_wrap_width: int = 78
    generation_wrap_width: int = 100
    revision_preview_chars: int = 12


@dataclass(frozen=True)
class QualityThresholds:
    """Thresholds for retained mechanical output observations."""

    repetition_ratio: float = 0.9
    min_text_length: int = 10
    min_token_count: int = 5
    min_phrase_repetitions: int = 3
    max_phrase_repetitions: int = 10
    phrase_coverage_threshold: float = 0.4
    min_phrase_length: int = 4
    max_phrase_length: int = 10
    min_catalog_keywords_for_repeat: int = 10
    min_catalog_keyword_repetitions: int = 3
    catalog_keyword_duplicate_ratio: float = 0.4
    long_prompt_tokens_threshold: int = 3000
    heavy_nontext_prompt_ratio: float = 0.5
    mixed_prompt_burden_ratio_floor: float = 0.25
    prompt_title_max_chars: int = 120
    prompt_description_max_chars: int = 420
    prompt_keyword_max_items: int = 20
    prompt_word_to_token_ratio: float = 1.3
    cutoff_tail_chars: int = 120

    def __post_init__(self) -> None:
        """Validate the retained detector thresholds."""
        unit_interval_fields = {
            "repetition_ratio": self.repetition_ratio,
            "phrase_coverage_threshold": self.phrase_coverage_threshold,
            "catalog_keyword_duplicate_ratio": self.catalog_keyword_duplicate_ratio,
            "heavy_nontext_prompt_ratio": self.heavy_nontext_prompt_ratio,
            "mixed_prompt_burden_ratio_floor": self.mixed_prompt_burden_ratio_floor,
        }
        for field_name, value in unit_interval_fields.items():
            if not 0.0 <= value <= 1.0:
                msg = (
                    f"quality_config.yaml thresholds.{field_name} must be between 0 and 1; "
                    f"got {value}"
                )
                raise ValueError(msg)
        if self.min_phrase_repetitions > self.max_phrase_repetitions:
            msg = (
                "quality_config.yaml has invalid phrase repetitions bounds: "
                f"min={self.min_phrase_repetitions}, max={self.max_phrase_repetitions}"
            )
            raise ValueError(msg)

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> QualityThresholds:
        """Create an instance from the packaged configuration mapping."""
        thresholds = _require_str_object_mapping(
            config.get("thresholds", {}),
            "quality_config.yaml thresholds section must be a mapping",
        )
        valid_fields = {field.name for field in fields(cls)}
        filtered_thresholds = {
            key: value for key, value in thresholds.items() if key in valid_fields
        }
        unknown_threshold_keys = set(thresholds) - valid_fields
        if unknown_threshold_keys:
            logger.warning(
                "Unrecognised keys in quality_config.yaml thresholds (ignored): %s",
                ", ".join(sorted(unknown_threshold_keys)),
            )
        unknown_sections = set(config) - {"thresholds"}
        if unknown_sections:
            logger.warning(
                "Unrecognised top-level sections in quality_config.yaml (ignored): %s",
                ", ".join(sorted(unknown_sections)),
            )
        return cls(**cast("dict[str, Any]", filtered_thresholds))


# Instantiate singletons for runtime use
FORMATTING = FormattingThresholds()
# Default QUALITY instance (will be updated if config is loaded)
QUALITY = QualityThresholds()


def load_quality_config(config_path: Path | None = None) -> None:
    """Load quality configuration from file and update global QUALITY instance.

    If no config_path is provided, loads the bundled default quality config
    resource shipped with the distribution.
    """
    with ExitStack() as exit_stack:
        if config_path is None:
            with suppress(FileNotFoundError, ModuleNotFoundError):
                resource = files("check_models_data").joinpath(
                    "quality_config.yaml",
                )
                config_path = exit_stack.enter_context(as_file(resource))
            if config_path is None:
                logger.warning(
                    "Bundled quality config resource not found: check_models_data/quality_config.yaml",
                )
                return
        elif not config_path.exists():
            logger.warning("Quality config file not found: %s", config_path)
            return

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config is None:
                    return
                config_mapping = _require_str_object_mapping(
                    config,
                    "quality_config.yaml top-level document must be a mapping",
                )
                new_quality = QualityThresholds.from_config(config_mapping)
                global QUALITY  # noqa: PLW0603 - single rebinding point for the config-loaded thresholds
                QUALITY = new_quality
                logger.debug("Loaded quality configuration from %s", config_path)
        except (OSError, TypeError, ValueError, yaml.YAMLError) as e:
            logger.warning("Failed to load quality config from %s: %s", config_path, e)


def _format_import_probe_output_excerpt(
    output: str,
    *,
    max_output_excerpt_chars: int = IMPORT_PROBE_OUTPUT_EXCERPT_CHARS,
) -> str:
    """Return a compact import-probe excerpt that preserves the terminal exception."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "no output"

    normalized = " ".join(output.split())
    if len(normalized) <= max_output_excerpt_chars:
        return normalized

    exception_line: str | None = None
    for line in reversed(lines):
        if re.match(r"^[A-Za-z_][\w.]*(?:Error|Exception):\s", line):
            exception_line = line
            break

    if exception_line is None:
        return f"{normalized[: max_output_excerpt_chars - 3]}..."

    candidate = f"{lines[0]} ... {exception_line}"
    if len(candidate) <= max_output_excerpt_chars:
        return candidate

    tail_budget = max_output_excerpt_chars - len(f"{lines[0]} ... ")
    if tail_budget <= IMPORT_PROBE_MIN_TAIL_CHARS:
        return f"{exception_line[: max_output_excerpt_chars - 3]}..."
    return f"{lines[0]} ... {exception_line[: tail_budget - 3]}..."


def _probe_import_runtime(
    *,
    import_target: str,
    error_prefix: str,
    detect_metal_nsrange: bool = False,
) -> str | None:
    """Run a subprocess import probe and return an actionable error message when it fails.

    Skipped inside an ``--isolate`` worker: the probe exists to shield the
    long-lived parent from a hard-crashing dependency, and a worker is already
    the crash boundary. A probe that merely *times out* is inconclusive, not a
    failure: under load (many test workers probing at once, a busy machine)
    the import finishes after the deadline, and treating that as "unavailable"
    produced false negatives both in real runs and in the parallel test suite.
    """
    inside_isolated_worker = len(sys.argv) >= 2 and sys.argv[1] == ISOLATED_WORKER_FLAG  # noqa: PLR2004 - argv[0] + flag
    if inside_isolated_worker or os.environ.get(IMPORT_PROBE_SKIP_ENV) == "1":
        return None
    try:
        probe_result = subprocess.run(  # noqa: S603 - fixed interpreter + fixed probe command
            [sys.executable, "-c", f"import {import_target}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=MLX_IMPORT_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "Import probe for %s timed out after %.0fs; treating it as inconclusive and "
            "importing in-process.",
            import_target,
            MLX_IMPORT_PROBE_TIMEOUT_SECONDS,
        )
        return None
    except OSError as probe_err:
        return f"{error_prefix} Import probe failed: {probe_err}"

    if probe_result.returncode == 0:
        return None

    combined_output = probe_result.stderr.strip() or probe_result.stdout.strip()

    if detect_metal_nsrange:
        combined_lower = combined_output.lower()
        if "nsrangeexception" in combined_lower and "objectatindex" in combined_lower:
            return (
                f"{error_prefix} No Metal device could be enumerated "
                "(NSRangeException during device discovery). This commonly happens in "
                "headless or virtualized sessions without visible Apple GPU access."
            )

    output_excerpt = _format_import_probe_output_excerpt(combined_output)
    return (
        f"{error_prefix} Import probe exited with code "
        f"{probe_result.returncode}. Probe output: {output_excerpt}"
    )


mx: Any = cast("Any", None)
mlx_probe_error = _probe_import_runtime(
    import_target="mlx.core",
    error_prefix=ERROR_MLX_RUNTIME_INIT,
    detect_metal_nsrange=True,
)
if mlx_probe_error is None:
    try:
        _mx_runtime = import_module("mlx.core")
    except ImportError:
        MISSING_DEPENDENCIES["mlx"] = ERROR_MLX_MISSING
    except (OSError, RuntimeError, ValueError) as mlx_init_err:
        MISSING_DEPENDENCIES["mlx"] = f"{ERROR_MLX_RUNTIME_INIT} {mlx_init_err}"
    else:
        mx = cast("Any", _mx_runtime)
else:
    MISSING_DEPENDENCIES["mlx"] = mlx_probe_error

ExifTags: SupportsExifTagsModule
GPSTAGS: Mapping[int, str]
TAGS: Mapping[int, str]
UnidentifiedImageError: type[Exception]
GPS: SupportsGPSEnum | None

try:
    from PIL import Image, ImageOps
    from PIL import UnidentifiedImageError as _PILUnidentifiedImageError

    UnidentifiedImageError = _PILUnidentifiedImageError
except ImportError:
    pillow_version = NOT_AVAILABLE

    class _PILUnavailableError(RuntimeError):
        """Raised when Pillow functionality is requested but unavailable."""

    class _ImageUnavailable:
        """Stub for PIL.Image that raises informative errors when used."""

        @staticmethod
        def open(*_args: object, **_kwargs: object) -> NoReturn:
            raise _PILUnavailableError(ERROR_PILLOW_MISSING)

    class _ExifTagsUnavailable:
        """Stub that surfaces a clear error if EXIF helpers are accessed."""

        def __getattr__(self, _name: str) -> NoReturn:
            raise _PILUnavailableError(ERROR_PILLOW_MISSING)

    ExifTags = cast("SupportsExifTagsModule", _ExifTagsUnavailable())
    Image = cast("Any", _ImageUnavailable())
    ImageOps = cast("Any", _ImageUnavailable())
    UnidentifiedImageError = _PILUnavailableError
    GPS = None
    GPSTAGS = cast("Mapping[int, str]", {})
    TAGS = cast("Mapping[int, str]", {})
    MISSING_DEPENDENCIES["Pillow"] = ERROR_PILLOW_MISSING
else:
    from PIL import ExifTags as PIL_ExifTags
    from PIL import IptcImagePlugin
    from PIL.ExifTags import GPS as PIL_GPS
    from PIL.ExifTags import GPSTAGS as PIL_GPSTAGS
    from PIL.ExifTags import TAGS as PIL_TAGS

    pillow_version = Image.__version__ if hasattr(Image, "__version__") else NOT_AVAILABLE
    ExifTags = cast("SupportsExifTagsModule", PIL_ExifTags)
    GPS = cast("SupportsGPSEnum", PIL_GPS)
    GPSTAGS = cast("Mapping[int, str]", PIL_GPSTAGS)
    TAGS = cast("Mapping[int, str]", PIL_TAGS)

# defusedxml is required by Pillow's Image.getxmp() for safe XMP/XML parsing.
# Declared explicitly in pyproject.toml even though Pillow[xmp] may also pull it
# transitively, so _extract_xmp_metadata() fails clearly if the environment drifts.
# Bound as a nullable module (same pattern as psutil above) so the dependency's
# use is a real reference — visible to static dependency scanners with no lint
# suppression — while Pillow still performs the actual parsing.
defusedxml_etree: types.ModuleType | None
try:
    import defusedxml.ElementTree as _DefusedElementTree
except ImportError:  # pragma: no cover - optional
    defusedxml_etree = None
else:
    defusedxml_etree = _DefusedElementTree
_defusedxml_available = defusedxml_etree is not None
if not _defusedxml_available:
    logger.warning(
        "defusedxml not installed — XMP metadata extraction will be disabled. "
        "Install with: pip install defusedxml",
    )

try:
    import numpy as np

    numpy_version: str = getattr(np, "__version__", NOT_AVAILABLE)
except ImportError:
    numpy_version = NOT_AVAILABLE


def _raise_mlx_vlm_missing(*_args: object, **_kwargs: object) -> NoReturn:
    """Raise a consistent runtime error when mlx-vlm is unavailable."""
    raise RuntimeError(ERROR_MLX_VLM_MISSING)


vlm_version: str = NOT_AVAILABLE
stream_generate: Callable[..., Iterator[GenerationResult]] = cast(
    "Callable[..., Iterator[GenerationResult]]", _raise_mlx_vlm_missing
)
apply_chat_template: ApplyChatTemplateCallable = cast(
    "ApplyChatTemplateCallable", _raise_mlx_vlm_missing
)
load: LoadCallable = cast("LoadCallable", _raise_mlx_vlm_missing)
load_image: LoadImageCallable = cast("LoadImageCallable", _raise_mlx_vlm_missing)


mlx_vlm_probe_error = _probe_import_runtime(
    import_target="mlx_vlm",
    error_prefix=ERROR_MLX_VLM_RUNTIME_INIT,
)
if mlx_vlm_probe_error is None:
    try:
        from mlx_vlm.generate import stream_generate as _mlx_vlm_stream_generate
        from mlx_vlm.prompt_utils import apply_chat_template as _mlx_vlm_apply_chat_template
        from mlx_vlm.utils import load as _mlx_vlm_load
        from mlx_vlm.utils import load_image as _mlx_vlm_load_image
        from mlx_vlm.version import __version__ as _mlx_vlm_version

        def _typed_mlx_vlm_load(
            path_or_hf_repo: str,
            adapter_path: str | None = None,
            lazy: bool = False,
            revision: str | None = None,
            strict: bool = True,
            *,
            trust_remote_code: bool = True,
            **kwargs: object,
        ) -> tuple[nn.Module, ProcessorMixin]:
            loaded: tuple[nn.Module, ProcessorMixin] = _mlx_vlm_load(
                path_or_hf_repo=path_or_hf_repo,
                adapter_path=adapter_path,
                lazy=lazy,
                revision=revision,
                strict=strict,
                trust_remote_code=trust_remote_code,
                **kwargs,
            )
            return loaded

        stream_generate = cast(
            "Callable[..., Iterator[GenerationResult]]", _mlx_vlm_stream_generate
        )
        apply_chat_template = _mlx_vlm_apply_chat_template
        load = _typed_mlx_vlm_load
        load_image = _mlx_vlm_load_image
        vlm_version = _mlx_vlm_version
    except ImportError:
        MISSING_DEPENDENCIES["mlx-vlm"] = ERROR_MLX_VLM_MISSING
else:
    MISSING_DEPENDENCIES["mlx-vlm"] = mlx_vlm_probe_error

# =============================================================================
# SECTION: TYPE ALIASES, PROTOCOLS & JSONL RECORDS
# =============================================================================

type ExifValue = Any  # Pillow yields varied scalar / tuple EXIF types; keep permissive
type ExifDict = dict[str | int, ExifValue]
type MetadataDict = dict[str, str | None]
type PathLike = str | Path
type JsonLike = bool | int | float | str | list[JsonLike] | dict[str, JsonLike] | None
type LogitBiasDict = dict[int, float]
type GPSDict = dict[str, ExifValue]  # GPS EXIF data structure
type EvaluationLane = Literal["triage", "blind", "assisted"]
type AssessmentProfile = Literal["general", "metadata"]
type RequestedEvaluationMode = EvaluationLane | Literal["auto"]
type SystemProfilerEntry = dict[str, object]
type SystemProfilerDict = dict[
    str, list[SystemProfilerEntry]
]  # macOS system_profiler JSON structure
type LibraryVersionDict = dict[str, str | None]  # Library name to version mapping (optional values)
type MetricValue = int | float | str | bool | None  # Common scalar metric variants for metrics


class MlxDeviceInfo(TypedDict, total=False):
    """Validated subset of ``mx.device_info()`` used by reports."""

    device_name: str
    architecture: str
    memory_size: int
    max_recommended_working_set_size: int


class _ExifNotExtracted:
    """Sentinel for callers that already checked EXIF and found nothing."""


EXIF_NOT_EXTRACTED: Final[_ExifNotExtracted] = _ExifNotExtracted()
type ExifExtractionInput = ExifDict | _ExifNotExtracted | None


class IPTCMetadata(TypedDict, total=False):
    """Normalized IPTC metadata extracted from an image."""

    iptc_keywords: list[str]
    iptc_caption: str


class XMPMetadata(TypedDict, total=False):
    """Normalized XMP metadata extracted from an image."""

    xmp_keywords: list[str]
    xmp_description: str
    xmp_title: str


class SupportsExifBaseNamespace(Protocol):
    """Minimal subset of ``PIL.ExifTags.Base`` used by EXIF helpers."""

    ExifOffset: int
    GPSInfo: int


class SupportsExifIfdNamespace(Protocol):
    """Minimal subset of ``PIL.ExifTags.IFD`` used by EXIF helpers."""

    Exif: int
    GPSInfo: int


class SupportsExifTagsModule(Protocol):
    """Minimal subset of Pillow's ``ExifTags`` namespace used here."""

    Base: SupportsExifBaseNamespace
    IFD: SupportsExifIfdNamespace


class SupportsGPSName(Protocol):
    """Minimal GPS enum member surface used for tag-name lookup."""

    name: str


class SupportsGPSEnum(Protocol):
    """Callable enum-like surface for Pillow GPS tag lookup."""

    def __call__(self, value: int) -> SupportsGPSName:
        """Return the GPS enum member for a numeric tag id."""
        ...


class HistoryModelResultRecord(TypedDict):
    """Per-model factual execution, timing, and resource data in raw history."""

    success: bool
    resolved_revision: NotRequired[str | None]
    generation_settings: NotRequired[dict[str, JsonLike]]
    failure_phase: NotRequired[str | None]
    error_stage: NotRequired[str | None]
    error_type: NotRequired[str | None]
    error_package: NotRequired[str | None]
    error_code: NotRequired[str | None]
    error_signature: NotRequired[str | None]
    stop_reason: NotRequired[str | None]
    prompt_tokens: NotRequired[int | None]
    generation_tokens: NotRequired[int | None]
    total_tokens: NotRequired[int | None]
    generation_tps: NotRequired[float | None]
    peak_memory_gb: NotRequired[float | None]
    active_memory_gb: NotRequired[float | None]
    cache_memory_gb: NotRequired[float | None]
    post_cleanup_active_memory_gb: NotRequired[float | None]
    post_cleanup_cache_memory_gb: NotRequired[float | None]
    generation_time_s: NotRequired[float | None]
    model_load_time_s: NotRequired[float | None]
    total_time_s: NotRequired[float | None]


class HistoryRunRecord(TypedDict, total=False):
    """Append-only run record shape for ``*.history.jsonl``."""

    _type: Literal["run"]
    format_version: Literal["1.0"]
    timestamp: str
    prompt_hash: str
    prompt_preview: str
    image_path: str | None
    model_results: dict[str, HistoryModelResultRecord]
    system: dict[str, str]
    library_versions: LibraryVersionDict
    runtime_fingerprint: dict[str, RuntimeProbeResult]
    eval_mode: EvaluationLane
    comparison_fingerprint: str


class JsonlTimingRecord(TypedDict):
    """Timing fields emitted per result row in ``results.jsonl``."""

    generation_time_s: float | None
    model_load_time_s: float | None
    total_time_s: float | None
    input_validation_time_s: float | None
    prompt_prep_time_s: float | None
    cleanup_time_s: float | None
    first_token_latency_s: float | None
    stop_reason: str | None


class JsonlMetricsRecord(TypedDict, total=False):
    """Performance metrics emitted for successful generations."""

    prompt_tokens: int
    generation_tokens: int
    total_tokens: int
    prompt_tps: float
    generation_tps: float
    peak_memory_gb: float
    peak_memory_working_set_pct: float
    active_memory_gb: float
    cache_memory_gb: float
    model_load_active_memory_gb: float
    peak_memory_delta_gb: float
    post_cleanup_active_memory_gb: float
    post_cleanup_cache_memory_gb: float


type SystemTelemetryMode = Literal["snapshot", "continuous", "off"]


class SystemTelemetryRecord(TypedDict, total=False):
    """Thermal and memory-pressure facts sampled around/during one model run.

    ``mode`` is "snapshot" (one probe pair before load and one after cleanup,
    outside timed inference) or "continuous" (opt-in background sampling).
    Per-probe sample counts are recorded separately so an unavailable probe is
    distinguishable from a clean one.
    """

    mode: SystemTelemetryMode
    interval_s: float
    cpu_samples: int
    cpu_speed_limit_min_pct: float
    cpu_throttled_samples: int
    memory_samples: int
    memory_pressure_level_max: int
    memory_pressure_elevated_samples: int


type ExecutionStatus = Literal["completed", "crashed", "indeterminate"]
type ModelUsability = Literal["usable", "usable_with_caveats", "unusable", "not_evaluated"]
type MaintainerStatus = Literal[
    "actionable_failure",
    "observation_needs_reproduction",
    "none",
]
type ObservationCode = Literal[
    "empty_output",
    "minimal_output",
    "repeated_output",
    "repetition_abort",
    "final_answer_duplicated",
    "missing_final_answer",
    "missing_requested_sections",
    "token_cap_truncation",
    "prompt_instruction_echo",
    "unexpected_catalog_preamble",
    "unexpected_special_token",
    "configured_wrapper_present",
    "thinking_trace_present",
    "thinking_trace_incomplete",
    "role_boundary_token_present",
    "catalog_constraint_violation",
    "duplicate_keywords",
    "no_keyword_overlap",
    "draft_returned_unchanged",
]
type UpstreamBoundary = Literal["not_started", "load_started", "generation_started"]
type MlxMemoryGetterName = Literal["get_active_memory", "get_cache_memory"]


class RuntimeProbeResult(TypedDict, total=False):
    """Status of a single runtime capability probe."""

    status: Required[Literal["ok", "unavailable", "errored", "timed_out"]]
    detail: str


type ComponentInstallType = Literal["editable", "wheel", "source-tree", "unknown"]


class DirectUrlDirInfo(TypedDict, total=False):
    """PEP 610 directory-source details used by provenance collection."""

    editable: bool


class DirectUrlVcsInfo(TypedDict, total=False):
    """PEP 610 version-control details used by provenance collection."""

    vcs: str
    requested_revision: str
    commit_id: str


class DistributionDirectUrlRecord(TypedDict, total=False):
    """Relevant fields from an installed distribution's PEP 610 metadata."""

    url: str
    dir_info: DirectUrlDirInfo
    vcs_info: DirectUrlVcsInfo
    subdirectory: str


class ComponentProvenanceRecord(TypedDict):
    """Local installation identity for one runtime component."""

    version: str | None
    install_type: ComponentInstallType
    source_location: str | None
    source_revision: str | None
    direct_url: str | None
    vcs_revision: str | None


class CheckModelsProvenanceRecord(TypedDict):
    """Producer identity recorded in run-level artifacts."""

    name: Literal["check_models"]
    version: str
    git_revision: str | None
    install_type: Literal["editable", "installed", "source-tree", "unknown"]
    dirty: NotRequired[bool | None]


class JsonlMetadataRecord(TypedDict, total=False):
    """Schema-3 header row: the complete run context for ``results.jsonl``.

    The sole current-run machine contract; the former ``run.json`` fields
    live here, while per-model provenance and prompt-burden facts stay on
    each result row.
    """

    _type: Required[Literal["metadata"]]
    format_version: Required[Literal["3.0"]]
    prompt: Required[str]
    prompt_sha256: Required[str]
    system: Required[dict[str, str]]
    timestamp: Required[str]
    # Wall-clock start (the run's end is ``timestamp``); explicit so the run
    # window never depends on subtracting a duration from the end.
    started_at: NotRequired[str]
    total_runtime_seconds: Required[float]
    counts: Required[RunOutcomeCounts]
    artifacts: Required[dict[str, str]]
    producer: Required[CheckModelsProvenanceRecord]
    image: Required[RunImageRecord | None]
    generation_settings: Required[dict[str, JsonLike]]
    trust_remote_code: Required[bool]
    comparison: Required[dict[str, JsonLike] | None]
    cache_discovery: NotRequired[list[CacheDiscoveryEntryRecord]]
    library_versions: LibraryVersionDict
    runtime_fingerprint: dict[str, RuntimeProbeResult]
    eval_mode: EvaluationLane
    assessment_profile: NotRequired[AssessmentProfile]
    metadata_exposed_to_prompt: bool
    component_provenance: dict[str, ComponentProvenanceRecord]
    execution_mode: Literal["in_process", "isolated"]


class ModelProvenanceRecord(TypedDict):
    """Requested and locally resolved identity for one model snapshot."""

    model: str
    requested_revision: str | None
    resolved_revision: str | None
    snapshot_path: str | None
    revision_source: NotRequired[str]


class RunOutcomeCounts(TypedDict):
    """Mutually consistent execution totals shared by run-level reports."""

    models_attempted: int
    models_evaluated: int
    models_completed: int
    models_crashed: int
    models_indeterminate: int


class RunImageRecord(TypedDict):
    """Publication-safe source-image identity for a benchmark run."""

    name: str
    source_url: NotRequired[str]
    sha256: str | None
    size_bytes: int | None
    width: int | None
    height: int | None
    megapixels: float | None


class CacheDiscoveryEntryRecord(TypedDict):
    """One cached repo's default-discovery classification and decision."""

    repo_id: str
    selected: bool
    layout_supported: bool
    layout_reasons: list[str]
    capability_verdict: ImageCapabilityVerdict
    model_purpose: ModelPurposeClass
    capability_evidence: list[str]
    skip_reasons: list[str]
    thinking_template: NotRequired[bool | None]
    model_type: str | None
    arch_supported: bool | None


@dataclass(frozen=True)
class RetainedRun:
    """One validated in-memory retained run: metadata plus ordered results."""

    metadata: JsonlMetadataRecord
    results: tuple[JsonlResultRecord, ...]


class JsonlAssessmentRecord(TypedDict):
    """One current-run assessment attached to a JSONL result row."""

    execution: ExecutionStatus
    usability: ModelUsability
    maintainer_status: MaintainerStatus
    observations: list[ObservationCode]
    details: NotRequired[JsonlObservationDetailsRecord]
    profile: NotRequired[AssessmentProfile]


class JsonlObservationDetailsRecord(TypedDict, total=False):
    """Exact mechanical evidence behind compact observation codes."""

    missing_sections: list[str]
    repeated_fragment: str
    instruction_echo_fragments: list[str]
    unexpected_catalog_preamble: str
    unexpected_special_tokens: list[str]
    configured_generation_wrappers: list[str]
    thinking_trace_markers: list[str]
    role_boundary_tokens: list[str]
    title_word_count: int
    title_word_range: list[int]
    description_sentence_count: int
    description_sentence_range: list[int]
    keyword_count: int
    keyword_count_range: list[int]
    duplicate_keywords: list[str]
    token_cap_reasons: list[str]
    unchanged_draft_fields: list[str]
    duplicated_answer_separator: str


class JsonlFailureRecord(TypedDict, total=False):
    """Raw failure evidence retained for a non-completed model attempt."""

    phase: str | None
    stage: str | None
    code: str | None
    message: str | None
    exception_type: str | None
    exception_module: str | None
    package: str | None
    traceback: str | None
    exception_chain: list[dict[str, str]]


class JsonlArchitectureRecord(TypedDict):
    """Cached-config architecture pre-check versus the installed mlx-vlm."""

    model_type: str
    resolved_model_type: str
    supported_by_installed_mlx_vlm: bool


class JsonlResultRecord(TypedDict):
    """Narrow per-model row shape for ``results.jsonl`` output."""

    _type: Literal["result"]
    model: str
    timestamp: str
    assessment: JsonlAssessmentRecord
    generated_text: str
    captured_output_on_fail: str
    captured_upstream_output: NotRequired[str]
    failure: JsonlFailureRecord | None
    metrics: JsonlMetricsRecord
    timing: JsonlTimingRecord
    model_provenance: ModelProvenanceRecord
    prompt_diagnostics: dict[str, JsonLike] | None
    model_burden: NotRequired[dict[str, JsonLike]]
    prompt_burden: NotRequired[dict[str, JsonLike]]
    architecture: NotRequired[JsonlArchitectureRecord]
    system_telemetry: NotRequired[SystemTelemetryRecord]


@dataclass(frozen=True)
class RunIssueSummarySource:
    """Validated retained inputs for the paste-ready whole-run issue summary."""

    metadata: JsonlMetadataRecord
    results: tuple[JsonlResultRecord, ...]
    image: RunImageRecord | None = None
    generation_settings: tuple[tuple[str, str], ...] = ()
    trust_remote_code: bool | None = None
    producer: CheckModelsProvenanceRecord | None = None
    run_window: tuple[datetime, datetime] | None = None


type RuntimePhaseName = Literal[
    "model_load",
    "prompt_prep",
    "upstream_prefill_first_token",
    "input_preparation_and_decode",
    "decode",
    "cleanup",
]

# The failure/timer phase vocabulary. Producers (PhaseTimer, exception phase
# tags, preflight raisers) are typed against this so a misspelled phase is a
# type error, not a silently unclassifiable failure.
type FailurePhaseName = Literal[
    "input_validation",
    "import",
    "model_load",
    "processor_load",
    "tokenizer_load",
    "model_preflight",
    "prompt_prep",
    "prefill",
    "decode",
    "generation_before_first_token",
    "generation_after_first_token",
    "cleanup",
]


class RuntimeAnalysisSummary(TypedDict):
    """Aggregated runtime interpretation shared across report renderers."""

    dominant_phase: RuntimePhaseName
    dominant_phase_share: float
    dominant_phase_count: int
    measured_models: int
    interpretation: str
    next_action: str
    phase_totals: dict[RuntimePhaseName, float]
    dominant_counts: dict[RuntimePhaseName, int]
    termination_counts: dict[str, int]
    generation_total: float
    generation_models: int
    prefill_split_models: int
    validation_total: float
    validation_models: int
    first_token_latency_avg: float | None
    first_token_latency_min: float | None
    first_token_latency_max: float | None
    first_token_latency_models: int


@dataclass(frozen=True)
class DiagnosticsArtifacts:
    """Diagnostics artifacts emitted at the end of a run."""

    outcome_counts: RunOutcomeCounts | None = None
    diagnostics_written: bool = False
    issue_reports: Mapping[str, Path] = dataclass_field(default_factory=dict)
    run_issue_summary: Path | None = None


@dataclass(frozen=True)
class ReportOutputPaths:
    """Resolved final report and log output paths."""

    index: Path
    html: Path
    gallery_markdown: Path
    jsonl: Path
    diagnostics: Path
    log: Path
    environment: Path

    @classmethod
    def from_root(cls, root: Path) -> Self:
        """Derive the canonical retained layout from one output root."""
        root = root.expanduser().resolve()
        reports = root / "reports"
        return cls(
            index=root / DEFAULT_OUTPUT_INDEX.name,
            html=reports / DEFAULT_HTML_OUTPUT.name,
            gallery_markdown=reports / DEFAULT_GALLERY_MD_OUTPUT.name,
            jsonl=root / DEFAULT_JSONL_OUTPUT.name,
            diagnostics=reports / DEFAULT_DIAGNOSTICS_OUTPUT.name,
            log=root / DEFAULT_LOG_OUTPUT.name,
            environment=root / DEFAULT_ENV_OUTPUT.name,
        )


@dataclass(frozen=True)
class ReportGenerationInputs:
    """Inputs required to generate final report artifacts and log their paths."""

    results: list[PerformanceResult]
    library_versions: LibraryVersionDict
    prompt: str
    metadata: MetadataDict | None
    overall_time: float
    image_path: Path | None
    system_info: dict[str, str]
    report_context: ReportRenderContext
    output_paths: ReportOutputPaths
    run_args: argparse.Namespace | None = None
    model_revision: str | None = None
    trust_remote_code: bool = True
    runtime_fingerprint: dict[str, RuntimeProbeResult] | None = None
    comparison: RunComparison | None = None
    history_appended: bool = False
    started_at: str | None = None
    # Wall-clock epoch when the run began; lets the retained record and the
    # dashboard report end-to-end duration once report generation is done.
    overall_start_time: float | None = None


@dataclass(frozen=True)
class ReportArtifact:
    """One retained artifact: identity, presentation, and optional job."""

    key: str
    public_key: str
    label: str
    path: Path
    dashboard_label: str
    dashboard_purpose: str
    job: Callable[[], None] | None = None


@dataclass(frozen=True)
class ReportArtifactOutcome:
    """Observed outcome for one canonical or optional report artifact."""

    key: str
    path: Path
    succeeded: bool
    error_message: str | None = None


class ChatTemplateKwargs(TypedDict, total=False):
    """Supported optional kwargs forwarded to ``mlx_vlm.apply_chat_template``."""

    enable_thinking: bool
    thinking_budget: int
    thinking_end_token: str
    thinking_mode: str
    thinking_start_token: str


class LoadExtraKwargs(TypedDict, total=False):
    """Optional upstream load kwargs this CLI forwards explicitly."""

    force_download: bool
    quantize_activations: bool


class SupportsTextDecoder(Protocol):
    """Minimal tokenizer/processor decode interface used by preflight checks."""

    def decode(self, *args: object, **kwargs: object) -> object:
        """Decode one token sequence."""
        del args, kwargs
        raise NotImplementedError

    def batch_decode(self, *args: object, **kwargs: object) -> object:
        """Decode one or more token sequences."""
        del args, kwargs
        raise NotImplementedError


class LoadCallable(Protocol):
    """Typed ``mlx_vlm.utils.load`` surface used by this script."""

    def __call__(
        self,
        path_or_hf_repo: str,
        adapter_path: str | None = None,
        lazy: bool = False,
        revision: str | None = None,
        strict: bool = True,
        *,
        trust_remote_code: bool = True,
        **kwargs: Unpack[LoadExtraKwargs],
    ) -> tuple[nn.Module, ProcessorMixin]:
        """Load an MLX-VLM model and processor."""
        del path_or_hf_repo, adapter_path, lazy, revision, strict, trust_remote_code, kwargs
        raise NotImplementedError


class ApplyChatTemplateCallable(Protocol):
    """Typed ``mlx_vlm.prompt_utils.apply_chat_template`` surface."""

    def __call__(
        self,
        processor: ProcessorMixin,
        config: Mapping[str, object] | object | None,
        prompt: str | dict[str, object] | list[object],
        add_generation_prompt: bool = True,
        return_messages: bool = False,
        num_images: int = 0,
        num_audios: int = 0,
        **kwargs: Unpack[ChatTemplateKwargs],
    ) -> str | list[dict[str, object]] | object:
        """Apply an upstream chat template to a prompt payload."""
        del processor, config, prompt
        del add_generation_prompt, return_messages, num_images, num_audios, kwargs
        raise NotImplementedError


class LoadImageCallable(Protocol):
    """Typed ``mlx_vlm.utils.load_image`` surface used for validation."""

    def __call__(self, image_source: str | Path | io.BytesIO, timeout: int = 10) -> object:
        """Load an image from a path or URL."""
        del image_source, timeout
        raise NotImplementedError


@runtime_checkable
class SupportsGenerationText(Protocol):
    """Minimal generation surface stored on ``PerformanceResult``.

    Report/test callers may pass lightweight stand-ins that only expose text
    plus a subset of numeric metrics. Consumers should use ``getattr`` or the
    helpers below when reading optional metrics from stored results.
    """

    @property
    def text(self) -> str | None:
        """Return generated text content when available."""
        ...


@runtime_checkable
class SupportsGenerationResult(SupportsGenerationText, Protocol):
    """Structural subset of live GenerationResult objects enriched locally.

    Using a Protocol keeps typing resilient to upstream changes in the
    concrete GenerationResult while still giving linters strong guarantees
    about the attributes actually consumed here.

    Note: `time`, `active_memory`, and `cache_memory` are added dynamically by
    our code after generation. `peak_memory` comes from the upstream
    GenerationResult returned by mlx-vlm.
    """

    token: object | None
    logprobs: object | None
    prompt_tokens: int | None
    generation_tokens: int | None
    total_tokens: int | None
    prompt_tps: float | None
    generation_tps: float | None
    time: float | None  # Dynamically added timing attribute
    active_memory: float | None  # Dynamically added active memory (GB)
    cache_memory: float | None  # Dynamically added cache memory (GB)
    model_load_active_memory: float | None  # Dynamically added post-load active memory (GB)
    peak_memory: float | None  # Upstream peak memory (GB)
    finish_reason: str | None  # Upstream stop/length termination classification


@dataclass(frozen=True)
class GenerationPerformanceData:
    """Normalized performance fields extracted from an upstream generation result."""

    prompt_tokens: int = 0
    generation_tokens: int = 0
    total_tokens: int = 0
    prompt_tps: float = 0.0
    generation_tps: float = 0.0
    peak_memory_gb: float = 0.0
    active_memory_gb: float = 0.0
    cache_memory_gb: float = 0.0
    generation_time_s: float | None = None
    # Upstream model-loop time until the first token; excludes prepare_inputs().
    first_token_latency_s: float | None = None
    finish_reason: str | None = None


class SupportsExifIfd(Protocol):
    """Minimal interface for EXIF objects providing nested IFD access."""

    def get_ifd(self, tag: object) -> Mapping[object, ExifValue] | None:
        """Retrieve a nested IFD mapping by tag identifier."""
        ...


type StoredGenerationResult = GenerationResult | SupportsGenerationText


def _generation_numeric_metric(generation: object | None, field_name: str) -> int | float | None:
    """Return an optional numeric generation metric when present."""
    value = getattr(generation, field_name, None)
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int | float) else None


def _generation_int_metric(generation: object | None, field_name: str) -> int | None:
    """Return an optional integer generation metric when present."""
    value = _generation_numeric_metric(generation, field_name)
    return value if isinstance(value, int) else None


def _generation_float_metric(generation: object | None, field_name: str) -> float | None:
    """Return an optional float generation metric when present."""
    value = _generation_numeric_metric(generation, field_name)
    return float(value) if value is not None else None


def _generation_text_value(generation: object | None) -> str:
    """Return generation text when available, else an empty string."""
    value = getattr(generation, "text", "")
    return value if isinstance(value, str) else ""


def _generation_nonnegative_int_metric(generation: object | None, field_name: str) -> int:
    """Return a non-negative integer generation metric, falling back to zero."""
    value = _generation_int_metric(generation, field_name)
    return value if value is not None and value >= 0 else 0


def _generation_nonnegative_float_metric(generation: object | None, field_name: str) -> float:
    """Return a non-negative float generation metric, falling back to zero."""
    value = _generation_float_metric(generation, field_name)
    return value if value is not None and value >= 0.0 else 0.0


def _generation_optional_nonnegative_float_metric(
    generation: object | None,
    field_name: str,
) -> float | None:
    """Return a non-negative optional float generation metric."""
    value = _generation_float_metric(generation, field_name)
    return value if value is not None and value >= 0.0 else None


def _object_model_load_active_memory_gb(source: object | None) -> float | None:
    """Return the locally attached post-model-load active memory baseline."""
    return _generation_optional_nonnegative_float_metric(source, _MODEL_LOAD_ACTIVE_MEMORY_ATTR)


def _extract_generation_performance_data(
    generation: object | None,
) -> GenerationPerformanceData:
    """Extract the latest mlx-vlm GenerationResult diagnostics in one place."""
    prompt_tokens = _generation_nonnegative_int_metric(generation, "prompt_tokens")
    generation_tokens = _generation_nonnegative_int_metric(generation, "generation_tokens")
    total_tokens = _generation_nonnegative_int_metric(generation, "total_tokens")
    prompt_tps = _generation_nonnegative_float_metric(generation, "prompt_tps")

    # mlx-vlm derives prompt_tps from its timed model loop through the first
    # token. This is not end-to-end TTFT because prepare_inputs() runs earlier.
    first_token_latency_s = None
    if prompt_tokens > 0 and prompt_tps > 0.0:
        first_token_latency_s = float(prompt_tokens) / prompt_tps

    raw_finish_reason = getattr(generation, "finish_reason", None)
    finish_reason = raw_finish_reason.strip() if isinstance(raw_finish_reason, str) else None

    return GenerationPerformanceData(
        prompt_tokens=prompt_tokens,
        generation_tokens=generation_tokens,
        total_tokens=total_tokens,
        prompt_tps=prompt_tps,
        generation_tps=_generation_nonnegative_float_metric(generation, "generation_tps"),
        peak_memory_gb=_generation_nonnegative_float_metric(generation, "peak_memory"),
        active_memory_gb=_generation_nonnegative_float_metric(generation, "active_memory"),
        cache_memory_gb=_generation_nonnegative_float_metric(generation, "cache_memory"),
        generation_time_s=_generation_optional_nonnegative_float_metric(generation, "time"),
        first_token_latency_s=first_token_latency_s,
        finish_reason=finish_reason or None,
    )


def _resolve_generation_stop_reason(
    performance_data: GenerationPerformanceData,
    *,
    requested_max_tokens: int,
) -> str:
    """Prefer upstream termination metadata, with a count-based legacy fallback."""
    if performance_data.finish_reason == "length":
        return "max_tokens"
    if performance_data.finish_reason == "stop":
        return "completed"
    if performance_data.finish_reason is not None:
        return performance_data.finish_reason
    if requested_max_tokens > 0 and performance_data.generation_tokens >= requested_max_tokens:
        return "max_tokens"
    return "completed"


# =============================================================================
# SECTION: APP CONSTANTS & CORE RESULT TYPES
# =============================================================================

# These constants define default values for various parameters used in the script.
DEFAULT_MAX_TOKENS: Final[int] = 1000
DEFAULT_EVAL_MODE: Final[RequestedEvaluationMode] = "auto"
_UNKNOWN_OWNER: Final[str] = "unknown"
TRIAGE_MAX_TOKENS: Final[int] = 200
DEFAULT_FOLDER: Final[Path] = Path.home() / "Pictures" / "Processed"
# Output paths relative to script's directory (not CWD) for consistency
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.resolve()
DEFAULT_HTML_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "reports" / "results.html"
DEFAULT_GALLERY_MD_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "reports" / "model_gallery.md"
DEFAULT_OUTPUT_INDEX: Final[Path] = _SCRIPT_DIR / "output" / "index.md"
DEFAULT_LOG_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "check_models.log"
DEFAULT_JSONL_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "results.jsonl"
DEFAULT_ENV_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "environment.log"
DEFAULT_DIAGNOSTICS_OUTPUT: Final[Path] = _SCRIPT_DIR / "output" / "reports" / "diagnostics.md"
_PREFLIGHT_ISSUES_ARG_ATTR: Final[str] = "_check_models_preflight_issues"
_GITHUB_REPO_URL: Final[str] = "https://github.com/jrp2014/check_models"
_GITHUB_RAW_URL: Final[str] = "https://raw.githubusercontent.com/jrp2014/check_models"
_GITHUB_DEFAULT_BRANCH: Final[str] = "main"
_GITHUB_REF_OVERRIDE: str | None = None
_PUBLISHED_OUTPUT_ROOT: Final[PurePosixPath] = PurePosixPath("src/output")
_PUBLISHED_REPORT_ARTIFACT_NAMES: Final[frozenset[str]] = frozenset(
    {
        DEFAULT_HTML_OUTPUT.name,
        DEFAULT_GALLERY_MD_OUTPUT.name,
        DEFAULT_DIAGNOSTICS_OUTPUT.name,
    }
)
_PUBLISHED_ROOT_OUTPUT_ARTIFACT_NAMES: Final[frozenset[str]] = frozenset(
    {
        DEFAULT_OUTPUT_INDEX.name,
        DEFAULT_LOG_OUTPUT.name,
        DEFAULT_JSONL_OUTPUT.name,
        DEFAULT_ENV_OUTPUT.name,
    }
)
_MODEL_LOAD_ACTIVE_MEMORY_ATTR: Final[str] = "model_load_active_memory"


class _LinkStyleState:
    """Mutable report link rendering mode shared by artifact helpers."""

    value: ClassVar[str] = "github"


DEFAULT_TEMPERATURE: Final[float] = 0.0  # Greedy/deterministic (matches mlx-vlm upstream)
DEFAULT_TIMEOUT: Final[float] = 300.0  # Default timeout in seconds
MAX_REASONABLE_TEMPERATURE: Final[float] = 2.0  # Warn if temperature exceeds this

# Additional Application Constants
IMAGE_OPEN_TIMEOUT: Final[float] = 5.0  # Timeout for opening/verifying image files
SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# Constants - EXIF
# Use Pillow's modern ExifTags enums (Pillow 10.0+) for type safety
IMPORTANT_EXIF_TAGS: Final[frozenset[str]] = frozenset(
    {
        "DateTimeOriginal",
        "DateTimeDigitized",
        "ImageDescription",
        "CreateDate",
        "Make",
        "Model",
        "LensModel",
        "ExposureTime",
        "FNumber",
        "ISOSpeedRatings",
        "FocalLength",
        "ExposureProgram",
    },
)
DATE_FORMATS: Final[tuple[str, ...]] = (
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y%m%d",
)
EXIF_DATE_TAGS: Final[tuple[str, ...]] = (
    "DateTimeOriginal",
    "DateTimeDigitized",
    "CreateDate",
    "DateTime",
)
EXIF_OFFSET_TAG_BY_DATE: Final[dict[str, str]] = {
    "DateTimeOriginal": "OffsetTimeOriginal",
    "DateTimeDigitized": "OffsetTimeDigitized",
    "CreateDate": "OffsetTimeDigitized",
    "DateTime": "OffsetTime",
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass(frozen=True)
class PromptDiagnostics:
    """Bounded prompt/rendering context for maintainer repro artifacts."""

    model_type: str | None = None
    processor_class: str | None = None
    tokenizer_class: str | None = None
    rendered_prompt_hash_sha256: str | None = None
    rendered_prompt_preview: str | None = None
    # Complete rendered chat-template prompt as sent upstream (the preview is
    # for bounded human surfaces; machine reports keep the full bytes).
    rendered_prompt: str | None = None
    rendered_prompt_chars: int | None = None
    image_placeholder_count: int | None = None
    rendered_prompt_token_count: int | None = None
    processed_image_width: int | None = None
    processed_image_height: int | None = None
    image_patch_count: int | None = None
    eos_token_id: JsonLike = None
    eos_token: str | None = None
    special_token_ids: tuple[JsonLike, ...] = ()
    special_tokens: tuple[str, ...] = ()
    generate_kwargs: dict[str, JsonLike] = dataclass_field(default_factory=dict)
    # How the thinking budget in generate_kwargs was chosen: "auto" when the
    # harness applied it because the template opened a thinking block,
    # "explicit" when the user passed thinking flags, None when no budget.
    thinking_budget_source: Literal["auto", "explicit"] | None = None
    template_thinking_markers: bool | None = None
    # Neutral legacy file-layout facts about the cached snapshot (e.g. missing
    # processor config). Evidence only: never an observation, never affects
    # usability; retained so a later failure can be traced to a snapshot that
    # always lacked the artifact.
    snapshot_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FailureException:
    """One exception in a failed run, stored in root-to-wrapper order."""

    exception_type: str
    module: str
    message: str
    origin: str | None = None


@dataclass(frozen=True)
class PerformanceResult:
    """Encapsulates a GenerationResult and execution metadata for a model run.

    Attributes:
        model_name: HuggingFace model identifier (e.g., 'mlx-community/nanoLLaVA')
        generation: The mlx-vlm GenerationResult, or None if generation failed
        success: Whether generation completed without errors
        failure_phase: First execution phase that failed (import/model_load/prefill/decode...)
        error_stage: Human-readable error class (OOM, API Mismatch, Model Error, ...)
        error_code: Canonical machine-readable code for cross-run bucketing
        error_signature: Stable signature hash for clustering related failures
        error_message: Human-readable error description
        captured_output_on_fail: Stderr/stdout captured when error occurred
        generation_time: Wall-clock time for text generation (excludes model load)
        model_load_time: Wall-clock time to load model into GPU memory
        total_time: End-to-end time including all stages
        error_type: Exception class name for error categorization in reports
        quality_analysis: Structured mechanical analysis used by ``ResultAssessment``
        active_memory: GPU memory in use (GB), from mx.get_active_memory()
        cache_memory: GPU memory in cache (GB), from mx.get_cache_memory()
        error_package: Error owner (mlx, mlx-vlm, transformers, model-repo-code, ...)
        error_traceback: Full traceback for actionable error reports
        requested_max_tokens: Requested generation budget for cutoff diagnosis
        prompt_diagnostics: Prompt/template and generation-kwarg context for maintainers
    """

    model_name: str
    generation: StoredGenerationResult | None
    success: bool
    upstream_boundary: UpstreamBoundary = "not_started"
    failure_phase: str | None = None
    error_stage: str | None = None
    error_code: str | None = None
    error_signature: str | None = None
    error_message: str | None = None
    captured_output_on_fail: str | None = None
    # Tee'd upstream console output for successful runs (failures use
    # captured_output_on_fail); bounded and deduplicated at capture time.
    captured_upstream_output: str | None = None
    generation_time: float | None = None
    model_load_time: float | None = None
    total_time: float | None = None
    error_type: str | None = None
    root_error_type: str | None = None
    root_error_module: str | None = None
    root_error_message: str | None = None
    exception_chain: tuple[FailureException, ...] = ()
    quality_analysis: GenerationQualityAnalysis | None = None
    assessment_profile: AssessmentProfile = "general"
    active_memory: float | None = None
    cache_memory: float | None = None
    error_package: str | None = None
    error_traceback: str | None = None
    runtime_diagnostics: RuntimeDiagnostics | None = None
    requested_max_tokens: int | None = None
    requested_revision: str | None = None
    model_burden: ModelBurdenFacts | None = None
    prompt_diagnostics: PromptDiagnostics | None = None
    rerun_evidence: RerunEvidence | None = None
    # Thermal/memory-pressure facts sampled while this model ran (darwin only).
    system_telemetry: SystemTelemetryRecord | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class RerunEvidence:
    """Secondary evidence from a differential rerun (never overwrites first-pass)."""

    rerun_success: bool
    rerun_error_code: str | None = None
    rerun_generated_chars: int | None = None
    rerun_generation_time: float | None = None
    rerun_prompt: str | None = None


@dataclass(frozen=True)
class RuntimeDiagnostics:
    """Detailed runtime attribution and termination diagnostics for one run."""

    input_validation_time_s: float | None = None
    model_load_time_s: float | None = None
    model_load_active_memory_gb: float | None = None
    prompt_prep_time_s: float | None = None
    # Legacy output key: this times the complete mlx_vlm.generate() call,
    # including prepare_inputs(), model prefill, and token decoding.
    decode_time_s: float | None = None
    cleanup_time_s: float | None = None
    # Upstream model-loop time through first token; excludes prepare_inputs().
    first_token_latency_s: float | None = None
    stop_reason: str | None = None
    # Allocator residue sampled after the per-model cleanup sequence.
    post_cleanup_active_memory_gb: float | None = None
    post_cleanup_cache_memory_gb: float | None = None


@dataclass(frozen=True)
class ImageInputProfile:
    """Resolved image dimensions used for input-normalized resource metrics."""

    width: int
    height: int
    megapixels: float
    processed_width: int | None = None
    processed_height: int | None = None


type PromptBurdenKind = Literal[
    "normal",
    "visual_input",
    "text",
    "mixed",
    "unknown",
    "unavailable",
]


@dataclass(frozen=True)
class PromptBurden:
    """Canonical classification of textual and visual prompt/input burden."""

    kind: PromptBurdenKind
    total_tokens: int | None = None
    text_tokens_est: int | None = None
    nontext_tokens_est: int | None = None
    visual_tokens_est: int | None = None
    template_tokens_est: int | None = None
    nontext_ratio: float | None = None
    text_tokens_source: str | None = None
    source: str = "unavailable"
    reason: str | None = None
    original_width: int | None = None
    original_height: int | None = None
    processed_width: int | None = None
    processed_height: int | None = None
    patch_count: int | None = None


def _classify_prompt_burden(
    *,
    total: int | None,
    text_est: int | None,
    nontext_est: int | None,
    ratio: float | None,
    placeholders: int | None,
    exact_text_tokens: bool = False,
) -> tuple[PromptBurdenKind, str | None]:
    """Classify prompt burden from token components; returns (kind, reason).

    With a heuristic text estimate, a heavy non-text share only counts as
    visual input when a recognised image placeholder confirms it. With an
    exact tokenizer count the ratio is authoritative on its own, so families
    whose placeholder the regex does not know (e.g. ``<|image_pad|>``) are
    classified the same way as the rest.
    """
    if total is None:
        return "unknown", "prompt_token_total_unavailable"
    if text_est is None or nontext_est is None:
        return "unavailable", "component_estimates_unavailable"
    substantial = total >= QUALITY.long_prompt_tokens_threshold
    if not substantial or ratio is None:
        return "normal", None
    if (placeholders or exact_text_tokens) and ratio >= QUALITY.heavy_nontext_prompt_ratio:
        return "visual_input", None
    if text_est >= QUALITY.long_prompt_tokens_threshold:
        return ("text" if ratio < QUALITY.mixed_prompt_burden_ratio_floor else "mixed"), None
    return "mixed", None


def _merged_processed_dimensions(
    diagnostics: PromptDiagnostics | None,
    image_profile: ImageInputProfile | None,
) -> tuple[int | None, int | None]:
    """Prefer per-run processed dimensions, falling back to the image profile."""
    width = (diagnostics.processed_image_width if diagnostics is not None else None) or (
        image_profile.processed_width if image_profile is not None else None
    )
    height = (diagnostics.processed_image_height if diagnostics is not None else None) or (
        image_profile.processed_height if image_profile is not None else None
    )
    return width, height


def _model_burden_rows(
    result: PerformanceResult,
) -> tuple[tuple[str, str | float | int | None], ...]:
    """Source-labelled model-burden facts as diagnostics rows (facts, no verdicts)."""
    burden = result.model_burden
    if burden is None:
        return ()
    rows: list[tuple[str, str | float | int | None]] = []
    weight_gb = burden.weight_bytes / 1e9 if burden.weight_bytes else None
    if weight_gb is not None:
        rows.append(("Checkpoint weights (GB)", f"{weight_gb:.2f}"))
    if burden.parameter_count is not None:
        count_text = f"{burden.parameter_count / 1e9:.2f}B"
        if burden.active_parameter_count is not None:
            count_text += f" total, {burden.active_parameter_count / 1e9:.2f}B active"
        rows.append(("Parameter count", f"{count_text} ({burden.parameter_count_source})"))
    elif burden.active_parameter_count is not None:
        # An "A3B"-style name states the active size only; the total is unknown.
        rows.append(
            (
                "Active parameter count",
                (
                    f"{burden.active_parameter_count / 1e9:.2f}B "
                    f"({burden.parameter_count_source}; total not stated in the name)"
                ),
            )
        )
    if burden.quantization_bits is not None or burden.quantization_mode is not None:
        parts = []
        if burden.quantization_bits is not None:
            parts.append(f"{burden.quantization_bits}-bit")
        if burden.quantization_group_size is not None:
            parts.append(f"group {burden.quantization_group_size}")
        if burden.quantization_mode is not None:
            parts.append(burden.quantization_mode)
        rows.append(("Quantization", ", ".join(parts)))
    if burden.context_length is not None:
        rows.append(
            (
                "Declared context length",
                f"{burden.context_length:,} ({burden.context_length_source})",
            )
        )
    runtime = result.runtime_diagnostics
    load_active = runtime.model_load_active_memory_gb if runtime is not None else None
    if load_active is not None and weight_gb:
        rows.append(
            (
                "Load active memory vs checkpoint",
                f"{load_active / weight_gb:.2f}x ({load_active:.2f} GB vs {weight_gb:.2f} GB on disk)",
            )
        )
    return tuple(rows)


def _prompt_composition_fact(result: PerformanceResult) -> str | None:
    """Describe the prompt's text/non-text token split when both parts are known."""
    analysis = _quality_analysis_for_result(result)
    if analysis is None:
        return None
    total = analysis.prompt_tokens_total
    text = analysis.prompt_tokens_text_est
    nontext = analysis.prompt_tokens_nontext_est
    rejected = analysis.prompt_tokens_text_exact_rejected
    if total is None or text is None or nontext is None or total <= 0:
        # The rejected exact count is evidence even when no split survived it.
        if rejected is not None and total is not None:
            return (
                f"unavailable; tokenizer count {rejected:,} rejected as inconsistent "
                f"with total {total:,} and the word-ratio estimate also exceeded it"
            )
        return None
    source = (
        "tokenizer-exact"
        if analysis.prompt_tokens_text_source == "tokenizer"
        else "word-ratio estimate"
    )
    if rejected is not None:
        source += f"; tokenizer count {rejected:,} rejected as inconsistent with total {total:,}"
    share = 100.0 * nontext / total
    return (
        f"{total:,} = {text:,} text/template ({source}) + {nontext:,} non-text "
        f"({share:.0f}%, image/audio expansion)"
    )


def _prompt_burden_for_result(
    result: PerformanceResult,
    image_profile: ImageInputProfile | None,
) -> PromptBurden:
    """Return the shared prompt/input burden view without re-tokenizing input."""
    analysis = _quality_analysis_for_result(result)
    total = analysis.prompt_tokens_total if analysis is not None else None
    text_est = analysis.prompt_tokens_text_est if analysis is not None else None
    nontext_est = analysis.prompt_tokens_nontext_est if analysis is not None else None
    ratio = nontext_est / total if total and nontext_est is not None else None
    diagnostics = result.prompt_diagnostics
    placeholders = diagnostics.image_placeholder_count if diagnostics is not None else 0
    processed_width, processed_height = _merged_processed_dimensions(diagnostics, image_profile)

    text_source = analysis.prompt_tokens_text_source if analysis is not None else None
    kind, reason = _classify_prompt_burden(
        total=total,
        text_est=text_est,
        nontext_est=nontext_est,
        ratio=ratio,
        placeholders=placeholders,
        exact_text_tokens=text_source == "tokenizer",
    )

    return PromptBurden(
        kind=kind,
        total_tokens=total,
        text_tokens_est=text_est,
        nontext_tokens_est=nontext_est,
        nontext_ratio=ratio,
        text_tokens_source=text_source,
        source=(
            ("exact_text_tokens" if text_source == "tokenizer" else "estimated_nontext")
            if nontext_est is not None
            else "unavailable"
        ),
        reason=reason,
        original_width=image_profile.width if image_profile is not None else None,
        original_height=image_profile.height if image_profile is not None else None,
        processed_width=processed_width,
        processed_height=processed_height,
        patch_count=diagnostics.image_patch_count if diagnostics is not None else None,
    )


class PhaseTimer:
    """Track named phase durations for one model run."""

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}
        self._start_times: dict[str, float] = {}

    def start(self, phase: FailurePhaseName) -> None:
        """Start timing a named phase if it is not already active."""
        if phase not in self._start_times:
            self._start_times[phase] = time.perf_counter()

    def stop(self, phase: FailurePhaseName) -> float | None:
        """Stop timing a named phase and return the elapsed time."""
        start_time = self._start_times.pop(phase, None)
        if start_time is None:
            return None
        elapsed = time.perf_counter() - start_time
        self._durations[phase] = self._durations.get(phase, 0.0) + elapsed
        return elapsed

    @contextmanager
    def track(self, phase: FailurePhaseName) -> Generator[None]:
        """Context manager that records elapsed time for a named phase."""
        self.start(phase)
        try:
            yield
        finally:
            self.stop(phase)

    def duration(self, phase: FailurePhaseName) -> float | None:
        """Return the accumulated duration for a phase, if available."""
        duration = self._durations.get(phase)
        if duration is None:
            return None
        return duration


class _TeeCaptureStream(io.TextIOBase):
    """Mirror writes to an underlying stream while buffering text for diagnostics."""

    __slots__ = ("_buffer", "_stream")

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._buffer = io.StringIO()

    def writable(self) -> bool:
        return True

    def write(self, data: str) -> int:
        self._buffer.write(data)
        return self._stream.write(data)

    def flush(self) -> None:
        # Finalization closes this wrapper after the harness (or pytest's
        # capture teardown) has already closed the underlying stream; that
        # late flush must not raise into the unraisable hook.
        if getattr(self._stream, "closed", False):
            return
        try:
            self._stream.flush()
        except ValueError:
            # Benign only when racing a close; an open sink's ValueError
            # is a genuine error and must propagate.
            if not getattr(self._stream, "closed", False):
                raise

    def isatty(self) -> bool:
        return self._stream.isatty()

    def getvalue(self) -> str:
        return self._buffer.getvalue()


# Gallery rendering helpers (outside class)
def _wrap_markdown_text(
    text: str,
    *,
    initial_indent: str = "",
    subsequent_indent: str = "",
    width: int = FORMATTING.markdown_wrap_width,
) -> list[str]:
    """Wrap plain Markdown text to the repository lint width."""
    if text == "":
        return [initial_indent.rstrip()]
    wrapped = textwrap.wrap(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapped or [initial_indent.rstrip()]


def _escape_markdown_underscore_runs(text: str) -> str:
    """Escape multi-underscore runs without altering single-word identifiers."""
    return re.sub(r"_{2,}", lambda match: r"\_" * len(match.group(0)), text)


def _markdown_emphasis(text: str) -> str:
    """Return repo-style Markdown emphasis for formatter-owned labels."""
    return f"*{text}*"


def _append_markdown_labeled_value(
    parts: list[str],
    *,
    label: str,
    value: str,
    bullet: bool = False,
) -> None:
    """Append a wrapped Markdown label/value line using repo-style emphasis."""
    prefix = (
        f"- {_markdown_emphasis(f'{label}:')} " if bullet else f"{_markdown_emphasis(f'{label}:')} "
    )
    subsequent_indent = "  " if bullet else " " * len(prefix)
    parts.extend(
        _wrap_markdown_text(
            value,
            initial_indent=prefix,
            subsequent_indent=subsequent_indent,
        ),
    )


def _escape_report_markdown_text(text: str) -> str:
    """Escape HTML-like text for non-code Markdown report blocks.

    Bare URLs become Markdown autolinks (``<https://…>``) and are left
    untouched inside the brackets: escaping them along with the surrounding
    prose turned the brackets into ``&lt;…&gt;`` (a bare URL again, MD034)
    and could mangle underscores in the path.
    """

    def _escape_prose(segment: str) -> str:
        escaped = html.escape(segment, quote=False)
        escaped = _escape_markdown_underscore_runs(escaped)
        return HTML_UNESCAPED_AMPERSAND_RE.sub("&amp;", escaped)

    parts: list[str] = []
    last = 0
    for match in _BARE_URL_RE.finditer(text):
        parts.append(_escape_prose(text[last : match.start()]))
        parts.append(f"<{match.group(1)}>")
        last = match.end()
    parts.append(_escape_prose(text[last:]))
    return "".join(parts)


def _escape_report_markdown_heading(text: str) -> str:
    """Escape HTML-like heading text while preserving ordinary ampersands."""
    escaped = text.replace("<", "&lt;").replace(">", "&gt;")
    return _escape_markdown_underscore_runs(escaped)


@dataclass(frozen=True)
class ReportParagraph:
    """Plain paragraph block for shared Markdown/HTML report sections."""

    text: str


@dataclass(frozen=True)
class ReportKeyValues:
    """Label/value list block shared by diagnostics, issue, review, and reports."""

    rows: tuple[tuple[str, str], ...]
    markdown_escaped: bool = False


@dataclass(frozen=True)
class ReportBulletList:
    """Bullet or numbered list block for shared report sections."""

    items: tuple[str, ...]
    ordered: bool = False


@dataclass(frozen=True)
class ReportLink:
    """Internal report link rendered safely in Markdown and HTML."""

    label: str
    anchor: str


@dataclass(frozen=True)
class ReportTargetLink:
    """Explicit artifact link rendered safely in Markdown and HTML."""

    label: str
    target: str


type ReportCell = str | ReportLink | ReportTargetLink


@dataclass(frozen=True)
class ReportTable:
    """Simple table block with renderer-specific escaping."""

    headers: tuple[str, ...]
    rows: tuple[tuple[ReportCell, ...], ...]
    markdown_escaped: bool = False
    compact: bool = False


@dataclass(frozen=True)
class ReportCodeBlock:
    """Fenced/preformatted code block for shared report sections."""

    content: str
    language: str = "text"


@dataclass(frozen=True)
class ReportDetails:
    """Collapsible details block for technical evidence."""

    summary: str
    blocks: tuple[ReportBlock, ...]


@dataclass(frozen=True)
class ReportRaw:
    """Renderer-specific trusted raw lines for unavoidable artifact details."""

    markdown_lines: tuple[str, ...] = ()
    html_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportSection:
    """Shared report section rendered into Markdown or HTML at artifact boundaries."""

    title: str
    blocks: tuple[ReportBlock, ...] = ()
    level: int = 2
    divider: bool = False


@dataclass(frozen=True)
class ReportModelOutput:
    """Readable presentation plus exact raw captured model output."""

    content: str
    raw_summary: str = "Exact raw output"


type ReportBlock = (
    ReportParagraph
    | ReportKeyValues
    | ReportBulletList
    | ReportTable
    | ReportCodeBlock
    | ReportDetails
    | ReportRaw
    | ReportSection
    | ReportModelOutput
)


class UnsupportedReportBlockError(TypeError):
    """Raised when shared report renderers receive an unsupported block type."""

    def __init__(self, block: object) -> None:
        block_name = type(block).__name__
        super().__init__(f"Unsupported report block: {block_name}")


class MissingGalleryAssessmentError(RuntimeError):
    """Raised when gallery rendering lacks the cached current-run assessments."""


def _render_report_section_markdown(block: ReportSection) -> list[str]:
    """Render a report section as Markdown lines."""
    rendered: list[str] = ["---", ""] if block.divider else []
    level = max(1, min(6, block.level))
    rendered.append(f"{'#' * level} {_escape_report_markdown_heading(block.title)}")
    rendered.append("")
    for child in block.blocks:
        child_lines = _render_report_markdown_block(child)
        if rendered[-1] == "" and child_lines and child_lines[0] == "":
            child_lines.pop(0)
        rendered.extend(child_lines)
    return rendered


def _render_report_key_values_markdown(block: ReportKeyValues) -> list[str]:
    """Render report key/value rows as Markdown lines."""
    rendered: list[str] = []
    for label, value in block.rows:
        rendered_label = label if block.markdown_escaped else _escape_report_markdown_text(label)
        rendered_value = value if block.markdown_escaped else _escape_report_markdown_text(value)
        _append_markdown_labeled_value(
            rendered,
            label=rendered_label,
            value=rendered_value,
            bullet=True,
        )
    if block.rows:
        rendered.append("")
    return rendered


def _render_report_bullet_list_markdown(block: ReportBulletList) -> list[str]:
    """Render a report bullet or ordered list as Markdown lines."""
    rendered: list[str] = []
    for index, item in enumerate(block.items, start=1):
        prefix = f"{index}. " if block.ordered else "- "
        rendered.extend(
            _wrap_markdown_text(
                _escape_report_markdown_text(item),
                initial_indent=prefix,
                subsequent_indent=" " * len(prefix),
            )
        )
    if block.items:
        rendered.append("")
    return rendered


def _render_report_table_markdown(block: ReportTable) -> list[str]:
    """Render a report table as Markdown lines."""
    escaped_headers = (
        list(block.headers)
        if block.markdown_escaped
        else [MARKDOWN_ESCAPER.escape(header) for header in block.headers]
    )
    escaped_rows = [
        tuple(_render_report_cell_markdown(cell, escaped=block.markdown_escaped) for cell in row)
        for row in block.rows
    ]
    if block.compact:
        header_line = f"| {' | '.join(escaped_headers)} |"
        divider_line = f"| {' | '.join('---' for _header in escaped_headers)} |"
        row_lines = [f"| {' | '.join(row)} |" for row in escaped_rows]
        return [header_line, divider_line, *row_lines, ""]
    return [*_render_padded_pipe_table(escaped_headers, escaped_rows), ""]


def _render_padded_pipe_table(
    headers: Sequence[str],
    rows: Sequence[tuple[str, ...]],
) -> list[str]:
    """Render a GitHub-style pipe table with columns padded to equal width."""
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row[: len(widths)]):
            widths[index] = max(widths[index], len(cell))
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)) + " |"
    divider_line = "|" + "|".join("-" * (width + 2) for width in widths) + "|"
    row_lines = [
        "| "
        + " | ".join(
            (row[index] if index < len(row) else "").ljust(width)
            for index, width in enumerate(widths)
        )
        + " |"
        for row in rows
    ]
    return [header_line, divider_line, *row_lines]


def _render_report_cell_markdown(cell: ReportCell, *, escaped: bool) -> str:
    """Render one table cell as safe Markdown."""
    if isinstance(cell, ReportLink):
        label = html.escape(cell.label, quote=False).replace("\\", "\\\\")
        label = label.replace("[", r"\[").replace("]", r"\]")
        anchor = html.escape(cell.anchor, quote=True).replace("(", "%28").replace(")", "%29")
        return f"[{label}](#{anchor})"
    if isinstance(cell, ReportTargetLink):
        label = html.escape(cell.label, quote=False).replace("\\", "\\\\")
        label = label.replace("[", r"\[").replace("]", r"\]")
        target = html.escape(cell.target, quote=True).replace("(", "%28").replace(")", "%29")
        return f"[{label}]({target})"
    return cell if escaped else MARKDOWN_ESCAPER.escape(cell)


def _render_report_raw_markdown(block: ReportRaw) -> list[str]:
    """Render trusted raw Markdown lines with the historical trailing blank rule."""
    raw_lines = list(block.markdown_lines)
    if raw_lines and raw_lines[-1] != "":
        raw_lines.append("")
    return raw_lines


def _render_report_model_output_markdown(block: ReportModelOutput) -> list[str]:
    """Render readable model Markdown, plus a collapsed raw view only when it differs."""
    readable = "\n".join(line.rstrip() for line in block.content.split("\n"))
    presentation = html.escape(readable, quote=False).replace("`", "&#96;").replace("@", "&#64;")
    rendered = [
        f"{_markdown_emphasis('Readable output:')}",
        "",
        '<pre class="model-output-readable">',
        presentation,
        "</pre>",
        "",
    ]
    # The readable view strips trailing whitespace and entity-escapes markup
    # characters; when both are no-ops the raw fence would be byte-identical,
    # so it earns no second copy.
    if readable != block.content or presentation != readable:
        _append_markdown_details_block(
            rendered,
            summary=block.raw_summary,
            body_lines=render_report_markdown((ReportCodeBlock(block.content),)),
        )
    return rendered


def _render_report_markdown_block(block: ReportBlock) -> list[str]:
    """Render one shared report block as Markdown."""
    rendered: list[str]
    if isinstance(block, ReportSection):
        rendered = _render_report_section_markdown(block)
    elif isinstance(block, ReportParagraph):
        rendered = [*_wrap_markdown_text(_escape_report_markdown_text(block.text)), ""]
    elif isinstance(block, ReportKeyValues):
        rendered = _render_report_key_values_markdown(block)
    elif isinstance(block, ReportBulletList):
        rendered = _render_report_bullet_list_markdown(block)
    elif isinstance(block, ReportTable):
        rendered = _render_report_table_markdown(block)
    elif isinstance(block, ReportCodeBlock):
        rendered = []
        _append_markdown_code_block(rendered, block.content, language=block.language)
    elif isinstance(block, ReportDetails):
        body_lines = render_report_markdown(block.blocks)
        rendered = []
        _append_markdown_details_block(rendered, summary=block.summary, body_lines=body_lines)
    elif isinstance(block, ReportRaw):
        rendered = _render_report_raw_markdown(block)
    elif isinstance(block, ReportModelOutput):
        rendered = _render_report_model_output_markdown(block)
    else:
        raise UnsupportedReportBlockError(block)
    return rendered


def _append_report_markdown_block(parts: list[str], block: ReportBlock) -> None:
    """Append one shared report block as Markdown."""
    parts.extend(_render_report_markdown_block(block))


def render_report_markdown(blocks: Sequence[ReportBlock]) -> list[str]:
    """Render shared report blocks to GitHub-flavoured Markdown lines."""
    parts: list[str] = []
    for block in blocks:
        _append_report_markdown_block(parts, block)
    while parts and parts[-1] == "":
        parts.pop()
    return parts


def _render_report_section_html(block: ReportSection) -> list[str]:
    """Render a report section as escaped HTML lines."""
    level = max(1, min(6, block.level))
    rendered = [f"<h{level}>{html.escape(block.title)}</h{level}>"]
    for child in block.blocks:
        rendered.extend(_render_report_html_block(child))
    return rendered


def _render_report_key_values_html(block: ReportKeyValues) -> list[str]:
    """Render report key/value rows as escaped HTML lines."""
    rendered = ["<ul>"]
    for label, value in block.rows:
        rendered.append(
            f"<li><b>{html.escape(label)}:</b> {html.escape(value)}</li>",
        )
    rendered.append("</ul>")
    return rendered


def _render_report_bullet_list_html(block: ReportBulletList) -> list[str]:
    """Render a report bullet or ordered list as escaped HTML lines."""
    tag = "ol" if block.ordered else "ul"
    rendered: list[str] = [f"<{tag}>"]
    rendered.extend([f"<li>{html.escape(item)}</li>" for item in block.items])
    rendered.append(f"</{tag}>")
    return rendered


def _render_report_table_html(block: ReportTable) -> list[str]:
    """Render a report table as escaped HTML lines."""
    rendered = ["<table>", "<thead>", "<tr>"]
    rendered.extend(f"<th>{html.escape(header)}</th>" for header in block.headers)
    rendered.extend(["</tr>", "</thead>", "<tbody>"])
    for row in block.rows:
        rendered.append("<tr>")
        rendered.extend(f"<td>{_render_report_cell_html(cell)}</td>" for cell in row)
        rendered.append("</tr>")
    rendered.extend(["</tbody>", "</table>"])
    return rendered


def _render_report_cell_html(cell: ReportCell) -> str:
    """Render one table cell as escaped HTML."""
    if isinstance(cell, ReportLink):
        return f'<a href="#{html.escape(cell.anchor, quote=True)}">{html.escape(cell.label)}</a>'
    if isinstance(cell, ReportTargetLink):
        return f'<a href="{html.escape(cell.target, quote=True)}">{html.escape(cell.label)}</a>'
    return html.escape(cell)


def _render_report_details_html(block: ReportDetails) -> list[str]:
    """Render an expandable details block as escaped HTML lines."""
    rendered = ["<details>", f"<summary>{html.escape(block.summary)}</summary>"]
    for child in block.blocks:
        rendered.extend(_render_report_html_block(child))
    rendered.append("</details>")
    return rendered


def _render_report_model_output_html(block: ReportModelOutput) -> list[str]:
    """Render exact escaped model output in HTML.

    HTML escaping is lossless, so the readable pre block already carries the
    exact bytes; a second collapsed raw copy would always be identical.
    """
    escaped_content = html.escape(block.content)
    return [
        "<p><b>Readable output:</b></p>",
        f'<pre class="model-output-readable">{escaped_content}</pre>',
    ]


def _render_report_html_block(block: ReportBlock) -> list[str]:
    """Render one shared report block to escaped HTML lines."""
    rendered: list[str]
    if isinstance(block, ReportSection):
        rendered = _render_report_section_html(block)
    elif isinstance(block, ReportParagraph):
        rendered = [f"<p>{html.escape(block.text)}</p>"]
    elif isinstance(block, ReportKeyValues):
        rendered = _render_report_key_values_html(block)
    elif isinstance(block, ReportBulletList):
        rendered = _render_report_bullet_list_html(block)
    elif isinstance(block, ReportTable):
        rendered = _render_report_table_html(block)
    elif isinstance(block, ReportCodeBlock):
        class_attr = f' class="language-{html.escape(block.language, quote=True)}"'
        rendered = [f"<pre><code{class_attr}>{html.escape(block.content)}</code></pre>"]
    elif isinstance(block, ReportDetails):
        rendered = _render_report_details_html(block)
    elif isinstance(block, ReportRaw):
        rendered = list(block.html_lines)
    elif isinstance(block, ReportModelOutput):
        rendered = _render_report_model_output_html(block)
    else:
        raise UnsupportedReportBlockError(block)
    return rendered


def render_report_html(blocks: Sequence[ReportBlock]) -> list[str]:
    """Render shared report blocks to escaped HTML lines."""
    parts: list[str] = []
    for block in blocks:
        parts.extend(_render_report_html_block(block))
    return parts


def _report_section(title: str, *blocks: ReportBlock, level: int = 2) -> ReportSection:
    """Build a typed section without repetitive tuple scaffolding."""
    return ReportSection(title, blocks, level)


def _gallery_runtime_facts(
    result: PerformanceResult,
    row: GalleryRow,
) -> tuple[tuple[str, str | None], ...]:
    """Return captured timing, token, and memory facts for gallery renderers."""
    generation = result.generation
    runtime = result.runtime_diagnostics
    generation_tps = _generation_float_metric(generation, "generation_tps")
    prompt_tps = _generation_float_metric(generation, "prompt_tps")
    peak_memory = _generation_float_metric(generation, "peak_memory")
    return (
        ("Model load time", _gallery_metric("model_load_time", result.model_load_time)),
        ("Generation time", _gallery_metric("generation_time", result.generation_time)),
        ("Total time", _gallery_metric("total_time", result.total_time)),
        (
            "Input validation time",
            _gallery_metric(
                "input_validation_time_s",
                runtime.input_validation_time_s if runtime is not None else None,
            ),
        ),
        (
            "Prompt preparation time",
            _gallery_metric(
                "prompt_prep_time_s",
                runtime.prompt_prep_time_s if runtime is not None else None,
            ),
        ),
        (
            "First-token latency",
            _gallery_metric(
                "first_token_latency_s",
                runtime.first_token_latency_s if runtime is not None else None,
            ),
        ),
        (
            "Cleanup time",
            _gallery_metric(
                "cleanup_time_s",
                runtime.cleanup_time_s if runtime is not None else None,
            ),
        ),
        (
            "Prompt tokens",
            _gallery_metric("prompt_tokens", _generation_int_metric(generation, "prompt_tokens")),
        ),
        ("Generation tokens", _gallery_metric("generation_tokens", row.generation_tokens)),
        (
            "Total tokens",
            _gallery_metric("total_tokens", _generation_int_metric(generation, "total_tokens")),
        ),
        (
            "Prompt throughput (raw)",
            f"{_gallery_metric('prompt_tps', prompt_tps)} tok/s" if prompt_tps is not None else "-",
        ),
        (
            "Generation throughput (raw)",
            f"{_gallery_metric('generation_tps', generation_tps)} tok/s"
            if generation_tps is not None
            else "-",
        ),
        ("Peak memory", _gallery_metric("peak_memory", peak_memory)),
        ("Active memory", _gallery_metric("active_memory", result.active_memory)),
        ("Cache memory", _gallery_metric("cache_memory", result.cache_memory)),
        (
            "Model-load active memory",
            _gallery_metric(
                "model_load_active_memory_gb",
                runtime.model_load_active_memory_gb if runtime is not None else None,
            ),
        ),
        (
            "Post-cleanup active memory",
            _gallery_metric(
                "post_cleanup_active_memory_gb",
                runtime.post_cleanup_active_memory_gb if runtime is not None else None,
            ),
        ),
        (
            "Post-cleanup cache memory",
            _gallery_metric(
                "post_cleanup_cache_memory_gb",
                runtime.post_cleanup_cache_memory_gb if runtime is not None else None,
            ),
        ),
        (
            "Stop reason",
            runtime.stop_reason if runtime is not None and runtime.stop_reason else "not captured",
        ),
    )


def _gallery_fact(value: object | None, *, missing: str = "not captured") -> str:
    """Render one optional gallery fact with its caller-selected missing label."""
    return missing if value is None or value == "" else str(value)


def _gallery_provenance_fact(
    model_provenance: ModelProvenanceRecord | None,
    key: Literal["requested_revision", "resolved_revision", "snapshot_path"],
    *,
    missing: str,
) -> str:
    """Distinguish absent provenance from an absent field in captured provenance."""
    if model_provenance is None:
        return "not captured"
    return _gallery_fact(model_provenance.get(key), missing=missing)


def _gallery_prompt_facts(
    result: PerformanceResult,
    model_provenance: ModelProvenanceRecord | None,
) -> tuple[tuple[str, str], ...]:
    """Return captured prompt, processor, and generation-setting facts."""
    prompt = result.prompt_diagnostics
    processed_image = "not captured"
    if (
        prompt is not None
        and prompt.processed_image_width is not None
        and prompt.processed_image_height is not None
    ):
        processed_image = f"{prompt.processed_image_width} x {prompt.processed_image_height} px"
    return (
        ("Requested maximum tokens", _gallery_fact(result.requested_max_tokens or None)),
        (
            "Rendered prompt characters",
            _gallery_fact(prompt.rendered_prompt_chars if prompt is not None else None),
        ),
        (
            "Image placeholders",
            _gallery_fact(prompt.image_placeholder_count if prompt is not None else None),
        ),
        ("Processed image", processed_image),
        (
            "Image patch count",
            _gallery_fact(prompt.image_patch_count if prompt is not None else None),
        ),
        (
            "Processor",
            _gallery_fact(prompt.processor_class if prompt is not None else None),
        ),
        (
            "Tokenizer",
            _gallery_fact(prompt.tokenizer_class if prompt is not None else None),
        ),
        (
            "Requested model revision",
            _gallery_provenance_fact(
                model_provenance,
                "requested_revision",
                missing="not requested",
            ),
        ),
        (
            "Resolved model revision",
            _gallery_provenance_fact(
                model_provenance,
                "resolved_revision",
                missing="not resolved",
            ),
        ),
        (
            "Resolved snapshot path",
            _gallery_provenance_fact(
                model_provenance,
                "snapshot_path",
                missing="not captured",
            ),
        ),
        (
            "Generation settings",
            json.dumps(prompt.generate_kwargs, sort_keys=True)
            if prompt is not None and prompt.generate_kwargs
            else "not captured",
        ),
        (
            "EOS token",
            prompt.eos_token
            if prompt is not None and prompt.eos_token is not None
            else "not captured",
        ),
    )


def _gallery_model_facts(
    result: PerformanceResult,
    row: GalleryRow,
    assessment: ResultAssessment,
    model_provenance: ModelProvenanceRecord | None,
) -> tuple[tuple[str, str | None], ...]:
    """Return factual per-model evidence shared by gallery renderers."""
    facts = (
        ("Execution", assessment.execution),
        ("Mechanical checks", _human_status_label(row.usability)),
        ("Assessment", _assessment_scope(result.assessment_profile)),
        ("Maintainer status", assessment.maintainer_status),
        (
            "Observations",
            _human_observation_labels(
                row.observations,
                details=_observation_details(result),
            ),
        ),
        ("Failure phase", result.failure_phase),
        ("Error stage", result.error_stage),
        ("Error code", result.error_code),
        ("Error type", result.error_type),
        ("Error package", result.error_package),
        ("Error message", result.error_message),
        ("Root exception type", result.root_error_type),
        ("Root exception module", result.root_error_module),
        ("Root exception message", result.root_error_message),
        ("Arch supported by installed mlx-vlm", _arch_precheck_summary(result.model_name)),
        *_gallery_runtime_facts(result, row),
        *_gallery_prompt_facts(result, model_provenance),
    )
    return tuple(
        (label, _home_relative_report_text(value) if value is not None else None)
        for label, value in facts
    )


def _gallery_model_evidence_blocks(result: PerformanceResult) -> tuple[ReportBlock, ...]:
    """Build one model's evidence body (output/traceback branches) shared by renderers.

    The captured-facts block stays renderer-specific so each side keeps its
    established escaping (Markdown pipe-escaper vs escaped HTML table).
    """
    blocks: list[ReportBlock] = []
    if result.success:
        output = _generation_text_value(result.generation)
        if not output:
            blocks.append(
                _report_section(
                    "Complete generated output", ReportParagraph("empty output"), level=4
                )
            )
        else:
            blocks.append(ReportModelOutput(output))
    else:
        traceback_block: ReportBlock = (
            ReportCodeBlock(_home_relative_report_text(result.error_traceback), language="python")
            if result.error_traceback
            else ReportParagraph("traceback not captured")
        )
        blocks.append(_report_section("Complete traceback", traceback_block, level=4))
        partial_output = _generation_text_value(result.generation)
        if partial_output:
            blocks.append(
                _report_section(
                    "Partial generated output", ReportCodeBlock(partial_output), level=4
                )
            )
        if result.captured_output_on_fail:
            blocks.append(
                _report_section(
                    "Captured upstream output",
                    ReportCodeBlock(_home_relative_report_text(result.captured_output_on_fail)),
                    level=4,
                )
            )
        if not partial_output and not result.captured_output_on_fail:
            blocks.append(ReportParagraph("No partial or captured output."))
    return tuple(blocks)


def _render_gallery_model(
    result: PerformanceResult,
    row: GalleryRow,
    assessment: ResultAssessment,
    model_provenance: ModelProvenanceRecord | None,
) -> list[str]:
    """Render complete captured evidence for one model without reclassification."""
    escaped_facts = tuple(
        (MARKDOWN_ESCAPER.escape(label), MARKDOWN_ESCAPER.escape(value))
        for label, value in _gallery_model_facts(result, row, assessment, model_provenance)
        if value is not None
    )
    out = [
        f'<a id="{_gallery_model_anchor(result.model_name)}"></a>',
        "",
        f"### {result.model_name}",
        "",
        "<details>",
        f"<summary>Complete evidence: {html.escape(result.model_name)}</summary>",
        "",
    ]
    out.extend(
        render_report_markdown(
            (
                ReportKeyValues(escaped_facts, markdown_escaped=True),
                *_gallery_model_evidence_blocks(result),
            )
        )
    )
    out.extend(["", "</details>", ""])
    return out


class ResultSet:
    """Cache-friendly wrapper around a collection of PerformanceResult.

    Provides:
        - Single-pass sorting by generation time (fastest first)
        - Lazy discovery/caching of available metric fields (generation + timing)
        - Simple iteration / length protocol support

    Rationale: Multiple rendering paths previously repeated the same sort
    and field extraction logic. Centralizing reduces duplication and
    guarantees consistent ordering across console, HTML, and Markdown
    outputs.
    """

    __slots__ = ("_failed", "_fields", "_results", "_successful")  # Sorted for lint consistency

    def __init__(self, results: list[PerformanceResult]) -> None:
        """Initialize and sort results.

        A shallow copy of ``results`` is taken to guard against external
        mutation after construction.
        """
        self._results = _sort_results_by_time(list(results))
        self._successful: list[PerformanceResult] | None = None
        self._failed: list[PerformanceResult] | None = None

    # Public API -----------------------------------------------------
    @property
    def results(self) -> list[PerformanceResult]:  # Sorted
        """Return results sorted by generation time (fastest first)."""
        return self._results

    @property
    def successful(self) -> list[PerformanceResult]:
        """Return cached list of successful results."""
        if self._successful is None:
            self._successful = [r for r in self._results if r.success]
        return self._successful

    @property
    def failed(self) -> list[PerformanceResult]:
        """Return cached list of failed results."""
        if self._failed is None:
            self._failed = [r for r in self._results if not r.success]
        return self._failed

    # Dunder conveniences --------------------------------------------
    def __len__(self) -> int:  # pragma: no cover - trivial
        """Return number of results."""
        return len(self._results)

    def __iter__(self) -> Iterator[PerformanceResult]:  # pragma: no cover - trivial
        """Iterate over sorted results."""
        return iter(self._results)


@dataclass(frozen=True)
class ProcessImageParams:
    """Parameters for processing an image with a model.

    Centralizes all parameters needed for model inference into a single
    immutable structure. This approach:
        - Reduces function signature complexity (single param vs many)
        - Makes parameter passing explicit and type-safe
        - Simplifies testing (one object to mock/construct)
        - Documents expected inputs clearly
    """

    model_identifier: str
    image_path: str | Path  # Support both file paths and URLs
    prompt: str
    max_tokens: int
    temperature: float
    timeout: float
    verbose: bool
    trust_remote_code: bool
    top_p: float
    min_p: float
    top_k: int
    repetition_penalty: float | None
    repetition_context_size: int
    lazy: bool
    max_kv_size: int | None
    kv_bits: float | None
    kv_quant_scheme: Literal["uniform", "turboquant"]
    kv_group_size: int
    quantized_kv_start: int
    kv_key_bits: float | None = None
    kv_value_bits: float | None = None
    kv_key_scheme: Literal["uniform", "turboquant"] | None = None
    kv_value_scheme: Literal["uniform", "turboquant"] | None = None
    seed: int | None = None
    presence_penalty: float | None = None
    presence_context_size: int = DEFAULT_PENALTY_CONTEXT_SIZE
    frequency_penalty: float | None = None
    frequency_context_size: int = DEFAULT_PENALTY_CONTEXT_SIZE
    logit_bias: LogitBiasDict | None = None
    force_download: bool = False
    quantize_activations: bool = False
    revision: str | None = None
    adapter_path: str | None = None
    prefill_step_size: int | None = None
    resize_shape: tuple[int, int] | None = None
    eos_tokens: tuple[str, ...] | None = None
    skip_special_tokens: bool = False
    processor_kwargs: dict[str, JsonLike] | None = None
    enable_thinking: bool = False
    thinking_budget: int | None = None
    thinking_mode: str | None = None
    thinking_start_token: str | None = None
    thinking_end_token: str = DEFAULT_THINKING_END_MARKER
    auto_thinking_budget: bool = True
    system_telemetry: SystemTelemetryMode = "snapshot"
    assessment_profile: AssessmentProfile = "general"


# =============================================================================
# SECTION: TIMING, LOGGING & RICH CONSOLE PLUMBING
# =============================================================================


class PerfCounterTimer:
    """Default timing strategy using time.perf_counter()."""

    def __init__(self) -> None:
        self._start_time: float | None = None

    def start(self) -> None:
        self._start_time = time.perf_counter()

    def stop(self) -> float:
        if self._start_time is None:
            msg = "Timer was not started"
            raise RuntimeError(msg)
        return time.perf_counter() - self._start_time


# Custom timeout context manager
# Python 3.11+ has asyncio.timeout, but signal-based timeout works across sync code
# Uses SIGALRM which is Unix-only - Windows doesn't support this signal mechanism
class TimeoutManager(ContextDecorator):
    """Apply a SIGALRM-based timeout around synchronous code on Unix."""

    def __init__(self, seconds: float) -> None:
        """Store the timeout window that ``__enter__`` arms via SIGALRM.

        Args:
            seconds: Maximum runtime, in seconds, before ``TimeoutError`` is raised.

        """
        self.seconds: float = seconds
        self.timer: signal._HANDLER | None = None

    def _timeout_handler(
        self,
        _signum: int,
        _frame: types.FrameType | None,
    ) -> NoReturn:
        msg: str = f"Operation timed out after {self.seconds} seconds"
        raise TimeoutError(msg)

    def __enter__(self) -> Self:
        """Enter the timeout context manager."""
        if hasattr(signal, "SIGALRM"):
            if self.seconds > 0:
                try:
                    self.timer = signal.signal(
                        signal.SIGALRM,
                        self._timeout_handler,
                    )
                    signal.alarm(math.ceil(self.seconds))
                except ValueError as e:
                    # Signal handling restricted (threading/subprocess environment)
                    logger.warning(
                        "Could not set SIGALRM for timeout: %s. "
                        "Timeout disabled - operations may hang indefinitely.",
                        e,
                    )
                    self.seconds = 0
        elif self.seconds > 0:
            logger.warning(
                "Timeout functionality requires signal.SIGALRM, "
                "not available on this platform (e.g., Windows). "
                "Timeout disabled.",
            )
            self.seconds = 0
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the timeout context manager and clear the alarm."""
        # Reset signal handler only if we successfully set it up
        if hasattr(signal, "SIGALRM") and self.seconds > 0 and self.timer is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self.timer)


# Logging uses the module-level logger initialized with the other constants.
# Contributor rule of thumb:
# - Send user-visible messages through logger so console and file logs stay aligned.
# - Use Rich to build structured renderables (for example tables or panels),
#   then route them through _log_rich_renderable() / _log_rich_table()
#   instead of calling Console.print() directly from feature code.
# Disable Hugging Face tokenizers parallelism to avoid fork-related warnings/deadlocks.
# This must be set before tokenizers are created/used.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Global rendering width override (set via --width); when set, all width
# calculations should honor this value instead of auto-detected terminal width.
WIDTH_OVERRIDE: int | None = None
ANSI_ESCAPE_RE: Final[re.Pattern[str]] = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])",
)


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for width calculations."""
    return ANSI_ESCAPE_RE.sub("", text)


def _display_width(text: str) -> int:
    """Return terminal display width with Unicode-aware fallback behavior."""
    width: int = cell_len(_strip_ansi(text))
    return width


def _display_align(text: str, width: int, *, alignment: Literal["left", "center"]) -> str:
    """Pad text based on display width rather than codepoint length."""
    pad_total = max(0, width - _display_width(text))
    if alignment == "center":
        left = pad_total // 2
        right = pad_total - left
        return f"{' ' * left}{text}{' ' * right}"
    return f"{text}{' ' * pad_total}"


# =============================================================================
# SECTION: FORMATTING, ESCAPING & DETECTOR HELPERS
# =============================================================================


class _RichColorState:
    """Mutable Rich color preference shared by console handlers."""

    enabled: ClassVar[bool] = (
        True
        if os.getenv("FORCE_COLOR", "").lower() in {"1", "true", "yes"}
        else (sys.stderr.isatty() and os.getenv("NO_COLOR") is None)
    )


def _set_rich_color_enabled(*, enabled: bool) -> None:
    """Globally enable or disable Rich console color for this process."""
    _RichColorState.enabled = enabled


def _rich_color_enabled() -> bool:
    """Return whether styled terminal output is enabled."""
    return _RichColorState.enabled


class LogStyles:
    """String constants describing structured log presentation styles."""

    HEADER: ClassVar[str] = "header"
    SECTION: ClassVar[str] = "section"
    RULE: ClassVar[str] = "rule"
    ERROR: ClassVar[str] = "error"
    SUCCESS: ClassVar[str] = "success"
    WARNING: ClassVar[str] = "warning"
    DETAIL: ClassVar[str] = "detail"
    METRIC_LABEL: ClassVar[str] = "metric_label"
    METRIC_VALUE: ClassVar[str] = "metric_value"
    GENERATED_TEXT: ClassVar[str] = "generated_text"
    FILE_PATH: ClassVar[str] = "file_path"
    MODEL_NAME: ClassVar[str] = "model_name"


def _make_rich_console(
    *,
    width: int | None = None,
    markup: bool = False,
    highlight: bool = False,
) -> Console:
    """Create the shared console object used by Rich logging."""
    colors_enabled = _rich_color_enabled()
    force_terminal = True if colors_enabled and os.getenv("FORCE_COLOR") is not None else None
    return Console(
        stderr=True,
        width=width,
        force_terminal=force_terminal,
        no_color=not colors_enabled,
        markup=markup,
        highlight=highlight,
        emoji=True,
    )


LOCAL_TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S %Z"
_LOCAL_TIMESTAMP_RE: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [A-Z]{2,5}"
)
CONSOLE_LOG_TIME_FORMAT: Final[str] = "[%H:%M:%S]"
# Display width consumed by the Rich log handler prefix when show_level=True:
# "[HH:MM:SS]" (10) + " " (1) + level padded to 8 chars (8) + " " (1) = 20.
_RICH_LOG_PREFIX_WIDTH: Final[int] = 20


class StyleAwareRichHandler(RichHandler):
    """Rich log handler that honors the script's existing structured style hints."""

    HINT_STYLES: ClassVar[dict[str, str]] = {
        LogStyles.RULE: "blue",
        LogStyles.HEADER: "bold magenta",
        LogStyles.SECTION: "bold magenta",
        LogStyles.ERROR: "bold red",
        LogStyles.SUCCESS: "bold green",
        LogStyles.WARNING: "bold yellow",
        LogStyles.DETAIL: "cyan",
        LogStyles.METRIC_LABEL: "bold white",
        LogStyles.METRIC_VALUE: "white",
        LogStyles.GENERATED_TEXT: "cyan",
        LogStyles.FILE_PATH: "cyan",
        LogStyles.MODEL_NAME: "magenta",
    }
    LEVEL_STYLES: ClassVar[dict[int, str]] = {
        logging.DEBUG: "dim",
        logging.WARNING: "yellow",
        logging.ERROR: "bold red",
        logging.CRITICAL: "bold red reverse",
    }

    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        """Render log records as Rich Text without changing the stored log record."""
        style_hint = getattr(record, "style_hint", None)
        rendered_message = self._message_for_hint(style_hint, message, record)
        style = self._style_for_record(record, style_hint)
        return Text(rendered_message, style=style)

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Render DEBUG's level label in gray while preserving message styling."""
        if record.levelno == logging.DEBUG:
            return Text.styled(record.levelname.ljust(8), "dim")
        return super().get_level_text(record)

    def _message_for_hint(
        self,
        style_hint: object,
        message: str,
        record: logging.LogRecord,
    ) -> str:
        """Apply lightweight structural transforms before Rich styling."""
        if style_hint == LogStyles.HEADER:
            width = int(getattr(record, "style_width", max(_display_width(message), 1)))
            return _display_align(message, width, alignment="center")
        if style_hint == LogStyles.SECTION:
            uppercase_enabled = bool(getattr(record, "style_uppercase", True))
            title = message.upper() if uppercase_enabled and "\x1b[" not in message else message
            return f"{getattr(record, 'style_prefix', '▶')} [ {title} ]"
        if style_hint == LogStyles.METRIC_LABEL:
            emoji = getattr(record, "style_emoji", "")
            return f"{emoji} {message}" if isinstance(emoji, str) and emoji else message
        return message

    def _style_for_record(self, record: logging.LogRecord, style_hint: object) -> str:
        """Return the Rich style for a log record."""
        style_override = getattr(record, "style_override", None)
        if isinstance(style_override, str) and style_override:
            return style_override
        if isinstance(style_hint, str):
            return self.HINT_STYLES.get(style_hint, "")
        return self.LEVEL_STYLES.get(record.levelno, "")


class FileSafeFormatter(logging.Formatter):
    """Formatter for file logs that strips ANSI/control formatting codes."""

    def format(self, record: logging.LogRecord) -> str:
        raw = super().format(record)
        return ANSI_ESCAPE_RE.sub("", raw)


class ConsoleRoutingFilter(logging.Filter):
    """Exclude records that should be written only to the file log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(record, "log_destination", None) != "file"


def _make_console_log_handler(
    *,
    level: int,
    verbose: bool,
    width: int | None = None,
) -> StyleAwareRichHandler:
    """Create the Rich console log handler for stderr output."""
    handler = StyleAwareRichHandler(
        console=_make_rich_console(width=width),
        show_time=True,
        omit_repeated_times=False,
        show_level=verbose,
        show_path=False,
        markup=False,
        highlighter=None,
        rich_tracebacks=verbose,
        log_time_format=CONSOLE_LOG_TIME_FORMAT,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(ConsoleRoutingFilter())
    return handler


# Configure an import-time console handler; setup_environment replaces it per CLI flags.
handler: StyleAwareRichHandler = _make_console_log_handler(
    level=logging.INFO,
    verbose=True,
)
logger.handlers.clear()
logger.addHandler(handler)

DECIMAL_GB: Final[float] = 1_000_000_000.0  # Decimal GB (mlx-vlm already divides by 1e9)
MEM_BYTES_TO_GB_THRESHOLD: Final[float] = 1_000_000.0  # > ~1MB treat as raw bytes from mlx
MEGAPIXEL_CONVERSION: Final[float] = 1_000_000.0  # Convert pixels to megapixels

# EXIF/GPS coordinate standards: camera hardware stores GPS as degrees-minutes-seconds tuples
MAX_GPS_COORD_LEN: Final[int] = 3  # Full GPS coordinate (degrees, minutes, seconds)
MED_GPS_COORD_LEN: Final[int] = 2  # GPS coordinate with 2 elements (degrees, minutes)
MIN_GPS_COORD_LEN: Final[int] = 1  # GPS coordinate with 1 element (degrees only)
RATIONAL_TUPLE_LEN: Final[int] = 2  # EXIF rational values are (numerator, denominator) tuples
EXIF_USERCOMMENT_PREFIX_LEN: Final[int] = 8  # EXIF UserComment has 8-byte encoding prefix

# --- EXIF & Metadata Heuristics ---
CJK_IDEOGRAPH_START: Final[int] = 0x4E00
MOJIBAKE_HEURISTIC_LEN: Final[int] = 50
MOJIBAKE_MARKERS: Final[tuple[str, ...]] = ("Â", "Ã", "â€", "â€™", "â€œ")
MOJIBAKE_REPAIR_ENCODINGS: Final[tuple[str, ...]] = ("latin-1", "cp1252")
MAX_TUPLE_LEN: Final[int] = 10
MAX_STR_LEN: Final[int] = 60
STR_TRUNCATE_LEN: Final[int] = 57

# Field display configuration: maps field names to (label, unit) tuples.
# Used by format_field_label() and table generators for consistent column headers.
FIELD_ABBREVIATIONS: Final[dict[str, tuple[str, str]]] = {
    "model_name": ("Model", "Name"),
    "prompt_tokens": ("Prompt", "(tokens)"),
    "generation_tokens": ("Generation", "(tokens)"),
    "total_tokens": ("Total", "Tokens"),
    "prompt_tps": ("Prompt", "Tps"),
    "generation_tps": ("Gen", "TPS"),
    "peak_memory": ("Peak", "(GB)"),
    "generation_time": ("Generation", "(s)"),
    "model_load_time": ("Load", "(s)"),
    "total_time": ("Total", "(s)"),
    "active_memory": ("Active", "Mem (GB)"),
    "cache_memory": ("Cache", "Mem (GB)"),
    "error_package": ("Error", "Package"),
}

MAX_OUTPUT_PREVIEW_CHARS: Final[int] = 280  # Max chars for output previews in summary tables
MIN_THROUGHPUT_SAMPLE_TOKENS: Final[int] = 16
MAX_CAPTURED_OUTPUT_LOG_CHARS: Final[int] = 1200  # Max chars of captured stdout/stderr in logs
# File-log retention for live mlx-vlm console output (tee buffer). Keep large enough
# for multi-paragraph model text while bounding pathological loops.
MAX_FILE_STREAM_CAPTURE_CHARS: Final[int] = 250_000
SELF_LOGGED_FAILURE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"^\[\d{2}:\d{2}:\d{2}\]\s+ERROR\s+Failed to load model\b"
)
SUMMARY_CHART_WIDTH: Final[int] = 24  # Character width for compact Rich summary bars
SUMMARY_MODEL_LABEL_MAX: Final[int] = 32  # Max model label length in summary tables/charts
SUMMARY_CHART_MAX_ROWS: Final[int] = 8  # Max rows shown in summary charts
MIN_MODELS_FOR_EFFICIENCY_CHART: Final[int] = 2  # Min successful rows for cross-model efficiency

# Performance timing fields: those from PerformanceResult (not GenerationResult)
# Automatically derived from FIELD_ABBREVIATIONS for consistency
PERFORMANCE_TIMING_FIELDS: Final[list[str]] = [
    field
    for field in FIELD_ABBREVIATIONS
    if field in {"generation_time", "model_load_time", "total_time", "error_package"}
]
# =============================================================================
# FORMATTING UTILITIES (Numbers, Memory, Time, Tokens/sec, Field Values)
# =============================================================================


def fmt_num(val: float | str) -> str:
    """Format numbers consistently with thousands separators across all output formats."""
    try:
        fval = float(val)
        if abs(fval) >= FORMATTING.large_number:
            return f"{fval:,.0f}"
        # For integers or whole numbers, use comma separator if >= thousand_separator
        if fval == int(fval) and abs(fval) >= FORMATTING.thousand_separator:
            return f"{int(fval):,}"
        if abs(fval) > 0:
            return f"{fval:.3g}"
        return str(val)
    except (ValueError, TypeError, OverflowError):
        return str(val)


def format_field_label(field_name: str) -> str:
    """Return a human-friendly label for a metric field name."""
    return field_name.replace("_", " ").title()


# =============================================================================
# TEXT ESCAPING & MECHANICAL OUTPUT DETECTORS - escaping strategy plus
# repetition/reasoning/echo/cutoff detectors and catalog contract checks
# =============================================================================


class HTMLSelectiveEscaper:
    """Selective HTML escaping preserving GitHub-safe tags.

    Escapes potentially unsafe HTML while preserving common formatting
    tags that GitHub Markdown recognizes (br, b, strong, i, em, code).
    Only bare tags are preserved; attributes are escaped so event handlers,
    style injection, and URL-bearing attributes cannot flow into HTML reports.
    Does NOT preserve 's' tag to avoid interpreting <s> tokens from
    model output as strikethrough.
    """

    allowed_tags: frozenset[str] = frozenset({"br", "b", "strong", "i", "em", "code"})
    tag_pattern: re.Pattern[str] = re.compile(r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s+[^<>]*?)?>")

    def escape(self, text: str) -> str:
        """Escape tags except allowed safe tags."""

        def _is_plain_allowed_tag(inner: str) -> bool:
            normalized = inner.strip()
            if not normalized:
                return False
            normalized = normalized.removeprefix("/").strip()
            normalized = normalized.removesuffix("/").strip()
            return bool(normalized) and normalized.lower() in self.allowed_tags

        def _escape_html_like(m: re.Match[str]) -> str:
            token = m.group(0)
            inner = token[1:-1].strip()
            if not inner:
                return html.escape(token, quote=True)
            if _is_plain_allowed_tag(inner):
                return token  # Keep recognized safe tag
            return html.escape(token, quote=True)

        return self.tag_pattern.sub(_escape_html_like, text)


def _escape_markdown_table_text(
    text: str,
    *,
    collapse_breaks_at: int,
    normalize_whitespace: bool,
) -> str:
    """Escape text for a Markdown table with a caller-selected whitespace policy."""
    result = text.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")
    result = re.sub(rf"(<br>\s*){{{collapse_breaks_at},}}", "<br><br>", result)
    if normalize_whitespace:
        result = re.sub(r"\s+", " ", result).strip()
    result = _wrap_bare_urls(result)
    result = result.replace("|", "\\|")
    result = HTML_ESCAPER.escape(result)
    result = _escape_markdown_underscore_runs(result)
    return HTML_UNESCAPED_AMPERSAND_RE.sub("&amp;", result)


class MarkdownPipeEscaper:
    """Markdown escaping for table pipe characters and formatting.

    Handles pipe character escaping and converts newlines to <br> tags
    to prevent breaking Markdown table formatting. Preserves model-generated
    markdown like **bold**, *italic*, `code` while preventing table breakage.
    """

    def escape(self, text: str) -> str:
        """Escape text for safe inclusion in Markdown tables.

        Converts newlines to <br> tags, wraps bare URLs, escapes pipes,
        and neutralizes HTML-like tags while preserving markdown formatting.
        """
        return _escape_markdown_table_text(
            text,
            collapse_breaks_at=2,
            normalize_whitespace=True,
        )


class DiagnosticsEscaper:
    """Markdown escaping optimized for error/diagnostic messages.

    Preserves diagnostic spacing while still preventing table breakage.
    """

    def escape(self, text: str) -> str:
        """Escape diagnostics text for Markdown tables.

        More lenient than standard escaping to preserve error message formatting.
        """
        return _escape_markdown_table_text(
            text,
            collapse_breaks_at=3,
            normalize_whitespace=False,
        )


# Instantiate default escapers for runtime use
HTML_ESCAPER = HTMLSelectiveEscaper()
MARKDOWN_ESCAPER = MarkdownPipeEscaper()
DIAGNOSTICS_ESCAPER = DiagnosticsEscaper()


def _format_memory_value_gb(num: float) -> str:
    """Format mixed-source memory value as GB string.

    Accepts raw bytes (mlx) or decimal GB (mlx-vlm). Returns a string without unit.
    """
    if num <= 0:
        return "0"
    gb: float = (num / DECIMAL_GB) if num > MEM_BYTES_TO_GB_THRESHOLD else num
    if gb >= FORMATTING.memory_gb_integer:
        return f"{gb:,.0f}"
    if gb >= 1:
        return f"{gb:,.1f}"
    return f"{gb:.2f}"


def _peak_memory_working_set_pct(
    peak_memory_gb: float | None,
    recommended_working_set_bytes: int | None,
) -> float | None:
    """Return peak allocator bytes as a percentage of Metal's recommendation."""
    if peak_memory_gb is None or not math.isfinite(peak_memory_gb) or peak_memory_gb < 0:
        return None
    if type(recommended_working_set_bytes) is not int or recommended_working_set_bytes <= 0:
        return None
    return peak_memory_gb * DECIMAL_GB / recommended_working_set_bytes * 100.0


def _format_time_seconds(num: float) -> str:
    """Format seconds with two decimals and trailing 's'."""
    return f"{num:.2f}s"


def _format_tps(num: float) -> str:
    """Format tokens-per-second with adaptive precision."""
    if abs(num) >= FORMATTING.large_number:
        return f"{num:,.0f}"
    if abs(num) >= FORMATTING.medium_number:
        return f"{num:.1f}"
    return f"{num:.3g}"


_MINUTES_DISPLAY_THRESHOLD_SECONDS: Final[float] = 90.0


def format_overall_runtime(total_seconds: float) -> str:
    """Format a duration the way a skimmer reads it.

    Short spans keep precise seconds (``56.78s``); anything from a minute
    and a half up reads as minutes and seconds (``15m 26s``) or hours,
    minutes, and seconds (``1h 05m 12s``) — no raw four-digit second counts.
    """
    if total_seconds < _MINUTES_DISPLAY_THRESHOLD_SECONDS:
        return f"{total_seconds:.2f}s"
    whole = int(total_seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s"


def _detect_repetitive_output(text: str, threshold: float | None = None) -> tuple[bool, str | None]:
    """Detect if generated text is highly repetitive (tokens or phrases).

    Checks for:
    1. Single token repetition (e.g., "<s> <s> <s>")
    2. Phrase repetition (e.g., "The scene is very visible. The scene is very visible.")

    Args:
        text: Generated text to check
        threshold: Fraction of text that must be repetitive to flag
            (default from QUALITY.repetition_ratio)

    Returns:
        Tuple of (is_repetitive, repeated_pattern)
    """
    if threshold is None:
        threshold = QUALITY.repetition_ratio

    tokens = text.split()
    if not text or len(text) < QUALITY.min_text_length or len(tokens) < QUALITY.min_token_count:
        return False, None

    token_counts = Counter(tokens)
    if token_counts:
        most_common_token, count = token_counts.most_common(1)[0]
        if count / len(tokens) >= threshold:
            return True, most_common_token

    repeated_item = _repeated_catalog_keyword(text)
    if repeated_item is not None:
        return True, f'keyword: "{repeated_item[:30]}"'

    # 2. Check for phrase repetition (n-grams)
    # Look for repeated sequences of configurable length (default 4+ tokens)
    min_phrase_len = QUALITY.min_phrase_length
    # We only care if the phrase appears multiple times and covers a significant portion of text

    # Simple heuristic: Check if any substring of length N repeats significantly
    # For efficiency, we'll check specific n-gram sizes
    text_lower = text.lower()
    words = text_lower.split()
    n_words = len(words)

    if n_words < min_phrase_len * 2:
        return False, None

    # Check n-grams up to configured maximum
    for n in range(min_phrase_len, min(QUALITY.max_phrase_length + 1, n_words // 2)):
        ngrams = [" ".join(words[i : i + n]) for i in range(n_words - n + 1)]
        if not ngrams:
            continue

        ngram_counts = Counter(ngrams)
        most_common_ngram, count = ngram_counts.most_common(1)[0]

        # If a phrase repeats more than configured threshold and covers significant portion
        # Or if it repeats excessively regardless of coverage
        if count > QUALITY.max_phrase_repetitions or (
            count > QUALITY.min_phrase_repetitions
            and (count * n) / n_words > QUALITY.phrase_coverage_threshold
        ):
            return True, f'phrase: "{most_common_ngram[:30]}..."'

    return False, None


# One alternation per recognised delimiter pair so every empty wrapper —
# not just <think></think> — stays neutral evidence per the documented policy.
_EMPTY_THINKING_WRAPPER_RE: Final[re.Pattern[str]] = re.compile(
    "|".join(
        rf"{re.escape(start_marker)}\s*{re.escape(end_marker)}"
        for start_marker, end_marker in THINKING_TRACE_DELIMITER_PAIRS
    ),
    re.IGNORECASE,
)


def _strip_empty_thinking_wrappers(text: str) -> str:
    """Remove empty protocol wrappers before semantic and token-leak checks."""
    return _EMPTY_THINKING_WRAPPER_RE.sub(" ", text)


def _final_answer_split(
    text: str,
    *,
    delimiter_pairs: Sequence[tuple[str, str]] = THINKING_TRACE_DELIMITER_PAIRS,
    seeded_text: str = "",
) -> tuple[str, tuple[str, ...]]:
    """Return (final answer, removed trace segments) for one output.

    The segments are exactly the spans the delimiter processing removed, in
    removal order, so a caller that reports "N characters of reasoning
    omitted" or opens the trace under disclosure never has to rediscover
    the boundary by text matching — which fails when the model drafts its
    final answer inside the thinking block.
    """
    if not text:
        return text, ()
    removed: list[str] = []

    def _collect(match: re.Match[str]) -> str:
        removed.append(match.group(0))
        return " "

    view = text
    seeded_lower = seeded_text.casefold()
    for start_marker, end_marker in delimiter_pairs:
        # Complete emitted blocks (non-greedy, may span lines).
        block_re = re.compile(
            rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}",
            re.IGNORECASE | re.DOTALL,
        )
        view = block_re.sub(_collect, view)
        # A closing marker whose opener was seeded by the prompt: everything
        # from the start of the output through that first end marker is
        # reasoning that continues the seeded block.
        start_lower = start_marker.casefold()
        end_lower = end_marker.casefold()
        seeded_open = seeded_lower.rfind(start_lower) > seeded_lower.rfind(end_lower)
        if seeded_open:
            view_lower = view.casefold()
            end_position = view_lower.find(end_lower)
            if end_position >= 0 and view_lower.find(start_lower, 0, end_position) < 0:
                cut = end_position + len(end_marker)
                removed.append(view[:cut])
                view = view[cut:]
    return view.strip(), tuple(removed)


def _final_answer_view(
    text: str,
    *,
    delimiter_pairs: Sequence[tuple[str, str]] = THINKING_TRACE_DELIMITER_PAIRS,
    seeded_text: str = "",
) -> str:
    """Return the text after removing every *complete* recognised thinking trace.

    Structural checks (catalogue sections, preamble, repetition, instruction
    echo, constraints) should judge the model's final answer, not its
    reasoning. Two shapes are removed:

    - ``<start>...<end>`` blocks emitted in the output;
    - a leading ``...<end>`` tail whose ``<start>`` lives in the prompt (a
      template- or seed-opened block the model merely closed).

    Incomplete traces (a start marker with no end) are left untouched so the
    incomplete-trace observation still sees them. Raw text and markers stay
    available to callers as neutral evidence.
    """
    return _final_answer_split(text, delimiter_pairs=delimiter_pairs, seeded_text=seeded_text)[0]


@dataclass(frozen=True)
class NormalizedOutput:
    """Mechanical-analysis copy plus configured wrappers removed from consideration."""

    text: str
    removed_wrappers: tuple[str, ...] = ()


def _normalize_output_for_analysis(
    text: str,
    *,
    known_special_tokens: Sequence[str] = (),
) -> NormalizedOutput:
    """Remove only tokenizer/configured wrappers from the mechanical-analysis copy."""
    candidates = {token for token in known_special_tokens if token and token.startswith(("<", "["))}
    if not candidates:
        return NormalizedOutput(text=text.strip())

    pattern = re.compile(
        "|".join(re.escape(token) for token in sorted(candidates, key=len, reverse=True))
    )
    removed: list[str] = []

    def _remove_wrapper(match: re.Match[str]) -> str:
        removed.append(match.group(0))
        return " "

    normalized = pattern.sub(_remove_wrapper, text)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return NormalizedOutput(text=normalized, removed_wrappers=tuple(removed))


def _configured_role_boundaries(text: str, wrappers: Sequence[str]) -> list[str]:
    """Return configured conversation-role tokens that escaped into model output."""
    leading_start = len(text) - len(text.lstrip())
    boundaries: list[str] = []
    for token in wrappers:
        token_lower = token.casefold()
        position = text.find(token)
        if position < 0 or not any(
            boundary in token_lower
            for boundary in ("user", "assistant", "system", "turn", "message", "utterance")
        ):
            continue
        if "assistant" not in token_lower or position > leading_start:
            boundaries.append(token)
    return _dedupe_preserve_order(boundaries)


@dataclass(frozen=True)
class MetadataProvenance:
    """Authoritative structured context plus fallible descriptive draft fields."""

    capture_date: str | None = None
    capture_time: str | None = None
    gps: str | None = None
    draft_title: str | None = None
    draft_description: str | None = None
    draft_keywords: tuple[str, ...] = ()

    @property
    def has_authoritative_context(self) -> bool:
        return bool(self.capture_date or self.capture_time or self.gps)

    @property
    def has_draft(self) -> bool:
        return bool(self.draft_title or self.draft_description or self.draft_keywords)


def _clean_metadata_text(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" ,")
    return cleaned or None


def _build_metadata_provenance(metadata: MetadataDict | None) -> MetadataProvenance:
    if not metadata:
        return MetadataProvenance()

    title = _clean_metadata_text(metadata.get("title"))
    description = _clean_metadata_text(metadata.get("description"))
    keyword_text = _clean_metadata_text(metadata.get("keywords")) or ""
    keyword_terms = _split_catalog_keywords(keyword_text)

    return MetadataProvenance(
        capture_date=_clean_metadata_text(metadata.get("date")),
        capture_time=_clean_metadata_text(metadata.get("time")),
        gps=_clean_metadata_text(metadata.get("gps")),
        draft_title=title,
        draft_description=description,
        draft_keywords=tuple(keyword_terms),
    )


def _normalize_phrase_for_matching(text: str) -> str:
    """Normalize free-form text for alias and overlap matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.casefold())).strip()


def _split_catalog_keywords(raw_keywords: str) -> list[str]:
    """Split keyword section text into normalized keyword terms."""
    if not raw_keywords:
        return []
    keywords: list[str] = []
    for item in re.split(r"[,\n]", raw_keywords):
        cleaned: str = re.sub(r"\s+", " ", item).strip(" -*•\t")
        if cleaned:
            keywords.append(cleaned)
    return keywords


def _repeated_catalog_keyword(text: str) -> str | None:
    """Return a repeated keyword when a catalog list is dominated by duplicates."""
    raw_keywords = _extract_catalog_sections(text).get("keywords", "")
    keywords = [
        _normalize_phrase_for_matching(item) for item in _split_catalog_keywords(raw_keywords)
    ]
    keywords = [item for item in keywords if item]
    if len(keywords) < QUALITY.min_catalog_keywords_for_repeat:
        return None
    counts = Counter(keywords)
    repeated, count = counts.most_common(1)[0]
    duplicate_ratio = (len(keywords) - len(counts)) / len(keywords)
    return (
        repeated
        if count >= QUALITY.min_catalog_keyword_repetitions
        and duplicate_ratio >= QUALITY.catalog_keyword_duplicate_ratio
        else None
    )


CATALOG_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?im)^[ \t]*(?:(?:#{1,6})[ \t]+|[>*-][ \t]*)?"
    r"\*{0,2}[ \t]*(title|description|keywords)"
    r"(?::[ \t]*\*{0,2}|\*{0,2}[ \t]*:)[ \t]*(.*)$",
)


def _extract_catalog_sections(text: str) -> dict[str, str]:
    """Extract ``Title/Description/Keywords`` sections from model output."""
    if not text:
        return {}

    matches: list[re.Match[str]] = list(CATALOG_SECTION_PATTERN.finditer(text))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        label: str = match.group(1).casefold()
        if label in sections:
            continue
        section_line: str = match.group(2).strip()
        next_start: int = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        trailing: str = text[match.end() : next_start].strip()
        combined: str = "\n".join(part for part in (section_line, trailing) if part).strip()
        sections[label] = combined
    return sections


def _missing_catalog_sections(text: str) -> list[str]:
    """Return requested catalog sections that are absent or structurally empty."""
    sections: dict[str, str] = _extract_catalog_sections(text)
    return [
        section for section in ("title", "description", "keywords") if not sections.get(section)
    ]


@dataclass(frozen=True)
class ReasoningOutputSignals:
    """Record explicit thinking trace delimiters for thinking-model runs."""

    has_thinking_trace: bool = False
    thinking_trace_incomplete: bool = False
    thinking_only_output: bool = False
    thinking_trace_markers: tuple[str, ...] = ()


def _detect_reasoning_output(
    text: str,
    *,
    delimiter_pairs: Sequence[tuple[str, str]] = THINKING_TRACE_DELIMITER_PAIRS,
    seeded_text: str = "",
) -> ReasoningOutputSignals:
    """Detect explicit reasoning delimiters without inferring policy from model names."""
    if not text:
        return ReasoningOutputSignals()

    semantic_text = text
    thinking_trace_markers: list[str] = []
    for start_marker, end_marker in delimiter_pairs:
        empty_wrapper = re.compile(
            rf"{re.escape(start_marker)}\s*{re.escape(end_marker)}",
            re.IGNORECASE,
        )
        if empty_wrapper.search(semantic_text):
            thinking_trace_markers.extend((start_marker, end_marker))
        semantic_text = empty_wrapper.sub(" ", semantic_text)
    text_lower: str = semantic_text.casefold()
    seeded_lower = seeded_text.casefold()
    thinking_trace_incomplete = False
    thinking_only_output = bool(thinking_trace_markers) and not semantic_text.strip()
    for start_marker, end_marker in delimiter_pairs:
        start_lower = start_marker.casefold()
        end_lower = end_marker.casefold()
        start_position = text_lower.find(start_lower)
        seeded_start_position = seeded_lower.rfind(start_lower)
        seeded_end_position = seeded_lower.rfind(end_lower)
        seeded_trace_open = (
            seeded_start_position >= 0 and seeded_end_position < seeded_start_position
        )
        if start_position < 0 and not seeded_trace_open:
            continue
        thinking_trace_markers.append(start_marker)
        end_position = text_lower.find(
            end_lower,
            start_position + len(start_marker) if start_position >= 0 else 0,
        )
        if end_position >= 0:
            thinking_trace_markers.append(end_marker)
            final_text = semantic_text[end_position + len(end_marker) :]
            thinking_only_output = thinking_only_output or not bool(
                re.search(r"[^\W_]", final_text, re.UNICODE)
            )
        else:
            thinking_trace_incomplete = True

    return ReasoningOutputSignals(
        has_thinking_trace=bool(thinking_trace_markers),
        thinking_trace_incomplete=thinking_trace_incomplete,
        thinking_only_output=thinking_only_output,
        thinking_trace_markers=tuple(_dedupe_preserve_order(thinking_trace_markers)),
    )


def _estimate_prompt_tokens_from_text(prompt: str | None) -> int | None:
    """Estimate text-only prompt tokens with a lightweight word-based heuristic."""
    if not prompt:
        return None
    words = len(prompt.split())
    if words == 0:
        return None
    return max(math.ceil(words * QUALITY.prompt_word_to_token_ratio), 1)


def _detect_likely_cutoff(
    text: str,
    *,
    generated_tokens: int | None,
    requested_max_tokens: int | None,
    is_repetitive: bool,
    missing_sections: Sequence[str],
    thinking_trace_incomplete: bool = False,
    assessment_profile: AssessmentProfile = "general",
) -> tuple[bool, list[str]]:
    """Detect likely early termination at the generation cap.

    Returns ``(hit_cap, reasons)`` where *reasons* may include degradation
    evidence such as ``"missing_sections"`` or ``"repetitive_tail"``.  A hit
    with no degradation reasons means the model produced structurally sound
    output that merely ran out of budget.
    """
    if generated_tokens is None or requested_max_tokens is None or requested_max_tokens <= 0:
        return False, []
    if generated_tokens < requested_max_tokens:
        return False, []

    tail = text.strip()[-QUALITY.cutoff_tail_chars :].strip()
    reasons: list[str] = []
    if missing_sections and text.strip():
        reasons.append("missing_sections")
    if is_repetitive:
        reasons.append("repetitive_tail")
    if thinking_trace_incomplete:
        reasons.append("incomplete_thinking_trace")
    if tail and assessment_profile == "metadata":
        if re.search(r"(title|description|keywords)\s*:?\s*$", tail, re.IGNORECASE):
            reasons.append("unfinished_section")
        if re.search(r"(?:^|\n)\s*(?:[-+*]|\d+[.)])(?:\s+\*{1,3})?\s*$", tail):
            reasons.append("dangling_markdown")
        # A capped answer ending mid-list (e.g. "Keywords: ..., Clouds,") was
        # still emitting comma-separated items when the budget ran out.
        if re.search(r"[,;]\s*$", tail):
            reasons.append("unfinished_list")
    return True, _dedupe_preserve_order(reasons)


# =============================================================================
# SECTION: METRICS, SCORING & FIELD FORMATTING
# =============================================================================
# These detect issues that are likely bugs in mlx-vlm or model integration,
# NOT inherent model quality problems. Separating them helps users know
# whether to report issues upstream vs. use a different model.

SPECIAL_TOKEN_LEAK_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"<end_of_turn>", "<end_of_turn>"),
    (r"</s>(?!\w)", "</s>"),
    (r"<s>(?!\w)", "<s>"),
    (r"\[INST\]", "[INST]"),
    (r"\[/INST\]", "[/INST]"),
    (re.escape(DEFAULT_THINKING_END_MARKER), DEFAULT_THINKING_END_MARKER),
    (r"\[PAD\]", "[PAD]"),
    (r"\[CLS\]", "[CLS]"),
    (r"\[SEP\]", "[SEP]"),
)
CONTROL_TOKEN_WRAPPER_RE: Final[re.Pattern[str]] = re.compile(
    r"<\|[^\s<>|]{1,80}(?:\|>|>)|<[^\s<>|]{1,80}\|>",
)


def _detect_special_token_leakage(text: str) -> tuple[bool, list[str]]:
    """Detect special/control tokens that leaked into output.

    These indicate the generation stop logic failed to halt at EOS/EOT tokens,
    or the output wasn't properly post-processed to strip special tokens.

    Args:
        text: Generated text to check

    Returns:
        Tuple of (has_leakage, list of leaked tokens found)
    """
    if not text:
        return False, []

    leaked_tokens: list[str] = []

    for pattern, token_name in SPECIAL_TOKEN_LEAK_PATTERNS:
        if re.search(pattern, text):
            leaked_tokens.append(token_name)

    leaked_tokens.extend(match.group(0) for match in CONTROL_TOKEN_WRAPPER_RE.finditer(text))

    deduplicated = _dedupe_preserve_order(leaked_tokens)
    return bool(deduplicated), deduplicated


# =============================================================================
# CATALOGING QUALITY METRICS, LIBRARY VERSIONS & PROVENANCE SNAPSHOTS
# =============================================================================


@dataclass(frozen=True)
class GenerationQualityAnalysis:
    """Mechanical observations and runtime facts used by ``ResultAssessment``."""

    is_repetitive: bool
    repeated_token: str | None
    assessment_profile: AssessmentProfile = "general"
    missing_sections: list[str] = dataclass_field(default_factory=list)
    has_thinking_trace: bool = False
    thinking_trace_incomplete: bool = False
    thinking_only_output: bool = False
    thinking_trace_markers: list[str] = dataclass_field(default_factory=list)
    word_count: int = 0
    prompt_checks_ran: bool = False
    likely_capped: bool = False
    token_cap_reasons: list[str] = dataclass_field(default_factory=list)
    prompt_tokens_total: int | None = None
    prompt_tokens_text_est: int | None = None
    prompt_tokens_nontext_est: int | None = None
    prompt_tokens_text_source: Literal["tokenizer", "heuristic"] | None = None
    prompt_tokens_text_exact_rejected: int | None = None
    special_token_wrappers: list[str] = dataclass_field(default_factory=list)
    configured_generation_wrappers: list[str] = dataclass_field(default_factory=list)
    role_boundary_tokens: list[str] = dataclass_field(default_factory=list)
    title_word_count: int | None = None
    keyword_count: int | None = None
    duplicate_keywords: list[str] = dataclass_field(default_factory=list)
    unexpected_special_tokens: list[str] = dataclass_field(default_factory=list)
    # The final answer appears twice, verbatim after whitespace collapsing;
    # the separator is whatever sat between the copies (often a leaked
    # control token such as </think>), or "" for back-to-back copies.
    duplicated_answer_separator: str | None = None


_DUPLICATED_ANSWER_MIN_CHARS: Final[int] = 80
_DUPLICATED_ANSWER_MAX_SEPARATOR_CHARS: Final[int] = 64


def _detect_duplicated_answer(text: str, *, is_repetitive: bool = False) -> str | None:
    """Return the separator between two verbatim copies of the answer, else ``None``.

    Whitespace is collapsed before comparison. The first copy must be at
    least ``_DUPLICATED_ANSWER_MIN_CHARS`` long and the separator short, so a
    genuinely repeated sentence inside prose does not qualify; degenerate
    looping is the repetition detector's job, not this one's.
    """
    if is_repetitive:
        return None
    collapsed = " ".join(text.split())
    length = len(collapsed)
    if length < 2 * _DUPLICATED_ANSWER_MIN_CHARS:
        return None
    half = (length + 1) // 2
    for split in range(half, min(length, half + _DUPLICATED_ANSWER_MAX_SEPARATOR_CHARS + 1)):
        second = collapsed[split:]
        if len(second) < _DUPLICATED_ANSWER_MIN_CHARS or not collapsed.startswith(second):
            continue
        return collapsed[len(second) : split].strip()
    return None


def _split_prompt_tokens(
    *,
    prompt_tokens: int | None,
    prompt: str | None,
    prompt_text_tokens: int | None,
) -> tuple[int | None, int | None, Literal["tokenizer", "heuristic"] | None, int | None]:
    """Split total prompt tokens into (text, non-text, source, rejected exact).

    Prefers an exact tokenizer count; either count must satisfy
    ``0 <= text <= total`` or the split is unavailable. An exact count that
    fails the invariant is retained as the rejected evidence value — it would
    otherwise publish an impossible split (e.g. "5 = 7 text + 0 non-text").
    """
    source: Literal["tokenizer", "heuristic"] | None
    rejected: int | None = None
    exact_is_consistent = prompt_text_tokens is not None and (
        prompt_tokens is None or 0 <= prompt_text_tokens <= prompt_tokens
    )
    if prompt_text_tokens is not None and exact_is_consistent:
        text_est: int | None = prompt_text_tokens
        source = "tokenizer"
    else:
        rejected = prompt_text_tokens
        text_est = _estimate_prompt_tokens_from_text(prompt)
        source = "heuristic" if text_est is not None else None
    if text_est is not None and prompt_tokens is not None and not 0 <= text_est <= prompt_tokens:
        # The same invariant binds the heuristic.
        text_est = None
        source = None
    nontext_est = (
        max(prompt_tokens - text_est, 0)
        if (prompt_tokens is not None and text_est is not None)
        else None
    )
    return text_est, nontext_est, source, rejected


def analyze_generation_text(  # noqa: PLR0913 - one analysis pass over every prompt-contract knob  # skylos: ignore[SKY-C303]
    text: str,
    generated_tokens: int | None,
    prompt_tokens: int | None = None,
    prompt: str | None = None,
    requested_max_tokens: int | None = None,
    assessment_profile: AssessmentProfile = "general",
    known_special_tokens: Sequence[str] = (),
    configured_generation_wrappers: Sequence[str] = (),
    thinking_trace_delimiters: Sequence[tuple[str, str]] = THINKING_TRACE_DELIMITER_PAIRS,
    seeded_thinking_text: str = "",
    prompt_text_tokens: int | None = None,
) -> GenerationQualityAnalysis:
    """Collect mechanical output observations and recorded runtime facts.

    ``prompt_text_tokens`` is the exact tokenizer count of the rendered prompt
    when the caller has one; otherwise a word-ratio heuristic estimates it.
    """
    # Thinking delimiters — every recognised pair plus any custom configured
    # pair — are structural markers that ``_final_answer_view`` must still see
    # to recognise a complete trace. Never let the generic special-token strip
    # remove them, even when the tokenizer declares them as special tokens.
    protected_markers = {marker for pair in thinking_trace_delimiters for marker in pair if marker}
    normalized = _normalize_output_for_analysis(
        text,
        known_special_tokens=[
            token for token in known_special_tokens if token not in protected_markers
        ],
    )
    # Final-answer semantic copy: drop complete thinking traces (emitted or
    # prompt-seeded), empty thinking wrappers, and generic control-token
    # wrappers before structural analysis, so a model that reasoned and then
    # produced the requested fields — or produced them inside a leaked wrapper
    # (e.g. "<|begin_of_box|>Title: ...") — is assessed on those fields. The
    # trace and any leak are still detected and reported from the raw text.
    analysis_text = CONTROL_TOKEN_WRAPPER_RE.sub(
        " ",
        _strip_empty_thinking_wrappers(
            _final_answer_view(
                normalized.text,
                delimiter_pairs=thinking_trace_delimiters,
                seeded_text=seeded_thinking_text,
            )
        ),
    )
    is_repetitive, repeated_token = _detect_repetitive_output(analysis_text)
    reasoning = _detect_reasoning_output(
        text, delimiter_pairs=thinking_trace_delimiters, seeded_text=seeded_thinking_text
    )
    sections = _extract_catalog_sections(analysis_text) if assessment_profile == "metadata" else {}
    missing_sections = (
        _missing_catalog_sections(analysis_text) if assessment_profile == "metadata" else []
    )
    keywords = _split_catalog_keywords(sections.get("keywords", ""))
    keyword_counts = Counter(filter(None, map(_normalize_phrase_for_matching, keywords)))
    (
        prompt_tokens_text_est,
        prompt_tokens_nontext_est,
        prompt_tokens_text_source,
        prompt_tokens_text_exact_rejected,
    ) = _split_prompt_tokens(
        prompt_tokens=prompt_tokens, prompt=prompt, prompt_text_tokens=prompt_text_tokens
    )
    likely_capped, cutoff_reasons = _detect_likely_cutoff(
        analysis_text,
        generated_tokens=generated_tokens,
        requested_max_tokens=requested_max_tokens,
        is_repetitive=is_repetitive,
        missing_sections=missing_sections,
        thinking_trace_incomplete=reasoning.thinking_trace_incomplete,
        assessment_profile=assessment_profile,
    )
    leakage_text = text
    for token in normalized.removed_wrappers:
        leakage_text = leakage_text.replace(token, " ")
    _has_special_tokens, unexpected_special_tokens = _detect_special_token_leakage(
        _strip_empty_thinking_wrappers(leakage_text),
    )
    # An empty generated wrapper from a reports_when_empty pair is still
    # unconsumed transport syntax. Keep it out of structural parsing, but
    # retain both markers as integration evidence.
    empty_reported_markers = tuple(
        marker
        for pair, empty_wrapper_re in _REPORTING_EMPTY_WRAPPER_PATTERNS
        if empty_wrapper_re.search(text)
        for marker in (pair.start, pair.end)
    )
    unexpected_special_tokens.extend(empty_reported_markers)
    if reasoning.has_thinking_trace:
        # A legitimate detected trace neutralises its own delimiters, including
        # <|...|>-style pairs where the generic control-token regex captures
        # only a prefix of the marker (e.g. "<|channel>" of "<|channel>thought").
        thinking_markers = {DEFAULT_THINKING_END_MARKER, *reasoning.thinking_trace_markers}
        unexpected_special_tokens = [
            wrapper
            for wrapper in unexpected_special_tokens
            if wrapper in empty_reported_markers
            or not any(wrapper in marker for marker in thinking_markers)
        ]
    unexpected_special_tokens = _dedupe_preserve_order(unexpected_special_tokens)
    present_configured_wrappers = [
        wrapper
        for wrapper in _dedupe_preserve_order(configured_generation_wrappers)
        if wrapper and wrapper in text
    ]

    return GenerationQualityAnalysis(
        is_repetitive=is_repetitive,
        repeated_token=repeated_token,
        assessment_profile=assessment_profile,
        missing_sections=missing_sections,
        has_thinking_trace=reasoning.has_thinking_trace,
        thinking_trace_incomplete=reasoning.thinking_trace_incomplete,
        thinking_only_output=reasoning.thinking_only_output,
        thinking_trace_markers=list(reasoning.thinking_trace_markers),
        word_count=len(re.findall(r"\b\w+\b", analysis_text)),
        prompt_checks_ran=bool(prompt),
        likely_capped=likely_capped,
        token_cap_reasons=cutoff_reasons,
        prompt_tokens_total=prompt_tokens,
        prompt_tokens_text_est=prompt_tokens_text_est,
        prompt_tokens_nontext_est=prompt_tokens_nontext_est,
        prompt_tokens_text_source=prompt_tokens_text_source,
        prompt_tokens_text_exact_rejected=prompt_tokens_text_exact_rejected,
        special_token_wrappers=list(normalized.removed_wrappers),
        configured_generation_wrappers=present_configured_wrappers,
        role_boundary_tokens=_configured_role_boundaries(text, normalized.removed_wrappers),
        title_word_count=len(re.findall(r"\b\w+(?:[-\u2019']\w+)*\b", sections["title"]))
        if "title" in sections
        else None,
        keyword_count=len(keywords) if "keywords" in sections else None,
        duplicate_keywords=[word for word, count in keyword_counts.items() if count > 1],
        unexpected_special_tokens=unexpected_special_tokens,
        duplicated_answer_separator=_detect_duplicated_answer(
            analysis_text, is_repetitive=is_repetitive
        ),
    )


def local_now_str(fmt: str = LOCAL_TIMESTAMP_FORMAT) -> str:
    """Return localized current time as a formatted string.

    Centralizes timestamp formatting so report generators and version info
    stay consistent and makes future changes (e.g. adding UTC or ISO8601
    variants) trivial.
    """
    return datetime.now().astimezone().strftime(fmt)


def _parse_local_timestamp(value: object, *, embedded: bool = False) -> datetime | None:
    """Parse one project timestamp, optionally from surrounding log text."""
    if not isinstance(value, str):
        return None
    match = (_LOCAL_TIMESTAMP_RE.search if embedded else _LOCAL_TIMESTAMP_RE.fullmatch)(value)
    if match is not None:
        with suppress(ValueError):
            return datetime.strptime(match[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return None


# Field name patterns for format dispatch
_TIME_FIELDS: frozenset[str] = frozenset(
    {"total_time", "generation_time", "model_load_time"},
)


def _coerce_numeric_value(value: object) -> float | None:
    """Return a float for numeric or numeric-string values, else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped.replace(",", ""))
        except ValueError:
            return None
    return None


def format_field_value(field_name: str, value: MetricValue) -> str:
    """Normalize values for report/log rendering using field-aware numeric rules.

    Handles memory/time/TPS conventions, preserves non-numeric strings as-is,
    and returns ``""`` for null values.
    """
    formatted_value: str
    if value is None:
        formatted_value = ""
    elif isinstance(value, bool):
        formatted_value = str(value)
    else:
        numeric_value = _coerce_numeric_value(value)
        if numeric_value is not None:
            if field_name.endswith("_memory"):
                formatted_value = _format_memory_value_gb(numeric_value)
            elif field_name.endswith("_tps"):
                formatted_value = _format_tps(numeric_value)
            elif field_name in _TIME_FIELDS:
                formatted_value = _format_time_seconds(numeric_value)
            else:
                formatted_value = fmt_num(numeric_value)
        elif isinstance(value, str):
            formatted_value = value
        else:
            formatted_value = str(value)

    return formatted_value


def _format_peak_memory_context(
    peak_memory_gb: float | None,
    recommended_working_set_bytes: int | None,
) -> str:
    """Format peak memory with optional Metal working-set context."""
    if peak_memory_gb is None:
        return ""
    peak = format_field_value("peak_memory", peak_memory_gb)
    if not peak:
        return ""
    percentage = _peak_memory_working_set_pct(
        peak_memory_gb,
        recommended_working_set_bytes,
    )
    if percentage is None or recommended_working_set_bytes is None:
        return peak
    working_set_gb = recommended_working_set_bytes / (1024**3)
    return (
        f"{peak} GB ({fmt_num(percentage)}% of {fmt_num(working_set_gb)} GB "
        "recommended working set)"
    )


# --- Console UI helpers (rules/separators) ---


def get_terminal_width(min_width: int = 60, max_width: int = 120) -> int:
    """Return a clamped terminal width for formatting.

    Uses shutil.get_terminal_size with a sensible fallback; clamps the
    value to avoid excessive lines on very wide terminals and poor display
    on very narrow ones.
    """
    # If an explicit override is set (via --width), prefer it and do not apply
    # per-call max_width limits; still enforce a minimal practical width.
    if WIDTH_OVERRIDE is not None and WIDTH_OVERRIDE > 0:
        return max(min_width, WIDTH_OVERRIDE)
    # Support environment-based override as well (useful in CI): MLX_VLM_WIDTH
    env_width = os.getenv("MLX_VLM_WIDTH")
    if env_width:
        try:
            return max(min_width, int(env_width))
        except ValueError:
            pass
    try:
        width = shutil.get_terminal_size(fallback=(FORMATTING.generation_wrap_width, 24)).columns
    except OSError:
        width = FORMATTING.generation_wrap_width
    return max(min_width, min(width, max_width))


def _log_wrapped_error(label: str, value: str) -> None:
    """Log error with simple formatting for readability."""
    width = get_terminal_width(max_width=100)

    # Label
    logger.error(label, extra={"style_hint": LogStyles.ERROR, "style_prefix": "ERROR"})

    # Content with wrapping and indentation
    cont_indent = "  "
    cont_avail = max(20, width - len(cont_indent))
    lines = value.splitlines() or [""]
    for original_line in lines:
        if not original_line.strip():
            continue
        wrapped = textwrap.wrap(
            original_line,
            width=cont_avail,
            break_long_words=False,
            break_on_hyphens=False,
            replace_whitespace=False,
        ) or [""]
        for wline in wrapped:
            formatted_line = f"{cont_indent}{wline}"
            logger.error(
                formatted_line,
                extra={"style_hint": LogStyles.DETAIL},
            )


def _apply_cli_output_preferences(args: argparse.Namespace) -> None:
    """Apply color and width preferences based on CLI flags.

    - Honors --no-color / --force-color to toggle Rich console styling
    - Applies --width via MLX_VLM_WIDTH env var for child processes too
    """
    if args.no_color:
        _set_rich_color_enabled(enabled=False)
    elif args.force_color:
        _set_rich_color_enabled(enabled=True)

    # Width override: prefer CLI value; store in env so subprocesses inherit it
    if args.width is not None:
        try:
            os.environ["MLX_VLM_WIDTH"] = str(int(args.width))
        except (TypeError, ValueError):
            # Invalid width -> remove override and fall back to detection
            os.environ.pop("MLX_VLM_WIDTH", None)
        else:
            if args.verbose:
                logger.debug(
                    "Width override set to %s columns",
                    os.environ.get("MLX_VLM_WIDTH"),
                )


def log_rule(
    width: int = FORMATTING.generation_wrap_width,
    *,
    char: str = "─",
    style: str | None = None,
    bold: bool = False,
    level: int = logging.INFO,
    pre_newline: bool = False,
    post_newline: bool = False,
) -> None:
    """Log a horizontal rule line with optional Rich styling.

    Uses unicode box-drawing characters for better visual separation.
    Keeps a single place for styling separators to ensure consistency.
    """
    if pre_newline:
        logger.log(level, "")

    line = char * max(1, width)
    extra: dict[str, object] = {"style_hint": LogStyles.RULE}
    if bold:
        style = f"bold {style}".strip() if style and "bold" not in style else style or "bold"
    if style:
        extra["style_override"] = style
    logger.log(level, line, extra=extra)

    if post_newline:
        logger.log(level, "")


# --- Utility Functions ---


def get_library_versions() -> LibraryVersionDict:
    """Return versions of key libraries as a dictionary, using None for missing."""

    def _get_version(pkg_name: str, fallback: str | None = None) -> str | None:
        try:
            return version(pkg_name)
        except PackageNotFoundError:
            return fallback

    def _none_if_na(v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip() if isinstance(v, str) else str(v).strip()
        if not s or s == NOT_AVAILABLE or s.startswith("N/A"):
            return None
        return s

    # Get MLX version (prefer metadata, fallback to module attribute)
    mlx_ver = _get_version("mlx", getattr(mx, "__version__", None))

    # Get MLX-VLM version
    mlx_vlm_ver = _get_version("mlx-vlm", vlm_version if "vlm_version" in globals() else None)

    return {
        "numpy": _none_if_na(_get_version("numpy", numpy_version)),
        "mlx": _none_if_na(mlx_ver),
        "mlx-metal": _none_if_na(_get_version("mlx-metal")),
        "mlx-vlm": _none_if_na(mlx_vlm_ver),
        "mlx-audio": _none_if_na(_get_version("mlx-audio")),
        "huggingface-hub": _none_if_na(_get_version("huggingface-hub", hf_version)),
        "transformers": _none_if_na(_get_version("transformers")),
        "tokenizers": _none_if_na(_get_version("tokenizers")),
        "Pillow": _none_if_na(_get_version("Pillow", pillow_version)),
    }


def _distribution_metadata_file_path(
    package_distribution: Distribution,
    metadata_filename: str,
) -> Path | None:
    """Resolve an exact dist-info metadata file path from distribution records."""
    try:
        distribution_files = package_distribution.files
    except (OSError, RuntimeError, ValueError):
        return None
    if distribution_files is None:
        return None

    for distribution_file in distribution_files:
        if distribution_file.name != metadata_filename:
            continue
        if not distribution_file.parent.name.endswith(".dist-info"):
            continue
        try:
            return Path(str(package_distribution.locate_file(distribution_file)))
        except (OSError, RuntimeError, ValueError):
            return None
    return None


def _distribution_text_file(distribution_name: str, filename: str) -> str | None:
    """Read allowlisted distribution metadata text without importing the package."""
    if filename not in ALLOWED_DISTRIBUTION_TEXT_FILES:
        return None

    try:
        package_distribution = distribution(distribution_name)
    except PackageNotFoundError:
        return None
    metadata_path = _distribution_metadata_file_path(
        package_distribution,
        DISTRIBUTION_DIRECT_URL_METADATA_FILE,
    )
    if metadata_path is None:
        return None
    try:
        return _read_text_file(
            metadata_path,
            max_bytes=MAX_DISTRIBUTION_TEXT_FILE_BYTES,
        )
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _distribution_is_editable(distribution_name: str) -> bool:
    """Return True when package metadata marks a distribution as editable."""
    direct_url_text = _distribution_text_file(
        distribution_name, DISTRIBUTION_DIRECT_URL_METADATA_FILE
    )
    if not direct_url_text:
        return False
    try:
        direct_url = json.loads(direct_url_text)
    except json.JSONDecodeError:
        return False
    if not isinstance(direct_url, dict):
        return False
    dir_info = direct_url.get("dir_info")
    return isinstance(dir_info, dict) and bool(dir_info.get("editable"))


def _distribution_direct_url(distribution_name: str) -> DistributionDirectUrlRecord | None:
    """Return parsed PEP 610 direct-URL metadata for an installed distribution."""
    text = _distribution_text_file(distribution_name, DISTRIBUTION_DIRECT_URL_METADATA_FILE)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    record: DistributionDirectUrlRecord = {}
    raw_url = payload.get("url")
    if isinstance(raw_url, str):
        record["url"] = raw_url
    raw_dir_info = payload.get("dir_info")
    if isinstance(raw_dir_info, dict):
        dir_info: DirectUrlDirInfo = {}
        editable = raw_dir_info.get("editable")
        if isinstance(editable, bool):
            dir_info["editable"] = editable
        record["dir_info"] = dir_info
    raw_vcs_info = payload.get("vcs_info")
    if isinstance(raw_vcs_info, dict):
        vcs_info: DirectUrlVcsInfo = {}
        vcs = raw_vcs_info.get("vcs")
        if isinstance(vcs, str):
            vcs_info["vcs"] = vcs
        requested_revision = raw_vcs_info.get("requested_revision")
        if isinstance(requested_revision, str):
            vcs_info["requested_revision"] = requested_revision
        commit_id = raw_vcs_info.get("commit_id")
        if isinstance(commit_id, str):
            vcs_info["commit_id"] = commit_id
        record["vcs_info"] = vcs_info
    subdirectory = payload.get("subdirectory")
    if isinstance(subdirectory, str):
        record["subdirectory"] = subdirectory
    return record


def _direct_url_source_path(payload: DistributionDirectUrlRecord | None) -> Path | None:
    """Resolve a local file URL from installed metadata without network access."""
    raw_url = payload.get("url") if payload is not None else None
    if not isinstance(raw_url, str):
        return None
    parsed = urlparse(raw_url)
    if parsed.scheme != "file":
        return None
    return Path(unquote(parsed.path))


def _local_source_revision(path: Path) -> str | None:
    """Return the Git revision for an existing local source directory."""
    if not path.is_dir():
        return None
    return _run_macos_toolchain_command(("git", "-C", str(path), "rev-parse", "HEAD"))


_COMPONENT_PROVENANCE_CACHE: dict[
    tuple[tuple[str, str | None], ...], dict[str, ComponentProvenanceRecord]
] = {}


def _collect_component_provenance(
    versions: Mapping[str, str | None] | None = None,
) -> dict[str, ComponentProvenanceRecord]:
    """Collect publication-safe local install provenance without network access.

    Memoised per process on the resolved version map: the answer comes from
    installed-distribution metadata and ``git rev-parse`` in editable
    checkouts, which do not change during a run, and every report surface
    asks for it.
    """
    resolved_versions = dict(versions or get_library_versions())
    check_models_version = _collect_check_models_provenance().get("version")
    resolved_versions.setdefault(
        "check_models",
        check_models_version if isinstance(check_models_version, str) else None,
    )
    cache_key = tuple(sorted(resolved_versions.items()))
    if (cached := _COMPONENT_PROVENANCE_CACHE.get(cache_key)) is not None:
        return {name: record.copy() for name, record in cached.items()}
    provenance: dict[str, ComponentProvenanceRecord] = {}
    for name, component_version in resolved_versions.items():
        direct = _distribution_direct_url(name)
        source_path = _direct_url_source_path(direct)
        dir_info = direct.get("dir_info") if direct is not None else None
        editable = dir_info is not None and dir_info.get("editable") is True
        install_type: ComponentInstallType
        if editable:
            install_type = "editable"
        elif name == "check_models" and source_path is None:
            install_type = "source-tree"
            source_path = _REPO_ROOT
        elif _distribution_location(name) is not None:
            install_type = "wheel"
        else:
            install_type = "unknown"
        if source_path is None:
            location = _distribution_location(name)
            source_path = Path(location) if location else None
        vcs_info = direct.get("vcs_info") if direct is not None else None
        vcs_revision = vcs_info.get("commit_id") if vcs_info is not None else None
        raw_direct_url = direct.get("url") if direct is not None else None
        provenance[name] = {
            "version": component_version,
            "install_type": install_type,
            "source_location": (
                _home_relative_report_text(str(source_path)) if source_path is not None else None
            ),
            "source_revision": (
                _local_source_revision(source_path)
                if source_path is not None and install_type in {"editable", "source-tree"}
                else None
            ),
            "direct_url": (
                _home_relative_report_text(raw_direct_url)
                if isinstance(raw_direct_url, str)
                else None
            ),
            "vcs_revision": vcs_revision,
        }
    _COMPONENT_PROVENANCE_CACHE[cache_key] = provenance
    return {name: record.copy() for name, record in provenance.items()}


def _distribution_location(distribution_name: str) -> str | None:
    """Return the installed distribution root path when metadata is available."""
    try:
        package_distribution = distribution(distribution_name)
    except PackageNotFoundError:
        return None
    try:
        return str(Path(str(package_distribution.locate_file(""))).resolve())
    except (OSError, RuntimeError, ValueError):
        return str(package_distribution.locate_file(""))


def _format_artifact_fingerprint(path: Path) -> str | None:
    """Format an artifact path with size and SHA256 for diagnostics."""
    if not path.is_file():
        return None
    try:
        size_bytes = path.stat().st_size
    except OSError:
        size_text = "size unavailable"
    else:
        size_text = f"{size_bytes:,} bytes"
    digest = _sha256_file(path)
    hash_text = f", sha256={digest}" if digest else ""
    return f"{path} ({size_text}{hash_text})"


def _get_mlx_backend_artifact_info() -> dict[str, str]:
    """Return MLX backend artifact provenance for report diagnostics."""
    info: dict[str, str] = {}
    if mx is None:
        info["MLX Backend"] = "mlx.core unavailable"
        return info

    mlx_editable = _distribution_is_editable("mlx")
    info["MLX Install Type"] = "editable local source" if mlx_editable else "wheel/site-packages"

    mlx_location = _distribution_location("mlx")
    if mlx_location:
        info["MLX Distribution Root"] = mlx_location

    mlx_metal_location = _distribution_location("mlx-metal")
    if mlx_metal_location:
        info["mlx-metal Distribution Root"] = mlx_metal_location
    elif mlx_editable:
        info["mlx-metal Distribution"] = "not installed; local editable mlx supplies backend"
    else:
        info["mlx-metal Distribution"] = "not installed"

    core_file = getattr(mx, "__file__", None)
    if not core_file:
        return info

    try:
        core_path = Path(core_file).resolve()
    except (OSError, RuntimeError, ValueError):
        core_path = Path(str(core_file))
    info["MLX Core Extension"] = str(core_path)

    mlx_package_dir = core_path.parent
    artifact_paths = (
        ("MLX Metallib", mlx_package_dir / "lib" / "mlx.metallib"),
        ("MLX libmlx.dylib", mlx_package_dir / "lib" / "libmlx.dylib"),
    )
    for label, artifact_path in artifact_paths:
        artifact_fingerprint = _format_artifact_fingerprint(artifact_path)
        if artifact_fingerprint:
            info[label] = artifact_fingerprint
        else:
            info[label] = f"missing at {artifact_path}"

    return info


def _is_version_at_least(installed: str, minimum: str) -> bool:
    """Return whether ``installed`` satisfies ``minimum`` using PEP 440 semantics."""
    try:
        is_at_least: bool = Version(installed) >= Version(minimum)
    except InvalidVersion:
        # An unparseable installed version cannot be shown to satisfy the floor.
        return False
    else:
        return is_at_least


def _collect_upstream_requirements(
    versions: LibraryVersionDict,
) -> dict[str, tuple[str, set[str]]]:
    """Collect package floors implied by installed stacks and project policy."""
    requirements: dict[str, tuple[str, set[str]]] = {}

    def _record_requirement(package: str, minimum: str, source_stack: str) -> None:
        current = requirements.get(package)
        if current is None:
            requirements[package] = (minimum, {source_stack})
            return

        current_minimum, current_sources = current
        merged_sources = current_sources | {source_stack}
        if _is_version_at_least(minimum, current_minimum):
            requirements[package] = (minimum, merged_sources)
        else:
            requirements[package] = (current_minimum, merged_sources)

    for package_name, minimum_version in PROJECT_RUNTIME_STACK_MINIMUMS.items():
        _record_requirement(package_name, minimum_version, "check_models")

    mlx_vlm_version = versions.get("mlx-vlm")
    if mlx_vlm_version:
        # Upstream mlx-vlm's own floors (its requirements.txt).
        for package_name, minimum_version in UPSTREAM_MLX_VLM_MINIMUMS.items():
            _record_requirement(package_name, minimum_version, "mlx-vlm")

    return requirements


def _detect_upstream_version_issues(versions: LibraryVersionDict) -> list[str]:
    """Return compatibility issues against current package minimums."""
    issues: list[str] = []
    requirements = _collect_upstream_requirements(versions)

    for package, (minimum, sources) in sorted(requirements.items()):
        source_label = ", ".join(sorted(sources))
        installed = versions.get(package)
        if installed is None:
            issues.append(
                f"{package} is missing; {source_label} expects {package}>={minimum}.",
            )
            continue

        if not _is_version_at_least(installed, minimum):
            issues.append(
                f"{package}=={installed} is below minimum {minimum} required by {source_label}.",
            )

    return issues


# The drift detector checks only the surface check_models actually calls.
# _GENERATE_CALL_ARGS are the call-site positional/required arguments;
# _SENT_GENERATE_KEYWORDS mirrors _build_generate_kwargs /
# _build_generate_extra_kwargs exactly (locked by a builder-parity test), so
# upstream parameters this harness never passes cannot raise false drift.
_GENERATE_CALL_ARGS: Final[tuple[str, ...]] = ("model", "processor", "prompt", "image")
_SENT_GENERATE_KEYWORDS: Final[tuple[str, ...]] = (
    # Always sent by _build_generate_kwargs
    "verbose",
    "temperature",
    "top_p",
    "repetition_penalty",
    "repetition_context_size",
    "seed",
    "presence_penalty",
    "presence_context_size",
    "frequency_penalty",
    "frequency_context_size",
    "logit_bias",
    "max_kv_size",
    "kv_bits",
    "kv_quant_scheme",
    "kv_group_size",
    "quantized_kv_start",
    "max_tokens",
    # Conditionally sent by _build_generate_extra_kwargs
    "kv_key_bits",
    "kv_value_bits",
    "kv_key_scheme",
    "kv_value_scheme",
    "min_p",
    "top_k",
    "prefill_step_size",
    "resize_shape",
    "eos_tokens",
    "skip_special_tokens",
    "enable_thinking",
    "thinking_budget",
    "thinking_end_token",
    "thinking_start_token",
)

_RUNTIME_API_CALL_CONTRACTS: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    "load": (
        "mlx_vlm.utils.load",
        (
            "path_or_hf_repo",
            "adapter_path",
            "lazy",
            "revision",
            "trust_remote_code",
            "force_download",
            "quantize_activations",
        ),
    ),
    "apply_chat_template": (
        "mlx_vlm.prompt_utils.apply_chat_template",
        ("processor", "config", "prompt", "num_images"),
    ),
    "stream_generate": (
        "mlx_vlm.generate.stream_generate",
        (*_GENERATE_CALL_ARGS, *_SENT_GENERATE_KEYWORDS),
    ),
    "load_image": (
        "mlx_vlm.utils.load_image",
        ("image_source",),
    ),
}
_GENERATION_RESULT_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "text",
    "prompt_tokens",
    "generation_tokens",
    "total_tokens",
    "prompt_tps",
    "generation_tps",
    "peak_memory",
)


def _get_callable_contract_issues(
    *,
    qualified_name: str,
    symbol_value: object,
    required_keyword_params: Sequence[str],
) -> list[str]:
    """Return contract issues for a callable surface used by check_models."""
    if symbol_value is _raise_mlx_vlm_missing:
        dependency_message = MISSING_DEPENDENCIES.get("mlx-vlm", ERROR_MLX_VLM_MISSING)
        return [
            (
                f"{qualified_name} is still bound to the missing-dependency placeholder "
                f"({dependency_message})."
            ),
        ]

    if not callable(symbol_value):
        return [f"{qualified_name} is not callable."]

    try:
        signature = inspect.signature(symbol_value)
    except (TypeError, ValueError) as err:
        return [f"{qualified_name} signature could not be inspected for API drift checks: {err}."]

    parameters = signature.parameters
    has_var_keyword = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    missing_keyword_params: list[str] = []
    positional_only_keyword_params: list[str] = []

    for parameter_name in required_keyword_params:
        parameter = parameters.get(parameter_name)
        if parameter is None:
            if not has_var_keyword:
                missing_keyword_params.append(parameter_name)
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            positional_only_keyword_params.append(parameter_name)

    issues: list[str] = []
    if missing_keyword_params:
        issues.append(
            f"{qualified_name} is missing required keyword parameter(s): "
            f"{', '.join(missing_keyword_params)}.",
        )
    if positional_only_keyword_params:
        issues.append(
            f"{qualified_name} exposes positional-only parameter(s) that check_models passes "
            f"by keyword: {', '.join(positional_only_keyword_params)}.",
        )
    return issues


def _resolve_generation_result_type() -> type[object] | None:
    """Resolve ``mlx_vlm.generate.GenerationResult`` without importing on module load."""
    if stream_generate is _raise_mlx_vlm_missing:
        return None
    try:
        generate_module = __import__("mlx_vlm.generate", fromlist=["GenerationResult"])
    except ImportError:
        return None

    candidate = getattr(generate_module, "GenerationResult", None)
    return candidate if isinstance(candidate, type) else None


def _get_generation_result_contract_issues(result_type: type[object] | None) -> list[str]:
    """Return drift issues for the upstream ``GenerationResult`` shape we consume."""
    if result_type is None:
        if stream_generate is _raise_mlx_vlm_missing:
            return []
        return [
            "mlx_vlm.generate.GenerationResult could not be imported for API drift checks.",
        ]

    field_names: set[str] = set()
    if is_dataclass(result_type):
        field_names.update(field.name for field in fields(result_type))

    raw_annotations = getattr(result_type, "__annotations__", None)
    if isinstance(raw_annotations, dict):
        field_names.update(
            field_name
            for field_name in raw_annotations
            if isinstance(field_name, str) and field_name.strip()
        )

    missing_fields = [
        field_name
        for field_name in _GENERATION_RESULT_REQUIRED_FIELDS
        if field_name not in field_names
    ]
    if not missing_fields:
        return []

    return [
        "mlx_vlm.generate.GenerationResult is missing required field(s): "
        + ", ".join(missing_fields)
        + "."
    ]


def _detect_runtime_api_drift_issues() -> tuple[str, ...]:
    """Return issues when installed MLX runtime call surfaces drift from our contract."""
    issues: list[str] = []
    missing_mlx_vlm_surfaces: list[str] = []
    for symbol_name, (
        qualified_name,
        required_keyword_params,
    ) in _RUNTIME_API_CALL_CONTRACTS.items():
        symbol_value = globals()[symbol_name]
        if symbol_value is _raise_mlx_vlm_missing:
            missing_mlx_vlm_surfaces.append(qualified_name)
            continue
        issues.extend(
            _get_callable_contract_issues(
                qualified_name=qualified_name,
                symbol_value=symbol_value,
                required_keyword_params=required_keyword_params,
            ),
        )

    if missing_mlx_vlm_surfaces:
        dependency_message = MISSING_DEPENDENCIES.get("mlx-vlm", ERROR_MLX_VLM_MISSING)
        issues.insert(
            0,
            "mlx-vlm import unavailable; affected API surfaces: "
            f"{', '.join(missing_mlx_vlm_surfaces)}. Root cause: {dependency_message}",
        )

    issues.extend(_get_generation_result_contract_issues(_resolve_generation_result_type()))
    return tuple(dict.fromkeys(issues))


def _collect_preflight_package_issues(versions: LibraryVersionDict) -> list[str]:
    """Collect actionable dependency/runtime issues before model execution."""
    issues = _detect_upstream_version_issues(versions)

    issues.extend(_detect_runtime_api_drift_issues())

    return issues


def _sort_results_by_time(results: list[PerformanceResult]) -> list[PerformanceResult]:
    """Return results ordered by effective generation time.

    Failed results are placed first (negative inf) to highlight errors,
    followed by successful results sorted by generation time (fastest first).
    """

    def get_time_value(result: PerformanceResult) -> float:
        """Extract time value for sorting, with fallback for failed results."""
        if not result.success:
            return float("-inf")  # Failed results go to the beginning

        # Use the generation_time field from PerformanceResult
        if result.generation_time is not None:
            return result.generation_time

        # Fallback: calculate time from GenerationResult tokens-per-second if available
        if result.generation is not None:
            g_tokens = _generation_int_metric(result.generation, "generation_tokens") or 0
            g_tps = _generation_float_metric(result.generation, "generation_tps") or 0.0
            if g_tps > 0 and g_tokens:
                return g_tokens / g_tps

        return float("inf")  # No timing data available

    return sorted(results, key=get_time_value)


# =============================================================================
# SECTION: CONSOLE, SYSTEM & IMAGE METADATA HELPERS
# =============================================================================


def _first_system_profiler_entry(
    device_info: SystemProfilerDict | None,
    section_name: str,
) -> SystemProfilerEntry | None:
    """Return the first entry from a system_profiler section when present."""
    if device_info is None:
        return None
    entries = device_info.get(section_name)
    if not entries:
        return None
    return entries[0]


def _normalize_system_profiler_data(payload: object) -> SystemProfilerDict | None:
    """Normalize parsed ``system_profiler -json`` output to the subset used here."""
    raw_payload = _as_str_object_mapping(payload)
    if raw_payload is None:
        return None

    normalized: SystemProfilerDict = {}
    for key, raw_entries in raw_payload.items():
        if not isinstance(raw_entries, list):
            continue

        normalized_entries: list[SystemProfilerEntry] = []
        for raw_entry in raw_entries:
            entry_mapping = _as_str_object_mapping(raw_entry)
            if entry_mapping is not None:
                normalized_entries.append(dict(entry_mapping))
        normalized[key] = normalized_entries

    return normalized


def _mapping_first_text_value(mapping: Mapping[str, object], *keys: str) -> str | None:
    """Return the first non-empty string value found under ``keys``."""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


@lru_cache(maxsize=1)
def get_device_info() -> SystemProfilerDict | None:
    """Return system_profiler display (GPU) info as dict or None on failure.

    Only invoked on macOS to enrich hardware section. Failures are swallowed
    (we log at debug) so version printing never hard-fails.
    """
    if platform.system() != "Darwin":  # system_profiler is macOS specific
        return None
    try:
        data = subprocess.check_output(
            ["/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"],
            text=True,
            timeout=5,
        )
        return _normalize_system_profiler_data(json.loads(data))
    except (
        subprocess.SubprocessError,
        json.JSONDecodeError,
        FileNotFoundError,
        PermissionError,
    ) as err:
        logger.debug("Could not retrieve GPU information: %s", err)
        return None


def print_version_info(versions: LibraryVersionDict) -> None:
    """Print library versions and system / hardware info.

    Uses get_system_characteristics() to provide consistent output across
    CLI, HTML, and Markdown reports. Errors are swallowed so version
    printing never fails.
    """
    logger.info("--- Library Versions ---")
    version_rows = [[name, ver or ""] for name, ver in sorted(versions.items())]
    if version_rows:
        _log_rich_table(headers=["Library", "Version"], rows=version_rows)

    logger.info(
        "Generated: %s",
        local_now_str(),
    )

    # --- System / hardware information block ---
    try:
        system_info = get_system_characteristics()
        if system_info:
            logger.info("")  # spacer
            logger.info("--- System Information ---")
            _log_rich_table(
                headers=["Property", "Value"],
                rows=[[key, value] for key, value in system_info.items()],
            )
        else:
            logger.debug("No system information available.")
    except (OSError, RuntimeError, ValueError) as err:
        logger.debug("Skipping system info block: %s", err)


# =============================================================================
# IMAGE & EXIF METADATA PROCESSING (file handling, GPS, EXIF) plus HTML
# helpers, runtime analysis, artifact URLs, and the observation registry
# =============================================================================


# --- File Handling ---
def find_most_recent_file(folder: PathLike) -> Path | None:
    """Return the most recently modified image file in a folder, or None.

    Scans for regular image files (with supported extensions: .jpg, .jpeg, .png, .webp)
    excluding hidden files starting with '.', and returns the one with the most recent
    modification time.
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        logger.error("Provided path is not a directory: %s", folder_path)
        return None

    try:
        # Find all regular image files, excluding hidden files (starting with '.')
        regular_files = [
            f
            for f in folder_path.iterdir()
            if f.is_file()
            and not f.name.startswith(".")
            and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ]

        # Return the most recently modified file, or None if no files found
        most_recent: Path | None = None
        if regular_files:
            most_recent = max(
                regular_files,
                key=lambda f: f.stat().st_mtime,
            )

    except FileNotFoundError:
        logger.exception("Directory not found: %s", folder_path)
        return None
    except PermissionError:
        logger.exception("Permission denied accessing folder: %s", folder_path)
        return None
    except OSError:
        logger.exception("OS error scanning folder %s", folder_path)
        return None

    # Log result and return
    if most_recent:
        logger.debug("Most recent image file found: %s", str(most_recent))
        return most_recent

    logger.debug("No image files found in directory: %s", folder_path)
    return None


def print_image_dimensions(image_path: PathLike) -> None:
    """Print the dimensions and megapixel count of an image file."""
    img_path = Path(image_path)
    try:
        with Image.open(img_path) as img:
            width, height = img.size
            total_pixels = width * height
            logger.info(
                "Image dimensions: %s (%.1f MPixels)",
                f"{width}x{height}",
                total_pixels / MEGAPIXEL_CONVERSION,
            )
    except (FileNotFoundError, UnidentifiedImageError):
        logger.exception("Error with image file %s", img_path)
    except OSError:
        logger.exception("Unexpected error reading image dimensions for %s", img_path)


def _load_image_input_profile(image_path: Path | None) -> ImageInputProfile | None:
    """Return image dimensions for input-normalized report metrics."""
    if image_path is None or not image_path.exists():
        return None
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        logger.debug("Could not read image profile from %s", image_path, exc_info=True)
        return None
    if width <= 0 or height <= 0:
        return None
    return ImageInputProfile(
        width=width,
        height=height,
        megapixels=(width * height) / MEGAPIXEL_CONVERSION,
    )


# --- EXIF & Metadata Handling ---
def _process_exif_subifd(exif_raw: SupportsExifIfd) -> ExifDict:
    out: ExifDict = {}
    try:
        exif_ifd = exif_raw.get_ifd(ExifTags.IFD.Exif)
        if exif_ifd:
            for tag_id, value in exif_ifd.items():
                tag_name = TAGS.get(tag_id, str(tag_id)) if isinstance(tag_id, int) else str(tag_id)
                out[tag_name] = value
    except (KeyError, AttributeError, TypeError):
        logger.warning("Could not extract Exif SubIFD")
    return out


def _validate_image_url_scheme(image_str: str) -> bool:
    """Return whether an image path is an HTTP(S) URL, rejecting unsupported schemes."""
    parsed_url = urlparse(image_str)
    if not parsed_url.scheme:
        return False
    scheme = parsed_url.scheme.lower()
    if scheme not in {"http", "https"}:
        msg = f"Unsupported URL scheme for image: {parsed_url.scheme}"
        raise ValueError(msg)
    return True


def _parse_public_image_source_url(value: str) -> str:
    """Parse an absolute HTTP(S) URL recorded as reproduction metadata."""
    parsed_url = urlparse(value)
    if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc:
        msg = "image source URL must be an absolute HTTP(S) URL"
        raise argparse.ArgumentTypeError(msg)
    return value


def _open_image_for_exif(image_path: PathLike, image_str: str, *, is_url: bool) -> Image.Image:
    """Open an image for EXIF extraction from a local path or HTTP(S) URL."""
    if not is_url:
        return Image.open(Path(image_path))

    logger.debug("Downloading image from URL for EXIF extraction: %s", image_str)
    with urlopen(  # noqa: S310 - scheme is restricted to http/https by caller
        image_str,
        timeout=30,
    ) as response:
        img_data = io.BytesIO(response.read())
    return Image.open(img_data)


def _decode_gps_tag_key(gps_tag_id: object) -> str:
    """Return a readable GPS tag key for EXIF GPS IFD entries."""
    if isinstance(gps_tag_id, int):
        tag_id_int = gps_tag_id
    elif isinstance(gps_tag_id, str):
        try:
            tag_id_int = int(gps_tag_id)
        except ValueError:
            return gps_tag_id
    else:
        return str(gps_tag_id)

    gps_key = GPSTAGS.get(tag_id_int, str(gps_tag_id))
    if GPS is None:
        return gps_key
    try:
        return GPS(tag_id_int).name
    except ValueError:
        return gps_key


def _decode_gps_ifd(gps_ifd: Mapping[object, ExifValue] | None) -> GPSDict | None:
    """Decode a GPS IFD mapping into readable GPS tag names."""
    if not isinstance(gps_ifd, dict) or not gps_ifd:
        return None
    return {_decode_gps_tag_key(gps_tag_id): gps_value for gps_tag_id, gps_value in gps_ifd.items()}


def _process_gps_ifd(exif_raw: SupportsExifIfd) -> GPSDict | None:
    """Extract and decode GPS IFD data, tolerating corrupt sub-IFDs."""
    try:
        gps_ifd = exif_raw.get_ifd(ExifTags.IFD.GPSInfo)
    except (KeyError, AttributeError, TypeError) as gps_err:
        logger.warning("Could not extract GPS IFD: %s", gps_err)
        return None
    return _decode_gps_ifd(gps_ifd)


def get_exif_data(image_path: PathLike) -> ExifDict | None:
    """Return decoded EXIF structure or ``None`` if absent.

    Supports both local file paths and URLs. For URLs, downloads the image
    into memory using urllib.request and PIL's file-like object support.

    Multi-pass extraction strategy (kept explicit for robustness / debugging):
        1. IFD0 pass: baseline tags (camera vendor, dimensions, etc.). We *skip*
            pointers to sub directories (Exif / GPS) so we can handle them with
            targeted try/except blocks and continue even if one sub-IFD is corrupt.
        2. Exif SubIFD pass: exposure details, lens, ISO. Failure here should not
            abort the whole extraction—exceptions are logged and ignored.
        3. GPS IFD pass: converted into a nested mapping so later code can decide
            whether/how to stringify. We do not attempt immediate DMS conversion
            here (that happens downstream) to keep responsibilities separate.

    Rationale: real-world photographs often contain partially corrupt EXIF
    segments; failing soft ensures we still display whatever remains.
    """
    image_str = str(image_path)
    is_url = _validate_image_url_scheme(image_str)
    try:
        img = _open_image_for_exif(image_path, image_str, is_url=is_url)
        with img:
            exif_raw: Any = img.getexif()
            if not exif_raw:
                logger.warning("No EXIF data found in %s", image_str)
                return None

            # Pass 1: IFD0 — baseline tags (skip SubIFD pointers handled below)
            _ifd0_skip = {ExifTags.Base.ExifOffset, ExifTags.Base.GPSInfo}
            exif_decoded: ExifDict = {
                TAGS.get(tag_id, str(tag_id)): value
                for tag_id, value in exif_raw.items()
                if tag_id not in _ifd0_skip
            }

            # Pass 2: Exif SubIFD (exposure, lens, ISO)
            exif_decoded.update(_process_exif_subifd(cast("SupportsExifIfd", exif_raw)))

            # Pass 3: GPS IFD
            gps_decoded = _process_gps_ifd(cast("SupportsExifIfd", exif_raw))
            if gps_decoded:
                exif_decoded["GPSInfo"] = gps_decoded

            return exif_decoded
    except (FileNotFoundError, UnidentifiedImageError):
        logger.exception("Error reading image: %s", image_str)
    except (OSError, ValueError, URLError) as e:
        logger.debug("Failed to extract EXIF from %s: %s", image_str, e)
    return None


def to_float(val: float | str | None) -> float | None:
    """Convert a value to float if possible, else return None."""
    if val is None:
        return None
    try:
        temp = float(val)
    except (TypeError, ValueError):
        return None
    else:
        return temp


def _convert_gps_coordinate(
    coord: tuple[Any, ...] | list[Any],
) -> tuple[float, float, float] | None:
    """Convert GPS EXIF coordinate to (degrees, minutes, seconds) tuple.

    GPS coordinates in EXIF can be:
    - (deg, min, sec) as floats/ints
    - ((deg_num, deg_den), (min_num, min_den), (sec_num, sec_den)) as rational tuples
    - (deg, decimal_minutes)

    This function normalizes these formats.

    Args:
        coord: Tuple or list of 2 or 3 values representing GPS coordinate

    Returns:
        Tuple of (degrees, minutes, seconds) as floats, or None if conversion fails
    """
    if not isinstance(coord, (tuple, list)):
        return None

    clen = len(coord)
    if clen not in (MIN_GPS_COORD_LEN, MED_GPS_COORD_LEN, MAX_GPS_COORD_LEN):
        return None

    # EXIF values have unpredictable types from camera vendors
    # Use object type to accept anything, then check with isinstance
    def _to_val(v: float | tuple[float, ...] | list[float] | str | object) -> float | None:
        if isinstance(v, (float, int)):
            return float(v)
        if isinstance(v, (tuple, list)) and len(v) == RATIONAL_TUPLE_LEN:
            try:
                # Cast to sequence for type checker - we've verified it's tuple/list
                seq = cast("Sequence[float]", v)
                num = seq[0]
                den = seq[1]
                return num / den if den != 0 else None
            except (ValueError, TypeError):
                return None
        return to_float(str(v))

    components = [_to_val(coord[i]) if i < clen else 0.0 for i in range(3)]

    if any(c is None for c in components[:clen]):
        return None

    return (components[0] or 0.0, components[1] or 0.0, components[2] or 0.0)


def _first_exif_datetime_values(
    exif_data: ExifDict,
) -> tuple[ExifValue | None, ExifValue | None]:
    """Return the first EXIF wall-clock value and its corresponding UTC offset."""
    for tag in EXIF_DATE_TAGS:
        if value := exif_data.get(tag):
            return value, exif_data.get(EXIF_OFFSET_TAG_BY_DATE[tag])
    return None, None


def _parse_exif_local_datetime(
    exif_date: ExifValue,
    exif_offset: ExifValue | None = None,
) -> datetime | None:
    """Parse an EXIF wall clock, attaching its declared or system-local zone."""
    exif_text = str(exif_date)
    for fmt in DATE_FORMATS:
        if exif_offset:
            with suppress(ValueError):
                return datetime.strptime(f"{exif_text} {exif_offset}", f"{fmt} %z")
        with suppress(ValueError):
            return datetime.strptime(exif_text, fmt).astimezone()
    return None


def _extract_primary_exif_local_datetime(
    exif_data: ExifDict,
    *,
    warning_message: str,
) -> datetime | None:
    """Return the parsed primary EXIF datetime when it is valid."""
    exif_date, exif_offset = _first_exif_datetime_values(exif_data)
    if not exif_date:
        return None

    try:
        return _parse_exif_local_datetime(exif_date, exif_offset)
    except (TypeError, UnicodeDecodeError) as err:
        logger.warning(warning_message, err)
        return None


def _extract_exif_datetime(exif_data: ExifDict) -> tuple[str | None, str | None]:
    """Return the known EXIF date/time pair without filesystem-derived guesses."""
    parsed = _extract_primary_exif_local_datetime(
        exif_data,
        warning_message="Could not localize EXIF date: %s",
    )
    if parsed is None:
        return None, None
    return parsed.strftime("%Y-%m-%d %H:%M:%S %Z"), parsed.strftime("%H:%M:%S")


def _mojibake_marker_count(text: str) -> int:
    """Count common UTF-8-as-Latin-1/CP1252 mojibake markers in text."""
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def _repair_mojibake_text(text: str) -> str:
    """Repair common EXIF text that was decoded as Latin-1/CP1252 instead of UTF-8."""
    marker_count = _mojibake_marker_count(text)
    if marker_count == 0:
        return text

    for encoding in MOJIBAKE_REPAIR_ENCODINGS:
        with suppress(UnicodeDecodeError, UnicodeEncodeError):
            repaired = text.encode(encoding).decode("utf-8")
            if _mojibake_marker_count(repaired) < marker_count:
                return repaired
    return text


def _decode_exif_string(value: bytes | str | None) -> str:
    """Robustly decode EXIF string values, handling encoding prefixes and fallbacks.

    Handles:
    - Byte strings with null terminators.
    - UserComment 8-byte encoding prefixes (ASCII, UNICODE, JIS).
    - Fallback from UTF-8 to Latin-1/CP1252.

    Args:
        value: The raw EXIF value (bytes or str)

    Returns:
        Decoded and sanitized string.
    """
    if not value:
        return ""
    if not isinstance(value, bytes):
        decoded_text = (
            value.replace("\x00", "").strip()
            if isinstance(value, str)
            else str(value).replace("\x00", "").strip()
        )
        return _repair_mojibake_text(decoded_text)

    decoded: str = ""
    # Handle UserComment prefixes (fixed 8-byte header)
    if len(value) >= EXIF_USERCOMMENT_PREFIX_LEN:
        prefix = value[:EXIF_USERCOMMENT_PREFIX_LEN]
        data = value[EXIF_USERCOMMENT_PREFIX_LEN:]
        if prefix.startswith(b"ASCII\x00"):
            decoded = data.decode("ascii", errors="replace").replace("\x00", "").strip()
        elif prefix.startswith(b"UNICODE\x00"):
            # UNICODE prefix usually implies UTF-16.
            # We try utf-16 first (which handles BOM).
            for enc in ("utf-16", "utf-16-be", "utf-16-le"):
                try:
                    candidate = data.decode(enc).replace("\x00", "").strip()
                except (UnicodeDecodeError, LookupError):
                    continue
                else:
                    if not candidate:
                        continue
                    # Heuristic: if we have a lot of high-range characters
                    # it might be the wrong endianness.
                    if (
                        any(ord(c) > CJK_IDEOGRAPH_START for c in candidate)
                        and len(candidate) < MOJIBAKE_HEURISTIC_LEN
                    ):
                        continue
                    decoded = candidate
                    break
            else:
                # Fallback for when heuristic skips everything
                with suppress(UnicodeDecodeError, ValueError):
                    decoded = data.decode("utf-16", errors="replace").replace("\x00", "").strip()
        elif prefix.startswith(b"JIS\x00"):
            decoded = data.decode("shift-jis", errors="replace").replace("\x00", "").strip()

    if decoded:
        return decoded

    # Default decoding strategy
    try:
        # Try UTF-8 first
        return value.decode("utf-8").replace("\x00", "").strip()
    except UnicodeDecodeError:
        # Fallback to Latin-1
        return value.decode("latin-1", errors="replace").replace("\x00", "").strip()


def _extract_description(exif_data: ExifDict) -> str | None:
    description = exif_data.get("ImageDescription")
    if description is None:
        return None
    desc = _decode_exif_string(description)
    return desc or None


def _extract_gps_str(gps_info_raw: object | None) -> str | None:
    """Convert EXIF GPS mapping to decimal-degree text with cardinal suffixes.

    Accepts mixed key formats (numeric EXIF ids or tag strings) and returns
    ``"<lat>°N/S, <lon>°E/W"`` when required coordinates are present.
    """
    if not isinstance(gps_info_raw, Mapping):
        return None
    gps_info: GPSDict = {}
    for k, v in gps_info_raw.items():
        if isinstance(k, int):
            tag_name: str = GPSTAGS.get(k, str(k))
        else:
            tag_name = str(k)
        gps_info[tag_name] = v
    lat = gps_info.get("GPSLatitude")
    lat_ref = gps_info.get("GPSLatitudeRef")
    lon = gps_info.get("GPSLongitude")
    lon_ref = gps_info.get("GPSLongitudeRef")
    logger.debug(
        "Extracted GPS fields: lat=%r, lat_ref=%r, lon=%r, lon_ref=%r",
        lat,
        lat_ref,
        lon,
        lon_ref,
    )
    latitude = _convert_gps_coordinate(lat) if lat and lat_ref else None
    longitude = _convert_gps_coordinate(lon) if lon and lon_ref else None
    logger.debug("Converted GPS: latitude=%r, longitude=%r", latitude, longitude)
    if latitude is None or longitude is None:
        logger.debug("GPS conversion failed: latitude or longitude is None.")
        return None

    def dms_to_dd(dms: tuple[float, float, float], ref: str) -> tuple[float, str]:
        """Convert DMS (degrees, minutes, seconds) to unsigned decimal degrees.

        Returns unsigned decimal and normalized cardinal direction (N/S/E/W).
        Display convention: show absolute value with cardinal direction suffix.
        """
        deg, min_, sec = dms
        dd = deg + min_ / 60.0 + sec / 3600.0
        ref_upper = ref.upper()
        return (dd, ref_upper)

    try:
        lat_ref_str: str = _decode_exif_string(lat_ref)
        lon_ref_str: str = _decode_exif_string(lon_ref)
        lat_dd, lat_card = dms_to_dd(latitude, lat_ref_str)
        lon_dd, lon_card = dms_to_dd(longitude, lon_ref_str)
    except (ValueError, AttributeError, TypeError) as err:
        logger.debug("Failed to convert GPS DMS to decimal: %s", err)
        return None
    else:
        # Format with degree symbol and cardinal direction (standard GPS display)
        return f"{lat_dd:.6f}°{lat_card}, {lon_dd:.6f}°{lon_card}"


def _read_iptc_info(image_path: PathLike) -> Mapping[tuple[int, int], object] | None:
    """Read raw IPTC/IIM metadata from an image, returning ``None`` on failure."""
    try:
        with Image.open(Path(image_path)) as img:
            return cast("Mapping[tuple[int, int], object] | None", IptcImagePlugin.getiptcinfo(img))
    except (OSError, ValueError, AttributeError):
        logger.debug("Failed to extract IPTC metadata from %s", image_path)
        return None


def _decode_iptc_keywords(raw_keywords_value: object) -> list[str]:
    """Decode IPTC keyword values into stripped strings."""
    if isinstance(raw_keywords_value, (bytes, bytearray)):
        raw_keywords = [bytes(raw_keywords_value)]
    elif isinstance(raw_keywords_value, list):
        raw_keywords = list(raw_keywords_value)
    else:
        raw_keywords = []

    keywords: list[str] = []
    for kw in raw_keywords:
        decoded = kw.decode("utf-8", errors="replace") if isinstance(kw, bytes) else str(kw)
        if decoded.strip():
            keywords.append(decoded.strip())
    return keywords


def _decode_iptc_caption(caption_raw: object) -> str | None:
    """Decode IPTC caption/abstract data into stripped text."""
    if isinstance(caption_raw, (bytes, bytearray)):
        caption_str = bytes(caption_raw).decode("utf-8", errors="replace").strip()
    elif isinstance(caption_raw, str):
        caption_str = caption_raw.strip()
    else:
        return None
    return caption_str or None


def _extract_iptc_metadata(image_path: PathLike) -> IPTCMetadata:
    """Extract IPTC/IIM metadata (keywords, caption) from an image.

    Uses Pillow's IptcImagePlugin to read standard IPTC records:
        - (2, 25): Keywords (multi-valued)
        - (2, 120): Caption/Abstract
    """
    iptc = _read_iptc_info(image_path)
    if not iptc:
        return {}

    result: IPTCMetadata = {}
    keywords = _decode_iptc_keywords(iptc.get((2, 25), []))
    if keywords:
        result["iptc_keywords"] = keywords

    caption = _decode_iptc_caption(iptc.get((2, 120)))
    if caption:
        result["iptc_caption"] = caption
    return result


def _is_str_object_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    """Return True when ``value`` is a mapping with string keys."""
    return isinstance(value, Mapping) and all(isinstance(key, str) for key in value)


def _as_str_object_mapping(value: object) -> Mapping[str, object] | None:
    """Return ``value`` as a string-keyed mapping when possible."""
    return value if _is_str_object_mapping(value) else None


def _require_str_object_mapping(value: object, error_message: str) -> Mapping[str, object]:
    """Return ``value`` as a string-keyed mapping or raise ``TypeError``."""
    mapping = _as_str_object_mapping(value)
    if mapping is None:
        raise TypeError(error_message)
    return mapping


def _xmp_value(container: Mapping[str, object], qualified_key: str) -> object | None:
    """Return an XMP value across namespace-qualified and Pillow-normalized keys."""
    if qualified_key in container:
        return container[qualified_key]

    local_name = qualified_key.rsplit("}", maxsplit=1)[-1].rsplit(":", maxsplit=1)[-1]
    for existing_key, value in container.items():
        existing_local_name = existing_key.rsplit("}", maxsplit=1)[-1].rsplit(":", maxsplit=1)[-1]
        if existing_local_name == local_name:
            return value
    return None


def _xmp_mapping_value(
    container: Mapping[str, object] | None,
    qualified_key: str,
) -> Mapping[str, object] | None:
    """Return a nested XMP mapping while tolerating Pillow's stripped namespaces."""
    if container is None:
        return None
    return _as_str_object_mapping(_xmp_value(container, qualified_key))


def _metadata_text_value(metadata: Mapping[str, object], key: str) -> str | None:
    """Return a string metadata value when present and correctly typed."""
    value = metadata.get(key)
    return value if isinstance(value, str) else None


def _metadata_keyword_list(metadata: Mapping[str, object], key: str) -> list[str]:
    """Return a string-list metadata value when present and correctly typed."""
    value = metadata.get(key)
    if not isinstance(value, list):
        return []

    keyword_items = [item for item in value if isinstance(item, str)]
    return keyword_items if len(keyword_items) == len(value) else []


def _xmp_alt_text(container: Mapping[str, object] | object, rdf_ns: str) -> str | None:
    """Extract a text value from an XMP rdf:Alt container."""
    container_mapping = _as_str_object_mapping(container)
    if container_mapping is None:
        return None
    alt = _xmp_mapping_value(container_mapping, f"{rdf_ns}Alt")
    if alt is None:
        return None
    text = _xmp_value(alt, f"{rdf_ns}li")
    if isinstance(text, list):
        text = next((item for item in text if isinstance(item, str | Mapping)), "")
    text_mapping = _as_str_object_mapping(text)
    if text_mapping is not None:
        text = text_mapping.get("text", text_mapping.get("#text", ""))
    return text.strip() if isinstance(text, str) and text.strip() else None


def _read_xmp_info(image_path: PathLike) -> Mapping[str, object] | None:
    """Read raw XMP metadata from an image, returning ``None`` on failure."""
    try:
        with Image.open(Path(image_path)) as img:
            if not hasattr(img, "getxmp"):
                return None
            return _as_str_object_mapping(img.getxmp())
    except (OSError, ValueError, AttributeError, TypeError):
        logger.debug("Failed to extract XMP metadata from %s", image_path)
        return None


def _xmp_description_block(
    xmp: Mapping[str, object],
    *,
    rdf_ns: str,
) -> Mapping[str, object] | None:
    """Return the XMP RDF description block when present."""
    return _xmp_mapping_value(
        _xmp_mapping_value(_xmp_mapping_value(xmp, "xmpmeta"), f"{rdf_ns}RDF"),
        f"{rdf_ns}Description",
    )


def _xmp_keywords(desc_block: Mapping[str, object], *, rdf_ns: str, dc_ns: str) -> list[str]:
    """Extract XMP dc:subject keywords from an RDF description block."""
    subject_mapping = _as_str_object_mapping(_xmp_value(desc_block, f"{dc_ns}subject"))
    if subject_mapping is None:
        return []
    bag = _xmp_mapping_value(subject_mapping, f"{rdf_ns}Bag")
    if bag is None:
        return []
    items = _xmp_value(bag, f"{rdf_ns}li") or []
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []
    return [str(keyword).strip() for keyword in items if str(keyword).strip()]


def _extract_xmp_metadata(image_path: PathLike) -> XMPMetadata:
    """Extract XMP metadata (dc:subject keywords, dc:title, dc:description).

    Uses Pillow's ``Image.getxmp()`` (8.2+). The returned dict is deeply
    nested and Pillow strips namespace prefixes from current releases; this
    function also accepts older namespace-qualified shapes.
    Requires the ``defusedxml`` package; returns empty if unavailable.
    """
    if not _defusedxml_available:
        logger.debug("Skipping XMP extraction — defusedxml not installed")
        return {}

    rdf_ns = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    dc_ns = "{http://purl.org/dc/elements/1.1/}"
    xmp = _read_xmp_info(image_path)
    if not xmp:
        return {}

    desc_block = _xmp_description_block(xmp, rdf_ns=rdf_ns)
    if desc_block is None:
        return {}

    result: XMPMetadata = {}
    keywords = _xmp_keywords(desc_block, rdf_ns=rdf_ns, dc_ns=dc_ns)
    if keywords:
        result["xmp_keywords"] = keywords

    description = _xmp_value(desc_block, f"{dc_ns}description") or {}
    desc_text = _xmp_alt_text(description, rdf_ns)
    if desc_text:
        result["xmp_description"] = desc_text

    title = _xmp_value(desc_block, f"{dc_ns}title") or {}
    title_text = _xmp_alt_text(title, rdf_ns)
    if title_text:
        result["xmp_title"] = title_text
    return result


def _extract_xp_keywords(exif_data: ExifDict) -> list[str]:
    """Extract Windows XP keywords from EXIF IFD0 (UTF-16LE encoded, semicolon-delimited)."""
    raw = exif_data.get("XPKeywords")
    if raw is None:
        return []
    if isinstance(raw, bytes):
        try:
            decoded = raw.decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            decoded = raw.decode("latin-1", errors="replace")
    elif isinstance(raw, str):
        decoded = raw
    else:
        return []
    return [kw.strip() for kw in decoded.split(";") if kw.strip()]


def _merge_keywords(*sources: list[str]) -> str | None:
    """Merge keyword lists from multiple sources, preserving first-seen order."""
    seen: set[str] = set()
    merged: list[str] = []
    for source in sources:
        for kw in source:
            lower = kw.lower()
            if lower not in seen:
                seen.add(lower)
                merged.append(kw)
    return ", ".join(merged) if merged else None


def extract_image_metadata(
    image_path: PathLike,
    *,
    exif_data: ExifExtractionInput = None,
) -> MetadataDict:
    """Derive high-level metadata (date, description, GPS, keywords, title, raw EXIF).

    Extracts from three metadata families:
        1. EXIF (IFD0 + SubIFD + GPS) via ``get_exif_data``
        2. IPTC/IIM keywords and caption via ``_extract_iptc_metadata``
        3. XMP dc:subject, dc:title, dc:description via ``_extract_xmp_metadata``
        4. Windows XP keywords from EXIF IFD0

    Keywords are merged (deduplicated, order-preserved) across all sources.
    Returns None for unavailable fields instead of sentinel strings.
    """
    metadata: MetadataDict = {}
    img_path = Path(image_path)
    if exif_data is None:
        resolved_exif_data: ExifDict = get_exif_data(img_path) or {}
    elif exif_data is EXIF_NOT_EXTRACTED:
        resolved_exif_data = {}
    else:
        resolved_exif_data = cast("ExifDict", exif_data)

    # IPTC + XMP extraction (separate image opens for header-only access)
    iptc = _extract_iptc_metadata(img_path)
    xmp = _extract_xmp_metadata(img_path)
    iptc_caption = _metadata_text_value(iptc, "iptc_caption")
    xmp_description = _metadata_text_value(xmp, "xmp_description")
    xmp_title = _metadata_text_value(xmp, "xmp_title")
    iptc_keywords = _metadata_keyword_list(iptc, "iptc_keywords")
    xmp_keywords = _metadata_keyword_list(xmp, "xmp_keywords")

    # Date, Time, GPS
    metadata["date"], metadata["time"] = _extract_exif_datetime(resolved_exif_data)
    metadata["gps"] = _extract_gps_str(resolved_exif_data.get("GPSInfo"))

    # Description: prefer IPTC caption → XMP description → EXIF ImageDescription
    description = iptc_caption or xmp_description or _extract_description(resolved_exif_data)
    metadata["description"] = description

    # Title: from XMP dc:title (falls back to None)
    metadata["title"] = xmp_title

    # Keywords: merge IPTC → XMP → Windows XP, deduplicated
    metadata["keywords"] = _merge_keywords(
        iptc_keywords,
        xmp_keywords,
        _extract_xp_keywords(resolved_exif_data),
    )

    # Raw EXIF for reference
    metadata["exif"] = str(resolved_exif_data)
    return metadata


def exif_value_to_str(tag_str: str, value: object) -> str:
    """Convert an EXIF value to a string for display, sanitizing and truncating it."""

    def _sanitize(s: str) -> str:
        """Replace control characters with spaces to prevent breaking table alignment."""
        # This regex targets ASCII control characters, including tabs and newlines.
        return re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", s).strip()

    processed_str: str
    if isinstance(value, bytes):
        processed_str = _sanitize(_decode_exif_string(value))
    elif isinstance(value, tuple | list) and len(value) > MAX_TUPLE_LEN:
        return f"<tuple len={len(value)}>"
    elif isinstance(value, bytearray):
        return f"<bytearray len={len(value)}>"
    else:
        try:
            processed_str = _sanitize(_repair_mojibake_text(str(value)))
        except (TypeError, ValueError) as str_err:
            logger.debug(
                "Could not convert EXIF value for tag '%s' to string: %s",
                tag_str,
                str_err,
            )
            return f"<unrepresentable type: {type(value).__name__}>"

    # Truncate the final sanitized string if it's too long
    if len(processed_str) > MAX_STR_LEN:
        return processed_str[:STR_TRUNCATE_LEN] + "..."
    return processed_str


def filter_and_format_tags(
    exif: ExifDict,
    *,
    show_all: bool = False,
) -> list[tuple[str, str, bool]]:
    """Filter and format EXIF tags for pretty printing."""
    tags: list[tuple[str, str, bool]] = []
    for tag, value in exif.items():
        tag_str: str = str(tag)
        if tag_str == "GPSInfo" and isinstance(value, dict):
            continue
        if isinstance(value, dict):
            logger.debug(
                "Skipping dictionary value for EXIF tag '%s' in pretty print.",
                tag_str,
            )
            continue
        value_str: str = exif_value_to_str(tag_str, value)
        is_important: bool = tag_str in IMPORTANT_EXIF_TAGS
        if show_all or is_important:
            tags.append((tag_str, value_str, is_important))
    return tags


def pretty_print_exif(
    exif: ExifDict,
    *,
    show_all: bool = True,
    title: str = "EXIF Metadata Summary",
) -> None:
    """Render selected EXIF tags in a Rich table.

    Only simple presentation logic lives here; extraction, filtering and
    sanitizing occur earlier (see ``get_exif_data`` / ``filter_and_format_tags``).
    """
    if not exif:
        logger.info("No EXIF data available.")
        return

    tags_to_print: list[tuple[str, str, bool]] = filter_and_format_tags(
        exif,
        show_all=show_all,
    )
    if not tags_to_print:
        log_warning_note("No relevant EXIF tags found to display.")
        return

    table = Table(box=box.ROUNDED, show_lines=False, expand=False)
    table.add_column("Tag", style="bold blue", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for tag_name, value_display, is_important_tag in tags_to_print:
        tag_cell = Text(tag_name, style="bold yellow" if is_important_tag else "")
        table.add_row(tag_cell, value_display)

    header_width: int = max(40, get_terminal_width(max_width=100))

    log_rule(header_width, char="=", style="blue", bold=True)
    logger.info(
        _display_align(title, header_width, alignment="center"),
        extra={"style_hint": LogStyles.HEADER, "style_width": header_width},
    )
    log_rule(header_width, char="=", style="blue", bold=True)

    _log_rich_renderable(table, width=header_width)
    log_rule(header_width, char="=", style="blue", bold=True)


def _metadata_has_descriptive_reference(
    metadata: Mapping[str, str | None] | None,
) -> bool:
    """Return whether title, description, or keyword metadata is available."""
    return bool(
        metadata
        and any(
            isinstance(metadata.get(field_name), str)
            and bool((metadata.get(field_name) or "").strip())
            for field_name in ("title", "description", "keywords")
        )
    )


def _prompt_builder_exposes_metadata(
    args: argparse.Namespace,
    metadata: MetadataDict | None,
) -> bool:
    """Return whether the generated prompt actually includes metadata context."""
    if getattr(args, "prompt", None):
        return False
    if (
        _resolve_eval_mode(str(getattr(args, "eval_mode", DEFAULT_EVAL_MODE)), metadata)
        != "assisted"
    ):
        return False
    provenance = _build_metadata_provenance(metadata)
    return provenance.has_authoritative_context or provenance.has_draft


def _build_report_mode_policy(
    *,
    eval_mode: str,
    metadata: MetadataDict | None = None,
    metadata_exposed_to_prompt: bool | None = None,
    assessment_profile: AssessmentProfile = "general",
) -> ReportModePolicy:
    """Return only factual evaluation-mode and prompt-exposure settings."""
    resolved_eval_mode = _resolve_eval_mode(eval_mode, metadata)
    resolved_metadata_exposure = (
        bool(metadata_exposed_to_prompt) and resolved_eval_mode == "assisted"
    )
    return ReportModePolicy(
        eval_mode=resolved_eval_mode,
        metadata_exposed_to_prompt=resolved_metadata_exposure,
        assessment_profile=assessment_profile,
    )


def _build_report_render_context(
    *,
    results: list[PerformanceResult],
    prompt: str,
    image_path: Path | None = None,
    metadata: MetadataDict | None = None,
    metadata_exposed_to_prompt: bool | None = None,
    eval_mode: str = DEFAULT_EVAL_MODE,
    system_info: dict[str, str] | None = None,
    recommended_working_set_bytes: int | None = None,
    preflight_issues: Sequence[str] = (),
    model_provenance: Mapping[str, ModelProvenanceRecord] | None = None,
) -> ReportRenderContext:
    """Analyze each result once and cache the sole current-run assessment."""
    resolved_results = [
        _populate_result_quality_analysis(
            result,
            prompt=prompt,
        )
        for result in results
    ]
    result_set: ResultSet = ResultSet(resolved_results)
    image_profile = _load_image_input_profile(image_path)
    resolved_system_info: dict[str, str] = (
        system_info if system_info is not None else get_system_characteristics()
    )
    return ReportRenderContext(
        result_set=result_set,
        system_info=resolved_system_info,
        recommended_working_set_bytes=recommended_working_set_bytes,
        image_profile=image_profile,
        preflight_issues=tuple(preflight_issues),
        mode_policy=_build_report_mode_policy(
            eval_mode=eval_mode,
            metadata=metadata,
            metadata_exposed_to_prompt=metadata_exposed_to_prompt,
            assessment_profile=resolved_results[0].assessment_profile
            if resolved_results
            else "general",
        ),
        assessments=tuple(
            (result.model_name, _assess_result(result)) for result in result_set.results
        ),
        model_provenance=tuple(
            (model_name, record.copy()) for model_name, record in (model_provenance or {}).items()
        ),
    )


def _validate_report_render_context(context: ReportRenderContext) -> None:
    """Reject inconsistent cached identities or outcome axes before publication."""
    result_names = tuple(result.model_name for result in context.result_set.results)
    assessment_names = tuple(model_name for model_name, _assessment in context.assessments)
    provenance_names = tuple(model_name for model_name, _record in context.model_provenance)
    named_groups = {
        "result": result_names,
        "assessment": assessment_names,
        "provenance": provenance_names,
    }
    for label, names in named_groups.items():
        if len(names) != len(set(names)):
            msg = f"report context contains duplicate {label} identities"
            raise ValueError(msg)

    result_keys = set(result_names)
    for label, names in (
        ("assessment", assessment_names),
        ("provenance", provenance_names),
    ):
        if set(names) != result_keys:
            msg = f"report context {label} keys do not match result keys"
            raise ValueError(msg)

    legal_axes: frozenset[tuple[ExecutionStatus, ModelUsability, MaintainerStatus]] = frozenset(
        {
            ("completed", "usable", "none"),
            # Compliance-only observations degrade usability without entering
            # the maintainer lane; integration signals add the maintainer axis.
            ("completed", "usable_with_caveats", "none"),
            ("completed", "usable_with_caveats", "observation_needs_reproduction"),
            ("completed", "unusable", "none"),
            ("completed", "unusable", "observation_needs_reproduction"),
            ("crashed", "not_evaluated", "actionable_failure"),
            ("indeterminate", "not_evaluated", "none"),
        }
    )
    for model_name, assessment in context.assessments:
        axes = (assessment.execution, assessment.usability, assessment.maintainer_status)
        if axes not in legal_axes:
            msg = f"report context has illegal outcome axes for {model_name}: {axes}"
            raise ValueError(msg)
        observations_expected = assessment.usability in {"usable_with_caveats", "unusable"}
        if bool(assessment.observations) != observations_expected:
            msg = f"report context has illegal observation partition for {model_name}"
            raise ValueError(msg)

    for model_name, provenance in context.model_provenance:
        if provenance.get("model") != model_name:
            msg = f"report context provenance record does not match key {model_name}"
            raise ValueError(msg)

    counts = _run_outcome_counts(context.assessments)
    usability_counts = Counter(
        assessment.usability for _model_name, assessment in context.assessments
    )
    expected_counts = {
        "models_attempted": len(result_names),
        "models_evaluated": counts["models_completed"] + counts["models_crashed"],
        "models_completed": (
            usability_counts["usable"]
            + usability_counts["usable_with_caveats"]
            + usability_counts["unusable"]
        ),
        "models_crashed": usability_counts["not_evaluated"] - counts["models_indeterminate"],
        "models_indeterminate": counts["models_indeterminate"],
    }
    if counts != expected_counts:
        msg = f"report context outcome partitions are inconsistent: {counts}"
        raise ValueError(msg)


def _html_attr(name: str, value: str) -> str:
    """Return a safely escaped HTML attribute."""
    return f' {name}="{html.escape(value, quote=True)}"'


def _html_class_attr(classes: Sequence[str]) -> str:
    """Return a safely escaped class attribute for a stable class list."""
    if not classes:
        return ""
    return _html_attr("class", " ".join(classes))


def _html_status_attrs(
    result: PerformanceResult,
    assessment: ResultAssessment,
) -> str:
    """Return presentation-only filter attributes from one cached assessment."""
    return "".join(
        (
            _html_attr("data-model", result.model_name.casefold()),
            _html_attr("data-execution", assessment.execution),
            _html_attr("data-usability", assessment.usability),
            _html_attr("data-maintainer-status", assessment.maintainer_status),
            _html_class_attr((assessment.execution, assessment.usability)),
        )
    )


def _html_table(
    *,
    caption: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_attrs: Sequence[str] = (),
    raw_columns: frozenset[int] = frozenset(),
    sort_values: Sequence[Sequence[str | int | float | None]] = (),
    sortable: bool = False,
) -> str:
    """Render a compact escaped table, allowing explicitly built internal-link cells."""
    parts = ["<table>", f"<caption>{html.escape(caption, quote=True)}</caption>", "<thead><tr>"]
    if sortable:
        parts.extend(
            (
                '<th scope="col"><button type="button" class="sort-button" '
                f'data-sort-column="{column_index}" onclick="sortChooserColumn(this)">'
                f"{html.escape(header, quote=True)}</button></th>"
            )
            for column_index, header in enumerate(headers)
        )
    else:
        parts.extend(
            f'<th scope="col">{html.escape(header, quote=True)}</th>' for header in headers
        )
    parts.extend(["</tr></thead>", "<tbody>"])
    for row_index, row in enumerate(rows):
        attrs = row_attrs[row_index] if row_index < len(row_attrs) else ""
        parts.append(f"<tr{attrs}>")
        for column_index, value in enumerate(row):
            cell = value if column_index in raw_columns else html.escape(value, quote=True)
            sort_value = (
                sort_values[row_index][column_index]
                if row_index < len(sort_values) and column_index < len(sort_values[row_index])
                else None
            )
            sort_attr = (
                _html_attr("data-sort-value", "" if sort_value is None else str(sort_value))
                if sortable
                else ""
            )
            parts.append(f"<td{sort_attr}>{cell}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>"])
    return "\n".join(parts)


def _peak_memory_delta_from_model_load_gb(result: PerformanceResult) -> float | None:
    """Return peak-memory growth after model load for one successful run."""
    if result.generation is None:
        return None
    peak_memory_gb = _generation_optional_nonnegative_float_metric(
        result.generation,
        "peak_memory",
    )
    model_load_active_gb = (
        result.runtime_diagnostics.model_load_active_memory_gb
        if result.runtime_diagnostics is not None
        else _object_model_load_active_memory_gb(result.generation)
    )
    if peak_memory_gb is None or model_load_active_gb is None:
        return None
    if not math.isfinite(peak_memory_gb) or not math.isfinite(model_load_active_gb):
        return None
    return max(peak_memory_gb - model_load_active_gb, 0.0)


_RUNTIME_PHASE_KEYS: Final[tuple[RuntimePhaseName, ...]] = (
    "model_load",
    "prompt_prep",
    "upstream_prefill_first_token",
    "input_preparation_and_decode",
    "decode",
    "cleanup",
)

_RUNTIME_PHASE_LABELS: Final[dict[RuntimePhaseName, str]] = {
    "model_load": "model load",
    "prompt_prep": "local prompt prep",
    "upstream_prefill_first_token": "upstream model prefill / first-token",  # skylos: ignore[SKY-S101] - phase-name key, not a secret; 4.33.2 entropy scanner misreads snake_case identifiers
    "input_preparation_and_decode": "input preparation + decode",
    "decode": "generation call total (unsplit)",
    "cleanup": "cleanup",
}

_RUNTIME_PHASE_ACTIONS: Final[dict[RuntimePhaseName, tuple[str, str]]] = {
    "upstream_prefill_first_token": (
        (
            "Most measured runtime is spent inside upstream generation before the first "
            "token is available."
        ),
        (
            "Inspect prompt/image token accounting, dynamic-resolution image burden, "
            "prefill step sizing, and cache/prefill behavior."
        ),
    ),
    "input_preparation_and_decode": (
        (
            "Most residual generation-call time falls outside the upstream model-loop "
            "first-token window, combining input preparation with token decoding."
        ),
        (
            "Profile prepare_inputs() and image preprocessing, then use generation TPS "
            "and token counts to assess the decode contribution."
        ),
    ),
    "decode": (
        (
            "Most measured runtime is spent inside the full generation call, but upstream "
            "model first-token timing was unavailable to split that call further."
        ),
        (
            "Use generation TPS and token counts to assess decode, then profile input "
            "preparation separately if the remaining call time is high."
        ),
    ),
    "prompt_prep": (
        (
            "Local prompt preparation is consuming a large share of runtime, which often "
            "means expensive chat-template or preflight validation work."
        ),
        "Inspect chat-template rendering, context blocks, and validators.",
    ),
    "model_load": (
        "Cold model load time is a major share of runtime for this cohort.",
        "Consider staged runs, model reuse, or narrowing the model set before reruns.",
    ),
    "cleanup": (
        "Post-run synchronization or cache cleanup is taking a non-trivial share of time.",
        "Inspect cleanup policy, synchronization frequency, and cache-reset behavior.",
    ),
}


def _positive_runtime_duration(value: float | None) -> float | None:
    """Return a finite positive runtime duration, or None when unavailable."""
    if not isinstance(value, int | float):
        return None
    duration = float(value)
    if not math.isfinite(duration) or duration <= 0.0:
        return None
    return duration


def _runtime_upstream_prefill_first_token_time_s(
    runtime: RuntimeDiagnostics | None,
) -> float | None:
    """Return the upstream prefill/first-token proxy from mlx-vlm prompt timing."""
    if runtime is None:
        return None
    return _positive_runtime_duration(runtime.first_token_latency_s)


def _runtime_generation_residual_time_s(runtime: RuntimeDiagnostics | None) -> float | None:
    """Return input-preparation plus decode time outside upstream model TTFT."""
    if runtime is None:
        return None
    decode_time = _positive_runtime_duration(runtime.decode_time_s)
    upstream_prefill_time = _runtime_upstream_prefill_first_token_time_s(runtime)
    if decode_time is None or upstream_prefill_time is None:
        return None
    residual_time = max(decode_time - upstream_prefill_time, 0.0)
    return residual_time if residual_time > 0.0 else None


def _runtime_phase_durations(runtime: RuntimeDiagnostics | None) -> dict[RuntimePhaseName, float]:
    """Return normalized non-negative phase durations for one run."""
    if runtime is None:
        return {}

    phase_durations: dict[RuntimePhaseName, float] = {}
    base_phase_values: tuple[tuple[RuntimePhaseName, float | None], ...] = (
        ("model_load", runtime.model_load_time_s),
        ("prompt_prep", runtime.prompt_prep_time_s),
    )
    for phase, value in base_phase_values:
        duration = _positive_runtime_duration(value)
        if duration is not None:
            phase_durations[phase] = duration

    upstream_prefill_time = _runtime_upstream_prefill_first_token_time_s(runtime)
    generation_residual_time = _runtime_generation_residual_time_s(runtime)
    decode_time = _positive_runtime_duration(runtime.decode_time_s)
    if upstream_prefill_time is not None:
        phase_durations["upstream_prefill_first_token"] = upstream_prefill_time
        if generation_residual_time is not None:
            phase_durations["input_preparation_and_decode"] = generation_residual_time
    elif decode_time is not None:
        phase_durations["decode"] = decode_time

    cleanup_time = _positive_runtime_duration(runtime.cleanup_time_s)
    if cleanup_time is not None:
        phase_durations["cleanup"] = cleanup_time
    return phase_durations


def _build_runtime_analysis_summary(
    results: Sequence[PerformanceResult],
) -> RuntimeAnalysisSummary | None:
    """Build a rule-based runtime interpretation from per-result phase timings."""
    phase_totals: dict[RuntimePhaseName, float] = dict.fromkeys(_RUNTIME_PHASE_KEYS, 0.0)
    dominant_counts: Counter[RuntimePhaseName] = Counter[RuntimePhaseName]()
    termination_counts: Counter[str] = Counter[str]()
    measured_models: int = 0
    generation_total: float = 0.0
    generation_models: int = 0
    prefill_split_models: int = 0
    validation_total: float = 0.0
    validation_models: int = 0
    first_token_latencies: list[float] = []

    for result in results:
        runtime: RuntimeDiagnostics | None = result.runtime_diagnostics
        phase_durations: dict[RuntimePhaseName, float] = _runtime_phase_durations(runtime)
        if phase_durations:
            measured_models += 1
            run_dominant_phase: RuntimePhaseName = max(
                phase_durations,
                key=phase_durations.__getitem__,
            )
            dominant_counts[run_dominant_phase] += 1
            for phase, duration in phase_durations.items():
                phase_totals[phase] += duration
        if runtime is not None:
            decode_time: float | None = _positive_runtime_duration(runtime.decode_time_s)
            if decode_time is not None:
                generation_total += decode_time
                generation_models += 1
            if _runtime_upstream_prefill_first_token_time_s(runtime) is not None:
                prefill_split_models += 1
            validation_time: float | None = runtime.input_validation_time_s
            validation_duration = _positive_runtime_duration(validation_time)
            if validation_duration is not None:
                validation_total += validation_duration
                validation_models += 1
            first_token_latency: float | None = runtime.first_token_latency_s
            first_token_duration = _positive_runtime_duration(first_token_latency)
            if first_token_duration is not None:
                first_token_latencies.append(first_token_duration)
        stop_reason: str | None = runtime.stop_reason if runtime is not None else None
        if stop_reason:
            termination_counts[stop_reason] += 1

    total_measured: float = sum(phase_totals.values())
    if measured_models == 0 or total_measured <= 0.0:
        return None

    dominant_phase: RuntimePhaseName = max(phase_totals, key=phase_totals.__getitem__)
    dominant_phase_share: float = phase_totals[dominant_phase] / total_measured
    interpretation: str
    next_action: str
    interpretation, next_action = _RUNTIME_PHASE_ACTIONS.get(
        dominant_phase,
        (
            "Runtime is distributed across multiple phases without a clear single bottleneck.",
            "Inspect per-phase distributions before changing benchmark policy.",
        ),
    )

    if termination_counts.get("timeout", 0) > 0:
        interpretation += (
            f" Timeouts also affected {termination_counts['timeout']} model(s), "
            "so some totals may be dominated by interrupted runs."
        )

    first_token_latency_avg: float | None = (
        sum(first_token_latencies) / len(first_token_latencies) if first_token_latencies else None
    )
    dominant_count_map: dict[RuntimePhaseName, int] = {
        phase: dominant_counts[phase] for phase in _RUNTIME_PHASE_KEYS if dominant_counts[phase] > 0
    }

    runtime_summary: RuntimeAnalysisSummary = {
        "dominant_phase": dominant_phase,
        "dominant_phase_share": dominant_phase_share,
        "dominant_phase_count": dominant_counts.get(dominant_phase, 0),
        "measured_models": measured_models,
        "interpretation": interpretation,
        "next_action": next_action,
        "phase_totals": phase_totals,
        "dominant_counts": dominant_count_map,
        "termination_counts": dict(termination_counts),
        "generation_total": generation_total,
        "generation_models": generation_models,
        "prefill_split_models": prefill_split_models,
        "validation_total": validation_total,
        "validation_models": validation_models,
        "first_token_latency_avg": first_token_latency_avg,
        "first_token_latency_min": min(first_token_latencies) if first_token_latencies else None,
        "first_token_latency_max": max(first_token_latencies) if first_token_latencies else None,
        "first_token_latency_models": len(first_token_latencies),
    }
    return runtime_summary


def _runtime_generation_total_fact(
    runtime_analysis: RuntimeAnalysisSummary,
) -> tuple[str, str] | None:
    """Build the total upstream generation timing fact for runtime summaries."""
    generation_total: float = runtime_analysis["generation_total"]
    generation_models: int = runtime_analysis["generation_models"]
    if generation_models <= 0 or generation_total <= 0.0:
        return None

    prefill_split_models: int = runtime_analysis["prefill_split_models"]
    if prefill_split_models > 0:
        split_note = (
            f"; upstream model prefill / first-token split available for "
            f"{prefill_split_models}/{generation_models} model(s)"
        )
    else:
        split_note = "; upstream model prefill / first-token split unavailable"
    return (
        "Generation total",
        (
            f"{format_overall_runtime(generation_total)} across {generation_models} model(s)"
            f"{split_note}."
        ),
    )


def _runtime_phase_totals_fact(
    runtime_analysis: RuntimeAnalysisSummary,
) -> tuple[str, str] | None:
    """Build the aggregate phase totals fact shared by report renderers."""
    phase_totals: dict[RuntimePhaseName, float] = runtime_analysis["phase_totals"]
    phase_summary = ", ".join(
        f"{_RUNTIME_PHASE_LABELS.get(phase, phase)}={format_overall_runtime(duration)}"
        for phase, duration in phase_totals.items()
        if duration > 0.0
    )
    if not phase_summary:
        return None
    return ("Phase totals", f"{phase_summary}.")


def _runtime_timing_snapshot_facts(
    runtime_analysis: RuntimeAnalysisSummary,
) -> list[tuple[str, str]]:
    """Build concise aggregate timing facts for optional runtime signals."""
    facts: list[tuple[str, str]] = []

    validation_models: int = runtime_analysis["validation_models"]
    validation_total: float = runtime_analysis["validation_total"]
    if validation_models > 0 and validation_total > 0.0:
        validation_avg: float = validation_total / validation_models
        facts.append(
            (
                "Validation overhead",
                (
                    f"{format_overall_runtime(validation_total)} total "
                    f"(avg {format_overall_runtime(validation_avg)} across "
                    f"{validation_models} model(s))."
                ),
            )
        )

    first_token_models: int = runtime_analysis["first_token_latency_models"]
    first_token_avg: float | None = runtime_analysis["first_token_latency_avg"]
    first_token_min: float | None = runtime_analysis["first_token_latency_min"]
    first_token_max: float | None = runtime_analysis["first_token_latency_max"]
    if (
        first_token_models > 0
        and first_token_avg is not None
        and first_token_min is not None
        and first_token_max is not None
    ):
        facts.append(
            (
                "Upstream model prefill / first-token time",
                (
                    f"Avg {format_overall_runtime(first_token_avg)} | "
                    f"Min {format_overall_runtime(first_token_min)} | "
                    f"Max {format_overall_runtime(first_token_max)} "
                    f"across {first_token_models} model(s)."
                ),
            )
        )

    return facts


def _relative_markdown_artifact_path(*, report_filename: Path, artifact_filename: Path) -> str:
    """Return a relative path for links between Markdown artifacts."""
    try:
        return os.path.relpath(artifact_filename, start=report_filename.parent)
    except ValueError:
        return str(artifact_filename)


def _github_blob_ref() -> str:
    """Return the GitHub blob/tree ref for tracked artifact links.

    Artifact links always target the default branch (or an explicit override).
    The producer's HEAD commit is never used: the artifacts being generated
    cannot be contained in any commit that exists at generation time, so a
    HEAD-pinned link would show the *previous* run while claiming durability.
    Branch links become correct once this run's artifacts are committed. A SHA
    override remains available for deliberate post-commit regeneration.
    """
    return _GITHUB_REF_OVERRIDE or _GITHUB_DEFAULT_BRANCH


def _github_repo_artifact_url(
    repo_relative_path: PurePosixPath,
    *,
    anchor: str | None = None,
    tree: bool = False,
) -> str:
    """Return a GitHub URL for a tracked artifact path within this repository."""
    encoded_path = "/".join(quote(part) for part in repo_relative_path.parts)
    view_name = "tree" if tree else "blob"
    url = f"{_GITHUB_REPO_URL}/{view_name}/{_github_blob_ref()}/{encoded_path}"
    if anchor is not None:
        return f"{url}#{anchor}"
    return url


def _published_output_repo_path(artifact_filename: Path) -> PurePosixPath | None:
    """Infer the tracked repo path for a published output artifact when possible."""
    try:
        repo_relative = artifact_filename.resolve().relative_to(_REPO_ROOT)
    except ValueError:
        repo_relative = None

    if repo_relative is not None and repo_relative.parts[:2] == _PUBLISHED_OUTPUT_ROOT.parts:
        return PurePosixPath(*repo_relative.parts)

    artifact_name = artifact_filename.name
    if artifact_name in _PUBLISHED_REPORT_ARTIFACT_NAMES:
        return _PUBLISHED_OUTPUT_ROOT / "reports" / artifact_name
    if artifact_name in _PUBLISHED_ROOT_OUTPUT_ARTIFACT_NAMES:
        return _PUBLISHED_OUTPUT_ROOT / artifact_name
    if artifact_name.startswith("source-image"):
        return _PUBLISHED_OUTPUT_ROOT / "reports" / "assets" / artifact_name
    if artifact_name == "run_summary.md" or (
        artifact_name.startswith("issue_") and artifact_name.endswith(".md")
    ):
        return _PUBLISHED_OUTPUT_ROOT / "issues" / artifact_name
    return None


def _github_output_artifact_url(
    artifact_filename: Path,
    *,
    anchor: str | None = None,
) -> str | None:
    """Return a GitHub URL for a published output artifact when it is known."""
    repo_relative = _published_output_repo_path(artifact_filename)
    if repo_relative is None:
        return None
    return _github_repo_artifact_url(repo_relative, anchor=anchor)


def _relative_markdown_artifact_target(
    *,
    report_filename: Path,
    artifact_filename: Path,
    anchor: str | None,
) -> str:
    """Return an escaped relative Markdown target with an optional anchor."""
    target = _relative_markdown_artifact_path(
        report_filename=report_filename,
        artifact_filename=artifact_filename,
    ).replace(" ", "%20")
    if anchor is not None:
        return f"{target}#{anchor}"
    return target


def _markdown_artifact_target(
    *,
    report_filename: Path,
    artifact_filename: Path,
    anchor: str | None = None,
) -> str:
    """Return the best Markdown target for a companion artifact link."""
    if _LinkStyleState.value != "relative":
        github_url = _github_output_artifact_url(artifact_filename, anchor=anchor)
        if github_url is not None:
            return github_url

    return _relative_markdown_artifact_target(
        report_filename=report_filename,
        artifact_filename=artifact_filename,
        anchor=anchor,
    )


def _issue_markdown_artifact_target(
    *,
    report_filename: Path,
    artifact_filename: Path,
    anchor: str | None = None,
) -> str:
    """Return a repository URL for a cross-file link pasted into a GitHub issue."""
    github_url = _github_output_artifact_url(artifact_filename, anchor=anchor)
    if github_url is not None:
        return github_url
    return _markdown_artifact_target(
        report_filename=report_filename,
        artifact_filename=artifact_filename,
        anchor=anchor,
    )


def _gallery_model_anchor(model_name: str) -> str:
    """Build a stable anchor for model sections in the gallery artifact."""
    normalized_name = model_name.lower().replace("/", " ")
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized_name)
    collapsed = re.sub(r"[-\s]+", "-", normalized).strip("-")
    return f"model-{collapsed or 'entry'}"


def _component_source_revision(provenance: object, name: str) -> str | None:
    """Return the recorded git revision for one component, when it has one."""
    if not isinstance(provenance, dict):
        return None
    entry = provenance.get(name)
    if not isinstance(entry, dict):
        return None
    revision = entry.get("source_revision") or entry.get("vcs_revision")
    return revision if isinstance(revision, str) and revision else None


def _collect_report_component_rows(
    *,
    versions: LibraryVersionDict,
    system_info: Mapping[str, str],
    library_names: Sequence[str] | None = None,
    system_keys: Sequence[str] | None = None,
    provenance: Mapping[str, object] | None = None,
) -> list[tuple[str, str]]:
    """Collect shared library/system rows for human-facing report artifacts.

    When ``provenance`` (the component_provenance mapping) is supplied, an
    editable/git install's exact source revision is listed beside its version:
    a version string such as 0.6.14 spans many upstream commits, including
    numerics fixes, so the revision is what pins a run's behaviour.
    """
    rows: list[tuple[str, str]] = []
    selected_library_names = tuple(library_names) if library_names is not None else tuple(versions)
    selected_system_keys = tuple(system_keys) if system_keys is not None else tuple(system_info)

    for library_name in selected_library_names:
        version_value = versions.get(library_name)
        if version_value:
            rows.append((library_name, version_value))
            revision = _component_source_revision(provenance, library_name)
            if revision is not None:
                rows.append((f"{library_name} source revision", revision))

    for system_key in selected_system_keys:
        system_value = system_info.get(system_key)
        if system_value:
            rows.append((system_key, _home_relative_report_text(system_value)))

    return rows


def _home_relative_report_text(value: str) -> str:
    """Replace local private prefixes in public report text."""
    home = str(Path.home())
    sanitized = value if home == "/" else value.replace(home, "~")
    sanitized = re.sub(r"/(?:Users|home)/[^/\s\"'<>]+", "~", sanitized)
    return re.sub(r"/private(?=/|$)", "<private>", sanitized)


def _public_model_provenance(
    record: ModelProvenanceRecord,
) -> ModelProvenanceRecord:
    """Return provenance with its operational snapshot path made portable."""
    return {
        **record,
        "snapshot_path": (
            _home_relative_report_text(record["snapshot_path"])
            if record["snapshot_path"] is not None
            else None
        ),
    }


def _quality_analysis_for_result(res: PerformanceResult) -> GenerationQualityAnalysis | None:
    """Return cached quality analysis for a result when present."""
    return res.quality_analysis


_EXTERNAL_CONNECTIVITY_NEEDLES: Final[tuple[str, ...]] = (
    "server disconnected without sending a response",
    "remoteprotocolerror",
    "connection refused",
    "connection reset",
    "connection aborted",
    "connection error",
    "network is unreachable",
    "temporary failure in name resolution",
    "nodename nor servname provided",
    "failed to establish a new connection",
    "503 service unavailable",
    "502 bad gateway",
    "504 gateway timeout",
)


def _has_external_connectivity_signal(text: str) -> bool:
    """Return whether text contains a narrow external-connectivity signature."""
    normalized = text.casefold()
    return any(needle in normalized for needle in _EXTERNAL_CONNECTIVITY_NEEDLES)


def _is_indeterminate_connectivity_failure(result: PerformanceResult) -> bool:
    """Return whether connectivity prevented a conclusive model attempt."""
    if result.success:
        return False
    combined = " ".join(
        part.casefold()
        for part in (
            result.error_message,
            result.error_traceback,
            result.captured_output_on_fail,
        )
        if part
    )
    return _has_external_connectivity_signal(combined)


# huggingface-hub download progress markers that show a load-phase timeout
# fired while the checkpoint was still being fetched, i.e. the model was
# never actually loaded or exercised.
_HF_DOWNLOAD_PROGRESS_NEEDLES: Final[tuple[str, ...]] = (
    "fetching ",  # "Fetching 13 files:  77%"
    "downloading bytes",
    "reconstructing (incomplete total",
    "not found in hf cache",
    "b/s]",  # per-file tqdm bar rate suffix: "... 7.4G/20.1G [04:02<07:12, 29.3MB/s]"
)


_THINKING_TEMPLATE_MARKERS: Final[tuple[str, ...]] = (
    "enable_thinking",
    "thinking_config",
    "reasoning_content",
    "<think>",
    "</think>",
    "<thinking>",
    "◁think▷",
)


def _resolve_snapshot_file(snapshot_path: Path, file_name: str) -> Path | None:
    """Resolve one snapshot file to a contained regular file, following links.

    Real HF cache snapshots link every file into the repo's ``blobs/`` store
    by design, so the no-follow artifact readers reject them outright. This
    follows the link but requires the target to remain inside the repo's
    cache directory (``models--*``, when the snapshot sits in the standard
    ``snapshots/`` layout) or inside the snapshot directory itself (a plain
    local model directory). Returns None when absent, escaping, or not a
    regular file.
    """
    candidate = snapshot_path / file_name
    try:
        root = (
            snapshot_path.parent.parent
            if snapshot_path.parent.name == "snapshots"
            else snapshot_path
        ).resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(root):
            return None
    except OSError:
        return None
    return resolved


def _read_snapshot_text(snapshot_path: Path, file_name: str) -> str | None:
    """Read one snapshot text file through :func:`_resolve_snapshot_file`."""
    resolved = _resolve_snapshot_file(snapshot_path, file_name)
    if resolved is None:
        return None
    try:
        return _read_text_file(resolved)
    except (OSError, ValueError):
        return None


def _read_snapshot_json(snapshot_path: Path, file_name: str) -> dict[str, JsonLike] | None:
    """Read one snapshot JSON object file; None when absent, unreadable, or not an object."""
    text = _read_snapshot_text(snapshot_path, file_name)
    if text is None:
        return None
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _template_declares_thinking(snapshot_path: Path | None) -> bool | None:
    """Scan a snapshot's chat template(s) for thinking markers (Nativ-style).

    Discovery-time complement to the render-time auto-budget check: a model
    whose template *declares* thinking but does not pre-open a block is the
    self-opening case a rendered-prompt check cannot see. Returns None when no
    chat template is found at all.
    """
    if snapshot_path is None or not snapshot_path.is_dir():
        return None
    found_template = False
    if (snapshot_path / "chat_template.jinja").is_file():
        found_template = True
        template_text = (_read_snapshot_text(snapshot_path, "chat_template.jinja") or "").casefold()
        if any(marker in template_text for marker in _THINKING_TEMPLATE_MARKERS):
            return True
    for file_name in ("tokenizer_config.json", "processor_config.json", "chat_template.json"):
        payload = _read_snapshot_json(snapshot_path, file_name)
        if payload is None:
            continue
        template_value = payload.get("chat_template")
        if template_value is None:
            continue
        found_template = True
        template_text = json.dumps(template_value, ensure_ascii=False).casefold()
        if any(marker in template_text for marker in _THINKING_TEMPLATE_MARKERS):
            return True
    return False if found_template else None


_PARAM_COUNT_NAME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([bm])(?![a-z0-9])", re.IGNORECASE)
# "A3B" / "a4b": an *active*-parameter designation (MoE), never the total.
_ACTIVE_PARAM_COUNT_NAME_RE = re.compile(
    r"(?<![a-z0-9])a(\d+(?:\.\d+)?)([bm])(?![a-z0-9])", re.IGNORECASE
)
_CONTEXT_LENGTH_CONFIG_KEYS: Final[tuple[str, ...]] = (
    "max_position_embeddings",
    "context_length",
    "max_sequence_length",
    "seq_length",
)


@dataclass(frozen=True)
class ModelBurdenFacts:
    """Raw, source-labelled facts about a model's on-disk and declared burden.

    Facts only, per review of the Nativ adaptation: no fit verdict, no
    headroom heuristics — the harness measures actual MLX memory, and these
    exist to explain load time and memory behaviour (e.g. load active memory
    far above checkpoint bytes is anomalous overhead worth a look).
    """

    weight_bytes: int | None = None
    parameter_count: int | None = None
    parameter_count_source: str | None = None
    active_parameter_count: int | None = None
    quantization_bits: int | None = None
    quantization_group_size: int | None = None
    quantization_mode: str | None = None
    context_length: int | None = None
    context_length_source: str | None = None


def _snapshot_weight_bytes(snapshot_path: Path) -> int | None:
    """Sum the sizes of the weight files the loader would actually select.

    Follows :func:`_loader_selected_weight_files`, so stale extra shard
    families, adapters beside an indexed checkpoint, and
    ``consolidated.safetensors`` never inflate the checkpoint bytes.
    """
    total = 0
    counted = 0
    for resolved in _loader_selected_weight_files(snapshot_path):
        try:
            total += resolved.stat().st_size
        except OSError:
            continue
        counted += 1
    return total if counted else None


def _size_token_value(value_text: str, unit: str) -> int:
    """Convert one "<number><B|M>" token to a parameter count."""
    # Decimal, not float: int(float("4.1") * 1e9) truncates to 4_099_999_999
    # (same defect mlx-lm fixed in ml-explore/mlx-lm#1726).
    return int(Decimal(value_text) * (10**9 if unit.lower() == "b" else 10**6))


def _parameter_counts_from_name(model_identifier: str) -> tuple[int | None, int | None]:
    """Return (total, active) parameter estimates from the size tokens in a name.

    MoE names may carry both ("30B-A3B") or only the active size ("A3B" in
    Kimi-VL-A3B). An active designation never stands in for the total: a
    name with no plain size token leaves the total unknown rather than
    reporting the active count as the checkpoint size.
    """
    active_spans = [
        (match.start(), match.end(), _size_token_value(match.group(1), match.group(2)))
        for match in _ACTIVE_PARAM_COUNT_NAME_RE.finditer(model_identifier)
    ]
    totals = [
        _size_token_value(match.group(1), match.group(2))
        for match in _PARAM_COUNT_NAME_RE.finditer(model_identifier)
        if not any(start <= match.start() < end for start, end, _value in active_spans)
    ]
    return (
        max(totals) if totals else None,
        max(value for _start, _end, value in active_spans) if active_spans else None,
    )


def _collect_model_burden(
    model_identifier: str,
    requested_revision: str | None = None,
) -> ModelBurdenFacts | None:
    """Collect burden facts from the resolved snapshot; None when unavailable."""
    snapshot_path = _resolve_model_snapshot_path(model_identifier, requested_revision)
    if snapshot_path is None or not snapshot_path.is_dir():
        # A cold in-process download during this run postdates the cached
        # cache scan; refresh once so the run's own downloads are visible.
        try:
            _get_hf_cache_info_cached(refresh=True)
        except (OSError, ValueError, FileNotFoundError, HFValidationError):
            return None
        snapshot_path = _resolve_model_snapshot_path(model_identifier, requested_revision)
    if snapshot_path is None or not snapshot_path.is_dir():
        return None
    config: dict[str, JsonLike] = _read_snapshot_json(snapshot_path, "config.json") or {}

    parameter_count: int | None = None
    parameter_count_source: str | None = None
    for key in ("num_parameters", "total_params", "n_params"):
        value = config.get(key)
        if isinstance(value, int) and value > 0:
            parameter_count = value
            parameter_count_source = key
            break
    active_parameter_count: int | None = None
    if parameter_count is None:
        parameter_count, active_parameter_count = _parameter_counts_from_name(model_identifier)
        if parameter_count is not None or active_parameter_count is not None:
            parameter_count_source = "name-estimate"

    quantization = config.get("quantization")
    quantization_bits: int | None = None
    quantization_group_size: int | None = None
    quantization_mode: str | None = None
    if isinstance(quantization, dict):
        bits = quantization.get("bits")
        group_size = quantization.get("group_size")
        mode = quantization.get("mode")
        quantization_bits = bits if isinstance(bits, int) else None
        quantization_group_size = group_size if isinstance(group_size, int) else None
        quantization_mode = mode if isinstance(mode, str) else None

    context_length: int | None = None
    context_length_source: str | None = None
    search_spaces: list[tuple[str, Mapping[str, JsonLike]]] = [("", config)]
    text_config = config.get("text_config")
    if isinstance(text_config, dict):
        search_spaces.append(("text_config.", text_config))
    for prefix, space in search_spaces:
        for key in _CONTEXT_LENGTH_CONFIG_KEYS:
            value = space.get(key)
            if isinstance(value, int) and value > 0:
                context_length = value
                context_length_source = f"{prefix}{key}"
                break
        if context_length is not None:
            break

    return ModelBurdenFacts(
        weight_bytes=_snapshot_weight_bytes(snapshot_path),
        parameter_count=parameter_count,
        parameter_count_source=parameter_count_source,
        active_parameter_count=active_parameter_count,
        quantization_bits=quantization_bits,
        quantization_group_size=quantization_group_size,
        quantization_mode=quantization_mode,
        context_length=context_length,
        context_length_source=context_length_source,
    )


class WeightShardStatus(NamedTuple):
    """Completeness of a sharded checkpoint per its safetensors index.

    ``index_error`` is set when an index file exists but cannot be read or
    validated — that fails closed (an unreadable index on a sharded
    checkpoint is itself evidence of an incomplete or corrupt download),
    unlike the absence of an index, which simply means a single-file
    checkpoint.
    """

    missing: int
    total: int
    missing_sample: tuple[str, ...]
    index_error: str | None = None


_WEIGHT_SHARD_SAMPLE_LIMIT: Final[int] = 5

INCOMPLETE_CACHE_REMEDY: Final[str] = (
    "The snapshot's safetensors index references weight shards that are absent "
    "or empty — typically an interrupted download. Re-run to resume it, or "
    "re-fetch with `hf download <model>`."
)


_SHARD_FAMILY_RE = re.compile(r"^(?P<stem>.+)-(?P<part>\d+)-of-(?P<total>\d+)\.safetensors$")


_FULL_CHECKPOINT_LOOSE_NAMES: Final[frozenset[str]] = frozenset(
    {"model.safetensors", "weights.safetensors"}
)


def _indexed_shard_names(snapshot_path: Path) -> tuple[str, ...] | None:
    """Shard names from the safetensors index; None when absent or unusable."""
    payload = _read_snapshot_json(snapshot_path, "model.safetensors.index.json")
    weight_map = payload.get("weight_map") if payload is not None else None
    if not isinstance(weight_map, dict):
        return None
    names = tuple(sorted({str(name) for name in weight_map.values() if name}))
    return names or None


def _glob_weight_names(snapshot_path: Path) -> tuple[str, ...] | None:
    """The loader's glob candidates: *.safetensors minus consolidated.safetensors."""
    try:
        return tuple(
            sorted(
                path.name
                for path in snapshot_path.glob("*.safetensors")
                if not path.name.endswith("consolidated.safetensors")
            )
        )
    except OSError:
        return None


def _loader_selected_weight_files(snapshot_path: Path) -> tuple[Path, ...]:
    """Containment-checked weight files mlx-vlm's load_model would select.

    Mirrors the loader's branch decision exactly: the indexed shards that
    exist win (a partial subset is selected as-is); only when the index is
    absent, unreadable, or empty — or none of its shards exist — does the
    glob fallback apply. Selected names resolve through the containment
    check; escaping or non-regular entries are dropped.
    """
    indexed = _indexed_shard_names(snapshot_path)
    names: tuple[str, ...] | None = None
    if indexed is not None:
        existing = tuple(name for name in indexed if (snapshot_path / name).exists())
        if existing:
            names = existing
    if names is None:
        names = _glob_weight_names(snapshot_path) or ()
    return tuple(
        resolved
        for name in names
        if (resolved := _resolve_snapshot_file(snapshot_path, name)) is not None
    )


def _loader_fallback_weights_present(snapshot_path: Path) -> bool:
    """Return whether mlx-vlm's glob fallback would find a complete weight set.

    The loader consults the index first, keeping the indexed shards that
    exist; only when none exist does it fall back to globbing
    ``*.safetensors`` (excluding ``consolidated.safetensors``) — e.g. a stale
    index beside a re-sharded checkpoint. Aligned with Nativ's discovery fix
    for the same class of snapshot (Blaizzy/nativ#370), the glob'd set must
    stand on its own: exactly one loose full-checkpoint file, or exactly the
    complete 1..N of one ``model``-stem shard series. Anything else swept up
    by the blind glob — a second series, an adapter, a stray loose file —
    would be merged into the load and cannot be vouched for. One deliberate
    divergence from Nativ remains at the call sites: a malformed or empty
    index with a self-standing weight set still rescues here, because
    mlx-vlm's Python loader swallows index errors and globs.
    """
    names = _glob_weight_names(snapshot_path)
    if names is None:
        return False
    families: dict[tuple[str, int], set[int]] = {}
    loose_full_checkpoint = 0
    for name in names:
        resolved = _resolve_snapshot_file(snapshot_path, name)
        try:
            usable = resolved is not None and resolved.stat().st_size > 0
        except OSError:
            usable = False
        if not usable:
            return False
        match = _SHARD_FAMILY_RE.match(name)
        if match is None:
            if name not in _FULL_CHECKPOINT_LOOSE_NAMES:
                # Adapters and other auxiliary safetensors would be merged
                # into the load; the set no longer stands on its own.
                return False
            loose_full_checkpoint += 1
            continue
        key = (match.group("stem"), int(match.group("total")))
        families.setdefault(key, set()).add(int(match.group("part")))
    if loose_full_checkpoint:
        return loose_full_checkpoint == 1 and not families
    if len(families) != 1:
        return False
    (stem, total), present = next(iter(families.items()))
    return stem == "model" and present == set(range(1, total + 1))


def _weight_shard_status(snapshot_path: Path) -> WeightShardStatus | None:
    """Check every shard the safetensors index references, Nativ-style.

    The index file downloads before its shards, so its mere presence does not
    make a model runnable. Each referenced shard must exist, resolve inside
    this repo's cache directory, and be a non-empty regular file. Returns None
    when there is no index (single-file checkpoints are validated by the
    plain safetensors presence check) — and likewise when the index is
    broken or wholly stale but the loader's glob fallback would find a
    complete weight set, because mlx-vlm swallows index errors and ignores
    an index none of whose shards exist.
    """
    index_path = snapshot_path / "model.safetensors.index.json"
    if not index_path.exists() and not index_path.is_symlink():
        return None

    def _invalid(reason: str) -> WeightShardStatus | None:
        # The loader swallows index errors and falls back to globbing
        # *.safetensors; a broken index beside a complete weight set is
        # therefore runnable (None: the plain presence check governs).
        # Without one, the broken index stays evidence of a corrupt
        # download and fails closed.
        if _loader_fallback_weights_present(snapshot_path):
            return None
        return WeightShardStatus(0, 0, (), index_error=reason)

    index_text = _read_snapshot_text(snapshot_path, "model.safetensors.index.json")
    if index_text is None:
        return _invalid("unreadable safetensors index (absent target or escaping link)")
    try:
        payload = json.loads(index_text)
    except ValueError as error:
        return _invalid(f"unreadable safetensors index ({error})")
    weight_map = payload.get("weight_map") if isinstance(payload, dict) else None
    if not isinstance(weight_map, dict):
        return _invalid("safetensors index has no weight_map object")
    shard_names = sorted({str(name) for name in weight_map.values() if name})
    if not shard_names:
        return _invalid("safetensors index names no shards")
    missing: list[str] = []
    for name in shard_names:
        resolved = _resolve_snapshot_file(snapshot_path, name)
        try:
            complete = resolved is not None and resolved.stat().st_size > 0
        except OSError:
            complete = False
        if not complete:
            missing.append(name)
    if missing:
        # mlx-vlm ignores the index only when none of its shards exist at
        # all; with a partial indexed subset it loads that subset, which
        # cannot supply the missing weights. Mirror that branch exactly
        # before crediting the loader's glob fallback.
        any_indexed_present = any((snapshot_path / name).exists() for name in shard_names)
        if not any_indexed_present and _loader_fallback_weights_present(snapshot_path):
            missing = []
    return WeightShardStatus(
        missing=len(missing),
        total=len(shard_names),
        missing_sample=tuple(missing[:_WEIGHT_SHARD_SAMPLE_LIMIT]),
    )


def _is_incomplete_cache_failure(result: PerformanceResult) -> bool:
    """Return whether a load failure sits on an incompletely downloaded snapshot.

    Environmental, like a download timeout: the model never had its weights,
    so the failure is evidence about the cache, not the model or runtime.
    """
    if result.success or result.failure_phase != "model_load":
        return False
    snapshot_path = _resolve_model_snapshot_path(result.model_name, result.requested_revision)
    if snapshot_path is None:
        return False
    status = _weight_shard_status(snapshot_path)
    return status is not None and (status.missing > 0 or status.index_error is not None)


DOWNLOAD_TIMEOUT_REMEDY: Final[str] = (
    "the per-model timeout expired while the checkpoint was still downloading, so the "
    "model was never loaded or tested. This is a local environment condition, not an "
    "mlx-vlm or model defect. Hugging Face Hub resumes partial downloads, so simply "
    "re-run to finish; or pre-fetch once with `hf download <model>` so the harness only "
    "sees a cached model; or give this cold run more headroom with --timeout."
)


def _is_download_timeout_failure(result: PerformanceResult) -> bool:
    """Return whether the per-model timeout expired mid-download.

    A cold first-time download of a large checkpoint can legitimately exceed
    the timeout that exists to bound hung *inference*. That is an
    environmental, indeterminate outcome — the model was never loaded, let
    alone run — not evidence of an mlx-vlm or model defect, so it must not
    become an actionable crash with a maintainer-facing issue draft.
    """
    if result.success or result.failure_phase != "model_load":
        return False

    def _is_timeout_type(name: str | None) -> bool:
        # Subclasses keep their own names (e.g. IsolatedWorkerTimeoutError);
        # anything in the TimeoutError family counts.
        return name is not None and name.endswith("TimeoutError")

    stop_reason = (
        result.runtime_diagnostics.stop_reason if result.runtime_diagnostics is not None else None
    )
    if (
        not _is_timeout_type(result.root_error_type)
        and not _is_timeout_type(result.error_type)
        and stop_reason != "timeout"
    ):
        chain_types = {entry.exception_type for entry in result.exception_chain}
        if not any(_is_timeout_type(name) for name in chain_types):
            return False
    captured = (result.captured_output_on_fail or "").casefold()
    return any(needle in captured for needle in _HF_DOWNLOAD_PROGRESS_NEEDLES)


def _advance_upstream_boundary(
    boundary: UpstreamBoundary,
    phase: str,
) -> UpstreamBoundary:
    """Advance, but never regress, the deepest entered upstream boundary."""
    if phase in _GENERATION_FAILURE_PHASES:
        return "generation_started"
    if phase == "model_load" and boundary == "not_started":
        return "load_started"
    return boundary


def _run_outcome_counts(
    assessments: Sequence[tuple[str, ResultAssessment]],
) -> RunOutcomeCounts:
    """Count cached execution statuses without reclassifying report rows."""
    statuses = [assessment.execution for _model, assessment in assessments]
    completed = statuses.count("completed")
    crashed = statuses.count("crashed")
    indeterminate = statuses.count("indeterminate")
    return {
        "models_attempted": len(statuses),
        "models_evaluated": completed + crashed,
        "models_completed": completed,
        "models_crashed": crashed,
        "models_indeterminate": indeterminate,
    }


GALLERY_STAMP_LIBRARY_NAMES: Final[tuple[str, ...]] = (
    "mlx-vlm",
    "mlx",
    "mlx-metal",
    "transformers",
    "tokenizers",
    "huggingface-hub",
)
GALLERY_STAMP_SYSTEM_KEYS: Final[tuple[str, ...]] = (
    "Python Version",
    "OS",
    "macOS Version",
    "GPU/Chip",
    "MLX Device",
    "GPU Architecture",
    "RAM",
    "Recommended Working Set",
    "Fused Attention",
)


def _markdown_inline_code(value: str) -> str:
    """Return a safe inline-code span for generated Markdown table cells."""
    escaped = MARKDOWN_ESCAPER.escape(value).replace("`", "&#96;")
    return f"`{escaped}`"


def _build_gallery_stamps_section(
    *,
    versions: LibraryVersionDict | None,
    system_info: Mapping[str, str],
) -> list[str]:
    """Build package and runtime stamps for the standalone gallery artifact."""
    if not versions:
        return []

    component_rows = _collect_report_component_rows(
        versions=versions or {},
        system_info=system_info,
        library_names=GALLERY_STAMP_LIBRARY_NAMES,
        system_keys=GALLERY_STAMP_SYSTEM_KEYS,
    )
    if not component_rows:
        return []

    library_names = set(GALLERY_STAMP_LIBRARY_NAMES)
    parts: list[str] = ["## Run Stamps", ""]
    for name, value in component_rows:
        if name in library_names:
            parts.append(
                f"- {_markdown_inline_code(name)}: {_markdown_inline_code(value)}",
            )
        else:
            _append_markdown_labeled_value(parts, label=name, value=value, bullet=True)
    parts.append("")
    return parts


def _gallery_summary_model_link(model_name: str) -> str:
    """Return a safe self-link for a model row in the gallery summary table."""
    escaped_name = MARKDOWN_ESCAPER.escape(model_name)
    return f"[`{escaped_name}`](#{_gallery_model_anchor(model_name)})"


def _valid_generation_tps(result: PerformanceResult) -> float | None:
    """Return mechanically valid throughput for a sufficiently large sample."""
    tokens = _generation_int_metric(result.generation, "generation_tokens")
    rate = _generation_float_metric(result.generation, "generation_tps")
    if tokens is None or tokens < MIN_THROUGHPUT_SAMPLE_TOKENS:
        return None
    return rate if rate is not None and rate >= 0 else None


_PREVIEW_TITLE_CHARS: Final[int] = 80
_PREVIEW_KEYWORDS_CHARS: Final[int] = 110
_PREVIEW_DESCRIPTION_MIN_CHARS: Final[int] = 60


def _field_aware_preview(answer: str, *, max_chars: int) -> str | None:
    """Preview a little of each catalogue field instead of the answer's head.

    A head-only preview spends its budget on the title and description and
    hides the keywords, usually the weakest field. Returns ``None`` when no
    labelled field was detected, so the caller falls back to the head.
    """
    sections = _extract_catalog_sections(answer)
    if not sections:
        return None
    collapse = _collapse_preview_line_whitespace

    def _field(label: str, body: str, budget: int) -> str:
        if not body.strip():
            return f"{label}: (not detected)"
        return f"{label}: {_truncate_text_preview(collapse(body).replace(chr(10), ' '), max_chars=budget)}"

    title_part = _field("Title", sections.get("title", ""), _PREVIEW_TITLE_CHARS)
    keywords = _split_catalog_keywords(sections.get("keywords", ""))
    if keywords:
        shown: list[str] = []
        for keyword in keywords:
            candidate = ", ".join([*shown, keyword])
            if len(candidate) > _PREVIEW_KEYWORDS_CHARS and shown:
                break
            shown.append(keyword)
        listed = ", ".join(shown) + (", ..." if len(shown) < len(keywords) else "")
        keywords_part = f"Keywords ({len(keywords)}): {listed}"
    else:
        keywords_part = "Keywords: (not detected)"
    separators = 2 * len(" | ")
    description_budget = max(
        _PREVIEW_DESCRIPTION_MIN_CHARS,
        max_chars - len(title_part) - len(keywords_part) - separators,
    )
    description_part = _field("Description", sections.get("description", ""), description_budget)
    return f"{title_part} | {description_part} | {keywords_part}"


def _gallery_row(result: PerformanceResult, assessment: ResultAssessment) -> GalleryRow:
    """Build one chooser row from cached assessment and captured facts only."""
    generation = result.generation
    output = _generation_text_value(generation)
    reasoning = ""
    field_preview: str | None = None
    if assessment.execution == "completed":
        # The preview shows what the model finally answered; a closed
        # reasoning trace is counted and kept available under disclosure so
        # a thinking model's preview is not spent on its scratch work.
        answer, reasoning = _final_answer_text(result)
        preview_source = answer or "empty output"
        if result.assessment_profile == "metadata":
            field_preview = _field_aware_preview(answer, max_chars=MAX_OUTPUT_PREVIEW_CHARS)
    else:
        preview_source = (
            result.error_message
            or result.error_traceback
            or output
            or result.captured_output_on_fail
            or "no failure evidence captured"
        )
    output_preview = field_preview or _truncate_text_preview(
        _collapse_preview_line_whitespace(preview_source),
        max_chars=MAX_OUTPUT_PREVIEW_CHARS,
    )
    peak_memory = _generation_float_metric(generation, "peak_memory")
    reasoning_preview = _truncate_text_preview(
        _collapse_preview_line_whitespace(reasoning), max_chars=MAX_OUTPUT_PREVIEW_CHARS
    )
    return GalleryRow(
        model=result.model_name,
        usability=assessment.usability,
        observations=assessment.observations,
        total_time_s=(
            result.total_time if result.total_time is not None and result.total_time >= 0 else None
        ),
        generation_tps=_valid_generation_tps(result),
        first_token_latency_s=(
            result.runtime_diagnostics.first_token_latency_s
            if result.runtime_diagnostics is not None
            else None
        ),
        peak_memory_gb=(peak_memory if peak_memory is not None and peak_memory >= 0 else None),
        prompt_tokens=_generation_int_metric(generation, "prompt_tokens"),
        generation_tokens=_generation_int_metric(generation, "generation_tokens"),
        output_preview=output_preview,
        reasoning_chars=len(reasoning),
        reasoning_preview=reasoning_preview,
    )


@dataclass(frozen=True, slots=True)
class ObservationDisplaySpec:
    """Single source of truth for one mechanical observation code."""

    code: ObservationCode
    maintainer_label: str
    selector_gloss: str
    unusable: bool = False
    # True when the observation plausibly indicates an mlx-vlm/library
    # integration issue (template handling, detokenization, control-token
    # leakage, degenerate decoding) rather than model prompt compliance.
    # Compliance-only observations stay chooser-relevant but do not put a
    # model into the maintainer lane.
    integration_signal: bool = False


# Display priority is list order: gross unusable signals first, then caveats.
_OBSERVATION_DISPLAY_SPECS: Final[tuple[ObservationDisplaySpec, ...]] = (
    ObservationDisplaySpec(
        "empty_output",
        "No response text was returned",
        "empty response",
        unusable=True,
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "repeated_output",
        "Response repeats the same text",
        "repeated text",
        unusable=True,
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "repetition_abort",
        "Generation was stopped early after sustained repeated output",
        "stopped early: repeating",
        unusable=True,
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "final_answer_duplicated",
        "Final answer emitted twice",
        "answer emitted twice",
        unusable=True,
    ),
    ObservationDisplaySpec(
        "missing_final_answer",
        "Internal reasoning is present but no final answer was returned",
        "thinking only, no answer",
        unusable=True,
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "unexpected_special_token",
        "Unrecognised model control tokens remain visible",
        "control tokens visible",
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "missing_requested_sections",
        "Required labelled fields not detected",
        "labelled fields not detected",
        unusable=True,
    ),
    ObservationDisplaySpec(
        "prompt_instruction_echo",
        "Response repeats the task instructions instead of only returning the requested fields",
        "echoes instructions",
        unusable=True,
    ),
    ObservationDisplaySpec(
        "unexpected_catalog_preamble",
        "Extra text appears before the Title field",
        "extra text before Title",
        unusable=True,
    ),
    ObservationDisplaySpec(
        "token_cap_truncation",
        "Response appears cut off at the token limit",
        "cut off at token limit",
        unusable=True,
    ),
    ObservationDisplaySpec(
        "thinking_trace_incomplete",
        "Internal reasoning block appears incomplete",
        "incomplete thinking block",
        unusable=True,
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "role_boundary_token_present",
        "Conversation-role control tokens remain visible",
        "role tokens visible",
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "thinking_trace_present",
        "Internal reasoning text remains visible",
        "thinking text visible",
        integration_signal=True,
    ),
    ObservationDisplaySpec(
        "configured_wrapper_present",
        "Expected model wrapper tokens remain visible",
        "wrapper tokens visible",
        integration_signal=True,
    ),
    ObservationDisplaySpec("duplicate_keywords", "Repeated keyword entries", "duplicate keywords"),
    # Legacy codes remain renderable for retained pre-0.17 evidence.
    ObservationDisplaySpec(
        "catalog_constraint_violation",
        "Title, description or keywords do not meet requested constraints",
        "title/description/keyword constraints failed",
    ),
    ObservationDisplaySpec(
        "minimal_output",
        "Response is unusually short",
        "very short response",
    ),
    ObservationDisplaySpec(
        "draft_returned_unchanged",
        "Title, Description and Keywords copy all supplied hints unchanged",
        "draft hints copied unchanged",
    ),
    ObservationDisplaySpec(
        "no_keyword_overlap",
        "Keywords do not overlap the supplied keyword hints",
        "no keyword overlap",
    ),
)
_OBSERVATION_DISPLAY_BY_CODE: Final[dict[ObservationCode, ObservationDisplaySpec]] = {
    spec.code: spec for spec in _OBSERVATION_DISPLAY_SPECS
}
_OBSERVATION_DISPLAY_PRIORITY: Final[tuple[ObservationCode, ...]] = tuple(
    spec.code for spec in _OBSERVATION_DISPLAY_SPECS
)
_OBSERVATION_DISPLAY_RANK: Final[dict[ObservationCode, int]] = {
    code: index for index, code in enumerate(_OBSERVATION_DISPLAY_PRIORITY)
}
_OBSERVATION_DISPLAY_LABELS: Final[dict[ObservationCode, str]] = {
    spec.code: spec.maintainer_label for spec in _OBSERVATION_DISPLAY_SPECS
}
_OBSERVATION_SELECTOR_GLOSSES: Final[dict[ObservationCode, str]] = {
    spec.code: spec.selector_gloss for spec in _OBSERVATION_DISPLAY_SPECS
}
_UNUSABLE_OBSERVATIONS: Final[frozenset[ObservationCode]] = frozenset(
    spec.code for spec in _OBSERVATION_DISPLAY_SPECS if spec.unusable
)
_INTEGRATION_SIGNAL_OBSERVATIONS: Final[frozenset[ObservationCode]] = frozenset(
    spec.code for spec in _OBSERVATION_DISPLAY_SPECS if spec.integration_signal
)
_RANGE_ENDPOINT_COUNT: Final[int] = 2
_USABILITY_DISPLAY_PRIORITY: Final[dict[ModelUsability, int]] = {
    "unusable": 0,
    "usable_with_caveats": 1,
    "usable": 2,
    "not_evaluated": 3,
}


def _literal_values(alias: object) -> frozenset[str]:
    """Return the string members of a PEP 695 `type X = Literal[...]` alias."""
    value = getattr(alias, "__value__", alias)
    return frozenset(cast("tuple[str, ...]", get_args(value)))


_EXECUTION_STATUS_VALUES: Final[frozenset[str]] = _literal_values(ExecutionStatus)
_MODEL_USABILITY_VALUES: Final[frozenset[str]] = _literal_values(ModelUsability)
_MAINTAINER_STATUS_VALUES: Final[frozenset[str]] = _literal_values(MaintainerStatus)
_OBSERVATION_CODE_VALUES: Final[frozenset[str]] = _literal_values(ObservationCode)

if set(_OBSERVATION_DISPLAY_BY_CODE) != _OBSERVATION_CODE_VALUES or len(
    _OBSERVATION_DISPLAY_SPECS
) != len(_OBSERVATION_CODE_VALUES):
    missing = sorted(_OBSERVATION_CODE_VALUES - set(_OBSERVATION_DISPLAY_BY_CODE))
    extra = sorted(set(_OBSERVATION_DISPLAY_BY_CODE) - _OBSERVATION_CODE_VALUES)
    message = (
        "Observation display registry must cover ObservationCode exactly; "
        f"missing={missing!r} extra={extra!r}"
    )
    raise RuntimeError(message)


def _assessment_actionability_key(
    model_name: str,
    usability: ModelUsability,
    observations: Sequence[ObservationCode],
) -> tuple[int, int, str]:
    """Order gross observations before repairable caveats, then by model."""
    severity = min(
        (
            _OBSERVATION_DISPLAY_RANK.get(code, len(_OBSERVATION_DISPLAY_RANK))
            for code in observations
        ),
        default=len(_OBSERVATION_DISPLAY_RANK),
    )
    return severity, _USABILITY_DISPLAY_PRIORITY[usability], model_name.casefold()


def _human_status_label(status: str) -> str:
    """Render a stable machine status for human-facing report surfaces."""
    return {
        "usable": "no concerns detected",
        "usable_with_caveats": "concerns detected",
        "unusable": "major concerns",
        "not_evaluated": "not assessed",
    }.get(status, status.replace("_", " "))


def _constraint_violation_labels(details: JsonlObservationDetailsRecord) -> list[str]:
    """Name only the catalogue constraints that were actually breached."""
    # Name only the constraints that were actually breached; an
    # in-range count alongside e.g. a duplicate-keyword violation must
    # not read as a second failure.
    constraint_labels: list[str] = []
    title_count = details.get("title_word_count")
    title_range = details.get("title_word_range")
    if (
        title_count is not None
        and title_range is not None
        and len(title_range) == _RANGE_ENDPOINT_COUNT
        and not title_range[0] <= title_count <= title_range[1]
    ):
        constraint_labels.append(
            f"Title has {title_count} words (requested {title_range[0]}-{title_range[1]})"
        )
    sentence_count = details.get("description_sentence_count")
    sentence_range = details.get("description_sentence_range")
    if (
        sentence_count is not None
        and sentence_range is not None
        and len(sentence_range) == _RANGE_ENDPOINT_COUNT
        and sentence_count > sentence_range[1]
    ):
        constraint_labels.append(
            f"Description has {sentence_count} sentences "
            f"(requested {sentence_range[0]}-{sentence_range[1]})"
        )
    keyword_count = details.get("keyword_count")
    keyword_range = details.get("keyword_count_range")
    if (
        keyword_count is not None
        and keyword_range is not None
        and len(keyword_range) == _RANGE_ENDPOINT_COUNT
        and not keyword_range[0] <= keyword_count <= keyword_range[1]
    ):
        constraint_labels.append(
            "Keyword list has "
            f"{keyword_count} terms (requested {keyword_range[0]}-{keyword_range[1]})"
        )
    duplicate_keywords = details.get("duplicate_keywords")
    if duplicate_keywords:
        constraint_labels.append(f"Duplicate keywords: {', '.join(duplicate_keywords)}")
    return constraint_labels


def _human_observation_labels(
    observations: Sequence[ObservationCode],
    *,
    details: JsonlObservationDetailsRecord | None = None,
) -> str:
    """Render stable observation codes as explanatory severity-ordered labels."""
    observed = set(observations)
    labels: list[str] = []
    for code in _OBSERVATION_DISPLAY_PRIORITY:
        if code not in observed:
            continue
        label = _OBSERVATION_DISPLAY_LABELS[code]
        if code == "missing_requested_sections" and details is not None:
            missing_sections = details.get("missing_sections")
            if missing_sections:
                # Strict label parsing: the content may still be present in an
                # unlabelled form, which the visible answer lets a human judge.
                fields = ", ".join(missing_sections)
                label = f"Required labelled fields not detected: {fields}"
        elif code == "final_answer_duplicated" and details is not None:
            separator = details.get("duplicated_answer_separator")
            if isinstance(separator, str) and separator:
                label = f"Final answer emitted twice, around {separator}"
        elif code in {"catalog_constraint_violation", "duplicate_keywords"} and details is not None:
            if constraint_labels := _constraint_violation_labels(details):
                label = "; ".join(constraint_labels)
        labels.append(label)
    return "; ".join(labels) or "none"


def _gallery_observation_labels(observations: Sequence[ObservationCode]) -> str:
    """Render short selector-facing observation glosses in severity order."""
    observed = set(observations)
    glosses = [
        _OBSERVATION_SELECTOR_GLOSSES[code]
        for code in _OBSERVATION_DISPLAY_PRIORITY
        if code in observed
    ]
    return "; ".join(glosses) or "none"


def _gallery_usability_sort_key(usability: ModelUsability) -> int:
    """Order selector evidence from directly usable to not evaluated."""
    return {
        "usable": 0,
        "usable_with_caveats": 1,
        "unusable": 2,
        "not_evaluated": 3,
    }[usability]


def _gallery_metric(field_name: str, value: MetricValue) -> str:
    """Format one captured metric, using a dash when unavailable."""
    return format_field_value(field_name, value) or "-"


def _gallery_throughput_cell(row: GalleryRow) -> str:
    """Render valid throughput or the explicit short-sample label."""
    if row.generation_tps is not None:
        return f"{_gallery_metric('generation_tps', row.generation_tps)} tok/s"
    if row.generation_tokens is not None and row.generation_tokens < MIN_THROUGHPUT_SAMPLE_TOKENS:
        return "insufficient sample"
    return "-"


def _gallery_reasoning_note(row: GalleryRow) -> str:
    """Return the omitted-reasoning note for a preview, or an empty string."""
    if not row.reasoning_chars:
        return ""
    return f"{row.reasoning_chars:,} characters of reasoning omitted"


def _gallery_preview_cell_markdown(row: GalleryRow) -> str:
    """Render the final-answer preview plus the omitted-reasoning note."""
    cell = MARKDOWN_ESCAPER.escape(row.output_preview)
    if note := _gallery_reasoning_note(row):
        cell += MARKDOWN_ESCAPER.escape(f" [{note}; complete output in the evidence block]")
    return cell


def _gallery_preview_cell_html(row: GalleryRow) -> str:
    """Render the escaped preview with the reasoning trace under disclosure."""
    cell = html.escape(row.output_preview)
    if note := _gallery_reasoning_note(row):
        cell += (
            f"<details><summary>{html.escape(note)}</summary>"
            f"<pre>{html.escape(row.reasoning_preview)}</pre></details>"
        )
    return cell


def _gallery_total_time_cell(row: GalleryRow) -> str:
    """Render captured end-to-end model time ahead of decode-only throughput."""
    return _format_time_seconds(row.total_time_s) if row.total_time_s is not None else "-"


def _render_gallery_table(
    *,
    headers: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
) -> list[str]:
    """Render one compact gallery table with the established lint guard."""
    table_lines = render_report_markdown(
        (ReportTable(headers=headers, rows=tuple(rows), markdown_escaped=True),)
    )
    return _guard_markdownlint_block(
        table_lines,
        rules=MARKDOWNLINT_GALLERY_SUMMARY_RULES,
    )


@dataclass(frozen=True)
class GalleryChooserData:
    """Shared, pre-sorted chooser facts consumed by both report renderers."""

    ordered: tuple[GalleryRow, ...]
    avoided: tuple[GalleryRow, ...]
    quickest: GalleryRow | None
    lowest_memory: GalleryRow | None


def _gallery_chooser_data(rows: Sequence[GalleryRow]) -> GalleryChooserData:
    """Compute the single chooser ordering and resource highlights once.

    Highlights consider only completions that had no detected concerns
    (usable, no observations). That is a format/structure bar, not an
    accuracy bar — passing while copying hint keywords or misnaming the
    subject still qualifies, which is why the wording never says "clean" or
    "good". Time to complete the task end-to-end is the
    highlight, not decode tok/s: tokenizers, image-token expansion and
    reasoning lengths differ so much across models that a tok/s ranking or
    a cross-model average carries little decision value.
    """
    ordered = tuple(
        sorted(rows, key=lambda row: (_gallery_usability_sort_key(row.usability), row.model))
    )
    avoided = tuple(row for row in ordered if row.usability in {"unusable", "not_evaluated"})
    usable = [row for row in ordered if row.usability == "usable" and not row.observations]
    timed = [row for row in usable if row.total_time_s is not None]
    quickest = (
        min(timed, key=lambda row: (cast("float", row.total_time_s), row.model)) if timed else None
    )
    with_memory = [row for row in usable if row.peak_memory_gb is not None]
    lowest_memory = (
        min(with_memory, key=lambda row: (cast("float", row.peak_memory_gb), row.model))
        if with_memory
        else None
    )
    return GalleryChooserData(
        ordered=ordered,
        avoided=avoided,
        quickest=quickest,
        lowest_memory=lowest_memory,
    )


def _run_objective_statement(eval_mode: str | None) -> str:
    """One canonical scope statement shared verbatim by every report surface.

    The models under test serve many purposes; every surface must say up
    front which single narrow objective this run measured so readers do not
    mistake mechanical findings for general model quality.
    """
    return (
        "This run records model responses to one shared image and prompt "
        f"(evaluation lane: {eval_mode or 'unknown'}). "
        "Mechanical checks are not factual-accuracy judgments; inspect the image, prompt "
        "and final answers before choosing a model. Results do not establish fitness for other tasks."
    )


_GALLERY_THROUGHPUT_CAVEAT: Final[str] = (
    "Decode tok/s stays per model in the chooser and is not averaged across models: "
    "tokenizers, image-token expansion and reasoning lengths differ too much for a "
    "cross-model mean to guide a choice."
)


def _gallery_chooser_explanation() -> str:
    """Return the metric caveat shared verbatim by both chooser formats."""
    return (
        "Mechanical observations and captured resource facts for this run only. "
        "No concerns detected does not mean the response fulfilled an arbitrary prompt "
        "or described the image accurately. Consult the assessment scope above. Total time is end-to-end; "
        "throughput covers generation only and requires "
        f"at least {MIN_THROUGHPUT_SAMPLE_TOKENS} generated tokens. "
        "Prefill/first is first-token latency when captured; Prompt tok is the full "
        "rendered prompt including image tokens, which drives prefill cost. "
        "For cross-attention architectures the token count reflects the tokenised "
        "text burden only, not total vision prefill compute."
    )


def _render_gallery_chooser(rows: Sequence[GalleryRow]) -> list[str]:
    """Render the skim-first chooser, resource highlights, and avoid list."""
    data = _gallery_chooser_data(rows)
    ordered = data.ordered
    chooser_rows = [
        (
            _gallery_summary_model_link(row.model),
            _markdown_inline_code(_human_status_label(row.usability)),
            _gallery_total_time_cell(row),
            _gallery_throughput_cell(row),
            _format_float_or_dash(row.first_token_latency_s, digits=2),
            _gallery_metric("peak_memory", row.peak_memory_gb),
            _gallery_metric("prompt_tokens", row.prompt_tokens),
            _gallery_metric("generation_tokens", row.generation_tokens),
            MARKDOWN_ESCAPER.escape(_gallery_observation_labels(row.observations)),
        )
        for row in ordered
    ]
    parts = [
        "## Current-run Chooser",
        "",
        _gallery_chooser_explanation(),
        "",
        *_render_gallery_table(
            headers=(
                "Model",
                "Mechanical checks",
                "Total s",
                "Gen TPS",
                "Prefill/first s",
                "Peak GB",
                "Prompt tok",
                "Gen tok",
                "Observations",
            ),
            rows=chooser_rows,
        ),
        "",
        "## Resource Highlights",
        "",
    ]

    # One sortable row set replaces the former lowest-memory/fastest re-listing
    # tables; the highlights carry the same decisions in a few lines.
    if data.quickest is not None:
        parts.extend(
            [
                (
                    "Quickest completion without detected concerns (end-to-end, including "
                    f"model load): `{data.quickest.model}` at "
                    f"{_gallery_total_time_cell(data.quickest)}"
                ),
                "",
            ]
        )
    else:
        parts.extend(
            [
                (
                    "No completion without detected concerns has a captured end-to-end time "
                    "in this run."
                ),
                "",
            ]
        )
    if data.lowest_memory is not None:
        parts.extend(
            [
                (
                    "Lowest peak memory among completions without detected concerns: "
                    f"`{data.lowest_memory.model}` at "
                    f"{_gallery_metric('peak_memory', data.lowest_memory.peak_memory_gb)} GB"
                ),
                "",
            ]
        )
    parts.extend([_GALLERY_THROUGHPUT_CAVEAT, ""])
    parts.extend(["## Avoid for This Run", ""])

    if data.avoided:
        parts.extend(
            _render_gallery_table(
                headers=("Model", "Mechanical checks", "Observations"),
                rows=[
                    (
                        _gallery_summary_model_link(row.model),
                        _markdown_inline_code(_human_status_label(row.usability)),
                        MARKDOWN_ESCAPER.escape(_gallery_observation_labels(row.observations)),
                    )
                    for row in data.avoided
                ],
            )
        )
    else:
        parts.append("No unusable or not-evaluated models in this run.")
    parts.append("")
    return parts


def _render_gallery_output_glance(rows: Sequence[GalleryRow]) -> list[str]:
    """Render every model's actual output preview as one skimmable table.

    The chooser carries mechanical judgements; this table answers the other
    first question — what did each model actually say — without expanding the
    per-model evidence blocks.
    """
    ordered = _gallery_chooser_data(rows).ordered
    if not ordered:
        return []
    return [
        "## Output at a Glance",
        "",
        (
            "A compact preview of each model's final answer (or failure evidence "
            "for crashes), in chooser order. Where the requested catalogue fields "
            "were detected, the preview shows a little of each: the title, the "
            "start of the description, and the first keywords with their count, "
            "so the weakest field is not hidden behind a long description. "
            f"Otherwise it is the first {MAX_OUTPUT_PREVIEW_CHARS} characters. A "
            "closed reasoning trace is left out of the preview and reported as an "
            "omitted-character count; the complete output, trace included, is in "
            "the model's evidence block below."
        ),
        "",
        *_render_gallery_table(
            headers=("Model", "Mechanical checks", "Output preview"),
            rows=[
                (
                    _gallery_summary_model_link(row.model),
                    _markdown_inline_code(_human_status_label(row.usability)),
                    _gallery_preview_cell_markdown(row),
                )
                for row in ordered
            ],
        ),
        "",
    ]


# =============================================================================
# SECTION: DIAGNOSTICS/REPORT CONTEXT BUILDERS
# =============================================================================


_TRACEBACK_TAIL_LINES: Final[int] = 6
# System info keys to include in the environment table (order matters)
_DIAGNOSTICS_SYSTEM_KEYS: Final[tuple[str, ...]] = (
    "Python Version",
    "OS",
    "macOS Version",
    "SDK Version",
    "SDK Path",
    "Xcode Version",
    "Xcode Build",
    "Active Developer Directory",
    "Metal SDK",
    "Metal Compiler Version",
    "Metallib Linker Version",
    "Apple Clang Version",
    "GPU/Chip",
    "GPU Cores",
    "MLX Device",
    "GPU Architecture",
    "Recommended Working Set",
    "Fused Attention",
    "Metal Support",
    "MLX Install Type",
    "MLX Distribution Root",
    "mlx-metal Distribution Root",
    "mlx-metal Distribution",
    "MLX Core Extension",
    "MLX Metallib",
    "MLX libmlx.dylib",
    "RAM",
)

# Library names to include in the environment table (order matters)
# NOTE: deliberately similar to _ISSUE_RELEVANT_LIB_NAMES below but not derivable
# from it: diagnostics adds mlx-audio (runtime probe surface) while issue drafts
# add Pillow (image decode provenance). Keep both lists explicit.
_DIAGNOSTICS_LIB_NAMES: Final[tuple[str, ...]] = (
    "mlx-vlm",
    "mlx",
    "mlx-metal",
    "mlx-audio",
    "transformers",
    "tokenizers",
    "huggingface-hub",
)

_ISSUE_RELEVANT_LIB_NAMES: Final[tuple[str, ...]] = (
    "mlx-vlm",
    "mlx",
    "mlx-metal",
    "transformers",
    "tokenizers",
    "huggingface-hub",
    "Pillow",
)
_ISSUE_RELEVANT_SYSTEM_KEYS: Final[tuple[str, ...]] = (
    "Python Version",
    "macOS Version",
    "GPU/Chip",
)


@dataclass(frozen=True)
class ResultAssessment:
    """Minimal current-run assessment shared by all report consumers."""

    execution: ExecutionStatus
    usability: ModelUsability
    maintainer_status: MaintainerStatus
    observations: tuple[ObservationCode, ...]


@dataclass(frozen=True)
class GalleryRow:
    """One facts-only chooser row derived from cached assessment and run metrics."""

    model: str
    usability: ModelUsability
    observations: tuple[ObservationCode, ...]
    total_time_s: float | None
    generation_tps: float | None
    first_token_latency_s: float | None
    peak_memory_gb: float | None
    prompt_tokens: int | None
    generation_tokens: int | None
    output_preview: str
    reasoning_chars: int = 0
    reasoning_preview: str = ""


def _execution_status(result: PerformanceResult) -> ExecutionStatus:
    """Classify the conclusive execution state for one model attempt.

    Connectivity failures and download-phase timeouts are *indeterminate*:
    the environment prevented a conclusive attempt, so they are neither a
    completion nor a crash attributable to the model or mlx-vlm.
    """
    if (
        _is_indeterminate_connectivity_failure(result)
        or _is_download_timeout_failure(result)
        or _is_incomplete_cache_failure(result)
    ):
        return "indeterminate"
    return "completed" if result.success else "crashed"


def _quality_observations(
    *,
    text: str,
    analysis: GenerationQualityAnalysis | None,
    stop_reason: str | None = None,
) -> tuple[ObservationCode, ...]:
    """Project text facts into stable ordered observation codes.

    Pure canonical projection shared by completed-result assessment and the
    standalone ``tools.analyze_output_quality`` tool, so no surface can carry
    a second, drifting verdict.
    """
    observations: list[ObservationCode] = []
    if not text.strip():
        observations.append("empty_output")
    is_repetitive = (
        analysis.is_repetitive if analysis is not None else _detect_repetitive_output(text)[0]
    )
    if is_repetitive:
        observations.append("repeated_output")
    if stop_reason == "repetition_abort":
        observations.append("repetition_abort")
    if analysis is None:
        return tuple(observations)
    if analysis.duplicated_answer_separator is not None:
        observations.append("final_answer_duplicated")

    non_thinking_wrappers = set(analysis.configured_generation_wrappers).difference(
        analysis.thinking_trace_markers
    )
    candidates: tuple[tuple[bool, ObservationCode], ...] = (
        (bool(analysis.missing_sections), "missing_requested_sections"),
        (
            analysis.likely_capped and bool(analysis.token_cap_reasons),
            "token_cap_truncation",
        ),
        (bool(analysis.unexpected_special_tokens), "unexpected_special_token"),
        (bool(non_thinking_wrappers), "configured_wrapper_present"),
        (analysis.thinking_only_output, "missing_final_answer"),
        (analysis.thinking_trace_incomplete, "thinking_trace_incomplete"),
        (bool(analysis.role_boundary_tokens), "role_boundary_token_present"),
        (bool(analysis.duplicate_keywords), "duplicate_keywords"),
    )
    observations.extend(code for condition, code in candidates if condition)
    return tuple(observations)


def _completed_assessment(observations: Sequence[ObservationCode]) -> ResultAssessment:
    """Derive the completed-result assessment from canonical observations."""
    ordered = tuple(observations)
    usability: ModelUsability = (
        "unusable"
        if set(ordered) & _UNUSABLE_OBSERVATIONS
        else "usable_with_caveats"
        if ordered
        else "usable"
    )
    maintainer_status: MaintainerStatus = (
        "observation_needs_reproduction"
        if set(ordered) & _INTEGRATION_SIGNAL_OBSERVATIONS
        else "none"
    )
    return ResultAssessment("completed", usability, maintainer_status, ordered)


def _assessment_observations(result: PerformanceResult) -> tuple[ObservationCode, ...]:
    """Thin result adapter over the canonical observation projection."""
    runtime = result.runtime_diagnostics
    return _quality_observations(
        text=_generation_text_value(result.generation),
        analysis=result.quality_analysis,
        stop_reason=runtime.stop_reason if runtime is not None else None,
    )


def _assess_result(result: PerformanceResult) -> ResultAssessment:
    """Return the minimal current-run outcome without legacy presentation policy."""
    execution = _execution_status(result)
    if execution == "completed":
        return _completed_assessment(_assessment_observations(result))
    maintainer_status: MaintainerStatus = "actionable_failure" if execution == "crashed" else "none"
    return ResultAssessment(execution, "not_evaluated", maintainer_status, ())


def _catalog_constraint_observation_details(
    analysis: GenerationQualityAnalysis,
) -> JsonlObservationDetailsRecord:
    """Return present catalogue-count evidence without adding empty fields."""
    details: JsonlObservationDetailsRecord = {}
    if analysis.title_word_count is not None:
        details["title_word_count"] = analysis.title_word_count
    if analysis.keyword_count is not None:
        details["keyword_count"] = analysis.keyword_count
    if analysis.duplicate_keywords:
        details["duplicate_keywords"] = list(analysis.duplicate_keywords)
    return details


def _observation_details(result: PerformanceResult) -> JsonlObservationDetailsRecord:
    """Return non-empty exact evidence for the result's mechanical observations."""
    analysis = result.quality_analysis
    if analysis is None:
        return {}
    details: JsonlObservationDetailsRecord = {}
    if analysis.missing_sections:
        details["missing_sections"] = list(analysis.missing_sections)
    if analysis.repeated_token:
        details["repeated_fragment"] = analysis.repeated_token
    if analysis.unexpected_special_tokens:
        details["unexpected_special_tokens"] = list(analysis.unexpected_special_tokens)
    if analysis.configured_generation_wrappers:
        details["configured_generation_wrappers"] = list(analysis.configured_generation_wrappers)
    if analysis.thinking_trace_markers:
        details["thinking_trace_markers"] = list(analysis.thinking_trace_markers)
    if analysis.role_boundary_tokens:
        details["role_boundary_tokens"] = list(analysis.role_boundary_tokens)
    details.update(_catalog_constraint_observation_details(analysis))
    if analysis.token_cap_reasons:
        details["token_cap_reasons"] = list(analysis.token_cap_reasons)
    if analysis.duplicated_answer_separator is not None:
        details["duplicated_answer_separator"] = analysis.duplicated_answer_separator
    return details


def _assessment_to_json(
    assessment: ResultAssessment,
    result: PerformanceResult | None = None,
) -> JsonlAssessmentRecord:
    """Serialize the sole current-run status record for machine artifacts."""
    record: JsonlAssessmentRecord = {
        "execution": assessment.execution,
        "usability": assessment.usability,
        "maintainer_status": assessment.maintainer_status,
        "observations": list(assessment.observations),
        "profile": result.assessment_profile if result is not None else "general",
    }
    if result is not None and (details := _observation_details(result)):
        record["details"] = details
    return record


@dataclass(frozen=True)
class ReportModePolicy:
    """Factual run-mode fields shared by retained machine artifacts."""

    eval_mode: EvaluationLane
    metadata_exposed_to_prompt: bool
    assessment_profile: AssessmentProfile = "general"


def _default_report_mode_policy() -> ReportModePolicy:
    """Return a conservative policy for contexts built without run metadata."""
    return _build_report_mode_policy(eval_mode=DEFAULT_EVAL_MODE, metadata=None)


@dataclass(frozen=True)
class ReportRenderContext:
    """Shared cached context for retained current-run report generation."""

    result_set: ResultSet
    system_info: dict[str, str]
    recommended_working_set_bytes: int | None = None
    image_profile: ImageInputProfile | None = None
    preflight_issues: tuple[str, ...] = ()
    mode_policy: ReportModePolicy = dataclass_field(default_factory=_default_report_mode_policy)
    assessments: tuple[tuple[str, ResultAssessment], ...] = ()
    model_provenance: tuple[tuple[str, ModelProvenanceRecord], ...] = ()


@dataclass(frozen=True)
class CanonicalHtmlReportContext:
    """Minimal cached facts required by the standalone HTML report."""

    result_set: ResultSet
    system_info: dict[str, str]
    assessments: tuple[tuple[str, ResultAssessment], ...]
    model_provenance: tuple[tuple[str, ModelProvenanceRecord], ...] = ()


type HtmlReportContext = ReportRenderContext | CanonicalHtmlReportContext


def _build_html_report_context(
    *,
    results: Sequence[PerformanceResult],
    prompt: str,
    system_info: dict[str, str] | None = None,
) -> CanonicalHtmlReportContext:
    """Build only the canonical gallery and diagnostics facts consumed by HTML."""
    analyzed_results = [
        _populate_result_quality_analysis(
            result,
            prompt=prompt,
        )
        for result in results
    ]
    return CanonicalHtmlReportContext(
        result_set=ResultSet(analyzed_results),
        system_info=system_info if system_info is not None else get_system_characteristics(),
        assessments=tuple(
            (result.model_name, _assess_result(result)) for result in analyzed_results
        ),
    )


def _append_markdown_code_block(
    parts: list[str],
    content: str,
    *,
    language: str = "text",
) -> None:
    """Append a fenced code block with consistent spacing.

    Uses a fence longer than any backtick run in ``content`` so nested
    Markdown/code fences remain valid when embedded.
    """
    normalized_content = content
    max_backtick_run = max(
        (len(m.group(0)) for m in re.finditer(r"`+", normalized_content)),
        default=0,
    )
    fence = "`" * max(3, max_backtick_run + 1)
    if not parts or parts[-1] != "":
        parts.append("")
    parts.append(f"{fence}{language}")
    parts.append(normalized_content)
    parts.append(fence)
    if not parts or parts[-1] != "":
        parts.append("")


def _is_markdown_blockquote_label_line(text: str) -> bool:
    """Return whether escaped blockquote text is just a short label line."""
    emphasis_wrapper = "&#42;&#42;"
    normalized = text
    if normalized.startswith(emphasis_wrapper) and normalized.endswith(emphasis_wrapper):
        normalized = normalized[len(emphasis_wrapper) : -len(emphasis_wrapper)]
    return re.fullmatch(r"[A-Za-z][A-Za-z0-9 \"'()/,&.-]{0,80}:", normalized) is not None


def _neutralize_markdown_blockquote_prefix(text: str) -> str:
    """Render leading Markdown control syntax as plain text in blockquotes."""
    replacement = text
    if text.startswith("[!"):
        replacement = f"&#91;{text[1:]}"
    else:
        setext_match = re.fullmatch(r"([=-])\1{2,}\s*", text)
        if setext_match is not None:
            underline_entity = "&#61;" if setext_match.group(1) == "=" else "&#45;"
            replacement = f"{underline_entity}{text[1:]}"
        else:
            bullet_entities: dict[str, str] = {
                "*": "&#42;",
                "+": "&#43;",
                "-": "&#45;",
            }
            lone_bullet_match = re.fullmatch(r"([*+-])", text)
            if lone_bullet_match is not None:
                replacement = bullet_entities[lone_bullet_match.group(1)]
            else:
                ordered_match = re.match(r"^(\d+)([.)])(?:(\s)|$)", text)
                if ordered_match is not None:
                    punctuation_entity = "&#46;" if ordered_match.group(2) == "." else "&#41;"
                    marker_spacing = ordered_match.group(3) or ""
                    replacement = (
                        f"{ordered_match.group(1)}{punctuation_entity}{marker_spacing}"
                        f"{text[ordered_match.end() :]}"
                    )
                else:
                    bullet_match = re.match(r"^([*+-])(\s)", text)
                    if bullet_match is not None:
                        replacement = (
                            f"{bullet_entities[bullet_match.group(1)]}{bullet_match.group(2)}"
                            f"{text[bullet_match.end() :]}"
                        )
                    else:
                        prefix_entities: dict[str, str] = {
                            "#": "&#35;",
                            ">": "&gt;",
                            "`": "&#96;",
                        }
                        leading_char = text[:1]
                        if leading_char in prefix_entities:
                            replacement = f"{prefix_entities[leading_char]}{text[1:]}"
                        elif _is_markdown_blockquote_label_line(text):
                            replacement = f"&#8203;{text}"

    return replacement


def _escape_markdown_blockquote_line(text: str) -> str:
    """Escape structural Markdown syntax for wrapped blockquote text."""
    escaped: str = _escape_markdown_underscore_runs(HTML_ESCAPER.escape(_wrap_bare_urls(text)))
    escaped = escaped.replace("*", "&#42;")
    escaped = HTML_UNESCAPED_AMPERSAND_RE.sub("&amp;", escaped)
    return _neutralize_markdown_blockquote_prefix(escaped)


def _append_markdown_wrapped_blockquote(
    parts: list[str],
    content: str,
    *,
    width: int = FORMATTING.markdown_wrap_width - 2,
) -> None:
    """Append a wrapping plain blockquote for human-facing text blocks.

    This path is for prompt/model-output readability. Technical logs and
    reproducibility commands should continue to use fenced code blocks.
    """
    if not parts or parts[-1] != "":
        parts.append("")
    parts.append("<!-- markdownlint-disable MD011 MD028 MD037 MD045 -->")
    blockquote_lines: list[str] = [">"]

    normalized: str = content.replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized.split("\n"):
        if raw_line == "":
            blockquote_lines.append(">")
            continue
        wrapped_lines: list[str] = textwrap.wrap(
            raw_line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
            drop_whitespace=False,
        )
        if not wrapped_lines:
            blockquote_lines.append(">")
            continue
        for wrapped_line in wrapped_lines:
            clean_line = wrapped_line.lstrip().rstrip(" \t\u00a0\u200b\u200c\u200d\u2060\ufeff")
            blockquote_lines.append(
                ">" if clean_line == "" else f"> {_escape_markdown_blockquote_line(clean_line)}"
            )

    parts.extend(blockquote_lines)
    parts.append("<!-- markdownlint-enable MD011 MD028 MD037 MD045 -->")
    if not parts or parts[-1] != "":
        parts.append("")


def _append_markdown_image_metadata_section(
    parts: list[str],
    metadata: MetadataDict | None,
) -> None:
    """Append selected image metadata fields for Markdown gallery output."""
    if not metadata:
        return

    metadata_fields: tuple[tuple[str, str | None], ...] = (
        ("Title", metadata.get("title")),
        ("Description", metadata.get("description")),
        ("Keywords", metadata.get("keywords")),
        ("Date", metadata.get("date")),
        ("Time", metadata.get("time")),
        ("GPS", metadata.get("gps")),
    )
    populated_fields: list[tuple[str, str]] = [
        (label, value) for label, value in metadata_fields if value is not None
    ]
    if not populated_fields:
        return

    parts.append("## Image Metadata")
    parts.append("")
    for label, value in populated_fields:
        normalized_value = value.replace("\r\n", "\n").replace("\r", "\n")
        paragraphs = [
            paragraph.strip() for paragraph in normalized_value.split("\n\n") if paragraph.strip()
        ]
        if not paragraphs:
            continue

        first_paragraph_lines = [
            line.strip() for line in paragraphs[0].splitlines() if line.strip()
        ]
        first_line = first_paragraph_lines[0] if first_paragraph_lines else ""
        _append_markdown_labeled_value(parts, label=label, value=first_line, bullet=True)

        remaining_lines = first_paragraph_lines[1:]
        if remaining_lines:
            parts.append("")
            parts.extend(f"    {line}" for line in remaining_lines)

        for paragraph in paragraphs[1:]:
            paragraph_lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            if not paragraph_lines:
                continue
            parts.append("")
            parts.extend(f"    {line}" for line in paragraph_lines)
    parts.append("")


def _write_markdown_artifact(
    filename: Path,
    markdown_lines: Sequence[str],
) -> None:
    """Normalize and write Markdown artifact content."""
    markdown_content: str = normalize_markdown_trailing_spaces("\n".join(markdown_lines)) + "\n"
    _write_text_file(filename, markdown_content)


def _append_markdown_section(
    parts: list[str],
    *,
    title: str,
    body_lines: list[str] | None = None,
) -> None:
    """Append a Markdown section heading with optional body lines."""
    title_match = re.fullmatch(r"(#{1,6})\s+(.+)", title)
    if title_match is not None:
        heading_level = len(title_match.group(1))
        heading_title = title_match.group(2)
    else:
        heading_level = 2
        heading_title = title

    rendered_body: list[str] = []
    if body_lines:
        for body_line in body_lines:
            if body_line == "":
                rendered_body.append("")
                continue
            if body_line.startswith(("- ", "* ", "|", "<", "#", "```")):
                rendered_body.append(body_line)
                continue
            if re.match(r"\d+\. ", body_line):
                rendered_body.append(body_line)
                continue
            rendered_body.extend(_wrap_markdown_text(body_line))
        rendered_body.append("")

    blocks: tuple[ReportBlock, ...] = (
        (ReportRaw(markdown_lines=tuple(rendered_body)),) if rendered_body else ()
    )
    parts.extend(
        render_report_markdown(
            (ReportSection(title=heading_title, level=heading_level, blocks=blocks),)
        )
    )
    parts.append("")


def _append_markdown_details_block(
    parts: list[str],
    *,
    summary: str,
    body_lines: Sequence[str],
) -> None:
    """Append an HTML <details> block for collapsed technical content."""
    normalized_body_lines = list(body_lines)
    while normalized_body_lines and normalized_body_lines[0] == "":
        normalized_body_lines.pop(0)
    while normalized_body_lines and normalized_body_lines[-1] == "":
        normalized_body_lines.pop()

    parts.append("<details>")
    parts.append(f"<summary>{html.escape(summary, quote=False)}</summary>")
    parts.append("")
    parts.extend(normalized_body_lines)
    if normalized_body_lines:
        parts.append("")
    parts.append("</details>")
    parts.append("")


_LOCAL_RUNNER_TRACEBACK_FRAME_RE: Final[re.Pattern[str]] = re.compile(
    r'^\s*File ".*(?:^|/)check_models\.py", line \d+, in ',
)
_TRACEBACK_CHAIN_SEPARATOR_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:The above exception was the direct cause of the following exception:"
    r"|During handling of the above exception, another exception occurred:)$",
)
_TRACEBACK_FILE_FRAME_RE: Final[re.Pattern[str]] = re.compile(r'^\s*File "')


def _normalize_traceback_for_report(traceback_str: str | None) -> str | None:
    """Normalize traceback text for diagnostics output."""
    if not traceback_str:
        return None

    lines = traceback_str.splitlines()
    kept: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _LOCAL_RUNNER_TRACEBACK_FRAME_RE.search(line):
            idx += 1
            while idx < len(lines):
                follow = lines[idx]
                if follow.lstrip().startswith('File "') or not follow.startswith(" "):
                    break
                idx += 1
            continue
        kept.append(line)
        idx += 1

    sanitized = _home_relative_report_text("\n".join(kept).strip())
    return sanitized or None


def _format_traceback_tail(traceback_str: str | None) -> str | None:
    """Extract the last meaningful lines from a full traceback.

    Strips blank lines and returns the tail suitable for inclusion in issue
    reports.  Returns None when no useful info can be extracted.
    """
    normalized = _normalize_traceback_for_report(traceback_str)
    if normalized is None:
        return None

    segments: list[list[str]] = []
    current_segment: list[str] = []
    for line in normalized.splitlines():
        if _TRACEBACK_CHAIN_SEPARATOR_RE.match(line.strip()):
            if current_segment:
                segments.append(current_segment)
            current_segment = []
            continue
        current_segment.append(line)
    if current_segment:
        segments.append(current_segment)

    nonblank_segments = [
        [ln for ln in segment if ln.strip()]
        for segment in segments
        if any(ln.strip() for ln in segment)
    ]
    upstream_segments = [
        segment
        for segment in nonblank_segments
        if any(_TRACEBACK_FILE_FRAME_RE.match(ln) for ln in segment)
    ]
    lines = (
        upstream_segments[0]
        if upstream_segments
        else [ln for ln in normalized.splitlines() if ln.strip()]
    )
    if not lines:
        return None
    tail = lines[-_TRACEBACK_TAIL_LINES:]
    return "\n".join(tail)


def _log_maintainer_summary(
    *,
    artifacts: DiagnosticsArtifacts,
    diagnostics_path: Path,
) -> None:
    """Emit factual cached outcome counts and direct diagnostics artifact paths."""
    log_blank()
    print_cli_section("Maintainer Summary")

    counts = artifacts.outcome_counts
    if counts is not None:
        logger.info(
            "Run outcomes: attempted=%d, evaluated=%d, completed=%d, crashed=%d, indeterminate=%d",
            counts["models_attempted"],
            counts["models_evaluated"],
            counts["models_completed"],
            counts["models_crashed"],
            counts["models_indeterminate"],
        )
    else:
        logger.info("Run outcome counts unavailable.")

    if artifacts.diagnostics_written:
        log_file_path(diagnostics_path, label="   Diagnostics:  ")
    for model_name, issue_path in sorted(artifacts.issue_reports.items()):
        log_file_path(issue_path, label=f"   Crash Draft ({model_name}):")


def _diagnostics_environment_section(
    *,
    versions: LibraryVersionDict,
    system_info: dict[str, str],
) -> list[str]:
    """Build environment details section for diagnostics report footer context."""
    table_rows = [
        (component, DIAGNOSTICS_ESCAPER.escape(value))
        for component, value in _collect_report_component_rows(
            versions=versions,
            system_info=system_info,
            library_names=_DIAGNOSTICS_LIB_NAMES,
            system_keys=_DIAGNOSTICS_SYSTEM_KEYS,
        )
    ]
    for component, provenance in _collect_component_provenance(versions).items():
        if component not in _DIAGNOSTICS_LIB_NAMES and component != "check_models":
            continue
        details: list[str] = [provenance["install_type"]]
        if provenance["source_revision"]:
            details.append(f"revision {provenance['source_revision'][:12]}")
        if provenance["source_location"]:
            details.append(provenance["source_location"])
        table_rows.append(
            (
                f"{component} provenance",
                DIAGNOSTICS_ESCAPER.escape("; ".join(details)),
            )
        )
    parts = _guard_markdownlint_block(
        render_report_markdown(
            (
                ReportSection(
                    title="Environment",
                    level=2,
                    divider=True,
                    blocks=(
                        ReportTable(
                            headers=("Component", "Version"),
                            rows=tuple(table_rows),
                            markdown_escaped=True,
                        ),
                    ),
                ),
            )
        ),
        rules=MARKDOWNLINT_TABLE_PIPE_RULES,
    )
    parts.append("")
    return parts


def _build_environment_failure_diagnostics(
    *,
    error_message: str,
    versions: LibraryVersionDict,
    system_info: dict[str, str],
) -> list[str]:
    """Build diagnostics content for environment preflight failures (no models run)."""
    parts: list[str] = [
        "# Diagnostics Report — environment preflight failure",
        "",
    ]
    _append_markdown_section(
        parts,
        title="## Summary",
        body_lines=[
            (
                "Run aborted before any model execution because core runtime "
                "dependencies were unavailable."
            ),
            f"**Error:** {DIAGNOSTICS_ESCAPER.escape(_home_relative_report_text(error_message))}",
        ],
    )
    parts.extend(
        _diagnostics_environment_section(
            versions=versions,
            system_info=system_info,
        ),
    )
    return parts


def _dedupe_preserve_order(items: Sequence[str]) -> list[str]:
    """Return unique items while preserving first-seen order."""
    unique_items: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


@dataclass(frozen=True)
class ReproCommandSpec:
    """Canonical tokenized native reproduction command used by reports."""

    base_tokens: tuple[str, ...]
    argument_tokens: tuple[str, ...] = ()

    def tokens(self) -> tuple[str, ...]:
        """Return the full command token sequence."""
        return (*self.base_tokens, *self.argument_tokens)

    def shell_command(self) -> str:
        """Return a shell-quoted command string for Markdown/code output."""
        return shlex_join(self.tokens())


def _jsonify_cli_value(value: object) -> object:
    """Convert argparse values into JSON-safe primitives."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonify_cli_value(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify_cli_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _jsonify_cli_value(v) for k, v in value.items()}
    return str(value)


def _sha256_text(value: str) -> str:
    """Return SHA256 hash of UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_FILE_DIGEST_CACHE: dict[tuple[str, int, int], str] = {}
_IMAGE_PREVIEW_CACHE: dict[tuple[str, int, int], tuple[str, str, bytes]] = {}


def _file_identity(path: Path) -> tuple[str, int, int] | None:
    """Return (resolved path, size, mtime_ns) — the cache key for per-file derived facts."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def _sha256_file(path: Path) -> str | None:
    """Return SHA256 hash for file contents, or None if unreadable.

    Cached per (path, size, mtime): the run hashes the same 66 MB input for
    the metadata header, every report, the comparison and the history row.
    """
    if not path.exists() or not path.is_file():
        return None
    identity = _file_identity(path)
    if identity is not None and (cached := _FILE_DIGEST_CACHE.get(identity)) is not None:
        return cached
    try:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return None
    if identity is not None:
        _FILE_DIGEST_CACHE[identity] = digest
    return digest


@dataclass(frozen=True)
class DiagnosticsPartitions:
    """Direct cached-assessment partitions for maintainer presentation."""

    actionable: tuple[PerformanceResult, ...]
    observations: tuple[PerformanceResult, ...]
    indeterminate: tuple[PerformanceResult, ...]
    # Completed with compliance-only observations: chooser-relevant context,
    # deliberately outside the maintainer lane.
    compliance: tuple[PerformanceResult, ...]
    clean: tuple[PerformanceResult, ...]


def _partition_diagnostics(context: HtmlReportContext) -> DiagnosticsPartitions:
    """Partition maintainer evidence using only cached current-run assessments."""
    assessments = dict(context.assessments)

    def sort_key(result: PerformanceResult) -> tuple[int, int, str]:
        assessment = assessments[result.model_name]
        return _assessment_actionability_key(
            result.model_name,
            assessment.usability,
            assessment.observations,
        )

    actionable = tuple(
        sorted(
            (
                result
                for result in context.result_set.results
                if assessments[result.model_name].maintainer_status == "actionable_failure"
            ),
            key=sort_key,
        )
    )
    observations = tuple(
        sorted(
            (
                result
                for result in context.result_set.results
                if assessments[result.model_name].maintainer_status
                == "observation_needs_reproduction"
            ),
            key=sort_key,
        )
    )
    indeterminate = tuple(
        sorted(
            (
                result
                for result in context.result_set.results
                if assessments[result.model_name].execution == "indeterminate"
            ),
            key=sort_key,
        )
    )
    compliance = tuple(
        sorted(
            (
                result
                for result in context.result_set.results
                if assessments[result.model_name].execution == "completed"
                and assessments[result.model_name].maintainer_status == "none"
                and assessments[result.model_name].observations
            ),
            key=sort_key,
        )
    )
    clean = tuple(
        sorted(
            (
                result
                for result in context.result_set.results
                if assessments[result.model_name].execution == "completed"
                and not assessments[result.model_name].observations
            ),
            key=sort_key,
        )
    )
    return DiagnosticsPartitions(actionable, observations, indeterminate, compliance, clean)


def _diagnostics_fact(value: object | None) -> str:
    """Render one optional factual value without adding interpretation."""
    if value is None or value == "":
        return "unavailable"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return _home_relative_report_text(value)
    if isinstance(value, int | float):
        return str(value)
    return _home_relative_report_text(json.dumps(_jsonify_cli_value(value), sort_keys=True))


def _diagnostics_exception_lines(result: PerformanceResult) -> tuple[str, ...]:
    """Return the recorded exception chain, compacting large parameter lists."""
    if result.exception_chain:
        return tuple(
            _home_relative_report_text(
                f"{item.module}.{item.exception_type}: "
                f"{_compact_run_issue_exception_message(item.message)}"
            )
            for item in result.exception_chain
        )
    exception_type = result.root_error_type or result.error_type
    module = result.root_error_module
    message = result.root_error_message or result.error_message
    if exception_type is None and message is None:
        return ("unavailable",)
    qualified_type = (
        f"{module}.{exception_type}"
        if module is not None and exception_type is not None
        else exception_type or module or "Exception"
    )
    compacted = _compact_run_issue_exception_message(message or "unavailable")
    return (_home_relative_report_text(f"{qualified_type}: {compacted}"),)


def _diagnostics_result_facts(
    result: PerformanceResult,
    assessment: ResultAssessment,
    *,
    run_args: argparse.Namespace | None,
    model_provenance: ModelProvenanceRecord | None,
) -> tuple[tuple[str, str], ...]:
    """Return exact per-model runtime and provenance fields for maintainers."""
    prompt_diagnostics = result.prompt_diagnostics
    runtime = result.runtime_diagnostics
    generation_kwargs = prompt_diagnostics.generate_kwargs if prompt_diagnostics is not None else {}
    resolved_revision = (
        model_provenance["resolved_revision"] if model_provenance is not None else None
    )
    requested_revision = (
        model_provenance["requested_revision"] if model_provenance is not None else None
    ) or getattr(run_args, "revision", None)
    processor = prompt_diagnostics.processor_class if prompt_diagnostics is not None else None
    tokenizer = prompt_diagnostics.tokenizer_class if prompt_diagnostics is not None else None
    rows: list[tuple[str, str]] = [
        ("Execution", assessment.execution),
        ("Mechanical checks", _human_status_label(assessment.usability)),
        ("Assessment", _assessment_scope(result.assessment_profile)),
        ("Maintainer status", assessment.maintainer_status),
        ("Observations", ", ".join(assessment.observations) or "none"),
    ]
    arch_summary = _arch_precheck_summary(result.model_name)
    if arch_summary is not None:
        rows.append(("Arch supported by installed mlx-vlm", arch_summary))
    detail_labels = {
        "missing_sections": "Labelled fields not detected",
        "repeated_fragment": "Repeated fragment",
        "instruction_echo_fragments": "Echoed instruction fragments",
        "unexpected_catalog_preamble": "Unexpected text before Title",
        "unexpected_special_tokens": "Unexpected special tokens",
        "configured_generation_wrappers": "Declared generation wrappers in output",
        "thinking_trace_markers": "Thinking trace markers",
        "role_boundary_tokens": "Role-boundary tokens in output",
        "title_word_count": "Title word count",
        "title_word_range": "Requested title word range",
        "description_sentence_count": "Description sentence count",
        "description_sentence_range": "Requested description sentence range",
        "keyword_count": "Keyword count",
        "keyword_count_range": "Requested keyword count range",
        "duplicate_keywords": "Duplicate keywords",
        "token_cap_reasons": "Token-cap degradation evidence",
        "unchanged_draft_fields": "Draft fields returned unchanged",
        "duplicated_answer_separator": "Text between the two answer copies",
    }
    rows.extend(
        (detail_labels.get(key, key.replace("_", " ").capitalize()), _diagnostics_fact(value))
        for key, value in _observation_details(result).items()
    )
    optional_facts = (
        ("Phase", result.failure_phase),
        ("Stage", result.error_stage),
        ("Package", result.error_package),
        ("Error type", result.error_type),
        (
            "Error message",
            (
                _compact_run_issue_exception_message(result.error_message)
                if result.error_message is not None
                else None
            ),
        ),
        ("Root error type", result.root_error_type),
        (
            "Root error message",
            (
                _compact_run_issue_exception_message(result.root_error_message)
                if result.root_error_message is not None
                else None
            ),
        ),
        ("Resolved model revision", resolved_revision),
        ("Requested model revision", requested_revision),
        ("Processor class", processor),
        ("Tokenizer class", tokenizer),
        ("Stop reason", runtime.stop_reason if runtime is not None else None),
        (
            "Post-cleanup active memory (GB)",
            runtime.post_cleanup_active_memory_gb if runtime is not None else None,
        ),
        (
            "Post-cleanup cache memory (GB)",
            runtime.post_cleanup_cache_memory_gb if runtime is not None else None,
        ),
        ("Prompt tokens", _generation_int_metric(result.generation, "prompt_tokens")),
        ("Prompt composition", _prompt_composition_fact(result)),
        *_model_burden_rows(result),
        ("Generation tokens", _generation_int_metric(result.generation, "generation_tokens")),
        (
            "Configured EOS token ID",
            prompt_diagnostics.eos_token_id if prompt_diagnostics else None,
        ),
        ("Configured EOS token", prompt_diagnostics.eos_token if prompt_diagnostics else None),
        ("Configured EOS token override", generation_kwargs.get("eos_tokens")),
        ("Configured thinking start token", generation_kwargs.get("thinking_start_token")),
        ("Configured thinking end token", generation_kwargs.get("thinking_end_token")),
        ("Configured thinking budget", generation_kwargs.get("thinking_budget")),
    )
    rows.extend(
        (label, _diagnostics_fact(value)) for label, value in optional_facts if value is not None
    )
    if assessment.execution == "indeterminate":
        rows.append(("Indeterminate root cause", _indeterminate_reason(result)))
    if prompt_diagnostics is not None and prompt_diagnostics.snapshot_notes:
        rows.append(("Snapshot notes (neutral)", "; ".join(prompt_diagnostics.snapshot_notes)))
    telemetry = result.system_telemetry
    if telemetry is not None:
        label = (
            "System pressure snapshots (before/after; cannot rule out transient "
            "pressure during inference)"
            if telemetry.get("mode") == "snapshot"
            else "System pressure during run"
        )
        rows.append((label, _telemetry_status_line(telemetry)))
    return tuple(rows)


_UPSTREAM_MEMORY_ESTIMATE_RE: Final[re.Pattern[str]] = re.compile(
    r"requires\s+[\d,.]+\s*[GM]B\b[^.\n]*", re.IGNORECASE
)
_OOM_CAPACITY_NOTE: Final[str] = (
    "An out-of-memory failure records that this checkpoint, image and prompt "
    "needed more memory than this machine could commit during generation. That "
    "is a resource-capacity outcome, not by itself evidence of a defect in "
    "mlx-vlm or in the model. Checkpoint size alone does not predict peak "
    "memory reliably enough to skip models automatically, so these facts are "
    "informational."
)


def _is_oom_failure(result: PerformanceResult) -> bool:
    """Return whether a crash is a memory-capacity failure (stage or message evidence)."""
    if result.success:
        return False
    if result.error_stage == "OOM":
        return True
    haystack = " ".join(
        text for text in (result.error_message, result.root_error_message) if text
    ).casefold()
    return any(needle in haystack for needle in _OOM_MESSAGE_NEEDLES)


def _oom_capacity_rows(
    result: PerformanceResult,
    *,
    system_info: Mapping[str, str] | None,
    image_profile: ImageInputProfile | None,
) -> tuple[tuple[str, str], ...]:
    """Bring the already-recorded capacity facts for an OOM crash together."""
    rows: list[tuple[str, str]] = []
    burden = result.model_burden
    if burden is not None and burden.weight_bytes:
        weight = f"{burden.weight_bytes / 1e9:.1f} GB"
        if burden.quantization_bits is not None:
            weight += f", {burden.quantization_bits}-bit"
        rows.append(("Checkpoint weights on disk", weight))
    for label, key in (
        ("Machine RAM", "RAM"),
        ("Recommended working set", "Recommended Working Set"),
    ):
        value = system_info.get(key) if system_info is not None else None
        if value:
            rows.append((label, value))
    if image_profile is not None:
        rows.append(
            (
                "Input image",
                (
                    f"{image_profile.width} x {image_profile.height} pixels "
                    f"({image_profile.megapixels:.1f} MP)"
                ),
            )
        )
    prompt_tokens = _generation_int_metric(result.generation, "prompt_tokens")
    diagnostics = result.prompt_diagnostics
    if prompt_tokens is not None:
        rows.append(("Prompt tokens", f"{prompt_tokens} (measured)"))
    elif diagnostics is not None and diagnostics.rendered_prompt_token_count is not None:
        rows.append(
            (
                "Prompt tokens",
                (
                    f"{diagnostics.rendered_prompt_token_count} text tokens in the rendered "
                    "template; image tokens not counted (generation reported no prompt total)"
                ),
            )
        )
    else:
        rows.append(("Prompt tokens", "not captured"))
    captured = result.captured_output_on_fail or ""
    if (match := _UPSTREAM_MEMORY_ESTIMATE_RE.search(captured)) is not None:
        rows.append(
            ("Upstream memory estimate", f"model {match.group(0).strip()} (mlx-vlm warning)")
        )
    return tuple(rows)


def _diagnostics_model_anchor(model_name: str) -> str:
    """Return the stable evidence anchor for one diagnostics entry."""
    gallery_anchor = _gallery_model_anchor(model_name)
    return f"diagnostic-{gallery_anchor.removeprefix('model-')}"


def _diagnostics_model_blocks(
    result: PerformanceResult,
    assessment: ResultAssessment,
    *,
    run_args: argparse.Namespace | None,
    model_provenance: ModelProvenanceRecord | None,
    system_info: Mapping[str, str] | None = None,
    image_profile: ImageInputProfile | None = None,
) -> tuple[ReportBlock, ...]:
    """Build one model's complete maintainer evidence in priority order."""
    blocks: list[ReportBlock] = []
    if assessment.execution == "crashed":
        blocks.append(
            _report_section(
                "Root exception and chain",
                ReportCodeBlock("\n".join(_diagnostics_exception_lines(result))),
                level=4,
            )
        )
        if _is_oom_failure(result):
            blocks.append(
                _report_section(
                    "Memory capacity context (informational)",
                    ReportKeyValues(
                        _oom_capacity_rows(
                            result, system_info=system_info, image_profile=image_profile
                        )
                    ),
                    ReportParagraph(_OOM_CAPACITY_NOTE),
                    level=4,
                )
            )
    blocks.append(
        _report_section(
            "Execution and provenance",
            ReportKeyValues(
                _diagnostics_result_facts(
                    result,
                    assessment,
                    run_args=run_args,
                    model_provenance=model_provenance,
                )
            ),
            level=4,
        )
    )
    if assessment.execution == "crashed" and result.error_traceback:
        # Always fold the complete traceback: the exact evidence is preserved
        # inside the details block without burying surrounding triage content.
        traceback_block = ReportCodeBlock(_home_relative_report_text(result.error_traceback))
        blocks.append(ReportDetails("Complete traceback", (traceback_block,)))
    if result.generation is not None:
        generated_output = _generation_text_value(result.generation) or "(empty)"
        if assessment.execution == "completed":
            output_block: ReportBlock = ReportCodeBlock(generated_output)
            output_title = "Complete output"
        else:
            output_block = ReportCodeBlock(generated_output)
            output_title = "Complete partial output"
        blocks.append(_report_section(output_title, output_block, level=4))
    if result.captured_output_on_fail:
        blocks.append(
            _report_section(
                "Captured stdout/stderr",
                ReportCodeBlock(_home_relative_report_text(result.captured_output_on_fail)),
                level=4,
            )
        )
    return tuple(blocks)


def _diagnostics_counts_blocks(
    context: HtmlReportContext,
) -> tuple[ReportBlock, ...]:
    """Build compact outcome and cached-assessment count tables."""
    assessments = [assessment for _model, assessment in context.assessments]
    outcomes = _run_outcome_counts(context.assessments)
    maintainer_counts = Counter(assessment.maintainer_status for assessment in assessments)
    usability_counts = Counter(assessment.usability for assessment in assessments)
    observation_counts: Counter[ObservationCode] = Counter(
        observation for assessment in assessments for observation in assessment.observations
    )
    # Severity-ranked (registry order): integration signals surface first.
    observation_label_counts = {
        _human_observation_labels((observation,)): observation_counts[observation]
        for observation in sorted(
            observation_counts, key=lambda code: _OBSERVATION_DISPLAY_RANK[code]
        )
    }
    outcome_rows = (
        ("Attempted", str(outcomes["models_attempted"])),
        ("Conclusive outcomes", str(outcomes["models_evaluated"])),
        ("Completed", str(outcomes["models_completed"])),
        ("Crashed", str(outcomes["models_crashed"])),
        ("Indeterminate", str(outcomes["models_indeterminate"])),
    )

    def count_blocks[T: str](
        label: str,
        heading: str,
        counts: Mapping[T, int],
        *,
        preserve_order: bool = False,
        key_label: Callable[[str], str] = lambda key: key.replace("_", " "),
    ) -> tuple[ReportBlock, ReportBlock]:
        ordered = counts.items() if preserve_order else sorted(counts.items())
        rows = tuple((key_label(key), str(value)) for key, value in ordered)
        return ReportParagraph(label), ReportTable(
            (heading, "Count"), rows or (("none recorded", "0"),)
        )

    return (
        ReportParagraph("Outcome counts"),
        ReportTable(("Outcome", "Count"), outcome_rows),
        *count_blocks("Maintainer status counts", "Maintainer status", maintainer_counts),
        *count_blocks(
            "Mechanical-check counts",
            "Mechanical checks",
            usability_counts,
            key_label=_human_status_label,
        ),
        *count_blocks(
            "Observation counts", "Observation", observation_label_counts, preserve_order=True
        ),
    )


def _diagnostics_clean_row(
    result: PerformanceResult,
    model_provenance: ModelProvenanceRecord | None,
) -> tuple[str, str, str]:
    """Build one compact clean-completion context row."""
    revision = model_provenance["resolved_revision"] if model_provenance is not None else None
    revision_preview = revision[: FORMATTING.revision_preview_chars] if revision else "-"
    prompt_diagnostics = result.prompt_diagnostics
    processor = (
        prompt_diagnostics.processor_class.rsplit(".", maxsplit=1)[-1]
        if prompt_diagnostics is not None and prompt_diagnostics.processor_class
        else "-"
    )
    runtime = result.runtime_diagnostics
    stop_reason = runtime.stop_reason if runtime is not None and runtime.stop_reason else "-"
    identity = f"rev {revision_preview}; {processor}; stop {stop_reason}"
    prompt_tokens = _generation_int_metric(result.generation, "prompt_tokens")
    generation_tokens = _generation_int_metric(result.generation, "generation_tokens")
    token_summary = (
        f"{prompt_tokens if prompt_tokens is not None else '-'} prompt / "
        f"{generation_tokens if generation_tokens is not None else '-'} generated"
    )
    generation_tps = _valid_generation_tps(result)
    if generation_tps is not None:
        throughput = f"{_gallery_metric('generation_tps', generation_tps)} tok/s"
    elif generation_tokens is not None and generation_tokens < MIN_THROUGHPUT_SAMPLE_TOKENS:
        throughput = "insufficient sample"
    else:
        throughput = "-"
    peak_memory = _generation_float_metric(result.generation, "peak_memory")
    memory = (
        f"{_gallery_metric('peak_memory', peak_memory)} GB peak" if peak_memory is not None else "-"
    )
    if runtime is not None and (
        runtime.post_cleanup_active_memory_gb is not None
        or runtime.post_cleanup_cache_memory_gb is not None
    ):
        active = _gallery_metric(
            "post_cleanup_active_memory_gb",
            runtime.post_cleanup_active_memory_gb,
        )
        cache = _gallery_metric(
            "post_cleanup_cache_memory_gb",
            runtime.post_cleanup_cache_memory_gb,
        )
        memory = f"{memory}; cleanup {active}/{cache} GB active/cache"
    return result.model_name, identity, f"{token_summary}; {throughput}; {memory}"


type DiagnosticsPresentation = Literal["expanded", "observation", "indeterminate"]


def _diagnostics_partition_blocks(
    results: Sequence[PerformanceResult],
    *,
    presentation: DiagnosticsPresentation,
    assessments: Mapping[str, ResultAssessment],
    provenance: Mapping[str, ModelProvenanceRecord],
    run_args: argparse.Namespace | None,
    system_info: Mapping[str, str] | None = None,
    image_profile: ImageInputProfile | None = None,
) -> tuple[ReportBlock, ...]:
    """Build one expanded or collapsed cached-assessment partition."""
    blocks: list[ReportBlock] = []
    for result in results:
        assessment = assessments[result.model_name]
        anchor = html.escape(_diagnostics_model_anchor(result.model_name), quote=True)
        anchor_block = ReportRaw(
            markdown_lines=(f'<a id="{anchor}"></a>',),
            html_lines=(f'<a id="{anchor}"></a>',),
        )
        evidence = _diagnostics_model_blocks(
            result,
            assessment,
            run_args=run_args,
            model_provenance=provenance.get(result.model_name),
            system_info=system_info,
            image_profile=image_profile,
        )
        if presentation == "expanded":
            entry: ReportBlock = ReportSection(result.model_name, evidence, level=3)
        else:
            if presentation == "observation":
                detail = _gallery_observation_labels(assessment.observations)
            elif _is_download_timeout_failure(result):
                detail = "indeterminate: download timeout (re-run, pre-fetch, or raise --timeout)"
            elif _is_incomplete_cache_failure(result):
                detail = (
                    "indeterminate: incomplete cached snapshot (resume or re-fetch the download)"
                )
            else:
                detail = "indeterminate: connectivity failure"
            entry = ReportDetails(
                f"{result.model_name} — {assessment.usability} — {detail}",
                (ReportSection(result.model_name, evidence, level=3),),
            )
        blocks.extend((anchor_block, entry))
    return tuple(blocks) or (ReportParagraph("None."),)


def _run_input_rows_for_context(
    image_path: Path | None,
    report_context: HtmlReportContext,
) -> tuple[tuple[str, str], ...]:
    """Lane and input-image rows from whichever report context a renderer holds."""
    results = report_context.result_set.results
    return _run_input_summary_rows(
        _run_image_record(image_path, getattr(report_context, "image_profile", None)),
        getattr(getattr(report_context, "mode_policy", None), "eval_mode", None),
        getattr(
            getattr(report_context, "mode_policy", None),
            "assessment_profile",
            results[0].assessment_profile if results else "general",
        ),
    )


def _diagnostics_evidence_blocks(
    report_context: HtmlReportContext,
    *,
    run_args: argparse.Namespace | None,
    image_path: Path | None = None,
) -> tuple[ReportBlock, ...]:
    """Build the shared skim-first diagnostics hierarchy from cached assessments."""
    assessments = _assessments_by_model(report_context)
    provenance = _model_provenance_by_model(report_context)
    # The canonical HTML context carries no image profile; the capacity rows
    # then simply omit the input-image line rather than re-reading the file.
    image_profile: ImageInputProfile | None = getattr(report_context, "image_profile", None)
    partitions = _partition_diagnostics(report_context)
    highlighted = (*partitions.actionable, *partitions.observations, *partitions.indeterminate)
    triage_rows = tuple(
        (
            ReportLink(result.model_name, _diagnostics_model_anchor(result.model_name)),
            assessments[result.model_name].execution,
            assessments[result.model_name].usability,
            assessments[result.model_name].maintainer_status,
            _gallery_observation_labels(assessments[result.model_name].observations),
        )
        for result in highlighted
    )
    triage: ReportBlock = (
        ReportTable(
            ("Model", "Execution", "Mechanical checks", "Maintainer status", "Observations"),
            triage_rows,
        )
        if triage_rows
        else ReportParagraph("No highlighted attempts.")
    )
    blocks: list[ReportBlock] = [
        _report_section(
            "Run Summary",
            ReportKeyValues(_run_input_rows_for_context(image_path, report_context)),
            *_diagnostics_counts_blocks(report_context),
        ),
        _report_section("Triage", triage),
        _report_section(
            "Crashes requiring action",
            *_diagnostics_partition_blocks(
                partitions.actionable,
                presentation="expanded",
                assessments=assessments,
                provenance=provenance,
                run_args=run_args,
                system_info=report_context.system_info,
                image_profile=image_profile,
            ),
        ),
        _report_section(
            "Completed Runs with Observations",
            *_diagnostics_partition_blocks(
                partitions.observations,
                presentation="observation",
                assessments=assessments,
                provenance=provenance,
                run_args=run_args,
                system_info=report_context.system_info,
                image_profile=image_profile,
            ),
        ),
        _report_section(
            "Indeterminate Attempts",
            *_diagnostics_partition_blocks(
                partitions.indeterminate,
                presentation="indeterminate",
                assessments=assessments,
                provenance=provenance,
                run_args=run_args,
                system_info=report_context.system_info,
                image_profile=image_profile,
            ),
        ),
    ]
    # Plain names: compliance models carry no diagnostics evidence blocks, so
    # there is no in-document anchor to link; complete evidence is in the
    # gallery, as the section preamble states.
    compliance_rows = tuple(
        (
            result.model_name,
            _human_status_label(assessments[result.model_name].usability),
            _gallery_observation_labels(assessments[result.model_name].observations),
        )
        for result in partitions.compliance
    )
    compliance: ReportBlock = (
        ReportTable(("Model", "Mechanical checks", "Observations"), compliance_rows)
        if compliance_rows
        else ReportParagraph("No compliance-only observations.")
    )
    blocks.append(
        _report_section(
            "Model Compliance Notes (not maintainer issues)",
            ReportParagraph(
                "Prompt-compliance observations (missing fields, constraint counts, hint "
                "copying, instruction echo, cap hits) inform model selection; complete "
                "evidence is in the model gallery."
            ),
            compliance,
        )
    )
    clean_rows = tuple(
        _diagnostics_clean_row(result, provenance.get(result.model_name))
        for result in partitions.clean
    )
    clean: ReportBlock = (
        ReportDetails(
            "Completions without detected concerns",
            (ReportTable(("Model", "Runtime identity", "Performance"), clean_rows),),
        )
        if clean_rows
        else ReportParagraph("No completion had no detected concerns.")
    )
    blocks.append(_report_section("Context for completions without detected concerns", clean))
    return tuple(blocks)


def _issue_provenance_blocks(
    *,
    library_versions: LibraryVersionDict,
    system_info: Mapping[str, str],
) -> tuple[ReportBlock, ...]:
    """Build prompt and environment blocks for a direct crash issue draft."""
    rows = list(
        _collect_report_component_rows(
            versions=library_versions,
            system_info=dict(system_info),
            library_names=_ISSUE_RELEVANT_LIB_NAMES,
            system_keys=_ISSUE_RELEVANT_SYSTEM_KEYS,
        )
    )
    producer = _collect_check_models_provenance()
    producer_parts = [producer["version"]]
    if producer["git_revision"]:
        producer_parts.append(f"revision {producer['git_revision']}")
    dirty = producer.get("dirty")
    if dirty is not None:
        producer_parts.append("dirty" if dirty else "clean")
    rows.append(("check_models", "; ".join(producer_parts)))
    components: ReportBlock = (
        ReportTable(("Component", "Value"), tuple(rows))
        if rows
        else ReportParagraph("Environment and component provenance unavailable.")
    )
    full_environment = ReportTable(
        ("Evidence", "Link"),
        (
            (
                "Complete dependency and toolchain inventory",
                ReportTargetLink(
                    "environment.log",
                    _github_repo_artifact_url(_PUBLISHED_OUTPUT_ROOT / DEFAULT_ENV_OUTPUT.name),
                ),
            ),
        ),
        compact=True,
    )
    return (
        _report_section(
            "Provenance and Environment",
            _report_section("Components", components, level=3),
            _report_section("Full environment evidence", full_environment, level=3),
        ),
    )


def generate_diagnostics_report(
    results: Sequence[PerformanceResult],
    filename: Path,
    *,
    prompt: str,
    library_versions: LibraryVersionDict,
    system_info: Mapping[str, str],
    report_context: ReportRenderContext,
    image_path: Path | None = None,
    run_args: argparse.Namespace | None = None,
) -> None:
    """Write current-run maintainer evidence without reclassifying results."""
    del results  # The cached context is the sole classification and result source.
    model_provenance = _model_provenance_by_model(report_context)
    partitions = _partition_diagnostics(report_context)
    highlighted = (
        *partitions.actionable,
        *partitions.observations,
        *partitions.indeterminate,
    )
    blocks = (
        ReportParagraph(_run_objective_statement(report_context.mode_policy.eval_mode)),
        *_diagnostics_evidence_blocks(report_context, run_args=run_args, image_path=image_path),
        *_diagnostics_shared_context_blocks(
            prompt=prompt,
            highlighted_results=highlighted,
            model_provenance=model_provenance,
            library_versions=library_versions,
            system_info=system_info,
            image_path=image_path,
            run_args=run_args,
        ),
    )
    # MD004/MD037: verbatim model-output evidence (repeated fragments,
    # preambles, reasoning text) may contain asterisk bullets and
    # emphasis-like sequences; the evidence contract forbids editing them.
    parts = [
        "# Diagnostics",
        "",
        *_guard_markdownlint_block(render_report_markdown(blocks), rules="MD004 MD037"),
    ]
    while parts and parts[-1] == "":
        parts.pop()
    _write_text_file(filename, "\n".join(parts) + "\n")


def _html_model_link(model_name: str) -> str:
    """Return a safe internal link to one complete-evidence entry."""
    anchor = _gallery_model_anchor(model_name)
    return (
        f'<a href="#{html.escape(anchor, quote=True)}">'
        f"<code>{html.escape(model_name, quote=True)}</code></a>"
    )


def _html_filter_controls() -> str:
    """Return dependency-free filters over exact cached assessment strings."""
    return """
<div class="filter-controls">
<strong>Filter current-run chooser:</strong>
<label>Model <input id="model-search" type="search" placeholder="Search models"></label>
<label>Execution <select id="execution-filter">
<option value="all">all</option><option value="completed">completed</option>
<option value="crashed">crashed</option><option value="indeterminate">indeterminate</option>
</select></label>
<label>Mechanical checks <select id="usability-filter">
<option value="all">all</option><option value="usable">no concerns detected</option>
<option value="usable_with_caveats">concerns detected</option>
<option value="unusable">major concerns</option><option value="not_evaluated">not assessed</option>
</select></label>
<label>Maintainer status <select id="maintainer-status-filter">
<option value="all">all</option><option value="actionable_failure">actionable_failure</option>
<option value="observation_needs_reproduction">observation_needs_reproduction</option>
<option value="none">none</option>
</select></label>
<span id="filter-info" role="status" aria-live="polite">Showing all rows</span>
</div>
<script>
function applyAssessmentFilters() {
    const query = document.getElementById('model-search').value.toLowerCase();
    const execution = document.getElementById('execution-filter').value;
    const usability = document.getElementById('usability-filter').value;
    const maintainer = document.getElementById('maintainer-status-filter').value;
    const rows = document.querySelectorAll('#chooser-table tr[data-model]');
    let visible = 0;
    rows.forEach(row => {
        const show = row.dataset.model.includes(query)
            && (execution === 'all' || row.dataset.execution === execution)
            && (usability === 'all' || row.dataset.usability === usability)
            && (maintainer === 'all' || row.dataset.maintainerStatus === maintainer);
        row.classList.toggle('hidden', !show);
        if (show) visible += 1;
    });
    document.getElementById('filter-info').textContent =
        `Showing ${visible} of ${rows.length} rows`;
}
function sortChooserColumn(button) {
    const table = document.querySelector('#chooser-table table');
    if (!table || !table.tBodies.length) return;
    const column = Number(button.dataset.sortColumn);
    const ascending = button.dataset.sortDirection !== 'ascending';
    table.querySelectorAll('.sort-button').forEach(candidate => {
        candidate.removeAttribute('data-sort-direction');
    });
    table.querySelectorAll('th[aria-sort]').forEach(heading => heading.removeAttribute('aria-sort'));
    button.dataset.sortDirection = ascending ? 'ascending' : 'descending';
    button.closest('th').setAttribute('aria-sort', button.dataset.sortDirection);
    const rows = Array.from(table.tBodies[0].rows);
    rows.sort((left, right) => {
        const leftValue = left.cells[column].dataset.sortValue || '';
        const rightValue = right.cells[column].dataset.sortValue || '';
        if (!leftValue || !rightValue) {
            if (!leftValue && !rightValue) return 0;
            return !leftValue ? 1 : -1;
        }
        const leftNumber = Number(leftValue);
        const rightNumber = Number(rightValue);
        const comparison = Number.isFinite(leftNumber) && Number.isFinite(rightNumber)
            ? leftNumber - rightNumber
            : leftValue.localeCompare(rightValue, undefined, {numeric: true});
        return ascending ? comparison : -comparison;
    });
    rows.forEach(row => table.tBodies[0].appendChild(row));
}
document.querySelectorAll('.filter-controls input, .filter-controls select')
    .forEach(control => control.addEventListener('input', applyAssessmentFilters));
applyAssessmentFilters();
</script>
"""


def _report_image_preview(image_path: Path | None) -> tuple[str, str, bytes] | None:
    """Return a bounded, orientation-corrected preview shared by report formats.

    Cached per (path, size, mtime): the gallery, the HTML report and the
    reproduction inputs all want the same re-encoding of the same input.
    """
    if image_path is None or not image_path.is_file():
        return None
    identity = _file_identity(image_path)
    if identity is not None and (cached := _IMAGE_PREVIEW_CACHE.get(identity)) is not None:
        return cached
    output_formats: Mapping[str, tuple[str, str, str]] = {
        ".jpg": (".jpg", "JPEG", "image/jpeg"),
        ".jpeg": (".jpeg", "JPEG", "image/jpeg"),
        ".png": (".png", "PNG", "image/png"),
        ".gif": (".gif", "GIF", "image/gif"),
        ".webp": (".webp", "WEBP", "image/webp"),
    }
    suffix, image_format, mime_type = output_formats.get(
        image_path.suffix.casefold(),
        (".jpg", "JPEG", "image/jpeg"),
    )
    try:
        with Image.open(image_path) as img_original:
            img_to_save: PILImage = ImageOps.exif_transpose(img_original).copy()
        try:
            img_to_save.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            if image_format == "JPEG" and img_to_save.mode not in {"RGB", "L"}:
                converted = img_to_save.convert("RGB")
                img_to_save.close()
                img_to_save = converted
            img_buffer = io.BytesIO()
            img_to_save.save(img_buffer, format=image_format)
        finally:
            img_to_save.close()
    except (OSError, ValueError):
        logger.warning("Failed to prepare report image preview: %s", image_path)
        return None
    preview = (suffix, mime_type, img_buffer.getvalue())
    if identity is not None:
        _IMAGE_PREVIEW_CACHE[identity] = preview
    return preview


def _html_embedded_image(image_path: Path | None) -> str:
    """Return an orientation-corrected embedded preview when an image is available."""
    preview = _report_image_preview(image_path)
    if preview is None:
        return ""
    _suffix, mime_type, image_bytes = preview
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    return (
        '<section id="test-image"><h2>Test Image</h2>'
        f'<img src="data:{html.escape(mime_type, quote=True)};base64,'
        f'{html.escape(image_data, quote=True)}" class="embedded-image" '
        'alt="Test image used for model evaluation"></section>'
    )


def _html_gallery_chooser(report_context: HtmlReportContext) -> str:
    """Render the same facts-only chooser and resource highlights as Markdown."""
    assessments = _assessments_by_model(report_context)
    rows = [
        _gallery_row(result, assessments[result.model_name])
        for result in report_context.result_set.results
    ]
    result_by_model = {result.model_name: result for result in report_context.result_set.results}
    data = _gallery_chooser_data(rows)
    ordered = data.ordered
    chooser_rows = [
        (
            _html_model_link(row.model),
            _human_status_label(assessments[row.model].execution),
            _human_status_label(row.usability),
            _human_status_label(assessments[row.model].maintainer_status),
            _gallery_total_time_cell(row),
            _gallery_throughput_cell(row),
            _format_float_or_dash(row.first_token_latency_s, digits=2),
            _gallery_metric("peak_memory", row.peak_memory_gb),
            _gallery_metric("prompt_tokens", row.prompt_tokens),
            _gallery_metric("generation_tokens", row.generation_tokens),
            _gallery_observation_labels(row.observations),
            _gallery_preview_cell_html(row),
        )
        for row in ordered
    ]
    chooser_attrs = [
        _html_status_attrs(result_by_model[row.model], assessments[row.model]) for row in ordered
    ]
    chooser_sort_values = [
        (
            row.model,
            assessments[row.model].execution,
            row.usability,
            assessments[row.model].maintainer_status,
            row.total_time_s,
            row.generation_tps,
            row.first_token_latency_s,
            row.peak_memory_gb,
            row.prompt_tokens,
            row.generation_tokens,
            _gallery_observation_labels(row.observations),
            row.output_preview,
        )
        for row in ordered
    ]
    parts = [
        '<section id="current-run-chooser">',
        "<h2>Current-run Chooser</h2>",
        f"<p>{html.escape(_gallery_chooser_explanation(), quote=True)}</p>",
        _html_filter_controls(),
        '<div id="chooser-table">',
        _html_table(
            caption="Current-run model chooser",
            headers=(
                "Model",
                "Execution",
                "Mechanical checks",
                "Maintainer status",
                "Total s",
                "Gen TPS",
                "Prefill/first s",
                "Peak GB",
                "Prompt tok",
                "Gen tok",
                "Observations",
                "Output preview",
            ),
            rows=chooser_rows,
            row_attrs=chooser_attrs,
            raw_columns=frozenset({0, 11}),
            sort_values=chooser_sort_values,
            sortable=True,
        ),
        "</div>",
        "<h3>Resource Highlights</h3>",
    ]
    # The chooser table is sortable by every column, so the former
    # lowest-memory/fastest re-listing tables collapse into highlight lines.
    if data.quickest is not None:
        parts.append(
            "<p>Quickest completion without detected concerns (end-to-end, including "
            f"model load): {_html_model_link(data.quickest.model)} at "
            f"{html.escape(_gallery_total_time_cell(data.quickest))}.</p>"
        )
    else:
        parts.append(
            "<p>No completion without detected concerns has a captured end-to-end time "
            "in this run.</p>"
        )
    if data.lowest_memory is not None:
        parts.append(
            "<p>Lowest peak memory among completions without detected concerns: "
            f"{_html_model_link(data.lowest_memory.model)} at "
            f"{html.escape(_gallery_metric('peak_memory', data.lowest_memory.peak_memory_gb))} "
            "GB.</p>"
        )
    parts.append(f"<p>{html.escape(_GALLERY_THROUGHPUT_CAVEAT)}</p>")

    parts.append("<h3>Avoid for This Run</h3>")
    if data.avoided:
        parts.append(
            _html_table(
                caption="Unusable and not-evaluated models",
                headers=("Model", "Mechanical checks", "Observations", "Output preview"),
                rows=[
                    (
                        _html_model_link(row.model),
                        _human_status_label(row.usability),
                        _gallery_observation_labels(row.observations),
                        row.output_preview,
                    )
                    for row in data.avoided
                ],
                raw_columns=frozenset({0}),
            )
        )
    else:
        parts.append("<p>No unusable or not-evaluated models in this run.</p>")
    parts.append("</section>")
    return "\n".join(parts)


def _html_gallery_model(
    result: PerformanceResult,
    row: GalleryRow,
    assessment: ResultAssessment,
    model_provenance: ModelProvenanceRecord | None,
) -> str:
    """Render one complete, escaped model-evidence entry from shared gallery facts."""
    facts = tuple(
        (label, value)
        for label, value in _gallery_model_facts(result, row, assessment, model_provenance)
        if value is not None
    )
    parts = [
        f'<article id="{html.escape(_gallery_model_anchor(result.model_name), quote=True)}">',
        f"<h3>{html.escape(result.model_name, quote=True)}</h3>",
        f"<details><summary>Complete evidence: {html.escape(result.model_name, quote=True)}</summary>",
        _html_table(
            caption=f"Captured facts for {result.model_name}",
            headers=("Fact", "Value"),
            rows=facts,
        ),
        *render_report_html(_gallery_model_evidence_blocks(result)),
        "</details>",
        "</article>",
    ]
    return "\n".join(parts)


def _html_complete_gallery(report_context: HtmlReportContext) -> str:
    """Render complete evidence in the same stable order as the Markdown gallery."""
    assessments = _assessments_by_model(report_context)
    model_provenance = _model_provenance_by_model(report_context)
    rows_by_model = {
        result.model_name: _gallery_row(result, assessments[result.model_name])
        for result in report_context.result_set.results
    }
    ordered_results = sorted(
        report_context.result_set.results,
        key=lambda result: (
            _gallery_usability_sort_key(rows_by_model[result.model_name].usability),
            result.model_name,
        ),
    )
    parts = [
        '<section id="complete-model-evidence">',
        "<h2>Complete Per-model Evidence</h2>",
        "<p>Complete generated or crash evidence for every attempted model.</p>",
    ]
    parts.extend(
        _html_gallery_model(
            result,
            rows_by_model[result.model_name],
            assessments[result.model_name],
            model_provenance.get(result.model_name),
        )
        for result in ordered_results
    )
    parts.append("</section>")
    return "\n".join(parts)


def _html_maintainer_diagnostics(
    report_context: HtmlReportContext,
    *,
    run_args: argparse.Namespace | None,
    image_path: Path | None,
) -> str:
    """Render the same cached diagnostic block hierarchy used by Markdown."""
    parts = [
        '<section id="maintainer-diagnostics">',
        "<h2>Maintainer Diagnostics</h2>",
        *render_report_html(
            _diagnostics_evidence_blocks(report_context, run_args=run_args, image_path=image_path)
        ),
        "</section>",
    ]
    return "\n".join(parts)


def _html_run_inputs(image_path: Path | None, report_context: HtmlReportContext) -> str:
    """Render the evaluation lane and input-image facts ahead of every table."""
    rows = _run_input_rows_for_context(image_path, report_context)
    return "".join(render_report_html((ReportKeyValues(rows),)))


def _html_runtime_facts(
    results: Sequence[PerformanceResult],
    total_runtime_seconds: float,
) -> str:
    """Render factual total and aggregate timing evidence without semantic projections."""
    # Rendered before reports finish, so this is the model sweep only; the
    # retained JSONL header and run summary carry the end-to-end duration.
    rows = [("Model sweep runtime", format_overall_runtime(total_runtime_seconds))]
    runtime_analysis = _build_runtime_analysis_summary(results)
    if runtime_analysis is not None:
        facts = [
            _runtime_generation_total_fact(runtime_analysis),
            _runtime_phase_totals_fact(runtime_analysis),
            *_runtime_timing_snapshot_facts(runtime_analysis),
        ]
        rows.extend(fact for fact in facts if fact is not None)
    return "\n".join(
        (
            '<section id="runtime">',
            "<h2>Runtime</h2>",
            "<p><b>Runtime</b></p>",
            "".join(render_report_html((ReportKeyValues(tuple(rows)),))),
            "</section>",
        )
    )


def _html_provenance(
    *,
    report_context: HtmlReportContext,
    versions: LibraryVersionDict,
    prompt: str,
    image_path: Path | None,
    run_args: argparse.Namespace | None,
) -> str:
    """Render the same single-copy reproduction context used by Markdown."""
    partitions = _partition_diagnostics(report_context)
    highlighted = (
        *partitions.actionable,
        *partitions.observations,
        *partitions.indeterminate,
    )
    blocks = _diagnostics_shared_context_blocks(
        prompt=prompt,
        highlighted_results=highlighted,
        model_provenance=_model_provenance_by_model(report_context),
        library_versions=versions,
        system_info=report_context.system_info,
        image_path=image_path,
        run_args=run_args,
    )
    return "\n".join(
        (
            '<section id="provenance">',
            *render_report_html(blocks),
            "</section>",
        )
    )


def _build_full_html_document(
    *,
    report_context: HtmlReportContext,
    versions: LibraryVersionDict,
    prompt: str,
    total_runtime_seconds: float,
    image_path: Path | None,
    run_args: argparse.Namespace | None,
) -> str:
    """Build standalone HTML from cached gallery and diagnostic facts only."""
    css = """
<style>
body { font-family: system-ui, sans-serif; line-height: 1.45; margin: 2rem auto; max-width: 1200px; padding: 0 1rem; }
nav a { margin-right: 1rem; }
table { border-collapse: collapse; margin: 1rem 0 2rem; width: 100%; }
caption { font-weight: 600; text-align: left; }
th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; }
th { background: #f2f2f2; }
.sort-button { background: transparent; border: 0; color: inherit; cursor: pointer; font: inherit; font-weight: bold; padding: 0; text-align: left; }
.sort-button::after { color: #666; content: " ↕"; }
.sort-button[data-sort-direction="ascending"]::after { content: " ↑"; }
.sort-button[data-sort-direction="descending"]::after { content: " ↓"; }
pre { background: #f7f7f7; border-left: 3px solid #666; overflow-x: auto; padding: 0.75rem; white-space: pre-wrap; }
details { margin: 0.75rem 0 1.5rem; }
summary { color: #0645ad; cursor: pointer; font-weight: 600; }
.crashed { background: #fff0f0; }
.indeterminate { background: #fff8dc; }
.filter-controls { background: #f5f5f5; border: 1px solid #ddd; margin: 1rem 0; padding: 0.75rem; }
.filter-controls label { display: inline-block; margin: 0.25rem 0.75rem 0.25rem 0; }
.hidden { display: none; }
.embedded-image { border: 1px solid #ccc; max-width: min(100%, 600px); }
</style>
"""
    return "\n".join(
        (
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>Model Results: Gallery and Diagnostics</title>",
            css,
            "</head>",
            "<body>",
            "<h1>Model Results: Gallery and Diagnostics</h1>",
            (
                '<nav aria-label="Report sections"><a href="#current-run-chooser">Chooser</a>'
                '<a href="#complete-model-evidence">Complete evidence</a>'
                '<a href="#maintainer-diagnostics">Maintainer diagnostics</a>'
                '<a href="#provenance">Provenance</a></nav>'
            ),
            "<p>"
            + html.escape(
                _run_objective_statement(
                    getattr(getattr(report_context, "mode_policy", None), "eval_mode", None)
                )
            )
            + "</p>",
            _html_run_inputs(image_path, report_context),
            _html_embedded_image(image_path),
            _html_runtime_facts(report_context.result_set.results, total_runtime_seconds),
            _html_gallery_chooser(report_context),
            _html_complete_gallery(report_context),
            _html_maintainer_diagnostics(
                report_context,
                run_args=run_args,
                image_path=image_path,
            ),
            _html_provenance(
                report_context=report_context,
                versions=versions,
                prompt=prompt,
                image_path=image_path,
                run_args=run_args,
            ),
            "</body>",
            "</html>",
        )
    )


# =============================================================================
# SECTION: REPORT GENERATORS & RUNTIME FINGERPRINTS
# =============================================================================


def generate_html_report(
    results: list[PerformanceResult],
    filename: Path,
    versions: LibraryVersionDict,
    prompt: str,
    total_runtime_seconds: float,
    image_path: Path | None = None,
    report_context: HtmlReportContext | None = None,
    run_args: argparse.Namespace | None = None,
) -> None:
    """Write a standalone HTML mirror of the facts-only gallery and diagnostics.

    Args:
        results: Run results to render.
        filename: Output HTML file path.
        versions: Installed library versions shown in the report.
        prompt: Prompt used for the run.
        total_runtime_seconds: Total wall-clock runtime for the full run.
        image_path: Optional input image path for the report header.
        report_context: Optional cached shared report context built in finalization.
        run_args: Original CLI arguments used to preserve diagnostic reproduction settings.
    """
    if not results:
        log_warning_note("No results to generate HTML report.")
        return

    if report_context is None:
        report_context = _build_html_report_context(
            results=results,
            prompt=prompt,
        )

    html_content = _build_full_html_document(
        report_context=report_context,
        versions=versions,
        prompt=prompt,
        total_runtime_seconds=total_runtime_seconds,
        image_path=image_path,
        run_args=run_args,
    )

    _write_text_file(filename, html_content)


def _generate_model_gallery_section(report_context: ReportRenderContext) -> list[str]:
    """Render complete evidence in stable usable-first order."""
    assessments = _assessments_by_model(report_context)
    model_provenance = _model_provenance_by_model(report_context)
    results = report_context.result_set.results
    rows_by_model = {
        result.model_name: _gallery_row(result, assessments[result.model_name])
        for result in results
    }
    ordered_results = sorted(
        results,
        key=lambda result: (
            _gallery_usability_sort_key(rows_by_model[result.model_name].usability),
            result.model_name,
        ),
    )
    md = [
        "## Complete Per-model Evidence",
        "",
        "Complete generated or crash evidence for every attempted model.",
        "",
    ]
    for result in ordered_results:
        md.extend(
            _render_gallery_model(
                result,
                rows_by_model[result.model_name],
                assessments[result.model_name],
                model_provenance.get(result.model_name),
            )
        )
        md.extend(["---", ""])
    return md


def generate_markdown_gallery_report(
    results: list[PerformanceResult],
    filename: Path,
    prompt: str,
    metadata: MetadataDict | None = None,
    report_context: ReportRenderContext | None = None,
    versions: LibraryVersionDict | None = None,
    image_path: Path | None = None,
) -> None:
    """Write the facts-only current-run chooser and complete model evidence."""
    if not results:
        log_warning_note("No results to generate Markdown gallery report.")
        return

    if report_context is None:
        raise MissingGalleryAssessmentError

    assessments = _assessments_by_model(report_context)
    gallery_rows = [
        _gallery_row(result, assessments[result.model_name])
        for result in report_context.result_set.results
    ]

    md: list[str] = []
    md.append("# Model Output Gallery")
    md.append("")
    md.append(f"Generated on: {local_now_str()}")
    md.append("")
    md.extend(
        f"- *{label}:* {value}"
        for label, value in _run_input_summary_rows(
            _run_image_record(image_path, report_context.image_profile),
            report_context.mode_policy.eval_mode,
            report_context.mode_policy.assessment_profile,
        )
    )
    md.append("")
    md.extend(_wrap_markdown_text(_run_objective_statement(report_context.mode_policy.eval_mode)))
    md.append("")
    md.extend(
        _wrap_markdown_text(
            "Complete per-model evidence artifact with image metadata, the source prompt, "
            "a facts-only chooser, and full generated or crash output for every attempted model.",
        ),
    )
    md.append("")
    if (preview := _report_image_preview(image_path)) is not None:
        suffix, _mime_type, image_bytes = preview
        asset = filename.parent / "assets" / _preview_asset_name(suffix, image_bytes)
        try:
            asset.parent.mkdir(parents=True, exist_ok=True)
            _write_bytes_file(asset, image_bytes)
            # Any pre-durability `source-image.jpg` beside it is left exactly
            # as it is: retained diagnostics and pasted issues may still
            # reference that name, and it is simply never overwritten again.
        except OSError:
            logger.warning("Failed to publish gallery reference image: %s", asset)
        else:
            md.extend(
                (
                    "## Reference Image",
                    "",
                    f"![Reference image](assets/{asset.name})",
                    "",
                )
            )
    md.extend(_render_gallery_chooser(gallery_rows))
    md.extend(_render_gallery_output_glance(gallery_rows))
    md.extend(
        _build_gallery_stamps_section(
            versions=versions,
            system_info=report_context.system_info,
        )
    )
    _append_markdown_image_metadata_section(md, metadata)
    md.append("## Prompt")
    _append_markdown_wrapped_blockquote(md, prompt)
    md.extend(_generate_model_gallery_section(report_context))

    _write_markdown_artifact(filename, md)


def _assessments_by_model(
    report_context: HtmlReportContext,
) -> dict[str, ResultAssessment]:
    """Index the cached minimal current-run assessment by model identifier."""
    return dict(report_context.assessments)


def _model_provenance_by_model(
    report_context: HtmlReportContext,
) -> dict[str, ModelProvenanceRecord]:
    """Index the cached requested and resolved model identities."""
    return dict(report_context.model_provenance)


# A bare http(s) URL that is not already inside angle brackets or a Markdown
# link: not preceded by [ or <, not followed by ] or >.
_BARE_URL_RE: Final[re.Pattern[str]] = re.compile(r"(?<![\[<])(https?://[^\s\)>\]]+)(?![\]>])")


def _wrap_bare_urls(text: str) -> str:
    """Wrap bare URLs in angle brackets (Markdown autolinks) to satisfy markdownlint MD034."""
    return _BARE_URL_RE.sub(r"<\1>", text)


def normalize_markdown_trailing_spaces(md_text: str) -> str:
    """Normalize trailing spaces on each line in Markdown text.

    Rules:
    - Keep exactly FORMATTING.markdown_hard_break_spaces trailing spaces (Markdown hard line break).
    - Strip any other trailing horizontal whitespace or invisible format characters,
      including non-breaking spaces and trailing BOM/zero-width markers, to avoid
      accidental MD009-style endings.
    """
    out_lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for ln in md_text.splitlines():
        if fence_char is not None:
            out_lines.append(ln)
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*",
                ln,
            )
            if closing is not None:
                fence_char = None
                fence_length = 0
            continue

        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", ln)
        if opening is not None:
            fence = opening.group(1)
            fence_char = fence[0]
            fence_length = len(fence)
            out_lines.append(ln)
            continue

        stripped = ln.rstrip(" \t\u00a0\u200b\u200c\u200d\u2060\ufeff")
        trailing = ln[len(stripped) :]
        if not trailing:
            out_lines.append(ln)
            continue
        if trailing == (" " * FORMATTING.markdown_hard_break_spaces):
            out_lines.append(ln)
        else:
            out_lines.append(stripped)
    return "\n".join(out_lines)


@lru_cache(maxsize=1)
def get_system_info() -> tuple[str, str | None]:
    """Get system architecture and GPU information.

    Cached since system info doesn't change during execution.

    Returns:
        Tuple of (architecture_string, optional_gpu_info)
    """
    arch: str = platform.machine()
    gpu_info: str | None = None
    if platform.system() == "Darwin":
        first_display = _first_system_profiler_entry(get_device_info(), "SPDisplaysDataType")
        if first_display is not None:
            gpu_info = _mapping_first_text_value(first_display, "sppci_model", "_name")
    return arch, gpu_info


def _run_macos_toolchain_command(
    command: Sequence[str],
    *,
    timeout: int = 2,
    empty_output: str | None = None,
) -> str | None:
    """Run a macOS toolchain probe and return stripped stdout on success."""
    try:
        result = subprocess.run(  # noqa: S603 - fixed macOS toolchain probes only
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or empty_output


@lru_cache(maxsize=1)
def _get_mlx_device_info() -> MlxDeviceInfo:
    """Return the validated report-facing subset of ``mx.device_info()``."""
    if mx is None:
        return {}
    device_info_fn = getattr(mx, "device_info", None)
    if not callable(device_info_fn):
        return {}
    try:
        payload = _as_str_object_mapping(device_info_fn())
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as err:
        logger.debug("Could not retrieve MLX device information: %s", err)
        return {}
    if payload is None:
        return {}

    info: MlxDeviceInfo = {}
    device_name = payload.get("device_name")
    if isinstance(device_name, str) and device_name.strip():
        info["device_name"] = device_name.strip()
    architecture = payload.get("architecture")
    if isinstance(architecture, str) and architecture.strip():
        info["architecture"] = architecture.strip()
    memory_size = payload.get("memory_size")
    if type(memory_size) is int and memory_size > 0:
        info["memory_size"] = memory_size
    recommended_size = payload.get("max_recommended_working_set_size")
    if type(recommended_size) is int and recommended_size > 0:
        info["max_recommended_working_set_size"] = recommended_size
    return info


def _get_macos_sysctl_value(name: str) -> str | None:
    """Read one allowlisted macOS hardware sysctl through the bounded runner."""
    if platform.system() != "Darwin":
        return None
    if name not in {"hw.memsize", "machdep.cpu.brand_string"}:
        return None
    return _run_macos_toolchain_command(["/usr/sbin/sysctl", "-n", name])


def _positive_int_text(value: str | None) -> int | None:
    """Parse a strictly positive integer or return no value."""
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _get_total_memory_bytes() -> int | None:
    """Return detected unified memory without inventing a fallback amount."""
    if psutil is not None:
        try:
            total = psutil.virtual_memory().total
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            total = None
        if type(total) is int and total > 0:
            return total
    sysctl_total = _positive_int_text(_get_macos_sysctl_value("hw.memsize"))
    if sysctl_total is not None:
        return sysctl_total
    return _get_mlx_device_info().get("memory_size")


def _get_recommended_working_set_bytes() -> int | None:
    """Return Metal's positive recommended working-set ceiling when available."""
    return _get_mlx_device_info().get("max_recommended_working_set_size")


def _first_toolchain_output_line(output: str | None) -> str | None:
    """Return the first non-empty line from a toolchain command output."""
    if output is None:
        return None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _get_macos_toolchain_info() -> dict[str, str]:
    """Get macOS developer toolchain info (Xcode, SDK, CLTools).

    Returns dict with available toolchain version info. Safe to call on any OS
    (returns empty dict on non-macOS).
    """
    info: dict[str, str] = {}
    if platform.system() != "Darwin":
        return info

    # Get SDK version (useful for Metal/framework compatibility)
    sdk_version = _run_macos_toolchain_command(
        ["/usr/bin/xcrun", "-sdk", "macosx", "--show-sdk-version"],
    )
    if sdk_version:
        info["SDK Version"] = sdk_version

    developer_dir = _run_macos_toolchain_command(["/usr/bin/xcode-select", "-p"])
    if developer_dir:
        info["Active Developer Directory"] = developer_dir

    # Get Xcode version (important for Metal shader compilation)
    xcode_output = _run_macos_toolchain_command(["/usr/bin/xcodebuild", "-version"])
    if xcode_output:
        # Output format: "Xcode 15.4\nBuild version 15F31d"
        lines = xcode_output.split("\n")
        if lines:
            info["Xcode Version"] = lines[0].replace("Xcode ", "").strip()
            if len(lines) > 1 and "Build version" in lines[1]:
                info["Xcode Build"] = lines[1].replace("Build version ", "").strip()

    # Get Metal SDK path (useful for debugging Metal issues)
    sdk_path = _run_macos_toolchain_command(
        ["/usr/bin/xcrun", "-sdk", "macosx", "--show-sdk-path"],
    )
    if sdk_path:
        info["SDK Path"] = sdk_path
        info["Metal SDK"] = Path(sdk_path).name

    metal_version = _first_toolchain_output_line(
        _run_macos_toolchain_command(["/usr/bin/xcrun", "metal", "--version"]),
    )
    if metal_version:
        info["Metal Compiler Version"] = metal_version

    metallib_version = _first_toolchain_output_line(
        _run_macos_toolchain_command(["/usr/bin/xcrun", "metallib", "--version"]),
    )
    if metallib_version:
        info["Metallib Linker Version"] = metallib_version

    clang_version = _first_toolchain_output_line(
        _run_macos_toolchain_command(["/usr/bin/xcrun", "clang", "--version"]),
    )
    if clang_version:
        info["Apple Clang Version"] = clang_version

    # Get Command Line Tools version if Xcode not available
    if "Xcode Version" not in info:
        clt_output = _run_macos_toolchain_command(
            ["/usr/bin/pkgutil", "--pkg-info", "com.apple.pkg.CLTools_Executables"],
        )
        if clt_output:
            for line in clt_output.split("\n"):
                if line.startswith("version:"):
                    info["CLTools Version"] = line.split(":", 1)[1].strip()
                    break

    return info


def _get_apple_silicon_info() -> dict[str, str]:
    """Get Apple Silicon GPU info from system_profiler.

    Returns dict with GPU cores and Metal support info. Safe to call on any
    architecture (returns empty dict on non-arm64).
    """
    info: dict[str, str] = {}
    if platform.machine() != "arm64":
        return info

    first = _first_system_profiler_entry(get_device_info(), "SPDisplaysDataType")
    if first is None:
        return info

    gpu_cores = first.get("sppci_cores")
    if gpu_cores is not None:
        info["GPU Cores"] = str(gpu_cores)

    metal_family = _mapping_first_text_value(first, "spdisplays_mtlgpufamilysupport")
    if metal_family is not None:
        info["Metal Support"] = metal_family.replace("spdisplays_metal", "Metal ")

    return info


def get_system_characteristics() -> dict[str, str]:
    """Gather system/hardware characteristics for inclusion in reports.

    Returns a dict with human-readable hardware info (OS, chip, RAM, cores, etc).
    Safe to call even if psutil or system_profiler unavailable.
    """
    info: dict[str, str] = {}

    try:
        # Basic platform info
        info["OS"] = f"{platform.system()} {platform.release()}"
        if platform.system() == "Darwin":
            info["macOS Version"] = platform.mac_ver()[0]
            info.update(_get_macos_toolchain_info())

        info["Python Version"] = sys.version.split()[0]
        info["Architecture"] = platform.machine()

        device_info = _get_mlx_device_info()

        # Get GPU/chip info with graceful fallbacks.
        _, profiler_gpu_name = get_system_info()
        chip_name = profiler_gpu_name
        if chip_name is None:
            chip_name = _get_macos_sysctl_value("machdep.cpu.brand_string")
        if chip_name is None:
            chip_name = device_info.get("device_name")
        if chip_name:
            info["GPU/Chip"] = chip_name

        device_name = device_info.get("device_name")
        if device_name:
            info["MLX Device"] = device_name
        gpu_architecture = device_info.get("architecture")
        if gpu_architecture:
            info["GPU Architecture"] = gpu_architecture

        # Get detailed Apple Silicon info
        info.update(_get_apple_silicon_info())

        total_memory_bytes = _get_total_memory_bytes()
        if total_memory_bytes is not None:
            info["RAM"] = f"{total_memory_bytes / (1024**3):.1f} GB"

        recommended_working_set_bytes = device_info.get("max_recommended_working_set_size")
        if recommended_working_set_bytes is not None:
            working_set_gb = recommended_working_set_bytes / (1024**3)
            info["Recommended Working Set"] = f"{fmt_num(working_set_gb)} GB"

        fused_attention = _probe_fused_attention()
        fused_attention_labels = {
            "ok": "Available",
            "unavailable": "Unavailable",
            "errored": "Error",
            "timed_out": "Timed out",
        }
        info["Fused Attention"] = fused_attention_labels[fused_attention["status"]]

        # Get CPU info if psutil available
        if psutil is not None:
            physical_cores = psutil.cpu_count(logical=False)
            if physical_cores:
                info["CPU Cores (Physical)"] = str(physical_cores)

            logical_cores = psutil.cpu_count(logical=True)
            if logical_cores:
                info["CPU Cores (Logical)"] = str(logical_cores)

        # Concise psutil memory/swap context facts (environmental evidence,
        # not proof of an MLX or model defect); degrade gracefully.
        info.update(_get_psutil_memory_facts())

        info.update(_get_mlx_backend_artifact_info())

    except (OSError, RuntimeError, ValueError) as err:
        logger.debug("Error gathering system characteristics: %s", err)

    return info


def _get_psutil_memory_facts() -> dict[str, str]:
    """Return available-memory and swap-use context facts when psutil exposes them."""
    facts: dict[str, str] = {}
    if psutil is None:
        return facts
    try:
        available = psutil.virtual_memory().available
        if type(available) is int and available > 0:
            facts["Available Memory (run start)"] = f"{available / (1024**3):.1f} GB"
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        logger.debug("psutil virtual_memory unavailable", exc_info=True)
    try:
        swap = psutil.swap_memory()
        if type(swap.total) is int and swap.total >= 0:
            facts["Swap Used (run start)"] = (
                f"{swap.used / (1024**3):.1f} GB of {swap.total / (1024**3):.1f} GB"
            )
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        logger.debug("psutil swap_memory unavailable", exc_info=True)
    return facts


def _probe_fused_attention() -> RuntimeProbeResult:
    """Report whether MLX exposes callable fused scaled-dot-product attention."""
    if mx is None:
        return RuntimeProbeResult(status="unavailable", detail="mlx not imported")
    try:
        fast = getattr(mx, "fast", None)
        attention = getattr(fast, "scaled_dot_product_attention", None)
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return RuntimeProbeResult(status="errored", detail=str(exc)[:120])
    if callable(attention):
        return RuntimeProbeResult(status="ok")
    return RuntimeProbeResult(status="unavailable")


def collect_runtime_fingerprint() -> dict[str, RuntimeProbeResult]:
    """Probe runtime capabilities once per run and record per-probe status.

    Each probe records ``ok``, ``unavailable``, ``errored``, or ``timed_out``
    (guardrail G2: never silently omit a probe).
    """
    probes: dict[str, RuntimeProbeResult] = {}

    # Metal GPU availability
    try:
        if mx is not None:
            mx.metal.is_available()
            probes["metal_gpu"] = RuntimeProbeResult(status="ok")
        else:
            probes["metal_gpu"] = RuntimeProbeResult(
                status="unavailable", detail="mlx not imported"
            )
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        probes["metal_gpu"] = RuntimeProbeResult(status="errored", detail=str(exc)[:120])

    # MLX framework version
    try:
        if mx is not None:
            probes["mlx_framework"] = RuntimeProbeResult(
                status="ok", detail=getattr(mx, "__version__", "unknown")
            )
        else:
            probes["mlx_framework"] = RuntimeProbeResult(status="unavailable")
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        probes["mlx_framework"] = RuntimeProbeResult(status="errored", detail=str(exc)[:120])

    # mlx-vlm importability was captured during module initialization.
    if "mlx-vlm" not in MISSING_DEPENDENCIES:
        probes["mlx_vlm"] = RuntimeProbeResult(status="ok")
    else:
        probes["mlx_vlm"] = RuntimeProbeResult(
            status="unavailable",
            detail=MISSING_DEPENDENCIES.get("mlx-vlm", "not imported"),
        )

    # GPU memory query
    try:
        if mx is not None and hasattr(mx, "get_active_memory"):
            active = mx.get_active_memory()
            probes["gpu_memory"] = RuntimeProbeResult(
                status="ok", detail=f"active={active / DECIMAL_GB:.2f}GB"
            )
        else:
            probes["gpu_memory"] = RuntimeProbeResult(status="unavailable")
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        probes["gpu_memory"] = RuntimeProbeResult(status="errored", detail=str(exc)[:120])

    probes["fused_attention"] = _probe_fused_attention()

    return probes


# =============================================================================
# SECTION: MODEL PROCESSING
# =============================================================================
def validate_inputs(
    image_path: PathLike,
    temperature: float = 0.0,
) -> None:
    """Validate input paths and parameters with comprehensive checks."""
    img_path: Path = Path(image_path)

    # Early validation for performance
    if not img_path.exists():
        msg = f"Image not found: {img_path}"
        raise FileNotFoundError(msg)
    if not img_path.is_file():
        msg = f"Not a file: {img_path}"
        raise ValueError(msg)

    # Check file extension (case-insensitive for robustness)
    if img_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        msg = f"Unsupported image format: {img_path.suffix}"
        raise ValueError(msg)

    validate_temperature(temp=temperature)


def validate_temperature(*, temp: float) -> None:
    """Validate temperature parameter is within acceptable range."""
    if temp < 0.0:
        msg: str = f"Temperature must be non-negative, got {temp}"
        raise ValueError(msg)
    if temp > MAX_REASONABLE_TEMPERATURE:
        logger.warning(
            "Temperature %.2f is unusually high (>%.1f). Output may be very random.",
            temp,
            MAX_REASONABLE_TEMPERATURE,
        )


def validate_sampling_params(
    *,  # Force all parameters to be keyword-only for clarity
    top_p: float,
    min_p: float,
    top_k: int,
    repetition_penalty: float | None,
) -> None:
    """Validate sampling parameters are within acceptable ranges."""
    if not 0.0 <= top_p <= 1.0:
        msg = f"top_p must be between 0.0 and 1.0, got {top_p}"
        raise ValueError(msg)

    if not 0.0 <= min_p <= 1.0:
        msg = f"min_p must be between 0.0 and 1.0, got {min_p}"
        raise ValueError(msg)

    if top_k < 0:
        msg = f"top_k must be >= 0, got {top_k}"
        raise ValueError(msg)

    if repetition_penalty is not None and repetition_penalty < 1.0:
        msg = f"repetition_penalty must be >= 1.0 if specified, got {repetition_penalty}"
        raise ValueError(msg)


def _validate_kv_bits_increments(name: str, bits: float) -> None:
    """Validate a KV bit-width is >= 1 in integer or .5 increments."""
    if bits < 1:
        msg = f"{name} must be >= 1 if specified, got {bits:g}"
        raise ValueError(msg)

    rounded_half = round(bits * 2) / 2
    if not math.isclose(bits, rounded_half, abs_tol=1e-6):
        msg = f"{name} must be an integer or .5 increment if specified, got {bits:g}"
        raise ValueError(msg)


def validate_kv_params(
    *,  # Force all parameters to be keyword-only for clarity
    max_kv_size: int | None,
    kv_bits: float | None,
    kv_quant_scheme: Literal["uniform", "turboquant"] = DEFAULT_KV_QUANT_SCHEME,
    kv_key_bits: float | None = None,
    kv_value_bits: float | None = None,
    kv_key_scheme: Literal["uniform", "turboquant"] | None = None,
    kv_value_scheme: Literal["uniform", "turboquant"] | None = None,
) -> None:
    """Validate KV cache parameters are within acceptable ranges."""
    if max_kv_size is not None and max_kv_size <= 0:
        msg = f"max_kv_size must be > 0 if specified, got {max_kv_size}"
        raise ValueError(msg)

    if kv_bits is None:
        # Upstream from_legacy() silently ignores per-tensor overrides when
        # kv_bits is unset, so fail fast instead of running a no-op config.
        set_overrides = [
            name
            for name, value in (
                ("kv_key_bits", kv_key_bits),
                ("kv_value_bits", kv_value_bits),
                ("kv_key_scheme", kv_key_scheme),
                ("kv_value_scheme", kv_value_scheme),
            )
            if value is not None
        ]
        if set_overrides:
            msg = f"per-tensor KV overrides require kv_bits: {', '.join(set_overrides)}"
            raise ValueError(msg)
        return

    _validate_kv_bits_increments("kv_bits", kv_bits)

    is_integer_bits = math.isclose(kv_bits, round(kv_bits), abs_tol=1e-6)
    if kv_quant_scheme == "uniform" and is_integer_bits:
        int_bits = round(kv_bits)
        if int_bits not in UNIFORM_KV_BITS:
            msg = (
                f"uniform kv_bits must be one of 2, 3, 4, 5, 6, or 8 if specified, got {kv_bits:g}"
            )
            raise ValueError(msg)

    # Fractional kv_bits switches the upstream base scheme to TurboQuant;
    # per-tensor schemes default to that base when not set explicitly.
    base_scheme = (
        "turboquant" if kv_quant_scheme == "turboquant" or not is_integer_bits else "uniform"
    )
    for name, bits, scheme in (
        ("kv_key_bits", kv_key_bits, kv_key_scheme),
        ("kv_value_bits", kv_value_bits, kv_value_scheme),
    ):
        if bits is None:
            continue
        _validate_kv_bits_increments(name, bits)
        effective_scheme = scheme if scheme is not None else base_scheme
        if effective_scheme == "uniform" and (
            not math.isclose(bits, round(bits), abs_tol=1e-6) or round(bits) not in UNIFORM_KV_BITS
        ):
            msg = f"uniform {name} must be one of 2, 3, 4, 5, 6, or 8 if specified, got {bits:g}"
            raise ValueError(msg)


_RESERVED_PROCESSOR_KWARG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "audio",
        "eos_tokens",
        "frequency_context_size",
        "frequency_penalty",
        "image",
        "kv_bits",
        "kv_group_size",
        "kv_key_bits",
        "kv_key_scheme",
        "kv_quant_scheme",
        "kv_value_bits",
        "kv_value_scheme",
        "logit_bias",
        "max_kv_size",
        "max_tokens",
        "min_p",
        "prefill_step_size",
        "presence_context_size",
        "presence_penalty",
        "processor",
        "prompt",
        "quantized_kv_start",
        "repetition_context_size",
        "repetition_penalty",
        "resize_shape",
        "seed",
        "skip_special_tokens",
        "enable_thinking",
        "thinking_budget",
        "thinking_end_token",
        "thinking_start_token",
        "temperature",
        "top_k",
        "top_p",
        "verbose",
    },
)


def _parse_processor_kwargs_arg(value: str) -> dict[str, JsonLike]:
    """Parse ``--processor-kwargs`` as a JSON object."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        msg = f"processor_kwargs must be valid JSON: {exc.msg}"
        raise argparse.ArgumentTypeError(msg) from exc

    if not isinstance(parsed, dict):
        msg = "processor_kwargs must be a JSON object"
        raise argparse.ArgumentTypeError(msg)
    if not all(isinstance(key, str) for key in parsed):
        msg = "processor_kwargs keys must all be strings"
        raise argparse.ArgumentTypeError(msg)
    return cast("dict[str, JsonLike]", parsed)


def _parse_logit_bias_arg(value: str) -> LogitBiasDict:
    """Parse ``--logit-bias`` as an OpenAI-style token-id to bias JSON object."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        msg = f"logit_bias must be valid JSON: {exc.msg}"
        raise argparse.ArgumentTypeError(msg) from exc

    if not isinstance(parsed, dict):
        msg = "logit_bias must be a JSON object"
        raise argparse.ArgumentTypeError(msg)

    logit_bias: LogitBiasDict = {}
    for raw_key, raw_value in parsed.items():
        try:
            token_id = int(raw_key)
        except (TypeError, ValueError) as exc:
            msg = f"logit_bias keys must be integer token ids, got {raw_key!r}"
            raise argparse.ArgumentTypeError(msg) from exc
        if not isinstance(raw_value, int | float) or isinstance(raw_value, bool):
            msg = f"logit_bias values must be numeric, got {raw_value!r}"
            raise argparse.ArgumentTypeError(msg)
        logit_bias[token_id] = float(raw_value)
    return logit_bias


def _normalize_resize_shape(raw_shape: Sequence[int] | None) -> tuple[int, int] | None:
    """Normalize CLI resize shape values to a ``(height, width)`` tuple."""
    if raw_shape is None:
        return None
    if len(raw_shape) not in (1, 2):
        msg = f"resize_shape must contain 1 or 2 integers, got {len(raw_shape)}"
        raise ValueError(msg)
    if any(size <= 0 for size in raw_shape):
        msg = f"resize_shape values must be > 0, got {list(raw_shape)}"
        raise ValueError(msg)
    if len(raw_shape) == 1:
        return (raw_shape[0], raw_shape[0])
    return (raw_shape[0], raw_shape[1])


def _decode_cli_eos_tokens(raw_tokens: Sequence[str] | None) -> tuple[str, ...] | None:
    """Decode CLI EOS tokens, supporting escaped characters like upstream mlx-vlm."""
    if raw_tokens is None:
        return None

    decoded_tokens: list[str] = []
    for token in raw_tokens:
        try:
            decoded_tokens.append(codecs.decode(token, "unicode_escape"))
        except (UnicodeDecodeError, UnicodeError):
            decoded_tokens.append(token)
    return tuple(decoded_tokens)


def _validate_processor_kwargs(
    processor_kwargs: Mapping[str, JsonLike] | None,
) -> dict[str, JsonLike] | None:
    """Reject processor kwargs that would collide with dedicated CLI flags."""
    if processor_kwargs is None:
        return None

    overlap = sorted(set(processor_kwargs).intersection(_RESERVED_PROCESSOR_KWARG_KEYS))
    if overlap:
        overlap_str = ", ".join(overlap)
        msg = f"processor_kwargs cannot override dedicated CLI arguments: {overlap_str}"
        raise ValueError(msg)
    return dict(processor_kwargs)


def _validate_server_shared_request_params(args: argparse.Namespace) -> None:
    """Validate direct-generation flags shared with the MLX-VLM server request API."""
    presence_context_size = getattr(
        args,
        "presence_context_size",
        DEFAULT_PENALTY_CONTEXT_SIZE,
    )
    frequency_context_size = getattr(
        args,
        "frequency_context_size",
        DEFAULT_PENALTY_CONTEXT_SIZE,
    )
    if presence_context_size is not None and presence_context_size <= 0:
        msg = f"presence_context_size must be > 0 if specified, got {presence_context_size}"
        raise ValueError(msg)
    if frequency_context_size is not None and frequency_context_size <= 0:
        msg = f"frequency_context_size must be > 0 if specified, got {frequency_context_size}"
        raise ValueError(msg)


def _validate_thinking_params(args: argparse.Namespace) -> None:
    """Validate opt-in thinking-mode arguments."""
    enable_thinking = bool(getattr(args, "enable_thinking", False))
    thinking_budget = getattr(args, "thinking_budget", None)
    thinking_start_token = getattr(args, "thinking_start_token", None)
    thinking_end_token = getattr(args, "thinking_end_token", DEFAULT_THINKING_END_MARKER)
    thinking_requested = bool(
        enable_thinking or thinking_budget is not None or thinking_start_token is not None,
    )

    if thinking_budget is not None and thinking_budget <= 0:
        msg = f"thinking_budget must be > 0 if specified, got {thinking_budget}"
        raise ValueError(msg)

    if thinking_requested and not enable_thinking:
        msg = "thinking_budget and thinking token flags require --enable-thinking"
        raise ValueError(msg)

    if enable_thinking and not thinking_end_token:
        msg = "thinking_end_token must be non-empty when thinking mode is enabled"
        raise ValueError(msg)


def validate_cli_arguments(args: argparse.Namespace) -> None:
    """Validate all CLI arguments before processing begins.

    This performs early validation to fail fast on invalid inputs
    before any expensive operations (model loading, image processing, etc.).
    """
    # Validate temperature
    validate_temperature(temp=args.temperature)

    # Validate max_tokens (None means the evaluation lane supplies the default later)
    if args.max_tokens is not None and args.max_tokens <= 0:
        msg = f"max_tokens must be > 0, got {args.max_tokens}"
        raise ValueError(msg)

    # Validate sampling parameters
    validate_sampling_params(
        top_p=args.top_p,
        min_p=args.min_p,
        top_k=args.top_k,
        repetition_penalty=args.repetition_penalty,
    )

    # Validate KV cache parameters
    validate_kv_params(
        max_kv_size=args.max_kv_size,
        kv_bits=args.kv_bits,
        kv_quant_scheme=args.kv_quant_scheme,
        kv_key_bits=getattr(args, "kv_key_bits", None),
        kv_value_bits=getattr(args, "kv_value_bits", None),
        kv_key_scheme=getattr(args, "kv_key_scheme", None),
        kv_value_scheme=getattr(args, "kv_value_scheme", None),
    )

    args.resize_shape = _normalize_resize_shape(getattr(args, "resize_shape", None))
    args.eos_tokens = _decode_cli_eos_tokens(getattr(args, "eos_tokens", None))
    args.processor_kwargs = _validate_processor_kwargs(
        getattr(args, "processor_kwargs", None),
    )
    _validate_server_shared_request_params(args)
    _validate_thinking_params(args)


def _build_generate_extra_kwargs(params: ProcessImageParams) -> GenerateKwargs:
    """Collect optional generate kwargs for benchmark runs."""
    extra_kwargs: GenerateKwargs = {}
    if params.min_p > 0.0:
        extra_kwargs["min_p"] = params.min_p
    if params.top_k > 0:
        extra_kwargs["top_k"] = params.top_k
    if params.prefill_step_size is not None:
        extra_kwargs["prefill_step_size"] = params.prefill_step_size
    if params.resize_shape is not None:
        extra_kwargs["resize_shape"] = params.resize_shape
    if params.eos_tokens is not None:
        extra_kwargs["eos_tokens"] = list(params.eos_tokens)
    # Per-tensor KV fields are merged through a cast because PyPI mlx-vlm
    # releases before per-tensor KV quantization lack these GenerateKwargs
    # keys, and CI type-checks against release stubs.
    per_tensor_kv_kwargs: dict[str, float | str] = {}
    if params.kv_key_bits is not None:
        per_tensor_kv_kwargs["kv_key_bits"] = params.kv_key_bits
    if params.kv_value_bits is not None:
        per_tensor_kv_kwargs["kv_value_bits"] = params.kv_value_bits
    if params.kv_key_scheme is not None:
        per_tensor_kv_kwargs["kv_key_scheme"] = params.kv_key_scheme
    if params.kv_value_scheme is not None:
        per_tensor_kv_kwargs["kv_value_scheme"] = params.kv_value_scheme
    extra_kwargs.update(cast("GenerateKwargs", per_tensor_kv_kwargs))
    if params.skip_special_tokens:
        extra_kwargs["skip_special_tokens"] = True
    if params.enable_thinking:
        extra_kwargs["enable_thinking"] = True
        extra_kwargs["thinking_end_token"] = params.thinking_end_token
        if params.thinking_budget is not None:
            extra_kwargs["thinking_budget"] = params.thinking_budget
        if params.thinking_start_token is not None:
            extra_kwargs["thinking_start_token"] = params.thinking_start_token
    return extra_kwargs


def _prompt_opens_thinking_block(
    formatted_prompt: str,
    pair: ThinkingDelimiterPair,
) -> bool:
    r"""True when the rendered prompt terminates with an open thinking marker.

    A chat template that opens a thinking block for the model to continue ends
    the prompt with the start marker (optionally followed by whitespace) —
    e.g. ``...assistant\n<think>``. A terminal check rejects closed blocks
    (``<think></think>`` no-think stubs), few-shot examples, and literal
    marker mentions in user text, all of which the model is not meant to
    continue.
    """
    return formatted_prompt.rstrip().endswith(pair.start)


def _auto_thinking_budget_kwargs(
    params: ProcessImageParams,
    formatted_prompt: str,
) -> GenerateKwargs:
    """Bound template-opened thinking blocks when no explicit flags are set.

    Upstream's ``ThinkingBudgetCriteria`` only engages when ``enable_thinking``
    is passed AND the rendered prompt already contains the thinking start
    token, so this affects only models whose chat template itself opens a
    thinking block (final marker unmatched, not merely mentioned or closed).
    Chat-template kwargs are untouched: hybrid models keep their default
    non-thinking behaviour, and any explicit thinking flag or
    ``--thinking-mode`` hands full control back to the user.
    """
    empty = cast("GenerateKwargs", {})
    if (
        not params.auto_thinking_budget
        or params.enable_thinking
        or params.thinking_mode is not None
    ):
        return empty
    budget = params.max_tokens - AUTO_THINKING_ANSWER_RESERVE_TOKENS
    if budget < AUTO_THINKING_BUDGET_MIN_TOKENS:
        return empty
    for pair in THINKING_TRACE_DELIMITERS:
        if not pair.auto_budget_eligible:
            continue
        if _prompt_opens_thinking_block(formatted_prompt, pair):
            return cast(
                "GenerateKwargs",
                {
                    "enable_thinking": True,
                    "thinking_budget": budget,
                    "thinking_start_token": pair.start,
                    "thinking_end_token": pair.end,
                },
            )
    return empty


def _apply_auto_thinking_budget(
    params: ProcessImageParams,
    formatted_prompt: str,
    generate_kwargs: GenerateKwargs,
) -> bool:
    """Inject the automatic thinking budget when the template opens thinking.

    Returns True when a budget was applied automatically.
    """
    auto_kwargs = _auto_thinking_budget_kwargs(params, formatted_prompt)
    if not auto_kwargs:
        return False
    generate_kwargs.update(auto_kwargs)
    logger.info(
        "Auto thinking budget: %s tokens for %s (template opens a thinking block; "
        "disable with --no-auto-thinking-budget)",
        auto_kwargs.get("thinking_budget"),
        params.model_identifier,
    )
    return True


def _build_generate_kwargs(
    params: ProcessImageParams,
    extra_kwargs: GenerateKwargs,
) -> GenerateKwargs:
    """Build the complete typed keyword contract for one upstream generate call."""
    generate_kwargs = extra_kwargs.copy()
    generate_kwargs["verbose"] = params.verbose
    generate_kwargs["temperature"] = params.temperature
    generate_kwargs["top_p"] = params.top_p
    generate_kwargs["repetition_penalty"] = params.repetition_penalty
    generate_kwargs["repetition_context_size"] = params.repetition_context_size
    generate_kwargs["seed"] = params.seed
    generate_kwargs["presence_penalty"] = params.presence_penalty
    generate_kwargs["presence_context_size"] = params.presence_context_size
    generate_kwargs["frequency_penalty"] = params.frequency_penalty
    generate_kwargs["frequency_context_size"] = params.frequency_context_size
    generate_kwargs["logit_bias"] = params.logit_bias
    generate_kwargs["max_kv_size"] = params.max_kv_size
    generate_kwargs["kv_bits"] = params.kv_bits
    generate_kwargs["kv_quant_scheme"] = params.kv_quant_scheme
    generate_kwargs["kv_group_size"] = params.kv_group_size
    generate_kwargs["quantized_kv_start"] = params.quantized_kv_start
    generate_kwargs["max_tokens"] = params.max_tokens
    return generate_kwargs


def _is_generation_processor(
    processor: object,
) -> TypeIs[ProcessorLike | PreTrainedTokenizer]:
    """Return whether a processor matches either upstream generation branch.

    ``TypeIs`` (PEP 742) rather than ``TypeGuard``: the positive branch is an
    intersection with the declared type, so a ``ProcessorMixin`` checked here
    is still a ``ProcessorMixin`` after the ``if``/``else`` rejoin instead of
    widening to the union (which pyright reports at the later call sites).
    """
    return hasattr(processor, "detokenizer") and (
        hasattr(processor, "tokenizer") or _has_text_decoder_api(processor)
    )


def _build_chat_template_kwargs(params: ProcessImageParams) -> ChatTemplateKwargs:
    """Collect optional chat-template kwargs for benchmark runs.

    Mirrors upstream ``mlx_vlm.generate`` semantics: ``thinking_mode`` applies
    whenever set (templates that support it), independent of enable_thinking.
    """
    template_kwargs: ChatTemplateKwargs = {}
    if params.thinking_mode is not None:
        template_kwargs["thinking_mode"] = params.thinking_mode
    if not params.enable_thinking:
        return template_kwargs

    template_kwargs["enable_thinking"] = True
    template_kwargs["thinking_end_token"] = params.thinking_end_token
    if params.thinking_budget is not None:
        template_kwargs["thinking_budget"] = params.thinking_budget
    if params.thinking_start_token is not None:
        template_kwargs["thinking_start_token"] = params.thinking_start_token
    return template_kwargs


_IMAGE_PLACEHOLDER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"<\|?image(?:_\d+)?\|?>", re.IGNORECASE),
    re.compile(r"<start_of_image>", re.IGNORECASE),
    re.compile(r"<image_soft_token>", re.IGNORECASE),
)
_MAX_PROMPT_DIAGNOSTIC_ITEMS: Final[int] = 32
_RENDERED_PROMPT_PREVIEW_CHARS: Final[int] = 800


def _prompt_diag_json_value(value: object) -> JsonLike:
    """Convert prompt-diagnostic values into bounded JSON-compatible data."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _prompt_diag_json_value(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_prompt_diag_json_value(item) for item in value]
    return str(value)


def _qualified_class_name(value: object | None) -> str | None:
    """Return a stable module-qualified class name for diagnostics."""
    if value is None:
        return None
    cls = value.__class__
    module = getattr(cls, "__module__", "")
    qualname = getattr(cls, "__qualname__", cls.__name__)
    return f"{module}.{qualname}" if module else qualname


def _count_image_placeholders(rendered_prompt: str) -> int:
    """Count common multimodal image placeholder spellings in rendered templates."""
    return sum(len(pattern.findall(rendered_prompt)) for pattern in _IMAGE_PLACEHOLDER_PATTERNS)


def _bounded_json_sequence(value: object) -> tuple[JsonLike, ...]:
    """Return a bounded tuple of JSON-compatible diagnostic values."""
    if value is None or isinstance(value, str | bytes | bytearray):
        return ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(_prompt_diag_json_value(item) for item in value[:_MAX_PROMPT_DIAGNOSTIC_ITEMS])


def _bounded_string_sequence(value: object) -> tuple[str, ...]:
    """Return a bounded tuple of stringified diagnostic values."""
    if value is None or isinstance(value, str | bytes | bytearray):
        return ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(item) for item in value[:_MAX_PROMPT_DIAGNOSTIC_ITEMS])


_CONDITIONAL_GENERATION_CONTEXTS: Final[dict[str, str]] = {
    "repetition_context_size": "repetition_penalty",
    "presence_context_size": "presence_penalty",
    "frequency_context_size": "frequency_penalty",
}
_CONDITIONAL_KV_GENERATION_SETTINGS: Final[frozenset[str]] = frozenset(
    {
        "kv_quant_scheme",
        "kv_group_size",
        "quantized_kv_start",
    }
)


def _generation_kwargs_for_prompt_diagnostics(
    *,
    generate_kwargs: Mapping[str, object],
    processor_passthrough_kwargs: Mapping[str, object],
) -> dict[str, JsonLike]:
    """Return publication-relevant forwarded generation kwargs in JSON-safe form."""
    kwargs: dict[str, object] = {}
    for key, value in generate_kwargs.items():
        if key == "verbose" or value is None:
            continue
        required_setting = _CONDITIONAL_GENERATION_CONTEXTS.get(key)
        if required_setting is not None and generate_kwargs.get(required_setting) is None:
            continue
        if key in _CONDITIONAL_KV_GENERATION_SETTINGS and generate_kwargs.get("kv_bits") is None:
            continue
        kwargs[key] = value
    if processor_passthrough_kwargs:
        kwargs["processor_kwargs"] = dict(processor_passthrough_kwargs)
    return {key: _prompt_diag_json_value(value) for key, value in sorted(kwargs.items())}


def _count_rendered_prompt_tokens(
    tokenizer: object,
    formatted_prompt: str,
    model_type: str | None,
    processor: object,
) -> int | None:
    """Return the exact token count of the rendered prompt, or None if unavailable.

    Mirrors upstream's ``should_add_special_tokens`` so the count matches what
    ``mlx_vlm.generate`` tokenizes (the rendered chat template plus any
    tokenizer-added markers), using duck-typed ``encode`` so every model family
    goes through the same path. Image placeholders count as rendered — their
    expansion is what ``prompt_tokens - this`` isolates. Best effort: never
    raises.
    """
    encode = getattr(tokenizer, "encode", None)
    if not callable(encode):
        return None
    add_special_tokens = False
    if model_type is not None:
        should_add = cast(
            "Callable[[str, object], object] | None",
            _optional_mlx_vlm_utils_attribute("should_add_special_tokens"),
        )
        if callable(should_add):
            try:
                add_special_tokens = bool(should_add(model_type, processor))
            except (AttributeError, TypeError, ValueError):
                add_special_tokens = False
    try:
        encoded = encode(formatted_prompt, add_special_tokens=add_special_tokens)
    except TypeError:
        try:
            encoded = encode(formatted_prompt)
        except (AttributeError, TypeError, ValueError, RuntimeError, OSError):
            return None
    except (AttributeError, ValueError, RuntimeError, OSError):
        return None
    ids: object = getattr(encoded, "ids", encoded)
    if not isinstance(ids, Sized):
        return None
    count = len(ids)
    return count if count >= 0 else None


def _optional_mlx_vlm_utils_attribute(name: str) -> object | None:
    """Return an attribute from ``mlx_vlm.utils`` when importable, else None."""
    try:
        utils_module = import_module("mlx_vlm.utils")
    except (ImportError, OSError, RuntimeError, ValueError):
        return None
    return getattr(utils_module, name, None)


def _build_prompt_diagnostics(
    *,
    params: ProcessImageParams,
    processor: ProcessorMixin,
    config: PreTrainedConfig | Mapping[str, object] | None,
    formatted_prompt: str,
    generate_kwargs: GenerateKwargs,
    processor_passthrough_kwargs: Mapping[str, object],
    thinking_budget_source: Literal["auto", "explicit"] | None = None,
    snapshot_notes: tuple[str, ...] = (),
) -> PromptDiagnostics:
    """Collect bounded prompt/template diagnostics for retained machine reports."""
    tokenizer = _extract_processor_tokenizer(processor)
    model_type_raw = _get_config_value(config, "model_type")
    model_type = str(model_type_raw) if model_type_raw is not None else None
    eos_token = getattr(tokenizer, "eos_token", None)
    processed_height = params.resize_shape[0] if params.resize_shape is not None else None
    processed_width = params.resize_shape[1] if params.resize_shape is not None else None
    return PromptDiagnostics(
        model_type=model_type,
        processor_class=_qualified_class_name(processor),
        tokenizer_class=_qualified_class_name(tokenizer),
        rendered_prompt_hash_sha256=_sha256_text(formatted_prompt),
        rendered_prompt_preview=_build_prompt_preview(
            formatted_prompt,
            max_chars=_RENDERED_PROMPT_PREVIEW_CHARS,
        ),
        rendered_prompt=formatted_prompt,
        rendered_prompt_chars=len(formatted_prompt),
        image_placeholder_count=_count_image_placeholders(formatted_prompt),
        rendered_prompt_token_count=_count_rendered_prompt_tokens(
            tokenizer, formatted_prompt, model_type, processor
        ),
        processed_image_width=processed_width,
        processed_image_height=processed_height,
        eos_token_id=_prompt_diag_json_value(getattr(tokenizer, "eos_token_id", None)),
        eos_token=str(eos_token) if eos_token is not None else None,
        special_token_ids=_bounded_json_sequence(getattr(tokenizer, "all_special_ids", None)),
        special_tokens=_bounded_string_sequence(getattr(tokenizer, "all_special_tokens", None)),
        thinking_budget_source=thinking_budget_source,
        template_thinking_markers=_template_declares_thinking(
            _resolve_model_snapshot_path(params.model_identifier, params.revision)
        ),
        snapshot_notes=snapshot_notes,
        generate_kwargs=_generation_kwargs_for_prompt_diagnostics(
            generate_kwargs=generate_kwargs,
            processor_passthrough_kwargs=processor_passthrough_kwargs,
        ),
    )


def _prompt_diagnostics_to_json(diagnostics: PromptDiagnostics | None) -> dict[str, JsonLike]:
    """Serialize prompt diagnostics as optional JSONL/repro metadata."""
    if diagnostics is None:
        return {}
    payload: dict[str, JsonLike] = {}
    for key in (
        "model_type",
        "processor_class",
        "tokenizer_class",
        "rendered_prompt_hash_sha256",
        "rendered_prompt_preview",
        "rendered_prompt",
        "rendered_prompt_chars",
        "image_placeholder_count",
        "rendered_prompt_token_count",
        "processed_image_width",
        "processed_image_height",
        "image_patch_count",
        "eos_token_id",
        "eos_token",
        "thinking_budget_source",
        "template_thinking_markers",
    ):
        value = getattr(diagnostics, key)
        if value is not None:
            if key == "rendered_prompt" and isinstance(value, str):
                value = _home_relative_report_text(value)
            payload[key] = _prompt_diag_json_value(value)
    if diagnostics.special_token_ids:
        payload["special_token_ids"] = list(diagnostics.special_token_ids)
    if diagnostics.special_tokens:
        payload["special_tokens"] = [
            _prompt_diag_json_value(item) for item in diagnostics.special_tokens
        ]
    if diagnostics.generate_kwargs:
        payload["generate_kwargs"] = dict(diagnostics.generate_kwargs)
    if diagnostics.snapshot_notes:
        payload["snapshot_notes"] = [
            _prompt_diag_json_value(note) for note in diagnostics.snapshot_notes
        ]
    return payload


_IMAGE_VALIDATION_CACHE: dict[str, tuple[int, int] | None] = {}


def _image_validation_cache_key(image_path: str | Path) -> tuple[str, tuple[int, int] | None]:
    """Return the cache identity and change-detection stamp for an image input."""
    try:
        stat_result = Path(image_path).stat()
    except OSError:
        # URLs and unreadable paths carry no stamp; a same-run repeat is enough.
        return str(image_path), None
    return str(image_path), (stat_result.st_size, stat_result.st_mtime_ns)


def validate_image_accessible(*, image_path: str | Path) -> None:
    """Validate image file is accessible and supported.

    Uses mlx_vlm's load_image() which supports both local file paths and URLs.
    This enables --image https://... usage following mlx-vlm best practices.
    A multi-model run validates the same input once: successful validations are
    cached for the process lifetime and revalidated if the file's size or
    mtime changes. Failures are never cached.
    """
    cache_name, cache_stamp = _image_validation_cache_key(image_path)
    if cache_name in _IMAGE_VALIDATION_CACHE and _IMAGE_VALIDATION_CACHE[cache_name] == cache_stamp:
        return
    try:
        with TimeoutManager(seconds=IMAGE_OPEN_TIMEOUT):
            # load_image() from mlx_vlm.utils handles both file paths and URLs
            # Returns PIL.Image.Image, verifying the image is accessible and valid
            # Convert Path to str since load_image expects str
            _ = load_image(str(image_path))
    except RuntimeError as err:
        if str(err) != ERROR_MLX_VLM_MISSING:
            msg = f"Error accessing image {image_path}: {err}"
            raise OSError(msg) from err

        # mlx-vlm is unavailable: use Pillow-only validation for local files so
        # direct function callers and unit tests can still validate image inputs.
        try:
            with TimeoutManager(seconds=IMAGE_OPEN_TIMEOUT), Image.open(image_path) as img:
                img.verify()
        except TimeoutError as timeout_err:
            msg = f"Timeout while reading image: {image_path}"
            raise OSError(msg) from timeout_err
        except UnidentifiedImageError as image_err:
            msg = f"File is not a recognized image format: {image_path}"
            raise ValueError(msg) from image_err
        except (OSError, ValueError) as image_err:
            msg = f"Error accessing image {image_path}: {image_err}"
            raise OSError(msg) from image_err
    except TimeoutError as err:
        msg = f"Timeout while reading image: {image_path}"
        raise OSError(msg) from err
    except UnidentifiedImageError as err:
        msg = f"File is not a recognized image format: {image_path}"
        raise ValueError(msg) from err
    except (OSError, ValueError) as err:
        msg = f"Error accessing image {image_path}: {err}"
        raise OSError(msg) from err
    _IMAGE_VALIDATION_CACHE[cache_name] = cache_stamp


@dataclass
class HFCacheScanState:
    """Mutable cache state for Hugging Face cache scans within one process."""

    attempted: bool = False
    info: HFCacheInfo | None = None
    error: OSError | ValueError | HFValidationError | None = None
    # Classified eligibility (layout + capability + arch pre-check) memoised
    # per scan: classification reads config.json per repo, and callers such
    # as the per-model arch pre-check would otherwise recompute it O(n²).
    # Keyed on the identity of the HFCacheInfo it was computed from, so a
    # refresh or a substituted cache info invalidates it automatically.
    eligibility: tuple[CachedModelEligibility, ...] | None = None
    eligibility_source_id: int | None = None


type ImageCapabilityVerdict = Literal["yes", "no", "unknown"]
type ModelPurposeClass = Literal[
    "image_to_text",
    "text_only",
    "embedding",
    "reranker",
    "speculative_drafter",
    "image_or_video_generation",
    "audio_or_other_generation",
    "image_understanding_non_generative",
    "unknown",
]


@dataclass(frozen=True)
class ImageCapability:
    """Evidence-backed classification of whether a cached repo fits this benchmark.

    ``verdict`` is tri-state for the single-image description benchmark:
    ``yes`` (positive evidence the model consumes image input and produces
    text), ``no`` (positive evidence it is a different model kind), or
    ``unknown`` (insufficient or contradictory evidence). Default discovery
    runs ``yes`` and ``unknown`` and skips only ``no``, so an unfamiliar new
    VLM is tried rather than silently excluded. ``evidence`` names the config
    keys/values that drove the decision so the skip reason is reproducible.
    """

    verdict: ImageCapabilityVerdict
    purpose: ModelPurposeClass
    evidence: tuple[str, ...] = ()

    @property
    def skip_reason(self) -> str | None:
        """Human-readable default-discovery exclusion reason, if excluded."""
        if self.verdict != "no":
            return None
        label = _MODEL_PURPOSE_LABELS[self.purpose]
        detail = f" ({'; '.join(self.evidence)})" if self.evidence else ""
        return f"model purpose: {label}{detail}"


_MODEL_PURPOSE_LABELS: Final[dict[ModelPurposeClass, str]] = {
    "image_to_text": "image-to-text generation",
    "text_only": "text-only generation",
    "embedding": "embedding model",
    "reranker": "sequence-classifier reranker",
    "speculative_drafter": "speculative drafter",
    "image_or_video_generation": "image/video generation pipeline, not image-to-text generation",
    "audio_or_other_generation": "audio-only or other non-image generation",
    "image_understanding_non_generative": (
        "image-consuming but non-text-generating model (classification, detection, "
        "segmentation, or multimodal embedding)"
    ),
    "unknown": "unknown",
}


@dataclass(frozen=True)
class CachedModelEligibility:
    """Auto-discovery eligibility for one cached Hugging Face repository.

    Two independent layers: ``supported`` is the mlx-vlm server-style cache
    *layout* test (files present), while ``capability`` is whether the repo
    appears to be an image-consuming text generator — the benchmark's actual
    requirement. ``selected`` combines them for default discovery.
    """

    repo_id: str
    supported: bool
    reasons: tuple[str, ...] = ()
    # Architecture pre-check (upstream --check-arch tier): config.json
    # model_type versus installed mlx_vlm/models packages. ``None`` means
    # indeterminate — never a claim that generation works.
    model_type: str | None = None
    resolved_model_type: str | None = None
    arch_supported: bool | None = None
    capability: ImageCapability = dataclass_field(
        default_factory=lambda: ImageCapability(
            verdict="unknown",
            purpose="unknown",
            evidence=("capability not classified",),
        )
    )
    # Whether the chat template declares thinking markers (None: no template
    # found). A neutral discovery fact — self-opening thinkers declare markers
    # without pre-opening a block, which render-time checks cannot see.
    thinking_template: bool | None = None

    @property
    def selected(self) -> bool:
        """True when default discovery should run this repo."""
        return self.supported and self.capability.verdict != "no"

    @property
    def skip_reasons(self) -> tuple[str, ...]:
        """Every concrete reason default discovery omits this repo."""
        reasons = tuple(f"cache layout: {reason}" for reason in self.reasons)
        capability_reason = self.capability.skip_reason
        if capability_reason is not None:
            reasons = (*reasons, capability_reason)
        return reasons


_HF_CACHE_SCAN_STATE = HFCacheScanState()


def _get_hf_cache_info_cached(*, refresh: bool = False) -> HFCacheInfo:
    """Return cached HF cache info for this run, with optional refresh."""
    state = _HF_CACHE_SCAN_STATE

    if refresh:
        state.attempted = False
        state.info = None
        state.error = None
        state.eligibility = None
        state.eligibility_source_id = None

    if state.attempted:
        if state.info is not None:
            return state.info
        cached_error = state.error
        if cached_error is None:
            msg = "Hugging Face cache scan previously failed with unknown error."
            raise OSError(msg)
        raise cached_error

    try:
        cache_info = scan_cache_dir()
    except (HFValidationError, FileNotFoundError, OSError, ValueError) as err:
        state.attempted = True
        state.info = None
        state.error = err
        raise

    state.attempted = True
    state.info = cache_info
    state.error = None
    return cache_info


def _check_hf_cache_integrity(model_identifier: str) -> None:
    """Check HuggingFace cache integrity for a model and log diagnostics.

    When a model fails to load, this helps distinguish between:
    - Code bugs (wrong parameters, incompatible model)
    - Environment bugs (corrupted cache, incomplete download)

    Args:
        model_identifier: HuggingFace model identifier
            (e.g., "mlx-community/Qwen2-VL-2B-Instruct-4bit")
    """
    min_cache_size_mb = 1  # Less than 1MB is suspicious for any model
    try:
        cache_info = _get_hf_cache_info_cached()
        encoded_repo_name = "models--" + model_identifier.replace("/", "--")
        matching_warnings = [
            warning
            for warning in cache_info.warnings
            if encoded_repo_name
            in {
                component.strip("'\"()[]{}:,. ")
                for component in str(warning).replace("\\", "/").split("/")
            }
        ]
        for cache_warning in matching_warnings:
            logger.warning(
                "⚠\ufe0f  Cache Warning: Hugging Face reported corruption for %s: %s",
                model_identifier,
                cache_warning,
            )

        # Find the specific repo in cache
        repo_found = False
        for repo in cache_info.repos:
            if model_identifier == repo.repo_id:
                repo_found = True
                logger.debug(
                    "HF Cache Info for %s: size=%s MB, files=%d",
                    repo.repo_id,
                    f"{repo.size_on_disk / (1024**2):.1f}",
                    repo.nb_files,
                )
                # Check for missing or corrupt files
                if repo.nb_files == 0:
                    logger.warning(
                        "⚠\ufe0f  Cache Warning: Model %s has 0 files "
                        "(incomplete download or corruption)",
                        model_identifier,
                    )
                elif repo.size_on_disk < min_cache_size_mb * (1024**2):
                    logger.warning(
                        "⚠\ufe0f  Cache Warning: Model %s cache is suspiciously small (%s MB)",
                        model_identifier,
                        f"{repo.size_on_disk / (1024**2):.1f}",
                    )
                break

        if not repo_found and not matching_warnings:
            logger.debug(
                "Model %s not found in HF cache (may need to download)",
                model_identifier,
            )
    except (OSError, ValueError, HFValidationError) as cache_err:
        logger.debug("Could not check HF cache integrity: %s", cache_err)


_FAILURE_PHASE_ATTR: Final[str] = "_check_models_failure_phase"
_PROMPT_DIAGNOSTICS_ATTR: Final[str] = "_check_models_prompt_diagnostics"

_STAGE_CODE_MAP: Final[dict[str, str]] = {
    "OOM": "OOM",
    "Timeout": "TIMEOUT",
    "Network Error": "NETWORK_ERROR",
    "Missing Dep": "MISSING_DEP",
    "Lib Version": "LIB_VERSION",
    "API Drift": "API_DRIFT",
    "API Mismatch": "API_MISMATCH",
    "Config Missing": "CONFIG_MISSING",
    "No Chat Template": "NO_CHAT_TEMPLATE",
    "Unsupported Arch": "UNSUPPORTED_ARCH",
    "Weight Mismatch": "WEIGHT_MISMATCH",
    "Type Cast Error": "TYPE_CAST",
    "Processor Error": "PROCESSOR",
    "Tokenizer Error": "TOKENIZER",
    "Model Error": "MODEL",
    "Error": "ERROR",
}
_PACKAGE_CODE_MAP: Final[dict[str, str]] = {
    "mlx": "MLX",
    "mlx-vlm": "MLX_VLM",
    "transformers": "TRANSFORMERS",
    "model-repo-code": "MODEL_REPO_CODE",
    "huggingface-hub": "HUGGINGFACE_HUB",
    "model-config": "MODEL_CONFIG",
    "unknown": "UNKNOWN",
}


_FAILURE_PHASE_VALUES: Final[frozenset[str]] = _literal_values(FailurePhaseName)
# Human labels for every failure phase (completeness asserted in tests).
_FAILURE_PHASE_HUMAN_LABELS: Final[dict[FailurePhaseName, str]] = {
    "input_validation": "input validation",
    "import": "dependency import",
    "model_load": "model loading",
    "processor_load": "processor loading",
    "tokenizer_load": "tokenizer loading",
    "model_preflight": "model preflight",
    "prompt_prep": "prompt templating",
    "prefill": "prompt preparation",
    "decode": "generation",
    "generation_before_first_token": "generation, before first token",
    "generation_after_first_token": "generation, after first token",
    "cleanup": "cleanup",
}
# Every phase that means "the upstream generation call had started".
_GENERATION_FAILURE_PHASES: Final[frozenset[str]] = frozenset(
    {"decode", "generation_before_first_token", "generation_after_first_token"}
)
# Message needles that identify a memory-capacity failure (Metal allocator and
# command-buffer wording); shared by stage classification and the crash draft.
_OOM_MESSAGE_NEEDLES: Final[tuple[str, ...]] = (
    "metal::malloc",
    "maximum allowed buffer size",
    "insufficient memory",
    "out of memory",
    "kiogpucommandbuffercallbackerroroutofmemory",
)


def _failure_phase_human_label(phase: str | None) -> str:
    """Return the canonical human label for a phase, tolerating foreign data."""
    if phase in _FAILURE_PHASE_VALUES:
        return _FAILURE_PHASE_HUMAN_LABELS[cast("FailurePhaseName", phase)]
    return (phase or "execution").replace("_", " ")


def _normalise_failure_phase(phase: str | None) -> FailurePhaseName | None:
    """Return the canonical failure phase, or ``None`` for unknown labels."""
    if phase is None:
        return None
    normalized = phase.strip().lower().replace("-", "_")
    if normalized in _FAILURE_PHASE_VALUES:
        return cast("FailurePhaseName", normalized)
    return None


def _tag_exception_failure_phase[E: BaseException](error: E, phase: FailurePhaseName) -> E:
    """Annotate an exception with the current failing phase."""
    normalized = _normalise_failure_phase(phase)
    if normalized is not None:
        setattr(cast("Any", error), _FAILURE_PHASE_ATTR, normalized)
    return error


def _tag_generation_boundary_failure[E: BaseException](error: E, *, token_seen: bool) -> E:
    """Tag a streaming failure with the first-token boundary unless a phase is known.

    Upstream does not say which of its internal stages failed, and "before the
    first token" is not the same as prefill (input preparation, cache set-up
    and the first decode step all happen there), so the boundary is reported
    as exactly that and nothing more specific.
    """
    if _extract_failure_phase(error) is not None:
        return error
    phase: FailurePhaseName = (
        "generation_after_first_token" if token_seen else "generation_before_first_token"
    )
    return _tag_exception_failure_phase(error, phase)


def _generation_failure_phase(error: BaseException) -> FailurePhaseName:
    """Prefer a phase already tagged on the chain; else the unsplit generation call."""
    return _extract_failure_phase(error) or "decode"


def _tag_exception_prompt_diagnostics[E: BaseException](
    error: E,
    diagnostics: PromptDiagnostics | None,
) -> E:
    """Attach rendered prompt diagnostics to an exception when available."""
    if diagnostics is not None:
        setattr(cast("Any", error), _PROMPT_DIAGNOSTICS_ATTR, diagnostics)
    return error


def _object_prompt_diagnostics(value: object | None) -> PromptDiagnostics | None:
    """Return prompt diagnostics attached to an arbitrary runtime object."""
    diagnostics = getattr(value, _PROMPT_DIAGNOSTICS_ATTR, None)
    return diagnostics if isinstance(diagnostics, PromptDiagnostics) else None


def _extract_failure_phase(
    error: BaseException,
    *,
    fallback: str | None = None,
) -> FailurePhaseName | None:
    """Extract the first known failure phase from an exception chain."""
    cur: BaseException | None = error
    while cur is not None:
        tagged = getattr(cur, _FAILURE_PHASE_ATTR, None)
        if isinstance(tagged, str) and tagged.strip():
            return _normalise_failure_phase(tagged)
        cur = cur.__cause__
    return _normalise_failure_phase(fallback)


def _exception_chain(error: BaseException) -> Iterator[BaseException]:
    """Yield an exception and its causal/context chain without looping forever."""
    seen: set[int] = set()
    cur: BaseException | None = error
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        yield cur
        if cur.__cause__ is not None:
            cur = cur.__cause__
        elif not cur.__suppress_context__:
            cur = cur.__context__
        else:
            cur = None


def _root_cause_exception(
    error: BaseException,
    *,
    chain: Iterable[BaseException] | None = None,
) -> BaseException:
    """Return the deepest exception, reusing a materialized chain when supplied."""
    root = error
    for candidate in chain if chain is not None else _exception_chain(error):
        root = candidate
    return root


def _failure_exception_record(error: BaseException) -> FailureException:
    """Materialize stable exception identity for failure artifacts."""
    frames = traceback.extract_tb(error.__traceback__)
    origin = frames[-1].filename if frames else None
    return FailureException(
        exception_type=type(error).__name__,
        module=type(error).__module__,
        message=str(error),
        origin=origin,
    )


def _serialize_exception_chain(
    chain: tuple[FailureException, ...],
) -> list[dict[str, str]]:
    """Serialize a stored exception chain without changing its chronology."""
    serialized: list[dict[str, str]] = []
    for entry in chain:
        item = {
            "type": entry.exception_type,
            "module": entry.module,
            "message": _home_relative_report_text(entry.message),
        }
        if entry.origin is not None:
            item["origin"] = _home_relative_report_text(entry.origin)
        serialized.append(item)
    return serialized


def _failure_exception_package(entry: FailureException) -> str:
    """Identify the package recorded by an exception module or traceback origin."""
    origin = " ".join(part for part in (entry.module, entry.origin) if part)
    return _attribute_error_to_package(entry.message, origin)


def _extract_exception_prompt_diagnostics(
    error: BaseException,
    *,
    chain: Iterable[BaseException] | None = None,
) -> PromptDiagnostics | None:
    """Return prompt diagnostics from a new or already-materialized exception chain."""
    for item in chain if chain is not None else _exception_chain(error):
        if diagnostics := _object_prompt_diagnostics(item):
            return diagnostics
    return None


def _sanitize_error_token(value: str | None, *, default: str) -> str:
    """Convert free-form labels into stable uppercase token segments."""
    if value is None or not value.strip():
        return default
    token = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper()).strip("_")
    return token or default


def _normalize_error_core_message(error_msg: str) -> str:
    """Normalize model-specific and numeric variations from top-level error text."""
    core = error_msg.split("\n", maxsplit=1)[0].strip() if error_msg else "Unknown error"
    wrapper_match = re.match(
        r"Model (?:generation|loading|preflight) failed(?:\s+for\s+\S+)?:\s*(.+)",
        core,
    )
    if wrapper_match:
        core = wrapper_match.group(1)
    return re.sub(r"\(N(?:,N)+\)", "(N,...)", re.sub(r"\d+", "N", core))


def _normalize_traceback_signature(traceback_str: str | None) -> str:
    """Return a stable traceback fingerprint fragment for signature hashing."""
    if not traceback_str:
        return ""

    normalized_lines: list[str] = []
    for raw_line in traceback_str.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("File "):
            line = re.sub(r'File ".*?([^/\\"]+)"', r'File "\1"', line)
            line = re.sub(r"line \d+", "line N", line)
        line = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", line)
        line = re.sub(r"\d+", "N", line)
        normalized_lines.append(line)

    if not normalized_lines:
        return ""
    return " | ".join(normalized_lines[-4:])


def _build_canonical_error_code(
    *,
    error_stage: str | None,
    error_package: str | None,
    failure_phase: str | None,
) -> str:
    """Build stable machine-readable error code for cross-run clustering."""
    package_token = _PACKAGE_CODE_MAP.get(
        (error_package or _UNKNOWN_OWNER).lower(),
        _sanitize_error_token(error_package, default="UNKNOWN"),
    )
    phase_token = _sanitize_error_token(_normalise_failure_phase(failure_phase), default="UNKNOWN")
    stage_token = _STAGE_CODE_MAP.get(
        error_stage or "",
        _sanitize_error_token(error_stage, default="ERROR"),
    )
    return f"{package_token}_{phase_token}_{stage_token}"


def _build_error_signature(
    *,
    error_code: str,
    error_message: str | None,
    error_traceback: str | None,
) -> str:
    """Build stable signature hash for clustering related failures."""
    canonical_message = _normalize_error_core_message(error_message or "Unknown error")
    traceback_sig = _normalize_traceback_signature(error_traceback)
    payload = f"{error_code}|{canonical_message}|{traceback_sig}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{error_code}:{digest}"


def _classify_error(error_msg: str) -> str:
    """Classify error message into a short, readable status code.

    Categories (in order of precedence):
        - OOM: Metal memory allocation failures
        - Timeout: Operation timed out
        - Missing Dep: Missing pip packages
        - Lib Version: Import errors due to version mismatches
        - API Drift: Required runtime surface missing/reshaped before invocation
        - API Mismatch: Unexpected keyword arguments (transformers/mlx-vlm API changes)
        - Config Missing: Model repository missing required config files
        - No Chat Template: Tokenizer/processor lacks chat template
        - Unsupported Arch: model_type not supported by installed mlx-vlm
        - Weight Mismatch: Model weights don't match expected parameters
        - Type Cast Error: MLX core type/cast errors (std::bad_cast)
        - Processor Error: Image processor instantiation failures
        - Tokenizer Error: Tokenizer class/loading failures
        - Model Error: Generic model loading/config issues
        - Error: Unclassified errors
    """
    msg_lower = error_msg.lower()

    # (Error Type, List of lowercase keywords that trigger this type)
    # Order matters: first match wins
    error_definitions = [
        # Critical infrastructure errors
        ("Network Error", list(_EXTERNAL_CONNECTIVITY_NEEDLES)),
        ("OOM", list(_OOM_MESSAGE_NEEDLES)),
        ("Timeout", ["timeout"]),
        # Dependency/version errors
        (
            "Missing Dep",
            ["requires", "packages", "pip install"],
        ),  # All must be present logic handled below
        ("Lib Version", ["cannot import name", "importerror"]),
        (
            "API Drift",
            [
                "generation runtime api drift",
                "missing-dependency placeholder",
                "missing required keyword parameter",
                "positional-only parameter",
                "required field(s)",
                "signature could not be inspected for api drift checks",
            ],
        ),
        # API compatibility errors
        ("API Mismatch", ["unexpected keyword argument", "got an unexpected keyword"]),
        # Model configuration/file errors
        (
            "Config Missing",
            ["does not appear to have a file named", "missing required file", "config is missing"],
        ),
        ("No Chat Template", ["chat_template is not set", "no template argument was passed"]),
        # Architecture support (upstream raises "Model type {x} not supported.")
        # Must precede Weight Mismatch / Model Error to avoid misclassification.
        ("Unsupported Arch", ["model type", "not supported"]),
        # Weight/parameter errors
        ("Weight Mismatch", ["missing", "parameters"]),
        # MLX core errors
        ("Type Cast Error", ["std::bad_cast"]),
        # Processor/tokenizer errors
        ("Processor Error", ["imageprocessor", "image_processor"]),
        ("Tokenizer Error", ["tokenizer class", "does not exist"]),
        # Generic model errors
        ("Model Error", ["model", "loading", "failed"]),
    ]

    for error_type, patterns in error_definitions:
        # Special case for multi-keyword AND logic (Missing Dep, Unsupported
        # Arch, Model Error)
        if error_type in {"Missing Dep", "Unsupported Arch"}:
            if all(p in msg_lower for p in patterns):
                return error_type
            continue

        if error_type == "Model Error":
            # "model" AND ("loading" OR "failed")
            if "model" in msg_lower and ("loading" in msg_lower or "failed" in msg_lower):
                return error_type
            continue

        if error_type == "Tokenizer Error":
            # "tokenizer class" AND "does not exist"
            if all(p in msg_lower for p in patterns):
                return error_type
            continue

        if error_type == "Weight Mismatch":
            # "missing" AND "parameters"
            if all(p in msg_lower for p in patterns):
                return error_type
            continue

        # Default OR logic for other patterns
        if any(p in msg_lower for p in patterns):
            return error_type

    return "Error"


def _attribute_error_to_package(error_msg: str, traceback_str: str | None = None) -> str:
    """Heuristically attribute an error to the most likely owning package.

    Uses ordered pattern precedence across message/traceback text so diagnostics
    can route issue reports to the right upstream project.
    """
    msg_lower = error_msg.lower()
    tb_lower = (traceback_str or "").lower()
    combined = msg_lower + " " + tb_lower
    # transformers_modules is the dynamic-module cache transformers uses for a
    # repo's trust_remote_code files: a frame there means the failing code
    # belongs to the model repository, not to any library — e.g. a repo's fast
    # image processor importing a symbol a newer transformers removed. Checked
    # before the message-first flow because such failures usually carry
    # library-looking messages ("cannot import name ...").
    if _has_external_connectivity_signal(combined) or "transformers_modules" in combined:
        return _UNKNOWN_OWNER if _has_external_connectivity_signal(combined) else "model-repo-code"

    # (Package Name, List of unique identification patterns)
    # Order matters: matches earlier in list take precedence
    package_definitions = [
        # Unexpected parameters surface inside mlx.nn.load_weights, but weights
        # the architecture does not expect indicate an mlx-vlm architecture/
        # conversion mismatch, so route there first (the traceback keeps the
        # mlx frames as evidence). Genuinely *missing* weights stay with the
        # model-config owner below.
        (
            "mlx-vlm",
            [
                "parameters not in model",
            ],
        ),
        (
            "mlx",
            [
                "metal::malloc",
                "maximum allowed buffer size",
                "insufficient memory",
                "out of memory",
                "kiogpucommandbuffercallbackerroroutofmemory",
                "std::bad_cast",
                "mlx/core/",
                "mlx/nn/",
                "mlx/python/mlx/",
            ],
        ),
        (
            "mlx-vlm",
            [
                "mlx_vlm/",
                "mlx_vlm.",
                "mlx-vlm/",
                "apply_chat_template",
                "generationresult",
                "load_image",
                "runtime api drift",
                "missing-dependency placeholder",
            ],
        ),
        (
            "transformers",
            [
                "transformers/",
                "cannot import name",
                "importerror",
                "unexpected keyword argument",
                "tokenizer class",
                "processing_utils",
                "tokenization_",
                "image_processing_",
                "_batch_encode_plus",
            ],
        ),
        (
            "huggingface-hub",
            [
                "huggingface_hub",
                "does not appear to have a file",
                "hfvalidationerror",
            ],
        ),
        (
            "model-config",
            [
                "chat_template is not set",
                "no template argument",
                "config.json",
                "missing required file",
                "model preflight failed",
                "tokenizer artifacts missing",
            ],
        ),
    ]

    def _matching_packages(text: str) -> list[str]:
        matches: list[str] = []
        for package, patterns in package_definitions:
            if any(pattern in text for pattern in patterns):
                matches.append(package)
        return matches

    message_matches = _matching_packages(msg_lower)
    if message_matches:
        return message_matches[0]

    traceback_matches = _matching_packages(tb_lower)
    if traceback_matches:
        chained_exception_markers = (
            "during handling of the above exception",
            "the above exception was the direct cause of the following exception",
        )
        if any(marker in tb_lower for marker in chained_exception_markers):
            wrapped_traceback_preference = (
                "transformers",
                "huggingface-hub",
                "model-config",
                "mlx",
                "mlx-vlm",
            )
            for package in wrapped_traceback_preference:
                if package in traceback_matches:
                    return package

    for package, patterns in package_definitions:
        if any(pattern in combined for pattern in patterns):
            return package

    # Special case for compound logic check which didn't fit the loop
    if "missing" in combined and "parameters" in combined:
        return "model-config"

    return "unknown"


def _load_model(
    params: ProcessImageParams,
) -> tuple[nn.Module, ProcessorMixin, PreTrainedConfig | Mapping[str, object] | None]:
    """Load model from HuggingFace Hub or local path.

    Args:
        params: The parameters for image processing, including model identifier.

    Returns:
        Tuple of ``(model, processor, config)`` where ``processor`` is an
        ``transformers.ProcessorMixin`` and ``config`` may be ``None``.
    """
    try:
        model, processor = load(
            path_or_hf_repo=params.model_identifier,
            adapter_path=params.adapter_path,
            lazy=params.lazy,
            revision=params.revision,
            trust_remote_code=params.trust_remote_code,
            force_download=params.force_download,
            quantize_activations=params.quantize_activations,
        )
    except Exception as load_error:
        chain_text = " ".join(
            f"{type(error).__name__}: {error}" for error in _exception_chain(load_error)
        )
        resolved_snapshot = (
            _resolve_model_snapshot(params.model_identifier, params.revision)
            if not params.force_download and _has_external_connectivity_signal(chain_text)
            else None
        )
        snapshot_path = resolved_snapshot.path if resolved_snapshot is not None else None
        # The resolver only returns a snapshot for an explicit revision when it
        # matched a cached hash/prefix/ref, so its source — not a directory-name
        # equality that a branch or tag name can never satisfy — is the check.
        revision_matches = params.revision is None or (
            resolved_snapshot is not None
            and resolved_snapshot.source in ("requested-revision", "local-path")
        )
        if (
            snapshot_path is None
            or not snapshot_path.is_dir()
            or str(snapshot_path) == params.model_identifier
            or not revision_matches
        ):
            raise
        logger.warning(
            "Hub access failed while loading %s; retrying resolved local snapshot %s.",
            params.model_identifier,
            snapshot_path,
        )
        model, processor = load(
            path_or_hf_repo=str(snapshot_path),
            adapter_path=params.adapter_path,
            lazy=params.lazy,
            revision=None,
            trust_remote_code=params.trust_remote_code,
            force_download=False,
            quantize_activations=params.quantize_activations,
        )
    config = cast(
        "PreTrainedConfig | Mapping[str, object] | None",
        getattr(model, "config", None),
    )
    return model, processor, config


def _set_failure_phase(
    phase_callback: Callable[[str], None] | None,
    phase: str,
) -> str:
    """Update the active execution phase and notify optional callback."""
    normalized = _normalise_failure_phase(phase) or phase
    if phase_callback is not None:
        phase_callback(normalized)
    return normalized


def _has_text_decoder_api(candidate: object) -> TypeGuard[SupportsTextDecoder]:
    """Return whether a candidate exposes the decode API we rely on."""
    return callable(getattr(candidate, "decode", None)) and callable(
        getattr(candidate, "batch_decode", None),
    )


def _extract_processor_tokenizer(
    processor: ProcessorMixin,
) -> PreTrainedTokenizerBase | SupportsTextDecoder | None:
    """Best-effort extraction of tokenizer from a loaded processor."""
    tokenizer = cast("object | None", getattr(processor, "tokenizer", None))
    if tokenizer is not None and _has_text_decoder_api(tokenizer):
        return tokenizer
    if _has_text_decoder_api(processor):
        return processor
    return None


_MIN_REVISION_HASH_PREFIX: Final[int] = 7


class ResolvedSnapshot(NamedTuple):
    """A locally resolved snapshot plus how its revision was chosen."""

    path: Path
    source: Literal["local-path", "requested-revision", "refs/main", "newest-snapshot"]


def _resolve_model_snapshot(
    model_identifier: str,
    requested_revision: str | None = None,
) -> ResolvedSnapshot | None:
    """Resolve the cached snapshot the way the loader will, not by recency.

    Resolution order mirrors huggingface_hub (and Nativ's discovery): an
    explicit requested revision (commit hash, hash prefix, or a cached ref
    name) wins; otherwise the cached ``main`` ref; only when neither exists is
    the newest snapshot by modification time used, and that fallback is
    labelled so provenance never silently passes it off as ``main``. A
    requested revision that cannot be resolved locally returns None rather
    than misreporting some other snapshot as the requested one.
    """
    if model_identifier.startswith(("/", "./", "../")):
        path = Path(model_identifier)
        return ResolvedSnapshot(path.resolve(), "local-path") if path.is_dir() else None

    try:
        cache_info = _get_hf_cache_info_cached()
    except (OSError, ValueError, FileNotFoundError, HFValidationError):
        return None

    for repo in cache_info.repos:
        if repo.repo_id == model_identifier:
            return _resolve_repo_snapshot(list(repo.revisions), requested_revision)
    return None


def _revision_matches_request(revision: object, requested_revision: str) -> bool:
    """Return whether a cached revision satisfies an explicit hash/prefix/ref."""
    commit_hash = str(getattr(revision, "commit_hash", "") or "")
    refs = {str(ref) for ref in getattr(revision, "refs", ()) or ()}
    return (
        commit_hash == requested_revision
        or (
            len(requested_revision) >= _MIN_REVISION_HASH_PREFIX
            and commit_hash.startswith(requested_revision)
        )
        or requested_revision in refs
    )


def _resolve_repo_snapshot(
    revisions: list[object],
    requested_revision: str | None,
) -> ResolvedSnapshot | None:
    """Pick the snapshot for one cached repo per the documented resolution order."""
    if not revisions:
        return None
    if requested_revision:
        for revision in revisions:
            if _revision_matches_request(revision, requested_revision):
                snapshot = getattr(revision, "snapshot_path", None)
                if snapshot:
                    return ResolvedSnapshot(Path(str(snapshot)), "requested-revision")
        return None
    for revision in revisions:
        if "main" in (getattr(revision, "refs", ()) or ()):
            snapshot = getattr(revision, "snapshot_path", None)
            if snapshot:
                return ResolvedSnapshot(Path(str(snapshot)), "refs/main")
    revisions.sort(
        key=lambda revision: float(getattr(revision, "last_modified", 0.0) or 0.0),
        reverse=True,
    )
    snapshot = getattr(revisions[0], "snapshot_path", None)
    return ResolvedSnapshot(Path(str(snapshot)), "newest-snapshot") if snapshot else None


def _resolve_model_snapshot_path(
    model_identifier: str,
    requested_revision: str | None = None,
) -> Path | None:
    """Path-only convenience over :func:`_resolve_model_snapshot`."""
    resolved = _resolve_model_snapshot(model_identifier, requested_revision)
    return resolved.path if resolved is not None else None


def _collect_model_provenance(
    model_identifier: str,
    *,
    requested_revision: str | None = None,
) -> ModelProvenanceRecord:
    """Return requested and locally selected model snapshot identity."""
    resolved = _resolve_model_snapshot(model_identifier, requested_revision)
    snapshot_path = resolved.path if resolved is not None else None
    resolved_revision = (
        snapshot_path.name
        if snapshot_path is not None and snapshot_path.parent.name == "snapshots"
        else None
    )
    record: ModelProvenanceRecord = {
        "model": model_identifier,
        "requested_revision": requested_revision,
        "resolved_revision": resolved_revision,
        "snapshot_path": (
            _home_relative_report_text(str(snapshot_path)) if snapshot_path is not None else None
        ),
    }
    if resolved is not None:
        record["revision_source"] = resolved.source
    return record


def _get_config_value(config: object | None, key: str) -> object | None:
    """Read config values from dict-like or object-like config containers."""
    if config is None:
        return None
    if isinstance(config, Mapping):
        config_map = cast("Mapping[str, object]", config)
        return config_map.get(key)
    return getattr(config, key, None)


def _raise_preflight_error(message: str, *, phase: FailurePhaseName) -> NoReturn:
    """Raise a preflight ValueError annotated with the failing phase."""
    raise _tag_exception_failure_phase(ValueError(message), phase)


def _validate_model_artifact_layout(
    *,
    model_identifier: str,
    snapshot_path: Path | None,
    tokenizer: PreTrainedTokenizerBase | SupportsTextDecoder | None,
) -> tuple[str, ...]:
    """Validate local model artifact structure and return neutral snapshot notes.

    These checks are intentionally non-fatal because many older/community repos
    rely on legacy file layouts that still run correctly with mlx-vlm. The
    notes are recorded as evidence on the per-model result (never as an
    observation and never affecting usability) so that a later failure on a
    newer mlx-vlm can be traced back to a snapshot that always lacked the
    artifact, without grepping run logs.
    """
    if snapshot_path is None or not snapshot_path.exists():
        logger.debug(
            "Skipping file-layout preflight for %s (snapshot unavailable).",
            model_identifier,
        )
        return ()

    notes: list[str] = []
    if tokenizer is not None:
        tokenizer_candidates = (
            "tokenizer_config.json",
            "tokenizer.json",
            "tokenizer.model",
            "vocab.json",
        )
        if not any((snapshot_path / name).exists() for name in tokenizer_candidates):
            notes.append(
                f"tokenizer artifacts missing from snapshot ({', '.join(tokenizer_candidates)})"
            )

    processor_candidates = ("preprocessor_config.json", "processor_config.json")
    if not any((snapshot_path / name).exists() for name in processor_candidates):
        notes.append(f"processor config missing from snapshot ({', '.join(processor_candidates)})")

    shard_status = _weight_shard_status(snapshot_path)
    if shard_status is not None:
        if shard_status.index_error is not None:
            notes.append(f"{shard_status.index_error} — incomplete or corrupt download")
        elif shard_status.missing:
            sample = ", ".join(shard_status.missing_sample)
            notes.append(
                f"{shard_status.missing} of {shard_status.total} weight shards missing "
                f"from snapshot (e.g. {sample}) — incomplete download"
            )

    for note in notes:
        logger.debug("Legacy snapshot note for %s: %s.", model_identifier, note)
    return tuple(notes)


def _run_model_preflight_validators(
    *,
    model_identifier: str,
    processor: ProcessorMixin,
    config: PreTrainedConfig | Mapping[str, object] | None,
    phase_callback: Callable[[str], None] | None = None,
    requested_revision: str | None = None,
) -> tuple[str, ...]:
    """Run preflight validators before invoking generation.

    Returns neutral snapshot notes (legacy file-layout facts) for the result.
    """
    _set_failure_phase(phase_callback, "tokenizer_load")
    tokenizer = _extract_processor_tokenizer(processor)
    if tokenizer is None:
        _raise_preflight_error(
            "Could not resolve tokenizer from loaded processor.",
            phase="tokenizer_load",
        )

    _set_failure_phase(phase_callback, "processor_load")
    if not callable(processor):
        _raise_preflight_error(
            "Loaded processor is not callable.",
            phase="processor_load",
        )

    _set_failure_phase(phase_callback, "model_preflight")
    model_type = _get_config_value(config, "model_type")
    if not isinstance(model_type, str) or not model_type.strip():
        logger.warning(
            "Preflight warning for %s: model config missing model_type.",
            model_identifier,
        )

    snapshot_path = _resolve_model_snapshot_path(model_identifier, requested_revision)
    return _validate_model_artifact_layout(
        model_identifier=model_identifier,
        snapshot_path=snapshot_path,
        tokenizer=tokenizer,
    )


def _ensure_generation_runtime_symbols() -> None:
    """Validate core generation callables before model execution."""
    runtime_api_issues = list(_detect_runtime_api_drift_issues())
    if not runtime_api_issues:
        return

    msg = "Generation runtime API drift: " + "; ".join(runtime_api_issues)
    raise _tag_exception_failure_phase(RuntimeError(msg), "import")


def _run_generation_guarded(
    *,
    params: ProcessImageParams,
    generate_once: Callable[[], GenerationResult | SupportsGenerationResult],
) -> GenerationResult | SupportsGenerationResult:
    """Run generation once, tagging failures with the deepest known generation phase.

    A phase already on the exception chain (the streaming first-token boundary,
    or anything tagged deeper) wins; only a failure with no such evidence is
    reported as the unsplit generation call.
    """
    try:
        return generate_once()
    except TimeoutError as gen_to_err:
        msg = f"Generation timed out for model {params.model_identifier}: {gen_to_err}"
        raise _tag_exception_failure_phase(
            TimeoutError(msg), _generation_failure_phase(gen_to_err)
        ) from gen_to_err
    except (OSError, ValueError) as gen_known_err:
        msg = f"Model generation failed for {params.model_identifier}: {gen_known_err}"
        logger.exception("Generation error for %s", params.model_identifier)
        raise _tag_exception_failure_phase(
            ValueError(msg), _generation_failure_phase(gen_known_err)
        ) from gen_known_err
    except (RuntimeError, TypeError, AttributeError, KeyError) as gen_err:
        msg = f"Model runtime error during generation for {params.model_identifier}: {gen_err}"
        logger.exception("Runtime error for %s", params.model_identifier)
        raise _tag_exception_failure_phase(
            ValueError(msg), _generation_failure_phase(gen_err)
        ) from gen_err


def _build_runtime_diagnostics(
    phase_timer: PhaseTimer,
    *,
    stop_reason: str | None,
    first_token_latency_s: float | None = None,
    model_load_active_memory_gb: float | None = None,
    post_cleanup_active_memory_gb: float | None = None,
    post_cleanup_cache_memory_gb: float | None = None,
) -> RuntimeDiagnostics:
    """Build immutable runtime diagnostics from a phase timer snapshot."""
    return RuntimeDiagnostics(
        input_validation_time_s=phase_timer.duration("input_validation"),
        model_load_time_s=phase_timer.duration("model_load"),
        model_load_active_memory_gb=model_load_active_memory_gb,
        prompt_prep_time_s=phase_timer.duration("prompt_prep"),
        decode_time_s=phase_timer.duration("decode"),
        cleanup_time_s=phase_timer.duration("cleanup"),
        first_token_latency_s=first_token_latency_s,
        stop_reason=stop_reason,
        post_cleanup_active_memory_gb=post_cleanup_active_memory_gb,
        post_cleanup_cache_memory_gb=post_cleanup_cache_memory_gb,
    )


class _PreparedPrompt(NamedTuple):
    """Rendered prompt payload plus neutral snapshot notes from preflight."""

    prompt: str | list[object]
    snapshot_notes: tuple[str, ...]


def _prepare_generation_prompt(
    *,
    params: ProcessImageParams,
    processor: ProcessorMixin,
    config: PreTrainedConfig | Mapping[str, object] | None,
    phase_callback: Callable[[str], None] | None,
    phase_timer: PhaseTimer | None,
) -> _PreparedPrompt:
    """Run preflight checks and build the prompt payload for generation."""
    try:
        chat_template_kwargs = _build_chat_template_kwargs(params)
        timer_scope = phase_timer.track("prompt_prep") if phase_timer is not None else nullcontext()
        with timer_scope:
            snapshot_notes = _run_model_preflight_validators(
                model_identifier=params.model_identifier,
                processor=processor,
                config=config,
                phase_callback=phase_callback,
                requested_revision=params.revision,
            )
            _set_failure_phase(phase_callback, "prefill")
            rendered = cast(
                "str | list[object]",
                apply_chat_template(
                    processor=processor,
                    config=config,
                    prompt=params.prompt,
                    num_images=1,
                    **chat_template_kwargs,
                ),
            )
            return _PreparedPrompt(prompt=rendered, snapshot_notes=snapshot_notes)
    except ValueError as preflight_err:
        message = f"Model preflight failed for {params.model_identifier}: {preflight_err}"
        logger.exception("Model preflight validation failed for %s", params.model_identifier)
        phase = (
            _extract_failure_phase(preflight_err, fallback="model_preflight") or "model_preflight"
        )
        raise _tag_exception_failure_phase(ValueError(message), phase) from preflight_err
    except (OSError, RuntimeError, TypeError, AttributeError, KeyError) as prefill_err:
        msg = f"Prompt prefill failed for {params.model_identifier}: {prefill_err}"
        logger.exception("Prompt prefill failed for %s", params.model_identifier)
        raise _tag_exception_failure_phase(ValueError(msg), "prefill") from prefill_err


def _cleanup_runtime_resources(*, synchronize_first: bool = True) -> None:
    """Clear runtime resources after each model run.

    Successful generation paths already synchronize before sampling timing and
    memory, so callers can skip the extra barrier when no further MLX work ran.
    Failure paths should still request the pre-cleanup synchronize to avoid
    clearing caches while kernels may still be in flight.
    """

    def _run_cleanup_step(step_name: str, func: Callable[[], object] | None) -> None:
        if func is None:
            return
        try:
            func()
        except (
            AttributeError,
            IndexError,
            OSError,
            RuntimeError,
            SystemError,
            TypeError,
            ValueError,
        ):
            logger.debug("Ignoring cleanup failure in %s", step_name, exc_info=True)

    if synchronize_first:
        synchronize_fn = cast("Callable[[], object] | None", getattr(mx, "synchronize", None))
        _run_cleanup_step("mx.synchronize", synchronize_fn)
    gc.collect()

    clear_cache_fn = cast("Callable[[], object] | None", getattr(mx, "clear_cache", None))
    _run_cleanup_step("mx.clear_cache", clear_cache_fn)

    reset_peak_memory_fn = cast(
        "Callable[[], object] | None",
        getattr(mx, "reset_peak_memory", None),
    )
    _run_cleanup_step("mx.reset_peak_memory", reset_peak_memory_fn)


def _generate_with_processor_passthrough(
    *,
    generate_fn: Callable[..., GenerationResult | SupportsGenerationResult],
    model: nn.Module,
    processor: ProcessorLike | PreTrainedTokenizer,
    params: ProcessImageParams,
    formatted_prompt: str,
    generate_kwargs: GenerateKwargs,
) -> GenerationResult | SupportsGenerationResult:
    """Call upstream generate() with user-provided passthrough kwargs.

    This branch is intentionally dynamic because ``processor_kwargs`` is a
    user-supplied JSON object whose keys depend on the active upstream model.
    """
    processor_kwargs = params.processor_kwargs or {}
    return generate_fn(
        model=model,
        processor=processor,
        prompt=formatted_prompt,
        image=str(params.image_path),
        **processor_kwargs,
        **generate_kwargs,
    )


def _sample_mlx_memory_gb(getter_name: MlxMemoryGetterName) -> float | None:
    """Best-effort sample one non-negative MLX allocator metric in decimal GB."""
    getter = cast("Callable[[], object] | None", getattr(mx, getter_name, None))
    if getter is None or not callable(getter):
        return None
    try:
        raw_value = getter()
    except (AttributeError, OSError, RuntimeError, SystemError, TypeError, ValueError):
        logger.debug("Unable to sample mx.%s", getter_name, exc_info=True)
        return None
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float) or raw_value < 0:
        return None
    return float(raw_value) / DECIMAL_GB


def _sample_active_memory_gb() -> float | None:
    """Sample MLX active memory in GB when the runtime exposes the metric."""
    return _sample_mlx_memory_gb("get_active_memory")


def _sample_cache_memory_gb() -> float | None:
    """Sample MLX cache memory in GB when the runtime exposes the metric."""
    return _sample_mlx_memory_gb("get_cache_memory")


def _sample_post_cleanup_memory_gb() -> tuple[float | None, float | None]:
    """Return the active/cache allocator state after one model cleanup."""
    return _sample_active_memory_gb(), _sample_cache_memory_gb()


def _attach_model_load_memory_baseline(
    output: GenerationResult | SupportsGenerationResult,
    *,
    model_load_active_memory_gb: float | None,
) -> SupportsGenerationResult:
    """Attach the post-model-load active memory baseline to the generation result."""
    result = cast("SupportsGenerationResult", output)
    result.model_load_active_memory = model_load_active_memory_gb
    return result


def _attach_generation_runtime_metrics(
    output: GenerationResult | SupportsGenerationResult,
    *,
    duration: float,
) -> SupportsGenerationResult:
    """Attach local timing and allocator snapshot metrics to a generation result."""
    result = cast("SupportsGenerationResult", output)
    result.time = duration
    result.active_memory = _sample_active_memory_gb() or 0.0
    result.cache_memory = _sample_cache_memory_gb() or 0.0
    return result


def _finalize_process_result(
    *,
    result_payload: PerformanceResult | None,
    params: ProcessImageParams,
    phase_timer: PhaseTimer,
    stop_reason: str | None,
    current_phase: str,
    total_start_time: float,
    upstream_boundary: UpstreamBoundary = "not_started",
    post_cleanup_active_memory_gb: float | None = None,
    post_cleanup_cache_memory_gb: float | None = None,
) -> PerformanceResult:
    """Attach final runtime diagnostics after cleanup has completed."""
    runtime_diagnostics = _build_runtime_diagnostics(
        phase_timer,
        stop_reason=(
            result_payload.runtime_diagnostics.stop_reason
            if result_payload is not None and result_payload.runtime_diagnostics is not None
            else stop_reason
        ),
        first_token_latency_s=(
            result_payload.runtime_diagnostics.first_token_latency_s
            if result_payload is not None and result_payload.runtime_diagnostics is not None
            else None
        ),
        model_load_active_memory_gb=(
            result_payload.runtime_diagnostics.model_load_active_memory_gb
            if result_payload is not None and result_payload.runtime_diagnostics is not None
            else None
        ),
        post_cleanup_active_memory_gb=post_cleanup_active_memory_gb,
        post_cleanup_cache_memory_gb=post_cleanup_cache_memory_gb,
    )
    if result_payload is None:
        fallback_error = RuntimeError(
            "process_image_with_model completed without producing a result",
        )
        return _build_failure_result(
            model_name=params.model_identifier,
            error=fallback_error,
            captured_output=None,
            failure_phase=current_phase,
            generation_time=phase_timer.duration("decode"),
            model_load_time=phase_timer.duration("model_load"),
            total_time=time.perf_counter() - total_start_time,
            runtime_diagnostics=runtime_diagnostics,
            requested_max_tokens=params.max_tokens,
            upstream_boundary=upstream_boundary,
        )
    return replace(
        result_payload,
        runtime_diagnostics=runtime_diagnostics,
        requested_revision=params.revision,
        model_burden=_collect_model_burden(params.model_identifier, params.revision),
    )


class _PreparedGeneration(NamedTuple):
    """Everything the execute step needs after load and prompt preparation."""

    model: nn.Module
    generation_processor: ProcessorLike | PreTrainedTokenizer
    formatted_prompt: str
    generate_kwargs: GenerateKwargs
    processor_passthrough_kwargs: Mapping[str, object]
    prompt_diagnostics: PromptDiagnostics


def _prepare_generation(
    params: ProcessImageParams,
    *,
    model: nn.Module,
    processor: ProcessorMixin,
    config: PreTrainedConfig | Mapping[str, object] | None,
    phase_callback: Callable[[str], None] | None,
    phase_timer: PhaseTimer | None,
) -> _PreparedGeneration:
    """Render the prompt and resolve the processor, kwargs, and diagnostics.

    This is the preparation half of a model run: it does not touch the
    upstream generate call, decode timing, or synchronisation.
    """
    # Resolve the generation-compatible processor/tokenizer *before* rendering
    # the prompt, so a missing tokenizer is attributed to processor loading
    # rather than to the prefill phase the prompt render enters.
    _set_failure_phase(phase_callback, "processor_load")
    if _is_generation_processor(processor):
        generation_processor: ProcessorLike | PreTrainedTokenizer = processor
    else:
        tokenizer = _extract_processor_tokenizer(processor)
        if tokenizer is None or not _is_generation_processor(tokenizer):
            msg = "mlx-vlm load returned no generation-compatible processor or tokenizer"
            raise _tag_exception_failure_phase(TypeError(msg), "processor_load")
        generation_processor = tokenizer

    prepared_prompt = _prepare_generation_prompt(
        params=params,
        processor=processor,
        config=config,
        phase_callback=phase_callback,
        phase_timer=phase_timer,
    )
    formatted = prepared_prompt.prompt
    # Handle list return from apply_chat_template
    formatted_prompt = (
        "\n".join(str(m) for m in formatted) if isinstance(formatted, list) else formatted
    )

    extra_kwargs = _build_generate_extra_kwargs(params)
    processor_passthrough_kwargs = params.processor_kwargs or {}
    generate_kwargs = _build_generate_kwargs(params, extra_kwargs)
    auto_budget_applied = _apply_auto_thinking_budget(params, formatted_prompt, generate_kwargs)
    if auto_budget_applied:
        thinking_budget_source: Literal["auto", "explicit"] | None = "auto"
    elif generate_kwargs.get("thinking_budget") is not None:
        thinking_budget_source = "explicit"
    else:
        thinking_budget_source = None
    prompt_diagnostics = _build_prompt_diagnostics(
        params=params,
        processor=processor,
        config=config,
        formatted_prompt=formatted_prompt,
        generate_kwargs=generate_kwargs,
        processor_passthrough_kwargs=processor_passthrough_kwargs,
        thinking_budget_source=thinking_budget_source,
        snapshot_notes=prepared_prompt.snapshot_notes,
    )
    return _PreparedGeneration(
        model=model,
        generation_processor=generation_processor,
        formatted_prompt=formatted_prompt,
        generate_kwargs=generate_kwargs,
        processor_passthrough_kwargs=processor_passthrough_kwargs,
        prompt_diagnostics=prompt_diagnostics,
    )


# Streaming repetition guard: a degenerate greedy loop (keyword cycling and
# similar) otherwise runs to the token cap, wasting sweep time to produce
# evidence that is unambiguous after a few hundred tokens. The guard never
# fires below the token floor, and requires four exact repeats of a
# substantial unit at the very end of the accumulated text.
_REPETITION_ABORT_MIN_TOKENS: Final[int] = 200
_REPETITION_ABORT_CHECK_EVERY: Final[int] = 25
_REPETITION_ABORT_TAIL_CHARS: Final[int] = 600
_REPETITION_TAIL_CYCLE_RE: Final[re.Pattern[str]] = re.compile(
    r"(.{12,160}?)(?:\1){3,}\Z", re.DOTALL
)


def _detect_streaming_repetition(tail: str) -> bool:
    """Return whether the text tail ends in >=4 exact repeats of one unit."""
    return _REPETITION_TAIL_CYCLE_RE.search(tail) is not None


def _stream_tail_repeats(pieces: Sequence[str], chunk: object, chunk_count: int) -> bool:
    """Check the retained tail for a degenerate cycle every N chunks past the floor."""
    if chunk_count % _REPETITION_ABORT_CHECK_EVERY != 0:
        return False
    generated = getattr(chunk, "generation_tokens", None)
    if not isinstance(generated, int) or generated < _REPETITION_ABORT_MIN_TOKENS:
        return False
    return _detect_streaming_repetition("".join(pieces)[-_REPETITION_ABORT_TAIL_CHARS:])


def _generate_with_repetition_guard(
    model: nn.Module,
    processor: ProcessorLike | PreTrainedTokenizer,
    prompt: str,
    image: str | list[str] | None = None,
    on_first_token: Callable[[], None] | None = None,
    **kwargs: object,
) -> GenerationResult | SupportsGenerationResult:
    """Upstream ``generate`` semantics with an early stop on degenerate loops.

    Mirrors upstream ``generate``: it registers custom EOS tokens on the
    tokenizer's stopping criteria (or resets them to the model default so a
    prior model's registration cannot leak), skips draft chunks the way the
    upstream accumulator does, and returns the final chunk's metrics with the
    joined text — adding only a tail-cycle check. An abort sets
    ``finish_reason="repetition_abort"``, which flows into the runtime stop
    reason and the matching observation; aborted generations are excluded
    from cross-run throughput comparisons and history bands because a rate
    over a few hundred tokens is not comparable with a full-length run.

    Upstream ``stream_generate`` does not echo text the way
    ``generate(verbose=True)`` did, so under ``verbose`` the guard streams
    each retained (non-draft, not-already-printed) chunk to stdout as it
    arrives — inside the tee capture, so the live console and the retained
    upstream capture both keep the text. Like upstream ``generate()``, the
    joined text passes through the processor's optional ``clean_output``
    hook before being returned.

    ``on_first_token`` fires once, when the first chunk arrives; a failure
    escaping the stream is tagged with that boundary (before/after the first
    token) unless a deeper phase is already on it.
    """
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    stopping_criteria = getattr(tokenizer, "stopping_criteria", None)
    eos_tokens = kwargs.get("eos_tokens")
    if stopping_criteria is not None:
        if eos_tokens is not None:
            stopping_criteria.add_eos_token_ids(eos_tokens)
        elif (eos_id := getattr(getattr(model, "config", None), "eos_token_id", None)) is not None:
            stopping_criteria.reset(eos_id)
    pieces: list[str] = []
    last: GenerationResult | SupportsGenerationResult | None = None
    aborted = False
    chunk_count = 0
    echo = sys.stdout if kwargs.get("verbose") else None
    try:
        for chunk in stream_generate(
            model=model, processor=processor, prompt=prompt, image=image, **kwargs
        ):
            if last is None and on_first_token is not None:
                on_first_token()
            last = chunk
            if getattr(chunk, "is_draft", False):
                # Speculative/diffusion draft chunks are progress display only;
                # upstream generate() excludes their text from the final answer,
                # so they are neither echoed nor retained.
                continue
            pieces.append(chunk.text)
            if (
                echo is not None
                and chunk.text
                and not getattr(chunk, "text_already_printed", False)
            ):
                echo.write(chunk.text)
                echo.flush()
            chunk_count += 1
            if _stream_tail_repeats(pieces, chunk, chunk_count):
                aborted = True
                break
        if echo is not None and pieces:
            echo.write("\n")
            echo.flush()
        if last is None:
            # Upstream generate() returns an empty result for an empty stream; an
            # empty stream is an empty_output observation, not a crash.
            return cast(
                "SupportsGenerationResult",
                types.SimpleNamespace(
                    text="", finish_reason=None, peak_memory=mx.get_peak_memory() / 1e9
                ),
            )
        text = "".join(pieces)
        # Upstream generate() applies the processor's optional clean_output hook
        # to the joined text (e.g. diffusion_gemma strips leaked channel
        # scaffolding); mirror it so stream_generate-based results match.
        clean_output = getattr(processor, "clean_output", None)
        if callable(clean_output) and isinstance(cleaned := clean_output(text), str):
            text = cleaned
        finish_reason = "repetition_abort" if aborted else getattr(last, "finish_reason", None)
        if is_dataclass(last) and not isinstance(last, type):
            return replace(last, text=text, finish_reason=finish_reason)
        duck = types.SimpleNamespace(**vars(last))
        duck.text = text
        duck.finish_reason = finish_reason
        return cast("SupportsGenerationResult", duck)
    except BaseException as stream_err:
        # The streaming boundary is the only phase evidence available here:
        # upstream does not say which of its stages failed. Output
        # finalisation (echo, clean_output, result assembly) is inside the
        # same block so a failure there keeps the boundary it reached.
        _tag_generation_boundary_failure(stream_err, token_seen=last is not None)
        raise


def _execute_prepared_generation(
    params: ProcessImageParams,
    prepared: _PreparedGeneration,
    *,
    phase_callback: Callable[[str], None] | None,
    phase_timer: PhaseTimer | None,
) -> tuple[GenerationResult | SupportsGenerationResult, float]:
    """Run the upstream generate call and return (output, synchronised duration).

    This is the execution half: it owns the upstream call, decode-phase
    timing, MLX synchronisation, and exception tagging with prompt
    diagnostics. Metric attachment stays with the caller.
    """

    def _note_first_token() -> None:
        _set_failure_phase(phase_callback, "generation_after_first_token")

    def _generate_once() -> GenerationResult | SupportsGenerationResult:
        if prepared.processor_passthrough_kwargs:
            return _generate_with_processor_passthrough(
                generate_fn=functools.partial(
                    _generate_with_repetition_guard, on_first_token=_note_first_token
                ),
                model=prepared.model,
                processor=prepared.generation_processor,
                params=params,
                formatted_prompt=prepared.formatted_prompt,
                generate_kwargs=prepared.generate_kwargs,
            )
        return _generate_with_repetition_guard(
            model=prepared.model,
            processor=prepared.generation_processor,
            prompt=prepared.formatted_prompt,
            image=str(params.image_path),
            on_first_token=_note_first_token,
            **prepared.generate_kwargs,
        )

    # Time the generation process manually since MLX VLM doesn't include timing.
    timer = PerfCounterTimer()
    timer.start()
    if phase_timer is not None:
        phase_timer.start("decode")
    # Failure phase (not the timer phase): a crash before any chunk arrives is
    # reported as exactly that, never assumed to be prefill.
    _set_failure_phase(phase_callback, "generation_before_first_token")
    try:
        output = _run_generation_guarded(
            params=params,
            generate_once=_generate_once,
        )
        # MLX is lazy: synchronize *before* stopping either timer so the
        # decode phase and the local generation duration both include all
        # pending GPU work and agree with each other.
        mx.synchronize()
        duration = timer.stop()
    except (TimeoutError, ValueError) as generation_err:
        _tag_exception_prompt_diagnostics(generation_err, prepared.prompt_diagnostics)
        raise
    finally:
        # On the success path the decode timer stops after synchronization;
        # this only closes it when an exception escaped before that point.
        if phase_timer is not None:
            phase_timer.stop("decode")
    return output, duration


def _run_model_generation(
    params: ProcessImageParams,
    phase_callback: Callable[[str], None] | None = None,
    phase_timer: PhaseTimer | None = None,
) -> GenerationResult | SupportsGenerationResult:
    """Load model + processor, prepare the request, execute it, attach metrics.

    Load, prepare, and execute stay in one call because they form a tightly
    coupled sequence (tokenizer/model/config interplay varies by repo), but
    preparation (:func:`_prepare_generation`) and execution
    (:func:`_execute_prepared_generation`) are separate seams. Errors are
    wrapped with traceback context so upstream summaries can show concise
    messages while verbose logs retain full detail.

    Args:
        params: The parameters for the image processing.
        phase_callback: Optional callback invoked when execution enters a new phase.
        phase_timer: Optional per-phase timer that records load, prep, and decode durations.
    """
    model: nn.Module
    processor: ProcessorMixin

    _set_failure_phase(phase_callback, "import")
    _ensure_generation_runtime_symbols()

    # Load model from HuggingFace Hub - this handles automatic download/caching
    # and converts weights to MLX format for Apple Silicon optimization
    _set_failure_phase(phase_callback, "model_load")
    try:
        if phase_timer is not None:
            with phase_timer.track("model_load"):
                model, processor, config = _load_model(params)
        else:
            model, processor, config = _load_model(params)
    except Exception as load_err:
        # Capture model loading errors and run cache diagnostics to distinguish
        # code bugs from environment issues (corrupted cache, incomplete download)
        error_details = f"Model loading failed: {load_err}"
        logger.debug(
            "Model load failure captured for %s: %s",
            params.model_identifier,
            load_err,
            extra={"log_destination": "file"},
        )
        _check_hf_cache_integrity(params.model_identifier)

        raise _tag_exception_failure_phase(ValueError(error_details), "model_load") from load_err

    model_load_active_memory_gb = _sample_active_memory_gb()

    prepared = _prepare_generation(
        params,
        model=model,
        processor=processor,
        config=config,
        phase_callback=phase_callback,
        phase_timer=phase_timer,
    )
    output, duration = _execute_prepared_generation(
        params,
        prepared,
        phase_callback=phase_callback,
        phase_timer=phase_timer,
    )

    # Capture local timing plus active/cache memory snapshots while model state is intact.
    result = _attach_generation_runtime_metrics(output, duration=duration)
    result = _attach_model_load_memory_baseline(
        result,
        model_load_active_memory_gb=model_load_active_memory_gb,
    )
    setattr(cast("Any", result), _PROMPT_DIAGNOSTICS_ATTR, prepared.prompt_diagnostics)
    return result


def _build_failure_result(  # noqa: PLR0913 - every retained failure fact is an explicit keyword  # skylos: ignore[SKY-C303]
    *,
    model_name: str,
    error: BaseException,
    captured_output: str | None,
    quality_analysis: GenerationQualityAnalysis | None = None,
    failure_phase: str | None = None,
    generation_time: float | None = None,
    model_load_time: float | None = None,
    total_time: float | None = None,
    runtime_diagnostics: RuntimeDiagnostics | None = None,
    requested_max_tokens: int | None = None,
    prompt_diagnostics: PromptDiagnostics | None = None,
    upstream_boundary: UpstreamBoundary = "not_started",
) -> PerformanceResult:
    """Build a standardized failure result payload for a model run."""
    error_msg = str(error)
    tb_str = traceback.format_exc()
    traversed_chain = tuple(_exception_chain(error))
    root_exception = _root_cause_exception(error, chain=traversed_chain)
    chronological_errors = (root_exception, *reversed(traversed_chain[:-1]))
    exception_chain = tuple(_failure_exception_record(item) for item in chronological_errors)
    root_error = exception_chain[0]
    root_error_msg = root_error.message
    classification_text = " ".join(part for part in (root_error_msg, error_msg) if part)
    resolved_phase = _extract_failure_phase(error, fallback=failure_phase)
    classified_stage = _classify_error(classification_text or error_msg)
    primary_package = _failure_exception_package(root_error)
    error_package = (
        primary_package
        if primary_package != _UNKNOWN_OWNER
        else _attribute_error_to_package(classification_text or error_msg, tb_str)
    )
    error_code = _build_canonical_error_code(
        error_stage=classified_stage,
        error_package=error_package,
        failure_phase=resolved_phase,
    )
    error_signature = _build_error_signature(
        error_code=error_code,
        error_message=root_error_msg or error_msg,
        error_traceback=tb_str,
    )
    resolved_prompt_diagnostics = prompt_diagnostics or _extract_exception_prompt_diagnostics(
        error,
        chain=traversed_chain,
    )
    return PerformanceResult(
        model_name=model_name,
        generation=None,
        success=False,
        upstream_boundary=upstream_boundary,
        failure_phase=resolved_phase,
        error_stage=classified_stage,
        error_code=error_code,
        error_signature=error_signature,
        error_message=error_msg,
        captured_output_on_fail=captured_output,
        error_type=type(error).__name__,
        root_error_type=root_error.exception_type,
        root_error_module=root_error.module,
        root_error_message=root_error_msg,
        exception_chain=exception_chain,
        quality_analysis=quality_analysis,
        error_package=error_package,
        error_traceback=tb_str,
        generation_time=generation_time,
        model_load_time=model_load_time,
        total_time=total_time,
        runtime_diagnostics=runtime_diagnostics,
        requested_max_tokens=requested_max_tokens,
        prompt_diagnostics=resolved_prompt_diagnostics,
    )


def _is_self_logged_rich_traceback_line(line: str) -> bool:
    """Return whether a captured stderr line came from our own Rich traceback log."""
    stripped = _strip_ansi(line).strip()
    if not stripped:
        return False
    if SELF_LOGGED_FAILURE_PREFIX_RE.search(stripped):
        return True
    if "Traceback (most recent call last)" in stripped:
        return True
    if "check_models.py:" in stripped:
        return True
    if "_run_model_generation" in stripped:
        return True
    return stripped.startswith(("╭", "╰", "│", "❱", "─"))


def _sanitize_failure_stderr_capture(stderr_text: str) -> str:
    """Drop self-logged Rich traceback noise while preserving external stderr."""
    normalized = stderr_text.replace("\r", "\n")
    kept = [
        _strip_ansi(line).rstrip()
        for line in normalized.splitlines()
        if not _is_self_logged_rich_traceback_line(line)
    ]
    return "\n".join(line for line in kept if line.strip()).strip()


def _normalize_stream_capture_text(text: str) -> str:
    """Normalize live console capture for durable file-log retention."""
    stripped = _strip_ansi(text)
    # Progress bars rewrite the same line with CR; keep the final state of each write.
    normalized = stripped.replace("\r\n", "\n")
    if "\r" in normalized:
        normalized = "\n".join(
            segment.rsplit("\r", maxsplit=1)[-1] for segment in normalized.split("\n")
        )
    lines = [line.rstrip() for line in normalized.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _compose_stream_capture_for_file_log(
    *,
    stdout_text: str,
    stderr_text: str,
) -> str | None:
    """Build one file-log body from tee'd stdout/stderr without console re-echo."""
    sections: list[str] = []
    stdout_clean = _normalize_stream_capture_text(stdout_text)
    if stdout_clean:
        sections.append(stdout_clean)
    stderr_clean = _sanitize_failure_stderr_capture(stderr_text)
    # Avoid duplicating stdout when libraries write the same block to both streams.
    if stderr_clean and (not stdout_clean or stderr_clean not in stdout_clean):
        sections.append(f"=== STDERR ===\n{stderr_clean}")
    if not sections:
        return None
    body = "\n\n".join(sections)
    if len(body) <= MAX_FILE_STREAM_CAPTURE_CHARS:
        return body
    omitted = len(body) - MAX_FILE_STREAM_CAPTURE_CHARS
    return (
        body[:MAX_FILE_STREAM_CAPTURE_CHARS]
        + f"\n...[truncated {omitted} characters for file-log size bound]"
    )


def _log_stream_capture_to_file(
    *,
    model_identifier: str,
    stdout_text: str,
    stderr_text: str,
) -> None:
    """Persist tee'd mlx-vlm console output to the file log only.

    Live generation already reaches the terminal via ``_TeeCaptureStream``. Re-logging
    to the console would duplicate that block; ``log_destination="file"`` keeps the
    durable copy without a second terminal echo.
    """
    body = _compose_stream_capture_for_file_log(
        stdout_text=stdout_text,
        stderr_text=stderr_text,
    )
    if body is None:
        return
    # Every continuation line carries the model id so a grep for one model
    # returns its whole captured block, not just the header record.
    prefixed = "\n".join(f"[{model_identifier}] {line}" for line in body.splitlines())
    logger.debug(
        "Captured mlx-vlm console output for %s:\n%s",
        model_identifier,
        prefixed,
        extra={"log_destination": "file"},
    )


def _build_success_process_result(
    *,
    params: ProcessImageParams,
    output: GenerationResult | SupportsGenerationResult,
    phase_timer: PhaseTimer,
    total_start_time: float,
    upstream_boundary: UpstreamBoundary,
    stdout_text: str = "",
    stderr_text: str = "",
) -> tuple[PerformanceResult, str | None]:
    """Build the successful PerformanceResult and resolved stop reason."""
    performance_data = _extract_generation_performance_data(output)
    generation_time = performance_data.generation_time_s or phase_timer.duration("decode")
    total_time = time.perf_counter() - total_start_time
    model_load_time = phase_timer.duration("model_load")
    first_token_latency_s = performance_data.first_token_latency_s
    active_mem_gb = performance_data.active_memory_gb
    cache_mem_gb = performance_data.cache_memory_gb
    stop_reason = _resolve_generation_stop_reason(
        performance_data,
        requested_max_tokens=params.max_tokens,
    )
    result_payload = PerformanceResult(
        model_name=params.model_identifier,
        generation=output,
        success=True,
        upstream_boundary=upstream_boundary,
        captured_upstream_output=_compose_stream_capture_for_file_log(
            stdout_text=stdout_text,
            stderr_text=stderr_text,
        ),
        generation_time=generation_time,
        model_load_time=model_load_time,
        total_time=total_time,
        active_memory=active_mem_gb if active_mem_gb > 0 else None,
        cache_memory=cache_mem_gb if cache_mem_gb > 0 else None,
        runtime_diagnostics=_build_runtime_diagnostics(
            phase_timer,
            first_token_latency_s=first_token_latency_s,
            model_load_active_memory_gb=_object_model_load_active_memory_gb(output),
            stop_reason=stop_reason,
        ),
        requested_max_tokens=params.max_tokens,
        prompt_diagnostics=_object_prompt_diagnostics(output),
        assessment_profile=params.assessment_profile,
    )
    result_payload = _populate_result_quality_analysis(
        result_payload,
        prompt=params.prompt,
        requested_max_tokens=params.max_tokens,
    )
    return result_payload, stop_reason


def _build_exception_process_result(
    *,
    params: ProcessImageParams,
    error: BaseException,
    stdout_text: str,
    stderr_text: str,
    current_phase: str,
    phase_timer: PhaseTimer,
    total_start_time: float,
    upstream_boundary: UpstreamBoundary,
) -> tuple[PerformanceResult, str]:
    """Build a failure PerformanceResult from tee buffers and the raised error."""
    captured_sections: list[str] = []
    stdout_clean = stdout_text.strip()
    stderr_clean = _sanitize_failure_stderr_capture(stderr_text)
    failure_quality_analysis: GenerationQualityAnalysis | None = None
    if stdout_clean:
        captured_sections.append("=== STDOUT ===\n" + stdout_clean)
        if (
            len(stdout_clean) >= QUALITY.min_text_length
            or len(stdout_clean.split()) >= QUALITY.min_token_count
        ):
            # Neutral captured-output evidence; the canonical assessment for
            # failures stays "not_evaluated" and carries no verdict string.
            failure_quality_analysis = analyze_generation_text(
                stdout_clean,
                max(len(stdout_clean.split()), 1),
                prompt=params.prompt,
                requested_max_tokens=params.max_tokens,
                assessment_profile=params.assessment_profile,
            )
    if stderr_clean:
        captured_sections.append("=== STDERR ===\n" + stderr_clean)
    captured_output = "\n\n".join(captured_sections) if captured_sections else None
    stop_reason = "timeout" if isinstance(error, TimeoutError) else "exception"
    result_payload = _build_failure_result(
        model_name=params.model_identifier,
        error=error,
        captured_output=captured_output,
        quality_analysis=failure_quality_analysis,
        failure_phase=current_phase,
        generation_time=phase_timer.duration("decode"),
        model_load_time=phase_timer.duration("model_load"),
        total_time=time.perf_counter() - total_start_time,
        runtime_diagnostics=_build_runtime_diagnostics(
            phase_timer,
            stop_reason=stop_reason,
        ),
        requested_max_tokens=params.max_tokens,
        upstream_boundary=upstream_boundary,
    )
    return result_payload, stop_reason


_TELEMETRY_CPU_SPEED_RE: Final[re.Pattern[str]] = re.compile(r"CPU_Speed_Limit\s*=\s*(\d+)")
_TELEMETRY_SAMPLE_INTERVAL_S: Final[float] = 2.0
# kern.memorystatus_vm_pressure_level: 1 = normal, 2 = warning, 4 = critical.
_MEMORY_PRESSURE_NORMAL_LEVEL: Final[int] = 1
_MEMORY_PRESSURE_CRITICAL_LEVEL: Final[int] = 4
_CPU_SPEED_UNTHROTTLED_PCT: Final[float] = 100.0


def _sample_thermal_cpu_speed_limit_pct() -> float | None:
    """Read the macOS thermal CPU speed limit (100 = no throttling).

    On Apple Silicon, nominal thermals report "No CPU power status has been
    recorded" instead of a CPU_Speed_Limit line; that means unthrottled.
    """
    output = _run_macos_toolchain_command(("/usr/bin/pmset", "-g", "therm"), timeout=3)
    if output is None:
        return None
    match = _TELEMETRY_CPU_SPEED_RE.search(output)
    if match:
        return float(match.group(1))
    if "No CPU power status has been recorded" in output:
        return _CPU_SPEED_UNTHROTTLED_PCT
    return None


def _sample_memory_pressure_level() -> int | None:
    """Read kern.memorystatus_vm_pressure_level (1 normal, 2 warning, 4 critical)."""
    output = _run_macos_toolchain_command(
        ("/usr/sbin/sysctl", "-n", "kern.memorystatus_vm_pressure_level"),
        timeout=3,
    )
    if output is None:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def _system_telemetry_probe() -> tuple[float | None, int | None]:
    """Take one (cpu_speed_limit_pct, memory_pressure_level) probe pair."""
    return _sample_thermal_cpu_speed_limit_pct(), _sample_memory_pressure_level()


def _system_telemetry_record_from_probes(
    probes: Sequence[tuple[float | None, int | None]],
    *,
    mode: SystemTelemetryMode,
    interval_s: float | None = None,
) -> SystemTelemetryRecord:
    """Aggregate probe pairs, keeping per-probe counts so gaps stay visible.

    Total probe failure still yields a record (both sample counts zero) so
    diagnostics can distinguish "telemetry ran but probes were unavailable"
    from telemetry being disabled.
    """
    cpu_limits = [cpu for cpu, _ in probes if cpu is not None]
    pressure_levels = [level for _, level in probes if level is not None]
    record: SystemTelemetryRecord = {
        "mode": mode,
        "cpu_samples": len(cpu_limits),
        "memory_samples": len(pressure_levels),
    }
    if interval_s is not None:
        record["interval_s"] = interval_s
    if cpu_limits:
        record["cpu_speed_limit_min_pct"] = min(cpu_limits)
        record["cpu_throttled_samples"] = sum(
            limit < _CPU_SPEED_UNTHROTTLED_PCT for limit in cpu_limits
        )
    if pressure_levels:
        record["memory_pressure_level_max"] = max(pressure_levels)
        record["memory_pressure_elevated_samples"] = sum(
            level > _MEMORY_PRESSURE_NORMAL_LEVEL for level in pressure_levels
        )
    return record


class _SystemTelemetrySampler:
    """Opt-in continuous sampler for thermal and memory-pressure state.

    Each tick shells out to `pmset -g therm` and `sysctl` (sudo-free reads).
    Because those subprocesses run while inference is being timed, continuous
    mode is opt-in; the default is a before/after snapshot pair taken outside
    the timed sections.
    """

    def __init__(self, interval_s: float = _TELEMETRY_SAMPLE_INTERVAL_S) -> None:
        self._interval_s = interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._probes: list[tuple[float | None, int | None]] = []

    def start(self) -> None:
        """Begin sampling until stop() is called."""
        self._thread = threading.Thread(
            target=self._run,
            name="system-telemetry-sampler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling and join; the timeout outlasts both 3s probe caps."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_s + 7.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            cpu_limit = _sample_thermal_cpu_speed_limit_pct()
            if self._stop_event.is_set():
                self._probes.append((cpu_limit, None))
                return
            self._probes.append((cpu_limit, _sample_memory_pressure_level()))
            self._stop_event.wait(self._interval_s)

    def snapshot(self) -> SystemTelemetryRecord:
        """Aggregate captured probes; zero sample counts stay visible."""
        return _system_telemetry_record_from_probes(
            self._probes,
            mode="continuous",
            interval_s=self._interval_s,
        )


def _telemetry_degradation_note(telemetry: SystemTelemetryRecord) -> str | None:
    """Describe throttling or memory pressure worth flagging, if any."""
    notes: list[str] = []
    min_limit = telemetry.get("cpu_speed_limit_min_pct")
    if min_limit is not None and min_limit < _CPU_SPEED_UNTHROTTLED_PCT:
        notes.append(
            f"CPU speed limited to {min_limit:.0f}% for "
            f"{telemetry.get('cpu_throttled_samples', 0)} sample(s)"
        )
    max_level = telemetry.get("memory_pressure_level_max")
    if max_level is not None and max_level > _MEMORY_PRESSURE_NORMAL_LEVEL:
        label = "critical" if max_level >= _MEMORY_PRESSURE_CRITICAL_LEVEL else "warning"
        notes.append(
            f"memory pressure reached {label} for "
            f"{telemetry.get('memory_pressure_elevated_samples', 0)} sample(s)"
        )
    return "; ".join(notes) if notes else None


def _telemetry_status_line(telemetry: SystemTelemetryRecord) -> str:
    """Full per-probe status for diagnostics: gaps are stated, never implied clean."""
    parts: list[str] = []
    cpu_samples = telemetry.get("cpu_samples", 0)
    if cpu_samples:
        min_limit = telemetry.get("cpu_speed_limit_min_pct", _CPU_SPEED_UNTHROTTLED_PCT)
        parts.append(f"CPU speed limit min {min_limit:.0f}% over {cpu_samples} sample(s)")
    else:
        parts.append("thermal probe unavailable")
    memory_samples = telemetry.get("memory_samples", 0)
    if memory_samples:
        max_level = telemetry.get("memory_pressure_level_max", _MEMORY_PRESSURE_NORMAL_LEVEL)
        parts.append(f"memory pressure max level {max_level} over {memory_samples} sample(s)")
    else:
        parts.append("memory-pressure probe unavailable")
    parts.append(f"mode {telemetry.get('mode', 'unknown')}")
    return "; ".join(parts)


def _resolve_system_telemetry_mode(flag: bool | None) -> SystemTelemetryMode:
    """Translate the BooleanOptionalAction value into the telemetry mode once."""
    if flag is True:
        return "continuous"
    if flag is False:
        return "off"
    return "snapshot"


def _start_system_telemetry(
    params: ProcessImageParams,
) -> tuple[_SystemTelemetrySampler | None, list[tuple[float | None, int | None]]]:
    """Start opt-in continuous sampling or take the leading snapshot probe.

    Called before timing starts so the default snapshot probe stays outside
    the timed sections; continuous sampling is opt-in because its
    subprocesses overlap timed inference. Telemetry is strictly best-effort:
    any failure here is logged and telemetry is simply absent for the model —
    it must never become a model failure or abort the sweep.
    """
    if sys.platform != "darwin" or params.system_telemetry == "off":
        return None, []
    try:
        if params.system_telemetry == "continuous":
            sampler = _SystemTelemetrySampler()
            sampler.start()
            return sampler, []
        return None, [_system_telemetry_probe()]
    except Exception:
        logger.debug("System telemetry could not start; continuing without it", exc_info=True)
        return None, []


def _finish_system_telemetry(
    sampler: _SystemTelemetrySampler | None,
    probes: list[tuple[float | None, int | None]],
) -> SystemTelemetryRecord | None:
    """Stop sampling (or take the trailing snapshot probe) and aggregate.

    Runs from the per-model ``finally`` block, so it must never raise: a
    failure here would otherwise convert a completed model into an exception
    or escape the isolation boundary entirely.
    """
    try:
        if sampler is not None:
            sampler.stop()
            return sampler.snapshot()
        if probes:
            probes.append(_system_telemetry_probe())
            return _system_telemetry_record_from_probes(probes, mode="snapshot")
    except Exception:
        logger.debug("System telemetry could not finish; recording none", exc_info=True)
    return None


def _attach_system_telemetry(
    result: PerformanceResult,
    telemetry: SystemTelemetryRecord | None,
    model_identifier: str,
) -> PerformanceResult:
    """Attach captured telemetry to the result, warning on degradation."""
    if telemetry is None:
        return result
    degradation = _telemetry_degradation_note(telemetry)
    if degradation is not None:
        logger.warning(
            "⚠\ufe0f  System pressure during %s: %s",
            model_identifier,
            degradation,
        )
    return replace(result, system_telemetry=telemetry)


# =============================================================================
# SECTION: ISOLATED MODEL EXECUTION (one child interpreter per model)
# =============================================================================

_ISOLATED_STDERR_TAIL_CHARS: Final[int] = 6000
_ISOLATION_TIMEOUT_GRACE_SECONDS: Final[float] = 120.0
_ISOLATION_PHASE_SINK: Callable[[str], None] | None = None
_SHELL_SIGNAL_EXIT_BASE: Final[int] = 128
_VARIADIC_TUPLE_ARGS: Final[int] = 2


class IsolatedWorkerCrashError(RuntimeError):
    """The child interpreter running one model died without reporting a result."""

    def __init__(self, model_identifier: str, returncode: int, detail: str) -> None:
        self.returncode = returncode
        signal_name = _signal_name_for_returncode(returncode)
        how = f"killed by {signal_name}" if signal_name else f"exited with status {returncode}"
        super().__init__(
            f"Isolated worker for {model_identifier} {how} before writing a result; {detail}"
        )


class IsolatedWorkerTimeoutError(TimeoutError):
    """The child interpreter running one model exceeded the parent's deadline."""

    def __init__(self, model_identifier: str, deadline_s: float, phase: str) -> None:
        super().__init__(
            f"Isolated worker for {model_identifier} exceeded {deadline_s:.0f}s "
            f"(model timeout plus {_ISOLATION_TIMEOUT_GRACE_SECONDS:.0f}s start-up/cleanup "
            f"grace) while in phase {phase}; the child was terminated"
        )


def _signal_name_for_returncode(returncode: int) -> str | None:
    """Map a negative subprocess return code (or 128+N) to a signal name."""
    number = (
        -returncode
        if returncode < 0
        else (returncode - _SHELL_SIGNAL_EXIT_BASE if returncode > _SHELL_SIGNAL_EXIT_BASE else 0)
    )
    if number <= 0:
        return None
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"


@dataclass(frozen=True)
class IsolatedGenerationResult:
    """Duck-typed stand-in for an upstream GenerationResult rebuilt from JSON.

    Reports only read generation metrics through ``getattr`` (``text``,
    ``prompt_tokens``, ``generation_tps``, ...), so a frozen holder whose
    unknown attributes resolve from the recorded mapping round-trips exactly
    what the child measured without importing or reconstructing upstream types.
    """

    text: str = ""
    extra: dict[str, JsonLike] = dataclass_field(default_factory=dict)

    def __getattr__(self, name: str) -> JsonLike:
        extra = cast("dict[str, JsonLike]", object.__getattribute__(self, "extra"))
        if name in extra:
            return extra[name]
        raise AttributeError(name)


def _json_safe(value: object) -> JsonLike:
    """Convert dataclasses, paths, tuples and sets into JSON-compatible values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_safe(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


def _namespace_to_json(args: argparse.Namespace) -> dict[str, JsonLike]:
    """Serialise parsed CLI arguments, tagging Path values so the child restores them."""
    payload: dict[str, JsonLike] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            payload[key] = {"__path__": str(value)}
        else:
            payload[key] = _json_safe(value)
    return payload


def _namespace_from_json(payload: Mapping[str, JsonLike]) -> argparse.Namespace:
    """Rebuild an argparse Namespace from ``_namespace_to_json`` output."""
    restored: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, dict) and set(value) == {"__path__"}:
            restored[key] = Path(str(value["__path__"]))
        else:
            restored[key] = value
    return argparse.Namespace(**restored)


def _dataclass_from_json[T](cls: type[T], data: object) -> T:
    """Rebuild a dataclass (recursively) from JSON produced by ``_json_safe``."""
    if not isinstance(data, Mapping):
        message = f"Expected a mapping for {cls.__name__}, got {type(data).__name__}"
        raise TypeError(message)
    hints = get_type_hints(cls)
    kwargs: dict[str, object] = {}
    for field in fields(cast("type[Any]", cls)):
        if field.name not in data:
            continue
        kwargs[field.name] = _coerce_json_value(hints.get(field.name), data[field.name])
    return cls(**kwargs)


def _coerce_union_json_value(annotation: object, value: object) -> object:
    """Try each non-None member of a union until one coerces cleanly."""
    for candidate in get_args(annotation):
        if candidate is type(None):
            continue
        try:
            return _coerce_json_value(candidate, value)
        except (TypeError, ValueError):
            continue
    return value


def _coerce_tuple_json_value(annotation: object, value: list[object]) -> tuple[object, ...]:
    """Rebuild ``tuple[T, ...]`` or fixed-arity tuples from a JSON list."""
    args = get_args(annotation)
    if len(args) == _VARIADIC_TUPLE_ARGS and args[1] is Ellipsis:
        return tuple(_coerce_json_value(args[0], item) for item in value)
    return tuple(
        _coerce_json_value(args[index] if index < len(args) else None, item)
        for index, item in enumerate(value)
    )


def _coerce_json_value(annotation: object, value: object) -> object:
    """Coerce one JSON value toward ``annotation`` (dataclasses, tuples, unions)."""
    if value is None or annotation is None:
        return value
    origin = get_origin(annotation)
    if origin in (types.UnionType, Union):
        return _coerce_union_json_value(annotation, value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _dataclass_from_json(annotation, value)
    if origin is tuple and isinstance(value, list):
        return _coerce_tuple_json_value(annotation, value)
    if origin is list and isinstance(value, list):
        (item_type,) = get_args(annotation) or (None,)
        return [_coerce_json_value(item_type, item) for item in value]
    return value


def _performance_result_to_json(result: PerformanceResult) -> dict[str, JsonLike]:
    """Serialise a PerformanceResult for the parent, flattening upstream generation."""
    payload = cast("dict[str, JsonLike]", _json_safe(result))
    generation = result.generation
    if generation is not None:
        generation_payload: dict[str, JsonLike] = {}
        if is_dataclass(generation) and not isinstance(generation, type):
            generation_payload = {
                field.name: _json_safe(getattr(generation, field.name))
                for field in fields(generation)
            }
        # check_models attaches runtime metrics (active_memory, cache_memory,
        # model_load_active_memory) to the upstream object dynamically; the
        # instance dict carries those, declared fields alone would drop them.
        instance_dict = getattr(generation, "__dict__", None)
        if isinstance(instance_dict, dict):
            for name, value in instance_dict.items():
                if not name.startswith("_") and name not in generation_payload:
                    generation_payload[name] = _json_safe(value)
        if not generation_payload:
            generation_payload = {
                name: _json_safe(getattr(generation, name))
                for name in dir(generation)
                if not name.startswith("_") and not callable(getattr(generation, name, None))
            }
        payload["generation"] = generation_payload
    return payload


def _performance_result_from_json(payload: Mapping[str, JsonLike]) -> PerformanceResult:
    """Rebuild a PerformanceResult from a child's JSON, with a duck-typed generation."""
    data = dict(payload)
    generation_payload = data.pop("generation", None)
    result = _dataclass_from_json(PerformanceResult, {**data, "generation": None})
    if isinstance(generation_payload, dict):
        text = generation_payload.get("text", "")
        extra = {key: value for key, value in generation_payload.items() if key != "text"}
        result = replace(
            result,
            generation=cast(
                "StoredGenerationResult",
                IsolatedGenerationResult(text=str(text or ""), extra=extra),
            ),
        )
    return result


def _isolated_worker_spec(
    args: argparse.Namespace, params: ProcessImageParams
) -> dict[str, JsonLike]:
    """Serialise one model request for a child interpreter.

    ``_isolated_params_from_spec`` is the exact inverse; the two are kept
    adjacent and round-trip tested because a key that drifts between them
    fails every isolated model before inference starts.
    """
    return {
        "args": _namespace_to_json(args),
        "model_identifier": params.model_identifier,
        "image_path": str(params.image_path),
        "prompt": params.prompt,
        "overrides": {
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
            "timeout": params.timeout,
            "verbose": params.verbose,
        },
    }


def _isolated_params_from_spec(
    spec: Mapping[str, JsonLike], args: argparse.Namespace
) -> ProcessImageParams:
    """Rebuild the child's ``ProcessImageParams`` from ``_isolated_worker_spec`` output."""
    overrides = cast("Mapping[str, JsonLike]", spec.get("overrides") or {})
    max_tokens = overrides.get("max_tokens")
    temperature = overrides.get("temperature")
    timeout = overrides.get("timeout")
    verbose = overrides.get("verbose")
    return _process_image_params_from_args(
        args,
        model_identifier=str(spec["model_identifier"]),
        image_path=Path(str(spec["image_path"])),
        prompt=str(spec["prompt"]),
        max_tokens=max_tokens
        if isinstance(max_tokens, int) and not isinstance(max_tokens, bool)
        else None,
        temperature=float(temperature)
        if isinstance(temperature, (int, float)) and not isinstance(temperature, bool)
        else None,
        timeout=float(timeout)
        if isinstance(timeout, (int, float)) and not isinstance(timeout, bool)
        else None,
        verbose=verbose if isinstance(verbose, bool) else None,
    )


def _run_model_isolated(args: argparse.Namespace, params: ProcessImageParams) -> PerformanceResult:
    """Run one model in a fresh child interpreter and return its PerformanceResult.

    A child that dies natively (segfault, abort, ``PyThreadState_Get``) becomes a
    phase-tagged crash record for that model — built through the same failure
    path as an in-process exception — instead of ending the sweep. The child
    reports the phase it reached through a progress file so the crash is
    attributed to ``model_load`` / ``decode`` / ... rather than "unknown".
    """
    deadline_s = params.timeout + _ISOLATION_TIMEOUT_GRACE_SECONDS
    with tempfile.TemporaryDirectory(prefix="check_models_worker_") as tmp:
        tmp_dir = Path(tmp)
        spec_path = tmp_dir / "spec.json"
        result_path = tmp_dir / "result.json"
        phase_path = tmp_dir / "phase.txt"
        stderr_path = tmp_dir / "stderr.txt"
        _write_text_file(spec_path, json.dumps(_isolated_worker_spec(args, params)))
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            ISOLATED_WORKER_FLAG,
            str(spec_path),
        ]
        logger.debug("Isolated worker: %s", shlex_join(command))
        start = time.perf_counter()
        _write_text_file(stderr_path, "")
        timed_out = False
        returncode = 0
        with stderr_path.open("a", encoding="utf-8") as stderr_file:
            try:
                completed = subprocess.run(  # noqa: S603 - this interpreter, this script, a temp spec
                    command,
                    check=False,
                    stdout=None,
                    stderr=stderr_file,
                    timeout=deadline_s,
                )
            except subprocess.TimeoutExpired:
                # subprocess.run has already killed the child; classify below.
                timed_out = True
            else:
                returncode = completed.returncode
        stderr_text = _read_text_tail(stderr_path, _ISOLATED_STDERR_TAIL_CHARS)
        if stderr_text.strip():
            logger.debug("[isolated worker stderr] %s\n%s", params.model_identifier, stderr_text)
        current_phase = _read_text_tail(phase_path, 200).strip() or "unknown"
        if timed_out:
            return _isolated_failure_result(
                params,
                IsolatedWorkerTimeoutError(params.model_identifier, deadline_s, current_phase),
                stderr_text=stderr_text,
                current_phase=current_phase,
                start=start,
            )
        if returncode == 0 and result_path.is_file():
            try:
                payload = json.loads(_read_text_file(result_path))
                if isinstance(payload, dict):
                    return _performance_result_from_json(payload)
                detail = "result payload was not a JSON object"
            except (OSError, ValueError, TypeError) as error:
                detail = f"result payload unreadable: {error}"
        else:
            detail = (
                "see the worker stderr tail in the run log"
                if stderr_text.strip()
                else "no stderr was captured"
            )
        return _isolated_failure_result(
            params,
            IsolatedWorkerCrashError(params.model_identifier, returncode, detail),
            stderr_text=stderr_text,
            current_phase=current_phase,
            start=start,
        )


def _isolated_failure_result(
    params: ProcessImageParams,
    error: Exception,
    *,
    stderr_text: str,
    current_phase: str,
    start: float,
) -> PerformanceResult:
    """Build a phase-tagged failure for a child that crashed or timed out."""
    phase_timer = PhaseTimer()
    boundary: UpstreamBoundary = _advance_upstream_boundary("not_started", current_phase)
    result_payload, stop_reason = _build_exception_process_result(
        params=params,
        error=error,
        stdout_text="",
        stderr_text=stderr_text,
        current_phase=current_phase,
        phase_timer=phase_timer,
        total_start_time=start,
        upstream_boundary=boundary,
    )
    return _finalize_process_result(
        result_payload=result_payload,
        params=params,
        phase_timer=phase_timer,
        stop_reason=stop_reason,
        current_phase=current_phase,
        total_start_time=start,
        upstream_boundary=boundary,
    )


def _read_text_tail(path: Path, max_chars: int) -> str:
    """Return up to the last ``max_chars`` of a regular text file, or '' when absent."""
    try:
        text = _read_text_file(path)
    except (OSError, ValueError):
        return ""
    return text[-max_chars:]


def _run_isolated_worker(spec_path: Path) -> int:
    """Child entry point: run one model from a spec file and write its result JSON."""
    global _ISOLATION_PHASE_SINK  # noqa: PLW0603 - process-local hook for this worker only
    # The parent created the spec's directory; the child only ever touches
    # sibling files there, never paths named inside the spec.
    worker_dir = spec_path.resolve().parent
    spec = json.loads(_read_text_file(spec_path))
    args = _namespace_from_json(spec["args"])
    phase_path = worker_dir / "phase.txt"
    result_path = worker_dir / "result.json"
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    def _record_phase(phase: str) -> None:
        try:
            _write_text_file(phase_path, phase)
        except OSError:
            logger.debug("Unable to record worker phase %s", phase, exc_info=True)

    _ISOLATION_PHASE_SINK = _record_phase
    crash_model = os.environ.get(ISOLATION_CRASH_TEST_ENV)
    if crash_model and crash_model == str(spec["model_identifier"]):
        # Test seam: prove a native abort in a child becomes a per-model record.
        _record_phase("decode")
        os.abort()
    load_quality_config(getattr(args, "quality_config", None))
    result = process_image_with_model(_isolated_params_from_spec(spec, args))
    _write_text_file(result_path, json.dumps(_performance_result_to_json(result)))
    return 0


def process_image_with_model(params: ProcessImageParams) -> PerformanceResult:
    """Process an image with a Vision Language Model, managing stats and errors."""
    stdout_capture = _TeeCaptureStream(sys.stdout)
    stderr_capture = _TeeCaptureStream(sys.stderr)
    telemetry_sampler, telemetry_probes = _start_system_telemetry(params)
    telemetry: SystemTelemetryRecord | None = None

    # Track overall timing
    total_start_time = time.perf_counter()
    current_phase: str = "input_validation"
    phase_timer = PhaseTimer()
    result_payload: PerformanceResult | None = None
    stop_reason: str | None = None
    cleanup_requires_sync = True
    upstream_boundary: UpstreamBoundary = "not_started"
    post_cleanup_active_memory_gb, post_cleanup_cache_memory_gb = None, None

    def _update_phase(phase: str) -> None:
        nonlocal current_phase, upstream_boundary
        current_phase = _normalise_failure_phase(phase) or phase
        upstream_boundary = _advance_upstream_boundary(upstream_boundary, current_phase)
        if _ISOLATION_PHASE_SINK is not None:
            _ISOLATION_PHASE_SINK(current_phase)

    try:
        _update_phase("input_validation")
        with phase_timer.track("input_validation"):
            validate_temperature(temp=params.temperature)
            validate_image_accessible(image_path=params.image_path)
        if params.verbose:
            logger.debug(
                "[verbose passthrough start] mlx-vlm.generate output for %s",
                params.model_identifier,
            )

        with (
            redirect_stdout(cast("TextIO", stdout_capture)),
            redirect_stderr(cast("TextIO", stderr_capture)),
            TimeoutManager(params.timeout),
        ):
            output: GenerationResult | SupportsGenerationResult = _run_model_generation(
                params=params,
                phase_callback=_update_phase,
                phase_timer=phase_timer,
            )
            cleanup_requires_sync = False
        if params.verbose:
            logger.debug(
                "[verbose passthrough end] mlx-vlm.generate output for %s",
                params.model_identifier,
            )
        result_payload, stop_reason = _build_success_process_result(
            params=params,
            output=output,
            phase_timer=phase_timer,
            total_start_time=total_start_time,
            upstream_boundary=upstream_boundary,
            stdout_text=stdout_capture.getvalue(),
            stderr_text=stderr_capture.getvalue(),
        )
    except (KeyboardInterrupt, SystemExit):
        # Never swallow operator interrupts or explicit exits: the sweep must
        # stop, not record the model as failed and continue.
        raise
    except Exception as e:  # noqa: BLE001 - per-model isolation boundary
        # This is the boundary that keeps one model's failure from aborting the
        # whole sweep. Processors and upstream APIs can raise anything
        # (TypeError, KeyError, AttributeError, custom errors); anticipating
        # each is brittle, so record any exception as a phase-tagged failure
        # with its traceback and move on to the next model.
        result_payload, stop_reason = _build_exception_process_result(
            params=params,
            error=e,
            stdout_text=stdout_capture.getvalue(),
            stderr_text=stderr_capture.getvalue(),
            current_phase=current_phase,
            phase_timer=phase_timer,
            total_start_time=total_start_time,
            upstream_boundary=upstream_boundary,
        )
    finally:
        # Always retain tee'd model console output in the file log (success and failure).
        # This is independent of --verbose: the terminal already saw the live stream.
        _log_stream_capture_to_file(
            model_identifier=params.model_identifier,
            stdout_text=stdout_capture.getvalue(),
            stderr_text=stderr_capture.getvalue(),
        )
        _update_phase("cleanup")
        with phase_timer.track("cleanup"):
            _cleanup_runtime_resources(synchronize_first=cleanup_requires_sync)
        post_cleanup_active_memory_gb, post_cleanup_cache_memory_gb = (
            _sample_post_cleanup_memory_gb()
        )
        telemetry = _finish_system_telemetry(telemetry_sampler, telemetry_probes)

    final_result = _finalize_process_result(
        result_payload=result_payload,
        params=params,
        phase_timer=phase_timer,
        stop_reason=stop_reason or "exception",
        current_phase=current_phase,
        total_start_time=total_start_time,
        upstream_boundary=upstream_boundary,
        post_cleanup_active_memory_gb=post_cleanup_active_memory_gb,
        post_cleanup_cache_memory_gb=post_cleanup_cache_memory_gb,
    )
    return _attach_system_telemetry(final_result, telemetry, params.model_identifier)


# =============================================================================
# SECTION: CLI RUN HELPERS & LOGGING
# =============================================================================


def print_cli_header(title: str) -> None:
    """Print a formatted CLI header with the given title."""
    width = get_terminal_width(max_width=100)
    log_rule(width, char="=", style="blue", bold=True)
    logger.info(
        title,
        extra={"style_hint": LogStyles.HEADER, "style_width": width},
    )
    log_rule(width, char="=", style="blue", bold=True)


def print_cli_section(title: str, *, show_rule: bool = True) -> None:
    """Print a formatted CLI section header with visual prefix."""
    width = get_terminal_width(max_width=100)
    if show_rule:
        log_rule(width, char="─", style="blue")
    logger.info(
        title,
        extra={
            "style_hint": LogStyles.SECTION,
            "style_uppercase": "\x1b[" not in title,
        },
    )


def print_cli_error(msg: str) -> None:
    """Print a formatted CLI error message."""
    logger.error(msg, extra={"style_hint": LogStyles.ERROR})


def exit_with_cli_error(
    msg: str,
    *,
    exit_code: int = 1,
    suppress_cause: bool = False,
    cause: BaseException | None = None,
) -> NoReturn:
    """Log a CLI-friendly error message and terminate the program."""
    print_cli_error(msg)
    if suppress_cause:
        raise SystemExit(exit_code) from None
    if cause is not None:
        raise SystemExit(exit_code) from cause
    raise SystemExit(exit_code)


def _log_styled(level: int, msg: str, *, prefix: str, separator: str, style_hint: str) -> None:
    """Log one styled status message with an optional emoji prefix."""
    formatted_msg = f"{prefix}{separator}{msg}" if prefix else msg
    logger.log(level, formatted_msg, extra={"style_hint": style_hint})


def log_success(msg: str, *, prefix: str = "✓") -> None:
    """Log a success message with green styling and optional prefix."""
    _log_styled(logging.INFO, msg, prefix=prefix, separator=" ", style_hint=LogStyles.SUCCESS)


def log_warning_note(msg: str, *, prefix: str = "⚠\ufe0f") -> None:
    """Log a warning note (non-error condition worth noting)."""
    _log_styled(logging.WARNING, msg, prefix=prefix, separator="  ", style_hint=LogStyles.WARNING)


def log_failure(msg: str, *, prefix: str = "✗") -> None:
    """Log a failure message with red styling and optional prefix."""
    _log_styled(logging.ERROR, msg, prefix=prefix, separator=" ", style_hint=LogStyles.ERROR)


def log_metric_label(label: str, *, emoji: str = "", indent: str = "") -> None:
    """Log a metric category label (e.g., '🔢 Tokens:') with consistent styling."""
    formatted = f"{indent}{label}"
    logger.info(
        formatted,
        extra={"style_hint": LogStyles.METRIC_LABEL, "style_emoji": emoji},
    )


def log_generated_text(
    text: str,
    *,
    wrap: bool = True,
    indent: str = "",
    max_lines: int | None = None,
) -> None:
    """Log generated model output with cyan styling and optional wrapping.

    Preserves original line breaks in the text. Each line is wrapped independently
    to terminal width if needed.

    Args:
        text: The generated text to display
        wrap: Whether to wrap long lines to terminal width
        indent: Indentation prefix for each line
        max_lines: Maximum number of lines to log (truncates if exceeded)
    """
    lines = text.splitlines()
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("... (truncated)")

    if wrap:
        width = get_terminal_width(max_width=100)
        avail_width = max(20, width - len(indent))

        for line in lines:
            if not line.strip():
                logger.info("", extra={"style_hint": LogStyles.GENERATED_TEXT})
                continue

            if len(line) <= avail_width:
                formatted = f"{indent}{line}"
                logger.info(formatted, extra={"style_hint": LogStyles.GENERATED_TEXT})
            else:
                wrapped = textwrap.wrap(
                    line,
                    width=avail_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                ) or [line]
                for wrapped_line in wrapped:
                    formatted = f"{indent}{wrapped_line}"
                    logger.info(formatted, extra={"style_hint": LogStyles.GENERATED_TEXT})
    else:
        for line in lines:
            formatted = f"{indent}{line}"
            logger.info(formatted, extra={"style_hint": LogStyles.GENERATED_TEXT})


def log_model_name(name: str, *, label: str = "") -> None:
    """Log a model identifier with magenta highlight.

    Args:
        name: The model identifier/name
        label: Optional label prefix (e.g., 'Model:')
    """
    if label:
        # Split formatting: plain label + styled name
        msg = "%s %s"
        logger.info(
            msg,
            label,
            name,
            extra={"style_hint": LogStyles.MODEL_NAME},
        )
    else:
        logger.info(name, extra={"style_hint": LogStyles.MODEL_NAME})


def log_file_path(path: Path | str, *, label: str = "", style: str = "cyan") -> None:
    """Log a file path with highlighting.

    Args:
        path: The file path to display
        label: Optional label prefix (e.g., '   HTML:')
        style: Rich style to use for the path
    """
    path_str = str(path)
    if label:
        msg = "%s %s"
        logger.info(
            msg,
            label,
            path_str,
            extra={"style_hint": LogStyles.FILE_PATH, "style_override": style},
        )
    else:
        logger.info(
            path_str,
            extra={"style_hint": LogStyles.FILE_PATH, "style_override": style},
        )


def log_blank(count: int = 1) -> None:
    """Log blank lines for spacing.

    Args:
        count: Number of blank lines to emit
    """
    for _ in range(count):
        logger.info("")


def _render_rich_lines(renderable: ConsoleRenderable, *, width: int | None = None) -> list[str]:
    """Render a Rich object to plain text lines for logger/file-log parity."""
    stream = io.StringIO()
    render_console = Console(
        file=stream,
        width=width or get_terminal_width(max_width=120),
        no_color=True,
        force_terminal=False,
        markup=False,
        highlight=False,
        emoji=True,
    )
    render_console.print(renderable)
    return stream.getvalue().splitlines()


def _log_rich_renderable(
    renderable: ConsoleRenderable,
    *,
    indent: str = "",
    width: int | None = None,
) -> None:
    """Log a Rich-rendered table/panel while keeping persisted logs plain."""
    # When no explicit width is given, subtract the log-handler prefix (timestamp
    # + level column) and indent from the terminal width so rendered rows don't
    # wrap once the handler prepends its own prefix to each logged line.
    render_width = width or max(
        40, get_terminal_width(max_width=120) - _RICH_LOG_PREFIX_WIDTH - len(indent)
    )
    for line in _render_rich_lines(renderable, width=render_width):
        logger.info("%s%s", indent, line)


type RichJustify = Literal["left", "center", "right"]


def _log_rich_table(
    *,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    justifications: Sequence[RichJustify] | None = None,
    max_widths: Sequence[int | None] | None = None,
    no_wrap_headers: frozenset[str] = frozenset(),
    indent: str = "   ",
) -> None:
    """Log a Rich table from plain rows with consistent console/file behavior."""
    table = Table(box=box.ROUNDED, show_lines=False, expand=False)
    for index, header in enumerate(headers):
        justify = (
            justifications[index] if justifications and index < len(justifications) else "left"
        )
        max_width = max_widths[index] if max_widths and index < len(max_widths) else None
        table.add_column(
            header,
            justify=justify,
            no_wrap=header in no_wrap_headers,
            max_width=max_width,
            overflow="fold",
        )
    for row in rows:
        table.add_row(*row)
    _log_rich_renderable(table, indent=indent)


type MetricTreeRow = tuple[str, str]


def _metric_tree_label(label: str, value: str) -> Text:
    """Build one Rich tree node for a key/value metric row."""
    text = Text()
    if label:
        text.append(_display_align(label, 12, alignment="left"), style="bold")
        text.append(" ")
    text.append(value)
    return text


def _log_metric_tree(
    title: str,
    rows: Sequence[MetricTreeRow],
    *,
    emoji: str = "",
    indent: str = "  ",
) -> None:
    """Log a Rich tree for grouped CLI metrics."""
    if not rows:
        return
    title_text = Text(f"{emoji} {title}" if emoji else title, style="bold white")
    tree = Tree(title_text, guide_style="dim")
    for label, value in rows:
        tree.add(_metric_tree_label(label, value))
    _log_rich_renderable(tree, indent=indent)


def _summary_parts(
    res: PerformanceResult,
    model_short: str,
    assessment: ResultAssessment,
) -> list[str]:
    """Assemble key=value summary segments for per-run triage."""
    parts: list[str] = [
        f"model={model_short}",
        f"execution={assessment.execution}",
        f"usability={assessment.usability}",
        f"maintainer={assessment.maintainer_status}",
    ]
    parts.append(
        f"observations={'+'.join(assessment.observations)}"
        if assessment.observations
        else "observations=none"
    )
    if res.error_stage:
        parts.append(f"stage={res.error_stage}")
    if res.failure_phase:
        parts.append(f"phase={res.failure_phase}")
    if res.error_code:
        parts.append(f"code={res.error_code}")
    if res.error_package:
        parts.append(f"package={res.error_package}")
    if res.error_type:
        parts.append(f"type={res.error_type}")
    return parts


def _quality_warning_messages(
    analysis: GenerationQualityAnalysis,
    generated_tokens: int | None,
) -> tuple[str, ...]:
    """Return the actionable mechanical warnings shared by console modes."""
    messages: list[str] = []
    if analysis.is_repetitive and analysis.repeated_token:
        messages.append(f"Repetitive: '{analysis.repeated_token}'")
    if analysis.missing_sections:
        messages.append(f"Labelled fields not detected: {', '.join(analysis.missing_sections)}")
    if analysis.thinking_trace_incomplete:
        messages.append("Expected thinking trace did not reach a final answer")
    if analysis.likely_capped and analysis.token_cap_reasons:
        messages.append(f"Output reached requested token limit ({generated_tokens} tokens)")
    if analysis.unexpected_special_tokens:
        messages.append(
            "Unexpected special token wrappers: "
            + ", ".join(analysis.unexpected_special_tokens[:2])
        )
    return tuple(messages)


def _log_quality_warnings(
    analysis: GenerationQualityAnalysis,
    generated_tokens: int | None,
) -> None:
    """Log the shared actionable warning set in stable severity order."""
    for message in _quality_warning_messages(analysis, generated_tokens):
        log_warning_note(message)


def _preview_generation(
    gen: StoredGenerationResult | None,
    *,
    analysis: GenerationQualityAnalysis | None = None,
    prompt: str | None = None,
) -> None:
    if not gen:
        return
    text_val = _generation_text_value(gen)
    gen_tokens = _generation_int_metric(gen, "generation_tokens")
    prompt_tokens = _generation_int_metric(gen, "prompt_tokens")
    if analysis is None:
        analysis = analyze_generation_text(
            text_val,
            gen_tokens,
            prompt_tokens=prompt_tokens,
            prompt=prompt,
        )

    if not text_val:
        log_metric_label("Generated Text:", emoji="📝")
        logger.info(
            "<empty>",
            extra={"style_hint": LogStyles.GENERATED_TEXT},
        )
        return

    _log_quality_warnings(analysis, gen_tokens)
    if analysis.likely_capped and not analysis.token_cap_reasons:
        # Same gate as the token_cap_truncation observation: a cap hit without
        # degradation evidence is neutral information, not a warning.
        logger.info("Output used the full requested token budget (%s tokens)", gen_tokens)

    # Show full output in trace (truncated in summary table)
    log_metric_label("Generated Text:", emoji="📝")
    log_generated_text(text_val, wrap=True)


def _log_verbose_success_details(
    res: PerformanceResult,
    *,
    analysis: GenerationQualityAnalysis | None = None,
    prompt: str | None = None,
) -> None:
    """Emit verbose block with warnings and metrics after the guard's live echo."""
    if not res.generation:
        return

    # Generated text was already streamed live by the repetition guard's
    # verbose echo inside the passthrough window; only its absence needs a
    # marker here.
    gen_text = getattr(res.generation, "text", None) or ""
    gen_tokens = _generation_int_metric(res.generation, "generation_tokens")

    if analysis is None:
        prompt_tokens = getattr(res.generation, "prompt_tokens", None)
        analysis = analyze_generation_text(
            gen_text,
            gen_tokens,
            prompt_tokens=prompt_tokens,
            prompt=prompt,
        )

    log_blank()

    _log_quality_warnings(analysis, gen_tokens)

    if not gen_text:
        log_metric_label("Generated Text:", emoji="📝")
        logger.info("   <empty>", extra={"style_hint": LogStyles.GENERATED_TEXT})

    log_blank()
    log_metric_label("Performance Metrics:", emoji="📊")
    _log_token_summary(res)
    _log_detailed_timings(res)
    log_blank()
    _log_perf_block(res)
    log_blank()
    _log_additional_diagnostics(res, gen_text)


def _log_token_summary(res: PerformanceResult) -> None:
    """Log tokens and generation TPS with tree structure for visual hierarchy."""
    if res.generation is None:
        return

    p_tokens = _generation_int_metric(res.generation, "prompt_tokens") or 0
    g_tokens = _generation_int_metric(res.generation, "generation_tokens") or 0
    tot_tokens = (p_tokens or 0) + (g_tokens or 0)
    gen_tps = _generation_float_metric(res.generation, "generation_tps") or 0.0
    prompt_tps = _generation_float_metric(res.generation, "prompt_tps") or 0.0

    _log_metric_tree(
        "Tokens:",
        (
            ("Prompt:", f"{fmt_num(p_tokens):>8} @ {fmt_num(prompt_tps)} tok/s"),
            ("Generated:", f"{fmt_num(g_tokens):>8} @ {fmt_num(gen_tps)} tok/s"),
            ("Total:", f"{fmt_num(tot_tokens):>8}"),
        ),
        emoji="🔢",
    )


def _log_detailed_timings(res: PerformanceResult) -> None:
    """Log detailed runtime timings and termination metadata with tree structure."""
    total_time_val = res.total_time
    generation_time_val = res.generation_time
    model_load_time_val = res.model_load_time
    runtime = res.runtime_diagnostics

    if not total_time_val or total_time_val <= 0:
        return
    total_time_seconds = total_time_val

    tt_val = format_field_value("total_time", total_time_val)
    tt_disp = tt_val if isinstance(tt_val, str) else _format_time_seconds(total_time_val)
    entries: list[tuple[str, str]] = [("Total:", f"{tt_disp:>8}")]

    def _append_phase_entry(
        *,
        label: str,
        value: float | None,
        field_name: str,
        include_pct: bool = True,
    ) -> None:
        if value is None or value <= 0:
            return
        formatted = format_field_value(field_name, value)
        display = formatted if isinstance(formatted, str) else _format_time_seconds(value)
        if include_pct:
            pct = value / total_time_seconds * 100
            entries.append((label, f"{display:>8} ({pct:>3.0f}%)"))
            return
        entries.append((label, f"{display:>8}"))

    _append_phase_entry(
        label="Generation:",
        value=generation_time_val,
        field_name="generation_time",
    )
    _append_phase_entry(
        label="Load:",
        value=model_load_time_val,
        field_name="model_load_time",
    )

    if runtime is not None:
        _append_phase_entry(
            label="Validation:",
            value=runtime.input_validation_time_s,
            field_name="total_time",
        )
        _append_phase_entry(
            label="Prompt prep:",
            value=runtime.prompt_prep_time_s,
            field_name="total_time",
        )
        _append_phase_entry(
            label="Cleanup:",
            value=runtime.cleanup_time_s,
            field_name="total_time",
        )
        _append_phase_entry(
            label="Upstream model prefill / first token:",
            value=runtime.first_token_latency_s,
            field_name="total_time",
            include_pct=False,
        )
        if runtime.stop_reason:
            entries.append(("Stop reason:", runtime.stop_reason))

    _log_metric_tree("Timing:", entries, emoji="⏱")


def _log_perf_block(res: PerformanceResult) -> None:
    """Log inner performance metrics (memory) with tree structure and emoji."""
    active_mem = getattr(res.generation, "active_memory", 0.0) or 0.0
    cached_mem = getattr(res.generation, "cache_memory", None)
    if not isinstance(cached_mem, int | float):
        cached_mem = getattr(res.generation, "cached_memory", 0.0)
    cached_mem = float(cached_mem or 0.0)
    peak_mem = getattr(res.generation, "peak_memory", 0.0) or 0.0

    # Only show memory section if at least one value is present
    if active_mem <= 0 and cached_mem <= 0 and peak_mem <= 0:
        return

    entries: list[MetricTreeRow] = []
    recommended_working_set_bytes = _get_recommended_working_set_bytes()

    def _append_mem(label: str, field: str, raw_val: float) -> None:
        if raw_val <= 0:
            return
        formatted = (
            _format_peak_memory_context(raw_val, recommended_working_set_bytes)
            if field == "peak_memory"
            else format_field_value(field, raw_val)
        )
        unit = "GB"
        text = (
            formatted
            if "recommended working set" in formatted or formatted.endswith(unit)
            else f"{formatted} GB"
        )
        entries.append((label, f"{text:>8}"))

    _append_mem("Active Δ:", "active_memory", active_mem)
    _append_mem("Cache Δ:", "cache_memory", cached_mem)
    _append_mem("Peak:", "peak_memory", peak_mem)
    _log_metric_tree("Memory:", entries, emoji="💾")


def _log_additional_diagnostics(
    res: PerformanceResult,
    gen_text: str,
) -> None:
    """Log retained mechanical output observations in detailed mode."""
    if not gen_text:
        return
    analysis = _quality_analysis_for_result(res)
    if analysis is not None:
        _log_metric_tree(
            "Output Observations:",
            (("Mechanical:", _format_quality_analysis_for_log(analysis)),),
            emoji="🔍",
        )


def log_metrics_legend() -> None:
    """Emit a one-time legend at the beginning of processing for clarity."""
    log_blank()
    panel = Panel(
        "Detailed mode: separate lines for timing, memory, tokens, TPS\n"
        "Warnings are shown for repetitive output and token-cap truncation.",
        title="📖 Metrics Legend",
        border_style="blue",
        box=box.ROUNDED,
    )
    _log_rich_renderable(panel, width=get_terminal_width(max_width=100))
    log_blank()


def _log_failure_details(result: PerformanceResult) -> None:
    """Emit actionable failure details for issue reporting."""
    if result.error_message:
        logger.info("Error: %s", result.error_message)

    if result.error_package:
        logger.info(
            "Error package: %s",
            result.error_package,
            extra={"style_hint": LogStyles.DETAIL},
        )
    if result.error_type:
        logger.info(
            "Error type: %s",
            result.error_type,
            extra={"style_hint": LogStyles.DETAIL},
        )

    traceback_tail = _format_traceback_tail(result.error_traceback)
    if traceback_tail:
        _log_wrapped_error("Traceback tail:", traceback_tail)

    captured_output = (result.captured_output_on_fail or "").strip()
    if captured_output:
        preview = _truncate_text_preview(
            captured_output,
            max_chars=MAX_CAPTURED_OUTPUT_LOG_CHARS,
        )
        _log_wrapped_error("Captured output:", preview)


def print_model_result(
    result: PerformanceResult,
    *,
    assessment: ResultAssessment | None = None,
    verbose: bool = False,
    run_index: int | None = None,
    total_runs: int | None = None,
    prompt: str | None = None,
) -> None:
    """Print a concise summary + optional verbose block for a model result."""
    resolved_assessment = assessment or _assess_result(result)
    run_prefix = "" if run_index is None else f"[RUN {run_index}/{total_runs}] "
    summary = (
        run_prefix
        + "SUMMARY "
        + " ".join(_summary_parts(result, result.model_name, resolved_assessment))
    )
    # Wrap summary to terminal width for readability
    width = get_terminal_width(max_width=100)
    for line in textwrap.wrap(summary, width=width, break_long_words=False, break_on_hyphens=False):
        if resolved_assessment.execution == "crashed":
            log_failure(line, prefix="")
        else:
            style = (
                LogStyles.WARNING
                if resolved_assessment.execution == "indeterminate"
                else LogStyles.DETAIL
            )
            logger.info(line, extra={"style_hint": style})
    if result.success and not verbose:  # quick exit with preview only
        _preview_generation(
            result.generation,
            analysis=result.quality_analysis,
            prompt=prompt,
        )
        return
    # For failures, show detailed error info; for success, show generation details
    if not result.success:
        log_blank()  # Single blank before error details
        _log_failure_details(result)
        return
    if result.generation and verbose:
        _log_verbose_success_details(
            result,
            analysis=result.quality_analysis,
            prompt=prompt,
        )


def print_cli_separator() -> None:
    """Print a visually distinct separator line using unicode box-drawing characters."""
    width = get_terminal_width(max_width=100)
    log_rule(width, char="─", style="blue")


def _dump_environment_to_log(output_path: Path) -> bool:
    """Dump complete Python environment to separate file for debugging/reproducibility.

    Captures output from pip freeze (and conda list if in conda environment)
    to provide complete package manifest for issue reproduction.

    Args:
        output_path: Path where the environment log should be written

    Returns:
        Whether this run actually wrote the log. A pre-existing file from an
        earlier run must never be presented as a current artifact, so callers
        record this signal instead of checking ``Path.exists()``.
    """
    try:
        # Detect if we're in a conda environment
        conda_env = os.environ.get("CONDA_DEFAULT_ENV")
        env_log_path = output_path
        env_lines = [
            "=" * 80,
            f"FULL ENVIRONMENT DUMP - {local_now_str()}",
            "=" * 80,
            "",
        ]

        # Use importlib.metadata (standard library) instead of subprocess calling pip/conda
        # to avoid S603 security lints and provide faster, more reliable dumping.
        try:
            # Read Name/Version via metadata.get: a dist-info husk without a
            # METADATA file has neither, and the .name/.version properties'
            # implicit-None path emits DeprecationWarnings on Python 3.13.
            def _get_name_version(d: Distribution) -> tuple[str, str]:
                meta = d.metadata
                if meta is None:
                    return "<unknown>", "<unknown>"
                return (
                    meta.get("Name") or "<unknown>",
                    meta.get("Version") or "<unknown>",
                )

            dists = sorted(
                (_get_name_version(d) for d in distributions()),
                key=lambda name_version: name_version[0].lower(),
            )
            env_lines.extend(
                [
                    "--- Python Packages (via importlib.metadata) ---",
                    f"Total packages: {len(dists)}",
                    "",
                ]
            )
            env_lines.extend(f"{name}=={dist_version}" for name, dist_version in dists)
            env_lines.append("")
        except (OSError, ValueError, RuntimeError) as dist_err:
            env_lines.append(f"Could not gather package list: {dist_err}")

        # Log conda environment name if applicable
        if conda_env:
            env_lines.append(f"Conda Environment: {conda_env}")

        env_lines.extend(
            [
                "=" * 80,
                f"Environment dump completed at {local_now_str()}",
                "=" * 80,
            ]
        )
        _write_text_file(env_log_path, "\n".join(env_lines) + "\n")

        # Log single line pointing to the file
        log_metric_label("Full environment dump written to:", emoji="📝")
        log_file_path(str(env_log_path))
        logger.debug("Environment details saved for reproducibility")

    except (OSError, FileNotFoundError, subprocess.SubprocessError) as e:
        logger.warning("Failed to dump environment info: %s", e)
        return False
    return True


def setup_environment(args: argparse.Namespace) -> LibraryVersionDict:
    """Configure logging, collect versions, print warnings."""
    # Apply CLI output preferences before constructing the Rich console handler.
    _apply_cli_output_preferences(args)

    # Set DEBUG if verbose, else INFO
    console_log_level: int = logging.DEBUG if args.verbose else logging.INFO
    # Remove all handlers and add console + file handlers
    logger.handlers.clear()

    # Rich console handler handles terminal width, color/no-color mode, and tracebacks.
    console_handler = _make_console_log_handler(
        level=console_log_level,
        verbose=bool(args.verbose),
        width=get_terminal_width(max_width=120),
    )
    logger.addHandler(console_handler)

    # File handler - write to specified log file (overwritten each run).
    # Skipped for --dry-run: no models are invoked, and overwriting the
    # retained log/environment artifacts of a real run would desynchronize
    # them from the run's other tracked outputs.
    if not args.dry_run:
        log_file: Path = _resolve_report_output_paths(args).log
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler: logging.FileHandler = logging.FileHandler(
            log_file,
            mode="w",
            encoding="utf-8",
        )
        # File gets full timestamp + level always (no colors in file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter: logging.Formatter = FileSafeFormatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt=LOCAL_TIMESTAMP_FORMAT,
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Logger captures everything so file handler gets debug info
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent double logging

    if args.verbose:
        logger.debug("Verbose/debug mode enabled.")

    # Dump full environment to log file for reproducibility (after logging setup)
    if not args.dry_run:
        # Recorded on args so finalisation reports the environment log as a
        # current artifact only when this run actually wrote it.
        args.environment_logged = _dump_environment_to_log(
            _resolve_report_output_paths(args).environment
        )

    # Note extra framework installs that are not part of the normal MLX path.
    st_present = bool(find_spec("sentence_transformers"))
    if st_present:
        logger.debug(
            "Detected 'sentence-transformers'. It's not used here by default and may "
            "import heavy backends.",
        )

    library_versions: LibraryVersionDict = get_library_versions()
    preflight_issues = _collect_preflight_package_issues(library_versions)
    _set_run_preflight_issues(args, preflight_issues)
    if preflight_issues:
        logger.warning("Detected upstream package compatibility risks:")
        for issue in preflight_issues:
            logger.warning("  - %s", issue)

    if args.verbose:
        print_version_info(library_versions)

    if args.trust_remote_code:
        print_cli_separator()
        log_warning_note("SECURITY WARNING: --trust-remote-code is enabled.")
        log_warning_note("This allows execution of remote code and may pose security risks.")

    return library_versions


def _set_run_preflight_issues(args: argparse.Namespace, issues: Sequence[str]) -> None:
    """Store preflight warning strings on argparse namespace for later reporting."""
    setattr(args, _PREFLIGHT_ISSUES_ARG_ATTR, tuple(issue for issue in issues))


def _get_run_preflight_issues(args: argparse.Namespace | None) -> tuple[str, ...]:
    """Read preflight warning strings from argparse namespace."""
    if args is None:
        return ()
    raw = getattr(args, _PREFLIGHT_ISSUES_ARG_ATTR, ())
    if isinstance(raw, tuple):
        return tuple(str(item) for item in raw)
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    return ()


def _raise_for_missing_runtime_dependencies() -> None:
    """Raise a fatal runtime error when core inference dependencies are unavailable."""
    transformers_version = get_library_versions().get("transformers")
    if transformers_version is None:
        MISSING_DEPENDENCIES.setdefault(
            "transformers",
            (
                "Core dependency missing: transformers. "
                f"Please install transformers>={PROJECT_MIN_TRANSFORMERS_VERSION}."
            ),
        )
    elif not _is_version_at_least(transformers_version, PROJECT_MIN_TRANSFORMERS_VERSION):
        MISSING_DEPENDENCIES["transformers"] = (
            f"Core dependency too old: transformers=={transformers_version}. "
            f"Need transformers>={PROJECT_MIN_TRANSFORMERS_VERSION}."
        )
    if not MISSING_DEPENDENCIES:
        return

    for dependency_name, message in sorted(MISSING_DEPENDENCIES.items()):
        logger.critical("[%s] %s", dependency_name, message)
    missing_list = ", ".join(sorted(MISSING_DEPENDENCIES))
    error_message = (
        f"Required runtime dependencies unavailable: {missing_list}. "
        "Install/repair these packages before running model checks."
    )
    raise RuntimeError(error_message)


# Path() collapses "://" to ":/", so a URL given to --image arrives as
# "https:/host/...". Require a scheme of at least two characters so a
# single-letter drive spec such as "C:/" is never mistaken for a URL.
_URL_LIKE_IMAGE_ARG_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9+.-]+:/", re.IGNORECASE)


def _reject_url_image_argument(image: Path) -> None:
    """Fail clearly when --image is given a URL instead of a local file path.

    argparse has already wrapped the value in a Path, so resolving and opening
    it would otherwise surface only a confusing ENOENT for a mangled path.
    """
    raw = str(image)
    if not _URL_LIKE_IMAGE_ARG_RE.match(raw):
        return
    exit_with_cli_error(
        f"--image expects a local file path, not a URL ({raw}). Download the file "
        "first (for a GitHub link use the /raw/ form), pass its path to --image, and "
        "optionally record the public location with --image-source-url so issue "
        "drafts get a complete reproduction command. Exiting.",
    )


def find_and_validate_image(args: argparse.Namespace) -> Path:
    """Find and validate the image file to process from arguments."""
    if getattr(args, "image", None) is not None:
        _reject_url_image_argument(args.image)
        return _validate_selected_image(args.image.resolve())

    folder_path: Path = args.folder.resolve()
    log_file_path(str(folder_path), label="Scanning folder:")
    if not folder_path.is_dir():
        exit_with_cli_error(f"Folder '{folder_path}' does not exist. Exiting.")
    most_recent_path: Path | None = find_most_recent_file(folder_path)
    if most_recent_path is None:
        exit_with_cli_error(
            f"Could not find the most recent image file in {folder_path}. Exiting.",
        )
        raise SystemExit  # pragma: no cover
    return _validate_selected_image(most_recent_path.resolve())


def _validate_selected_image(image_path: Path) -> Path:
    """Verify one selected image and return its resolved path."""
    log_file_path(str(image_path), label="Image File:     ")
    try:
        with Image.open(image_path) as image:
            image.verify()
        print_image_dimensions(image_path)
    except (FileNotFoundError, UnidentifiedImageError, OSError) as image_error:
        exit_with_cli_error(
            f"Cannot open or verify image {image_path}: {image_error}. Exiting.",
            suppress_cause=True,
        )
    return image_path


def handle_metadata(image_path: Path, args: argparse.Namespace) -> MetadataDict:
    """Extract, print, and return image metadata."""
    print_cli_section("Image Metadata")

    # Single EXIF extraction shared by metadata and verbose pretty-print
    exif_data: ExifDict | None = get_exif_data(image_path)
    metadata: MetadataDict = extract_image_metadata(
        image_path,
        exif_data=exif_data if exif_data is not None else EXIF_NOT_EXTRACTED,
    )

    # Display key metadata (fallback to empty at presentation time)
    logger.info("Date: %s", metadata.get("date") or "")
    logger.info("Description: %s", metadata.get("description") or "")
    logger.info("GPS Location: %s", metadata.get("gps") or "")
    if metadata.get("title"):
        logger.info("Title: %s", metadata["title"])
    if metadata.get("keywords"):
        logger.info("Keywords: %s", metadata["keywords"])

    if args.verbose:
        # Reuse already-extracted EXIF data (no second image open)
        if exif_data:
            pretty_print_exif(exif_data, show_all=True)
        else:
            logger.info("No detailed EXIF data available.")
    return metadata


def _resolve_eval_mode(
    eval_mode: str,
    metadata: Mapping[str, str | None] | None,
) -> EvaluationLane:
    """Resolve automatic and legacy aliases to one concrete evaluation lane."""
    match eval_mode:
        case "triage" | "blind" | "assisted":
            return eval_mode
        case "auto":
            return "assisted" if _metadata_has_descriptive_reference(metadata) else "blind"
        case _:
            msg = f"Unsupported evaluation mode: {eval_mode}"
            raise ValueError(msg)


def _apply_eval_mode_defaults(
    args: argparse.Namespace,
    metadata: Mapping[str, str | None] | None,
) -> None:
    """Apply metadata-aware eval-mode and token-cap defaults to parsed CLI args."""
    requested_eval_mode = str(getattr(args, "eval_mode", DEFAULT_EVAL_MODE))
    if requested_eval_mode == "assisted" and not _metadata_has_descriptive_reference(metadata):
        msg = (
            "The assisted evaluation lane requires descriptive metadata "
            "(even with --prompt, which overrides only the lane prompt)."
        )
        raise ValueError(msg)
    resolved_eval_mode = _resolve_eval_mode(requested_eval_mode, metadata)
    if requested_eval_mode == DEFAULT_EVAL_MODE:
        reason = (
            "descriptive image metadata found"
            if resolved_eval_mode == "assisted"
            else "no descriptive image metadata found"
        )
        logger.info("Auto eval mode selected '%s' (%s).", resolved_eval_mode, reason)
    if getattr(args, "prompt", None):
        logger.info(
            "--prompt overrides the '%s' lane prompt; the lane still governs the "
            "default token cap and report labeling.",
            resolved_eval_mode,
        )
    args.eval_mode = resolved_eval_mode
    args.assessment_profile = getattr(args, "assessment_profile", None) or (
        "general" if getattr(args, "prompt", None) or resolved_eval_mode == "triage" else "metadata"
    )

    # None marks "not set on the CLI": an explicit --max-tokens always wins, even
    # when it equals a lane default (the old value-comparison sentinel silently
    # replaced an explicit 500 with the triage cap).
    if getattr(args, "max_tokens", None) is not None:
        return
    args.max_tokens = TRIAGE_MAX_TOKENS if resolved_eval_mode == "triage" else DEFAULT_MAX_TOKENS


def _compact_prompt_text(value: str, *, max_chars: int) -> str:
    """Normalize whitespace and clip prompt context fields to a safe size."""
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _summarize_prompt_keywords(raw_keywords: str) -> str:
    """Return complete deduplicated keyword hints, bounded only by item count."""
    deduped_items: list[str] = []
    seen: set[str] = set()
    for item in raw_keywords.split(","):
        compact_item = _clean_metadata_text(item)
        if not compact_item:
            continue
        key = compact_item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped_items.append(compact_item)
        if len(deduped_items) >= QUALITY.prompt_keyword_max_items:
            break
    return ", ".join(deduped_items)


def _build_cataloguing_prompt(
    metadata: MetadataDict,
    *,
    include_metadata_hints: bool = True,
) -> str:
    provenance = _build_metadata_provenance(metadata if include_metadata_hints else None)
    parts: list[str]
    if include_metadata_hints:
        parts = [
            "Create British-English catalogue metadata from the image and supplied context.",
            "",
            (
                "Treat any capture date/time and GPS as authoritative facts, but do not claim "
                "they are visible. Descriptive hints may be incomplete or wrong: retain details "
                "supported by the image, correct conflicts, and add important visible details. "
                "Prefer image evidence when a hint conflicts, and omit uncertain details."
            ),
        ]
    else:
        parts = [
            (
                "Create British-English catalogue metadata using only clearly visible facts. "
                "Omit uncertain details and unsupported identity, location, event, brand, "
                "species, period, or intent."
            ),
        ]

    if provenance.has_authoritative_context:
        parts.extend(["", "Context: Authoritative context:"])
        capture_parts = [provenance.capture_date] if provenance.capture_date else []
        if provenance.capture_time and provenance.capture_time not in (
            provenance.capture_date or ""
        ):
            capture_parts.append(provenance.capture_time)
        capture_value = " ".join(capture_parts)
        if capture_value:
            parts.append(f"- Capture date/time: {capture_value}")
        if provenance.gps:
            parts.append(f"- GPS: {provenance.gps}")

    if provenance.has_draft:
        hint_heading = (
            "Descriptive hints:"
            if provenance.has_authoritative_context
            else "Context: Descriptive hints:"
        )
        parts.extend(["", hint_heading])
        if provenance.draft_title:
            title_hint = _compact_prompt_text(
                provenance.draft_title,
                max_chars=QUALITY.prompt_title_max_chars,
            )
            parts.append(f"- Title hint: {title_hint}")
        if provenance.draft_description:
            description_hint = _compact_prompt_text(
                provenance.draft_description,
                max_chars=QUALITY.prompt_description_max_chars,
            )
            parts.append(f"- Description hint: {description_hint}")
        if provenance.draft_keywords:
            keyword_hint = _summarize_prompt_keywords(", ".join(provenance.draft_keywords))
            if keyword_hint:
                parts.append(f"- Keyword hints: {keyword_hint}")

    description_requirement = (
        "- a 1-2-sentence factual description combining relevant context with the main visible "
        "subject, setting, action, lighting, and distinctive details;"
        if include_metadata_hints
        else "- a 1-2-sentence factual description of the main subject, setting, action, "
        "lighting, and distinctive details;"
    )
    keyword_requirement = (
        "- 10-18 unique, comma-separated keywords covering relevant context and visible details."
        if include_metadata_hints
        else "- 10-18 unique, comma-separated keywords."
    )
    parts.extend(
        [
            "",
            "Write:",
            "- a concrete 5-10-word title;",
            description_requirement,
            keyword_requirement,
            "",
            "Return exactly these three sections and nothing else:",
            "Title:",
            "Description:",
            "Keywords:",
        ]
    )

    return "\n".join(parts)


def prepare_prompt(args: argparse.Namespace, metadata: MetadataDict) -> str:
    """Prepare the prompt for the VLM, using user input or generating from metadata."""
    print_cli_section("Prompt Configuration")
    max_display_len = 200

    eval_mode = _resolve_eval_mode(str(getattr(args, "eval_mode", DEFAULT_EVAL_MODE)), metadata)

    prompt: str
    if args.prompt:
        prompt = args.prompt
        prompt_source = "custom (no automatic hints)"
        logger.info("Using user-provided prompt from --prompt.")
        logger.info(
            "User-provided prompt (--prompt): %s",
            _build_prompt_preview(prompt, max_chars=max_display_len),
        )
    elif eval_mode == "triage":
        prompt = TRIAGE_PROMPT
        prompt_source = "brief caption (no hints)"
        logger.info("Using triage-mode prompt (minimal context).")
    else:
        include_metadata_hints = eval_mode == "assisted"
        prompt_source = (
            "built-in (metadata hints)" if include_metadata_hints else "built-in (no hints)"
        )
        logger.info("Generating default prompt for the '%s' evaluation lane.", eval_mode)
        prompt = _build_cataloguing_prompt(
            metadata if include_metadata_hints else {},
            include_metadata_hints=include_metadata_hints,
        )
        logger.debug("Using generated %s-lane prompt.", eval_mode)
        logger.info(
            "Final prompt: %s",
            _build_prompt_preview(prompt, max_chars=max_display_len),
        )
    logger.debug("Full prompt:\n%s", prompt)
    logger.info("Prompt length: %d characters", len(prompt))
    logger.info(
        "Lane: %s | Prompt: %s | Assessment: %s | Max tokens: %s",
        eval_mode,
        prompt_source,
        getattr(args, "assessment_profile", None) or "unresolved",
        getattr(args, "max_tokens", None),
    )
    logger.info("Assessment: %s", _assessment_scope(getattr(args, "assessment_profile", None)))
    return prompt


def _hf_cache_file_name(cache_file: object) -> str:
    """Return the display filename for a Hugging Face cached file object."""
    file_name = getattr(cache_file, "file_name", None)
    if isinstance(file_name, str) and file_name:
        return PurePosixPath(file_name).name
    file_path = getattr(cache_file, "file_path", None)
    if file_path is not None:
        return Path(str(file_path)).name
    if isinstance(cache_file, str):
        return PurePosixPath(cache_file).name
    return ""


def _hf_cache_revision_files(revision: object) -> frozenset[str]:
    """Return basename set for the files attached to one cached revision."""
    files = getattr(revision, "files", ())
    return frozenset(
        file_name for cache_file in files if (file_name := _hf_cache_file_name(cache_file))
    )


def _hf_cache_main_revision_files(repo: object) -> frozenset[str] | None:
    """Return cached files for the repo's main revision, if present."""
    refs = getattr(repo, "refs", None)
    if isinstance(refs, Mapping) and "main" in refs:
        return _hf_cache_revision_files(refs["main"])

    for revision in getattr(repo, "revisions", ()):
        revision_refs = getattr(revision, "refs", ())
        if "main" in revision_refs:
            return _hf_cache_revision_files(revision)
    return None


def _hf_cache_main_snapshot_path(repo: object) -> Path | None:
    """Return the snapshot directory for the repo's main revision, if present."""
    refs = getattr(repo, "refs", None)
    if isinstance(refs, Mapping) and "main" in refs:
        snapshot = getattr(refs["main"], "snapshot_path", None)
        return Path(str(snapshot)) if snapshot else None
    for revision in getattr(repo, "revisions", ()):
        if "main" in getattr(revision, "refs", ()):
            snapshot = getattr(revision, "snapshot_path", None)
            return Path(str(snapshot)) if snapshot else None
    return None


def _mlx_vlm_package_root() -> Path | None:
    """Locate the installed mlx-vlm package directory without importing it."""
    try:
        spec = find_spec("mlx_vlm")
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _package_dir_names(root: Path) -> frozenset[str]:
    """Return the non-private package directories directly under ``root``."""
    if not root.is_dir():
        return frozenset()
    return frozenset(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and not entry.name.startswith(("_", "."))
    )


@functools.cache
def _installed_mlx_vlm_model_types() -> frozenset[str] | None:
    """Return model-type package dirs of the installed mlx-vlm without importing it."""
    root = _mlx_vlm_package_root()
    if root is None or not (root / "models").is_dir():
        return None
    return _package_dir_names(root / "models")


@functools.cache
def _mlx_vlm_drafter_model_types() -> frozenset[str]:
    """Model types the installed mlx-vlm treats as speculative drafters.

    Parsed from ``speculative/drafters/__init__.py`` (``DRAFTER_KIND_BY_MODEL_TYPE``)
    plus the drafter package directories, never by importing mlx. A drafter
    checkpoint is a target model's helper, not an image-to-text model; running
    it in the sweep would only produce a load crash misread as a model bug.
    """
    root = _mlx_vlm_package_root()
    if root is None:
        return frozenset()
    drafters_dir = root / "speculative" / "drafters"
    model_types = set(_package_dir_names(drafters_dir))
    try:
        tree = ast.parse((drafters_dir / "__init__.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return frozenset(model_types)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "DRAFTER_KIND_BY_MODEL_TYPE"
            for target in node.targets
        ):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                break
            if isinstance(value, dict):
                model_types.update(str(key).lower() for key in value)
    return frozenset(model_types)


_IMAGE_GENERATION_CLASS_FLAGS: Final[frozenset[str]] = frozenset(
    {"is_image_generation_model", "is_image_edit_model"}
)


@functools.cache
def _mlx_vlm_image_generation_model_types() -> frozenset[str]:
    """Model types whose upstream loader declares image generation or editing.

    Mirrors Nativ's capability manifest: each ``models/<type>/model.py`` class
    that sets ``is_image_generation_model`` or ``is_image_edit_model`` to True
    marks a family that produces images rather than text. Parsed from source
    without importing mlx; the package directory name and any literal
    ``model_type`` class attribute both count.
    """
    root = _mlx_vlm_package_root()
    if root is None:
        return frozenset()
    model_types: set[str] = set()
    for model_path in sorted((root / "models").glob("*/model.py")):
        try:
            tree = ast.parse(model_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            flagged = False
            literal_model_type: str | None = None
            for statement in node.body:
                target: ast.expr
                value: ast.expr | None
                if isinstance(statement, ast.AnnAssign):
                    target, value = statement.target, statement.value
                elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target, value = statement.targets[0], statement.value
                else:
                    continue
                if not isinstance(target, ast.Name) or not isinstance(value, ast.Constant):
                    continue
                if target.id in _IMAGE_GENERATION_CLASS_FLAGS and value.value is True:
                    flagged = True
                elif target.id == "model_type" and isinstance(value.value, str):
                    literal_model_type = value.value.strip().lower()
            if flagged:
                model_types.add(model_path.parent.name.lower())
                if literal_model_type:
                    model_types.add(literal_model_type)
    return frozenset(model_types)


@functools.cache
def _mlx_vlm_model_remapping() -> Mapping[str, str]:
    """Parse mlx-vlm's MODEL_REMAPPING alias table from source without importing mlx."""
    try:
        spec = find_spec("mlx_vlm")
    except (ImportError, ValueError):
        return {}
    if spec is None or not spec.submodule_search_locations:
        return {}
    utils_path = Path(next(iter(spec.submodule_search_locations))) / "utils.py"
    try:
        tree = ast.parse(utils_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "MODEL_REMAPPING":
                try:
                    value = ast.literal_eval(node.value)
                except ValueError:
                    return {}
                if isinstance(value, dict):
                    return {str(key): str(item) for key, item in value.items()}
    return {}


def _read_cached_repo_json(repo: object, file_name: str) -> dict[str, JsonLike] | None:
    """Read one bounded JSON metadata file from a cached repo's main snapshot.

    HF cache snapshots link files into blobs/ by design, so resolve the link
    but require containment inside this repo's cache directory before
    reading. Returns None when the file is absent, unreadable, or not an
    object.
    """
    snapshot = _hf_cache_main_snapshot_path(repo)
    if snapshot is None:
        return None
    return _read_snapshot_json(snapshot, file_name)


# Positive image-input evidence: keys mlx-vlm VLM configs carry (surveyed across
# every cached VLM family: vision_config plus image/vision token ids).
_IMAGE_INPUT_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "vision_config",
        "image_token_id",
        "image_token_index",
        "image_start_token_id",
        "image_end_token_id",
        "vision_start_token_id",
        "vision_end_token_id",
        "mm_vision_select_layer",
        "image_grid_pinpoints",
        "vision_soft_tokens_per_image",
    }
)
# Sequence-classifier reranker model types (mirrors mlx_vlm.reranker kinds).
_SEQUENCE_CLASSIFIER_RERANKER_TYPES: Final[frozenset[str]] = frozenset(
    {"bert", "modernbert", "xlm_roberta"}
)
# Architecture-name markers for text-generating models (surveyed across every
# cached VLM family) versus image-consuming architectures that do not generate
# text (segmentation, detection, classification, multimodal embedding).
_GENERATIVE_ARCH_MARKERS: Final[tuple[str, ...]] = (
    "ForConditionalGeneration",
    "ForCausalLM",
    "ForBlockDiffusion",
    "ChatModel",
    "ForVision2Seq",
    "ForImageTextToText",
)
_NON_GENERATIVE_IMAGE_ARCH_MARKERS: Final[tuple[str, ...]] = (
    "ForImageClassification",
    "ForObjectDetection",
    "ForSemanticSegmentation",
    "ForInstanceSegmentation",
    "ForUniversalSegmentation",
    "ForZeroShotImageClassification",
    "ForZeroShotObjectDetection",
    "ForImageSegmentation",
    "ForMaskedImageModeling",
    "ForDepthEstimation",
    "ForImageEmbedding",
    "CLIPModel",
    "SiglipModel",
)


def _meaningful_config_value(value: JsonLike) -> bool:
    """True when a config key carries real evidence (not null/empty/false)."""
    if value is None or value is False:
        return False
    if isinstance(value, (str, list, dict)):
        return bool(value)
    return True


def _speculative_drafter_signal(
    config: Mapping[str, JsonLike],
    *,
    model_type: str,
    architectures: tuple[str, ...],
) -> ImageCapability | None:
    """Recognise a speculative-decoding draft model (adapted from Nativ's discovery).

    Three signals: the installed mlx-vlm's drafter table, a DSpark projector
    stamp in ``dflash_config``, or a DSpark/DFlash/EAGLE-3 architecture name.
    A type that is also a full model family (upstream lists ``laguna`` as a
    drafter kind while shipping a laguna model loader) is not excluded on
    the table alone; the projector stamp or architecture must confirm it.
    """
    if model_type in _mlx_vlm_drafter_model_types() and (
        model_type not in (_installed_mlx_vlm_model_types() or frozenset())
    ):
        return ImageCapability(
            "no", "speculative_drafter", (f"model_type={model_type} is an mlx-vlm drafter",)
        )
    dflash_config = config.get("dflash_config")
    projector = dflash_config.get("projector_type") if isinstance(dflash_config, dict) else None
    if isinstance(projector, str) and projector.lower() == "dspark":
        return ImageCapability(
            "no", "speculative_drafter", (f"dflash_config.projector_type={projector}",)
        )
    drafter_arch = next(
        (a for a in architectures if any(m in a.lower() for m in ("dspark", "dflash", "eagle3"))),
        None,
    )
    if drafter_arch is not None:
        return ImageCapability("no", "speculative_drafter", (f"architectures={drafter_arch}",))
    return None


def _image_generation_family_signal(model_type: str) -> ImageCapability | None:
    """Recognise an image-producing family from upstream's loader class flags."""
    resolved_model_type = _mlx_vlm_model_remapping().get(model_type, model_type)
    if resolved_model_type not in _mlx_vlm_image_generation_model_types():
        return None
    return ImageCapability(
        "no",
        "image_or_video_generation",
        (
            (
                f"model_type={model_type} is flagged is_image_generation_model/"
                "is_image_edit_model by the installed mlx-vlm"
            ),
        ),
    )


def _capability_negative_signal(
    config: Mapping[str, JsonLike],
    *,
    model_type: str,
    architectures: tuple[str, ...],
) -> ImageCapability | None:
    """Return a confident non-image classification, or None if no such signal.

    Checks the most specific signals first. ``id2label``/``num_labels`` alone
    are NOT reranker signals — surveyed VLM configs carry them too — so the
    reranker rule requires a sequence-classifier model type or architecture.
    """
    if config.get("speculators_model_type"):
        return ImageCapability(
            "no",
            "speculative_drafter",
            (f"speculators_model_type={config['speculators_model_type']}",),
        )
    upstream_signal = _speculative_drafter_signal(
        config, model_type=model_type, architectures=architectures
    ) or _image_generation_family_signal(model_type)
    if upstream_signal is not None:
        return upstream_signal
    embeddings_meta = config.get("mlx_embeddings")
    if isinstance(embeddings_meta, dict) and embeddings_meta.get("kind") == "embedding":
        return ImageCapability("no", "embedding", ("mlx_embeddings.kind=embedding",))
    seq_arch = next((a for a in architectures if "ForSequenceClassification" in a), None)
    if model_type in _SEQUENCE_CLASSIFIER_RERANKER_TYPES or seq_arch is not None:
        evidence = (
            f"model_type={model_type}",
            *((f"architectures={seq_arch}",) if seq_arch else ()),
        )
        return ImageCapability("no", "reranker", evidence)
    has_image_keys = any(k in config for k in _IMAGE_INPUT_CONFIG_KEYS)
    pipeline_keys = ("unet_config", "vae_config", "transformer_config")
    if any(k in config for k in pipeline_keys) and not has_image_keys:
        return ImageCapability(
            "no",
            "image_or_video_generation",
            ("generation-pipeline config keys without image-input keys",),
        )
    return None


def _capability_from_image_evidence(
    config: Mapping[str, JsonLike],
    *,
    architectures: tuple[str, ...],
) -> ImageCapability | None:
    """Classify from image-input evidence; None when the config carries none.

    Only keys carrying real values count: FastVLM ships image_grid_pinpoints as
    null alongside genuine vision keys, and ``"vision_config": null`` must not
    be positive evidence on its own. A positive verdict also requires a
    text-generating architecture; image evidence without one is ``unknown``
    (still run), while known non-generative image architectures
    (classification, detection, segmentation, multimodal embedding) are a
    confident exclusion.
    """
    image_keys = tuple(
        sorted(k for k in _IMAGE_INPUT_CONFIG_KEYS if _meaningful_config_value(config.get(k)))
    )
    arch_text = " ".join(architectures)
    generative_arch = any(m in arch_text for m in _GENERATIVE_ARCH_MARKERS)
    non_generative_image_arch = next(
        (a for a in architectures if any(m in a for m in _NON_GENERATIVE_IMAGE_ARCH_MARKERS)),
        None,
    )
    if non_generative_image_arch is not None and not generative_arch:
        return ImageCapability(
            "no",
            "image_understanding_non_generative",
            (f"architectures={non_generative_image_arch}",),
        )
    if not image_keys:
        return None
    if generative_arch:
        return ImageCapability(
            "yes", "image_to_text", (f"image-input keys: {', '.join(image_keys)}",)
        )
    return ImageCapability(
        "unknown",
        "unknown",
        (
            f"image-input keys: {', '.join(image_keys)}",
            f"no generative-text architecture (architectures={arch_text or '?'})",
        ),
    )


_SENTENCE_TRANSFORMER_LAYOUT_FILES: Final[tuple[str, ...]] = (
    "modules.json",
    "1_Pooling/config.json",
    "sentence_bert_config.json",
)


def _embedding_layout_signal(repo: object) -> ImageCapability | None:
    """Classify sentence-transformers layouts as embeddings (Nativ heuristic).

    These repos carry a plain text-encoder config that the generative-arch
    rules would leave ``unknown`` (and therefore run); the layout files are
    an unambiguous embedding signal that needs no ``mlx_embeddings`` stamp.
    """
    snapshot = _hf_cache_main_snapshot_path(repo)
    if snapshot is None:
        return None
    present = tuple(
        name for name in _SENTENCE_TRANSFORMER_LAYOUT_FILES if (snapshot / name).is_file()
    )
    if not present:
        return None
    return ImageCapability(
        "no",
        "embedding",
        tuple(f"sentence-transformers layout file: {name}" for name in present),
    )


def _classify_image_capability(repo: object) -> ImageCapability:
    """Classify a cached repo's fit for the single-image description benchmark.

    Reads only bounded metadata already in the snapshot (config.json and, when
    present, model_index.json) and derives a tri-state verdict from explicit
    keys, model type, architectures, and task stamps. It never infers policy
    from repo names and never rejects an unfamiliar layout solely because its
    capability cannot be inferred (that is ``unknown``, which still runs).
    """
    model_index = _read_cached_repo_json(repo, "model_index.json")
    if model_index is not None:
        # Diffusers-style pipelines declare themselves in model_index.json.
        class_name = str(model_index.get("_class_name", "")) or "present"
        return ImageCapability(
            "no",
            "image_or_video_generation",
            (f"model_index.json _class_name={class_name}",),
        )
    config = _read_cached_repo_json(repo, "config.json")
    if config is None:
        return ImageCapability("unknown", "unknown", ("no readable config.json",))

    layout_signal = _embedding_layout_signal(repo)
    if layout_signal is not None:
        return layout_signal

    model_type = str(config.get("model_type") or "").lower().replace("-", "_")
    raw_architectures = config.get("architectures")
    architectures = (
        tuple(str(a) for a in raw_architectures if a) if isinstance(raw_architectures, list) else ()
    )
    negative = _capability_negative_signal(
        config, model_type=model_type, architectures=architectures
    )
    if negative is not None:
        return negative

    image_verdict = _capability_from_image_evidence(config, architectures=architectures)
    if image_verdict is not None:
        return image_verdict

    # No image-input evidence. Text-only mirrors upstream's _is_text_only_config
    # (no vision/audio/dflash config); audio-only takes audio but not images.
    generative_arch = any(m in " ".join(architectures) for m in _GENERATIVE_ARCH_MARKERS)
    has_audio = any(
        _meaningful_config_value(config.get(k)) for k in ("audio_config", "audio_token_id")
    )
    modality_keys = ("vision_config", "audio_config", "dflash_config")
    verdict: ImageCapability
    if has_audio and generative_arch:
        verdict = ImageCapability(
            "no", "audio_or_other_generation", ("audio_config present, no image-input keys",)
        )
    elif (
        model_type
        and generative_arch
        and not any(_meaningful_config_value(config.get(k)) for k in modality_keys)
    ):
        verdict = ImageCapability(
            "no", "text_only", (f"model_type={model_type}", "no vision_config/image token keys")
        )
    else:
        verdict = ImageCapability(
            "unknown",
            "unknown",
            (
                f"model_type={model_type or '?'}",
                "no image-input keys and no confident non-image signal",
            ),
        )
    return verdict


def _model_arch_precheck(repo: object) -> tuple[str | None, str | None, bool | None]:
    """Check the cached config's model_type against installed mlx-vlm model packages.

    Mirrors upstream's ``--check-arch`` tier: a file-presence and folder-name
    check only, never a proof that generation works. Returns
    ``(model_type, resolved_model_type, supported)`` where ``supported`` is
    ``None`` when indeterminate (no config, unreadable config, or no installed
    mlx-vlm package to compare against).
    """
    config = _read_cached_repo_json(repo, "config.json")
    if config is None:
        return None, None, None
    raw_model_type = config.get("model_type") or config.get("speculators_model_type")
    if not isinstance(raw_model_type, str) or not raw_model_type:
        return None, None, None
    model_type = raw_model_type.lower()
    resolved = _mlx_vlm_model_remapping().get(model_type, model_type)
    installed = _installed_mlx_vlm_model_types()
    if installed is None:
        return model_type, resolved, None
    return model_type, resolved, resolved in installed


def _cached_repo_model_eligibility(repo: object) -> CachedModelEligibility:
    """Classify whether a cached repo should be auto-run like mlx-vlm's server list."""
    repo_id = str(getattr(repo, "repo_id", ""))
    repo_type = str(getattr(repo, "repo_type", ""))
    reasons: list[str] = []

    if repo_type != "model":
        reasons.append(f"repo type is {repo_type!r}, not 'model'")

    main_files = _hf_cache_main_revision_files(repo)
    if main_files is None:
        reasons.append("missing main revision in cache")
    else:
        if "config.json" not in main_files:
            reasons.append("missing config.json")
        if "tokenizer_config.json" not in main_files:
            reasons.append("missing tokenizer_config.json")
        has_safetensors = "model.safetensors.index.json" in main_files or any(
            file_name.endswith(".safetensors") for file_name in main_files
        )
        if not has_safetensors:
            reasons.append("missing safetensors weights")
        elif "model.safetensors.index.json" in main_files:
            # An index downloads before its shards; require every referenced
            # shard to actually be present and non-empty (Nativ does the same).
            snapshot = _hf_cache_main_snapshot_path(repo)
            shard_status = _weight_shard_status(snapshot) if snapshot is not None else None
            if shard_status is not None:
                if shard_status.index_error is not None:
                    reasons.append(shard_status.index_error)
                elif shard_status.missing:
                    sample = ", ".join(shard_status.missing_sample)
                    reasons.append(
                        f"{shard_status.missing} of {shard_status.total} "
                        f"weight shards missing (e.g. {sample})"
                    )

    model_type, resolved_model_type, arch_supported = _model_arch_precheck(repo)
    return CachedModelEligibility(
        repo_id=repo_id,
        supported=not reasons,
        reasons=tuple(reasons),
        model_type=model_type,
        resolved_model_type=resolved_model_type,
        arch_supported=arch_supported,
        capability=_classify_image_capability(repo),
        thinking_template=_template_declares_thinking(_hf_cache_main_snapshot_path(repo)),
    )


def get_cached_model_eligibility() -> tuple[CachedModelEligibility, ...]:
    """Return supported/skipped classifications for Hugging Face cache repos.

    Memoised per cache scan (invalidated with the scan on refresh), so
    per-model callers do not re-read every repo's config.json.
    """
    state = _HF_CACHE_SCAN_STATE
    try:
        cache_info = _get_hf_cache_info_cached()
    except HFValidationError:
        logger.warning("Hugging Face cache directory invalid.")
        return ()
    except FileNotFoundError:
        logger.warning("Hugging Face cache directory not found.")
        return ()
    except (OSError, ValueError) as e:
        logger.warning("Unexpected error scanning Hugging Face cache: %s", e)
        return ()
    if state.eligibility is not None and state.eligibility_source_id == id(cache_info):
        return state.eligibility
    eligibility = tuple(
        sorted(
            (_cached_repo_model_eligibility(repo) for repo in cache_info.repos),
            key=lambda entry: entry.repo_id,
        )
    )
    state.eligibility = eligibility
    state.eligibility_source_id = id(cache_info)
    return eligibility


def _cache_discovery_records() -> list[CacheDiscoveryEntryRecord]:
    """Serialise every cached repo's classification for machine artifacts.

    Retained in the ``results.jsonl`` metadata header so downstream tools can
    distinguish an intentional non-test (capability exclusion) from a crash or
    an unavailable model.
    Skipped non-image models never enter the per-model results.
    """
    return [
        {
            "repo_id": entry.repo_id,
            "selected": entry.selected,
            "layout_supported": entry.supported,
            "layout_reasons": list(entry.reasons),
            "capability_verdict": entry.capability.verdict,
            "model_purpose": entry.capability.purpose,
            "capability_evidence": list(entry.capability.evidence),
            "skip_reasons": list(entry.skip_reasons),
            "model_type": entry.model_type,
            "arch_supported": entry.arch_supported,
            "thinking_template": entry.thinking_template,
        }
        for entry in get_cached_model_eligibility()
    ]


def _arch_precheck_for_model(model_id: str) -> tuple[str | None, str | None, bool | None]:
    """Return the cached-config architecture pre-check for one model id.

    Returns ``(model_type, resolved_model_type, supported)`` with all ``None``
    when the model is not in the local cache scan or the check is indeterminate.
    """
    for entry in get_cached_model_eligibility():
        if entry.repo_id == model_id:
            return entry.model_type, entry.resolved_model_type, entry.arch_supported
    return None, None, None


def _arch_precheck_summary(model_id: str) -> str | None:
    """Render the architecture pre-check as one human-readable fact value."""
    model_type, resolved, supported = _arch_precheck_for_model(model_id)
    if supported is None or model_type is None:
        return None
    resolved_note = f" via {resolved}" if resolved is not None and resolved != model_type else ""
    verdict = "yes" if supported else "no"
    return f"{verdict} (model_type {model_type}{resolved_note})"


def _all_cached_repo_ids() -> list[str]:
    """Return all cached repo IDs, including repos that auto-discovery will skip."""
    return sorted(entry.repo_id for entry in get_cached_model_eligibility())


def _warn_explicit_non_image_models(model_identifiers: Sequence[str]) -> None:
    """Warn when an explicitly requested cached model classifies as non-image."""
    by_id = {entry.repo_id: entry for entry in get_cached_model_eligibility()}
    for model_id in model_identifiers:
        entry = by_id.get(model_id)
        if entry is None or entry.capability.verdict != "no":
            continue
        logger.warning(
            "Explicitly requested %s classifies as non-image (%s); running outside the "
            "default benchmark scope, so interpret its result accordingly.",
            model_id,
            entry.capability.skip_reason,
        )


def _warn_explicit_incomplete_cache(
    model_identifiers: Sequence[str],
    *,
    requested_revision: str | None = None,
) -> int:
    """Warn when an explicitly requested model fails the cached-layout check.

    Explicit ``--models`` bypasses the default-discovery layout check, which
    inspects the cached *main* revision. A failure there means that revision
    is absent or incomplete — an interrupted download, or simply no cached
    ``main`` — not necessarily that the run will download anything: an
    explicitly requested ``--revision`` may already be complete. So the
    warning states the facts, says the run *may* need to download for the
    revision it will load (resumable, bounded by ``--timeout``), and gives a
    pre-fetch command for that revision. Returns the number of models warned.
    """
    by_id = {entry.repo_id: entry for entry in get_cached_model_eligibility()}
    revision_note = f"the requested revision {requested_revision}" if requested_revision else "it"
    revision_flag = f" --revision {requested_revision}" if requested_revision else ""
    warned = 0
    for model_id in model_identifiers:
        entry = by_id.get(model_id)
        if entry is None or entry.supported:
            continue
        warned += 1
        logger.warning(
            "Explicitly requested %s: its cached main revision fails the default-discovery "
            "layout check (%s), so the run may need to download files for %s (resumable, "
            "bounded by --timeout). Pre-fetch with `hf download %s%s` to keep the run "
            "offline.",
            model_id,
            "; ".join(entry.reasons),
            revision_note,
            model_id,
            revision_flag,
        )
    return warned


def _log_capability_unknown_warnings(entries: Sequence[CachedModelEligibility]) -> None:
    """Warn about selected repos whose image capability could not be inferred."""
    unknown = [
        entry for entry in entries if entry.selected and entry.capability.verdict == "unknown"
    ]
    if not unknown:
        return
    logger.warning(
        "%d selected cached repo(s) have unknown image capability (running anyway; "
        "interpret results with the evidence below):",
        len(unknown),
    )
    for entry in unknown:
        logger.warning("   - %s: %s", entry.repo_id, "; ".join(entry.capability.evidence))


def _supported_cached_model_ids_with_skipped_logging(
    eligibility: Iterable[CachedModelEligibility],
) -> list[str]:
    """Return selected cached model IDs and log every skipped repo with its reasons.

    Skips fall into two explicit classes: cache-layout failures (the mlx-vlm
    server-style file test) and capability exclusions (confident non-image
    model kinds). No cached repo disappears silently.
    """
    entries = tuple(eligibility)
    skipped = [entry for entry in entries if not entry.selected]
    if skipped:
        logger.warning(
            "Skipped %d cached repo(s) that default discovery will not run:",
            len(skipped),
        )
        for entry in skipped:
            reasons = entry.skip_reasons or ("unsupported cache layout",)
            logger.warning("   - %s: %s", entry.repo_id, "; ".join(reasons))
    _log_capability_unknown_warnings(entries)
    return sorted(entry.repo_id for entry in entries if entry.selected)


def get_cached_model_ids() -> list[str]:
    """Return cached model IDs selected by default discovery (layout + capability)."""
    return sorted(entry.repo_id for entry in get_cached_model_eligibility() if entry.selected)


def validate_model_identifier(model_id: str) -> None:
    """Validate model ID is well-formed (org/name format or existing local path).

    Args:
        model_id: Model identifier to validate

    Raises:
        ValueError: If model_id is empty, malformed, or local path doesn't exist

    """
    if not model_id or not model_id.strip():
        msg = "Model identifier cannot be empty"
        raise ValueError(msg)

    # Check if it's a local path (starts with / or ./ or ../)
    if model_id.startswith(("/", "./", "../")):
        model_path = Path(model_id)
        if not model_path.exists():
            msg = f"Local model path does not exist: {model_id}"
            raise ValueError(msg)
        if not model_path.is_dir():
            msg = f"Local model path is not a directory: {model_id}"
            raise ValueError(msg)
    elif " " in model_id:
        # Hub identifier: basic sanity checks
        msg = f"Model identifier contains spaces: '{model_id}'"
        raise ValueError(msg)
        # Optionally check for org/name format (though single names are valid too)
        # For now, just ensure it's not obviously malformed


def validate_and_warn_model_selection(args: argparse.Namespace) -> None:
    """Validate exclusions against local cache membership and current selection.

    Args:
        args: Parsed command line arguments

    """
    if not args.exclude:
        return  # No exclusions to validate

    cached_models = set(_all_cached_repo_ids())
    excluded_models: set[str] = set(args.exclude)
    ineffective_exclusions: set[str] = excluded_models - cached_models

    if ineffective_exclusions:
        ineffective_list = sorted(ineffective_exclusions)
        logger.warning(
            "The following excluded models are not in the local cache and will have no effect: %s",
            ", ".join(ineffective_list),
        )

    if not args.verbose:
        return

    if args.models:
        effective_exclusions = excluded_models & set(args.models)
        if effective_exclusions:
            logger.info(
                "Effective exclusions for this run (selected models that will be filtered out): %s",
                ", ".join(sorted(effective_exclusions)),
            )
        return

    effective_exclusions = excluded_models & set(get_cached_model_ids())
    if effective_exclusions:
        logger.info(
            "Effective exclusions (models that will be filtered out): %s",
            ", ".join(sorted(effective_exclusions)),
        )


def apply_exclusions(
    model_list: list[str],
    exclude_list: list[str],
    context: str,
) -> list[str]:
    """Apply exclusion list to models and log results.

    Args:
        model_list: List of model identifiers to filter
        exclude_list: List of models to exclude
        context: Description for logging (e.g., "explicit list", "cached models")

    Returns:
        Filtered list with excluded models removed

    """
    if not exclude_list:
        return model_list

    excluded_set = set(exclude_list)
    original_count = len(model_list)
    filtered = [model for model in model_list if model not in excluded_set]
    excluded_count = original_count - len(filtered)

    if excluded_count > 0:
        logger.info(
            "Excluded %d model(s) from %s. Remaining: %d model(s)",
            excluded_count,
            context,
            len(filtered),
        )

    return filtered


def _process_image_params_from_args(
    args: argparse.Namespace,
    *,
    model_identifier: str,
    image_path: Path,
    prompt: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
    verbose: bool | None = None,
) -> ProcessImageParams:
    """Build inference parameters once, with explicit per-run overrides."""
    return ProcessImageParams(
        model_identifier=model_identifier,
        image_path=image_path,
        prompt=prompt,
        max_tokens=args.max_tokens if max_tokens is None else max_tokens,
        temperature=args.temperature if temperature is None else temperature,
        timeout=args.timeout if timeout is None else timeout,
        verbose=args.verbose if verbose is None else verbose,
        trust_remote_code=args.trust_remote_code,
        top_p=args.top_p,
        min_p=args.min_p,
        top_k=args.top_k,
        repetition_penalty=args.repetition_penalty,
        repetition_context_size=args.repetition_context_size,
        seed=args.seed,
        presence_penalty=args.presence_penalty,
        presence_context_size=args.presence_context_size,
        frequency_penalty=args.frequency_penalty,
        frequency_context_size=args.frequency_context_size,
        logit_bias=args.logit_bias,
        lazy=args.lazy_load,
        max_kv_size=args.max_kv_size,
        kv_bits=args.kv_bits,
        kv_quant_scheme=args.kv_quant_scheme,
        kv_group_size=args.kv_group_size,
        quantized_kv_start=args.quantized_kv_start,
        kv_key_bits=args.kv_key_bits,
        kv_value_bits=args.kv_value_bits,
        kv_key_scheme=args.kv_key_scheme,
        kv_value_scheme=args.kv_value_scheme,
        force_download=args.force_download,
        quantize_activations=args.quantize_activations,
        revision=args.revision,
        adapter_path=args.adapter_path,
        prefill_step_size=args.prefill_step_size,
        resize_shape=args.resize_shape,
        eos_tokens=args.eos_tokens,
        skip_special_tokens=args.skip_special_tokens,
        processor_kwargs=args.processor_kwargs,
        enable_thinking=args.enable_thinking,
        thinking_budget=args.thinking_budget,
        thinking_mode=args.thinking_mode,
        thinking_start_token=args.thinking_start_token,
        thinking_end_token=args.thinking_end_token,
        auto_thinking_budget=getattr(args, "auto_thinking_budget", True),
        system_telemetry=_resolve_system_telemetry_mode(getattr(args, "system_telemetry", None)),
        assessment_profile=getattr(args, "assessment_profile", None) or "general",
    )


def _run_one_model(
    args: argparse.Namespace,
    *,
    model_identifier: str,
    image_path: Path,
    prompt: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
    verbose: bool | None = None,
) -> PerformanceResult:
    """Run one model in-process, or in a child interpreter under ``--isolate``.

    Every model execution — first pass and differential reruns alike — goes
    through here so the selected crash boundary applies uniformly.
    """
    params = _process_image_params_from_args(
        args,
        model_identifier=model_identifier,
        image_path=image_path,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        verbose=verbose,
    )
    result = (
        _run_model_isolated(args, params)
        if getattr(args, "isolate", False)
        else process_image_with_model(params)
    )
    return replace(result, assessment_profile=params.assessment_profile)


def process_models(
    args: argparse.Namespace,
    image_path: Path,
    *,  # Force keyword-only arguments for clarity
    prompt: str,
) -> list[PerformanceResult]:
    """Resolve the definitive model list and execute each model run.

    Selection logic:
        * If --models provided: start with that list; optionally filter via --exclude.
        * Else: enumerate cached model repo IDs and apply --exclude.
    Each resolved identifier is processed sequentially (future work: parallel
    scheduling once thread/process safety of underlying libs confirmed).
    """
    # Validate model selection and warn about ineffective exclusions
    validate_and_warn_model_selection(args)

    model_identifiers: list[str]
    if args.models:
        # Case 1: Explicit models specified - apply exclusions to this list
        model_identifiers = args.models
        logger.info("Processing specified models: %s", ", ".join(model_identifiers))
        model_identifiers = apply_exclusions(
            model_identifiers,
            args.exclude or [],
            "explicit list",
        )
        # Explicit selection overrides the capability filter and the layout
        # check, but both stay visible so the run's behaviour is no surprise.
        _warn_explicit_non_image_models(model_identifiers)
        _warn_explicit_incomplete_cache(
            model_identifiers, requested_revision=getattr(args, "revision", None)
        )
    else:
        # Case 2: No explicit models - scan cache and apply exclusions
        logger.info("Scanning cache for models to process...")
        cache_eligibility = get_cached_model_eligibility()
        model_identifiers = _supported_cached_model_ids_with_skipped_logging(cache_eligibility)
        if not model_identifiers:
            skipped_count = sum(1 for entry in cache_eligibility if not entry.selected)
            skipped_hint = (
                f" {skipped_count} cached repo(s) were present but skipped as unsupported; "
                "see the skipped-repo warnings above."
                if skipped_count
                else ""
            )
            exit_with_cli_error(
                "No models found in the local Hugging Face cache. "
                "Download a model (e.g., `huggingface-cli download mlx-community/<model>`) "
                f"or pass explicit IDs with --models.{skipped_hint}",
            )
        model_identifiers = apply_exclusions(
            model_identifiers,
            args.exclude or [],
            "cached models",
        )

    results: list[PerformanceResult] = []
    if not model_identifiers:
        msg = "No models specified or found in cache."
        if not args.models:
            msg += " Ensure models are downloaded and cache is accessible."
        exit_with_cli_error(msg)
    else:
        logger.info("Processing %d model(s)...", len(model_identifiers))

        # Validate all model identifiers before processing
        # (Note: Sampling/KV params already validated in validate_cli_arguments)
        for model_id in model_identifiers:
            try:
                validate_model_identifier(model_id)
            except ValueError:
                logger.exception("Invalid model identifier '%s'", model_id)
                raise

    # Emit legend once if verbose
    if args.verbose:
        log_metrics_legend()

    arch, gpu_info = get_system_info()
    logger.debug("System: %s, GPU: %s", arch, gpu_info if gpu_info is not None else "")
    for idx, model_id in enumerate(model_identifiers, start=1):
        print_cli_separator()
        log_blank()  # Add visual separation between model runs
        # Use full model ID (e.g. "mlx-community/Qwen2-VL-2B-Instruct") instead of just the name
        model_label = model_id
        run_label = f"[{idx}/{len(model_identifiers)}]"
        # Compact logging for model header
        log_model_name(model_label, label=f"Processing Model {run_label}:")

        result: PerformanceResult = _run_one_model(
            args, model_identifier=model_id, image_path=image_path, prompt=prompt
        )
        result = _assess_and_log_model_outcome(result, args=args, prompt=prompt)
        results.append(replace(result, completed_at=local_now_str()))

    return results


def _format_quality_log_flag(
    label: str,
    enabled: bool,
    *,
    detail: str | None = None,
) -> str | None:
    """Return a compact log flag when a quality condition is active."""
    if not enabled:
        return None
    if detail is None:
        return f"{label}=True"
    return f"{label}=True ({detail})"


def _format_repetitive_quality_log_part(analysis: GenerationQualityAnalysis) -> str | None:
    """Return the repetitive-output log segment when present."""
    return _format_quality_log_flag(
        "repetitive",
        analysis.is_repetitive,
        detail=(f"token={analysis.repeated_token}" if analysis.repeated_token else None),
    )


def _assess_and_log_model_outcome(
    result: PerformanceResult,
    *,
    args: argparse.Namespace,
    prompt: str,
) -> PerformanceResult:
    """Attach the mechanical analysis to a completed result and log the outcome."""
    if result.success and result.generation:
        result = _populate_result_quality_analysis(
            result,
            prompt=prompt,
            requested_max_tokens=args.max_tokens,
        )
        if result.quality_analysis is None:
            msg = f"Quality analysis missing for successful result {result.model_name}"
            raise RuntimeError(msg)
        assessment = _assess_result(result)
        if assessment.observations:
            logger.info(
                "Mechanical observations for %s: %s",
                result.model_name,
                ", ".join(assessment.observations),
            )
    # One grep-able line per model with what a rerun needs, so the file log
    # is a self-contained timeline rather than a replay of the reports.
    logger.debug(
        "%s",
        _reproduction_log_line(result, requested_revision=getattr(args, "revision", None)),
    )
    return result


def _reproduction_log_line(result: PerformanceResult, *, requested_revision: str | None) -> str:
    """Return the ``REPRO`` line: resolved revision, phase, stop reason, codes, kwargs.

    Emitted once per model at DEBUG so ``grep 'REPRO model=<id>'`` on the
    file log yields the facts needed to rerun that model natively; the
    metrics blocks and reports carry the same numbers but not in one line.
    """
    provenance = _collect_model_provenance(result.model_name, requested_revision=requested_revision)
    runtime = result.runtime_diagnostics
    diagnostics = result.prompt_diagnostics
    assessment = _assess_result(result)
    kwargs = json.dumps(
        diagnostics.generate_kwargs if diagnostics is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return (
        f"REPRO model={result.model_name}"
        f" revision={provenance['resolved_revision'] or 'unknown'}"
        f" execution={assessment.execution}"
        f" phase={result.failure_phase or '-'}"
        f" stop={runtime.stop_reason if runtime is not None and runtime.stop_reason else '-'}"
        f" observations={','.join(assessment.observations) or 'none'}"
        f" kwargs={kwargs}"
    )


def _format_quality_analysis_for_log(analysis: GenerationQualityAnalysis) -> str:
    """Serialize retained mechanical facts into a compact terminal log line."""
    thinking_marker = (
        analysis.thinking_trace_markers[0] if analysis.thinking_trace_markers else "marker"
    )
    parts_raw: tuple[str | None, ...] = (
        _format_repetitive_quality_log_part(analysis),
        (
            f"missing_sections={'+'.join(analysis.missing_sections)}"
            if analysis.missing_sections
            else None
        ),
        _format_quality_log_flag(
            "thinking_trace",
            analysis.has_thinking_trace,
            detail=thinking_marker,
        ),
        _format_quality_log_flag(
            "thinking_incomplete",
            analysis.thinking_trace_incomplete,
        ),
        _format_quality_log_flag("likely_capped", analysis.likely_capped),
        _format_quality_log_flag(
            "unexpected_special_token",
            bool(analysis.unexpected_special_tokens),
            detail=",".join(analysis.unexpected_special_tokens[:2]),
        ),
    )
    parts = [part for part in parts_raw if part is not None]
    parts.append(f"words={analysis.word_count}")

    return ", ".join(parts) if parts else "no issues detected"


def _truncate_text_preview(text: str, *, max_chars: int) -> str:
    """Trim text previews to a fixed character budget."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _collapse_preview_line_whitespace(text: str) -> str:
    """Collapse horizontal whitespace while preserving source line boundaries."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(" ".join(line.split()) for line in normalized.split("\n"))


def _result_thinking_delimiters(result: PerformanceResult) -> tuple[tuple[str, str], ...]:
    """Recognised thinking delimiter pairs plus any pair configured for this generation."""
    pairs = list(THINKING_TRACE_DELIMITER_PAIRS)
    diagnostics = result.prompt_diagnostics
    if diagnostics is not None:
        start_marker = diagnostics.generate_kwargs.get("thinking_start_token")
        end_marker = diagnostics.generate_kwargs.get("thinking_end_token")
        if isinstance(start_marker, str) and isinstance(end_marker, str):
            configured_pair = (start_marker, end_marker)
            if all(configured_pair) and configured_pair not in pairs:
                pairs.append(configured_pair)
    return tuple(pairs)


def _result_seeded_thinking_text(result: PerformanceResult) -> str:
    """Return the rendered prompt whose seeded opener a closing marker may continue."""
    diagnostics = result.prompt_diagnostics
    if diagnostics is None:
        return ""
    return diagnostics.rendered_prompt or diagnostics.rendered_prompt_preview or ""


def _final_answer_text(result: PerformanceResult) -> tuple[str, str]:
    """Split a completed output into (final answer, reasoning removed before it).

    Uses the same complete-trace rule as the assessment (``_final_answer_view``):
    only closed thinking traces — emitted or prompt-seeded — count as reasoning,
    so an unclosed trace stays in the answer text where its observation is
    still visible. The reasoning text is returned so a reader can open it
    under disclosure rather than losing it.
    """
    text = _generation_text_value(result.generation)
    answer, removed = _final_answer_split(
        text,
        delimiter_pairs=_result_thinking_delimiters(result),
        seeded_text=_result_seeded_thinking_text(result),
    )
    if not removed or not answer:
        return text, ""
    return answer, "\n".join(segment.strip() for segment in removed if segment.strip())


def _configured_thinking_markers(diagnostics: PromptDiagnostics | None) -> tuple[str, ...]:
    """Return the thinking start/end markers configured for this generation."""
    if diagnostics is None:
        return ()
    markers = [
        value
        for key in ("thinking_start_token", "thinking_end_token")
        if isinstance(value := diagnostics.generate_kwargs.get(key), str) and value
    ]
    return tuple(_dedupe_preserve_order(markers))


def _configured_output_wrappers(diagnostics: PromptDiagnostics | None) -> tuple[str, ...]:
    """Return wrappers to strip from the analysis copy before structural checks.

    Thinking start/end markers are deliberately excluded: they are structural
    delimiters that ``_final_answer_view`` must still see to recognise a
    complete trace. Stripping them here (as happened whenever a thinking
    budget was configured) destroyed the closure marker, so a model that
    reasoned and then answered was judged on its reasoning as preamble.
    They remain in ``_configured_generation_wrappers`` as reported evidence.
    """
    if diagnostics is None:
        return ()

    # analyze_generation_text additionally protects every recognised
    # THINKING_TRACE_DELIMITER_PAIRS marker; this filter covers the custom
    # configured pair so the reported wrapper list stays honest.
    thinking_markers = set(_configured_thinking_markers(diagnostics))
    wrappers = [
        wrapper
        for wrapper in (*diagnostics.special_tokens, *_configured_generation_wrappers(diagnostics))
        if wrapper not in thinking_markers
    ]
    return tuple(_dedupe_preserve_order(wrappers))


def _configured_generation_wrappers(
    diagnostics: PromptDiagnostics | None,
) -> tuple[str, ...]:
    """Return string wrappers declared by tokenizer EOS and mlx-vlm generation types."""
    if diagnostics is None:
        return ()

    wrappers: list[str] = []
    if diagnostics.eos_token:
        wrappers.append(diagnostics.eos_token)
    for key in ("eos_tokens", "thinking_start_token", "thinking_end_token"):
        value = diagnostics.generate_kwargs.get(key)
        if isinstance(value, str):
            wrappers.append(value)
        elif isinstance(value, list):
            wrappers.extend(item for item in value if isinstance(item, str))
    return tuple(_dedupe_preserve_order(wrappers))


def _populate_result_quality_analysis(
    result: PerformanceResult,
    *,
    prompt: str | None = None,
    requested_max_tokens: int | None = None,
) -> PerformanceResult:
    """Attach mechanical analysis to a completed result exactly once per prompt."""
    if not result.success or result.generation is None:
        return result

    text = str(getattr(result.generation, "text", ""))
    cached_analysis = _quality_analysis_for_result(result)
    if (
        cached_analysis is not None
        and cached_analysis.assessment_profile == result.assessment_profile
        and (not prompt or cached_analysis.prompt_checks_ran)
    ):
        return result

    generated_tokens = _generation_int_metric(result.generation, "generation_tokens")
    prompt_tokens = _generation_int_metric(result.generation, "prompt_tokens")
    resolved_requested_max_tokens = (
        requested_max_tokens if requested_max_tokens is not None else result.requested_max_tokens
    )
    diagnostics = result.prompt_diagnostics
    analysis = analyze_generation_text(
        text,
        generated_tokens,
        prompt_tokens=prompt_tokens,
        prompt=prompt,
        requested_max_tokens=resolved_requested_max_tokens,
        assessment_profile=result.assessment_profile,
        known_special_tokens=_configured_output_wrappers(diagnostics),
        configured_generation_wrappers=_configured_generation_wrappers(diagnostics),
        thinking_trace_delimiters=_result_thinking_delimiters(result),
        seeded_thinking_text=_result_seeded_thinking_text(result),
        prompt_text_tokens=(
            diagnostics.rendered_prompt_token_count if diagnostics is not None else None
        ),
    )
    return replace(result, quality_analysis=analysis)


# =============================================================================
# SECTION: RESULT ENRICHMENT/HISTORY/FINALIZATION
# =============================================================================


def _format_counter_items[T: str](counter: Counter[T]) -> str:
    """Format a counter as ``label=count`` pairs ordered by frequency."""
    if not counter:
        return "none"
    return ", ".join(f"{label}={count}" for label, count in counter.most_common())


def _short_model_label(model_name: str, *, max_len: int = SUMMARY_MODEL_LABEL_MAX) -> str:
    """Return a compact model label suitable for narrow summary tables/charts."""
    label = model_name.rsplit("/", maxsplit=1)[-1]
    if len(label) <= max_len:
        return label
    return label[: max_len - 3] + "..."


def _format_float_or_dash(value: float | None, *, digits: int = 2) -> str:
    """Format a float value with fixed precision, or ``-`` when missing."""
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def _log_rich_metric_chart(
    title: str,
    entries: Sequence[tuple[str, float]],
    *,
    unit: str = "",
    digits: int = 2,
    max_rows: int = SUMMARY_CHART_MAX_ROWS,
) -> None:
    """Log a compact Rich bar chart for ranked model metrics."""
    if not entries:
        return
    ranked = sorted(entries, key=lambda item: item[1], reverse=True)[:max_rows]
    max_value = max(value for _label, value in ranked)
    if max_value <= 0:
        return

    logger.info("%s", title)
    chart = Table.grid(padding=(0, 1))
    chart.add_column(justify="left", no_wrap=True)
    chart.add_column(ratio=1)
    chart.add_column(justify="right", no_wrap=True)
    for label, value in ranked:
        chart.add_row(
            _short_model_label(label),
            Bar(max_value, 0, value, width=SUMMARY_CHART_WIDTH),
            f"{_format_float_or_dash(value, digits=digits)}{unit}",
        )
    _log_rich_renderable(chart, indent="   ")


@dataclass(frozen=True)
class ModelComparisonData:
    """Prepared rows and ranking inputs for the current-run comparison summary."""

    rows: tuple[tuple[str, ...], ...]
    tps_entries: tuple[tuple[str, float], ...]
    total_time_entries: tuple[tuple[str, float], ...]
    crashed: tuple[PerformanceResult, ...]


def _model_comparison_sort_key(
    result: PerformanceResult,
    assessments: Mapping[str, ResultAssessment],
) -> tuple[int, float, str]:
    """Sort completed runs first, then generation speed and model name."""
    assessment = assessments[result.model_name]
    execution_order = {"completed": 0, "crashed": 1, "indeterminate": 2}
    return (
        execution_order[assessment.execution],
        -(_valid_generation_tps(result) or 0.0),
        result.model_name,
    )


def _model_comparison_row(
    index: int,
    result: PerformanceResult,
    assessment: ResultAssessment,
) -> tuple[str, ...]:
    """Build one fixed-width console comparison row from captured metrics."""
    runtime = result.runtime_diagnostics
    tps = _valid_generation_tps(result)
    peak_memory = _generation_optional_nonnegative_float_metric(result.generation, "peak_memory")
    model_load_time = (
        runtime.model_load_time_s
        if runtime is not None and runtime.model_load_time_s is not None
        else result.model_load_time
    )
    execution_code = {"completed": "C", "crashed": "X", "indeterminate": "I"}[assessment.execution]
    usability_code = {
        "usable": "U",
        "usable_with_caveats": "C",
        "unusable": "X",
        "not_evaluated": "-",
    }[assessment.usability]
    return (
        str(index),
        _short_model_label(result.model_name, max_len=21),
        f"{execution_code}/{usability_code}",
        _format_float_or_dash(runtime.input_validation_time_s if runtime is not None else None),
        _format_float_or_dash(model_load_time),
        _format_float_or_dash(runtime.prompt_prep_time_s if runtime is not None else None),
        _format_float_or_dash(runtime.first_token_latency_s if runtime is not None else None),
        _format_float_or_dash(_runtime_generation_residual_time_s(runtime)),
        _format_float_or_dash(runtime.cleanup_time_s if runtime is not None else None),
        _format_float_or_dash(result.total_time),
        _format_float_or_dash(tps, digits=1),
        _format_float_or_dash(
            peak_memory if peak_memory is not None and peak_memory > 0 else None,
            digits=2,
        ),
    )


def _collect_model_comparison_data(
    results: Sequence[PerformanceResult],
    assessments: Mapping[str, ResultAssessment],
) -> ModelComparisonData:
    """Collect display rows, ranking samples, and crashes in one ordered pass."""
    rows: list[tuple[str, ...]] = []
    tps_entries: list[tuple[str, float]] = []
    total_time_entries: list[tuple[str, float]] = []
    crashed: list[PerformanceResult] = []
    sorted_results = sorted(
        results, key=lambda result: _model_comparison_sort_key(result, assessments)
    )

    for index, result in enumerate(sorted_results, start=1):
        assessment = assessments[result.model_name]
        rows.append(_model_comparison_row(index, result, assessment))
        eligible = assessment.execution == "completed" and assessment.usability in {
            "usable",
            "usable_with_caveats",
        }
        tps = _valid_generation_tps(result)
        if eligible and tps is not None:
            tps_entries.append((result.model_name, tps))
        if (
            eligible
            and result.total_time is not None
            and math.isfinite(result.total_time)
            and result.total_time > 0
        ):
            total_time_entries.append((result.model_name, result.total_time))
        if assessment.execution == "crashed":
            crashed.append(result)

    return ModelComparisonData(
        rows=tuple(rows),
        tps_entries=tuple(tps_entries),
        total_time_entries=tuple(total_time_entries),
        crashed=tuple(crashed),
    )


def _log_model_comparison_table_and_charts(
    results: list[PerformanceResult],
    *,
    assessments: Mapping[str, ResultAssessment],
    recommended_working_set_bytes: int | None = None,
) -> None:
    """Log cached outcome axes and rank only usable completed observations."""
    if not results:
        return

    comparison = _collect_model_comparison_data(results, assessments)

    logger.info("📋 Model Comparison (current run):")
    if recommended_working_set_bytes is not None:
        logger.info(
            "   Recommended working set: %s GB",
            fmt_num(recommended_working_set_bytes / (1024**3)),
        )
    logger.info("   E/U: execution C=completed, X=crashed, I=indeterminate")
    logger.info("        usability U=usable, C=caveated, X=unusable, -=not evaluated")
    logger.info("   First=prefill/first token; Remain=input preparation + decode")
    _log_rich_table(
        headers=(
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
        ),
        rows=comparison.rows,
        max_widths=(2, 21, 3, 5, 5, 5, 5, 6, 5, 6, 5, 5),
    )

    if comparison.tps_entries:
        log_blank()
        _log_rich_metric_chart(
            "📊 TPS comparison chart:",
            comparison.tps_entries,
            unit=" tps",
            digits=1,
        )
    if len(comparison.total_time_entries) >= MIN_MODELS_FOR_EFFICIENCY_CHART:
        inverted = [(name, 1.0 / value) for name, value in comparison.total_time_entries]
        _log_rich_metric_chart(
            "⏱ Efficiency chart (higher is faster overall):",
            inverted,
            unit=" 1/s",
            digits=3,
        )

    if comparison.crashed:
        stage_counts = Counter(result.error_stage or "Unknown" for result in comparison.crashed)
        _log_rich_metric_chart(
            "❌ Failure stage frequency:",
            [(stage, float(count)) for stage, count in stage_counts.items()],
            unit=" x",
            digits=0,
        )


type PerformanceMetricSample = tuple[PerformanceResult, float]


@dataclass(frozen=True)
class PerformanceMetricSamples:
    """Validated samples used by the performance-highlight summary."""

    total: tuple[PerformanceMetricSample, ...]
    memory: tuple[PerformanceMetricSample, ...]
    load: tuple[PerformanceMetricSample, ...]


def _collect_performance_metric_samples(
    results: Sequence[PerformanceResult],
) -> PerformanceMetricSamples:
    """Collect finite, domain-valid samples for each highlighted metric."""
    total: tuple[PerformanceMetricSample, ...] = tuple(
        (result, result.total_time)
        for result in results
        if result.total_time is not None
        and result.total_time >= 0
        and math.isfinite(result.total_time)
    )
    memory_samples: list[PerformanceMetricSample] = []
    for result in results:
        value = _generation_optional_nonnegative_float_metric(
            result.generation,
            "peak_memory",
        )
        if value is None or value <= 0 or not math.isfinite(value):
            continue
        memory_samples.append((result, value))
    memory = tuple(memory_samples)
    load: tuple[PerformanceMetricSample, ...] = tuple(
        (result, result.model_load_time)
        for result in results
        if result.model_load_time is not None
        and result.model_load_time >= 0
        and math.isfinite(result.model_load_time)
    )
    return PerformanceMetricSamples(total=total, memory=memory, load=load)


def _log_image_memory_highlights(
    results: Sequence[PerformanceResult],
    image_profile: ImageInputProfile | None,
) -> None:
    """Log image-relative peak-memory facts when both inputs are captured."""
    if image_profile is None or image_profile.megapixels <= 0:
        return
    peak_deltas_gb = tuple(
        delta
        for result in results
        if (delta := _peak_memory_delta_from_model_load_gb(result)) is not None
    )
    if not peak_deltas_gb:
        return

    average_delta_gb = sum(peak_deltas_gb) / len(peak_deltas_gb)
    logger.info("   Input image size: %.2f MP", image_profile.megapixels)
    logger.info("   Average peak delta from post-load: %.2f GB", average_delta_gb)
    logger.info(
        "   Peak memory delta / MP: %.0f MB/MP",
        average_delta_gb * 1024 / image_profile.megapixels,
    )


def _log_performance_highlights(
    eligible_results: list[PerformanceResult],
    *,
    image_profile: ImageInputProfile | None = None,
    recommended_working_set_bytes: int | None = None,
) -> None:
    """Log valid metrics for completed usable or caveated observations only."""
    if not eligible_results:
        return

    samples = _collect_performance_metric_samples(eligible_results)
    if not samples.total and not samples.memory and not samples.load:
        return

    # Time to complete the task end-to-end is the decision metric; decode
    # tok/s and any cross-model average (or tokens-per-GB ratio) mislead when
    # tokenizers, image expansion and reasoning lengths differ per model.
    logger.info("🏆 Performance Highlights:")
    if samples.total:
        quickest, quickest_total = min(samples.total, key=lambda item: item[1])
        logger.info(
            "   ⏱ Quickest completion: %s (%s end-to-end)",
            quickest.model_name,
            _format_time_seconds(quickest_total),
        )
    if samples.memory:
        most_efficient, efficient_memory = min(samples.memory, key=lambda item: item[1])
        logger.info(
            "   💾 Lowest peak memory: %s (%.1f GB)",
            most_efficient.model_name,
            efficient_memory,
        )
    if samples.load:
        fastest_load, load_time = min(samples.load, key=lambda item: item[1])
        logger.info("   ⚡ Fastest load: %s (%.2fs)", fastest_load.model_name, load_time)

    if samples.memory:
        average_peak_memory = sum(value for _result, value in samples.memory) / len(samples.memory)
        logger.info("📈 Resource Usage:")
        logger.info(
            "   Average peak memory: %s",
            _format_peak_memory_context(
                average_peak_memory,
                recommended_working_set_bytes,
            ),
        )

    _log_image_memory_highlights(eligible_results, image_profile)


def _log_failed_models_summary(failed: list[PerformanceResult]) -> None:
    """Log only recorded crash fields and their exact distribution."""
    logger.info("❌ Crashed Models (%d):", len(failed))
    for res in failed:
        logger.info(
            "  - %s | phase=%s | stage=%s | module=%s | package=%s | code=%s | traceback=%s",
            res.model_name,
            res.failure_phase or "unavailable",
            res.error_stage or "Unknown",
            res.root_error_module or "unavailable",
            res.error_package or "unavailable",
            res.error_code or "unavailable",
            "available" if res.error_traceback else "unavailable",
            extra={"style_hint": LogStyles.ERROR},
        )
        if res.error_message:
            error_type = res.root_error_type or res.error_type or "Error"
            error_message = res.root_error_message or res.error_message
            logger.info(
                "    -> error=%s: %s",
                error_type,
                _truncate_text_preview(error_message, max_chars=160),
                extra={"style_hint": LogStyles.WARNING},
            )

    package_names: list[str] = [res.error_package or _UNKNOWN_OWNER for res in failed]
    stage_names: list[str] = [res.error_stage or "Unknown" for res in failed]
    pkg_counts: Counter[str] = Counter(package_names)
    stage_counts: Counter[str] = Counter(stage_names)
    logger.info("   By package: %s", _format_counter_items(pkg_counts))
    logger.info("   By stage: %s", _format_counter_items(stage_counts))


def _log_completed_models_list(
    completed: Sequence[PerformanceResult],
    assessments: Mapping[str, ResultAssessment],
) -> None:
    """Log completed models in compact actionability-ordered tables."""
    logger.info("Completed Models (%d):", len(completed))
    groups: tuple[tuple[ModelUsability, str], ...] = (
        ("unusable", "Major concerns"),
        ("usable_with_caveats", "Concerns detected"),
        ("usable", "No concerns detected"),
    )
    for usability, label in groups:
        grouped = sorted(
            (
                result
                for result in completed
                if assessments[result.model_name].usability == usability
            ),
            key=lambda item: _assessment_actionability_key(
                item.model_name,
                assessments[item.model_name].usability,
                assessments[item.model_name].observations,
            ),
        )
        if not grouped:
            continue
        logger.info("%s (%d):", label, len(grouped))
        if usability == "usable":
            _log_rich_table(
                headers=("Model",),
                rows=tuple((result.model_name,) for result in grouped),
                max_widths=(100,),
            )
            continue
        _log_rich_table(
            headers=("Model", "Observations"),
            rows=tuple(
                (
                    result.model_name,
                    _gallery_observation_labels(assessments[result.model_name].observations),
                )
                for result in grouped
            ),
            max_widths=(64, None),
        )


def _indeterminate_reason(result: PerformanceResult) -> str:
    """Return the root cause and remedy for an indeterminate attempt."""
    if _is_download_timeout_failure(result):
        return f"download timeout: {DOWNLOAD_TIMEOUT_REMEDY}"
    if _is_incomplete_cache_failure(result):
        return f"incomplete cached snapshot: {INCOMPLETE_CACHE_REMEDY}"
    return result.error_message or "external connectivity failure"


def _log_indeterminate_models_summary(indeterminate: Sequence[PerformanceResult]) -> None:
    """Log attempts the environment prevented from being conclusively evaluated.

    Each line states the root cause and what to do about it, so an
    indeterminate outcome never reads as "nothing happened".
    """
    logger.info("Indeterminate Models (%d):", len(indeterminate))
    for result in indeterminate:
        logger.info(
            "  - %s | %s",
            result.model_name,
            _indeterminate_reason(result),
            extra={"style_hint": LogStyles.WARNING},
        )


def log_summary(
    results: list[PerformanceResult],
    *,
    assessments: Mapping[str, ResultAssessment] | None = None,
    image_path: Path | None = None,
) -> None:
    """Log current-run execution, performance, and mechanical observations."""
    if not results:
        return

    resolved_assessments = (
        dict(assessments)
        if assessments is not None
        else {result.model_name: _assess_result(result) for result in results}
    )

    log_blank()
    log_rule(style="blue", bold=True)
    logger.info("Results Summary", extra={"style_hint": LogStyles.HEADER})
    log_rule(style="blue", bold=True)

    completed = [
        result
        for result in results
        if resolved_assessments[result.model_name].execution == "completed"
    ]
    crashed = [
        result
        for result in results
        if resolved_assessments[result.model_name].execution == "crashed"
    ]
    indeterminate = [
        result
        for result in results
        if resolved_assessments[result.model_name].execution == "indeterminate"
    ]
    eligible_for_highlights = [
        result
        for result in completed
        if resolved_assessments[result.model_name].usability in {"usable", "usable_with_caveats"}
    ]
    recommended_working_set_bytes = _get_recommended_working_set_bytes()

    assessment_counts = Counter(
        resolved_assessments[result.model_name].execution for result in results
    )
    usability_counts = Counter(
        resolved_assessments[result.model_name].usability for result in results
    )
    maintainer_counts = Counter(
        resolved_assessments[result.model_name].maintainer_status for result in results
    )
    observation_counts: Counter[str] = Counter(
        observation
        for result in completed
        for observation in resolved_assessments[result.model_name].observations
    )
    logger.info("Execution outcomes: %s", _format_counter_items(assessment_counts))
    logger.info("Usability outcomes: %s", _format_counter_items(usability_counts))
    logger.info("Maintainer outcomes: %s", _format_counter_items(maintainer_counts))
    logger.info("Mechanical observations: %s", _format_counter_items(observation_counts))

    if eligible_for_highlights:
        _log_performance_highlights(
            eligible_for_highlights,
            image_profile=_load_image_input_profile(image_path),
            recommended_working_set_bytes=recommended_working_set_bytes,
        )
        log_blank()
        log_blank()

    _log_model_comparison_table_and_charts(
        results,
        assessments=resolved_assessments,
        recommended_working_set_bytes=recommended_working_set_bytes,
    )
    log_blank()

    if completed:
        _log_completed_models_list(completed, resolved_assessments)
    if crashed:
        log_blank()
        _log_failed_models_summary(crashed)
    if indeterminate:
        log_blank()
        _log_indeterminate_models_summary(indeterminate)


def _history_path_for_jsonl(jsonl_path: Path) -> Path:
    """Derive history JSONL path from the main JSONL report path."""
    return jsonl_path.with_name(f"{jsonl_path.stem}.history.jsonl")


def _build_prompt_preview(prompt: str, *, max_chars: int = 200) -> str:
    """Return prompt preview truncated to ``max_chars``."""
    return prompt if len(prompt) <= max_chars else f"{prompt[:max_chars]}..."


def _resolved_memory_deltas_gb(
    result: PerformanceResult,
    performance: GenerationPerformanceData,
) -> tuple[float, float]:
    """Prefer explicitly captured memory deltas, falling back to generation data."""
    active = (
        result.active_memory if result.active_memory is not None else performance.active_memory_gb
    )
    cache = result.cache_memory if result.cache_memory is not None else performance.cache_memory_gb
    return active, cache


def _history_model_result_from_result(
    result: PerformanceResult,
    *,
    resolved_revision: str | None = None,
) -> HistoryModelResultRecord:
    """Return raw execution, timing, token, and resource facts for one model."""
    record: HistoryModelResultRecord = {
        "success": result.success,
        "resolved_revision": resolved_revision,
        "failure_phase": result.failure_phase,
        "error_stage": result.error_stage,
        "error_type": result.error_type,
        "error_package": result.error_package,
        "error_code": result.error_code,
        "error_signature": result.error_signature,
        "generation_time_s": result.generation_time,
        "model_load_time_s": result.model_load_time,
        "total_time_s": result.total_time,
    }
    # Effective per-model settings (a thinking budget, say) are not in the
    # run-level fingerprint, which keeps only settings shared by the whole
    # sweep; noise bands match them per model instead.
    diagnostics = result.prompt_diagnostics
    if diagnostics is not None and diagnostics.generate_kwargs:
        record["generation_settings"] = dict(diagnostics.generate_kwargs)
    if result.generation is not None:
        performance = _extract_generation_performance_data(result.generation)
        active_memory_gb, cache_memory_gb = _resolved_memory_deltas_gb(result, performance)
        record.update(
            {
                "prompt_tokens": performance.prompt_tokens,
                "generation_tokens": performance.generation_tokens,
                "total_tokens": performance.total_tokens,
                "generation_tps": performance.generation_tps,
                "peak_memory_gb": performance.peak_memory_gb,
                "active_memory_gb": active_memory_gb,
                "cache_memory_gb": cache_memory_gb,
            }
        )
    if result.runtime_diagnostics is not None:
        record["stop_reason"] = result.runtime_diagnostics.stop_reason
        record["post_cleanup_active_memory_gb"] = (
            result.runtime_diagnostics.post_cleanup_active_memory_gb
        )
        record["post_cleanup_cache_memory_gb"] = (
            result.runtime_diagnostics.post_cleanup_cache_memory_gb
        )
    return record


def _build_history_run_record(
    *,
    results: list[PerformanceResult],
    prompt: str,
    system_info: dict[str, str],
    library_versions: LibraryVersionDict,
    image_path: Path | None,
    runtime_fingerprint: dict[str, RuntimeProbeResult] | None = None,
    eval_mode: EvaluationLane,
    comparison_fingerprint: str | None = None,
    model_provenance: Mapping[str, ModelProvenanceRecord] | None = None,
) -> HistoryRunRecord:
    """Build one append-only run record without current-report semantics.

    ``eval_mode`` must already be a resolved lane: re-resolving here with no
    metadata would silently record ``blind`` for an assisted run if an
    unresolved requested mode ever leaked through.
    """
    record: HistoryRunRecord = {
        "_type": "run",
        "format_version": HISTORY_FORMAT_VERSION,
        "timestamp": local_now_str(),
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_preview": _build_prompt_preview(prompt),
        "image_path": str(image_path) if image_path is not None else None,
        "model_results": {
            result.model_name: _history_model_result_from_result(
                result,
                resolved_revision=(
                    model_provenance[result.model_name]["resolved_revision"]
                    if model_provenance is not None and result.model_name in model_provenance
                    else None
                ),
            )
            for result in results
        },
        "system": system_info,
        "library_versions": library_versions,
        "eval_mode": eval_mode,
    }
    if runtime_fingerprint is not None:
        record["runtime_fingerprint"] = runtime_fingerprint
    if comparison_fingerprint is not None:
        record["comparison_fingerprint"] = comparison_fingerprint
    return record


def append_history_record(
    *,
    history_path: Path,
    results: list[PerformanceResult],
    prompt: str,
    system_info: dict[str, str],
    library_versions: LibraryVersionDict,
    image_path: Path | None = None,
    runtime_fingerprint: dict[str, RuntimeProbeResult] | None = None,
    eval_mode: EvaluationLane,
    comparison_fingerprint: str | None = None,
    model_provenance: Mapping[str, ModelProvenanceRecord] | None = None,
) -> HistoryRunRecord | None:
    """Append raw factual run data for optional out-of-band history analysis.

    Returns the record on a confirmed append and ``None`` when the write failed,
    so callers never assume the current run is the last history row.
    """
    record = _build_history_run_record(
        results=results,
        prompt=prompt,
        system_info=system_info,
        library_versions=library_versions,
        image_path=image_path,
        runtime_fingerprint=runtime_fingerprint,
        eval_mode=eval_mode,
        comparison_fingerprint=comparison_fingerprint,
        model_provenance=model_provenance,
    )

    try:
        _write_text_file(history_path, json.dumps(record) + "\n", append=True)
    except OSError:
        logger.exception("Failed to append history record to %s", history_path)
        return None

    return record


def _build_jsonl_metadata_record(  # noqa: PLR0913 - the schema-3 header names each retained field  # skylos: ignore[SKY-C303]
    *,
    prompt: str,
    system_info: dict[str, str],
    mode_policy: ReportModePolicy,
    counts: RunOutcomeCounts,
    generation_settings: dict[str, JsonLike],
    image: RunImageRecord | None,
    library_versions: LibraryVersionDict | None = None,
    runtime_fingerprint: dict[str, RuntimeProbeResult] | None = None,
    execution_mode: Literal["in_process", "isolated"] = "in_process",
    total_runtime_seconds: float = 0.0,
    artifacts: Mapping[str, str] | None = None,
    producer: CheckModelsProvenanceRecord | None = None,
    trust_remote_code: bool = True,
    comparison: RunComparison | None = None,
    started_at: str | None = None,
) -> JsonlMetadataRecord:
    """Build the schema-3 metadata header row carrying the whole run context."""
    record: JsonlMetadataRecord = {
        "_type": "metadata",
        "format_version": JSONL_FORMAT_VERSION,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "system": {key: _home_relative_report_text(value) for key, value in system_info.items()},
        "timestamp": local_now_str(),
        "total_runtime_seconds": round(total_runtime_seconds, 3),
        "counts": counts,
        "artifacts": {
            key: _home_relative_report_text(value) for key, value in (artifacts or {}).items()
        },
        "producer": producer or _collect_check_models_provenance(),
        "image": image,
        "generation_settings": generation_settings,
        "trust_remote_code": trust_remote_code,
        "comparison": _run_comparison_to_json(comparison),
        "eval_mode": mode_policy.eval_mode,
        "assessment_profile": mode_policy.assessment_profile,
        "metadata_exposed_to_prompt": mode_policy.metadata_exposed_to_prompt,
        "execution_mode": execution_mode,
    }
    if started_at is not None:
        record["started_at"] = started_at
    if library_versions is not None:
        record["library_versions"] = library_versions
        record["component_provenance"] = _collect_component_provenance(library_versions)
    if runtime_fingerprint is not None:
        record["runtime_fingerprint"] = runtime_fingerprint
    discovery = _cache_discovery_records()
    if discovery:
        record["cache_discovery"] = discovery
    return record


def _build_jsonl_metrics_record(
    result: PerformanceResult,
    recommended_working_set_bytes: int | None,
) -> JsonlMetricsRecord:
    """Build captured and derived performance metrics for one JSONL result."""
    runtime = result.runtime_diagnostics
    metrics: JsonlMetricsRecord = {}
    if runtime is not None:
        if runtime.post_cleanup_active_memory_gb is not None:
            metrics["post_cleanup_active_memory_gb"] = runtime.post_cleanup_active_memory_gb
        if runtime.post_cleanup_cache_memory_gb is not None:
            metrics["post_cleanup_cache_memory_gb"] = runtime.post_cleanup_cache_memory_gb

    generation = result.generation
    if generation is None:
        return metrics

    performance_data = _extract_generation_performance_data(generation)
    active_memory_gb, cache_memory_gb = _resolved_memory_deltas_gb(result, performance_data)
    metrics.update(
        {
            "prompt_tokens": performance_data.prompt_tokens,
            "generation_tokens": performance_data.generation_tokens,
            "total_tokens": performance_data.total_tokens,
            "prompt_tps": performance_data.prompt_tps,
            "generation_tps": performance_data.generation_tps,
            "peak_memory_gb": performance_data.peak_memory_gb,
            "active_memory_gb": active_memory_gb,
            "cache_memory_gb": cache_memory_gb,
        }
    )
    model_load_active_memory_gb = (
        runtime.model_load_active_memory_gb
        if runtime is not None
        else _object_model_load_active_memory_gb(generation)
    )
    if model_load_active_memory_gb is not None:
        metrics["model_load_active_memory_gb"] = model_load_active_memory_gb
    peak_memory_delta_gb = _peak_memory_delta_from_model_load_gb(result)
    if peak_memory_delta_gb is not None:
        metrics["peak_memory_delta_gb"] = peak_memory_delta_gb
    working_set_pct = _peak_memory_working_set_pct(
        performance_data.peak_memory_gb,
        recommended_working_set_bytes,
    )
    if working_set_pct is not None:
        metrics["peak_memory_working_set_pct"] = working_set_pct
    return metrics


def _build_jsonl_failure_record(
    result: PerformanceResult,
    execution: ExecutionStatus,
) -> JsonlFailureRecord | None:
    """Build complete captured failure evidence for a non-completed result."""
    if execution == "completed":
        return None

    root_exception = result.exception_chain[0] if result.exception_chain else None
    failure: JsonlFailureRecord = {
        "phase": result.failure_phase,
        "stage": result.error_stage,
        "code": result.error_code,
        "message": (
            _home_relative_report_text(result.error_message)
            if result.error_message is not None
            else None
        ),
        "exception_type": (
            result.root_error_type
            or (root_exception.exception_type if root_exception is not None else None)
            or result.error_type
        ),
        "exception_module": (
            result.root_error_module
            or (root_exception.module if root_exception is not None else None)
        ),
        "package": result.error_package,
        "traceback": (
            _home_relative_report_text(result.error_traceback)
            if result.error_traceback is not None
            else None
        ),
    }
    if result.exception_chain:
        failure["exception_chain"] = _serialize_exception_chain(result.exception_chain)
    return failure


def _build_jsonl_result_record(
    result: PerformanceResult,
    assessment: ResultAssessment,
    *,
    requested_revision: str | None,
    model_provenance: ModelProvenanceRecord | None = None,
    recommended_working_set_bytes: int | None = None,
) -> JsonlResultRecord:
    """Build one narrow JSONL row from cached assessment and captured facts."""
    runtime = result.runtime_diagnostics
    generation = result.generation
    metrics = _build_jsonl_metrics_record(result, recommended_working_set_bytes)
    failure = _build_jsonl_failure_record(result, assessment.execution)

    prompt_diagnostics = _prompt_diagnostics_to_json(result.prompt_diagnostics)
    burden_payload = (
        {
            field_info.name: value
            for field_info in fields(result.model_burden)
            if (value := getattr(result.model_burden, field_info.name)) is not None
        }
        if result.model_burden is not None
        else None
    )
    record: JsonlResultRecord = {
        "_type": "result",
        "model": result.model_name,
        "timestamp": result.completed_at or local_now_str(),
        "assessment": _assessment_to_json(assessment, result),
        "generated_text": _generation_text_value(generation),
        "captured_output_on_fail": _home_relative_report_text(result.captured_output_on_fail or ""),
        "failure": failure,
        "metrics": metrics,
        "timing": {
            "generation_time_s": result.generation_time,
            "model_load_time_s": result.model_load_time,
            "total_time_s": result.total_time,
            "input_validation_time_s": (
                runtime.input_validation_time_s if runtime is not None else None
            ),
            "prompt_prep_time_s": runtime.prompt_prep_time_s if runtime is not None else None,
            "cleanup_time_s": runtime.cleanup_time_s if runtime is not None else None,
            "first_token_latency_s": (
                runtime.first_token_latency_s if runtime is not None else None
            ),
            "stop_reason": runtime.stop_reason if runtime is not None else None,
        },
        "model_provenance": _public_model_provenance(
            model_provenance
            or _collect_model_provenance(
                result.model_name,
                requested_revision=requested_revision,
            )
        ),
        "prompt_diagnostics": prompt_diagnostics or None,
    }
    if burden_payload:
        record["model_burden"] = cast("dict[str, JsonLike]", burden_payload)
    model_type, resolved_model_type, arch_supported = _arch_precheck_for_model(result.model_name)
    if model_type is not None and resolved_model_type is not None and arch_supported is not None:
        record["architecture"] = {
            "model_type": model_type,
            "resolved_model_type": resolved_model_type,
            "supported_by_installed_mlx_vlm": arch_supported,
        }
    if result.captured_upstream_output:
        record["captured_upstream_output"] = _home_relative_report_text(
            result.captured_upstream_output
        )
    if result.system_telemetry is not None:
        record["system_telemetry"] = result.system_telemetry
    return record


def _build_retained_run(  # noqa: PLR0913 - one assembly point for the whole retained-run contract  # skylos: ignore[SKY-C303]
    results: Sequence[PerformanceResult],
    *,
    prompt: str,
    system_info: dict[str, str],
    library_versions: LibraryVersionDict | None = None,
    runtime_fingerprint: dict[str, RuntimeProbeResult] | None = None,
    mode_policy: ReportModePolicy | None = None,
    requested_revision: str | None = None,
    report_context: ReportRenderContext | None = None,
    execution_mode: Literal["in_process", "isolated"] = "in_process",
    total_runtime_seconds: float = 0.0,
    artifacts: Mapping[str, str] | None = None,
    image_path: Path | None = None,
    image_source_url: str | None = None,
    trust_remote_code: bool = True,
    comparison: RunComparison | None = None,
    producer: CheckModelsProvenanceRecord | None = None,
    started_at: str | None = None,
) -> RetainedRun:
    """Build the schema-3 retained run: one metadata row plus ordered results."""
    resolved_policy = (
        mode_policy
        if mode_policy is not None
        else (
            report_context.mode_policy
            if report_context is not None
            else _default_report_mode_policy()
        )
    )
    if report_context is None:
        report_context = _build_report_render_context(
            results=list(results),
            prompt=prompt,
            eval_mode=resolved_policy.eval_mode,
            metadata_exposed_to_prompt=resolved_policy.metadata_exposed_to_prompt,
            system_info=system_info,
        )
    if mode_policy is None:
        resolved_policy = report_context.mode_policy
    cached_results = {result.model_name: result for result in report_context.result_set.results}
    assessments = _assessments_by_model(report_context)
    model_provenance = _model_provenance_by_model(report_context)
    header = _build_jsonl_metadata_record(
        prompt=prompt,
        system_info=system_info,
        library_versions=library_versions,
        runtime_fingerprint=runtime_fingerprint,
        mode_policy=resolved_policy,
        execution_mode=execution_mode,
        counts=_run_outcome_counts(report_context.assessments),
        generation_settings=_common_generation_settings(list(results)),
        image=_run_image_record(
            image_path,
            report_context.image_profile,
            source_url=image_source_url,
        )
        if image_path is not None
        else None,
        total_runtime_seconds=total_runtime_seconds,
        artifacts=artifacts,
        producer=producer,
        trust_remote_code=trust_remote_code,
        comparison=comparison,
        started_at=started_at,
    )
    records: list[JsonlResultRecord] = []
    for original_result in results:
        result = cached_results.get(original_result.model_name, original_result)
        record = _build_jsonl_result_record(
            result,
            assessments[result.model_name],
            requested_revision=requested_revision,
            model_provenance=model_provenance.get(result.model_name),
            recommended_working_set_bytes=report_context.recommended_working_set_bytes,
        )
        burden = _prompt_burden_for_result(result, report_context.image_profile)
        record["prompt_burden"] = {
            "total_tokens": burden.total_tokens,
            "text_tokens_est": burden.text_tokens_est,
            "nontext_tokens_est": burden.nontext_tokens_est,
            "text_tokens_source": burden.text_tokens_source,
            "nontext_ratio": (
                round(burden.nontext_ratio, 2) if burden.nontext_ratio is not None else None
            ),
            "kind": burden.kind,
            "processed_image_width": burden.processed_width,
            "processed_image_height": burden.processed_height,
            "image_patch_count": burden.patch_count,
        }
        records.append(record)
    return RetainedRun(metadata=header, results=tuple(records))


def _write_retained_run(run: RetainedRun, filename: Path) -> None:
    """Serialize one retained run as a metadata line plus ordered result lines."""
    lines = [json.dumps(run.metadata)]
    lines.extend(json.dumps(result) for result in run.results)
    # Stage next to the target and rename, so a failed rewrite (serialisation,
    # disk full, interrupt) leaves the previous file untouched rather than
    # truncated: the final manifest reconciliation relies on that guarantee.
    staging = filename.with_name(f".{filename.name}.{os.getpid()}.tmp")
    try:
        _write_text_file(staging, "\n".join(lines) + "\n")
        staging.replace(filename)
    finally:
        staging.unlink(missing_ok=True)


def save_jsonl_report(
    results: list[PerformanceResult],
    filename: Path,
    prompt: str,
    system_info: dict[str, str],
    **retained_kwargs: object,
) -> None:
    """Build and write the sole machine artifact in one step (test/regen seam)."""
    run = _build_retained_run(
        results,
        prompt=prompt,
        system_info=system_info,
        **cast("dict[str, Any]", retained_kwargs),
    )
    _write_retained_run(run, filename)


def _declared_checkout_version() -> str | None:
    """Return the version ``pyproject.toml`` declares beside this script, if any."""
    try:
        declared = tomllib.loads((_SCRIPT_DIR / "pyproject.toml").read_text(encoding="utf-8")).get(
            "project", {}
        )
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    version_value = declared.get("version") if isinstance(declared, dict) else None
    return version_value if isinstance(version_value, str) and version_value.strip() else None


def _collect_check_models_provenance() -> CheckModelsProvenanceRecord:
    """Collect best-effort producer identity for reproducible run snapshots.

    Inside a checkout (editable install or bare source tree) the version is
    the one the checkout declares, reported alongside its Git revision;
    installed-distribution metadata describes whichever version was last
    ``pip install``-ed and is the fallback only outside a checkout.
    """
    installed = True
    try:
        package_version = version("check_models")
    except PackageNotFoundError:
        package_version = "unknown"
        installed = False

    revision = os.environ.get("GITHUB_SHA") or _run_macos_toolchain_command(
        ("git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD")
    )
    install_type: Literal["editable", "installed", "source-tree", "unknown"]
    if installed and _distribution_is_editable("check_models"):
        install_type = "editable"
    elif revision is not None and (_REPO_ROOT / ".git").exists():
        install_type = "source-tree"
    elif installed:
        install_type = "installed"
    else:
        install_type = "unknown"
    if install_type in {"editable", "source-tree"}:
        package_version = _declared_checkout_version() or package_version
    status = (
        _run_macos_toolchain_command(
            (
                "git",
                "-C",
                str(_REPO_ROOT),
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                ".",
                ":(exclude)src/output",
            ),
            empty_output="",
        )
        if revision is not None
        else None
    )
    return {
        "name": "check_models",
        "version": package_version,
        "git_revision": revision,
        "install_type": install_type,
        "dirty": bool(status) if status is not None else None,
    }


def _common_generation_settings(results: Sequence[PerformanceResult]) -> dict[str, JsonLike]:
    """Return generation settings shared by every result that captured them."""
    captured = [
        diagnostics.generate_kwargs
        for result in results
        if (diagnostics := result.prompt_diagnostics) is not None and diagnostics.generate_kwargs
    ]
    if not captured:
        return {}
    common = dict(captured[0])
    for settings in captured[1:]:
        common = {key: value for key, value in common.items() if settings.get(key) == value}
    return common


def _run_image_record(
    image_path: Path | None,
    image_profile: ImageInputProfile | None,
    *,
    source_url: str | None = None,
) -> RunImageRecord | None:
    """Return a publication-safe source-image manifest without exposing local paths."""
    if image_path is None:
        return None
    try:
        size_bytes = image_path.stat().st_size
    except OSError:
        size_bytes = None
    record: RunImageRecord = {
        "name": image_path.name,
        "sha256": _sha256_file(image_path),
        "size_bytes": size_bytes,
        "width": image_profile.width if image_profile is not None else None,
        "height": image_profile.height if image_profile is not None else None,
        "megapixels": image_profile.megapixels if image_profile is not None else None,
    }
    if source_url is not None:
        record["source_url"] = source_url
    return record


def _describe_run_image(image: RunImageRecord) -> str:
    """One-line input summary: format, dimensions with megapixels, and byte size."""
    parts = [_reproduction_image_format(image)]
    if image["width"] is not None and image["height"] is not None:
        dimensions = f"{image['width']:,} x {image['height']:,} pixels"
        if image["megapixels"] is not None:
            dimensions += f" ({image['megapixels']:.1f} MP)"
        parts.append(dimensions)
    if image["size_bytes"] is not None:
        # Decimal megabytes, matching how camera files and Finder report size.
        parts.append(f"{image['size_bytes'] / 1_000_000:.1f} MB")
    return ", ".join(parts)


def _assessment_scope(profile: str | None) -> str:
    """State the checks actually selected; absence is never a passed contract."""
    if profile == "metadata":
        return "General checks + metadata fields and duplicate keywords; length limits and factual accuracy not assessed"
    if profile == "general":
        return "General checks only; task compliance not assessed"
    return "Legacy assessment; profile not recorded"


def _run_input_summary_rows(
    image: RunImageRecord | None,
    eval_mode: str | None,
    assessment_profile: str | None = None,
) -> tuple[tuple[str, str], ...]:
    """Evaluation lane and input-image facts that every summary surface leads with.

    A 66-megapixel, 66 MB photograph is what turns a prefill into a
    minute-long wait; a skimmer must see that before any per-model timing.
    """
    return (
        ("Evaluation lane", eval_mode or "unknown"),
        ("Assessment", _assessment_scope(assessment_profile)),
        ("Input image", _describe_run_image(image) if image is not None else "unavailable"),
    )


def _output_index_link(index_filename: Path, artifact_path: Path, label: str) -> str:
    """Return a Markdown link from the output index to one artifact."""
    target = _markdown_artifact_target(
        report_filename=index_filename,
        artifact_filename=artifact_path,
    )
    return f"[{MARKDOWN_ESCAPER.escape(label)}]({target})"


# Derived from the canonical Literals / observation registry (F1).
_RUN_ISSUE_EXECUTION_VALUES: Final[frozenset[str]] = _EXECUTION_STATUS_VALUES
_RUN_ISSUE_USABILITY_VALUES: Final[frozenset[str]] = _MODEL_USABILITY_VALUES
_RUN_ISSUE_MAINTAINER_VALUES: Final[frozenset[str]] = _MAINTAINER_STATUS_VALUES
_RUN_ISSUE_OBSERVATION_VALUES: Final[frozenset[str]] = _OBSERVATION_CODE_VALUES


# =============================================================================
# SECTION: RUN COMPARISON (current sweep vs a retained baseline)
# =============================================================================

DEFAULT_COMPARE_WITH: Final[str] = "auto"
_COMPARISON_HISTORY_WINDOW: Final[int] = 10
_COMPARISON_MIN_BAND_SAMPLES: Final[int] = 4
_COMPARISON_TPS_RATIO_FALLBACK_BAND: Final[tuple[float, float]] = (0.85, 1.15)
_COMPARISON_TPS_BAND_MIN_HALF_WIDTH: Final[float] = 0.10
_COMPARISON_PEAK_MEMORY_MIN_DELTA_GB: Final[float] = 0.5
_COMPARISON_PEAK_MEMORY_MIN_DELTA_RATIO: Final[float] = 0.10
_COMPARISON_GIT_TIMEOUT_SECONDS: Final[float] = 20.0


@dataclass(frozen=True)
class RunComparisonModelChange:
    """One model whose execution, usability, or observation set moved."""

    model: str
    baseline_execution: str
    current_execution: str
    baseline_usability: str
    current_usability: str
    observations_added: tuple[str, ...]
    observations_removed: tuple[str, ...]


@dataclass(frozen=True)
class RunComparisonThroughputFlag:
    """One model whose generation throughput left its usual band."""

    model: str
    baseline_tps: float
    current_tps: float
    ratio: float
    band_low: float
    band_high: float
    band_source: Literal["history", "fallback"]
    band_samples: int


@dataclass(frozen=True)
class RunComparisonMemoryChange:
    """One model whose peak memory moved by more than noise."""

    model: str
    baseline_peak_gb: float
    current_peak_gb: float
    delta_gb: float


@dataclass(frozen=True)
class RunComparison:
    """Mechanical diff of the current sweep against a retained baseline sweep."""

    baseline_label: str
    baseline_timestamp: str | None
    baseline_components: tuple[tuple[str, str], ...]
    compared_models: int
    models_added: tuple[str, ...]
    models_removed: tuple[str, ...]
    changes: tuple[RunComparisonModelChange, ...]
    identical_text_models: int
    text_compared_models: int
    tps_ratio_median: float | None
    tps_ratio_min: float | None
    tps_ratio_max: float | None
    tps_compared_models: int
    throughput_flags: tuple[RunComparisonThroughputFlag, ...]
    memory_changes: tuple[RunComparisonMemoryChange, ...]
    history_runs_used: int
    baseline_execution_mode: str = "in_process"
    current_execution_mode: str = "in_process"
    baseline_hardware: str | None = None
    current_hardware: str | None = None
    comparability: Literal["comparable", "unknown", "incomparable"] = "comparable"
    incomparable_reasons: tuple[str, ...] = ()
    unverified_facts: tuple[str, ...] = ()
    revision_changes: tuple[tuple[str, str, str], ...] = ()
    throughput_comparable: bool = True

    @property
    def comparable(self) -> bool:
        """Return whether the per-model diff may be shown at all."""
        return self.comparability != "incomparable"

    @property
    def has_changes(self) -> bool:
        """Return whether anything beyond noise moved."""
        return bool(
            self.models_added
            or self.models_removed
            or self.changes
            or self.throughput_flags
            or self.memory_changes
        )


@dataclass(frozen=True)
class ComparisonBaseline:
    """A loaded baseline: where it came from plus its validated JSONL rows.

    ``image`` and ``generation_settings`` come from the baseline's retained
    metadata header when it can be read from the same source; they drive the
    like-for-like
    check so a prompt, image, or settings change is never reported as a model
    regression.
    """

    label: str
    metadata: JsonlMetadataRecord
    results: tuple[JsonlResultRecord, ...]
    image: RunImageRecord | None = None
    generation_settings: tuple[tuple[str, str], ...] = ()


def _run_git_capture(args: Sequence[str], cwd: Path) -> str | None:
    """Run a read-only git command and return stdout, or None on any failure."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - fixed git binary, read-only subcommands
            [git, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_COMPARISON_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_tracked_relpath(path: Path) -> tuple[Path, str] | None:
    """Return (repo_root, repo-relative POSIX path) when ``path`` is tracked in git."""
    parent = path.parent if path.parent.exists() else Path.cwd()
    top = _run_git_capture(["rev-parse", "--show-toplevel"], parent)
    if not top:
        return None
    repo_root = Path(top.strip())
    try:
        relpath = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    tracked = _run_git_capture(["ls-files", "--error-unmatch", "--", relpath], repo_root)
    if tracked is None:
        return None
    return repo_root, relpath


def _parse_jsonl_text_rows(text: str, label: str) -> list[JsonLike]:
    """Decode JSONL text into rows with label-aware errors."""
    lines = [line for line in text.splitlines() if line]
    if not lines:
        message = f"Missing JSONL metadata in {label}"
        raise ValueError(message)
    rows: list[JsonLike] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            message = f"Invalid JSONL row {line_number} in {label}: {error.msg}"
            raise ValueError(message) from error
    return rows


def _baseline_from_jsonl_text(text: str, label: str) -> ComparisonBaseline:
    """Validate baseline JSONL text into a ComparisonBaseline.

    A schema-2 baseline fails the single loader's format check; the caller
    logs that one-time incomparability instead of keeping an adapter.
    """
    run = _load_retained_run_text(text, label)
    source = _run_issue_summary_source_from_run(run)
    return ComparisonBaseline(
        label=label,
        metadata=run.metadata,
        results=run.results,
        image=source.image,
        generation_settings=source.generation_settings,
    )


def _resolve_comparison_baseline(
    spec: str | None,
    jsonl_path: Path,
) -> ComparisonBaseline | None:
    """Resolve ``--compare-with`` into a loaded baseline, or None when unavailable.

    ``auto`` compares against the retained sweep at ``HEAD`` when the JSONL path
    is tracked in git; ``none`` disables; an existing file is read directly;
    anything else is treated as a git ref for the same repo-relative path.
    Every failure mode degrades to "no comparison" — this is evidence, not a
    gate — and is logged once.
    """
    if spec is None:
        spec = DEFAULT_COMPARE_WITH
    choice = spec.strip()
    if choice.lower() == "none":
        return None
    try:
        if choice.lower() != "auto":
            candidate = Path(choice).expanduser()
            if candidate.is_file():
                return _baseline_from_jsonl_text(_read_text_file(candidate), str(candidate))
        tracked = _git_tracked_relpath(jsonl_path)
        if tracked is None:
            if choice.lower() != "auto":
                logger.warning(
                    "--compare-with %s: %s is not a file and %s is not tracked in git; "
                    "skipping comparison.",
                    choice,
                    choice,
                    jsonl_path,
                )
            return None
        repo_root, relpath = tracked
        ref = "HEAD" if choice.lower() == "auto" else choice
        text = _run_git_capture(["show", f"{ref}:{relpath}"], repo_root)
        if text is None:
            logger.warning(
                "--compare-with %s: could not read %s:%s from git; skipping comparison.",
                choice,
                ref,
                relpath,
            )
            return None
        label = f"{ref}:{relpath}"
        if ref == "HEAD":
            sha = _run_git_capture(["rev-parse", "--short", "HEAD"], repo_root)
            if sha:
                label = f"{sha.strip()}:{relpath}"
        return _baseline_from_jsonl_text(text, label)
    except (OSError, ValueError, TypeError) as error:
        logger.warning(
            "--compare-with %s: baseline unusable (%s); skipping comparison.", choice, error
        )
        return None


def _history_band_tps_sample(facts: object) -> float | None:
    """Return one usable throughput sample from a history facts dict.

    Aborted generations carry rates over truncated sequences; they must not
    shape the noise band.
    """
    if not isinstance(facts, dict) or facts.get("stop_reason") == "repetition_abort":
        return None
    tps = facts.get("generation_tps")
    if isinstance(tps, (int, float)) and tps > 0:
        return float(tps)
    return None


def _history_tps_bands(
    history_path: Path,
    *,
    fingerprint: str | None,
    exclude_last: bool,
    current_revisions: Mapping[str, str | None] | None = None,
    current_settings: Mapping[str, str | None] | None = None,
) -> tuple[dict[str, tuple[float, float, int]], int]:
    """Return per-model (low, high, samples) throughput bands from retained history.

    Uses the last ``_COMPARISON_HISTORY_WINDOW`` runs with the same comparison
    fingerprint — prompt, image, generation settings, lane, execution mode and
    hardware (rows recorded without one are excluded: they cannot be shown to
    be the same workload, so the fixed fallback band applies) — and a Tukey
    fence (Q1 - 1.5 IQR, Q3 + 1.5 IQR) per model, never narrower than ±10% of
    the median. A model's samples must also come from the revision now under
    test when ``current_revisions`` names one, and from the same effective
    per-model generation settings when ``current_settings`` carries their
    canonical form (see ``_canonical_generation_settings``). ``exclude_last`` drops the
    record just appended for the current run so it cannot vouch for itself;
    callers pass it only after a confirmed append.
    """
    if not history_path.is_file():
        return {}, 0
    try:
        rows = [line for line in _read_text_file(history_path).splitlines() if line]
    except OSError:
        return {}, 0
    if exclude_last and rows:
        rows = rows[:-1]
    runs: list[dict[str, JsonLike]] = []
    for line in rows:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("_type") != "run":
            continue
        if fingerprint and record.get("comparison_fingerprint") != fingerprint:
            # Rows without a matching fingerprint cannot be shown to be the
            # same workload; a band must only be built from runs known to match.
            continue
        runs.append(record)
    runs = runs[-_COMPARISON_HISTORY_WINDOW:]
    samples: dict[str, list[float]] = {}
    for record in runs:
        model_results = record.get("model_results")
        if not isinstance(model_results, dict):
            continue
        for model, facts in model_results.items():
            if not _history_sample_matches_current(
                facts,
                wanted_revision=(current_revisions or {}).get(model),
                wanted_settings=(current_settings or {}).get(model),
            ):
                continue
            if (tps := _history_band_tps_sample(facts)) is not None:
                samples.setdefault(model, []).append(tps)
    bands: dict[str, tuple[float, float, int]] = {}
    for model, values in samples.items():
        if len(values) < _COMPARISON_MIN_BAND_SAMPLES:
            continue
        ordered = sorted(values)
        q1, q3 = _quantile(ordered, 0.25), _quantile(ordered, 0.75)
        median = _quantile(ordered, 0.5)
        iqr = q3 - q1
        # A handful of near-identical samples yields a fence a couple of percent
        # wide, which flags ordinary run-to-run variance; never narrower than
        # ±10% of the history median.
        low = min(q1 - 1.5 * iqr, median * (1.0 - _COMPARISON_TPS_BAND_MIN_HALF_WIDTH))
        high = max(q3 + 1.5 * iqr, median * (1.0 + _COMPARISON_TPS_BAND_MIN_HALF_WIDTH))
        bands[model] = (max(low, 0.0), high, len(values))
    return bands, len(runs)


def _current_model_revisions(
    current: Sequence[JsonlResultRecord],
) -> dict[str, str | None]:
    """Resolved revision per model in the current run, from the retained rows."""
    return {
        record["model"]: provenance.get("resolved_revision")
        for record in current
        if isinstance(provenance := record.get("model_provenance"), dict)
    }


def _current_model_settings(
    current: Sequence[JsonlResultRecord],
) -> dict[str, str | None]:
    """Canonical effective generation settings per model in the current run."""
    return {
        record["model"]: _canonical_generation_settings(diagnostics.get("generate_kwargs"))
        for record in current
        if isinstance(diagnostics := record.get("prompt_diagnostics"), dict)
    }


def _history_sample_matches_current(
    facts: object,
    *,
    wanted_revision: str | None,
    wanted_settings: str | None,
) -> bool:
    """Return whether a history sample shares the current model's revision and settings.

    A wanted fact the row cannot show it matches (missing or different)
    excludes the sample; an unknown current fact excludes nothing.
    """
    if wanted_revision is not None and (
        not isinstance(facts, dict) or facts.get("resolved_revision") != wanted_revision
    ):
        return False
    return wanted_settings is None or (
        isinstance(facts, dict)
        and _canonical_generation_settings(facts.get("generation_settings")) == wanted_settings
    )


def _canonical_generation_settings(settings: object) -> str | None:
    """Canonical JSON for one model's effective generation settings, or None if absent."""
    if not isinstance(settings, dict) or not settings:
        return None
    return json.dumps(settings, ensure_ascii=False, sort_keys=True, default=str)


def _quantile(ordered: Sequence[float], q: float) -> float:
    """Linear-interpolated quantile of an already-sorted sequence."""
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _comparison_component_rows(metadata: JsonlMetadataRecord) -> tuple[tuple[str, str], ...]:
    """Summarise a baseline's stack identity (version plus short source revision)."""
    rows: list[tuple[str, str]] = []
    provenance = metadata.get("component_provenance") or {}
    versions = metadata.get("library_versions") or {}
    for name in ("check_models", "mlx", "mlx-vlm", "transformers"):
        entry = provenance.get(name) if isinstance(provenance, dict) else None
        version = None
        revision = None
        if isinstance(entry, dict):
            version = entry.get("version")
            revision = entry.get("source_revision") or entry.get("vcs_revision")
        if version is None:
            version = versions.get(name) if isinstance(versions, dict) else None
        if version is None and revision is None:
            continue
        text = f"{version}" if version is not None else ""
        if isinstance(revision, str) and revision:
            text = f"{text} @ {revision[:9]}".strip()
        rows.append((name, text))
    system_info = metadata.get("system")
    python_version = system_info.get("Python Version") if isinstance(system_info, dict) else None

    if python_version:
        rows.append(("python", f"{python_version}"))
    if (hardware := _comparison_hardware(metadata)) is not None:
        rows.append(("hardware", hardware))
    return tuple(rows)


def _record_repetition_aborted(record: JsonlResultRecord) -> bool:
    """Return whether this result's generation was stopped by the repetition guard."""
    return "repetition_abort" in record["assessment"]["observations"]


def _result_generation_tps(record: JsonlResultRecord) -> float | None:
    metrics = record.get("metrics") or {}
    value = metrics.get("generation_tps") if isinstance(metrics, dict) else None
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def _result_peak_memory_gb(record: JsonlResultRecord) -> float | None:
    metrics = record.get("metrics") or {}
    value = metrics.get("peak_memory_gb") if isinstance(metrics, dict) else None
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def _model_revision_change(
    model: str, now: JsonlResultRecord, before: JsonlResultRecord
) -> tuple[str, str, str] | None:
    """Return (model, baseline revision, current revision) when the snapshot moved."""
    now_rev = (now.get("model_provenance") or {}).get("resolved_revision")
    before_rev = (before.get("model_provenance") or {}).get("resolved_revision")
    if now_rev and before_rev and now_rev != before_rev:
        return (model, before_rev, now_rev)
    return None


def _model_assessment_change(
    model: str, now: JsonlResultRecord, before: JsonlResultRecord
) -> RunComparisonModelChange | None:
    """Return the execution/usability/observation transition for one model, if any."""
    now_a, before_a = now["assessment"], before["assessment"]
    now_obs, before_obs = set(now_a["observations"]), set(before_a["observations"])
    if (
        now_a["execution"] == before_a["execution"]
        and now_a["usability"] == before_a["usability"]
        and now_obs == before_obs
    ):
        return None
    return RunComparisonModelChange(
        model=model,
        baseline_execution=before_a["execution"],
        current_execution=now_a["execution"],
        baseline_usability=before_a["usability"],
        current_usability=now_a["usability"],
        observations_added=tuple(sorted(now_obs - before_obs)),
        observations_removed=tuple(sorted(before_obs - now_obs)),
    )


def _model_throughput_flag(
    model: str,
    *,
    now_tps: float,
    before_tps: float,
    band: tuple[float, float, int] | None,
) -> RunComparisonThroughputFlag | None:
    """Flag a model whose throughput left its history band (or the fallback band)."""
    ratio = now_tps / before_tps
    if band is not None:
        low, high, samples = band
        if not low <= now_tps <= high:
            return RunComparisonThroughputFlag(
                model, before_tps, now_tps, ratio, low, high, "history", samples
            )
        return None
    low_ratio, high_ratio = _COMPARISON_TPS_RATIO_FALLBACK_BAND
    if not low_ratio <= ratio <= high_ratio:
        return RunComparisonThroughputFlag(
            model,
            before_tps,
            now_tps,
            ratio,
            before_tps * low_ratio,
            before_tps * high_ratio,
            "fallback",
            0,
        )
    return None


def _model_memory_change(
    model: str, now: JsonlResultRecord, before: JsonlResultRecord
) -> RunComparisonMemoryChange | None:
    """Return a peak-memory move beyond both the absolute and relative floors."""
    now_peak, before_peak = _result_peak_memory_gb(now), _result_peak_memory_gb(before)
    if now_peak is None or before_peak is None:
        return None
    delta = now_peak - before_peak
    if (
        abs(delta) >= _COMPARISON_PEAK_MEMORY_MIN_DELTA_GB
        and abs(delta) / before_peak >= _COMPARISON_PEAK_MEMORY_MIN_DELTA_RATIO
    ):
        return RunComparisonMemoryChange(model, before_peak, now_peak, delta)
    return None


def _compare_model_performance(
    model: str,
    now: JsonlResultRecord,
    before: JsonlResultRecord,
    *,
    bands: Mapping[str, tuple[float, float, int]],
    ratios: list[float],
    flags: list[RunComparisonThroughputFlag],
    memory: list[RunComparisonMemoryChange],
) -> None:
    """Accumulate throughput and memory deltas for one like-for-like model pair."""
    if _record_repetition_aborted(now) or _record_repetition_aborted(before):
        # A rate measured over an aborted (few-hundred-token) generation is
        # not comparable with a full-length run; autoregressive throughput
        # varies with sequence length.
        return
    now_tps, before_tps = _result_generation_tps(now), _result_generation_tps(before)
    if now_tps is not None and before_tps is not None:
        ratios.append(now_tps / before_tps)
        flag = _model_throughput_flag(
            model, now_tps=now_tps, before_tps=before_tps, band=bands.get(model)
        )
        if flag is not None:
            flags.append(flag)
    if (memory_change := _model_memory_change(model, now, before)) is not None:
        memory.append(memory_change)


def compare_run_results(
    current: Sequence[JsonlResultRecord],
    baseline: ComparisonBaseline,
    *,
    history_path: Path | None = None,
    comparison_fingerprint: str | None = None,
    history_excludes_current: bool = True,
    current_execution_mode: str = "in_process",
    current_metadata: JsonlMetadataRecord | None = None,
    current_image: RunImageRecord | None = None,
    current_generation_settings: tuple[tuple[str, str], ...] = (),
) -> RunComparison:
    """Diff current JSONL result rows against a baseline sweep, mechanically.

    Everything is model-agnostic: execution/usability/observation transitions,
    byte-identical generated text, throughput ratios against per-model history
    bands (or a fixed ±15% fallback when history is thin), and peak-memory
    moves beyond 0.5 GB and 10%. The runs must be like-for-like — same prompt,
    image, evaluation lane, and generation settings — or the per-model diff is
    withheld and the reasons are reported instead; per-model revision changes
    are reported alongside the diff.
    """
    incomparable_reasons, unverified_facts = _comparison_compatibility(
        baseline,
        current_metadata=current_metadata,
        current_image=current_image,
        current_generation_settings=current_generation_settings,
    )
    baseline_hardware = _comparison_hardware(baseline.metadata)
    current_hardware = _comparison_hardware(current_metadata)
    throughput_comparable = (
        current_execution_mode == str(baseline.metadata.get("execution_mode", "in_process"))
        and baseline_hardware == current_hardware
        and not unverified_facts
        and not incomparable_reasons
    )
    current_by = {record["model"]: record for record in current}
    baseline_by = {record["model"]: record for record in baseline.results}
    shared = [model for model in current_by if model in baseline_by]
    bands, history_runs = (
        _history_tps_bands(
            history_path,
            fingerprint=comparison_fingerprint,
            exclude_last=history_excludes_current,
            current_revisions=_current_model_revisions(current),
            current_settings=_current_model_settings(current),
        )
        if history_path is not None
        else ({}, 0)
    )

    changes: list[RunComparisonModelChange] = []
    identical_text = 0
    text_compared = 0
    ratios: list[float] = []
    flags: list[RunComparisonThroughputFlag] = []
    memory: list[RunComparisonMemoryChange] = []
    revision_changes: list[tuple[str, str, str]] = []
    for model in shared:
        now, before = current_by[model], baseline_by[model]
        if (revision := _model_revision_change(model, now, before)) is not None:
            revision_changes.append(revision)
        if (change := _model_assessment_change(model, now, before)) is not None:
            changes.append(change)
        if now["assessment"]["execution"] == "completed" and (
            before["assessment"]["execution"] == "completed"
        ):
            text_compared += 1
            if now.get("generated_text", "") == before.get("generated_text", ""):
                identical_text += 1
        if throughput_comparable:
            _compare_model_performance(
                model, now, before, bands=bands, ratios=ratios, flags=flags, memory=memory
            )

    ratios_sorted = sorted(ratios)
    return RunComparison(
        baseline_label=baseline.label,
        baseline_timestamp=baseline.metadata.get("timestamp"),
        baseline_components=_comparison_component_rows(baseline.metadata),
        compared_models=len(shared),
        models_added=tuple(sorted(set(current_by) - set(baseline_by))),
        models_removed=tuple(sorted(set(baseline_by) - set(current_by))),
        changes=tuple(changes),
        identical_text_models=identical_text,
        text_compared_models=text_compared,
        tps_ratio_median=_quantile(ratios_sorted, 0.5) if ratios_sorted else None,
        tps_ratio_min=ratios_sorted[0] if ratios_sorted else None,
        tps_ratio_max=ratios_sorted[-1] if ratios_sorted else None,
        tps_compared_models=len(ratios_sorted),
        throughput_flags=tuple(flags),
        memory_changes=tuple(memory),
        history_runs_used=history_runs,
        baseline_execution_mode=str(baseline.metadata.get("execution_mode", "in_process")),
        current_execution_mode=current_execution_mode,
        baseline_hardware=baseline_hardware,
        current_hardware=current_hardware,
        comparability=(
            "incomparable"
            if incomparable_reasons
            else ("unknown" if unverified_facts else "comparable")
        ),
        incomparable_reasons=incomparable_reasons,
        unverified_facts=unverified_facts,
        revision_changes=tuple(revision_changes),
        throughput_comparable=throughput_comparable,
    )


def _hardware_identity(system_info: Mapping[str, object] | None) -> str | None:
    """Chip, GPU core count and RAM: the facts that set throughput and peak memory.

    The chip name alone is not an identity — the same chip ships with
    different GPU core counts and memory, and both move the numbers.
    """
    if not isinstance(system_info, Mapping):
        return None
    chip = system_info.get("GPU/Chip")
    if not isinstance(chip, str) or not chip:
        return None
    parts = [chip]
    if isinstance(cores := system_info.get("GPU Cores"), str) and cores:
        parts.append(f"{cores} GPU cores")
    if isinstance(ram := system_info.get("RAM"), str) and ram:
        parts.append(f"{ram} RAM")
    return ", ".join(parts)


def _comparison_hardware(metadata: JsonlMetadataRecord | None) -> str | None:
    """Return the hardware identity a run executed on, or None when the header lacks it."""
    return _hardware_identity(metadata.get("system") if metadata is not None else None)


def _comparison_fingerprint(
    *,
    prompt: str,
    image_sha256: str | None,
    generation_settings: Mapping[str, JsonLike],
    execution_mode: str,
    eval_mode: str,
    system_info: Mapping[str, object] | None,
) -> str:
    """Identity of one throughput workload: inputs, settings, lane, mode and hardware.

    History noise bands are built only from runs sharing this fingerprint. A
    blind prompt reused for several photographs, a settings change on the same
    prompt, an isolated rerun, or another machine must not blend into one
    "noise" estimate; runs recorded before the fingerprint existed simply
    fall back to the fixed band.
    """
    payload = {
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "image_sha256": image_sha256,
        "generation_settings": {
            key: json.dumps(value, ensure_ascii=False, sort_keys=True)
            for key, value in sorted(generation_settings.items())
        },
        "execution_mode": execution_mode,
        "eval_mode": eval_mode,
        "hardware": _hardware_identity(system_info),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _comparison_fingerprint_from_metadata(metadata: JsonlMetadataRecord) -> str:
    """Fingerprint of a retained run from its schema-3 header alone."""
    image = metadata.get("image")
    sha256 = image.get("sha256") if isinstance(image, dict) else None
    settings = metadata.get("generation_settings")
    return _comparison_fingerprint(
        prompt=metadata["prompt"],
        image_sha256=sha256 if isinstance(sha256, str) else None,
        generation_settings=settings if isinstance(settings, dict) else {},
        execution_mode=str(metadata.get("execution_mode", "in_process")),
        eval_mode=str(metadata.get("eval_mode", "")),
        system_info=cast("Mapping[str, object] | None", metadata.get("system")),
    )


def _comparison_compatibility(
    baseline: ComparisonBaseline,
    *,
    current_metadata: JsonlMetadataRecord | None,
    current_image: RunImageRecord | None,
    current_generation_settings: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (mismatch reasons, facts that could not be verified).

    A fact missing on either side is *unknown*, not a mismatch — but it is
    named, so absent evidence is never silently promoted to "comparable".
    """
    reasons: list[str] = []
    unverified: list[str] = []
    if current_metadata is None:
        unverified.append("current run metadata")
    else:
        if current_metadata.get("prompt") != baseline.metadata.get("prompt"):
            reasons.append("prompt differs")
        now_mode, before_mode = (
            current_metadata.get("eval_mode"),
            baseline.metadata.get("eval_mode"),
        )
        if now_mode and before_mode and now_mode != before_mode:
            reasons.append(f"evaluation lane differs ({before_mode} → {now_mode})")
        elif not (now_mode and before_mode):
            unverified.append("evaluation lane")
    now_sha = current_image.get("sha256") if current_image else None
    before_sha = baseline.image.get("sha256") if baseline.image else None
    if now_sha and before_sha:
        if now_sha != before_sha:
            reasons.append(f"image differs (sha256 {before_sha[:12]}… → {now_sha[:12]}…)")
    else:
        unverified.append("image identity")
    if current_metadata is not None and current_metadata.get(
        "assessment_profile"
    ) != baseline.metadata.get("assessment_profile"):
        reasons.append("assessment profile differs (or was not recorded in the baseline)")
    if _comparison_hardware(current_metadata) is None or (
        _comparison_hardware(baseline.metadata) is None
    ):
        unverified.append("hardware identity")
    if current_generation_settings and baseline.generation_settings:
        now_settings = dict(current_generation_settings)
        before_settings = dict(baseline.generation_settings)
        diffs = sorted(
            f"{key} {before_settings.get(key)} → {now_settings.get(key)}"
            for key in set(now_settings) | set(before_settings)
            if now_settings.get(key) != before_settings.get(key)
        )
        if diffs:
            reasons.append("generation settings differ: " + ", ".join(diffs))
    else:
        unverified.append("generation settings")
    return tuple(reasons), tuple(unverified)


def _run_comparison_to_json(comparison: RunComparison | None) -> dict[str, JsonLike] | None:
    """Serialise a RunComparison for the retained ``results.jsonl`` metadata."""
    if comparison is None:
        return None

    def _r(value: float | None) -> float | None:
        return round(value, 4) if value is not None else None

    execution_mode: JsonLike = {
        "baseline": comparison.baseline_execution_mode,
        "current": comparison.current_execution_mode,
    }
    hardware: JsonLike = {
        "baseline": comparison.baseline_hardware,
        "current": comparison.current_hardware,
    }
    if not comparison.comparable:
        return {
            "baseline": comparison.baseline_label,
            "baseline_timestamp": comparison.baseline_timestamp,
            "baseline_components": cast("JsonLike", dict(comparison.baseline_components)),
            "comparability": comparison.comparability,
            "incomparable_reasons": cast("JsonLike", list(comparison.incomparable_reasons)),
            "execution_mode": execution_mode,
            "hardware": hardware,
        }
    return {
        "baseline": comparison.baseline_label,
        "baseline_timestamp": comparison.baseline_timestamp,
        "baseline_components": cast("JsonLike", dict(comparison.baseline_components)),
        "comparability": comparison.comparability,
        "unverified_facts": cast("JsonLike", list(comparison.unverified_facts)),
        "throughput_comparable": comparison.throughput_comparable,
        "revision_changes": [
            {"model": model, "baseline": before, "current": after}
            for model, before, after in comparison.revision_changes
        ],
        "compared_models": comparison.compared_models,
        "models_added": cast("JsonLike", list(comparison.models_added)),
        "models_removed": cast("JsonLike", list(comparison.models_removed)),
        "changes": [
            {
                "model": change.model,
                "execution": [change.baseline_execution, change.current_execution],
                "usability": [change.baseline_usability, change.current_usability],
                "observations_added": list(change.observations_added),
                "observations_removed": list(change.observations_removed),
            }
            for change in comparison.changes
        ],
        "identical_text_models": comparison.identical_text_models,
        "text_compared_models": comparison.text_compared_models,
        "generation_tps_ratio": {
            "median": _r(comparison.tps_ratio_median),
            "min": _r(comparison.tps_ratio_min),
            "max": _r(comparison.tps_ratio_max),
            "compared_models": comparison.tps_compared_models,
        },
        "throughput_flags": [
            {
                "model": flag.model,
                "baseline_tps": _r(flag.baseline_tps),
                "current_tps": _r(flag.current_tps),
                "ratio": _r(flag.ratio),
                "band": [_r(flag.band_low), _r(flag.band_high)],
                "band_source": flag.band_source,
                "band_samples": flag.band_samples,
            }
            for flag in comparison.throughput_flags
        ],
        "memory_changes": [
            {
                "model": change.model,
                "baseline_peak_gb": _r(change.baseline_peak_gb),
                "current_peak_gb": _r(change.current_peak_gb),
                "delta_gb": _r(change.delta_gb),
            }
            for change in comparison.memory_changes
        ],
        "history_runs_used": comparison.history_runs_used,
        "execution_mode": execution_mode,
        "hardware": hardware,
    }


def _comparison_opt_float(raw: JsonLike) -> float | None:
    """Narrow one optional retained comparison number, rejecting non-numbers."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        message = f"comparison field is not a number: {raw!r}"
        raise TypeError(message)
    return float(raw)


def _comparison_req_float(raw: JsonLike) -> float:
    """Narrow one required retained comparison number."""
    number = _comparison_opt_float(raw)
    if number is None:
        message = "comparison field is missing a required number"
        raise TypeError(message)
    return number


def _comparison_req_int(raw: JsonLike) -> int:
    """Narrow one required retained comparison integer."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        message = f"comparison field is not an integer: {raw!r}"
        raise TypeError(message)
    return raw


def _comparison_req_str(raw: JsonLike) -> str:
    """Narrow one required retained comparison string."""
    if not isinstance(raw, str):
        message = f"comparison field is not a string: {raw!r}"
        raise TypeError(message)
    return raw


def _comparison_str_items(raw: JsonLike) -> tuple[str, ...]:
    """Narrow one retained comparison list of strings."""
    if not isinstance(raw, list):
        message = f"comparison field is not a list: {raw!r}"
        raise TypeError(message)
    return tuple(_comparison_req_str(item) for item in raw)


def _comparison_pair(raw: JsonLike) -> tuple[JsonLike, JsonLike]:
    """Narrow one retained comparison before/after pair."""
    if not isinstance(raw, list) or len(raw) != _COMPARISON_JSON_PAIR_LENGTH:
        message = f"comparison field is not a two-item list: {raw!r}"
        raise TypeError(message)
    return raw[0], raw[1]


def _comparison_band_source(raw: JsonLike) -> Literal["history", "fallback"]:
    """Narrow one retained throughput-band source to its known values."""
    if raw not in ("history", "fallback"):
        message = f"comparison band_source is not a known value: {raw!r}"
        raise ValueError(message)
    return cast("Literal['history', 'fallback']", raw)


def _comparison_req_bool(raw: JsonLike) -> bool:
    """Narrow one required retained comparison boolean (never bool() coercion)."""
    if not isinstance(raw, bool):
        message = f"comparison field is not a boolean: {raw!r}"
        raise TypeError(message)
    return raw


def _comparison_opt_str(raw: JsonLike) -> str | None:
    """Narrow one optional retained comparison string."""
    if raw is not None and not isinstance(raw, str):
        message = f"comparison field is not a string or null: {raw!r}"
        raise TypeError(message)
    return raw


def _comparison_mapping(raw: JsonLike) -> dict[str, JsonLike]:
    """Narrow one retained comparison object, defaulting only true absence."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        message = f"comparison field is not an object: {raw!r}"
        raise TypeError(message)
    return raw


def _comparison_rows(raw: JsonLike) -> tuple[dict[str, JsonLike], ...]:
    """Narrow one retained comparison list of objects."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        message = f"comparison field is not a list of objects: {raw!r}"
        raise TypeError(message)
    return tuple(cast("dict[str, JsonLike]", item) for item in raw)


def _run_comparison_from_json(value: dict[str, JsonLike]) -> RunComparison:
    """Rehydrate the retained metadata comparison for summary regeneration.

    Strict inverse of :func:`_run_comparison_to_json` for the fields every
    renderer consumes; a malformed payload raises and the caller degrades to
    regenerating without the baseline section.
    """
    components = _comparison_mapping(value.get("baseline_components"))
    execution_mode = _comparison_mapping(value.get("execution_mode"))
    hardware = _comparison_mapping(value.get("hardware"))
    comparability_value = value.get("comparability", "comparable")
    if comparability_value not in ("comparable", "unknown", "incomparable"):
        message = f"comparison comparability is not a known value: {comparability_value!r}"
        raise ValueError(message)
    comparability = cast("Literal['comparable', 'unknown', 'incomparable']", comparability_value)
    identity: dict[str, object] = {
        "baseline_label": _comparison_req_str(value.get("baseline", "unknown baseline")),
        "baseline_timestamp": _comparison_opt_str(value.get("baseline_timestamp")),
        "baseline_components": tuple(
            (_comparison_req_str(name), _comparison_req_str(part))
            for name, part in components.items()
        ),
        "baseline_execution_mode": _comparison_req_str(
            execution_mode.get("baseline", "in_process")
        ),
        "current_execution_mode": _comparison_req_str(execution_mode.get("current", "in_process")),
        "baseline_hardware": _comparison_opt_str(hardware.get("baseline")),
        "current_hardware": _comparison_opt_str(hardware.get("current")),
        "comparability": comparability,
    }
    if comparability == "incomparable":
        return RunComparison(
            compared_models=0,
            models_added=(),
            models_removed=(),
            changes=(),
            identical_text_models=0,
            text_compared_models=0,
            tps_ratio_median=None,
            tps_ratio_min=None,
            tps_ratio_max=None,
            tps_compared_models=0,
            throughput_flags=(),
            memory_changes=(),
            history_runs_used=0,
            incomparable_reasons=_comparison_str_items(value.get("incomparable_reasons") or []),
            **cast("dict[str, Any]", identity),
        )
    ratio = _comparison_mapping(value.get("generation_tps_ratio"))
    changes = tuple(
        RunComparisonModelChange(
            model=_comparison_req_str(change["model"]),
            baseline_execution=_comparison_req_str(_comparison_pair(change["execution"])[0]),
            current_execution=_comparison_req_str(_comparison_pair(change["execution"])[1]),
            baseline_usability=_comparison_req_str(_comparison_pair(change["usability"])[0]),
            current_usability=_comparison_req_str(_comparison_pair(change["usability"])[1]),
            observations_added=_comparison_str_items(change["observations_added"]),
            observations_removed=_comparison_str_items(change["observations_removed"]),
        )
        for change in _comparison_rows(value.get("changes"))
    )
    throughput_flags = tuple(
        RunComparisonThroughputFlag(
            model=_comparison_req_str(flag["model"]),
            baseline_tps=_comparison_req_float(flag["baseline_tps"]),
            current_tps=_comparison_req_float(flag["current_tps"]),
            ratio=_comparison_req_float(flag["ratio"]),
            band_low=_comparison_req_float(_comparison_pair(flag["band"])[0]),
            band_high=_comparison_req_float(_comparison_pair(flag["band"])[1]),
            band_source=_comparison_band_source(flag["band_source"]),
            band_samples=_comparison_req_int(flag["band_samples"]),
        )
        for flag in _comparison_rows(value.get("throughput_flags"))
    )
    memory_changes = tuple(
        RunComparisonMemoryChange(
            model=_comparison_req_str(change["model"]),
            baseline_peak_gb=_comparison_req_float(change["baseline_peak_gb"]),
            current_peak_gb=_comparison_req_float(change["current_peak_gb"]),
            delta_gb=_comparison_req_float(change["delta_gb"]),
        )
        for change in _comparison_rows(value.get("memory_changes"))
    )
    return RunComparison(
        compared_models=_comparison_req_int(value.get("compared_models", 0)),
        models_added=_comparison_str_items(value.get("models_added") or []),
        models_removed=_comparison_str_items(value.get("models_removed") or []),
        changes=changes,
        identical_text_models=_comparison_req_int(value.get("identical_text_models", 0)),
        text_compared_models=_comparison_req_int(value.get("text_compared_models", 0)),
        tps_ratio_median=_comparison_opt_float(ratio.get("median")),
        tps_ratio_min=_comparison_opt_float(ratio.get("min")),
        tps_ratio_max=_comparison_opt_float(ratio.get("max")),
        tps_compared_models=_comparison_req_int(ratio.get("compared_models", 0)),
        throughput_flags=throughput_flags,
        memory_changes=memory_changes,
        history_runs_used=_comparison_req_int(value.get("history_runs_used", 0)),
        unverified_facts=_comparison_str_items(value.get("unverified_facts") or []),
        revision_changes=tuple(
            (
                _comparison_req_str(entry["model"]),
                _comparison_req_str(entry["baseline"]),
                _comparison_req_str(entry["current"]),
            )
            for entry in _comparison_rows(value.get("revision_changes"))
        ),
        throughput_comparable=_comparison_req_bool(value.get("throughput_comparable", True)),
        **cast("dict[str, Any]", identity),
    )


_COMPARISON_JSON_PAIR_LENGTH: Final[int] = 2
_COMPARISON_MODEL_LIST_LIMIT: Final[int] = 8


def _comparison_model_list(models: Sequence[str]) -> str:
    """List models inline, collapsing long lists (targeted runs) to a count."""
    if len(models) > _COMPARISON_MODEL_LIST_LIMIT:
        return f"{len(models)} models (targeted run against a full-sweep baseline)"
    return ", ".join(f"`{model}`" for model in models)


def _format_usability_transition(before: str, after: str) -> str:
    before_label = _human_status_label(before)
    return before_label if before == after else f"{before_label} → {_human_status_label(after)}"


def _format_observation_delta(change: RunComparisonModelChange) -> str:
    """Compact +added/-removed observation labels shared by every renderer."""
    # Baseline codes come from a JSONL on disk (possibly written by an older
    # harness), so an unknown code falls back to its raw name instead of
    # crashing comparison rendering.
    parts = [
        f"+{_OBSERVATION_SELECTOR_GLOSSES.get(cast('ObservationCode', code), code)}"
        for code in change.observations_added
    ] + [
        f"-{_OBSERVATION_SELECTOR_GLOSSES.get(cast('ObservationCode', code), code)}"
        for code in change.observations_removed
    ]
    return "; ".join(parts) or "—"


@dataclass(frozen=True)
class _ComparisonView:
    """Formatted comparison rows derived once and shared by Markdown and terminal.

    The retained metadata keeps its own raw-number serialization; everything
    human-facing renders from this view so wording and withholding rules cannot
    drift between surfaces.
    """

    identity_rows: tuple[tuple[str, str], ...]
    summary_rows: tuple[tuple[str, str], ...]
    banner: str | None
    revision_note: str | None
    membership_items: tuple[str, ...]
    change_rows: tuple[tuple[str, str, str, str], ...]
    flag_rows: tuple[tuple[str, str, str, str, str], ...]
    memory_rows: tuple[tuple[str, str, str, str], ...]


def _comparison_view(comparison: RunComparison) -> _ComparisonView:
    """Derive every formatted row of the baseline diff exactly once."""
    if not comparison.throughput_comparable:
        ratio_text = (
            "withheld (hardware, execution mode or inputs not established as like-for-like)"
        )
    elif (
        comparison.tps_ratio_median is not None
        and comparison.tps_ratio_min is not None
        and comparison.tps_ratio_max is not None
    ):
        ratio_text = (
            f"{comparison.tps_ratio_median:.3f} (range {comparison.tps_ratio_min:.2f}-"
            f"{comparison.tps_ratio_max:.2f}, {comparison.tps_compared_models} models)"
        )
    else:
        ratio_text = "n/a"
    band_text = (
        f"history (last {comparison.history_runs_used} same-prompt runs, Tukey fence, "
        "at least ±10% of the median)"
        if comparison.history_runs_used >= _COMPARISON_MIN_BAND_SAMPLES
        else "fixed ±15% fallback (insufficient history)"
    )

    identity_rows: list[tuple[str, str]] = [("Baseline", comparison.baseline_label)]
    if comparison.baseline_timestamp:
        identity_rows.append(("Baseline run timestamp", comparison.baseline_timestamp))
    identity_rows.extend(
        (f"Baseline {name}", value) for name, value in comparison.baseline_components
    )

    summary_rows: list[tuple[str, str]] = [
        ("Models compared", str(comparison.compared_models)),
        (
            "Identical generated text",
            (
                f"{comparison.identical_text_models} of "
                f"{comparison.text_compared_models} completed in both"
            ),
        ),
        ("Generation tok/s ratio (now/baseline)", ratio_text),
        ("Throughput noise band", band_text),
    ]
    if comparison.current_execution_mode != comparison.baseline_execution_mode:
        mode_note = (
            f"{comparison.current_execution_mode} now vs "
            f"{comparison.baseline_execution_mode} in the baseline — per-process "
            "start-up differs, so throughput is not directly comparable"
        )
        summary_rows.append(("Execution mode", mode_note))
    if comparison.current_hardware != comparison.baseline_hardware:
        hardware_note = (
            f"{comparison.current_hardware or 'unknown'} now vs "
            f"{comparison.baseline_hardware or 'unknown'} in the baseline — throughput "
            "and peak memory are not comparable across machines"
        )
        summary_rows.append(("Hardware", hardware_note))

    banner: str | None = None
    if comparison.comparability == "incomparable":
        banner = (
            "**Not directly comparable** — the per-model diff is withheld because the "
            "runs differ in: " + "; ".join(comparison.incomparable_reasons) + ". "
            "Treat any difference against this baseline as a change of inputs, not a "
            "change of model or runtime behaviour."
        )
    elif comparison.comparability == "unknown":
        banner = (
            "**Comparability unknown** — could not verify: "
            + ", ".join(comparison.unverified_facts)
            + " (the baseline's retained metadata was unavailable or incomplete). Quality "
            "transitions are shown; throughput and memory comparisons are withheld."
        )

    revision_note = (
        "Model revisions changed since the baseline (their rows below reflect a "
        "different snapshot, not only a different run): "
        + ", ".join(
            f"`{model}` {before[:9]} → {after[:9]}"
            for model, before, after in comparison.revision_changes
        )
        if comparison.revision_changes
        else None
    )

    membership_items: list[str] = []
    if comparison.models_added:
        membership_items.append(
            "New this run (no baseline): " + _comparison_model_list(comparison.models_added)
        )
    if comparison.models_removed:
        membership_items.append(
            "In baseline, not run this time: " + _comparison_model_list(comparison.models_removed)
        )

    change_rows = tuple(
        (
            change.model,
            _format_usability_transition(change.baseline_execution, change.current_execution),
            _format_usability_transition(change.baseline_usability, change.current_usability),
            _format_observation_delta(change),
        )
        for change in comparison.changes
    )
    flag_rows = tuple(
        (
            flag.model,
            f"{flag.baseline_tps:.1f}",
            f"{flag.current_tps:.1f}",
            f"{flag.ratio:.2f}",
            f"{flag.band_low:.1f}-{flag.band_high:.1f} ({flag.band_source}"
            + (f", n={flag.band_samples}" if flag.band_samples else "")
            + ")",
        )
        for flag in comparison.throughput_flags
    )
    memory_rows = tuple(
        (
            memory_change.model,
            f"{memory_change.baseline_peak_gb:.1f}",
            f"{memory_change.current_peak_gb:.1f}",
            f"{memory_change.delta_gb:+.1f}",
        )
        for memory_change in comparison.memory_changes
    )
    return _ComparisonView(
        identity_rows=tuple(identity_rows),
        summary_rows=tuple(summary_rows),
        banner=banner,
        revision_note=revision_note,
        membership_items=tuple(membership_items),
        change_rows=change_rows,
        flag_rows=flag_rows,
        memory_rows=memory_rows,
    )


def _run_issue_summary_comparison_section(comparison: RunComparison) -> ReportSection:
    """Render the mechanical diff against the baseline sweep for run_summary.md."""
    view = _comparison_view(comparison)
    if not comparison.comparable:
        assert view.banner is not None  # noqa: S101 - incomparable always carries a banner
        return ReportSection(
            "Since the baseline sweep",
            (ReportParagraph(view.banner), ReportKeyValues(view.identity_rows)),
        )
    blocks: list[ReportBlock] = [ReportKeyValues(view.identity_rows + view.summary_rows)]
    if view.banner is not None:
        blocks.append(ReportParagraph(view.banner))
    if view.revision_note is not None:
        blocks.append(ReportParagraph(view.revision_note))
    if view.membership_items:
        blocks.append(ReportBulletList(view.membership_items))
    if view.change_rows:
        blocks.append(
            ReportTable(
                ("Model", "Execution", "Usability", "Observation delta"),
                view.change_rows,
                compact=True,
            )
        )
    else:
        blocks.append(
            ReportParagraph(
                "No execution, usability, or observation-set changes against the baseline."
            )
        )
    if view.flag_rows:
        blocks.append(
            ReportTable(
                ("Model", "Baseline tok/s", "Now tok/s", "Ratio", "Expected band"),
                view.flag_rows,
                compact=True,
            )
        )
    if view.memory_rows:
        blocks.append(
            ReportTable(
                ("Model", "Baseline peak GB", "Now peak GB", "Delta"),
                view.memory_rows,
                compact=True,
            )
        )
    blocks.append(
        ReportParagraph(
            "Mechanical diff only: one image, temperature as configured; single-observation "
            "flips on one model are usually run-to-run variance, broad shifts are not."
        )
    )
    return ReportSection("Since the baseline sweep", tuple(blocks))


def _plain_log_text(text: str) -> str:
    """Strip the view's Markdown emphasis/backticks for terminal logging."""
    return text.replace("**", "").replace("`", "")


def _log_run_comparison(comparison: RunComparison | None) -> None:
    """Log the same comparison rows the summary renders, via the shared view."""
    if comparison is None:
        return
    view = _comparison_view(comparison)
    print_cli_section("Comparison with baseline sweep")
    logger.info("Baseline: %s", comparison.baseline_label)
    if view.banner is not None:
        logger.warning("%s", _plain_log_text(view.banner))
        if not comparison.comparable:
            return
    for label, value in view.summary_rows:
        logger.info("%s: %s", label, value)
    if view.revision_note is not None:
        logger.info("%s", _plain_log_text(view.revision_note))
    for item in view.membership_items:
        logger.info("%s", _plain_log_text(item))
    for model, execution, usability, observations in view.change_rows:
        logger.info("  %s: %s | %s | %s", model, execution, usability, observations)
    for model, baseline_tps, now_tps, ratio, band in view.flag_rows:
        logger.info(
            "  %s: %s -> %s tok/s (x%s) outside band %s", model, baseline_tps, now_tps, ratio, band
        )
    for model, baseline_peak, now_peak, delta in view.memory_rows:
        logger.info("  %s: peak %s -> %s GB (%s)", model, baseline_peak, now_peak, delta)
    if not comparison.has_changes:
        logger.info("No changes beyond noise against the baseline sweep.")


def _validate_run_issue_metadata(
    metadata_value: JsonLike,
    jsonl_path: Path,
) -> JsonlMetadataRecord:
    """Validate and narrow the schema-3.0 metadata row."""
    if not isinstance(metadata_value, dict) or metadata_value.get("_type") != "metadata":
        message = f"First JSONL row in {jsonl_path} must be metadata"
        raise ValueError(message)
    if metadata_value.get("format_version") != JSONL_FORMAT_VERSION:
        message = (
            f"results.jsonl format_version must be {JSONL_FORMAT_VERSION} "
            f"(found {metadata_value.get('format_version')!r})"
        )
        raise ValueError(message)
    system = metadata_value.get("system")
    versions = metadata_value.get("library_versions")
    if (
        not isinstance(metadata_value.get("prompt"), str)
        or not isinstance(metadata_value.get("timestamp"), str)
        or not isinstance(system, dict)
        or any(not isinstance(value, str) for value in system.values())
        or (
            versions is not None
            and (
                not isinstance(versions, dict)
                or any(
                    value is not None and not isinstance(value, str) for value in versions.values()
                )
            )
        )
    ):
        message = "JSONL metadata is missing required run context"
        raise ValueError(message)
    _validate_schema3_metadata_fields(metadata_value)
    return cast("JsonlMetadataRecord", metadata_value)


def _validate_schema3_counts(counts: JsonLike) -> None:
    """Enforce shape, non-negativity, and internal arithmetic of the run counts."""
    count_keys = (
        "models_attempted",
        "models_evaluated",
        "models_completed",
        "models_crashed",
        "models_indeterminate",
    )
    if not isinstance(counts, dict) or any(
        not isinstance(counts.get(key), int)
        or isinstance(counts.get(key), bool)
        or cast("int", counts.get(key)) < 0
        for key in count_keys
    ):
        message = "JSONL metadata counts are missing or invalid"
        raise ValueError(message)
    attempted = cast("int", counts["models_attempted"])
    completed = cast("int", counts["models_completed"])
    crashed = cast("int", counts["models_crashed"])
    indeterminate = cast("int", counts["models_indeterminate"])
    if (
        attempted != completed + crashed + indeterminate
        or cast("int", counts["models_evaluated"]) != completed + crashed
    ):
        message = "JSONL metadata counts are internally inconsistent"
        raise ValueError(message)


def _validate_schema3_metadata_fields(metadata_value: dict[str, JsonLike]) -> None:
    """Enforce the schema-3 required run-context fields the loader vouches for."""
    prompt = metadata_value.get("prompt")
    digest = metadata_value.get("prompt_sha256")
    if (
        not isinstance(digest, str)
        or not isinstance(prompt, str)
        or digest != hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    ):
        message = "JSONL metadata prompt_sha256 is missing or does not match the prompt"
        raise ValueError(message)
    runtime = metadata_value.get("total_runtime_seconds")
    if not isinstance(runtime, int | float) or isinstance(runtime, bool) or runtime < 0:
        message = "JSONL metadata total_runtime_seconds is missing or invalid"
        raise ValueError(message)
    _validate_schema3_counts(metadata_value.get("counts"))
    artifacts = metadata_value.get("artifacts")
    if not isinstance(artifacts, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in artifacts.items()
    ):
        message = "JSONL metadata artifacts manifest is missing or invalid"
        raise ValueError(message)
    if _narrow_run_issue_producer(metadata_value.get("producer")) is None:
        message = "JSONL metadata producer identity is missing or invalid"
        raise ValueError(message)
    if "image" not in metadata_value:
        message = "JSONL metadata image field is missing (use an explicit null)"
        raise ValueError(message)
    image = metadata_value.get("image")
    if image is not None and _narrow_run_issue_image(image) is None:
        message = "JSONL metadata image record is invalid"
        raise ValueError(message)
    if not isinstance(metadata_value.get("generation_settings"), dict):
        message = "JSONL metadata generation_settings are missing"
        raise RunIssueSummaryValidationError(message)
    if not isinstance(metadata_value.get("trust_remote_code"), bool):
        message = "JSONL metadata trust_remote_code is missing"
        raise RunIssueSummaryValidationError(message)
    started_at = metadata_value.get("started_at")
    if started_at is not None and not isinstance(started_at, str):
        message = "JSONL metadata started_at must be a string when present"
        raise RunIssueSummaryValidationError(message)
    if "comparison" not in metadata_value or not isinstance(
        metadata_value.get("comparison"), dict | type(None)
    ):
        message = "JSONL metadata comparison field is missing or invalid"
        raise RunIssueSummaryValidationError(message)


class RunIssueSummaryValidationError(ValueError):
    """Type-shape violation in retained inputs.

    Subclassing ValueError keeps regeneration catch paths intact while
    satisfying the raise-TypeError-for-types lint (TRY004) with a class whose
    name states the contract.
    """


def _require_optional_str_fields(
    record: Mapping[str, JsonLike],
    keys: Sequence[str],
    *,
    context: str,
) -> None:
    """Raise when any named field is present with a non-string value."""
    for key in keys:
        value = record.get(key)
        if value is not None and not isinstance(value, str):
            message = f"{context} has invalid field {key}"
            raise ValueError(message)


def _json_int_or_none(value: JsonLike) -> int | None:
    """Narrow a JSON value to int, rejecting bools."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _validate_run_issue_failure(value: JsonLike, line_number: int) -> None:
    """Validate the bounded failure fields consumed by the summary renderer."""
    if value is None:
        return
    context = f"JSONL result row {line_number} failure"
    if not isinstance(value, dict):
        message = f"{context} is not a record"
        raise RunIssueSummaryValidationError(message)
    _require_optional_str_fields(
        value, ("phase", "stage", "exception_type", "message"), context=context
    )
    chain = value.get("exception_chain")
    if chain is None:
        return
    if not isinstance(chain, list):
        message = f"{context} has an invalid exception chain"
        raise RunIssueSummaryValidationError(message)
    for entry in chain:
        if not isinstance(entry, dict):
            message = f"{context} has an invalid exception chain entry"
            raise RunIssueSummaryValidationError(message)
        _require_optional_str_fields(entry, ("type", "message"), context=context)


def _validate_run_issue_model_provenance(
    value: JsonLike,
    line_number: int,
    expected_model: str,
) -> None:
    """Validate the model and revision fields consumed by the summary renderer."""
    context = f"JSONL result row {line_number} model provenance"
    if not isinstance(value, dict) or not isinstance(value.get("model"), str):
        message = f"{context} is invalid"
        raise RunIssueSummaryValidationError(message)
    if value["model"] != expected_model:
        message = f"{context} does not match {expected_model}"
        raise ValueError(message)
    _require_optional_str_fields(
        value, ("requested_revision", "resolved_revision"), context=context
    )


_RUN_ISSUE_ASSESSMENT_VOCABULARIES: Final[tuple[tuple[str, frozenset[str]], ...]] = (
    ("execution", _RUN_ISSUE_EXECUTION_VALUES),
    ("usability", _RUN_ISSUE_USABILITY_VALUES),
    ("maintainer_status", _RUN_ISSUE_MAINTAINER_VALUES),
)


_DETAIL_STRING_LIST_FIELDS: Final[tuple[str, ...]] = (
    "missing_sections",
    "instruction_echo_fragments",
    "unexpected_special_tokens",
    "configured_generation_wrappers",
    "thinking_trace_markers",
    "role_boundary_tokens",
    "duplicate_keywords",
    "token_cap_reasons",
    "unchanged_draft_fields",
)
_DETAIL_TEXT_FIELDS: Final[tuple[str, ...]] = (
    "repeated_fragment",
    "unexpected_catalog_preamble",
)
_DETAIL_COUNT_FIELDS: Final[tuple[str, ...]] = (
    "title_word_count",
    "description_sentence_count",
    "keyword_count",
)
_DETAIL_RANGE_FIELDS: Final[tuple[str, ...]] = (
    "title_word_range",
    "description_sentence_range",
    "keyword_count_range",
)

_DETAIL_RANGE_LENGTH: Final[int] = 2


def _is_detail_count(value: JsonLike) -> bool:
    """A count is an int and never a bool (bool subclasses int)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_detail_string_list(value: JsonLike) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_detail_text(value: JsonLike) -> bool:
    return isinstance(value, str)


def _is_detail_int_pair(value: JsonLike) -> bool:
    return (
        isinstance(value, list)
        and len(value) == _DETAIL_RANGE_LENGTH
        and all(_is_detail_count(item) for item in value)
    )


def _validate_run_issue_details(details: dict[str, JsonLike], line_number: int) -> None:
    """Enforce the observation-detail value types the renderers index into.

    Known ``JsonlObservationDetailsRecord`` keys must carry their declared
    shapes (string lists of strings, non-bool integer counts, exactly-two-int
    ranges, plain-string fragments); unknown keys stay permitted for forward
    compatibility.
    """
    checks: tuple[tuple[tuple[str, ...], Callable[[JsonLike], bool]], ...] = (
        (_DETAIL_STRING_LIST_FIELDS, _is_detail_string_list),
        (_DETAIL_TEXT_FIELDS, _is_detail_text),
        (_DETAIL_COUNT_FIELDS, _is_detail_count),
        (_DETAIL_RANGE_FIELDS, _is_detail_int_pair),
    )
    for field_names, is_valid in checks:
        for field in field_names:
            if field in details and not is_valid(details[field]):
                message = f"JSONL result row {line_number} has invalid observation detail {field}"
                raise RunIssueSummaryValidationError(message)


def _validate_run_issue_result_shapes(
    value: dict[str, JsonLike],
    assessment: dict[str, JsonLike],
    line_number: int,
) -> None:
    """Enforce the retained row-field shapes every report consumer indexes into."""
    shaped_fields = (
        ("timestamp", str),
        ("generated_text", str),
        ("captured_output_on_fail", str),
        ("metrics", dict),
        ("timing", dict),
    )
    diagnostics = value["prompt_diagnostics"]
    if any(not isinstance(value[name], shape) for name, shape in shaped_fields) or not (
        diagnostics is None or isinstance(diagnostics, dict)
    ):
        message = f"JSONL result row {line_number} has invalid retained field shapes"
        raise RunIssueSummaryValidationError(message)
    details = assessment.get("details")
    if details is not None:
        if not isinstance(details, dict):
            message = f"JSONL result row {line_number} has a non-mapping assessment details"
            raise RunIssueSummaryValidationError(message)
        _validate_run_issue_details(details, line_number)
    generate_kwargs = diagnostics.get("generate_kwargs") if diagnostics else None
    if generate_kwargs is not None and not isinstance(generate_kwargs, dict):
        message = f"JSONL result row {line_number} has non-mapping prompt generate_kwargs"
        raise RunIssueSummaryValidationError(message)


def _validate_run_issue_result(value: JsonLike, line_number: int) -> JsonlResultRecord:
    """Validate and narrow one cached per-model assessment row."""
    if not isinstance(value, dict) or value.get("_type") != "result":
        message = f"JSONL row {line_number} must be a result record"
        raise ValueError(message)
    if any(key not in value for key in ("model", "assessment", "failure", "model_provenance")):
        message = f"JSONL result row {line_number} is missing its cached assessment"
        raise ValueError(message)
    if any(
        key not in value
        for key in (
            "timestamp",
            "generated_text",
            "captured_output_on_fail",
            "metrics",
            "timing",
            "prompt_diagnostics",
        )
    ):
        message = f"JSONL result row {line_number} is missing required retained fields"
        raise ValueError(message)
    model = value["model"]
    assessment = value["assessment"]
    if not isinstance(model, str) or not isinstance(assessment, dict):
        message = f"JSONL result row {line_number} has invalid field types"
        raise RunIssueSummaryValidationError(message)
    _validate_run_issue_result_shapes(value, assessment, line_number)
    vocabulary_violation = any(
        not isinstance(assessment.get(field), str) or assessment.get(field) not in vocabulary
        for field, vocabulary in _RUN_ISSUE_ASSESSMENT_VOCABULARIES
    )
    observations = assessment.get("observations")
    if (
        vocabulary_violation
        or not isinstance(observations, list)
        or any(
            not isinstance(item, str) or item not in _RUN_ISSUE_OBSERVATION_VALUES
            for item in observations
        )
    ):
        message = f"JSONL result row {line_number} has an invalid cached assessment"
        raise ValueError(message)
    _validate_run_issue_failure(value["failure"], line_number)
    _validate_run_issue_model_provenance(
        value["model_provenance"],
        line_number,
        model,
    )
    return cast("JsonlResultRecord", value)


def _narrow_run_issue_image(value: JsonLike) -> RunImageRecord | None:
    """Narrow optional retained image facts into the publication-safe contract."""
    if not isinstance(value, dict):
        return None
    name = value.get("name")
    if not isinstance(name, str):
        return None
    sha256 = value.get("sha256")
    megapixels = value.get("megapixels")
    record: RunImageRecord = {
        "name": name,
        "sha256": (
            sha256.lower()
            if isinstance(sha256, str) and re.fullmatch(r"[0-9a-fA-F]{64}", sha256)
            else None
        ),
        "size_bytes": _json_int_or_none(value.get("size_bytes")),
        "width": _json_int_or_none(value.get("width")),
        "height": _json_int_or_none(value.get("height")),
        "megapixels": (
            float(megapixels)
            if isinstance(megapixels, int | float) and not isinstance(megapixels, bool)
            else None
        ),
    }
    source_url = value.get("source_url")
    if isinstance(source_url, str):
        with suppress(argparse.ArgumentTypeError):
            record["source_url"] = _parse_public_image_source_url(source_url)
    return record


def _narrow_run_issue_producer(value: JsonLike) -> CheckModelsProvenanceRecord | None:
    """Narrow optional producer facts used by the paste-ready run context."""
    if not isinstance(value, dict):
        return None
    version_value = value.get("version")
    if value.get("name") != "check_models" or not isinstance(version_value, str):
        return None
    install_type = value.get("install_type")
    if install_type not in {"editable", "installed", "source-tree", "unknown"}:
        return None
    revision = value.get("git_revision")
    dirty = value.get("dirty")
    if revision is not None and not isinstance(revision, str):
        return None
    if dirty is not None and not isinstance(dirty, bool):
        return None
    record: CheckModelsProvenanceRecord = {
        "name": "check_models",
        "version": version_value,
        "git_revision": revision,
        "install_type": cast(
            "Literal['editable', 'installed', 'source-tree', 'unknown']",
            install_type,
        ),
    }
    if "dirty" in value:
        record["dirty"] = dirty
    return record


def _load_retained_run_text(text: str, label: str) -> RetainedRun:
    """Decode and validate one retained run from JSONL text (the sole loader)."""
    parsed_rows = _parse_jsonl_text_rows(text, label)
    if not parsed_rows:
        message = f"{label} contains no rows"
        raise ValueError(message)
    metadata = _validate_run_issue_metadata(parsed_rows[0], Path(label))
    results = tuple(
        _validate_run_issue_result(value, line_number)
        for line_number, value in enumerate(parsed_rows[1:], start=2)
    )
    execution_counts = Counter(result["assessment"]["execution"] for result in results)
    counts = metadata["counts"]
    comparisons = (
        ("models_attempted", counts["models_attempted"], len(results)),
        ("models_completed", counts["models_completed"], execution_counts["completed"]),
        ("models_crashed", counts["models_crashed"], execution_counts["crashed"]),
        (
            "models_indeterminate",
            counts["models_indeterminate"],
            execution_counts["indeterminate"],
        ),
    )
    mismatched = [
        f"{name}={actual} (rows say {expected})"
        for name, actual, expected in comparisons
        if actual != expected
    ]
    if mismatched:
        message = f"{label}: metadata counts disagree with the result rows: " + "; ".join(
            mismatched
        )
        raise ValueError(message)
    return RetainedRun(metadata=metadata, results=results)


def _load_retained_run(path: Path) -> RetainedRun:
    """Load and validate the retained run at ``path``."""
    return _load_retained_run_text(_read_text_file(path), str(path))


def _retained_run_window(
    metadata: JsonlMetadataRecord,
    results: Sequence[JsonlResultRecord] = (),
) -> tuple[datetime, datetime] | None:
    """Derive the run's wall-clock window.

    ``started_at`` is authoritative. Older headers only carry the end
    timestamp and a runtime that, before 0.16.7, was a perf-counter duration
    excluding system sleep, so the arithmetic start could land after the
    run's own early log lines; the earliest retained result timestamp bounds
    the start from above instead.
    """
    run_end = _parse_local_timestamp(metadata.get("timestamp"))
    if run_end is None:
        return None
    started = _parse_local_timestamp(metadata.get("started_at"))
    if started is not None and started <= run_end:
        return started, run_end
    runtime = metadata.get("total_runtime_seconds")
    if not isinstance(runtime, int | float) or isinstance(runtime, bool) or runtime < 0:
        return None
    run_start = run_end - timedelta(seconds=runtime)
    row_times = [
        row_time
        for result in results
        if (row_time := _parse_local_timestamp(result.get("timestamp"))) is not None
    ]
    if row_times:
        run_start = min(run_start, *row_times)
    return run_start, run_end


def _run_issue_summary_source_from_run(run: RetainedRun) -> RunIssueSummarySource:
    """Project one retained run into the paste-ready summary's source shape."""
    metadata = run.metadata
    settings = metadata.get("generation_settings")
    generation_settings = (
        tuple(
            (key, json.dumps(value, ensure_ascii=False, sort_keys=True))
            for key, value in sorted(settings.items())
        )
        if isinstance(settings, dict)
        else ()
    )
    raw_trust = metadata.get("trust_remote_code")
    return RunIssueSummarySource(
        metadata=metadata,
        results=run.results,
        image=_narrow_run_issue_image(cast("JsonLike", metadata.get("image"))),
        generation_settings=generation_settings,
        trust_remote_code=raw_trust if isinstance(raw_trust, bool) else None,
        producer=_narrow_run_issue_producer(cast("JsonLike", metadata.get("producer"))),
        run_window=_retained_run_window(metadata, run.results),
    )


def _load_run_issue_summary_source(output_paths: ReportOutputPaths) -> RunIssueSummarySource:
    """Load and validate the retained schema-3 inputs used by the issue summary."""
    return _run_issue_summary_source_from_run(_load_retained_run(output_paths.jsonl))


def _run_issue_summary_path(output_paths: ReportOutputPaths) -> Path:
    """Return the canonical paste-ready whole-run issue path."""
    return output_paths.index.parent / "issues" / "run_summary.md"


def _remove_run_issue_summary(output_paths: ReportOutputPaths) -> OSError | None:
    """Remove a derived summary that cannot describe the current run safely."""
    try:
        _run_issue_summary_path(output_paths).unlink()
    except FileNotFoundError:
        return None
    except OSError as error:
        return error
    return None


def _github_issue_report_paths(
    model_names: Sequence[str],
    issues_dir: Path,
) -> dict[str, Path]:
    """Return collision-safe per-model issue paths using the canonical naming rule."""
    paths: dict[str, Path] = {}
    used_filenames: set[str] = set()
    for model_name in model_names:
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", model_name).strip("._") or "model"
        base_name = f"issue_{name}"
        filename = f"{base_name}.md"
        suffix = 2
        while filename in used_filenames:
            filename = f"{base_name}_{suffix}.md"
            suffix += 1
        used_filenames.add(filename)
        paths[model_name] = issues_dir / filename
    return paths


def _reproduction_image_format(image: RunImageRecord) -> str:
    """Return a concise image format inferred from the publication-safe name."""
    suffix = Path(image["name"]).suffix.removeprefix(".").upper()
    return "JPEG" if suffix in {"JPG", "JPEG"} else suffix or "unavailable"


def _reproduction_image_facts(image: RunImageRecord | None) -> tuple[tuple[str, str], ...]:
    """Return publication-safe image characteristics for an issue report."""
    if image is None:
        return (("Image input", "characteristics unavailable"),)
    rows: list[tuple[str, str]] = [("Image format", _reproduction_image_format(image))]
    if image["width"] is not None and image["height"] is not None:
        rows.append(("Image dimensions", f"{image['width']:,} x {image['height']:,} pixels"))
    if image["size_bytes"] is not None:
        rows.append(("Image size", f"{image['size_bytes']:,} bytes"))
    if image["sha256"] is not None:
        rows.append(("Image SHA-256", image["sha256"]))
    if source_url := image.get("source_url"):
        rows.append(("Public source", source_url))
    return tuple(rows)


def _public_reproduction_filename(image: RunImageRecord, source_url: str) -> str:
    """Return a safe basename for downloading the public reproduction image."""
    source_suffix = PurePosixPath(urlparse(source_url).path).suffix.lower()
    suffix = source_suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", source_suffix) else ""
    if not suffix:
        image_suffix = Path(image["name"]).suffix.lower()
        suffix = image_suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", image_suffix) else ""
    return f"repro-image{suffix or '.img'}"


def _retained_generation_args(source: RunIssueSummarySource) -> argparse.Namespace:
    """Restore JSON-rendered common generation values for native CLI rendering."""
    values = {key: json.loads(value) for key, value in source.generation_settings}
    values["trust_remote_code"] = source.trust_remote_code is True
    return argparse.Namespace(**values)


_REPRO_THINKING_KWARG_KEYS: Final[tuple[str, ...]] = (
    "enable_thinking",
    "thinking_budget",
    "thinking_start_token",
    "thinking_end_token",
)


def _repro_thinking_overrides(
    run_args: argparse.Namespace | None,
    effective_generate_kwargs: Mapping[str, object] | None,
) -> dict[str, object]:
    """Return per-model thinking kwargs that differ from the global CLI args."""
    if run_args is None or not effective_generate_kwargs:
        return {}
    return {
        key: effective_generate_kwargs[key]
        for key in _REPRO_THINKING_KWARG_KEYS
        if key in effective_generate_kwargs
        and effective_generate_kwargs[key] != getattr(run_args, key, None)
    }


def _effective_repro_args(
    run_args: argparse.Namespace | None,
    effective_generate_kwargs: Mapping[str, object] | None,
) -> argparse.Namespace | None:
    """Overlay per-model effective generate kwargs onto global repro args.

    The auto thinking budget is applied per model at generation time, so a
    repro built from global CLI arguments alone would not reproduce the
    recorded output. The per-model kwargs captured in prompt diagnostics win.
    """
    overrides = _repro_thinking_overrides(run_args, effective_generate_kwargs)
    if run_args is None or not overrides:
        return run_args
    merged = argparse.Namespace(**vars(run_args))
    for key, value in overrides.items():
        setattr(merged, key, value)
    return merged


def _shared_repro_thinking_caveat(
    highlighted_results: Sequence[PerformanceResult],
    run_args: argparse.Namespace | None,
) -> ReportParagraph | None:
    """Warn when per-model automatic thinking flags diverge from the shared command.

    The shared reproduction command is rendered once with ``MODEL_ID``
    substitution, so it cannot carry flags that were auto-applied per model.
    """
    affected: list[str] = []
    for result in highlighted_results:
        diagnostics = result.prompt_diagnostics
        overrides = _repro_thinking_overrides(
            run_args,
            diagnostics.generate_kwargs if diagnostics is not None else None,
        )
        if overrides:
            budget = overrides.get("thinking_budget")
            flags = "--enable-thinking"
            if budget is not None:
                flags += f" --thinking-budget {budget}"
            affected.append(f"`{result.model_name}` ({flags})")
    if not affected:
        return None
    return ReportParagraph(
        "The shared command omits per-model automatic thinking flags. When "
        "substituting these models, append the flags recorded in their "
        "diagnostics blocks: " + "; ".join(affected) + "."
    )


def _preview_asset_name(suffix: str, data: bytes) -> str:
    """Digest-named preview asset: later sweeps add files, never replace them.

    A reproduction command pasted into an issue downloads this exact file
    and checks its digest; a name that every sweep overwrote made older
    commands fail verification as soon as the input photograph changed.
    """
    return f"source-image-{hashlib.sha256(data).hexdigest()[:16]}{suffix}"


def _published_preview_record(image_path: Path | None) -> RunImageRecord | None:
    """Describe the retained gallery preview as a shareable, digest-verifiable stand-in.

    Every run writes a downscaled re-encoding of the input under
    ``reports/assets`` with a digest-derived name; once the run's artifacts
    are committed, its raw GitHub URL and digest let a maintainer reproduce
    an observation on public bytes when the original photograph is not
    published. It is a stand-in, never the exact inference input.
    """
    preview = _report_image_preview(image_path)
    if preview is None:
        return None
    suffix, _mime_type, data = preview
    try:
        with Image.open(io.BytesIO(data)) as decoded:
            width, height = decoded.size
    except (OSError, ValueError):
        return None
    name = _preview_asset_name(suffix, data)
    repo_path = _PUBLISHED_OUTPUT_ROOT / "reports" / "assets" / name
    encoded_path = "/".join(quote(part) for part in repo_path.parts)
    return {
        "name": name,
        "source_url": f"{_GITHUB_RAW_URL}/{_github_blob_ref()}/{encoded_path}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "width": width,
        "height": height,
        "megapixels": (width * height) / MEGAPIXEL_CONVERSION,
    }


def _verified_public_reproduction_blocks(
    *,
    image: RunImageRecord,
    source_url: str,
    sha256: str,
    model_name: str,
    prompt: str,
    run_args: argparse.Namespace | None,
    resolved_revision: str | None,
    lead: str,
) -> tuple[ReportBlock, ...]:
    """Download-verify-run command for a public image whose digest is known."""
    filename = _public_reproduction_filename(image, source_url)
    commands = [
        "set -euo pipefail",
        shlex_join(("curl", "--fail", "--location", "--output", filename, source_url)),
    ]
    hash_record = f"{sha256}  {filename}"
    commands.append(f"{shlex_join(('printf', '%s\\n', hash_record))} | shasum -a 256 --check")
    commands.append(
        build_native_mlx_vlm_repro_command_spec(
            model_name=model_name,
            prompt=prompt,
            image_ref=filename,
            run_args=run_args,
            resolved_revision=resolved_revision,
        ).shell_command()
    )
    return (ReportParagraph(lead), ReportCodeBlock("\n".join(commands), language="bash"))


def _reproduction_input_blocks(
    *,
    model_name: str,
    prompt: str,
    image: RunImageRecord | None,
    run_args: argparse.Namespace | None,
    resolved_revision: str | None,
    crash_phase: str | None = None,
    effective_generate_kwargs: Mapping[str, object] | None = None,
    published_preview: RunImageRecord | None = None,
) -> tuple[ReportBlock, ...]:
    """Describe exact inputs and render a command only when it is exact evidence.

    A full command is rendered for a verifiable public image, or for model-load
    crashes, which occur before image decoding and so reproduce with any image.
    When the original is unpublished but the run's committed preview is known,
    a clearly labelled stand-in command is rendered against that public file.
    """
    run_args = _effective_repro_args(run_args, effective_generate_kwargs)
    blocks: list[ReportBlock] = [
        ReportKeyValues(_reproduction_image_facts(image)),
        ReportDetails("Exact prompt", (ReportCodeBlock(prompt),)),
    ]
    source_url = image.get("source_url") if image is not None else None
    if image is None or source_url is None:
        if crash_phase == "model_load":
            blocks.extend(
                (
                    ReportParagraph(
                        "The crash occurred during model load, before image decoding, so "
                        "the exact input image is not required: substitute any local "
                        "image for the placeholder path and run one native mlx-vlm "
                        "process."
                    ),
                    ReportCodeBlock(
                        build_native_mlx_vlm_repro_command_spec(
                            model_name=model_name,
                            prompt=prompt,
                            image_ref="any-local-image.jpg",
                            run_args=run_args,
                            resolved_revision=resolved_revision,
                            minimal_load=True,
                        ).shell_command(),
                        language="bash",
                    ),
                )
            )
            return tuple(blocks)
        blocks.append(
            ReportParagraph(
                "The original local input is not published, so this report does not claim "
                "a complete reproduction command. Use a shareable equivalent image or add "
                "the original image before filing."
            )
        )
        preview_url = published_preview.get("source_url") if published_preview else None
        preview_sha256 = published_preview["sha256"] if published_preview else None
        if published_preview is not None and preview_url and preview_sha256:
            blocks.append(
                ReportKeyValues(
                    (
                        ("Retained preview", preview_url),
                        (
                            "Preview dimensions",
                            f"{published_preview['width']:,} x {published_preview['height']:,} pixels",
                        ),
                        ("Preview size", f"{published_preview['size_bytes']:,} bytes"),
                        ("Preview SHA-256", preview_sha256),
                    )
                )
            )
            blocks.extend(
                _verified_public_reproduction_blocks(
                    image=published_preview,
                    source_url=preview_url,
                    sha256=preview_sha256,
                    model_name=model_name,
                    prompt=prompt,
                    run_args=run_args,
                    resolved_revision=resolved_revision,
                    lead=(
                        "Shareable stand-in: the retained gallery preview is a downscaled "
                        "re-encoding of the original, so an observation reproduced on it "
                        "must be reported as reproduced on the preview, not on the exact "
                        "inference input. The asset is named by its digest, so later sweeps "
                        "never replace it; the URL resolves once this run's artifacts are "
                        "committed. Download and verify it, then run one native mlx-vlm "
                        "process."
                    ),
                )
            )
        return tuple(blocks)

    sha256 = image["sha256"]
    if sha256 is None:
        blocks.append(
            ReportParagraph(
                "A valid SHA-256 digest is unavailable, so the public source cannot be "
                "verified as the exact input and this report withholds a reproduction command."
            )
        )
        return tuple(blocks)

    blocks.extend(
        _verified_public_reproduction_blocks(
            image=image,
            source_url=source_url,
            sha256=sha256,
            model_name=model_name,
            prompt=prompt,
            run_args=run_args,
            resolved_revision=resolved_revision,
            lead="Download and verify the exact public input, then run one native mlx-vlm process.",
        )
    )
    return tuple(blocks)


def _compact_run_issue_exception_message(message: str) -> str:
    """Collapse a large repeated unexpected-parameter list in the aggregate report."""
    match = re.fullmatch(
        r"(?P<prefix>.*?)(?P<label>Received (?P<count>\d+) parameters not in model):\s*"
        r"(?P<parameters>.+)",
        message,
        re.DOTALL,
    )
    if match is None:
        return message
    parameters = [item.strip().removesuffix(".") for item in match["parameters"].split(",")]
    inline_parameter_limit = 6
    if len(parameters) <= inline_parameter_limit:
        return message
    families = _dedupe_preserve_order([item.partition(".")[0] for item in parameters])
    sample = ", ".join(parameters[:3])
    return (
        f"{match['prefix']}{match['label']}; "
        f"families: {', '.join(families)}; representative parameters: {sample}."
    )


def _run_issue_summary_exception_lines(failure: JsonlFailureRecord | None) -> str:
    """Return a compact exception chain without traceback or captured output."""
    if failure is None:
        return "No structured exception evidence captured."
    chain = failure.get("exception_chain")
    if chain:
        lines = []
        for entry in chain:
            exception_type = entry.get("type") or "Exception"
            message = _compact_run_issue_exception_message(entry.get("message") or "no message")
            lines.append(f"{exception_type}: {message}")
        return "\ncaused by: ".join(lines)
    exception_type = failure.get("exception_type") or "Exception"
    message = _compact_run_issue_exception_message(failure.get("message") or "no message")
    return f"{exception_type}: {message}"


def _run_issue_summary_artifact_link(
    *,
    summary_path: Path,
    artifact_path: Path,
    label: str,
    anchor: str | None = None,
) -> ReportTargetLink:
    """Build one safely rendered link from the issue summary to retained evidence."""
    return ReportTargetLink(
        label,
        _issue_markdown_artifact_target(
            report_filename=summary_path,
            artifact_filename=artifact_path,
            anchor=anchor,
        ),
    )


def _pluralized_count(count: int, singular: str, plural: str | None = None) -> str:
    """Render a compact count phrase with stable pluralization."""
    return f"{count} {singular if count == 1 else plural or f'{singular}s'}"


def _run_issue_summary_assessment_label(assessment: JsonlAssessmentRecord) -> str:
    """Render cached execution and usability values as compact human labels."""
    return f"{assessment['execution'].replace('_', ' ')} / {_human_status_label(assessment['usability'])}"


def _run_issue_summary_crash_section(
    result: JsonlResultRecord,
    *,
    source: RunIssueSummarySource,
    output_paths: ReportOutputPaths,
    summary_path: Path,
    issue_reports: Mapping[str, Path],
) -> ReportSection:
    """Build the expanded, bounded evidence section for one actionable crash."""
    failure = result.get("failure")
    provenance = result.get("model_provenance")
    requested_revision = provenance.get("requested_revision") if provenance else None
    resolved_revision = provenance.get("resolved_revision") if provenance else None
    facts = [
        (
            "Execution / usability",
            _run_issue_summary_assessment_label(result["assessment"]),
        ),
    ]
    if failure is not None:
        facts.extend(
            (label, value)
            for label, value in (
                ("Phase", failure.get("phase")),
                ("Stage", failure.get("stage")),
            )
            if value
        )
    if requested_revision:
        facts.append(("Requested revision", requested_revision))
    if resolved_revision:
        facts.append(("Resolved revision", resolved_revision))

    evidence_rows: list[tuple[ReportCell, ...]] = [
        (
            "Full diagnostics",
            _run_issue_summary_artifact_link(
                summary_path=summary_path,
                artifact_path=output_paths.diagnostics,
                label="model evidence",
                anchor=_diagnostics_model_anchor(result["model"]),
            ),
        )
    ]
    issue_path = issue_reports.get(result["model"])
    if issue_path is not None:
        evidence_rows.append(
            (
                "Detailed issue draft",
                _run_issue_summary_artifact_link(
                    summary_path=summary_path,
                    artifact_path=issue_path,
                    label="crash draft",
                ),
            )
        )
    return ReportSection(
        result["model"],
        (
            ReportKeyValues(tuple(facts)),
            ReportParagraph("Root exception chain"),
            ReportCodeBlock(_run_issue_summary_exception_lines(failure)),
            ReportSection(
                "Reproduction inputs",
                _reproduction_input_blocks(
                    model_name=result["model"],
                    prompt=source.metadata["prompt"],
                    image=source.image,
                    run_args=_retained_generation_args(source),
                    resolved_revision=resolved_revision or requested_revision,
                    crash_phase=failure.get("phase") if failure is not None else None,
                    effective_generate_kwargs=cast(
                        "Mapping[str, object] | None",
                        (result.get("prompt_diagnostics") or {}).get("generate_kwargs"),
                    ),
                ),
                level=4,
            ),
            ReportTable(("Evidence", "Link"), tuple(evidence_rows), compact=True),
        ),
        level=3,
    )


def _run_issue_failure_observed_result(failure: JsonlFailureRecord, captured: str) -> str:
    """Describe a recorded failure for the review tables, root cause first."""
    phase = failure.get("phase")
    phase_label = _failure_phase_human_label(phase)
    message = failure.get("message") or ""
    if "connection reset" in message.casefold():
        return f"Network connection reset during {phase_label}"
    if (
        phase == "model_load"
        and "timed out" in message.casefold()
        and any(needle in captured for needle in _HF_DOWNLOAD_PROGRESS_NEEDLES)
    ):
        return f"Download timeout: {DOWNLOAD_TIMEOUT_REMEDY}"
    stage = failure.get("stage")
    if stage:
        return f"{stage} during {phase_label}"
    exception_type = failure.get("exception_type")
    if exception_type:
        return f"{exception_type} during {phase_label}"
    return f"Attempt stopped during {phase_label}"


def _count_observation(results: Sequence[JsonlResultRecord], code: str) -> int:
    """Count results whose assessment carries the given observation code."""
    return sum(1 for result in results if code in result["assessment"]["observations"])


def _count_stop_reason(results: Sequence[JsonlResultRecord], reason: str) -> int:
    """Count results whose recorded stop reason matches.

    Reaching the token limit is neutral on its own (a model may finish a usable
    answer exactly at the cap); the separate ``token_cap_truncation``
    observation carries the degradation evidence.
    """
    return sum(1 for result in results if result.get("timing", {}).get("stop_reason") == reason)


def _run_issue_summary_constraint_breakdown(
    results: Sequence[JsonlResultRecord],
) -> ReportSection | None:
    """Aggregate which catalogue constraint fails fleet-wide, with medians.

    Distinguishes "the prompt's constraints are hard for everyone" from
    "individual models are sloppy" without opening per-model diagnostics.
    Rendered only when at least one model violated a constraint.
    """

    def _int_pair(value: JsonLike) -> tuple[int, int] | None:
        # Retained artifacts are unvalidated here; never index blindly.
        pair_length = 2
        if (
            isinstance(value, list)
            and len(value) == pair_length
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
        ):
            return cast("int", value[0]), cast("int", value[1])
        return None

    title_by_range: dict[tuple[int, int], list[int]] = {}
    description_by_range: dict[tuple[int, int], list[int]] = {}
    keyword_by_range: dict[tuple[int, int], list[int]] = {}
    duplicate_models = 0

    def _record_outside_range(
        groups: dict[tuple[int, int], list[int]],
        count: JsonLike,
        bounds_value: JsonLike,
    ) -> None:
        bounds = _int_pair(bounds_value)
        if (
            isinstance(count, int)
            and not isinstance(count, bool)
            and bounds is not None
            and not bounds[0] <= count <= bounds[1]
        ):
            groups.setdefault(bounds, []).append(count)

    for result in results:
        assessment = result["assessment"]
        if not {"catalog_constraint_violation", "duplicate_keywords"}.intersection(
            assessment["observations"]
        ):
            continue
        details = cast("dict[str, JsonLike]", assessment.get("details") or {})
        _record_outside_range(
            title_by_range, details.get("title_word_count"), details.get("title_word_range")
        )
        _record_outside_range(
            description_by_range,
            details.get("description_sentence_count"),
            details.get("description_sentence_range"),
        )
        _record_outside_range(
            keyword_by_range, details.get("keyword_count"), details.get("keyword_count_range")
        )
        if details.get("duplicate_keywords"):
            duplicate_models += 1
    if not (title_by_range or description_by_range or keyword_by_range or duplicate_models):
        return None

    def _range_line(label: str, observed: list[int], bounds: tuple[int, int], unit: str) -> str:
        below = sum(1 for value in observed if value < bounds[0])
        above = sum(1 for value in observed if value > bounds[1])
        return (
            f"{label}: {len(observed)} model(s) outside {bounds[0]}-{bounds[1]}{unit} "
            f"({below} below, {above} above; median observed {median(observed):g})"
        )

    lines: list[str] = []
    for bounds, observed in sorted(title_by_range.items()):
        lines.append(_range_line("Title length", observed, bounds, " words"))
    for bounds, observed in sorted(description_by_range.items()):
        lines.append(_range_line("Description length", observed, bounds, " sentences"))
    for bounds, observed in sorted(keyword_by_range.items()):
        lines.append(_range_line("Keyword count", observed, bounds, ""))
    if duplicate_models:
        lines.append(f"Duplicate keywords: {duplicate_models} model(s)")
    return ReportSection(
        "Constraint-failure breakdown",
        (
            ReportParagraph(
                "How the fleet failed the catalogue constraints — a skew toward one "
                "constraint suggests prompt difficulty rather than individual model faults."
            ),
            ReportBulletList(tuple(lines)),
        ),
    )


def _run_issue_summary_observed_result(result: JsonlResultRecord) -> str:
    """Render one model row's observed result for the paste-ready review tables."""
    assessment = result["assessment"]
    if assessment["observations"]:
        return _human_observation_labels(
            assessment["observations"],
            details=assessment.get("details"),
        )
    failure = result.get("failure")
    if failure is None:
        return "No assessment evidence was captured"
    captured = (result.get("captured_output_on_fail") or "").casefold()
    return _run_issue_failure_observed_result(failure, captured)


def _run_issue_observation_cluster_key(result: JsonlResultRecord) -> tuple[str, ...]:
    """Return a stable observation signature for cluster counting."""
    observations = result["assessment"]["observations"]
    if not observations:
        return ()
    ordered = tuple(code for code in _OBSERVATION_DISPLAY_PRIORITY if code in set(observations))
    return ordered or tuple(observations)


def _run_issue_summary_observation_cluster_section(
    results: Sequence[JsonlResultRecord],
) -> ReportSection | None:
    """Summarize repeated observation signatures above the per-model review tables."""
    counts: Counter[tuple[str, ...]] = Counter()
    for result in results:
        key = _run_issue_observation_cluster_key(result)
        if key:
            counts[key] += 1
    if not counts:
        return None
    rows = tuple(
        (
            _human_observation_labels(cast("Sequence[ObservationCode]", signature)),
            str(count),
        )
        # Integration importance first (best display rank in the signature),
        # then frequency: a rare repetition cluster outranks a common
        # constraint-miss cluster.
        for signature, count in sorted(
            counts.items(),
            key=lambda item: (
                min(_OBSERVATION_DISPLAY_RANK[cast("ObservationCode", code)] for code in item[0]),
                -item[1],
            ),
        )
    )
    return ReportSection(
        "Observation clusters",
        (
            ReportParagraph(
                "Repeated mechanical observation signatures among results requiring review."
            ),
            ReportTable(("Observed result", "Models"), rows, compact=True),
        ),
    )


_RUN_ISSUE_USABILITY_ORDER: Final[dict[ModelUsability, int]] = {
    "usable": 0,
    "usable_with_caveats": 1,
    "unusable": 2,
    "not_evaluated": 3,
}


def _run_issue_summary_quality_cells(result: JsonlResultRecord) -> tuple[str, str, str]:
    """Format captured per-model resource facts for the quality table."""
    metrics = result.get("metrics") or {}
    timing = result.get("timing") or {}
    total_time = timing.get("total_time_s")
    total_cell = (
        _format_time_seconds(float(total_time))
        if isinstance(total_time, (int, float)) and total_time >= 0
        else "-"
    )
    generation_tokens = metrics.get("generation_tokens")
    generation_tps = metrics.get("generation_tps")
    if (
        isinstance(generation_tps, (int, float))
        and isinstance(generation_tokens, int)
        and generation_tokens >= MIN_THROUGHPUT_SAMPLE_TOKENS
    ):
        tps_cell = f"{_format_tps(float(generation_tps))} tok/s"
    elif isinstance(generation_tokens, int):
        tps_cell = "insufficient sample"
    else:
        tps_cell = "-"
    peak_memory = metrics.get("peak_memory_gb")
    peak_cell = (
        _gallery_metric("peak_memory", float(peak_memory))
        if isinstance(peak_memory, (int, float)) and peak_memory >= 0
        else "-"
    )
    return total_cell, tps_cell, peak_cell


def _run_issue_summary_quality_observed(result: JsonlResultRecord) -> str:
    """Return the compact observed-result cell for the quality table."""
    assessment = result["assessment"]
    if assessment["execution"] == "crashed":
        failure = result["failure"]
        phase = failure.get("phase") if isinstance(failure, dict) else None
        return f"crashed during {_failure_phase_human_label(phase)}" if phase else "crashed"
    observations: tuple[ObservationCode, ...] = tuple(assessment["observations"])
    # The annotation keeps pyright from widening the comprehension to str.
    ordered: tuple[ObservationCode, ...] = tuple(
        code for code in _OBSERVATION_DISPLAY_PRIORITY if code in set(observations)
    )
    glosses = tuple(
        _OBSERVATION_SELECTOR_GLOSSES.get(code, code) for code in (ordered or observations)
    )
    return "; ".join(glosses) if glosses else "none"


def _run_issue_summary_timing_rows(metadata: JsonlMetadataRecord) -> tuple[tuple[str, str], ...]:
    """Start, finish, and a human-readable duration for the run-summary header."""
    rows: list[tuple[str, str]] = []
    if (started := metadata.get("started_at")) is not None:
        rows.append(("Run started", started))
    rows.append(("Run finished", metadata["timestamp"]))
    runtime = metadata.get("total_runtime_seconds")
    if isinstance(runtime, int | float) and not isinstance(runtime, bool) and runtime >= 0:
        rows.append(("Run duration", format_overall_runtime(float(runtime))))
    return tuple(rows)


def _run_issue_summary_quality_section(
    results: Sequence[JsonlResultRecord],
) -> ReportSection:
    """Rank every attempted model by current-run usability with captured facts."""
    ordered = sorted(
        results,
        key=lambda result: (
            _RUN_ISSUE_USABILITY_ORDER.get(
                result["assessment"]["usability"],
                len(_RUN_ISSUE_USABILITY_ORDER),
            ),
            result["model"].lower(),
        ),
    )
    rows: list[tuple[ReportCell, ...]] = []
    for result in ordered:
        total_cell, tps_cell, peak_cell = _run_issue_summary_quality_cells(result)
        rows.append(
            (
                result["model"],
                _human_status_label(result["assessment"]["usability"]),
                total_cell,
                tps_cell,
                peak_cell,
                _run_issue_summary_quality_observed(result),
            )
        )
    return ReportSection(
        "Model quality at a glance",
        (
            ReportParagraph(
                "Every attempted model ranked by mechanical observations, with captured "
                "resource facts. No concerns detected is not a task-compliance or accuracy "
                "verdict. Consult the assessment scope above and inspect the final answers. "
                "Crashes and integration signals have expanded "
                "maintainer evidence."
            ),
            ReportTable(
                (
                    "Model",
                    "Mechanical checks",
                    "Total",
                    "Gen tok/s",
                    "Peak GB",
                    "Observed",
                ),
                tuple(rows),
                compact=True,
            ),
        ),
    )


def _run_issue_summary_surfaced_sections(
    results: Sequence[JsonlResultRecord],
    *,
    output_paths: ReportOutputPaths,
    summary_path: Path,
) -> tuple[ReportSection, ...]:
    """Build one compact review table for each non-actionable execution status."""
    heading_by_execution: dict[ExecutionStatus, str] = {
        "completed": "Completed attempts requiring review",
        "crashed": "Crashed attempts requiring review",
        "indeterminate": "Indeterminate attempts requiring review",
    }

    sections: list[ReportSection] = []
    cluster_section = _run_issue_summary_observation_cluster_section(results)
    if cluster_section is not None:
        sections.append(cluster_section)
    for execution, heading in heading_by_execution.items():
        rows: list[tuple[ReportCell, ...]] = []
        for result in sorted(
            results,
            key=lambda result: _assessment_actionability_key(
                result["model"],
                result["assessment"]["usability"],
                result["assessment"]["observations"],
            ),
        ):
            assessment = result["assessment"]
            if assessment["execution"] != execution:
                continue
            rows.append(
                (
                    result["model"],
                    _human_status_label(assessment["usability"]),
                    _run_issue_summary_observed_result(result),
                    _run_issue_summary_artifact_link(
                        summary_path=summary_path,
                        artifact_path=output_paths.diagnostics,
                        label="diagnostics",
                        anchor=_diagnostics_model_anchor(result["model"]),
                    ),
                )
            )
        if rows:
            sections.append(
                ReportSection(
                    heading,
                    (
                        ReportTable(
                            ("Model", "Mechanical checks", "Observed result", "Evidence"),
                            tuple(rows),
                            compact=True,
                        ),
                    ),
                )
            )
    return tuple(sections)


def _run_issue_summary_context_section(source: RunIssueSummarySource) -> ReportSection:
    """Build compact run settings and environment context."""
    rows: list[tuple[str, str]] = []
    if source.image is not None:
        rows.append(
            (
                "Image",
                ", ".join(value for _, value in _reproduction_image_facts(source.image)[:3]),
            )
        )
    rows.extend((f"Generation: {key}", value) for key, value in source.generation_settings)
    if source.trust_remote_code is not None:
        rows.append(("Trust remote code", str(source.trust_remote_code).lower()))
    if source.producer is not None:
        producer = source.producer
        rows.append(("check_models version", producer["version"]))
        if producer["git_revision"] is not None:
            rows.append(("check_models revision", producer["git_revision"]))
        if (dirty := producer.get("dirty")) is not None:
            rows.append(("check_models source dirty", str(dirty).lower()))
    versions = source.metadata.get("library_versions", {})
    provenance = source.metadata.get("component_provenance", {})
    if isinstance(versions, dict):
        for name in ("mlx-vlm", "mlx", "transformers"):
            if not versions.get(name):
                continue
            rows.append((name, str(versions[name])))
            # An editable/git install's version string does not identify the
            # code (0.6.14 covers many upstream commits, including numerics
            # fixes), so surface the exact source revision beside it.
            revision = _component_source_revision(provenance, name)
            if revision is not None:
                rows.append((f"{name} source revision", revision))
    system = source.metadata["system"]
    rows.extend(
        (label, system[label])
        for label in ("macOS Version", "GPU/Chip", "Python Version")
        if system.get(label)
    )
    blob_ref = _github_blob_ref()
    if re.fullmatch(r"[0-9a-f]{40}", blob_ref):
        # Only reachable via an explicit ref override supplied after the run's
        # artifacts were committed; a producer-HEAD pin is never used because
        # that commit predates the artifacts it would claim to contain.
        link_caveat = (
            f"GitHub links are pinned to producer commit `{blob_ref[:12]}`, so the "
            "linked evidence is durable."
        )
    else:
        link_caveat = (
            "GitHub links target the repository's mutable main branch; they resolve "
            "to this run's evidence only once these artifacts are committed, and a "
            "later run's commit supersedes them. Pin links to that artifact commit "
            "when durable issue evidence is required."
        )
    return ReportSection(
        "Run context",
        (
            ReportKeyValues(tuple(rows)),
            ReportParagraph(link_caveat),
        ),
    )


def _run_issue_artifact_is_stale(
    path: Path,
    run_window: tuple[datetime, datetime] | None,
) -> bool:
    """Return whether a retained text artifact is conclusively from another run."""
    if run_window is None:
        return False
    try:
        _reject_symlink_parent(path)
        canonical_path = _canonical_file_path(path)
        _reject_symlink_parent(canonical_path)
        fd = _open_regular_file_no_symlink(canonical_path, os.O_RDONLY)
        with os.fdopen(fd, "rb") as handle:
            prefix = b"".join(handle.readline(4096) for _ in range(4)).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    artifact_time = _parse_local_timestamp(prefix, embedded=True)
    if artifact_time is None:
        return False
    run_start, run_end = run_window
    tolerance = timedelta(minutes=1)
    return artifact_time < run_start - tolerance or artifact_time > run_end + tolerance


def _run_issue_summary_artifacts_section(
    output_paths: ReportOutputPaths,
    summary_path: Path,
    *,
    source: RunIssueSummarySource,
    include_gallery_markdown: bool,
) -> ReportSection:
    """Build links to the complete retained artifacts."""
    artifact_rows = [
        ("Diagnostics", output_paths.diagnostics),
    ]
    if include_gallery_markdown:
        artifact_rows.append(("Model gallery", output_paths.gallery_markdown))
    artifact_rows.append(("Results JSONL", output_paths.jsonl))
    retained_logs = (("Environment", output_paths.environment), ("Log", output_paths.log))
    stale_names = {
        path.name
        for _label, path in retained_logs
        if _run_issue_artifact_is_stale(path, source.run_window)
    }
    artifact_rows.extend(
        (label, path) for label, path in retained_logs if path.name not in stale_names
    )
    rows = tuple(
        (
            label,
            _run_issue_summary_artifact_link(
                summary_path=summary_path,
                artifact_path=path,
                label=path.name,
            ),
        )
        for label, path in artifact_rows
    )
    content: list[ReportBlock] = []
    if stale_names:
        omitted = ", ".join(f"`{name}`" for name in sorted(stale_names))
        content.append(
            ReportParagraph(
                f"Stale retained artifacts omitted because their timestamps fall outside this "
                f"run: {omitted}."
            )
        )
    content.append(ReportTable(("Artifact", "Link"), rows, compact=True))
    return ReportSection("Full artifacts", tuple(content))


def _run_issue_summary_clean_completions_section(
    results: Sequence[JsonlResultRecord],
    *,
    output_paths: ReportOutputPaths,
    summary_path: Path,
    include_gallery_markdown: bool,
) -> ReportSection:
    """Name the models that completed with nothing for a maintainer to look at."""
    clean_count = sum(
        result["assessment"]["execution"] == "completed"
        and not result["assessment"]["observations"]
        for result in results
    )
    compliance_only_count = sum(
        result["assessment"]["execution"] == "completed"
        and result["assessment"]["maintainer_status"] == "none"
        and bool(result["assessment"]["observations"])
        for result in results
    )
    clean_models = sorted(
        result["model"]
        for result in results
        if result["assessment"]["execution"] == "completed"
        and not result["assessment"]["observations"]
    )
    clean_phrase = _pluralized_count(clean_count, "completion") + " without detected concerns"
    if clean_models:
        clean_phrase += " (" + ", ".join(f"`{model}`" for model in clean_models) + ")"
    clean_sentence = f"{clean_phrase}."
    if compliance_only_count:
        clean_sentence = (
            f"{clean_phrase}; "
            f"{compliance_only_count} more completed with prompt-compliance "
            "observations only (not maintainer issues)."
        )
    if include_gallery_markdown:
        gallery_link = _run_issue_summary_artifact_link(
            summary_path=summary_path,
            artifact_path=output_paths.gallery_markdown,
            label="full model gallery",
        )
        clean_sentence += f" See the {_render_report_cell_markdown(gallery_link, escaped=False)}."
    return ReportSection(
        "Completions without detected concerns",
        (
            ReportRaw(
                markdown_lines=(clean_sentence,),
            ),
        ),
    )


def generate_run_issue_summary_report(
    output_paths: ReportOutputPaths,
    *,
    issue_reports: Mapping[str, Path] | None = None,
    include_gallery_markdown: bool = True,
    comparison: RunComparison | None = None,
) -> Path | None:
    """Generate a paste-ready whole-run issue from the retained schema-3 artifact."""
    source = _load_run_issue_summary_source(output_paths)
    summary_path = _run_issue_summary_path(output_paths)
    actionable = tuple(
        result
        for result in source.results
        if result["assessment"]["maintainer_status"] == "actionable_failure"
    )
    surfaced = tuple(
        result
        for result in source.results
        if result["assessment"]["maintainer_status"] != "none"
        or result["assessment"]["execution"] == "indeterminate"
    )
    other = tuple(result for result in surfaced if result not in actionable)

    counts = Counter(result["assessment"]["execution"] for result in source.results)
    title = (
        "# mlx-vlm compatibility findings across "
        f"{len(source.results)} cached vision-language models"
    )
    eval_mode = str(source.metadata.get("eval_mode", "unknown"))
    blocks: list[ReportBlock] = [
        ReportParagraph(
            "**What this run measures.** "
            + _run_objective_statement(eval_mode)
            + " check_models gave every locally cached MLX vision-language "
            "model the same image and the same prompt (reproduced below), "
            "through mlx-vlm's generation pipeline, and recorded mechanical "
            "facts about each attempt: whether it ran, what the selected "
            "assessment profile checked (stated under *Assessment* below), and "
            "its speed and memory. There is no semantic quality scoring; every "
            "observation is a reproducible mechanical fact from this one image "
            "and prompt."
        ),
        ReportSection(
            "Run summary",
            (
                ReportKeyValues(
                    (
                        *_run_issue_summary_timing_rows(source.metadata),
                        *_run_input_summary_rows(
                            source.image, eval_mode, source.metadata.get("assessment_profile")
                        ),
                        ("Models attempted", str(len(source.results))),
                        ("Completed", str(counts["completed"])),
                        ("Crashed", str(counts["crashed"])),
                        ("Indeterminate", str(counts["indeterminate"])),
                        ("Crashes requiring action", str(len(actionable))),
                        ("Other results requiring review", str(len(other))),
                        (
                            "Reached token limit",
                            str(_count_stop_reason(source.results, "max_tokens")),
                        ),
                        (
                            "Incomplete output at token limit",
                            str(_count_observation(source.results, "token_cap_truncation")),
                        ),
                        (
                            "Stopped early for repetition",
                            str(_count_observation(source.results, "repetition_abort")),
                        ),
                    )
                ),
                ReportParagraph(
                    "Observations are mechanical facts from one image, not general model-quality "
                    "judgements."
                ),
                ReportDetails(
                    "Exact prompt sent to every model",
                    (ReportCodeBlock(source.metadata["prompt"]),),
                ),
            ),
        ),
    ]
    if comparison is not None:
        blocks.append(_run_issue_summary_comparison_section(comparison))
    blocks.append(_run_issue_summary_quality_section(source.results))
    if (constraint_section := _run_issue_summary_constraint_breakdown(source.results)) is not None:
        blocks.append(constraint_section)

    if actionable:
        blocks.append(
            ReportSection(
                "Crashes requiring action",
                tuple(
                    _run_issue_summary_crash_section(
                        result,
                        source=source,
                        output_paths=output_paths,
                        summary_path=summary_path,
                        issue_reports=issue_reports or {},
                    )
                    for result in actionable
                ),
            )
        )

    if other:
        blocks.extend(
            _run_issue_summary_surfaced_sections(
                other,
                output_paths=output_paths,
                summary_path=summary_path,
            )
        )

    blocks.append(
        _run_issue_summary_clean_completions_section(
            source.results,
            output_paths=output_paths,
            summary_path=summary_path,
            include_gallery_markdown=include_gallery_markdown,
        )
    )

    blocks.extend(
        (
            _run_issue_summary_context_section(source),
            _run_issue_summary_artifacts_section(
                output_paths,
                summary_path,
                source=source,
                include_gallery_markdown=include_gallery_markdown,
            ),
        )
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown_artifact(
        summary_path,
        (title, "", *render_report_markdown(tuple(blocks))),
    )
    return summary_path


def regenerate_run_issue_summary(output_dir: Path) -> Path | None:
    """Regenerate only the paste-ready issue body from retained run artifacts."""
    output_paths = ReportOutputPaths.from_root(output_dir)
    source = _load_run_issue_summary_source(output_paths)
    crash_models = tuple(
        result["model"]
        for result in source.results
        if result["assessment"]["execution"] == "crashed"
        and result["assessment"]["maintainer_status"] == "actionable_failure"
    )
    issue_reports = {
        model_name: path
        for model_name, path in _github_issue_report_paths(
            crash_models,
            output_paths.index.parent / "issues",
        ).items()
        if path.is_file()
    }
    comparison_value = source.metadata.get("comparison")
    comparison: RunComparison | None = None
    if isinstance(comparison_value, dict):
        try:
            comparison = _run_comparison_from_json(comparison_value)
        except (KeyError, IndexError, TypeError, ValueError):
            logger.warning(
                "Retained comparison metadata could not be rehydrated; "
                "regenerating the summary without the baseline section."
            )
    return generate_run_issue_summary_report(
        output_paths,
        issue_reports=issue_reports,
        comparison=comparison,
    )


def _output_index_dashboard_lines(
    assessments: Sequence[tuple[str, ResultAssessment]],
    run_duration_seconds: float | None = None,
    *,
    image: RunImageRecord | None = None,
    eval_mode: str | None = None,
    assessment_profile: AssessmentProfile | None = None,
) -> list[str]:
    """Render run-outcome counts and top observations for the output index."""
    counts = _run_outcome_counts(assessments)
    usability_counter = Counter(assessment.usability for _model, assessment in assessments)
    observation_counter: Counter[ObservationCode] = Counter(
        code for _model, assessment in assessments for code in assessment.observations
    )
    lines = [
        "## Run at a glance",
        "",
        *(
            [f"- Run duration: {format_overall_runtime(run_duration_seconds)}"]
            if run_duration_seconds is not None
            else []
        ),
        *(
            [
                f"- {label}: {value}"
                for label, value in _run_input_summary_rows(image, eval_mode, assessment_profile)
            ]
            if image is not None or eval_mode is not None
            else []
        ),
        (
            f"- Models attempted: {counts['models_attempted']} "
            f"(completed {counts['models_completed']}, "
            f"crashed {counts['models_crashed']}, "
            f"indeterminate {counts['models_indeterminate']})"
        ),
        (
            "- Mechanical checks: "
            + ", ".join(
                f"{_human_status_label(label)} {usability_counter.get(label, 0)}"
                for label in ("usable", "usable_with_caveats", "unusable", "not_evaluated")
            )
        ),
    ]
    if observation_counter:
        # Rank by integration importance (registry order), not frequency, so
        # e.g. repetition outranks a frequent-but-benign constraint miss.
        ranked = sorted(
            observation_counter.items(),
            key=lambda item: _OBSERVATION_DISPLAY_RANK[item[0]],
        )
        top_observations = ", ".join(
            f"{_OBSERVATION_DISPLAY_LABELS[code]} ({count})" for code, count in ranked[:5]
        )
        lines.append(f"- Top observations: {top_observations}")
    lines.append("")
    return lines


def generate_output_index_report(
    filename: Path,
    *,
    artifacts: Sequence[ReportArtifact],
    run_issue_summary: Path | None = None,
    issue_reports: Mapping[str, Path] | None = None,
    assessments: Sequence[tuple[str, ResultAssessment]] | None = None,
    eval_mode: str | None = None,
    run_duration_seconds: float | None = None,
    image: RunImageRecord | None = None,
    assessment_profile: AssessmentProfile | None = None,
) -> None:
    """Write a run dashboard plus navigation for current-run artifacts only.

    ``artifacts`` must already be filtered to this run's successful outcomes:
    a file that still exists after a failed renderer is prior-run evidence,
    not a current artifact, and must not be linked.
    """
    # Labels derive from the actual paths so custom output names stay honest.
    links = tuple(
        (artifact.path, artifact.path.name)
        for artifact in artifacts
        if artifact.key != "output_index"
    )
    md = [
        "# Check Models Output Index",
        "",
        f"Assessment: {_assessment_scope(assessment_profile)}",
        "",
    ]
    md.extend((*_wrap_markdown_text(_run_objective_statement(eval_mode)), ""))
    if assessments is not None:
        md.extend(
            _output_index_dashboard_lines(
                assessments,
                run_duration_seconds,
                image=image,
                eval_mode=eval_mode,
                assessment_profile=assessment_profile,
            )
        )
    if run_issue_summary is not None:
        md.extend(("## Start here", ""))
        md.append(
            f"- {_output_index_link(filename, run_issue_summary, 'Run summary')} — "
            "per-model quality ranking, crash triage, and paste-ready issue body"
        )
        md.append("")
    if assessments is not None:
        md.append("## Artifacts")
        md.append("")
    md.extend(f"- {_output_index_link(filename, path, label)}" for path, label in links)
    if issue_reports:
        md.extend(("", "## Issue drafts", ""))
        md.extend(
            f"- {_output_index_link(filename, path, model_name)}"
            for model_name, path in sorted(issue_reports.items())
        )
    _write_text_file(filename, "\n".join(md) + "\n")


def _guard_markdownlint_block(lines: Sequence[str], *, rules: str) -> list[str]:
    """Wrap Markdown lines with markdownlint disable/enable comments."""
    return [
        f"<!-- markdownlint-disable {rules} -->",
        "",
        *lines,
        f"<!-- markdownlint-enable {rules} -->",
    ]


def _issue_repro_portable_path_ref(raw_ref: str, *, fallback: str) -> str:
    """Return a repository-relative or basename-only path for pasted repros."""
    candidate_path = Path(raw_ref)
    if not candidate_path.is_absolute():
        return raw_ref
    try:
        return str(PurePosixPath(*candidate_path.resolve().relative_to(_REPO_ROOT).parts))
    except (OSError, ValueError):
        return candidate_path.name or fallback


def _issue_public_image_source_url(run_args: argparse.Namespace | None) -> str | None:
    """Return validated public source metadata from an executed argument set."""
    source_url = getattr(run_args, "image_source_url", None) if run_args is not None else None
    if not isinstance(source_url, str):
        return None
    try:
        return _parse_public_image_source_url(source_url)
    except argparse.ArgumentTypeError:
        return None


def _append_native_cli_optional_pair(
    tokens: list[str],
    flag: str,
    value: object | None,
) -> None:
    """Append a native mlx-vlm CLI flag/value pair when a value is present."""
    if value is not None:
        tokens.extend([flag, str(value)])


def _append_native_cli_sequence(
    tokens: list[str],
    flag: str,
    value: object | None,
) -> None:
    """Append a native mlx-vlm CLI multi-value argument when present."""
    if value is None or isinstance(value, str | bytes | bytearray):
        if value:
            tokens.extend([flag, str(value)])
        return
    if isinstance(value, Sequence):
        values = [str(item) for item in value if item is not None]
        if values:
            tokens.extend([flag, *values])


_NATIVE_CLI_SEQUENCE_ARGS: Final[tuple[tuple[str, str], ...]] = (
    ("--resize-shape", "resize_shape"),
    ("--eos-tokens", "eos_tokens"),
)
_NATIVE_CLI_OPTIONAL_ARGS: Final[tuple[tuple[str, str], ...]] = (
    ("--seed", "seed"),
    ("--repetition-penalty", "repetition_penalty"),
    ("--max-kv-size", "max_kv_size"),
    ("--kv-bits", "kv_bits"),
    ("--kv-key-bits", "kv_key_bits"),
    ("--kv-value-bits", "kv_value_bits"),
    ("--kv-key-scheme", "kv_key_scheme"),
    ("--kv-value-scheme", "kv_value_scheme"),
    ("--presence-penalty", "presence_penalty"),
    ("--frequency-penalty", "frequency_penalty"),
    ("--prefill-step-size", "prefill_step_size"),
    ("--thinking-budget", "thinking_budget"),
    ("--thinking-mode", "thinking_mode"),
    ("--thinking-start-token", "thinking_start_token"),
)
_NATIVE_CLI_NONDEFAULT_ARGS: Final[tuple[tuple[str, str, object], ...]] = (
    # Sampling flags exist on the upstream generate CLI since #1994 (post-0.6.15).
    # Emitted only when non-default, so repro commands stay valid for releases
    # predating them unless the run actually used the setting.
    ("--top-p", "top_p", 1.0),
    ("--min-p", "min_p", 0.0),
    ("--top-k", "top_k", 0),
    ("--repetition-context-size", "repetition_context_size", DEFAULT_PENALTY_CONTEXT_SIZE),
    ("--presence-context-size", "presence_context_size", DEFAULT_PENALTY_CONTEXT_SIZE),
    ("--frequency-context-size", "frequency_context_size", DEFAULT_PENALTY_CONTEXT_SIZE),
    ("--kv-quant-scheme", "kv_quant_scheme", DEFAULT_KV_QUANT_SCHEME),
    ("--kv-group-size", "kv_group_size", DEFAULT_KV_GROUP_SIZE),
    ("--quantized-kv-start", "quantized_kv_start", DEFAULT_QUANTIZED_KV_START),
    ("--thinking-end-token", "thinking_end_token", DEFAULT_THINKING_END_MARKER),
)
_NATIVE_CLI_BOOLEAN_FLAGS: Final[tuple[tuple[str, str], ...]] = (
    ("--skip-special-tokens", "skip_special_tokens"),
    ("--enable-thinking", "enable_thinking"),
)
_NATIVE_CLI_LOAD_BOOLEAN_FLAGS: Final[tuple[tuple[str, str, bool], ...]] = (
    ("--force-download", "force_download", False),
    ("--trust-remote-code", "trust_remote_code", True),
    ("--quantize-activations", "quantize_activations", False),
)
_NATIVE_GENERATION_KWARG_DEFAULTS: Final[tuple[tuple[str, object], ...]] = (("logit_bias", None),)


def _append_native_cli_load_args(
    tokens: list[str],
    run_args: argparse.Namespace,
    resolved_revision: str | None,
) -> None:
    """Append model-loading arguments shared by full and load-only repros."""
    if (adapter_path := getattr(run_args, "adapter_path", None)) is not None:
        tokens.extend(
            [
                "--adapter-path",
                _issue_repro_portable_path_ref(str(adapter_path), fallback="path/to/adapter"),
            ]
        )
    _append_native_cli_optional_pair(
        tokens,
        "--revision",
        resolved_revision or getattr(run_args, "revision", None),
    )
    for flag, attribute, default in _NATIVE_CLI_LOAD_BOOLEAN_FLAGS:
        if bool(getattr(run_args, attribute, default)):
            tokens.append(flag)


def _build_native_mlx_vlm_cli_tokens(
    *,
    model_name: str,
    prompt: str,
    image_ref: str,
    run_args: argparse.Namespace | None,
    resolved_revision: str | None = None,
    minimal_load: bool = False,
) -> list[str]:
    """Build a native ``python -m mlx_vlm.generate`` command for issue drafts."""
    tokens = [
        "python",
        "-m",
        "mlx_vlm.generate",
        "--model",
        model_name,
        "--image",
        image_ref,
        "--prompt",
        "x" if minimal_load else prompt,
        "--max-tokens",
        str(
            8
            if minimal_load
            else (
                getattr(run_args, "max_tokens", DEFAULT_MAX_TOKENS)
                if run_args is not None
                else DEFAULT_MAX_TOKENS
            )
        ),
        "--temperature",
        str(
            DEFAULT_TEMPERATURE
            if minimal_load
            else (
                getattr(run_args, "temperature", DEFAULT_TEMPERATURE)
                if run_args is not None
                else DEFAULT_TEMPERATURE
            )
        ),
    ]
    if run_args is None:
        _append_native_cli_optional_pair(tokens, "--revision", resolved_revision)
        return tokens

    _append_native_cli_load_args(tokens, run_args, resolved_revision)
    if minimal_load:
        return tokens

    for flag, attribute in _NATIVE_CLI_SEQUENCE_ARGS:
        _append_native_cli_sequence(tokens, flag, getattr(run_args, attribute, None))
    for flag, attribute in _NATIVE_CLI_OPTIONAL_ARGS:
        _append_native_cli_optional_pair(tokens, flag, getattr(run_args, attribute, None))
    for flag, attribute, default in _NATIVE_CLI_NONDEFAULT_ARGS:
        value = getattr(run_args, attribute, default)
        if value != default:
            tokens.extend([flag, str(value)])
    for flag, attribute in _NATIVE_CLI_BOOLEAN_FLAGS:
        if bool(getattr(run_args, attribute, False)):
            tokens.append(flag)
    processor_kwargs = getattr(run_args, "processor_kwargs", None)
    if processor_kwargs:
        tokens.extend(["--processor-kwargs", json.dumps(processor_kwargs, sort_keys=True)])
    generation_kwargs = {
        attribute: value
        for attribute, default in _NATIVE_GENERATION_KWARG_DEFAULTS
        if (value := getattr(run_args, attribute, default)) != default
    }
    if generation_kwargs:
        tokens.extend(["--gen-kwargs", json.dumps(generation_kwargs, sort_keys=True)])
    return tokens


def build_native_mlx_vlm_repro_command_spec(
    *,
    model_name: str,
    prompt: str,
    image_ref: str,
    run_args: argparse.Namespace | None,
    resolved_revision: str | None = None,
    minimal_load: bool = False,
) -> ReproCommandSpec:
    """Build a native ``mlx_vlm.generate`` CLI repro command spec."""
    tokens = _build_native_mlx_vlm_cli_tokens(
        model_name=model_name,
        prompt=prompt,
        image_ref=image_ref,
        run_args=run_args,
        resolved_revision=resolved_revision,
        minimal_load=minimal_load,
    )
    return ReproCommandSpec(
        base_tokens=tuple(tokens[:3]),
        argument_tokens=tuple(tokens[3:]),
    )


def _diagnostics_shared_context_blocks(
    *,
    prompt: str,
    highlighted_results: Sequence[PerformanceResult],
    model_provenance: Mapping[str, ModelProvenanceRecord],
    library_versions: LibraryVersionDict,
    system_info: Mapping[str, str],
    image_path: Path | None,
    run_args: argparse.Namespace | None,
) -> tuple[ReportBlock, ...]:
    """Build single-copy prompt, reproduction, and environment context."""
    image = _run_image_record(
        image_path,
        _load_image_input_profile(image_path),
        source_url=_issue_public_image_source_url(run_args),
    )
    model_rows = tuple(
        (
            result.model_name,
            _diagnostics_fact(
                model_provenance[result.model_name]["resolved_revision"]
                if result.model_name in model_provenance
                else None
            ),
        )
        for result in highlighted_results
    )
    component_rows = tuple(
        _collect_report_component_rows(
            versions=library_versions,
            system_info=dict(system_info),
            library_names=_DIAGNOSTICS_LIB_NAMES,
            system_keys=_DIAGNOSTICS_SYSTEM_KEYS,
            provenance=_collect_component_provenance(library_versions),
        )
    )
    model_block: ReportBlock = (
        ReportTable(("Model", "Resolved revision"), model_rows)
        if model_rows
        else ReportParagraph("No highlighted models.")
    )
    component_block: ReportBlock = (
        ReportTable(("Component", "Value"), component_rows)
        if component_rows
        else ReportParagraph("Environment and component provenance unavailable.")
    )
    thinking_caveat = _shared_repro_thinking_caveat(highlighted_results, run_args)
    reproduction_blocks: tuple[ReportBlock, ...] = _reproduction_input_blocks(
        model_name="MODEL_ID",
        prompt=prompt,
        image=image,
        run_args=run_args,
        resolved_revision="RESOLVED_REVISION",
        published_preview=_published_preview_record(image_path),
    )
    if thinking_caveat is not None:
        reproduction_blocks = (*reproduction_blocks, thinking_caveat)
    return (
        _report_section(
            "Shared Reproduction and Provenance",
            _report_section(
                "Reproduction inputs",
                *reproduction_blocks,
                level=3,
            ),
            _report_section("Highlighted model revisions", model_block, level=3),
            _report_section("Components and system", component_block, level=3),
        ),
    )


def _generate_github_issue_reports(
    *,
    report_context: ReportRenderContext,
    output_dir: Path,
    library_versions: LibraryVersionDict,
    system_info: Mapping[str, str],
    prompt: str,
    image_path: Path | None = None,
    run_args: argparse.Namespace | None = None,
) -> Mapping[str, Path]:
    """Write one factual issue draft per crashed actionable result."""
    issues_dir = output_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    for stale in issues_dir.glob("issue_*.md"):
        stale.unlink()
    stale_index = issues_dir / "index.md"
    if stale_index.exists():
        stale_index.unlink()

    assessments = dict(report_context.assessments)
    model_provenance = _model_provenance_by_model(report_context)
    actionable = _partition_diagnostics(report_context).actionable
    crashes = tuple(
        result for result in actionable if assessments[result.model_name].execution == "crashed"
    )
    generated: dict[str, Path] = {}
    issue_paths = _github_issue_report_paths(
        tuple(result.model_name for result in crashes),
        issues_dir,
    )
    issue_image = _run_image_record(
        image_path,
        report_context.image_profile or _load_image_input_profile(image_path),
        source_url=_issue_public_image_source_url(run_args),
    )
    for result in crashes:
        issue_path = issue_paths[result.model_name]
        parts = [f"# Crash: {MARKDOWN_ESCAPER.escape(result.model_name)}", ""]
        provenance = model_provenance.get(result.model_name)
        issue_blocks: tuple[ReportBlock, ...] = (
            _report_section(
                "Maintainer evidence",
                ReportSection(
                    result.model_name,
                    _diagnostics_model_blocks(
                        result,
                        assessments[result.model_name],
                        run_args=run_args,
                        model_provenance=provenance,
                        system_info=report_context.system_info,
                        image_profile=report_context.image_profile,
                    ),
                    level=3,
                ),
            ),
            _report_section(
                "Reproduction inputs",
                *_reproduction_input_blocks(
                    model_name=result.model_name,
                    prompt=prompt,
                    image=issue_image,
                    run_args=run_args,
                    resolved_revision=(
                        provenance["resolved_revision"] if provenance is not None else None
                    ),
                    crash_phase=result.failure_phase,
                    published_preview=_published_preview_record(image_path),
                    effective_generate_kwargs=(
                        result.prompt_diagnostics.generate_kwargs
                        if result.prompt_diagnostics is not None
                        else None
                    ),
                ),
            ),
        )
        parts.extend(
            render_report_markdown(
                (
                    *issue_blocks,
                    *_issue_provenance_blocks(
                        library_versions=library_versions,
                        system_info=system_info,
                    ),
                )
            )
        )
        while parts and parts[-1] == "":
            parts.pop()
        _write_text_file(issue_path, "\n".join(parts) + "\n")
        generated[result.model_name] = issue_path
    return generated


def _write_diagnostics_artifacts(
    *,
    args: argparse.Namespace,
    library_versions: LibraryVersionDict,
    system_info: dict[str, str],
    prompt: str,
    image_path: Path | None,
    diagnostics_path: Path,
    report_context: ReportRenderContext,
) -> DiagnosticsArtifacts:
    """Write current-run diagnostics and direct per-crash issue drafts."""
    generate_diagnostics_report(
        report_context.result_set.results,
        diagnostics_path,
        prompt=prompt,
        library_versions=library_versions,
        system_info=system_info,
        report_context=report_context,
        image_path=image_path,
        run_args=args,
    )
    issue_reports = _generate_github_issue_reports(
        report_context=report_context,
        output_dir=diagnostics_path.parent.parent,  # Diagnostics is in output/reports/ now
        library_versions=library_versions,
        system_info=system_info,
        prompt=prompt,
        image_path=image_path,
        run_args=args,
    )
    if issue_reports:
        logger.info("GitHub Issue reports generated for %d issue(s).", len(issue_reports))
        for issue_key, issue_path in sorted(issue_reports.items()):
            log_file_path(issue_path, label=f"   Issue Report ({issue_key}):")

    return DiagnosticsArtifacts(
        outcome_counts=_run_outcome_counts(report_context.assessments),
        diagnostics_written=True,
        issue_reports=issue_reports,
    )


def _write_environment_failure_diagnostics(
    *,
    args: argparse.Namespace,
    library_versions: LibraryVersionDict,
    error_message: str,
) -> None:
    """Write a minimal diagnostics report when runtime deps are missing."""
    diagnostics_path: Path = _resolve_report_output_paths(args).diagnostics
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    system_info = get_system_characteristics()
    parts = _build_environment_failure_diagnostics(
        error_message=error_message,
        versions=library_versions,
        system_info=system_info,
    )
    try:
        _write_text_file(diagnostics_path, "\n".join(parts) + "\n")
    except OSError:
        logger.exception("Failed to write environment diagnostics report to %s", diagnostics_path)
    else:
        log_file_path(diagnostics_path, label="   Diagnostics:  ")


def _resolve_report_output_paths(args: argparse.Namespace) -> ReportOutputPaths:
    """Resolve all final report/log output paths once from the output root."""
    return ReportOutputPaths.from_root(args.output_dir)


def _public_artifact_path(path: Path) -> str:
    """Return a stable public artifact path for committed output snapshots."""
    resolved = path.resolve()
    output_root = (_SCRIPT_DIR / "output").resolve()
    try:
        return str(PurePosixPath(*resolved.relative_to(output_root).parts))
    except ValueError:
        try:
            return str(PurePosixPath(*resolved.relative_to(_SCRIPT_DIR.resolve()).parts))
        except ValueError:
            return _home_relative_report_text(str(path))


def _build_report_artifacts(inputs: ReportGenerationInputs) -> tuple[ReportArtifact, ...]:
    """Build the ordered retained artifact plan — the single artifact source.

    Identity, public manifest key, log label, dashboard presentation, and the
    generation job live together so the manifest, logs, dashboard, and output
    index cannot drift apart. Artifacts without a job (diagnostics runs via
    its dedicated runner; log and environment are produced by the run itself)
    receive their outcomes from the orchestrator.
    """
    output_paths = inputs.output_paths
    return (
        ReportArtifact(
            key="output_index",
            public_key="output_index",
            label="   Output Index:   ",
            path=output_paths.index,
            dashboard_label="Output Index",
            dashboard_purpose="Links to retained run artifacts",
            job=lambda: generate_output_index_report(
                output_paths.index,
                artifacts=(),
                assessments=inputs.report_context.assessments,
                eval_mode=inputs.report_context.mode_policy.eval_mode,
                run_duration_seconds=inputs.overall_time,
            ),
        ),
        ReportArtifact(
            key="html",
            public_key="results_html",
            label="   HTML Report:     ",
            path=output_paths.html,
            dashboard_label="HTML Report",
            dashboard_purpose="Standalone gallery and diagnostics",
            job=lambda: generate_html_report(
                results=inputs.results,
                filename=output_paths.html,
                versions=inputs.library_versions,
                prompt=inputs.prompt,
                total_runtime_seconds=inputs.overall_time,
                image_path=inputs.image_path,
                report_context=inputs.report_context,
                run_args=inputs.run_args,
            ),
        ),
        ReportArtifact(
            key="markdown_gallery",
            public_key="model_gallery",
            label="   Gallery Report:  ",
            path=output_paths.gallery_markdown,
            dashboard_label="Gallery Report",
            dashboard_purpose="Complete per-model evidence",
            job=lambda: generate_markdown_gallery_report(
                results=inputs.results,
                filename=output_paths.gallery_markdown,
                prompt=inputs.prompt,
                metadata=inputs.metadata,
                report_context=inputs.report_context,
                versions=inputs.library_versions,
                image_path=inputs.image_path,
            ),
        ),
        ReportArtifact(
            key="diagnostics",
            public_key="diagnostics",
            label="   Diagnostics:     ",
            path=output_paths.diagnostics,
            dashboard_label="Diagnostics",
            dashboard_purpose="Current-run maintainer evidence",
        ),
        ReportArtifact(
            key="jsonl",
            public_key="results_jsonl",
            label="   JSONL Report:    ",
            path=output_paths.jsonl,
            dashboard_label="JSONL Data",
            dashboard_purpose="Machine-readable run and per-model evidence",
        ),
        ReportArtifact(
            key="log",
            public_key="log",
            label="   Log File:",
            path=output_paths.log,
            dashboard_label="System Log",
            dashboard_purpose="Step-by-step CLI trace log",
        ),
        ReportArtifact(
            key="environment",
            public_key="environment",
            label="   Environment:",
            path=output_paths.environment,
            dashboard_label="Environment Log",
            dashboard_purpose="Pip freeze & conda env config log",
        ),
    )


def _run_issue_summary_failure(
    summary_path: Path,
    error_message: str,
) -> tuple[Path | None, ReportArtifactOutcome]:
    """Describe one failed or skipped run-issue-summary artifact outcome."""
    return None, ReportArtifactOutcome(
        key="run_issue_summary",
        path=summary_path,
        succeeded=False,
        error_message=error_message,
    )


def _generate_run_issue_summary_output(
    inputs: ReportGenerationInputs,
    *,
    issue_reports: Mapping[str, Path],
    jsonl_succeeded: bool,
    diagnostics_succeeded: bool,
    gallery_succeeded: bool,
) -> tuple[Path | None, ReportArtifactOutcome | None]:
    """Generate the optional summary only from current-run canonical inputs."""
    summary_path = _run_issue_summary_path(inputs.output_paths)
    if not jsonl_succeeded:
        cleanup_error = _remove_run_issue_summary(inputs.output_paths)
        error_message = "Skipped because current JSONL generation failed."
        if cleanup_error is not None:
            error_message += f" Stale summary cleanup failed: {cleanup_error}"
        return _run_issue_summary_failure(summary_path, error_message)
    summary_required = any(
        assessment.maintainer_status != "none" or assessment.execution == "indeterminate"
        for _, assessment in inputs.report_context.assessments
    )
    if not summary_required:
        cleanup_error = _remove_run_issue_summary(inputs.output_paths)
        if cleanup_error is None:
            return None, None
        return _run_issue_summary_failure(
            summary_path,
            f"Stale summary cleanup failed: {cleanup_error}",
        )
    if not diagnostics_succeeded:
        cleanup_error = _remove_run_issue_summary(inputs.output_paths)
        error_message = "Skipped because current diagnostics generation failed."
        if cleanup_error is not None:
            error_message += f" Stale summary cleanup failed: {cleanup_error}"
        return _run_issue_summary_failure(summary_path, error_message)
    try:
        generated = generate_run_issue_summary_report(
            inputs.output_paths,
            issue_reports=issue_reports,
            include_gallery_markdown=gallery_succeeded,
            comparison=inputs.comparison,
        )
    except Exception as error:  # report isolation must contain renderer defects
        cleanup_error = _remove_run_issue_summary(inputs.output_paths)
        logger.exception("Failed to generate paste-ready run issue summary.")
        error_message = str(error)
        if cleanup_error is not None:
            error_message += f"; stale summary cleanup failed: {cleanup_error}"
        return _run_issue_summary_failure(summary_path, error_message)
    outcome = (
        ReportArtifactOutcome(
            key="run_issue_summary",
            path=generated,
            succeeded=True,
        )
        if generated is not None
        else None
    )
    return generated, outcome


def _run_diagnostics_artifact(
    inputs: ReportGenerationInputs,
    outcomes: list[ReportArtifactOutcome],
) -> tuple[DiagnosticsArtifacts, bool]:
    """Write the diagnostics artifacts, recording the outcome; never raises.

    Returns the artifacts (falling back to outcome counts only on failure) and
    whether the write succeeded, mirroring the per-artifact runner but keeping
    the diagnostics payload the later index/summary steps depend on.
    """
    diagnostics_path = inputs.output_paths.diagnostics
    try:
        artifacts = _write_diagnostics_artifacts(
            args=inputs.run_args or argparse.Namespace(),
            library_versions=inputs.library_versions,
            system_info=inputs.system_info,
            prompt=inputs.prompt,
            image_path=inputs.image_path,
            diagnostics_path=diagnostics_path,
            report_context=inputs.report_context,
        )
    except Exception as error:  # report isolation must contain renderer defects
        logger.exception("Failed to generate diagnostics report.")
        outcomes.append(
            ReportArtifactOutcome(
                key="diagnostics",
                path=diagnostics_path,
                succeeded=False,
                error_message=str(error),
            )
        )
        fallback = DiagnosticsArtifacts(
            outcome_counts=_run_outcome_counts(inputs.report_context.assessments)
        )
        return fallback, False
    outcomes.append(ReportArtifactOutcome(key="diagnostics", path=diagnostics_path, succeeded=True))
    return artifacts, True


def _log_report_generation_outcomes(
    *,
    artifacts: Sequence[ReportArtifact],
    outcomes: Sequence[ReportArtifactOutcome],
    run_issue_summary: Path | None,
) -> None:
    """Log the report-generation verdict and every successfully written path."""
    failures = [outcome for outcome in outcomes if not outcome.succeeded]
    logger.info("")
    if failures:
        logger.warning("Reports generated with %d failure(s):", len(failures))
        for outcome in failures:
            logger.warning("   %s: %s", outcome.key, outcome.error_message)
    else:
        log_success("Reports successfully generated:", prefix="📊")
    successful_keys = {outcome.key for outcome in outcomes if outcome.succeeded}
    for artifact in artifacts:
        if artifact.key in successful_keys:
            log_file_path(artifact.path, label=artifact.label)
    if run_issue_summary is not None:
        log_file_path(run_issue_summary, label="   Run Issue:       ")


def _compute_run_comparison(
    inputs: ReportGenerationInputs, current: RetainedRun
) -> RunComparison | None:
    """Diff the in-memory retained run against the configured baseline (best effort).

    The entire computation — baseline resolution, current-source loading, and
    the diff itself — sits behind one ordinary-exception boundary: comparison
    is an enhancement, and no implementation defect in it may cost the run's
    reports. ``KeyboardInterrupt``/``SystemExit`` still propagate.
    """
    try:
        spec = getattr(inputs.run_args, "compare_with", DEFAULT_COMPARE_WITH)
        baseline = _resolve_comparison_baseline(spec, inputs.output_paths.jsonl)
        if baseline is None:
            return None
        current_image = (
            _run_image_record(inputs.image_path, inputs.report_context.image_profile)
            if inputs.image_path is not None
            else None
        )
        return compare_run_results(
            current.results,
            baseline,
            history_path=_history_path_for_jsonl(inputs.output_paths.jsonl),
            comparison_fingerprint=_comparison_fingerprint_from_metadata(current.metadata),
            history_excludes_current=inputs.history_appended,
            current_execution_mode=str(current.metadata.get("execution_mode", "in_process")),
            current_metadata=current.metadata,
            current_image=current_image,
            current_generation_settings=tuple(
                (key, json.dumps(value, ensure_ascii=False, sort_keys=True))
                for key, value in sorted(_common_generation_settings(inputs.results).items())
            ),
        )
    except Exception as error:  # comparison must never cost the run's reports
        logger.warning("Comparison skipped: unexpected comparison failure (%s)", error)
        logger.debug("Comparison failure detail", exc_info=True)
        return None


def _build_retained_run_guarded(
    inputs: ReportGenerationInputs, artifacts: Sequence[ReportArtifact]
) -> RetainedRun | None:
    """Build the retained run behind the report isolation boundary."""
    manifest = {artifact.public_key: _public_artifact_path(artifact.path) for artifact in artifacts}
    if any(
        assessment.execution == "indeterminate" or assessment.maintainer_status != "none"
        for _model_name, assessment in inputs.report_context.assessments
    ):
        manifest["run_issue_summary"] = "issues/run_summary.md"
    try:
        return _build_retained_run(
            inputs.results,
            prompt=inputs.prompt,
            system_info=inputs.system_info,
            library_versions=inputs.library_versions,
            runtime_fingerprint=inputs.runtime_fingerprint,
            requested_revision=inputs.model_revision,
            report_context=inputs.report_context,
            execution_mode=(
                "isolated" if getattr(inputs.run_args, "isolate", False) else "in_process"
            ),
            total_runtime_seconds=inputs.overall_time,
            started_at=inputs.started_at,
            artifacts=manifest,
            image_path=inputs.image_path,
            image_source_url=(
                getattr(inputs.run_args, "image_source_url", None)
                if inputs.run_args is not None
                else None
            ),
            trust_remote_code=inputs.trust_remote_code,
            comparison=inputs.comparison,
        )
    except Exception:
        logger.exception("Failed to build the retained run record.")
        return None


def _elapsed_run_seconds(inputs: ReportGenerationInputs) -> float:
    """End-to-end wall-clock seconds so far, or the pre-report figure if unknown."""
    if inputs.overall_start_time is None:
        return inputs.overall_time
    return time.time() - inputs.overall_start_time


def _finalize_retained_run_record(
    inputs: ReportGenerationInputs,
    retained: RetainedRun | None,
    artifacts: Sequence[ReportArtifact],
    outcomes: Sequence[ReportArtifactOutcome],
    *,
    run_issue_summary: Path | None,
    jsonl_succeeded: bool,
) -> None:
    """Rewrite the JSONL header once every report outcome is known.

    The pre-report write lists every planned destination. A renderer that
    failed (leaving nothing, or a stale file from an earlier run) must not
    stay advertised in the sole machine contract, so the manifest is reduced
    to the artifacts this run produced — matching index.md — and the
    duration and timestamp become end-to-end. A failed rewrite keeps the
    earlier header rather than costing the run.
    """
    if retained is None or not jsonl_succeeded:
        return
    successful_keys = frozenset(outcome.key for outcome in outcomes if outcome.succeeded)
    manifest = {
        artifact.public_key: _public_artifact_path(artifact.path)
        for artifact in artifacts
        if artifact.key in successful_keys
    }
    if run_issue_summary is not None:
        manifest["run_issue_summary"] = "issues/run_summary.md"
    metadata: JsonlMetadataRecord = {**retained.metadata, "artifacts": manifest}
    if inputs.overall_start_time is not None:
        metadata["total_runtime_seconds"] = round(time.time() - inputs.overall_start_time, 3)
        metadata["timestamp"] = local_now_str()
    try:
        _write_retained_run(
            RetainedRun(metadata=metadata, results=retained.results), inputs.output_paths.jsonl
        )
    except Exception:
        logger.exception(
            "Retained-run manifest reconciliation failed; the pre-report header stands."
        )


def _run_jsonl_artifact(
    retained: RetainedRun | None,
    artifact: ReportArtifact,
    jsonl_path: Path,
    run_artifact: Callable[[ReportArtifact], bool],
    outcomes: list[ReportArtifactOutcome],
) -> bool:
    """Write the retained run through the artifact boundary, or record the miss."""
    if retained is None:
        outcomes.append(
            ReportArtifactOutcome(
                key="jsonl",
                path=jsonl_path,
                succeeded=False,
                error_message="retained-run build failed",
            )
        )
        return False
    return run_artifact(replace(artifact, job=partial(_write_retained_run, retained, jsonl_path)))


def _generate_reports_and_log_outputs(
    inputs: ReportGenerationInputs,
) -> tuple[ReportArtifactOutcome, ...]:
    """Write canonical JSONL first, then isolate every optional renderer."""
    cached_results = {
        result.model_name: result for result in inputs.report_context.result_set.results
    }
    inputs = replace(
        inputs,
        results=[cached_results.get(result.model_name, result) for result in inputs.results],
    )
    artifacts = _build_report_artifacts(inputs)
    by_key = {artifact.key: artifact for artifact in artifacts}
    outcomes: list[ReportArtifactOutcome] = []

    def run_artifact(artifact: ReportArtifact) -> bool:
        if artifact.job is None:
            return False
        try:
            artifact.job()
        except Exception as error:  # report isolation must contain renderer defects
            logger.exception("Failed to generate %s report.", artifact.key)
            outcomes.append(
                ReportArtifactOutcome(
                    key=artifact.key,
                    path=artifact.path,
                    succeeded=False,
                    error_message=str(error),
                )
            )
            return False
        else:
            outcomes.append(
                ReportArtifactOutcome(
                    key=artifact.key,
                    path=artifact.path,
                    succeeded=True,
                )
            )
            return True

    retained = _build_retained_run_guarded(inputs, artifacts)

    if retained is not None and inputs.comparison is None:
        comparison = _compute_run_comparison(inputs, retained)
        if comparison is not None:
            try:
                _log_run_comparison(comparison)
            except Exception:
                logger.exception("Comparison skipped: unexpected comparison rendering failure.")
                # A comparison whose view derivation crashes here would crash
                # the summary renderer too; degrade to no comparison.
                comparison = None
        if comparison is not None:
            inputs = replace(inputs, comparison=comparison)
            retained = RetainedRun(
                metadata={**retained.metadata, "comparison": _run_comparison_to_json(comparison)},
                results=retained.results,
            )
            artifacts = _build_report_artifacts(inputs)
            by_key = {artifact.key: artifact for artifact in artifacts}

    jsonl_succeeded = _run_jsonl_artifact(
        retained,
        by_key["jsonl"],
        inputs.output_paths.jsonl,
        run_artifact,
        outcomes,
    )

    diagnostics_artifacts, diagnostics_succeeded = _run_diagnostics_artifact(inputs, outcomes)
    _log_maintainer_summary(
        artifacts=diagnostics_artifacts,
        diagnostics_path=inputs.output_paths.diagnostics,
    )

    gallery_succeeded = run_artifact(by_key["markdown_gallery"])

    run_issue_summary, summary_outcome = _generate_run_issue_summary_output(
        inputs,
        issue_reports=diagnostics_artifacts.issue_reports,
        jsonl_succeeded=jsonl_succeeded,
        diagnostics_succeeded=diagnostics_succeeded,
        gallery_succeeded=gallery_succeeded,
    )
    if summary_outcome is not None:
        outcomes.append(summary_outcome)
    if run_issue_summary is not None:
        diagnostics_artifacts = replace(
            diagnostics_artifacts,
            run_issue_summary=run_issue_summary,
        )

    for artifact in artifacts:
        if artifact.job is not None and artifact.key not in {
            "output_index",
            "jsonl",
            "diagnostics",
            "markdown_gallery",
        }:
            run_artifact(artifact)

    # The run itself produces the operational logs: the file logger owns
    # check_models.log for the whole run, and environment.log is written by the
    # earlier environment dump when enabled.
    outcomes.append(ReportArtifactOutcome(key="log", path=inputs.output_paths.log, succeeded=True))
    if bool(getattr(inputs.run_args, "environment_logged", False)):
        outcomes.append(
            ReportArtifactOutcome(
                key="environment", path=inputs.output_paths.environment, succeeded=True
            )
        )

    # The index runs last so its links are driven by this run's outcomes:
    # a stale file surviving a failed renderer must not be presented.
    successful_keys = frozenset(outcome.key for outcome in outcomes if outcome.succeeded)
    available = tuple(artifact for artifact in artifacts if artifact.key in successful_keys)
    index_artifact = replace(
        by_key["output_index"],
        job=lambda: generate_output_index_report(
            inputs.output_paths.index,
            artifacts=available,
            run_issue_summary=run_issue_summary,
            issue_reports=diagnostics_artifacts.issue_reports,
            assessments=inputs.report_context.assessments,
            eval_mode=inputs.report_context.mode_policy.eval_mode,
            run_duration_seconds=_elapsed_run_seconds(inputs),
            image=_run_image_record(inputs.image_path, inputs.report_context.image_profile),
            assessment_profile=inputs.report_context.mode_policy.assessment_profile,
        ),
    )
    run_artifact(index_artifact)

    # The definitive machine record is written last: only artifacts this run
    # actually produced stay in its manifest, and its duration and timestamp
    # cover report generation too.
    _finalize_retained_run_record(
        inputs,
        retained,
        artifacts,
        outcomes,
        run_issue_summary=run_issue_summary,
        jsonl_succeeded=jsonl_succeeded,
    )

    _log_report_generation_outcomes(
        artifacts=artifacts,
        outcomes=outcomes,
        run_issue_summary=run_issue_summary,
    )
    return tuple(outcomes)


# ---------- Phase 5: Automatic Differential Reruns ----------

RERUN_TRIAGE_MAX_TOKENS: Final[int] = 100
RERUN_TRIAGE_TIMEOUT: Final[float] = 60.0


def _select_rerun_candidates(
    results: list[PerformanceResult],
) -> list[PerformanceResult]:
    """Select crashes and completed runs with recorded mechanical observations."""
    return [
        result
        for result in results
        if _assess_result(result).maintainer_status
        in {"actionable_failure", "observation_needs_reproduction"}
    ]


def _build_rerun_evidence(
    rerun_result: PerformanceResult,
    *,
    rerun_prompt: str,
) -> RerunEvidence:
    """Build a RerunEvidence summary from a rerun PerformanceResult."""
    gen_chars: int | None = None
    if rerun_result.generation is not None:
        text = getattr(rerun_result.generation, "text", None)
        if text is not None:
            gen_chars = len(text)
    return RerunEvidence(
        rerun_success=rerun_result.success,
        rerun_error_code=rerun_result.error_code,
        rerun_generated_chars=gen_chars,
        rerun_generation_time=rerun_result.generation_time,
        rerun_prompt=rerun_prompt,
    )


def _run_differential_reruns(
    candidates: list[PerformanceResult],
    args: argparse.Namespace,
    image_path: Path,
) -> list[PerformanceResult]:
    """Rerun candidate models with a simple triage prompt for secondary evidence.

    Returns the original results list with ``rerun_evidence`` populated on
    candidates that were rerun.  First-pass data is never overwritten (G3).
    """
    if not candidates:
        return []

    logger.info(
        "Running differential reruns for %d triage candidate(s)...",
        len(candidates),
    )
    updated: list[PerformanceResult] = []
    for idx, result in enumerate(candidates, start=1):
        logger.info(
            "  Rerun %d/%d: %s",
            idx,
            len(candidates),
            result.model_name,
        )
        rerun_result = _run_one_model(
            argparse.Namespace(**{**vars(args), "assessment_profile": "general"}),
            model_identifier=result.model_name,
            image_path=image_path,
            prompt=TRIAGE_PROMPT,
            max_tokens=RERUN_TRIAGE_MAX_TOKENS,
            temperature=0.0,
            timeout=RERUN_TRIAGE_TIMEOUT,
            verbose=False,
        )
        evidence = _build_rerun_evidence(rerun_result, rerun_prompt=TRIAGE_PROMPT)
        updated_result = replace(result, rerun_evidence=evidence)
        logger.info(
            "  Rerun %s: %s (chars=%s)",
            result.model_name,
            "ok" if evidence.rerun_success else "fail",
            evidence.rerun_generated_chars,
        )
        updated.append(updated_result)
    return updated


def _print_reports_dashboard(
    artifacts: Sequence[ReportArtifact],
    outcomes: Sequence[ReportArtifactOutcome],
    history_path: Path | None = None,
    *,
    run_issue_summary: Path | None = None,
) -> None:
    """Print the console dashboard for artifacts the current run produced.

    Rows are driven by successful outcomes, never bare file existence, so a
    stale file surviving a failed renderer is not presented as current.
    """
    console = _make_rich_console(markup=True, highlight=True)

    table = Table(
        box=None,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("Artifact / Report", style="bold green", width=22)
    table.add_column("Purpose", style="italic white", width=42)
    table.add_column("Local Location (Clickable)", style="blue")

    def add_row(label: str, purpose: str, path: Path | None) -> None:
        if path is None:
            return
        uri = f"file://{path.resolve()}"
        clickable_link = f"[link={uri}]{uri}[/link]"
        table.add_row(label, purpose, clickable_link)

    successful_keys = frozenset(outcome.key for outcome in outcomes if outcome.succeeded)
    for artifact in artifacts:
        if artifact.key in successful_keys:
            add_row(artifact.dashboard_label, artifact.dashboard_purpose, artifact.path)

    add_row(
        "Run Issue Summary",
        "Start here: model-quality ranking and paste-ready GitHub issue body",
        run_issue_summary,
    )

    if history_path and history_path.exists():
        add_row("Run History", "Persistent database of previous runs", history_path)

    panel = Panel(
        table,
        title="[bold green]📊 MLX VLM CHECKER - ARTIFACT DASHBOARD[/bold green]",
        subtitle="[bold yellow]💡 Tip: CMD+Click any link to open locally[/bold yellow]",
        border_style="blue",
        expand=True,
    )
    console.print()
    console.print(panel)


def finalize_execution(
    *,
    args: argparse.Namespace,
    results: list[PerformanceResult],
    library_versions: LibraryVersionDict,
    overall_start_time: float,
    prompt: str,
    image_path: Path | None = None,
    metadata: MetadataDict | None = None,
    started_at: str | None = None,
) -> None:
    """Output summary statistics, generate reports, and display timing information."""
    overall_time: float = time.time() - overall_start_time
    if results:
        metadata_exposed_to_prompt = _prompt_builder_exposes_metadata(args, metadata)

        # Gather system characteristics for reports
        system_info = get_system_characteristics()
        recommended_working_set_bytes = _get_recommended_working_set_bytes()
        runtime_fingerprint = collect_runtime_fingerprint()
        requested_revision = (
            str(args.revision) if getattr(args, "revision", None) is not None else None
        )
        model_provenance = {
            result.model_name: _collect_model_provenance(
                result.model_name,
                requested_revision=requested_revision,
            )
            for result in results
        }
        report_context = _build_report_render_context(
            results=[
                replace(
                    result,
                    assessment_profile=getattr(args, "assessment_profile", None) or "general",
                )
                for result in results
            ],
            prompt=prompt,
            image_path=image_path,
            metadata=metadata,
            metadata_exposed_to_prompt=metadata_exposed_to_prompt,
            eval_mode=str(getattr(args, "eval_mode", DEFAULT_EVAL_MODE)),
            system_info=system_info,
            recommended_working_set_bytes=recommended_working_set_bytes,
            preflight_issues=_get_run_preflight_issues(args),
            model_provenance=model_provenance,
        )
        results = list(report_context.result_set.results)
        _validate_report_render_context(report_context)
        assessments = dict(report_context.assessments)
        for index, result in enumerate(results, start=1):
            if index > 1:
                print_cli_separator()
            print_model_result(
                result,
                assessment=assessments[result.model_name],
                verbose=bool(getattr(args, "verbose", False)),
                run_index=index,
                total_runs=len(results),
                prompt=prompt,
            )
        log_summary(
            results,
            assessments=assessments,
            image_path=image_path,
        )

        # Prepare output paths
        output_paths = _resolve_report_output_paths(args)
        history_path = _history_path_for_jsonl(output_paths.jsonl)
        eval_mode = report_context.mode_policy.eval_mode

        for output_path in (
            output_paths.index,
            output_paths.html,
            output_paths.gallery_markdown,
            output_paths.jsonl,
            output_paths.diagnostics,
            output_paths.log,
            output_paths.environment,
        ):
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Preserve raw append-only history without reading it into current reports.
        current_image_record = _run_image_record(image_path, report_context.image_profile)
        history_record = append_history_record(
            history_path=history_path,
            results=results,
            prompt=prompt,
            system_info=system_info,
            library_versions=library_versions,
            image_path=image_path,
            runtime_fingerprint=runtime_fingerprint,
            eval_mode=eval_mode,
            comparison_fingerprint=_comparison_fingerprint(
                prompt=prompt,
                image_sha256=(
                    current_image_record["sha256"] if current_image_record is not None else None
                ),
                generation_settings=_common_generation_settings(results),
                execution_mode="isolated" if getattr(args, "isolate", False) else "in_process",
                eval_mode=eval_mode,
                system_info=system_info,
            ),
            model_provenance=model_provenance,
        )

        log_file_path(history_path, label="   History:     ")

        report_inputs = ReportGenerationInputs(
            results=results,
            library_versions=library_versions,
            prompt=prompt,
            metadata=metadata,
            overall_time=overall_time,
            started_at=started_at,
            overall_start_time=overall_start_time,
            image_path=image_path,
            system_info=system_info,
            report_context=report_context,
            output_paths=output_paths,
            run_args=args,
            history_appended=history_record is not None,
            model_revision=requested_revision,
            trust_remote_code=bool(getattr(args, "trust_remote_code", True)),
            runtime_fingerprint=runtime_fingerprint,
        )
        report_outcomes = _generate_reports_and_log_outputs(report_inputs)
        run_issue_summary = next(
            (
                outcome.path
                for outcome in report_outcomes
                if outcome.key == "run_issue_summary" and outcome.succeeded
            ),
            None,
        )

        # Print the beautiful report summary dashboard
        _print_reports_dashboard(
            _build_report_artifacts(report_inputs),
            report_outcomes,
            history_path=history_path,
            run_issue_summary=run_issue_summary,
        )

    else:
        log_warning_note("No models processed. No performance summary generated.")
        logger.info("Skipping report generation as no models were processed.")

    print_cli_section("Final Summary")
    log_blank()
    logger.info(
        "⏱  Overall runtime: %s",
        format_overall_runtime(time.time() - overall_start_time),
        extra={"style_hint": LogStyles.METRIC_LABEL},
    )
    print_version_info(library_versions)


# =============================================================================
# SECTION: MAIN ORCHESTRATION & ARGPARSE
# =============================================================================


def main(args: argparse.Namespace) -> None:
    """Run CLI execution for MLX VLM model check."""
    _LinkStyleState.value = getattr(args, "link_style", "github")

    # Wall clock, not a perf counter: the reported run duration must match
    # what a person experienced, including any time the machine was asleep.
    overall_start_time: float = time.time()
    started_at: str = local_now_str()
    library_versions: LibraryVersionDict | None = None
    try:
        library_versions = setup_environment(args)
        # Validate all CLI arguments early to fail fast (after logging setup)
        validate_cli_arguments(args)

        print_cli_header("MLX Vision Language Model Check")

        image_path = find_and_validate_image(args)

        metadata = handle_metadata(image_path, args)
        _apply_eval_mode_defaults(args, metadata)

        prompt = prepare_prompt(args, metadata)

        # Handle dry-run mode: show what would be run and exit
        if getattr(args, "dry_run", False):
            _handle_dry_run(args, image_path, prompt, library_versions)
            return

        # Hard-fail before any model execution when core runtime deps are unavailable.
        _raise_for_missing_runtime_dependencies()

        results = process_models(args, image_path, prompt=prompt)

        # Phase 5: Differential reruns for crashes and mechanical observations
        if getattr(args, "rerun_triage", False):
            candidates = _select_rerun_candidates(results)
            if candidates:
                updated = _run_differential_reruns(candidates, args, image_path)
                # Merge rerun evidence back into results list
                rerun_map = {r.model_name: r for r in updated}
                results = [rerun_map.get(r.model_name, r) for r in results]

        finalize_execution(
            args=args,
            results=results,
            library_versions=library_versions,
            overall_start_time=overall_start_time,
            prompt=prompt,
            image_path=image_path,
            metadata=metadata,
            started_at=started_at,
        )
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user.")
        sys.exit(130)
    except SystemExit:
        raise
    except RuntimeError as main_err:
        message = str(main_err)
        if message.startswith("Required runtime dependencies unavailable:"):
            log_failure("Required runtime dependencies unavailable; no models were run.")
            log_warning_note(
                "Install/repair the missing packages and re-run. Environment details and a "
                "minimal diagnostics report have been written for triage.",
            )
            _write_environment_failure_diagnostics(
                args=args,
                library_versions=library_versions or get_library_versions(),
                error_message=message,
            )
        else:
            logger.critical("Fatal error in main execution: %s", main_err, exc_info=True)
        sys.exit(1)
    except (OSError, ValueError) as main_err:
        logger.critical("Fatal error in main execution: %s", main_err, exc_info=True)
        sys.exit(1)


def _handle_dry_run(
    args: argparse.Namespace,
    image_path: Path,
    prompt: str,
    library_versions: LibraryVersionDict,
) -> None:
    """Handle --dry-run mode: display what would be run without invoking models.

    Args:
        args: Parsed command line arguments
        image_path: Resolved image path
        prompt: Generated or user-provided prompt
        library_versions: Dictionary of library versions
    """
    print_cli_section("Dry Run Mode")
    logger.info("🔍 Validating configuration without running models...")
    log_blank()

    # Image info
    logger.info("📷 Image: %s", image_path)
    if image_path.exists():
        size_mb = image_path.stat().st_size / (1024 * 1024)
        logger.info("   Size: %.2f MB", size_mb)
    log_blank()

    # Prompt info
    logger.info("💬 Prompt:")
    # Wrap prompt for readability
    wrapped = textwrap.wrap(prompt, width=90)
    max_lines = FORMATTING.max_prompt_preview_lines
    for line in wrapped[:max_lines]:
        logger.info("   %s", line)
    if len(wrapped) > max_lines:
        logger.info("   ... (%d more lines)", len(wrapped) - max_lines)
    log_blank()

    validate_and_warn_model_selection(args)

    # Discover models
    if args.models:
        model_identifiers = args.models
        logger.info("📦 Models specified explicitly:")
        selection_context = "explicit list"
        _warn_explicit_incomplete_cache(
            model_identifiers, requested_revision=getattr(args, "revision", None)
        )
    else:
        model_identifiers = _supported_cached_model_ids_with_skipped_logging(
            get_cached_model_eligibility()
        )
        logger.info("📦 Cached models selected by default discovery (layout + image capability):")
        selection_context = "cached models"

    model_identifiers = apply_exclusions(
        model_identifiers,
        args.exclude or [],
        selection_context,
    )

    if not model_identifiers:
        logger.warning("   ⚠\ufe0f  No models to process!")
    else:
        unsupported_arch_count = 0
        capability_by_id = {
            entry.repo_id: entry.capability for entry in get_cached_model_eligibility()
        }
        for idx, model_id in enumerate(model_identifiers, start=1):
            model_type, resolved, arch_supported = _arch_precheck_for_model(model_id)
            capability = capability_by_id.get(model_id)
            capability_note = (
                f"  ❔ image capability unknown ({'; '.join(capability.evidence)})"
                if capability is not None and capability.verdict == "unknown"
                else ""
            )
            if arch_supported is False:
                unsupported_arch_count += 1
                resolved_note = (
                    f" (resolves to {resolved})" if resolved and resolved != model_type else ""
                )
                logger.info(
                    "   %2d. %s  ⚠\ufe0f model_type %s%s not in installed mlx_vlm/models",
                    idx,
                    model_id,
                    model_type,
                    resolved_note,
                )
            else:
                logger.info("   %2d. %s%s", idx, model_id, capability_note)
        if unsupported_arch_count:
            logger.warning(
                "   %d model(s) use architectures not supported by the installed mlx-vlm "
                "(folder-name pre-check only; they will still be attempted to capture "
                "real crash evidence)",
                unsupported_arch_count,
            )

    log_blank()
    logger.info("📊 Would process %d model(s)", len(model_identifiers))
    log_blank()

    # Library versions
    print_version_info(library_versions)

    log_blank()
    log_success("Dry run complete. No models were invoked.", prefix="✅")


def main_cli() -> None:
    """CLI entry point for the MLX VLM checker script."""
    if len(sys.argv) >= 3 and sys.argv[1] == ISOLATED_WORKER_FLAG:  # noqa: PLR2004 - argv[0], flag, spec
        raise SystemExit(_run_isolated_worker(Path(sys.argv[2])))
    parser = _build_cli_parser()

    # Parse arguments
    args: argparse.Namespace = parser.parse_args()

    # If neither --folder nor --image is specified, assume default folder
    if getattr(args, "folder", None) is None and getattr(args, "image", None) is None:
        args.folder = DEFAULT_FOLDER
        logger.info(
            "No --folder or --image specified. Assuming default folder: %s",
            DEFAULT_FOLDER,
        )
        print_cli_section("No image or folder specified")
        logger.info(
            "Assuming default folder: %s. To override, specify --folder or --image.",
            DEFAULT_FOLDER,
        )
        if not DEFAULT_FOLDER.exists():
            logger.warning(
                "Default folder does not exist: %s — create it or use --folder / --image.",
                DEFAULT_FOLDER,
            )

    # Print all command-line arguments if verbose is set
    if getattr(args, "verbose", False):
        print_cli_section("Command Line Parameters")
        for arg_name, arg_value in sorted(vars(args).items()):
            logger.info("  %s: %s", arg_name, arg_value)

    # Load quality configuration
    load_quality_config(getattr(args, "quality_config", None))

    main(args)


class _ConditionalDefaultsHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Show argparse defaults only when they are real user-facing defaults."""

    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help or ""
        if action.default in (None, argparse.SUPPRESS):
            return help_text
        return super()._get_help_string(action) or help_text


class _ArgumentAdder(Protocol):
    """Minimal argparse container protocol for parser and argument groups."""

    def add_argument(self, *_name_or_flags: str, **kwargs: Any) -> argparse.Action:  # noqa: ANN401 - argparse keyword protocol
        """Register an argparse option."""
        ...


def _add_output_path_arguments(parser: _ArgumentAdder) -> None:
    """Register the output-root and comparison arguments on the CLI parser."""
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_SCRIPT_DIR / "output",
        help="Root directory for the canonical report, machine-data, issue, and log layout.",
    )
    parser.add_argument(
        "--compare-with",
        type=str,
        default=DEFAULT_COMPARE_WITH,
        metavar="auto|none|PATH|GITREF",
        help=(
            "Baseline sweep to diff this run against in run_summary.md and the retained "
            "results.jsonl metadata. "
            "'auto' uses the retained results.jsonl at git HEAD when the output path is "
            "tracked (the last committed sweep); 'none' disables; a path reads that "
            "results.jsonl; any other value is a git ref for the same repo-relative path."
        ),
    )


def _add_input_arguments(parser: argparse.ArgumentParser) -> None:
    """Register image/folder input arguments."""
    input_group = parser.add_argument_group("Input")
    input_selector = input_group.add_mutually_exclusive_group(required=False)
    input_selector.add_argument(
        "-f",
        "--folder",
        type=Path,
        default=None,
        help=(
            "Folder to scan. Requires a path when provided. The most recently modified "
            "image file in the folder will be used. If both --folder and --image are "
            f"omitted, the most recently modified image in {DEFAULT_FOLDER} will be used."
        ),
    )
    input_selector.add_argument(
        "-i",
        "--image",
        type=Path,
        default=None,
        help=("Path to a specific image file to process directly. Requires a path when provided."),
    )
    input_group.add_argument(
        "--image-source-url",
        type=_parse_public_image_source_url,
        default=None,
        help=(
            "Public HTTP(S) location of the exact selected image, recorded only as "
            "reproduction metadata; the URL is never used as the inference input."
        ),
    )


def _add_model_prompt_generation_arguments(parser: argparse.ArgumentParser) -> None:
    """Register model, prompt, and generation control arguments."""
    model_group = parser.add_argument_group("Model Selection")
    model_group.add_argument(
        "-m",
        "--models",
        action="extend",
        nargs="+",
        type=str,
        default=None,
        help=(
            "Specify models by ID/path. Overrides cache scan. "
            "May be provided multiple times; model lists accumulate."
        ),
    )
    model_group.add_argument(
        "-e",
        "--exclude",
        action="extend",
        nargs="+",
        type=str,
        default=None,
        help=(
            "Exclude models by ID/path from the model list "
            "(works with both explicit --models and cache scan). "
            "May be provided multiple times; exclusions accumulate."
        ),
    )
    model_group.add_argument(
        "--trust-remote-code",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Allow custom code from Hub models (SECURITY RISK). "
            "Use --no-trust-remote-code to disable."
        ),
    )
    model_group.add_argument(
        "--revision",
        type=str,
        default=None,
        help="Model revision (branch, tag, or commit hash) for version pinning.",
    )
    model_group.add_argument(
        "--adapter-path",
        type=str,
        default=None,
        help="Path to LoRA adapter weights to apply on top of the base model.",
    )

    prompt_group = parser.add_argument_group("Prompt and Processor")
    prompt_group.add_argument(
        "-p",
        "--prompt",
        type=str,
        default=None,
        help=(
            "Prompt text to send to the model. Requires text when provided. If omitted, "
            "the resolved --eval-mode lane supplies the prompt. When provided, it "
            "overrides the lane prompt only: the lane still governs the default token "
            "cap and report labeling. No metadata hints are appended; 'assisted' still requires descriptive "
            "metadata."
        ),
    )
    prompt_group.add_argument(
        "--resize-shape",
        type=int,
        nargs="+",
        default=None,
        help=(
            "Resize image input before processor handling. "
            "Provide 1 integer for square resize or 2 for height width after a "
            "single flag occurrence."
        ),
    )
    prompt_group.add_argument(
        "--eos-tokens",
        action="extend",
        type=str,
        nargs="+",
        default=None,
        help=(
            "Additional EOS tokens to stop on. Supports escaped values like \\n. "
            "May be provided multiple times; token lists accumulate."
        ),
    )
    prompt_group.add_argument(
        "--skip-special-tokens",
        action="store_true",
        default=False,
        help="Skip tokenizer special tokens in the detokenized output.",
    )
    prompt_group.add_argument(
        "--processor-kwargs",
        type=_parse_processor_kwargs_arg,
        default=None,
        help=(
            "Extra processor kwargs as a JSON object. "
            'Example: --processor-kwargs \'{"cropping": false, "max_patches": 3}\''
        ),
    )
    prompt_group.add_argument(
        "--enable-thinking",
        action="store_true",
        default=False,
        help="Enable thinking mode in the upstream chat template and generation flow.",
    )
    prompt_group.add_argument(
        "--thinking-mode",
        type=str,
        default=None,
        help=(
            "Value passed to chat templates that support thinking_mode (matches mlx-vlm upstream)."
        ),
    )
    prompt_group.add_argument(
        "--thinking-budget",
        type=int,
        default=None,
        help="Maximum number of thinking tokens before forcing the end token.",
    )
    prompt_group.add_argument(
        "--thinking-start-token",
        type=str,
        default=None,
        help="Token marking the start of a thinking block, such as <think>.",
    )
    prompt_group.add_argument(
        "--thinking-end-token",
        type=str,
        default=DEFAULT_THINKING_END_MARKER,
        help="Token marking the end of a thinking block when thinking mode is enabled.",
    )
    prompt_group.add_argument(
        "--auto-thinking-budget",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When no explicit thinking flags are given, cap thinking for models "
            f"whose chat template opens a thinking block: budget = max-tokens - "
            f"{AUTO_THINKING_ANSWER_RESERVE_TOKENS} (skipped below "
            f"{AUTO_THINKING_BUDGET_MIN_TOKENS}). Other models are unaffected; "
            "the chat template itself is never altered."
        ),
    )

    generation_group = parser.add_argument_group("Generation Controls")
    generation_group.add_argument(
        "--assessment-profile",
        choices=("general", "metadata"),
        default=None,
        help=(
            "Checks applied to the answer, not a prompt change. Defaults to metadata for "
            "built-in metadata prompts and general for custom/triage prompts; explicit "
            "selection overrides the default. Metadata checks Title/Description/Keywords "
            "and duplicate keywords, not prose limits. --rerun-triage always uses general."
        ),
    )
    generation_group.add_argument(
        "--eval-mode",
        choices=[DEFAULT_EVAL_MODE, "triage", "blind", "assisted"],
        default=DEFAULT_EVAL_MODE,
        help=(
            "Evaluation lane: 'auto' (default) selects 'assisted' when descriptive metadata "
            "is available and 'blind' otherwise; 'triage' = brief compatibility caption, "
            f"{TRIAGE_MAX_TOKENS} tokens; 'blind' = structured cataloguing without metadata "
            f"hints, {DEFAULT_MAX_TOKENS} tokens; 'assisted' = structured cataloguing with "
            f"metadata hints, {DEFAULT_MAX_TOKENS} tokens. A custom --prompt overrides the "
            "lane prompt only; the lane still governs the default token cap and report "
            "labeling."
        ),
    )
    generation_group.add_argument(
        "-x",
        "--max-tokens",
        type=int,
        default=None,
        help=(
            "Max new tokens to generate. When omitted, the resolved evaluation lane "
            f"supplies the default ({DEFAULT_MAX_TOKENS}; triage {TRIAGE_MAX_TOKENS}). "
            "An explicit value always wins over the lane default."
        ),
    )
    generation_group.add_argument(
        "-t",
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature.",
    )
    generation_group.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Nucleus sampling parameter (0.0-1.0). Lower values = more focused output.",
    )
    generation_group.add_argument(
        "--min-p",
        type=float,
        default=0.0,
        help="Minimum-probability sampling floor (0.0-1.0). 0.0 disables min-p filtering.",
    )
    generation_group.add_argument(
        "--top-k",
        type=int,
        default=0,
        help="Top-k sampling limit. 0 disables top-k filtering.",
    )
    generation_group.add_argument(
        "-r",
        "--repetition-penalty",
        type=float,
        default=None,
        help="Penalize repeated tokens (>1.0 discourages repetition). None = no penalty.",
    )
    generation_group.add_argument(
        "--repetition-context-size",
        type=int,
        default=20,
        help="Context window size for repetition penalty.",
    )

    server_group = parser.add_argument_group("MLX-VLM Server Controls")
    server_group.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Seed forwarded to upstream generation sampling. "
            "Matches the MLX-VLM server request field."
        ),
    )
    server_group.add_argument(
        "--presence-penalty",
        type=float,
        default=None,
        help="Additive penalty for tokens that already appeared in generated context.",
    )
    server_group.add_argument(
        "--presence-context-size",
        type=int,
        default=DEFAULT_PENALTY_CONTEXT_SIZE,
        help="Number of recent generated tokens used for presence penalty.",
    )
    server_group.add_argument(
        "--frequency-penalty",
        type=float,
        default=None,
        help="Additive penalty scaled by token frequency in generated context.",
    )
    server_group.add_argument(
        "--frequency-context-size",
        type=int,
        default=DEFAULT_PENALTY_CONTEXT_SIZE,
        help="Number of recent generated tokens used for frequency penalty.",
    )
    server_group.add_argument(
        "--logit-bias",
        type=_parse_logit_bias_arg,
        default=None,
        help="OpenAI-style token-id bias JSON object, e.g. '{\"42\": -1.5}'.",
    )


def _add_runtime_workflow_console_arguments(parser: argparse.ArgumentParser) -> None:
    """Register runtime, workflow, and console presentation arguments."""
    runtime_group = parser.add_argument_group("Runtime and Memory")
    runtime_group.add_argument(
        "--system-telemetry",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "macOS thermal CPU speed limit and memory-pressure telemetry via read-only "
            "probes (pmset -g / sysctl -n; no system settings are changed; darwin only, "
            "sudo-free). Default: one snapshot probe pair per model, taken outside timed "
            "inference. --system-telemetry opts into continuous background sampling "
            "(its subprocesses overlap timed inference); --no-system-telemetry disables "
            "telemetry entirely. Aggregates are recorded per model in results.jsonl and "
            "surfaced in diagnostics."
        ),
    )
    runtime_group.add_argument(
        "-L",
        "--lazy-load",
        action="store_true",
        default=False,
        help="Use lazy loading for models (loads weights on-demand, reduces peak memory).",
    )
    runtime_group.add_argument(
        "--force-download",
        action="store_true",
        default=False,
        help="Force mlx-vlm/Hugging Face Hub to download model files instead of using cache.",
    )
    runtime_group.add_argument(
        "--quantize-activations",
        action="store_true",
        default=False,
        help="Enable mlx-vlm activation quantization during model loading when supported.",
    )
    runtime_group.add_argument(
        "--max-kv-size",
        type=int,
        default=None,
        help="Maximum KV cache size (limits memory for long sequences). None = no limit.",
    )
    runtime_group.add_argument(
        "-b",
        "--kv-bits",
        type=float,
        default=None,
        help=(
            "Quantize KV cache to N bits. Uniform supports 2, 3, 4, 5, 6, "
            "or 8; fractional values such as 3.5 use TurboQuant automatically."
        ),
    )
    runtime_group.add_argument(
        "--kv-quant-scheme",
        choices=["uniform", "turboquant"],
        default=DEFAULT_KV_QUANT_SCHEME,
        help=(
            "KV cache quantization backend. Default: uniform. "
            "Use turboquant to match upstream TurboQuant cache handling."
        ),
    )
    runtime_group.add_argument(
        "--kv-key-bits",
        type=float,
        default=None,
        help=(
            "Override the KV cache key bit-width per tensor (requires --kv-bits; "
            "TurboQuant defaults to floor(--kv-bits))."
        ),
    )
    runtime_group.add_argument(
        "--kv-value-bits",
        type=float,
        default=None,
        help=(
            "Override the KV cache value bit-width per tensor (requires --kv-bits; "
            "TurboQuant defaults to ceil(--kv-bits))."
        ),
    )
    runtime_group.add_argument(
        "--kv-key-scheme",
        choices=["uniform", "turboquant"],
        default=None,
        help="Override the KV quantization backend for keys only (requires --kv-bits).",
    )
    runtime_group.add_argument(
        "--kv-value-scheme",
        choices=["uniform", "turboquant"],
        default=None,
        help="Override the KV quantization backend for values only (requires --kv-bits).",
    )
    runtime_group.add_argument(
        "-g",
        "--kv-group-size",
        type=int,
        default=DEFAULT_KV_GROUP_SIZE,
        help="Quantization group size for KV cache.",
    )
    runtime_group.add_argument(
        "--quantized-kv-start",
        type=int,
        default=DEFAULT_QUANTIZED_KV_START,
        help=(
            "Start position for KV cache quantization. "
            f"Default: {DEFAULT_QUANTIZED_KV_START} (matches mlx-vlm upstream)."
        ),
    )
    runtime_group.add_argument(
        "--prefill-step-size",
        type=int,
        default=2048,
        help="Step size for prompt prefill. Default: 2048 (matches mlx-vlm upstream).",
    )
    runtime_group.add_argument(
        "-T",
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for model operations.",
    )

    quality_group = parser.add_argument_group("Quality and Workflow")
    quality_group.add_argument(
        "-c",
        "--quality-config",
        type=Path,
        default=None,
        help="Path to custom quality configuration YAML file.",
    )
    quality_group.add_argument(
        "--isolate",
        action="store_true",
        default=False,
        help=(
            "Run each model in a fresh child interpreter. A native crash (segfault, abort, "
            "interpreter-finalization fault) in one model is then recorded as that model's "
            "phase-tagged failure instead of ending the sweep; costs a few seconds of "
            "import time per model and frees GPU memory between models."
        ),
    )
    quality_group.add_argument(
        "--rerun-triage",
        action="store_true",
        default=False,
        help=(
            "After the first pass, rerun crashed models and completed models with "
            "recorded mechanical observations using a simple prompt. "
            f"Reruns override prompt, assessment (general), max tokens ({RERUN_TRIAGE_MAX_TOKENS}), "
            f"temperature (0), timeout ({RERUN_TRIAGE_TIMEOUT:g}s), and verbose output (off). "
            "Other settings, including --isolate, are retained; first-pass results are never overwritten."
        ),
    )
    quality_group.add_argument(
        "--link-style",
        choices=["relative", "github"],
        default="github",
        help=(
            "Link format for companion artifacts in Markdown reports: "
            "'github' (default) generates absolute GitHub web URLs so pasted report "
            "content keeps working outside the local checkout; "
            "'relative' generates offline-friendly local relative paths."
        ),
    )
    quality_group.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Validate arguments and show what would be run without invoking any models. "
            "Lists discovered models, the generated prompt, and image path then exits."
        ),
    )

    console_group = parser.add_argument_group("Console Output")
    console_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose and debug output (DEBUG logging).",
    )
    console_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output.",
    )
    console_group.add_argument(
        "--force-color",
        action="store_true",
        help="Force enable ANSI colors even if not a TTY.",
    )
    console_group.add_argument(
        "--width",
        type=int,
        default=None,
        help=(
            "Force a specific CLI output width (columns) for separators and text wrapping. "
            "Overrides terminal detection. Also supported via MLX_VLM_WIDTH env var."
        ),
    )


def _build_cli_parser() -> argparse.ArgumentParser:
    """Build and return the command-line parser for the CLI entry point."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        # Pin prog to the 3.13 default (basename of argv[0]) rather than relying on
        # argparse's heuristic: Python 3.14 derives it from the `-m` invocation
        # instead, and the exact rule differs between 3.14 point releases
        # (3.14.6 rendered "python3 -m pytest" under a patched argv; 3.14.7 does
        # not), which made the usage line depend on the interpreter patch level.
        prog=Path(sys.argv[0]).name or "check_models.py",
        description="MLX VLM Model Checker",
        usage="%(prog)s [-h] [-f FOLDER | -i IMAGE] [options]",
        formatter_class=_ConditionalDefaultsHelpFormatter,
    )

    _add_input_arguments(parser)
    output_group = parser.add_argument_group("Output Reports")
    _add_output_path_arguments(output_group)
    _add_model_prompt_generation_arguments(parser)
    _add_runtime_workflow_console_arguments(parser)
    return parser


if __name__ == "__main__":
    main_cli()
