"""Test that runtime dependency block in README matches pyproject runtime deps.

This enforces local parity in addition to CI. The test focuses only on runtime deps
(not optional extras groups) and parses dependencies with packaging's PEP 508 parser.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import typing
import zipfile
from pathlib import Path
from textwrap import dedent

import pytest
import yaml
from packaging.requirements import Requirement

import check_models
from check_models_data import dependency_policy
from tools import (
    check_suppressions,
    filter_danger_report,
    quarantine_broken_pip_metadata,
    safe_io,
    update_readme_deps,
    validate_env,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

_TEST_FILE = Path(__file__).resolve()
# tests/ parent, then package root (vlm)
PKG_ROOT = _TEST_FILE.parents[1]
REPO_ROOT = PKG_ROOT.parent


def _write_pip_dist_info(
    site_dir: Path,
    distribution: str,
    version: str,
    *,
    complete: bool,
) -> Path:
    metadata_dir = site_dir / f"{distribution}-{version}.dist-info"
    metadata_dir.mkdir()
    safe_io.write_text_no_follow(metadata_dir / "INSTALLER", "pip\n")
    if complete:
        safe_io.write_text_no_follow(
            metadata_dir / "METADATA",
            f"Name: {distribution}\nVersion: {version}\n",
        )
        safe_io.write_text_no_follow(metadata_dir / "RECORD", "")
    return metadata_dir


def _first_existing(paths: list[Path]) -> Path:
    for p in paths:
        if p.exists():
            return p
    msg = f"None of the candidate paths exist: {paths}"
    raise FileNotFoundError(msg)


PYPROJECT = _first_existing(
    [PKG_ROOT / "pyproject.toml", REPO_ROOT / "pyproject.toml"],
)  # prefer in-package
README = _first_existing(
    [PKG_ROOT / "README.md", REPO_ROOT / "README.md"],
)  # prefer in-package
PACKAGED_QUALITY_CONFIG = PKG_ROOT / "check_models_data" / "quality_config.yaml"
LEGACY_ROOT_QUALITY_CONFIG = PKG_ROOT / "quality_config.yaml"
ROOT_SKYLOS_CONFIG = REPO_ROOT / ".skylos" / "config.yaml"
COPILOT_INSTRUCTIONS = REPO_ROOT / ".github" / "copilot-instructions.md"
AGENT_QUALITY_WORKFLOW = REPO_ROOT / ".agents" / "workflows" / "quality.md"
AGENT_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
# Upstream skill names a local skill may cite as its source (skills/skills/ in
# Blaizzy/mlx-vlm); a cited name outside this set is a typo or a removal.
UPSTREAM_MLX_VLM_SKILLS = frozenset(
    {
        "add-new-model",
        "benchmarking",
        "cli-inference",
        "contributing",
        "convert-quantize",
        "hf-cache-models",
        "reproducible-github-issues",
        "server-inference",
    }
)
SKYLOS_DANGER_ADVISORY_SCRIPT = PKG_ROOT / "tools" / "run_skylos_danger_advisory.sh"
SKYLOS_VERIFY_SCRIPT = PKG_ROOT / "tools" / "run_skylos_verify.sh"

SKYLOS_ADVISORY_QUALITY_IGNORES = {
    "SKY-C401",
    "SKY-L004",
    "SKY-L017",
    "SKY-L026",
    "SKY-L028",
    "SKY-L029",
    "SKY-P403",
    "SKY-Q306",
    "SKY-Q501",
    "SKY-Q502",
    "SKY-Q701",
    "SKY-Q702",
    "SKY-Q802",
    "SKY-Q803",
    "SKY-R104",
}
SKYLOS_MONOLITH_QUALITY_LIMITS = {
    "complexity": 24,
    "nesting": 6,
    "max_lines": 450,
    "duplicate_strings": 40,
}

MANUAL_MARKERS = ("<!-- MANUAL_INSTALL_START -->", "<!-- MANUAL_INSTALL_END -->")

IMPORT_NAME_BY_REQUIREMENT = {
    "huggingface-hub": "huggingface_hub",
    "mlx-vlm": "mlx_vlm",
    "pillow": "PIL",
    "pyyaml": "yaml",
}


def _dependency_key(requirement: Requirement) -> str:
    extras = f"[{','.join(sorted(requirement.extras))}]" if requirement.extras else ""
    return f"{requirement.name}{extras}"


def _dependency_spec(requirement: Requirement) -> str:
    marker = f"; {requirement.marker}" if requirement.marker else ""
    return f"{requirement.specifier}{marker}"


def _parse_runtime_deps(text: str) -> dict[str, str]:
    data = tomllib.loads(text)
    # project.dependencies is a list of strings
    deps_list = data.get("project", {}).get("dependencies", [])

    deps: dict[str, str] = {}
    for line in deps_list:
        requirement = Requirement(line)
        deps[_dependency_key(requirement)] = _dependency_spec(requirement)
    return deps


def _extract_manual_block(readme: str) -> str:
    start, end = MANUAL_MARKERS
    pattern = re.compile(rf"{re.escape(start)}(.*?){re.escape(end)}", re.DOTALL)
    m = pattern.search(readme)
    if not m:
        msg = "Manual install markers not found in README.md"
        raise RuntimeError(msg)
    return m.group(1)


def test_safe_io_read_text_no_follow_rejects_symlinked_file(tmp_path: Path) -> None:
    """Maintenance-tool text reads should not follow attacker-swapped symlinks."""
    target_path = tmp_path / "target.txt"
    target_path.write_text("safe text", encoding="utf-8")
    symlink_path = tmp_path / "link.txt"
    symlink_path.symlink_to(target_path)

    with pytest.raises(OSError, match="Refusing to follow symlink"):
        safe_io.read_text_no_follow(symlink_path)


def test_safe_io_read_text_no_follow_enforces_byte_cap(tmp_path: Path) -> None:
    """Maintenance-tool text reads should reject unexpectedly large files."""
    text_path = tmp_path / "large.txt"
    text_path.write_text("abcdef", encoding="utf-8")

    with pytest.raises(OSError, match=r"exceeds 3 bytes"):
        safe_io.read_text_no_follow(text_path, max_bytes=3)


def test_readme_runtime_block_matches_pyproject() -> None:
    """Ensure the runtime dependencies in README match pyproject.toml."""
    py_text = PYPROJECT.read_text(encoding="utf-8")
    rd_text = README.read_text(encoding="utf-8")
    runtime_deps = _parse_runtime_deps(py_text)

    manual_block = _extract_manual_block(rd_text)
    # Pull quoted specs from pip install line
    quoted = re.findall(r'"([^"]+)"', manual_block)
    if not quoted:
        msg = "No quoted packages found in manual install block"
        raise RuntimeError(msg)

    seen: dict[str, str] = {}
    for q in quoted:
        requirement = Requirement(q)
        seen[_dependency_key(requirement)] = _dependency_spec(requirement)

    # All runtime deps must exist
    missing = [k for k in runtime_deps if k not in seen]
    if missing:
        msg = f"Runtime deps missing from README: {missing}"
        raise RuntimeError(msg)

    # No extras should leak (heuristic: check optional groups defined later if needed)
    forbidden = {
        "psutil",
        "tokenizers",
        "torch",
        "torchvision",
        "torchaudio",
    }
    leaked = sorted(forbidden & set(seen))
    if leaked:
        msg = f"Optional deps leaked into runtime block: {leaked}"
        raise RuntimeError(msg)


def test_update_readme_deps_fallback_parser_without_packaging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dependency sync should run before project dependencies are installed."""
    monkeypatch.setattr(update_readme_deps, "_Requirement", None)

    assert update_readme_deps._parse_requirement("Pillow[xmp]>=10.3.0") == (
        "Pillow[xmp]",
        ">=10.3.0",
    )
    assert update_readme_deps._parse_requirement(
        "huggingface-hub[typing, torch]>=1.10.1",
    ) == ("huggingface-hub[torch,typing]", ">=1.10.1")

    groups = update_readme_deps.extract_optional_groups(
        """
        [project]
        dependencies = []

        [project.optional-dependencies]
        extras = ["tokenizers>=0.15.0", "Pillow[xmp]>=10.3.0"]
        """,
    )

    assert groups == {"extras": ["tokenizers", "Pillow"]}


def test_dependency_policy_module_tracks_pyproject_stack_floors() -> None:
    """Shared dependency policy should stay aligned with declared packaging metadata."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime_deps = pyproject["project"]["dependencies"]
    extras_deps = pyproject["project"]["optional-dependencies"]["extras"]

    assert f"mlx>={dependency_policy.PROJECT_RUNTIME_STACK_MINIMUMS['mlx']}" in runtime_deps
    assert f"mlx-vlm>={dependency_policy.PROJECT_RUNTIME_STACK_MINIMUMS['mlx-vlm']}" in runtime_deps
    assert f"transformers{dependency_policy.PROJECT_TRANSFORMERS_VERSION_SPEC}" in runtime_deps
    assert (
        f"huggingface-hub[typing]>={dependency_policy.PROJECT_RUNTIME_STACK_MINIMUMS['huggingface-hub']}"
        in runtime_deps
    )
    # mlx-lm is neither imported nor required by mlx-vlm any more: nowhere.
    assert not any(dep.startswith("mlx-lm") for dep in runtime_deps + extras_deps)


def _normalized_requirement_names(requirements: Iterable[str]) -> set[str]:
    return {
        re.split(r"[\[<>=!~; ]", requirement, maxsplit=1)[0].strip().lower().replace("_", "-")
        for requirement in requirements
    }


def test_validate_env_fallback_matches_declared_runtime_dependencies() -> None:
    """The no-pyproject fallback must check exactly the declared hard runtime set.

    It exists for the case where pyproject.toml cannot be loaded, so a stale
    literal there would flag removed packages as missing while overlooking
    genuinely missing ones (as happened when wcwidth was retired).
    """
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared = _normalized_requirement_names(pyproject["project"]["dependencies"])
    fallback = _normalized_requirement_names(dependency_policy.VALIDATE_ENV_CORE_FALLBACK_SPECS)
    assert fallback == declared


def test_dependency_policy_tracks_current_upstream_transformers_floor() -> None:
    """The project floor tracks the released mlx-vlm stack (0.6.16, first py.typed)."""
    assert dependency_policy.PROJECT_RUNTIME_STACK_MINIMUMS["transformers"] == "5.14.0"
    assert dependency_policy.UPSTREAM_MLX_VLM_MINIMUMS["transformers"] == "5.14.0"


def test_dependency_policy_does_not_cap_transformers() -> None:
    """Transformers should retain its floor without an upper version bound."""
    assert dependency_policy.PROJECT_TRANSFORMERS_VERSION_SPEC == ">=5.14.0"


def test_pillow_floor_uses_security_fixed_release() -> None:
    """Pillow's declared floor should exclude vulnerabilities fixed in 12.3.0."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert dependency_policy.PROJECT_PILLOW_MINIMUM_VERSION == "12.3.0"
    assert (
        f"Pillow[xmp]>={dependency_policy.PROJECT_PILLOW_MINIMUM_VERSION}"
        in pyproject["project"]["dependencies"]
    )
    assert (
        dependency_policy.VALIDATE_ENV_CORE_FALLBACK_SPECS["Pillow"]
        == f">={dependency_policy.PROJECT_PILLOW_MINIMUM_VERSION}"
    )


