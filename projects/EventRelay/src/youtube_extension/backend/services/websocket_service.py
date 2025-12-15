#!/usr/bin/env python3
"""
WebSocket Service
=================

Extracted WebSocket handling business logic.
Handles real-time communication, message routing, and connection management.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    Extracted from main.py for better separation of concerns.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and track new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection from tracking"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast message to all active connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)


class WebSocketService:
    """
    Service for handling WebSocket business logic.
    Provides unified interface for real-time communication operations.
    """
    
    def __init__(self, connection_manager: WebSocketConnectionManager, 
                 video_processing_service, chat_service=None):
        """
        Initialize WebSocket service.
        
        Args:
            connection_manager: WebSocket connection manager
            video_processing_service: Service for video processing
            chat_service: Optional chat processing service
        """
        self.connection_manager = connection_manager
        self.video_processing_service = video_processing_service
        self.chat_service = chat_service
    
    async def handle_websocket_connection(self, websocket: WebSocket):
        """
        Handle complete WebSocket connection lifecycle.
        
        Args:
            websocket: WebSocket connection instance
        """
        await self.connection_manager.connect(websocket)
        
        try:
            logger.info("WebSocket connection established")
            
            # Send welcome message
            welcome_message = {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to YouTube Extension API"
            }
            await self.connection_manager.send_personal_message(
                json.dumps(welcome_message), websocket
            )
            
            # Message handling loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    logger.info(f"WebSocket message received: {message.get('type', 'unknown')}")
                    
                    # Route message to appropriate handler
                    response = await self._route_message(message)
                    
                    # Send response back to client
                    await self.connection_manager.send_personal_message(
                        json.dumps(response), websocket
                    )
                    
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    self.connection_manager.disconnect(websocket)
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = self._create_error_response(
                        "Invalid JSON format", "json_decode_error"
                    )
                    await self.connection_manager.send_personal_message(
                        json.dumps(error_response), websocket
                    )
                    
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    error_response = self._create_error_response(
                        f"Internal server error: {str(e)}", "internal_error"
                    )
                    await self.connection_manager.send_personal_message(
                        json.dumps(error_response), websocket
                    )
        
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
            self.connection_manager.disconnect(websocket)
    
    async def _route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route incoming message to appropriate handler.
        
        Args:
            message: Incoming message dictionary
            
        Returns:
            Response message dictionary
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "chat":
            return await self._handle_chat_message(message)
            
        elif message_type == "video_processing":
            return await self._handle_video_processing_message(message)
            
        elif message_type == "ping":
            return self._handle_ping_message(message)
            
        else:
            return self._create_error_response(
                f"Unknown message type: {message_type}",
                "unknown_message_type"
            )
    
    async def _handle_chat_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle chat messages via WebSocket.
        
        Args:
            message: Chat message data
            
        Returns:
            Chat response message
        """
        try:
            chat_text = message.get("message", "")
            session_id = message.get("session_id", "default")
            
            # Use chat service if available
            if self.chat_service:
                try:
                    response_text = await self.chat_service.process_chat_message(
                        chat_text, session_id
                    )
                except Exception as e:
                    logger.error(f"Chat service error: {e}")
                    response_text = f"AI Assistant: I received your message: '{chat_text}'. (Chat service error: {str(e)})"
            else:
                # Fallback to simple response
                response_text = f"AI Assistant: I received your message: '{chat_text}'. I'm here to help with video processing and analysis! Please provide a YouTube URL for video processing."
            
            return {
                "type": "chat_response",
                "response": response_text,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            return self._create_error_response(
                f"Error processing chat message: {str(e)}",
                "chat_processing_error"
            )
    
    async def _handle_video_processing_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle video processing messages via WebSocket.
        
        Args:
            message: Video processing message data
            
        Returns:
            Video processing response message
        """
        try:
            video_url = message.get("video_url", "")
            
            if not video_url:
                return self._create_error_response(
                    "Video URL required",
                    "missing_video_url"
                )
            
            # Process video using video processing service
            try:
                result = await self.video_processing_service.process_video_basic(
                    video_url, message.get("options", {})
                )
                
                return {
                    "type": "video_processing_response",
                    "result": result["result"],
                    "status": result["status"],
                    "progress": result.get("progress", 100.0),
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error in video processing: {e}")
                return {
                    "type": "video_processing_response",
                    "result": {
                        "video_url": video_url,
                        "status": "error",
                        "error": str(e)
                    },
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error handling video processing message: {e}")
            return self._create_error_response(
                f"Error processing video: {str(e)}",
                "video_processing_error"
            )
    
    def _handle_ping_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ping messages.
        
        Args:
            message: Ping message data
            
        Returns:
            Pong response message
        """
        return {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "original_message": message.get("data", {})
        }
    
    def _create_error_response(self, error_message: str, error_type: str = "error") -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error_message: Error message text
            error_type: Type/category of error
            
        Returns:
            Error response dictionary
        """
        return {
            "type": "error",
            "error_type": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
    
    async def broadcast_system_message(self, message: str, message_type: str = "system"):
        """
        Broadcast system message to all connected clients.
        
        Args:
            message: Message to broadcast
            message_type: Type of system message
        """
        try:
            system_message = {
                "type": message_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.connection_manager.broadcast(json.dumps(system_message))
            logger.info(f"System message broadcasted: {message}")
            
        except Exception as e:
            logger.error(f"Error broadcasting system message: {e}")
    
    async def send_progress_update(self, websocket: WebSocket, progress: float, 
                                 message: str = "", data: Dict[str, Any] = None):
        """
        Send progress update to specific client.
        
        Args:
            websocket: Target WebSocket connection
            progress: Progress percentage (0-100)
            message: Progress message
            data: Additional progress data
        """
        try:
            progress_message = {
                "type": "progress",
                "progress": progress,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat()
            }
            
            await self.connection_manager.send_personal_message(
                json.dumps(progress_message), websocket
            )
            
        except Exception as e:
            logger.error(f"Error sending progress update: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection statistics.
        
        Returns:
            Connection statistics
        """
        return {
            "active_connections": len(self.connection_manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }