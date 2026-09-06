# Claude Code Instructions

All project conventions, architecture, environment setup, coding standards,
and change workflows are maintained in a single canonical file:

**Read [.github/copilot-instructions.md](.github/copilot-instructions.md) before making any changes.**

Key reminders:

- Always use `conda activate mlx-vlm` before running Python
- Before `make quality`, run `make format`, clear Ruff lint issues with
  `make -C src lint-fix` / `make lint`, then run the full quality gate
- `src/check_models.py` is an intentional single-file monolith — do not split it
- Add tests to existing `src/tests/test_*.py` files, never create standalone scripts
- Validation tests must not rewrite tracked `src/output/` assets or leave
  generated files anywhere under `src/`; send generated output to a
  temp directory (`tmp_path`). Ordinary gitignored tool caches
  (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.skylos`)
  are fine
- Keep `CHANGELOG.md` (`[Unreleased]`) up to date for maintainer-relevant changes, including refactors and tooling updates
- For upstream mlx-vlm isolation/issues/cache discovery, read `.agents/skills/`
  (`native-mlx-vlm-repro`, `upstream-mlx-vlm-issues`, `hf-cache-mlx-vlm-models`);
  use conda + pip only (never `uv`)