def test_ty_quality_check_resolves_gitignored_generated_stubs() -> None:
    """Ty must not exclude the configured typings path merely because Git ignores it."""
    common_quality = (PKG_ROOT / "tools" / "common_quality.sh").read_text(encoding="utf-8")

    assert 'check --no-respect-ignore-files --python "$python_path"' in common_quality


def test_pyrefly_quality_check_passes_explicit_targets() -> None:
    """Pyrefly must run in single-file mode, not project discovery.

    Explicit targets enumerated via ``git ls-files`` bypass Pyrefly's
    filesystem discovery entirely, so the gate's file set cannot be eaten by
    parent-repo ignore files or future discovery heuristics. This is the
    second layer of the worktree defense; the generated config additionally
    neutralizes the known discovery pitfalls (see the companion generated-
    config test).
    """
    common_quality = (PKG_ROOT / "tools" / "common_quality.sh").read_text(encoding="utf-8")

    assert "quality_pyrefly_default_targets" in common_quality
    assert (
        'git -C "$(quality_src_root)" ls-files --cached --others --exclude-standard'
        in common_quality
    )
    assert '"${targets[@]}" 2>&1 | tee "$output_path"' in common_quality


def test_mypy_uses_generated_typings_without_gating_stub_internals() -> None:
    """Generated third-party stubs should inform call sites, not fail strict checks."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    overrides = pyproject["tool"]["mypy"]["overrides"]

    generated_overrides = [
        override
        for override in overrides
        if set(override.get("module", []))
        & {
            "mlx_vlm",
            "mlx_vlm.*",
            "tokenizers",
            "tokenizers.*",
            "transformers",
            "transformers.*",
        }
    ]

    assert generated_overrides
    for override in generated_overrides:
        assert override["ignore_errors"] is True


def test_root_makefile_exposes_documented_maintenance_targets() -> None:
    """Contributor docs should be able to use maintenance targets from repo root."""
    root_makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    for target in ("check-outdated", "audit", "clean-mlx", "clean-mlx-dry-run"):
        assert f".PHONY: {target}" in root_makefile
        assert f"{target}:" in root_makefile


def test_dependency_docs_do_not_reference_removed_lockfile_workflows() -> None:
    """Live docs should not point contributors at removed requirements/lock workflows."""
    live_docs = {
        "implementation": (REPO_ROOT / "docs" / "IMPLEMENTATION_GUIDE.md").read_text(
            encoding="utf-8"
        ),
        "contributing": (REPO_ROOT / "docs" / "CONTRIBUTING.md").read_text(encoding="utf-8"),
        "src_makefile": (PKG_ROOT / "Makefile").read_text(encoding="utf-8"),
    }
    removed_phrases = (
        "CI uses lock files",
        "compatible with lock files",
        "make sync-deps",
        "make upgrade-deps",
        "src/requirements.txt",
        "requirements-dev.txt",
        "make -C vlm",
    )

    for doc_name, text in live_docs.items():
        for phrase in removed_phrases:
            assert phrase not in text, (doc_name, phrase)


def test_root_readme_describes_supported_cache_filter() -> None:
    """The quick README should match the detailed supported-cache discovery docs."""
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "server-supported cache filter" in root_readme
    assert "all models found in your local HF cache" not in root_readme


def test_package_skylos_scan_excludes_generated_artifacts() -> None:
    """Package-local Skylos config should scan maintained source, not generated outputs."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    skylos_config = pyproject["tool"]["skylos"]
    skylos_gate = skylos_config["gate"]

    assert "addopts" not in skylos_config

    excludes = set(skylos_config["exclude"])
    assert {
        "output",
        "package-lock.json",
        "node_modules",
        "build",
        "dist",
        "*.egg-info",
        "check_models.suppression-audit*.py",
    } <= excludes
    assert set(skylos_config["ignore"]) >= SKYLOS_ADVISORY_QUALITY_IGNORES
    for key, value in SKYLOS_MONOLITH_QUALITY_LIMITS.items():
        assert skylos_config[key] == value
    assert skylos_gate == {
        "fail_on_critical": True,
        "max_critical": 0,
        "max_high": 0,
        "max_security": 0,
        "max_quality": 0,
        "strict": False,
    }


def test_root_skylos_config_mirrors_package_quality_policy() -> None:
    """Repo-root scans should use the same advisory quality calibration as package scans."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    package_config = pyproject["tool"]["skylos"]
    root_config = yaml.safe_load(ROOT_SKYLOS_CONFIG.read_text(encoding="utf-8"))

    assert isinstance(root_config, dict)
    assert {
        "output",
        "src/output",
        "package-lock.json",
        "node_modules",
        "build",
        "dist",
        "*.egg-info",
        "src/check_models.suppression-audit*.py",
        # Third-party checkouts and agent worktrees must never gate this repo.
        ".worktrees",
        ".claude",
    } <= set(root_config["exclude"])
    assert set(root_config["ignore"]) == set(package_config["ignore"])
    for key in SKYLOS_MONOLITH_QUALITY_LIMITS:
        assert root_config[key] == package_config[key]
    assert root_config["gate"] == package_config["gate"]


def test_ruff_uses_current_floor_and_all_stable_rules() -> None:
    """Every stable rule shipped by the supported Ruff release should be selected."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    ruff_config = pyproject["tool"]["ruff"]
    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]

    assert "ruff>=0.16.0" in dev_deps
    assert ruff_config["required-version"] == ">=0.16.0"
    assert ruff_config["lint"]["select"] == ["ALL"]

    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")
    assert '"ruff>=0.16.0"' in setup_script


