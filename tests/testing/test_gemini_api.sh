#!/bin/bash
# Test Gemini API connection

export GEMINI_API_KEY="AIzaSyDtYn1Sg9QnvrNm8P4AdazfhiqtzV9FL8k"

echo "Testing Gemini API..."
echo "API Key: ${GEMINI_API_KEY:0:15}..."
echo ""

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts": [{"text": "Respond with just SUCCESS if you receive this."}]
    }]
  }' | python3 -m json.tool | head -30
