# Deployment Files Overview

This directory contains all files needed to deploy the Flashcard API to DigitalOcean.

## Files Created

### For DigitalOcean App Platform

- **`.do/app.yaml`** - App Platform configuration file
  - Defines service, database, environment variables
  - Auto-detected by App Platform
  - Includes health checks and scaling

- **`Procfile`** - Alternative deployment method
  - Used if App Platform doesn't detect app.yaml
  - Defines web process command

- **`runtime.txt`** - Python version specification
  - Ensures correct Python version is used

### For DigitalOcean Droplet

- **`deploy_droplet.sh`** - Automated deployment script
  - Sets up Ubuntu server
  - Installs dependencies
  - Configures Nginx, MySQL, systemd service
  - Run with: `sudo ./deploy_droplet.sh`

- **`nginx.conf`** - Nginx reverse proxy configuration
  - SSL/HTTPS setup
  - Security headers
  - Proxy configuration for FastAPI
  - Place in `/etc/nginx/sites-available/`

- **`gunicorn_config.py`** - Production WSGI server config
  - Worker processes configuration
  - Logging setup
  - Performance tuning
  - Used by systemd service

### Documentation

- **`DIGITALOCEAN_DEPLOYMENT.md`** - Complete deployment guide
  - Step-by-step instructions
  - Troubleshooting
  - Best practices

- **`DIGITALOCEAN_QUICK_START.md`** - Quick reference guide
  - Fast setup instructions
  - Minimum required steps

## Quick Deployment

### App Platform (Easiest)

1. Push code to GitHub
2. Create app in DigitalOcean App Platform
3. Add environment variables
4. Deploy

See `DIGITALOCEAN_QUICK_START.md` for details.

### Droplet (More Control)

1. Create Ubuntu 22.04 droplet
2. Run `deploy_droplet.sh`
3. Configure `.env` file
4. Set up database
5. Configure Nginx domain
6. Set up SSL

See `DIGITALOCEAN_DEPLOYMENT.md` for details.

## Environment Variables

All required variables are documented in:
- `env.template` - Template file
- `DIGITALOCEAN_DEPLOYMENT.md` - Full documentation

Minimum required:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `JWT_SECRET_KEY`
- `DEBUG=False`
- `CORS_ORIGINS`

## Production Checklist

- [ ] Environment variables configured
- [ ] Database created and schema imported
- [ ] SSL certificate installed (Droplet)
- [ ] Firewall configured
- [ ] Service running and enabled
- [ ] Health check passing
- [ ] Logs monitored
- [ ] Backups configured
- [ ] Domain DNS configured
- [ ] CORS origins updated

## Support

For detailed instructions, see:
- `DIGITALOCEAN_DEPLOYMENT.md` - Complete guide
- `DIGITALOCEAN_QUICK_START.md` - Quick start

For issues:
- Check service logs
- Verify environment variables
- Test database connection
- Review Nginx configuration
