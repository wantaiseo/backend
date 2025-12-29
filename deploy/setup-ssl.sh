#!/bin/bash
# ========================================
# CiteKit - SSL Certificate Setup
# ========================================
#
# Run after initial deployment to setup Let's Encrypt SSL
#
# Usage: ./deploy/setup-ssl.sh YOUR_DOMAIN.com your@email.com
#
# ========================================

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 api.citekit.com admin@citekit.com"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "========================================"
echo "  Setting up SSL for $DOMAIN"
echo "========================================"
echo -e "${NC}"

# ========================================
# 1. Update nginx config with domain
# ========================================
echo -e "${YELLOW}[1/4] Updating nginx configuration...${NC}"
sed -i "s/YOUR_DOMAIN.com/$DOMAIN/g" nginx/conf.d/api.conf
echo "Updated nginx config with domain: $DOMAIN"

# ========================================
# 2. Restart nginx to apply changes
# ========================================
echo -e "${YELLOW}[2/4] Restarting nginx...${NC}"
docker-compose -f docker-compose.production.yml restart nginx

# Wait for nginx to be ready
sleep 5

# ========================================
# 3. Get SSL certificate
# ========================================
echo -e "${YELLOW}[3/4] Obtaining SSL certificate...${NC}"
docker-compose -f docker-compose.production.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# ========================================
# 4. Enable HTTPS in nginx
# ========================================
echo -e "${YELLOW}[4/4] Enabling HTTPS...${NC}"

# Uncomment the HTTPS server block
sed -i 's/# server {/server {/g' nginx/conf.d/api.conf
sed -i 's/#     listen 443/    listen 443/g' nginx/conf.d/api.conf
sed -i 's/#     server_name/    server_name/g' nginx/conf.d/api.conf
sed -i 's/#     ssl_/    ssl_/g' nginx/conf.d/api.conf
sed -i 's/#     add_header/    add_header/g' nginx/conf.d/api.conf
sed -i 's/#     location/    location/g' nginx/conf.d/api.conf
sed -i 's/#         /        /g' nginx/conf.d/api.conf
sed -i 's/# }/}/g' nginx/conf.d/api.conf

# Enable HTTP to HTTPS redirect
sed -i 's/# location \/ {/location \/ {/g' nginx/conf.d/api.conf
sed -i 's/#     return 301/    return 301/g' nginx/conf.d/api.conf

# Comment out the HTTP proxy block (now handled by HTTPS)
# This is a bit tricky, users may need to manually edit

# Restart nginx
docker-compose -f docker-compose.production.yml restart nginx

echo ""
echo -e "${GREEN}========================================"
echo "  SSL Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Your API is now available at: https://$DOMAIN"
echo ""
echo "Certificate will auto-renew via certbot container."
echo ""
echo "Test your SSL: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
