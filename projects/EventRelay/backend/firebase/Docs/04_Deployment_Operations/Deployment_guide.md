# Deployment Guide

## Overview
This guide provides comprehensive procedures for deploying the application across different environments, including development, staging, and production.

## Environment Overview

### Development Environment
- **Purpose**: Local development and testing
- **URL**: http://localhost:3000
- **Database**: Local SQLite/PostgreSQL
- **Features**: Hot reload, debug logging, mock data

### Staging Environment
- **Purpose**: Pre-production testing and validation
- **URL**: https://staging.yourapp.com
- **Database**: Staging database (separate from production)
- **Features**: Production-like setup, real data subsets

### Production Environment
- **Purpose**: Live application serving users
- **URL**: https://yourapp.com
- **Database**: Production database with backups
- **Features**: Optimized performance, monitoring, high availability

## Prerequisites

### System Requirements
- **Node.js**: v18.0.0 or higher
- **npm/yarn**: Latest stable version
- **Docker**: v20.10.0 or higher (for containerized deployment)
- **Git**: v2.30.0 or higher

### Required Accounts and Access
- AWS/GCP/Azure account with deployment permissions
- Database access credentials
- CDN configuration access
- SSL certificate management
- Monitoring service accounts (DataDog, New Relic, etc.)

## Environment Setup

### 1. Local Development Setup

#### Clone Repository
```bash
git clone https://github.com/your-org/your-app.git
cd your-app
```

#### Install Dependencies
```bash
# Using npm
npm install

# Or using yarn
yarn install
```

#### Environment Configuration
Create `.env.local` file:
```bash
# Database
DATABASE_URL="postgresql://localhost:5432/yourapp_dev"

# Authentication
JWT_SECRET="your-jwt-secret-key"
JWT_EXPIRES_IN="2h"

# External Services
REDIS_URL="redis://localhost:6379"
SMTP_HOST="localhost"
SMTP_PORT="1025"

# Feature Flags
ENABLE_DEBUG_LOGGING="true"
ENABLE_MOCK_DATA="true"
```

#### Database Setup
```bash
# Create database
createdb yourapp_dev

# Run migrations
npm run db:migrate

# Seed development data
npm run db:seed
```

#### Start Development Server
```bash
# Start with hot reload
npm run dev

# Or with debugger
npm run dev:debug
```

### 2. Staging Environment Setup

#### Infrastructure Requirements
- **EC2 Instance**: t3.medium or equivalent
- **RDS Database**: PostgreSQL 15
- **Redis**: ElastiCache cluster
- **Load Balancer**: ALB with SSL termination
- **CDN**: CloudFront distribution

#### Deployment Configuration
```bash
# .env.staging
NODE_ENV="staging"
DATABASE_URL="postgresql://staging-db:5432/yourapp"
REDIS_URL="redis://staging-redis:6379"
AWS_REGION="us-east-1"
S3_BUCKET="yourapp-staging-assets"
```

#### SSL Certificate Setup
```bash
# Using AWS Certificate Manager
aws acm request-certificate \
  --domain-name staging.yourapp.com \
  --validation-method DNS
```

### 3. Production Environment Setup

#### Infrastructure Requirements
- **ECS Cluster**: Multi-AZ deployment
- **RDS Aurora**: PostgreSQL with read replicas
- **Redis Cluster**: Multi-node cluster
- **Application Load Balancer**: With auto-scaling
- **CloudFront**: Global CDN
- **WAF**: Web Application Firewall
- **Backup**: Automated daily backups

#### Security Configuration
```bash
# .env.production
NODE_ENV="production"
DATABASE_URL="postgresql://prod-db:5432/yourapp"
REDIS_URL="redis://prod-redis:6379"
ENCRYPTION_KEY="your-256-bit-key"
AWS_REGION="us-east-1"
S3_BUCKET="yourapp-production-assets"

# Security
FORCE_HTTPS="true"
SECURE_COOKIES="true"
CORS_ORIGIN="https://yourapp.com"
```

## Deployment Procedures

### Automated Deployment (Recommended)

#### Using GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build application
        run: npm run build

      - name: Deploy to staging
        if: github.ref == 'refs/heads/develop'
        run: npm run deploy:staging

      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: npm run deploy:production
```

#### Using AWS CodePipeline
```yaml
# buildspec.yml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18

  pre_build:
    commands:
      - npm ci

  build:
    commands:
      - npm test
      - npm run build

  post_build:
    commands:
      - npm run deploy
```

### Manual Deployment

#### 1. Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations prepared
- [ ] Rollback plan documented
- [ ] Stakeholder notification sent
- [ ] Maintenance window scheduled (if needed)

#### 2. Deployment Steps
```bash
# 1. Create deployment branch
git checkout -b deployment/2025-01-20

# 2. Run full test suite
npm test

# 3. Build production assets
npm run build

# 4. Run database migrations
npm run db:migrate

# 5. Deploy application
npm run deploy:production

# 6. Verify deployment
curl -I https://yourapp.com/health

# 7. Monitor for errors
tail -f /var/log/application.log
```

#### 3. Post-Deployment Verification
```bash
# Health check
curl https://yourapp.com/api/health

# Database connectivity
npm run db:check

