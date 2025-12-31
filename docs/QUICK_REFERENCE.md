# EventRelay Integration Quick Reference

## 🎯 Goal
Connect FastAPI backend (port 8000) with Next.js frontend (port 3000) to enable complete EventRelay workflow.

---

## 📊 Current vs Target State

### Current (Broken) 🔴
```
Frontend                Backend
  Mock Data    ⛔        FastAPI
  No API Client          Legacy Endpoints
  No Types               Inconsistent APIs
  
❌ No real integration
❌ Dashboard shows fake data
❌ No video processing workflow
```

### Target (Working) ✅
```
Frontend                    Backend
┌──────────────┐           ┌────────────────┐
│ Next.js :3000│  ←─────→  │ FastAPI :8000  │
│              │   REST    │                │
│ • VideoInput │  ─────→   │ POST /videos   │
│ • Status     │  ←─────   │ GET /status    │
│ • Events     │  ←─────   │ GET /events    │
│ • Agents     │  ←─────   │ GET /agents    │
└──────────────┘           └────────────────┘

✅ Full workflow: URL → Transcript → Events → Results
✅ Real-time status updates
✅ Type-safe communication
```

---

## 🔄 The EventRelay Workflow

```
┌─────────────────┐
│ 1. Paste URL    │  User inputs YouTube link
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Process      │  Backend transcribes video
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Extract      │  AI finds events in transcript
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Dispatch     │  Agents execute tasks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Show Results │  Display outputs to user
└─────────────────┘
```

---

## 📦 What Needs to Be Built

### Backend (Phase 1 - 2-3 days)
```python
# New Endpoints to Create:

POST   /api/v1/videos/process         # Submit YouTube URL
GET    /api/v1/videos/{job_id}/status # Check progress
POST   /api/v1/events/extract         # Extract events
POST   /api/v1/agents/dispatch        # Start agents
GET    /api/v1/agents/{id}/status     # Agent status
GET    /api/v1/health                 # Health check

# Standardized Response Format:
{
  "status": "success",
  "data": { /* payload */ },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123"
}
```

### Frontend (Phase 2 - 1-2 days)
```typescript
// New Services to Create:

services/
├── api-client.ts      // HTTP client with retry
├── video-service.ts   // Video operations
├── event-service.ts   // Event operations
└── agent-service.ts   // Agent operations

types/
├── video.ts           // Video types
├── event.ts           // Event types
└── agent.ts           // Agent types
```

### UI Components (Phase 3 - 3-4 days)
```typescript
// Components to Build:

components/
├── VideoInput.tsx       // URL input form
├── VideoStatus.tsx      // Processing status
├── TranscriptViewer.tsx // Show transcript
├── EventList.tsx        // List events
├── AgentDashboard.tsx   // Agent status
└── ResultsViewer.tsx    // Show outputs
```

---

## 🚀 Implementation Order

### Week 1: Foundation
```
Day 1-2: Backend API
  ✓ Create standardized endpoints
  ✓ Add error handling
  ✓ Update CORS

Day 3: Frontend Services  
  ✓ Create API client
  ✓ Define types
  ✓ Build service layer
```

### Week 2: Integration
```
Day 4-6: UI Components
  ✓ Build video input
  ✓ Build status display
  ✓ Build event list
  ✓ Build agent dashboard

Day 7: State Management
  ✓ Setup Zustand
  ✓ Connect components
```

### Week 3: Polish
```
Day 8-9: Testing
  ✓ Backend tests
  ✓ Frontend tests
  ✓ Integration tests

Day 10: Documentation
  ✓ Update docs
  ✓ Add examples
  ✓ Test deployment
```

---

## 📝 Using the Copilot Prompts

### Step-by-Step Process

1. **Open the prompt file:**
   ```
   docs/prompts/PHASE_1_BACKEND_API.md
   ```

2. **Copy the entire prompt** (e.g., "Prompt 1.1: Define API Response Format")

3. **Paste into your AI assistant** (GitHub Copilot, Claude, etc.)

4. **Follow the implementation steps** provided in the prompt

5. **Test with the examples** at the end of the prompt

6. **Check off the item** in the testing checklist

7. **Move to next prompt**

### Example: Using Prompt 1.1

```
1. Copy from: docs/prompts/PHASE_1_BACKEND_API.md
   Section: "Prompt 1.1: Define API Response Format"

2. Paste into Copilot Chat or Claude

3. It will create:
   - src/youtube_extension/backend/api/v1/models.py
   - APIResponse, ErrorResponse models
   - Complete with validation

4. Test:
   - Run backend
   - Check /docs endpoint
   - Verify models show up

5. ✓ Mark complete and move to Prompt 1.2
```

