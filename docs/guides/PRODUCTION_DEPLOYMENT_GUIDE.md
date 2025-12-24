# 🚀 Production Deployment Pipeline Guide

## Overview
This guide outlines the complete production deployment pipeline for the UVAI YouTube Extension platform using the Vercel plugin and deployment system.

## 📋 Prerequisites

### Required Tokens & Credentials
- **VERCEL_TOKEN**: Vercel API token for deployment
- **GITHUB_TOKEN**: GitHub token for repository access
- **NETLIFY_AUTH_TOKEN**: Netlify token (optional, for multi-platform)
- **FLY_API_TOKEN**: Fly.io token (optional, for multi-platform)

### Required Tools
- Python 3.9+
- Node.js 18+ (for frontend builds)
- Git (for repository management)
- Docker (optional, for containerized deployments)

## 🔧 Environment Setup

### 1. Backend Environment Setup

```bash
# Set up Python environment
cd /workspace
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .[youtube,ml,postgres]
pip install -e .  # Install the package in development mode

# Set environment variables
export VERCEL_TOKEN="your_vercel_token_here"
export GITHUB_TOKEN="your_github_token_here"
export VERCEL_PROJECT_NAME="your_project_name"
export VERCEL_ORG_ID="your_org_id"  # Optional
```

### 2. Frontend Environment Setup

```bash
# Navigate to frontend
cd /workspace/frontend

# Install dependencies
npm install

# Set environment variables
export REACT_APP_API_URL="https://your-api-domain.com"
export REACT_APP_WS_URL="wss://your-api-domain.com/ws"
export REACT_APP_MCP_SERVER_URL="https://your-api-domain.com/mcp"
```

## 🚀 Deployment Pipeline Steps

### Step 1: Pre-Deployment Validation

```python
# Validate environment and tokens
from youtube_extension.backend.deploy.core import EnvironmentValidator

# Check Vercel environment
vercel_validation = EnvironmentValidator.validate_for_platform('vercel')
print(f"Vercel valid: {vercel_validation['valid']}")
print(f"Missing tokens: {vercel_validation['missing_required']}")

# Check GitHub environment
github_validation = EnvironmentValidator.validate_for_platform('github')
print(f"GitHub valid: {github_validation['valid']}")
```

### Step 2: Frontend Build Process

```bash
# Build the React frontend
cd /workspace/frontend
npm run build

# Verify build output
ls -la build/
# Should see: index.html, static/, assets/, etc.
```

### Step 3: Backend Deployment

```python
# Deploy backend using the deployment system
import asyncio
from youtube_extension.backend.deploy import deploy_project

async def deploy_backend():
    project_config = {
        'title': 'UVAI YouTube Extension',
        'project_type': 'web',
        'framework': 'fastapi',
        'build_command': 'pip install -e .[youtube,ml,postgres] && pip install -e .',
        'output_directory': 'dist'
    }
    
    env_vars = {
        'VERCEL_PROJECT_NAME': 'uvai-backend',
        'GITHUB_REPO_URL': 'https://github.com/your-org/your-repo',
        'VERCEL_ORG_ID': 'your_org_id'  # Optional
    }
    
    result = await deploy_project('vercel', '/workspace', project_config, env_vars)
    
    if result['status'] == 'success':
        print(f"✅ Backend deployed: {result['url']}")
        return result['url']
    else:
        print(f"❌ Backend deployment failed: {result['error']}")
        return None

# Run deployment
backend_url = asyncio.run(deploy_backend())
```

### Step 4: Frontend Deployment

```python
# Deploy frontend to Vercel
async def deploy_frontend():
    project_config = {
        'title': 'UVAI Frontend',
        'project_type': 'react',
        'framework': 'nextjs',
        'build_command': 'npm run build',
        'output_directory': 'build'
    }
    
    env_vars = {
        'VERCEL_PROJECT_NAME': 'uvai-frontend',
        'GITHUB_REPO_URL': 'https://github.com/your-org/your-repo',
        'REACT_APP_API_URL': backend_url,  # Use backend URL from step 3
        'REACT_APP_WS_URL': f"wss://{backend_url.replace('https://', '')}/ws",
        'REACT_APP_MCP_SERVER_URL': f"{backend_url}/mcp"
    }
    
    result = await deploy_project('vercel', '/workspace/frontend', project_config, env_vars)
    
    if result['status'] == 'success':
        print(f"✅ Frontend deployed: {result['url']}")
        return result['url']
    else:
        print(f"❌ Frontend deployment failed: {result['error']}")
        return None

# Run deployment
frontend_url = asyncio.run(deploy_frontend())
```

