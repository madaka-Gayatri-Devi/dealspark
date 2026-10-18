#!/usr/bin/env bash
# ====================================================================
# DealSpark - Ubuntu 22.04 LTS VPS Initial Setup Script
# Run this script as root or with sudo on your freshly provisioned VPS.
# ====================================================================
set -euo pipefail

echo "========================================================"
echo " Starting DealSpark VPS Server Provisioning"
echo "========================================================"

# 1. Update system packages
apt update && apt upgrade -y

# 2. Install essential system dependencies
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    curl \
    nginx \
    mysql-server \
    certbot \
    python3-certbot-nginx \
    ufw

# 3. Create application and log directories
mkdir -p /var/www/dealspark
mkdir -p /var/log/dealspark
chown -R www-data:www-data /var/log/dealspark
chmod -R 775 /var/log/dealspark

# 4. Enable and start core services
systemctl enable --now mysql
systemctl enable --now nginx

# 5. Configure firewall (UFW)
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "========================================================"
echo " [OK] Server core software installed successfully!"
echo " MySQL, Nginx, Python3, and UFW are active."
echo " Next: Configure MySQL database and deploy application files."
echo "========================================================"
