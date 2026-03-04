from enum import Enum


class UpgradePolicy(str, Enum):
    hard_fail = "hard_fail"
    best_effort = "best_effort"

def upgrade_to_v0(data: dict) -> dict:
    # shim older shapes in storage/video_packs/*/pack.json → v0 fields
    data.setdefault("version", "v0")
    data.setdefault("metrics", {})
    data.setdefault("concepts", [])
    data.setdefault("chapters", [])
    data.setdefault("keyframes", [])
    data.setdefault("requirements", [])
    data.setdefault("code_snippets", [])
    data.setdefault("code_cues", [])
    data.setdefault("tasks", [])
    data.setdefault("artifacts", [])
    return data
