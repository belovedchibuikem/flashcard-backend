# 🔧 cPanel Python App Configuration - CORRECTED

## ❌ Issues Found in Your Configuration

Based on your screenshots, here are the **incorrect** values:

1. **Application root**: `flashcards.carschek.com` ❌ (This is a domain, not a file path!)
2. **Application startup file**: `main.py` ❌ (Should be `passenger_wsgi.py`)
3. **Application Entry point**: `passenger_wsgi.py` ❌ (Should be `application`)

---

## ✅ CORRECT Configuration

### Field-by-Field Correct Values:

#### 1. **Python version**
- **Value**: `3.8.20` ✅ (or select 3.9+ if available)
- **Status**: This is fine, but 3.9+ is recommended

#### 2. **Application root** ⚠️ **CRITICAL FIX**
- **Current (WRONG)**: `flashcards.carschek.com`
- **Should be**: `/home/carschek/api` or `/home/carschek/public_html/flashcards`
- **Description**: This must be a **file path on the server**, not a domain name!

**How to find your correct path:**
1. Go to **File Manager** in cPanel
2. Navigate to where you uploaded your backend files
3. Look at the path shown in File Manager (e.g., `/home/carschek/api`)
4. Use that exact path

**Common paths:**
- `/home/carschek/api` (if you created an `api` folder)
- `/home/carschek/public_html/flashcards` (if in public_html)
- `/home/carschek/flashcards` (if in home directory)

#### 3. **Application URL**
- **Value**: `flashcards.carschek.com` ✅
- **Status**: This is correct!

#### 4. **Application startup file** ⚠️ **FIX NEEDED**
- **Current (WRONG)**: `main.py`
- **Should be**: `passenger_wsgi.py`
- **Description**: This is the file cPanel will execute to start your app

#### 5. **Application Entry point** ⚠️ **FIX NEEDED**
- **Current (WRONG)**: `passenger_wsgi.py`
- **Should be**: `application`
- **Description**: This is the **variable name** inside `passenger_wsgi.py` that contains your FastAPI app

---

## 📋 Step-by-Step Fix

### Step 1: Verify Your Files Are Uploaded
1. Go to **File Manager** in cPanel
2. Navigate to where your backend files are
3. Verify these files exist:
   - `passenger_wsgi.py` ✅
   - `main.py` ✅
   - `requirements.txt` ✅
   - `app/` folder ✅
4. **Note the full path** (e.g., `/home/carschek/api`)

### Step 2: Update Configuration

Fill in the form with these **EXACT** values:

```
Python version: 3.8.20 (or 3.9+ if available)
Application root: /home/carschek/api          ← FILE PATH, not domain!
Application URL: flashcards.carschek.com      ← Domain/subdomain
Application startup file: passenger_wsgi.py   ← File name
Application Entry point: application          ← Variable name
```

### Step 3: Create Application
Click **"CREATE"** button

---

## 🔍 How to Find Your Application Root Path

### Method 1: Via File Manager
1. Open **File Manager** in cPanel
2. Navigate to your backend files
3. Look at the breadcrumb path at the top
4. Copy the full path (starts with `/home/`)

### Method 2: Via Terminal/SSH
```bash
# Navigate to your files
cd ~/api  # or wherever your files are
pwd  # This shows the full path
```

### Method 3: Check Subdomain Settings
1. Go to **Subdomains** in cPanel
2. Find `flashcards.carschek.com`
3. Check the **Document Root** - this might be your app directory
4. Use that path (or create files there)

---

## ✅ Complete Correct Configuration Example

```
┌─────────────────────────────────────────┐
│ Python version:                          │
│ [3.8.20 ▼]                              │
│                                         │
│ Application root:                       │
│ [/home/carschek/api]                    │ ← FILE PATH
│                                         │
│ Application URL:                        │
│ [flashcards.carschek.com ▼]            │ ← DOMAIN
│                                         │
│ Application startup file:               │
│ [passenger_wsgi.py]                     │ ← FILE NAME
│                                         │
│ Application Entry point:                │
│ [application]                           │ ← VARIABLE NAME
└─────────────────────────────────────────┘
```

---

## ⚠️ Common Mistakes

### Mistake 1: Application root = Domain
- ❌ `flashcards.carschek.com`
- ✅ `/home/carschek/api`

### Mistake 2: Startup file = Entry point
- ❌ Startup: `main.py`, Entry: `passenger_wsgi.py`
- ✅ Startup: `passenger_wsgi.py`, Entry: `application`

### Mistake 3: Wrong file path
- ❌ `/home/carschek/flashcards.carschek.com`
- ✅ `/home/carschek/api` (where your files actually are)

---

## 🧪 Verify Before Creating

Before clicking "CREATE", verify:

1. ✅ **Application root** is a file path starting with `/home/`
2. ✅ **Application root** directory contains `passenger_wsgi.py`
3. ✅ **Startup file** is `passenger_wsgi.py` (not `main.py`)
4. ✅ **Entry point** is `application` (not `passenger_wsgi.py`)
5. ✅ **Application URL** matches your subdomain

---

## 📝 Quick Reference Card

```
┌──────────────────────────────────────┐
│ CORRECT CONFIGURATION                │
├──────────────────────────────────────┤
│ Python: 3.8.20 (or 3.9+)            │
│ Root: /home/carschek/api            │
│ URL: flashcards.carschek.com        │
│ Startup: passenger_wsgi.py          │
│ Entry: application                   │
└──────────────────────────────────────┘
```

---

**After fixing these values, the application should create successfully!**