def test_conda_setup_verifier_imports_declared_non_dev_dependencies() -> None:
    """The fresh setup smoke check should only import packages it just installed."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")
    verifier_match = re.search(r'python -c "\n(.*?)\n"', setup_script, re.DOTALL)
    assert verifier_match is not None

    declared_requirements = [
        *pyproject["project"]["dependencies"],
        *pyproject["project"]["optional-dependencies"]["extras"],
        *pyproject["project"]["optional-dependencies"]["torch"],
    ]
    declared_imports = {
        IMPORT_NAME_BY_REQUIREMENT.get(requirement.name.lower(), requirement.name.replace("-", "_"))
        for requirement_text in declared_requirements
        for requirement in [Requirement(requirement_text)]
    }
    imported_modules = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(ast.parse(verifier_match.group(1)))
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert imported_modules <= declared_imports


def test_conda_setup_verifies_mlx_backend_pair() -> None:
    """Fresh setup should fail fast on mismatched or missing MLX Metal artifacts."""
    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")

    assert "metadata.version('mlx-metal')" in setup_script
    assert "mlx/mlx-metal version mismatch" in setup_script
    assert "mlx.metallib" in setup_script
    assert "MLX Metal library missing" in setup_script
    assert "MLX editable install detected" in setup_script


def test_conda_setup_uses_current_huggingface_cli_installation() -> None:
    """Avoid installing removed huggingface-hub extras on any bootstrap path."""
    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")

    assert '"huggingface_hub[cli]"' not in setup_script
    assert "command -v hf" in setup_script

    makefile = (PKG_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "huggingface_hub[cli]" not in makefile


@pytest.mark.subprocess
def test_common_quality_finds_conda_executable_without_sourcing_conda_sh(tmp_path: Path) -> None:
    """Quality helpers should resolve conda directly instead of sourcing conda.sh."""
    fake_conda = tmp_path / "miniconda3" / "bin" / "conda"
    fake_conda.parent.mkdir(parents=True)
    fake_conda.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_conda.chmod(0o755)

    output_path = tmp_path / "conda-bin.txt"
    run_script = tmp_path / "check_common_quality_conda_bin.sh"
    run_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            export HOME="{tmp_path}"
            export PATH=/usr/bin:/bin
            source "{PKG_ROOT / "tools" / "common_quality.sh"}"
            quality_find_conda_bin > "{output_path}"
            """
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-created script
        ["/bin/bash", str(run_script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=PKG_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert output_path.read_text(encoding="utf-8").strip() == str(fake_conda)


@pytest.mark.subprocess
def test_common_quality_rejects_local_python_fallback_without_override(tmp_path: Path) -> None:
    """Local quality runs should fail instead of silently using PATH python."""
    run_script = tmp_path / "reject_python_fallback.sh"
    run_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            unset CONDA_PREFIX
            unset CONDA_DEFAULT_ENV
            unset CI
            export HOME="{tmp_path}"
            export PATH=/usr/bin:/bin
            source "{PKG_ROOT / "tools" / "common_quality.sh"}"
            if quality_setup_python > "{tmp_path / "stdout.txt"}" 2> "{tmp_path / "stderr.txt"}"; then
                exit 44
            fi
            grep -q "Unable to resolve required conda environment" "{tmp_path / "stderr.txt"}"
            """
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-created script
        ["/bin/bash", str(run_script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=PKG_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.subprocess
def test_common_quality_python_tools_do_not_fall_back_to_path_by_default(tmp_path: Path) -> None:
    """Python tools should resolve from the chosen interpreter's bin directory."""
    env_bin = tmp_path / "env" / "bin"
    path_bin = tmp_path / "path-bin"
    env_bin.mkdir(parents=True)
    path_bin.mkdir()
    fake_python = env_bin / "python"
    fake_python.symlink_to(Path(sys.executable).resolve())
    fake_path_tool = path_bin / "ty"
    fake_path_tool.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_path_tool.chmod(0o755)

    run_script = tmp_path / "reject_path_tool_fallback.sh"
    run_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            cd "{PKG_ROOT}"
            export PATH="{path_bin}:/usr/bin:/bin"
            source tools/common_quality.sh
            QUALITY_PYTHON="{fake_python}"
            QUALITY_PYTHON_SOURCE="conda-env:mlx-vlm"
            export QUALITY_PYTHON QUALITY_PYTHON_SOURCE
            if quality_find_python_tool ty > "{tmp_path / "tool.txt"}"; then
                exit 44
            fi
            """
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-created script
        ["/bin/bash", str(run_script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=PKG_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_conda_setup_uses_conda_executable_without_sourcing_conda_sh() -> None:
    """Setup should use conda directly and avoid dynamic conda.sh sourcing."""
    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")

    assert "source_conda_sh" not in setup_script
    assert "conda info --base" not in setup_script
    assert 'conda activate "$ENV_NAME"' not in setup_script
    assert "conda_cmd()" in setup_script
    assert "activate_environment_path()" in setup_script


def test_clean_builds_uses_static_help_and_guarded_direct_child_removal() -> None:
    """Cleanup tooling should avoid self-read help and unguarded direct-child rm calls."""
    clean_script = (PKG_ROOT / "tools" / "clean_builds.sh").read_text(encoding="utf-8")

    assert 'head -n 17 "$0"' not in clean_script
    assert "show_help()" in clean_script
    assert "remove_direct_child_dir()" in clean_script
    assert 'rm -rf "${dir:?}/$pattern"' not in clean_script
    assert "sudo rm -rf" not in clean_script


def test_packaged_quality_config_is_the_only_default_source() -> None:
    """The packaged config should be the sole checked-in default copy."""
    assert PACKAGED_QUALITY_CONFIG.exists()
    assert not LEGACY_ROOT_QUALITY_CONFIG.exists()


@pytest.mark.subprocess
def test_built_wheel_includes_packaged_quality_config(tmp_path: Path) -> None:
    """Built wheels should ship the packaged default quality config."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    # Build from a copy: setuptools writes build/ and *.egg-info next to the
    # sources. Those are not throwaway caches: a stale egg-info changes what
    # importlib.metadata reports for the package, and build/ holds a second
    # copy of the sources that the static checkers would scan.
    source_copy = tmp_path / "src"
    shutil.copytree(
        PKG_ROOT,
        source_copy,
        ignore=shutil.ignore_patterns(
            ".*",
            "__pycache__",
            "build",
            "dist",
            "*.egg-info",
            "node_modules",
            "output",
            "tests",
            "typings",
        ),
    )

    # Standard PEP 517 build: pip provisions the declared [build-system]
    # requirements in an isolated environment, so this passes or fails on the
    # checked-in packaging metadata alone, never on whatever happens to be
    # installed around it (a transitive setuptools once masked exactly that).
    result = subprocess.run(  # noqa: S603 - fixed interpreter builds the checked-in package
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--wheel-dir",
            str(dist_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=source_copy,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    wheel_paths = sorted(dist_dir.glob("check_models-*.whl"))
    assert len(wheel_paths) == 1

    with zipfile.ZipFile(wheel_paths[0]) as archive:
        assert "check_models_data/quality_config.yaml" in archive.namelist()


def test_markdownlint_cli2_is_repo_local_uncapped_and_updateable() -> None:
    """Keep markdownlint-cli2 aligned between npm metadata and update tooling.

    Policy: the spec is a caret range (not an exact pin) and update.sh can move
    to the latest release. The lockfile is deliberately untracked, so it is
    only cross-checked when a local `npm install` has produced one.
    """
    package_json = json.loads((PKG_ROOT / "package.json").read_text(encoding="utf-8"))

    markdownlint_spec = package_json["devDependencies"]["markdownlint-cli2"]
    assert markdownlint_spec.startswith("^"), "markdownlint-cli2 must stay uncapped (caret range)"
    # No repo-scoped npm scripts: the canonical markdownlint invocation lives in
    # tools/run_quality_checks.sh; a second spelling here would drift.
    assert "scripts" not in package_json

    lock_path = PKG_ROOT / "package-lock.json"
    if lock_path.exists():
        package_lock = json.loads(lock_path.read_text(encoding="utf-8"))
        assert (
            markdownlint_spec
            == package_lock["packages"][""]["devDependencies"]["markdownlint-cli2"]
        )
        locked_version = package_lock["packages"]["node_modules/markdownlint-cli2"]["version"]
        assert locked_version, "lockfile must resolve markdownlint-cli2"
        # The security override for the transitive smol-toml stays pinned and synced.
        assert (
            package_lock["packages"]["node_modules/smol-toml"]["version"]
            == package_json["overrides"]["smol-toml"]
        )

    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    assert 'npm install --ignore-scripts --no-audit --no-fund --prefix "$PROJECT_ROOT"' in (
        update_script
    )
    assert (
        'npm install --no-audit --no-fund --prefix "$PROJECT_ROOT" --save-dev markdownlint-cli2@latest'
        in update_script
    )
    assert "--save-exact" not in update_script
    assert update_script.index("markdownlint-cli2@latest") > update_script.index(
        "UPDATE_NODE_TOOLING"
    )


def test_generated_markdown_lint_guards_use_named_rule_sets() -> None:
    """Report-specific markdownlint guards should stay centralized."""
    source = (PKG_ROOT / "check_models.py").read_text(encoding="utf-8")

    # Behavioural checks on the live constants; exact source spelling is not
    # asserted so harmless refactors (annotation style, quoting) stay legal.
    assert check_models.MARKDOWNLINT_GALLERY_SUMMARY_RULES == "MD034 MD037 MD049"
    assert check_models.MARKDOWNLINT_TABLE_PIPE_RULES == "MD060"
    assert "MARKDOWNLINT_MAIN_TABLE_RULES" not in source
    assert "MARKDOWNLINT_DETAILS_RULES" not in source
    assert "<!-- markdownlint-disable MD033 MD034 MD037 MD049 -->" not in source
    assert "<!-- markdownlint-enable MD033 MD034 MD037 MD049 -->" not in source
    assert "<!-- markdownlint-disable MD034 -->" not in source
    assert "<!-- markdownlint-enable MD034 -->" not in source


def test_agent_quality_guidance_avoids_redundant_pytest_after_quality() -> None:
    """Agent-facing workflow docs should treat make quality as the full pytest gate."""
    copilot_text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    quality_workflow = AGENT_QUALITY_WORKFLOW.read_text(encoding="utf-8")

    assert "full pytest" in copilot_text
    assert "Do not run it again after a successful `make quality`" in copilot_text
    assert "make skylos-danger" in copilot_text
    assert "make skylos-danger-llm" in copilot_text
    assert "make skylos-verify" in copilot_text
    assert "runs blocking inside `make quality`" in copilot_text
    assert "`make quality` already runs the full pytest suite" in quality_workflow
    assert "make skylos-danger-llm" in quality_workflow
    assert "make skylos-verify" in quality_workflow
    assert "`make test` — execute unit tests" not in copilot_text


def test_agent_monolith_size_note_matches_current_file() -> None:
    """Agent-facing file map should not drift badly from the monolith size."""
    copilot_text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    source_lines = len((PKG_ROOT / "check_models.py").read_text(encoding="utf-8").splitlines())
    match = re.search(
        r"`src/check_models\.py` \| \*\*Single-file CLI monolith\*\* \(~([\d,]+) lines\)",
        copilot_text,
    )

    assert match is not None
    documented_lines = int(match.group(1).replace(",", ""))
    assert abs(source_lines - documented_lines) <= 500


def test_output_artifact_policy_is_documented_and_gitignored() -> None:
    """Generated output docs should match the repo ignore policy."""
    readme = README.read_text(encoding="utf-8")
    gitignore_lines = {
        line.strip() for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }

    for phrase in (
        "production Markdown reports are linted by the quality gate",
        "use the `test_` prefix",
        "do not commit ad-hoc debug output",
    ):
        assert phrase in readme

    assert {
        "src/output/test_*",
        "src/output/reports/test_*",
        "src/output/issues/test_*",
        # The append-only history is deliberately untracked.
        "src/output/results.history.jsonl",
    }.issubset(gitignore_lines)


def test_readme_documents_only_the_simplified_report_contract() -> None:
    """Public output documentation should expose only retained report artifacts."""
    readme = README.read_text(encoding="utf-8")

    for artifact in (
        "reports/diagnostics.md",
        "reports/model_gallery.md",
        "reports/results.html",
        "results.jsonl",
        "index.md",
        "check_models.log",
        "environment.log",
        "results.history.jsonl",
    ):
        assert f"`{artifact}`" in readme

    for retired in (
        "results.md",
        "results.tsv",
        "review.md",
        "model_selection.md",
        "model_capabilities.md",
        "model_capabilities.json",
        "repro_bundles",
        "--output-markdown",
        "--output-review",
        "--output-model-selection",
        "--output-model-capabilities",
        "--output-model-capabilities-json",
        "--output-tsv",
    ):
        assert retired not in readme

    for vocabulary in (
        "`execution`: `completed`, `crashed`, or `indeterminate`",
        "`usability`: `usable`, `usable_with_caveats`, `unusable`, or `not_evaluated`",
        ("`maintainer_status`: `actionable_failure`, `observation_needs_reproduction`, or `none`"),
    ):
        assert vocabulary in readme


def test_readme_documents_facts_first_evidence_boundaries() -> None:
    """Public docs should explain neutral, weak, and indeterminate evidence."""
    readme = README.read_text(encoding="utf-8")

    for phrase in (
        "Complete model output is retained as evidence",
        "Crashes prioritize the complete traceback",
        "Reaching the configured token cap alone is neutral",
        "Long complete output is not a fault",
        "task compliance not assessed",
        "Length ranges are no longer inferred from prose",
        "External connectivity failures are `indeterminate`",
        "Configured thinking tokens are not automatically faults",
        "explicit `eos_tokens`",
        "no model-name allowlist",
        "EXIF timestamps are interpreted as capture wall clocks",
        "`First`, `Remain`, `Clean`, `Total`, `TPS`, and `GB`",
        "combines image\nand other input preparation with token decoding",
        "`insufficient sample`",
        "Issue drafts are created only for hard actionable crashes",
        "append-only raw history",
    ):
        assert phrase in readme


def test_validation_artifact_hygiene_policy_is_documented() -> None:
    """Validation guidance should forbid dirtying tracked benchmark assets."""
    required_phrase = "Validation tests must not rewrite tracked `src/output/` assets"

    docs = {
        "copilot instructions": COPILOT_INSTRUCTIONS.read_text(encoding="utf-8"),
        "agent instructions": (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        "claude instructions": (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
        "quality workflow": (REPO_ROOT / ".github" / "workflows" / "quality.yml").read_text(
            encoding="utf-8"
        ),
        "contributor guide": (REPO_ROOT / "docs" / "CONTRIBUTING.md").read_text(encoding="utf-8"),
        "cli readme": (PKG_ROOT / "README.md").read_text(encoding="utf-8"),
    }

    for label, text in docs.items():
        assert required_phrase in text, label

    for label, text in docs.items():
        assert "temp directory" in text, label


def test_canonical_agent_guidance_orders_matrix_acceptance_after_quality() -> None:
    """Costly matrices must follow deterministic tests and use a valid Run 1 baseline."""
    guidance = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    for phrase in (
        "Before a costly real-model matrix",
        "deterministic\n  focused tests",
        "full `make quality`",
        "not as substitutes for ordinary tests",
        "rerun and audit Run 1",
        "before starting comparative Run 2",
        "Never compare a known-invalid baseline",
    ):
        assert phrase in guidance


def test_canonical_agent_guidance_requires_generated_markdown_preflight() -> None:
    """Generated reports should satisfy repository Markdown style before a matrix."""
    guidance = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    for phrase in (
        "Emit generated Markdown in the repository's markdownlint style directly",
        "blank lines around headings and lists",
        "unique headings or an explicitly configured sibling-heading structure",
        "asterisks rather than underscores for emphasis",
        "preserve model text, tabs, and trailing spaces",
        "proper blank-line spacing and a language identifier",
        "narrow report-local markdownlint configuration",
        "escape table-cell content",
        "representative reports from fixtures",
        "temporary or `test_*` output paths",
        "run markdownlint before the expensive matrix",
        "must not need post-run hand editing",
        "shared render helpers and focused tests",
        "supported report-only regeneration path",
        "existing canonical JSONL",
        "before Run 1",
    ):
        assert phrase in guidance


def test_production_assessment_policy_has_no_fixture_specific_exceptions() -> None:
    """Policy feeders must not embed benchmark model, image, or location literals."""
    source = (PKG_ROOT / "check_models.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    string_literals = {
        node.value.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert not any(re.fullmatch(r"org/[a-z0-9_-]+", value) for value in string_literals)
    assert string_literals.isdisjoint(
        {
            "granite",
            "pink couch",
            "tabby",
            "brick storefront",
            "harbor sunset",
            "remote controls",
            "deben estuary",
            "woodbridge",
            "welwyn garden city",
        }
    )

    config = yaml.safe_load(PACKAGED_QUALITY_CONFIG.read_text(encoding="utf-8"))
    assert set(config) == {"thresholds"}
    assert "min_keywords_for_duplication_check" not in config["thresholds"]


def test_python_sources_write_variation_selectors_as_escapes() -> None:
    r"""Raw U+FE0F must appear only via the \ufe0f escape in Python sources.

    CodeQL's tsg-python extractor mis-slices emoji variation selectors while
    evaluating string literals in any file containing PEP 695 syntax; when the
    same literal carries a %-format directive the extractor's error reporter
    crashes and the whole file is silently dropped from security analysis.
    Writing the selector as an escape keeps the rendered glyph identical while
    the source stays ASCII at that position.
    """
    excluded_parts = {".worktrees", "build", "output", "check_models.egg-info"}
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted(REPO_ROOT.glob("src/**/*.py"))
        if not excluded_parts.intersection(path.parts)
        and "\ufe0f" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], offenders


def test_quality_script_runs_skylos_quality_gate() -> None:
    """Local quality checks should include the calibrated Skylos quality gate."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
    quality_script = (PKG_ROOT / "tools" / "run_quality_checks.sh").read_text(encoding="utf-8")
    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")

    skylos_specs = [dep for dep in dev_deps if dep.startswith("skylos")]
    assert len(skylos_specs) == 1
    # The setup script must install the same spec pyproject declares,
    # whatever that spec is (deliberately not pinned).
    assert f'"{skylos_specs[0]}"' in setup_script
    assert (
        'quality_require_python_tool skylos "Install dev dependencies with: pip install -e .[dev]"'
        in quality_script
    )
    assert 'echo "=== Skylos Quality Gate ==="' in quality_script
    assert 'echo "=== Skylos Audit Gate ==="' in quality_script
    assert "SKYLOS_JOBS" not in quality_script
    # The danger scan is deliberately blocking in full mode, and only via the
    # wrapper script (never a bare `skylos --danger` that would bypass the
    # worktree post-filter and non-interactive guards).
    assert 'bash "$SCRIPT_DIR/run_skylos_danger_advisory.sh" --full --gate' in quality_script
    assert "skylos . --danger" not in quality_script
    # One markdownlint step (with the worktree exclusion) serves both modes:
    # one definition plus one call in fast mode and one in full mode.
    assert quality_script.count('"!**/.worktrees/**"') == 1
    assert quality_script.count("run_markdownlint_step") == 3
    # Skylos runs before pytest, never concurrently: its grep verification
    # aborts when files appear or vanish under it.
    assert quality_script.index('echo "=== Skylos Quality Gate ==="') < quality_script.index(
        'echo "=== Pytest ==="'
    )
    assert re.search(
        r"TERM=dumb NO_COLOR=1 CLICOLOR=0 FORCE_COLOR=0 PY_COLORS=0\s+\\?\s*"
        r"quality_run_skylos \. --quality --secrets --sca --gate --no-upload "
        r"--format concise",
        quality_script,
    )
    assert re.search(
        r"TERM=dumb NO_COLOR=1 CLICOLOR=0 FORCE_COLOR=0 PY_COLORS=0\s+\\?\s*"
        r"quality_run_skylos \. -a",
        quality_script,
    )


def test_skylos_danger_advisory_script_is_separate_and_agent_friendly() -> None:
    """Advisory Skylos danger scans should stay separate from the blocking quality gate."""
    script = SKYLOS_DANGER_ADVISORY_SCRIPT.read_text(encoding="utf-8")

    assert "--danger --json" in script
    assert "skylos cicd annotate" in script
    assert "--severity medium" in script
    assert "cicd gate" in script
    assert "--advisory" in script
    assert "--llm" in script
    assert ".skylos/skylos-danger-advisory.llm.txt" in script


@pytest.mark.subprocess
def test_skylos_danger_scan_excludes_third_party_worktrees(tmp_path: Path) -> None:
    """The real wrapper must pass its worktree exclusion to the scanner process."""
    repo_root = tmp_path / "repo"
    tools_dir = repo_root / "src" / "tools"
    tools_dir.mkdir(parents=True)
    script = tools_dir / SKYLOS_DANGER_ADVISORY_SCRIPT.name
    script.write_bytes(SKYLOS_DANGER_ADVISORY_SCRIPT.read_bytes())
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    for helper_name in ("filter_danger_report.py", "safe_io.py"):
        helper = PKG_ROOT / "tools" / helper_name
        (tools_dir / helper_name).write_bytes(helper.read_bytes())
    call_log = tmp_path / "skylos-calls.log"
    (tools_dir / "common_quality.sh").write_text(
        dedent(
            """\
            quality_repo_root() { printf '%s\\n' "$TEST_REPO_ROOT"; }
            quality_setup_python() {
                QUALITY_PYTHON="$TEST_PYTHON"
                export QUALITY_PYTHON
            }
            quality_require_python_tool() { return 0; }
            quality_run_python_tool() {
                printf '%s\\n' "$*" >> "$TEST_CALL_LOG"
                shift
                while [ "$#" -gt 0 ]; do
                    if [ "$1" = "-o" ]; then
                        printf '{"danger":[]}\\n' > "$2"
                        break
                    fi
                    shift
                done
            }
            quality_run_skylos() { quality_run_python_tool skylos "$@"; }
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-copied script
        ["/bin/bash", str(script), "--full", "--gate"],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root,
        env={
            **os.environ,
            "TEST_REPO_ROOT": str(repo_root),
            "TEST_PYTHON": sys.executable,
            "TEST_CALL_LOG": str(call_log),
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    scan_call = next(
        line for line in call_log.read_text().splitlines() if "--danger --json" in line
    )
    assert "--exclude .worktrees" in scan_call


def test_skylos_verify_script_wraps_repo_context_verifier() -> None:
    """The Skylos verify helper should keep agent checks repo-scoped and deterministic."""
    script = SKYLOS_VERIFY_SCRIPT.read_text(encoding="utf-8")

    assert "Usage: bash tools/run_skylos_verify.sh" in script
    assert 'cd "$(quality_repo_root)"' in script
    assert "quality_require_python_tool skylos" in script
    assert 'quality_run_skylos verify . --project-context "$@"' in script


def test_defusedxml_probe_is_a_real_import_without_suppression() -> None:
    """Defusedxml is bound as a nullable module: scanner-visible, no lint suppression.

    A bare ``find_spec`` probe hid the dependency from static dependency
    scanners (SKY-U005 false positive), while a plain guarded import needed an
    F401 suppression. Binding the module (the psutil pattern) satisfies both.
    """
    check_models_source = (PKG_ROOT / "check_models.py").read_text(encoding="utf-8")
    defusedxml_probe = check_models_source[
        check_models_source.index("defusedxml is required") : check_models_source.index(
            "try:\n    import numpy as np",
        )
    ]

    assert "import defusedxml.ElementTree as _DefusedElementTree" in defusedxml_probe
    assert "defusedxml_etree = _DefusedElementTree" in defusedxml_probe
    assert 'find_spec("defusedxml.ElementTree")' not in defusedxml_probe
    assert "F401" not in defusedxml_probe
    assert "noqa" not in defusedxml_probe
    assert check_models._defusedxml_available is (check_models.defusedxml_etree is not None)


@pytest.mark.subprocess
def test_pyrefly_quality_gate_fails_on_warnings(tmp_path: Path) -> None:
    """The quality helper should treat Pyrefly warnings as gate failures."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_python = fake_bin / "python"
    fake_python.symlink_to(Path(sys.executable).resolve())

    fake_pyrefly = fake_bin / "pyrefly"
    fake_pyrefly.write_text(
        dedent(
            """\
            #!/usr/bin/env bash
            echo ' INFO Checking project configured at `fake`'
            echo ' WARN synthetic warning [test-warning]'
            echo ' INFO 0 errors'
            exit 0
            """
        ),
        encoding="utf-8",
    )
    fake_pyrefly.chmod(0o755)

    output_log = tmp_path / "pyrefly.log"
    run_script = tmp_path / "run_pyrefly_gate.sh"
    run_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            cd \"{PKG_ROOT}\"
            source tools/common_quality.sh
            QUALITY_PYTHON=\"{fake_python}\"
            QUALITY_PYTHON_SOURCE=\"synthetic-test\"
            if quality_run_pyrefly_check > \"{output_log}\" 2>&1; then
                pyrefly_gate_status=0
            else
                pyrefly_gate_status=$?
            fi
            cat \"{output_log}\"
            test \"$pyrefly_gate_status\" -eq 1
            """
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)
    bash_path = Path("/bin/bash")

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-created script
        [str(bash_path), str(run_script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=PKG_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "WARN synthetic warning [test-warning]" in result.stdout
    assert "Pyrefly emitted warnings; treat warnings as quality failures." in result.stdout


@pytest.mark.subprocess
def test_pyrefly_generated_config_neutralizes_parent_repo_ignore_files(
    tmp_path: Path,
) -> None:
    """The generated Pyrefly config must not inherit parent-repo ignore files.

    Linked worktrees (for example .claude/worktrees/*) sit under a hidden
    directory that the parent repo's .git/info/exclude ignores, so project
    discovery finds zero files unless the generated config disables ignore-file
    collection and Pyrefly's hidden-directory exclude heuristic, restoring the
    dropped default excludes explicitly.
    """
    config_path = tmp_path / "pyrefly-generated.toml"
    run_script = tmp_path / "write_pyrefly_config.sh"
    run_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            cd \"{PKG_ROOT}\"
            source tools/common_quality.sh
            QUALITY_PYTHON=\"{sys.executable}\"
            quality_write_pyrefly_config \"{config_path}\" \"{sys.executable}\"
            """
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    result = subprocess.run(  # noqa: S603 - fixed /bin/bash runs a test-created script
        ["/bin/bash", str(run_script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=PKG_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    generated = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert generated["use-ignore-files"] is False
    assert generated["disable-project-excludes-heuristics"] is True

    # The generated config is a throwaway that lives in $TMPDIR, so every
    # pattern and path is anchored to the package root rather than resolved
    # relative to the config file.
    project_excludes = generated["project-excludes"]
    for restored_default in ("**/node_modules/", "**/__pycache__/", "**/.*/**"):
        assert f"{PKG_ROOT.resolve()}/{restored_default}" in project_excludes, (
            f"disabled exclude heuristics must be restored explicitly: {restored_default}"
        )
    assert generated["project-includes"] == [f"{PKG_ROOT.resolve()}/**/*.py"]
    assert generated["search-path"][0] == str(PKG_ROOT.resolve())
    for entry in generated["search-path"]:
        assert Path(entry).is_absolute(), entry


def _update_script_function(name: str) -> str:
    """Extract one top-level shell function body from update.sh."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    match = re.search(
        rf"^{re.escape(name)}\(\) \{{\n.*?^\}}\n", update_script, re.DOTALL | re.MULTILINE
    )
    assert match is not None, name
    return match.group(0)


@pytest.mark.parametrize(
    ("force", "unchanged", "dirty", "verified", "expected"),
    [
        pytest.param("0", "1", "0", "1", "skip", id="unchanged-clean-verified"),
        pytest.param("0", "1", "1", "1", "rebuild", id="unchanged-dirty"),
        pytest.param("0", "0", "0", "1", "rebuild", id="changed-head"),
        pytest.param("0", "1", "0", "0", "rebuild", id="wrong-editable-origin"),
        pytest.param("1", "1", "0", "1", "rebuild", id="force-reinstall"),
    ],
)
def test_update_script_rebuild_decision(
    force: str, unchanged: str, dirty: str, verified: str, expected: str
) -> None:
    """A rebuild is skipped only for an unchanged, clean, verified checkout.

    A dirty checkout can leave modified C++, Metal, or packaging inputs
    behind an unchanged HEAD, so the compiled extension in use would predate
    the source the provenance claims; it must always rebuild.
    """
    function = _update_script_function("mlx_repo_rebuild_decision")
    result = subprocess.run(  # noqa: S603 - fixed /bin/bash evaluates an extracted repo function
        [
            "/bin/bash",
            "-c",
            f"{function}\nmlx_repo_rebuild_decision {force} {unchanged} {dirty} {verified}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected


def test_update_script_wires_dirty_state_into_the_rebuild_decision() -> None:
    """Stage 3 records git status --porcelain; Stage 4 consults it before skipping."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")

    assert 'if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then' in update_script
    assert "REPO_DIRTY[idx]=1" in update_script
    decision_call = (
        'mlx_repo_rebuild_decision "${FORCE_REINSTALL:-0}" "${REPO_UNCHANGED[idx]}" '
        '"${REPO_DIRTY[idx]}" "$editable_verified"'
    )
    assert decision_call in update_script
    assert update_script.index("REPO_DIRTY[idx]=1") < update_script.index(decision_call)


def test_quality_script_drops_hook_exported_git_dir_before_entering_src() -> None:
    """Git exports GIT_DIR into hooks; left set, git treats src/ as the work tree.

    Every ``git diff`` a tool ran from ``src/`` then reported the whole
    repository as deleted (a Skylos SKY-L021 storm from linked worktrees).
    """
    quality_script = (PKG_ROOT / "tools" / "run_quality_checks.sh").read_text(encoding="utf-8")

    assert "\nunset GIT_DIR\n" in quality_script
    assert quality_script.index("unset GIT_DIR") < quality_script.index('cd "$(quality_src_root)"')


def test_update_script_uses_upstream_mlx_editable_dev_install() -> None:
    """Local MLX builds should follow upstream's editable dev install guidance."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "docs" / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert 'INSTALL_CMD=(pip_install_verbose -e ".[dev]")' in update_script
    assert "macOS SDK" in update_script
    assert "Apple Clang" in update_script
    assert "Native arm64 shell detected" in update_script
    assert "MLX_LOCAL_BUILD_SMOKE" in update_script
    assert "mlx.metallib" in update_script
    assert "MLX runtime backend provenance" in update_script
    assert "SKIP_TORCH=1 bash tools/update.sh" in contributing
    assert "# Skip PyTorch support" in contributing
    assert "MLX_LOCAL_BUILD_SMOKE=0" in contributing


def test_update_script_import_repair_hint_uses_distribution_names() -> None:
    """Postflight repair output should use pip package names, not import module names."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")

    assert "IMPORT_TO_PIP_PACKAGE" in update_script
    assert "printf '%s\\n' \"mlx-vlm\"" in update_script
    assert "REPAIR_PKGS" in update_script
    assert 'REPAIR_PKGS+=("$(IMPORT_TO_PIP_PACKAGE "$pkg")")' in update_script
    assert "Fix with: pip install ${REPAIR_PKGS[*]}" in update_script
    assert "Fix with: pip install ${MISSING_PKGS[*]}" not in update_script


def test_update_script_updates_system_packages_by_default_and_node_latest_opt_in() -> None:
    """The updater should refresh system packages by default but keep npm latest opt-in."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    readme = (PKG_ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "docs" / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "UPDATE_SYSTEM_PACKAGES" in update_script
    assert "UPDATE_NODE_TOOLING" in update_script
    assert 'if [[ "${UPDATE_SYSTEM_PACKAGES:-1}" == "1" ]]; then' in update_script
    assert 'if [[ "${UPDATE_NODE_TOOLING:-0}" == "1" ]]; then' in update_script
    assert "Skipping conda base/environment package updates (UPDATE_SYSTEM_PACKAGES=0)" in (
        update_script
    )
    assert "Skipping Homebrew update/upgrade (UPDATE_SYSTEM_PACKAGES=0)" in update_script
    assert "Installing repo-local markdownlint tooling from package-lock.json" in update_script
    assert (
        "`UPDATE_SYSTEM_PACKAGES` | `tools/update.sh` conda base/env and Homebrew updates | `1` (run system updates)"
        in readme
    )
    assert "`UPDATE_SYSTEM_PACKAGES=0`: Skip conda base/environment updates and Homebrew" in (
        contributing
    )

    package_latest = "markdownlint-cli2@latest"
    assert package_latest in update_script
    assert update_script.index(package_latest) > update_script.index("UPDATE_NODE_TOOLING")


def test_update_script_cleans_stale_pip_invalid_distribution_backups() -> None:
    """update.sh should clean pip '~package' backups that cause invalid-distribution warnings."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")

    assert "cleanup_pip_invalid_distribution_backups" in update_script
    assert 'if not name.startswith("~"):' in update_script
    assert "path.is_symlink()" in update_script
    assert "Removed stale pip invalid-distribution backup" in update_script
    assert "CLEAN_PIP_INVALID_DISTS=0" in update_script


def test_update_script_quarantines_broken_packaging_metadata_before_upgrade() -> None:
    """The packaging-tool upgrade should preflight only its own metadata."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    helper_name = "quarantine_broken_pip_metadata.py"
    install_command = 'pip_install_tool pip wheel "setuptools>=80,<82" build pyrefly'

    assert helper_name in update_script
    helper_position = update_script.index(helper_name)
    install_position = update_script.index(install_command)
    preflight = update_script[helper_position:install_position]
    assert "pip wheel setuptools build pyrefly" in " ".join(preflight.split())
    assert helper_position < install_position


def test_quarantine_broken_pip_metadata_moves_only_malformed_targets(
    tmp_path: Path,
) -> None:
    """A stale wheel metadata husk should not mask its healthy replacement."""
    quarantine = quarantine_broken_pip_metadata.quarantine_broken_metadata
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    quarantine_parent = tmp_path / "quarantine"
    quarantine_parent.mkdir()
    stale_wheel = _write_pip_dist_info(site_dir, "wheel", "0.47.0", complete=False)
    healthy_wheel = _write_pip_dist_info(site_dir, "wheel", "0.48.0", complete=True)
    unrelated = _write_pip_dist_info(site_dir, "example", "1.0.0", complete=False)

    moved = quarantine(
        ["wheel"],
        site_dirs=[site_dir],
        quarantine_parent=quarantine_parent,
    )

    assert len(moved) == 1
    source, destination = moved[0]
    assert source == stale_wheel
    assert not stale_wheel.exists()
    assert healthy_wheel.is_dir()
    assert unrelated.is_dir()
    assert destination.is_dir()
    assert (destination / "INSTALLER").read_text(encoding="utf-8") == "pip\n"
    assert destination.is_relative_to(quarantine_parent)


def test_quarantine_broken_pip_metadata_is_noop_for_healthy_target(
    tmp_path: Path,
) -> None:
    """Healthy metadata should not create an empty quarantine directory."""
    quarantine = quarantine_broken_pip_metadata.quarantine_broken_metadata
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    quarantine_parent = tmp_path / "quarantine"
    quarantine_parent.mkdir()
    healthy_wheel = _write_pip_dist_info(site_dir, "wheel", "0.48.0", complete=True)

    moved = quarantine(
        ["wheel"],
        site_dirs=[site_dir],
        quarantine_parent=quarantine_parent,
    )

    assert moved == []
    assert healthy_wheel.is_dir()
    assert list(quarantine_parent.iterdir()) == []


def test_quarantine_broken_pip_metadata_refuses_symlink(tmp_path: Path) -> None:
    """Metadata quarantine must not follow a matching symlink."""
    quarantine = quarantine_broken_pip_metadata.quarantine_broken_metadata
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    metadata_link = site_dir / "wheel-0.47.0.dist-info"
    metadata_link.symlink_to(target, target_is_directory=True)

    with pytest.raises(RuntimeError, match="refusing symlinked metadata directory"):
        quarantine(["wheel"], site_dirs=[site_dir], quarantine_parent=tmp_path)

    assert metadata_link.is_symlink()
    assert target.is_dir()


def test_update_script_reconciles_project_after_mlx_dependency_churn() -> None:
    """update.sh should let pyproject.toml reconcile deps after MLX updates."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    policy_source = (PKG_ROOT / "check_models_data" / "dependency_policy.py").read_text(
        encoding="utf-8",
    )
    main_flow = update_script[update_script.index("# Clean build artifacts if requested") :]

    assert "UPDATE_PIP_CONSTRAINT" not in update_script
    assert "UPDATE_PIP_CONSTRAINT_SPECS" not in policy_source
    # One shared invocation injects the private local-mlx pin (empty-safe on
    # bash 3.2); both public wrappers delegate to it.
    assert (
        'pip install "${args[@]}" ${LOCAL_MLX_PIN_ARGS[@]+"${LOCAL_MLX_PIN_ARGS[@]}"}'
        in update_script
    )
    assert update_script.count("run_eager_pip_install") >= 3  # def + two wrappers
    # Detection is a separate, non-mutating gate so set -e reaches the updater.
    assert "if local_mlx_repos_present; then" in update_script
    assert 'pip_install_tool "setuptools>=80,<82"' in update_script

    local_update_pos = main_flow.index("update_local_mlx_repos")
    pypi_update_pos = main_flow.index("pip_install mlx mlx-metal mlx-vlm")
    reconcile_pos = main_flow.index("reconcile_project_environment_from_pyproject")
    local_smoke_pos = main_flow.index("run_local_mlx_backend_smoke")
    critical_check_pos = main_flow.index("[update.sh] Verifying critical packages")

    assert local_update_pos < reconcile_pos
    assert pypi_update_pos < reconcile_pos
    assert reconcile_pos < local_smoke_pos
    assert reconcile_pos < critical_check_pos
    assert "python -m pip check" in update_script
    assert "python -m tools.validate_env" in update_script


def test_update_script_defers_macos_deployment_target_to_upstream_mlx() -> None:
    """Local mlx builds should let upstream MLX choose the deployment target."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")

    mlx_build_start = update_script.index("# MLX build controls are passed to pip via CMAKE_ARGS.")
    mlx_build_end = update_script.index(
        "[[ ${REPO_SKIP[idx]} -eq 1 ]] && continue",
        mlx_build_start,
    )
    mlx_build = update_script[mlx_build_start:mlx_build_end]

    assert "MACOSX_DEPLOYMENT_TARGET" not in mlx_build
    assert "MLX_METAL_JIT" in mlx_build
    assert 'INSTALL_CMD=(pip_install_verbose -e ".[dev]")' in mlx_build


def test_quality_ci_defers_macos_deployment_target_to_upstream_mlx() -> None:
    """MacOS CI should let upstream MLX choose the deployment target."""
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
    )

    for job_name in ("static-quality", "runtime-smoke"):
        steps = workflow["jobs"][job_name]["steps"]
        step_names = {step.get("name") for step in steps}
        install_command = next(
            step["run"] for step in steps if step.get("name") == "Install dependencies"
        )

        assert "Target host macOS for native builds" not in step_names
        assert "MACOSX_DEPLOYMENT_TARGET" not in install_command


def test_mlx_runtime_imports_avoid_static_native_module_resolution() -> None:
    """Static checkers should not need importable stubs for the native MLX module."""
    source_path = PKG_ROOT / "check_models.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    direct_mlx_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) and any(alias.name == "mlx.core" for alias in node.names)
    ]
    dynamic_mlx_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "mlx.core"
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "import_module")
            or (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
            )
        )
    ]

    assert not direct_mlx_imports, source_path
    assert dynamic_mlx_imports, source_path


def test_workflows_pin_actions_and_keep_skylos_danger_advisory_nonblocking() -> None:
    """Workflow security hardening and advisory Skylos danger wiring should stay in place."""
    action_ref_pattern = re.compile(r"^[^@]+@[0-9a-f]{40}$")

    # Glob so a new workflow file cannot silently escape these requirements.
    workflow_paths = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in (REPO_ROOT / ".github" / "workflows").glob(pattern)
    )
    assert workflow_paths, "no workflow files found"
    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

        assert workflow["permissions"] == {}
        for job_name, job in workflow["jobs"].items():
            assert job["permissions"] == {"contents": "read"}, job_name
            for step in job.get("steps", []):
                if "uses" in step:
                    assert action_ref_pattern.match(step["uses"]), (
                        workflow_path.name,
                        step["uses"],
                    )
                if step.get("name") == "Checkout":
                    assert step["with"]["persist-credentials"] is False
                if step.get("uses", "").startswith("actions/upload-artifact@"):
                    assert step["with"]["if-no-files-found"] == "error"

    quality_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
    )
    advisory_job = quality_workflow["jobs"]["skylos-advisory"]
    advisory_step_names = [step.get("name") for step in advisory_job["steps"]]

    assert advisory_job["runs-on"] == "ubuntu-latest"
    assert "Install Skylos" in advisory_step_names
    assert "Run Skylos advisory danger scan" in advisory_step_names

    static_quality_install = next(
        step["run"]
        for step in quality_workflow["jobs"]["static-quality"]["steps"]
        if step.get("name") == "Install dependencies"
    )
    assert "npm install --ignore-scripts --no-audit --no-fund --prefix src" in (
        static_quality_install
    )


def test_should_audit_path_excludes_generated_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    included = repo_root / "src" / "module.py"
    excluded_build = repo_root / "src" / "build" / "lib" / "check_models.py"
    excluded_conda = repo_root / ".conda" / "lib" / "python3.13" / "site.py"
    excluded_worktree = repo_root / ".worktrees" / "upstream" / "module.py"
    excluded_output = repo_root / "src" / "output" / "results.md"
    included.parent.mkdir(parents=True)
    excluded_build.parent.mkdir(parents=True)
    excluded_conda.parent.mkdir(parents=True)
    excluded_worktree.parent.mkdir(parents=True)
    excluded_output.parent.mkdir(parents=True)
    included.write_text("print('ok')\n", encoding="utf-8")
    excluded_build.write_text("value = 1  # noqa: F401\n", encoding="utf-8")
    excluded_conda.write_text("value = 1  # noqa: F401\n", encoding="utf-8")
    excluded_worktree.write_text("value = 1  # noqa: F401\n", encoding="utf-8")
    excluded_output.write_text("<!-- markdownlint-disable MD028 -->\n", encoding="utf-8")

    assert check_suppressions.should_audit_path(included, repo_root) is True
    assert check_suppressions.should_audit_path(excluded_build, repo_root) is False
    assert check_suppressions.should_audit_path(excluded_conda, repo_root) is False
    assert check_suppressions.should_audit_path(excluded_worktree, repo_root) is False
    assert check_suppressions.should_audit_path(excluded_output, repo_root) is False


def test_find_suppressions_detects_specific_and_bare_directives(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "value = 1  # noqa: F841\n"
        "other = 2  # noqa\n"
        "typed = value  # type: ignore[attr-defined]\n"
        "fallback = value  # type: ignore\n",
        encoding="utf-8",
    )

    findings = check_suppressions.find_suppressions(file_path)

    assert [finding.kind for finding in findings] == [
        "noqa",
        "bare-noqa",
        "type-ignore",
        "bare-type-ignore",
    ]
    assert findings[0].codes == ("F841",)
    assert findings[2].codes == ("attr-defined",)


def test_find_suppressions_ignores_suppression_text_inside_python_strings(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'message = "Bare # noqa is not allowed"\nother = "# type: ignore[attr-defined]"\n',
        encoding="utf-8",
    )

    assert check_suppressions.find_suppressions(file_path) == []


def test_check_if_needed_fails_bare_suppressions(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    src_root = repo_root / "src"
    src_root.mkdir(parents=True)
    file_path = src_root / "sample.py"
    file_path.write_text("value = 1  # noqa\n", encoding="utf-8")
    finding = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="bare-noqa",
        codes=(),
        line_text="value = 1  # noqa",
    )

    needed, reason = check_suppressions.check_if_needed(
        finding,
        repo_root=repo_root,
        src_root=src_root,
    )

    assert needed is False
    assert "not allowed" in reason


@pytest.mark.parametrize(
    ("checker_output", "expected_needed", "expected_reason"),
    [
        (
            "PLR0912 Too many branches",
            False,
            "No violation found for: PLR0915",
        ),
        (
            "PLR0912 Too many branches\nPLR0915 Too many statements",
            True,
            "Suppression needed: PLR0912, PLR0915 violations found",
        ),
    ],
)
def test_check_if_needed_requires_evidence_for_every_suppressed_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checker_output: str,
    expected_needed: bool,
    expected_reason: str,
) -> None:
    """Every code on a combined suppression must have checker evidence."""
    repo_root = tmp_path / "repo"
    src_root = repo_root / "src"
    src_root.mkdir(parents=True)
    file_path = src_root / "sample.py"
    file_path.write_text(
        "def sample():  # noqa: PLR0912, PLR0915 - fixture rationale\n    pass\n",
        encoding="utf-8",
    )
    finding = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="noqa",
        codes=("PLR0912", "PLR0915"),
        line_text="def sample():  # noqa: PLR0912, PLR0915 - fixture rationale",
    )
    result = subprocess.CompletedProcess(
        args=["ruff"],
        returncode=1,
        stdout=checker_output,
        stderr="",
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return result

    monkeypatch.setattr(check_suppressions, "_run_for_finding", fake_run)

    needed, reason = check_suppressions.check_if_needed(
        finding,
        repo_root=repo_root,
        src_root=src_root,
    )

    assert needed is expected_needed
    assert reason == expected_reason


def test_run_for_finding_uses_active_python_for_ruff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    src_root = repo_root / "src"
    src_root.mkdir(parents=True)
    file_path = src_root / "sample.py"
    file_path.write_text("unused = 1  # noqa: F841\n", encoding="utf-8")
    finding = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="noqa",
        codes=("F841",),
        line_text="unused = 1  # noqa: F841",
    )
    recorded_args: list[str] = []

    def fake_run(
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        assert cwd == src_root
        recorded_args.extend(args)
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="F841", stderr="")

    monkeypatch.setattr(check_suppressions.subprocess, "run", fake_run)

    result = check_suppressions._run_for_finding(
        finding,
        repo_root=repo_root,
        src_root=src_root,
    )

    assert result is not None
    assert recorded_args[:4] == [sys.executable, "-m", "ruff", "check"]


