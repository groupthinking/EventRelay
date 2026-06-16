"""
VERA Pillar 1: Identity — Cryptographic Agent Credentials

Every agent gets a signed JWT at pipeline start. The orchestrator verifies
the token before accepting any stage result. Think of it as a passport:
no agent acts without proving who it is, and that proof is unforgeable.

Dependencies: python-jose[cryptography]
Env vars: VERA_SIGNING_KEY, VERA_SIGNING_KEY_ID, VERA_TOKEN_LIFETIME_HOURS
"""

import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import VeraConfig, get_vera_config

logger = logging.getLogger("vera.identity")

# --- In-process fallback for revocation checks when Redis unavailable ---
_revoked_agents: dict[str, str] = {}  # agent_id → reason
_revoked_tokens: set[str] = set()     # token jti values


class AgentCredential:
    """Represents a verified agent credential."""

    __slots__ = ("agent_id", "agent_name", "maturity_level", "capability_ref",
                 "org_id", "environment", "token_id", "issued_at", "expires_at")

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        maturity_level: int = 0,
        capability_ref: str = "",
        org_id: str = "eventrelay",
        environment: str = "development",
        token_id: str = "",
        issued_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.maturity_level = maturity_level
        self.capability_ref = capability_ref or f"cap:{agent_name}-v1"
        self.org_id = org_id
        self.environment = environment
        self.token_id = token_id or str(uuid.uuid4())
        self.issued_at = issued_at or datetime.now(timezone.utc)
        self.expires_at = expires_at

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "maturity_level": self.maturity_level,
            "capability_ref": self.capability_ref,
            "org_id": self.org_id,
            "environment": self.environment,
            "token_id": self.token_id,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class IdentityService:
    """Issues and verifies agent JWT credentials.

    When VERA_SIGNING_KEY is configured, uses ES256 JWTs.
    Falls back to HMAC-SHA256 signed tokens when no key is available
    (development mode only — logs a warning).
    """

    def __init__(self, config: Optional[VeraConfig] = None):
        self.config = config or get_vera_config()
        self._use_jwt = self.config.has_signing_key

        if self._use_jwt:
            try:
                from jose import jwt as jose_jwt  # noqa: F401
                self._jose_jwt = jose_jwt
                logger.info("VERA Identity: ES256 JWT mode (production)")
            except ImportError:
                logger.warning(
                    "python-jose not installed — falling back to HMAC tokens. "
                    "Install with: pip install python-jose[cryptography]"
                )
                self._use_jwt = False
        else:
            logger.warning(
                "VERA Identity: HMAC fallback mode (VERA_SIGNING_KEY not set). "
                "Agent tokens are signed but not with asymmetric crypto."
            )

    def issue_credential(
        self,
        agent_id: str,
        agent_name: str,
        maturity_level: int = 0,
        capabilities: Optional[list[str]] = None,
    ) -> tuple[str, AgentCredential]:
        """Issue a signed credential token for an agent.

        Returns:
            (token_string, AgentCredential) — the token to include in
            pipeline messages and the parsed credential object.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.config.token_lifetime_hours)
        token_id = str(uuid.uuid4())

        credential = AgentCredential(
            agent_id=agent_id,
            agent_name=agent_name,
            maturity_level=maturity_level,
            capability_ref=f"cap:{agent_name}-v1",
            org_id="eventrelay",
            environment=self.config.environment,
            token_id=token_id,
            issued_at=now,
            expires_at=expires,
        )

        if self._use_jwt:
            token = self._issue_jwt(credential)
        else:
            token = self._issue_hmac_token(credential)

        logger.info(
            "credential_issued",
            extra={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "maturity_level": maturity_level,
                "token_id": token_id,
                "expires": expires.isoformat(),
            },
        )

        return token, credential

    def verify_credential(self, token: str) -> Optional[AgentCredential]:
        """Verify a credential token and return the parsed credential.

        Returns None if the token is invalid, expired, or revoked.
        """
        if self._use_jwt:
            credential = self._verify_jwt(token)
        else:
            credential = self._verify_hmac_token(token)

        if credential is None:
            return None

        # Check revocation
        if credential.agent_id in _revoked_agents:
            logger.warning(
                "credential_revoked",
                extra={
                    "agent_id": credential.agent_id,
                    "reason": _revoked_agents[credential.agent_id],
                },
            )
            return None

        if credential.token_id in _revoked_tokens:
            logger.warning(
                "token_revoked",
                extra={"token_id": credential.token_id},
            )
            return None

        return credential

    def revoke_agent(self, agent_id: str, reason: str) -> None:
        """Revoke all credentials for an agent (kill switch integration)."""
        _revoked_agents[agent_id] = reason
        logger.critical(
            "agent_revoked",
            extra={"agent_id": agent_id, "reason": reason},
        )

    def revoke_token(self, token_id: str) -> None:
        """Revoke a specific token by its JTI."""
        _revoked_tokens.add(token_id)
        logger.warning("token_revoked", extra={"token_id": token_id})

    def is_revoked(self, agent_id: str) -> bool:
        """Check if an agent's credentials are revoked."""
        return agent_id in _revoked_agents

    # --- JWT implementation (production) ---

    def _issue_jwt(self, cred: AgentCredential) -> str:
        claims = {
            "sub": f"agent:{cred.agent_id}",
            "iss": "vera-identity-service",
            "iat": cred.issued_at,
            "exp": cred.expires_at,
            "jti": cred.token_id,
            "vera": {
                "agent_name": cred.agent_name,
                "maturity_level": cred.maturity_level,
                "capability_ref": cred.capability_ref,
                "org_id": f"org:{cred.org_id}",
                "environment": cred.environment,
            },
        }
        return self._jose_jwt.encode(
            claims,
            self.config.signing_key,
            algorithm="ES256",
            headers={"kid": self.config.signing_key_id},
        )

    def _verify_jwt(self, token: str) -> Optional[AgentCredential]:
        try:
            claims = self._jose_jwt.decode(
                token,
                self.config.signing_key,
                algorithms=["ES256"],
                options={"verify_exp": True},
            )
            vera = claims.get("vera", {})
            return AgentCredential(
                agent_id=claims["sub"].removeprefix("agent:"),
                agent_name=vera.get("agent_name", ""),
                maturity_level=vera.get("maturity_level", 0),
                capability_ref=vera.get("capability_ref", ""),
                org_id=vera.get("org_id", "").removeprefix("org:"),
                environment=vera.get("environment", ""),
                token_id=claims.get("jti", ""),
                issued_at=datetime.fromtimestamp(claims["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
            )
        except Exception as e:
            logger.warning("jwt_verification_failed", extra={"error": str(e)})
            return None

    # --- HMAC fallback implementation (development) ---

    def _issue_hmac_token(self, cred: AgentCredential) -> str:
        """Create an HMAC-signed token string for development use."""
        payload = (
            f"{cred.agent_id}|{cred.agent_name}|{cred.maturity_level}|"
            f"{cred.capability_ref}|{cred.org_id}|{cred.environment}|"
            f"{cred.token_id}|{int(cred.issued_at.timestamp())}|"
            f"{int(cred.expires_at.timestamp())}"
        )
        sig = self._hmac_sign(payload)
        return f"vera-hmac:{payload}:{sig}"

    def _verify_hmac_token(self, token: str) -> Optional[AgentCredential]:
        """Verify an HMAC-signed token string."""
        if not token.startswith("vera-hmac:"):
            logger.warning("invalid_token_format")
            return None

        parts = token[len("vera-hmac:"):].rsplit(":", 1)
        if len(parts) != 2:
            logger.warning("malformed_hmac_token")
            return None

        payload, sig = parts
        if self._hmac_sign(payload) != sig:
            logger.warning("hmac_signature_mismatch")
            return None

        fields = payload.split("|")
        if len(fields) != 9:
            logger.warning("hmac_field_count_mismatch")
            return None

        agent_id, agent_name, maturity_str, cap_ref, org_id, env, token_id, iat_str, exp_str = fields

        # Check expiry
        now = time.time()
        exp = int(exp_str)
        if now > exp:
            logger.warning("hmac_token_expired", extra={"agent_id": agent_id})
            return None

        return AgentCredential(
            agent_id=agent_id,
            agent_name=agent_name,
            maturity_level=int(maturity_str),
            capability_ref=cap_ref,
            org_id=org_id,
            environment=env,
            token_id=token_id,
            issued_at=datetime.fromtimestamp(int(iat_str), tz=timezone.utc),
            expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        )

    @staticmethod
    def _hmac_sign(payload: str) -> str:
        """HMAC-SHA256 sign a payload using a machine-derived key.

        In dev mode without VERA_SIGNING_KEY, we derive a stable key from
        the machine ID. This is NOT secure for production — it's a fallback
        so the identity flow works end-to-end during development.
        """
        import hmac as _hmac
        # Derive key from a combination of factors available at runtime
        key_material = f"vera-dev-{uuid.getnode()}"
        key = hashlib.sha256(key_material.encode()).digest()
        return _hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


# --- Module-level singleton ---

_identity_service: Optional[IdentityService] = None


def get_identity_service() -> IdentityService:
    """Get the singleton identity service."""
    global _identity_service
    if _identity_service is None:
        _identity_service = IdentityService()
    return _identity_service
