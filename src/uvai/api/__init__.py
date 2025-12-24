"""
UVAI API package

Preferred entrypoint: `uvai.api.main:app`
"""

# Optional convenience re-export
try:
    from .main import app as app  # noqa: F401
except Exception:
    # `main` may not import if dependencies are missing; avoid import-time crash here
    pass