def test_agents_and_claude_docs_stay_in_sync() -> None:
    """AGENTS.md and CLAUDE.md must stay byte-identical below their H1 titles."""

    def body_below_title(path: Path) -> str:
        lines = safe_io.read_text_no_follow(path).splitlines()
        return "\n".join(lines[1:])

    agents = REPO_ROOT / "AGENTS.md"
    claude = REPO_ROOT / "CLAUDE.md"
    assert agents.is_file()
    assert claude.is_file()
    assert body_below_title(agents) == body_below_title(claude), (
        "AGENTS.md and CLAUDE.md have drifted; apply edits to both files"
    )


def test_precommit_framework_config_installs_both_hooks() -> None:
    """The checked-in pre-commit config is the single hook mechanism."""
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))

    assert tuple(config["default_install_hook_types"]) == ("pre-commit", "pre-push")
    entries = [hook["entry"] for repo in config["repos"] for hook in repo["hooks"]]
    for entry in entries:
        script = entry.removeprefix("bash ").split()[0]
        assert (REPO_ROOT / script).is_file(), entry
    assert any("run_commit_hygiene.sh" in entry for entry in entries)
    assert any("check_quality_simple.sh" in entry for entry in entries)
    assert (PKG_ROOT / "tools" / "validate_env.py").read_text(encoding="utf-8").count(
        'REQUIRED_HOOK_TYPES: tuple[str, ...] = ("pre-commit", "pre-push")'
    ) == 1


