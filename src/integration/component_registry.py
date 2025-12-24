import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IntelligenceComponentRegistry:
    def __init__(self):
        self.components = {}
        self.dependencies = {}
        self.processing_order = []
        
    def register_component(self, component_name: str, component_class: Any, dependencies: list = None):
        self.components[component_name] = {
            'class': component_class,
            'instance': None,
            'dependencies': dependencies or [],
            'status': 'registered',
            'last_health_check': None
        }
        self._update_processing_order()
        
    async def initialize_components(self):
        for component_name in self.processing_order:
            component_info = self.components[component_name]
            try:
                component_info['instance'] = component_info['class']()
                # Assuming components might have an async initialize method
                if hasattr(component_info['instance'], 'initialize'):
                    await component_info['instance'].initialize()
                component_info['status'] = 'active'
                logger.info(f"Initialized component: {component_name}")
            except Exception as e:
                component_info['status'] = 'failed'
                logger.error(f"Failed to initialize {component_name}: {e}")

    def get_component(self, component_name: str) -> Any:
        component_info = self.components.get(component_name)
        if component_info and component_info['instance']:
            return component_info['instance']
        raise ValueError(f"Component {component_name} not found or not initialized.")

    def _update_processing_order(self):
        # Simple topological sort for demonstration. In a real system, this would be more robust.
        # For now, just add components in registration order.
        self.processing_order = list(self.components.keys())
