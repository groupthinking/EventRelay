import os

from gemini_client import GeminiInteractionClient


def run_analysis():
    print("Initializing Competitor Analysis...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        return

    client = GeminiInteractionClient(api_key=api_key)

    # Constructing the detailed research prompt
    prompt = """
    Perform a deep comprehensive analysis of the following competitors and tools in the AI/Video/Dev tools space:
    1. GitHub Code Wiki Button (https://github.com/groupthinking/github-code-wiki-button) & Chrome Extension (https://chromewebstore.google.com/detail/github-code-wiki-button-u/eamgaijkcackfmgpnddepjindfhmobnl)
    2. UVAI (https://uvai.io)
    3. CodeWiki (https://codewiki.google/)
    4. VidIQ (vidiq.com)
    5. NoteGPT (https://notegpt.io/ai-grader) & Extension (https://chromewebstore.google.com/detail/notegpt-youtube-summary-c/baecjmoceaobpnffgnlkloccenkoibbb)
    6. GetStream (getstream.io)

    GOALS:
    1. **Comparative Analysis**: Functionality, target audience, and unique selling points.
    2. **User Sentiment & Fail Points**: Search for reviews, social media mentions, and feedback to identify why users choose these products and where they fail (pain points).
    3. **Strategy Recommendations**:
        - Marketing: How can we take market share? What angles are they missing?
        - UI/UX: specific design and experience recommendations for our CI/CX updates.
    
    Provide the output as a detailed Markdown report.
    """

    print("Submitting Deep Research Query...")
    try:
        interaction = client.create_interaction(
            input_text=prompt,
            agent="deep-research-pro-preview-12-2025",
            background=True
        )
        interaction_id = interaction.get("id")
        print(f"Research Task Started! ID: {interaction_id}")

        print("Polling for results (this may take several minutes)...")
        # Increasing timeout to 10 minutes for deep research
        result = client.wait_for_completion(interaction_id, timeout=600)

        print("\n--- Research Complete ---")
        outputs = result.get("outputs", [])

        report_content = ""
        for output in outputs:
            if output.get("type") == "text":
                report_content += output.get("text")

        # Save to file
        output_filename = "COMPETITOR_ANALYSIS_REPORT.md"
        with open(output_filename, "w") as f:
            f.write(report_content)

        print(f"Report saved to: {output_filename}")

    except Exception as e:
        print(f"Analysis Failed: {e}")

if __name__ == "__main__":
    run_analysis()
