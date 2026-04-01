import asyncio
from typing import List, Dict, Any, Optional
from .vector_store import FaissVectorStore
from .mcp_bridge import RemoteMCPBridge
from .query_router import QueryRouter
from .events import log_event
from .database import smart_store_coupon
import os

class RAGAgent:
    def __init__(self, vector_store: Optional[FaissVectorStore] = None):
        self.vs = vector_store or FaissVectorStore()
        self.mcp = RemoteMCPBridge()
        self.router = QueryRouter()
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_url = os.getenv("OPENAI_API_URL")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.vs.search(query, top_k)

    async def call_llm(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        # lightweight wrapper; can be extended to call MCP or other LLMs
        from .chatbot import ChatbotManager
        bot = ChatbotManager()
        return await bot.call_llm(prompt, model=model)

    async def answer_query(self, user_query: str, user_id: Optional[str] = None, gps: Optional[tuple] = None, country: str = "VE", radius_miles: float = 100.0) -> Dict[str, Any]:
        decision = self.router.route_query(user_query, country=country, radius_miles=radius_miles)

        # 1. Retrieve candidate docs
        docs = self.retrieve(user_query, top_k=8)

        mcp_results: Dict[str, Any] = {}
        if decision.should_call_mcp:
            if decision.extracted_codes:
                try:
                    mcp_results["coupon_checks"] = [self.mcp.verify_logistics_coupon(code) for code in decision.extracted_codes[:3]]
                except Exception as exc:
                    mcp_results["coupon_checks_error"] = str(exc)

            smart_store_coupon({
                "title": decision.title_hint or user_query[:80],
                "description": user_query,
                "country": decision.country,
                "radius_miles": decision.radius_miles,
                "category": ", ".join(decision.matched_keywords[:5]),
                "source": "rag-agent-router",
                "code": decision.extracted_codes[0] if decision.extracted_codes else None,
            })

        # 2. Build RAG prompt (concise)
        context = "\n".join([f"- {d['meta'].get('title', d['doc_id'])}: {d['meta'].get('snippet','')}" for d in docs if d.get('meta')])
        prompt = (
            "Eres un asistente humano, cálido y útil para promociones en Venezuela. "
            "You are also helpful in English when the user switches languages. "
            f"User: {user_query}\n"
            f"Scope country={decision.country}, radius_miles={decision.radius_miles}.\n"
            f"Matched keywords={decision.matched_keywords}.\n"
            f"MCP checks={mcp_results}.\n"
            f"Context:\n{context}\n"
            "Answer briefly, naturally, and prioritize nearby promotions, discounts, coupons, and expiration timing."
        )
        # 3. Call LLM
        llm_resp = await self.call_llm(prompt)
        log_event(user_id, "rag_query", {
            "query": user_query,
            "country": decision.country,
            "radius_miles": decision.radius_miles,
            "keywords": decision.matched_keywords,
            "codes": decision.extracted_codes,
            "mcp_used": decision.should_call_mcp,
        })
        return {
            "query": user_query,
            "routing": {
                "should_call_mcp": decision.should_call_mcp,
                "matched_keywords": decision.matched_keywords,
                "codes": decision.extracted_codes,
                "country": decision.country,
                "radius_miles": decision.radius_miles,
            },
            "context_docs": docs,
            "mcp": mcp_results,
            "llm": llm_resp,
        }
