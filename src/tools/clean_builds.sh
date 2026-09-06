#!/usr/bin/env bash
# Clean build artifacts and caches from local MLX development repositories.
#
# This script removes:
# - Python build artifacts (build/, dist/, *.egg-info/, .eggs/)
# - Bytecode caches (__pycache__/, *.pyc, *.pyo)
# - Test caches (.pytest_cache/)
# - Type checking caches (.mypy_cache/)
# - Linter caches (.ruff_cache/)
# - macOS Finder metadata (.DS_Store)
# - Manual validation outputs (output/test_*, files or directories)
#
# Note: This does NOT remove compiled Metal kernels from system caches.
# Metal kernel caches are managed by the Metal framework and cleared on reboot
# or via system cache cleaning utilities.
#
# Usage:
#   bash tools/clean_builds.sh              # Clean local MLX repos + check_models project
#   bash tools/clean_builds.sh --dry-run    # Show what would be cleaned
#   bash tools/clean_builds.sh --help       # Show this help

set -euo pipefail

DRY_RUN=0

show_help() {
	cat <<'EOF'
Clean build artifacts and caches from local MLX development repositories.

Usage:
  bash tools/clean_builds.sh              # Clean local MLX repos + check_models project
  bash tools/clean_builds.sh --dry-run    # Show what would be cleaned
  bash tools/clean_builds.sh --help       # Show this help
EOF
}

# Parse arguments
for arg in "$@"; do
	case $arg in
		--dry-run)
			DRY_RUN=1
			shift
			;;
		--help|-h)
			show_help
			exit 0
			;;
		*)
			echo "Unknown option: $arg"
			echo "Run with --help for usage information"
			exit 1
			;;
	esac
done

# Determine directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Repositories to clean (in order)
MLX_REPOS=("mlx" "mlx-vlm" "mlx-data")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 MLX Build Artifact Cleanup"
if [[ $DRY_RUN -eq 1 ]]; then
	echo "   DRY RUN MODE - No files will be deleted"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_CLEANED=0

