# Deployment Token Setup - Action Items

## Current Status
❌ **Deployment tokens NOT configured**  
✅ Backend server running (http://localhost:8000/)  
✅ Video-to-Software pipeline operational (limited to code generation)  
✅ Skill Mesh pilot running (23 skills, 100% delivery)  

---

## What's Missing
The video-to-software endpoint returns this error:
```json
{
  "deployment": {
    "status": "error",
    "error": "GitHub token not configured"
  }
}
```

**Root cause**: `deployment_manager.py` line 45 pulls from `os.getenv('GITHUB_TOKEN')`

---

## Quick Fix - Manual Token Export

### Option 1: Session Export (Temporary)
```bash
# In the shell running uvicorn:
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export VERCEL_TOKEN="vercel_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Then restart uvicorn (Ctrl+C and rerun startup command)
```

### Option 2: .env File (Persistent)
```bash
cd /Users/garvey/Dev/OpenAI_Hub/projects/EventRelay

# Create .env file:
cat > .env << 'ENVEOF'
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VERCEL_TOKEN=vercel_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
ENVEOF

chmod 600 .env

# Ensure .env is in .gitignore:
echo ".env" >> .gitignore

# Restart uvicorn with .env loaded:
source .env && .venv/bin/python3 -m uvicorn youtube_extension.backend.main:app --reload --port 8000
```

---

## Where to Get Tokens

### GitHub Token
1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "UVAI Video-to-Software Pipeline"
4. Select scope: **repo** (full control)
5. Generate and copy token

### Vercel Token
1. Visit: https://vercel.com/account/tokens
2. Click "Create Token"
3. Name: "UVAI Deployments"
4. Scope: **Full Account**
5. Generate and copy token

---

## Verification Test

Once tokens are set, test with:
```bash
curl -s -X POST http://localhost:8000/api/video-to-software \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "project_type": "web",
    "deployment_target": "vercel",
    "features": ["responsive_design"]
  }' | python3 -m json.tool
```

**Expected successful response**:
```json
{
  "project_name": "...",
  "github_repo": "https://github.com/YOUR_USERNAME/...",
  "live_url": "https://....vercel.app",
  "deployment": {
    "status": "success",
    "platform": "vercel"
  }
}
```

---

## Integration with Pilot

After tokens are configured:
1. Watchdogs will capture deployment metrics
2. Skill mesh can learn deployment error resolutions
3. Full end-to-end demo ready for stakeholders

