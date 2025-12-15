from enum import Enum
class UpgradePolicy(str, Enum):
    hard_fail = "hard_fail"
    best_effort = "best_effort"

def upgrade_to_v0(data: dict) -> dict:
    # shim older shapes in storage/video_packs/*/pack.json \uc0\u8594  v0 fields
    # (add minimal keys if missing; do not change semantics)
    data.setdefault("version", "v0")
    data.setdefault("metrics", {})
    data.setdefault("concepts", [])
    data.setdefault("keyframes", [])
    data.setdefault("requirements", [])
    data.setdefault("code_snippets", [])
    data.setdefault("artifacts", [])
    return data