def test_python_floor_is_single_sourced() -> None:
    """Every encoding of the minimum Python version must agree with pyproject."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requires_python = pyproject["project"]["requires-python"]
    assert requires_python.startswith(">=")
    floor = requires_python.removeprefix(">=").strip()

    assert pyproject["tool"]["mypy"]["python_version"] == floor
    assert pyproject["tool"]["pyright"]["pythonVersion"] == floor
    assert pyproject["tool"]["pyrefly"]["python-version"] == floor

    assert ".".join(str(part) for part in validate_env.REQUIRED_PYTHON_VERSION) == floor

    setup_script = (PKG_ROOT / "tools" / "setup_conda_env.sh").read_text(encoding="utf-8")
    assert f"python={floor}" in setup_script

    # CI runs the floor plus any newer candidate (a staged Python move is
    # rehearsed in CI before the working env follows). Every literal version
    # in the workflows must be >= the floor, and the floor itself must still be
    # exercised somewhere so the supported minimum stays tested.
    floor_parts = tuple(int(part) for part in floor.split("."))
    ci_versions: set[str] = set()
    for workflow_path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for match in re.finditer(r'"(3\.\d{1,2})"', workflow_text):
            ci_versions.add(match.group(1))
    assert floor in ci_versions, f"CI no longer tests the Python floor {floor}: {ci_versions}"
    for version in ci_versions:
        assert tuple(int(part) for part in version.split(".")) >= floor_parts, version


def test_update_smoke_defaults_are_documented() -> None:
    """The smoke model and expected output are mirrored into docs by hand."""
    update_script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    model_match = re.search(r"MLX_LOCAL_BUILD_SMOKE_MODEL:-([^}]+)\}", update_script)
    expected_match = re.search(r"MLX_LOCAL_BUILD_SMOKE_EXPECTED:-([^}]+)\}", update_script)
    assert model_match is not None
    assert expected_match is not None
    model = model_match.group(1)
    expected = expected_match.group(1)

    package_readme = (PKG_ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "docs" / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for text, name in ((package_readme, "src/README.md"), (contributing, "CONTRIBUTING.md")):
        assert model in text, f"smoke model not documented in {name}"
        assert expected in text, f"smoke expected output not documented in {name}"


def test_section_banners_match_copilot_instructions() -> None:
    """The monolith's SECTION landmarks and the documented map must stay identical."""
    source = (PKG_ROOT / "check_models.py").read_text(encoding="utf-8")
    banners = re.findall(r"^# SECTION: (.+)$", source, re.MULTILINE)
    # Only the §3 table rows define the map; prose mentions elsewhere are free.
    documented = re.findall(
        r"^\|.*?`SECTION: ([^`]+)`",
        COPILOT_INSTRUCTIONS.read_text(encoding="utf-8"),
        re.MULTILINE,
    )

    assert banners, "no SECTION banners found in check_models.py"
    assert banners == documented, (
        "SECTION banners and copilot-instructions §3 have drifted (order matters)"
    )


