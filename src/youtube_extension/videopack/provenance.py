import hashlib, json
from typing import Dict

def stable_hash(obj: Dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()
