# 🤖 CLAUDE SETUP INSTRUCTIONS

## How to Use Claude Code to Set Up Your Dashboard

You have 2 setup scripts. Use one based on your system:

### **For Ubuntu / WSL (Linux):**
```bash
bash setup.sh
```

### **For Windows (PowerShell):**
```powershell
.\setup.ps1
```

---

## 📋 Step-by-Step with Claude Code

### **Option 1: Let Claude Do Everything (Easiest)**

1. **Download all files** from Claude to your computer

2. **Create project folder:**
   ```bash
   mkdir coach-dashboard
   cd coach-dashboard
   ```

3. **Copy ALL files** into this folder:
   - dashboard_app.py
   - requirements.txt
   - setup.sh (or setup.ps1 for Windows)
   - README.md
   - QUICK_START.md
   - etc.

4. **Create data subfolder:**
   ```bash
   mkdir data
   ```

5. **Copy your 4 data files** into `data/` folder:
   - coach_eligibility_20260121_195256.xlsx
   - mapping.xlsx
   - deals_flat.csv
   - owners.json

6. **Open Claude Code** in this folder and ask:
   ```
   Can you run the setup.sh script for me?
   ```

7. **Claude will:**
   - Check Python installation ✓
   - Create data folder ✓
   - Verify all files present ✓
   - Create virtual environment ✓
   - Install all dependencies ✓
   - Validate everything ✓
   - Give you the run command ✓

---

### **Option 2: Manual Steps (If Script Doesn't Work)**

If the script fails, Claude can help manually:

```
In Claude Code:
1. Check Python: python3 --version
2. Create venv: python3 -m venv venv
3. Activate: source venv/bin/activate (or .\venv\Scripts\activate on Windows)
4. Install: pip install -r requirements.txt
5. Verify: python -m py_compile dashboard_app.py
6. Run: streamlit run dashboard_app.py
```

---

## 🚀 What To Ask Claude Code

After setup completes, you can ask Claude:

**To start the app:**
```
"Can you run: streamlit run dashboard_app.py"
```

**If something's wrong:**
```
"I'm getting error X. Can you debug this?"
```

**To understand the code:**
```
"Explain how the histogram visualization works"
```

**To modify:**
```
"Change the histogram colors to blue"
```

---

## ✅ Setup Script Does

The `setup.sh` (or `setup.ps1`) script:

✓ Checks Python 3 is installed
✓ Creates `data/` folder
✓ Verifies all 4 data files present
✓ Verifies app files present (dashboard_app.py, requirements.txt)
✓ Creates virtual environment
✓ Installs all Python packages
✓ Validates package imports
✓ Checks dashboard_app.py syntax
✓ Shows success message with run command

Takes about **1-2 minutes** total.

---

## 📂 Final Folder Structure After Setup

```
coach-dashboard/
├── dashboard_app.py
├── requirements.txt
├── setup.sh
├── setup.ps1
├── README.md
├── QUICK_START.md
├── venv/                          ← Created by script
│   ├── bin/ (or Scripts/ on Windows)
│   ├── lib/
│   └── ...
└── data/
    ├── coach_eligibility_20260121_195256.xlsx
    ├── mapping.xlsx
    ├── deals_flat.csv
    └── owners.json
```

---

## 🎯 Quick Commands To Give Claude

**Setup everything:**
```
"Run setup.sh for me"
```

**Start the dashboard:**
```
"Run streamlit run dashboard_app.py"
```

**Check if Python is installed:**
```
"Check: python3 --version"
```

**Create virtual environment:**
```
"Create a Python virtual environment"
```

**Install dependencies:**
```
"Install: pip install -r requirements.txt"
```

---

## ❓ Troubleshooting with Claude

If something fails, tell Claude:

```
"I got this error: [paste error]
Can you fix it?"
```

Claude can:
- Check file paths
- Verify installations
- Fix permission issues
- Debug Python errors
- Suggest solutions

---

## 💡 Pro Tips

1. **Keep Claude in the project folder** so it sees your files
2. **Copy the exact error message** if something fails
3. **Let Claude run commands** - that's what Claude Code is for!
4. **Ask Claude to explain** anything in the code you don't understand

---

## 🎉 After Setup

Once `setup.sh` completes with "✅ SETUP COMPLETE!":

```bash
streamlit run dashboard_app.py
```

Then:
- Browser opens at http://localhost:8501 ✨
- Dashboard loads in 2 seconds
- Use filters to interact with data
- All charts are interactive

---

## 📞 If Setup Script Fails

Ask Claude Code:

```
"The setup.sh script failed. Can you:
1. Check what Python version I have
2. Try to install requirements.txt manually
3. Tell me what's missing"
```

Claude can diagnose and fix most issues!

---

## 🚀 Let's Go!

1. **Download files** from Claude
2. **Organize folder** (app files + data subfolder)
3. **Ask Claude:** "Can you run setup.sh?"
4. **Wait** for ✅ SETUP COMPLETE
5. **Ask Claude:** "Run streamlit run dashboard_app.py"
6. **Enjoy** your dashboard! 🎉

---

**Questions?** Just ask Claude Code - it's there to help! 💪
