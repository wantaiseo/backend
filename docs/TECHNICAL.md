# CiteKit — Technical Documentation

> **Version:** 2.0  
> **Last Updated:** December 23, 2024  
> **Status:** ✅ Production Ready  
> **License:** MIT

---

## 🎯 What We've Built

**CiteKit** is a full-stack system that converts any website into an **LLM-native knowledge package**. It helps websites get properly cited by AI models like ChatGPT, Claude, Gemini, and Perplexity.

### Core Output Files

| File | Purpose | Status |
|------|---------|--------|
| `index.html` | **Premium visual dashboard** - Beautiful dark-mode report | ✅ Working |
| `llm.txt` | Canonical instruction document for LLMs | ✅ Working |
| `mcp.json` | Intent-to-endpoint mappings for AI agents | ✅ Working |
| `facts.jsonld` | Schema.org structured data for knowledge graphs | ✅ Working |
| `AUDIT.md` | GEO Score (0-100) with actionable recommendations | ✅ Working |
| `DEPLOY.md` | Platform-specific deployment instructions | ✅ Working |
| `sitemap.json` | Classified page index | ✅ Working |
| `pages/*.json` | Individual page structured data | ✅ Working |
| `BENCHMARK.md` | Competitor comparison (optional) | ✅ Working |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WANTGEO SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│   │   FRONTEND   │────▶│   BACKEND    │────▶│    CELERY    │            │
│   │   (Vite+React)     │   (FastAPI)  │     │   (Workers)  │            │
│   │   Port: 5173  │    │   Port: 8000 │     │   + Redis    │            │
│   └──────────────┘     └──────────────┘     └──────────────┘            │
│          │                    │                    │                     │
│          │                    │                    │                     │
│          │              ┌─────┴─────┐              │                     │
│          │              │ Supabase  │◀─────────────┘                     │
│          └─────────────▶│    DB     │                                    │
│                         │ + Auth    │                                    │
│                         └───────────┘                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Processing Pipeline:
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ DISCOVER │──▶│ EXTRACT  │──▶│ CLASSIFY │──▶│SYNTHESIZE│──▶│ PACKAGE  │
│ (URLs)   │   │ (Content)│   │ (Gemini) │   │ (Gemini) │   │  (ZIP)   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
     5%            30%            50-60%         70-85%         100%
```

---

## 🛠️ Technology Stack

### Backend (Python)

| Component | Technology | File(s) |
|-----------|------------|---------|
| **API Framework** | FastAPI | `main.py` |
| **Authentication** | Supabase Auth | `auth.py` |
| **Job Queue** | Celery + Redis | `celery_app.py`, `tasks.py` |
| **Database** | Supabase (PostgreSQL) | `database.py` |
| **URL Discovery** | Custom + aiohttp | `discovery.py` |
| **Content Extraction** | Trafilatura + Playwright | `extractor.py` |
| **Classification** | Google Gemini | `classifier.py` |
| **LLM Generation** | Google Gemini 2.5 Flash | `synthesizer.py` |
| **Audit Engine** | Custom scoring | `auditor.py` |
| **Benchmarking** | Custom | `benchmark.py` |
| **Packaging** | Custom + HTML templates | `packager.py` |
| **Models** | Pydantic v2 | `models.py` |

### Frontend (React)

| Component | Technology | File(s) |
|-----------|------------|---------|
| **Framework** | React 18 + Vite | `frontend/` |
| **Styling** | Tailwind CSS | `index.css` |
| **Animations** | Framer Motion | Throughout |
| **Routing** | React Router | `App.jsx` |
| **Auth Context** | React Context | `AuthContext.jsx` |
| **API Client** | Fetch | `lib/api.js` |

---

## ✅ What's Working

### 1. **Full Authentication System**
- User signup/login via Supabase
- JWT token management
- Protected API endpoints
- Persistent sessions

### 2. **Premium Landing Page**
- Dark monochrome aesthetic
- Typewriter animation headline
- Multi-LLM citation demo (ChatGPT, Gemini, Perplexity, Claude)
- Responsive design
- Scroll-based animations

### 3. **User Dashboard**
- Job history with status
- Real-time progress tracking
- Download completed packages
- Cancel running jobs

### 4. **Complete Processing Pipeline**

```
Phase 1: DISCOVERY (0-5%)
├── robots.txt parsing
├── Sitemap.xml discovery
├── Homepage link crawling
├── URL normalization (handles www. prefix)
└── Deduplication

