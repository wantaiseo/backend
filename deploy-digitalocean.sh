#!/bin/bash
# ========================================
# CiteKit - Digital Ocean Deployment Script
# ========================================
#
# Run this from the backend directory on your droplet
# Make sure .env file exists with all required variables
#
# Usage: ./deploy-digitalocean.sh
#
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "========================================"
echo "  CiteKit - Digital Ocean Deployment"
echo "========================================"
echo -e "${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Create .env with the following variables:"
    echo ""
    cat << 'EOF'
# Required Environment Variables
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
RAZORPAY_KEY_ID=rzp_live_xxxxx
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
PAYMENT_AMOUNT_PAISE=42000
PAYMENT_CURRENCY=INR
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
ADMIN_EMAIL=admin@yourdomain.com
JWT_SECRET=your-super-secret-jwt-key-change-this
EOF
    echo ""
    exit 1
fi

# ========================================
# 1. Pull latest code
# ========================================
echo -e "${YELLOW}[1/5] Pulling latest code...${NC}"
if [ -d .git ]; then
    git pull origin main || git pull origin master || echo "No remote to pull from"
fi

# ========================================
# 2. Build images
# ========================================
echo -e "${YELLOW}[2/5] Building Docker images...${NC}"
docker-compose -f docker-compose.production.yml build --no-cache

# ========================================
# 3. Stop existing containers
# ========================================
echo -e "${YELLOW}[3/5] Stopping existing containers...${NC}"
docker-compose -f docker-compose.production.yml down || true

# ========================================
# 4. Start services
# ========================================
echo -e "${YELLOW}[4/5] Starting services...${NC}"
docker-compose -f docker-compose.production.yml up -d

# ========================================
# 5. Wait and check health
# ========================================
echo -e "${YELLOW}[5/5] Checking service health...${NC}"
sleep 10

# Check if API is healthy
if docker-compose -f docker-compose.production.yml exec -T api curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${RED}⚠️ API health check failed. Checking logs...${NC}"
    docker-compose -f docker-compose.production.yml logs --tail=50 api
fi

# Check if Worker is running
if docker-compose -f docker-compose.production.yml ps | grep -q "worker.*Up"; then
    echo -e "${GREEN}✅ Worker is running!${NC}"
else
    echo -e "${RED}⚠️ Worker may not be running. Checking logs...${NC}"
    docker-compose -f docker-compose.production.yml logs --tail=50 worker
fi

# Check if Redis is healthy
if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is healthy!${NC}"
else
    echo -e "${RED}⚠️ Redis may not be running.${NC}"
fi

echo ""
echo -e "${GREEN}========================================"
echo "  Deployment Complete!"
echo "========================================${NC}"
echo ""
echo "Services running:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "View logs: docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "If this is first deploy, run SSL setup:"
echo "  ./deploy/setup-ssl.sh YOUR_DOMAIN.com your@email.com"
echo ""
