# DecisionPilot

> Transform meeting recordings into executed Jira tickets automatically.

[![AWS Nova](https://img.shields.io/badge/AWS-Nova-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## What It Does

DecisionPilot is an AI pipeline that converts a raw meeting recording into structured Jira tickets automatically.

Instead of summarizing meetings, it extracts decisions, action items, risks, and open questions — and determines what should actually happen next.

Upload a meeting recording and optional slides or whiteboard screenshots. Within 60 seconds:

- **Decisions, action items, risks, and open questions** extracted with speaker attribution
- **Slides and screenshots** analyzed via Nova vision — capturing commitments written but never spoken
- Each action item **confidence-scored across 4 dimensions**: action clarity, ownership certainty, evidence strength, deadline presence
- Items routed to **AUTO** (Jira ticket created), **REVIEW** (queued for approval), or **CLARIFY** (generates the exact question needed)
- **Meeting health score** (0–100, grade A–F) for every meeting

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS credentials with Bedrock access

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
uvicorn main:app --port 8001 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`  
API docs at `http://localhost:8001/docs`

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

JIRA_URL=https://your-workspace.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=DEV

MOCK_MODE=false   # set true to run without AWS/Jira
```

---

## Pipeline

```
Upload (audio + optional slides/screenshots)
         ↓
AWS Transcribe — speaker diarization
         ↓
Nova Lite Vision — slide & whiteboard analysis
         ↓
Nova Lite — extraction (decisions, actions, risks, questions)
         ↓
Deterministic evidence linker + quality gate
         ↓
Nova Lite — confidence scoring (4 dimensions)
         ↓
Health score engine
         ↓
Execution router → Jira REST API
```

---

## Project Structure

```
decisionpilot/
├── backend/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── extractor_agent.py
│   │   └── slide_analysis_agent.py
│   ├── main.py
│   ├── confidence_scorer.py
│   ├── execution_router.py
│   ├── health_score_engine.py
│   ├── quality_gate.py
│   ├── transcription_service.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Upload page
│   │   └── analysis/[id]/   # Results dashboard
│   └── package.json
└── scripts/
    ├── verify_aws.py
    └── check_setup.sh
```

---

## Tech Stack

- **Amazon Nova Lite** — extraction, confidence scoring, multimodal vision
- **AWS Transcribe** — multi-speaker diarization
- **FastAPI** — backend pipeline
- **Next.js 15** — frontend
- **Jira REST API** — ticket creation
- **pdf2image + Pillow** — slide-to-image conversion

---

## License

MIT
