# YouTube Agent Engine - Quick Start

## 🚀 Get Started in 2 Minutes

### Step 1: Create `.env` file (if using real API)
```bash
# Windows (PowerShell)
Set-Content .env "GEMINI_API_KEY=your_key_here"

# macOS / Linux
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Pin to Taskbar (Optional - Windows)

#### Quick Method:
1. Right-click `launch.bat` → Send to → Desktop (creates shortcut)
2. Right-click the shortcut on desktop → Pin to taskbar
3. Click the taskbar icon to launch the app anytime

#### Alternative - Direct Shortcut:
1. Create a shortcut to `launch.bat` anywhere
2. Set working directory to the project folder
3. Pin to taskbar

**macOS/Linux Users:**
- Add `./launch.sh` to your applications menu
- Or make it executable: `chmod +x launch.sh && ./launch.sh`

---

## 📲 Use the Chrome Extension

### Install:
1. Start the app: `python launch.bat` (Windows) or `./launch.sh` (macOS/Linux)
2. Open Chrome → `chrome://extensions`
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked"
5. Select the `chrome-extension` folder
6. Done! 🎬 appears in your toolbar

### Use:
- **On YouTube videos**: Click the 🎬 icon in your toolbar
- **Or use the button**: YouTube videos show a "🎬 Analyze with AI" button below the title
- Results open in a new tab

---

## 💻 How to Use

### Web UI (http://127.0.0.1:8000)
```bash
python app.py              # Desktop only
python app.py --lan        # Desktop + mobile on WiFi
python app.py --demo       # Test without API key
```

### Command Line
```bash
python main.py "https://youtu.be/VIDEO_ID"
python main.py "https://youtu.be/VIDEO_ID" -t "Extract action items"
python main.py "https://youtu.be/VIDEO_ID" --list-models
```

---

## 🔗 Access Options

### Desktop (Laptop/PC)
- **Local**: http://127.0.0.1:8000
- **LAN**: http://[your-ip]:8000?token=... (with `--lan`)

### Mobile (Phone/Tablet)
```bash
python app.py --lan
```
- Scan the QR code printed in terminal
- Or manually type the URL shown
- Both devices must be on the same WiFi

---

## 🆘 Troubleshooting

### "API Key not found"
- Create `.env` file: `GEMINI_API_KEY=your_key`
- Or run: `python app.py --demo`

### Server won't start
- Port 8000 already in use?
- Try: `python app.py --port 9000`

### Chrome extension says "Server not found"
- Is the app running? Check terminal window
- Try: `python app.py` in the same project folder

### Can't access from phone
- Use `--lan` flag: `python app.py --lan`
- Both devices must be on **same WiFi**
- Check firewall: Windows may ask for permission

---

## 📝 Examples

### Analyze a TED talk
```bash
python main.py "https://www.youtube.com/watch?v=abcdef123456"
```

### Get action items
```bash
python main.py "https://youtu.be/abcdef123456" -t "List all action items"
```

### Try it first (no API key)
```bash
python app.py --demo
```

### Analyze with a specific model
```bash
python main.py "https://youtu.be/abcdef123456" -m gemini-3.6-flash
```

---

## 🔐 Security Notes

- **Desktop**: Only accessible at 127.0.0.1 (just your computer)
- **LAN**: Protected by random token, changes each restart
- **WiFi**: Don't use `--lan` on public WiFi
- **API Key**: Stored locally in `.env`, never sent to cloud

---

## 📦 What's Included

| File | Purpose |
|------|---------|
| `app.py` | Web UI server (FastAPI) |
| `main.py` | Command-line interface |
| `agent.py` | AI analysis engine (Gemini) |
| `extractor.py` | YouTube data extraction |
| `launch.bat` | Windows launcher (pin to taskbar) |
| `launch.sh` | macOS/Linux launcher |
| `chrome-extension/` | Browser extension |
| `static/index.html` | Web UI interface |

---

## ✨ Features

✓ Video summaries, takeaways, highlights, insights  
✓ Timestamp-clickable moments  
✓ Custom analysis tasks  
✓ Schema-constrained output (not hallucinations)  
✓ Prompt injection defenses  
✓ Mobile access over WiFi  
✓ Chrome extension for 1-click analysis  
✓ No public deployment needed  

---

## 🎯 Next Steps

1. **Test it**: `python app.py --demo` (no API key)
2. **Get an API key**: [Google AI Studio](https://aistudio.google.com/apikey)
3. **Create `.env`**: Add `GEMINI_API_KEY=...`
4. **Install extension**: Load `chrome-extension` folder in Chrome
5. **Pin to taskbar**: Right-click `launch.bat`, pin to taskbar

Enjoy analyzing videos! 🎬
