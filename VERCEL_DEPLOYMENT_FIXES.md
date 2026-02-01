# Vercel Deployment Fixes

## Issues Fixed

### 1. ✅ Removed Invalid Packages
- Removed `python-cors==1.0.0` (doesn't exist)
- FastAPI has built-in CORS middleware

### 2. ✅ Removed Heavy ML Dependencies
- Removed `torch==2.1.0` (not compatible with Python 3.12)
- Removed `transformers==4.35.0` (requires torch)
- TrOCR is optional and gracefully falls back if unavailable

### 3. ✅ Updated for Python 3.12 Compatibility
- Updated `numpy` from `1.24.3` to `>=1.26.0` (Python 3.12 compatible)
- Changed `opencv-python` to `opencv-python-headless` (better for serverless)
- Changed all `==` to `>=` for better compatibility

### 4. ✅ Made Optional Dependencies Optional
- Commented out `spacy` and `nltk` (heavy NLP dependencies)
- These are optional and can be installed separately if needed

## Potential Remaining Issues

### pdf2image
`pdf2image` requires `poppler` system library which may not be available on Vercel. If you get errors related to this:

**Solution**: Comment it out in requirements.txt if not critical:
```python
# pdf2image>=1.16.3  # Requires poppler system library
```

### Google Cloud Libraries
These are large and may cause deployment timeouts. If you're not using them, comment them out:
```python
# google-cloud-vision>=3.4.5
# google-cloud-documentai>=2.20.1
```

### Azure Libraries
If not using Azure OCR, comment them out:
```python
# azure-cognitiveservices-vision-computervision>=0.9.0
# msrest>=0.7.1
```

## Minimal Vercel Requirements

If you still have issues, use `requirements-vercel.txt` which contains only essential dependencies:

```bash
# Copy minimal requirements for Vercel
cp requirements-vercel.txt requirements.txt
```

## Testing Locally

Test with Python 3.12 before deploying:
```bash
python3.12 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

## Next Steps

1. Try deploying with updated `requirements.txt`
2. If errors persist, check the full error message
3. Use `requirements-vercel.txt` for minimal deployment
4. Comment out optional services you're not using
