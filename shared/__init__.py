# Shared libraries package
#
# When the backend runs from the repo root, this package shadows
# ``src/shared`` (which hosts ``shared.youtube``), silently breaking
# ``from shared.youtube import ...`` in local dev and pytest collection.
# Production Docker images copy only ``src/``, so this file never ships.
# Extending ``__path__`` lets both package roots resolve, making the
# shadowing failure mode impossible.
from pathlib import Path as _Path

_src_shared = str(_Path(__file__).resolve().parent.parent / "src" / "shared")
if _Path(_src_shared).is_dir() and _src_shared not in __path__:
    __path__.append(_src_shared)
del _Path, _src_shared
