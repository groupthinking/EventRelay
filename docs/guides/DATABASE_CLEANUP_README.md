# Database Cleanup System

Automated database cleanup system for UVAI YouTube extension to prevent SQLite databases from growing unnecessarily over time.

## Overview

This system provides automated cleanup for the SQLite monitoring databases:
- `performance_monitoring.db` (36KB) - Performance metrics and alerts
- `.runtime/api_cost_monitoring.db` (32KB) - API usage and cost tracking

## Features

- ✅ **Configurable Retention Policies**: Different retention periods for different data types
- ✅ **Automated Scheduling**: Run cleanups daily, hourly, or weekly
- ✅ **Comprehensive Logging**: Detailed reports of cleanup operations
- ✅ **Safe Operations**: Transaction-based deletions with rollback support
- ✅ **Space Optimization**: Automatic VACUUM after cleanup to reclaim space
- ✅ **Multiple Scheduling Options**: Cron, systemd, or manual execution

## Retention Policies

### Performance Monitoring Database
- **Performance Metrics**: 30 days retention
- **Performance Alerts**: 90 days retention
- **Benchmark Results**: 180 days retention

### API Cost Monitoring Database
- **API Usage Records**: 90 days retention
- **Daily Budgets**: 365 days retention

## Quick Start

### 1. Manual Cleanup (Test First)

```bash
# Dry run to see what would be cleaned
cd /Users/garvey/Desktop/youtube_extension
python3 scripts/scheduled_cleanup.py --dry-run

# Run actual cleanup
python3 scripts/scheduled_cleanup.py
```

### 2. Automated Setup

#### Option A: Cron (Recommended for macOS/Linux)

```bash
# Install daily cleanup
./scripts/cleanup_cron_setup.sh

# Install hourly cleanup
./scripts/cleanup_cron_setup.sh hourly

# Check status
./scripts/cleanup_cron_setup.sh status

# Remove cleanup job
./scripts/cleanup_cron_setup.sh uninstall
```

#### Option B: Systemd (Linux only)

```bash
# Copy service files
sudo cp scripts/uvai-cleanup.service /etc/systemd/system/
sudo cp scripts/uvai-cleanup.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable uvai-cleanup.timer
sudo systemctl start uvai-cleanup.timer

# Check status
sudo systemctl list-timers uvai-cleanup.timer
```

## Configuration

### Retention Policy Configuration

Edit `src/youtube_extension/backend/services/database_cleanup_config.json`:

```json
{
  "retention_policies": {
    "performance_monitoring.db": [
      {
        "table_name": "performance_metrics",
        "retention_days": 30,
        "batch_size": 5000,
        "enabled": true,
        "description": "Keep performance metrics for 30 days"
      }
    ]
  },
  "cleanup_schedule": {
    "enabled": true,
    "interval_hours": 24,
    "start_hour": 2
  }
}
```

### Environment Variables

```bash
# Enable dry run mode
export CLEANUP_DRY_RUN=true

# Set logging level
export CLEANUP_LOG_LEVEL=DEBUG

# Email address for reports
export CLEANUP_REPORT_EMAIL=admin@example.com
```

## Manual Operations

### Run Specific Database Cleanup

```bash
# Clean only performance monitoring
python3 scripts/scheduled_cleanup.py --performance

# Clean only API costs
python3 scripts/scheduled_cleanup.py --api-costs
```

### Check Cleanup Status

```bash
# View cleanup statistics
python3 -c "from src.youtube_extension.backend.services.database_cleanup_service import cleanup_service; print(cleanup_service.get_cleanup_report())"
```

### Manual Trigger from Code

```python
from src.youtube_extension.backend.services.performance_monitor import performance_monitor
from src.youtube_extension.backend.services.api_cost_monitor import cost_monitor

# Clean performance database
result = await performance_monitor.trigger_manual_cleanup()

# Clean API cost database
result = await cost_monitor.trigger_manual_cleanup()
```

## Monitoring and Logs

### Log Files

