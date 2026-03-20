#!/usr/bin/env python3
"""
Build plan models for structured instruction extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class BuildStep:
    """Single actionable build step derived from video analysis."""

    step_number: int
    action: str
    description: str
    target_file: str
    code: str = ""
    dependencies: List[int] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class BuildPlan:
    """Ordered build plan that downstream generators can consume."""

    title: str
    summary: str
    prerequisites: List[str] = field(default_factory=list)
    steps: List[BuildStep] = field(default_factory=list)