def test_no_ci_only_mlx_core_stub_generation() -> None:
    """mlx.core stubs come from the mlx distribution itself; nothing must regenerate them.

    Both the PyPI wheel and an editable build ship ``mlx/core/*.pyi`` generated at
    build time by mlx's own ``nanobind_add_stub``. A recursive
    ``python -m nanobind.stubgen -m mlx.core -r`` run emits submodule stubs without
    imports (hundreds of mypy name-defined errors), so the retired CI step and the
    nanobind dev dependency must not come back.
    """
    quality_workflow = (REPO_ROOT / ".github" / "workflows" / "quality.yml").read_text(
        encoding="utf-8"
    )
    pyproject_text = (REPO_ROOT / "src" / "pyproject.toml").read_text(encoding="utf-8")
    copilot_text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

    for label, text in (
        ("quality.yml", quality_workflow),
        ("pyproject.toml", pyproject_text),
        ("copilot-instructions.md", copilot_text),
    ):
        assert "nanobind" not in text, f"{label} reintroduces nanobind stub generation"


def test_make_format_covers_every_gate_formatted_directory() -> None:
    """`make format` must reach every directory the full gate's `ruff format .` reaches."""
    makefile = (PKG_ROOT / "Makefile").read_text(encoding="utf-8")
    fmt_match = re.search(r"^FMT_PATHS := (.+)$", makefile, re.MULTILINE)
    assert fmt_match is not None
    fmt_paths = set(fmt_match.group(1).split())

    expected_dirs = {
        path.name
        for path in PKG_ROOT.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name
        not in {"node_modules", "output", "build", "dist", "check_models.egg-info", "typings"}
        and any(path.glob("*.py"))
    }
    assert expected_dirs | {"check_models.py"} <= fmt_paths | expected_dirs & fmt_paths | {
        "check_models.py"
    }
    assert expected_dirs <= fmt_paths, (
        f"make format misses {expected_dirs - fmt_paths}; the gate's `ruff format .` "
        "would still reformat them"
    )


