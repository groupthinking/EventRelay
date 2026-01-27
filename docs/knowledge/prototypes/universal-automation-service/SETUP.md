# Universal Automation Service - Setup Guide

## 🚀 Quick Start

This service integrates **existing production systems** (EventRelay + UVAI) with optional Gemini enhancement.

---

## 📦 Installation

### 1. Install Python Dependencies

```bash
cd /Users/garvey/Dev/OpenAI_Hub/universal-automation-service

# Install Gemini API SDK
pip3 install google-genai google-auth

# Verify installation
python3 -c "from google import genai; print('✅ Gemini SDK installed')"
```

### 2. Set Environment Variables

```bash
# Gemini API (for enhanced video understanding)
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

# GitHub (for auto-deployment)
export GITHUB_TOKEN="your-github-token-here"

# Optional: YouTube API (for EventRelay)
export YOUTUBE_API_KEY="your-youtube-api-key"
```

**Permanent setup (add to ~/.zshrc):**
```bash
echo 'export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"' >> ~/.zshrc
echo 'export GITHUB_TOKEN="your-github-token-here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Verify EventRelay & UVAI Projects

```bash
# Check EventRelay exists
ls /Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/src/youtube_extension/services/workflows/

# Check UVAI exists
ls /Users/garvey/Dev/OpenAI_Hub/projects/UVAI/src/tools/

# Both should show workflow and deployment files
```

---

## 🎯 Usage

### Mode 1: Hybrid (Recommended - Uses Everything)

```bash
python3 universal_coordinator.py "https://youtube.com/watch?v=VIDEO_ID" --mode hybrid
```

**What it does:**
1. **Gemini**: Enhanced video understanding (visual analysis, code extraction)
2. **EventRelay**: Full video-to-action workflow (generates applications)
3. **DeploymentManager**: Auto-deploy to GitHub
4. **UVAI Codex**: Security validation + multi-platform deployment

**Output:**
- GitHub repository with working code
- Deployed to Vercel/Netlify/Fly.io
- Revenue-ready service

---

### Mode 2: Production (EventRelay + UVAI Only)

```bash
python3 universal_coordinator.py "https://youtube.com/watch?v=VIDEO_ID" --mode production
```

**What it does:**
1. **EventRelay**: TranscriptActionWorkflow → generates full applications
2. **DeploymentManager**: GitHub deployment
3. **UVAI Codex**: Validation + deployment

**Use when:** Gemini API quota reached or not needed

---

### Mode 3: Gemini Only (Fast Analysis, No Deployment)

```bash
python3 universal_coordinator.py "https://youtube.com/watch?v=VIDEO_ID" --mode gemini --no-deploy
```

**What it does:**
1. **Gemini**: Deep video understanding with 10 analysis dimensions

**Use when:** Quick analysis needed, no deployment

---

## 📊 Example Outputs

### Successful Run (Hybrid Mode):

```
================================================================================
🚀 UNIVERSAL AUTOMATION COORDINATOR
================================================================================
📺 Video URL: https://youtube.com/watch?v=jawdcPoZJmI
⚙️  Mode: hybrid
🚀 Auto-deploy: True
================================================================================

🎬 STAGE 1: Gemini Video Understanding
--------------------------------------------------------------------------------
[Gemini] Processing: summary...
[Gemini] ✓ Completed: summary
[Gemini] Processing: topics...
[Gemini] ✓ Completed: topics
... (10 analysis dimensions)
✅ Gemini analysis complete

🔄 STAGE 2: EventRelay Video-to-Action Workflow
--------------------------------------------------------------------------------
✅ EventRelay processing complete
   📊 Category: Tutorial
   📋 Actions: 12
   💻 Project scaffold generated

🚀 STAGE 3: Project Deployment
--------------------------------------------------------------------------------
✅ GitHub deployment successful
   📦 Repository: https://github.com/UVAI/codex-vs-claude-tutorial
   🌐 Live URL: https://codex-vs-claude.vercel.app

🔒 STAGE 4: UVAI Codex Validation & Deployment
--------------------------------------------------------------------------------
✅ UVAI Codex validation complete
   🔒 Security score: 9.2/10
   📊 Quality score: 8.5/10
   🌐 Production URL: https://codex-vs-claude-tutorial.fly.dev

================================================================================
✅ PIPELINE COMPLETE
================================================================================
⏱️  Total processing time: 127.34s
📊 Stages completed: 4

🚀 DEPLOYED SERVICES:
   • GITHUB: https://github.com/UVAI/codex-vs-claude-tutorial
   • VERCEL: https://codex-vs-claude.vercel.app
   • FLY: https://codex-vs-claude-tutorial.fly.dev

💰 REVENUE POTENTIAL:
   • Estimated monthly: $500-2000
   • Service type: SaaS/API

================================================================================

📄 Full results saved to: results_20251018_165432.json
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | For Gemini mode | Enhanced video understanding |
| `GITHUB_TOKEN` | For deployment | Auto-deploy to GitHub |
| `YOUTUBE_API_KEY` | Optional | EventRelay video fetching |

