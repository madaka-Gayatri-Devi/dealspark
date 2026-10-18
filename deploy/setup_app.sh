#!/usr/bin/env bash
# ====================================================================
# DealSpark - Application Server & Web Setup Script
# Run on the VPS as root or sudo after application files are in /var/www/dealspark
# ====================================================================
set -euo pipefail

APP_DIR="/var/www/dealspark"
cd "${APP_DIR}"

echo "[1/6] Creating Python virtual environment..."
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[2/6] Configuring file permissions..."
mkdir -p "${APP_DIR}/static/uploads/products"
chown -R www-data:www-data "${APP_DIR}"
chmod -R 755 "${APP_DIR}"
chmod -R 775 "${APP_DIR}/static/uploads"

echo "[3/6] Setting up Systemd Gunicorn service..."
cp "${APP_DIR}/deploy/systemd/dealspark.service" /etc/systemd/system/dealspark.service
systemctl daemon-reload
systemctl enable --now dealspark.service

echo "[4/6] Setting up Nginx reverse proxy..."
cp "${APP_DIR}/deploy/nginx/dealspark.conf" /etc/nginx/sites-available/dealspark.conf
ln -sf /etc/nginx/sites-available/dealspark.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "[5/6] Verifying DealSpark service status..."
systemctl status dealspark.service --no-pager

echo "========================================================"
echo " [SUCCESS] DealSpark is running on Gunicorn and Nginx!"
echo " Next step: Obtain free SSL certificate with:"
echo " sudo certbot --nginx -d dealspark.in -d www.dealspark.in"
echo "========================================================"
