from typing import Dict, Type
from .base_agent import BaseAgent

_REG: Dict[str, Type[BaseAgent]] = {}

def register(cls: Type[BaseAgent]):
    _REG[cls.name] = cls
    return cls

def get(name: str) -> Type[BaseAgent]:
    if name not in _REG: raise KeyError(name)
    return _REG[name]
