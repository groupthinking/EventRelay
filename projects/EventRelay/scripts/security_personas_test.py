#!/usr/bin/env python3
"""
Security Personas Testing Script
================================

Tests the system from different user perspectives:
- Free tier user
- Paid user
- Hacker/Attacker
- Competitor
"""

import os
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class UserPersona(Enum):
    FREE_USER = "free_user"
    PAID_USER = "paid_user"
    HACKER = "hacker"
    COMPETITOR = "competitor"

@dataclass
class TestResult:
    persona: UserPersona
    test_name: str
    status: str
    details: Dict[str, Any]
    vulnerabilities: List[str]

class SecurityPersonasTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def test_free_user(self):
        """Test system as a free tier user"""
        print("\n🆓 Testing as FREE USER...")
        
        # Test 1: Rate limiting
        result = await self._test_rate_limiting("free_user")
        self.results.append(result)
        
        # Test 2: Feature access
        features_to_test = [
            "/api/chat",
            "/api/process-video",
            "/api/process-video-markdown",
            "/api/video-to-software"
        ]
        
        for feature in features_to_test:
            async with aiohttp.ClientSession() as session:
                try:
                    # No auth headers for free user
                    async with session.post(
                        f"{self.base_url}{feature}",
                        json={"video_url": "https://youtube.com/watch?v=test"}
                    ) as resp:
                        status = resp.status
                        content = await resp.text()
                        
                        self.results.append(TestResult(
                            persona=UserPersona.FREE_USER,
                            test_name=f"Access to {feature}",
                            status="PASS" if status in [200, 201, 422] else "FAIL",
                            details={"status": status, "response": content[:200]},
                            vulnerabilities=[]
                        ))
                except Exception as e:
                    self.results.append(TestResult(
                        persona=UserPersona.FREE_USER,
                        test_name=f"Access to {feature}",
                        status="ERROR",
                        details={"error": str(e)},
                        vulnerabilities=[]
                    ))
                    
    async def test_paid_user(self):
        """Test system as a paid user"""
        print("\n💳 Testing as PAID USER...")
        
        # Simulate paid user with API key
        headers = {"X-API-Key": "test-paid-user-key-123"}
        
        # Test 1: Enhanced rate limits
        result = await self._test_rate_limiting("paid_user", headers)
        self.results.append(result)
        
        # Test 2: Premium features
        premium_features = [
            "/api/batch-process",
            "/api/export",
            "/results/download"
        ]
        
        for feature in premium_features:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{self.base_url}{feature}",
                        headers=headers
                    ) as resp:
                        status = resp.status
                        
                        self.results.append(TestResult(
                            persona=UserPersona.PAID_USER,
                            test_name=f"Premium feature: {feature}",
                            status="CONFIGURED" if status != 404 else "NOT_IMPLEMENTED",
                            details={"status": status},
                            vulnerabilities=[]
                        ))
                except Exception as e:
                    self.results.append(TestResult(
                        persona=UserPersona.PAID_USER,
                        test_name=f"Premium feature: {feature}",
                        status="ERROR",
                        details={"error": str(e)},
                        vulnerabilities=[]
                    ))
                    
    async def test_hacker(self):
        """Test system as a malicious actor"""
        print("\n🔴 Testing as HACKER...")
        
        vulnerabilities = []
        
        # Test 1: SQL Injection attempts
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "1; SELECT * FROM credentials"
        ]
        
        for payload in sql_payloads:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        json={"message": payload}
                    ) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            if "error" not in content.lower():
                                vulnerabilities.append(f"Potential SQL injection with payload: {payload}")
                except:
                    pass
                    
        # Test 2: Path traversal
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in path_payloads:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{self.base_url}/results/{payload}"
                    ) as resp:
                        if resp.status == 200:
                            vulnerabilities.append(f"Path traversal vulnerability with: {payload}")
                except:
                    pass
                    
        # Test 3: XSS attempts
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        json={"message": payload}
                    ) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            if payload in content:
                                vulnerabilities.append(f"Potential XSS vulnerability with: {payload}")
                except:
                    pass
                    
        # Test 4: API key extraction
        sensitive_endpoints = [
            "/env",
            "/.env",
            "/config",
            "/api/config",
            "/api/keys",
            "/.git/config"
        ]
        
        for endpoint in sensitive_endpoints:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as resp:
                        if resp.status == 200:
                            vulnerabilities.append(f"Exposed sensitive endpoint: {endpoint}")
                except:
                    pass
                    
        # Test 5: Authentication bypass
        auth_bypass_headers = [
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "localhost"},
            {"X-Admin": "true"},
            {"Authorization": "Bearer null"},
            {"X-API-Key": ""},
        ]
        
        for headers in auth_bypass_headers:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{self.base_url}/api/admin",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            vulnerabilities.append(f"Auth bypass with headers: {headers}")
                except:
                    pass
                    
        self.results.append(TestResult(
            persona=UserPersona.HACKER,
            test_name="Security vulnerability scan",
            status="SECURE" if not vulnerabilities else "VULNERABLE",
            details={"vulnerabilities_found": len(vulnerabilities)},
            vulnerabilities=vulnerabilities
        ))
        
    async def test_competitor(self):
        """Test system as a competitor trying to extract business logic"""
        print("\n🕵️ Testing as COMPETITOR...")
        
        findings = []
        
        # Test 1: API documentation exposure
        doc_endpoints = [
            "/docs",
            "/redoc",
            "/swagger",
            "/api-docs",
            "/openapi.json"
        ]
        
        for endpoint in doc_endpoints:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as resp:
                        if resp.status == 200:
                            findings.append(f"API documentation exposed at: {endpoint}")
                except:
                    pass
                    
        # Test 2: Source code exposure
        source_patterns = [
            "/.git/",
            "/src/",
            "/backend/",
            "/agents/",
            "/.vscode/",
            "/package.json",
            "/requirements.txt"
        ]
        
        for pattern in source_patterns:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.base_url}{pattern}") as resp:
                        if resp.status in [200, 403]:  # 403 might indicate directory listing disabled
                            findings.append(f"Potential source exposure: {pattern}")
                except:
                    pass
                    
        # Test 3: Business logic extraction
        async with aiohttp.ClientSession() as session:
            try:
                # Try to understand rate limits
                rate_limit_info = []
                for i in range(20):
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        json={"message": "test"}
                    ) as resp:
                        headers = resp.headers
                        if 'X-RateLimit-Limit' in headers:
                            rate_limit_info.append({
                                "limit": headers.get('X-RateLimit-Limit'),
                                "remaining": headers.get('X-RateLimit-Remaining'),
                                "reset": headers.get('X-RateLimit-Reset')
                            })
                            
                if rate_limit_info:
                    findings.append(f"Rate limit information exposed: {rate_limit_info[0]}")
                    
            except:
                pass
                
        self.results.append(TestResult(
            persona=UserPersona.COMPETITOR,
            test_name="Business intelligence gathering",
            status="PROTECTED" if len(findings) < 2 else "EXPOSED",
            details={"findings": len(findings)},
            vulnerabilities=findings
        ))
        
    async def _test_rate_limiting(self, user_type: str, headers: Optional[Dict] = None):
        """Test rate limiting for different user types"""
        request_times = []
        blocked_at = None
        
        async with aiohttp.ClientSession() as session:
            for i in range(30):  # Try 30 requests
                start_time = time.time()
                try:
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        json={"message": f"test {i}"},
                        headers=headers or {}
                    ) as resp:
                        if resp.status == 429:  # Rate limited
                            blocked_at = i
                            break
                        request_times.append(time.time() - start_time)
                except:
                    break
                    
        return TestResult(
            persona=UserPersona(user_type),
            test_name="Rate limiting test",
            status="CONFIGURED" if blocked_at else "NOT_CONFIGURED",
            details={
                "requests_before_limit": blocked_at or ">30",
                "avg_response_time": sum(request_times) / len(request_times) if request_times else 0
            },
            vulnerabilities=["No rate limiting detected"] if not blocked_at else []
        )
        
    def generate_report(self):
        """Generate security testing report"""
        print("\n\n=== SECURITY PERSONAS TEST REPORT ===\n")
        
        for persona in UserPersona:
            persona_results = [r for r in self.results if r.persona == persona]
            if not persona_results:
                continue
                
            print(f"\n{persona.value.upper().replace('_', ' ')} TESTS:")
            print("-" * 50)
            
            for result in persona_results:
                status_icon = "✅" if result.status in ["PASS", "SECURE", "PROTECTED", "CONFIGURED"] else "❌"
                print(f"{status_icon} {result.test_name}: {result.status}")
                
                if result.vulnerabilities:
                    print("   ⚠️  Vulnerabilities found:")
                    for vuln in result.vulnerabilities[:5]:  # Show first 5
                        print(f"      - {vuln}")
                    if len(result.vulnerabilities) > 5:
                        print(f"      ... and {len(result.vulnerabilities) - 5} more")
                        
        # Summary
        total_vulnerabilities = sum(len(r.vulnerabilities) for r in self.results)
        secure_tests = len([r for r in self.results if r.status in ["SECURE", "PROTECTED", "CONFIGURED"]])
        
        print("\n\n=== SUMMARY ===")
        print(f"Total tests run: {len(self.results)}")
        print(f"Secure tests: {secure_tests}/{len(self.results)}")
        print(f"Total vulnerabilities found: {total_vulnerabilities}")
        
        # Save detailed report
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {
                    "persona": r.persona.value,
                    "test": r.test_name,
                    "status": r.status,
                    "details": r.details,
                    "vulnerabilities": r.vulnerabilities
                }
                for r in self.results
            ],
            "summary": {
                "total_tests": len(self.results),
                "secure_tests": secure_tests,
                "vulnerabilities": total_vulnerabilities
            }
        }
        
        report_path = Path("results/security_personas_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\nDetailed report saved to: {report_path}")
        
        return total_vulnerabilities == 0
        
    async def run_all_tests(self):
        """Run all persona tests"""
        print("Starting security personas testing...")
        print("Note: This assumes the backend is running on http://localhost:8000")
        
        # Check if backend is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status != 200:
                        print("❌ Backend not responding. Please start it first.")
                        return False
        except:
            print("❌ Cannot connect to backend at http://localhost:8000")
            print("Please run: python backend/main.py")
            return False
            
        # Run all persona tests
        await self.test_free_user()
        await self.test_paid_user()
        await self.test_hacker()
        await self.test_competitor()
        
        # Generate report
        return self.generate_report()
        

if __name__ == "__main__":
    tester = SecurityPersonasTester()
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(tester.run_all_tests())
        exit(0 if success else 1)
    finally:
        loop.close()
