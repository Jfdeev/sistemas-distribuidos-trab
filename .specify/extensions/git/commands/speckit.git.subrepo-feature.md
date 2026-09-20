---
description: "Create the feature branch inside the nested sub-repositories that will be modified"
---

# Create Sub-Repository Feature Branches

Create (or switch to) the feature branch inside the **nested sub-repositories** that will be changed during implementation, mirroring the workspace feature branch but following each sub-repo's Git Flow naming convention (e.g. `feature/2086011-excel-export-formulas`).

The workspace root is a git repository, and each top-level sub-folder containing a `.git` (e.g. `vale-connect-base-products-availability-v2`, `integra-packages`, `vale-ibp-platform-frontend-resources`, `vale-ibp-platform-base-docker-images`, `vale-integra-pipelines`) is an **independent** git repository. The core `speckit.git.feature` command only branches the workspace repo; this command complements it for the sub-repos where code actually changes.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Prerequisites

- Verify Git is available by running `git rev-parse --is-inside-work-tree 2>/dev/null`. If Git is not available, warn the user and skip.
- A workspace feature branch must already exist (created by `speckit.git.feature` during `/speckit-specify`). The sub-repo branch suffix is derived from the workspace branch unless `-BranchName` / `--branch-name` is provided.

## Determine the target sub-repositories

Only branch the sub-repos that will actually be modified. Derive the set from the implementation plan:

0. Locate the feature directory the same way the core commands do: run `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` (or read `.specify/feature.json`) to resolve `FEATURE_DIR`, then read `FEATURE_DIR/tasks.md` and `FEATURE_DIR/plan.md`.
1. Read the file paths referenced by `tasks.md` (and `plan.md` if needed).
2. For each path, take the **top-level workspace folder** (the first path segment, e.g. `vale-connect-base-products-availability-v2/services/...` → `vale-connect-base-products-availability-v2`).
3. Keep only the distinct folders that are independent git repositories (contain `.git`) and are **not** the workspace root.
4. Pass that distinct set as the target repos.

If no sub-repo is targeted (all changes live in the workspace repo), this command is a no-op.

## Branch Prefix

Determine the Git Flow type prefix by checking configuration in this order:

1. Check `.specify/extensions/git/git-config.yml` for `subrepo_branch_prefix` value
2. Default to `feature` if absent

## Execution

Run the appropriate script based on your platform. List each target sub-repo:

- **Bash**: `.specify/extensions/git/scripts/bash/create-subrepo-branches.sh --json --allow-existing-branch --target-repos <repo1> <repo2> ...`
- **PowerShell**: `.specify/extensions/git/scripts/powershell/create-subrepo-branches.ps1 -Json -AllowExistingBranch -TargetRepos <repo1>,<repo2>,...`

**IMPORTANT**:
- Always include the JSON flag (`--json` / `-Json`) so the output can be parsed reliably.
- The script reads the workspace current branch automatically; pass `-BranchName` / `--branch-name` only to override it.
- `-AllowExistingBranch` / `--allow-existing-branch` switches to the branch if it already exists (re-running implementation is safe and idempotent).
- Use `-DryRun` / `--dry-run` to preview which repos would be branched without making changes.

## Output

The script outputs JSON with:
- `BRANCH_NAME`: The composed sub-repo branch name (e.g. `feature/2086011-excel-export-formulas`)
- `RESULTS`: One entry per target repo with `REPO`, `PATH`, `BRANCH`, `STATUS` (`created` | `switched` | `exists` | `skipped` | `error` | `dry-run`) and `DETAIL`

## Graceful Degradation

- A target path that is not a git repository, does not exist, or is the workspace root is skipped with a reason.
- If Git is not installed, the script exits without making changes.
- The script exits non-zero only if a real branch creation/switch failed (`STATUS: error`).
