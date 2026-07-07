# Shared libraries package
#
# When the backend runs from the repo root, this package shadows
# ``src/shared`` (which hosts ``shared.youtube``), silently breaking
# ``from shared.youtube import ...`` in local dev and pytest collection.
# Production Docker images copy only ``src/``, so this file never ships.
# Extending ``__path__`` lets both package roots resolve, making the
# shadowing failure mode impossible.
import os as _os

_src_shared = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src", "shared"
)
if _os.path.isdir(_src_shared) and _src_shared not in __path__:
    __path__.append(_src_shared)
del _os, _src_shared
