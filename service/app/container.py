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
        self.settings = settings or get_settings()
        self._store: JobStore | None = None

    @property
    def store(self) -> JobStore:
        if self._store is None:
            self._store = self._build_store()
        return self._store

    def _build_store(self) -> JobStore:
        dsn = self.settings.database_url
        if dsn:
            # Imported lazily so tests/local don't require the async DB driver.
            from .store.sqlalchemy_store import SqlAlchemyJobStore

            return SqlAlchemyJobStore(dsn)
        return InMemoryJobStore()


# Module-level container; overridable in tests via dependency_overrides.
_container = Container()


def get_container() -> Container:
    return _container


def get_store() -> JobStore:
    return _container.store
