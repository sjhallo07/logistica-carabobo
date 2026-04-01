import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_API_URL = os.getenv("SUPABASE_API_URL")
LOCAL_NON_RELATIONAL_STORE = Path("./data/non_relational_store.jsonl")


def _ensure_data_dir() -> None:
    LOCAL_NON_RELATIONAL_STORE.parent.mkdir(parents=True, exist_ok=True)


def compact_training_record(record: Dict[str, Any], max_text: int = 600) -> Dict[str, Any]:
    compact: Dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        if isinstance(value, bool):
            compact[key] = int(value)
        elif isinstance(value, (int, float, str)):
            compact[key] = str(value).strip()[:max_text] if isinstance(value, str) else value
        elif isinstance(value, list):
            compact[f"{key}_count"] = len(value)
            scalars = [str(v)[:80] for v in value[:5] if isinstance(v, (str, int, float, bool))]
            if scalars:
                compact[key] = ", ".join(scalars)
        elif isinstance(value, dict):
            for sub_key, sub_value in list(value.items())[:10]:
                if isinstance(sub_value, (str, int, float, bool)):
                    compact[f"{key}_{sub_key}"] = str(sub_value).strip()[:max_text] if isinstance(sub_value, str) else sub_value
    return compact


def save_non_relational_record(record: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_data_dir()
    with LOCAL_NON_RELATIONAL_STORE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"status": "stored-local-jsonl", "path": str(LOCAL_NON_RELATIONAL_STORE)}


def find_coupon_by_title(title: Optional[str]):
    if not title:
        return None
    normalized_title = title.strip()
    if not normalized_title:
        return None
    try:
        if supabase is not None:  # type: ignore[name-defined]
            res = supabase.table("coupons").select("id,title").eq("title", normalized_title).limit(1).execute()
            data = getattr(res, "data", None) or (res.get("data") if isinstance(res, dict) else None)
            return data[0] if data else None
    except Exception:
        pass
    if SUPABASE_API_URL and SUPABASE_KEY:
        try:
            import httpx
            url = f"{SUPABASE_API_URL.rstrip('/')}/rest/v1/coupons"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            params = {"select": "id,title", "title": f"eq.{normalized_title}", "limit": "1"}
            resp = httpx.get(url, headers=headers, params=params, timeout=10.0)
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None
        except Exception:
            return None
    return None


def smart_store_coupon(record: Dict[str, Any]) -> Dict[str, Any]:
    compact = compact_training_record(record)
    title = compact.get("title") or compact.get("business") or compact.get("code")
    existing = find_coupon_by_title(title if isinstance(title, str) else None)

    if existing:
        relational_payload = {
            "title": title,
            "code": compact.get("code"),
            "place": compact.get("place"),
            "business": compact.get("business"),
            "address": compact.get("address"),
            "expiration": compact.get("expiration"),
            "source": compact.get("source", "agentic-router"),
        }
        return save_coupon(relational_payload)

    non_relational_payload = {
        "title": title,
        "storage": "non-relational",
        "country": compact.get("country", "VE"),
        "category": compact.get("category"),
        "training_features": compact,
    }
    return save_non_relational_record(non_relational_payload)

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
