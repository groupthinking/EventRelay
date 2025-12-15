# Universal Automation Service - Quick Start Guide

**Status:** ✅ Gemini Mode WORKING | ⚠️ Production Mode Blocked by Dependencies

---

## ✅ WHAT WORKS RIGHT NOW

### Gemini-Only Mode (No Dependencies Required)

You can process videos with Gemini API for enhanced video understanding **right now**:

```bash
# Set API key
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

# Process video (analysis only, no deployment)
python3 universal_coordinator.py "https://youtu.be/YOUR_VIDEO" --mode gemini --no-deploy
```

**What you get:**
- 10-dimensional video analysis
- Complete transcript with timestamps
- Topics and key concepts extraction
- Automation opportunities identified
- Visual analysis of video content
- Code/commands extracted from video
- Step-by-step procedures
- Sentiment analysis
- Claude Code skill suggestions

**Output:** JSON file with comprehensive analysis saved to `results_TIMESTAMP.json`

---

## ⚠️ WHAT'S BLOCKED

### Production Mode (EventRelay + UVAI)

**Blocker 1: NumPy Dependency Conflict**
- EventRelay uses `transformers` library with `torch`
- PyTorch compiled against NumPy 1.x
- System has NumPy 2.3.3
- **Error:** `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.3.3`

**Blocker 2: UVAI Import Paths**
- UVAI imports not resolving correctly
- **Error:** `No module named 'agents.infrastructure_packaging_agent'`

---

## 🚀 HOW TO FIX (Choose One Approach)

### Option 1: Quick Test with Gemini Only (WORKS NOW)

```bash
# 1. Set environment variable
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

# 2. Test with a recent programming tutorial video
python3 universal_coordinator.py "https://youtu.be/SHORT_VIDEO" --mode gemini --no-deploy

# 3. Check results
cat results_*.json | python3 -m json.tool
```

### Option 2: Fix Dependencies for Full Pipeline

**Step 1: Create Virtual Environment**
```bash
cd /Users/garvey/Dev/OpenAI_Hub/universal-automation-service

# Create isolated environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install compatible NumPy
pip3 install "numpy<2"

# Install Gemini SDK
pip3 install google-genai google-auth

# Install EventRelay dependencies (if needed)
pip3 install transformers torch
```

**Step 2: Set Environment Variables**
```bash
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"
export GITHUB_TOKEN="your-github-token-here"
```

**Step 3: Test Imports**
```bash
python3 test_imports.py
```

**Step 4: Test Full Pipeline**
```bash
# Production mode (EventRelay + UVAI, no Gemini)
python3 universal_coordinator.py "https://youtu.be/VIDEO" --mode production

# Hybrid mode (All systems)
python3 universal_coordinator.py "https://youtu.be/VIDEO" --mode hybrid
```

### Option 3: Global NumPy Downgrade (Affects Other Projects)

```bash
# WARNING: This may break other Python projects
pip3 install --force-reinstall "numpy<2"

# Then test
python3 test_imports.py
```

---

## 📋 TESTING CHECKLIST

Use this to verify each component:

```bash
# Run diagnostic script
python3 test_imports.py
```

**Expected output when all dependencies fixed:**
```
============================================================
SUMMARY
============================================================
Gemini          : ✅ PASS
UVAI            : ✅ PASS
EventRelay      : ✅ PASS

============================================================
🎉 ALL SYSTEMS OPERATIONAL
Ready to run: python3 universal_coordinator.py
============================================================
```

**Current output:**
```
Gemini          : ✅ PASS
UVAI            : ❌ FAIL
EventRelay      : ❌ FAIL
```

---

## 🎯 RECOMMENDED VIDEO TO TEST

Find a **recent programming tutorial** (last 5 days) from YouTube. Examples:
- "Building a SaaS application with [framework]"
- "API development tutorial"
- "Deploying to cloud platforms"
- "Automation workflows"

**Avoid:**
- Music videos (not relevant to our use case)
- Long videos (>30 min on free tier)
- Non-technical content

---

## 💡 USAGE EXAMPLES

### Example 1: Quick Video Analysis (Gemini Only)

```bash
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

python3 universal_coordinator.py \
  "https://youtu.be/programming-tutorial" \
  --mode gemini \
  --no-deploy
```

**Output:** Comprehensive analysis in `results_*.json`

### Example 2: Full Production Pipeline (When Dependencies Fixed)

```bash
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"
export GITHUB_TOKEN="ghp_your_token_here"

python3 universal_coordinator.py \
  "https://youtu.be/saas-tutorial" \
  --mode hybrid
```

**Output:**
- Gemini analysis
- EventRelay video-to-action workflow
- GitHub repository created
- Vercel/Netlify deployment
- UVAI Codex validation
- Revenue-ready service

### Example 3: Custom API Keys

```bash
python3 universal_coordinator.py \
  "https://youtu.be/video" \
  --mode hybrid \
  --gemini-key "custom-key" \
  --github-token "custom-token"
```

---

## 📊 CURRENT STATUS SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| **Gemini Processor** | ✅ WORKING | Ready for video analysis |
| **Universal Coordinator** | ✅ WORKING | CLI functional, graceful fallback |
| **EventRelay Import** | ❌ BLOCKED | NumPy 1.x vs 2.3.3 conflict |
| **UVAI Import** | ❌ BLOCKED | Import path issues |
| **Monitoring Dashboard** | ✅ WORKING | localhost:3000 |
| **Documentation** | ✅ COMPLETE | All setup guides ready |

---

## 🔍 TROUBLESHOOTING

### Error: "GEMINI_API_KEY not found"

```bash
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"
```

### Error: "429 RESOURCE_EXHAUSTED"

You've hit Gemini API rate limit. Either:
1. Wait for quota reset
2. Use production mode (no Gemini): `--mode production`

### Error: "NumPy 1.x vs 2.3.3"

Fix with virtual environment (Option 2 above) or global downgrade (Option 3).

### Error: "No module named 'agents.infrastructure_packaging_agent'"

UVAI import paths need verification. This is being investigated.

---

## 📞 NEXT STEPS

**Right Now:**
1. ✅ Test Gemini mode with recent video
2. ⏳ Fix NumPy dependency (use virtual environment)
3. ⏳ Verify UVAI import paths
4. ⏳ Test full pipeline

**After Dependencies Fixed:**
1. Process first production video
2. Verify GitHub deployment
3. Test multi-platform deployment
4. Validate revenue generation workflow
5. Monitor deployed services

---

## 📁 KEY FILES

- **universal_coordinator.py** - Main entry point
- **gemini_video_processor.py** - Gemini integration (WORKING)
- **test_imports.py** - Dependency diagnostic tool
- **SETUP.md** - Complete setup guide
- **INTEGRATION_STATUS.md** - Detailed status report
- **FINAL_INTEGRATION_SUMMARY.md** - Integration overview

---

**Status:** Gemini mode ready for testing. Production mode pending dependency resolution.

**Test Command:**
```bash
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"
python3 universal_coordinator.py "https://youtu.be/SHORT_VIDEO" --mode gemini --no-deploy
```
