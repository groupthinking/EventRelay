#!/usr/bin/env python3
"""
QuantomCode Cryptographic Signer
================================

Security layer for Vision-Reasoning Stack using ECDSA P-256 signatures.
All vision outputs are signed before caching/transmission for tamper verification.
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger("QuantomCodeSigner")


class QuantomCodeSigner:
    """
    Cryptographic signing and verification for vision outputs.

    Uses ECDSA P-256 curve with existing quantomcode keys for:
    - Signing all vision processing outputs
    - Verifying cached/received data integrity
    - Creating tamper-proof manifests
    """

    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ):
        """
        Initialize signer with key paths.

        Args:
            private_key_path: Path to ECDSA private key PEM
            public_key_path: Path to ECDSA public key PEM
        """
        self._private_key = None
        self._public_key = None

        # Default paths relative to EventRelay root
        root = Path(__file__).parent.parent.parent
        self._private_key_path = private_key_path or str(
            root / "quantomcode_private.pem"
        )
        self._public_key_path = public_key_path or str(root / "quantomcode_public.pem")

        self._load_keys()

    def _load_keys(self):
        """Load ECDSA keys from PEM files."""
        try:
            # Load private key (for signing)
            private_path = Path(self._private_key_path)
            if private_path.exists():
                with open(private_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(
                        f.read(), password=None
                    )
                logger.info("✅ Loaded QuantomCode private key")
            else:
                logger.warning(f"⚠️ Private key not found: {self._private_key_path}")

            # Load public key (for verification)
            public_path = Path(self._public_key_path)
            if public_path.exists():
                with open(public_path, "rb") as f:
                    self._public_key = serialization.load_pem_public_key(f.read())
                logger.info("✅ Loaded QuantomCode public key")
            else:
                logger.warning(f"⚠️ Public key not found: {self._public_key_path}")

        except Exception as e:
            logger.error(f"❌ Failed to load keys: {e}")
            raise

    def _serialize_data(self, data: dict[str, Any]) -> bytes:
        """
        Serialize data deterministically for signing.

        Uses sorted keys and consistent JSON formatting to ensure
        identical serialization across systems.
        """
        return json.dumps(
            data, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")

    def sign_output(self, data: dict[str, Any]) -> bytes:
        """
        Sign vision output with private key.

        Args:
            data: Dictionary containing vision processing output

        Returns:
            ECDSA signature as bytes

        Raises:
            ValueError: If private key not available
        """
        if not self._private_key:
            raise ValueError("Private key not available for signing")

        serialized = self._serialize_data(data)
        signature = self._private_key.sign(serialized, ec.ECDSA(hashes.SHA256()))

        logger.debug(f"Signed data hash: {hashlib.sha256(serialized).hexdigest()[:16]}")
        return signature

    def sign_output_b64(self, data: dict[str, Any]) -> str:
        """Sign and return base64-encoded signature for JSON transmission."""
        return base64.b64encode(self.sign_output(data)).decode("ascii")

    def verify_signature(self, data: dict[str, Any], signature: bytes) -> bool:
        """
        Verify signature against data using public key.

        Args:
            data: Original data dictionary
            signature: ECDSA signature bytes

        Returns:
            True if signature is valid, False otherwise
        """
        if not self._public_key:
            raise ValueError("Public key not available for verification")

        serialized = self._serialize_data(data)

        try:
            self._public_key.verify(signature, serialized, ec.ECDSA(hashes.SHA256()))
            logger.debug("✅ Signature verified successfully")
            return True
        except InvalidSignature:
            logger.warning("❌ Signature verification failed")
            return False

    def verify_signature_b64(self, data: dict[str, Any], signature_b64: str) -> bool:
        """Verify base64-encoded signature."""
        signature = base64.b64decode(signature_b64)
        return self.verify_signature(data, signature)

    def create_manifest(
        self, results: list[dict[str, Any]], batch_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Create tamper-proof manifest of processed outputs.

        Args:
            results: List of vision result dictionaries
            batch_id: Optional batch identifier

        Returns:
            Manifest dictionary with signature
        """
        # Create ordered hash of all results
        result_hashes = []
        for result in results:
            serialized = self._serialize_data(result)
            result_hash = hashlib.sha256(serialized).hexdigest()
            result_hashes.append(result_hash)

        manifest = {
            "version": "1.0",
            "batch_id": batch_id
            or f"batch_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result_count": len(results),
            "result_hashes": result_hashes,
            "merkle_root": self._compute_merkle_root(result_hashes),
        }

        # Sign the manifest
        manifest["signature"] = self.sign_output_b64(manifest)

        logger.info(
            f"📜 Created manifest: {manifest['batch_id']} "
            f"({manifest['result_count']} results)"
        )
        return manifest

    def _compute_merkle_root(self, hashes: list[str]) -> str:
        """Compute Merkle root of hash list for efficient verification."""
        if not hashes:
            return hashlib.sha256(b"").hexdigest()

        if len(hashes) == 1:
            return hashes[0]

        # Pad to even length
        if len(hashes) % 2 == 1:
            hashes = hashes + [hashes[-1]]

        # Combine pairs
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())

        return self._compute_merkle_root(next_level)

    def is_signing_available(self) -> bool:
        """Check if signing is available (private key loaded)."""
        return self._private_key is not None

    def is_verification_available(self) -> bool:
        """Check if verification is available (public key loaded)."""
        return self._public_key is not None


# Global singleton instance
_signer_instance: Optional[QuantomCodeSigner] = None


def get_signer() -> QuantomCodeSigner:
    """Get or create global signer instance."""
    global _signer_instance
    if _signer_instance is None:
        _signer_instance = QuantomCodeSigner()
    return _signer_instance


if __name__ == "__main__":
    # Test signing and verification
    logging.basicConfig(level=logging.DEBUG)

    signer = QuantomCodeSigner()

    test_data = {
        "provider": "google_video_ai",
        "labels": ["clapperboard", "video", "production"],
        "ocr_text": "SCENE 12 TAKE 3",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print("\n🔐 QuantomCode Signer Test")
    print("=" * 40)

    if signer.is_signing_available():
        signature = signer.sign_output(test_data)
        print(f"✅ Signed data: {len(signature)} bytes")
        print(f"   Signature (b64): {base64.b64encode(signature).decode()[:50]}...")

        if signer.is_verification_available():
            valid = signer.verify_signature(test_data, signature)
            print(f"✅ Verification: {'PASSED' if valid else 'FAILED'}")

            # Test tamper detection
            test_data["labels"].append("tampered")
            valid_tampered = signer.verify_signature(test_data, signature)
            print(
                f"✅ Tamper detection: {'PASSED' if not valid_tampered else 'FAILED'}"
            )
    else:
        print("⚠️ Private key not available for signing test")
