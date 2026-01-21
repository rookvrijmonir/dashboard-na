# ============================================================================
# COACH DASHBOARD - AUTOMATED SETUP SCRIPT (Windows PowerShell)
# ============================================================================
# Run this from the project folder:
#   .\setup.ps1
# 
# If you get "execution policy" error, run:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#
# Or in WSL with Claude Code:
#   Let Claude execute this script for you
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   COACH DASHBOARD - AUTOMATED SETUP                           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ============================================================================
# STEP 1: CHECK PYTHON
# ============================================================================
Write-Host "🐍 Checking Python installation..." -ForegroundColor Cyan

try {
    $python = python --version 2>&1
    Write-Host "✅ $python found" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found!" -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# STEP 2: CREATE DATA FOLDER
# ============================================================================
Write-Host ""
Write-Host "📁 Setting up folders..." -ForegroundColor Cyan

if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" > $null
    Write-Host "✅ Created data/ folder" -ForegroundColor Green
} else {
    Write-Host "✅ data/ folder already exists" -ForegroundColor Green
}

# ============================================================================
# STEP 3: CHECK DATA FILES
# ============================================================================
Write-Host ""
Write-Host "📋 Checking data files..." -ForegroundColor Cyan

$dataFiles = @(
    "coach_eligibility_20260121_195256.xlsx",
    "mapping.xlsx",
    "deals_flat.csv",
    "owners.json"
)

$missingFiles = @()

foreach ($file in $dataFiles) {
    $path = "data\$file"
    if (Test-Path $path) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Missing: $file" -ForegroundColor Yellow
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Missing data files:" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "   - $file" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "📍 Copy these files to the data\ folder and run setup.ps1 again" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "✅ All data files present!" -ForegroundColor Green

# ============================================================================
# STEP 4: CHECK APP FILES
# ============================================================================
Write-Host ""
Write-Host "🎯 Checking app files..." -ForegroundColor Cyan

$appFiles = @("dashboard_app.py", "requirements.txt")

foreach ($file in $appFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        exit 1
    }
}

# ============================================================================
# STEP 5: CREATE VIRTUAL ENVIRONMENT (OPTIONAL BUT RECOMMENDED)
# ============================================================================
Write-Host ""
Write-Host "🔧 Setting up virtual environment..." -ForegroundColor Cyan

if (-not (Test-Path "venv")) {
    Write-Host "   Creating venv..." -ForegroundColor Gray
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate venv
$activatePath = "venv\Scripts\Activate.ps1"
if (Test-Path $activatePath) {
    & $activatePath
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
}

# ============================================================================
# STEP 6: INSTALL DEPENDENCIES
# ============================================================================
Write-Host ""
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Cyan
Write-Host "   (This may take 1-2 minutes on first run)" -ForegroundColor Gray
Write-Host ""

python -m pip install --upgrade pip | Out-Null
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "✅ All dependencies installed!" -ForegroundColor Green

# ============================================================================
# STEP 7: VERIFY INSTALLATION
# ============================================================================
Write-Host ""
Write-Host "🧪 Verifying installation..." -ForegroundColor Cyan

$pythonTest = @'
import sys
try:
    import streamlit
    import pandas
    import plotly
    import openpyxl
    print("OK")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)
'@

$result = python -c $pythonTest
if ($result -eq "OK") {
    Write-Host "✅ All Python packages loaded successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Missing package" -ForegroundColor Red
    exit 1
}

# ============================================================================
# STEP 8: FINAL CHECKS
# ============================================================================
Write-Host ""
Write-Host "📊 Final validation..." -ForegroundColor Cyan

$compileTest = python -m py_compile dashboard_app.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ dashboard_app.py is valid Python code" -ForegroundColor Green
} else {
    Write-Host "❌ dashboard_app.py has syntax errors" -ForegroundColor Red
    exit 1
}

# ============================================================================
# STEP 9: SUCCESS!
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ SETUP COMPLETE!                                           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📊 You're ready to run the dashboard!" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Start the dashboard with:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   streamlit run dashboard_app.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "📍 The app will open at: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "   - Filters update charts in real-time" -ForegroundColor Gray
Write-Host "   - Hover over charts for detailed info" -ForegroundColor Gray
Write-Host "   - Click legend items to show/hide data" -ForegroundColor Gray
Write-Host "   - Press 'R' in Streamlit to refresh" -ForegroundColor Gray
Write-Host ""
Write-Host "❓ Need help?" -ForegroundColor Cyan
Write-Host "   - Read README.md for full documentation" -ForegroundColor Gray
Write-Host "   - Check QUICK_START.md for troubleshooting" -ForegroundColor Gray
Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Gray
