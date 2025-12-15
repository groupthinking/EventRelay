# Quick Start: API Key Setup

This guide walks you through setting up your EventRelay environment in under 5 minutes.

## Step 1: Clone and Install

```bash
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev,youtube,ml]
```

## Step 2: Setup API Keys (Interactive)

```bash
python3 scripts/setup_env.py
```

Follow the prompts:

1. **Google Gemini API** (Primary - Recommended)
   - Visit: https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Copy and paste when prompted

2. **OpenAI API** (Alternative)
   - Visit: https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy and paste when prompted

3. **YouTube API** (Optional but Recommended)
   - Visit: https://console.cloud.google.com/apis/credentials
   - Create credentials → API key
   - Enable YouTube Data API v3
   - Copy and paste when prompted

## Step 3: Validate Configuration

```bash
python3 scripts/validate_env.py
```

You should see:
```
✅ Environment validation passed!

Configured API keys:
  ✓ GEMINI_API_KEY: AIzaSyABC...
  ✓ YOUTUBE_API_KEY: AIzaSyXYZ...

You're ready to run the application!
```

## Step 4: Start the Application

```bash
# Terminal 1 - Backend
uvicorn uvai.api.main:app --reload --port 8000

# Terminal 2 - Frontend
npm start --prefix frontend
```

## Optional: Monitor .env Changes

During development, you can monitor your `.env` file for changes:

```bash
python3 scripts/monitor_env.py
```

This will automatically validate your configuration whenever you update `.env`.

## Troubleshooting

### "No valid AI provider key found"

You need at least ONE of:
- `GEMINI_API_KEY` (recommended)
- `OPENAI_API_KEY`

Run `python3 scripts/setup_env.py` to add them.

### "API key format looks incorrect"

Check that you copied the entire key without extra spaces or newlines.

### Scripts not executable

```bash
chmod +x scripts/setup_env.py scripts/validate_env.py scripts/monitor_env.py
```

## Next Steps

- Read [Environment Monitoring Guide](ENV_MONITORING.md) for advanced features
- Check [AGENTS.md](../AGENTS.md) for contributor guidelines
- Visit API documentation at http://localhost:8000/docs

## Need Help?

- Review `.env.example` for all available configuration options
- Check existing issues on GitHub
- Run validation with verbose output: `python3 scripts/validate_env.py`
