#!/usr/bin/env python3
"""
API Validation Test - All Integration Methods
Validates both Python SDK and REST API approaches
"""
import asyncio
import json
import os
import subprocess
import time

import pytest
from google import genai

# API key must come from the environment — never hardcode credentials.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    pytest.skip(
        "API validation test requires GEMINI_API_KEY env var",
        allow_module_level=True,
    )

async def test_gemini_python_sdk():
    """Test Gemini using Python SDK"""
    print("=" * 70)
    print("Test 1: Gemini Python SDK")
    print("=" * 70)

    client = genai.Client(api_key=GEMINI_API_KEY)

    start = time.time()
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents="List 3 AI trends in 2025"
    )
    elapsed = time.time() - start

    print(f"✅ Model: gemini-2.0-flash-exp")
    print(f"✅ Response: {response.text[:200]}...")
    print(f"✅ Latency: {elapsed:.2f}s")
    print()

    return {
        "method": "Python SDK",
        "model": "gemini-2.0-flash-exp",
        "response_length": len(response.text),
        "latency": elapsed,
        "status": "success"
    }

def test_gemini_rest_api():
    """Test Gemini using REST API"""
    print("=" * 70)
    print("Test 2: Gemini REST API")
    print("=" * 70)

    start = time.time()

    # Use subprocess to avoid curl shell escaping issues
    cmd = [
        "curl", "-s",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent",
        "-H", "Content-Type: application/json",
        "-H", f"X-goog-api-key: {GEMINI_API_KEY}",
        "-d", json.dumps({
            "contents": [{
                "parts": [{"text": "List 3 AI trends in 2025"}]
            }]
        })
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    data = json.loads(result.stdout)
    response_text = data["candidates"][0]["content"]["parts"][0]["text"]
    token_count = data["usageMetadata"]["totalTokenCount"]

    print(f"✅ Model: {data['modelVersion']}")
    print(f"✅ Response: {response_text[:200]}...")
    print(f"✅ Tokens: {token_count}")
    print(f"✅ Latency: {elapsed:.2f}s")
    print()

    return {
        "method": "REST API",
        "model": data["modelVersion"],
        "response_length": len(response_text),
        "total_tokens": token_count,
        "latency": elapsed,
        "status": "success"
    }

async def main():
    print("\n🧪 API Validation Test Suite\n")
    print("Validating all integration methods with live APIs\n")

    results = {}

    # Test 1: Python SDK
    try:
        results["python_sdk"] = await test_gemini_python_sdk()
    except Exception as e:
        print(f"❌ Python SDK test failed: {e}\n")
        results["python_sdk"] = {"status": "failed", "error": str(e)}

    # Test 2: REST API
    try:
        results["rest_api"] = test_gemini_rest_api()
    except Exception as e:
        print(f"❌ REST API test failed: {e}\n")
        results["rest_api"] = {"status": "failed", "error": str(e)}

    # Summary
    print("=" * 70)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r.get("status") == "success")
    total = len(results)

    print(f"Tests Passed: {passed}/{total}\n")

    if results["python_sdk"].get("status") == "success":
        print("✅ Gemini Python SDK: OPERATIONAL")
        print(f"   - Latency: {results['python_sdk']['latency']:.2f}s")

    if results["rest_api"].get("status") == "success":
        print("✅ Gemini REST API: OPERATIONAL")
        print(f"   - Latency: {results['rest_api']['latency']:.2f}s")
        print(f"   - Token efficiency: {results['rest_api']['total_tokens']} tokens")

    if passed == total:
        print("\n🎉 ALL API METHODS VALIDATED - PRODUCTION READY")
    else:
        print(f"\n⚠️  {total - passed} method(s) failed")

    print(f"\n📋 Integration Status:")
    print(f"   - Python SDK: {'✅ Working' if results['python_sdk'].get('status') == 'success' else '❌ Failed'}")
    print(f"   - REST API: {'✅ Working' if results['rest_api'].get('status') == 'success' else '❌ Failed'}")
    print(f"   - Avg latency: {(results['python_sdk'].get('latency', 0) + results['rest_api'].get('latency', 0)) / 2:.2f}s")

    return results

if __name__ == "__main__":
    result = asyncio.run(main())
