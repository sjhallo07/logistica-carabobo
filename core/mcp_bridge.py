import httpx
from typing import Dict, Any
import os
import re
from datetime import datetime

# Env
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_BUSINESS_ID = os.getenv("IG_BUSINESS_ID")
IG_API_VERSION = os.getenv("IG_API_VERSION", "v17.0")

class RemoteMCPBridge:
    BASE_URL = "http://api.logistica-carabobo.io/mcp"

    ALLOWED_SEGMENTS = ["San Diego", "Lomas del Este", "Guacara", "La Entrada"]

    def get_traffic_arc(self, segment: str) -> Dict[str, Any]:
        if segment not in self.ALLOWED_SEGMENTS:
            raise ValueError(f"Segmento inválido: {segment}. Debe ser uno de: {', '.join(self.ALLOWED_SEGMENTS)}")
        resp = httpx.post(f"{self.BASE_URL}/get_traffic_arc", json={"segment": segment}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def verify_logistics_coupon(self, code: str) -> Dict[str, Any]:
        if not isinstance(code, str):
            raise ValueError("El código debe ser un string")
        resp = httpx.post(f"{self.BASE_URL}/verify_logistics_coupon", json={"code": code}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ----- Instagram / Web search helpers -----
    def _extract_coupons_from_text(self, text: str):
        if not text:
            return []
        candidates = []
        # Look for explicit patterns like 'code: ABC123' or 'cupón ABC123'
        patterns = [r'(?i)\\b(?:code|cup[oó]n|promo|descuento)[:\\s-]*([A-Z0-9]{4,12})\\b',
                    r'\\b([A-Z0-9]{5,12})\\b']
        for pat in patterns:
            for m in re.findall(pat, text):
                candidates.append(m)
        # unique
        return list(dict.fromkeys([c.upper() for c in candidates]))

    def search_instagram_profile(self, profile_url: str, limit: int = 25) -> Dict[str, Any]:
        """Search a public Instagram profile for recent posts and extract coupon codes.
        Uses Instagram Graph API when IG_ACCESS_TOKEN is set; otherwise returns stubbed results.
        """
        if IG_ACCESS_TOKEN and IG_BUSINESS_ID:
            # Ideally use Graph API: fetch media from the profile if accessible. Here we attempt a naive approach.
            try:
                # NOTE: For production use the IG Graph endpoints with proper permissions.
                resp = httpx.get(
                    f"https://graph.facebook.com/{IG_API_VERSION}/{IG_BUSINESS_ID}/media",
                    params={"fields": "id,caption,permalink,timestamp,media_type", "limit": limit, "access_token": IG_ACCESS_TOKEN},
                    timeout=10
                )
                resp.raise_for_status()
                items = resp.json().get("data", [])
                results = []
                for it in items:
                    caps = it.get("caption", "")
                    codes = self._extract_coupons_from_text(caps)
                    if codes:
                        results.append({"permalink": it.get("permalink"), "timestamp": it.get("timestamp"), "codes": codes, "caption": caps})
                return {"source": "instagram_profile", "profile_url": profile_url, "results": results}
            except Exception as e:
                return {"error": str(e), "stub": True}
        # Fallback stub: return empty or a simulated coupon
        simulated = [{"permalink": profile_url, "timestamp": datetime.utcnow().isoformat(), "codes": ["FIRST2026"], "caption": "¡Usa el código FIRST2026 para 20% off!"}]
        return {"source": "instagram_profile_stub", "profile_url": profile_url, "results": simulated}

    def search_instagram_hashtag(self, hashtag: str, limit: int = 25, since: str = None) -> Dict[str, Any]:
        """Search posts for a hashtag and extract coupon codes. Uses Graph API when configured, otherwise stub."""
        tag = hashtag.lstrip('#')
        if IG_ACCESS_TOKEN and IG_BUSINESS_ID:
            try:
                # Get hashtag id
                resp = httpx.get(
                    f"https://graph.facebook.com/{IG_API_VERSION}/ig_hashtag_search",
                    params={"user_id": IG_BUSINESS_ID, "q": tag, "access_token": IG_ACCESS_TOKEN},
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if not data:
                    return {"source": "instagram_hashtag", "hashtag": tag, "results": []}
                hashtag_id = data[0].get("id")
                # fetch recent media
                resp2 = httpx.get(
                    f"https://graph.facebook.com/{IG_API_VERSION}/{hashtag_id}/recent_media",
                    params={"user_id": IG_BUSINESS_ID, "fields": "id,caption,permalink,timestamp,media_type", "limit": limit, "access_token": IG_ACCESS_TOKEN},
                    timeout=10
                )
                resp2.raise_for_status()
                items = resp2.json().get("data", [])
                results = []
                for it in items:
                    caps = it.get("caption", "")
                    codes = self._extract_coupons_from_text(caps)
                    if codes:
                        results.append({"permalink": it.get("permalink"), "timestamp": it.get("timestamp"), "codes": codes, "caption": caps})
                return {"source": "instagram_hashtag", "hashtag": tag, "results": results}
            except Exception as e:
                return {"error": str(e), "stub": True}
        # Fallback stubbed result
        simulated = [{"permalink": f"https://www.instagram.com/p/FAKE_{tag}/", "timestamp": datetime.utcnow().isoformat(), "codes": ["PROMO10"], "caption": f"Usa PROMO10 para descuento en {tag}!"}]
        return {"source": "instagram_hashtag_stub", "hashtag": tag, "results": simulated}

    def web_search_google(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Perform a simple web search by querying Google and extracting result titles/links.
        Note: scraping Google is brittle and may be rate-limited; for production use use an API like SerpAPI or Google's Custom Search API.
        """
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)"}
            resp = httpx.get("https://www.google.com/search", params={"q": query, "num": limit}, headers=headers, timeout=10)
            resp.raise_for_status()
            html = resp.text
            # Very simple extraction of links via regex (best-effort)
            links = re.findall(r'<a href="/url\?q=(https?://[^&\\"]+)', html)
            titles = re.findall(r'<h3.*?>(.*?)</h3>', html)
            results = []
            for i, link in enumerate(links[:limit]):
                title = titles[i] if i < len(titles) else link
                results.append({"title": re.sub('<[^<]+?>', '', title), "link": link})
            return {"source": "google_search", "query": query, "results": results}
        except Exception as e:
            return {"error": str(e), "stub": True}
