import asyncio
from core.chatbot import ChatbotManager
from core.rag_agent import RAGAgent

async def main():
    bot = ChatbotManager()
    # Venezuela-first text query demo
    result = bot.process_text_input(
        "Necesito promoción 2x1 de comida en Valencia cerca de Sambil con cupón 25%",
        gps=(10.1620, -68.0077),
        expiring_within_hours=48,
    )
    print("=== Text query result ===")
    print(result)

    # Example of calling the async LLM wrapper (if OPENAI_API_KEY is set)
    prompt = result["prompt_for_llm"]
    llm_reply = await bot.call_llm(prompt)
    print("=== LLM Reply ===")
    print(llm_reply)

    agent = RAGAgent()
    agent_result = await agent.answer_query(
        "Busco promoción 2x1 de hamburguesas en Naguanagua con cupón 15 y delivery",
        user_id="demo-user",
        gps=(10.2607, -68.0102),
        country="VE",
        radius_miles=100,
    )
    print("=== Agentic RAG Result ===")
    print(agent_result)

if __name__ == "__main__":
    asyncio.run(main())
