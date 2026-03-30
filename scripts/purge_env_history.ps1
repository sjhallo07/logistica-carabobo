#!/usr/bin/env pwsh
<#
Script to back up a mirror of the repo and remove .env from history using git-filter-repo.
Usage: run from project root: pwsh .\scripts\purge_env_history.ps1
#>
param()

Write-Host "This script will help purge .env from the repo history. It will create a mirror backup first." -ForegroundColor Yellow
$repo = (Get-Location).Path
$backup = Join-Path $repo "../repo-backup.git"
if (Test-Path $backup) {
    Write-Host "Backup path $backup already exists. Remove or rename it and re-run." -ForegroundColor Red
    exit 1
}

Write-Host "Creating mirror clone to: $backup"
git clone --mirror . $backup
if ($LASTEXITCODE -ne 0) { Write-Host "git clone failed" -ForegroundColor Red; exit 1 }

Write-Host "Run git-filter-repo on mirror to remove .env..."
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found. Install it via: pip install git-filter-repo" -ForegroundColor Yellow
    exit 1
}

Push-Location $backup
git filter-repo --invert-paths --path .env
if ($LASTEXITCODE -ne 0) { Write-Host "git-filter-repo failed" -ForegroundColor Red; Pop-Location; exit 1 }

Write-Host "Pushing cleaned mirror to origin (force)..."
git push --force --all
git push --force --tags
Pop-Location
Write-Host "Done. Verify remote and coordinate with collaborators to reclone." -ForegroundColor Green
