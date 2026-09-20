#!/usr/bin/env pwsh
# Git extension: create-subrepo-branches.ps1
# Creates (or switches to) a feature branch inside the nested sub-repositories
# that will be modified during /speckit-implement, mirroring the workspace
# feature branch but following each sub-repo's Git Flow naming convention
# (e.g. feature/2086011-excel-export-formulas).
#
# The workspace root is itself a git repository; the sub-repos are independent
# git repositories nested under it. The core create-new-feature.ps1 only ever
# branches the workspace repo. This script complements it for the sub-repos.
[CmdletBinding()]
param(
    [string]$BranchName,
    [string]$Prefix = 'feature',
    [Parameter()]
    [string[]]$TargetRepos = @(),
    [switch]$AllowExistingBranch,
    [switch]$DryRun,
    [switch]$Json,
    [switch]$Help
)
$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host "Usage: ./create-subrepo-branches.ps1 [-Json] [-DryRun] [-AllowExistingBranch] [-BranchName <name>] [-Prefix <prefix>] -TargetRepos <repo1>,<repo2>..."
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -BranchName <name>     Feature branch suffix to use. Defaults to the workspace current branch."
    Write-Host "  -Prefix <prefix>       Git Flow type prefix for the sub-repo branch (default: feature)."
    Write-Host "  -TargetRepos <list>    Comma-separated sub-repo directory names/paths to branch (the repos that will be changed)."
    Write-Host "  -AllowExistingBranch   Switch to the branch if it already exists instead of failing."
    Write-Host "  -DryRun                Compute branch name and targets without creating branches."
    Write-Host "  -Json                  Output result as JSON."
    Write-Host "  -Help                  Show this help message."
    exit 0
}

function Find-ProjectRoot {
    param([string]$StartDir)
    $current = (Resolve-Path $StartDir).Path
    while ($true) {
        foreach ($marker in @('.specify', '.git')) {
            if (Test-Path (Join-Path $current $marker)) {
                return $current
            }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) { return $null }
        $current = $parent
    }
}

$workspaceRoot = Find-ProjectRoot -StartDir $PSScriptRoot
if (-not $workspaceRoot) {
    Write-Error "Could not determine workspace root (no .specify or .git found)."
    exit 1
}

function Test-RepoHasGit {
    param([string]$RepoRoot)
    try {
        if (-not (Test-Path (Join-Path $RepoRoot '.git'))) { return $false }
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return $false }
        git -C $RepoRoot rev-parse --is-inside-work-tree 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# Resolve the feature branch suffix: explicit -BranchName, else the workspace current branch.
if ([string]::IsNullOrWhiteSpace($BranchName)) {
    $workspaceBranch = (git -C $workspaceRoot rev-parse --abbrev-ref HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($workspaceBranch)) {
        Write-Error "Could not resolve the workspace feature branch. Pass -BranchName explicitly."
        exit 1
    }
    $BranchName = $workspaceBranch.Trim()
}

# Strip any pre-existing type prefix so we don't double it (e.g. feature/feature/...).
# The workspace feature branch carries a Git Flow "tipo/" segment; the id-assunto
# suffix never contains a '/', so removing a single leading segment is safe.
$suffix = $BranchName -replace '^[^/]+/', ''
$Prefix = $Prefix.Trim().TrimEnd('/')
if ([string]::IsNullOrWhiteSpace($Prefix)) { $Prefix = 'feature' }
$targetBranch = "$Prefix/$suffix"

if (-not $TargetRepos -or $TargetRepos.Count -eq 0) {
    $msg = "[specify] Warning: No target sub-repos provided; nothing to branch."
    if ($Json) { [Console]::Error.WriteLine($msg) } else { Write-Warning $msg }
    if ($Json) {
        [PSCustomObject]@{ BRANCH_NAME = $targetBranch; RESULTS = @() } | ConvertTo-Json -Compress
    }
    exit 0
}

$results = @()
foreach ($repo in $TargetRepos) {
    if ([string]::IsNullOrWhiteSpace($repo)) { continue }

    if ([System.IO.Path]::IsPathRooted($repo)) {
        $repoPath = $repo
    } else {
        $repoPath = Join-Path $workspaceRoot $repo
    }

    $entry = [ordered]@{
        REPO   = $repo
        PATH   = $repoPath
        BRANCH = $targetBranch
        STATUS = ''
        DETAIL = ''
    }

    if (-not (Test-Path $repoPath)) {
        $entry.STATUS = 'skipped'; $entry.DETAIL = 'path not found'
        $results += [PSCustomObject]$entry; continue
    }

    $resolvedRepo = (Resolve-Path $repoPath).Path
    if ($resolvedRepo -eq $workspaceRoot) {
        $entry.STATUS = 'skipped'; $entry.DETAIL = 'workspace root (handled by core feature branch)'
        $results += [PSCustomObject]$entry; continue
    }

    if (-not (Test-RepoHasGit -RepoRoot $resolvedRepo)) {
        $entry.STATUS = 'skipped'; $entry.DETAIL = 'not a git repository'
        $results += [PSCustomObject]$entry; continue
    }

    if ($DryRun) {
        $entry.STATUS = 'dry-run'; $entry.DETAIL = 'would create/switch branch'
        $results += [PSCustomObject]$entry; continue
    }

    $currentBranch = ''
    try { $currentBranch = (git -C $resolvedRepo rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch {}

    if ($currentBranch -eq $targetBranch) {
        $entry.STATUS = 'exists'; $entry.DETAIL = 'already on branch'
        $results += [PSCustomObject]$entry; continue
    }

    $createError = git -C $resolvedRepo checkout -q -b $targetBranch 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        $entry.STATUS = 'created'; $entry.DETAIL = "from $currentBranch"
        $results += [PSCustomObject]$entry; continue
    }

    $existing = git -C $resolvedRepo branch --list $targetBranch 2>$null
    if ($existing) {
        if ($AllowExistingBranch) {
            $switchError = git -C $resolvedRepo checkout -q $targetBranch 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                $entry.STATUS = 'switched'; $entry.DETAIL = "from $currentBranch"
            } else {
                $entry.STATUS = 'error'; $entry.DETAIL = "branch exists but checkout failed: $($switchError.Trim())"
            }
        } else {
            $entry.STATUS = 'error'; $entry.DETAIL = "branch '$targetBranch' already exists (use -AllowExistingBranch to switch)"
        }
    } else {
        $entry.STATUS = 'error'; $entry.DETAIL = "failed to create branch: $($createError.Trim())"
    }
    $results += [PSCustomObject]$entry
}

if ($Json) {
    $obj = [PSCustomObject]@{
        BRANCH_NAME = $targetBranch
        RESULTS     = $results
    }
    if ($DryRun) { $obj | Add-Member -NotePropertyName 'DRY_RUN' -NotePropertyValue $true }
    $obj | ConvertTo-Json -Depth 5 -Compress
} else {
    Write-Output "BRANCH_NAME: $targetBranch"
    foreach ($r in $results) {
        Write-Output ("  [{0}] {1} -> {2} ({3})" -f $r.STATUS, $r.REPO, $r.BRANCH, $r.DETAIL)
    }
}

$hadError = $results | Where-Object { $_.STATUS -eq 'error' }
if ($hadError) { exit 1 }