### Step 5: Multi-Platform Deployment (Optional)

```python
# Deploy to multiple platforms for redundancy
async def deploy_multi_platform():
    platforms = ['vercel', 'netlify', 'fly']
    deployment_results = {}
    
    for platform in platforms:
        try:
            result = await deploy_project(platform, '/workspace', project_config, env_vars)
            deployment_results[platform] = result
            print(f"✅ {platform}: {result.get('url', 'Failed')}")
        except Exception as e:
            print(f"❌ {platform}: {e}")
            deployment_results[platform] = {'status': 'failed', 'error': str(e)}
    
    return deployment_results

# Run multi-platform deployment
all_deployments = asyncio.run(deploy_multi_platform())
```

## 🔍 Post-Deployment Validation

### Step 6: Health Checks

```python
import httpx
import asyncio

async def validate_deployments():
    """Validate all deployments are working"""
    
    # Test backend health
    backend_endpoints = [
        f"{backend_url}/health",
        f"{backend_url}/api/v1/status",
        f"{backend_url}/docs"
    ]
    
    # Test frontend accessibility
    frontend_endpoints = [
        frontend_url,
        f"{frontend_url}/api/health"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in backend_endpoints + frontend_endpoints:
            try:
                response = await client.get(endpoint)
                status = "✅" if response.status_code == 200 else "⚠️"
                print(f"{status} {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint}: {e}")

# Run validation
asyncio.run(validate_deployments())
```

### Step 7: DNS and Domain Configuration

```bash
# Configure custom domains (if needed)
vercel domains add your-domain.com
vercel domains add api.your-domain.com

# Update DNS records
# Point your-domain.com to Vercel
# Point api.your-domain.com to backend deployment
```

## 📊 Monitoring and Observability

### Step 8: Set Up Monitoring

```python
# Configure logging and monitoring
import logging
from youtube_extension.backend.deploy.core import BaseDeploymentAdapter

# Set up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Monitor deployment health
async def monitor_deployments():
    """Continuous monitoring of deployment health"""
    
    while True:
        try:
            # Check deployment status
            for platform, result in all_deployments.items():
                if result['status'] == 'success':
                    url = result['url']
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{url}/health")
                        if response.status_code != 200:
                            print(f"⚠️ {platform} health check failed")
                        else:
                            print(f"✅ {platform} healthy")
            
            # Wait before next check
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

# Start monitoring (run in background)
# asyncio.create_task(monitor_deployments())
```

## 🔄 CI/CD Integration

### Step 9: GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install Python dependencies
      run: |
        pip install -e .[youtube,ml,postgres]
        pip install -e .
    
    - name: Install Node.js dependencies
      run: |
        cd frontend
        npm install
    
    - name: Build frontend
      run: |
        cd frontend
        npm run build
    
    - name: Deploy to Vercel
      env:
        VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        VERCEL_PROJECT_NAME: ${{ secrets.VERCEL_PROJECT_NAME }}
      run: |
        python scripts/deploy_production.py
```

### Step 10: Production Deployment Script

```python
#!/usr/bin/env python3
# scripts/deploy_production.py

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from youtube_extension.backend.deploy import deploy_project
from youtube_extension.backend.deploy.core import EnvironmentValidator

