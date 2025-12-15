# Security Policy

The UVAI YouTube Extension processes third-party content, user credentials, and AI provider keys. This policy explains which versions receive security updates, how to report issues, and the minimum safeguards expected of contributors and operators.

## Supported Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.0.x   | ✅ Supported | Actively patched and monitored |
| < 1.0   | ❌ Unsupported | Upgrade to the current minor release |

Security fixes are released on the latest patch of the supported minor version. Operating older versions in production is at your own risk.

## Reporting a Vulnerability

1. **Email** `security@uvai.com` (CC `team@uvai.com`) with the following:
   - Description and potential impact
   - Steps to reproduce or proof-of-concept
   - Affected environment (local, staging, production)
   - Any mitigating controls already in place
2. **Expected response time**: acknowledgement within 24 hours, triage update within 3 business days.
3. **Coordinated disclosure**: please allow us 30 days to address critical issues before public disclosure unless a shorter timeline is mutually agreed.

If email is unavailable, open a private security advisory via the GitHub repository’s “Security” tab.

## Handling Sensitive Data

- Never commit secrets; use `.env`, secret managers, or CI vaults. `.env.example` lists required variables.
- Restrict API keys to the minimum scopes (YouTube Data API, Gemini, OpenAI, Google Speech-to-Text) and rotate them quarterly.
- Store production credentials in dedicated secret stores (AWS Secrets Manager, GCP Secret Manager, 1Password) instead of shell profiles when possible.
- Ensure `~/CLAUDE.md`, `~/.claude/CLAUDE.md`, and `/Users/garvey/CLAUDE_CODE_GOVERNANCE.md` have been reviewed before enabling MCP agents.

## Secure Development Practices

- Run `youtube-extension lint` and `youtube-extension test` before submitting changes; this enforces Ruff, mypy, and pytest checks.
- Apply security patches promptly via `pip install -e .[dev]` and `npm audit fix` workflows.
- Use feature flags when integrating new agents to avoid exposing experimental endpoints in production.
- Monitor dependencies with `scripts/check_credentials.py` and container scans in your CI pipeline.

## Infrastructure Hardening

- Enforce HTTPS for any public deployment behind a load balancer or CDN.
- Keep `docker-compose.*.yml` secrets externalised via environment files or credential stores.
- Configure rate limiting and circuit breakers using the defaults in `mcp_servers/youtube_api_proxy.py` unless a revised quota plan is documented.
- Enable Prometheus/OTEL exporters to watch for anomalous traffic and API quota spikes.

## Incident Response

If you suspect compromise:
1. Revoke affected API keys immediately.
2. Rotate all secrets stored in `.env` or secret managers.
3. Capture logs from `youtube_extension_api.log` and the Prometheus metrics service for forensic review.
4. Notify the security contacts using the procedure above.

Thank you for helping keep the UVAI YouTube Extension secure.
