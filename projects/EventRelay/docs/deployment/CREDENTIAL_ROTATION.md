# Credential Rotation Procedures

This document outlines the procedures for rotating all credentials used in EventRelay production environments.

## 🔐 Overview

**Credential rotation frequency:**
- OAuth credentials: Every 90 days
- API keys: Every 180 days
- Database passwords: Every 180 days
- JWT secrets: Every 365 days
- Session secrets: Every 365 days

**Last rotation:** [Date to be filled]
**Next scheduled rotation:** [Date to be filled]

## 📋 Pre-Rotation Checklist

Before rotating any credentials:

- [ ] Schedule maintenance window (if applicable)
- [ ] Notify team members
- [ ] Backup current credentials securely
- [ ] Test rotation procedure in staging
- [ ] Prepare rollback plan
- [ ] Document current state

## 1. Google OAuth Credentials Rotation

**Frequency:** Every 90 days
**Priority:** CRITICAL
**Downtime:** ~5 minutes

### Step 1: Generate New Credentials

1. Log in to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to: APIs & Services → Credentials
3. Select your OAuth 2.0 Client ID
4. Click "Create OAuth client ID" for new credentials OR click existing and regenerate
5. Download the new client secret JSON

### Step 2: Update Secrets Manager

```bash
# Using AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/google-oauth-client-id \
  --secret-string "NEW_CLIENT_ID"

aws secretsmanager update-secret \
  --secret-id prod/eventrelay/google-oauth-client-secret \
  --secret-string "NEW_CLIENT_SECRET"

# Or using HashiCorp Vault
vault kv put secret/prod/eventrelay/oauth \
  google_client_id="NEW_CLIENT_ID" \
  google_client_secret="NEW_CLIENT_SECRET"
```

### Step 3: Update Application Configuration

```bash
# Option A: Update environment variables (Kubernetes)
kubectl set env deployment/eventrelay \
  GOOGLE_CLIENT_ID="NEW_CLIENT_ID" \
  GOOGLE_CLIENT_SECRET="NEW_CLIENT_SECRET" \
  -n production

# Option B: Update .env.production (if not using secrets manager)
# DO NOT COMMIT THIS FILE
nano /opt/eventrelay/.env.production
# Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

### Step 4: Rolling Restart

```bash
# Kubernetes rolling restart
kubectl rollout restart deployment/eventrelay -n production
kubectl rollout status deployment/eventrelay -n production

# Or for Docker Compose
docker-compose restart eventrelay-api

# Or for systemd
sudo systemctl restart eventrelay-api
```

### Step 5: Verify OAuth Flow

```bash
# Test OAuth flow
curl -X GET https://api.yourdomain.com/auth/login
# Should redirect to Google OAuth consent screen

# Test callback
# Complete OAuth flow in browser and verify success
```

### Step 6: Revoke Old Credentials

1. Return to Google Cloud Console
2. Find the old OAuth client ID
3. Click "Delete" to revoke old credentials
4. Confirm revocation

**Wait 24 hours before deleting old credentials to ensure no issues.**

## 2. AI Service API Keys Rotation

**Frequency:** Every 180 days
**Priority:** HIGH
**Downtime:** ~2 minutes

### OpenAI API Key

```bash
# 1. Generate new key at https://platform.openai.com/api-keys

# 2. Update secrets manager
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/openai-api-key \
  --secret-string "sk-NEW_KEY_HERE"

# 3. Update environment and restart
kubectl set env deployment/eventrelay OPENAI_API_KEY="sk-NEW_KEY_HERE" -n production
kubectl rollout restart deployment/eventrelay -n production

# 4. Verify
curl -X POST https://api.yourdomain.com/api/v1/test-ai \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai"}'

# 5. Delete old key from OpenAI dashboard
```

### Anthropic Claude API Key

```bash
# 1. Generate new key at https://console.anthropic.com/

# 2. Update secrets manager
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/anthropic-api-key \
  --secret-string "sk-ant-NEW_KEY_HERE"

# 3. Update and restart
kubectl set env deployment/eventrelay ANTHROPIC_API_KEY="sk-ant-NEW_KEY_HERE" -n production
kubectl rollout restart deployment/eventrelay -n production
```

### Google Gemini API Key

```bash
# 1. Generate new key at https://makersuite.google.com/app/apikey

# 2. Update secrets manager
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/gemini-api-key \
  --secret-string "AIzaSy_NEW_KEY_HERE"

# 3. Update and restart
kubectl set env deployment/eventrelay GEMINI_API_KEY="AIzaSy_NEW_KEY_HERE" -n production
kubectl rollout restart deployment/eventrelay -n production
```

## 3. Database Credentials Rotation

**Frequency:** Every 180 days
**Priority:** HIGH
**Downtime:** ~10 minutes (with proper planning: 0 minutes)

### PostgreSQL Password Rotation (Zero-Downtime)

```bash
# 1. Create new user with same permissions
psql -h db.yourdomain.com -U postgres -d eventrelay_production

CREATE USER eventrelay_new WITH PASSWORD 'new_secure_password';
GRANT ALL PRIVILEGES ON DATABASE eventrelay_production TO eventrelay_new;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eventrelay_new;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eventrelay_new;

