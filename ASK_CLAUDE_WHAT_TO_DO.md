# 🤖 CLAUDE CODE - WHAT TO ASK

## TL;DR - Just Copy-Paste These Commands

You have Claude Code open in your `coach-dashboard` folder? Perfect!

### **Step 1: Verify Everything**
Copy-paste this command in Claude Code:

```
python3 verify_setup.py
```

It will check everything. If all green ✅, skip to Step 3.

### **Step 2: If Something's Missing**

Copy-paste BOTH commands (one at a time):

```
bash setup.sh
```

Or on Windows:

```
.\setup.ps1
```

Claude will handle the rest. Takes ~2 minutes.

### **Step 3: Start the Dashboard**

```
streamlit run dashboard_app.py
```

Done! 🎉 Browser opens at http://localhost:8501

---

## What Each Command Does

### `python3 verify_setup.py`
Checks if everything is ready:
- ✅ Python installed?
- ✅ All packages installed?
- ✅ Data files present?
- ✅ App files valid?

Takes ~5 seconds. Green = ready!

### `bash setup.sh` (Linux/WSL)
Automatically sets up everything:
- Creates `data/` folder
- Creates Python virtual environment
- Installs all packages
- Verifies everything works

Takes ~2 minutes first time.

### `.\setup.ps1` (Windows)
Same as above but for Windows PowerShell.

### `streamlit run dashboard_app.py`
Starts the dashboard.
Browser opens automatically at http://localhost:8501

---

## Common Scenarios

### "I just downloaded everything"

```
1. Ask Claude: "Can you run: python3 verify_setup.py"
2. If green ✅, ask Claude: "Can you run: streamlit run dashboard_app.py"
3. Done!
```

### "Something's missing or broken"

```
1. Ask Claude: "Run the setup.sh script for me"
2. Wait for ✅ SETUP COMPLETE
3. Ask Claude: "Run streamlit run dashboard_app.py"
```

### "I want to check what's installed"

```
Ask Claude: "Can you tell me what Python packages I have installed?"
```

### "Dashboard won't load"

```
Ask Claude: "Can you:
1. Run: python3 verify_setup.py
2. Tell me what's wrong
3. Fix it"
```

### "I want to change something in the code"

```
Ask Claude: "Can you:
1. Show me the histogram code in dashboard_app.py
2. Change the colors to blue
3. Restart the dashboard"
```

---

## What Claude Can Do For You

✅ Run bash/PowerShell commands
✅ Install Python packages
✅ Check if files exist
✅ Edit code files
✅ Restart the dashboard
✅ Debug errors
✅ Explain what's happening
✅ Create missing files

---

## Pro Tips

1. **Keep Claude in the project folder** so it sees your files
2. **Copy exact error messages** if something fails
3. **Ask "Can you..." not "How to..."** - Claude executes commands!
4. **If something hangs**, press Ctrl+C to stop it

---

## Emergency Commands

If setup is totally broken:

```
rm -rf venv
pip install -r requirements.txt
python3 verify_setup.py
```

Ask Claude to run these one by one.

---

## Your Command Cheat Sheet

```bash
# Check everything
python3 verify_setup.py

# Auto-setup (Linux/WSL)
bash setup.sh

# Auto-setup (Windows)
.\setup.ps1

# Start dashboard
streamlit run dashboard_app.py

# Stop dashboard (in Claude)
# Press Ctrl+C in the terminal

# Check Python version
python3 --version

# Check if packages installed
pip list

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

---

## That's It!

🚀 **Your next move:** Open Claude Code in your `coach-dashboard` folder and ask:

```
"Can you run: python3 verify_setup.py"
```

Then follow what Claude tells you. That's all! 💪

---

**Questions?** Just ask Claude - it's there to help!
