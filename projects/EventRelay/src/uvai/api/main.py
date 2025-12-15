"""
Thin wrapper exposing the canonical ASGI app under the `uvai.api` namespace.
Run with: uvicorn uvai.api.main:app --reload
"""

from __future__ import annotations

# Set safe defaults early to avoid OpenMP duplicate aborts and ensure device fallbacks
import logging as _logging
import os as _os
import site as _site
from pathlib import Path as _Path

_os.environ.setdefault("OMP_NUM_THREADS", "1")
_os.environ.setdefault("MKL_NUM_THREADS", "1")
_os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
_os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def _dedupe_openmp_runtime() -> None:
    """Ensure only a single libiomp5.dylib copy is active.

    Mixing PyTorch wheels (torch + functorch, etc.) often installs multiple
    copies of Intel's OpenMP runtime. Instead of setting
    ``KMP_DUPLICATE_LIB_OK`` and hoping for the best, remove redundant copies
    eagerly so the process cannot abort later under load.
    """

    search_roots = {_Path(path) for path in _site.getsitepackages()}
    user_site = getattr(_site, "getusersitepackages", lambda: None)()
    if user_site:
        search_roots.add(_Path(user_site))

    # Add the project virtualenv if we're inside one.
    venv_prefix = _os.environ.get("VIRTUAL_ENV")
    if venv_prefix:
        search_roots.add(_Path(venv_prefix) / "lib")

    candidates = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("libiomp5.dylib"):
            try:
                real_path = path.resolve()
            except OSError:
                real_path = path
            candidates.append(real_path)

    unique_candidates = []
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        unique_candidates.append(path)

    if len(unique_candidates) <= 1:
        return

    preferred = next((p for p in unique_candidates if "torch/lib" in str(p)), unique_candidates[0])
    for path in unique_candidates:
        if path == preferred or not path.exists():
            continue
        disabled = path.with_suffix(path.suffix + ".disabled")
        try:
            path.rename(disabled)
            try:
                path.symlink_to(preferred)
            except OSError:
                # If symlink creation fails (e.g. on systems without permissions),
                # leave the file disabled; downstream imports will surface errors.
                pass
            _logging.getLogger("uvai.openmp").warning(
                "Removed duplicate OpenMP runtime at %s (kept %s)", disabled, preferred
            )
        except OSError as exc:
            raise RuntimeError(
                "Multiple libiomp5.dylib copies detected and cleanup failed. "
                "Please remove duplicates manually to prevent SIGABRT crashes."
            ) from exc


_dedupe_openmp_runtime()

if "DATABASE_URL" not in _os.environ:
    _runtime_dir = _Path(__file__).resolve().parents[3] / ".runtime"
    try:
        _runtime_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    _default_db = _runtime_dir / "app.db"
    _os.environ.setdefault("DATABASE_URL", f"sqlite:////{_default_db.as_posix().lstrip('/')}")

try:
    # Re-export the production-ready FastAPI app
    from youtube_extension.backend.main_v2 import app as app  # noqa: F401
except Exception as import_error:
    # Surface import errors clearly when running uvicorn
    raise RuntimeError(f"Failed to import canonical app: {import_error}")
