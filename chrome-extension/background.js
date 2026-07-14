const BACKEND_URL = "http://localhost:8000/api/glean/set-cookie";
const GLEAN_URL   = "https://manhattan-associates-be.glean.com";

async function pushCookies() {
  try {
    // Get ALL cookies for the Glean domain
    const allCookies = await chrome.cookies.getAll({ url: GLEAN_URL });

    if (!allCookies || allCookies.length === 0) {
      await chrome.storage.local.set({ status: "no_cookie", lastPush: null });
      return;
    }

    // Build name→value dict
    const cookieDict = {};
    for (const ck of allCookies) {
      cookieDict[ck.name] = ck.value;
    }

    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: cookieDict }),
    });

    if (resp.ok) {
      const now = new Date().toLocaleTimeString();
      const count = allCookies.length;
      await chrome.storage.local.set({
        status: "ok",
        lastPush: `${now} (${count} cookies)`,
        cookieNames: Object.keys(cookieDict),
      });
      console.log(`[MAWM Bridge] Pushed ${count} cookies at ${now}`);
    } else {
      await chrome.storage.local.set({ status: "backend_error", lastPush: null });
    }
  } catch (err) {
    await chrome.storage.local.set({ status: "backend_offline", lastPush: null });
  }
}

chrome.runtime.onInstalled.addListener(pushCookies);
chrome.runtime.onStartup.addListener(pushCookies);

// Re-push whenever any Glean cookie changes
chrome.cookies.onChanged.addListener(({ cookie }) => {
  if (cookie.domain.includes("glean.com")) {
    pushCookies();
  }
});

// Manual push from popup
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "push_now") pushCookies();
});
