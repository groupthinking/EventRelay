# NotebookLM Workflow Skill

## Description
Operational guide for the complete NotebookLM workflow: Ingesting video transcripts (via custom script) and Querying/Chatting (via MCP).

## When to Use This Workflow
- You have a video transcript (Markdown/Text) and want to query it using Google's NotebookLM.
- You need to generate audio summaries (podcasts) from technical documentation.
- You want to use RAG (Retrieval-Augmented Generation) on large documents with NotebookLM's superior context handling.

## Prerequisites
- Google Cloud Project with NotebookLM access.
- Valid Google Account.
- Local environment with Chrome installed (macOS).

## Workflow Steps

### Phase 1: Ingestion (Upload Source)

Because NotebookLM does not have a public API for uploading sources, we use a browser automation script with a persistent login session.

1.  **Launch Secure Browser Session**
    Run the helper script to open a Chrome instance with remote debugging enabled. This bypasses "browser is unsafe" checks.
    ```bash
    ./scripts/launch_notebooklm_chrome.sh
    ```

2.  **Authenticate**
    - The browser window will open to `https://notebooklm.google.com/`.
    - **Log in manually** with your Google account.
    - Ensure you can see your dashboard.
    - Keep this browser window OPEN.

3.  **Run Ingestion Script**
    Run the ingestion script pointing to your transcript file.
    ```bash
    python src/utils/notebooklm_ingest.py path/to/transcript.md
    ```
    *The script will connect to the open browser, create a new notebook, upload the file, and output the **Notebook URL**.*

### Phase 2: Intelligence (Query via MCP)

Once the notebook is created and the source is uploaded, use the `notebooklm-mcp` server to interact with it.

1.  **Get Notebook ID**
    Extract the ID from the URL provided in Phase 1 (e.g., `https://notebooklm.google.com/notebook/NOTEBOOK_ID`).

2.  **Verify Connection (Optional)**
    Use the MCP tool to list notebooks and confirm visibility.
    ```json
    {
      "method": "notebooklm.list_notebooks"
    }
    ```

3.  **Query or Chat**
    Use the MCP tools to query the specific notebook.
    ```json
    {
      "method": "notebooklm.query",
      "params": {
        "notebook_id": "YOUR_NOTEBOOK_ID",
        "query": "Summarize the key points from the video transcript."
      }
    }
    ```

## Troubleshooting

**Error: "Browser is unsafe"**
- **Cause:** Automated browser detection by Google.
- **Fix:** Ensure you are using Phase 1 Step 1 (`launch_notebooklm_chrome.sh`) and logging in *manually* before running the Python script. Do not let the Python script launch its own browser if you are having login issues.

**Error: "Target closed" / "Connection refused"**
- **Cause:** The Chrome instance from Step 1 was closed or the port 9222 is blocked.
- **Fix:** Rerun `./scripts/launch_notebooklm_chrome.sh`.

**Error: Source not found in Notebook**
- **Cause:** Upload might have timed out or failed silently.
- **Fix:** Check the open browser window. If the file is not there, upload it manually. The MCP can still query it once it's there.
