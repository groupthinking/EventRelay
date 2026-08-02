"""
Cloud Services Module
=====================

Google Cloud Platform services for cloud-native deployment:
- Firestore: Shared state management
- Cloud Tasks: Async job queue
- Vertex AI: Agent Builder integration
- Cloud Storage: File storage
"""

from .cloud_tasks_queue import (
    CloudTasksQueueService,
    TaskConfig,
    VideoProcessingTask,
    cleanup_cloud_tasks_service,
    get_cloud_tasks_service,
)
from .firestore_state import (
    FirestoreStateService,
    VideoProcessingState,
    cleanup_firestore_service,
    get_firestore_service,
)
from .vertex_ai_agent import (
    AgentConfig,
    AgentResponse,
    VertexAIAgentService,
    get_vertex_ai_service,
)

__all__ = [
    # Firestore
    'FirestoreStateService',
    'VideoProcessingState',
    'get_firestore_service',
    'cleanup_firestore_service',
    # Cloud Tasks
    'CloudTasksQueueService',
    'VideoProcessingTask',
    'TaskConfig',
    'get_cloud_tasks_service',
    'cleanup_cloud_tasks_service',
    # Vertex AI
    'VertexAIAgentService',
    'AgentConfig',
    'AgentResponse',
    'get_vertex_ai_service',
]
