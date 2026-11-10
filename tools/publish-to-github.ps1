[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,
    [string]$Repository = 'rtynbirf/polymath-os',
    [string]$Branch = 'docs/agent-execution-pack'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Git {
    param([string[]]$GitArgs)
    & git -C $script:RepoRoot @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE" }
}

function Invoke-Gh {
    param([string[]]$GhArgs)
    & gh @GhArgs
    if ($LASTEXITCODE -ne 0) { throw "gh $($GhArgs -join ' ') failed with exit code $LASTEXITCODE" }
}

$PackRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RepoRoot = (Resolve-Path $RepoPath).Path
$script:RepoRoot = $RepoRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed or not in PATH.' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) is required. Install it and run: gh auth login --web' }

$top = (& git -C $RepoRoot rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0) { throw "RepoPath is not a Git repository: $RepoRoot" }
if ((Resolve-Path $top).Path -ne $RepoRoot) { throw 'RepoPath must be the repository root, not a nested directory.' }

$origin = (& git -C $RepoRoot remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0) { throw 'The repository has no origin remote.' }
if ($origin -notmatch '(?i)(github\.com[:/]rtynbirf/polymath-os)(\.git)?$') {
    throw "Origin does not match the requested repository. Found: $origin"
}

# Authentication is handled by the user's local GitHub CLI session; no PAT is read or stored here.
Invoke-Gh -GhArgs @('auth', 'status', '--hostname', 'github.com') | Out-Host
$baseBranch = (& gh repo view $Repository --json defaultBranchRef --jq '.defaultBranchRef.name')
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($baseBranch)) {
    throw "Cannot read repository metadata for $Repository. Confirm access with gh auth status."
}

$status = (& git -C $RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw 'Cannot read Git status.' }
if (-not [string]::IsNullOrWhiteSpace(($status -join ''))) {
    throw 'Working tree is not clean. Commit or stash existing work before publishing this documentation pack.'
}

$remoteBranch = (& git -C $RepoRoot ls-remote --heads origin $Branch)
if ($LASTEXITCODE -ne 0) { throw 'Cannot check remote branch. Check network and repository access.' }
if (-not [string]::IsNullOrWhiteSpace(($remoteBranch -join ''))) {
    throw "Remote branch already exists: $Branch. Choose another -Branch or inspect the existing branch."
}

Invoke-Git -GitArgs @('fetch', 'origin', $baseBranch)
Invoke-Git -GitArgs @('switch', '--create', $Branch, '--track', "origin/$baseBranch")

# Preflight all paths before copying anything. Identical files are safe; differing collisions stop the operation.
$files = @(Get-ChildItem -LiteralPath $PackRoot -File -Recurse -Force | Where-Object {
    $_.FullName -notmatch '[\\/]\.git[\\/]'
})
$conflicts = [System.Collections.Generic.List[string]]::new()
foreach ($file in $files) {
    $relative = $file.FullName.Substring($PackRoot.Length).TrimStart([char[]]@('\', '/'))
    $destination = Join-Path $RepoRoot $relative
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $sourceHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($sourceHash -ne $destinationHash) { $conflicts.Add($relative) }
    }
}
if ($conflicts.Count -gt 0) {
    throw ("Conflicting existing files; no files were copied. Merge these deliberately, then rerun:`n - " + ($conflicts -join "`n - "))
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($PackRoot.Length).TrimStart([char[]]@('\', '/'))
    $destination = Join-Path $RepoRoot $relative
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}

Push-Location $RepoRoot
try {
    & python tools/validate_pack.py
    if ($LASTEXITCODE -ne 0) { throw 'Agent pack validator failed.' }
    & python -m unittest discover -s tests -p 'test_validate_pack.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Agent pack unit tests failed.' }
    Invoke-Git -GitArgs @('diff', '--check')
    Invoke-Git -GitArgs @('add', '--all')
    $staged = (& git diff --cached --name-only)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect staged changes.' }
    if ([string]::IsNullOrWhiteSpace(($staged -join ''))) { throw 'No changes to publish; files may already be present.' }
    Invoke-Git -GitArgs @('commit', '-m', 'docs(agent-execution): add agent operating pack')
    Invoke-Git -GitArgs @('push', '--set-upstream', 'origin', $Branch)

    $body = @'
## Summary
- Add the agent execution contract, role definitions, task workflow, evidence model, security baseline, evaluation plan, and roadmap.
- Add JSON Schemas, initial read-only discovery tasks, templates, and package validation.
- Preserve existing repository files; the publisher refuses differing path collisions.

## Verification
- `python tools/validate_pack.py`
- `python -m unittest discover -s tests -p test_validate_pack.py -v`
- `git diff --check`

This PR adds the execution framework only. It does not claim that the multi-agent runtime is implemented or that repository discovery tasks have already run.
'@
    $prUrl = (& gh pr create --repo $Repository --base $baseBranch --head $Branch --title 'docs(agent-execution): add agent operating pack' --body $body)
    if ($LASTEXITCODE -ne 0) { throw "Branch was pushed, but PR creation failed. Create the PR manually from branch $Branch." }
    Write-Output "PUSHED_BRANCH=$Branch"
    Write-Output "PULL_REQUEST=$prUrl"
}
finally {
    Pop-Location
}
