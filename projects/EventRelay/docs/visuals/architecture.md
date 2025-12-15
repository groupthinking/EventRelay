# UVAI YouTube Extension Architecture

```mermaid
graph TD
    subgraph Client
        UI[React Dashboard]
        Agents[Agent Scripts]
    end

    subgraph Backend
        API[FastAPI Service]
        Router[Cloud AI Router]
        MCP[MCP Coordinator]
        Services[Domain Services]
        DB[(SQLite / Postgres)]
        Cache[(Redis)]
    end

    subgraph AIProviders
        YT[YouTube Data API]
        Speech[Google Speech-to-Text V2]
        Gemini[Gemini / Veo Models]
        OpenAI[OpenAI Models]
    end

    UI -->|REST / WebSockets| API
    Agents -->|CLI / MCP| API

    API --> Router
    API --> Services
    Router --> MCP
    Services --> DB
    Services --> Cache

    Router --> YT
    Router --> Speech
    Router --> Gemini
    Router --> OpenAI

    Speech --> GCS[(GCS Buckets)]
    Services --> Artifacts[youtube_processed_videos/]
```

- The **React dashboard** and external agents call into the FastAPI backend via REST or WebSocket channels.
- The **Cloud AI router** handles provider selection, retry logic, and quota-aware fallbacks while the **MCP coordinator** orchestrates MCP-compliant agents.
- Processed data and metadata persist in SQLite/Postgres and Redis while bulk artifacts flow to `youtube_processed_videos/` and configured GCS buckets.
- Provider integrations span YouTube Data API, Google Speech-to-Text V2, Gemini/Veo, and OpenAI models.

Add product screenshots (`.png`, `.jpg`, `.gif`) to this folder and link them from the main README as they become available.
