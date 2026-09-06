"""Pytest configuration and shared fixtures for test suite.

This module provides:
- Shared fixtures for test images, folders, and paths
- Session-scoped fixtures for expensive resources
- Helper utilities for common test patterns
- Configuration for test markers and plugins

Performance optimizations:
- Session-scoped fixtures avoid repeated setup
- Module-scoped fixtures share resources across tests in same file
- Lazy imports defer heavy module loading
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# =============================================================================
# EARLY ENVIRONMENT SETUP (MUST happen before huggingface_hub imports)
# =============================================================================

# Set up HF cache directory early, before any huggingface_hub functions cache the path.
# Strategy (following HuggingFace documentation):
# 1. If HF_HUB_CACHE is set → use it (user explicitly configured)
# 2. Else if default cache exists (~/.cache/huggingface/hub) → use it
# 3. Else create temp cache (CI environment without cache)
_DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"

# Every worker imports check_models, which imports mlx-vlm in-process anyway;
# the subprocess import probe would only add ~2 s of start-up per worker and,
# with many workers probing at once, contention-driven timeouts.
os.environ.setdefault("CHECK_MODELS_SKIP_IMPORT_PROBE", "1")

# Bytecode never lands inside the tree (the gate exports the same prefix;
# this covers direct `pytest`/`make test` runs and the workers, which import
# this file too). Tests write only to tmp_path for the same reason.
if not os.environ.get("PYTHONPYCACHEPREFIX"):
    _PYCACHE_PREFIX = str(
        Path(tempfile.gettempdir()) / "check_models-quality-pytest-cache" / "pycache"
    )
    os.environ["PYTHONPYCACHEPREFIX"] = _PYCACHE_PREFIX
    sys.pycache_prefix = _PYCACHE_PREFIX

if "HF_HUB_CACHE" not in os.environ and not _DEFAULT_HF_CACHE.exists():
    # CI environment - create temp cache to prevent CacheNotFound
    _temp_hf_cache = Path(tempfile.gettempdir()) / "pytest_hf_cache"
    _temp_hf_cache.mkdir(parents=True, exist_ok=True)
    (_temp_hf_cache / "hub").mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_CACHE"] = str(_temp_hf_cache / "hub")
    os.environ["HF_HOME"] = str(_temp_hf_cache)

# Now import huggingface_hub after environment is configured
import pytest  # noqa: E402 - after HF cache env setup
from huggingface_hub import scan_cache_dir  # noqa: E402 - after HF cache env setup
from huggingface_hub.errors import CacheNotFound  # noqa: E402 - after HF cache env setup
from PIL import Image  # noqa: E402 - after HF cache env setup

import check_models  # noqa: E402 - after HF cache env setup

if TYPE_CHECKING:
    from collections.abc import Generator

# All paths relative to test file locations for portability
TEST_DIR = Path(__file__).parent
SRC_DIR = TEST_DIR.parent


# =============================================================================
# ENVIRONMENT FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def setup_hf_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure HuggingFace cache directory exists for all tests.

    CI environments like GitHub Actions runners may not have the default
    HF cache directory, causing CacheNotFound errors. This fixture creates
    a temporary cache directory for each test.
    """
    cache_dir = tmp_path / "hf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HF_HUB_CACHE", str(cache_dir))
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf_home"))


# =============================================================================
# LOGGING FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_logger_handlers() -> Generator[None]:
    """Reset check_models logger handlers before each test to avoid closed stream issues.

    The check_models module configures its logger with sys.stderr at import time.
    When pytest captures output, the stream may be swapped, causing "I/O operation
    on closed file" errors. This fixture ensures handlers use a fresh stream and
    propagate is enabled for caplog to work correctly.
    """
    # Import lazily to avoid circular imports at module load time
    from check_models import logger  # noqa: PLC0415 - avoid circular import at load

    # Save original state
    original_propagate = logger.propagate
    original_handlers = logger.handlers[:]

    # Enable propagation so caplog can capture records
    logger.propagate = True

    yield

    # After test: restore original state and reset handlers to use current sys.stderr
    logger.propagate = original_propagate
    logger.handlers = original_handlers

    # Ensure handlers use current sys.stderr to prevent "closed file" errors
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.stream = sys.stderr


# =============================================================================
# IMAGE FIXTURES
# =============================================================================


