#!/bin/bash
# ============================================================================
# COACH DASHBOARD - AUTOMATED SETUP SCRIPT
# ============================================================================
# Run this from the project folder:
#   bash setup.sh
# 
# Or in WSL with Claude Code:
#   Let Claude execute this script for you
# ============================================================================

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   COACH DASHBOARD - AUTOMATED SETUP                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: CHECK PYTHON
# ============================================================================
echo "🐍 Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    echo "   Install from: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"

# ============================================================================
# STEP 2: CREATE DATA FOLDER
# ============================================================================
echo ""
echo "📁 Setting up folders..."

if [ ! -d "data" ]; then
    mkdir -p data
    echo "✅ Created data/ folder"
else
    echo "✅ data/ folder already exists"
fi

# ============================================================================
# STEP 3: CHECK DATA FILES
# ============================================================================
echo ""
echo "📋 Checking data files..."

DATA_FILES=(
    "coach_eligibility_20260121_195256.xlsx"
    "mapping.xlsx"
    "deals_flat.csv"
    "owners.json"
)

MISSING_FILES=()

for file in "${DATA_FILES[@]}"; do
    if [ -f "data/$file" ]; then
        echo "✅ Found: $file"
    else
        echo "⚠️  Missing: $file"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "❌ Missing data files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "📍 Copy these files to the data/ folder and run setup.sh again"
    exit 1
fi

echo ""
echo "✅ All data files present!"

# ============================================================================
# STEP 4: CHECK APP FILES
# ============================================================================
echo ""
echo "🎯 Checking app files..."

APP_FILES=(
    "dashboard_app.py"
    "requirements.txt"
)

for file in "${APP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        echo "   This should be in the project root!"
        exit 1
    fi
done

# ============================================================================
# STEP 5: CREATE VIRTUAL ENVIRONMENT (OPTIONAL BUT RECOMMENDED)
# ============================================================================
echo ""
echo "🔧 Setting up virtual environment..."

if [ ! -d "venv" ]; then
    echo "   Creating venv..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✅ Virtual environment activated"
fi

# ============================================================================
# STEP 6: INSTALL DEPENDENCIES
# ============================================================================
echo ""
echo "📦 Installing Python dependencies..."
echo "   (This may take 1-2 minutes on first run)"
echo ""

pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo ""
echo "✅ All dependencies installed!"

# ============================================================================
# STEP 7: VERIFY INSTALLATION
# ============================================================================
echo ""
echo "🧪 Verifying installation..."

# Test imports
python3 << 'PYEOF'
import sys
try:
    import streamlit
    import pandas
    import plotly
    import openpyxl
    print("✅ All Python packages loaded successfully")
except ImportError as e:
    print(f"❌ Missing package: {e}")
    sys.exit(1)
PYEOF

# ============================================================================
# STEP 8: FINAL CHECKS
# ============================================================================
echo ""
echo "📊 Final validation..."

# Check if dashboard_app.py is valid Python
python3 -m py_compile dashboard_app.py 2> /dev/null
if [ $? -eq 0 ]; then
    echo "✅ dashboard_app.py is valid Python code"
else
    echo "❌ dashboard_app.py has syntax errors"
    exit 1
fi

# ============================================================================
# STEP 9: SUCCESS!
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ SETUP COMPLETE!                                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 You're ready to run the dashboard!"
echo ""
echo "🚀 Start the dashboard with:"
echo ""
echo "   streamlit run dashboard_app.py"
echo ""
echo "📍 The app will open at: http://localhost:8501"
echo ""
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "💡 Tips:"
echo "   - Filters update charts in real-time"
echo "   - Hover over charts for detailed info"
echo "   - Click legend items to show/hide data"
echo "   - Press 'R' in Streamlit to refresh"
echo ""
echo "❓ Need help?"
echo "   - Read README.md for full documentation"
echo "   - Check QUICK_START.md for troubleshooting"
echo ""
echo "═════════════════════════════════════════════════════════════════"
