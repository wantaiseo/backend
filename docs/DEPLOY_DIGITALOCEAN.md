# CiteKit - Digital Ocean Droplet Deployment Guide

## Overview

This guide covers deploying CiteKit backend to a Digital Ocean Droplet (VPS).

**Recommended Droplet Specs:**
- **Size:** 2GB RAM / 1 vCPU minimum (4GB/2vCPU recommended)
- **OS:** Ubuntu 22.04 LTS
- **Region:** Choose closest to your users
- **Cost:** ~$12-24/month

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         Digital Ocean Droplet       │
                    │                                     │
Internet ──────────▶│  ┌─────────┐   ┌─────────────────┐  │
  :80/:443          │  │  Nginx  │──▶│  FastAPI (API)  │  │
                    │  │  + SSL  │   └─────────────────┘  │
                    │  └─────────┘            │           │
                    │                         │           │
                    │      ┌──────────────────┘           │
                    │      ▼                              │
                    │  ┌─────────┐   ┌─────────────────┐  │
                    │  │  Redis  │◀──│  Celery Worker  │  │
                    │  └─────────┘   └─────────────────┘  │
                    │                                     │
                    └─────────────────────────────────────┘
```

## Quick Start

### 1. Create Droplet

1. Go to [Digital Ocean](https://cloud.digitalocean.com)
2. Create Droplet → **Ubuntu 22.04** → **Basic** → **Regular SSD**
3. Choose **$12/mo (2GB RAM)** or **$24/mo (4GB RAM)**
4. Add your SSH key
5. Create Droplet

### 2. Point Domain to Droplet

Add an A record in your DNS:
```
Type: A
Name: api (or @ for root)
Value: YOUR_DROPLET_IP
TTL: 300
```

### 3. Initial Server Setup

SSH into your droplet and run the setup script:

```bash
ssh root@YOUR_DROPLET_IP

# Download and run setup script
curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/backend/deploy/setup-droplet.sh | bash
```

Or manually:
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | bash
apt install docker-compose-plugin -y

# Create app directory
mkdir -p /home/citekit/app
cd /home/citekit/app
```

### 4. Clone and Configure

```bash
cd /home/citekit/app

# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# Or upload files manually
scp -r backend/* root@YOUR_DROPLET_IP:/home/citekit/app/

# Create environment file
cp .env.production .env
nano .env  # Fill in your secrets
```

### 5. Update Domain in Nginx Config

```bash
# Replace YOUR_DOMAIN.com with your actual domain
nano nginx/conf.d/api.conf
```

### 6. Deploy

```bash
chmod +x deploy-digitalocean.sh
./deploy-digitalocean.sh
```

### 7. Setup SSL (Let's Encrypt)

```bash
chmod +x deploy/setup-ssl.sh
./deploy/setup-ssl.sh api.yourdomain.com your@email.com
```

## File Structure

```
backend/
├── docker-compose.production.yml  # Production compose file
├── Dockerfile.production          # Production Dockerfile
├── deploy-digitalocean.sh         # Main deploy script
├── .env.production                # Environment template
├── nginx/
│   ├── nginx.conf                 # Nginx main config
│   └── conf.d/
│       └── api.conf               # API server config
└── deploy/
    ├── setup-droplet.sh           # Initial server setup
    └── setup-ssl.sh               # SSL certificate setup
```

## Operations

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f worker
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.production.yml restart

# Specific service
docker-compose -f docker-compose.production.yml restart api
```

### Update Deployment
```bash
git pull origin main
./deploy-digitalocean.sh
```

### Check Status
```bash
docker-compose -f docker-compose.production.yml ps
```

### Shell into Container
```bash
docker-compose -f docker-compose.production.yml exec api bash
```

## Monitoring

### Basic Health Check
```bash
curl http://YOUR_DOMAIN/health/live
```

### System Resources
```bash
htop
docker stats
```

### Disk Usage
```bash
df -h
docker system df
```

### Clean Up
```bash
# Remove unused Docker resources
docker system prune -a
```

## Troubleshooting

### API Not Starting
```bash
docker-compose -f docker-compose.production.yml logs api
```

### Worker Not Processing Jobs
```bash
docker-compose -f docker-compose.production.yml logs worker
docker-compose -f docker-compose.production.yml exec redis redis-cli ping
```

### SSL Certificate Issues
```bash
# Check certificate
docker-compose -f docker-compose.production.yml exec nginx ls -la /etc/letsencrypt/live/

# Force renewal
docker-compose -f docker-compose.production.yml run --rm certbot renew --force-renewal
docker-compose -f docker-compose.production.yml restart nginx
```

### Out of Memory
```bash
# Check memory
free -h

# Check swap
swapon --show

# Add more swap (if needed)
fallocate -l 4G /swapfile2
chmod 600 /swapfile2
mkswap /swapfile2
swapon /swapfile2
```

## Cost Breakdown

| Component | Cost/Month |
|-----------|------------|
| Droplet (2GB) | $12 |
| Droplet (4GB) | $24 |
| Backups (optional) | +20% |
| **Total** | **$12-30** |

*Much cheaper than Cloud Run at scale!*

## Security Checklist

- [ ] SSH key authentication (disable password auth)
- [ ] Firewall enabled (UFW)
- [ ] SSL/TLS enabled
- [ ] Environment variables secured
- [ ] Regular security updates (`unattended-upgrades`)
- [ ] Backup strategy in place
