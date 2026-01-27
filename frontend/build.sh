#!/bin/bash
# Build script for Railway frontend deployment
# Injects the API URL into index.html

if [ -n "$KIRO_API_URL" ]; then
    echo "Injecting API URL: $KIRO_API_URL"
    sed -i "s|// window.KIRO_API_URL = 'https://your-api.railway.app';|window.KIRO_API_URL = '$KIRO_API_URL';|g" index.html
    # Backup: try matching just the variable assignment if the full line failed
    if grep -q "// window.KIRO_API_URL" index.html; then
        sed -i "s|// window.KIRO_API_URL = .*|window.KIRO_API_URL = '$KIRO_API_URL';|g" index.html
    fi
    echo "API URL injected successfully"
else
    echo "Warning: KIRO_API_URL not set, frontend will use default localhost"
fi

# Install serve for static file serving
npm install
