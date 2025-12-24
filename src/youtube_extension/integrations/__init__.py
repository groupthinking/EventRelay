"""
UVAI Integrations Layer

This module handles all external system integrations and deployment orchestration.
Integrations are designed to be pluggable and environment-aware.

Available Integrations:
- Frontend: Web interface and user experience components
- Deployment: Multi-platform deployment automation
- Optimization: Performance optimization and scaling
- Quality Assurance: Testing and validation frameworks
- Cloud AI: Major cloud AI/ML provider integrations

Architecture:
- Pluggable integration components
- Environment-specific configuration
- Comprehensive monitoring and health checks
- Automated deployment and rollback capabilities
- Unified cloud AI service interfaces
"""

# Cloud AI integrations
from .cloud_ai import CloudAIIntegrator

# Optional integrations (only if available)
__all__ = [
    "CloudAIIntegrator"
]

# Try to import optional integrations
try:
    from .frontend import FrontendIntegration
    __all__.append("FrontendIntegration")
except ImportError:
    pass

try:
    from .deployment import DeploymentOrchestrator
    __all__.append("DeploymentOrchestrator")
except ImportError:
    pass

try:
    from .optimization import PerformanceOptimizer
    __all__.append("PerformanceOptimizer")
except ImportError:
    pass

try:
    from .qa import QualityAssurance
    __all__.append("QualityAssurance")
except ImportError:
    pass
