#!/usr/bin/env python3
"""
Integration Test Runner
Orchestrates all integration tests and generates comprehensive reports
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, Any

def run_integration_test_suite() -> Dict[str, Any]:
    """Run the complete integration test suite"""
    print("🚀 STARTING INTEGRATION TEST SUITE")
    print("="*60)
    
    test_start_time = datetime.now()
    results = {
        'start_time': test_start_time.isoformat(),
        'tests_run': [],
        'overall_success': False,
        'summary': {}
    }
    
    try:
        # Run main integration tests
        print("📋 Running AI Agent + MCP Server Integration Tests...")
        result = subprocess.run([
            sys.executable, 
            'tests/integration/test_ai_mcp_integration.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        results['tests_run'].append({
            'name': 'AI Agent + MCP Integration',
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        })
        
        # Additional validation tests
        print("🔍 Running System Validation Tests...")
        validation_success = run_system_validation()
        results['tests_run'].append({
            'name': 'System Validation',
            'success': validation_success,
            'details': 'Docker, package.json, and file structure validation'
        })
        
        # Calculate overall success
        all_successful = all(test['success'] for test in results['tests_run'])
        results['overall_success'] = all_successful
        
        # Generate summary
        test_end_time = datetime.now()
        duration = (test_end_time - test_start_time).total_seconds()
        
        results['end_time'] = test_end_time.isoformat()
        results['duration_seconds'] = duration
        results['summary'] = {
            'total_tests': len(results['tests_run']),
            'passed_tests': sum(1 for test in results['tests_run'] if test['success']),
            'failed_tests': sum(1 for test in results['tests_run'] if not test['success']),
            'success_rate': (sum(1 for test in results['tests_run'] if test['success']) / len(results['tests_run'])) * 100 if results['tests_run'] else 0
        }
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        results['overall_success'] = False
        return results

def run_system_validation() -> bool:
    """Run system validation checks"""
    print("🔧 Validating system components...")
    
    validations = []
    
    # Check Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        docker_available = result.returncode == 0
        validations.append(('Docker', docker_available))
        print(f"{'✅' if docker_available else '❌'} Docker: {'Available' if docker_available else 'Not available'}")
    except:
        validations.append(('Docker', False))
        print("❌ Docker: Not available")
    
    # Check key files
    key_files = [
        'Dockerfile.production',
        'package.json',
        'mcp_server.py',
        'learning_app_processor.py',
        '.github/workflows/production-deploy.yml'
    ]
    
    for file_path in key_files:
        exists = os.path.exists(file_path)
        validations.append((f'File: {file_path}', exists))
        print(f"{'✅' if exists else '❌'} {file_path}: {'Present' if exists else 'Missing'}")
    
    # Check AI agent structure
    ai_agent_files = [
        'ai-learning-agent/package.json',
        'ai-learning-agent/src/index.js',
        'ai-learning-agent/public/index.html'
    ]
    
    for file_path in ai_agent_files:
        exists = os.path.exists(file_path)
        validations.append((f'AI Agent: {file_path}', exists))
        print(f"{'✅' if exists else '❌'} {file_path}: {'Present' if exists else 'Missing'}")
    
    # Return overall validation result
    all_valid = all(result for _, result in validations)
    print(f"\n{'✅' if all_valid else '❌'} System Validation: {'PASSED' if all_valid else 'FAILED'}")
    
    return all_valid

def generate_report(results: Dict[str, Any]) -> None:
    """Generate comprehensive test report"""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE INTEGRATION TEST REPORT")
    print("="*60)
    
    # Overall status
    status = "✅ PASSED" if results['overall_success'] else "❌ FAILED"
    print(f"🎯 Overall Status: {status}")
    print(f"📅 Start Time: {results['start_time']}")
    print(f"📅 End Time: {results.get('end_time', 'N/A')}")
    print(f"⏱️  Duration: {results.get('duration_seconds', 0):.2f} seconds")
    
    # Summary statistics
    summary = results.get('summary', {})
    print(f"\n📈 Test Summary:")
    print(f"   Total Tests: {summary.get('total_tests', 0)}")
    print(f"   Passed: {summary.get('passed_tests', 0)}")
    print(f"   Failed: {summary.get('failed_tests', 0)}")
    print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
    
    # Individual test results
    print(f"\n🔍 Individual Test Results:")
    for i, test in enumerate(results.get('tests_run', []), 1):
        status_icon = "✅" if test['success'] else "❌"
        print(f"   {i}. {status_icon} {test['name']}")
        if not test['success'] and 'stderr' in test:
            print(f"      Error: {test['stderr'][:100]}...")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if results['overall_success']:
        print("   🚀 System is ready for production deployment")
        print("   📦 All components are validated and functional")
        print("   🔄 CI/CD pipeline can be activated")
    else:
        print("   ⚠️  Address failing tests before production deployment")
        print("   🔧 Review system validation failures")
        print("   📋 Check logs for specific error details")
    
    # Next steps
    print(f"\n🎯 Next Steps:")
    if results['overall_success']:
        print("   1. Commit and push changes to trigger CI/CD")
        print("   2. Deploy to staging environment")
        print("   3. Run production readiness checklist")
        print("   4. Schedule production deployment")
    else:
        print("   1. Review and fix failing tests")
        print("   2. Re-run integration test suite")
        print("   3. Validate all system components")
        print("   4. Update documentation as needed")
    
    print("="*60)

def save_results(results: Dict[str, Any]) -> None:
    """Save test results to file"""
    try:
        os.makedirs('tests/reports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tests/reports/integration_test_report_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Test report saved to: {filename}")
        
    except Exception as e:
        print(f"⚠️  Could not save test report: {e}")

def main():
    """Main test runner function"""
    print("🎯 INTEGRATION TEST RUNNER")
    print("="*60)
    
    # Run integration tests
    results = run_integration_test_suite()
    
    # Generate report
    generate_report(results)
    
    # Save results
    save_results(results)
    
    # Exit with appropriate code
    exit_code = 0 if results['overall_success'] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 