remove_direct_child_dir() {
	local parent_dir=$1
	local child_name=$2
	local target=""

	case $child_name in
		build|dist|.eggs)
			;;
		*)
			echo "Refusing to remove unexpected direct child: $child_name" >&2
			return 1
			;;
	esac

	target="$parent_dir/$child_name"
	if [[ ! -d "$target" ]]; then
		return 0
	fi

	case "$target" in
		"$parent_dir"/*)
			;;
		*)
			echo "Refusing to remove path outside parent: $target" >&2
			return 1
			;;
	esac

	find "$target" -depth -delete
}

# Clean function
clean_directory() {
	local dir=$1
	local name=$2
	
	if [[ ! -d "$dir" ]]; then
		return
	fi
	
	echo "Cleaning: $name"
	echo "  Path: $dir"
	
	local cleaned=0
	
	# Build directories
	for pattern in "build" "dist" ".eggs"; do
		if [[ -d "$dir/$pattern" ]]; then
			if [[ $DRY_RUN -eq 1 ]]; then
				echo "  [DRY RUN] Would remove: $pattern/"
			else
				remove_direct_child_dir "$dir" "$pattern"
				echo "  ✓ Removed: $pattern/"
			fi
			((cleaned++))
		fi
	done
	
	# Egg-info directories
	while IFS= read -r -d '' egginfo; do
		if [[ $DRY_RUN -eq 1 ]]; then
			echo "  [DRY RUN] Would remove: $(basename "$egginfo")"
		else
			rm -rf "$egginfo"
			echo "  ✓ Removed: $(basename "$egginfo")"
		fi
		((cleaned++))
	done < <(find "$dir" -maxdepth 1 -type d -name '*.egg-info' -print0 2>/dev/null)
	
	# Cache directories (including linter caches)
	for cache in "__pycache__" ".pytest_cache" ".mypy_cache" ".ruff_cache"; do
		local count=0
		if [[ $DRY_RUN -eq 1 ]]; then
			count=$(find "$dir" -type d -name "$cache" 2>/dev/null | wc -l | tr -d ' ')
			if [[ $count -gt 0 ]]; then
				echo "  [DRY RUN] Would remove: $count $cache directories"
				((cleaned++))
			fi
		else
			while IFS= read -r -d '' cachedir; do
				rm -rf "$cachedir"
				((count++))
			done < <(find "$dir" -type d -name "$cache" -print0 2>/dev/null)
			if [[ $count -gt 0 ]]; then
				echo "  ✓ Removed: $count $cache directories"
				((cleaned++))
			fi
		fi
	done
	
	# Bytecode files
	local pyc_count=0
	if [[ $DRY_RUN -eq 1 ]]; then
		pyc_count=$(find "$dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) 2>/dev/null | wc -l | tr -d ' ')
		if [[ $pyc_count -gt 0 ]]; then
			echo "  [DRY RUN] Would remove: $pyc_count bytecode files"
			((cleaned++))
		fi
	else
		while IFS= read -r -d '' pycfile; do
			rm -f "$pycfile"
			((pyc_count++))
		done < <(find "$dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -print0 2>/dev/null)
		if [[ $pyc_count -gt 0 ]]; then
			echo "  ✓ Removed: $pyc_count bytecode files"
			((cleaned++))
		fi
	fi
	
	# .DS_Store files (macOS Finder metadata)
	local ds_count=0
	if [[ $DRY_RUN -eq 1 ]]; then
		ds_count=$(find "$dir" -type f -name '.DS_Store' 2>/dev/null | wc -l | tr -d ' ')
		if [[ $ds_count -gt 0 ]]; then
			echo "  [DRY RUN] Would remove: $ds_count .DS_Store files"
			((cleaned++))
		fi
	else
		while IFS= read -r -d '' dsfile; do
			rm -f "$dsfile"
			((ds_count++))
		done < <(find "$dir" -type f -name '.DS_Store' -print0 2>/dev/null)
		if [[ $ds_count -gt 0 ]]; then
			echo "  ✓ Removed: $ds_count .DS_Store files"
			((cleaned++))
		fi
	fi
	
	if [[ $cleaned -eq 0 ]]; then
		echo "  (no artifacts found)"
	fi
	
	TOTAL_CLEANED=$((TOTAL_CLEANED + cleaned))
	echo ""
}

# Clean local MLX repositories
for repo in "${MLX_REPOS[@]}"; do
	REPO_PATH="$PARENT_DIR/$repo"
	if [[ -d "$REPO_PATH/.git" ]]; then
		clean_directory "$REPO_PATH" "$repo (local dev)"
	fi
done

# Clean check_models project
clean_directory "$SCRIPTS_DIR/src" "mlx-vlm-check (check_models)"

# Clean manual validation outputs (`--output-dir output/test_*`; pytest itself
# writes only to its temp directory)
OUTPUT_DIR="$SCRIPTS_DIR/src/output"
if [[ -d "$OUTPUT_DIR" ]]; then
	echo "Cleaning: Manual validation outputs"
	echo "  Path: $OUTPUT_DIR"
	test_cleaned=0
	while IFS= read -r -d '' testfile; do
		if [[ $DRY_RUN -eq 1 ]]; then
			echo "  [DRY RUN] Would remove: $(basename "$testfile")"
		else
			rm -rf "$testfile"
			echo "  ✓ Removed: $(basename "$testfile")"
		fi
		((test_cleaned++))
	done < <(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -name 'test_*' -print0 2>/dev/null)
	if [[ $test_cleaned -eq 0 ]]; then
		echo "  (no test output files found)"
	else
		TOTAL_CLEANED=$((TOTAL_CLEANED + test_cleaned))
	fi
	echo ""
fi

# Clean root-level caches in check_models project
echo "Cleaning: check_models root caches"
echo "  Path: $SCRIPTS_DIR"
root_cleaned=0
for cache in ".pytest_cache" ".mypy_cache" ".ruff_cache"; do
	if [[ -d "$SCRIPTS_DIR/$cache" ]]; then
		if [[ $DRY_RUN -eq 1 ]]; then
			echo "  [DRY RUN] Would remove: $cache/"
		else
			rm -rf "${SCRIPTS_DIR:?}/$cache"
			echo "  ✓ Removed: $cache/"
		fi
		((root_cleaned++))
	fi
done
# Clean .DS_Store at root level
if [[ -f "$SCRIPTS_DIR/.DS_Store" ]]; then
	if [[ $DRY_RUN -eq 1 ]]; then
		echo "  [DRY RUN] Would remove: .DS_Store"
	else
		rm -f "$SCRIPTS_DIR/.DS_Store"
		echo "  ✓ Removed: .DS_Store"
	fi
	((root_cleaned++))
fi
if [[ $root_cleaned -eq 0 ]]; then
	echo "  (no artifacts found)"
fi
TOTAL_CLEANED=$((TOTAL_CLEANED + root_cleaned))
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $DRY_RUN -eq 1 ]]; then
	echo "DRY RUN COMPLETE"
	echo "Run without --dry-run to actually remove files"
else
	if [[ $TOTAL_CLEANED -gt 0 ]]; then
		echo "✓ Cleanup complete - removed $TOTAL_CLEANED artifact groups"
	else
		echo "✓ All clean - no artifacts found"
	fi
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Note: Metal kernel caches are managed by macOS and persist in"
echo "system temp directories. They're automatically cleared on reboot."
echo "Inspect /tmp/com.apple.metal/ before removing any specific stale cache files."
echo ""
echo "Build artifacts cleaned. To rebuild MLX repos from scratch:"
echo "  cd /path/to/mlx && cmake -S . -B build && cmake --build build"
echo "  Then run: pip install -e ."
