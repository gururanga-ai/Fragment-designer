import { Component } from 'react'

function readBackup(key) {
  if (!key) return null
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function BackupPanel({ backupKey }) {
  const backup = readBackup(backupKey)
  if (!backup) {
    return <p className="text-xs text-[#94A3B8] italic mb-4">No recoverable backup found for this screen yet.</p>
  }
  const { savedAt, ...data } = backup
  const jsonStr = JSON.stringify(data, null, 2)
  const savedAgo = savedAt ? Math.max(0, Math.round((Date.now() - savedAt) / 1000)) : null

  const download = () => {
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'recovered-unsaved-work.json'
    a.click()
    URL.revokeObjectURL(url)
  }
  const copy = async () => {
    try { await navigator.clipboard.writeText(jsonStr) } catch { /* clipboard permission denied — user can still select+copy the textarea below */ }
  }

  return (
    <div className="mb-4">
      <p className="text-xs text-[#166534] font-semibold mb-1">
        ✓ Last unsaved state{savedAgo != null ? ` (from ${savedAgo}s ago)` : ''} recovered below — copy or download it before resetting.
      </p>
      <textarea
        readOnly
        value={jsonStr}
        rows={8}
        onClick={e => e.target.select()}
        className="w-full text-[10px] font-mono border border-[#CBD5E1] rounded p-2 bg-[#F8FAFC] resize-none"
      />
      <div className="flex gap-2 mt-2">
        <button onClick={copy} className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-semibold hover:bg-[#BFDBFE]">
          📋 Copy JSON
        </button>
        <button onClick={download} className="px-3 py-1.5 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-semibold hover:bg-[#FDE68A]">
          ⬇ Download JSON
        </button>
      </div>
    </div>
  )
}

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="h-full flex items-center justify-center p-8">
          <div className="max-w-lg bg-white border border-[#FCA5A5] rounded-lg shadow-lg p-6">
            <p className="text-[#991B1B] font-bold text-sm mb-2">⚠ {this.props.title || 'Something went wrong'}</p>
            <p className="text-xs text-[#7F1D1D] font-mono bg-[#FEF2F2] rounded p-3 mb-4 whitespace-pre-wrap break-words">
              {this.state.error.message || String(this.state.error)}
            </p>
            <p className="text-xs text-[#374151] mb-4">
              This usually means the pasted/imported JSON had an unexpected shape. Fix the data or reset below.
            </p>
            <BackupPanel backupKey={this.props.backupKey} />
            <button
              onClick={() => { this.setState({ error: null }); this.props.onReset?.() }}
              className="px-4 py-2 text-xs bg-[#1E3A8A] text-white rounded-md font-semibold hover:bg-[#1E40AF]"
            >
              Reset
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