def test_quality_script_globs_workflow_yaml_files() -> None:
    """Workflow YAML validation must enumerate by glob, not by hardcoded list."""
    quality_script = (PKG_ROOT / "tools" / "run_quality_checks.sh").read_text(encoding="utf-8")

    assert 'find "$(quality_repo_root)/.github/workflows"' in quality_script
    assert ".github/workflows/quality.yml" not in quality_script


def test_danger_report_filter_drops_only_worktree_findings(tmp_path: Path) -> None:
    """The Skylos danger post-filter must drop .worktrees findings and keep the rest."""
    report: dict[str, object] = {
        "danger": [
            {"file": "/repo/.worktrees/mlx-vlm-x/.github/workflows/tests.yml", "rule": "D292"},
            {"file": "/repo/.claude/worktrees/agent-x/src/check_models.py", "rule": "D215"},
            {"file": "/repo/src/tools/update.sh", "rule": "D301"},
            "not-a-dict-entry",
        ],
        "grade": {"overall": {"score": 54}},
    }
    dropped = filter_danger_report.drop_worktree_findings(report)

    assert dropped == 2
    assert report["danger"] == [
        {"file": "/repo/src/tools/update.sh", "rule": "D301"},
        "not-a-dict-entry",
    ]

    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({"danger": []}), encoding="utf-8")
    assert filter_danger_report.main(["prog", str(report_path)]) == 0


