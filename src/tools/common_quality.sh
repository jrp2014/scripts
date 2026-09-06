#!/usr/bin/env bash
# Shared helpers for local hooks, static quality checks, and runtime smoke.

CONDA_ENV="${CONDA_ENV:-mlx-vlm}"

quality_find_conda_bin() {
    local candidate=""

    if command -v conda >/dev/null 2>&1; then
        command -v conda
        return 0
    fi

    for candidate in \
        "$HOME/miniconda3/bin/conda" \
        "$HOME/miniforge3/bin/conda" \
        "$HOME/mambaforge/bin/conda" \
        "/opt/homebrew/Caskroom/miniconda/base/bin/conda" \
        "/opt/homebrew/Caskroom/miniforge/base/bin/conda" \
        "/opt/homebrew/Caskroom/mambaforge/base/bin/conda" \
        "/opt/homebrew/anaconda3/bin/conda" \
        "$HOME/anaconda3/bin/conda"
    do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

quality_tools_dir() {
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

quality_src_root() {
    cd "$(quality_tools_dir)/.." && pwd
}

quality_repo_root() {
    cd "$(quality_tools_dir)/../.." && pwd
}

quality_find_conda_env_python() {
    local conda_bin=""
    local env_prefix=""
    local env_python=""
    local candidate_base=""

    if [ -n "${CONDA_PREFIX:-}" ] && [ "$(basename "$CONDA_PREFIX")" = "$CONDA_ENV" ]; then
        env_python="$CONDA_PREFIX/bin/python"
        if [ -x "$env_python" ]; then
            printf '%s\n' "$env_python"
            return 0
        fi
    fi

    if conda_bin="$(quality_find_conda_bin)"; then
        env_prefix="$("$conda_bin" env list 2>/dev/null | awk -v env_name="$CONDA_ENV" '$1 == env_name { print $NF; exit }')"
        if [ -n "$env_prefix" ] && [ -x "$env_prefix/bin/python" ]; then
            printf '%s\n' "$env_prefix/bin/python"
            return 0
        fi
    fi

    for candidate_base in \
        "$HOME/miniconda3" \
        "$HOME/miniforge3" \
        "$HOME/mambaforge" \
        "/opt/homebrew/Caskroom/miniconda/base" \
        "/opt/homebrew/Caskroom/miniforge/base" \
        "/opt/homebrew/Caskroom/mambaforge/base" \
        "/opt/homebrew/anaconda3" \
        "$HOME/anaconda3"
    do
        env_python="$candidate_base/envs/$CONDA_ENV/bin/python"
        if [ -x "$env_python" ]; then
            printf '%s\n' "$env_python"
            return 0
        fi
    done

    return 1
}

quality_python_fallback_allowed() {
    case "${QUALITY_ALLOW_PYTHON_FALLBACK:-}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
    esac

    case "${CI:-}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
    esac

    return 1
}

quality_path_tool_fallback_allowed() {
    case "${QUALITY_ALLOW_PATH_TOOLS:-}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
    esac

    return 1
}

quality_setup_python() {
    local env_python=""


    if env_python="$(quality_find_conda_env_python)"; then
        QUALITY_PYTHON="$env_python"
        QUALITY_PYTHON_SOURCE="conda-env:$CONDA_ENV"
    elif quality_python_fallback_allowed; then
        if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
            QUALITY_PYTHON="$CONDA_PREFIX/bin/python"
            QUALITY_PYTHON_SOURCE="active-conda:$CONDA_PREFIX"
        elif command -v python3 >/dev/null 2>&1; then
            QUALITY_PYTHON="$(command -v python3)"
            QUALITY_PYTHON_SOURCE="fallback:python3"
        elif command -v python >/dev/null 2>&1; then
            QUALITY_PYTHON="$(command -v python)"
            QUALITY_PYTHON_SOURCE="fallback:python"
        else
            echo "❌ Unable to resolve required Python interpreter." >&2
            return 1
        fi
    else
        echo "❌ Unable to resolve required conda environment '$CONDA_ENV'." >&2
        echo "   Activate it first: conda activate $CONDA_ENV" >&2
        echo "   CI may set CI=true; local overrides may set QUALITY_ALLOW_PYTHON_FALLBACK=1." >&2
        return 1
    fi

    export QUALITY_PYTHON
    export QUALITY_PYTHON_SOURCE
}

quality_require_command() {
    local command_name="$1"
    local install_hint="$2"

    if command -v "$command_name" >/dev/null 2>&1; then
        return 0
    fi

    echo "❌ Required command '$command_name' not found." >&2
    if [ -n "$install_hint" ]; then
        echo "   $install_hint" >&2
    fi
    return 1
}

    quality_find_python_tool() {
        local tool_name="$1"
        local python_bin_dir=""

        python_bin_dir="$(dirname "$QUALITY_PYTHON")"
        if [ -x "$python_bin_dir/$tool_name" ]; then
            printf '%s\n' "$python_bin_dir/$tool_name"
            return 0
        fi

        if quality_path_tool_fallback_allowed && command -v "$tool_name" >/dev/null 2>&1; then
            command -v "$tool_name"
            return 0
        fi

        return 1
    }

    quality_require_python_tool() {
        local tool_name="$1"
        local install_hint="$2"

        if quality_find_python_tool "$tool_name" >/dev/null 2>&1; then
            return 0
        fi

        echo "❌ Required command '$tool_name' not found." >&2
        if [ -n "$install_hint" ]; then
            echo "   $install_hint" >&2
        fi
        return 1
    }

    quality_run_python_tool() {
        local tool_name="$1"
        local tool_path=""

        tool_path="$(quality_find_python_tool "$tool_name")" || return 1
        shift
        "$tool_path" "$@"
    }

    # Skylos's grade renderer copies its README badge to the system clipboard
    # (pyperclip, copy_badge=True with no CLI switch), overwriting whatever the
    # user had there. pyperclip is a hard Skylos dependency, but the import is
    # lazy and the copy is wrapped in `except pyperclip.PyperclipException`, so
    # a throwaway stub module that raises it turns the copy into a silent
    # no-op. The stub lives only for the duration of the call and is never a
    # tracked source file, so it is invisible to the linters and to Skylos.
    quality_run_skylos() {
        local stub_dir status
        # Explicit template: GNU mktemp (Linux CI) requires the X's, BSD mktemp
        # (macOS) accepts them; `-t prefix` alone is BSD-only.
        stub_dir="$(mktemp -d "${TMPDIR:-/tmp}/skylos-clipboard-shim.XXXXXX")" || return 1
        printf '%s\n' \
            '"""Clipboard shim: keep Skylos from overwriting the user clipboard."""' \
            '' \
            '' \
            'class PyperclipException(RuntimeError):' \
            '    """Raised so Skylos takes its quiet no-clipboard branch."""' \
            '' \
            '' \
            'def copy(_text):' \
            '    raise PyperclipException("clipboard disabled by check_models quality tooling")' \
            '' \
            '' \
            'def paste():' \
            '    return ""' \
            > "$stub_dir/pyperclip.py"
        PYTHONPATH="$stub_dir${PYTHONPATH:+:$PYTHONPATH}" quality_run_python_tool skylos "$@"
        status=$?
        rm -rf "$stub_dir"
        return "$status"
    }

    quality_resolve_python_path() {
        if [ -n "${QUALITY_PYTHON:-}" ] && [ -x "$QUALITY_PYTHON" ]; then
            printf '%s\n' "$QUALITY_PYTHON"
            return 0
        fi

        if [ -n "${QUALITY_PYTHON:-}" ] && command -v "$QUALITY_PYTHON" >/dev/null 2>&1; then
            command -v "$QUALITY_PYTHON"
            return 0
        fi

        return 1
    }

    quality_print_ty_diagnostics() {
        local python_path="$1"
        local ty_path="$2"
        shift 2

        echo "[ty] target conda env: ${CONDA_ENV}"
        echo "[ty] active conda env: ${CONDA_DEFAULT_ENV:-<none>}"
        echo "[ty] resolved python (${QUALITY_PYTHON_SOURCE:-unknown}): ${python_path}"
        echo "[ty] resolved ty: ${ty_path}"
        echo "[ty] check targets: ${*:-check_models.py}"

        if [ "${QUALITY_PYTHON_SOURCE:-}" != "conda-env:${CONDA_ENV}" ]; then
            echo "[ty] warning: target env '${CONDA_ENV}' was not resolved directly; import resolution may differ from the expected repo conda environment." >&2
        fi
    }

    quality_run_ty_check() {
        local python_path=""
        local ty_path=""

        python_path="$(quality_resolve_python_path)" || return 1
        ty_path="$(quality_find_python_tool ty)" || return 1
        quality_print_ty_diagnostics "$python_path" "$ty_path" "$@"
        "$ty_path" check --no-respect-ignore-files --python "$python_path" "$@"
    }

    quality_write_pyrefly_config() {
        local config_path="$1"
        local python_path="$2"
        local pyproject_path=""
        local main_checkout_root=""

        pyproject_path="$(quality_src_root)/pyproject.toml"
        # Linked worktrees (for example .claude/worktrees/*) share the primary
        # checkout's gitignored assets such as typings/; resolve that root so
        # relative search-path entries can fall back to it.
        main_checkout_root="$(git -C "$(quality_src_root)" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || main_checkout_root=""
        if [ -n "$main_checkout_root" ]; then
            main_checkout_root="$(dirname "$main_checkout_root")"
        fi
        "$QUALITY_PYTHON" - "$config_path" "$python_path" "$pyproject_path" "$main_checkout_root" <<'PY'
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

config_path = Path(sys.argv[1])
python_path = Path(sys.argv[2]).resolve()
pyproject_path = Path(sys.argv[3])
main_checkout_root = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None

tool_config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["tool"]["pyrefly"]
tool_config = dict(tool_config)
tool_config.pop("conda-environment", None)
tool_config["python-interpreter-path"] = str(python_path)

# Project discovery must work from linked worktrees under hidden directories
# (for example .claude/worktrees/*), where parent-repo ignore files such as
# .git/info/exclude and Pyrefly's hidden-directory heuristic would otherwise
# match the entire checkout and leave nothing to check.
tool_config["use-ignore-files"] = False
tool_config["disable-project-excludes-heuristics"] = True

# Disabling the heuristics/ignore files drops Pyrefly's default excludes and
# the gitignore-driven ones, so restore them explicitly to keep the gate as
# strict as the primary checkout without scanning generated junk.
# Anchored to the package root (the config file itself lives outside the
# tree, so relative globs would resolve against the wrong directory).
src_root = pyproject_path.parent.resolve()
explicit_excludes = [
    f"{src_root}/{pattern}"
    for pattern in (
        "**/node_modules/",
        "**/__pycache__/",
        "**/venv/**/*",
        "**/.*/**",
        "**/build/",
        "**/dist/",
        "**/*.egg-info/",
        "**/output/test*",
    )
]
project_excludes = [
    pattern if Path(pattern).is_absolute() else f"{src_root}/{pattern}"
    for pattern in tool_config.get("project-excludes", [])
]
project_excludes.extend(
    pattern for pattern in explicit_excludes if pattern not in project_excludes
)
tool_config["project-excludes"] = project_excludes

# The config file lives outside the tree, so tell Pyrefly where the project
# is instead of letting it infer an import root from the config's directory.
tool_config.setdefault("project-includes", [f"{src_root}/**/*.py"])

# Absolutize search-path entries; a relative entry missing from this checkout
# (worktrees do not carry gitignored typings/) resolves against the primary
# checkout instead so both use the same stub source. The package root itself
# always leads so `check_models`, `check_models_data` and `tools` resolve.
checkout_root = src_root.parent
search_path_entries: list[str] = [str(src_root)]
for entry in tool_config.get("search-path", []):
    entry_path = Path(entry)
    resolved = entry_path if entry_path.is_absolute() else (src_root / entry_path).resolve()
    if not resolved.exists() and main_checkout_root is not None:
        try:
            relative_to_checkout = resolved.relative_to(checkout_root)
        except ValueError:
            relative_to_checkout = None
        if relative_to_checkout is not None:
            fallback = main_checkout_root / relative_to_checkout
            if fallback.exists():
                resolved = fallback
    if str(resolved) not in search_path_entries:
        search_path_entries.append(str(resolved))
tool_config["search-path"] = search_path_entries


def format_toml(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_toml(item) for item in value) + "]"
    raise TypeError(f"Unsupported Pyrefly config value type: {type(value).__name__}")
lines: list[str] = []
for key, value in tool_config.items():
    lines.append(f"{key} = {format_toml(value)}")

config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
    }

    quality_print_pyrefly_diagnostics() {
        local python_path="$1"
        local pyrefly_path="$2"
        local config_path="$3"
        local target_display=""
        shift 3

        if [ "$#" -eq 0 ]; then
            target_display="<project discovery>"
        elif [ "$#" -gt 8 ]; then
            target_display="$# explicit files (git ls-files enumeration)"
        else
            target_display="$*"
        fi

        echo "[pyrefly] active conda env: ${CONDA_DEFAULT_ENV:-<none>}"
        echo "[pyrefly] resolved python (${QUALITY_PYTHON_SOURCE:-unknown}): ${python_path}"
        echo "[pyrefly] resolved pyrefly: ${pyrefly_path}"
        echo "[pyrefly] generated config: ${config_path}"
        echo "[pyrefly] check targets: ${target_display}"
    }

    # Explicit targets switch Pyrefly to single-file checking mode, which
    # skips filesystem discovery entirely — so the gate's file set cannot be
    # eaten by ignore files or future discovery heuristics, independent of the
    # generated config neutralizing the known ones. git ls-files is the same
    # authority the other gates align with and keeps gitignore semantics
    # without hand-mirrored exclude globs.
    quality_pyrefly_default_targets() {
        git -C "$(quality_src_root)" ls-files --cached --others --exclude-standard -- '*.py' '*.pyi' \
            | LC_ALL=C sort -u \
            | grep -v '^tools/\.archived/' || true
    }

    quality_run_pyrefly_check() {
        local python_path=""
        local pyrefly_path=""
        local config_path=""
        local output_path=""
        local exit_code=0
        local -a targets=("$@")

        if [ "${#targets[@]}" -eq 0 ]; then
            local src_root=""
            src_root="$(quality_src_root)"
            while IFS= read -r target; do
                targets+=("$src_root/$target")
            done < <(quality_pyrefly_default_targets)
            if [ "${#targets[@]}" -eq 0 ]; then
                echo "❌ Pyrefly target enumeration found no Python files (git ls-files returned nothing)." >&2
                return 1
            fi
        fi

        python_path="$(quality_resolve_python_path)" || return 1
        pyrefly_path="$(quality_find_python_tool pyrefly)" || return 1
        # Outside the tree: the tests that exercise this wrapper must not
        # write under src/, and a temporary config left behind by an aborted
        # run should not show up in git status. The generated config carries
        # absolute paths, so its location does not matter to Pyrefly.
        config_path="$(mktemp "${TMPDIR:-/tmp}/pyrefly-quality.XXXXXX")"
        output_path="$(mktemp "${TMPDIR:-/tmp}/pyrefly-output.XXXXXX")"

        if ! quality_write_pyrefly_config "$config_path" "$python_path"; then
            rm -f "$config_path"
            rm -f "$output_path"
            return 1
        fi

        quality_print_pyrefly_diagnostics "$python_path" "$pyrefly_path" "$config_path" "${targets[@]}"
        if "$pyrefly_path" check \
            -c "$config_path" \
            --min-severity warn \
            --output-format full-text \
            "${targets[@]}" 2>&1 | tee "$output_path"; then
            exit_code=0
        else
            exit_code=$?
        fi

        if [ "$exit_code" -eq 0 ] && grep -Eq '^[[:space:]]*WARN([[:space:]]|$)' "$output_path"; then
            echo "❌ Pyrefly emitted warnings; treat warnings as quality failures." >&2
            exit_code=1
        fi

        rm -f "$config_path"
        rm -f "$output_path"
        return "$exit_code"
    }

quality_validate_yaml_files() {
    "$QUALITY_PYTHON" - "$@" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as err:
    print("❌ PyYAML is required for YAML validation in quality hooks.")
    print("   Activate the repo conda env first: conda activate mlx-vlm")
    raise SystemExit(1) from err

errors: list[str] = []

for raw_path in sys.argv[1:]:
    path = Path(raw_path)
    try:
        text = path.read_text(encoding="utf-8")
        list(yaml.safe_load_all(text))
    except OSError as err:
        errors.append(f"{path}: could not read file ({err})")
    except yaml.YAMLError as err:
        errors.append(f"{path}: invalid YAML ({err})")

if errors:
    print("❌ YAML validation failed:")
    for error in errors:
        print(f"   - {error}")
    raise SystemExit(1)
PY
}

quality_run_markdownlint() {
    local src_root
    src_root="$(quality_src_root)"

    if [ -x "$src_root/node_modules/.bin/markdownlint-cli2" ]; then
        "$src_root/node_modules/.bin/markdownlint-cli2" "$@"
        return
    fi

    if command -v markdownlint-cli2 >/dev/null 2>&1; then
        markdownlint-cli2 "$@"
        return
    fi

    if command -v npx >/dev/null 2>&1; then
        npx --no-install markdownlint-cli2 "$@"
        return
    fi

    echo "❌ markdownlint-cli2 not found." >&2
    echo "   Install with: npm install --prefix src" >&2
    return 1
}
