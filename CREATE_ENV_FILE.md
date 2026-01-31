# How to Create .env File

## Quick Method (Windows PowerShell)

1. **Open PowerShell in the backend folder:**
   ```powershell
   cd C:\wamp64\www\flashcard\backend
   ```

2. **Copy the template:**
   ```powershell
   Copy-Item env.template .env
   ```

3. **Edit the .env file** and add your API keys

## Manual Method

1. **Copy `env.template` file**
2. **Rename it to `.env`** (with the dot at the beginning)
3. **Open `.env` in a text editor**
4. **Fill in your API keys**

## Minimum Required Configuration

To get started, you only need these two values:

```env
DATABASE_URL=mysql+pymysql://root:@localhost:3306/flashcard_db
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

## Getting Your OpenAI API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Paste it in `.env` file: `OPENAI_API_KEY=sk-your-key-here`

## Verify .env File

After creating `.env`, verify it exists:

```powershell
cd backend
Test-Path .env
```

Should return: `True`

## Important Notes

- ✅ `.env` file is already in `.gitignore` (won't be committed to Git)
- ✅ Never share your `.env` file or API keys
- ✅ Change `JWT_SECRET_KEY` to a random string in production
- ✅ Optional keys can be left empty if not using those services

## Next Steps

After creating `.env`:
1. Add your OpenAI API key
2. Verify database URL is correct
3. Run: `python main.py` to start the backend

