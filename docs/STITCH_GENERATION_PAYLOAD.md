# Stitch Generation Payloads

**Note:** The automated token appears to be expired. Please use these payloads with a valid `STITCH_ACCESS_TOKEN`.

## Step 1: Create Project
**Method:** `tools/call` -> `create_project`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_project",
    "arguments": {
      "title": "EventRelay Dashboard"
    }
  }
}
```

## Step 2: Generate Screen (The Main Payload)
**Method:** `tools/call` -> `generate_screen_from_text`
**Prerequisite:** Replace `YOUR_PROJECT_ID` with the ID returned from Step 1 (e.g., `projects/12345...`).

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "generate_screen_from_text",
    "arguments": {
      "projectId": "YOUR_PROJECT_ID",
      "modelId": "GEMINI_3_PRO",
      "deviceType": "DESKTOP",
      "prompt": "Create a modern, professional 'Video Intelligence Dashboard' for developers called EventRelay. \n\n**Visual Style:**\n- 'Brutalist Utility' aesthetic: High contrast, data-dense, monospaced fonts for code/data.\n- Dark mode default.\n- Clean, sharp edges (not overly rounded).\n\n**Layout (Split-Screen):**\n- **Header:** Minimal bar with 'EventRelay' logo, System Status indicator (Green pulse), and User Profile.\n- **Left Sidebar (40% width):** \n  - Prominent YouTube URL Input field at the top.\n  - Video Player area (16:9 aspect ratio placeholder).\n  - Scrollable Metadata section below video (Title, Views, Duration, Channel).\n- **Right Content Area (60% width):**\n  - Tabbed Interface: 'Analysis', 'Transcript', 'Events', 'Build'.\n  - **Analysis Tab:** Markdown-styled text area for AI summaries.\n  - **Transcript Tab:** Time-stamped text list.\n  - **Events Tab:** Cards showing detected events (e.g., 'Tutorial Start', 'Code Demo') with 'Action' buttons.\n  - **Build Tab:** A code editor view showing generated code artifacts.\n\n**Functionality Notes for Code Generation:**\n- The frontend must be React + Tailwind CSS.\n- It needs to call `POST http://localhost:8000/process_video` to populate the Analysis tab.\n- It needs to call `POST http://localhost:8000/api/v1/transcript-action` when action buttons are clicked.\n\n**Proof of Functionality:**\n- Show the UI in a state where a video has been loaded (e.g., 'Rick Roll' or a tech tutorial).\n- Display mock data in the Analysis tab that looks like a real AI insight."
    }
  }
}
```

## Execution via Curl
```bash
# 1. Export your token
export STITCH_ACCESS_TOKEN="your_valid_token_here"

# 2. Run the command
curl -X POST -H "Authorization: Bearer $STITCH_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d @payload.json \
     https://stitch.googleapis.com/mcp
```

