const STATUS_LABELS = {
  ok:        ["ok",   "Logged in to Glean — ready"],
  no_cookie: ["warn", "Not logged in to Glean (log in at app.glean.com)"],
};

function render(status, lastSeen) {
  const [cls, label] = STATUS_LABELS[status] || ["warn", status || "Unknown"];
  document.getElementById("dot").className = `dot ${cls}`;
  document.getElementById("status-text").className = `value ${cls}`;
  document.getElementById("status-text").textContent = label;
  document.getElementById("last-seen").textContent = lastSeen || "—";
}

function loadAndRender() {
  chrome.storage.local.get(["status", "lastSeen"], ({ status, lastSeen }) => {
    render(status, lastSeen);
  });
}

loadAndRender();

document.getElementById("refresh-btn").addEventListener("click", async () => {
  document.getElementById("status-text").textContent = "Checking…";
  await chrome.runtime.sendMessage({ type: "refresh_status" }).catch(() => {});
  setTimeout(loadAndRender, 400);
});
