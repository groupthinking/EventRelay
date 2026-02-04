#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

# Add src to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
src_dir = root_dir / "src"
sys.path.append(str(src_dir))

try:
    import dotenv

    dotenv.load_dotenv(root_dir / ".env")
    print("✅ .env loaded successfully")
except ImportError:
    print("⚠️ python-dotenv not installed. Using existing environment variables.")


def check_m1_native():
    import platform

    is_arm = platform.machine() == "arm64"
    is_native = os.getenv("CPUTYPE") != "x86_64"  # Basic check
    print(f"🖥️  Architecture: {platform.machine()}")
    if is_arm:
        print("✅ Running natively on Apple Silicon")
    else:
        print("⚠️ Running under Rosetta 2? (Detected x86_64)")


def check_keys():
    print("\n🔑  API Key Validation:")
    keys_to_check = {
        "YOUTUBE_API_KEY": "YouTube Data API v3",
        "GEMINI_API_KEY": "Google Gemini API",
        "OPENAI_API_KEY": "OpenAI API",
        "ANTHROPIC_API_KEY": "Anthropic Claude API",
        "STITCH_ACCESS_TOKEN": "Google Stitch (OAuth)",
    }

    for key, label in keys_to_check.items():
        val = os.getenv(key)
        if not val:
            print(f"   ❌ {label}: NOT SET")
            continue

        # Test basic format
        if key == "OPENAI_API_KEY" and not val.startswith("sk-"):
            print(f"   ⚠️ {label}: Malformed key (should start with sk-)")
        elif key == "YOUTUBE_API_KEY" and not val.startswith("AIza"):
            print(f"   ⚠️ {label}: Malformed key (should start with AIza)")
        else:
            print(f"   ✅ {label}: CONFIGURED ({'*' * 8}{val[-4:]})")


def check_imports():
    print("\n📦 Module Import Verification:")
    modules = [
        "youtube_extension.backend.services",
        "uvai.api",
        "pydantic_core",
        "googleapiclient",
        "openai",
        "anthropic",
        "google.generativeai",
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"   ✅ {mod}")
        except ImportError as e:
            print(f"   ❌ {mod}: {e}")


if __name__ == "__main__":
    print("🚀 EVR Environment Calibration Utility")
    print("=" * 40)
    check_m1_native()
    check_keys()
    check_imports()
    print("=" * 40)
