#!/usr/bin/env python3
"""
Coach Dashboard - Setup Verification Script

Run this to verify your setup is complete:
    python3 verify_setup.py

This script checks:
- Python packages are installed
- Data files are present
- App files are valid
- Everything needed to run the dashboard
"""

import os
import sys
from pathlib import Path

def print_header(text):
    """Print a colored header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_python_version():
    """Check Python version"""
    print("🐍 Python Version")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"   Python {version}")
    
    if sys.version_info >= (3, 8):
        print("   ✅ Python 3.8+ (OK)\n")
        return True
    else:
        print("   ❌ Python 3.8+ required!\n")
        return False

def check_packages():
    """Check if required packages are installed"""
    print("📦 Python Packages")
    
    packages = {
        'streamlit': 'Streamlit (web framework)',
        'pandas': 'Pandas (data handling)',
        'plotly': 'Plotly (interactive charts)',
        'openpyxl': 'OpenPyXL (Excel reading)',
        'numpy': 'NumPy (numerical computing)',
    }
    
    all_ok = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"   ✅ {description}")
        except ImportError:
            print(f"   ❌ {description} - NOT INSTALLED")
            all_ok = False
    
    print()
    return all_ok

def check_data_files():
    """Check if data files exist"""
    print("📋 Data Files")
    
    data_files = [
        'coach_eligibility_20260121_195256.xlsx',
        'mapping.xlsx',
        'deals_flat.csv',
        'owners.json',
    ]
    
    all_ok = True
    for filename in data_files:
        filepath = Path('data') / filename
        if filepath.exists():
            size = filepath.stat().st_size
            size_kb = size / 1024
            print(f"   ✅ {filename} ({size_kb:.1f} KB)")
        else:
            print(f"   ❌ {filename} - NOT FOUND")
            all_ok = False
    
    print()
    return all_ok

def check_app_files():
    """Check if app files exist and are valid"""
    print("🎯 Application Files")
    
    app_files = ['dashboard_app.py', 'requirements.txt']
    
    all_ok = True
    for filename in app_files:
        filepath = Path(filename)
        if filepath.exists():
            print(f"   ✅ {filename}")
            
            # For Python files, check syntax
            if filename.endswith('.py'):
                try:
                    compile(open(filepath).read(), filename, 'exec')
                except SyntaxError as e:
                    print(f"      ❌ Syntax error: {e}")
                    all_ok = False
        else:
            print(f"   ❌ {filename} - NOT FOUND")
            all_ok = False
    
    print()
    return all_ok

def check_data_folder():
    """Check if data folder exists"""
    print("📁 Folder Structure")
    
    if Path('data').exists():
        print(f"   ✅ data/ folder exists")
        file_count = len(list(Path('data').glob('*')))
        print(f"   ✅ Contains {file_count} files")
        print()
        return True
    else:
        print(f"   ❌ data/ folder not found")
        print()
        return False

def check_streamlit_config():
    """Check if Streamlit can be imported and run"""
    print("⚙️  Streamlit Configuration")
    
    try:
        import streamlit as st
        print(f"   ✅ Streamlit version: {st.__version__}")
        print()
        return True
    except ImportError:
        print("   ❌ Streamlit not installed")
        print()
        return False

def main():
    """Run all checks"""
    print_header("COACH DASHBOARD - SETUP VERIFICATION")
    
    checks = [
        ("Python Version", check_python_version),
        ("Data Folder", check_data_folder),
        ("Data Files", check_data_files),
        ("App Files", check_app_files),
        ("Python Packages", check_packages),
        ("Streamlit Config", check_streamlit_config),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error checking {name}: {e}\n")
            results.append((name, False))
    
    # Summary
    print_header("SUMMARY")
    
    all_ok = all(result for _, result in results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print()
    
    if all_ok:
        print_header("✅ SETUP COMPLETE - READY TO RUN!")
        print("🚀 Start the dashboard with:\n")
        print("   streamlit run dashboard_app.py\n")
        print("📍 The app will open at: http://localhost:8501\n")
        return 0
    else:
        print_header("❌ SETUP INCOMPLETE")
        print("Please fix the issues above, then run this script again.\n")
        print("💡 Common fixes:\n")
        print("   1. Missing data files?")
        print("      → Copy them to the data/ folder\n")
        print("   2. Missing packages?")
        print("      → Run: pip install -r requirements.txt\n")
        print("   3. Python not installed?")
        print("      → Install from: https://www.python.org\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
