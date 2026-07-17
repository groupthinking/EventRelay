## 2024-07-09 - Replace weak MD5 hashing with SHA-256 for caching
**Vulnerability:** Weak MD5 hashes were being used for generating cache keys and processing IDs across multiple backend services (e.g., `cache_service.py`, `database_optimizer.py`, etc.).
**Learning:** This repo frequently uses hashes for non-cryptographic purposes (caching and IDs). However, using MD5 triggers static analysis security warnings (like Bandit rules B324/B303) as the algorithm is vulnerable to collision attacks and considered insecure by modern cryptographic standards.
**Prevention:** Avoid using `hashlib.md5()` entirely. Default to `hashlib.sha256()` even for non-cryptographic uses to maintain a secure baseline and comply with automated security policies.
## 2026-07-15 - Prevent Information Disclosure in 500 Responses
**Vulnerability:** API routes were returning internal server exceptions and stack traces directly to the client via `HTTPException(..., detail=str(e))`.
**Learning:** Developers often unintentionally leak sensitive deployment context (e.g., paths, database errors) when relying on generic exception catching blocks.
**Prevention:** Hardcode static error strings for unexpected 500 exceptions (e.g., `detail="Internal server error"`). The exception is still recorded server-side via `logger.error(...)`; use `exc_info=True` on handlers where the full traceback aids debugging (this is not yet applied uniformly across every handler). Client responses must never echo `str(e)` — including via f-strings such as `detail=f"...: {e}"`, which leak the same internal detail as `detail=str(e)`.
