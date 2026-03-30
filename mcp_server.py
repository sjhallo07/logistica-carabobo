from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.mcp_bridge import RemoteMCPBridge

app = FastAPI(title="Local MCP Server for Logistica Carabobo")
bridge = RemoteMCPBridge()

class ProfileSearch(BaseModel):
    profile_url: str
    limit: Optional[int] = 25

class HashtagSearch(BaseModel):
    hashtag: str
    limit: Optional[int] = 25
    since: Optional[str] = None

class WebSearch(BaseModel):
    query: str
    limit: Optional[int] = 10

class SegmentQuery(BaseModel):
    segment: str

class CouponQuery(BaseModel):
    code: str

@app.post('/mcp/search_instagram_profile')
async def search_instagram_profile(payload: ProfileSearch):
    try:
        result = await bridge.search_instagram_profile_public(payload.profile_url, limit=payload.limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/search_instagram_hashtag')
async def search_instagram_hashtag(payload: HashtagSearch):
    try:
        # bridge.search_instagram_hashtag is sync; call directly
        result = bridge.search_instagram_hashtag(payload.hashtag, limit=payload.limit, since=payload.since)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/web_search_google')
async def web_search_google(payload: WebSearch):
    try:
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
