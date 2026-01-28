# Design Brief: EventRelay Video Intelligence Dashboard

## 1. Project Overview
**Goal:** Create a modern, responsive React-based frontend for the EventRelay Video Intelligence Platform.
**Core Function:** Transform YouTube videos into actionable intelligence (transcripts, event detection, code generation).
**Design Aesthetic:** "Brutalist utility" meets "Modern SaaS" (clean, data-dense, functional).
**Reference:** `video-to-learning-app` (Split-screen layout).

## 2. Key Features
- **Video Input:** Simple, prominent input field for YouTube URLs.
- **Split-Screen Layout:**
  - **Left Panel:** Video Player + Metadata + Controls.
  - **Right Panel:** Intelligence Feed (Transcript, Extracted Events, Action Items, Generated Code).
- **Real-Time Feedback:** Status indicators for "Processing", "Analyzing", "Generating".
- **Action Execution:** Buttons to trigger downstream agents (e.g., "Deploy to Cloud Run", "Save to Database").

## 3. Technical Stack (Target)
- **Framework:** React 18+ (Vite)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** React Context or Zustand
- **Backend Connection:** REST API (FastAPI)

## 4. API Integration Points
The frontend must connect to the `Prescient Twin` backend (running on port 8000).

### Primary Endpoints
| Endpoint | Method | Payload | Purpose |
|----------|--------|---------|---------|
| `/process_video` | POST | `{ "youtube_url": "..." }` | **Analysis Phase:** Get transcript, summary, and AI insights. Returns JSON with markdown analysis. |
| `/api/v1/transcript-action` | POST | `{ "youtube_url": "..." }` | **Action Phase:** Trigger full agent workflow (Event Extraction -> Agent Dispatch). |
| `/execute_video` | POST | `{ "video_url": "...", "auto_deploy": false }` | **Build Phase:** Generate and deploy applications based on video content. |

## 5. UI/UX Requirements
### Layout Structure
- **Header:** Minimal branding ("EventRelay"), Status (System Health), User Profile.
- **Main Content:**
  - **Empty State:** Centered Input Field ("Paste YouTube URL").
  - **Active State:** Split View.
    - **Left (40%):** Sticky Video Player. Scrollable Metadata below.
    - **Right (60%):** Tabs for different outputs:
      - **"Analysis":** Markdown summary (rendered nicely).
      - **"Transcript":** Time-synced text.
      - **"Actions":** List of detected events and buttons to act.
      - **"Build":** (Optional) Generated code preview or "App" view (like the reference).

### Components needed
1.  **UrlInput:** with validation (YouTube regex).
2.  **VideoPlayer:** Wrapper around `react-player` or iframe.
3.  **MarkdownRenderer:** For the AI analysis output.
4.  **ActionCard:** To display specific events/tasks extracted from video.
5.  **CodeBlock:** To display generated code snippets (with syntax highlighting).
6.  **StatusBadge:** Pulse animation for active processing.

## 6. Competitive Analysis Notes (VibeVoice & Competitors)
- **VibeVoice:** Focuses on voice-to-action. Our UI should emphasize the *textual* result of the voice processing.
- **Competitors (Loom/Descript):** They excel at *editing* text to edit video. We excel at *reading* video to trigger *external actions*.
- **differentiation:** We are not an editor; we are an **Execution Engine**. The UI should reflect "Command Center" more than "Editor".

## 7. Implementation Plan (Stitch)
1.  Use Stitch to scaffold the basic React structure.
2.  Implement the `UrlInput` and `VideoPlayer` first.
3.  Connect `/process_video` to populate the "Analysis" tab.
4.  Refine the visual hierarchy to handle dense text data (transcripts/logs).
