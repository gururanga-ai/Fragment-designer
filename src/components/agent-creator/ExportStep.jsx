import { useState, useEffect } from 'react'
import StackLoginModal from './StackLoginModal'
import { buildPublishPayload } from '../../utils/agentBuilder'
import { getStoredStackSession, clearStoredStackSession, stackPublish } from '../../utils/stackApi'
import { safeCopyToClipboard } from '../../utils/clipboard'

export default function ExportStep({ agentJson, agentId, config, flows, contents }) {
  const [copied, setCopied] = useState(false)
  const [session, setSession] = useState(() => getStoredStackSession())
  const [loginOpen, setLoginOpen] = useState(false)
  const [publishStatus, setPublishStatus] = useState(null) // { state: 'busy'|'ok'|'error', message }
  const jsonStr = JSON.stringify(agentJson, null, 2)

  useEffect(() => {
    if (publishStatus?.state !== 'ok') return
    const t = setTimeout(() => setPublishStatus(null), 6000)
    return () => clearTimeout(t)
  }, [publishStatus])

  const copyJson = async () => {
    const ok = await safeCopyToClipboard(jsonStr)
    if (!ok) { alert('Could not copy automatically — select and copy the JSON manually.'); return }
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

  const doPublish = async (activeSession) => {
    setPublishStatus({ state: 'busy', message: 'Publishing…' })
    try {
      const payload = buildPublishPayload(config, flows, contents)
      await stackPublish({ ...activeSession, agent: payload })
      setPublishStatus({ state: 'ok', message: `Published ${payload.AgentId} to ${activeSession.stackName}.` })
    } catch (err) {
      setPublishStatus({ state: 'error', message: err.message })
    }
  }

  const handlePublishClick = () => {
    if (!session) { setLoginOpen(true); return }
    doPublish(session)
  }

  const handleLoggedIn = (newSession) => {
    setSession(newSession)
    setLoginOpen(false)
    doPublish(newSession)
  }

  const logout = () => {
    clearStoredStackSession()
    setSession(null)
  }

  return (
    <div className="flex flex-col h-full">
      {loginOpen && <StackLoginModal onLogin={handleLoggedIn} onClose={() => setLoginOpen(false)} />}

      <div className="bg-[#F1F5F9] px-4 py-3 flex items-center gap-3 border-b border-[#CBD5E1] shrink-0 flex-wrap">
        <span className="font-semibold text-[#111827]">Assembled Agent JSON</span>
        <span className="text-xs text-[#94A3B8]">{agentId || 'ext-newAgent'}</span>
        {session && (
          <span className="text-xs text-[#166534] bg-[#F0FDF4] border border-[#BBF7D0] rounded px-2 py-0.5">
            🔐 {session.stackName}.{session.domain || 'sce.manh.com'} ({session.org}/{session.facilityId})
            <button onClick={logout} className="ml-2 text-[#94A3B8] hover:text-red-600">✕</button>
          </span>
        )}
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
          <button
            onClick={handlePublishClick}
            disabled={publishStatus?.state === 'busy'}
            className="px-3 py-1.5 text-xs bg-[#1E3A8A] text-white rounded font-semibold hover:bg-[#1E40AF] disabled:opacity-50"
          >
            {publishStatus?.state === 'busy' ? 'Publishing…' : '🚀 Publish to Stack'}
          </button>
        </div>
      </div>

      {publishStatus && publishStatus.state !== 'busy' && (
        <div className={`px-4 py-2 text-xs shrink-0 border-b ${
          publishStatus.state === 'ok' ? 'bg-[#F0FDF4] border-[#BBF7D0] text-[#166534]' : 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]'
        }`}>
          {publishStatus.state === 'ok' ? '✓ ' : '⚠ '}{publishStatus.message}
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-auto bg-[#1E293B] p-4">
        <pre className="text-[#E2E8F0] text-xs font-mono leading-relaxed whitespace-pre-wrap">{jsonStr}</pre>
      </div>
    </div>
  )
}
