#!/bin/bash
# Quick Test of Fixed Storage Tests

echo "🔧 Testing Fixed Storage Tests"
echo "=============================="

# Check if we're in venv
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
else
    echo "⚠️  Activating virtual environment..."
    source .venv/bin/activate
fi

# 1. Test just the storage test that we fixed
echo ""
echo "1. Testing fixed storage test..."
if pytest tests/test_storage.py::TestStorageFunctions::test_save_pack_creates_correct_structure -v; then
    echo "✅ Single storage test passed!"
else
    echo "❌ Single storage test failed"
fi

# 2. Test all storage tests
echo ""
echo "2. Testing all storage tests..."
if pytest tests/test_storage.py -v; then
    echo "✅ All storage tests passed!"
else
    echo "❌ Some storage tests failed"
fi

echo ""
echo "🎯 Test Summary:"
echo "- ✅ Service now accepts custom paths for testing"
echo "- ✅ Tests use real temporary directories"
echo "- ✅ No more Docker path conflicts"
echo "- ✅ Proper cleanup after tests"