Phase 2: EXTRACTION (5-30%)
├── Static HTTP fetch
├── Playwright fallback for JS pages
├── Clean text extraction (Trafilatura)
├── Title/description/headings
└── Word count analysis

Phase 3: CLASSIFICATION (30-50%)
├── Batched API calls (5 pages/request)
├── Page type classification
├── Intent classification
├── Topic extraction
└── Confidence scoring

Phase 4: SYNTHESIS (50-85%)
├── llm.txt generation (Gemini)
├── mcp.json generation (Gemini)
├── facts.jsonld generation (Gemini)
└── Fallback handling

Phase 5: AUDIT (85-90%)
├── Content quality scoring (0-25)
├── Metadata completeness (0-25)
├── Structure clarity (0-25)
├── LLM readiness (0-25)
├── Issue detection
└── Recommendations

Phase 6: PACKAGING (90-100%)
├── HTML report generation (index.html)
├── ZIP creation
├── File organization
└── Job completion
```

### 5. **HTML Report Dashboard**
- Premium dark-mode UI
- Animated score circle
- Score breakdown cards
- Issue list with severity indicators
- Site statistics
- File links
- Next steps recommendations

### 6. **URL Normalization**
- Handles `www.oizom.com` → `https://www.oizom.com`
- Handles `oizom.com` → `https://oizom.com`
- Passes through full URLs unchanged

---

## 📂 File Structure

```
wantgeo.com/
├── main.py              # FastAPI app, routes
├── auth.py              # Supabase auth endpoints
├── tasks.py             # Celery task definitions
├── celery_app.py        # Celery configuration
├── config.py            # Settings (env vars)
├── database.py          # Supabase client
├── models.py            # Pydantic data models
├── discovery.py         # URL discovery engine
├── extractor.py         # Content extraction
├── classifier.py        # Gemini classification
├── synthesizer.py       # LLM content generation
├── auditor.py           # GEO score calculation
├── benchmark.py         # Competitor analysis
├── packager.py          # ZIP generation + HTML report
│
├── templates/
│   └── report.html      # HTML dashboard template
│
├── output/              # Generated packages
│   └── {domain}-geo.zip
│
├── frontend/            # React application
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Landing.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Login.jsx
│   │   │   └── Signup.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   └── ui/
│   │   ├── lib/
│   │   │   └── api.js
│   │   └── context/
│   │       └── AuthContext.jsx
│   └── package.json
│
├── requirements.txt
├── .env                 # Environment variables
└── TECHNICAL.md         # This file
```

---

## 🔌 API Endpoints

### Authentication

```http
POST /auth/signup
Content-Type: application/json
{"email": "user@example.com", "password": "password123"}
→ {"access_token": "...", "refresh_token": "...", "user": {...}}

POST /auth/login
Content-Type: application/json
{"email": "user@example.com", "password": "password123"}
→ {"access_token": "...", "refresh_token": "...", "user": {...}}
```

### Compilation

```http
POST /compile
Authorization: Bearer {token}
Content-Type: application/json
{
  "url": "stripe.com/docs",  # Can be with or without https://
  "crawl_depth": "shallow",  # shallow (20), auto (50), deep (100)
  "competitors": []          # Optional competitor URLs
}
→ {"job_id": "uuid", "status": "pending", "message": "..."}

GET /status/{job_id}
→ {"job_id": "...", "status": "completed", "progress": 100, 
   "total_pages": 20, "geo_score": 54, "result_path": "output/..."}

GET /download/{job_id}
Authorization: Bearer {token}
→ (ZIP file download)

GET /preview/{job_id}
→ {"structure": "...", "content": {...}, "facts": {...}}

POST /cancel/{job_id}
Authorization: Bearer {token}
→ {"message": "Job cancelled"}

GET /jobs
Authorization: Bearer {token}
→ [{"job_id": "...", "status": "...", ...}, ...]
```

---

## 🔧 Environment Configuration

