# CiteKit - Backend API

**AI-Ready Website Compiler** - Convert any website into LLM-optimized knowledge packages.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Features

- **Website Crawling** - Intelligent discovery of all pages
- **Content Extraction** - Clean text extraction with trafilatura
- **AI Classification** - Gemini-powered page categorization
- **LLM.txt Generation** - Creates AI-readable site summaries
- **Citation Scoring** - Measures AI-readiness (0-100)
- **Razorpay Payments** - Integrated payment gateway
- **Supabase Auth** - Google OAuth authentication

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | Supabase (PostgreSQL) |
| Queue | Celery + Redis |
| AI | Google Gemini |
| Payments | Razorpay |
| Container | Docker |
| Hosting | Cloud Run |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├──────────────┬──────────────┬──────────────┬───────────────┤
│   /compile   │   /status    │    /auth     │   /payments   │
└──────┬───────┴──────┬───────┴──────┬───────┴───────┬───────┘
       │              │              │               │
       ▼              ▼              ▼               ▼
┌─────────────┐ ┌──────────┐ ┌────────────┐ ┌─────────────┐
│ Celery Task │ │ Supabase │ │  Supabase  │ │  Razorpay   │
│   Queue     │ │    DB    │ │    Auth    │ │   Gateway   │
└─────────────┘ └──────────┘ └────────────┘ └─────────────┘
```

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone and enter directory
git clone https://github.com/YOUR_USERNAME/geo-compiler-api.git
cd geo-compiler-api

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Start Redis (required)
# Option A: Docker
docker run -d -p 6379:6379 redis:alpine

# Option B: Local Redis
# Download from https://redis.io/download

# 6. Start Celery Worker (new terminal)
celery -A celery_app worker --loglevel=info

# 7. Start API Server
uvicorn main:app --reload --port 8000
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## 🌐 Deployment (Cloud Run)

### Prerequisites
- Google Cloud account with billing
- Docker Desktop
- gcloud CLI

### Deploy

```bash
# 1. Set your project ID
export GCP_PROJECT_ID="your-project-id"

# 2. Create secrets in GCP
./scripts/setup-secrets.sh

# 3. Deploy
./deploy.sh
```

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed instructions.

## 📁 Project Structure

```
geo-compiler-api/
├── main.py              # FastAPI application
├── config.py            # Settings & environment config
├── models.py            # Pydantic models
├── database.py          # Supabase database layer
├── auth.py              # Authentication routes
├── payments.py          # Razorpay integration
├── tasks.py             # Celery background tasks
├── celery_app.py        # Celery configuration
│
├── discovery.py         # URL discovery engine
├── extractor.py         # Content extraction
├── classifier.py        # AI page classification
├── synthesizer.py       # LLM.txt & MCP generation
├── facts_generator.py   # facts.jsonld v2 (6-step pipeline)
├── packager.py          # ZIP package creation
├── citation_scorer.py   # AI-readiness scoring
├── auditor.py           # Site auditing
├── benchmark.py         # Competitor benchmarking
├── schema_generator.py  # Schema.org generation
│
├── middleware.py        # Rate limiting, validation
├── error_handler.py     # Error handling
│
├── static/              # Static files
├── templates/           # HTML templates
├── tests/               # Test suite
├── docs/                # Documentation
├── scripts/             # Utility scripts
│
├── Dockerfile           # Local Docker build
├── Dockerfile.cloudrun  # Cloud Run optimized
├── Dockerfile.worker    # Celery worker
├── docker-compose.yml   # Local development
├── deploy.sh            # Cloud Run deployment
│
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
├── .env.example         # Environment template
└── README.md            # This file
```


## 🔧 API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Google OAuth redirect |
| GET | `/auth/callback` | OAuth callback |
| GET | `/auth/me` | Get current user |
| POST | `/auth/logout` | Logout |

### Compilation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/compile` | Start compilation job |
| GET | `/status/{job_id}` | Get job status |
| GET | `/preview/{job_id}` | Preview results |
| GET | `/download/{job_id}` | Download ZIP |
| POST | `/cancel/{job_id}` | Cancel job |
| GET | `/jobs` | List user's jobs |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payments/create-order` | Create Razorpay order |
| POST | `/payments/verify` | Verify payment |
| POST | `/payments/webhook` | Razorpay webhook |

## ⚙️ Configuration

All configuration is via environment variables. See [.env.example](.env.example).

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `REDIS_URL` | ✅ | Redis connection URL |
| `RAZORPAY_KEY_ID` | ✅ | Razorpay API key |
| `RAZORPAY_KEY_SECRET` | ✅ | Razorpay secret |
| `FRONTEND_URL` | ✅ | Frontend URL for CORS |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_api.py -v
```

## 💰 Cost Estimation (Cloud Run)

| Compiles/Month | Estimated Cost |
|----------------|----------------|
| 100 | ~$8 |
| 500 | ~$12 |
| 1000 | ~$20 |

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📞 Support

- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/geo-compiler-api/issues)
- Email: support@your-domain.com
