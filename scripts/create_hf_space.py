from huggingface_hub import HfApi
import os, sys

repo_id = 'sjhallo07/marcos-mora-chatbot-multimodal'

token = os.environ.get('HF_TOKEN')
if not token:
    print('HF_TOKEN not set in environment', file=sys.stderr)
    sys.exit(2)

api = HfApi()
try:
    api.create_repo(repo_id=repo_id, repo_type='space', space_sdk='docker', private=False, token=token)
    print('Created repo', repo_id)
except Exception as e:
    print('Create repo error (may already exist):', e)
