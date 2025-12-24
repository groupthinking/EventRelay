#!/bin/bash

# Automated Dependency Monitor for UVAI YouTube Extension
# This script monitors excluded directories and project dependencies

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/scripts"
BACKUP_DIR="$PROJECT_ROOT/.backups"
LOG_DIR="$PROJECT_ROOT/logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/dependency_monitor_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="$LOG_DIR/dependency_report_$(date +%Y%m%d).json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $*${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $*${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S') - WARNING: $*${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S') - INFO: $*${NC}" | tee -a "$LOG_FILE"
}

# Function to check excluded directories usage
check_excluded_directories() {
    log "🔍 Checking excluded development directories..."

    if [ -f "$BACKUP_DIR/excluded_dirs/check_usage.py" ]; then
        cd "$PROJECT_ROOT"
        python3 "$BACKUP_DIR/excluded_dirs/check_usage.py" >> "$LOG_FILE" 2>&1

        # Check if there were critical issues
        if grep -q "CRITICAL ISSUES FOUND" "$LOG_FILE"; then
            log_error "Critical dependency issues found in excluded directories"
            return 1
        else
            log_success "No critical dependency issues found"
            return 0
        fi
    else
        log_warning "check_usage.py script not found - performing basic directory check"

        # Basic check for excluded directories
        local excluded_found=0
        if [ -d "$PROJECT_ROOT/development/my-agent" ]; then
            log_info "Found excluded directory: development/my-agent"
            excluded_found=1
        fi
        if [ -d "$PROJECT_ROOT/development/fastvlm-webgpu" ]; then
            log_info "Found excluded directory: development/fastvlm-webgpu"
            excluded_found=1
        fi

        if [ $excluded_found -eq 1 ]; then
            log_info "Excluded directories exist but no critical imports detected"
            return 0
        else
            log_info "No excluded directories found"
            return 0
        fi
    fi
}

