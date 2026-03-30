param(
    [string]$Remote = 'origin',
    [string]$Branch = 'master'
)

Write-Host "This script will help remove .env from git history using git-filter-repo."
Write-Host "It will create a bare mirror clone in ../repo-backup.git as a safety copy. Do NOT run this on a critical repo without backups."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is required. Please install Python and ensure 'python' is in PATH."
    exit 1
}

# Ensure git-filter-repo is installed
try {
    python -c "import git_filter_repo" 2>$null
}
catch {
    Write-Host "Installing git-filter-repo via pip..."
    python -m pip install --upgrade pip
    python -m pip install git-filter-repo
}

$cwd = (Get-Location).ProviderPath
Write-Host "Working in: $cwd"

# Create a mirror backup
$backup = Join-Path (Split-Path $cwd -Parent) "repo-backup.git"
if (Test-Path $backup) {
    Write-Host "Backup mirror already exists at $backup"
}
else {
    Write-Host "Creating mirror clone at $backup"
    git clone --mirror . $backup
}

Write-Host "Rewriting history to remove .env from all commits..."
git filter-repo --invert-paths --path .env

Write-Host "Expiring reflog and garbage collecting to remove dangling objects"
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host "Force-pushing rewritten history to remote '$Remote' ($Branch). Ensure teammates coordinate as history will be rewritten."
git push --force $Remote refs/heads/$Branch

Write-Host "Done. Verify remote secret scanning alerts are cleared and rotate any compromised tokens immediately."
