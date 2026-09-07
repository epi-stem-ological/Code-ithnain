# YouTube Agent Engine - Chrome Extension

Analyze any YouTube video directly from your browser. Get summaries, takeaways, highlights, and insights with a single click.

## Installation

### For Windows:

1. **Save the batch file to your taskbar** (optional):
   - Right-click `launch.bat` → Send to → Desktop (create shortcut)
   - Right-click the shortcut → Pin to taskbar

2. **Start the local server**:
   ```powershell
   python launch.bat
   ```
   Keep this window open while using the extension.

3. **Load the extension**:
   - Open Chrome and go to `chrome://extensions`
   - Enable "Developer mode" (toggle in top right)
   - Click "Load unpacked"
   - Select the `chrome-extension` folder
   - Done! You should see 🎬 in your toolbar

### For macOS / Linux:

1. **Create a launch script**:
   ```bash
   chmod +x launch.sh
   ./launch.sh
   ```

2. **Load the extension**:
   - Open Chrome and go to `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension` folder

## Usage

### Option 1: Click the extension icon in your toolbar
- Go to any YouTube video page
- Click the 🎬 icon
- Paste the video URL (or it auto-fills from the current page)
- Optional: customize the analysis task
- Click "Analyze"
- Results open in a new tab

### Option 2: Click the "Analyze with AI" button on YouTube
- Visit any YouTube video page
- Look for the blue "🎬 Analyze with AI" button below the title
- Click it to open the analyzer

## Requirements

- YouTube Agent Engine must be running locally on `http://127.0.0.1:8000`
- Chrome or Chromium-based browser
- `.env` file with `GEMINI_API_KEY` (or use `--demo` mode)

## Security

- The extension only communicates with your local server
- No data is sent to external services
- Your API key stays on your machine
- All analysis happens locally

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Server not found" error | Make sure the app is running: `python app.py` |
| Extension doesn't appear | Refresh the YouTube page after loading the extension |
| "Analyze" button doesn't show on YouTube | Try refreshing the page, or wait a few seconds for it to load |
| Results are blank | Check the browser console (F12 > Console) for error messages |

## Tips

- Leave the terminal/PowerShell window open while using the extension
- The extension auto-detects the current YouTube video URL
- You can override the URL if analyzing a different video
- Use custom tasks for specific analyses: "Extract all timestamps", "Summarize for a 10-year-old", etc.
