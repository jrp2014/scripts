"""Version and environment reporting tests.

Test that version and environment info is correctly reported in logs and outputs
for reproducibility.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import check_models
import check_models


def test_cli_version_and_env_reporting(tmp_path: Path) -> None:
    output_root = tmp_path / "test_env_reporting"
    derived = check_models.ReportOutputPaths.from_root(output_root)
    env_log = derived.environment

    test_args = [
        "check_models.py",
        "--folder",
        str(tmp_path),
        "--output-dir",
        str(output_root),
    ]

    with patch.object(sys, "argv", test_args), pytest.raises(SystemExit):
        check_models.main_cli()

    # Check that the log file was created and contains version/environment info
    assert env_log.exists()
    content = env_log.read_text(encoding="utf-8").lower()
    assert "python" in content
    assert "mlx" in content or "mlx-vlm" in content
    # Environment dump now uses importlib.metadata (not pip/conda subprocess calls)
    assert "packages" in content or "environment" in content