### API Keys Setup

**Gemini API Key:**
1. Visit: https://aistudio.google.com/app/apikey
2. Generate API key
3. Add to environment: `export GEMINI_API_KEY="your-key"`

**GitHub Token:**
1. Visit: https://github.com/settings/tokens
2. Generate token with `repo` and `workflow` permissions
3. Add to environment: `export GITHUB_TOKEN="your-token"`

---

## 🎓 Advanced Usage

### Analysis Only (No Deployment)

```bash
python3 universal_coordinator.py "URL" --no-deploy
```

### Custom GitHub Token

```bash
python3 universal_coordinator.py "URL" --github-token "ghp_customtoken123"
```

### Custom Gemini Key

```bash
python3 universal_coordinator.py "URL" --gemini-key "AIza_customkey456"
```

---

## 🐛 Troubleshooting

### Error: "Gemini processor not available"

**Solution:**
```bash
pip3 install google-genai google-auth
```

### Error: "EventRelay not available"

**Cause:** EventRelay project not at expected path

**Solution:**
```bash
# Verify path
ls /Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/src/
```

### Error: "UVAI deployer not available"

**Cause:** UVAI project not at expected path

**Solution:**
```bash
# Verify path
ls /Users/garvey/Dev/OpenAI_Hub/projects/UVAI/src/
```

### Error: "GitHub token not configured"

**Solution:**
```bash
export GITHUB_TOKEN="your-token-here"
# Or pass via CLI
python3 universal_coordinator.py "URL" --github-token "your-token"
```

### Gemini API Quota Exceeded

**Error:** `429 RESOURCE_EXHAUSTED`

**Solution:** Use production mode (no Gemini):
```bash
python3 universal_coordinator.py "URL" --mode production
```

---

## 📈 Performance

### Expected Processing Times

| Mode | Typical Duration | Bottleneck |
|------|------------------|------------|
| Gemini only | 30-60s | API calls (10 prompts) |
| Production | 2-5 min | Code generation |
| Hybrid | 2-6 min | Code generation + deployment |

### Optimization Tips

1. **Use `--mode production`** if Gemini quota low
2. **Use `--no-deploy`** for faster analysis-only runs
3. **Run in background** for multiple videos:
   ```bash
   python3 universal_coordinator.py "URL1" &
   python3 universal_coordinator.py "URL2" &
   ```

---

## 💰 Cost Breakdown

### Gemini API Costs (Free Tier)

- **Free tier limit:** 8 hours of video per day
- **Video processing:** ~$0.10 per 10-minute video
- **Daily limit value:** ~$2.88 worth of processing free

### Infrastructure Costs

- **GitHub:** Free for public repos
- **Vercel:** Free tier available
- **Netlify:** Free tier available
- **Fly.io:** Free tier available

**Total cost for 10 videos/day:** ~$0-1.00 (within free tiers)

---

## 🚀 Production Deployment

### Running as Service

```bash
# Create systemd service (optional)
sudo nano /etc/systemd/system/universal-automation.service
```

```ini
[Unit]
Description=Universal Automation Service
After=network.target

[Service]
Type=simple
User=garvey
WorkingDirectory=/Users/garvey/Dev/OpenAI_Hub/universal-automation-service
Environment="GEMINI_API_KEY=your-key"
Environment="GITHUB_TOKEN=your-token"
ExecStart=/usr/bin/python3 universal_coordinator.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Batch Processing

```bash
# Process multiple videos
cat video_urls.txt | while read url; do
  python3 universal_coordinator.py "$url" --mode hybrid
done
```

---

## 📚 Integration with Existing Systems

### With EventRelay

The coordinator automatically integrates with:
- `TranscriptActionWorkflow` → Video processing
- `DeploymentManager` → GitHub + platform deployment

### With UVAI

The coordinator automatically integrates with:
- `UVAICodexUniversalDeployment` → Codex validation
- `InfrastructurePackagingAgent` → Security checks

### With Gemini

The coordinator uses our custom:
- `gemini_video_processor.py` → Enhanced video understanding

---

## ✅ Verification

Test the complete pipeline:

```bash
# 1. Test Gemini
python3 gemini_video_processor.py "https://youtube.com/watch?v=SHORT_VIDEO"

# 2. Test full pipeline
python3 universal_coordinator.py "https://youtube.com/watch?v=SHORT_VIDEO" --mode hybrid

# 3. Check output
cat results_*.json | jq '.stages'
```

---

## 🎯 Next Steps

1. **Process first video** with `--mode hybrid`
2. **Monitor deployed services** at GitHub/Vercel/Fly URLs
3. **Track revenue** from deployed applications
4. **Scale** by processing more videos

---

**Status:** ✅ Ready for production use
**Requirements:** Python 3.9+, Gemini API key, GitHub token
**Output:** Revenue-generating deployed applications
