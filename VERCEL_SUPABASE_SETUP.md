# How to Connect Supabase Database to Vercel

## 🎯 Step-by-Step Guide

### Step 1: Get Your Supabase Connection String

1. **Go to Supabase Dashboard**
   - Visit: [https://app.supabase.com](https://app.supabase.com)
   - Sign in to your account

2. **Select Your Project**
   - Click on the project you want to use

3. **Navigate to Database Settings**
   - Click **Settings** (gear icon) in the left sidebar
   - Click **Database** under the "Project Settings" section

4. **Find Connection String**
   - Scroll down to **Connection string** section
   - Look for **URI** format (not JDBC or other formats)
   - It should look like:
     ```
     postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
     ```

5. **Copy the Connection String**
   - Click the **Copy** button next to the URI
   - **Important**: Replace `[YOUR-PASSWORD]` with your actual database password
   - Your password is shown in the **Database password** section (or you can reset it)

**Example of what you'll copy:**
```
postgresql://postgres:your_actual_password_here@db.abcdefghijklmnop.supabase.co:5432/postgres
```

---

### Step 2: Add to Vercel Environment Variables

1. **Go to Vercel Dashboard**
   - Visit: [https://vercel.com/dashboard](https://vercel.com/dashboard)
   - Sign in to your account

2. **Select Your Project**
   - Click on the project where you want to add the database URL

3. **Open Settings**
   - Click **Settings** tab at the top

4. **Go to Environment Variables**
   - Click **Environment Variables** in the left sidebar (under "Configuration")

5. **Add New Variable**
   - Click **Add New** button
   - Fill in the form:
     - **Key**: `DATABASE_URL`
     - **Value**: Paste your Supabase connection string from Step 1
     - **Environment**: Select all three:
       - ☑️ Production
       - ☑️ Preview
       - ☑️ Development
   - Click **Save**

**Example:**
```
Key: DATABASE_URL
Value: postgresql://postgres:your_password@db.xxxxx.supabase.co:5432/postgres
Environment: Production, Preview, Development (all selected)
```

---

### Step 3: Deploy Your Application

After adding the environment variable, you need to trigger a new deployment:

**Option A: Automatic (if connected to Git)**
- Push any commit to your repository
- Vercel will automatically deploy with the new environment variable

**Option B: Manual Redeploy**
1. Go to **Deployments** tab
2. Click the **⋯** (three dots) menu on your latest deployment
3. Click **Redeploy**
4. Confirm the redeploy

---

### Step 4: Verify Connection

1. **Check Health Endpoint**
   - Visit: `https://your-app.vercel.app/health`
   - Should return:
     ```json
     {
       "status": "healthy",
       "api": "running",
       "version": "1.0.0",
       "database": "connected"
     }
     ```

2. **Check Deployment Logs**
   - Go to **Deployments** tab
   - Click on your latest deployment
   - Check **Build Logs** and **Function Logs** for any database connection errors

---

## 🔐 Finding Your Supabase Database Password

If you don't know your database password:

1. Go to Supabase Dashboard → Your Project → **Settings** → **Database**
2. Scroll to **Database password** section
3. If you see it, copy it
4. If not, click **Reset database password**
5. Copy the new password (you won't see it again!)
6. Update your connection string with the new password

---

## 📝 Connection String Format

Your Supabase connection string should follow this format:

```
postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
```

**Components:**
- `postgresql://` - Protocol
- `postgres` - Username (always "postgres" for Supabase)
- `PASSWORD` - Your database password
- `db.PROJECT_REF.supabase.co` - Your project's database host
- `5432` - Port (always 5432 for Supabase)
- `postgres` - Database name (always "postgres" for Supabase)

---

## ✅ Quick Checklist

- [ ] Got Supabase connection string (URI format)
- [ ] Replaced `[YOUR-PASSWORD]` with actual password
- [ ] Added `DATABASE_URL` to Vercel environment variables
- [ ] Selected all environments (Production, Preview, Development)
- [ ] Saved the environment variable
- [ ] Triggered a new deployment
- [ ] Verified connection at `/health` endpoint

---

## 🐛 Troubleshooting

### Error: "could not connect to server"

**Possible causes:**
- Wrong password in connection string
- Connection string format is incorrect
- Supabase project is paused (free tier pauses after inactivity)

**Solutions:**
1. Double-check password is correct
2. Verify connection string format
3. Check if Supabase project is active (restore if paused)

---

### Error: "password authentication failed"

**Solution:**
- Reset your Supabase database password
- Update the `DATABASE_URL` in Vercel with the new password
- Redeploy

---

### Error: "database does not exist"

**Solution:**
- Supabase uses `postgres` as the default database name
- Make sure your connection string ends with `/postgres`
- Don't change the database name in the connection string

---

### Tables Not Created

**Solution:**
- Tables are created automatically on first request
- Or run the schema manually:
  1. Connect to Supabase using a SQL editor
  2. Run `database/schema_postgresql.sql`
  3. Or use Supabase SQL Editor in the dashboard

---

### Environment Variable Not Working

**Solution:**
- Make sure you selected all environments (Production, Preview, Development)
- Redeploy after adding the variable
- Check that the variable name is exactly `DATABASE_URL` (case-sensitive)

---

## 🔒 Security Notes

- ✅ Never commit your `.env` file or connection strings to Git
- ✅ Use environment variables for all sensitive data
- ✅ Supabase connection strings include passwords - keep them secret
- ✅ Rotate passwords regularly
- ✅ Use Supabase's connection pooling for production (optional)

---

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)

---

## 🎯 Next Steps

After connecting:
1. ✅ Verify connection at `/health` endpoint
2. ✅ Run database schema: `database/schema_postgresql.sql`
3. ✅ Test your API endpoints
4. ✅ Monitor Supabase dashboard for connection activity

---

**Need Help?** Check the deployment logs in Vercel or Supabase dashboard for detailed error messages.
