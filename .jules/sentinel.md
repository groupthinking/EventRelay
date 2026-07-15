## 2026-07-09 - Replace weak MD5 hashing with SHA-256 for caching
**Vulnerability:** Weak MD5 hashes were being used for generating cache keys and processing IDs across multiple backend services (e.g., `cache_service.py`, `database_optimizer.py`, etc.).
**Learning:** This repo frequently uses hashes for non-cryptographic purposes (caching and IDs). However, using MD5 triggers static analysis security warnings (like Bandit rules B324/B303) as the algorithm is vulnerable to collision attacks and considered insecure by modern cryptographic standards.
**Prevention:** Avoid using `hashlib.md5()` entirely. Default to `hashlib.sha256()` even for non-cryptographic uses to maintain a secure baseline and comply with automated security policies.
