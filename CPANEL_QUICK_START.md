# 🚀 Quick Start: Deploy FastAPI on cPanel

## Prerequisites Checklist
- [ ] cPanel account with Python support
- [ ] MySQL database access
- [ ] Subdomain ready (e.g., `api.yourdomain.com`)

---

## ⚡ Quick Deployment Steps

### 1. **Create Python App in cPanel**
1. Login to cPanel
2. Find **"Python App"** or **"Setup Python App"**
3. Click **"Create Application"**
4. Fill in:
   - **Python Version**: 3.9 or higher
   - **App Directory**: `/home/username/api` (or your choice)
   - **App URL**: `api.yourdomain.com` (create subdomain first if needed)
   - **App Startup File**: `passenger_wsgi.py`
   - **App Entry Point**: `application`
5. Click **"Create"**

### 2. **Upload Your Files**
Upload all backend files to the app directory:
```
/home/username/api/
├── app/
├── passenger_wsgi.py
├── main.py
├── requirements.txt
├── .env
└── .htaccess
```

### 3. **Install Dependencies**
In cPanel Terminal or via SSH:
```bash
cd /home/username/api
source /home/username/virtualenv/api/3.9/bin/activate  # Use your Python version
pip install -r requirements.txt
```

### 4. **Configure Environment**
Create/update `.env` file:
```env
DATABASE_URL=mysql+pymysql://dbuser:dbpass@localhost:3306/dbname
OPENAI_API_KEY=your_key_here
JWT_SECRET_KEY=your_secret_key
DEBUG=False
CORS_ORIGINS=https://yourdomain.com,http://localhost:3000
```

### 5. **Set Up Database**
1. Create MySQL database in cPanel
2. Import `database/schema.sql` via phpMyAdmin
3. Update `.env` with database credentials

### 6. **Set Permissions**
```bash
chmod 755 passenger_wsgi.py
chmod 777 uploads  # Create this directory first
```

### 7. **Restart App**
In Python App Manager, click **"Restart"**

### 8. **Test**
Visit: `https://api.yourdomain.com/docs`

---

## 📝 Important Files Created

1. **`passenger_wsgi.py`** - cPanel entry point
2. **`.htaccess`** - Apache configuration
3. **`deploy_cpanel.sh`** - Deployment script

---

## 🔧 Common Issues & Solutions

### Issue: "Module not found"
**Solution**: Ensure virtual environment is activated and dependencies installed

### Issue: "Database connection error"
**Solution**: Check `.env` DATABASE_URL format:
```
mysql+pymysql://username:password@localhost:3306/database_name
```

### Issue: "500 Internal Server Error"
**Solution**: 
- Check error logs in cPanel
- Verify `passenger_wsgi.py` exists and is correct
- Ensure all imports work

### Issue: "CORS errors"
**Solution**: Update `CORS_ORIGINS` in `.env` with your frontend domain

---

## 📞 Need Help?

Check the full guide: `DEPLOYMENT_CPANEL_GUIDE.md`
