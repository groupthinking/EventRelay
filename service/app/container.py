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
class Container:
    """Dependency injection container.
    
    Lazily builds and caches service dependencies. Store selection is based
    on settings.database_url: SqlAlchemyJobStore (Postgres) if set, otherwise
    InMemoryJobStore for tests/local development.
    """
    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the container with the provided settings or the application default.
        
        Parameters:
            settings (Settings | None): Optional settings object to configure the container.
                If omitted, the global `get_settings()` result is used. Initializes internal
                caches (e.g., `_store`) to `None`.
        """
        self.settings = settings or get_settings()
        self._store: JobStore | None = None

    `@property`
    def store(self) -> JobStore:
        """
        Lazily constructs and caches the application's JobStore and returns it.
        
        Returns:
            JobStore: The container's cached JobStore instance.
        """
        if self._store is None:
            self._store = self._build_store()
        return self._store

    @property
    def transcript_provider(self) -> TranscriptProvider:
        """
        Lazily constructs and returns the application's transcript provider, defaulting to a YouTube captions provider.
        
        Returns:
            TranscriptProvider: The cached transcript provider instance; a YouTubeCaptionsProvider is created and stored on first access.
        """
        if self._transcript_provider is None:
            from .pipeline.transcript import YouTubeCaptionsProvider

            self._transcript_provider = YouTubeCaptionsProvider()
        return self._transcript_provider

    @property
    def llm(self) -> LLMClient:
        """
        Return the application's cached LLM client, building and caching it on first access.
        
        Returns:
            LLMClient: The configured LLM client instance.
        """
        if self._llm is None:
            self._llm = self._build_llm()
        return self._llm

    def _build_store(self) -> JobStore:
        """
        Constructs and returns the application's JobStore based on the configured database URL.
        
        Returns:
            JobStore: A `SqlAlchemyJobStore` when `self.settings.database_url` is set, otherwise an `InMemoryJobStore`.
        """
        dsn = self.settings.database_url
        if dsn:
            from .store.sqlalchemy_store import SqlAlchemyJobStore

            return SqlAlchemyJobStore(dsn)
        return InMemoryJobStore()

    def _build_llm(self) -> LLMClient:
        """
        Build an LLM client configured from the container's settings.
        
        Returns:
            LLMClient: a configured GeminiLLMClient instance using the container's Gemini API key and LLM model.
        
        Raises:
            RuntimeError: if the Gemini API key is not set in settings (set EVENTRELAY_GEMINI_API_KEY).
        """
        key = self.settings.gemini_api_key
        if not key:
            raise RuntimeError("No LLM configured: set EVENTRELAY_GEMINI_API_KEY")
        from .llm.gemini import GeminiLLMClient

        return GeminiLLMClient(api_key=key, model=self.settings.llm_model)


# Module-level container; overridable in tests via the private attributes.
_container = Container()


def get_container() -> Container:
    """
    Get the module-level dependency-injection container.
    
    Returns:
        container (Container): The shared module-level Container instance used by the application.
    """
    return _container


def get_store() -> JobStore:
    """
    Access the application's shared JobStore instance.
    
    Returns:
        The shared `JobStore` singleton managed by the module-level container.
    """
    return _container.store
