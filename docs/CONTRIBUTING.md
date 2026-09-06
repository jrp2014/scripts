# Contributing to MLX VLM Check

Thank you for your interest in contributing to MLX VLM Check! This document guides you through the practical workflow of contributing: getting set up, making changes, and submitting them.

**Target audience**: New contributors, anyone submitting a pull request.

> [!NOTE]
> This project was restructured in October 2025. The old package-local tree is
> now `src/`, and contributor-facing `make` commands should be run from the repo
> root unless a package-local target is explicitly documented.

**Related documents**:

- [README.md](../README.md) - Project overview and quick start
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Detailed coding standards and technical conventions
- [src/README.md](../src/README.md) - Detailed package usage and CLI documentation
- [notes/](notes/) - Design notes and project evolution

## Table of Contents

- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Quality Checks](#quality-checks)
- [Testing](#testing)
- [Dependency Management](#dependency-management)
- [Submitting Changes](#submitting-changes)
- [Getting Help](#getting-help)

## Development Setup

### Prerequisites

- macOS (preferably with Apple Silicon)
- Python 3.13+
- conda or miniconda
- Git

### Initial Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/jrp2014/check_models.git
   cd check_models
   ```

2. **Create and activate conda environment**:

   ```bash
   bash src/tools/setup_conda_env.sh
   conda activate mlx-vlm
   ```

3. **Install development dependencies**:

   ```bash
   make dev
   ```

   This will:
   - Install all Python dependencies (runtime + dev + extras + torch)
   - Install the package in editable mode
   - Install repo-local Markdown hook tooling if `npm` is available

   **Optional follow-up**:

   - Install markdown tooling: `make install-markdownlint` (requires Node.js/npm)
   - Use package-local install variants via `make -C src help`

4. **Verify installation**:

   ```bash
   # Verify environment (run from src/)
   cd src
   python -m tools.validate_env
   cd ..
   ```

   If you answered `y` to development dependencies during setup, the repo's
   git hooks are already installed. To reinstall them manually:

   ```bash
   pre-commit install
   ```

### Manual Environment Validation

If bootstrap didn't work or you want to check your environment:

```bash
# Check environment health (run from src/ directory)
cd src
python -m tools.validate_env

# Auto-fix common issues
python -m tools.validate_env --fix
```

## Making Changes

### Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:

   - Follow the [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) conventions
   - Add tests for new functionality
   - Update documentation as needed

3. **Run the full local gate**:

   ```bash
   make quality
   ```

   `make quality` includes the full pytest suite. Use `make test` as a
   faster pytest-only loop while developing, not as an extra step after a
   successful quality run.

   Validation tests must not rewrite tracked `src/output/` assets. Tests that
   exercise report generation write to a temp directory (`tmp_path`), so
   contributors and CI never need to restore benchmark snapshots after
   verification. Manual validation runs of the CLI use a gitignored `test_*`
   path under `src/output/` instead.

### Code Style

- **Python**: Follow PEP 8, enforced by ruff
- **Line length**: 100 characters (configurable exceptions for long strings)
- **Type annotations**: Required for all new code
- **Docstrings**: Required for non-obvious functions
- **Logging and Rich output**: Send user-visible messages through `logger` so console and file logs stay aligned. Use Rich to build tables or panels, then route them through the existing logging helpers instead of calling `Console.print()` directly from feature code.

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for detailed conventions.

## Quality Checks

### Automated Checks

The project uses several automated quality checks:

1. **Ruff** (formatting and linting):

   ```bash
   make format      # Format code
   make lint        # Lint code
   ```

2. **Mypy** (type checking):

   ```bash
   make typecheck   # Type check with mypy
   ```

3. **Ty** (import-aware type checking with explicit env resolution):

   ```bash
   make ty          # Runs Ty using the resolved mlx-vlm interpreter
   ```

   Use `make ty` instead of calling `ty check` directly. The repo wrapper
   resolves the expected `mlx-vlm` conda environment and prints diagnostics for
   the target env, active env, resolved Python path, and resolved Ty binary so
   import-resolution problems are visible instead of mysterious.

4. **Vulture** (dead-code scan):

   ```bash
   make vulture     # Runs the configured dead-code scan for src/check_models.py and src/tools/
   ```

   The repo keeps the default Vulture gate conservative for day-to-day work:
   it scans `src/check_models.py` plus the Python utilities under `src/tools/`
   with `min_confidence = 100` from `src/pyproject.toml`, so only
   high-confidence dead-code findings fail the quality gate by default.

5. **Tests**:

   ```bash
   make test        # Run pytest only; useful before the full gate
   ```

6. **Combined quality check**:

   ```bash
   make quality     # Runs ruff + mypy + ty + pyrefly + vulture + Skylos quality/audit + full pytest + shellcheck + markdownlint
   ```

   The Ty and Vulture steps inside `make quality` use the same checked-in repo
   wrappers and config as their standalone targets, so local runs and CI use
   the same behavior. A successful `make quality` run supersedes `make test`;
   run `make test` separately only when you want a pytest-only feedback loop.
   Validation tests must not rewrite tracked `src/output/` assets; they write
   generated reports and logs to a temp directory (`tmp_path`).
   The blocking Skylos steps gate quality, secrets, dependency-vulnerability,
   `-a` audit findings, and (in full mode) `--danger` security findings via the
   Skylos Danger Gate. Run `make skylos-danger` for the same `--danger` scan in
   advisory/diff-aware form (useful for triage on PR diffs), or
   `make skylos-danger-llm` for the LLM-oriented rendering for agent triage.
   For a narrow agent/edit-loop check, run
   `make skylos-verify ARGS='--file path/to/file --range L1:L2'`.

7. **Markdown linting**:

   `make quality` runs markdownlint via the repo-local install, a global
   `markdownlint-cli2`, or an `npx --no-install` fallback. If none of those are
   available, the quality gate fails.

   ```bash
   # Install markdown linting (requires Node.js/npm)
   make install-markdownlint

   # Or run via npx from the repo root with the checked-in config
   npx --no-install markdownlint-cli2 --config .markdownlint.jsonc '**/*.md' '!src/node_modules/**' '!**/node_modules/**'
   ```

### VS Code Problems

This repo ships a checked-in `Make: vulture` task in `.vscode/tasks.json`.
Run that task from VS Code to surface Vulture findings as `warning` entries in
the Problems panel, mapped to paths under `src/`.

The matcher is intentionally attached only to the dedicated Vulture task.
`Make: quality` mixes output from many tools, and generic `file:line:` text
from unrelated steps can otherwise create noisy or stale Problems entries.

The repo does not force Vulture to auto-run on every save or file change.
Re-run `Make: vulture` after larger refactors, deletions, or control-flow
changes, and use `Make: quality` as the broader gate.

### Git Hooks

The hooks come from the checked-in `.pre-commit-config.yaml` (`pre-commit
install`):

- `pre-commit` stage: staged hygiene via `src/tools/run_commit_hygiene.sh`
   (validates staged YAML/TOML/shebangs, formats and lints staged Python, fixes
   staged Markdown, syncs README deps when `src/pyproject.toml` changes).
- `pre-push` stage: the fast static gate via `src/tools/check_quality_simple.sh`
   (workflow YAML validation, dependency sync verification, Ruff format check +
   lint, mypy, ty, pyrefly, Vulture, and `pytest -m "not slow and not e2e"`).

To bypass hooks (not recommended):

```bash
git commit --no-verify
git push --no-verify
```

### Continuous Integration

All pull requests must pass:

- Quality workflow (`.github/workflows/quality.yml`) `static-quality` job: workflow YAML validation, dependency sync check, ruff format check + lint, mypy + ty + pyrefly + Vulture, Skylos quality/secrets/SCA plus `-a` audit, pytest, shellcheck, markdownlint
- Quality workflow (`.github/workflows/quality.yml`) `runtime-smoke` job: isolated runtime smoke probe via `src/tools/run_runtime_smoke.sh`
- Dependency sync guard (`.github/workflows/dependency-sync.yml`)

## Testing

### Quick Verification

To verify that your environment and `mlx-vlm` are working correctly before running the full test suite, you can use the CLI (conda env active; **pip**, not `uv`):

```bash
python -m mlx_vlm.generate --model mlx-community/nanoLLaVA --image /path/to/image.jpg
```

For maintainer-facing upstream isolation, prefer:

1. Retained crash drafts under `src/output/issues/` and the shared repro in
   `src/output/reports/diagnostics.md` when a run already exists.
2. A minimized native `python -m mlx_vlm.generate` command (greedy /
   `--temperature 0.0`, bounded `--max-tokens`, pinned `--revision` when known).
3. One model per process to avoid sequential Metal-state interactions.

Agent workflows for native repros, HF cache filter alignment, and issue-ready
Markdown live under `.agents/skills/` (`native-mlx-vlm-repro`,
`hf-cache-mlx-vlm-models`, `upstream-mlx-vlm-issues`). Default model discovery
matches the mlx-vlm server cache filter (`config.json`, `tokenizer_config.json`,
safetensors on `main`); use `python -m check_models --dry-run` or
`get_cached_model_ids()` rather than ad-hoc cache scanners.

Alternatively, refer to the official smoke test script:

- [test_smoke.py](https://github.com/Blaizzy/mlx-vlm/blob/main/mlx_vlm/tests/test_smoke.py)

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest src/tests/test_specific.py

# Run with verbose output
pytest src/tests/ -v
```

### Writing Tests

- Place tests in `src/tests/`
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Include both positive and negative test cases
- Aim for high coverage of critical paths
- When testing evaluation history or capability aggregation, label fixtures with
  the resolved `triage`, `blind`, or `assisted` lane and verify that records
  from other lanes and unlabelled legacy history are excluded.
- Report tests must write to a temp directory (`tmp_path`), never under `src/`.
  Never refresh tracked `src/output/` fixtures as a side effect of pytest.
  Ordinary gitignored tool caches (`__pycache__`, `.pytest_cache` and the
  like) are not generated output and may stay in the tree.
- Refresh tracked benchmark snapshots only with the documented representative
  production command and only when its exact source image is available. Review
  every generated artifact, retain the complete `results.html`, avoid private
  absolute paths in copy/paste repro commands, and stage only the intended
  public snapshot files.
- Assert semantics at the canonical fact/view boundary where possible, then add
  compact renderer assertions for primary/supporting artifact roles and for the
  current-run versus lane-matched historical capability distinction.

## Submitting Changes

### Pull Request Process

1. **Ensure all checks pass**:

   ```bash
   make ci
   ```

2. **Update documentation**:

   - Update README.md if adding user-facing features
   - Update IMPLEMENTATION_GUIDE.md if changing technical conventions
   - Add docstrings to new functions

3. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

4. **Push and create PR**:

   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a pull request on GitHub.

### PR Requirements

Your PR must:

- Pass all CI checks
- Include tests for new functionality
- Update relevant documentation
- Have a clear description of changes
- Reference any related issues

## Dependency Management

> [!NOTE]
> Canonical source: [.github/copilot-instructions.md](../.github/copilot-instructions.md)
> (dependency policy) and `src/pyproject.toml`. If this section disagrees with
> those, they win.

### Dependency Structure

The project organizes dependencies into groups:

- **Runtime**: Core dependencies needed to run `check_models.py` (mlx, mlx-vlm, Pillow, etc.)
- **Extras**: Optional enhancements (psutil, tokenizers, einops, num2words, sentencepiece);
  tokenizers and sentencepiece specs track the Transformers compatibility window
- **Torch**: PyTorch stack for models that require it (torch, torchvision, torchaudio, timm);
  torch and timm floors track Transformers optional-extra metadata
- **Dev**: Development tools (ruff, mypy, pytest)

Install specific groups as needed:

```bash
# Runtime only (from repo root)
pip install -e src/

# With extras / torch / dev (from repo root)
pip install -e "src/[extras,torch]"
pip install -e "src/[dev]"

# Everything
make dev

# Package-local installation helpers
make -C src install-torch
make -C src install-all
```

### Managing Dependencies

Dependencies are defined in `src/pyproject.toml` as the single source of truth.

```bash
# Full update: conda/brew, local MLX repo builds, stubs, smoke (tools/update.sh):
make update

# Quick in-env refresh only (pip upgrade + editable reinstall):
make update-quick

# Check for outdated packages:
make check-outdated

# Security audit:
make audit

# Sync README dependency blocks:
make deps-sync

# Verify README dependency blocks are already in sync (CI-style):
python -m tools.update_readme_deps --check
```

#### Advanced: update.sh options (what `make update` runs)

`make update` runs `src/tools/update.sh`; invoke the script directly when you
need its environment-variable switches:

```bash
cd src
bash tools/update.sh
```

**When to use `make update` / `update.sh`**:

- You have local development builds of MLX, MLX-LM, or MLX-VLM
- You want system package managers (conda/Homebrew) refreshed too
- You need environment diagnostics, stub regeneration, and the runtime smoke

**When to use `make update-quick`**:

- Standard workflow (using released packages from PyPI)
- Quick in-env refresh after pulling repository changes
- You don't need special handling for local MLX builds

**Features of update.sh**:

- Automatically detects and uses local MLX development builds
- Validates Python version (>= 3.13 required)
- Checks for virtual environment activation
- Verifies MLX source-build prerequisites from upstream's current guidance:
  CMake >= 3.25, Xcode >= 15, macOS SDK >= 14, Apple Clang >= 15, Metal
  tools, and a native arm64 shell on macOS
- Installs the project editable environment with dev and extras enabled by default
- Uses repo-local Node tooling (`npm install --ignore-scripts --prefix src`) for
  markdownlint instead of relying on global packages; latest npm upgrades are
  opt-in
- Reinstalls `check_models` from `src/pyproject.toml` after local/PyPI MLX
  updates so the project dependency policy performs the final reconciliation
- Verifies dependency sync across `pyproject.toml`, generated README install blocks, and updater assumptions
- Logs MLX backend provenance, including the installed `mlx`, `mlx-metal`,
  `libmlx.dylib`, and `mlx.metallib` locations and hashes
- Runs a deterministic local-MLX smoke test in `auto` mode when the default
  smoke model is already cached, so broken local Metal artifacts fail before
  they are mistaken for model-quality regressions

**Environment Variables**:

- `SKIP_TORCH=1`: Skip PyTorch installation (torch is included by default)
- `UPDATE_SYSTEM_PACKAGES=0`: Skip conda base/environment updates and Homebrew
  update/upgrade. By default, `update.sh` refreshes system package managers.
- `UPDATE_NODE_TOOLING=1`: Upgrade repo-local markdownlint tooling to the
  latest npm release. By default, `update.sh` installs from `package-lock.json`.
- `CLEAN_PIP_INVALID_DISTS=0`: Skip cleanup of stale pip `~package` backup
  directories that can produce "Ignoring invalid distribution" warnings.
- `MLX_METAL_JIT=ON`: Build local `mlx` with runtime Metal compilation
  (mapped to `CMAKE_ARGS=-DMLX_METAL_JIT=ON`; if unset, MLX's default
  `MLX_METAL_JIT=OFF` uses pre-built kernels)
- `MLX_LOCAL_BUILD_SMOKE=auto|1|0`: Run the local MLX runtime smoke test.
  `auto` is the default and runs only when the smoke model is already cached;
  `1` forces the test and may download the model; `0` skips it.
- `MLX_LOCAL_BUILD_SMOKE_MODEL`: Override the default smoke model
  (`mlx-community/MiniCPM-V-4.6-8bit`).
- `MLX_LOCAL_BUILD_SMOKE_EXPECTED`: Override the expected deterministic output
  substring (`Hello! How can I help you today?`).

`tools/update.sh` (what `make update` runs) auto-detects sibling `mlx`
and `mlx-vlm` repositories and follows upstream MLX editable dev
install guidance for `mlx`; without local repos it falls back to PyPI updates.
Use `make update-quick` for a lightweight in-env refresh only.

**MLX_METAL_JIT Trade-offs**:

- `OFF` (default): Pre-built GPU kernels, larger binary (~100MB+ metallib), instant execution
- `ON`: Runtime compilation, smaller binary, cold-start delay (few hundred ms to few seconds on first use per kernel, then cached permanently)

**Example usage**:

```bash
# Standard build with pre-built kernels (default)
bash tools/update.sh

# Smaller binary with runtime compilation (cold start penalty)
MLX_METAL_JIT=ON bash tools/update.sh

# Bypass the local MLX smoke only after confirming the backend artifact manually
MLX_LOCAL_BUILD_SMOKE=0 bash tools/update.sh

# Skip PyTorch support
SKIP_TORCH=1 bash tools/update.sh
```

### Updating Dependencies

1. Edit `src/pyproject.toml` to update the dependency specification:
   - Runtime dependencies: `[project.dependencies]`
   - Dev dependencies: `[project.optional-dependencies.dev]`
   - Optional extras: `[project.optional-dependencies.extras]`
2. Run `make deps-sync` to update README blocks
3. Test thoroughly with `make quality` before committing. During local
   iteration, use targeted pytest commands or `make test` for a faster
   pytest-only loop.
4. Commit the changes

### Keeping Your Environment Up-to-Date

After pulling changes from the repository, refresh your environment with:

```bash
make update-quick
```

This command will:

- Update pip in your conda/venv environment
- Reinstall the project with all dependencies (dev, extras, torch)
- Apply the current dependency bounds from `src/pyproject.toml`

For the full update — conda/Homebrew refresh, local MLX repo pulls and source
builds, stub regeneration, and the runtime smoke — run `make update`
(which runs `src/tools/update.sh`).

### Cleaning Build Artifacts

Build artifacts can accumulate during development, especially when working with local MLX builds:

```bash
# Clean project artifacts (recommended for regular cleanup)
make clean              # Remove __pycache__, build/, dist/, test caches

# Deep clean including type stubs
make clean-all          # Deep clean

# Clean local MLX development repositories
make clean-mlx          # Remove build artifacts from mlx, mlx-vlm, mlx-data

# Preview what would be cleaned (dry run)
make clean-mlx-dry-run

# Or use the script directly
bash src/tools/clean_builds.sh
bash src/tools/clean_builds.sh --dry-run  # See what would be cleaned
```

**What gets cleaned:**

- Python build artifacts: `build/`, `dist/`, `*.egg-info/`, `.eggs/`
- Bytecode caches: `__pycache__/`, `*.pyc`, `*.pyo`
- Test caches: `.pytest_cache/`, `.mypy_cache/`

**Note on Metal kernel caches:** Compiled Metal shaders are cached by macOS in system temp directories and persist across builds. These are automatically managed by the Metal framework and cleared on reboot. To manually clear (use with caution): `sudo rm -rf /tmp/com.apple.metal/*`

According to the [official MLX documentation](https://ml-explore.github.io/mlx/build/html/install.html#binary-size-minimization), the Metal kernel cache persists across reboots and is system-managed for performance.

**When to clean:**

- Before rebuilding MLX with different compiler flags (for example changing
  `MLX_METAL_JIT`)
- When experiencing odd build or runtime errors
- To free up disk space
- After switching between different MLX versions or branches

**Note**: This does not change dependency bounds. To allow newer or different
versions, edit `src/pyproject.toml`, run `make deps-sync`, then run
`make update`.

## Release Process

Until automated releases are set up, version bumps are a short manual workflow:

1. Choose the next semantic version:

   - **Patch** (`x.y.Z`) for fixes, docs-only updates, and tooling changes
   - **Minor** (`x.Y.z`) for backward-compatible features or new report fields
   - **Major** (`X.y.z`) for breaking CLI, schema, or workflow changes

2. Update the package version in `src/pyproject.toml`:

   ```toml
   [project]
   version = "0.5.0"
   ```

3. Move the relevant entries from `CHANGELOG.md`'s `Unreleased` section into a
   dated release heading such as `## [0.5.0] - 2026-04-19`, then leave a fresh
   empty `Unreleased` section at the top.

4. Run the full quality gate from the repo root:

   ```bash
   make quality
   ```

5. Commit the release with an explicit message and push it:

   ```bash
   git add CHANGELOG.md docs/CONTRIBUTING.md src/pyproject.toml
   git commit -m "chore: release 0.5.0"
   git push
   ```

6. Start the next cycle by recording any follow-up work back under
   `CHANGELOG.md`'s `Unreleased` section.

## Getting Help

- Check [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for coding conventions
- Review existing issues on GitHub
- Ask questions in issue comments
- Run `make help` to see available commands

## Code of Conduct

- Be respectful and constructive
- Focus on what is best for the project
- Show empathy towards other contributors

---

Thank you for contributing! 🎉
