#!/usr/bin/env python3
"""
MCP State Coordinator - Manages shared state between all MCP servers
Enables cross-server communication and coordination for UVAI ecosystem
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import aiofiles
import websockets
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MCPStateCoordinator')

@dataclass
class MCPServerState:
    server_id: str
    status: str  # 'online', 'offline', 'error', 'initializing'
    last_ping: float
    capabilities: List[str]
    websocket: Any # Store the WebSocket connection for direct communication
    current_task: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class SharedAction:
    action_id: str
    server_id: str
    action_type: str  # 'video_analysis', 'code_execution', 'search', etc.
    payload: Dict[str, Any]
    timestamp: float
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    dependencies: List[str] = None  # Other action_ids this depends on
    results: Dict[str, Any] = None

class MCPStateCoordinator:
    def __init__(self, db_path: str = "/Users/garvey/mcp-ecosystem/shared-state/mcp_state.db"):
        self.db_path = db_path
        self.servers: Dict[str, MCPServerState] = {}
        self.actions: Dict[str, SharedAction] = {}
        self.websocket_port = 8005
        self.connected_clients = set()
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database for persistent state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Servers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                server_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_ping REAL NOT NULL,
                capabilities TEXT NOT NULL,
                current_task TEXT,
                metadata TEXT
            )
        ''')
        
        # Actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                action_id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL,
                dependencies TEXT,
                results TEXT
            )
        ''')
        
        # Action dependencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_dependencies (
                action_id TEXT,
                depends_on TEXT,
                FOREIGN KEY (action_id) REFERENCES actions (action_id),
                FOREIGN KEY (depends_on) REFERENCES actions (action_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def register_server(self, server_id: str, capabilities: List[str], websocket: Any, metadata: Dict[str, Any] = None):
        """Register a new MCP server"""
        server_state = MCPServerState(
            server_id=server_id,
            status='online',
            last_ping=time.time(),
            capabilities=capabilities,
            websocket=websocket,
            metadata=metadata or {}
        )
        
        self.servers[server_id] = server_state
        self._persist_server_state(server_state)
        
        logger.info(f"Registered server: {server_id} with capabilities: {capabilities}")
        asyncio.create_task(self._broadcast_server_update(server_id, 'registered'))
    
    def update_server_status(self, server_id: str, status: str, current_task: str = None):
        """Update server status"""
        if server_id in self.servers:
            self.servers[server_id].status = status
            self.servers[server_id].last_ping = time.time()
            if current_task:
                self.servers[server_id].current_task = current_task
            
            self._persist_server_state(self.servers[server_id])
            asyncio.create_task(self._broadcast_server_update(server_id, 'status_updated'))
    
    async def submit_action(self, server_id: str, action_type: str, payload: Dict[str, Any], 
                          dependencies: List[str] = None) -> str:
        """Submit a new shared action"""
        action_id = f"{server_id}_{action_type}_{int(time.time() * 1000)}"
        
        action = SharedAction(
            action_id=action_id,
            server_id=server_id,
            action_type=action_type,
            payload=payload,
            timestamp=time.time(),
            status='pending',
            dependencies=dependencies or []
        )
        
        self.actions[action_id] = action
        self._persist_action(action)
        
        # Check if dependencies are met
        if await self._check_dependencies(action_id):
            action.status = 'ready'
            self._persist_action(action)
        
        await self._broadcast_action_update(action_id, 'submitted')
        logger.info(f"Action submitted: {action_id} by {server_id}")
        
        return action_id
    
    async def update_action_status(self, action_id: str, status: str, results: Dict[str, Any] = None):
        """Update action status and results"""
        if action_id in self.actions:
            self.actions[action_id].status = status
            if results:
                self.actions[action_id].results = results
            
            self._persist_action(self.actions[action_id])
            await self._broadcast_action_update(action_id, 'updated')
            
            # Check if this completion enables other actions
            if status == 'completed':
                await self._check_dependent_actions(action_id)
    
    async def _check_dependencies(self, action_id: str) -> bool:
        """Check if all dependencies for an action are completed"""
        action = self.actions.get(action_id)
        if not action or not action.dependencies:
            return True
        
        for dep_id in action.dependencies:
            dep_action = self.actions.get(dep_id)
            if not dep_action or dep_action.status != 'completed':
                return False
        
        return True
    
    async def _check_dependent_actions(self, completed_action_id: str):
        """Check and update actions that depend on the completed action"""
        for action_id, action in self.actions.items():
            if (action.dependencies and completed_action_id in action.dependencies 
                and action.status == 'pending'):
                if await self._check_dependencies(action_id):
                    action.status = 'ready'
                    self._persist_action(action)
                    await self._broadcast_action_update(action_id, 'ready')
    
    def get_server_by_capability(self, capability: str) -> List[str]:
        """Get servers that have a specific capability"""
        return [server_id for server_id, server in self.servers.items() 
                if capability in server.capabilities and server.status == 'online']
    
    def get_available_servers(self) -> Dict[str, MCPServerState]:
        """Get all online servers"""
        return {sid: server for sid, server in self.servers.items() if server.status == 'online'}
    
    def get_pending_actions(self, server_id: str = None) -> List[SharedAction]:
        """Get pending actions, optionally filtered by server"""
        actions = [action for action in self.actions.values() if action.status in ['pending', 'ready']]
        if server_id:
            actions = [action for action in actions if action.server_id == server_id]
        return actions
    
    def _persist_server_state(self, server: MCPServerState):
        """Persist server state to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO servers 
            (server_id, status, last_ping, capabilities, current_task, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            server.server_id,
            server.status,
            server.last_ping,
            json.dumps(server.capabilities),
            server.current_task,
            json.dumps(server.metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def _persist_action(self, action: SharedAction):
        """Persist action to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO actions 
            (action_id, server_id, action_type, payload, timestamp, status, dependencies, results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            action.action_id,
            action.server_id,
            action.action_type,
            json.dumps(action.payload),
            action.timestamp,
            action.status,
            json.dumps(action.dependencies or []),
            json.dumps(action.results or {})
        ))
        
        conn.commit()
        conn.close()
    
    async def _broadcast_server_update(self, server_id: str, event_type: str):
        """Broadcast server update to all connected clients"""
        if not self.connected_clients:
            return
        
        message = {
            'type': 'server_update',
            'event': event_type,
            'server_id': server_id,
            'server_state': asdict(self.servers[server_id]) if server_id in self.servers else None,
            'timestamp': time.time()
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_action_update(self, action_id: str, event_type: str):
        """Broadcast action update to all connected clients"""
        if not self.connected_clients:
            return
        
        message = {
            'type': 'action_update',
            'event': event_type,
            'action_id': action_id,
            'action': asdict(self.actions[action_id]) if action_id in self.actions else None,
            'timestamp': time.time()
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        message_str = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.connected_clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected_clients
    
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections from MCP servers"""
        self.connected_clients.add(websocket)
        logger.info(f"New WebSocket connection: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({'error': 'Invalid JSON'}))
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    await websocket.send(json.dumps({'error': str(e)}))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"WebSocket connection closed: {websocket.remote_address}")
    
    async def _handle_websocket_message(self, websocket, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'register_server':
            server_id = data.get('server_id')
            capabilities = data.get('capabilities', [])
            metadata = data.get('metadata', {})
            self.register_server(server_id, capabilities, websocket, metadata)
            await websocket.send(json.dumps({'status': 'registered', 'server_id': server_id}))
        
        elif msg_type == 'update_status':
            server_id = data.get('server_id')
            status = data.get('status')
            current_task = data.get('current_task')
            self.update_server_status(server_id, status, current_task)
            await websocket.send(json.dumps({'status': 'updated'}))
        
        elif msg_type == 'submit_action':
            server_id = data.get('server_id')
            action_type = data.get('action_type')
            payload = data.get('payload', {})
            dependencies = data.get('dependencies', [])
            action_id = await self.submit_action(server_id, action_type, payload, dependencies)
            await websocket.send(json.dumps({'status': 'submitted', 'action_id': action_id}))
        
        elif msg_type == 'update_action':
            action_id = data.get('action_id')
            status = data.get('status')
            results = data.get('results', {})
            await self.update_action_status(action_id, status, results)
            await websocket.send(json.dumps({'status': 'updated'}))
        
        elif msg_type == 'get_servers':
            servers = {sid: asdict(server) for sid, server in self.get_available_servers().items()}
            await websocket.send(json.dumps({'type': 'servers', 'servers': servers}))
        
        elif msg_type == 'get_actions':
            server_id = data.get('server_id')
            actions = [asdict(action) for action in self.get_pending_actions(server_id)]
            await websocket.send(json.dumps({'type': 'actions', 'actions': actions}))

        elif msg_type == 'tool_call_request':
            target_server_id = data.get('server_id')
            tool_name = data.get('tool_name')
            tool_arguments = data.get('tool_arguments', {})
            request_id = data.get('id') # Use the ID from the incoming request

            logger.info(f"Received tool_call_request for {target_server_id}/{tool_name} (ID: {request_id})")

            if target_server_id not in self.servers or not self.servers[target_server_id].websocket.open:
                error_message = f"Target server {target_server_id} not found or not connected."
                logger.error(error_message)
                await websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": error_message}
                }))
                return

            target_server_websocket = self.servers[target_server_id].websocket

            # Construct the actual MCP tool call message for the target server
            mcp_tool_call_message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_arguments
                }
            }

            try:
                # Send the tool call to the target server
                await target_server_websocket.send(json.dumps(mcp_tool_call_message))
                # Wait for the response from the target server
                response_from_target = json.loads(await target_server_websocket.recv())

                logger.info(f"Tool call response from {target_server_id}: {response_from_target}")

                # Forward the response back to the original client (HybridOrchestrationSystem)
                await websocket.send(json.dumps(response_from_target))

            except websockets.exceptions.ConnectionClosed as e:
                error_message = f"Connection to target server {target_server_id} closed: {e}"
                logger.error(error_message)
                await websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": error_message}
                }))
            except Exception as e:
                error_message = f"Error routing tool call to {target_server_id}: {e}"
                logger.error(error_message)
                await websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": error_message}
                }))
    
    async def start_server(self):
        """Start the WebSocket server for MCP coordination"""
        logger.info(f"Starting MCP State Coordinator on port {self.websocket_port}")
        
        start_server = websockets.serve(
            self.websocket_handler,
            "localhost",
            self.websocket_port
        )
        
        await start_server
        logger.info("MCP State Coordinator is running")
    
    async def health_check_loop(self):
        """Periodically check server health and clean up stale servers"""
        while True:
            current_time = time.time()
            stale_servers = []
            
            for server_id, server in self.servers.items():
                if current_time - server.last_ping > 300:  # 5 minutes timeout
                    stale_servers.append(server_id)
            
            for server_id in stale_servers:
                self.servers[server_id].status = 'offline'
                self._persist_server_state(self.servers[server_id])
                await self._broadcast_server_update(server_id, 'timeout')
                logger.warning(f"Server {server_id} marked as offline due to timeout")
            
            await asyncio.sleep(60)  # Check every minute

async def main():
    """Main function to run the MCP State Coordinator"""
    coordinator = MCPStateCoordinator()
    
    # Start health check loop
    health_task = asyncio.create_task(coordinator.health_check_loop())
    
    # Start WebSocket server
    server_task = asyncio.create_task(coordinator.start_server())
    
    try:
        await asyncio.gather(health_task, server_task)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP State Coordinator")
        health_task.cancel()
        server_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())