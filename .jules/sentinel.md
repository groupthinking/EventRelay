## 2026-07-10 - Migrate away from MD5 for generic cache keys
**Vulnerability:** Use of `hashlib.md5` for hashing cache keys and general text processing across multiple backend services (`cache_service.py`, `database_optimizer.py`, `load_balancer.py`, etc.).
**Learning:** Even for non-cryptographic uses, `md5` is considered a weak hash function and is flagged by standard security scanners (like Bandit). Using it establishes a poor baseline and can lead to accidental use in security-sensitive contexts.
**Prevention:** Default to `hashlib.sha256()` across the codebase to maintain a secure baseline.
