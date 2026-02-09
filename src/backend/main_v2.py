# Shim module to support imports like `from backend.main_v2 import app`
# Points to the actual production backend entry point
from youtube_extension.backend.main import app  # noqa: F401
