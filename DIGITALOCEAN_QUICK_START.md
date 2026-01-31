# DigitalOcean Quick Start Guide

Choose your deployment method:

## Option 1: App Platform (Easiest - Recommended for Beginners)

**Time**: 10-15 minutes  
**Cost**: $5-12/month + $15/month for database

### Steps:

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for DigitalOcean deployment"
   git push origin main
   ```

2. **Create App in DigitalOcean**
   - Go to https://cloud.digitalocean.com/apps
   - Click "Create App"
   - Connect GitHub and select your repository
   - Choose `backend` directory

3. **Add Environment Variables**
   - In App Platform dashboard → Settings → Environment Variables
   - Add all variables from `env.template`
   - Mark sensitive ones as "Encrypted"

4. **Deploy**
   - Click "Deploy"
   - Wait for build to complete
   - Your API will be live at `https://your-app-name.ondigitalocean.app`

5. **Add Database (Optional)**
   - Components → Add Component → Database → MySQL 8
   - Connection string auto-added as `DATABASE_URL`

**Done!** Your API is live with automatic SSL and scaling.

---

## Option 2: Droplet (More Control)

**Time**: 30-45 minutes  
**Cost**: $12/month

### Steps:

1. **Create Droplet**
   - Ubuntu 22.04 LTS
   - At least 2GB RAM
   - Your SSH key

2. **SSH into Droplet**
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Run Deployment Script**
   ```bash
   cd /tmp
   # Upload deploy_droplet.sh or download from GitHub
   chmod +x deploy_droplet.sh
   sudo ./deploy_droplet.sh
   ```

4. **Clone Repository**
   ```bash
   cd /opt/flashcard-api
   sudo -u flashcard git clone https://github.com/your-username/flashcard.git .
   ```

5. **Set Up Database**
   ```bash
   sudo mysql -u root -p
   # Then run SQL commands from deployment guide
   ```

6. **Configure Environment**
   ```bash
   sudo -u flashcard nano /opt/flashcard-api/backend/.env
   # Add all required variables
   ```

7. **Set Up SSL**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

8. **Start Service**
   ```bash
   sudo systemctl start flashcard-api
   ```

**Done!** Your API is live at `https://your-domain.com`

---

## Required Environment Variables

Minimum required for both methods:

```bash
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False
CORS_ORIGINS=https://your-frontend.com
```

---

## Next Steps

1. Test your API: `curl https://your-domain.com/health`
2. Update mobile app with new API URL
3. Set up monitoring and backups
4. Review full deployment guide: `DIGITALOCEAN_DEPLOYMENT.md`

---

## Need Help?

- Check `DIGITALOCEAN_DEPLOYMENT.md` for detailed instructions
- Review logs: `sudo journalctl -u flashcard-api -f` (Droplet)
- Check App Platform runtime logs (App Platform)
