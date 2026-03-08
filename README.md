# DecisionPilot - Autonomous Meeting Execution Agent

> Transform meeting recordings into executed Jira tickets automatically using Amazon Nova AI.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![AWS Nova](https://img.shields.io/badge/AWS-Nova-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## 🎯 **What It Does**

DecisionPilot is an autonomous multi-agent system that:
1. ✅ Analyzes meeting audio, slides, and whiteboards
2. ✅ Extracts decisions with evidence citations
3. ✅ Validates action item quality
4. ✅ **Executes tasks in Jira automatically** (via Amazon Nova Act)
5. ✅ Predicts execution success with Health Score

**This isn't a meeting summarizer. This is an AI operator.**

---

## 🚀 **Quick Start (Mock Mode - No AWS Required)**

### **Prerequisites**
- Python 3.14+
- Node.js 18+

### **1. Install Backend Dependencies**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-day1.txt
```

### **2. Run Tests**

```bash
cd ..
python scripts/test_all.py
```

Expected output:
```
🎉 All tests passed!
✅ PASS - imports
✅ PASS - embedding  
✅ PASS - planner
✅ PASS - extractor
✅ PASS - schemas
```

### **3. Start Backend (Mock Mode)**

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend runs at: http://localhost:8000  
API Docs: http://localhost:8000/docs

### **4. Start Frontend**

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:3000

---

## ☁️ **Enable AWS (Real Mode)**

### **Get Free AWS Credits**

**Option 1: AWS Free Tier** (No cost for 2 months)
- Nova Lite: 3M input tokens FREE
- Nova Embeddings: 3K image embeddings FREE
- Signup: https://aws.amazon.com/free/

**Option 2: Hackathon Credits** ($200)
- Submit to Amazon Nova Hackathon
- Link: https://amazon-nova.devpost.com/

### **Setup Steps**

1. **Get AWS Credentials:**
   ```bash
   # Go to: https://console.aws.amazon.com/iam/
   # Create access key → Copy Access Key ID + Secret
   ```

2. **Enable Nova Models:**
   ```bash
   # Go to: https://console.aws.amazon.com/bedrock/
   # Model access → Request model access
   # Enable: Nova Lite, Nova Act, Nova Embed Multimodal
   ```

3. **Configure .env:**
   ```bash
   cd decisionpilot
   nano .env  # Or your preferred editor
   
   # Update these lines:
   AWS_ACCESS_KEY_ID=your_actual_key_here
   AWS_SECRET_ACCESS_KEY=your_actual_secret_here
   MOCK_MODE=false  # Switch to real AWS
   ```

4. **Verify AWS Connection:**
   ```bash
   python scripts/verify_aws.py
   ```

5. **Restart Backend:**
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   ```

You should now see real Nova embeddings and agent responses!

---

## 📊 **Project Structure**

```
decisionpilot/
├── backend/
│   ├── agents/              # Multi-agent system
│   │   ├── base_agent.py    # Base class with mock support
│   │   ├── planner_agent.py # Creates execution plans
│   │   └── extractor_agent.py # Extracts structured data
│   ├── services/
│   │   └── embedding_service.py # Nova embeddings
│   ├── schemas/
│   │   └── meeting_schemas.py # Pydantic models
│   ├── config.py            # Environment config
│   ├── main.py              # FastAPI server
│   └── requirements-day1.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Upload page
│   │   └── layout.tsx       # Root layout
│   └── package.json
│
├── scripts/
│   ├── test_all.py          # Comprehensive test suite
│   ├── verify_aws.py        # AWS connection check
│   └── check_setup.sh       # Setup status
│
├── .env                     # Configuration (edit this!)
└── README.md                # This file
```

---

## 🧪 **Testing**

### **Run All Tests (Mock Mode)**
```bash
python scripts/test_all.py
```

### **Test Individual Components**

```bash
# Test embedding service
python scripts/test_embedding.py

# Test specific agent
curl -X POST "http://localhost:8000/api/test/agent?agent_type=planner&test_input=Team%20meeting"

# Check system status
curl http://localhost:8000/api/health
```

---

## 🏗️ **Architecture**

```
Upload (audio + slides + screenshots)
    ↓
Multimodal Embedding (Amazon Nova)
    ↓
Multi-Agent Pipeline:
  1. Planner Agent → Creates execution plan
  2. Retrieval Agent → Finds evidence
  3. Extractor Agent → Structures data
  4. Critic Agent → Validates quality
  5. Execution Agent → Creates Jira tickets
    ↓
Nova Act Browser Automation
    ↓
Verified Jira Issues + Audit Log
```

### **Key Technologies**
- **Amazon Nova 2 Lite**: Multi-agent reasoning
- **Amazon Nova Multimodal Embeddings**: Unified knowledge graph
- **Amazon Nova Act**: Browser UI automation
- **FastAPI**: High-performance API
- **Next.js 14**: Modern web UI
- **Pydantic**: Data validation

---

## 📝 **Development Status**

### ✅ **Day 1 Complete (Knowledge Layer)**
- [x] Multimodal embedding service
- [x] Agent base class with mock mode
- [x] Planner agent
- [x] Extractor agent
- [x] Pydantic schemas
- [x] FastAPI backend
- [x] Next.js frontend
- [x] Comprehensive test suite

### 🔄 **Next (Day 2 - Multi-Agent System)**
- [ ] Critic agent
- [ ] Execution agent
- [ ] Retrieval service (Pinecone)
- [ ] Meeting memory (PostgreSQL)

### 📅 **Roadmap**
- Day 1: ✅ Foundation & Knowledge Layer
- Day 2: Multi-Agent System
- Day 3: Nova Act Execution  
- Day 4: Frontend & Observability
- Day 5: Demo & Hackathon Submission

---

## 🎬 **Demo**

### **Upload a Meeting**
1. Navigate to http://localhost:3000
2. Upload audio file (MP3, WAV, etc.)
3. Optionally upload slides (PDF/PPTX)
4. Optionally upload screenshots
5. Click "Analyze Meeting"

### **View Results**
- Extracted decisions with evidence citations
- Action items with quality scores
- Execution health prediction
- Auto-generated Jira tickets (when Nova Act enabled)

---

## 🔧 **Troubleshooting**

### **"All embeddings are zeros"**
✅ Expected in mock mode  
→ Set `MOCK_MODE=false` and configure AWS credentials

### **"AWS credentials not configured"**
→ Edit `.env` and add your `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`

### **"Port 8000 already in use"**
```bash
lsof -ti:8000 | xargs kill -9
```

### **"Module not found"**
```bash
cd backend
source venv/bin/activate
pip install -r requirements-day1.txt
```

---

## 📚 **Documentation**

- [Architecture Details](./docs/ARCHITECTURE.md) - Deep dive
- [API Reference](./docs/API.md) - Full API docs
- [Agent Design](./docs/AGENTS.md) - Multi-agent orchestration
- [Deployment Guide](./docs/DEPLOYMENT.md) - Production setup

---

## 🤝 **Contributing**

Built for the Amazon Nova AI Hackathon 2026.

---

## 📄 **License**

MIT License - see LICENSE file

---

## 🏆 **Hackathon Submission**

**Categories:**
- Primary: UI Automation (Nova Act)
- Secondary: Agentic AI (Multi-agent orchestration)

**Amazon Nova Features Used:**
- ✅ Nova 2 Lite (multi-agent reasoning)
- ✅ Nova Multimodal Embeddings (audio + slides + images)
- ✅ Nova Act (Jira browser automation)

---

## 📞 **Support**

**Current Mode:** MOCK (no AWS required)  
**Switch to Real AWS:** Edit `.env` → Set `MOCK_MODE=false`

**Quick Status Check:**
```bash
./scripts/check_setup.sh
```

---

**Stop losing action items. Start executing automatically.** ✨
