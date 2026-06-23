# Extracting the EventRelay API into its own repo

This bundle turns the monorepo's clean spine (`service/`) into a standalone,
deployable repository. The extraction is **near-pure copy**: every import is
relative or `service.app.*`, and the Dockerfile already builds with the repo
root as context, so the verified code moves unchanged.

## Why a fresh repo (not `git filter-repo`)

A fresh `git init` gives the published product a **clean history**. The monorepo
carries committed browser-session credentials in its history (introduced at
`82ce454`) that still require a coordinated purge; a new root never inherits
that exposure. You lose the spine's ~6 commits of provenance — but those are
summarized in `docs/PORTING_PARAMETERS.md`, which travels with the bundle.

If you would rather preserve history, use instead:

```bash
git filter-repo --path service/ --path-rename service/:    # keeps commits, NOT the clean slate
```

…and then audit the resulting history yourself.

## Steps (fresh, recommended)

```bash
# 1. Assemble the tree (from the monorepo root)
bash export/eventrelay-api/assemble.sh ../eventrelay-api

# 2. Verify it stands on its own — no DB, keys, or network needed
cd ../eventrelay-api
make install-dev
make test            # expect the full spine suite green
make openapi         # should produce no diff to service/openapi.json

# 3. Initialize and publish
git init
git add -A
git commit -m "chore: extract EventRelay API from monorepo spine"
# create the empty GitHub repo (e.g. groupthinking/eventrelay-api), then:
git remote add origin git@github.com:<org>/eventrelay-api.git
git push -u origin main
```

## What moves, what stays

| Moves to the new repo | Stays in the monorepo |
|---|---|
| `service/` (app, tests, openapi.json) | `apps/web` (the studio frontend) |
| `service/Dockerfile` → repo-root `Dockerfile` | legacy `src/youtube_extension` |
| `docs/PORTING_PARAMETERS.md`, `docs/SC7_CUTOVER.md` | everything else |
| new root scaffolding (this bundle) | — |

## After extraction

1. **Repoint the frontend.** `apps/web` already consumes this service over HTTP
   via `lib/eventrelay-client.ts`; set `NEXT_PUBLIC_BACKEND_URL` to the deployed
   Cloud Run URL. No code change — the contract is the only coupling.
2. **Generate the SDK** from `service/openapi.json` (Stainless). Do **not** drag
   the monorepo's `sdk/python/eventrelay_sdk` along — that one tracks the legacy
   40-path backend, not this contract.
3. **Wire deploy secrets** (`deploy-cloud-run.yml` header lists them) and run the
   live end-to-end fail-frame: submit 3 real YouTube URLs; PASS = each reaches
   `succeeded` with a non-empty transcript, ≥1 valid `<domain>.<entity>.<action>`
   event, and a non-empty summary.
