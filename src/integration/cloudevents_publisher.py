"""
CloudEvents Publisher for EventMesh Integration
-----------------------------------------------
Implements CloudEvents v1.0 specification for standardized event publishing.
Supports multiple backends: Pub/Sub, HTTP webhooks, OpenWhisk triggers.

CloudEvents Specification: https://cloudevents.io/
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import httpx
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class CloudEvent:
    """
    CloudEvents v1.0 compliant event structure.
    
    Required attributes:
    - id: Unique event identifier
    - source: Context in which event occurred
    - specversion: CloudEvents spec version (1.0)
    - type: Event type descriptor
    
    Optional attributes:
    - datacontenttype: Media type of data
    - dataschema: Schema URL for data
    - subject: Subject of event in context of source
    - time: Event timestamp
    - data: Event payload
    """

    SPEC_VERSION = "1.0"

    def __init__(
        self,
        source: str,
        type: str,
        data: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        subject: Optional[str] = None,
        datacontenttype: str = "application/json",
        dataschema: Optional[str] = None,
        time: Optional[datetime] = None,
        **extensions: Any
    ):
        self.id = id or str(uuid.uuid4())
        self.source = source
        self.specversion = self.SPEC_VERSION
        self.type = type
        self.datacontenttype = datacontenttype
        self.dataschema = dataschema
        self.subject = subject
        self.time = time or datetime.now(timezone.utc)
        self.data = data or {}
        self.extensions = extensions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to CloudEvents JSON representation."""
        event = {
            "id": self.id,
            "source": self.source,
            "specversion": self.specversion,
            "type": self.type,
            "time": self.time.isoformat() if isinstance(self.time, datetime) else self.time,
        }

        if self.subject:
            event["subject"] = self.subject
        if self.datacontenttype:
            event["datacontenttype"] = self.datacontenttype
        if self.dataschema:
            event["dataschema"] = self.dataschema
        if self.data is not None:
            event["data"] = self.data

        # Add extension attributes
        event.update(self.extensions)

        return event

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


