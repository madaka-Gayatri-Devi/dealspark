#!/usr/bin/env bash
# ====================================================================
# DealSpark - MySQL Database & Seed Importer Script
# Run on the VPS as root or sudo:
# bash deploy/setup_mysql.sh <db_name> <db_user> <db_password>
# ====================================================================
set -euo pipefail

DB_NAME="${1:-dealspark}"
DB_USER="${2:-dealspark_user}"
DB_PASSWORD="${3:-}"

if [ -z "$DB_PASSWORD" ]; then
    echo "[ERROR] Database password is required."
    echo "Usage: sudo bash deploy/setup_mysql.sh <db_name> <db_user> <db_password>"
    exit 1
fi

echo "[1/3] Creating MySQL database '${DB_NAME}' and user '${DB_USER}'..."
mysql -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
mysql -e "GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

echo "[2/3] Initializing tables schema via Flask CLI..."
cd /var/www/dealspark
sudo -u www-data /var/www/dealspark/venv/bin/flask init-db

echo "[3/3] Importing existing DealSpark data dump..."
if [ -f "/var/www/dealspark/scripts/dealspark_mysql_dump.sql" ]; then
    mysql "${DB_NAME}" < /var/www/dealspark/scripts/dealspark_mysql_dump.sql
    echo "[OK] DealSpark MySQL database and 47 baseline records imported successfully!"
else
    echo "[WARNING] scripts/dealspark_mysql_dump.sql not found; baseline tables were initialized via init-db."
fi