- **Cron logs**: `logs/cleanup_cron.log`
- **Cleanup reports**: `logs/cleanup_report_YYYYMMDD_HHMMSS.txt`
- **JSON results**: `logs/cleanup_results_YYYYMMDD_HHMMSS.json`

### Sample Cleanup Report

```
============================================================
DATABASE CLEANUP REPORT - 2025-09-12T14:30:00.000000+00:00
============================================================

Database: performance_monitoring.db
Tables cleaned: 3
  ✅ performance_metrics: 1250 records deleted, 0.15MB freed
  ✅ performance_alerts: 45 records deleted, 0.02MB freed
  ✅ benchmark_results: 12 records deleted, 0.01MB freed

Database: .runtime/api_cost_monitoring.db
Tables cleaned: 2
  ✅ api_usage: 890 records deleted, 0.12MB freed
  ✅ daily_budgets: 5 records deleted, 0.00MB freed

SUMMARY:
Total databases cleaned: 2
Total records deleted: 2202
Total space freed: 0.30MB
============================================================
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Test imports
python3 -c "from src.youtube_extension.backend.services.database_cleanup_service import cleanup_service"
```

**2. Permission Issues**
```bash
# Check database file permissions
ls -la *.db

# Check script permissions
ls -la scripts/scheduled_cleanup.py
```

**3. Cron Not Running**
```bash
# Check cron logs
tail -f /var/log/syslog | grep cron

# Test manual execution
cd /Users/garvey/Desktop/youtube_extension
/usr/local/bin/python3 scripts/scheduled_cleanup.py --dry-run
```

### Recovery

**Restore from Backup**
```bash
# Stop cleanup service
./scripts/cleanup_cron_setup.sh uninstall

# Restore database files
cp backup/performance_monitoring.db ./
cp backup/api_cost_monitoring.db ./.runtime/

# Restart cleanup service
./scripts/cleanup_cron_setup.sh
```

## Performance Impact

### Resource Usage
- **Memory**: ~50MB during cleanup operations
- **CPU**: Minimal (< 5% during batch operations)
- **Disk I/O**: High during VACUUM operations (temporary)
- **Duration**: Typically 1-30 seconds depending on data volume

### Optimization Tips

1. **Schedule during off-peak hours** (default: 2:00 AM)
2. **Use batch sizes appropriate for your system**
3. **Monitor disk space before cleanup**
4. **Enable WAL mode for better concurrency** (if needed)

## Advanced Configuration

### Custom Cleanup Logic

```python
from src.youtube_extension.backend.services.database_cleanup_service import DatabaseCleanupService

# Create custom cleanup service
cleanup = DatabaseCleanupService()

# Add custom retention policy
cleanup.add_retention_policy(
    "custom_database.db",
    RetentionPolicy(
        table_name="custom_table",
        retention_days=60,
        batch_size=2000,
        description="Custom cleanup policy"
    )
)

# Run custom cleanup
results = cleanup.cleanup_database("custom_database.db")
```

### Integration with Monitoring

```python
# Add cleanup metrics to your monitoring
cleanup_report = cleanup_service.get_cleanup_report()

# Send to your metrics system
await performance_monitor.record_metric(
    "cleanup",
    "records_deleted",
    cleanup_report['cleanup_stats']['total_records_deleted']
)
```

## Security Considerations

- ✅ Database files are accessed with user permissions only
- ✅ No network access required for cleanup operations
- ✅ Sensitive data is not logged in cleanup reports
- ✅ Configuration files contain no secrets

## Maintenance

### Regular Tasks

- **Monthly**: Review retention policies for appropriateness
- **Weekly**: Check cleanup logs for errors
- **Daily**: Monitor database sizes and cleanup effectiveness

### Updates

```bash
# Update retention policies
vim src/youtube_extension/backend/services/database_cleanup_config.json

# Test changes
python3 scripts/scheduled_cleanup.py --dry-run

# Deploy changes
# (No restart required - config is loaded dynamically)
```

---

**Need Help?** Check the logs in `logs/` directory or run with `--verbose` flag for detailed debugging information.
