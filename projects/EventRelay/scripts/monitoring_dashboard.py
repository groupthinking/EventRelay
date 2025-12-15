#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard for Enterprise MCP Server
Provides comprehensive observability and alerting
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path
import time
from dataclasses import dataclass

# Web dashboard imports
from fastapi import FastAPI, WebSocket, HTMLResponse, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Monitoring imports
import psutil
from collections import deque, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric: str
    threshold: float
    condition: str  # "greater", "less", "equal"
    severity: str   # "critical", "warning", "info"
    enabled: bool = True

class AlertManager:
    """Alert management system"""
    
    def __init__(self):
        self.rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_handlers = []
        
        # Default alert rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule("high_cpu", "system.cpu_percent", 80.0, "greater", "warning"),
            AlertRule("high_memory", "system.memory_percent", 85.0, "greater", "critical"),
            AlertRule("circuit_breaker_open", "circuit_breaker.failures", 1.0, "greater", "critical"),
            AlertRule("high_error_rate", "errors_per_minute", 10.0, "greater", "warning"),
            AlertRule("low_success_rate", "success_rate", 95.0, "less", "warning")
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
            logger.info(f"🚨 Alert rule '{rule.name}' configured")
    
    def add_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        self.rules[rule.name] = rule
        logger.info(f"➕ Alert rule '{rule.name}' added")
    
    def evaluate_alerts(self, metrics: Dict[str, float]):
        """Evaluate all alert rules against current metrics"""
        current_time = time.time()
        new_alerts = []
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            metric_value = metrics.get(rule.metric, 0)
            triggered = False
            
            if rule.condition == "greater" and metric_value > rule.threshold:
                triggered = True
            elif rule.condition == "less" and metric_value < rule.threshold:
                triggered = True
            elif rule.condition == "equal" and metric_value == rule.threshold:
                triggered = True
            
            if triggered:
                if rule_name not in self.active_alerts:
                    # New alert
                    alert = {
                        "rule_name": rule_name,
                        "metric": rule.metric,
                        "value": metric_value,
                        "threshold": rule.threshold,
                        "severity": rule.severity,
                        "triggered_at": current_time,
                        "status": "active"
                    }
                    self.active_alerts[rule_name] = alert
                    self.alert_history.append(alert.copy())
                    new_alerts.append(alert)
                    logger.warning(f"🚨 ALERT: {rule_name} - {rule.metric}={metric_value} {rule.condition} {rule.threshold}")
            else:
                # Alert resolved
                if rule_name in self.active_alerts:
                    resolved_alert = self.active_alerts.pop(rule_name)
                    resolved_alert["status"] = "resolved"
                    resolved_alert["resolved_at"] = current_time
                    self.alert_history.append(resolved_alert)
                    logger.info(f"✅ RESOLVED: {rule_name}")
        
        return new_alerts
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """Get alert history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [alert for alert in self.alert_history 
                if alert.get("triggered_at", 0) > cutoff_time]

class MCPMonitoringDashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self, mcp_server=None):
        self.app = FastAPI(title="MCP Server Monitoring Dashboard")
        self.mcp_server = mcp_server
        self.alert_manager = AlertManager()
        
        # Real-time data storage
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.connected_clients = set()
        
        # Setup routes
        self._setup_routes()
        
        # Start background monitoring
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("📊 Monitoring Dashboard initialized")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            html_content = self._generate_dashboard_html()
            return HTMLResponse(content=html_content)
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get current metrics"""
            try:
                current_metrics = await self._collect_metrics()
                return {
                    "timestamp": time.time(),
                    "metrics": current_metrics,
                    "alerts": self.alert_manager.get_active_alerts()
                }
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                return {"error": str(e)}
        
        @self.app.get("/api/health")
        async def get_health():
            """Get comprehensive health status"""
            try:
                if self.mcp_server:
                    health_status = await self.mcp_server.health_checker.run_checks()
                    return health_status
                else:
                    return {"overall_status": "unknown", "message": "MCP server not connected"}
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return {"overall_status": "error", "error": str(e)}
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get alert information"""
            return {
                "active_alerts": self.alert_manager.get_active_alerts(),
                "alert_history": self.alert_manager.get_alert_history(),
                "alert_rules": {name: {
                    "metric": rule.metric,
                    "threshold": rule.threshold,
                    "condition": rule.condition,
                    "severity": rule.severity,
                    "enabled": rule.enabled
                } for name, rule in self.alert_manager.rules.items()}
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates"""
            await websocket.accept()
            self.connected_clients.add(websocket)
            logger.info("👤 Client connected to real-time monitoring")
            
            try:
                while True:
                    await websocket.receive_text()  # Keep connection alive
            except Exception as e:
                logger.info("👋 Client disconnected from monitoring")
            finally:
                self.connected_clients.discard(websocket)
    
    def _generate_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .alert-critical { border-left: 4px solid #ef4444; }
        .alert-warning { border-left: 4px solid #f59e0b; }
        .alert-info { border-left: 4px solid #3b82f6; }
        .status-healthy { color: #10b981; }
        .status-degraded { color: #f59e0b; }
        .status-unhealthy { color: #ef4444; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-6">
        <h1 class="text-3xl font-bold mb-6">🚀 Enterprise MCP Server Monitoring</h1>
        
        <!-- Status Overview -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Overall Health</h3>
                <div id="overall-status" class="text-2xl font-bold">Loading...</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Active Alerts</h3>
                <div id="active-alerts-count" class="text-2xl font-bold text-red-500">0</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Circuit Breakers</h3>
                <div id="circuit-breaker-status" class="text-2xl font-bold">Loading...</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-2">Success Rate</h3>
                <div id="success-rate" class="text-2xl font-bold">Loading...</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-4">System Metrics</h3>
                <canvas id="system-chart" height="200"></canvas>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-4">Request Metrics</h3>
                <canvas id="request-chart" height="200"></canvas>
            </div>
        </div>
        
        <!-- Alerts Panel -->
        <div class="bg-white p-6 rounded-lg shadow mb-6">
            <h3 class="text-lg font-semibold mb-4">🚨 Active Alerts</h3>
            <div id="alerts-container">No active alerts</div>
        </div>
        
        <!-- Health Checks -->
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-semibold mb-4">💊 Health Checks</h3>
            <div id="health-checks-container">Loading...</div>
        </div>
    </div>
    
    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        // Charts
        const systemCtx = document.getElementById('system-chart').getContext('2d');
        const requestCtx = document.getElementById('request-chart').getContext('2d');
        
        const systemChart = new Chart(systemCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU %',
                    data: [],
                    borderColor: '#3b82f6',
                    tension: 0.1
                }, {
                    label: 'Memory %',
                    data: [],
                    borderColor: '#ef4444',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, max: 100 } }
            }
        });
        
        const requestChart = new Chart(requestCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Requests/min',
                    data: [],
                    borderColor: '#10b981',
                    tension: 0.1
                }, {
                    label: 'Errors/min',
                    data: [],
                    borderColor: '#f59e0b',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
        
        // Update dashboard data
        async function updateDashboard() {
            try {
                // Get metrics
                const metricsResponse = await fetch('/api/metrics');
                const metricsData = await metricsResponse.json();
                
                // Get health
                const healthResponse = await fetch('/api/health');
                const healthData = await healthResponse.json();
                
                // Get alerts
                const alertsResponse = await fetch('/api/alerts');
                const alertsData = await alertsResponse.json();
                
                // Update status overview
                document.getElementById('overall-status').textContent = healthData.overall_status || 'Unknown';
                document.getElementById('overall-status').className = `text-2xl font-bold status-${healthData.overall_status}`;
                
                document.getElementById('active-alerts-count').textContent = alertsData.active_alerts.length;
                
                // Update charts
                updateCharts(metricsData);
                
                // Update alerts
                updateAlerts(alertsData.active_alerts);
                
                // Update health checks
                updateHealthChecks(healthData.checks || {});
                
            } catch (error) {
                console.error('Failed to update dashboard:', error);
            }
        }
        
        function updateCharts(data) {
            const now = new Date().toLocaleTimeString();
            const metrics = data.metrics || {};
            
            // System chart
            systemChart.data.labels.push(now);
            systemChart.data.datasets[0].data.push(metrics['system.cpu_percent'] || 0);
            systemChart.data.datasets[1].data.push(metrics['system.memory_percent'] || 0);
            
            if (systemChart.data.labels.length > 50) {
                systemChart.data.labels.shift();
                systemChart.data.datasets.forEach(dataset => dataset.data.shift());
            }
            
            systemChart.update();
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            
            if (alerts.length === 0) {
                container.innerHTML = '<p class="text-gray-500">No active alerts</p>';
                return;
            }
            
            container.innerHTML = alerts.map(alert => `
                <div class="p-4 mb-4 border-l-4 alert-${alert.severity}">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="font-semibold">${alert.rule_name}</h4>
                            <p class="text-sm text-gray-600">${alert.metric} = ${alert.value} (threshold: ${alert.threshold})</p>
                            <p class="text-xs text-gray-500">Triggered: ${new Date(alert.triggered_at * 1000).toLocaleString()}</p>
                        </div>
                        <span class="px-2 py-1 text-xs font-semibold rounded bg-${alert.severity === 'critical' ? 'red' : alert.severity === 'warning' ? 'yellow' : 'blue'}-100 text-${alert.severity === 'critical' ? 'red' : alert.severity === 'warning' ? 'yellow' : 'blue'}-800">
                            ${alert.severity.toUpperCase()}
                        </span>
                    </div>
                </div>
            `).join('');
        }
        
        function updateHealthChecks(checks) {
            const container = document.getElementById('health-checks-container');
            
            container.innerHTML = Object.entries(checks).map(([name, check]) => `
                <div class="flex justify-between items-center p-3 border-b">
                    <span class="font-medium">${name}</span>
                    <span class="px-2 py-1 text-xs font-semibold rounded ${
                        check.status === 'healthy' ? 'bg-green-100 text-green-800' :
                        check.status === 'unhealthy' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                    }">
                        ${check.status.toUpperCase()}
                    </span>
                </div>
            `).join('');
        }
        
        // Initial load and periodic updates
        updateDashboard();
        setInterval(updateDashboard, 5000); // Update every 5 seconds
        
        ws.onmessage = function(event) {
            updateDashboard(); // Real-time update on WebSocket message
        };
    </script>
</body>
</html>
        '''
    
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect current system and application metrics"""
        metrics = {}
        
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            metrics.update({
                "system.cpu_percent": cpu_percent,
                "system.memory_percent": memory.percent,
                "system.memory_available": memory.available,
                "system.timestamp": time.time()
            })
            
            # MCP server metrics (if available)
            if self.mcp_server:
                server_metrics = self.mcp_server.metrics.get_summary()
                metrics.update({
                    "mcp.uptime": server_metrics.get("uptime_seconds", 0),
                    "mcp.total_metrics": server_metrics.get("total_metrics", 0)
                })
                
                # Circuit breaker metrics
                for name, cb in self.mcp_server.circuit_breakers.items():
                    cb_metrics = cb.get_metrics()
                    metrics[f"circuit_breaker.{name}.success_rate"] = cb_metrics["success_rate"]
                    metrics[f"circuit_breaker.{name}.failure_count"] = cb_metrics["failure_count"]
            
            # Store metrics history
            for key, value in metrics.items():
                self.metrics_history[key].append({
                    "timestamp": time.time(),
                    "value": value
                })
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Collect current metrics
                current_metrics = await self._collect_metrics()
                
                # Evaluate alerts
                new_alerts = self.alert_manager.evaluate_alerts(current_metrics)
                
                # Send real-time updates to connected clients
                if self.connected_clients and (new_alerts or len(self.connected_clients) > 0):
                    message = {
                        "type": "metrics_update",
                        "data": current_metrics,
                        "alerts": new_alerts,
                        "timestamp": time.time()
                    }
                    
                    # Send to all connected clients
                    disconnected_clients = set()
                    for client in self.connected_clients:
                        try:
                            await client.send_text(json.dumps(message))
                        except:
                            disconnected_clients.add(client)
                    
                    # Remove disconnected clients
                    self.connected_clients -= disconnected_clients
                
                await asyncio.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the monitoring dashboard"""
        logger.info(f"🌐 Starting monitoring dashboard on http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")

# Standalone execution
async def main():
    """Run monitoring dashboard standalone"""
    dashboard = MCPMonitoringDashboard()
    dashboard.run()

if __name__ == "__main__":
    asyncio.run(main())