class CloudEventsPublisher:
    """
    Multi-backend CloudEvents publisher supporting:
    - Google Cloud Pub/Sub
    - HTTP webhooks
    - Apache OpenWhisk triggers
    - Local file sink (for testing)
    """

    def __init__(
        self,
        backend: Literal["pubsub", "http", "openwhisk", "file"] = "pubsub",
        project_id: Optional[str] = None,
        topic_name: Optional[str] = None,
        webhook_url: Optional[str] = None,
        openwhisk_api_host: Optional[str] = None,
        openwhisk_auth: Optional[str] = None,
        openwhisk_namespace: Optional[str] = None,
        file_path: Optional[str] = None,
    ):
        self.backend = backend
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.topic_name = topic_name or os.getenv("PUBSUB_TOPIC", "video-events")
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
        self.openwhisk_api_host = openwhisk_api_host or os.getenv("OPENWHISK_API_HOST")
        self.openwhisk_auth = openwhisk_auth or os.getenv("OPENWHISK_AUTH")
        self.openwhisk_namespace = openwhisk_namespace or os.getenv("OPENWHISK_NAMESPACE", "guest")
        self.file_path = file_path or os.getenv("EVENTS_FILE_PATH", "/tmp/cloudevents.jsonl")

        # Initialize backend clients
        self._pubsub_client = None
        self._http_client = None

        if backend == "pubsub" and self.project_id:
            try:
                self._pubsub_client = pubsub_v1.PublisherClient()
                self._topic_path = self._pubsub_client.topic_path(
                    self.project_id, self.topic_name
                )
                logger.info(f"CloudEvents publisher initialized with Pub/Sub: {self._topic_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize Pub/Sub client: {e}")

        if backend in ("http", "openwhisk"):
            self._http_client = httpx.AsyncClient(timeout=30.0)
            logger.info(f"CloudEvents publisher initialized with {backend} backend")

    async def publish(
        self,
        source: str,
        type: str,
        data: Optional[Dict[str, Any]] = None,
        subject: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """
        Publish a CloudEvent.
        
        Args:
            source: Event source URI (e.g., "/video-processor/gemini")
            type: Event type (e.g., "com.eventrelay.video.analyzed")
            data: Event payload
            subject: Event subject (e.g., video URL)
            **kwargs: Additional CloudEvent attributes or extensions
        
        Returns:
            Event ID if successful, None otherwise
        """
        event = CloudEvent(
            source=source,
            type=type,
            data=data,
            subject=subject,
            **kwargs
        )

        logger.info(f"Publishing CloudEvent: type={type}, id={event.id}")

        try:
            if self.backend == "pubsub":
                return await self._publish_pubsub(event)
            elif self.backend == "http":
                return await self._publish_http(event)
            elif self.backend == "openwhisk":
                return await self._publish_openwhisk(event)
            elif self.backend == "file":
                return await self._publish_file(event)
            else:
                logger.error(f"Unsupported backend: {self.backend}")
                return None
        except Exception as e:
            logger.error(f"Failed to publish CloudEvent: {e}", exc_info=True)
            return None

    async def _publish_pubsub(self, event: CloudEvent) -> Optional[str]:
        """Publish to Google Cloud Pub/Sub."""
        if not self._pubsub_client:
            logger.warning("Pub/Sub client not initialized")
            return None

        try:
            # Pub/Sub requires bytes
            data = event.to_json().encode("utf-8")

            # Add CloudEvents attributes as message attributes
            attributes = {
                "ce_id": event.id,
                "ce_source": event.source,
                "ce_specversion": event.specversion,
                "ce_type": event.type,
            }

            future = self._pubsub_client.publish(
                self._topic_path,
                data,
                **attributes
            )
            message_id = future.result()
            logger.info(f"Published CloudEvent {event.id} to Pub/Sub: {message_id}")
            return event.id
        except Exception as e:
            logger.error(f"Pub/Sub publish failed: {e}")
            return None

    async def _publish_http(self, event: CloudEvent) -> Optional[str]:
        """Publish to HTTP webhook endpoint."""
        if not self.webhook_url:
            logger.warning("Webhook URL not configured")
            return None

        if not self._http_client:
            logger.warning("HTTP client not initialized")
            return None

        try:
            # CloudEvents HTTP binding: structured content mode
            headers = {
                "Content-Type": "application/cloudevents+json",
            }

            response = await self._http_client.post(
                self.webhook_url,
                json=event.to_dict(),
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"Published CloudEvent {event.id} to webhook: {self.webhook_url}")
            return event.id
        except Exception as e:
            logger.error(f"HTTP webhook publish failed: {e}")
            return None

    async def _publish_openwhisk(self, event: CloudEvent) -> Optional[str]:
        """
        Publish to Apache OpenWhisk trigger.
        
        OpenWhisk triggers can invoke actions based on events.
        Uses the OpenWhisk REST API to fire triggers.
        """
        if not all([self.openwhisk_api_host, self.openwhisk_auth]):
            logger.warning("OpenWhisk configuration incomplete")
            return None

        if not self._http_client:
            logger.warning("HTTP client not initialized")
            return None

        try:
            # Extract trigger name from event type or use default
            # Format: com.eventrelay.video.analyzed -> video_analyzed_trigger
            trigger_name = event.type.split(".")[-1].replace("-", "_") + "_trigger"

            # OpenWhisk trigger URL
            url = (
                f"{self.openwhisk_api_host}/api/v1/namespaces/"
                f"{self.openwhisk_namespace}/triggers/{trigger_name}"
            )

            # Basic auth
            username, password = self.openwhisk_auth.split(":")

            response = await self._http_client.post(
                url,
                json=event.to_dict(),
                auth=(username, password),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            logger.info(
                f"Published CloudEvent {event.id} to OpenWhisk trigger: {trigger_name}"
            )
            return event.id
        except Exception as e:
            logger.error(f"OpenWhisk publish failed: {e}")
            return None

    async def _publish_file(self, event: CloudEvent) -> Optional[str]:
        """Write event to local file (for testing/development)."""
        try:
            import aiofiles

            async with aiofiles.open(self.file_path, mode="a") as f:
                await f.write(event.to_json() + "\n")

            logger.info(f"Published CloudEvent {event.id} to file: {self.file_path}")
            return event.id
        except Exception as e:
            logger.error(f"File publish failed: {e}")
            return None

    async def close(self):
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()


# Convenience factory function
def create_publisher(
    backend: Optional[str] = None,
    **kwargs
) -> CloudEventsPublisher:
    """
    Create a CloudEvents publisher with environment-based configuration.
    
    Environment variables:
    - CLOUDEVENTS_BACKEND: "pubsub", "http", "openwhisk", or "file"
    - GOOGLE_CLOUD_PROJECT: GCP project ID
    - PUBSUB_TOPIC: Pub/Sub topic name
    - WEBHOOK_URL: HTTP webhook endpoint
    - OPENWHISK_API_HOST: OpenWhisk API host (e.g., https://openwhisk.ng.bluemix.net)
    - OPENWHISK_AUTH: OpenWhisk credentials (username:password)
    - OPENWHISK_NAMESPACE: OpenWhisk namespace
    - EVENTS_FILE_PATH: File path for file backend
    """
    backend = backend or os.getenv("CLOUDEVENTS_BACKEND", "pubsub")
    return CloudEventsPublisher(backend=backend, **kwargs)
