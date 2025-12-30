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

## 🌐 Deployment (Digital Ocean)
 
 This project uses a standard VPS deployment on Digital Ocean with Docker Compose, Nginx, and Let's Encrypt for SSL.
 
 ### Prerequisites
 - Digital Ocean Droplet (Ubuntu 22.04 LTS)
 - Domain name pointed to Droplet IP
 - SSH access
 
 ### Quick Deploy
 
 ```bash
 # 1. SSH into Droplet
 ssh root@YOUR_DROPLET_IP
 
 # 2. Clone Repository
 git clone https://github.com/samayp42/backend.git .
 
 # 3. Setup Secrets
 cp .env.production .env
 nano .env
 
 # 4. Deploy
 chmod +x deploy-digitalocean.sh
 ./deploy-digitalocean.sh
 ```
 
 See [DEPLOY_DIGITALOCEAN.md](./docs/DEPLOY_DIGITALOCEAN.md) for the complete step-by-step guide including SSL setup and monitoring.
 
 ## 💰 Cost Estimation (Digital Ocean)
 
 | Spec | Cost/Month | Capacity |
 |------|------------|----------|
 | 2GB / 1 vCPU | $12 | ~1,000 compiles/mo |
 | 4GB / 2 vCPU | $24 | ~5,000 compiles/mo |


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
