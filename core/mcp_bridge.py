import httpx
from typing import Dict, Any
import os
import re
from datetime import datetime
import asyncio
from typing import List
from urllib.parse import quote, unquote

# Env
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_BUSINESS_ID = os.getenv("IG_BUSINESS_ID")
IG_API_VERSION = os.getenv("IG_API_VERSION", "v17.0")

class RemoteMCPBridge:
    # Determine MCP endpoint from environment:
    # Priority: MCP_BASE_URL env -> derive from SUPABASE_URL env -> default to local MCP
    _env_mcp = os.getenv("MCP_BASE_URL")
    if _env_mcp:
        BASE_URL = _env_mcp
    else:
        # If SUPABASE_URL is set (e.g. https://<project_ref>.supabase.co) auto-construct the MCP proxy URL
        _supabase = os.getenv("SUPABASE_URL")
        if _supabase:
            # extract project ref from host
            try:
                # remove scheme
                host = _supabase.split("//")[-1]
                project_ref = host.split('.')[0]
                BASE_URL = f"https://mcp.supabase.com/mcp?project_ref={project_ref}&features=docs%2Caccount%2Cdatabase%2Cdebugging%2Cdevelopment%2Cfunctions%2Cbranching%2Cstorage"
            except Exception:
                BASE_URL = "http://localhost:9000/mcp"
        else:
            # Use MCP_PORT or PORT env var if provided, otherwise default to 9000
            _port = os.getenv("MCP_PORT") or os.getenv("PORT") or "9000"
            BASE_URL = f"http://localhost:{_port}/mcp"

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

    def add_coupon(self, coupon: Dict[str, Any]) -> Dict[str, Any]:
        """Post a coupon record to the MCP add_coupon endpoint."""
        resp = httpx.post(f"{self.BASE_URL}/add_coupon", json=coupon, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ----- Instagram / Web search helpers -----
    def _extract_coupons_from_text(self, text: str):
        if not text:
            return []
        candidates = []
        # Look for explicit patterns like 'code: ABC123' or 'cupón ABC123'
        # patterns: explicit key words followed by code, or standalone alphanumeric tokens 5-12 chars
        # Require at least one digit in the fallback token to avoid capturing common words
        patterns = [r"\b(?:code|cup[oó]n|promo|descuento)[:\s-]*([A-Z0-9]{4,12})\b",
                r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{5,12}\b"]
        for pat in patterns:
            for m in re.findall(pat, text, flags=re.IGNORECASE):
                # m may be a tuple if groups; ensure it's a string
                if isinstance(m, tuple):
                    m = m[0]
                candidates.append(m)
        # unique
        return list(dict.fromkeys([c.upper() for c in candidates]))

    def _normalize_instagram_username(self, profile_url: str) -> str:
        value = (profile_url or "").strip()
        if not value:
            raise ValueError("empty_profile_url")

        if value.startswith("@"):
            value = value[1:]

        if "instagram.com" in value:
            value = value.rstrip("/")
            value = value.split("/")[-1].split("?")[0]

        value = value.strip().strip("/")
        if not value:
            raise ValueError("No username parsed")
        return value

    def _extract_posts_from_instagram_payload(self, payload: Dict[str, Any], limit: int, profile_url: str) -> List[Dict[str, Any]]:
        posts: List[Dict[str, Any]] = []
        edges = []

        if not isinstance(payload, dict):
            return posts

        if (data := payload.get('items')):
            edges = data
        elif (graphql := payload.get('graphql')) and graphql.get('user'):
            edges = graphql['user'].get('edge_owner_to_timeline_media', {}).get('edges', [])
        elif (data2 := payload.get('data')) and isinstance(data2, dict):
            user = data2.get('user', {})
            if user:
                edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
            if not edges and data2.get('xdt_api__v1__feed__user_timeline_graphql_connection'):
                edges = data2.get('xdt_api__v1__feed__user_timeline_graphql_connection', {}).get('edges', [])

        for it in edges[:limit]:
            node = it.get('node', it) if isinstance(it, dict) else it
            caption = ''
            if isinstance(node, dict):
                caption = node.get('caption') or node.get('edge_media_to_caption', {}).get('edges', [])
                if isinstance(caption, list) and caption:
                    caption = caption[0].get('node', {}).get('text', '')
                if 'edge_media_to_caption' in node and not caption:
                    cap_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                    if cap_edges:
                        caption = cap_edges[0].get('node', {}).get('text', '')
                permalink = node.get('permalink') or f"https://www.instagram.com/p/{node.get('shortcode', '')}/"
                timestamp = node.get('taken_at_timestamp') or node.get('timestamp') or node.get('date')
                if isinstance(timestamp, int):
                    ts = datetime.utcfromtimestamp(timestamp).isoformat()
                else:
                    ts = timestamp or datetime.utcnow().isoformat()
                codes = self._extract_coupons_from_text(caption)
                posts.append({
                    "permalink": permalink or profile_url,
                    "timestamp": ts,
                    "codes": codes,
                    "caption": caption,
                })

        return posts

    def _extract_search_results_from_html(self, html: str, limit: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not html:
            return results

        # Google-style results
        google_pairs = re.findall(r'<a href="/url\?q=(https?://[^&\"]+)[^>]*>.*?<h3.*?>(.*?)</h3>', html, flags=re.IGNORECASE | re.DOTALL)
        for link, title in google_pairs:
            clean_title = re.sub('<[^<]+?>', '', title).strip()
            if clean_title and link:
                results.append({"title": clean_title, "link": link})
            if len(results) >= limit:
                return results[:limit]

        # DuckDuckGo-style results
        ddg_pairs = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
        for raw_link, title in ddg_pairs:
            link = raw_link
            if 'uddg=' in raw_link:
                link = unquote(raw_link.split('uddg=')[-1].split('&')[0])
            clean_title = re.sub('<[^<]+?>', '', title).strip()
            if clean_title and link.startswith('http'):
                results.append({"title": clean_title, "link": link})
            if len(results) >= limit:
                break

        # Unique by link preserving order
        deduped = []
        seen = set()
        for item in results:
            if item['link'] not in seen:
                seen.add(item['link'])
                deduped.append(item)
        return deduped[:limit]

    def _run_async(self, coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

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
        # Fallback to public web search instead of synthetic coupon data
        return self._run_async(self.search_instagram_profile_public(profile_url, limit=limit))

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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            resp = httpx.get(
                "https://www.google.com/search",
                params={"q": query, "num": limit, "hl": "es"},
                headers=headers,
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
            results = self._extract_search_results_from_html(resp.text, limit=limit)
            if results:
                return {"source": "google_search", "query": query, "results": results}

            # Fallback to DuckDuckGo HTML if Google markup yields no parseable results.
            resp2 = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=15,
                follow_redirects=True,
            )
            resp2.raise_for_status()
            ddg_results = self._extract_search_results_from_html(resp2.text, limit=limit)
            return {"source": "duckduckgo_search", "query": query, "results": ddg_results}
        except Exception as e:
            return {"error": str(e), "stub": True}

    async def search_instagram_profile_public(self, profile_url: str, limit: int = 25, delay: float = 1.0) -> Dict[str, Any]:
        """Attempt to fetch a public Instagram profile without API (best-effort).
        Tries the public JSON endpoints first, then falls back to HTML scraping.
        Adds small delays to avoid aggressive scraping. Returns extracted posts with coupon codes.
        """
        # extract username
        try:
            username = self._normalize_instagram_username(profile_url)
        except Exception:
            return {"error": "invalid_profile_url", "profile_url": profile_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/{username}/",
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # Try current web profile endpoint first, then older JSON endpoints.
            json_urls = [
                f"https://www.instagram.com/api/v1/users/web_profile_info/?username={quote(username)}",
                f"https://www.instagram.com/{username}/?__a=1&__d=dis",
                f"https://www.instagram.com/{username}/?__a=1"
            ]
            for url in json_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        j = None
                        try:
                            j = resp.json()
                        except Exception:
                            # sometimes returns JS; fall through
                            j = None
                        if j:
                            posts = self._extract_posts_from_instagram_payload(j, limit=limit, profile_url=profile_url)
                            if posts:
                                await asyncio.sleep(delay)
                                return {"source": "instagram_public_json", "username": username, "results": posts}
                except httpx.HTTPStatusError:
                    pass
                except Exception:
                    pass

            # Fallback: fetch HTML and try to parse window._sharedData or ld+json
            try:
                resp = await client.get(f"https://www.instagram.com/{username}/")
                if resp.status_code != 200:
                    return {"error": f"http_{resp.status_code}", "profile_url": profile_url}
                html = resp.text
                # try window._sharedData = { ... };
                m = re.search(r"window\._sharedData\s*=\s*(\{.*?\})\s*;", html, re.DOTALL)
                data = None
                if not m:
                    # try LD+JSON
                    m2 = re.search(r"<script type=\"application/ld\+json\">(.*?)</script>", html, re.DOTALL)
                    if m2:
                        try:
                            import json
                            data = json.loads(m2.group(1))
                        except Exception:
                            data = None
                else:
                    try:
                        import json
                        data = json.loads(m.group(1))
                    except Exception:
                        data = None

                results = []
                if data:
                    # try to find media entries
                    entries = []
                    if (graphql := data.get('entry_data')):
                        # older structure
                        for k in graphql.values():
                            for item in k:
                                media = item.get('graphql', {}).get('user', {}).get('edge_owner_to_timeline_media', {}).get('edges', [])
                                if media:
                                    entries.extend(media)
                    # generic search for captions in JSON
                    def walk_for_captions(obj):
                        if isinstance(obj, dict):
                            for kk, vv in obj.items():
                                if kk in ('caption', 'edge_media_to_caption'):
                                    if isinstance(vv, str):
                                        yield vv
                                    elif isinstance(vv, dict):
                                        edges = vv.get('edges', [])
                                        for e in edges:
                                            yield e.get('node', {}).get('text', '')
                                else:
                                    for x in walk_for_captions(vv):
                                        yield x
                        elif isinstance(obj, list):
                            for item in obj:
                                for x in walk_for_captions(item):
                                    yield x

                    # collect captions
                    caps = list(walk_for_captions(data))
                    for c in caps[:limit]:
                        codes = self._extract_coupons_from_text(c)
                        if codes:
                            results.append({"permalink": profile_url, "timestamp": datetime.utcnow().isoformat(), "codes": codes, "caption": c})

                # final fallback: return honest empty result instead of synthetic coupon data
                if not results:
                    return {
                        "source": "instagram_public_html",
                        "username": username,
                        "results": [],
                        "note": "No public coupon-like matches were extracted from the profile response",
                    }
                await asyncio.sleep(delay)
                return {"source": "instagram_public_html", "username": username, "results": results}
            except Exception as e:
                return {"error": str(e), "stub": True}