@pytest.fixture
def minimal_test_image(tmp_path: Path) -> Path:
    """Create a minimal valid test image (fastest, for CLI validation tests)."""
    img_path = tmp_path / "minimal.jpg"
    img = Image.new("RGB", (10, 10), color="red")
    img.save(img_path, "JPEG", quality=50)
    return img_path


@pytest.fixture
def test_image(tmp_path: Path) -> Path:
    """Create a small valid test image (100x100, for standard tests)."""
    img_path = tmp_path / "test.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_path, "JPEG", quality=85)
    return img_path


@pytest.fixture
def realistic_test_image(tmp_path: Path) -> Path:
    """Create a realistic test image with visual elements (for E2E tests)."""
    img_path = tmp_path / "realistic.jpg"
    img = Image.new("RGB", (640, 480), color=(135, 206, 235))
    pixels = img.load()
    if pixels:
        for x in range(540, 600):
            for y in range(40, 100):
                if (x - 570) ** 2 + (y - 70) ** 2 < 900:
                    pixels[x, y] = (255, 255, 0)
        for x in range(640):
            for y in range(380, 480):
                pixels[x, y] = (34, 139, 34)
        for x in range(200, 350):
            for y in range(250, 380):
                pixels[x, y] = (139, 90, 43)
        for x in range(180, 370):
            for y in range(200, 250):
                pixels[x, y] = (178, 34, 34)
    img.save(img_path, "JPEG", quality=85)
    return img_path


# =============================================================================
# FOLDER FIXTURES
# =============================================================================


@pytest.fixture
def empty_folder(tmp_path: Path) -> Path:
    """Create an empty folder for testing no-image scenarios."""
    folder = tmp_path / "empty"
    folder.mkdir()
    return folder


@pytest.fixture
def folder_with_images(tmp_path: Path) -> Path:
    """Create a folder with multiple test images (different timestamps)."""
    folder = tmp_path / "images"
    folder.mkdir()

    base_mtime = 1_000_000.0
    for i, name in enumerate(["old.jpg", "middle.jpg", "newest.jpg"]):
        img_path = folder / name
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(img_path)
        os.utime(img_path, (base_mtime + i, base_mtime + i))
    return folder


@pytest.fixture
def folder_with_single_image(tmp_path: Path) -> Path:
    """Create a folder with exactly one image."""
    folder = tmp_path / "single"
    folder.mkdir()
    img_path = folder / "only.jpg"
    img = Image.new("RGB", (50, 50), color="green")
    img.save(img_path)
    return folder


@pytest.fixture(autouse=True)
def _reset_provenance_cache() -> None:
    """Component provenance is memoised per process; tests patch its inputs."""
    check_models._COMPONENT_PROVENANCE_CACHE.clear()


@pytest.fixture(autouse=True)
def _pin_render_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the rendering width every test sees.

    Console rendering derives its width from the terminal; under pytest-xdist
    a worker's stdout is a pipe and the fallback is narrower than in a serial
    run, which silently truncated tree rows and broke exact-string assertions.
    ``MLX_VLM_WIDTH`` is the harness's own override, so this keeps every
    rendering test deterministic regardless of how the suite is invoked.
    """
    monkeypatch.setenv("MLX_VLM_WIDTH", "120")


# =============================================================================
# ENVIRONMENT DETECTION FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def mlx_vlm_available() -> bool:
    """Check if mlx-vlm is available (session-scoped, checked once)."""
    return importlib.util.find_spec("mlx_vlm") is not None


@pytest.fixture(scope="session")
def fixture_model_cached() -> bool:
    """Check if the fixture model (nanoLLaVA) is cached (session-scoped)."""
    fixture_model = "mlx-community/nanoLLaVA-1.5-4bit"
    try:
        repo_ids = [r.repo_id for r in scan_cache_dir().repos]
    except (OSError, ValueError, RuntimeError, CacheNotFound):
        return False
    else:
        return fixture_model in repo_ids


# =============================================================================
# PYTEST HOOKS & CONFIGURATION
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end integration tests")
    config.addinivalue_line("markers", "subprocess: marks tests that spawn subprocesses")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark tests based on their characteristics."""
    for item in items:
        # Auto-mark tests in test_e2e_smoke.py as slow and e2e
        if "test_e2e_smoke" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.e2e)