---

## ✅ How to Know It's Working

### Backend Tests
```bash
# Start backend
uvicorn uvai.api.main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/docs  # Should show OpenAPI docs
curl http://localhost:8000/api/v1/health  # Should return JSON

# Test video processing
curl -X POST http://localhost:8000/api/v1/videos/process \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtube.com/watch?v=auJzb1D-fag"}'
# Should return: {"status": "success", "data": {"job_id": "..."}}
```

### Frontend Tests
```bash
# Start frontend
cd apps/web
npm run dev

# Visit http://localhost:3000
# Should see:
# 1. Video input field
# 2. Can paste YouTube URL
# 3. Shows processing status
# 4. Displays results when done
```

### Integration Test
```
1. Open http://localhost:3000
2. Paste: https://youtube.com/watch?v=auJzb1D-fag
3. Click "Process Video"
4. See progress bar
5. See transcript appear
6. See events listed
7. See agent status
8. See final results

✅ If all 8 steps work = SUCCESS!
```

---

## 🔧 Quick Troubleshooting

### CORS Errors
```
Problem: Frontend can't reach backend
Fix: Check backend main_v2.py has:
  allow_origins=["http://localhost:3000"]
```

### 404 Errors
```
Problem: Endpoint not found
Fix: 
  1. Check endpoint exists in backend
  2. Verify URL is correct in frontend
  3. Check /docs for actual endpoints
```

### Type Errors
```
Problem: TypeScript errors in frontend
Fix:
  1. Ensure types match backend models
  2. Check field names are identical
  3. Verify optional vs required fields
```

### Processing Failures
```
Problem: Video processing fails
Fix:
  1. Check API keys in .env
  2. Verify YouTube URL is valid
  3. Check backend logs for errors
  4. Ensure services are initialized
```

---

## 📚 Documentation Files

### Start Here
- `docs/MASTER_IMPLEMENTATION_GUIDE.md` - **READ THIS FIRST**
- `docs/BACKEND_FRONTEND_INTEGRATION.md` - Detailed tasks

### Implementation Prompts
- `docs/prompts/PHASE_1_BACKEND_API.md` - Backend endpoints
- `docs/prompts/PHASE_2_FRONTEND_SERVICES.md` - Frontend services
- `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` - UI, state, tests, docs

### Reference
- `README.md` - Project overview
- `.env.example` - Environment variables
- `AGENTS.md` - Agent guidelines

---

## 🎯 Success Checklist

### You're Done When...

#### Backend ✓
- [ ] All endpoints return standardized format
- [ ] CORS allows localhost:3000
- [ ] OpenAPI docs complete
- [ ] Tests pass: `pytest tests/ -v`

#### Frontend ✓
- [ ] Can submit YouTube URL
- [ ] Status updates in real-time
- [ ] Events display correctly
- [ ] Agent dashboard works
- [ ] Tests pass: `npm test`

#### Integration ✓
- [ ] Full workflow: URL → Results
- [ ] No CORS errors
- [ ] No 404 errors
- [ ] Error messages are clear
- [ ] Performance <200ms API, <3s page load

---

## 💡 Pro Tips

1. **Work in phases** - Complete Phase 1 before Phase 2
2. **Test often** - Test after each change
3. **Use the prompts** - They have all the details
4. **Check examples** - Working code in prompts
5. **Read logs** - Backend logs show what's wrong
6. **Use DevTools** - Browser console shows frontend issues
7. **Test manually** - Automated tests miss UX issues
8. **Document issues** - Track problems and solutions

---

## 🚦 Getting Started Right Now

```bash
# 1. Read the master guide
open docs/MASTER_IMPLEMENTATION_GUIDE.md

# 2. Setup environment
cp .env.example .env
# Add your API keys

# 3. Start backend
uvicorn uvai.api.main:app --reload --port 8000

# 4. Open Phase 1 prompts
open docs/prompts/PHASE_1_BACKEND_API.md

# 5. Copy Prompt 1.1 and start implementing!
```

---

## 📞 Need Help?

1. **Check troubleshooting** in this guide
2. **Review the prompts** - they have solutions
3. **Check logs** - backend/frontend errors
4. **Read existing code** - look for patterns
5. **Test in isolation** - narrow down the issue

---

**Last Updated:** 2024-12-31  
**Status:** Ready for implementation  
**Estimated Time:** 10-15 days  
**Difficulty:** Intermediate  

**Remember:** You have complete documentation and prompts for every step. Just follow them in order! 🚀
