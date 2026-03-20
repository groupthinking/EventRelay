#!/usr/bin/env python3
"""
Hybrid Cache
============

Two-tier caching following Flutter asset transformation pattern:
- Edge Layer: Local SQLite for low-latency frame lookups
- Cloud Layer: GCS for large video files and shared state

All cached items include QuantomCode signatures for integrity verification.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Cloud storage
try:
    from google.cloud import storage

    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    logging.warning("Google Cloud Storage not available")

from quantomcode_signer import get_signer

logger = logging.getLogger("HybridCache")


class HybridCache:
    """
    Two-tier cache with edge (local) and cloud (GCS) layers.

    Write Path:
    1. Store in local SQLite (immediate)
    2. Async upload to GCS (background)

    Read Path:
    1. Check local SQLite first
    2. Fall back to GCS if not found
    3. Populate local cache from GCS hit

    All items are verified with QuantomCode signatures.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        gcs_bucket: Optional[str] = None,
        gcs_prefix: str = "vision-cache",
        ttl_seconds: int = 3600 * 24,  # 24 hours default
    ):
        """
        Initialize hybrid cache.

        Args:
            db_path: Path to local SQLite database
            gcs_bucket: GCS bucket name for cloud layer
            gcs_prefix: Prefix for GCS objects
            ttl_seconds: Cache TTL in seconds
        """
        self._db_path = db_path or str(
            Path(__file__).parent / "vision_cache.db"
        )
        self._gcs_bucket = gcs_bucket or os.getenv(
            "VISION_GCS_BUCKET", "uvai-vision-cache"
        )
        self._gcs_prefix = gcs_prefix
        self._ttl_seconds = ttl_seconds
        self._signer = get_signer()
        self._gcs_client = None
        self._bucket = None

        self._init_local_db()
        self._init_gcs()

    def _init_local_db(self):
        """Initialize local SQLite cache database."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_items (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                signature TEXT,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
        """)

        # Index for expiration cleanup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON cache_items(expires_at)
        """)

        conn.commit()
        conn.close()
        logger.info(f"✅ Local cache initialized: {self._db_path}")

    def _init_gcs(self):
        """Initialize GCS client for cloud layer."""
        if not HAS_GCS:
            logger.warning("GCS not available - cloud layer disabled")
            return

        try:
            self._gcs_client = storage.Client()
            self._bucket = self._gcs_client.bucket(self._gcs_bucket)
            logger.info(f"✅ GCS cache initialized: gs://{self._gcs_bucket}")
        except Exception as e:
            logger.warning(f"⚠️ GCS initialization failed: {e}")

    async def get(self, key: str, verify_signature: bool = True) -> Optional[dict]:
        """
        Get item from cache with signature verification.

        Args:
            key: Cache key
            verify_signature: Whether to verify QuantomCode signature

        Returns:
            Cached data dict, or None if not found/expired/invalid
        """
        # Try local cache first
        result = await self._get_local(key)

        if result is None and self._bucket:
            # Try GCS
            result = await self._get_gcs(key)
            if result:
                # Populate local cache from GCS hit
                await self._set_local(key, result["data"], result.get("signature"))

        if result is None:
            return None

        # Verify signature if required
        if verify_signature and result.get("signature"):
            if not self._verify_signature(result["data"], result["signature"]):
                logger.warning(f"❌ Signature verification failed: {key}")
                return None

        # Update access stats
        await self._update_access_stats(key)

        return result["data"]

    async def set(
        self,
        key: str,
        data: dict[str, Any],
        sign: bool = True,
        sync_to_cloud: bool = True,
    ) -> bool:
        """
        Store item in cache with optional signing and cloud sync.

        Args:
            key: Cache key
            data: Data to cache
            sign: Whether to sign with QuantomCode
            sync_to_cloud: Whether to async upload to GCS

        Returns:
            Success status
        """
        signature = None
        if sign and self._signer.is_signing_available():
            signature = self._signer.sign_output_b64(data)

        # Store locally (immediate)
        success = await self._set_local(key, data, signature)

        # Async sync to cloud
        if sync_to_cloud and self._bucket:
            asyncio.create_task(self._set_gcs(key, data, signature))

        return success

    async def _get_local(self, key: str) -> Optional[dict]:
        """Get from local SQLite cache."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_local_sync, key)

    def _get_local_sync(self, key: str) -> Optional[dict]:
        """Synchronous local get."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT data, signature, expires_at
            FROM cache_items
            WHERE cache_key = ?
            """,
            (key,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        data_str, signature, expires_at = row

        # Check expiration
        if expires_at < time.time():
            # Expired - schedule cleanup
            asyncio.create_task(self._delete_local(key))
            return None

        return {
            "data": json.loads(data_str),
            "signature": signature,
        }

    async def _set_local(
        self, key: str, data: dict, signature: Optional[str]
    ) -> bool:
        """Store in local SQLite cache."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._set_local_sync, key, data, signature
        )

    def _set_local_sync(
        self, key: str, data: dict, signature: Optional[str]
    ) -> bool:
        """Synchronous local set."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            now = time.time()
            expires_at = now + self._ttl_seconds

            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_items
                (cache_key, data, signature, created_at, expires_at, access_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (key, json.dumps(data), signature, now, expires_at),
            )

            conn.commit()
            conn.close()
            logger.debug(f"📥 Cached locally: {key}")
            return True
        except Exception as e:
            logger.error(f"Local cache error: {e}")
            return False

    async def _delete_local(self, key: str):
        """Delete from local cache."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_local_sync, key)

    def _delete_local_sync(self, key: str):
        """Synchronous local delete."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_items WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()

    async def _get_gcs(self, key: str) -> Optional[dict]:
        """Get from GCS cloud cache."""
        if not self._bucket:
            return None

        try:
            loop = asyncio.get_event_loop()
            blob_name = f"{self._gcs_prefix}/{key}.json"
            blob = self._bucket.blob(blob_name)

            content = await loop.run_in_executor(
                None, lambda: blob.download_as_string() if blob.exists() else None
            )

            if content:
                data = json.loads(content)
                logger.debug(f"☁️ GCS cache hit: {key}")
                return data

        except Exception as e:
            logger.warning(f"GCS get error: {e}")

        return None

    async def _set_gcs(self, key: str, data: dict, signature: Optional[str]):
        """Store in GCS cloud cache (async background)."""
        if not self._bucket:
            return

        try:
            loop = asyncio.get_event_loop()
            blob_name = f"{self._gcs_prefix}/{key}.json"
            blob = self._bucket.blob(blob_name)

            content = json.dumps(
                {
                    "data": data,
                    "signature": signature,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await loop.run_in_executor(
                None,
                lambda: blob.upload_from_string(
                    content, content_type="application/json"
                ),
            )
            logger.debug(f"☁️ Cached to GCS: {key}")

        except Exception as e:
            logger.warning(f"GCS set error: {e}")

    async def _update_access_stats(self, key: str):
        """Update access statistics for cache analytics."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_access_stats_sync, key)

    def _update_access_stats_sync(self, key: str):
        """Synchronous access stats update."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE cache_items
            SET access_count = access_count + 1, last_accessed = ?
            WHERE cache_key = ?
            """,
            (time.time(), key),
        )
        conn.commit()
        conn.close()

    def _verify_signature(self, data: dict, signature: str) -> bool:
        """Verify QuantomCode signature."""
        if not self._signer.is_verification_available():
            return True  # Skip if no public key

        return self._signer.verify_signature_b64(data, signature)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count of removed items."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cleanup_expired_sync)

    def _cleanup_expired_sync(self) -> int:
        """Synchronous cleanup."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM cache_items WHERE expires_at < ?", (time.time(),)
        )
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} expired cache items")

        return deleted

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_stats_sync)

    def _get_stats_sync(self) -> dict[str, Any]:
        """Synchronous stats collection."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM cache_items")
        total_items = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM cache_items WHERE expires_at < ?",
            (time.time(),),
        )
        expired_items = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(access_count) FROM cache_items")
        total_accesses = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_items": total_items,
            "expired_items": expired_items,
            "active_items": total_items - expired_items,
            "total_accesses": total_accesses,
            "local_db_path": self._db_path,
            "gcs_bucket": self._gcs_bucket if self._bucket else None,
            "gcs_enabled": self._bucket is not None,
        }


# Global singleton
_cache_instance: Optional[HybridCache] = None


def get_cache() -> HybridCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = HybridCache()
    return _cache_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def test():
        cache = HybridCache()

        print("\n💾 Hybrid Cache Test")
        print("=" * 40)

        # Test set/get cycle
        test_key = "test:vision:frame123"
        test_data = {
            "labels": ["clapperboard", "studio"],
            "ocr_text": "SCENE 12 TAKE 3",
            "confidence": 0.95,
        }

        print(f"\n📥 Setting: {test_key}")
        await cache.set(test_key, test_data)

        print(f"📤 Getting: {test_key}")
        result = await cache.get(test_key)
        print(f"   Result: {result}")
        print(f"   Match: {result == test_data}")

        # Get stats
        stats = await cache.get_stats()
        print(f"\n📊 Cache Stats: {stats}")

    asyncio.run(test())
