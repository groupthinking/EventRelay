"""
Real Mode Guard - Runtime protection against simulation code
==============================================================

This module enforces REAL_MODE_ONLY by detecting and preventing
simulation patterns from executing in production environments.

When REAL_MODE_ONLY=true (production), this guard will:
1. Detect simulation patterns in stack traces
2. Raise RuntimeError when simulation code is called
3. Prevent fake delays and placeholder implementations

This ensures all production code uses real implementations.
"""

import os
import sys
import traceback
from typing import List, Tuple


# Read environment variable at module load
REAL_MODE_ONLY = os.getenv("REAL_MODE_ONLY", "true").lower() in ("true", "1", "yes")


# Simulation patterns to detect
SIMULATION_PATTERNS = [
    "asyncio.sleep(0.0",  # Fake delays with small values
    "Math.random()",      # JavaScript-style fake metrics
    "hash(name) %",       # Fake health checks using hash
    "# Placeholder",      # Placeholder comments
    "# FAKE",            # Explicitly marked as fake
    "# Simulate",        # Simulation comments
    "# TODO: Real implementation",  # TODOs indicating missing real code
]


def detect_simulation_in_stack() -> Tuple[bool, str]:
    """
    Analyze the current stack trace for simulation patterns.
    
    Returns:
        (is_simulation, pattern): Tuple indicating if simulation detected and which pattern
    """
    if not REAL_MODE_ONLY:
        return False, ""
    
    # Get current stack trace
    stack = traceback.format_stack()
    stack_str = "".join(stack)
    
    # Check for simulation patterns
    for pattern in SIMULATION_PATTERNS:
        if pattern in stack_str:
            return True, pattern
    
    return False, ""


def enforce_real_mode(context: str = "") -> None:
    """
    Runtime guard that checks for simulation code execution.
    
    Args:
        context: Optional context string to include in error message
    
    Raises:
        RuntimeError: If simulation pattern detected in REAL_MODE_ONLY
    """
    if not REAL_MODE_ONLY:
        return
    
    is_simulation, pattern = detect_simulation_in_stack()
    
    if is_simulation:
        error_msg = f"REAL_MODE_ONLY: Simulation pattern detected: {pattern}"
        if context:
            error_msg += f"\nContext: {context}"
        error_msg += "\nSet REAL_MODE_ONLY=false to allow simulation code."
        
        raise RuntimeError(error_msg)


def validate_no_fake_delays(func_name: str, delay_value: float) -> None:
    """
    Validate that async sleep calls are not being used for fake delays.
    
    Args:
        func_name: Name of the function calling sleep
        delay_value: The delay value in seconds
    
    Raises:
        RuntimeError: If fake delay detected in REAL_MODE_ONLY
    """
    if not REAL_MODE_ONLY:
        return
    
    # Delays less than 1ms are likely fake/simulation delays
    if delay_value < 0.001:
        raise RuntimeError(
            f"REAL_MODE_ONLY: Fake delay detected in {func_name}: "
            f"asyncio.sleep({delay_value}). "
            "Use real operations instead of simulated delays. "
            "Set REAL_MODE_ONLY=false to allow simulation code."
        )


def validate_no_placeholders(code: str, file_name: str = "") -> None:
    """
    Validate that code doesn't contain placeholder implementations.
    
    Args:
        code: Source code to validate
        file_name: Optional file name for error message
    
    Raises:
        RuntimeError: If placeholder detected in REAL_MODE_ONLY
    """
    if not REAL_MODE_ONLY:
        return
    
    placeholder_indicators = [
        "# Placeholder",
        "# TODO: Real implementation",
        "# FAKE",
        "# Simulate",
        "pass  # Not implemented",
    ]
    
    for indicator in placeholder_indicators:
        if indicator in code:
            location = f" in {file_name}" if file_name else ""
            raise RuntimeError(
                f"REAL_MODE_ONLY: Placeholder code detected{location}: {indicator}. "
                "Replace with real implementation. "
                "Set REAL_MODE_ONLY=false to allow placeholder code."
            )


def get_enforcement_status() -> dict:
    """
    Get current enforcement status for monitoring/debugging.
    
    Returns:
        dict with enforcement configuration
    """
    return {
        "real_mode_only": REAL_MODE_ONLY,
        "enforcement_active": REAL_MODE_ONLY,
        "patterns_monitored": len(SIMULATION_PATTERNS),
        "environment_variable": os.getenv("REAL_MODE_ONLY", "not set"),
    }


# Module initialization message
if REAL_MODE_ONLY:
    print("🔒 REAL_MODE_ONLY enforced - simulation code will raise RuntimeError", file=sys.stderr)
else:
    print("⚠️  REAL_MODE_ONLY disabled - simulation code allowed", file=sys.stderr)
