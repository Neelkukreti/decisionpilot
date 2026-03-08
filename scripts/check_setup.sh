#!/bin/bash
# Quick setup status checker

cd "$(dirname "$0")/.."

echo "========================================"
echo "🔍 DecisionPilot Setup Status"
echo "========================================"

# Check .env file exists
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    
    # Check if AWS credentials are filled in
    if grep -q "PASTE_YOUR" .env; then
        echo "⚠️  AWS credentials NOT configured (still has placeholders)"
        echo "   👉 Edit .env and add your AWS keys"
    else
        echo "✅ AWS credentials appear configured"
    fi
else
    echo "❌ .env file missing"
fi

# Check Python venv
if [ -d "backend/venv" ]; then
    echo "✅ Python virtual environment created"
else
    echo "❌ Python venv missing"
fi

# Check if dependencies installed
if [ -f "backend/venv/bin/python" ]; then
    backend/venv/bin/python -c "import boto3" 2>/dev/null && echo "✅ boto3 installed" || echo "❌ boto3 not installed"
    backend/venv/bin/python -c "import fastapi" 2>/dev/null && echo "✅ fastapi installed" || echo "❌ fastapi not installed"
else
    echo "⚠️  Cannot check dependencies (venv/bin/python not found)"
fi

echo ""
echo "========================================"
echo "📋 Next Steps:"
echo "========================================"

if grep -q "PASTE_YOUR" .env 2>/dev/null; then
    echo "1. Get AWS credentials from:"
    echo "   https://console.aws.amazon.com/iam/"
    echo ""
    echo "2. Edit .env and paste credentials"
    echo ""
    echo "3. Enable Nova models in Bedrock:"
    echo "   https://console.aws.amazon.com/bedrock/"
    echo ""
    echo "4. Run: python scripts/verify_aws.py"
else
    echo "✅ Ready to test AWS connection!"
    echo ""
    echo "Run: cd backend && source venv/bin/activate && python ../scripts/verify_aws.py"
fi

echo "========================================"
