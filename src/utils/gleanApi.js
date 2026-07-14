/**
 * Glean API calls — all routed through /api/glean/* backend proxy.
 * Uses fetch streaming to deliver partial responses as they arrive.
 */

/**
 * Stream a generic Glean /chat request.
 * onPartial(text) is called with the growing response as it streams.
 * Returns the final full text.
 */
export async function gleanChat({ conversation, chatId, agent_context, onPartial, signal }) {
  const resp = await fetch('/api/glean/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation, chatId, agent_context: agent_context || null }),
    signal,
  })

  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`Glean error ${resp.status}: ${err}`)
  }

  return readStream(resp, onPartial)
}

/**
 * Stream a Glean /runworkflow request (Fragment Designer agent).
 * onPartial(text) is called with the growing response.
 * Returns the final full text.
 */
export async function gleanRunWorkflow({ prompt, uploadedFileIds, fragment_json, issues, onPartial, signal }) {
  const resp = await fetch('/api/glean/agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, uploadedFileIds: uploadedFileIds || [], fragment_json: fragment_json || {}, issues: issues || [] }),
    signal,
  })

  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`Glean error ${resp.status}: ${err}`)
  }

  return readStream(resp, onPartial)
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
