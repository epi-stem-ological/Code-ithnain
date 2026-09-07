// YouTube Agent Engine - Content Script
// Adds "Analyze with AI" button to YouTube video pages

const API_BASE = "http://127.0.0.1:8000";

// Wait for page to load and inject button
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectButton);
} else {
  injectButton();
}

function injectButton() {
  // Try multiple selectors to find where to inject the button
  const selectors = [
    "ytd-video-primary-info-renderer",
    "div#info-strings",
    "div#info"
  ];

  let injected = false;
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      addButtonToElement(element);
      injected = true;
      break;
    }
  }

  if (!injected) {
    // Fallback: watch for element to appear
    const observer = new MutationObserver(() => {
      for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && !element.dataset.aiButtonInjected) {
          addButtonToElement(element);
          observer.disconnect();
          return;
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
}

function addButtonToElement(container) {
  if (container.dataset.aiButtonInjected) return;

  const button = document.createElement("button");
  button.innerHTML = "🎬 Analyze with AI";
  button.style.cssText = `
    margin-top: 12px;
    padding: 10px 16px;
    background: linear-gradient(135deg, #36c 0%, #2580cc 100%);
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 8px rgba(51, 102, 204, 0.3);
  `;

  button.addEventListener("mouseover", () => {
    button.style.background = "linear-gradient(135deg, #2580cc 0%, #1a6fb3 100%)";
    button.style.boxShadow = "0 4px 12px rgba(51, 102, 204, 0.4)";
  });

  button.addEventListener("mouseout", () => {
    button.style.background = "linear-gradient(135deg, #36c 0%, #2580cc 100%)";
    button.style.boxShadow = "0 2px 8px rgba(51, 102, 204, 0.3)";
  });

  button.addEventListener("click", async () => {
    button.disabled = true;
    button.innerHTML = "⏳ Opening...";

    try {
      // Check if server is running
      const serverCheck = await fetch(`${API_BASE}/api/models`, { timeout: 2000 }).catch(() => null);

      if (!serverCheck) {
        alert(
          "YouTube Agent Engine is not running.\n\n" +
          "Start it with: python app.py\n\n" +
          "Then click the extension icon again."
        );
        button.disabled = false;
        button.innerHTML = "🎬 Analyze with AI";
        return;
      }

      // Open popup
      chrome.runtime.sendMessage({ action: "openAnalyzer" }, () => {
        button.disabled = false;
        button.innerHTML = "🎬 Analyze with AI";
      });

    } catch (e) {
      alert("Error: Could not reach the server. Make sure it's running on port 8000.");
      button.disabled = false;
      button.innerHTML = "🎬 Analyze with AI";
    }
  });

  container.insertBefore(button, container.firstChild);
  container.dataset.aiButtonInjected = "true";
}
