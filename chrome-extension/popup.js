const STATUS_LABELS = {
  ok:              ["ok",    "Cookie active — Glean connected"],
  no_cookie:       ["warn",  "Not logged in to Glean"],
  cookie_removed:  ["warn",  "Cookie was removed — log in again"],
  backend_offline: ["error", "Backend offline (start ./start.sh)"],
  backend_error:   ["error", "Backend returned an error"],
};

function render(status, lastPush) {
  const [cls, label] = STATUS_LABELS[status] || ["warn", status || "Unknown"];
  document.getElementById("dot").className = `dot ${cls}`;
  document.getElementById("status-text").className = `value ${cls}`;
  document.getElementById("status-text").textContent = label;
  document.getElementById("last-push").textContent = lastPush || "—";
}

// Load stored state
chrome.storage.local.get(["status", "lastPush", "cookieNames"], ({ status, lastPush, cookieNames }) => {
  render(status, lastPush);
  if (cookieNames && cookieNames.length) {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `<div class="label">Cookies sent</div><div class="value" style="font-size:10px;word-break:break-all">${cookieNames.join(", ")}</div>`;
    document.querySelector("#push-btn").before(el);
  }
});

// Push now button — sends message to background worker
document.getElementById("push-btn").addEventListener("click", async () => {
  document.getElementById("status-text").textContent = "Pushing…";
  // Trigger background to push, then re-read state
  await chrome.runtime.sendMessage({ type: "push_now" });
  setTimeout(() => {
    chrome.storage.local.get(["status", "lastPush"], ({ status, lastPush }) => {
      render(status, lastPush);
    });
  }, 800);
});
