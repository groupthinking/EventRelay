import os
import sys

from gemini_client import GeminiInteractionClient


def verify_integration():
    print("Starting verification of Deep Research Agent...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("skipped: GEMINI_API_KEY not set. Cannot run live verification.")
        print("Please export GEMINI_API_KEY and run this script manually.")
        return

    try:
        client = GeminiInteractionClient(api_key=api_key)
        print("Authentication successful.")

        query = "State of Exoplanet Research 2025"
        print(f"Submitting research query: '{query}'")

        # Initiate research
        interaction = client.create_interaction(
            input_text=query,
            agent="deep-research-pro-preview-12-2025",
            background=True
        )

        interaction_id = interaction.get("id")
        print(f"Interaction created. ID: {interaction_id}")

        # Poll for completion (optional, demo purposes)
        print("Polling for completion (timeout 60s)...")
        result = client.wait_for_completion(interaction_id, timeout=60)

        print("\n--- Research Result ---")
        outputs = result.get("outputs", [])
        for output in outputs:
            if output.get("type") == "text":
                print(output.get("text")[:500] + "...\n(truncated)")

        print("\nVerification successful!")

    except Exception as e:
        print(f"\nVerification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_integration()
