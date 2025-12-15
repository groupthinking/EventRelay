import os
import sys
from openai import OpenAI

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
model = "grok-4-fast-reasoning"
history = []

print("🚀 Grok CLI (Python - Bulletproof)! 'quit' to exit, 'clear' to reset. Model: grok-4-fast-reasoning")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ['quit', 'exit']:
        print(f"👋 Exited. Turns: {len(history)//2}")
        break
    if user_input.lower() == 'clear':
        history = []
        print("History cleared.")
        continue
    if not user_input:
        continue

    history.append({"role": "user", "content": user_input})
    try:
        response = client.chat.completions.create(
            model=model,
            messages=history,
            temperature=0.7
        )
        reply = response.choices[0].message.content
        print(f"Grok: {reply}")
        tokens = response.usage.total_tokens if response.usage else 0
        print(f"(Tokens: {tokens})")
        history.append({"role": "assistant", "content": reply})
    except Exception as e:
        print(f"❌ Error: {e} (Check credits at console.x.ai)")
