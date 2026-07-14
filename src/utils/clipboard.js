/**
 * Clipboard helpers that don't throw on insecure-context origins (plain http://
 * hosts other than localhost), where navigator.clipboard is undefined.
 */

export async function safeCopyToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // fall through to legacy fallback
    }
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.focus()
  ta.select()
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  document.body.removeChild(ta)
  return ok
}

export async function safeReadClipboardText() {
  if (!navigator.clipboard?.readText) return null
  try {
    return await navigator.clipboard.readText()
  } catch {
    return null
  }
}

export async function safeReadClipboardItems() {
  if (!navigator.clipboard?.read) return null
  try {
    return await navigator.clipboard.read()
  } catch {
    return null
  }
}
