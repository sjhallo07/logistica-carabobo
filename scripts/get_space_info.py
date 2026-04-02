import json
import os

from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

repo_id = os.environ.get("HF_SPACE_REPO_ID", "sjhallo07/marcos-mora-chatbot-multimodal")
token = os.environ.get("HF_TOKEN")

if not token:
    print("HF_TOKEN not set")
    raise SystemExit(2)

api = HfApi()
try:
    info = api.space_info(repo_id, token=token)
    print(json.dumps(info.__dict__, default=str, indent=2))
except Exception as e:
    print('Error:', e)
