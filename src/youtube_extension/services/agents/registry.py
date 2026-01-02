
from .base_agent import BaseAgent

_REG: dict[str, type[BaseAgent]] = {}

def register(cls: type[BaseAgent]):
    _REG[cls.name] = cls
    return cls

def get(name: str) -> type[BaseAgent]:
    if name not in _REG: raise KeyError(name)
    return _REG[name]
