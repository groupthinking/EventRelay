import asyncio
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Optional


class ModelProvider(Enum):
    """Supported AI model providers."""

    OPENAI = "openai"
    CLAUDE = "claude"
    GROK = "grok"
    GEMINI = "gemini"


class TokenBucket:
    """
    A token bucket rate limiter.
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

    async def consume(self, amount: int = 1) -> float:
        """
        Consume tokens. Returns the wait time if tokens are not available.
        """
        async with self.lock:
            now = time.time()
            # Refill tokens
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= amount:
                self.tokens -= amount
                return 0.0

            # Need to wait
            deficit = amount - self.tokens
            wait_time = deficit / self.refill_rate

            # Pretend we waited and consumed the tokens at that future time
            self.tokens -= amount
            return wait_time

    def get_approximate_usage(self) -> int:
        """Returns an approximation of how many tokens were used recently"""
        now = time.time()
        elapsed = now - self.last_refill
        current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        return int(max(0, self.capacity - current_tokens) + 0.5)


class RateLimiter:
    """
    Basic rate limiter for AI API requests.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize rate limiter with configuration.

        Args:
            config: Dictionary mapping provider name to rate limit settings
                   e.g., {"claude": {"requests_per_minute": 100, "tokens_per_minute": 50000}}
        """
        self.config = config if config is not None else {}
        self._request_buckets: dict[str, TokenBucket] = {}
        self._token_buckets: dict[str, TokenBucket] = {}

    def _get_or_create_buckets(self, provider_name: str) -> tuple[TokenBucket, TokenBucket]:
        if provider_name not in self._request_buckets:
            provider_config = self.config.get(provider_name, {})
            # Default to 100 requests per minute
            req_limit = provider_config.get("requests_per_minute", 100)
            req_refill = req_limit / 60.0
            self._request_buckets[provider_name] = TokenBucket(req_limit, req_refill)

            # Default to 50000 tokens per minute
            tok_limit = provider_config.get("tokens_per_minute", 50000)
            tok_refill = tok_limit / 60.0
            self._token_buckets[provider_name] = TokenBucket(tok_limit, tok_refill)

        return self._request_buckets[provider_name], self._token_buckets[provider_name]

    async def wait_if_needed(self, provider: ModelProvider, tokens: int = 0):
        """
        Check rate limits and wait if necessary.

        Args:
            provider: Model provider to check
            tokens: Estimated tokens for this request
        """
        provider_name = provider.value
        req_bucket, tok_bucket = self._get_or_create_buckets(provider_name)

        # We first check both wait times, then sleep the max.
        # This simplifies the locking, although in reality they are consumed immediately.
        # But for requests, we always consume 1.
        req_wait = await req_bucket.consume(1)
        tok_wait = 0.0
        if tokens > 0:
            tok_wait = await tok_bucket.consume(tokens)

        max_wait = max(req_wait, tok_wait)
        if max_wait > 0:
            await asyncio.sleep(max_wait)

    def get_statistics(self) -> dict[str, Any]:
        """Get current rate limiting statistics."""
        stats = {}

        for provider_name in set(self._request_buckets.keys()).union(self.config.keys()):
            req_bucket, tok_bucket = self._get_or_create_buckets(provider_name)

            stats[provider_name] = {
                "requests_last_minute": int(req_bucket.get_approximate_usage()),
                "tokens_last_minute": int(tok_bucket.get_approximate_usage()),
                "limit_requests": self.config.get(provider_name, {}).get(
                    "requests_per_minute", 100
                ),
                "limit_tokens": self.config.get(provider_name, {}).get(
                    "tokens_per_minute", 50000
                ),
            }

        return stats
