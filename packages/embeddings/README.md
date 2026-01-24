# @eventrelay/embeddings

pgvector embeddings and semantic search for EventRelay.

## Features

- **Vertex AI Embeddings**: Uses `text-embedding-004` (768 dimensions)
- **pgvector Storage**: Cloud SQL PostgreSQL with vector similarity search
- **Semantic Search**: Cosine distance-based RAG queries

## Usage

```typescript
import {
  generateEmbedding,
  searchSimilar,
  embedJobAnalysis,
} from "@eventrelay/embeddings";

// Generate embedding for text
const embedding = await generateEmbedding("How to build a Next.js app");

// Search similar content
const results = await searchSimilar(embedding, 5);

// Embed job analysis results
await embedJobAnalysis(jobId, {
  summary: "Video tutorial about...",
  steps: ["Step 1", "Step 2"],
  insights: ["Key insight 1"],
  codeBlocks: ["const x = 1;"],
});
```

## Environment Variables

```bash
GOOGLE_CLOUD_PROJECT=your-project
GCP_LOCATION=us-central1
CLOUDSQL_HOST=/cloudsql/project:region:instance
CLOUDSQL_DATABASE=your-db
CLOUDSQL_USER=postgres
CLOUDSQL_PASSWORD=secret
```

## Origin

Migrated from `action-genai-video-issue-analyzer` as part of EventRelay consolidation.
