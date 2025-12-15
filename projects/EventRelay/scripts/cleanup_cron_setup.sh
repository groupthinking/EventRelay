#!/bin/bash
# UVAI Database Cleanup Cron Setup Script
# =======================================
#
# This script sets up automated database cleanup using cron.
# Run this script to install the cleanup job.
#
# Usage:
#   ./cleanup_cron_setup.sh          # Install daily cleanup (default)
#   ./cleanup_cron_setup.sh hourly   # Install hourly cleanup
#   ./cleanup_cron_setup.sh weekly   # Install weekly cleanup
#

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/scheduled_cleanup.py"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON_PATH="/usr/local/bin/python3"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to get current cron jobs
get_current_cron() {
    crontab -l 2>/dev/null || echo ""
}

# Function to check if cleanup job already exists
cleanup_job_exists() {
    local current_cron="$1"
    echo "$current_cron" | grep -q "scheduled_cleanup.py" || return 1
}

# Function to remove existing cleanup jobs
remove_existing_jobs() {
    local current_cron="$1"
    echo "$current_cron" | grep -v "scheduled_cleanup.py" || echo ""
}

# Function to create cron job based on frequency
create_cron_job() {
    local frequency="$1"
    local cleanup_script="$2"

    case "$frequency" in
        "hourly")
            # Every hour at minute 30
            echo "30 * * * * cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" \"$cleanup_script\" >> \"$LOG_DIR/cleanup_cron.log\" 2>&1"
            ;;
        "daily")
            # Daily at 2:00 AM
            echo "0 2 * * * cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" \"$cleanup_script\" >> \"$LOG_DIR/cleanup_cron.log\" 2>&1"
            ;;
        "weekly")
            # Weekly on Sunday at 2:00 AM
            echo "0 2 * * 0 cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" \"$cleanup_script\" >> \"$LOG_DIR/cleanup_cron.log\" 2>&1"
            ;;
        "test")
            # Every 5 minutes for testing
            echo "*/5 * * * * cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" \"$cleanup_script\" >> \"$LOG_DIR/cleanup_cron.log\" 2>&1"
            ;;
        *)
            echo "ERROR: Invalid frequency '$frequency'. Use: hourly, daily, weekly, or test"
            exit 1
            ;;
    esac
}

# Main script
main() {
    local frequency="${1:-daily}"

    echo "UVAI Database Cleanup Cron Setup"
    echo "================================"
    echo ""
    echo "Project Root: $PROJECT_ROOT"
    echo "Cleanup Script: $CLEANUP_SCRIPT"
    echo "Log Directory: $LOG_DIR"
    echo "Frequency: $frequency"
    echo ""

    # Check if cleanup script exists
    if [[ ! -f "$CLEANUP_SCRIPT" ]]; then
        echo "ERROR: Cleanup script not found at $CLEANUP_SCRIPT"
        exit 1
    fi

    # Check if Python exists
    if [[ ! -x "$PYTHON_PATH" ]]; then
        echo "WARNING: Python not found at $PYTHON_PATH, trying python3..."
        if command -v python3 &> /dev/null; then
            PYTHON_PATH="python3"
            echo "Found python3 at $(which python3)"
        else
            echo "ERROR: Python 3 not found"
            exit 1
        fi
    fi

    # Get current cron jobs
    local current_cron
    current_cron=$(get_current_cron)

    # Check if cleanup job already exists
    if cleanup_job_exists "$current_cron"; then
        echo "Existing cleanup job found. Updating..."
        current_cron=$(remove_existing_jobs "$current_cron")
    else
        echo "No existing cleanup job found. Installing new job..."
    fi

    # Create new cron job
    local new_job
    new_job=$(create_cron_job "$frequency" "$CLEANUP_SCRIPT")

    # Combine existing jobs with new job
    local updated_cron
    if [[ -n "$current_cron" ]]; then
        updated_cron="$current_cron
$new_job"
    else
        updated_cron="$new_job"
    fi

    # Install the updated cron jobs
    echo "$updated_cron" | crontab -

    echo ""
    echo "✅ SUCCESS: Database cleanup cron job installed!"
    echo ""
    echo "Cron job details:"
    echo "  Frequency: $frequency"
    echo "  Command: $new_job"
    echo "  Logs: $LOG_DIR/cleanup_cron.log"
    echo ""
    echo "To view current cron jobs: crontab -l"
    echo "To remove this job: crontab -r (removes ALL cron jobs)"
    echo "To edit manually: crontab -e"
    echo ""
    echo "Test the job manually:"
    echo "  cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" \"$CLEANUP_SCRIPT\" --dry-run"
}

# Function to uninstall cleanup job
uninstall() {
    echo "Uninstalling UVAI database cleanup cron job..."

    local current_cron
    current_cron=$(get_current_cron)

    if cleanup_job_exists "$current_cron"; then
        local updated_cron
        updated_cron=$(remove_existing_jobs "$current_cron")
        echo "$updated_cron" | crontab -
        echo "✅ Cleanup job removed successfully"
    else
        echo "No cleanup job found to remove"
    fi
}

# Function to show status
status() {
    echo "UVAI Database Cleanup Status"
    echo "============================"

    local current_cron
    current_cron=$(get_current_cron)

    if cleanup_job_exists "$current_cron"; then
        echo "✅ Cleanup job is INSTALLED"
        echo ""
        echo "Current cleanup job:"
        echo "$current_cron" | grep "scheduled_cleanup.py"
        echo ""
        echo "Log file: $LOG_DIR/cleanup_cron.log"
    else
        echo "❌ Cleanup job is NOT installed"
        echo ""
        echo "To install: $0 [hourly|daily|weekly]"
    fi
}

# Help function
show_help() {
    cat << EOF
UVAI Database Cleanup Cron Setup

USAGE:
    $0 [COMMAND] [FREQUENCY]

COMMANDS:
    (no command)    Install cleanup job (default: daily)
    uninstall       Remove cleanup job
    status          Show cleanup job status
    test            Install test job (runs every 5 minutes)

FREQUENCIES:
    hourly          Run cleanup every hour
    daily           Run cleanup daily at 2:00 AM (default)
    weekly          Run cleanup weekly on Sunday at 2:00 AM

EXAMPLES:
    $0              # Install daily cleanup
    $0 hourly       # Install hourly cleanup
    $0 weekly       # Install weekly cleanup
    $0 test         # Install test cleanup (every 5 min)
    $0 uninstall    # Remove cleanup job
    $0 status       # Show job status

LOGS:
    Cleanup logs: $LOG_DIR/cleanup_cron.log
    Manual test: cd "$PROJECT_ROOT" && python3 "$CLEANUP_SCRIPT" --dry-run

EOF
}

# Parse command line arguments
case "${1:-}" in
    "uninstall")
        uninstall
        ;;
    "status")
        status
        ;;
    "test")
        main "test"
        ;;
    "hourly"|"daily"|"weekly")
        main "$1"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    "")
        main "daily"
        ;;
    *)
        echo "ERROR: Unknown command '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac
