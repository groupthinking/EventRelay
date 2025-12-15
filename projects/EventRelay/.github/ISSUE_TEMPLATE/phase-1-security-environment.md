---
name: Phase 1 - Security & Environment Setup
about: Production preparation Phase 1 - Security hardening and environment configuration
title: '[Phase 1] Security & Environment Setup'
labels: ['production', 'security', 'phase-1', 'high-priority']
assignees: ''
---

# 🔒 Phase 1: Security & Environment Setup

**Estimated Time:** 8 hours  
**Priority:** HIGH (blocking production)  
**Dependencies:** None (can start immediately)

## 📋 Overview

This phase focuses on securing the application and setting up proper environment configurations for production deployment. Critical security vulnerabilities must be addressed before proceeding to subsequent phases.

---

## ✅ Tasks Checklist

### 🔴 CRITICAL - Security (4 hours)

- [ ] **Rotate Google OAuth Credentials**
  - [ ] Access Google Cloud Console
  - [ ] Navigate to APIs & Services > Credentials
  - [ ] Delete exposed OAuth client: `833571612383-*`
  - [ ] Create new OAuth 2.0 Client ID
  - [ ] Download new credentials JSON
  - [ ] Update application configuration
  - [ ] Test authentication flow
  - [ ] Verify old credentials no longer work

- [ ] **Audit for Additional Secrets**
  - [ ] Run secret scanning tools (e.g., `gitleaks`, `trufflehog`)
  - [ ] Check `.env.example` vs actual `.env` files
  - [ ] Review git history for exposed secrets
  - [ ] Verify `.gitignore` is comprehensive
  - [ ] Document all API keys and their purposes

- [ ] **Set Up Secrets Manager**
  - [ ] Choose secrets management solution (AWS Secrets Manager, HashiCorp Vault, or Google Secret Manager)
  - [ ] Install and configure secrets manager client
  - [ ] Migrate all secrets from environment variables
  - [ ] Update application to fetch secrets from manager
  - [ ] Test secret rotation functionality
  - [ ] Document secrets manager usage

### 🟡 HIGH - Environment Configuration (2 hours)

- [ ] **Create Production Environment Files**
  - [ ] Copy `.env.example` to `.env.production`
  - [ ] Populate all required production values:
    - [ ] `YOUTUBE_API_KEY` (production quota)
    - [ ] `GEMINI_API_KEY` (production key)
    - [ ] `OPENAI_API_KEY` (if used)
    - [ ] `GOOGLE_SPEECH_PROJECT_ID`
    - [ ] `GOOGLE_SPEECH_LOCATION`
    - [ ] `GOOGLE_SPEECH_RECOGNIZER`
    - [ ] `GOOGLE_SPEECH_GCS_BUCKET`
    - [ ] Database connection strings
    - [ ] Redis URL (if applicable)
  - [ ] Validate all environment variables
  - [ ] Create `.env.staging` for staging environment
  - [ ] Document environment-specific configurations

- [ ] **Configure Security Headers**
  - [ ] Enable HTTPS/TLS in production
  - [ ] Add security headers to API responses:
    - [ ] `Strict-Transport-Security`
    - [ ] `X-Content-Type-Options: nosniff`
    - [ ] `X-Frame-Options: DENY`
    - [ ] `X-XSS-Protection: 1; mode=block`
    - [ ] `Content-Security-Policy`
  - [ ] Test header configuration
  - [ ] Document security policy

### 🟢 MEDIUM - Rate Limiting & Protection (2 hours)

- [ ] **Implement Rate Limiting**
  - [ ] Choose rate limiting strategy (Redis-based recommended)
  - [ ] Configure rate limits per endpoint:
    - [ ] `/api/v1/transcript-action` - 10 req/min per IP
    - [ ] `/api/v1/process-video` - 5 req/min per IP
    - [ ] `/api/v1/cloud-ai/*` - 20 req/min per IP
  - [ ] Add rate limit headers to responses
  - [ ] Test rate limiting behavior
  - [ ] Document rate limits in API docs

