"""Regression guard: optional google-genai must never break module import.

`src/youtube_extension/main.py` includes routers inside broad try/except blocks,
so an ImportError (or NameError from an annotation referencing a missing SDK
symbol) anywhere in the transitive import chain silently drops entire routers.
`src/agents/gemini_video_master_agent.py` imports `google.genai` optionally, so
it must stay importable when the SDK is absent.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_IMPORT_WITHOUT_GENAI = textwrap.dedent(
    """
    import builtins
    import sys

    _real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "google.genai" or name.startswith("google.genai."):
            raise ImportError("google.genai blocked for regression test")
        return _real_import(name, *args, **kwargs)

    builtins.__import__ = _blocked_import
    for module in [m for m in sys.modules if m.startswith("google")]:
        del sys.modules[module]

    from agents import gemini_video_master_agent as master

    assert master.GEMINI_AVAILABLE is False, "SDK block did not take effect"
    assert master.genai is None
    assert master.types is None
    # Annotation must not be evaluated at class-body execution time.
    assert callable(master.GeminiVideoMasterAgent._build_gemini_generation_config)
    print("OK")
    """
)


def test_gemini_master_agent_imports_without_google_genai() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_WITHOUT_GENAI],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
    )

    assert result.returncode == 0, (
        "gemini_video_master_agent failed to import without google-genai:\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert "OK" in result.stdout
