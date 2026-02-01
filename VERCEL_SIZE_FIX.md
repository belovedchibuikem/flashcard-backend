# Vercel Serverless Function Size Fix

## Problem
Serverless function exceeds Vercel's 250 MB unzipped limit.

## Heavy Dependencies Removed

### Removed (~300MB+ total):
1. **google-cloud-vision** (~100MB+) - Use REST API instead
2. **google-cloud-documentai** (~100MB+) - Use REST API instead  
3. **opencv-python-headless** (~50MB+) - Not critical for core functionality
4. **numpy** (~20MB+) - May be needed by pillow, but try without first
5. **boto3** (~30MB+) - Use REST API or boto3-stubs instead
6. **azure-cognitiveservices-vision-computervision** (~30MB+) - Use REST API instead
7. **cloudinary** (~10MB+) - Only if not using Cloudinary

## Solution Applied

Updated `requirements.txt` to remove heavy packages. The code already handles missing packages gracefully with try/except blocks, so the app will:
- Skip Google Cloud Vision/Document AI if not available
- Skip Azure OCR if not available  
- Skip OpenCV if not available
- Use Tesseract as fallback OCR (lightweight)

## Alternative: Use REST APIs Instead of SDKs

Instead of heavy SDKs, you can use HTTP requests:

### Google Cloud Vision API (REST)
```python
import requests
import base64

def call_google_vision_api(image_path):
    with open(image_path, 'rb') as f:
        image_content = base64.b64encode(f.read()).decode()
    
    url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    payload = {
        "requests": [{
            "image": {"content": image_content},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    response = requests.post(url, json=payload)
    return response.json()
```

### AWS Textract (REST)
```python
import requests
import base64

def call_aws_textract(image_path):
    # Use AWS Signature V4 for authentication
    # Or use AWS Lambda as proxy
    pass
```

## Current Minimal Requirements

The updated `requirements.txt` now includes only:
- Core FastAPI framework
- Database drivers
- AI APIs (OpenAI, Anthropic, Gemini) - lightweight
- Basic image processing (Pillow, Tesseract)
- PDF processing (PyPDF2, pdfplumber)
- Authentication libraries

**Estimated size**: ~50-80 MB (well under 250 MB limit)

## Testing

1. Deploy with updated `requirements.txt`
2. Test OCR functionality - should fall back to Tesseract
3. If you need Google Cloud/Azure OCR, implement REST API calls instead of SDKs

## Next Steps

If you need the removed services:
1. Implement REST API calls instead of SDKs
2. Or use a separate microservice for heavy OCR processing
3. Or use Vercel Edge Functions for lightweight operations
