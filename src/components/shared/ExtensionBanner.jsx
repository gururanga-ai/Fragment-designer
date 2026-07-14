import { useState, useEffect } from 'react'
import { hasExtensionBridge } from '../../utils/gleanApi'

const DISMISS_KEY = 'mawm-extension-banner-dismissed'

// Shown when the MAWM Glean Bridge extension isn't detected — without it, Glean calls fall back
// to a shared server-side session instead of the user's own, which is wrong for anyone but a
// single solo local user (see gleanApi.js's hasExtensionBridge doc comment).
export default function ExtensionBanner() {
  const [installed, setInstalled] = useState(true) // assume installed until checked, avoid a flash
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(DISMISS_KEY) === '1')
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    setInstalled(hasExtensionBridge())
  }, [])

  if (installed || dismissed) return null

  const dismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, '1')
    setDismissed(true)
  }

  return (
    <div className="bg-[#FFFBEB] border-b border-[#FDE68A] px-4 py-2 text-sm shrink-0">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[#92400E] font-semibold">⚠ Glean Bridge extension not detected</span>
        <span className="text-[#92400E] text-xs flex-1 min-w-[200px]">
          Glean requests will use a shared fallback session instead of your own login.
        </span>
        <a
          href="/api/extension/download"
          className="px-3 py-1 text-xs bg-[#1E3A8A] text-white rounded font-semibold hover:bg-[#1E40AF]"
        >
          ⬇ Download Extension
        </a>
        <button
          onClick={() => setExpanded(e => !e)}
          className="px-3 py-1 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-medium hover:bg-[#FDE68A]"
        >
          {expanded ? 'Hide steps' : 'Install steps'}
        </button>
        <button onClick={dismiss} className="text-[#92400E] hover:text-[#78350F] text-xs ml-auto">
          Dismiss for now
        </button>
      </div>
      {expanded && (
        <ol className="mt-2 pl-5 text-xs text-[#92400E] space-y-1 list-decimal">
          <li>Click <strong>Download Extension</strong> above — saves <code>mawm-glean-bridge-extension.zip</code></li>
          <li>Unzip it somewhere you won't move/delete (e.g. <code>~/mawm-glean-bridge</code>) — Chrome loads it from that folder, so unzip before the next step</li>
          <li>Open <code>chrome://extensions</code> in a new tab</li>
          <li>Turn on <strong>Developer mode</strong> (top-right toggle)</li>
          <li>Click <strong>Load unpacked</strong> and select the unzipped <code>mawm-glean-bridge</code> folder</li>
          <li>Make sure you're logged in to Glean (<a href="https://app.glean.com" target="_blank" rel="noreferrer" className="underline">app.glean.com</a>) in this browser</li>
          <li>Reload this page — this banner should disappear once the extension is detected</li>
        </ol>
      )}
    </div>
  )
}