def test_artifact_schema_version_constants_match_typed_dict_literals() -> None:
    """Writers/readers share version constants that must match the TypedDict Literals."""
    jsonl_literal = typing.get_args(
        typing.get_type_hints(check_models.JsonlMetadataRecord)["format_version"]
    )
    history_literal = typing.get_args(
        typing.get_type_hints(check_models.HistoryRunRecord)["format_version"]
    )

    assert jsonl_literal == (check_models.JSONL_FORMAT_VERSION,)
    assert history_literal == (check_models.HISTORY_FORMAT_VERSION,)


def test_check_if_needed_rejects_suppressions_without_justification(tmp_path: Path) -> None:
    """A suppression must say why it is safe, not only what it silences."""
    repo_root = tmp_path / "repo"
    src_root = repo_root / "src"
    src_root.mkdir(parents=True)
    file_path = src_root / "sample.py"
    file_path.write_text("unused = 1  # noqa: F841\n", encoding="utf-8")
    finding = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="noqa",
        codes=("F841",),
        line_text="unused = 1  # noqa: F841",
    )

    needed, reason = check_suppressions.check_if_needed(
        finding,
        repo_root=repo_root,
        src_root=src_root,
    )

    assert needed is False
    assert "no justification" in reason
    # The rationale extractor recognises both comment styles.
    justified_noqa = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="noqa",
        codes=("F841",),
        line_text="unused = 1  # noqa: F841 - fixture keeps the name visible",
    )
    justified_ignore = check_suppressions.SuppressionFinding(
        file_path=file_path,
        line_num=1,
        kind="type-ignore",
        codes=("assignment",),
        line_text="x = y  # type: ignore[assignment]  # narrowing is deliberate",
    )
    assert check_suppressions._suppression_rationale(justified_noqa)
    assert check_suppressions._suppression_rationale(justified_ignore)


def _run_update_pip_wrapper_harness(driver: str, tmp_path: Path) -> str:
    """Run update.sh's pin/wrapper helpers against a fake pip; return its arg log.

    The helpers are extracted verbatim from the script (the contiguous block
    from the pin state through ``pip_install_verbose``) so the test exercises
    the shipped code, not a copy.
    """
    script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    start = script.index('LOCAL_MLX_CONSTRAINT_FILE=""')
    end = script.index("# Helper function: pip install for build/infrastructure tools only.")
    helpers = script[start:end]

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    pip_log = tmp_path / "pip-args.log"
    fake_pip = fake_bin / "pip"
    safe_io.write_text_no_follow(
        fake_pip,
        "#!/bin/bash\n"
        f'echo "ARGS: $*" >> "{pip_log}"\n'
        f'echo "CALLER_PIP_CONSTRAINT: ${{PIP_CONSTRAINT:-unset}}" >> "{pip_log}"\n',
        mode=0o755,
    )

    completed = subprocess.run(  # noqa: S603 - test harness, fixed bash, temp files
        ["/bin/bash", "-c", helpers + "\n" + driver],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    log_text = safe_io.read_text_no_follow(pip_log) if pip_log.exists() else ""
    return log_text + completed.stdout


def test_update_pip_wrappers_normal_and_forced_without_pin(tmp_path: Path) -> None:
    """Without a pin, wrappers pass eager upgrades and honour FORCE_REINSTALL."""
    log = _run_update_pip_wrapper_harness("pip_install somepkg", tmp_path)
    assert "--constraint" not in log
    assert "--force-reinstall" not in log

    log = _run_update_pip_wrapper_harness("FORCE_REINSTALL=1\npip_install somepkg", tmp_path)
    assert "--force-reinstall" in log
    assert "--constraint" not in log


def test_update_pip_wrappers_pin_constrains_and_suppresses_force(tmp_path: Path) -> None:
    """The mlx pin adds a private --constraint and outranks FORCE_REINSTALL.

    Regression: FORCE_REINSTALL plus the pin previously produced
    ResolutionImpossible (the exact local dev version cannot come from PyPI);
    local-source preservation must win, with the suppression logged.
    """
    driver = """
get_installed_distribution_version() { echo "0.32.2.dev20260825+abc123"; }
pin_local_mlx_build
pip_install somepkg
FORCE_REINSTALL=1
pip_install otherpkg
"""
    log = _run_update_pip_wrapper_harness(driver, tmp_path)
    assert "--constraint" in log
    assert "--force-reinstall" not in log
    assert "FORCE_REINSTALL suppressed" in log
    assert "Pinned local mlx 0.32.2.dev20260825+abc123" in log


def test_update_pin_failure_is_fatal_when_version_unreadable(tmp_path: Path) -> None:
    """An unpinnable local build must stop the run, not continue unprotected."""
    driver = """
get_installed_distribution_version() { echo ""; }
if pin_local_mlx_build; then
    echo "PIN_RC: 0"
else
    echo "PIN_RC: 1"
fi
"""
    log = _run_update_pip_wrapper_harness(driver, tmp_path)
    assert "PIN_RC: 1" in log
    assert "refusing to continue" in log


def test_update_pip_wrappers_preserve_caller_constraint_and_clean_up(tmp_path: Path) -> None:
    """Caller PIP_CONSTRAINT passes through untouched; the pin file is removed on exit."""
    caller_file = tmp_path / "caller-constraints.txt"
    caller_file.write_text("requests==2.0.0\n", encoding="utf-8")
    driver = f"""
export PIP_CONSTRAINT="{caller_file}"
get_installed_distribution_version() {{ echo "0.32.2.dev20260825+abc123"; }}
pin_local_mlx_build
pip_install somepkg
echo "PINFILE: $LOCAL_MLX_CONSTRAINT_FILE"
"""
    log = _run_update_pip_wrapper_harness(driver, tmp_path)
    assert f"CALLER_PIP_CONSTRAINT: {caller_file}" in log
    pin_file = next(
        line.split("PINFILE: ", 1)[1].strip()
        for line in log.splitlines()
        if line.startswith("PINFILE: ")
    )
    assert pin_file
    assert not Path(pin_file).exists(), "EXIT trap must remove the pin file"
    # And the script must never export global pip state for the pin.
    script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    assert "export PIP_CONSTRAINT" not in script


def test_pip_show_helpers_survive_set_e_pipefail_with_chatty_pip(tmp_path: Path) -> None:
    """The helpers must not die under `set -euo pipefail` however chatty pip is.

    Regression: `pip show | awk '{...; exit}'` raced SIGPIPE — awk quit at the
    matched line, pip took EPIPE, and once the updater ran under live `set -e`
    the failing command substitution in `pin_local_mlx_build` killed the whole
    script with no output, right after "mlx installed successfully".
    """
    script = (PKG_ROOT / "tools" / "update.sh").read_text(encoding="utf-8")
    helper_names = (
        "pip_show_field",
        "get_editable_project_location",
        "get_installed_distribution_version",
    )
    helper_parts: list[str] = []
    for name in helper_names:
        match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", script, re.MULTILINE | re.DOTALL)
        assert match is not None, f"helper {name} missing from update.sh"
        helper_parts.append(match.group(0))
    helper_block = "".join(helper_parts)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    lines = "\n".join(f"Filler-{i}: value" for i in range(4000))
    safe_io.write_text_no_follow(
        fake_python,
        "#!/bin/bash\n"
        'echo "Name: mlx"\n'
        'echo "Version: 0.32.2.dev1+abc"\n'
        f'cat <<"BULK"\n{lines}\nBULK\n'
        'echo "Editable project location: /tmp/mlx"\n',
        mode=0o755,
    )
    driver = (
        "set -euo pipefail\n"
        + helper_block
        + '\nversion="$(get_installed_distribution_version mlx)"\n'
        + 'location="$(get_editable_project_location mlx)"\n'
        + 'echo "VERSION: $version"\n'
        + 'echo "LOCATION: $location"\n'
    )
    completed = subprocess.run(  # noqa: S603 - test harness, fixed bash, temp files
        ["/bin/bash", "-c", driver],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    assert completed.returncode == 0, completed.stderr
    assert "VERSION: 0.32.2.dev1+abc" in completed.stdout
    assert "LOCATION: /tmp/mlx" in completed.stdout


def _skill_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML-ish frontmatter block, joining folded (`>`) continuation lines."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None, "SKILL.md must start with a frontmatter block"
    fields: dict[str, str] = {}
    current: str | None = None
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) and current is not None:
            fields[current] = (fields[current] + " " + line.strip()).strip()
            continue
        key, _, value = line.partition(":")
        current = key.strip()
        fields[current] = value.strip().lstrip(">").strip()
    return fields


def test_agent_skills_are_well_formed_and_listed() -> None:
    """Adapted from upstream mlx-vlm's ``skills/scripts/validate_skills.py``.

    Every skill: frontmatter ``name`` equal to its directory, a real trigger
    sentence as ``description``, a row in the Copilot skills table, and no
    ``uv`` commands in its code fences (this repo is conda + pip). Upstream
    skills cited as sources must exist upstream.
    """
    skill_dirs = sorted(path for path in AGENT_SKILLS_DIR.iterdir() if path.is_dir())
    assert skill_dirs, "no skills found"
    copilot_text = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    for skill_dir in skill_dirs:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = _skill_frontmatter(text)
        assert frontmatter.get("name") == skill_dir.name, skill_dir.name
        assert len(frontmatter.get("description", "")) >= 40, skill_dir.name
        assert f"| `{skill_dir.name}` |" in copilot_text, f"{skill_dir.name} missing from table"
        for fence in re.findall(r"```[a-z]*\n(.*?)```", text, re.DOTALL):
            for line in fence.splitlines():
                assert not line.strip().startswith("uv "), f"{skill_dir.name}: uv command"
        for cited in re.findall(r"skills/skills/([a-z0-9-]+)", text):
            assert cited in UPSTREAM_MLX_VLM_SKILLS, f"{skill_dir.name} cites unknown {cited}"
