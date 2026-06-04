"""Dependency-injection container (the one pattern preserved from the legacy repo).

Holds the singletons the app needs and hands them to routes via FastAPI
`Depends`. Store selection happens here and nowhere else: Postgres when a DSN is
configured, in-memory otherwise (tests/local).
"""
from __future__ import annotations

from .config import Settings, get_settings
from .store.base import JobStore
from .store.memory import InMemoryJobStore


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the dependency container with application settings and prepare lazy store construction.
        
        Parameters:
            settings (Settings | None): Optional Settings to use for the container. If omitted, the global `get_settings()` result is used.
        
        Notes:
            The actual `JobStore` instance is not created here; `self._store` is initialized to `None` so the store is constructed lazily on first access to the `store` property.
        """
        self.settings = settings or get_settings()
        self._store: JobStore | None = None

    @property
    def store(self) -> JobStore:
        """
        Lazily construct and return the application's JobStore instance.
        
        Constructs the store on first access and caches it for subsequent calls so the same `JobStore` is returned thereafter.
        
        Returns:
            JobStore: The configured application job store.
        """
        if self._store is None:
            self._store = self._build_store()
        return self._store

    def _build_store(self) -> JobStore:
        """
        Construct the application's JobStore implementation based on the configured database URL.
        
        Returns:
            JobStore: A `SqlAlchemyJobStore` initialized with `settings.database_url` if a DSN is configured, otherwise an `InMemoryJobStore`.
        """
        dsn = self.settings.database_url
        if dsn:
            # Imported lazily so tests/local don't require the async DB driver.
            from .store.sqlalchemy_store import SqlAlchemyJobStore

            return SqlAlchemyJobStore(dsn)
        return InMemoryJobStore()


# Module-level container; overridable in tests via dependency_overrides.
_container = Container()


def get_container() -> Container:
    """
    Get the module-level Container singleton used as the default dependency source.
    
    This returns the single Container instance created at module import time. Intended to be used with FastAPI dependency injection and can be overridden in tests via FastAPI's dependency_overrides.
    
    Returns:
        Container: The module-level Container instance.
    """
    return _container


def get_store() -> JobStore:
    """
    Retrieve the application's singleton JobStore from the module container.
    
    Returns:
        The configured `JobStore` instance (cached by the container).
    """
    return _container.store
