# Implementation Notes

## Build order

1. Install dependencies: `npm install ai` or use the included `package.json`.
2. Pull Vercel env: `vc env pull .env.local`.
3. Run AI Gateway smoke test: `node --env-file=.env.local index.mjs`.
4. Add the API routes.
5. Replace the demo Agent Substrate store with your real persistence layer.
6. Add `InspectorSidebar` to the real inspector layout and pass the selected agent.
7. Run typecheck, tests, and deploy.

## Production hardening

- Replace `authorizeExport` with your real auth/session/ACL logic.
- Replace console audit logging with a durable audit event write.
- If event history can exceed normal response size, persist export artifacts and return a signed download URL.
- Add rate limiting for export requests.
- Add model config validation during deployment.

## End-to-end test run hypotheses

- Selected agent downloads a JSON file.
- No selected agent disables the button.
- Missing agent returns 404.
- Unauthorized user returns 403 after real auth is wired.
- Connection credentials never appear in the JSON.
- Event history pagination returns all pages in order.
