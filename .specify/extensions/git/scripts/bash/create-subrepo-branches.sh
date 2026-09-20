#!/usr/bin/env bash
# Git extension: create-subrepo-branches.sh
# Creates (or switches to) a feature branch inside the nested sub-repositories
# that will be modified during /speckit-implement, mirroring the workspace
# feature branch but following each sub-repo's Git Flow naming convention
# (e.g. feature/2086011-excel-export-formulas).
#
# The workspace root is itself a git repository; the sub-repos are independent
# git repositories nested under it. The core create-new-feature.sh only ever
# branches the workspace repo. This script complements it for the sub-repos.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BRANCH_NAME=""
PREFIX="feature"
ALLOW_EXISTING=false
DRY_RUN=false
JSON=false
TARGET_REPOS=()

usage() {
    echo "Usage: ./create-subrepo-branches.sh [--json] [--dry-run] [--allow-existing-branch] [--branch-name <name>] [--prefix <prefix>] --target-repos <repo1> [<repo2> ...]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch-name) BRANCH_NAME="$2"; shift 2 ;;
        --prefix) PREFIX="$2"; shift 2 ;;
        --allow-existing-branch) ALLOW_EXISTING=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --json) JSON=true; shift ;;
        --help) usage; exit 0 ;;
        --target-repos) shift; while [[ $# -gt 0 && "$1" != --* ]]; do TARGET_REPOS+=("$1"); shift; done ;;
        *) TARGET_REPOS+=("$1"); shift ;;
    esac
done

find_project_root() {
    local current="$1"
    while true; do
        if [[ -e "$current/.specify" || -e "$current/.git" ]]; then
            printf '%s\n' "$current"; return 0
        fi
        local parent
        parent="$(dirname "$current")"
        [[ "$parent" == "$current" ]] && return 1
        current="$parent"
    done
}

WORKSPACE_ROOT="$(find_project_root "$SCRIPT_DIR")" || {
    echo "Could not determine workspace root (no .specify or .git found)." >&2; exit 1; }

repo_has_git() {
    local repo_root="$1"
    { [[ -d "$repo_root/.git" || -f "$repo_root/.git" ]]; } && \
        command -v git >/dev/null 2>&1 && \
        git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

if [[ -z "$BRANCH_NAME" ]]; then
    if ! BRANCH_NAME="$(git -C "$WORKSPACE_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)" || [[ -z "$BRANCH_NAME" ]]; then
        echo "Could not resolve the workspace feature branch. Pass --branch-name explicitly." >&2; exit 1
    fi
fi

# Strip any pre-existing type prefix so we don't double it (e.g. feature/feature/...).
# The workspace feature branch carries a Git Flow "tipo/" segment; the id-assunto
# suffix never contains a '/', so removing a single leading segment is safe.
SUFFIX=$(echo "$BRANCH_NAME" | sed -E 's#^[^/]+/##')
PREFIX="${PREFIX%/}"
[[ -z "$PREFIX" ]] && PREFIX="feature"
TARGET_BRANCH="$PREFIX/$SUFFIX"

if [[ ${#TARGET_REPOS[@]} -eq 0 ]]; then
    echo "[specify] Warning: No target sub-repos provided; nothing to branch." >&2
    $JSON && printf '{"BRANCH_NAME":"%s","RESULTS":[]}\n' "$TARGET_BRANCH"
    exit 0
fi

json_entries=()
had_error=false

emit() {
    local status="$1" repo="$2" path="$3" detail="$4"
    if $JSON; then
        json_entries+=("{\"REPO\":\"$repo\",\"PATH\":\"$path\",\"BRANCH\":\"$TARGET_BRANCH\",\"STATUS\":\"$status\",\"DETAIL\":\"$detail\"}")
    else
        printf '  [%s] %s -> %s (%s)\n' "$status" "$repo" "$TARGET_BRANCH" "$detail"
    fi
}

for repo in "${TARGET_REPOS[@]}"; do
    [[ -z "$repo" ]] && continue
    if [[ "$repo" = /* ]]; then repo_path="$repo"; else repo_path="$WORKSPACE_ROOT/$repo"; fi

    if [[ ! -e "$repo_path" ]]; then emit "skipped" "$repo" "$repo_path" "path not found"; continue; fi
    resolved="$(cd "$repo_path" && pwd)"
    if [[ "$resolved" == "$WORKSPACE_ROOT" ]]; then
        emit "skipped" "$repo" "$resolved" "workspace root (handled by core feature branch)"; continue
    fi
    if ! repo_has_git "$resolved"; then emit "skipped" "$repo" "$resolved" "not a git repository"; continue; fi

    if $DRY_RUN; then emit "dry-run" "$repo" "$resolved" "would create/switch branch"; continue; fi

    current_branch="$(git -C "$resolved" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
    if [[ "$current_branch" == "$TARGET_BRANCH" ]]; then
        emit "exists" "$repo" "$resolved" "already on branch"; continue
    fi

    if git -C "$resolved" checkout -q -b "$TARGET_BRANCH" 2>/dev/null; then
        emit "created" "$repo" "$resolved" "from $current_branch"; continue
    fi

    if git -C "$resolved" branch --list "$TARGET_BRANCH" | grep -q .; then
        if $ALLOW_EXISTING; then
            if git -C "$resolved" checkout -q "$TARGET_BRANCH" 2>/dev/null; then
                emit "switched" "$repo" "$resolved" "from $current_branch"
            else
                emit "error" "$repo" "$resolved" "branch exists but checkout failed"; had_error=true
            fi
        else
            emit "error" "$repo" "$resolved" "branch already exists (use --allow-existing-branch)"; had_error=true
        fi
    else
        emit "error" "$repo" "$resolved" "failed to create branch"; had_error=true
    fi
done

if $JSON; then
    printf '{"BRANCH_NAME":"%s","RESULTS":[%s]}\n' "$TARGET_BRANCH" "$(IFS=,; echo "${json_entries[*]}")"
else
    echo "BRANCH_NAME: $TARGET_BRANCH"
fi

$had_error && exit 1
exit 0
