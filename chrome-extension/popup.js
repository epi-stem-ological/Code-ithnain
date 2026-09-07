// YouTube Agent Engine - Chrome Extension Popup

const API_BASE = "http://127.0.0.1:8000";

// DOM elements
const urlInput = document.getElementById("url");
const taskInput = document.getElementById("task");
const modelSelect = document.getElementById("model");
const analyzeBtn = document.getElementById("analyze");
const settingsBtn = document.getElementById("settings");
const statusDiv = document.getElementById("status");
const loadingDiv = document.getElementById("loading");
const serverStatus = document.getElementById("serverStatus");

// Initialize popup
document.addEventListener("DOMContentLoaded", async () => {
  // Get current tab URL
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const youtubeUrl = extractYouTubeUrl(tab.url);

  if (youtubeUrl) {
    urlInput.value = youtubeUrl;
  } else {
    showStatus("Not a YouTube page. Paste a YouTube URL above.", "error");
  }

  // Check server and load models
  await checkServer();
  await loadModels();

  // Event listeners
  analyzeBtn.addEventListener("click", handleAnalyze);
  settingsBtn.addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });
});

// Extract YouTube URL from current page
function extractYouTubeUrl(url) {
  if (url.includes("youtube.com/watch")) {
    return url;
  }
  if (url.includes("youtu.be/")) {
    return url;
  }
  return null;
}

// Check if local server is running
async function checkServer() {
  try {
    const resp = await fetch(`${API_BASE}/api/models`, { timeout: 2000 });
    if (resp.ok) {
      serverStatus.textContent = "✓ Server is running on 127.0.0.1:8000";
      serverStatus.style.background = "#efe";
      serverStatus.style.color = "#3c3";
      return true;
    }
  } catch (e) {
    serverStatus.textContent = "✗ Server not found. Start with: python app.py";
    serverStatus.style.background = "#fee";
    serverStatus.style.color = "#c33";
  }
  return false;
}

// Load available models
async function loadModels() {
  try {
    const resp = await fetch(`${API_BASE}/api/models`);
    const data = await resp.json();

    modelSelect.innerHTML = "";
    data.models.forEach(model => {
      const option = document.createElement("option");
      option.value = model.name;
      option.textContent = model.display_name || model.name;
      if (model.name === data.default) {
        option.selected = true;
      }
      modelSelect.appendChild(option);
    });
  } catch (e) {
    modelSelect.innerHTML = '<option value="">Error loading models</option>';
  }
}

// Handle analyze button click
async function handleAnalyze() {
  const url = urlInput.value.trim();
  if (!url) {
    showStatus("Please enter a YouTube URL", "error");
    return;
  }

  if (!modelSelect.value) {
    showStatus("Please start the app: python app.py", "error");
    return;
  }

  analyzeBtn.disabled = true;
  loadingDiv.classList.add("show");
  statusDiv.className = "status";

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        model: modelSelect.value,
        task: taskInput.value.trim() || undefined
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    // Open result in a new tab
    const resultWindow = window.open("about:blank", "_blank");
    resultWindow.document.write(formatResultHTML(result));
    resultWindow.document.close();

    showStatus("✓ Analysis complete! Check the new tab.", "success");

  } catch (error) {
    showStatus(`Error: ${error.message}. Make sure the server is running.`, "error");
  } finally {
    analyzeBtn.disabled = false;
    loadingDiv.classList.remove("show");
  }
}

// Format analysis result as HTML
function formatResultHTML(result) {
  const video = result.video;
  const analysis = result.analysis;

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${video.title} - Analysis</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8f9fa;
      color: #333;
      line-height: 1.6;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 24px 16px;
    }
    header {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h1 {
      font-size: 24px;
      margin-bottom: 8px;
    }
    .video-meta {
      display: flex;
      gap: 16px;
      font-size: 14px;
      color: #666;
      margin-bottom: 12px;
    }
    .video-link {
      color: #36c;
      text-decoration: none;
    }
    .video-link:hover {
      text-decoration: underline;
    }
    section {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h2 {
      font-size: 18px;
      margin-bottom: 12px;
      color: #1a1a1a;
    }
    .summary {
      font-size: 15px;
      line-height: 1.8;
    }
    .takeaway, .highlight, .insight-item, .note {
      margin-bottom: 12px;
      padding: 12px;
      background: #f5f5f5;
      border-radius: 4px;
      border-left: 3px solid #36c;
    }
    .takeaway-title {
      font-weight: 600;
      color: #1a1a1a;
      margin-bottom: 4px;
    }
    .takeaway-why {
      font-size: 13px;
      color: #666;
    }
    .timestamp {
      display: inline-block;
      background: #36c;
      color: white;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      margin-right: 8px;
    }
    .timestamp:hover {
      background: #2580cc;
    }
    .insight-category {
      font-weight: 600;
      color: #36c;
      margin-bottom: 8px;
    }
    .insight-points {
      padding-left: 16px;
    }
    .insight-point {
      margin-bottom: 6px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>${escapeHtml(video.title)}</h1>
      <div class="video-meta">
        <span>By ${escapeHtml(video.author)}</span>
        <span>${video.duration}</span>
        <span>${video.word_count} words</span>
        <a href="${escapeHtml(video.url)}" class="video-link" target="_blank">Watch on YouTube</a>
      </div>
    </header>

    <section>
      <h2>Summary</h2>
      <div class="summary">${escapeHtml(analysis.summary)}</div>
    </section>

    ${analysis.takeaways && analysis.takeaways.length > 0 ? `
    <section>
      <h2>Takeaways</h2>
      ${analysis.takeaways.map(t => `
        <div class="takeaway">
          <div class="takeaway-title">${escapeHtml(t.takeaway)}</div>
          <div class="takeaway-why">${escapeHtml(t.why)}</div>
        </div>
      `).join('')}
    </section>
    ` : ''}

    ${analysis.highlights && analysis.highlights.length > 0 ? `
    <section>
      <h2>Highlights</h2>
      ${analysis.highlights.map(h => `
        <div class="highlight">
          <div><span class="timestamp" onclick="window.open('${escapeHtml(video.url)}&t=${timeToSeconds(h.timestamp)}', '_blank')">${escapeHtml(h.timestamp)}</span>
          <strong>${escapeHtml(h.title)}</strong></div>
          <div style="margin-top: 6px; font-size: 14px; color: #666;">${escapeHtml(h.detail)}</div>
        </div>
      `).join('')}
    </section>
    ` : ''}

    ${analysis.insights && analysis.insights.length > 0 ? `
    <section>
      <h2>Insights</h2>
      ${analysis.insights.map(insight => `
        <div class="insight-item">
          <div class="insight-category">${escapeHtml(insight.category)}</div>
          <div class="insight-points">
            ${insight.points.map(point => `
              <div class="insight-point">• ${escapeHtml(point)}</div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </section>
    ` : ''}

    ${analysis.content_notes && analysis.content_notes.length > 0 ? `
    <section>
      <h2>Content Notes</h2>
      ${analysis.content_notes.map(note => `
        <div class="note">${escapeHtml(note)}</div>
      `).join('')}
    </section>
    ` : ''}
  </div>

  <script>
    function timeToSeconds(timestamp) {
      const parts = timestamp.split(':').map(Number);
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
  </script>
</body>
</html>
  `;
}

// Utility: Escape HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Show status message
function showStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

// Convert HH:MM:SS to seconds
function timeToSeconds(timestamp) {
  const parts = timestamp.split(':').map(Number);
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
}
