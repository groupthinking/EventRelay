#!/usr/bin/env python3
"""
Cursor Status Dashboard
Real-time monitoring dashboard for Cursor connectivity and system health.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
from aiohttp import web
import jinja2
import aiofiles

from cursor_monitor import CursorConnectionMonitor
from backup_api_manager import BackupAPIManager
from auto_recovery_system import AutomatedRecoverySystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CursorStatusDashboard:
    """Web-based dashboard for Cursor status monitoring."""

    def __init__(self):
        self.monitor = CursorConnectionMonitor()
        self.backup_manager = BackupAPIManager()
        self.recovery_system = AutomatedRecoverySystem()
        self.app = web.Application()
        self.setup_routes()

        # Dashboard data
        self.dashboard_data = {
            "last_update": None,
            "cursor_status": {},
            "api_health": {},
            "recovery_status": {},
            "system_metrics": {}
        }

        # Template environment
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('templates'),
            autoescape=True
        )

    def setup_routes(self):
        """Setup web application routes."""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/health', self.get_health)
        self.app.router.add_get('/api/recovery', self.get_recovery)
        self.app.router.add_post('/api/recovery/trigger', self.trigger_recovery)
        self.app.router.add_static('/static', 'static')

    async def index(self, request):
        """Serve the main dashboard page."""
        try:
            template = self.template_env.get_template('dashboard.html')

            # Update dashboard data
            await self.update_dashboard_data()

            return web.Response(
                text=template.render(**self.dashboard_data),
                content_type='text/html'
            )
        except Exception as e:
            logger.error(f"Dashboard render error: {e}")
            return web.Response(text=f"Error: {e}", status=500)

    async def get_status(self, request):
        """API endpoint for Cursor status."""
        try:
            status = await self.monitor.check_cursor_status()
            return web.json_response(asdict(status))
        except Exception as e:
            logger.error(f"Status API error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_health(self, request):
        """API endpoint for API health status."""
        try:
            health_report = self.backup_manager.get_health_report()
            return web.json_response(health_report)
        except Exception as e:
            logger.error(f"Health API error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_recovery(self, request):
        """API endpoint for recovery status."""
        try:
            recovery_report = self.recovery_system.get_recovery_report()
            return web.json_response(recovery_report)
        except Exception as e:
            logger.error(f"Recovery API error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def trigger_recovery(self, request):
        """API endpoint to manually trigger recovery."""
        try:
            data = await request.json()
            incident_type = data.get('incident_type', 'connection_timeout')

            success = await self.recovery_system.execute_recovery_plan(incident_type)

            return web.json_response({
                "success": success,
                "incident_type": incident_type,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Recovery trigger error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def update_dashboard_data(self):
        """Update dashboard data with latest information."""
        try:
            # Cursor status
            cursor_status = await self.monitor.check_cursor_status()
            self.dashboard_data["cursor_status"] = asdict(cursor_status)

            # API health
            api_health = self.backup_manager.get_health_report()
            self.dashboard_data["api_health"] = api_health

            # Recovery status
            recovery_status = self.recovery_system.get_recovery_report()
            self.dashboard_data["recovery_status"] = recovery_status

            # System metrics
            system_metrics = await self.get_system_metrics()
            self.dashboard_data["system_metrics"] = system_metrics

            self.dashboard_data["last_update"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Dashboard data update error: {e}")

    async def get_system_metrics(self) -> Dict:
        """Get system performance metrics."""
        try:
            # Basic system metrics (macOS specific)
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections()),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"System metrics error: {e}")
            return {"error": str(e)}

    async def start_background_updates(self):
        """Start background update tasks."""
        async def update_loop():
            while True:
                try:
                    await self.update_dashboard_data()
                    await asyncio.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Background update error: {e}")
                    await asyncio.sleep(30)

        asyncio.create_task(update_loop())

    def create_html_template(self):
        """Create the HTML template for the dashboard."""
        template_dir = Path("/Users/garvey/Desktop/youtube_extension/templates")
        template_dir.mkdir(exist_ok=True)

        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cursor Status Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .status-healthy { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
        .card { margin-bottom: 1rem; }
        .metric-card { text-align: center; }
        .metric-value { font-size: 2rem; font-weight: bold; }
        .refresh-indicator { display: none; }
        .refreshing .refresh-indicator { display: inline; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="fas fa-chart-line"></i> Cursor Status Dashboard
            </span>
            <span class="navbar-text" id="last-update">
                Last update: {{ last_update or 'Never' }}
            </span>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <!-- Alert for active incidents -->
        {% if recovery_status.active_incident %}
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Active Incident:</strong> {{ recovery_status.active_incident }}
            <button class="btn btn-sm btn-outline-danger ms-2" onclick="triggerRecovery()">
                <i class="fas fa-wrench"></i> Run Recovery
            </button>
        </div>
        {% endif %}

        <div class="row">
            <!-- Cursor Status -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-terminal"></i> Cursor Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6 metric-card">
                                <div class="metric-value status-{{ 'healthy' if cursor_status.is_connected else 'error' }}">
                                    <i class="fas fa-{{ 'check-circle' if cursor_status.is_connected else 'times-circle' }}"></i>
                                </div>
                                <div>Connection</div>
                            </div>
                            <div class="col-6 metric-card">
                                <div class="metric-value">{{ cursor_status.response_time_ms | round(1) if cursor_status.response_time_ms else 'N/A' }}</div>
                                <div>Response (ms)</div>
                            </div>
                        </div>
                        <hr>
                        <p><strong>Version:</strong> {{ cursor_status.version }}</p>
                        {% if cursor_status.last_error %}
                        <p class="text-danger"><strong>Last Error:</strong> {{ cursor_status.last_error }}</p>
                        {% endif %}
                        <p class="text-muted small">Last checked: {{ cursor_status.timestamp }}</p>
                    </div>
                </div>
            </div>

            <!-- Recovery Statistics -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-shield-alt"></i> Recovery System</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-4 metric-card">
                                <div class="metric-value">{{ recovery_status.success_rate_percentage | round(1) }}%</div>
                                <div>Success Rate</div>
                            </div>
                            <div class="col-4 metric-card">
                                <div class="metric-value">{{ recovery_status.total_recovery_attempts }}</div>
                                <div>Total Attempts</div>
                            </div>
                            <div class="col-4 metric-card">
                                <div class="metric-value status-{{ 'healthy' if not recovery_status.active_incident else 'error' }}">
                                    {{ 'OK' if not recovery_status.active_incident else 'ACTIVE' }}
                                </div>
                                <div>Status</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- API Health Status -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-server"></i> API Health Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Provider</th>
                                        <th>Status</th>
                                        <th>Uptime</th>
                                        <th>Avg Response (ms)</th>
                                        <th>Consecutive Failures</th>
                                        <th>Last Check</th>
                                    </tr>
                                </thead>
                                <tbody id="api-health-table">
                                    {% for provider, summary in api_health.summary.items() %}
                                    <tr>
                                        <td>{{ provider }}</td>
                                        <td>
                                            <span class="status-{{ 'healthy' if summary.is_healthy else 'error' }}">
                                                <i class="fas fa-{{ 'check-circle' if summary.is_healthy else 'times-circle' }}"></i>
                                                {{ 'Healthy' if summary.is_healthy else 'Unhealthy' }}
                                            </span>
                                        </td>
                                        <td>{{ summary.uptime_percentage | round(1) }}%</td>
                                        <td>{{ summary.average_response_time_ms | round(1) if summary.average_response_time_ms else 'N/A' }}</td>
                                        <td>{{ summary.consecutive_failures }}</td>
                                        <td>{{ summary.last_check }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Metrics -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-cogs"></i> System Metrics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-2 metric-card">
                                <div class="metric-value">{{ system_metrics.cpu_percent | round(1) }}%</div>
                                <div>CPU Usage</div>
                            </div>
                            <div class="col-md-2 metric-card">
                                <div class="metric-value">{{ system_metrics.memory_percent | round(1) }}%</div>
                                <div>Memory Usage</div>
                            </div>
                            <div class="col-md-2 metric-card">
                                <div class="metric-value">{{ system_metrics.disk_usage | round(1) }}%</div>
                                <div>Disk Usage</div>
                            </div>
                            <div class="col-md-2 metric-card">
                                <div class="metric-value">{{ system_metrics.network_connections }}</div>
                                <div>Network Connections</div>
                            </div>
                            <div class="col-md-2 metric-card">
                                <div class="metric-value">{{ system_metrics.load_average[0] | round(2) if system_metrics.load_average else 'N/A' }}</div>
                                <div>Load Average</div>
                            </div>
                            <div class="col-md-2">
                                <button class="btn btn-primary w-100" onclick="refreshData()">
                                    <i class="fas fa-sync-alt"></i> Refresh
                                    <i class="fas fa-spinner fa-spin refresh-indicator"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Recovery Attempts -->
        {% if recovery_status.recent_attempts %}
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-history"></i> Recent Recovery Attempts</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>Strategy</th>
                                        <th>Success</th>
                                        <th>Duration (ms)</th>
                                        <th>Error</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for attempt in recovery_status.recent_attempts %}
                                    <tr>
                                        <td>{{ attempt.timestamp }}</td>
                                        <td>{{ attempt.strategy }}</td>
                                        <td>
                                            <span class="status-{{ 'healthy' if attempt.success else 'error' }}">
                                                {{ 'Success' if attempt.success else 'Failed' }}
                                            </span>
                                        </td>
                                        <td>{{ attempt.duration_ms | round(1) }}</td>
                                        <td>{{ attempt.error_message or '-' }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <script>
        let refreshTimeout;

        async function refreshData() {
            const refreshBtn = document.querySelector('button[onclick="refreshData()"]');
            refreshBtn.classList.add('refreshing');

            try {
                // Update all data sections
                await Promise.all([
                    updateCursorStatus(),
                    updateAPIHealth(),
                    updateRecoveryStatus(),
                    updateSystemMetrics()
                ]);

                document.getElementById('last-update').textContent = 'Last update: ' + new Date().toISOString();
            } catch (error) {
                console.error('Refresh error:', error);
            } finally {
                refreshBtn.classList.remove('refreshing');
            }
        }

        async function updateCursorStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();

            // Update status indicators
            const connectionIcon = document.querySelector('.metric-value i');
            connectionIcon.className = `fas fa-${data.is_connected ? 'check-circle' : 'times-circle'}`;
            connectionIcon.parentElement.className = `metric-value status-${data.is_connected ? 'healthy' : 'error'}`;
        }

        async function updateAPIHealth() {
            const response = await fetch('/api/health');
            const data = await response.json();

            // Update API health table
            const tbody = document.getElementById('api-health-table');
            tbody.innerHTML = '';

            for (const [provider, summary] of Object.entries(data.summary || {})) {
                const row = `
                    <tr>
                        <td>${provider}</td>
                        <td>
                            <span class="status-${summary.is_healthy ? 'healthy' : 'error'}">
                                <i class="fas fa-${summary.is_healthy ? 'check-circle' : 'times-circle'}"></i>
                                ${summary.is_healthy ? 'Healthy' : 'Unhealthy'}
                            </span>
                        </td>
                        <td>${summary.uptime_percentage.toFixed(1)}%</td>
                        <td>${summary.average_response_time_ms ? summary.average_response_time_ms.toFixed(1) : 'N/A'}</td>
                        <td>${summary.consecutive_failures}</td>
                        <td>${summary.last_check}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            }
        }

        async function updateRecoveryStatus() {
            const response = await fetch('/api/recovery');
            const data = await response.json();

            // Update success rate and other metrics
            // Implementation would update specific DOM elements
        }

        async function updateSystemMetrics() {
            // System metrics are updated on full refresh
        }

        async function triggerRecovery() {
            if (!confirm('Trigger recovery process?')) return;

            try {
                const response = await fetch('/api/recovery/trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ incident_type: 'connection_timeout' })
                });

                const result = await response.json();

                if (result.success) {
                    alert('Recovery triggered successfully');
                    refreshData();
                } else {
                    alert('Recovery failed: ' + JSON.stringify(result));
                }
            } catch (error) {
                alert('Recovery trigger error: ' + error.message);
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);

        // Initial data load
        document.addEventListener('DOMContentLoaded', refreshData);
    </script>
</body>
</html>
        """

        template_file = template_dir / "dashboard.html"
        with open(template_file, 'w') as f:
            f.write(template_content)

    async def run_dashboard(self, host='localhost', port=8080):
        """Run the dashboard server."""
        # Create template if it doesn't exist
        template_dir = Path("/Users/garvey/Desktop/youtube_extension/templates")
        if not (template_dir / "dashboard.html").exists():
            self.create_html_template()

        # Start background updates
        await self.start_background_updates()

        logger.info(f"Starting dashboard on http://{host}:{port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        # Keep the server running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour
        except KeyboardInterrupt:
            logger.info("Dashboard stopped")
        finally:
            await runner.cleanup()

async def main():
    """Main entry point for the dashboard."""
    dashboard = CursorStatusDashboard()

    try:
        await dashboard.run_dashboard()
    except KeyboardInterrupt:
        logger.info("Dashboard shutdown requested")

if __name__ == "__main__":
    asyncio.run(main())
