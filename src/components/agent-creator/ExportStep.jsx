import { useState } from 'react'

export default function ExportStep({ agentJson, agentId }) {
  const [copied, setCopied] = useState(false)
  const jsonStr = JSON.stringify(agentJson, null, 2)

  const copyJson = async () => {
    await navigator.clipboard.writeText(jsonStr)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadJson = () => {
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${agentId || 'agent'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="bg-[#F1F5F9] px-4 py-3 flex items-center gap-3 border-b border-[#CBD5E1] shrink-0">
        <span className="font-semibold text-[#111827]">Assembled Agent JSON</span>
        <span className="text-xs text-[#94A3B8]">{agentId || 'ext-newAgent'}</span>
        <div className="ml-auto flex gap-2">
          <button
            onClick={copyJson}
            className={`px-3 py-1.5 text-xs rounded font-medium transition-colors ${
              copied ? 'bg-green-100 text-green-700' : 'bg-[#FEF3C7] text-[#92400E] hover:bg-[#FDE68A]'
            }`}
          >
            {copied ? '✓ Copied!' : 'Copy JSON'}
          </button>
          <button
            onClick={downloadJson}
            className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]"
          >
            Save File
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto bg-[#1E293B] p-4">
        <pre className="text-[#E2E8F0] text-xs font-mono leading-relaxed whitespace-pre-wrap">{jsonStr}</pre>
      </div>
    </div>
  )
}
