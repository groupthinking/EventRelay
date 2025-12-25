import json
import logging
import os
from typing import Any, Dict, Optional

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

class PubSubService:
    """
    Service for interacting with Google Cloud Pub/Sub.
    Handles publishing messages to topics.
    """

    def __init__(self, project_id: str, topic_name: str):
        """
        Initialize PubSubService.

        Args:
            project_id: GCP Project ID
            topic_name: Pub/Sub Topic Name
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self._publisher = None
        self._topic_path = None
        
        # Only initialize if we have the necessary config
        if self.project_id and self.topic_name:
             try:
                self._publisher = pubsub_v1.PublisherClient()
                self._topic_path = self._publisher.topic_path(self.project_id, self.topic_name)
                logger.info(f"PubSubService initialized for topic: {self._topic_path}")
             except Exception as e:
                 logger.warning(f"Failed to initialize PubSub publisher: {e}")

    async def publish_message(self, data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Publish a message to the configured Pub/Sub topic.

        Args:
            data: Dictionary of data to publish (will be JSON encoded)
            attributes: Optional dictionary of attributes

        Returns:
            Message ID if successful, None otherwise.
        """
        if not self._publisher or not self._topic_path:
            logger.warning("PubSub publisher not initialized, skipping publish.")
            return None

        try:
            json_data = json.dumps(data).encode("utf-8")
            future = self._publisher.publish(self._topic_path, json_data, **(attributes or {}))
            message_id = future.result()
            logger.info(f"Published message {message_id} to {self._topic_path}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish message to Pub/Sub: {e}")
            return None