# Key functionality tests
npm run test:e2e

# Performance check
npm run perf:test
```

## Rollback Procedures

### Automated Rollback
```bash
# Quick rollback to previous version
npm run rollback

# Or specify version
npm run rollback -- --version v1.2.3
```

### Manual Rollback Steps
```bash
# 1. Stop new deployment
kubectl scale deployment your-app --replicas=0

# 2. Restore previous version
kubectl set image deployment/your-app app=your-app:v1.2.3

# 3. Scale up previous version
kubectl scale deployment your-app --replicas=3

# 4. Verify rollback success
curl https://yourapp.com/api/health
```

### Rollback Triggers
- Error rate > 5% for 5 minutes
- Response time > 5 seconds for 3 minutes
- Manual intervention required
- Security vulnerability discovered

## Monitoring and Alerting

### Application Monitoring
```yaml
# Prometheus metrics
metrics:
  - name: http_requests_total
    type: counter
    help: Total number of HTTP requests

  - name: http_request_duration_seconds
    type: histogram
    help: HTTP request duration in seconds

  - name: database_connections_active
    type: gauge
    help: Number of active database connections
```

### Alert Rules
```yaml
# Alert when error rate is high
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: High error rate detected

# Alert when response time is slow
- alert: SlowResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: Slow response time detected
```

### Log Aggregation
```bash
# Using ELK Stack
# 1. Application logs → Filebeat
# 2. Filebeat → Logstash
# 3. Logstash → Elasticsearch
# 4. Kibana for visualization

# Or using CloudWatch Logs
aws logs create-log-group --log-group-name /your-app/production
```

## Backup and Recovery

### Database Backups
```bash
# Automated daily backups
0 2 * * * /usr/local/bin/pg_dump yourapp > /backups/daily_$(date +\%Y\%m\%d).sql

# Point-in-time recovery
pg_restore -d yourapp /backups/daily_20250120.sql
```

### Application Backups
```bash
# Configuration backup
tar -czf /backups/config_$(date +\%Y\%m\%d).tar.gz /etc/your-app/

# User uploads backup
aws s3 sync s3://yourapp-uploads/ s3://yourapp-backups/$(date +\%Y\%m\%d)/
```

### Disaster Recovery
```yaml
# Recovery Time Objective (RTO): 4 hours
# Recovery Point Objective (RPO): 1 hour

recovery_procedures:
  - infrastructure_recreation
  - database_restore
  - application_redeployment
  - data_validation
  - service_verification
```

## Performance Optimization

### Application Performance
```javascript
// Enable gzip compression
app.use(compression());

// Cache static assets
app.use(express.static('public', { maxAge: '1y' }));

// Database query optimization
const users = await User.findAll({
  attributes: ['id', 'name', 'email'],
  limit: 100,
  offset: 0
});
```

### Infrastructure Optimization
```yaml
# Auto-scaling configuration
autoScaling:
  minCapacity: 2
  maxCapacity: 10
  targetCPUUtilization: 70
  targetMemoryUtilization: 80

# CDN configuration
cdn:
  priceClass: PriceClass_100
  compress: true
  defaultTTL: 86400
```

## Security Checklist

### Pre-Deployment
- [ ] Security scan completed (npm audit, Snyk)
- [ ] Secrets properly configured (no hardcoded values)
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation in place

### Production Security
- [ ] Web Application Firewall (WAF) enabled
- [ ] SSL/TLS certificates valid
- [ ] Security headers configured
- [ ] Database encrypted
- [ ] Access logs enabled
- [ ] Intrusion detection active

## Troubleshooting

### Common Deployment Issues

#### Application Won't Start
```bash
# Check logs
tail -f /var/log/your-app/application.log

# Check environment variables
env | grep -E "(DATABASE|REDIS|JWT)"

# Check port availability
netstat -tlnp | grep :3000
```

#### Database Connection Issues
```bash
# Test database connectivity
psql -h localhost -U yourapp -d yourapp

# Check connection pool
npm run db:pool-status

# Verify credentials
cat .env | grep DATABASE_URL
```

#### High Memory Usage
```bash
# Check memory usage
top -p $(pgrep -f "node.*your-app")

# Check for memory leaks
npm run mem:profile

# Restart with increased memory
NODE_OPTIONS="--max-old-space-size=4096" npm start
```

### Emergency Contacts
- **DevOps Lead**: devops@yourapp.com | +1-555-0123
- **Database Admin**: dba@yourapp.com | +1-555-0124
- **Security Team**: security@yourapp.com | +1-555-0125
- **Infrastructure Provider**: support@cloudprovider.com

## Maintenance Schedule

### Daily Tasks
- [ ] Monitor error rates and performance metrics
- [ ] Review application and system logs
- [ ] Check disk space and resource utilization
- [ ] Verify backup completion

### Weekly Tasks
- [ ] Security updates and patch management
- [ ] Database maintenance and optimization
- [ ] Log rotation and archival
- [ ] Performance trend analysis

### Monthly Tasks
- [ ] Full security audit
- [ ] Disaster recovery testing
- [ ] Capacity planning review
- [ ] Dependency updates

---

*This deployment guide should be reviewed and updated quarterly or after significant infrastructure changes. Last updated: 2025-01-20*
