#!/bin/bash
# ========================================
# CiteKit - Digital Ocean Droplet Setup
# ========================================
# 
# Run this script on a fresh Ubuntu 22.04 Droplet
# Prerequisites: SSH access to the droplet
#
# Usage:
#   1. SSH into your droplet: ssh root@YOUR_DROPLET_IP
#   2. Run: curl -sSL https://raw.githubusercontent.com/YOUR_REPO/setup.sh | bash
#   Or clone repo and run: ./deploy/setup-droplet.sh
#
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "========================================"
echo "  CiteKit - Digital Ocean Droplet Setup"
echo "========================================"
echo -e "${NC}"

# ========================================
# 1. Update System
# ========================================
echo -e "${YELLOW}[1/7] Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

# ========================================
# 2. Install Docker
# ========================================
echo -e "${YELLOW}[2/7] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Add current user to docker group
    usermod -aG docker $USER
    
    # Enable Docker on boot
    systemctl enable docker
    systemctl start docker
else
    echo "Docker already installed."
fi

# Install Docker Compose
echo -e "${YELLOW}[3/7] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
    # Also install standalone for compatibility
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose already installed."
fi

# ========================================
# 4. Create App User
# ========================================
echo -e "${YELLOW}[4/7] Creating app user...${NC}"
if ! id "citekit" &>/dev/null; then
    useradd -m -s /bin/bash -G docker citekit
    echo "Created user 'citekit'"
else
    echo "User 'citekit' already exists."
fi

# ========================================
# 5. Setup Firewall
# ========================================
echo -e "${YELLOW}[5/7] Configuring firewall...${NC}"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
echo "Firewall configured: SSH, HTTP, HTTPS allowed."

# ========================================
# 6. Setup Swap (for 2GB droplets)
# ========================================
echo -e "${YELLOW}[6/7] Setting up swap...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
    echo "2GB swap created."
else
    echo "Swap already exists."
fi

# ========================================
# 7. Create App Directory
# ========================================
echo -e "${YELLOW}[7/7] Creating app directory...${NC}"
APP_DIR="/home/citekit/app"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/output
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/certbot/conf
mkdir -p $APP_DIR/certbot/www
chown -R citekit:citekit /home/citekit

echo ""
echo -e "${GREEN}========================================"
echo "  Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Clone your repository:"
echo "   cd /home/citekit/app"
echo "   git clone https://github.com/YOUR_REPO/backend.git ."
echo ""
echo "2. Create .env file with your secrets:"
echo "   nano .env"
echo ""
echo "3. Update nginx/conf.d/api.conf with your domain"
echo ""
echo "4. Run the deployment:"
echo "   ./deploy-digitalocean.sh"
echo ""
echo "5. Setup SSL:"
echo "   ./setup-ssl.sh YOUR_DOMAIN.com your@email.com"
echo ""
