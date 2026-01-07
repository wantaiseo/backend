---
description: CRITICAL - Read this before making ANY changes to hosting, SSL, nginx, or deployment
---

# ⚠️ HOSTING INFRASTRUCTURE - READ BEFORE EDITING

**STOP. READ THIS ENTIRE FILE BEFORE TOUCHING ANY DEPLOYMENT/HOSTING CODE.**

This file documents the production hosting setup for CiteKit (wantaiseo.com).
Breaking this setup will take the site OFFLINE.

---

## Architecture Overview

```
                    INTERNET
                       │
                       ▼
              ┌─────────────────┐
              │   CLOUDFLARE    │  ← Handles DNS, CDN, DDoS protection
              │   (DNS Proxy)   │  ← SSL Mode: FULL (NOT Flexible)
              └────────┬────────┘
                       │ HTTPS (Port 443)
                       ▼
              ┌─────────────────┐
              │  DigitalOcean   │  ← Droplet: Ubuntu 22.04
              │    Droplet      │  ← IP: Check Cloudflare DNS
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     NGINX       │  ← Listens on 80 + 443
              │  (Docker)       │  ← SSL: Cloudflare Origin Cert
              └────────┬────────┘
                       │ HTTP (Port 8000)
                       ▼
              ┌─────────────────┐
              │   FastAPI       │  ← Backend API
              │   (Docker)      │
              └─────────────────┘
```

---

## CRITICAL CONFIGURATION DETAILS

### 1. SSL/TLS Setup

**DO NOT USE LET'S ENCRYPT / CERTBOT. We use Cloudflare Origin Certificates.**

| Setting | Value |
|---------|-------|
| SSL Provider | Cloudflare Origin Certificate |
| Certificate Location | `/etc/ssl/cloudflare/origin.pem` (on HOST, not in Docker) |
| Private Key Location | `/etc/ssl/cloudflare/origin.key` (on HOST) |
| Certificate Validity | 15 years (generated Jan 2026) |
| Cloudflare SSL Mode | **FULL** (Not Flexible, Not Full Strict) |

**Why Cloudflare Origin Certs?**
- No renewal needed (15 year validity)
- No ACME challenge complexity
- Works seamlessly with Cloudflare proxy
- Certbot/Let's Encrypt DOES NOT WORK with Cloudflare proxy enabled

### 2. Nginx Configuration

**Location:** `nginx/conf.d/api.conf`

**MUST contain:**
```nginx
ssl_certificate /etc/ssl/cloudflare/origin.pem;
ssl_certificate_key /etc/ssl/cloudflare/origin.key;
```

**MUST NOT contain:**
```nginx
# DO NOT USE THESE - THEY DON'T EXIST
ssl_certificate /etc/letsencrypt/live/*/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/*/privkey.pem;
```

### 3. Docker Compose

**File:** `docker-compose.production.yml`

**Nginx volume mounts MUST include:**
```yaml
volumes:
  - /etc/ssl/cloudflare:/etc/ssl/cloudflare:ro
```

**DO NOT include certbot service** - it's not needed and causes confusion.

### 4. Cloudflare Settings

| Setting | Value | Location |
|---------|-------|----------|
| SSL/TLS Mode | Full | SSL/TLS → Overview |
| Always Use HTTPS | ON | SSL/TLS → Edge Certificates |
| Minimum TLS Version | 1.2 | SSL/TLS → Edge Certificates |

**DO NOT change SSL mode to "Flexible"** - this will break the setup.

---

## Domains

| Domain | Purpose |
|--------|---------|
| `wantaiseo.com` | Main frontend (Vercel) |
| `www.wantaiseo.com` | Redirects to wantaiseo.com |
| `api.wantaiseo.com` | Backend API (DigitalOcean) |

---

## CORS Configuration

**Backend allows these origins:**
- `https://wantaiseo.com`
- `https://www.wantaiseo.com`
- `http://localhost:5173` (dev only)