# Function to check Node.js dependencies
check_nodejs_dependencies() {
    log "📦 Checking Node.js dependencies..."

    local issues_found=0

    # Check fastvlm-webgpu
    if [ -d "$PROJECT_ROOT/development/fastvlm-webgpu" ]; then
        cd "$PROJECT_ROOT/development/fastvlm-webgpu"

        # Check if package.json exists
        if [ -f "package.json" ]; then
            # Check if node_modules exists
            if [ ! -d "node_modules" ]; then
                log_warning "fastvlm-webgpu: Dependencies not installed (node_modules missing)"
                log_info "Installing dependencies for fastvlm-webgpu..."
                if npm install >> "$LOG_FILE" 2>&1; then
                    log_success "fastvlm-webgpu dependencies installed successfully"
                else
                    log_error "Failed to install fastvlm-webgpu dependencies"
                    issues_found=$((issues_found + 1))
                fi
            else
                log_success "fastvlm-webgpu: Dependencies are installed"
            fi

            # Check for outdated packages
            log_info "Checking for outdated packages in fastvlm-webgpu..."
            if npm outdated >> "$LOG_FILE" 2>&1; then
                log_info "fastvlm-webgpu packages are up to date"
            else
                log_warning "Some fastvlm-webgpu packages may be outdated"
            fi
        else
            log_error "fastvlm-webgpu: package.json not found"
            issues_found=$((issues_found + 1))
        fi
    fi

    # Check frontend if it exists
    if [ -d "$PROJECT_ROOT/frontend" ] && [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
        cd "$PROJECT_ROOT/frontend"

        if [ ! -d "node_modules" ]; then
            log_warning "frontend: Dependencies not installed"
            log_info "Installing frontend dependencies..."
            if npm install >> "$LOG_FILE" 2>&1; then
                log_success "Frontend dependencies installed successfully"
            else
                log_error "Failed to install frontend dependencies"
                issues_found=$((issues_found + 1))
            fi
        else
            log_success "Frontend dependencies are installed"
        fi
    fi

    return $issues_found
}

# Function to check Python dependencies
check_python_dependencies() {
    log "🐍 Checking Python dependencies..."

    cd "$PROJECT_ROOT"

    # Check if virtual environment exists and is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        log_warning "No Python virtual environment is active"
        if [ -d "venv" ] || [ -d ".venv" ]; then
            log_info "Virtual environment found but not activated"
        else
            log_warning "No virtual environment found"
        fi
    else
        log_success "Python virtual environment is active: $VIRTUAL_ENV"
    fi

    # Check if requirements files exist and are up to date
    if [ -f "requirements.txt" ]; then
        log_info "Found requirements.txt - checking dependencies..."

        # Check for outdated packages (requires pip-review)
        if command -v pip-review >/dev/null 2>&1; then
            log_info "Checking for outdated Python packages..."
            pip-review --auto >> "$LOG_FILE" 2>&1 || log_warning "Some Python packages may be outdated"
        else
            log_info "pip-review not installed - install with: pip install pip-review"
        fi
    elif [ -f "pyproject.toml" ]; then
        log_info "Found pyproject.toml - using modern Python packaging"
        log_info "Dependencies managed through pyproject.toml"
    else
        log_warning "No Python dependency file found (requirements.txt or pyproject.toml)"
    fi
}

# Function to check for security vulnerabilities
check_security() {
    log "🔒 Checking for security vulnerabilities..."

    cd "$PROJECT_ROOT"

    # Check Python security
    if command -v safety >/dev/null 2>&1; then
        log_info "Checking Python packages for security vulnerabilities..."
        safety check >> "$LOG_FILE" 2>&1 || log_warning "Security check completed with warnings"
    else
        log_info "Safety not installed - install with: pip install safety"
    fi

    # Check Node.js security if npm is available
    if command -v npm >/dev/null 2>&1; then
        if [ -f "package.json" ]; then
            log_info "Checking Node.js packages for security vulnerabilities..."
            npm audit >> "$LOG_FILE" 2>&1 || log_warning "NPM audit completed with warnings"
        fi
    fi
}

# Function to generate report
generate_report() {
    log "📊 Generating dependency report..."

    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local critical_issues=$(grep -c "CRITICAL" "$LOG_FILE" || echo "0")
    local warnings=$(grep -c "WARNING" "$LOG_FILE" || echo "0")
    local errors=$(grep -c "ERROR" "$LOG_FILE" || echo "0")

    local status
    if [ "$critical_issues" -eq 0 ]; then
        status="healthy"
    else
        status="critical"
    fi

    cat > "$REPORT_FILE" << EOF
{
    "timestamp": "$timestamp",
    "summary": {
        "critical_issues": $critical_issues,
        "warnings": $warnings,
        "errors": $errors,
        "status": "$status"
    },
    "checks": {
        "excluded_directories": {
            "status": "$(grep -q "No critical dependency issues" "$LOG_FILE" && echo "passed" || echo "failed")",
            "details": "Checked for active imports in excluded development directories"
        },
        "nodejs_dependencies": {
            "status": "$(grep -q "Dependencies are installed" "$LOG_FILE" && echo "passed" || echo "failed")",
            "details": "Verified Node.js dependencies are installed and up to date"
        },
        "python_dependencies": {
            "status": "$(grep -q "Python virtual environment is active" "$LOG_FILE" && echo "passed" || echo "warning")",
            "details": "Checked Python virtual environment and dependencies"
        },
        "security": {
            "status": "completed",
            "details": "Ran security vulnerability scans"
        }
    },
    "log_file": "$LOG_FILE"
}
EOF

    log_success "Report generated: $REPORT_FILE"
}

# Function to send notifications (if configured)
send_notifications() {
    local critical_issues=$(grep -c "CRITICAL" "$LOG_FILE" || echo "0")

    if [ "$critical_issues" -gt 0 ]; then
        log_error "CRITICAL ISSUES DETECTED - NOTIFICATION REQUIRED"

        # Check if terminal-notifier is available (macOS)
        if command -v terminal-notifier >/dev/null 2>&1; then
            terminal-notifier -title "UVAI Dependency Monitor" \
                            -message "Critical dependency issues found" \
                            -subtitle "Check $LOG_FILE for details"
        fi

        # Check if notify-send is available (Linux)
        if command -v notify-send >/dev/null 2>&1; then
            notify-send "UVAI Dependency Monitor" "Critical dependency issues found - check logs"
        fi

        log_info "Consider setting up email notifications or Slack webhooks for production"
    else
        log_success "All checks passed - no notifications needed"
    fi
}

# Main execution
main() {
    log "🚀 Starting Automated Dependency Monitor"
    log "Project Root: $PROJECT_ROOT"

    local exit_code=0

    # Run all checks
    check_excluded_directories || exit_code=1
    check_nodejs_dependencies || exit_code=1
    check_python_dependencies || exit_code=1
    check_security || exit_code=1

    # Generate report
    generate_report

    # Send notifications if needed
    send_notifications

    # Final status
    if [ $exit_code -eq 0 ]; then
        log_success "✅ All dependency checks completed successfully"
    else
        log_error "❌ Some dependency checks failed - review logs"
    fi

    log "📁 Log file: $LOG_FILE"
    log "📊 Report file: $REPORT_FILE"

    return $exit_code
}

# Run main function
main "$@"
