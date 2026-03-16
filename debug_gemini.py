import asyncio, os
from src.integration.gemini_video import GeminiVideoService

async def main():
    svc = GeminiVideoService()
    res = await svc.analyze_video("https://www.youtube.com/watch?v=b1mjQIiH7r4", "Watch this video and tell me what it is about.")
    print("RAW SUMMARY:")
    print(res.summary)
    print("KEY EVENTS:")
    print(res.key_events)

if __name__ == "__main__":
    asyncio.run(main())
