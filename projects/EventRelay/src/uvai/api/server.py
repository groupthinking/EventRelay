from __future__ import annotations
import os
import uvicorn


def main() -> None:
    host = os.getenv("UVAI_HOST", "0.0.0.0")
    port = int(os.getenv("UVAI_PORT", "8000"))
    reload = os.getenv("UVAI_RELOAD", "1").lower() in ("1", "true", "yes")

    uvicorn.run(
        "uvai.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
