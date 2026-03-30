import os
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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

    def match_documents(query_embedding: List[float], match_threshold: float = 0.75, match_count: int = 5):
        return supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count
        }).execute()

except Exception:
    # Fallback stubs for environments without supabase installed.
    supabase = None  # type: ignore

    def insert_knowledge(content: str, metadata: Dict[str, Any], embedding: List[float]):
        # No-op stub for tests/local runs.
        return {"status": "stubbed", "content": content, "metadata": metadata}

    def match_documents(query_embedding: List[float], match_threshold: float = 0.75, match_count: int = 5):
        # Return empty list as default when no DB is available.
        return []