```env
# Required
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional (with defaults)
GEMINI_MODEL=gemini-2.5-flash
REDIS_URL=redis://localhost:6379/0
OUTPUT_DIR=./output
```

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis server
- Gemini API key
- Supabase project

### Start All Services

```bash
# Terminal 1: Redis
redis-server --daemonize yes

# Terminal 2: Celery Worker
source venv/bin/activate
celery -A celery_app worker --loglevel=info

# Terminal 3: Backend API
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Frontend
cd frontend
npm run dev
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📊 GEO Score Breakdown

| Component | Max Points | What It Measures |
|-----------|------------|------------------|
| **Content Quality** | 25 | Word count, thin content (<50 words), average page length |
| **Metadata Completeness** | 25 | Titles, descriptions, headings, H1 hierarchy |
| **Structure Clarity** | 25 | URL patterns, page type diversity, duplicate detection |
| **LLM Readiness** | 25 | Classification confidence, topic coverage, critical pages |

### Score Tiers

| Score | Label | Description |
|-------|-------|-------------|
| 80-100 | 🟢 Excellent | Highly optimized for AI discovery |
| 60-79 | 🔵 Good | Well-prepared with room to improve |
| 40-59 | 🟠 Fair | Basic readiness, address issues |
| 0-39 | 🔴 Needs Work | Significant improvements needed |

---

## 💰 Cost Analysis

### Per Job (50 pages)

| Component | Cost |
|-----------|------|
| Classification (10 batches) | ~$0.002 |
| llm.txt generation | ~$0.001 |
| mcp.json generation | ~$0.001 |
| facts.jsonld generation | ~$0.001 |
| **Total LLM** | **~$0.005** |
| Server compute | ~$0.05 |
| Database transactions | ~$0.01 |
| **Total Cost** | **~$0.07** |

### Pricing Model

| | Amount |
|---|--------|
| Revenue per package | $5.00 |
| Total costs | ~$0.07 |
| **Gross Margin** | **98.6%** |

---

## 🔜 Roadmap

### Completed ✅
- [x] Full authentication system
- [x] Premium landing page UI
- [x] Complete processing pipeline
- [x] HTML visual report
- [x] URL normalization (www handling)
- [x] facts.jsonld generation
- [x] GEO score with breakdown
- [x] User dashboard
- [x] Job management (cancel, download)

### In Progress 🚧
- [ ] Production deployment (Vercel + Railway)
- [ ] Stripe payment integration
- [ ] Usage quotas and limits

### Future 📋
- [ ] Incremental updates (diff-based)
- [ ] Multi-language support
- [ ] WordPress/CMS plugins
- [ ] Citation analytics
- [ ] Custom MCP schemas

---

## 🧪 Testing

### Test Account
```
Email: demo@wantgeo.com
Password: demo1234
```

### Test Flow
1. Go to http://localhost:5173
2. Log in with test account
3. Enter URL: `stripe.com/docs`
4. Select "Shallow" depth
5. Click Compile
6. Wait for completion (~2-3 min)
7. Download ZIP
8. Open `index.html` in browser

---

## 📝 Key Files to Know

| File | What It Does |
|------|--------------|
| `main.py` | All API routes, FastAPI setup |
| `tasks.py` | Celery job orchestration, pipeline flow |
| `synthesizer.py` | Gemini prompts for llm.txt, mcp.json, facts.jsonld |
| `auditor.py` | GEO score calculation logic |
| `packager.py` | ZIP creation, HTML report generation |
| `templates/report.html` | HTML dashboard template |
| `frontend/src/pages/Landing.jsx` | Landing page UI |
| `frontend/src/pages/Dashboard.jsx` | User dashboard |
| `frontend/src/lib/api.js` | API client functions |

---

## 🐛 Known Issues

1. **Oizom.com fails** - JS-heavy site, Playwright needed but extraction still empty
2. **Gemini 429 errors** - API quota limits, need to wait or use different key
3. **Long synthesis times** - Gemini can take 20+ seconds for large sites

---

## 📞 Support

- **Backend Logs**: Check Celery worker terminal
- **API Docs**: http://localhost:8000/docs
- **Frontend Dev**: http://localhost:5173 (hot reload)

---

*Built with ❤️ by WANTGEO Team — December 2024*
