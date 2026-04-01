import asyncio
from typing import List, Dict, Any, Optional
from .vector_store import FaissVectorStore
from .mcp_bridge import RemoteMCPBridge
import os

class RAGAgent:
    def __init__(self, vector_store: Optional[FaissVectorStore] = None):
        self.vs = vector_store or FaissVectorStore()
        self.mcp = RemoteMCPBridge()
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_url = os.getenv("OPENAI_API_URL")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.vs.search(query, top_k)

    async def call_llm(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        # lightweight wrapper; can be extended to call MCP or other LLMs
        from .chatbot import ChatbotManager
        bot = ChatbotManager()
        return await bot.call_llm(prompt, model=model)

    async def answer_query(self, user_query: str, user_id: Optional[str] = None, gps: Optional[tuple] = None) -> Dict[str, Any]:
        # 1. Retrieve candidate docs
        docs = self.retrieve(user_query, top_k=8)
        # 2. Build RAG prompt (concise)
        context = "\n".join([f"- {d['meta'].get('title', d['doc_id'])}: {d['meta'].get('snippet','')}" for d in docs if d.get('meta')])
        prompt = f"User: {user_query}\nContext:\n{context}\nAnswer briefly and include any coupon codes or expiration info."
        # 3. Call LLM
        llm_resp = await self.call_llm(prompt)
        # 4. Optionally call MCP for verification (e.g., verify coupon)
        verification = None
        # Example: if LLM produced a token-looking string, ask MCP verify_logistics_coupon
        # (left defensive; do not call without pattern)
        return {"query": user_query, "context_docs": docs, "llm": llm_resp, "verification": verification}
