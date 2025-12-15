#!/usr/bin/env python3
import time
import psutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [MONITOR] %(message)s')
logger = logging.getLogger(__name__)

def monitor_mcp_performance():
    """Monitor MCP server performance"""
    while True:
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                logger.warning(f"High memory usage: {memory.percent}%")

            # Check CPU usage
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 70:
                logger.warning(f"High CPU usage: {cpu}%")

            time.sleep(60)  # Monitor every minute

        except KeyboardInterrupt:
            logger.info("Monitoring stopped")
            break
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_mcp_performance()
