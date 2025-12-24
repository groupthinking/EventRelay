---
name: Phase 2 - Monitoring & CI/CD Setup
about: Production preparation Phase 2 - Deploy monitoring stack and validate CI/CD pipelines
title: '[Phase 2] Monitoring & CI/CD Setup'
labels: ['production', 'monitoring', 'ci-cd', 'phase-2', 'high-priority']
assignees: ''
---

# 📊 Phase 2: Monitoring & CI/CD Setup

**Estimated Time:** 8 hours  
**Priority:** HIGH  
**Dependencies:** Phase 1 (Security & Environment Setup) must be complete

## 📋 Overview

This phase establishes comprehensive monitoring, observability, and continuous integration/deployment infrastructure. Essential for maintaining production reliability and enabling rapid iteration.

---

## ✅ Tasks Checklist

### 🔴 CRITICAL - Monitoring Stack (4 hours)

- [ ] **Deploy Prometheus**
  - [ ] Install Prometheus server
  - [ ] Configure scraping for application metrics
  - [ ] Set up metrics endpoints in FastAPI:
    - [ ] `/metrics` - Prometheus format
    - [ ] Request duration histograms
    - [ ] Request count by endpoint
    - [ ] Error rate by endpoint
    - [ ] Active connections gauge
  - [ ] Configure retention policies (30 days recommended)
  - [ ] Test metrics collection
  - [ ] Document Prometheus configuration

- [ ] **Configure Grafana Dashboards**
  - [ ] Install Grafana
  - [ ] Connect Grafana to Prometheus data source
  - [ ] Create application dashboard:
    - [ ] API response times (p50, p95, p99)
    - [ ] Request rate by endpoint
    - [ ] Error rate percentage
    - [ ] Video processing queue depth
    - [ ] Transcript success/failure rate
  - [ ] Create infrastructure dashboard:
    - [ ] CPU usage
    - [ ] Memory usage
    - [ ] Disk I/O
    - [ ] Network throughput
  - [ ] Export dashboard JSON for version control
  - [ ] Document dashboard usage

- [ ] **Set Up Alerting Rules**
  - [ ] Configure Alertmanager
  - [ ] Define alert rules:
    - [ ] High error rate (>5% for 5 minutes)
    - [ ] Slow response times (p99 >2s for 5 minutes)
    - [ ] Service down (no heartbeat for 1 minute)
    - [ ] High memory usage (>90% for 10 minutes)
    - [ ] Disk space low (<10% remaining)
  - [ ] Configure notification channels (email, Slack, PagerDuty)
  - [ ] Test alert firing and resolution
  - [ ] Document on-call procedures

### 🟡 HIGH - Log Aggregation (2 hours)

- [ ] **Configure Centralized Logging**
  - [ ] Choose logging solution (ELK Stack, Loki, or Cloud provider)
  - [ ] Set up log shipping from application
  - [ ] Configure structured logging in application:
    - [ ] Use `structlog` for Python backend
    - [ ] Include correlation IDs
    - [ ] Include user context (sanitized)
    - [ ] Include request/response metadata
  - [ ] Create log retention policies
  - [ ] Set up log queries and saved searches:
    - [ ] Errors in last hour
    - [ ] Slow queries
    - [ ] Failed video processing
    - [ ] Authentication failures
  - [ ] Test log searching and filtering
  - [ ] Document logging best practices

### 🟢 MEDIUM - CI/CD Pipeline (2 hours)

- [ ] **Validate GitHub Actions Workflows**
  - [ ] Review `.github/workflows/ci.yml`:
    - [ ] Runs on all PRs
    - [ ] Executes linting (ruff, black, mypy)
    - [ ] Runs full test suite
    - [ ] Checks test coverage (>60% target)
    - [ ] Builds Docker images
  - [ ] Review `.github/workflows/deploy.yml`:
    - [ ] Triggers on main branch merge
    - [ ] Builds production images
    - [ ] Runs smoke tests
    - [ ] Deploys to staging first
    - [ ] Manual approval for production
  - [ ] Add workflow status badges to README
  - [ ] Test workflows on a feature branch
  - [ ] Document CI/CD process

