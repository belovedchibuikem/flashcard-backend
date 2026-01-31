# DigitalOcean Deployment Guide

This guide covers deploying the Flashcard API backend to DigitalOcean using either **App Platform** (PaaS) or **Droplet** (VPS).

## Table of Contents

1. [DigitalOcean App Platform Deployment](#digitalocean-app-platform-deployment)
2. [DigitalOcean Droplet Deployment](#digitalocean-droplet-deployment)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [SSL/HTTPS Setup](#sslhttps-setup)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## DigitalOcean App Platform Deployment

App Platform is a Platform-as-a-Service (PaaS) solution that handles deployment, scaling, and SSL automatically.

### Prerequisites

- DigitalOcean account
- GitHub repository with your code
- MySQL database (can be created via App Platform or use managed database)

### Step 1: Prepare Your Repository

1. Ensure your code is pushed to GitHub
2. Make sure `.do/app.yaml` exists in the `backend` directory
3. Update `.do/app.yaml` with your repository details:
   ```yaml
   github:
     repo: your-username/flashcard
     branch: main
   ```

### Step 2: Create App in DigitalOcean

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Connect your GitHub account and select your repository
4. Choose the `backend` directory as the source
5. App Platform will detect the `app.yaml` file automatically

### Step 3: Configure Environment Variables

In the App Platform dashboard:

1. Go to **Settings** → **App-Level Environment Variables**
2. Add all required variables (see [Environment Variables](#environment-variables) section)
3. Mark sensitive variables as **Encrypted**

### Step 4: Create Database (Optional)

If you want a managed database:

1. In App Platform, go to **Components** → **Add Component** → **Database**
2. Choose **MySQL 8**
3. Select a plan (Basic plan starts at $15/month)
4. The database connection string will be automatically added as `DATABASE_URL`

### Step 5: Deploy

1. Click **"Deploy"**
2. App Platform will:
   - Build your application
   - Install dependencies
   - Start the service
   - Set up SSL automatically
3. Your app will be available at `https://your-app-name.ondigitalocean.app`

### Step 6: Custom Domain (Optional)

1. Go to **Settings** → **Domains**
2. Add your custom domain
3. Follow DNS configuration instructions
4. SSL certificate will be automatically provisioned

### App Platform Configuration File

The `.do/app.yaml` file includes:

- **Service configuration**: Gunicorn with Uvicorn workers
- **Health checks**: `/health` endpoint
- **Scaling**: Auto-scaling based on traffic
- **Environment variables**: Template for all required vars
- **Database**: Optional managed MySQL database

---

## DigitalOcean Droplet Deployment

A Droplet is a Virtual Private Server (VPS) where you have full control.

### Prerequisites

- DigitalOcean account
- SSH access to your droplet
- Domain name (optional but recommended)

### Step 1: Create Droplet

1. Go to [DigitalOcean Droplets](https://cloud.digitalocean.com/droplets/new)
2. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic plan (at least 2GB RAM recommended)
   - **Region**: Choose closest to your users
   - **Authentication**: SSH keys (recommended) or password
3. Click **"Create Droplet"**

### Step 2: Initial Server Setup

1. SSH into your droplet:
   ```bash
   ssh root@your-droplet-ip
   ```

2. Run the deployment script:
   ```bash
   cd /tmp
   wget https://raw.githubusercontent.com/your-username/flashcard/main/backend/deploy_droplet.sh
   chmod +x deploy_droplet.sh
   sudo ./deploy_droplet.sh
   ```

   Or manually copy the script and run it.

### Step 3: Clone Your Repository

```bash
cd /opt/flashcard-api
sudo -u flashcard git clone https://github.com/your-username/flashcard.git .
```

Or upload files via SCP:
```bash
scp -r backend/* root@your-droplet-ip:/opt/flashcard-api/backend/
```

### Step 4: Set Up MySQL Database

```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Login to MySQL
sudo mysql -u root -p

# Create database and user
CREATE DATABASE flashcard_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'flashcard_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON flashcard_db.* TO 'flashcard_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
mysql -u flashcard_user -p flashcard_db < /opt/flashcard-api/database/schema.sql
```

### Step 5: Configure Environment Variables

```bash
sudo -u flashcard nano /opt/flashcard-api/backend/.env
```

Update all required variables (see [Environment Variables](#environment-variables) section).

### Step 6: Configure Nginx

1. Copy the Nginx configuration:
   ```bash
   sudo cp /opt/flashcard-api/backend/nginx.conf /etc/nginx/sites-available/flashcard-api
   ```

2. Update domain name:
   ```bash
   sudo nano /etc/nginx/sites-available/flashcard-api
   # Replace "your-domain.com" with your actual domain
   ```

3. Enable the site:
   ```bash
   sudo ln -s /etc/nginx/sites-available/flashcard-api /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Step 7: Set Up SSL with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Certbot will:
- Install SSL certificate
- Configure automatic renewal
- Update Nginx configuration

### Step 8: Start the Service

```bash
sudo systemctl start flashcard-api
sudo systemctl enable flashcard-api
sudo systemctl status flashcard-api
```

### Step 9: Verify Deployment

1. Check service status:
   ```bash
   sudo systemctl status flashcard-api
   ```

2. Check logs:
   ```bash
   sudo journalctl -u flashcard-api -f
   ```

3. Test health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

4. Test public endpoint:
   ```bash
   curl https://your-domain.com/health
   ```

---

## Environment Variables

### Required Variables

```bash
# Database
DATABASE_URL=mysql+pymysql://flashcard_user:password@localhost:3306/flashcard_db

# OpenAI (Required for AI features)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# JWT Authentication
JWT_SECRET_KEY=your-random-secret-key-here  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# CORS (Add your frontend URLs)
CORS_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com
```

### Optional Variables

```bash
# File Storage (S3 recommended for production)
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET_NAME=flashcard-uploads
AWS_REGION=us-east-1

# Alternative: Cloudinary
# STORAGE_TYPE=cloudinary
# CLOUDINARY_CLOUD_NAME=your-cloud-name
# CLOUDINARY_API_KEY=your-api-key
# CLOUDINARY_API_SECRET=your-api-secret

# Additional AI Services (Optional)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_GEMINI_API_KEY=...
AZURE_VISION_KEY=...
AZURE_VISION_ENDPOINT=https://your-region.api.cognitive.microsoft.com/

# Upload Settings
MAX_UPLOAD_SIZE=52428800  # 50MB
```

### Generating JWT Secret Key

```bash
openssl rand -hex 32
```

---

## Database Setup

### Using DigitalOcean Managed Database (Recommended)

1. Create database in App Platform or separately
2. Connection string format:
   ```
   mysql+pymysql://username:password@host:port/database?ssl_ca=/path/to/ca-certificate.crt
   ```

### Using MySQL on Droplet

See Step 4 in [Droplet Deployment](#step-4-set-up-mysql-database) section.

### Importing Schema

```bash
mysql -u flashcard_user -p flashcard_db < database/schema.sql
```

---

## SSL/HTTPS Setup

### App Platform

SSL is automatically configured. Just add your custom domain in settings.

### Droplet

Use Let's Encrypt (free SSL):

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Certificates auto-renew. Verify renewal:
```bash
sudo certbot renew --dry-run
```

---

## Monitoring & Maintenance

### View Logs

**App Platform:**
- Go to **Runtime Logs** in dashboard

**Droplet:**
```bash
# Service logs
sudo journalctl -u flashcard-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Service

**App Platform:**
- Use dashboard or `doctl` CLI

**Droplet:**
```bash
sudo systemctl restart flashcard-api
```

### Update Application

**App Platform:**
- Push to GitHub, App Platform auto-deploys

**Droplet:**
```bash
cd /opt/flashcard-api
sudo -u flashcard git pull
sudo -u flashcard /opt/flashcard-api/backend/venv/bin/pip install -r backend/requirements.txt
sudo systemctl restart flashcard-api
```

### Backup Database

**Managed Database:**
- Use DigitalOcean's automated backups

**Droplet MySQL:**
```bash
mysqldump -u flashcard_user -p flashcard_db > backup_$(date +%Y%m%d).sql
```

### Health Checks

Monitor the `/health` endpoint:
```bash
curl https://your-domain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## Troubleshooting

### Service Won't Start

1. Check logs: `sudo journalctl -u flashcard-api -n 50`
2. Verify `.env` file exists and has correct values
3. Check database connection
4. Verify Python dependencies installed

### Database Connection Errors

1. Verify MySQL is running: `sudo systemctl status mysql`
2. Check database credentials in `.env`
3. Test connection: `mysql -u flashcard_user -p flashcard_db`

### Nginx Errors

1. Test configuration: `sudo nginx -t`
2. Check error logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify service is running: `curl http://localhost:8000/health`

### SSL Certificate Issues

1. Check certificate: `sudo certbot certificates`
2. Renew manually: `sudo certbot renew`
3. Verify Nginx config includes SSL settings

---

## Cost Estimation

### App Platform
- **Basic Plan**: $5/month (512MB RAM, 1 vCPU)
- **Professional Plan**: $12/month (1GB RAM, 1 vCPU) - Recommended
- **Database**: $15/month (Basic MySQL)

### Droplet
- **Basic Droplet**: $12/month (2GB RAM, 1 vCPU) - Recommended
- **Managed Database**: $15/month (optional)

---

## Security Best Practices

1. **Never commit `.env` files** to Git
2. **Use strong passwords** for database and JWT secret
3. **Enable firewall** (UFW on Ubuntu)
4. **Keep system updated**: `sudo apt update && sudo apt upgrade`
5. **Use SSH keys** instead of passwords
6. **Enable fail2ban** for SSH protection
7. **Regular backups** of database
8. **Monitor logs** for suspicious activity

---

## Support

For issues or questions:
- Check logs first
- Review DigitalOcean documentation
- Check FastAPI/Gunicorn documentation
- Review error messages carefully

---

**Last Updated**: 2024
