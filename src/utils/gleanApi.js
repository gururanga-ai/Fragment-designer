/**
 * Glean API calls.
 *
 * Two paths:
 * 1. Extension relay (preferred) — ask the backend to build the exact Glean request body
 *    (pure JSON construction, no auth needed), then hand it to the MAWM Glean Bridge browser
 *    extension, which fetches Glean directly using the user's own ambient session. The cookie
 *    value never leaves the browser and never touches a shared backend — each user's calls are
 *    always made as themselves, which matters when this app is hosted somewhere shared.
 * 2. Server proxy fallback — if the extension isn't installed/reachable (e.g. local dev without
 *    it loaded yet), falls back to the old behavior: backend holds a cookie and makes the call
 *    itself. Fine for solo local dev, NOT fine for a shared deployment (one shared identity).
 *
 * Uses fetch streaming to deliver partial responses as they arrive either way.
 */

// Stable extension ID — deterministic because chrome-extension/manifest.json pins a "key"
// (see chrome-extension/extension_key.pem, not committed). Without a pinned key, Chrome would
// assign a random id per unpacked-install location and this constant would need updating per user.
export const GLEAN_BRIDGE_EXTENSION_ID = 'ajelmaojeobbcphnnehkkcejpgffbiid'

// True only if some extension has this page in its externally_connectable.matches — Chrome only
// injects chrome.runtime into a page when a matching extension is installed and enabled, so this
// doubles as a real "is the bridge extension installed" check, not just a capability check.
export function hasExtensionBridge() {
  return typeof chrome !== 'undefined' && !!chrome.runtime && typeof chrome.runtime.connect === 'function'
}

// Relays one Glean call through the browser extension. Mirrors the cumulative-text-vs-delta
// handling the backend's _stream_glean does server-side, since here we get Glean's raw
// newline-delimited-JSON lines straight from the extension instead of pre-parsed SSE.
function relayViaExtension({ url, params, body }, onPartial, signal) {
  return new Promise((resolve, reject) => {
    let port
    try {
      port = chrome.runtime.connect(GLEAN_BRIDGE_EXTENSION_ID, { name: 'glean-relay' })
    } catch (err) {
      reject(err)
      return
    }
    let lastText = ''
    let lastMessageId = null
    let settled = false

    const finish = (fn, arg) => { if (settled) return; settled = true; signal?.removeEventListener('abort', onAbort); fn(arg) }
    const onAbort = () => { try { port.disconnect() } catch { /* noop */ } finish(reject, new DOMException('Aborted', 'AbortError')) }
    signal?.addEventListener('abort', onAbort)

    port.onMessage.addListener(msg => {
      if (msg.type === 'line') {
        try {
          const obj = JSON.parse(msg.line)
          if (obj.error) { finish(reject, new Error(obj.error)); return }
          for (const m of obj.messages || []) {
            if (m.author === 'USER') continue
            // Glean tags "**Searching company knowledge**" / "**Reading:**" progress narration as
            // messageType UPDATE, distinct from the real streamed answer (messageType CONTENT) —
            // same shape otherwise, so skipping this leaks the narration into the final text.
            if (m.messageType && m.messageType !== 'CONTENT') continue
            // Deep Research mode streams its own visible reasoning/planning trace under messageType
            // CONTENT too (confirmed via raw capture: 3 distinct CONTENT messageIds in one call, the
            // real answer only in the last one) — restart accumulation whenever messageId changes so
            // only the latest (actual final) message survives.
            if (m.messageId !== lastMessageId) { lastMessageId = m.messageId; lastText = '' }
            const chunkText = (m.fragments || []).filter(f => f && typeof f.text === 'string').map(f => f.text).join('')
            if (!chunkText) continue
            lastText = chunkText.startsWith(lastText) ? chunkText : lastText + chunkText
            onPartial?.(lastText)
          }
        } catch { /* partial/non-JSON line — ignore */ }
      } else if (msg.type === 'done') {
        finish(resolve, lastText)
      } else if (msg.type === 'error') {
        finish(reject, new Error(msg.error))
      }
    })
    port.onDisconnect.addListener(() => {
      if (settled) return
      const err = chrome.runtime.lastError
      finish(reject, new Error(err ? err.message : 'Extension disconnected mid-request (this can happen on longer Glean lookups like company-knowledge search) — try again'))
    })
    port.postMessage({ type: 'glean_relay', url, params, body })
  })
}

