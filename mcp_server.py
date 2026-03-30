from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from core.mcp_bridge import RemoteMCPBridge
import json
from pathlib import Path

app = FastAPI(title="Local MCP Server for Logistica Carabobo")
bridge = RemoteMCPBridge()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# Load allowed models from .vscode/mcp.json if present
def load_allowed_models() -> list:
    cfg_path = Path(__file__).resolve().parents[0] / '.vscode' / 'mcp.json'
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            server = cfg.get('servers', {}).get('my-mcp-server-df3ec9ee', {})
            return server.get('allowedModels', [])
    except Exception:
        return []

ALLOWED_MODELS = load_allowed_models()

class ProfileSearch(BaseModel):
    profile_url: str
    limit: Optional[int] = 25
    model: Optional[str] = None

class HashtagSearch(BaseModel):
    hashtag: str
    limit: Optional[int] = 25
    since: Optional[str] = None
    model: Optional[str] = None

class WebSearch(BaseModel):
    query: str
    limit: Optional[int] = 10
    model: Optional[str] = None

class SegmentQuery(BaseModel):
    segment: str

class CouponQuery(BaseModel):
    code: str

@app.post('/mcp/search_instagram_profile')
async def search_instagram_profile(payload: ProfileSearch):
    try:
        # optional model validation
        model = payload.model
        logger.info(f"search_instagram_profile called for %s (limit=%s) model=%s", payload.profile_url, payload.limit, model)
        if model and ALLOWED_MODELS and model not in ALLOWED_MODELS:
            raise HTTPException(status_code=400, detail=f"Model '{model}' is not allowed for this MCP server")
        result = await bridge.search_instagram_profile_public(payload.profile_url, limit=payload.limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/search_instagram_hashtag')
async def search_instagram_hashtag(payload: HashtagSearch):
    try:
        model = payload.model
        logger.info(f"search_instagram_hashtag called for %s (limit=%s) model=%s", payload.hashtag, payload.limit, model)
        if model and ALLOWED_MODELS and model not in ALLOWED_MODELS:
            raise HTTPException(status_code=400, detail=f"Model '{model}' is not allowed for this MCP server")
        # bridge.search_instagram_hashtag is sync; call directly
        result = bridge.search_instagram_hashtag(payload.hashtag, limit=payload.limit, since=payload.since)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/web_search_google')
async def web_search_google(payload: WebSearch):
    try:
        model = payload.model
        logger.info(f"web_search_google called for query=%s (limit=%s) model=%s", payload.query, payload.limit, model)
        if model and ALLOWED_MODELS and model not in ALLOWED_MODELS:
            raise HTTPException(status_code=400, detail=f"Model '{model}' is not allowed for this MCP server")
        result = bridge.web_search_google(payload.query, limit=payload.limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/get_traffic_arc')
async def get_traffic_arc(payload: SegmentQuery):
    try:
        return bridge.get_traffic_arc(payload.segment)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/mcp/verify_logistics_coupon')
async def verify_logistics_coupon(payload: CouponQuery):
    try:
        return bridge.verify_logistics_coupon(payload.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get('/mcp/health')
async def health():
    return {"status": "ok"}
