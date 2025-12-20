import os
import google.generativeai as genai
import sys

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return
    
    # Strip whitespace just in case
    api_key = api_key.strip()
    
    print(f"🔑 Testing key: {api_key[:8]}... (length: {len(api_key)})")
    
    try:
        genai.configure(api_key=api_key)
        models = list(genai.list_models())
        print(f"📊 Found {len(models)} models:")
        for m in models:
            print(f"   - {m.name} (supports: {m.supported_generation_methods})")
        
        if not models:
            print("⚠️ No models found at all!")
            return

        model_name = 'gemini-1.5-flash'
        if not any(model_name in m.name for m in models):
             # Try to find any available model
             if models:
                 model_name = models[0].name
                 print(f"⚠️ {model_name} not found, trying {model_name}")

        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"✅ Generate content success: {response.text}")
        
    except Exception as e:
        print(f"❌ Gemini test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini()
