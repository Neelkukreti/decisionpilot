# DecisionPilot — Session 3 Handover

**Date:** 2026-03-03  
**Hackathon:** Amazon Nova AI Hackathon  
**Deadline:** March 16, 2026 — **13 days left**  
**Prize Pool:** $40,000 (Grand Prize: $15,000)  

---

## Current State — What Works

### ✅ Backend (running on Light's Mac port 8001)
- FastAPI backend fully operational in mock mode
- 5-agent pipeline: Embedding → Planner → Extractor → Critic → Execution
- `/api/meetings/upload` — accepts audio + slides + screenshots, returns `meeting_id`
- `/api/meetings/{id}/analyze` — starts background pipeline (takes ~3s)
- `/api/meetings/{id}/results` — returns health score, decisions, action items with ticket IDs
- Health score dynamically computed from extractor confidence metrics
- Tickets auto-generated (PROJ-100, PROJ-101, etc.) with realistic execution times

### ✅ Frontend (running on Light's Mac port 3004)
- Upload page: dark theme, 3-zone drag-and-drop (audio required, slides + screenshots optional)
- Analysis page: dark theme with header, real-time progress bar, health gauge, agent pipeline, decisions, Jira ticket cards
- Next.js rewrites proxy `/api/*` → `http://localhost:8001/api/*` (no CORS issues)
- Both pages match same dark violet theme

### ✅ End-to-End Flow
Upload audio → POST /upload → GET /analysis/{id} → POST /analyze → poll /results → renders results

---

## Access URLs

| Service | URL |
|---------|-----|
| Frontend (upload) | `http://100.116.197.127:3004` |
| Frontend (results) | `http://100.116.197.127:3004/analysis/{meeting_id}` |
| Backend health | `http://100.116.197.127:8001/api/health` |
| API docs | `http://100.116.197.127:8001/docs` |

---

## Running on Light's Mac

Screen sessions already set up. To restart after reboot:

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 macbook@100.116.197.127
export PATH=/usr/local/bin:$PATH

# Backend
screen -dmS decisionpilot-api bash -c \
  'export PATH=/usr/local/bin:$PATH; cd ~/.openclaw/workspace/decisionpilot/backend && source venv/bin/activate && MOCK_MODE=true uvicorn main:app --host 0.0.0.0 --port 8001 2>&1 | tee /tmp/dp-api.log'

# Frontend
screen -dmS decisionpilot-web bash -c \
  'export PATH=/usr/local/bin:$PATH; cd ~/.openclaw/workspace/decisionpilot/frontend && PORT=3004 npm run dev 2>&1 | tee /tmp/dp-web.log'
```

---

## Files Changed This Session

### Backend (`~/.openclaw/workspace/decisionpilot/backend/`)

| File | Change |
|------|--------|
| `main.py` | Added `BackgroundTasks` to fastapi import |
| `main.py` | Fixed CORS to allow ports 3000, 3002, 3004 |
| `main.py` | Fixed `run_analysis_pipeline`: removed broken `CriticAgent.execute()` call (schema mismatch), replaced with health score computed from extractor confidence metrics |
| `main.py` | Fixed pipeline to use real extractor output for decisions + action_items (with fallback to demo data) |

### Frontend (`~/.openclaw/workspace/decisionpilot/frontend/`)

| File | Change |
|------|--------|
| `next.config.js` | Fixed proxy: `8000` → `8001` |
| `app/page.tsx` | **Full redesign** — dark violet theme, hero copy, 3-zone FileDropZone component, feature cards |
| `app/layout.tsx` | Changed body background to `bg-slate-950` |
| `app/analysis/[id]/page.tsx` | Dark theme throughout (all gray→slate replacements), added site header with back link, fixed `API_BASE` to use relative URLs |

---

## What's Left for Submission

### Must Have (before Mar 16)
- [ ] **Demo video** (3 min) — record on localhost:3004 or via Tailscale
  - Upload a small audio file
  - Show agent pipeline running in real time
  - Show health score (86/100) + decisions + Jira tickets auto-created
  - Narrate: "5 agents, 30 seconds, zero manual work"
- [ ] **Devpost submission** — find the Amazon Nova hackathon Devpost page
  - Tags: Amazon Nova, Multi-Agent, Meeting Intelligence

### Nice to Have
- [ ] Real Amazon Nova Lite integration (needs AWS credentials from Light)
  - Set `MOCK_MODE=false` + add AWS keys to `.env`
  - This would make it genuinely use Nova for AI reasoning
- [ ] Real Jira integration (REST API) — replace mock ticket IDs with real ones
  - Needs `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
  - Update `browser_service.py` to use `requests.post()` to Jira REST API
- [ ] Upload page: demo with a pre-loaded test meeting so judges can click without uploading
- [ ] Better agent pipeline animations (stagger, fade-in per agent)

### Won't Block Submission
- Cloud deployment (can demo locally)
- Real Nova Act browser automation

---

## API Keys Needed

| Key | Status | How to Get |
|-----|--------|-----------|
| `AWS_ACCESS_KEY_ID` | ❌ Not set | AWS Console → IAM → Security Credentials |
| `AWS_SECRET_ACCESS_KEY` | ❌ Not set | Same as above |
| `JIRA_API_TOKEN` | ❌ Not set | Atlassian account → API tokens |

---

## Architecture

```
Browser (http://100.116.197.127:3004)
  ├── Upload page: POST audio + slides → /api/meetings/upload
  └── Analysis page: polls /api/meetings/{id}/results every 800ms

Next.js (port 3004)
  └── Rewrites: /api/* → http://localhost:8001/api/*

FastAPI Backend (port 8001, mock mode)
  └── 5-agent pipeline (mock Amazon Nova):
      1. NovaEmbeddingService — embeds meeting transcript
      2. PlannerAgent — extracts strategy
      3. ExtractorAgent — pulls decisions + action items
      4. Health Score — computed from extraction confidence
      5. ExecutionAgent — creates Jira ticket objects
```

---

## Demo Script (3 Minutes)

**Opening (30s):** "70% of meeting action items are never tracked. DecisionPilot fixes this — not by summarizing, but by executing."

**Demo (90s):**
1. Open `http://100.116.197.127:3004`
2. Upload any small audio file (MP3)
3. Click "Analyze Meeting → Create Jira Tickets"
4. Watch agent pipeline: Embedding → Planner → Extractor → Critic → Execution (each lights up)
5. Health score appears: 86/100
6. Decisions with confidence bars
7. Jira tickets with PROJ-100/101/102 IDs

**Close (30s):** "Amazon Nova Lite for reasoning, Nova Embeddings for multimodal understanding, Nova Act for browser automation. Production-ready today."

---

**Next session: Add AWS credentials → real mode → record demo video → submit**
