import asyncio
from agent.llm.client import LLMClient

async def test_llm():
    client = LLMClient()
    prompt = "Generate a short 3-word slogan for an AI job app."
    try:
        response = await client.complete(prompt)
        print(f"LLM Response: {response.strip()}")
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
