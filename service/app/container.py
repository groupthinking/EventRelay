"""Dependency-injection container (the one pattern preserved from the legacy repo).

Holds the singletons the app needs — store, transcript provider, model seam —
and hands them to routes/jobs. This is the only place providers are selected;
tests inject fakes by overriding the private attributes.
"""

from __future__ import annotations

from .config import Settings, get_settings
from .llm.base import LLMClient
from .pipeline.transcript import TranscriptProvider
from .store.base import JobStore
from .store.memory import InMemoryJobStore


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._store: JobStore | None = None
        self._transcript_provider: TranscriptProvider | None = None
        self._llm: LLMClient | None = None

    @property
    def store(self) -> JobStore:
        if self._store is None:
            self._store = self._build_store()
        return self._store

    @property
    def transcript_provider(self) -> TranscriptProvider:
        if self._transcript_provider is None:
            from .pipeline.transcript import YouTubeCaptionsProvider

            self._transcript_provider = YouTubeCaptionsProvider()
        return self._transcript_provider

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = self._build_llm()
        return self._llm

    def _build_store(self) -> JobStore:
        dsn = self.settings.database_url
        if dsn:
            from .store.sqlalchemy_store import SqlAlchemyJobStore

            return SqlAlchemyJobStore(dsn)
        return InMemoryJobStore()

    def _build_llm(self) -> LLMClient:
        key = self.settings.gemini_api_key
        if not key:
            raise RuntimeError("No LLM configured: set EVENTRELAY_GEMINI_API_KEY")
        from .llm.gemini import GeminiLLMClient

        return GeminiLLMClient(api_key=key, model=self.settings.llm_model)


# Module-level container; overridable in tests via the private attributes.
_container = Container()


def get_container() -> Container:
    return _container


def get_store() -> JobStore:
    return _container.store
