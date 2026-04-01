import asyncio
from core.chatbot import ChatbotManager

async def main():
    bot = ChatbotManager()
    # Example text query
    result = bot.process_text_input("coffee near me", gps=(40.7128, -74.0060), expiring_within_hours=48)
    print("=== Text query result ===")
    print(result)

    # Example of calling the async LLM wrapper (if OPENAI_API_KEY is set)
    prompt = result["prompt_for_llm"]
    llm_reply = await bot.call_llm(prompt)
    print("=== LLM Reply ===")
    print(llm_reply)

if __name__ == "__main__":
    asyncio.run(main())