- [ ] **Create Deployment Pipeline**
  - [ ] Set up staging environment:
    - [ ] Configure staging infrastructure
    - [ ] Deploy application to staging
    - [ ] Set up staging database
    - [ ] Configure staging secrets
  - [ ] Create deployment scripts:
    - [ ] `scripts/deploy_staging.sh`
    - [ ] `scripts/deploy_production.sh`
    - [ ] Include health checks
    - [ ] Include rollback procedures
  - [ ] Configure blue-green or canary deployment
  - [ ] Document deployment process
  - [ ] Create deployment runbook

---

## 🚀 Getting Started Prompt

```bash
# Step 1: Deploy monitoring stack
echo "📊 Phase 2: Starting Monitoring & CI/CD Setup"

# Step 2: Install Prometheus
# Using Docker Compose (recommended)
cat > docker-compose.monitoring.yml <<EOF
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infrastructure/grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=\${GRAFANA_PASSWORD}

volumes:
  prometheus_data:
  grafana_data:
EOF

# Step 3: Create Prometheus config
mkdir -p infrastructure/prometheus
cat > infrastructure/prometheus/prometheus.yml <<EOF
name: "Phase 2: Monitoring & CI/CD Setup"
about: Deploy comprehensive monitoring, logging, and continuous deployment infrastructure
title: "[PHASE 2] Monitoring & CI/CD Setup"
labels: ["phase-2", "monitoring", "cicd", "infrastructure"]
assignees: []
---

# Phase 2: Monitoring & CI/CD Setup

**Estimated Time:** 8 hours  
**Priority:** HIGH  
**Dependencies:** Phase 1 (Security & Environment Setup)

## 🎯 Objective

Establish production-grade monitoring, logging, alerting, and continuous deployment infrastructure to ensure system reliability and rapid deployment capabilities.

## 📋 Task Checklist

### 1. Prometheus Metrics Setup (1.5 hours)
- [ ] Install and configure Prometheus server
- [ ] Implement custom metrics in backend services
- [ ] Set up service discovery for dynamic targets
- [ ] Configure metric retention policies
- [ ] Create basic recording rules
- [ ] Test metrics collection and storage
- [ ] Document metrics naming conventions

### 2. Grafana Dashboard Configuration (1.5 hours)
- [ ] Deploy Grafana instance
- [ ] Connect Grafana to Prometheus data source
- [ ] Create system health dashboard
- [ ] Build API performance dashboard
- [ ] Design user activity dashboard
- [ ] Set up video processing metrics dashboard
- [ ] Configure dashboard auto-refresh and time ranges
- [ ] Export and version control dashboards

### 3. Centralized Logging Setup (2 hours)
- [ ] Choose logging solution (ELK Stack / Loki / CloudWatch)
- [ ] Deploy logging infrastructure
- [ ] Configure application log forwarding
- [ ] Set up log aggregation and indexing
- [ ] Create log retention policies
- [ ] Implement structured logging format
- [ ] Build log query and search interface
- [ ] Test log collection from all services

### 4. Alerting Rules Configuration (1.5 hours)
- [ ] Define alert severity levels (critical, warning, info)
- [ ] Create CPU/memory usage alerts
- [ ] Set up API error rate alerts
- [ ] Configure disk space monitoring alerts
- [ ] Implement database connection alerts
- [ ] Set up SSL certificate expiration alerts
- [ ] Configure alert notification channels (email, Slack, PagerDuty)
- [ ] Test alert firing and notifications

### 5. GitHub Actions CI/CD Pipeline (1.5 hours)
- [ ] Create deployment workflow for staging environment
- [ ] Set up production deployment workflow
- [ ] Implement automated testing in pipeline
- [ ] Configure build artifact storage
- [ ] Set up deployment approval gates
- [ ] Implement rollback procedures
- [ ] Add deployment status notifications
- [ ] Test full deployment cycle

## 🚀 Getting Started

Run these commands to begin Phase 2:

```bash
cd /home/runner/work/EventRelay/EventRelay

