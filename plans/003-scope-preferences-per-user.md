# Plan 003: Replace process-global `sessionPreferences` singleton with per-user cookie storage in `/api/v1/preferences`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 25c5e936e..HEAD -- apps/web/src/app/api/v1/preferences/route.ts`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `25c5e936e` (`origin/main`), 2026-11-19

## Why this matters

`apps/web/src/app/api/v1/preferences/route.ts` stores user preferences in a module-level mutable variable (`let sessionPreferences = DEFAULT_PREFERENCES`). In any multi-user Node/serverless instance, User A saving preferences silently overwrites User B's preferences, and User B calling `GET /api/v1/preferences` reads User A's data.

## Current state

- `apps/web/src/app/api/v1/preferences/route.ts` — `GET` / `PUT` / `POST` handler for `UserPreferences`.
- `apps/web/src/lib/preferences.ts` — defines `DEFAULT_PREFERENCES` and `UserPreferences` type.

Excerpt of `apps/web/src/app/api/v1/preferences/route.ts:1-56` at `25c5e936e`:

```ts
export const runtime = 'nodejs';

let sessionPreferences: UserPreferences = DEFAULT_PREFERENCES;
...
export async function GET() {
  return NextResponse.json({
    preferences: sessionPreferences,
    source: 'session-default',
  });
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json() as Partial<UserPreferences>;
    sessionPreferences = normalizePreferences(body);
    return NextResponse.json({
      ok: true,
      preferences: sessionPreferences,
    });
```

## Commands you will need

| Purpose   | Command                                                                  | Expected on success |
|-----------|--------------------------------------------------------------------------|---------------------|
| Typecheck | `cd apps/web && npx tsc --noEmit`                                        | exit 0, no errors   |
| Unit test | `cd apps/web && npx vitest run src/app/api/v1/preferences/__tests__/`    | all tests pass      |
| Full web  | `cd apps/web && npx vitest run`                                          | all tests pass      |

## Scope

**In scope** (the only files you should modify):
- `apps/web/src/app/api/v1/preferences/route.ts`
- `apps/web/src/app/api/v1/preferences/__tests__/route.test.ts` (create)

**Out of scope** (do NOT touch):
- `apps/web/src/lib/preferences.ts` — keep `UserPreferences` schema and `DEFAULT_PREFERENCES` unchanged.
- Database migrations or external KV stores — an `HttpOnly`, `SameSite=Lax` JSON cookie scoped per browser session cleanly eliminates cross-user leakage with zero external dependencies.

## Git workflow

- Branch from `origin/main`: `fix/preferences-per-user-cookie`
- Conventional Commits message: `fix(api): scope /api/v1/preferences to per-user cookie instead of global singleton`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Remove `let sessionPreferences` and read/write via `uvai_user_prefs` cookie

In `apps/web/src/app/api/v1/preferences/route.ts`:
1. Delete `let sessionPreferences: UserPreferences = DEFAULT_PREFERENCES;`.
2. Add constant `const PREFERENCES_COOKIE = 'uvai_user_prefs';`.
3. Add a pure helper `readPreferencesFromRequest(request: NextRequest): { preferences: UserPreferences; source: 'cookie' | 'session-default' }` that reads `request.cookies.get(PREFERENCES_COOKIE)?.value`, parses JSON inside a `try/catch`, and passes the result through `normalizePreferences(...)` (falling back to `DEFAULT_PREFERENCES` and `'session-default'` if absent or malformed).
4. Update `GET(request: NextRequest)` to call `readPreferencesFromRequest(request)` and return `{ preferences, source }`.
5. Update `PUT(request: NextRequest)` to normalize the request body into `const preferences = normalizePreferences(body)`, build `const res = NextResponse.json({ ok: true, preferences })`, and set `res.cookies.set(PREFERENCES_COOKIE, JSON.stringify(preferences), { httpOnly: true, sameSite: 'lax', path: '/', maxAge: 60 * 60 * 24 * 180, secure: process.env.NODE_ENV === 'production' })`.
6. On invalid JSON in `PUT`, return HTTP `400` with `readPreferencesFromRequest(request).preferences` (never another user's preferences).

**Verify**: `cd apps/web && npx tsc --noEmit` → exit 0, no errors.

### Step 2: Add unit tests proving zero cross-user leakage

Create `apps/web/src/app/api/v1/preferences/__tests__/route.test.ts` covering:
1. User A `PUT`s `{ industry: 'fintech', tone: 'executive' }` → returns `200`, sets `uvai_user_prefs` cookie.
2. User B `GET`s with no cookie → returns `DEFAULT_PREFERENCES` (NOT User A's `'fintech'` / `'executive'`).
3. User A `GET`s with the cookie from step 1 → returns `{ industry: 'fintech', tone: 'executive', ... }`, `source: 'cookie'`.
4. Corrupted cookie value → safely falls back to `DEFAULT_PREFERENCES` without throwing.
5. Invalid JSON body on `PUT` → returns `400`.

**Verify**: `cd apps/web && npx vitest run src/app/api/v1/preferences/__tests__/route.test.ts` → 5/5 tests pass.

## Test plan

- File: `apps/web/src/app/api/v1/preferences/__tests__/route.test.ts`
- Verification: `cd apps/web && npx vitest run` → exit 0, all tests pass.

## Done criteria

- [ ] `cd apps/web && npx tsc --noEmit` exits 0
- [ ] `grep -n "let sessionPreferences" apps/web/src/app/api/v1/preferences/route.ts` returns no matches
- [ ] `cd apps/web && npx vitest run src/app/api/v1/preferences/__tests__/route.test.ts` passes all 5 cases
- [ ] `cd apps/web && npx vitest run` exits 0
- [ ] Only in-scope files modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:
- `apps/web/src/app/api/v1/preferences/route.ts` has drifted from `25c5e936e`.
- Any caller requires `source` to always equal `'session-default'` even after saving (check with `grep -rn "session-default" apps/web/src/`).

## Maintenance notes

- If preferences grow beyond ~2 KB or need cross-device sync for signed-in users, migrate the backing store to Postgres/Upstash keyed by NextAuth `session.user.id` while keeping the `normalizePreferences` boundary.
