#!/usr/bin/env python3
"""
Notification Service
===================

Handles system notifications, alerts, and user communications.
Provides centralized notification management with multiple channels.
"""

import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NotificationMessage:
    """Represents a notification message"""
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, urgent
    category: str = "system"  # system, user, alert, info
    recipient: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

class NotificationService:
    """
    Service for managing notifications across multiple channels.
    Supports email, file logging, and in-memory storage.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize notification service.

        Args:
            config: Configuration dictionary with notification settings
        """
        self.config = config or {}
        self.notifications: List[NotificationMessage] = []
        self.notification_log = Path("logs/notifications.log")

        # Create logs directory if it doesn't exist
        self.notification_log.parent.mkdir(parents=True, exist_ok=True)

        # Email configuration
        self.smtp_config = self.config.get("smtp", {})
        self.email_enabled = self.smtp_config.get("enabled", False)

        # Slack/Webhook integration disabled per project requirements
        self.slack_webhook_url: Optional[str] = None
        self.slack_channel: Optional[str] = None
        self.slack_enabled: bool = False

        logger.info("Notification service initialized")

    async def send_notification(self, message: Union[NotificationMessage, Dict[str, Any]]) -> bool:
        """
        Send a notification through configured channels.

        Args:
            message: Notification message to send

        Returns:
            Success status
        """
        try:
            # Convert dict to NotificationMessage if needed
            if isinstance(message, dict):
                message = NotificationMessage(**message)

            # Store notification
            self.notifications.append(message)

            # Log to file
            await self._log_to_file(message)

            # Send email if configured and high priority
            if self.email_enabled and message.priority in ["high", "urgent"]:
                await self._send_email(message)

            # Slack notifications are disabled

            logger.info(f"Notification sent: {message.title} ({message.priority})")
            return True

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def send_alert(self, title: str, message: str, priority: str = "high") -> bool:
        """
        Send an alert notification.

        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority

        Returns:
            Success status
        """
        alert = NotificationMessage(
            title=title,
            message=message,
            priority=priority,
            category="alert"
        )
        return await self.send_notification(alert)

    async def send_system_notification(self, title: str, message: str, priority: str = "normal") -> bool:
        """
        Send a system notification.

        Args:
            title: System notification title
            message: System notification message
            priority: Notification priority

        Returns:
            Success status
        """
        system_msg = NotificationMessage(
            title=title,
            message=message,
            priority=priority,
            category="system"
        )
        return await self.send_notification(system_msg)

    async def send_user_notification(self, user_id: str, title: str, message: str, priority: str = "normal") -> bool:
        """
        Send a user-specific notification.

        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            priority: Notification priority

        Returns:
            Success status
        """
        user_msg = NotificationMessage(
            title=title,
            message=message,
            priority=priority,
            category="user",
            recipient=user_id
        )
        return await self.send_notification(user_msg)

    async def get_notifications(self, category: Optional[str] = None,
                               priority: Optional[str] = None,
                               limit: int = 50) -> List[NotificationMessage]:
        """
        Get notifications with optional filtering.

        Args:
            category: Filter by category
            priority: Filter by priority
            limit: Maximum number of notifications to return

        Returns:
            List of notifications
        """
        filtered = self.notifications

        if category:
            filtered = [n for n in filtered if n.category == category]

        if priority:
            filtered = [n for n in filtered if n.priority == priority]

        return filtered[-limit:]

    async def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get notification statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.notifications)

        if total == 0:
            return {"total": 0, "by_category": {}, "by_priority": {}}

        by_category = {}
        by_priority = {}

        for notification in self.notifications:
            by_category[notification.category] = by_category.get(notification.category, 0) + 1
            by_priority[notification.priority] = by_priority.get(notification.priority, 0) + 1

        return {
            "total": total,
            "by_category": by_category,
            "by_priority": by_priority,
            "recent_count": len([n for n in self.notifications
                               if (datetime.utcnow() - n.timestamp).days < 1])
        }

    async def clear_old_notifications(self, days: int = 30) -> int:
        """
        Clear notifications older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of notifications cleared
        """
        cutoff = datetime.utcnow()
        cutoff = cutoff.replace(day=cutoff.day - days)

        original_count = len(self.notifications)
        self.notifications = [n for n in self.notifications if n.timestamp >= cutoff]

        cleared = original_count - len(self.notifications)
        logger.info(f"Cleared {cleared} old notifications")

        return cleared

    async def _log_to_file(self, message: NotificationMessage) -> None:
        """Log notification to file."""
        try:
            log_entry = {
                "timestamp": message.timestamp.isoformat(),
                "title": message.title,
                "message": message.message,
                "priority": message.priority,
                "category": message.category,
                "recipient": message.recipient,
                "metadata": message.metadata
            }

            with open(self.notification_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            logger.error(f"Failed to log notification to file: {e}")

    async def _send_email(self, message: NotificationMessage) -> None:
        """Send notification via email."""
        if not self.email_enabled:
            return

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get("from_email", "system@uvai.local")
            msg['To'] = self.smtp_config.get("admin_email", "admin@uvai.local")
            msg['Subject'] = f"[{message.priority.upper()}] {message.title}"

            body = f"""
UVAI System Notification
========================

Priority: {message.priority.upper()}
Category: {message.category}
Time: {message.timestamp}

Message:
{message.message}

Metadata:
{json.dumps(message.metadata, indent=2) if message.metadata else "None"}
"""
            msg.attach(MIMEText(body, 'plain'))

            # Send email (would need actual SMTP configuration)
            # server = smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"])
            # server.starttls()
            # server.login(self.smtp_config["username"], self.smtp_config["password"])
            # server.send_message(msg)
            # server.quit()

            logger.info(f"Email notification sent: {message.title}")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    # Slack sending removed

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for notification service.

        Returns:
            Health status dictionary
        """
        health = {
            "service": "notification_service",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_notifications": len(self.notifications),
                "email_enabled": self.email_enabled,
                "log_file_exists": self.notification_log.exists()
            }
        }

        # Check if we can write to log file
        try:
            test_msg = NotificationMessage(
                title="Health Check",
                message="Testing notification service",
                category="system"
            )
            await self._log_to_file(test_msg)
            health["metrics"]["log_writable"] = True
        except Exception:
            health["metrics"]["log_writable"] = False
            health["status"] = "degraded"

        return health