# 1. Check if monitoring infrastructure exists
ls -la monitoring/ infrastructure/ || echo "Create monitoring directory"

# 2. Review existing metrics
grep -r "metrics\|prometheus\|histogram\|counter" backend/ || echo "No metrics found"

# 3. Check logging setup
grep -r "logger\|logging.getLogger" backend/ frontend/ | wc -l

# 4. Review GitHub Actions workflows
ls -la .github/workflows/
cat .github/workflows/*.yml 2>/dev/null || echo "No workflows found"

# 5. Check deployment scripts
ls -la scripts/*deploy* scripts/*production* 2>/dev/null || echo "No deployment scripts"
```

## 📦 Infrastructure Setup

### Prometheus Configuration (prometheus.yml)
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'eventrelay-api'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
EOF

# Step 4: Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Step 5: Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Step 6: Access Grafana
echo "📊 Grafana available at: http://localhost:3001"
echo "   Default login: admin / \${GRAFANA_PASSWORD}"
```

---

## 🧪 Testing & Validation

### Before Marking Complete:

1. **Monitoring Validation**
   ```bash
   # Verify Prometheus is collecting metrics
   curl http://localhost:9090/api/v1/query?query=up
   
   # Check application metrics are available
   curl http://localhost:8000/metrics | grep http_requests_total
   
   # Verify Grafana dashboards load
   curl -u admin:password http://localhost:3001/api/dashboards/home
   ```

2. **Alerting Validation**
   ```bash
   # Trigger test alert (stop application)
   docker stop eventrelay-api
   
   # Wait for alert to fire (check Alertmanager UI)
   # Alert should appear within configured time
   
   # Restart application
   docker start eventrelay-api
   
   # Verify alert resolves
   ```

3. **CI/CD Validation**
   ```bash
   # Create test feature branch
   git checkout -b test/ci-cd-validation
   
   # Make trivial change and push
   echo "# CI/CD test" >> README.md
   git add README.md
   git commit -m "test: CI/CD validation"
   git push origin test/ci-cd-validation
   
   # Create PR and verify workflows run
   gh pr create --title "Test: CI/CD validation" --body "Testing CI/CD pipelines"
   
   # Check workflow status
   gh run list --branch test/ci-cd-validation
   ```

4. **Logging Validation**
   ```bash
   # Generate test logs
   curl -X POST http://localhost:8000/api/v1/process-video \
     -H "Content-Type: application/json" \
     -d '{"video_url": "https://www.youtube.com/watch?v=test"}'
   
   # Verify logs are centralized
   # (Command depends on chosen logging solution)
   ```

---

## 📊 Success Criteria

- [ ] Prometheus collecting metrics from application
- [ ] Grafana dashboards displaying real-time data
- [ ] At least 3 alert rules configured and tested
- [ ] Alerts firing and resolving correctly
- [ ] Logs centralized and searchable
- [ ] CI/CD workflows passing on test branch
- [ ] Staging environment deployed and accessible
- [ ] Deployment scripts tested and documented
- [ ] All monitoring endpoints responding

---

## 📚 References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Prometheus Integration](https://github.com/trallnag/prometheus-fastapi-instrumentator)
- Repository: `docs/status/EXECUTIVE_SUMMARY.md` - Phase 2 details

---

## 🔗 Related Issues

- Depends on: Phase 1 - Security & Environment Setup (must be complete)
- Blocks: Phase 3 - Testing & Launch
- Related: Production deployment infrastructure

---

## 💬 Notes

**IMPORTANT:** Before starting this phase:
1. Verify Phase 1 is complete (all security checks passing)
2. Ensure production environment variables are configured
3. Have access to cloud infrastructure (for deployment)

**Recommended Tools:**
- Monitoring: Prometheus + Grafana (open source, battle-tested)
- Logging: Grafana Loki (integrates well with Prometheus)
- CI/CD: GitHub Actions (already configured)
- Deployment: Docker + Fly.io or similar PaaS

**Time-Saving Tips:**
- Use infrastructure-as-code (Terraform) for monitoring stack
- Import pre-built Grafana dashboards from grafana.com
- Use GitHub Actions marketplace for common CI/CD tasks
  - job_name: 'eventrelay-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    
  - job_name: 'eventrelay-agents'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8002']
```

### Grafana Dashboard Setup
```bash
# Install Grafana
docker run -d -p 3000:3000 --name=grafana grafana/grafana

# Add Prometheus data source
# Create dashboards: System Health, API Performance, Agent Activity
```

### Logging Infrastructure
```bash
# Option 1: Loki + Promtail (lightweight)
docker-compose -f docker-compose.logging.yml up -d

# Option 2: ELK Stack (full-featured)
docker-compose -f docker-compose.elk.yml up -d
```

## 🧪 Testing & Validation

### Metrics Validation
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=up'

# Test custom metrics
curl http://localhost:8000/metrics | grep eventrelay_
```

### Logging Validation
```bash
# Generate test logs
python scripts/test_logging.py

# Query logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="eventrelay"}' | jq

# Check log volume
du -sh /var/log/eventrelay/
```

### Alerting Validation
```bash
# Trigger test alert
curl -X POST http://localhost:9090/api/v1/alerts

# Check alert manager
curl http://localhost:9093/api/v2/alerts | jq
```

### CI/CD Validation
```bash
# Trigger workflow locally with act
act -j deploy-staging --secret-file .env.github

# Validate GitHub Actions
gh workflow list
gh workflow run deploy-staging.yml
gh run watch
```

## 🎯 Monitoring Dashboards

### System Health Dashboard
- CPU usage (per service)
- Memory usage (per service)
- Disk I/O
- Network throughput
- Container status
- Database connections

### API Performance Dashboard
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Endpoint latency breakdown
- Cache hit rate
- Queue depth

### Video Processing Dashboard
- Videos processed per hour
- Processing success rate
- Average processing time
- Queue length
- Agent activity status
- AI API usage and costs

### User Activity Dashboard
- Active users
- Video views
- Agent invocations
- Feature usage metrics
- User session duration

## ✅ Success Criteria

- [ ] Prometheus collecting metrics from all services
- [ ] Grafana dashboards displaying real-time data
- [ ] Centralized logging operational with searchable interface
- [ ] Alert rules configured and tested
- [ ] Notification channels working (email/Slack/PagerDuty)
- [ ] CI/CD pipeline deploying to staging successfully
- [ ] Production deployment workflow approved and documented
- [ ] Rollback procedure tested and verified
- [ ] All monitoring documentation complete

## 📊 Key Metrics to Track

### Performance Metrics
- API response time < 200ms (p95)
- Video processing time < 60s (average)
- Database query time < 100ms (p95)
- Cache hit rate > 80%

### Reliability Metrics
- Uptime > 99.9%
- Error rate < 0.1%
- Alert response time < 5 minutes
- Deployment frequency > 1/day

### Resource Metrics
- CPU usage < 70% (average)
- Memory usage < 80%
- Disk usage < 80%
- Network saturation < 70%

## 📚 References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [The Twelve-Factor App - Logs](https://12factor.net/logs)
- Project Monitoring Guide: `docs/deployment/MONITORING_GUIDE.md`
- CI/CD Setup: `docs/deployment/CICD_SETUP.md`

## 🔗 Related Phases

**Previous Phase:**
- Phase 1: Security & Environment Setup (#TBD)

**Next Phase:**
- Phase 3: Testing & Production Launch (#TBD)

---

**Phase 2 Start Date:** [To be filled]  
**Phase 2 Completion Date:** [To be filled]  
**Phase Lead:** [To be assigned]
