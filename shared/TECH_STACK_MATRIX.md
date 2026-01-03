# Tech Stack Matrix

| Component    | Directory                       | Stack           | Version              | Notes                     |
| ------------ | ------------------------------- | --------------- | -------------------- | ------------------------- |
| **Frontend** | `apps/web`                      | Next.js / React | Next 14.2 / React 18 | Main Platform UI          |
| **VibeSDK**  | `projects/netmesh-production`   | Vite / React    | React 19.1           | Cloudflare Worker + UI    |
| **Backend**  | `src/`                          | Python          | 3.9+                 | Main API (FastAPI/Agents) |
| **Firebase** | `apps/firebase`                 | Node.js         | -                    | Functions / Integrations  |
| **MCP**      | `mcp-servers/python-suite`      | Python          | -                    | Core Agent Logic          |
| **MCP**      | `mcp-servers/gcp-vector-db`     | Node.js         | TS 5.3               | Vector Search             |
| **MCP**      | `mcp-servers/unified-analytics` | Node.js         | TS 5.0               | Analytics                 |

## Standardization Goals

1. **TypeScript**: Target v5.x (Achieved for known active servers).
2. **React**: EventRelay (v18) vs Netmesh (v19). Keep distinct for now.
3. **Python**: Ensure 3.10+ where possible (Currently 3.9 detected in env).

## Infrastructure

- **Orchestration**: Kubernetes + KEDA (Planned)
- **Database**: Cloud SQL (Postgres + pgvector)
- **Messaging**: Redis / NATS (Planned)
