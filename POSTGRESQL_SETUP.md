# PostgreSQL Database URL Setup Guide

## 📋 Quick Setup

### For Local Development

1. **Create a `.env` file** in the `backend/` directory (copy from `env.template`)

2. **Set the `DATABASE_URL`** with your PostgreSQL connection string:

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/flashcard_db
```

### PostgreSQL URL Format

```
postgresql://username:password@host:port/database_name
```

**Example for local PostgreSQL:**
```bash
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/flashcard_db
```

**Example with no password:**
```bash
DATABASE_URL=postgresql://postgres@localhost:5432/flashcard_db
```

---

## 🌐 For Cloud Providers

### Vercel Postgres

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project → **Storage** tab
3. Click **Create Database** → Select **Postgres**
4. After creation, go to **.env.local** tab
5. Copy the `POSTGRES_URL` value
6. Set it as `DATABASE_URL` in your environment variables

**Format:**
```
postgres://user:pass@host.vercel-postgres.com:5432/dbname
```

**Note:** The app automatically converts `postgres://` to `postgresql://` for SQLAlchemy compatibility.

---

### Supabase

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project → **Settings** → **Database**
3. Copy the **Connection string** (URI format)
4. Set it as `DATABASE_URL`

**Format:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

---

### Neon

1. Go to [Neon Console](https://console.neon.tech)
2. Select your project → **Connection Details**
3. Copy the **Connection string**
4. Set it as `DATABASE_URL`

**Format:**
```
postgresql://user:pass@ep-xxxxx.us-east-2.aws.neon.tech/dbname
```

---

### Railway

1. Go to [Railway Dashboard](https://railway.app)
2. Select your PostgreSQL service
3. Go to **Variables** tab
4. Copy the `DATABASE_URL` value
5. Use it directly (already formatted correctly)

**Format:**
```
postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

---

### DigitalOcean Managed Database

1. Go to [DigitalOcean Dashboard](https://cloud.digitalocean.com)
2. Select your database → **Connection Details**
3. Copy the **Connection string**
4. Set it as `DATABASE_URL`

**Format:**
```
postgresql://username:password@host.db.ondigitalocean.com:25060/database?sslmode=require
```

---

## 🔧 Setting Environment Variables

### Local Development (.env file)

Create `backend/.env` file:

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/flashcard_db
```

### Vercel Deployment

1. Go to **Settings** → **Environment Variables**
2. Add new variable:
   - **Name**: `DATABASE_URL`
   - **Value**: Your PostgreSQL connection string
   - **Environment**: Select all (Production, Preview, Development)
3. Click **Save**
4. Redeploy your application

### DigitalOcean App Platform

1. Go to **Settings** → **App-Level Environment Variables**
2. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: Your PostgreSQL connection string
3. Click **Save**

### cPanel / Traditional Hosting

1. Create `.env` file in your project root
2. Add: `DATABASE_URL=postgresql://user:pass@host:port/dbname`
3. Ensure `.env` is not publicly accessible

---

## ✅ Verify Connection

After setting `DATABASE_URL`, test the connection:

### Option 1: Health Check Endpoint

Visit: `http://localhost:8000/health`

Should return:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Option 2: Check Logs

Start your FastAPI server:
```bash
cd backend
python -m uvicorn main:app --reload
```

Look for database connection messages in the console.

---

## 🗄️ Create Database Schema

After setting the connection, create the tables:

### Option 1: Automatic (Recommended)

The app will automatically create tables on first request if they don't exist.

### Option 2: Manual SQL

Run the PostgreSQL schema file:

```bash
psql -h localhost -U postgres -d flashcard_db -f database/schema_postgresql.sql
```

Or using a GUI tool (pgAdmin, DBeaver, etc.):
1. Connect to your database
2. Open `database/schema_postgresql.sql`
3. Execute the script

---

## 🔍 Troubleshooting

### Connection Refused

**Error:** `could not connect to server: Connection refused`

**Solutions:**
- Check PostgreSQL is running: `pg_isready` or `sudo systemctl status postgresql`
- Verify host and port are correct
- Check firewall settings

### Authentication Failed

**Error:** `password authentication failed for user`

**Solutions:**
- Verify username and password are correct
- Check `pg_hba.conf` allows password authentication
- Try resetting PostgreSQL password

### Database Does Not Exist

**Error:** `database "flashcard_db" does not exist`

**Solutions:**
- Create the database: `createdb flashcard_db`
- Or connect to PostgreSQL and run: `CREATE DATABASE flashcard_db;`

### SSL Required

**Error:** `SSL connection is required`

**Solutions:**
- Add `?sslmode=require` to connection string:
  ```
  postgresql://user:pass@host:port/dbname?sslmode=require
  ```

### URL Format Issues

**Error:** `invalid dsn` or connection errors

**Solutions:**
- Ensure URL starts with `postgresql://` or `postgres://`
- Check special characters in password are URL-encoded
- Verify no extra spaces or quotes around the URL

---

## 📝 Notes

- The app **automatically detects** PostgreSQL vs MySQL from the URL format
- Both `postgresql://` and `postgres://` are supported (auto-converted)
- Connection pooling is configured automatically
- Tables are created automatically on first request (if using SQLAlchemy models)

---

## 🎯 Quick Reference

**Local PostgreSQL:**
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/flashcard_db
```

**Vercel Postgres:**
```bash
DATABASE_URL=postgres://user:pass@host.vercel-postgres.com:5432/dbname
```

**Supabase:**
```bash
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

**Neon:**
```bash
DATABASE_URL=postgresql://user:pass@ep-xxxxx.us-east-2.aws.neon.tech/dbname
```
