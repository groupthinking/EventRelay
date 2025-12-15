Title: Critical — Remove hardcoded API keys and secrets

Summary
-------
Several files in the repository contain hardcoded API keys or long-lived secrets. This is a critical security risk for production and public distribution.

Examples found (non-exhaustive)
- `build_extensions/uvai-platform/core/ai-reasoning-engine/video-analyzer/grok_enhanced_youtube_error.py` contains a hardcoded `grok_api_key` string.
- `scripts/production_demo.py` contains `API_KEY = "uvai_prod_10ac559f899665b1cb9dbf075b6966a0"`.
- Various archived artifacts and frontend config files reference `gemini_api_key` and other env keys (may contain secrets).

Risk
----
- Credential leakage, unauthorized API usage, unexpected billing, and reputational damage.

Recommended remediation
----------------------
1. Immediately remove any hardcoded secrets from source tree.
2. Rotate compromised keys (on provider consoles) and mark them as revoked.
3. Replace secrets with environment variables and a well-documented `.env.example` or secret manager integration.
4. Add a repo pre-commit hook that detects API-key-like patterns and blocks commits.
5. Add a GitHub secret scanning/monitoring integration and run a secret-scan on git history (BFG or git-secrets) if keys were committed historically.

Suggested labels: security, critical, infra

Next steps (automated)
----------------------
- Create a focused PR to remove the two obvious hardcoded keys and add `.env.example` references.
- Provide a short runbook for key rotation and evidence of rotation to close this issue.