# 2. Update secrets manager with new credentials
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/db-password \
  --secret-string "new_secure_password"

# 3. Update DATABASE_URL
# New URL: postgresql://eventrelay_new:new_secure_password@host:5432/eventrelay_production

# 4. Rolling update (no downtime)
kubectl set env deployment/eventrelay \
  DATABASE_URL="postgresql://eventrelay_new:new_secure_password@host:5432/eventrelay_production" \
  -n production

kubectl rollout restart deployment/eventrelay -n production

# 5. Wait for all pods to be running with new credentials
kubectl rollout status deployment/eventrelay -n production

# 6. Verify connections
kubectl exec -it deployment/eventrelay -n production -- \
  python -c "from sqlalchemy import create_engine; engine = create_engine(os.environ['DATABASE_URL']); print(engine.connect())"

# 7. Drop old user (after 24 hours of monitoring)
psql -h db.yourdomain.com -U postgres -d eventrelay_production
DROP USER eventrelay_old;
```

## 4. Redis Password Rotation

**Frequency:** Every 180 days

```bash
# 1. Set new password in Redis
redis-cli -h redis.yourdomain.com -a old_password
CONFIG SET requirepass new_password
CONFIG REWRITE

# 2. Update secrets and restart application
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/redis-password \
  --secret-string "new_password"

kubectl set env deployment/eventrelay \
  REDIS_PASSWORD="new_password" \
  -n production
```

## 5. JWT Secret Rotation

**Frequency:** Every 365 days
**Note:** This will invalidate all active sessions

```bash
# 1. Generate new secret
NEW_JWT_SECRET=$(openssl rand -hex 32)

# 2. Update secrets manager
aws secretsmanager update-secret \
  --secret-id prod/eventrelay/jwt-secret \
  --secret-string "$NEW_JWT_SECRET"

# 3. Update and restart (users will need to re-login)
kubectl set env deployment/eventrelay JWT_SECRET_KEY="$NEW_JWT_SECRET" -n production
kubectl rollout restart deployment/eventrelay -n production

# 4. Notify users about session expiration
# Send email or display banner about re-authentication
```

## 6. Backup Credentials (AWS)

```bash
# Rotate AWS access keys
# 1. Create new access key in AWS IAM
# 2. Update application with new key
# 3. Test backups with new credentials
# 4. Delete old access key
```

## 🚨 Emergency Rotation Procedure

If credentials are compromised:

### Immediate Actions (< 5 minutes)

```bash
# 1. Revoke compromised credentials immediately
# Google OAuth: Delete client in Cloud Console
# API keys: Delete from provider dashboard

# 2. Generate and deploy new credentials
# Use expedited rotation procedure above

# 3. Restart all services
kubectl rollout restart deployment/eventrelay -n production

# 4. Check logs for unauthorized access
kubectl logs deployment/eventrelay -n production --since=24h | grep ERROR
```

### Post-Incident (< 1 hour)

```bash
# 1. Audit all API usage
# 2. Review access logs
# 3. Identify scope of compromise
# 4. Notify affected users if necessary
# 5. Update security policies
# 6. Document incident and response
```

## 📊 Rotation Tracking

| Credential Type | Last Rotated | Next Rotation | Rotation By | Notes |
|----------------|--------------|---------------|-------------|-------|
| Google OAuth | [Date] | [Date] | [Name] | |
| OpenAI API | [Date] | [Date] | [Name] | |
| Anthropic API | [Date] | [Date] | [Name] | |
| Gemini API | [Date] | [Date] | [Name] | |
| Database Password | [Date] | [Date] | [Name] | |
| Redis Password | [Date] | [Date] | [Name] | |
| JWT Secret | [Date] | [Date] | [Name] | |

## ✅ Post-Rotation Checklist

After rotating credentials:

- [ ] Update rotation tracking table
- [ ] Test all affected functionality
- [ ] Monitor error rates for 24 hours
- [ ] Document any issues encountered
- [ ] Update runbook if needed
- [ ] Notify team of completion
- [ ] Schedule next rotation

## 🔍 Verification Scripts

Save these scripts for quick verification:

```bash
#!/bin/bash
# verify-credentials.sh

echo "🔍 Verifying all credentials..."

# Test database connection
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()" && \
  echo "✅ Database connection successful" || echo "❌ Database connection failed"

# Test Redis connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping && \
  echo "✅ Redis connection successful" || echo "❌ Redis connection failed"

# Test OpenAI API
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | grep -q "model" && \
  echo "✅ OpenAI API key valid" || echo "❌ OpenAI API key invalid"

# Test OAuth
curl -s https://api.yourdomain.com/auth/login | grep -q "google" && \
  echo "✅ OAuth endpoint accessible" || echo "❌ OAuth endpoint failed"

echo "🏁 Verification complete"
```

## 📚 References

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [OWASP Credential Management](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Storage_Cheat_Sheet.html)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

## 🆘 Support Contacts

**Emergency credential issues:**
- On-call engineer: [phone/pager]
- Security team: security@yourdomain.com
- Infrastructure team: infra@yourdomain.com

**Escalation path:**
1. On-call engineer
2. Engineering lead
3. CTO
4. CEO (if security incident)