// A mid-stream port disconnect (Chrome's hard cap on a single MV3 background-worker operation —
// no keepalive can bypass it, see background.js's comment) is not an auth failure: the user's
// own Glean session is still fine, only that one relay connection got killed. Retrying with a
// fresh port picks the live session back up. Only fall through to the shared server-proxy
// fallback (which uses a session that isn't the caller's own, and in a long-idle deployment is
// often just stale) after retries are exhausted — long calls like flow/fragment generation are
// exactly the ones likely to outlive the worker's lifetime, short ones like config rarely do.
async function relayWithRetry(built, onPartial, signal, retries = 2) {
  let lastErr
  for (let i = 0; i <= retries; i++) {
    try {
      return await relayViaExtension(built, onPartial, signal)
    } catch (err) {
      if (signal?.aborted || !/disconnected/i.test(err.message || '')) throw err
      lastErr = err
    }
  }
  throw lastErr
}

/**
 * Stream a generic Glean /chat request (Agent Creator).
 * onPartial(text) is called with the growing response as it streams.
 * Returns the final full text.
 */
export async function gleanChat({ conversation, chatId, agent_context, uploadedFileIds, useDeepResearch, mode, onPartial, onFallback, signal }) {
  const proxyCall = async () => {
    const resp = await fetch('/api/glean/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation, chatId, agent_context: agent_context || null, uploadedFileIds: uploadedFileIds || [], useDeepResearch: !!useDeepResearch, mode: mode || 'agent_creator' }),
      signal,
    })
    if (!resp.ok) {
      const err = await resp.text()
      throw new Error(`Glean error ${resp.status}: ${err}`)
    }
    return readStream(resp, onPartial)
  }

  if (hasExtensionBridge()) {
    const built = await fetch('/api/glean/chat/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation, chatId, agent_context: agent_context || null, uploadedFileIds: uploadedFileIds || [], useDeepResearch: !!useDeepResearch, mode: mode || 'agent_creator' }),
      signal,
    }).then(r => r.json())
    try {
      return await relayWithRetry(built, onPartial, signal)
    } catch (err) {
      if (signal?.aborted || !/disconnected/i.test(err.message || '')) throw err
      // Retries (relayWithRetry) already gave the extension multiple fresh-port chances using the
      // caller's own live session — falling back here means those all failed too, so this really
      // is a last resort. Uses the backend's stored session, not the caller's own — a known,
      // visible degradation, not silent.
      onFallback?.()
      return proxyCall()
    }
  }

  return proxyCall()
}

/**
 * Stream a Glean /runworkflow request (Fragment Designer agent).
 * onPartial(text) is called with the growing response.
 * Returns the final full text.
 */
export async function gleanRunWorkflow({ prompt, uploadedFileIds, fragment_json, issues, selected_node, var_pool, conversation, useDeepResearch, onPartial, onFallback, signal }) {
  const proxyCall = async () => {
    const resp = await fetch('/api/glean/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, uploadedFileIds: uploadedFileIds || [], fragment_json: fragment_json || {}, issues: issues || [], selected_node: selected_node || null, var_pool: var_pool || {}, conversation: conversation || [], useDeepResearch: !!useDeepResearch }),
      signal,
    })
    if (!resp.ok) {
      const err = await resp.text()
      throw new Error(`Glean error ${resp.status}: ${err}`)
    }
    return readStream(resp, onPartial)
  }

  if (hasExtensionBridge()) {
    const built = await fetch('/api/glean/agent/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, uploadedFileIds: uploadedFileIds || [], fragment_json: fragment_json || {}, issues: issues || [], selected_node: selected_node || null, var_pool: var_pool || {}, conversation: conversation || [], useDeepResearch: !!useDeepResearch }),
      signal,
    }).then(r => r.json())
    try {
      return await relayWithRetry(built, onPartial, signal)
    } catch (err) {
      if (signal?.aborted || !/disconnected/i.test(err.message || '')) throw err
      onFallback?.()
      return proxyCall()
    }
  }

  return proxyCall()
}

/**
 * Upload a file (image/screenshot) to Glean via backend proxy.
 * Returns { fileId, filename } or throws on error.
 */
export async function gleanUploadFile(file) {
  const form = new FormData()
  form.append('file', file, file.name || 'image.png')
  const resp = await fetch('/api/glean/upload', { method: 'POST', body: form })
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`Upload error ${resp.status}: ${err}`)
  }
  return resp.json()
}

async function readStream(resp, onPartial) {
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let fullText = ''
  let done = false

  while (!done) {
    const { value, done: streamDone } = await reader.read()
    if (streamDone) break
    const chunk = decoder.decode(value, { stream: true })
    for (const line of chunk.split('\n')) {
      const t = line.trim()
      if (!t) continue
      if (t.startsWith('data: ')) {
        const payload = t.slice(6)
        if (payload === '[DONE]') { done = true; break }
        try {
          const obj = JSON.parse(payload)
          if (obj.error) throw new Error(obj.error)
          if (obj.text !== undefined) {
            fullText = obj.text
            onPartial?.(fullText)
          }
        } catch (e) {
          if (e.message && !e.message.includes('JSON')) throw e
        }
      }
    }
  }
  return fullText
}
