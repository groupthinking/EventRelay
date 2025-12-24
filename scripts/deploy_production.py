#!/usr/bin/env python3
"""
Production Deployment Script for UVAI YouTube Extension
This script handles the complete deployment pipeline to Vercel
"""

import asyncio
import os
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime

# Use absolute imports from installed package
from youtube_extension.backend.deploy import deploy_project
from youtube_extension.backend.deploy.core import EnvironmentValidator

class ProductionDeployer:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def validate_environment(self):
        """Validate all required environment variables and tokens"""
        self.log("🔍 Validating environment...")
        
        required_vars = {
            'VERCEL_TOKEN': 'Vercel API token',
            'GITHUB_TOKEN': 'GitHub API token (optional)',
            'VERCEL_PROJECT_NAME': 'Vercel project name'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            self.log(f"❌ Missing required environment variables: {', '.join(missing_vars)}", "ERROR")
            return False
        
        # Validate Vercel token
        vercel_validation = EnvironmentValidator.validate_for_platform('vercel')
        if not vercel_validation['valid']:
            self.log(f"❌ Vercel validation failed: {vercel_validation['missing_required']}", "ERROR")
            return False
        
        self.log("✅ Environment validation passed")
        return True
    
    async def test_api_connectivity(self):
        """Test API connectivity before deployment"""
        self.log("🔗 Testing API connectivity...")
        
        token = os.getenv('VERCEL_TOKEN')
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get('https://api.vercel.com/v2/user', headers=headers)
                if response.status_code == 200:
                    user_data = response.json()
                    self.log(f"✅ Vercel API connected - User: {user_data.get('username', 'Unknown')}")
                    return True
                else:
                    self.log(f"❌ Vercel API connection failed: {response.status_code}", "ERROR")
                    return False
        except Exception as e:
            self.log(f"❌ API connectivity test failed: {e}", "ERROR")
            return False
    
    async def deploy_backend(self):
        """Deploy the backend to Vercel"""
        self.log("🚀 Deploying backend...")
        
        project_config = {
            'title': 'UVAI Backend',
            'project_type': 'web',
            'framework': 'fastapi',
            'build_command': 'pip install -e .[youtube,ml,postgres] && pip install -e .',
            'output_directory': 'dist'
        }
        
        env_vars = {
            'VERCEL_PROJECT_NAME': os.getenv('VERCEL_PROJECT_NAME', 'uvai-backend'),
            'GITHUB_REPO_URL': os.getenv('GITHUB_REPO_URL', 'https://github.com/test/test-repo'),
            'VERCEL_ORG_ID': os.getenv('VERCEL_ORG_ID')  # Optional
        }
        
        try:
            result = await deploy_project('vercel', '/workspace', project_config, env_vars)
            
            if result['status'] == 'success':
                self.log(f"✅ Backend deployed successfully: {result['url']}")
                self.results['backend'] = result
                return result['url']
            else:
                self.log(f"❌ Backend deployment failed: {result.get('error', 'Unknown error')}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Backend deployment exception: {e}", "ERROR")
            return None
    
    async def deploy_frontend(self, backend_url):
        """Deploy the frontend to Vercel"""
        self.log("🚀 Deploying frontend...")
        
        project_config = {
            'title': 'UVAI Frontend',
            'project_type': 'react',
            'framework': 'nextjs',
            'build_command': 'npm run build',
            'output_directory': 'build'
        }
        
        env_vars = {
            'VERCEL_PROJECT_NAME': os.getenv('VERCEL_FRONTEND_PROJECT_NAME', 'uvai-frontend'),
            'GITHUB_REPO_URL': os.getenv('GITHUB_REPO_URL', 'https://github.com/test/test-repo'),
            'REACT_APP_API_URL': backend_url,
            'REACT_APP_WS_URL': f"wss://{backend_url.replace('https://', '')}/ws",
            'REACT_APP_MCP_SERVER_URL': f"{backend_url}/mcp"
        }
        
        try:
            result = await deploy_project('vercel', '/workspace/frontend', project_config, env_vars)
            
            if result['status'] == 'success':
                self.log(f"✅ Frontend deployed successfully: {result['url']}")
                self.results['frontend'] = result
                return result['url']
            else:
                self.log(f"❌ Frontend deployment failed: {result.get('error', 'Unknown error')}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Frontend deployment exception: {e}", "ERROR")
            return None
    
    async def validate_deployments(self, backend_url, frontend_url):
        """Validate that deployments are working"""
        self.log("🔍 Validating deployments...")
        
        validation_results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test backend
            if backend_url:
                try:
                    response = await client.get(f"{backend_url}/health")
                    if response.status_code == 200:
                        self.log("✅ Backend health check passed")
                        validation_results['backend'] = True
                    else:
                        self.log(f"⚠️ Backend health check failed: {response.status_code}", "WARNING")
                        validation_results['backend'] = False
                except Exception as e:
                    self.log(f"❌ Backend health check error: {e}", "ERROR")
                    validation_results['backend'] = False
            
            # Test frontend
            if frontend_url:
                try:
                    response = await client.get(frontend_url)
                    if response.status_code == 200:
                        self.log("✅ Frontend accessibility check passed")
                        validation_results['frontend'] = True
                    else:
                        self.log(f"⚠️ Frontend accessibility check failed: {response.status_code}", "WARNING")
                        validation_results['frontend'] = False
                except Exception as e:
                    self.log(f"❌ Frontend accessibility check error: {e}", "ERROR")
                    validation_results['frontend'] = False
        
        return validation_results
    
    def generate_deployment_report(self, backend_url, frontend_url, validation_results):
        """Generate a deployment report"""
        self.log("📊 Generating deployment report...")
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        report = {
            'deployment_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'status': 'success' if all(validation_results.values()) else 'partial'
            },
            'deployments': {
                'backend': {
                    'url': backend_url,
                    'status': 'success' if backend_url else 'failed',
                    'validation': validation_results.get('backend', False)
                },
                'frontend': {
                    'url': frontend_url,
                    'status': 'success' if frontend_url else 'failed',
                    'validation': validation_results.get('frontend', False)
                }
            },
            'environment': {
                'vercel_token_set': bool(os.getenv('VERCEL_TOKEN')),
                'github_token_set': bool(os.getenv('GITHUB_TOKEN')),
                'project_name': os.getenv('VERCEL_PROJECT_NAME', 'Not set')
            }
        }
        
        # Save report to file
        report_file = f"deployment_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"📄 Deployment report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("🎉 DEPLOYMENT SUMMARY")
        print("="*60)
        print(f"⏱️  Duration: {duration.total_seconds():.1f} seconds")
        print(f"📊 Status: {report['deployment_summary']['status']}")
        print()
        
        if backend_url:
            print(f"🚀 Backend: {backend_url}")
            print(f"   Status: {'✅ Healthy' if validation_results.get('backend') else '⚠️ Issues'}")
        else:
            print("🚀 Backend: ❌ Failed")
        
        if frontend_url:
            print(f"🌐 Frontend: {frontend_url}")
            print(f"   Status: {'✅ Accessible' if validation_results.get('frontend') else '⚠️ Issues'}")
        else:
            print("🌐 Frontend: ❌ Failed")
        
        print()
        print("📄 Full report saved to:", report_file)
        print("="*60)
        
        return report
    
    async def run_deployment(self):
        """Run the complete deployment pipeline"""
        self.log("🚀 Starting Production Deployment Pipeline")
        self.log("="*50)
        
        # Step 1: Validate environment
        if not await self.validate_environment():
            return False
        
        # Step 2: Test API connectivity
        if not await self.test_api_connectivity():
            return False
        
        # Step 3: Deploy backend
        backend_url = await self.deploy_backend()
        if not backend_url:
            self.log("❌ Backend deployment failed, stopping pipeline", "ERROR")
            return False
        
        # Step 4: Deploy frontend
        frontend_url = await self.deploy_frontend(backend_url)
        if not frontend_url:
            self.log("⚠️ Frontend deployment failed, but backend is available", "WARNING")
        
        # Step 5: Validate deployments
        validation_results = await self.validate_deployments(backend_url, frontend_url)
        
        # Step 6: Generate report
        report = self.generate_deployment_report(backend_url, frontend_url, validation_results)
        
        return report['deployment_summary']['status'] == 'success'

async def main():
    """Main entry point"""
    deployer = ProductionDeployer()
    
    try:
        success = await deployer.run_deployment()
        if success:
            print("\n🎉 Production deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Production deployment failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())