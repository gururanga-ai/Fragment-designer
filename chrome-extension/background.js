const GLEAN_URL = "https://manhattan-associates-be.glean.com";

// ── Login status (for the popup) — reads a cookie's presence, never its value ──────────────
async function refreshStatus() {
  const cookies = await chrome.cookies.getAll({ url: GLEAN_URL, name: "glean-session-store" });
  await chrome.storage.local.set({
    status: cookies.length ? "ok" : "no_cookie",
    lastSeen: new Date().toLocaleTimeString(),
  });
}
chrome.runtime.onInstalled.addListener(refreshStatus);
chrome.runtime.onStartup.addListener(refreshStatus);
chrome.cookies.onChanged.addListener(({ cookie }) => {
  if (cookie.domain.includes("glean.com")) refreshStatus();
});

// Manual refresh from the popup (internal message, not external)
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "refresh_status") {
    refreshStatus().then(() => sendResponse({ ok: true }));
    return true; // keep the message channel open for the async response
  }
});

// ── Relay: web app connects, sends { type:'glean_relay', url, body, params }. We fetch Glean
// directly from this background context using the browser's own ambient session
// (credentials:'include' — the cookie value itself is never read, serialized, or transmitted
// anywhere by this extension) and stream the response back over the port line-by-line, mirroring
// Glean's own newline-delimited JSON stream so the web app's existing parsing logic works
// unchanged. This replaces the old model of pushing the raw cookie value to a shared backend,
// which meant every user of a shared-hosted web app was making Glean calls under whoever pushed
// last — this way each user's own browser session is always what gets used, for every call. ──
// Company-knowledge-search requests (e.g. Enhance Prompt) can run well past Chrome's ~30s
// background service-worker idle timeout. An open port is *supposed* to keep the worker alive,
// but this has been unreliable in practice for onConnectExternal ports on some Chrome versions —
// ticking a real chrome.* API call periodically resets the idle timer as a belt-and-suspenders
// measure so long-running relays don't get killed mid-stream (which surfaces to the user as an
// unexplained "Extension disconnected" with no actual error).
function startKeepAlive() {
  const id = setInterval(() => { chrome.runtime.getPlatformInfo(() => {}); }, 15000);
  return () => clearInterval(id);
}

chrome.runtime.onConnectExternal.addListener((port) => {
  port.onMessage.addListener(async (msg) => {
    if (!msg || msg.type !== "glean_relay") return;
    const stopKeepAlive = startKeepAlive();
    try {
      const target = new URL(msg.url);
      for (const [k, v] of Object.entries(msg.params || {})) target.searchParams.set(k, v);

      const resp = await fetch(target.toString(), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "text/plain" },
        body: JSON.stringify(msg.body),
      });

      if (resp.status === 401) {
        port.postMessage({ type: "error", error: "Glean 401 — not logged in to Glean in this browser" });
        return;
      }
      if (!resp.ok || !resp.body) {
        const text = await resp.text().catch(() => "");
        port.postMessage({ type: "error", error: `Glean HTTP ${resp.status}: ${text.slice(0, 200)}` });
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n")) !== -1) {
          const line = buf.slice(0, idx).trim();
          buf = buf.slice(idx + 1);
          if (line) port.postMessage({ type: "line", line });
        }
      }
      port.postMessage({ type: "done" });
    } catch (err) {
      port.postMessage({ type: "error", error: String(err && err.message || err) });
    } finally {
      stopKeepAlive();
    }
  });
});
