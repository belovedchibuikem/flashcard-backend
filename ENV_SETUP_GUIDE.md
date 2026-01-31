# Environment Variables Setup Guide

## Quick Setup

1. **Copy the example file:**
   ```bash
   cd backend
   copy .env.example .env
   ```

2. **Edit `.env` file** and add your API keys

3. **Required Keys** (Minimum to run):
   - `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
   - `DATABASE_URL` - Your MySQL connection string

## Getting API Keys

### 1. OpenAI API Key (REQUIRED)
- Go to: https://platform.openai.com/api-keys
- Sign up or log in
- Click "Create new secret key"
- Copy and paste into `.env` file
- **Cost**: Pay-per-use, ~$0.01 per 1K tokens

### 2. Database URL
- For WAMP default: `mysql+pymysql://root:@localhost:3306/flashcard_db`
- If MySQL has password: `mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/flashcard_db`

### 3. Azure Computer Vision (OPTIONAL - Better Handwritten OCR)
- Go to: https://azure.microsoft.com/en-us/services/cognitive-services/computer-vision/
- Create a resource
- Get your key and endpoint
- **Accuracy**: 98%+ for handwritten notes
- **Cost**: ~$1 per 1,000 pages

### 4. AWS Textract (OPTIONAL - Better Document OCR)
- Go to: https://aws.amazon.com/textract/
- Create AWS account
- Get access key and secret key
- **Accuracy**: 99%+ for documents
- **Cost**: ~$1.50 per 1,000 pages

### 5. Claude API Key (OPTIONAL - For Long Documents)
- Go to: https://console.anthropic.com/
- Sign up
- Get API key
- **Use Case**: Documents longer than 8,000 tokens
- **Cost**: ~$3 per 1M tokens

### 6. Gemini API Key (OPTIONAL - Fast Generation)
- Go to: https://makersuite.google.com/app/apikey
- Get API key
- **Use Case**: Fast, cost-efficient generation
- **Cost**: ~$0.075 per 1M tokens

## Minimum Configuration

To run the app with basic features, you only need:

```env
DATABASE_URL=mysql+pymysql://root:@localhost:3306/flashcard_db
OPENAI_API_KEY=sk-your-key-here
JWT_SECRET_KEY=any-random-string-here
```

## Recommended Configuration (For Best Accuracy)

```env
DATABASE_URL=mysql+pymysql://root:@localhost:3306/flashcard_db
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
AZURE_VISION_KEY=your-azure-key
AZURE_VISION_ENDPOINT=https://your-region.api.cognitive.microsoft.com/
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
JWT_SECRET_KEY=secure-random-string-here
```

## Security Notes

1. **Never commit `.env` file to Git** - It's already in `.gitignore`
2. **Change JWT_SECRET_KEY** - Use a random string in production
3. **Keep API keys secret** - Don't share them publicly
4. **Use different keys for development/production**

## Testing Your Configuration

After setting up `.env`, test it:

```bash
cd backend
python -c "from app.config import settings; print('OpenAI Key:', 'Set' if settings.OPENAI_API_KEY else 'Missing')"
```

## Troubleshooting

**"Module not found" errors:**
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

**"API key invalid" errors:**
- Check API key is correct
- Check for extra spaces
- Verify API key is active

**Database connection errors:**
- Check MySQL is running
- Verify DATABASE_URL format
- Test connection: `mysql -u root -p`

