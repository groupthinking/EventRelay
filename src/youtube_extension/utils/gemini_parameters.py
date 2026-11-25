"""Model-aware sampling policy shared by Gemini API and Vertex callers.

Google recommends provider-managed sampling for Gemini 3 and newer.
Older Gemini models and other providers retain their configured overrides.
"""

import re
from typing import Any


def without_deprecated_sampling(model: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy, stripping sampling overrides only for Gemini >= 3.

    Accept bare, models/, Gateway google/, and Vertex publisher resource IDs.
    Do not infer a model version from arbitrary aliases or other providers.
    """
    match = re.fullmatch(r"gemini-(\d+)(?:[.-].*)?", model.strip().lower().rsplit("/", 1)[-1])
    result = dict(config)
    if match and int(match.group(1)) >= 3:
        for key in ("temperature", "top_p", "top_k", "topP", "topK"):
            result.pop(key, None)
    return result
