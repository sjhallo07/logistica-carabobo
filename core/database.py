import os
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_API_URL = os.getenv("SUPABASE_API_URL")

# Try to import supabase client; if unavailable (e.g., local dev without deps),
# provide lightweight stubs so tests can run without external dependencies.
try:
    from supabase import create_client, Client  # type: ignore
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def insert_knowledge(content: str, metadata: Dict[str, Any], embedding: List[float]):
        return supabase.table("logistics_knowledge").insert({
            "content": content,
            "metadata": metadata,
            "embedding": embedding
        }).execute()

    def save_instagram_coupons(coupons: List[Dict[str, Any]], source: str, source_id: str = None):
        # coupons: list of {permalink, timestamp, codes, caption}
        rows = []
        for c in coupons:
            rows.append({
                "source": source,
                "source_id": source_id,
                "permalink": c.get("permalink"),
                "timestamp": c.get("timestamp"),
                "codes": c.get("codes"),
                "caption": c.get("caption")
            })
        return supabase.table("instagram_coupons").insert(rows).execute()

    def save_coupon(coupon: Dict[str, Any]):
        """Save a single coupon record into a relational table called 'coupons' using Supabase client."""
        try:
            return supabase.table("coupons").insert(coupon).execute()
        except Exception as e:
            return {"status": "error", "error": str(e), "coupon": coupon}

    def match_documents(query_embedding: List[float], match_threshold: float = 0.75, match_count: int = 5):
        try:
            # Supabase RPC expects positional args depending on the function signature.
            # Try calling with named params (some setups expect a single json param too).
            return supabase.rpc("match_documents", {
                "match_count": match_count,
                "match_threshold": match_threshold,
                "query_embedding": query_embedding
            }).execute()
        except Exception as e:
            # Graceful fallback: return empty result with error info so caller can handle it.
            return {"status": "error", "error": str(e), "hint": "Ensure the SQL function public.match_documents(...) exists in Supabase. See sql/create_match_documents.sql in the repo."}

except Exception:
    # Fallback stubs for environments without supabase installed.
    supabase = None  # type: ignore

    def insert_knowledge(content: str, metadata: Dict[str, Any], embedding: List[float]):
        # No-op stub for tests/local runs.
        return {"status": "stubbed", "content": content, "metadata": metadata}

    def match_documents(query_embedding: List[float], match_threshold: float = 0.75, match_count: int = 5):
        # Return empty list as default when no DB is available.
        return []

    def save_instagram_coupons(coupons: List[Dict[str, Any]], source: str, source_id: str = None):
        # Stub: just return input for local/dev
        # If SUPABASE_API_URL is provided, try to use the REST Data API as a fallback
        if SUPABASE_API_URL and SUPABASE_KEY:
            try:
                import json
                import httpx
                rows = []
                for c in coupons:
                    rows.append({
                        "source": source,
                        "source_id": source_id,
                        "permalink": c.get("permalink"),
                        "timestamp": c.get("timestamp"),
                        "codes": c.get("codes"),
                        "caption": c.get("caption")
                    })
                url = f"{SUPABASE_API_URL.rstrip('/')}/rest/v1/instagram_coupons"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                resp = httpx.post(url, headers=headers, content=json.dumps(rows), timeout=10.0)
                resp.raise_for_status()
                return {"status": "inserted", "rows": resp.json()}
            except Exception as e:
                return {"status": "error", "error": str(e), "stub_rows": coupons}
        return {"status": "stubbed", "rows": coupons, "source": source, "source_id": source_id}

    def save_coupon(coupon: Dict[str, Any]):
        """Save a single coupon record into a relational table called 'coupons'.
        Expected fields: code, place, business, address, expiration, source
        """
        try:
            if SUPABASE_API_URL and SUPABASE_KEY:
                import json
                import httpx
                url = f"{SUPABASE_API_URL.rstrip('/')}/rest/v1/coupons"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                resp = httpx.post(url, headers=headers, content=json.dumps([coupon]), timeout=10.0)
                resp.raise_for_status()
                return {"status": "inserted", "rows": resp.json()}
        except Exception as e:
            return {"status": "error", "error": str(e), "coupon": coupon}
        return {"status": "stubbed", "coupon": coupon}
