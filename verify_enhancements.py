import asyncio
import json
import os
from dotenv import load_dotenv
from src.agents.specialized.precision_extractor import PrecisionExtractorAgent
from src.core.collections import SmartCollectionEngine

load_dotenv()


async def verify_precision_extractor():
    print("\n--- Verifying Precision Extractor Agent ---")
    agent = PrecisionExtractorAgent()

    # Using a sample video URL (e.g., a recipe or technical tutorial)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing connectivity, but usually we'd use a real one
    # Note: real multimodal analysis requires a valid video and API key

    try:
        context = "This is a test video containing a secret recipe for happiness."
        result = await agent.extract_precision_data(video_url, context)
        print("Extraction Result Success!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Extraction failed (likely due to missing video or API limits): {e}")


def verify_smart_collections():
    print("\n--- Verifying Smart Collection Engine ---")
    engine = SmartCollectionEngine()

    test_cases = [
        {
            "metadata": {
                "title": "Advanced Quantum Computing Lecture",
                "description": "Exploring qubits and entanglement.",
            },
            "analysis": {"topics": ["physics", "computing"]},
        },
        {
            "metadata": {
                "title": "Best Italian Lasagna Recipe",
                "description": "Homemade pasta and rich ragu.",
            },
            "analysis": {"topics": ["cooking", "food"]},
        },
        {
            "metadata": {
                "title": "Building a SaaS with Next.js and Tailwind",
                "description": "Full stack development tutorial.",
            },
            "analysis": {"topics": ["coding", "design"]},
        },
    ]

    for case in test_cases:
        collections = engine.categorize_video(case["analysis"], case["metadata"])
        print(f"Video: {case['metadata']['title']}")
        print(f"Assigned Collections: {collections}")


async def main():
    await verify_precision_extractor()
    verify_smart_collections()


if __name__ == "__main__":
    asyncio.run(main())
