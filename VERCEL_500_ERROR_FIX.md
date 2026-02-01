# Vercel 500 Error Fix

## Common Causes

### 1. Database Connection Failure
The app tries to connect to MySQL on startup. If `DATABASE_URL` is not set or incorrect, it crashes.

**Fix Applied**: Made database connection optional on startup - app will start even if database is unavailable.

### 2. Missing Dependencies
Some code imports packages that aren't in requirements.txt (like cv2, numpy).

**Fix Applied**: Updated `preprocess_image` to handle missing OpenCV/numpy gracefully with PIL fallback.

### 3. Environment Variables Not Set
Required environment variables might be missing.

**Required Environment Variables**:
```bash
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=your-secret-key
```

## Fixes Applied

1. ✅ Made database table creation optional (won't crash if DB unavailable)
2. ✅ Updated image preprocessing to handle missing OpenCV/numpy
3. ✅ Changed DATABASE_URL default to empty (forces explicit config)
4. ✅ Added vercel.json for proper function configuration

## Next Steps

1. **Set Environment Variables in Vercel**:
   - Go to Vercel Dashboard → Your Project → Settings → Environment Variables
   - Add all required variables (DATABASE_URL, OPENAI_API_KEY, etc.)

2. **Check Vercel Logs**:
   - Go to Vercel Dashboard → Your Project → Functions → View Logs
   - Look for the actual error message

3. **Test Health Endpoint**:
   - Visit: `https://your-app.vercel.app/health`
   - This will show if database connection is working

4. **If Still Failing**:
   - Check Vercel function logs for the exact error
   - Verify all environment variables are set
   - Ensure DATABASE_URL is correct and database is accessible from Vercel

## Common Issues

### Database Not Accessible
Vercel serverless functions can't connect to localhost databases. You need:
- A cloud database (PlanetScale, Railway, AWS RDS, etc.)
- Or use Vercel Postgres
- Or use a database with public IP

### Missing Environment Variables
Check that all required variables are set in Vercel dashboard.

### Import Errors
If you see import errors, check that all packages in requirements.txt are compatible with Python 3.12.