**Defined in:** `backend/config.py` → `cors_origins_list` property

---

## Deployment

### CI/CD
- **Trigger:** Push to `main` branch
- **Workflow:** `.github/workflows/deploy.yml`
- **Action:** SSH into DigitalOcean, `git pull`, `docker compose up`

### Manual Deployment
```bash
ssh root@<DROPLET_IP>
cd /app
git pull origin main
docker compose -f docker-compose.production.yml up -d --build
```

### Restart Services
```bash
docker compose -f docker-compose.production.yml restart
```

### View Logs
```bash
docker compose -f docker-compose.production.yml logs -f api
docker compose -f docker-compose.production.yml logs -f nginx
docker compose -f docker-compose.production.yml logs -f worker
```

---

## Common Issues & Fixes

### Error 521 (Web Server Down)
**Cause:** Nginx can't start due to missing SSL certificates
**Fix:** Verify `/etc/ssl/cloudflare/` contains `origin.pem` and `origin.key`

### CORS Errors
**Cause:** Frontend origin not in allowed list
**Fix:** Add origin to `cors_origins_list` in `config.py`

### Nginx Crash Loop
**Check:** `docker logs app-nginx-1`
**Common causes:**
- Missing SSL cert files (fix cert paths)
- Bad nginx config syntax (run `nginx -t`)

---

## Files That Affect Hosting (DO NOT EDIT WITHOUT READING THIS)

| File | Impact |
|------|--------|
| `docker-compose.production.yml` | Docker service definitions |
| `nginx/conf.d/api.conf` | Nginx routing + SSL |
| `nginx/nginx.conf` | Nginx base config |
| `backend/config.py` | CORS, environment vars |
| `.github/workflows/deploy.yml` | CI/CD pipeline |

---

## Emergency Contacts / Recovery

### If Site Goes Down:
1. SSH into droplet: `ssh root@<IP>`
2. Check containers: `docker ps`
3. Check logs: `docker logs <container>`
4. Restart: `docker compose -f docker-compose.production.yml restart`

### If SSL Breaks:
1. Verify files exist: `ls -la /etc/ssl/cloudflare/`
2. If missing, regenerate in Cloudflare Dashboard → SSL/TLS → Origin Server
3. Save new cert/key to `/etc/ssl/cloudflare/`
4. Restart nginx: `docker restart app-nginx-1`

---

## ⚠️ How to Safely Modify Protected Files

The following files have warning headers and are CRITICAL to production:

| File | Purpose |
|------|---------|
| `docker-compose.production.yml` | Docker service definitions |
| `nginx/conf.d/api.conf` | Nginx routing + SSL |
| `.github/workflows/deploy.yml` | CI/CD pipeline |

### Before Editing:
1. **READ THIS ENTIRE DOCUMENT**
2. Understand what each file does
3. Test changes locally if possible
4. Coordinate with team - changes trigger auto-deploy

### Safe Edit Process:
1. Create a feature branch: `git checkout -b fix/infrastructure-change`
2. Make your changes
3. Push and create a PR for review
4. Only merge after verification
5. Monitor deployment logs after merge

### Emergency Rollback:
```bash
git revert HEAD
git push origin main
```

---

## AI Instructions

**BEFORE making any changes to:**
- `docker-compose.production.yml`
- `nginx/conf.d/api.conf`
- SSL/TLS configuration
- Deployment scripts

**YOU MUST:**
1. Read this entire file
2. Understand the Cloudflare → Nginx → API flow
3. Verify changes won't break SSL (we use Cloudflare Origin Certs, NOT Let's Encrypt)
4. Test changes locally if possible
5. Warn the user about potential downtime

**NEVER:**
- Add certbot/Let's Encrypt configuration
- Change SSL cert paths to `/etc/letsencrypt/`
- Remove the `/etc/ssl/cloudflare` volume mount
- Change Cloudflare SSL mode without understanding implications
