from pathlib import Path
import os
import sys

from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

repo_id = os.environ.get("HF_SPACE_REPO_ID", "sjhallo07/marcos-mora-chatbot-multimodal")
token = os.environ.get("HF_TOKEN")

if not token:
    print("HF_TOKEN not set in environment or .env", file=sys.stderr)
    sys.exit(2)

repo_root = Path(__file__).resolve().parents[1]

ignore_patterns = [
    ".env",
    ".env.*",
    ".git/**",
    ".venv/**",
    ".venv313/**",
    ".venv*/**",
    "**/.venv/**",
    "**/.venv313/**",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".ipynb_checkpoints/**",
    "data/faiss/**",
    "third_party/**",
]

delete_patterns = [
    ".venv/**",
    ".venv313/**",
    "**/.venv/**",
    "**/.venv313/**",
    ".pytest_cache/**",
    "__pycache__/**",
]

api = HfApi()

try:
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=False,
        token=token,
    )
    print(f"Space created or already exists: {repo_id}")
except Exception as e:
    print(f"Create repo notice: {e}")

try:
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(repo_root),
        ignore_patterns=ignore_patterns,
        delete_patterns=delete_patterns,
        token=token,
        commit_message="Deploy Hugging Face Space from local workspace",
    )
    print(f"Uploaded workspace to https://huggingface.co/spaces/{repo_id}")
except Exception as e:
    print(f"Upload failed: {e}", file=sys.stderr)
    sys.exit(1)
