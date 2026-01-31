#!/bin/bash
# Deployment script for cPanel
# Run this script via SSH after uploading files

echo "🚀 Starting FastAPI Deployment on cPanel..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment (adjust path based on cPanel Python App Manager)
# The path will be shown in cPanel Python App Manager after creating the app
# Example: source /home/username/virtualenv/api/3.9/bin/activate
echo "📦 Activating virtual environment..."
# Uncomment and update the path below:
# source /home/username/virtualenv/api/3.9/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
echo "📁 Creating uploads directory..."
mkdir -p uploads
chmod 777 uploads

# Set file permissions
echo "🔐 Setting file permissions..."
chmod 755 passenger_wsgi.py
chmod 644 *.py
find app -type f -name "*.py" -exec chmod 644 {} \;

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# Database Configuration
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/flashcard_db

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# JWT Configuration
JWT_SECRET_KEY=change-this-to-a-random-secret-key-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Upload Configuration
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=52428800

# CORS Configuration (add your frontend domain)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
EOF
    echo "✅ Created .env template. Please update with your actual values!"
fi

echo "✅ Deployment script completed!"
echo "📝 Next steps:"
echo "   1. Update .env file with your actual configuration"
echo "   2. Import database schema using phpMyAdmin"
echo "   3. Restart the Python app in cPanel"
echo "   4. Test your API endpoints"
