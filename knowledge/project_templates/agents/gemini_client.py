import os
import time
from typing import Any, Dict, Optional

import requests


class GeminiInteractionClient:
    """
    A client for interacting with the Gemini v1beta Interactions API.
    Designed to support specialized agents like 'deep-research'.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set in GEMINI_API_KEY environment variable.")
        self.headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def create_interaction(self,
                           input_text: str,
                           agent: str = "deep-research-pro-preview-12-2025",
                           background: bool = True) -> Dict[str, Any]:
        """
        Creates a new interaction with the specified agent.
        """
        payload = {
            "agent": agent,
            "input": input_text,
            "background": background
        }

        response = requests.post(self.BASE_URL, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_interaction(self, interaction_id: str) -> Dict[str, Any]:
        """
        Retrieves the status and content of an existing interaction.
        """
        url = f"{self.BASE_URL}/{interaction_id}"
        response = requests.get(url, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response Body: {response.text}")
            raise
        return response.json()

    def wait_for_completion(self, interaction_id: str, poll_interval: int = 5, timeout: int = 600) -> Dict[str, Any]:
        """
        Polls the interaction endpoint until the status is 'completed' or timeout is reached.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            interaction = self.get_interaction(interaction_id)
            status = interaction.get("status")

            print(f"Status: {status}...")

            if status == "completed":
                return interaction
            elif status in ["failed", "cancelled"]:
                raise RuntimeError(f"Interaction ended with status: {status}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Interaction {interaction_id} timed out after {timeout} seconds.")

if __name__ == "__main__":
    # fast test if run directly
    try:
        client = GeminiInteractionClient()
        print("Client initialized successfully.")
    except Exception as e:
        print(f"Client initialization check: {e}")