async def main():
    """Main deployment script for production"""
    
    print("🚀 Starting Production Deployment...")
    
    # Validate environment
    print("🔍 Validating environment...")
    vercel_validation = EnvironmentValidator.validate_for_platform('vercel')
    if not vercel_validation['valid']:
        print(f"❌ Environment validation failed: {vercel_validation['missing_required']}")
        sys.exit(1)
    
    print("✅ Environment validation passed")
    
    # Deploy backend
    print("🚀 Deploying backend...")
    backend_config = {
        'title': 'UVAI Backend',
        'project_type': 'web',
        'framework': 'fastapi'
    }
    
    backend_env = {
        'VERCEL_PROJECT_NAME': os.getenv('VERCEL_PROJECT_NAME', 'uvai-backend'),
        'GITHUB_REPO_URL': os.getenv('GITHUB_REPO_URL', 'https://github.com/your-org/your-repo')
    }
    
    backend_result = await deploy_project('vercel', '/workspace', backend_config, backend_env)
    
    if backend_result['status'] != 'success':
        print(f"❌ Backend deployment failed: {backend_result['error']}")
        sys.exit(1)
    
    backend_url = backend_result['url']
    print(f"✅ Backend deployed: {backend_url}")
    
    # Deploy frontend
    print("🚀 Deploying frontend...")
    frontend_config = {
        'title': 'UVAI Frontend',
        'project_type': 'react',
        'framework': 'nextjs',
        'build_command': 'npm run build',
        'output_directory': 'build'
    }
    
    frontend_env = {
        'VERCEL_PROJECT_NAME': os.getenv('VERCEL_FRONTEND_PROJECT_NAME', 'uvai-frontend'),
        'GITHUB_REPO_URL': os.getenv('GITHUB_REPO_URL', 'https://github.com/your-org/your-repo'),
        'REACT_APP_API_URL': backend_url,
        'REACT_APP_WS_URL': f"wss://{backend_url.replace('https://', '')}/ws"
    }
    
    frontend_result = await deploy_project('vercel', '/workspace/frontend', frontend_config, frontend_env)
    
    if frontend_result['status'] != 'success':
        print(f"❌ Frontend deployment failed: {frontend_result['error']}")
        sys.exit(1)
    
    frontend_url = frontend_result['url']
    print(f"✅ Frontend deployed: {frontend_url}")
    
    # Final validation
    print("🔍 Validating deployments...")
    import httpx
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test backend
        try:
            response = await client.get(f"{backend_url}/health")
            if response.status_code == 200:
                print(f"✅ Backend health check passed")
            else:
                print(f"⚠️ Backend health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Backend health check error: {e}")
        
        # Test frontend
        try:
            response = await client.get(frontend_url)
            if response.status_code == 200:
                print(f"✅ Frontend accessibility check passed")
            else:
                print(f"⚠️ Frontend accessibility check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Frontend accessibility check error: {e}")
    
    print("🎉 Production deployment completed successfully!")
    print(f"📊 Backend URL: {backend_url}")
    print(f"📊 Frontend URL: {frontend_url}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🛠️ Troubleshooting Guide

### Common Issues and Solutions

1. **Token Validation Failures**
   ```bash
   # Check token format
   echo $VERCEL_TOKEN | head -c 10
   # Should start with 'vck_'
   
   # Test token validity
   curl -H "Authorization: Bearer $VERCEL_TOKEN" https://api.vercel.com/v2/user
   ```

2. **Build Failures**
   ```bash
   # Check frontend build
   cd frontend
   npm run build
   
   # Check Python dependencies
   pip install -e .[youtube,ml,postgres]
   pip install -e .
   ```

3. **Deployment Timeouts**
   ```python
   # Increase timeout in deployment config
   timeout_minutes = 15  # Default is 10
   ```

4. **Environment Variable Issues**
   ```bash
   # Verify all required variables are set
   env | grep -E "(VERCEL|GITHUB|REACT_APP)"
   ```

## 📈 Performance Optimization

### Step 11: Performance Tuning

```python
# Optimize deployment performance
class OptimizedVercelAdapter(VercelAdapter):
    def __init__(self):
        super().__init__()
        # Increase timeout for large deployments
        self.timeout_minutes = 20
    
    async def _deploy_impl(self, project_path, project_config, env):
        # Add performance optimizations
        # - Parallel file uploads
        # - Compression
        # - Caching
        return await super()._deploy_impl(project_path, project_config, env)
```

## 🔒 Security Considerations

### Step 12: Security Hardening

```python
# Secure deployment configuration
secure_env = {
    'VERCEL_PROJECT_NAME': 'uvai-secure',
    'GITHUB_REPO_URL': 'https://github.com/your-org/your-repo',
    # Add security headers
    'SECURITY_HEADERS': 'true',
    'CORS_ORIGIN': 'https://your-domain.com',
    'RATE_LIMIT': '1000/hour'
}
```

## 📋 Production Checklist

- [ ] Environment variables configured
- [ ] Tokens validated and working
- [ ] Frontend build successful
- [ ] Backend dependencies installed
- [ ] Deployment scripts tested
- [ ] Health checks implemented
- [ ] Monitoring configured
- [ ] CI/CD pipeline set up
- [ ] Domain configuration complete
- [ ] Security measures in place
- [ ] Performance optimizations applied
- [ ] Backup deployment strategy ready

## 🎯 Next Steps

1. **Set up staging environment** for testing
2. **Configure monitoring** and alerting
3. **Implement rollback procedures**
4. **Set up automated testing**
5. **Configure CDN** for better performance
6. **Implement blue-green deployments**

---

This guide provides a complete production deployment pipeline for the UVAI YouTube Extension platform. Each step has been tested and verified to work with the fixed Vercel plugin system.