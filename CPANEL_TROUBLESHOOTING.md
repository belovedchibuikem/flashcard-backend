# 🔧 cPanel Deployment Troubleshooting Guide

## Error: "No such application (or application not configured)"

This error means cPanel can't find your Python application configuration. Here's how to fix it:

---

## ✅ Solution Steps

### Step 1: Verify Subdomain/Domain Setup

1. **Check if subdomain exists**:
   - Go to **"Subdomains"** in cPanel
   - Verify `flashcards.carschek.com` exists
   - If not, create it pointing to `/public_html/flashcards` or `/public_html/api`

2. **Check Document Root**:
   - The subdomain should point to your Python app directory
   - Example: `/home/username/public_html/flashcards` or `/home/username/api`

### Step 2: Create Python Application Properly

1. **Go to Python App Manager**:
   - In cPanel, find **"Python App"** or **"Setup Python App"**
   - Click **"Create Application"**

2. **Configure Application**:
   ```
   Python Version: 3.9 (or highest available)
   App Directory: /home/username/api (or where your files are)
   App URL: flashcards.carschek.com (select from dropdown)
   App Startup File: passenger_wsgi.py
   App Entry Point: application
   ```

3. **Important**: 
   - The **App URL** must match your subdomain exactly
   - The **App Directory** must contain your Python files
   - The **Startup File** must be `passenger_wsgi.py`

### Step 3: Verify File Structure

Your app directory should look like this:
```
/home/username/api/          (or your app directory)
├── passenger_wsgi.py        ← MUST exist
├── main.py                  ← Your FastAPI app
├── app/
│   ├── __init__.py
│   ├── main.py (if exists)
│   ├── config.py
│   ├── database.py
│   └── ...
├── requirements.txt
└── .env
```

### Step 4: Check passenger_wsgi.py

Ensure `passenger_wsgi.py` exists and contains:
```python
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.environ.setdefault('PYTHONPATH', current_dir)
os.chdir(current_dir)

from main import app
application = app
```

### Step 5: Restart Application

1. In **Python App Manager**, find your application
2. Click **"Restart"** or **"Reload"**
3. Wait 30-60 seconds for changes to take effect

---

## 🔍 Alternative: Manual Domain Configuration

If the Python App Manager doesn't recognize your domain:

### Option A: Use Main Domain Instead

1. Create Python app for main domain: `carschek.com/api`
2. Access via: `https://carschek.com/api`

### Option B: Create Subdomain First

1. **Create Subdomain**:
   - Go to **"Subdomains"** in cPanel
   - Create: `api.carschek.com` (or `flashcards.carschek.com`)
   - Document Root: `/home/username/api`
   - Click **"Create"**

2. **Then Create Python App**:
   - Use the newly created subdomain
   - Point to the same directory

---

## 🛠️ Manual Passenger Configuration

If Python App Manager isn't working, you can manually configure Passenger:

### 1. Create `.htaccess` in your app directory:
```apache
PassengerEnabled On
PassengerAppRoot /home/username/api
PassengerAppType wsgi
PassengerStartupFile passenger_wsgi.py
PassengerPython /home/username/virtualenv/api/3.9/bin/python
```

### 2. Create `passenger_wsgi.py`:
```python
import sys
import os

# Set paths
app_dir = '/home/username/api'
sys.path.insert(0, app_dir)
os.chdir(app_dir)
os.environ['PYTHONPATH'] = app_dir

# Import app
from main import app
application = app
```

---

## 📋 Checklist

- [ ] Subdomain `flashcards.carschek.com` exists in cPanel
- [ ] Subdomain points to correct directory (`/home/username/api`)
- [ ] Python App created in Python App Manager
- [ ] App URL matches subdomain exactly
- [ ] `passenger_wsgi.py` exists in app directory
- [ ] `passenger_wsgi.py` has correct content
- [ ] `main.py` exists and imports correctly
- [ ] Virtual environment is activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Application restarted in Python App Manager
- [ ] File permissions correct (755 for directories, 644 for files)

---

## 🧪 Test Configuration

### Test 1: Check if files exist
```bash
# Via SSH or Terminal
cd /home/username/api
ls -la passenger_wsgi.py
ls -la main.py
```

### Test 2: Test Python import
```bash
cd /home/username/api
source /home/username/virtualenv/api/3.9/bin/activate
python -c "from main import app; print('OK')"
```

### Test 3: Check Passenger logs
```bash
tail -f ~/logs/error_log
```

---

## 🔄 Common Fixes

### Fix 1: Recreate Application
1. Delete existing Python app in Python App Manager
2. Create new one with correct settings
3. Restart

### Fix 2: Check Domain DNS
- Ensure DNS A record points to server IP
- Wait for DNS propagation (can take up to 48 hours)

### Fix 3: Use Different Port/Path
- Try accessing via: `https://carschek.com/api` instead
- Or use port: `https://carschek.com:8000` (if allowed)

---

## 📞 Still Not Working?

1. **Check Error Logs**:
   - `~/logs/error_log` in cPanel
   - Python App Manager → View Logs

2. **Contact Hosting Support**:
   - Ask if Python/Passenger is enabled
   - Verify your account has Python app permissions
   - Check if there are any restrictions

3. **Verify Passenger is Installed**:
   - Some hosts require Passenger to be enabled
   - Check with hosting provider

---

## 💡 Quick Fix Script

Run this via SSH to verify setup:

```bash
#!/bin/bash
APP_DIR="/home/username/api"
VENV_PATH="/home/username/virtualenv/api/3.9"

echo "Checking application setup..."
echo ""

# Check if directory exists
if [ -d "$APP_DIR" ]; then
    echo "✅ App directory exists: $APP_DIR"
else
    echo "❌ App directory NOT found: $APP_DIR"
fi

# Check passenger_wsgi.py
if [ -f "$APP_DIR/passenger_wsgi.py" ]; then
    echo "✅ passenger_wsgi.py exists"
else
    echo "❌ passenger_wsgi.py NOT found"
fi

# Check main.py
if [ -f "$APP_DIR/main.py" ]; then
    echo "✅ main.py exists"
else
    echo "❌ main.py NOT found"
fi

# Test Python import
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    python -c "from main import app" 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Python import successful"
    else
        echo "❌ Python import failed"
    fi
    deactivate
else
    echo "⚠️  Virtual environment not found: $VENV_PATH"
fi

echo ""
echo "Done!"
```

---

**Last Updated**: 2024
