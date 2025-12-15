import importlib
from typing import Dict, Any, Callable, Awaitable

AdapterFunc = Callable[[str, Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]

# Registry of available deployment adapters
_adapters: Dict[str, str] = {
    "vercel": "youtube_extension.backend.deploy.vercel",
    "netlify": "youtube_extension.backend.deploy.netlify",
    "fly": "youtube_extension.backend.deploy.fly",
}

_loaded: Dict[str, AdapterFunc] = {}

# Registry of adapter classes for new architecture
_adapter_classes: Dict[str, str] = {
    "vercel": "youtube_extension.backend.deploy.vercel:VercelAdapter",
    "netlify": "youtube_extension.backend.deploy.netlify:NetlifyAdapter",
    "fly": "youtube_extension.backend.deploy.fly:FlyAdapter",
}

_loaded_classes: Dict[str, Any] = {}

def get_adapter(target: str) -> AdapterFunc:
    """Get legacy adapter function"""
    target = target.lower()
    if target not in _adapters:
        raise ValueError(f"Unsupported deployment target: {target}")
    if target not in _loaded:
        module = importlib.import_module(_adapters[target])
        _loaded[target] = getattr(module, "deploy")  # type: ignore
    return _loaded[target]

def get_adapter_class(target: str) -> Any:
    """Get new architecture adapter class"""
    target = target.lower()
    if target not in _adapter_classes:
        raise ValueError(f"Unsupported deployment target: {target}")

    if target not in _loaded_classes:
        module_path, class_name = _adapter_classes[target].split(':')
        module = importlib.import_module(module_path)
        _loaded_classes[target] = getattr(module, class_name)

    return _loaded_classes[target]

async def deploy_project(target: str, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """Unified entrypoint to call specific adapter - supports both old and new architecture"""
    try:
        # Try new architecture first
        adapter_class = get_adapter_class(target)
        adapter = adapter_class()
        result = await adapter.deploy(project_path, project_config, env)

        # Convert new architecture result to legacy format
        return {
            "status": result.status,
            "deployment_id": result.deployment_id,
            "url": result.url,
            "platform": result.platform,
            "error": result.error_message,
            "build_log_url": result.build_log_url,
            **result.metadata
        }

    except (ImportError, AttributeError):
        # Fall back to legacy architecture
        adapter = get_adapter(target)
        return await adapter(project_path, project_config, env)

def list_available_adapters() -> Dict[str, str]:
    """List all available deployment adapters"""
    return {
        "vercel": "Vercel deployment platform",
        "netlify": "Netlify deployment platform",
        "fly": "Fly.io deployment platform"
    }

def is_adapter_available(target: str) -> bool:
    """Check if a deployment adapter is available"""
    try:
        get_adapter_class(target)
        return True
    except (ValueError, ImportError, AttributeError):
        try:
            get_adapter(target)
            return True
        except (ValueError, ImportError, AttributeError):
            return False
