-- Reject placeholder hosts in `deployment_url`.
--
-- The original constraint (`delivery_runs_deployment_url_is_https`) only
-- required the URL to start with `https://`. That was too weak to mean
-- "shipped": `https://localhost`, `https://example.com/app`, and
-- `https://example.org` all satisfied it, so a run pointing at a local dev
-- server or a documentation placeholder could still be stored as `delivered`.
--
-- The application-side guard (`isRealDeploymentUrl` in
-- `src/lib/delivery-lifecycle.ts`) already rejected those hosts, so the two
-- layers disagreed. The cross-layer parity suite
-- (`src/lib/__tests__/delivery-guard-parity.integration.test.ts`) exists to
-- fail CI when that happens, and this migration is the database half of the fix.
--
-- Keep the host list here in lockstep with `PLACEHOLDER_HOSTS` in
-- `src/lib/delivery-lifecycle.ts`. The parity suite enforces that.

ALTER TABLE delivery_runs
  DROP CONSTRAINT IF EXISTS delivery_runs_deployment_url_is_https;

ALTER TABLE delivery_runs
  DROP CONSTRAINT IF EXISTS delivery_runs_deployment_url_real;

-- A real deployment URL must:
--   1. be absolute https with a non-empty host
--   2. not be a loopback / unspecified address
--   3. not be a reserved documentation domain (example.com/org/net),
--      including any subdomain of one
--
-- The host is the run of characters after `https://` up to the first `/`, `?`,
-- or `#`, and may carry a `:port` suffix.
ALTER TABLE delivery_runs
  ADD CONSTRAINT delivery_runs_deployment_url_real CHECK (
    deployment_url IS NULL
    OR (
      deployment_url ~ '^https://[^/?#]+'
      -- Loopback and unspecified addresses, plus bare/subdomain `localhost`.
      AND deployment_url !~* '^https://([^/?#@]*\.)?localhost(:[0-9]+)?([/?#]|$)'
      AND deployment_url !~* '^https://127\.0\.0\.1(:[0-9]+)?([/?#]|$)'
      AND deployment_url !~* '^https://0\.0\.0\.0(:[0-9]+)?([/?#]|$)'
      AND deployment_url !~* '^https://\[::1\](:[0-9]+)?([/?#]|$)'
      -- RFC 2606 reserved documentation domains.
      AND deployment_url !~* '^https://([^/?#@]*\.)?example\.(com|org|net)(:[0-9]+)?([/?#]|$)'
    )
  );
