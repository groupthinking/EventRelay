#!/bin/bash

# Script to create a test account for local development
# Usage: ./scripts/create-test-account.sh

set -e

BASE_URL="http://localhost:5173"
EMAIL="garveyht@gmail.com"
PASSWORD="TestPassword123!"
NAME="Garvey"

echo "🔐 Creating test account for netmesh-production..."
echo "📧 Email: $EMAIL"
echo ""

# Step 1: Get CSRF token
echo "📝 Step 1: Getting CSRF token..."
CSRF_RESPONSE=$(curl -s -c /tmp/netmesh-cookies.txt -b /tmp/netmesh-cookies.txt \
  -X GET "$BASE_URL/api/auth/csrf-token" \
  -H "Content-Type: application/json")

echo "CSRF Response: $CSRF_RESPONSE"

# Extract CSRF token from response
CSRF_TOKEN=$(echo $CSRF_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -z "$CSRF_TOKEN" ]; then
  echo "❌ Failed to get CSRF token"
  echo "Response: $CSRF_RESPONSE"
  exit 1
fi

echo "✅ CSRF Token obtained: ${CSRF_TOKEN:0:20}..."
echo ""

# Step 2: Register the account
echo "📝 Step 2: Registering account..."
REGISTER_RESPONSE=$(curl -s -c /tmp/netmesh-cookies.txt -b /tmp/netmesh-cookies.txt \
  -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"name\": \"$NAME\"
  }")

echo "Register Response: $REGISTER_RESPONSE"
echo ""

# Check if registration was successful
if echo "$REGISTER_RESPONSE" | grep -q '"success":true'; then
  echo "✅ Account created successfully!"
  echo ""
  echo "🎉 You can now login with:"
  echo "   Email: $EMAIL"
  echo "   Password: $PASSWORD"
  echo ""
  echo "🌐 Visit: $BASE_URL"
else
  echo "❌ Registration failed"
  echo "Response: $REGISTER_RESPONSE"
  
  # Check if user already exists
  if echo "$REGISTER_RESPONSE" | grep -q "already registered"; then
    echo ""
    echo "ℹ️  Account already exists. You can login with:"
    echo "   Email: $EMAIL"
    echo "   Password: (use your existing password)"
    echo ""
    echo "🌐 Visit: $BASE_URL"
  fi
  
  exit 1
fi

# Cleanup
rm -f /tmp/netmesh-cookies.txt

echo ""
echo "✨ Setup complete!"