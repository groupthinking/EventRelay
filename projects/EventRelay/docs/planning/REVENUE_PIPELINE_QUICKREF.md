# Revenue Pipeline Quick Reference

**One-Page Guide** | [Full Documentation](REVENUE_PIPELINE_TESTING.md)

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Setup environment
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev,youtube,ml]

# 2. Configure API keys
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here

# 3. Verify setup
python3 scripts/check_revenue_pipeline_prerequisites.py

# 4. Run test
python3 scripts/test_revenue_pipeline.py
```

---

## 📋 Prerequisites Checklist

- [ ] Python 3.9+
- [ ] 5GB+ disk space
- [ ] At least one API key: `GEMINI_API_KEY` or `GOOGLE_API_KEY` or `OPENAI_API_KEY`
- [ ] `.env` file created from `.env.example`
- [ ] Dependencies installed: `pip install -e .[dev,youtube,ml]`
- [ ] (Optional) Vercel CLI for deployment: `npm i -g vercel`

---

## 🎯 What It Does

```
YouTube URL → Video Processing → AI Code Generation → Deployment
     ↓              ↓                    ↓                ↓
  Extract ID    Get transcript      Generate code    Deploy to web
  Fetch meta    AI analysis         85+ files        Live URL
```

**Duration**: 30-60 seconds (generation) | 5-10 minutes (with deployment)  
**Cost**: $0.001-0.01 per video (Gemini) | $0.19-0.23 (OpenAI)

---

## 🤖 Custom Agents

Use `@agent-name` in GitHub Copilot Chat:

| Agent | Use For | Example |
|-------|---------|---------|
| **@python-backend** | FastAPI, async, DB | `@python-backend Create new API endpoint` |
| **@frontend** | React, hooks, TS | `@frontend Build video player component` |
| **@testing** | Unit, integration tests | `@testing Write tests for processor` |
| **@mcp** | MCP tools, agents | `@mcp Implement MCP tool` |
| **@documentation** | Docs, guides | `@documentation Document API endpoint` |
| **@video-processing** | Video, transcripts | `@video-processing Extract events` |

---

## 🛠️ Common Commands

```bash
# Check prerequisites
python3 scripts/check_revenue_pipeline_prerequisites.py

# Test pipeline (no deployment)
python3 scripts/test_revenue_pipeline.py

# Use generated project
cd /path/to/generated/project
npm install && npm run dev

# Deploy to production
vercel --prod
```

---

## ⚠️ Troubleshooting

| Error | Solution |
|-------|----------|
| **Missing API key** | Add to `.env`: `GEMINI_API_KEY=your_key` |
| **Module not found** | `pip install -e .[dev,youtube,ml]` |
| **No disk space** | Free 5GB: `pip cache purge` |
| **Port in use** | `lsof -i :8000` then kill process |
| **Vercel not found** | Optional: `npm i -g vercel` |

---

## 📊 Expected Output

```
✅ Status: SUCCESS
📺 Video: Next.js Tutorial
📁 Project: /tmp/generated_projects/nextjs-abc123
⏱️ Duration: 45.23 seconds

📦 Steps Completed:
  ✅ Video Processing
  ✅ Code Generation
  ⏭️ Deployment (optional)

🚀 Next Steps:
  1. cd /tmp/generated_projects/nextjs-abc123
  2. npm install
  3. npm run dev
```

---

## 📚 Documentation Links

- **[REVENUE_PIPELINE_TESTING.md](REVENUE_PIPELINE_TESTING.md)** - Complete guide
- **[REVENUE_PIPELINE.md](REVENUE_PIPELINE.md)** - Architecture
- **[README.md](README.md)** - Project overview
- **[.github/agents/](.github/agents/)** - Custom agents

---

## 💰 API Costs

| Provider | Cost/Video | Speed | Recommended |
|----------|-----------|-------|-------------|
| **Gemini** | $0.001-0.006 | Fast | ✅ Yes |
| OpenAI | $0.19-0.23 | Fast | For variety |
| AssemblyAI | $0.15-0.37 | Medium | Alternative |

---

## 🎓 Learning Path

1. ✅ Set up environment and API keys
2. ✅ Run prerequisite checker
3. ✅ Test with sample video
4. ✅ Explore generated code
5. ✅ Try custom agents
6. ✅ Deploy to production

---

**Need Help?** Check [REVENUE_PIPELINE_TESTING.md](REVENUE_PIPELINE_TESTING.md) for detailed troubleshooting and examples.
