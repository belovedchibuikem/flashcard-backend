# Database Options for Vercel Deployment

## Overview
Vercel doesn't provide MySQL hosting, but you can use external database services. Your FastAPI app now supports both **MySQL** and **PostgreSQL**.

---

## 🎯 Recommended Database Options

### Option 1: Vercel Postgres (Recommended for Vercel) ⭐
**Best for**: Easy integration with Vercel

**Pros**:
- Native Vercel integration
- Free tier available
- Automatic connection pooling
- Easy setup

**Setup**:
1. Go to Vercel Dashboard → Your Project → Storage → Create Database
2. Select "Postgres"
3. Copy the connection string
4. Set as `DATABASE_URL` environment variable

**Connection String Format**:
```
postgres://user:password@host:port/dbname
```

**Cost**: Free tier: 256 MB storage, 60 hours compute/month

---

### Option 2: PlanetScale (MySQL) ⭐
**Best for**: MySQL compatibility, serverless MySQL

**Pros**:
- Serverless MySQL
- Free tier available
- Branching (like Git for databases)
- Auto-scaling

**Setup**:
1. Sign up at [planetscale.com](https://planetscale.com)
2. Create a database
3. Get connection string
4. Set as `DATABASE_URL` environment variable

**Connection String Format**:
```
mysql://user:password@host:port/dbname?ssl-mode=REQUIRED
```

**Cost**: Free tier: 1 database, 1 GB storage, 1 billion row reads/month

---

### Option 3: Supabase (PostgreSQL)
**Best for**: Full-featured backend with auth, storage, etc.

**Pros**:
- PostgreSQL database
- Built-in authentication
- Real-time subscriptions
- Storage included
- Free tier

**Setup**:
1. Sign up at [supabase.com](https://supabase.com)
2. Create a project
3. Get connection string from Settings → Database
4. Set as `DATABASE_URL` environment variable

**Connection String Format**:
```
postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
postgresql://postgres:password@db.@@@Beloved?123?.supabase.co:5432/postgres
```

**Cost**: Free tier: 500 MB database, 2 GB bandwidth

---
@@@Beloved?123?

### Option 4: Railway (MySQL or PostgreSQL)
**Best for**: Simple setup, both MySQL and PostgreSQL

**Pros**:
- Simple interface
- Both MySQL and PostgreSQL
- Free tier available
- Easy to use

**Setup**:
1. Sign up at [railway.app](https://railway.app)
2. Create a MySQL or PostgreSQL database
3. Get connection string
4. Set as `DATABASE_URL` environment variable

**Cost**: Free tier: $5 credit/month

---

### Option 5: Neon (PostgreSQL)
**Best for**: Serverless PostgreSQL

**Pros**:
- Serverless PostgreSQL
- Branching (like Git)
- Free tier
- Auto-scaling

**Setup**:
1. Sign up at [neon.tech](https://neon.tech)
2. Create a project
3. Get connection string
4. Set as `DATABASE_URL` environment variable

**Cost**: Free tier: 0.5 GB storage, 192 hours compute/month

---

### Option 6: AWS RDS / Google Cloud SQL
**Best for**: Enterprise/production

**Pros**:
- Full control
- High availability
- Both MySQL and PostgreSQL

**Cons**:
- More complex setup
- Paid service

---

## 🔧 Configuration

### Environment Variable
Set `DATABASE_URL` in Vercel Dashboard → Settings → Environment Variables:

**For PostgreSQL**:
```
postgresql://user:password@host:port/dbname
# or
postgres://user:password@host:port/dbname
```

**For MySQL**:
```
mysql+pymysql://user:password@host:port/dbname
# or (for PlanetScale)
mysql://user:password@host:port/dbname?ssl-mode=REQUIRED
```

### Auto-Detection
The app automatically detects database type from `DATABASE_URL`:
- `postgres://` or `postgresql://` → PostgreSQL
- `mysql://` or `mysql+pymysql://` → MySQL

---

## 📊 Migration Guide

### From MySQL to PostgreSQL

1. **Export data from MySQL**:
   ```bash
   mysqldump -u user -p database_name > backup.sql
   ```

2. **Create PostgreSQL database** (on your chosen provider)

3. **Convert schema**:
   - Most SQLAlchemy models work with both
   - Some MySQL-specific features need adjustment:
     - `AUTO_INCREMENT` → `SERIAL` or `BIGSERIAL`
     - `ENGINE=InnoDB` → Not needed in PostgreSQL
     - `ENUM` → Works in both, but syntax differs

4. **Update DATABASE_URL** in Vercel environment variables

5. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

### Using Alembic for Migrations

Your app uses Alembic for migrations. It works with both MySQL and PostgreSQL:

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## ✅ Quick Start (Recommended: Vercel Postgres)

1. **Create Vercel Postgres**:
   - Vercel Dashboard → Storage → Create Database → Postgres

2. **Set Environment Variable**:
   - Copy connection string from Vercel
   - Add to Environment Variables as `DATABASE_URL`

3. **Deploy**:
   - Push code to trigger deployment
   - Tables will be created automatically on first request

4. **Verify**:
   - Visit: `https://your-app.vercel.app/health`
   - Should show `"database": "connected"`

---

## 🔍 Testing Database Connection

The `/health` endpoint checks database connectivity:

```bash
curl https://your-app.vercel.app/health
```

Response:
```json
{
  "status": "healthy",
  "api": "running",
  "version": "1.0.0",
  "database": "connected"
}
```

---

## 📝 Notes

- **SQLAlchemy** abstracts database differences - most code works with both
- **Alembic** handles migrations for both MySQL and PostgreSQL
- **Connection pooling** is configured automatically
- **SSL/TLS** is required for most cloud databases (handled automatically)

---

## 🎯 Recommendation

**For Vercel deployment**: Use **Vercel Postgres** (easiest) or **PlanetScale** (if you prefer MySQL).

Both are free tier friendly and integrate well with Vercel.
