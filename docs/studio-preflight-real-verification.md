# Studio preflight verification with real services

`studio-deploy` is a preflight endpoint. It must reject private source URLs and
hold deployment when artifact-bound evidence is missing. A HOLD does not mean
an application was deployed.

The former route test replaced authentication, G.A.T.E., and the SSRF guard.
It has been removed. Its replacement sends actual HTTP requests to `next start`
using the production build, then starts `next dev` to verify the approved preview
origin behavior. There are no module replacements, fake DNS answers, intercepted
HTTP responses, substituted gate decisions, or in-memory receipt stores.

Run from the repository root with the supported Node version:

```sh
npm ci --legacy-peer-deps
npm run build:web
npm --workspace=apps/web run test:studio-preflight:real -- --provision-redis
```

The explicit `--provision-redis` option creates a free, isolated Upstash database
using the provider's [documented temporary database endpoint](https://github.com/upstash/redis-js#readme).
It expires after 72 hours and is not attached to a production account. Returned
credentials remain in process memory. For an existing **dedicated integration
database**, omit that flag and provide `STUDIO_PREFLIGHT_REDIS_REST_URL` and
`STUDIO_PREFLIGHT_REDIS_REST_TOKEN`. Do not supply shared production credentials.

The runner starts its own local application instances with a fresh signing key
and creates cryptographically valid NextAuth session tokens. It exercises real
session validation, including a token signed with a different key. It does not
exercise Google's interactive OAuth login or claim to impersonate a production
user. It does not inherit provider secrets, internal bypass headers, or
`NODE_OPTIONS` hooks from the caller.

The default source is `https://www.youtube.com/watch?v=auJzb1D-fag`; a real source
can be supplied with `STUDIO_PREFLIGHT_SOURCE_URL`. DNS is live. A DNS failure is
a verification failure, not a reason to replace the resolver or skip the case.

Checks cover:

- Missing/invalid sessions and cross-origin rejection in production.
- Real SSRF rejection for IPv4 loopback, IPv6 loopback, link-local metadata,
  localhost, and the cloud metadata hostname.
- Missing URLs, non-HTTP sources, invalid JSON, body size, and content type.
- Public-source admission to a signed, retained `GATE_HOLD_MISSING_EVIDENCE`.
- Rejection of browser authority/artifact claims as deployment authorization.
- Authentication and retained HOLD behavior for approved development previews.

Each rejection must leave the authenticated subject's receipt index unchanged.
Each valid preflight must return the correct HOLD reason, a verifiable signature,
and a receipt independently read back from the actual Redis service with a bounded
TTL. `GATE_HOLD_RUNTIME_UNAVAILABLE`, an unretained receipt, a missing service,
and a failed prerequisite all fail the run. Cleanup deletes only keys created
under this run's unique subject and confirms they are gone.

Production rate limits remain active. During the server-reported reset wait,
the runner sends real Redis PING commands to verify continued dependency health.
A failed PING fails the check. Temporary-provider diagnostics retain only numeric
usage counters, never the metrics link or credentials.

The CI build job runs this verification after building the application; it does
not depend on Vitest's aliases or mocks. It retains the JSON response/receipt
evidence and redacted server logs as a `studio-preflight-real-<sha>` artifact.
Locally, evidence defaults to `apps/web/test-results/studio-preflight-real.json`;
override it with `STUDIO_PREFLIGHT_REPORT`.

This verifies the production preflight path and its dependencies. It does not
grant a deployment PASS, start a paid provider workflow, or deploy or merge code.
