#!/bin/zsh
# grok_cli.sh v3 - Bulletproof Grok CLI (Escaping + Validation)
# Requires: jq (brew install jq if missing)

MODEL="grok-4-fast-reasoning"
BASE_URL="https://api.x.ai/v1/chat/completions"
declare -a HISTORY  # Fresh array each run

# Sanitize input: Strip control chars (U+0000-U+001F)
sanitize() {
  echo "$1" | tr -d '\000-\037\177-\377' | sed 's/"/\\"/g; s/\\/\\\\/g'  # Enhanced: quotes + backslashes
}

echo "🚀 Grok CLI v3 (Control-Proof)! Commands: 'quit', 'clear' (ignore input), 'reset' (wipe history), 'raw' (debug)."
echo "Model: $MODEL | Test: Type a simple query first."

while true; do
  read -r "input?You: "
  input=$(sanitize "$input")  # Clean input
  input="${input#"${input%%[![:space:]]*}"}"  # Trim leading
  input="${input%"${input##*[![:space:]]}"}"  # Trim trailing
  if [[ "$input" == "quit" ]]; then
    echo "👋 Exited. History: ${#HISTORY[@]} entries."
    break
  elif [[ "$input" == "clear" ]]; then
    echo "🧹 Input cleared—try again."
    continue
  elif [[ "$input" == "reset" ]]; then
    HISTORY=()
    echo "🔄 History reset—fresh start."
    continue
  elif [[ "$input" == "raw" ]]; then
    RAW_MODE="true"
    echo "🔧 Raw debug ON."
    continue
  elif [[ -z "$input" ]]; then
    continue
  fi

  # Build & validate user message
  USER_MSG=$(jq -cn --arg content "$input" '{"role": "user", "content": $content}' 2>/dev/null)
  if [[ $? -ne 0 ]]; then
    echo "❌ Input too wild (control chars?). Plain text only."
    continue
  fi
  HISTORY+=("$USER_MSG")

  # Validate & filter history
  VALID_HISTORY=()
  for entry in "${HISTORY[@]}"; do
    if echo "$entry" | jq empty >/dev/null 2>&1; then
      VALID_HISTORY+=("$entry")
    else
      echo "⚠️ Dropped bad history entry."
    fi
  done
  HISTORY=("${VALID_HISTORY[@]}")

  MESSAGES=$(printf '%s\n' "${HISTORY[@]}" | jq -s . 2>/dev/null)
  if [[ $? -ne 0 ]]; then
    echo "❌ JSON fail—'reset' and retry."
    continue
  fi
  PAYLOAD=$(jq -n --argjson msgs "$MESSAGES" --arg m "$MODEL" '{model: $m, messages: $msgs, temperature: 0.7}')

  # API Call
  RESPONSE=$(curl -s "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $XAI_API_KEY" \
    -d "$PAYLOAD")

  # Extract
  if echo "$RESPONSE" | jq -e '.choices[0]' >/dev/null 2>&1; then
    REPLY=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')
    echo "Grok: $REPLY"
    ASST_MSG=$(jq -cn --arg content "$REPLY" '{"role": "assistant", "content": $content}' 2>/dev/null)
    if [[ $? -eq 0 ]]; then
      HISTORY+=("$ASST_MSG")
    fi
    USAGE=$(echo "$RESPONSE" | jq '.usage.total_tokens // 0')
    echo "(Tokens: $USAGE)"
    RAW_MODE=""
  else
    ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "API issue (check console.x.ai credits)"')
    echo "❌ API: $ERROR_MSG"
    if [[ "$RAW_MODE" == "true" ]]; then
      echo "Debug Payload: $(echo "$PAYLOAD" | head -c 200)... "
    fi
  fi
  echo "---"
done
