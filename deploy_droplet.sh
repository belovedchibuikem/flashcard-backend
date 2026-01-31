#!/bin/bash
# DigitalOcean Droplet Deployment Script
# This script sets up the Flashcard API backend on a fresh Ubuntu droplet

set -e  # Exit on any error

echo "=========================================="
echo "Flashcard API - DigitalOcean Droplet Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="flashcard-api"
APP_USER="flashcard"
APP_DIR="/opt/flashcard-api"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
NGINX_CONFIG="/etc/nginx/sites-available/${APP_NAME}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${GREEN}Step 2: Installing system dependencies...${NC}"
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    mysql-server \
    certbot \
    python3-certbot-nginx \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libmysqlclient-dev \
    pkg-config \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libopencv-dev \
    python3-opencv

echo -e "${GREEN}Step 3: Creating application user...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
    echo -e "${GREEN}User $APP_USER created${NC}"
else
    echo -e "${YELLOW}User $APP_USER already exists${NC}"
fi

echo -e "${GREEN}Step 4: Setting up application directory...${NC}"
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo -e "${GREEN}Step 5: Cloning repository (if not already present)...${NC}"
if [ ! -d "$APP_DIR/.git" ]; then
    echo -e "${YELLOW}Please clone your repository manually or copy files to $APP_DIR${NC}"
    echo -e "${YELLOW}Example: git clone https://github.com/your-username/flashcard.git $APP_DIR${NC}"
else
    echo -e "${GREEN}Repository already cloned${NC}"
fi

echo -e "${GREEN}Step 6: Setting up Python virtual environment...${NC}"
cd "$APP_DIR/backend"
if [ ! -d "venv" ]; then
    sudo -u "$APP_USER" python3.11 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
fi

echo -e "${GREEN}Step 7: Installing Python dependencies...${NC}"
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install -r requirements.txt

echo -e "${GREEN}Step 8: Setting up MySQL database...${NC}"
echo -e "${YELLOW}Please configure MySQL manually:${NC}"
echo "1. Run: mysql_secure_installation"
echo "2. Create database: CREATE DATABASE flashcard_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "3. Create user: CREATE USER 'flashcard_user'@'localhost' IDENTIFIED BY 'your_secure_password';"
echo "4. Grant privileges: GRANT ALL PRIVILEGES ON flashcard_db.* TO 'flashcard_user'@'localhost';"
echo "5. Flush privileges: FLUSH PRIVILEGES;"
echo "6. Import schema: mysql -u flashcard_user -p flashcard_db < database/schema.sql"

echo -e "${GREEN}Step 9: Creating .env file...${NC}"
if [ ! -f "$APP_DIR/backend/.env" ]; then
    cp "$APP_DIR/backend/env.template" "$APP_DIR/backend/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/backend/.env"
    chmod 600 "$APP_DIR/backend/.env"
    echo -e "${YELLOW}Please edit $APP_DIR/backend/.env with your configuration${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

echo -e "${GREEN}Step 10: Creating systemd service file...${NC}"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Flashcard API - FastAPI Application
After=network.target mysql.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$APP_DIR/backend/venv/bin/gunicorn -c gunicorn_config.py main:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$APP_NAME"
echo -e "${GREEN}Systemd service created and enabled${NC}"

echo -e "${GREEN}Step 11: Configuring Nginx...${NC}"
cat > "$NGINX_CONFIG" << 'NGINX_EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
NGINX_EOF

ln -sf "$NGINX_CONFIG" "/etc/nginx/sites-enabled/${APP_NAME}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
echo -e "${GREEN}Nginx configured${NC}"

echo -e "${GREEN}Step 12: Setting up firewall...${NC}"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
echo -e "${GREEN}Firewall configured${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit $APP_DIR/backend/.env with your configuration"
echo "2. Update Nginx config: $NGINX_CONFIG (replace your-domain.com)"
echo "3. Set up MySQL database (see instructions above)"
echo "4. Import database schema: mysql -u flashcard_user -p flashcard_db < $APP_DIR/database/schema.sql"
echo "5. Start the service: systemctl start $APP_NAME"
echo "6. Check status: systemctl status $APP_NAME"
echo "7. View logs: journalctl -u $APP_NAME -f"
echo "8. Set up SSL: certbot --nginx -d your-domain.com -d www.your-domain.com"
echo ""
echo -e "${YELLOW}Important: Update the domain name in Nginx config before starting!${NC}"
