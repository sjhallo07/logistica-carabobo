#!/usr/bin/env bash
set -euo pipefail

REMOTE=${1:-origin}
BRANCH=${2:-master}

echo "This script will remove .env from git history using git-filter-repo."
echo "A bare mirror backup will be created at ../repo-backup.git"

if ! command -v python >/dev/null 2>&1; then
  echo "python is required. Please install it and ensure it's in PATH." >&2
  exit 1
fi

if ! python -c "import git_filter_repo" >/dev/null 2>&1; then
  echo "Installing git-filter-repo via pip..."
  python -m pip install --upgrade pip
  python -m pip install git-filter-repo
fi

CWD=$(pwd)
BACKUP_DIR="$(dirname "$CWD")/repo-backup.git"
if [ -d "$BACKUP_DIR" ]; then
  echo "Backup mirror already exists at $BACKUP_DIR"
else
  echo "Creating mirror clone at $BACKUP_DIR"
  git clone --mirror . "$BACKUP_DIR"
fi

echo "Rewriting history to remove .env from all commits..."
git filter-repo --invert-paths --path .env

echo "Expire reflog and garbage collect"
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "Force pushing rewritten history to remote '$REMOTE' branch '$BRANCH'"
git push --force "$REMOTE" refs/heads/"$BRANCH"

echo "Finished. Rotate any compromised tokens immediately."
