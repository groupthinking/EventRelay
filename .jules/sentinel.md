## 2026-07-10 - Migrate away from MD5 for generic cache keys
**Vulnerability:** Use of `hashlib.md5` for hashing cache keys and general text processing across multiple backend services (`cache_service.py`, `database_optimizer.py`, `load_balancer.py`, etc.).
**Learning:** Even for non-cryptographic uses, `md5` is considered a weak hash function and is flagged by standard security scanners (like Bandit). Using it establishes a poor baseline and can lead to accidental use in security-sensitive contexts.
**Prevention:** Default to `hashlib.sha256()` across the codebase to maintain a secure baseline.

## 2026-07-11 - Prevent Information Disclosure in API Error Responses
**Vulnerability:** API routes (`agents/actions`, `extract-events`, `video/search`) were catching exceptions and passing the raw `error.message` or `String(error)` directly to the client in JSON responses. This could leak sensitive internal details such as stack traces, database query failures, or downstream API key warnings.
**Learning:** Using dynamic error strings from exceptions in client-facing responses is an information disclosure risk. Even when an upstream provider fails (e.g. OpenAI returning 401), forwarding that message verbatim can map internal architecture for attackers. Furthermore, global changes like blindly replacing `md5` with `sha256` or removing `shell=True` without `shlex.split` cause severe regressions and constitute security theater if not contextually evaluated.
**Prevention:** Always hardcode generic error messages in `catch` blocks for client-facing API responses (e.g., `{ error: 'Action generation failed' }`). Log the detailed, dynamic error securely on the server-side instead. Evaluate security fixes within their specific context to avoid functional regressions.