- [ ] **Enable CORS Properly**
  - [ ] Configure allowed origins for production
  - [ ] Set up credentials handling
  - [ ] Test cross-origin requests
  - [ ] Document CORS policy

---

## 🚀 Getting Started Prompt

```bash
# Step 1: Start with critical security fixes
echo "🔒 Phase 1: Starting Security & Environment Setup"

# Step 2: Rotate OAuth credentials first
echo "📝 Action Required: Go to Google Cloud Console"
echo "   1. Navigate to: https://console.cloud.google.com/apis/credentials"
echo "   2. Delete exposed client: 833571612383-*"
echo "   3. Create new OAuth 2.0 Client ID"
echo "   4. Download credentials and save securely"

# Step 3: Audit for secrets
echo "🔍 Scanning repository for secrets..."
# Install gitleaks if not available
# brew install gitleaks  # macOS
# or download from: https://github.com/gitleaks/gitleaks/releases

gitleaks detect --source . --verbose --no-git

# Step 4: Set up environment files
cp .env.example .env.production
echo "📝 Action Required: Edit .env.production with production values"

# Step 5: Test configuration
python scripts/check_credentials.py --env production
```

---

## 🧪 Testing & Validation

### Before Marking Complete:

1. **Security Validation**
   ```bash
   # Verify no secrets in repository
   gitleaks detect --source . --no-git
   
   # Verify new OAuth credentials work
   python -c "from src.youtube_extension.backend.config.production_config import get_config; print(get_config().validate_configuration())"
   ```

2. **Environment Validation**
   ```bash
   # Test production environment loads
   export ENV=production
   python -c "from src.youtube_extension.backend.config.production_config import get_config; cfg = get_config(); print('✅ Production config valid' if cfg.has_gemini_key and cfg.has_youtube_key else '❌ Missing keys')"
   ```

3. **Rate Limiting Test**
   ```bash
   # Test rate limiting is active
   for i in {1..15}; do curl -I http://localhost:8000/api/v1/health; done
   # Should see 429 Too Many Requests after threshold
   ```

---

## 📊 Success Criteria

- [ ] All exposed secrets rotated
- [ ] No secrets found in repository scan
- [ ] Secrets manager operational
- [ ] Production `.env` file complete and validated
- [ ] Security headers active in responses
- [ ] Rate limiting functional on all endpoints
- [ ] CORS configured for production domains
- [ ] All tests in this phase pass

---
name: "Phase 1: Security & Environment Setup"
about: Complete security audit, credential rotation, and production environment setup
title: "[PHASE 1] Security & Environment Setup"
labels: ["phase-1", "security", "environment", "production"]
assignees: []
---

# Phase 1: Security & Environment Setup

**Estimated Time:** 8 hours  
**Priority:** CRITICAL  
**Dependencies:** None (starting phase)

## 🎯 Objective

Establish secure production environment with proper credential management, environment configuration, and security hardening measures.

## 📋 Task Checklist

### 1. OAuth Credential Rotation (2 hours)
- [ ] Audit all OAuth credentials in repository history
- [ ] Generate new OAuth 2.0 credentials in Google Cloud Console
- [ ] Remove old credentials from all environments
- [ ] Update `.env.production` with new credentials
- [ ] Verify no hardcoded secrets in codebase
- [ ] Test OAuth flow with new credentials
- [ ] Document credential rotation procedure

### 2. Secrets Management Setup (1.5 hours)
- [ ] Choose secrets management solution (AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager)
- [ ] Set up secrets manager infrastructure
- [ ] Migrate all secrets to secrets manager
- [ ] Configure application to read from secrets manager
- [ ] Update deployment scripts to use secrets manager
- [ ] Test secret rotation procedures
- [ ] Document secrets management workflow

