---
description: Search and Chat with the Codebase
---

# Chat with Repo

This workflow allows you to index your repository and then ask questions about it using Vector Search.

## Prerequisite

Ensure `OPENAI_API_KEY` is set in your environment.

## Steps

1. **(Optional) Ingest/Update Index**
   Run this only when you want to refresh the vector database with the latest code changes.

   ```bash
   python3 scripts/ingest_repo.py
   ```

2. **Chat**
   Ask a question to the codebase.
   ```bash
   python3 scripts/chat_repo.py "Your Question Here"
   ```
