# API Testing Guide

This guide shows you how to test your API endpoints deployed on Vercel at `https://fastapi-ashy-sigma.vercel.app/`

## Quick Test - Health Check

### 1. Browser Test (Easiest)
Open these URLs in your browser:

- **Root endpoint**: https://fastapi-ashy-sigma.vercel.app/
- **Health check**: https://fastapi-ashy-sigma.vercel.app/health
- **API Docs (Swagger UI)**: https://fastapi-ashy-sigma.vercel.app/docs
- **Alternative Docs (ReDoc)**: https://fastapi-ashy-sigma.vercel.app/redoc

### 2. FastAPI Interactive Docs (Recommended)
The easiest way to test all endpoints is using the Swagger UI:

1. Visit: **https://fastapi-ashy-sigma.vercel.app/docs**
2. You'll see all available endpoints organized by tags
3. Click on any endpoint to expand it
4. Click "Try it out" to test the endpoint
5. Fill in the parameters and click "Execute"

## Testing with cURL Commands

### Public Endpoints (No Authentication Required)

#### 1. Root Endpoint
```bash
curl https://fastapi-ashy-sigma.vercel.app/
```

Expected response:
```json
{
  "message": "AI-Powered Smart Flashcard Generator API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

#### 2. Health Check
```bash
curl https://fastapi-ashy-sigma.vercel.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "api": "running",
  "version": "1.0.0",
  "database": "connected" // or "unavailable" if DB not configured
}
```

### Authentication Endpoints

#### 3. Register a New User
```bash
curl -X POST "https://fastapi-ashy-sigma.vercel.app/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

Expected response:
```json
{
  "id": 1,
  "email": "test@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "created_at": "2024-01-01T00:00:00"
}
```

#### 4. Login
```bash
curl -X POST "https://fastapi-ashy-sigma.vercel.app/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123"
```

**Note**: FastAPI OAuth2 uses `application/x-www-form-urlencoded` for login, not JSON.

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the `access_token` for authenticated requests!**

### Authenticated Endpoints (Require Token)

Replace `YOUR_ACCESS_TOKEN` with the token from login.

#### 5. Get Current User Info
```bash
curl -X GET "https://fastapi-ashy-sigma.vercel.app/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 6. Get All Flashcards
```bash
curl -X GET "https://fastapi-ashy-sigma.vercel.app/api/flashcards/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 7. Create a Flashcard
```bash
curl -X POST "https://fastapi-ashy-sigma.vercel.app/api/flashcards/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "answer": "Python is a high-level programming language",
    "flashcard_type": "concept",
    "difficulty_level": "easy",
    "tags": ["programming", "python"]
  }'
```

#### 8. Get Topics
```bash
curl -X GET "https://fastapi-ashy-sigma.vercel.app/api/topics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 9. Get Study Materials
```bash
curl -X GET "https://fastapi-ashy-sigma.vercel.app/api/materials/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing with PowerShell (Windows)

### Register User
```powershell
$body = @{
    email = "test@example.com"
    username = "testuser"
    password = "testpassword123"
    full_name = "Test User"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://fastapi-ashy-sigma.vercel.app/api/auth/register" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Login
```powershell
$body = @{
    username = "test@example.com"
    password = "testpassword123"
}

$response = Invoke-RestMethod -Uri "https://fastapi-ashy-sigma.vercel.app/api/auth/login" `
    -Method Post `
    -ContentType "application/x-www-form-urlencoded" `
    -Body $body

$token = $response.access_token
Write-Host "Token: $token"
```

### Get Flashcards (with token)
```powershell
$headers = @{
    Authorization = "Bearer $token"
}

Invoke-RestMethod -Uri "https://fastapi-ashy-sigma.vercel.app/api/flashcards/" `
    -Method Get `
    -Headers $headers
```

## Testing with Postman

1. **Import Collection**:
   - Create a new collection named "Flashcard API"
   - Set base URL: `https://fastapi-ashy-sigma.vercel.app`

2. **Register User**:
   - Method: `POST`
   - URL: `{{baseUrl}}/api/auth/register`
   - Headers: `Content-Type: application/json`
   - Body (raw JSON):
     ```json
     {
       "email": "test@example.com",
       "username": "testuser",
       "password": "testpassword123",
       "full_name": "Test User"
     }
     ```

3. **Login**:
   - Method: `POST`
   - URL: `{{baseUrl}}/api/auth/login`
   - Headers: `Content-Type: application/x-www-form-urlencoded`
   - Body (x-www-form-urlencoded):
     - `username`: `test@example.com`
     - `password`: `testpassword123`
   - **Save the `access_token` from response**

4. **Set Collection Variable**:
   - Go to Collection Variables
   - Add variable: `token` = `{{access_token}}`

5. **Add Authorization to Collection**:
   - Go to Collection → Authorization
   - Type: `Bearer Token`
   - Token: `{{token}}`
   - This applies to all requests in the collection

6. **Test Authenticated Endpoints**:
   - All endpoints will now automatically include the Bearer token

## Testing from Mobile App

### 1. Check API Service Configuration
Make sure `mobile/lib/services/api_service.dart` has:
```dart
static const String baseUrl = 'https://fastapi-ashy-sigma.vercel.app/api';
```

### 2. Test Login Flow
1. Open the mobile app
2. Try to register/login
3. Check the console/logs for API responses
4. Verify that authentication tokens are saved

### 3. Test API Calls
The mobile app should automatically:
- Include the Bearer token in headers for authenticated requests
- Handle 401 errors and clear tokens
- Cache GET responses

## Common Issues & Solutions

### Issue: 401 Unauthorized
**Solution**: Make sure you're including the Bearer token:
```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Issue: 422 Validation Error
**Solution**: Check the request body format. Login uses `application/x-www-form-urlencoded`, not JSON.

### Issue: 500 Internal Server Error
**Possible causes**:
- Database not configured (check `/health` endpoint)
- Missing environment variables
- Check Vercel logs for detailed error messages

### Issue: CORS Error (Browser)
**Solution**: CORS is configured for web browsers. Mobile apps don't have CORS restrictions.

## Testing Checklist

- [ ] Root endpoint returns API info
- [ ] Health check shows API status
- [ ] Can register a new user
- [ ] Can login and get access token
- [ ] Can get current user info with token
- [ ] Can create flashcards
- [ ] Can get flashcards list
- [ ] Can create topics
- [ ] Can upload study materials
- [ ] Mobile app can connect to API

## API Endpoints Summary

### Public
- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (OAuth2)
- `GET /api/auth/me` - Get current user (requires auth)

### Flashcards (`/api/flashcards`)
- `GET /api/flashcards/` - List flashcards (requires auth)
- `POST /api/flashcards/` - Create flashcard (requires auth)
- `GET /api/flashcards/due` - Get due flashcards (requires auth)
- `POST /api/flashcards/generate/{material_id}` - Generate flashcards from material (requires auth)

### Topics (`/api/topics`)
- `GET /api/topics/` - List topics (requires auth)
- `POST /api/topics/` - Create topic (requires auth)

### Study Materials (`/api/materials`)
- `GET /api/materials/` - List materials (requires auth)
- `POST /api/materials/` - Upload material (requires auth)

### And many more... See `/docs` for complete list!

## Next Steps

1. Test the basic endpoints using Swagger UI at `/docs`
2. Register a test user
3. Login and get a token
4. Test authenticated endpoints
5. Test from your mobile app
6. Check Vercel logs if you encounter errors

For detailed endpoint documentation, visit: **https://fastapi-ashy-sigma.vercel.app/docs**
