# Quick Start: Database Setup for Vercel

## 🚀 Fastest Option: Vercel Postgres

### Step 1: Create Database
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to **Storage** tab
4. Click **Create Database**
5. Select **Postgres**
6. Choose a name and region
7. Click **Create**

### Step 2: Get Connection String
1. After creation, click on your database
2. Go to **.env.local** tab
3. Copy the `POSTGRES_URL` value
4. It looks like: `postgres://user:pass@host:port/dbname`

### Step 3: Set Environment Variable
1. Go to **Settings** → **Environment Variables**
2. Add new variable:
   - **Name**: `DATABASE_URL`
   - **Value**: Paste the connection string from Step 2
   - **Environment**: Production, Preview, Development (select all)
3. Click **Save**

### Step 4: Deploy
1. Push your code or trigger a new deployment
2. The app will automatically create tables on first request

### Step 5: Verify
Visit: `https://your-app.vercel.app/health`

Should return:
```json
{
  "status": "healthy",
  "api": "running",
  "version": "1.0.0",
  "database": "connected"
}
```

---

## 🔄 Alternative: PlanetScale (MySQL)

### Step 1: Create Account
1. Go to [planetscale.com](https://planetscale.com)
2. Sign up (free tier available)

### Step 2: Create Database
1. Click **"New database"**
2. Choose a name (e.g., `flashcard_db`)
3. Select a region
4. Click **"Create database"**

### Step 3: Get Connection String
1. Click on your database
2. Go to **"Connect"** tab
3. Select **"Python"** from dropdown
4. Copy the connection string
5. It looks like: `mysql://user:pass@host:port/dbname?ssl-mode=REQUIRED`

### Step 4: Set Environment Variable
1. In Vercel Dashboard → **Settings** → **Environment Variables**
2. Add:
   - **Name**: `DATABASE_URL`
   - **Value**: Paste connection string from Step 3
   - **Environment**: All
3. Click **Save**

### Step 5: Deploy & Verify
Same as Vercel Postgres steps 4-5 above.

---

## 📝 Environment Variable Format

### PostgreSQL (Vercel Postgres, Supabase, Neon)
```
postgresql://user:password@host:port/dbname
# or
postgres://user:password@host:port/dbname
```

### MySQL (PlanetScale, Railway)
```
mysql+pymysql://user:password@host:port/dbname
# or (for PlanetScale)
mysql://user:password@host:port/dbname?ssl-mode=REQUIRED
```

---

## ✅ What's Already Configured

Your app is already set up to:
- ✅ Auto-detect database type (MySQL or PostgreSQL)
- ✅ Handle connection pooling
- ✅ Work with both database types
- ✅ Create tables automatically

Just set the `DATABASE_URL` environment variable and you're done!

---

## 🆘 Troubleshooting

### Database not connecting?
1. Check `DATABASE_URL` is set correctly
2. Verify connection string format
3. Check database allows connections from Vercel IPs
4. Check `/health` endpoint for error details

### Tables not created?
- Tables are created automatically on first request
- Or run migrations manually (if using Alembic)

### SSL errors?
- Most cloud databases require SSL
- Connection strings usually include SSL settings
- If not, add `?ssl-mode=REQUIRED` for MySQL

---

## 🎯 Recommendation

**For Vercel**: Use **Vercel Postgres** - it's the easiest and most integrated option.

**For MySQL compatibility**: Use **PlanetScale** - serverless MySQL with free tier.