### 3. Production Environment Configuration (2 hours)
- [ ] Create `.env.production.template` file
- [ ] Set up production database configuration
- [ ] Configure Redis for caching (if applicable)
- [ ] Set up production API endpoints and URLs
- [ ] Configure CORS policies for production domains
- [ ] Set up environment-specific feature flags
- [ ] Validate all environment variables are documented

### 4. Security Headers Implementation (1.5 hours)
- [ ] Implement Content Security Policy (CSP)
- [ ] Add X-Frame-Options header
- [ ] Configure X-Content-Type-Options
- [ ] Set up Strict-Transport-Security (HSTS)
- [ ] Implement X-XSS-Protection
- [ ] Add Referrer-Policy header
- [ ] Test security headers with security scanner

### 5. Rate Limiting Configuration (1 hour)
- [ ] Implement rate limiting middleware
- [ ] Configure rate limits per endpoint
- [ ] Set up rate limit storage (Redis recommended)
- [ ] Add rate limit headers to responses
- [ ] Test rate limiting behavior
- [ ] Document rate limit policies
- [ ] Create rate limit bypass mechanism for internal services

## 🚀 Getting Started

Run these commands to begin Phase 1:

```bash
# 1. Audit existing secrets
cd /home/runner/work/EventRelay/EventRelay
git log --all --full-history --source -- "*secret*" "*credential*" "*.env" | head -50

# 2. Check for hardcoded secrets
grep -r "AIza" . --exclude-dir={node_modules,.git,dist} || echo "No API keys found"
grep -r "sk-" . --exclude-dir={node_modules,.git,dist} || echo "No OpenAI keys found"

# 3. Review current environment setup
cat .env.example
ls -la .env* 2>/dev/null || echo "No env files found"

# 4. Check security headers implementation
grep -r "helmet\|CSP\|X-Frame-Options" backend/ frontend/ || echo "No security headers found"

# 5. Check rate limiting
grep -r "rate.limit\|throttle" backend/ || echo "No rate limiting found"
```

## 🧪 Testing & Validation

### Security Validation
```bash
# Test OAuth flow
python -c "from backend.services.auth import verify_oauth; print(verify_oauth())"

# Scan for secrets
pip install detect-secrets
detect-secrets scan --all-files

# Check security headers
curl -I https://your-production-url.com | grep -E "X-|Content-Security"
```

### Environment Validation
```bash
# Validate production environment
python scripts/validate_environment.py --env production

# Test secrets manager access
python scripts/test_secrets_access.py
```

## ✅ Success Criteria

- [ ] All OAuth credentials rotated and tested
- [ ] Zero secrets in codebase or git history
- [ ] Secrets manager fully operational
- [ ] Production environment fully configured
- [ ] All security headers implemented and tested
- [ ] Rate limiting active on all API endpoints
- [ ] Security scan shows zero critical vulnerabilities
- [ ] Documentation complete and up-to-date

## 📚 References

- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [Google OAuth 2.0 Setup](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- Repository: `docs/status/EXECUTIVE_SUMMARY.md` - Phase 1 details
- Repository: `SECURITY.md` - Security policies

---

## 🔗 Related Issues

- Depends on: None (first phase)
- Blocks: Phase 2 - Monitoring & CI/CD
- Blocks: Phase 3 - Testing & Launch

---

## 💬 Notes

**IMPORTANT:** Do not proceed to Phase 2 until:
1. OAuth credentials are rotated
2. Secrets manager is operational
3. All security validations pass

This phase is BLOCKING for production deployment. Security cannot be compromised.
- [OAuth 2.0 Best Practices](https://tools.ietf.org/html/rfc6749)
- [Rate Limiting Strategies](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- Project Security Documentation: `docs/SECURITY.md`
- Environment Setup Guide: `docs/deployment/ENVIRONMENT_SETUP.md`

## 🔗 Next Phase

After completing Phase 1, proceed to:
- **Phase 2: Monitoring & CI/CD Setup** (#TBD)

---

**Phase 1 Start Date:** [To be filled]  
**Phase 1 Completion Date:** [To be filled]  
**Phase Lead:** [To be assigned]
