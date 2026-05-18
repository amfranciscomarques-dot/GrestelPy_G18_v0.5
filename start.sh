#!/bin/bash
echo "A iniciar GrestelPy..."

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "A criar ambiente virtual..."
    python3 -m venv .venv
fi

# Install dependencies
echo "A instalar dependencias..."
source .venv/bin/activate
pip install -r requirements.txt --quiet

# Open browser after server starts
(sleep 2 && xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null) &

echo ""
echo "Servidor disponivel em: http://localhost:8000"
echo "Prima Ctrl+C para parar o servidor."
echo ""

python3 server.py
