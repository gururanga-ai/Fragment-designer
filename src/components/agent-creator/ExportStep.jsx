import { useState, useEffect } from 'react'
import StackLoginModal from './StackLoginModal'
import { buildPublishPayload, extractJson } from '../../utils/agentBuilder'
import { getStoredStackSession, clearStoredStackSession, stackPublish, stackChatStart, stackChatSend, stackChatTrace, stackChatEnd } from '../../utils/stackApi'
import { safeCopyToClipboard } from '../../utils/clipboard'
import { gleanChat } from '../../utils/gleanApi'

const TEST_MESSAGE = 'Hi'

// ── Trace tree rendering helpers ──────────────────────────────────────────
const ICONS = { root: '▶', task: '📋', route: '🔀', action: '⚙' }

function actionStatus(node) {
  const s = node.actionExecutionData?.status
  if (s) return s // SUCCESS | FAILURE | SKIPPED
  // Wrapper nodes (root/task/route) carry no actionExecutionData of their own —
  // bubble up failure from descendants so the tree shows where the break is at a glance.
  const kids = node.childTraces || []
  if (kids.some(k => actionStatus(k) === 'FAILURE')) return 'FAILURE'
  if (kids.length > 0 && kids.every(k => actionStatus(k) === 'SKIPPED')) return 'SKIPPED'
  return 'SUCCESS'
}

function durationMs(node) {
  return node.actionExecutionData?.durationMs ?? null
}

// Flattens the route's direct action children in execution order so a trace node's
// actionExecutionData.sequenceNumber (1-based) can be matched back to the real flow action at
// the same array index — the trace has no other shared identifier with the authored flow JSON.
function flattenRouteActions(root) {
  const route = root?.childTraces?.[0]?.childTraces?.[0]
  return (route?.childTraces || []).filter(n => n.objectType === 'action')
}

function TraceNode({ node, depth, failedFlowAction, onFixAction, fixingKey, fixStatusByKey }) {
  const status = actionStatus(node)
  const isFailure = status === 'FAILURE'
  const isSkipped = status === 'SKIPPED'
  const dur = durationMs(node)
  const err = node.actionExecutionData?.errorMessage
  const seq = node.actionExecutionData?.sequenceNumber
  const key = `${node.objectType}-${node.id}-${seq ?? depth}`
  const isThisFixable = isFailure && node.objectType === 'action'
  const fixKey = `seq${seq}`
  const fixState = fixStatusByKey[fixKey]

  return (
    <div style={{ marginLeft: depth * 18 }} className="mb-1.5">
      <div
        className={`rounded border px-3 py-2 text-xs ${
          isFailure ? 'bg-[#FEF2F2] border-[#FCA5A5]' : isSkipped ? 'bg-[#F1F5F9] border-[#CBD5E1] opacity-70' : 'bg-white border-[#E2E8F0]'
        }`}
      >
        <div className="flex items-center gap-2">
          <span>{ICONS[node.objectType] || '•'}</span>
          <span className="font-semibold text-[#111827]">{node.id}</span>
          <span className="text-[#94A3B8]">{node.objectType}</span>
          {dur !== null && <span className="ml-auto text-[#94A3B8]">{dur}ms</span>}
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
            isFailure ? 'bg-red-100 text-red-700' : isSkipped ? 'bg-slate-200 text-slate-600' : 'bg-green-100 text-green-700'
          }`}>
            {status}
          </span>
        </div>
        {err && (
          <div className="mt-1 text-[#991B1B] font-mono text-[10px] whitespace-pre-wrap">{err}</div>
        )}
        {isThisFixable && (
          <div className="mt-1.5 flex items-center gap-2">
            <button
              onClick={() => onFixAction(seq, err)}
              disabled={fixingKey === fixKey}
              className="text-[10px] px-2 py-1 rounded bg-[#4C1D95] text-white font-semibold hover:bg-[#5B21B6] disabled:opacity-50"
            >
              {fixingKey === fixKey ? '⏳ Asking Glean…' : '✨ Fix with AI'}
            </button>
            {failedFlowAction && (
              <span className="text-[10px] text-[#64748B]">matched to flow action "{failedFlowAction.name}"</span>
            )}
            {fixState && (
              <span className={`text-[10px] font-semibold ${fixState.startsWith('✓') ? 'text-green-700' : 'text-red-700'}`}>{fixState}</span>
            )}
          </div>
        )}
      </div>
      {(node.childTraces || []).map((child, i) => (
        <TraceNode
          key={i}
          node={child}
          depth={depth + 1}
          failedFlowAction={failedFlowAction}
          onFixAction={onFixAction}
          fixingKey={fixingKey}
          fixStatusByKey={fixStatusByKey}
        />
      ))}
    </div>
  )
}

// Applies a Glean FLOW MODE APPLY-FIX surgical `_action` array to flows.default.default — same
// remove -> modify -> add ordering FlowBuilder.jsx's insertActions uses, so a fix applied here
// behaves identically to one applied from the Build Flow tab.
function applySurgicalFix(flows, onFlowsChange, flowId, taskId, incoming) {
  const current = flows?.[flowId]?.[taskId] || []
  let updated = [...current]
  incoming.filter(a => ['remove', 'delete'].includes((a._action || '').toLowerCase())).forEach(a => {
    const idx = updated.findIndex(x => x.name === a.name)
    if (idx !== -1) updated.splice(idx, 1)
  })
  incoming.filter(a => ['modify', 'update', 'change'].includes((a._action || '').toLowerCase())).forEach(a => {
    const { _action, ...cleaned } = a
    const idx = updated.findIndex(x => x.name === a.name)
    if (idx !== -1) updated[idx] = cleaned
  })
  incoming.filter(a => ['add', 'insert'].includes((a._action || '').toLowerCase())).forEach(a => {
    const { _action, AfterActionField, Beforeactionfield, ...cleaned } = a
    let insertIdx = updated.length
    if (AfterActionField) { const idx = updated.findIndex(x => x.name === AfterActionField); if (idx !== -1) insertIdx = idx + 1 }
    else if (Beforeactionfield) { const idx = updated.findIndex(x => x.name === Beforeactionfield); if (idx !== -1) insertIdx = idx }
    updated.splice(insertIdx, 0, cleaned)
  })
  onFlowsChange(prev => ({ ...prev, [flowId]: { ...(prev[flowId] || {}), [taskId]: updated } }))
}

export default function ExportStep({ agentJson, agentId, config, flows, contents, onFlowsChange }) {
  const [copied, setCopied] = useState(false)
  const [session, setSession] = useState(() => getStoredStackSession())
  const [loginOpen, setLoginOpen] = useState(false)
  const [publishStatus, setPublishStatus] = useState(null) // { state: 'busy'|'ok'|'error', message }
  const [testOpen, setTestOpen] = useState(false)
  const [testStatus, setTestStatus] = useState(null) // { state: 'busy'|'ok'|'error', message }
  const [testTraces, setTestTraces] = useState(null)
  const [fixingKey, setFixingKey] = useState(null)
  const [fixStatusByKey, setFixStatusByKey] = useState({})
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

  // Runs the full save -> startChat -> send -> agentTrace sequence against the real stack, then
  // opens the trace panel. Each step is labeled in testStatus so a failure at any point (not just
  // an action failure inside the agent's own flow) is immediately clear.
  const runTest = async (activeSession) => {
    setTestOpen(true)
    setTestTraces(null)
    setFixStatusByKey({})
    try {
      setTestStatus({ state: 'busy', message: 'Step 1/4: Publishing agent…' })
      const payload = buildPublishPayload(config, flows, contents)
      await stackPublish({ ...activeSession, agent: payload })
      const agentIdForChat = payload.AgentId

      setTestStatus({ state: 'busy', message: 'Step 2/4: Starting chat session…' })
      const startResp = await stackChatStart({ ...activeSession, agentId: agentIdForChat })
      const sessionId = startResp?.data?.SessionId || startResp?.SessionId
      if (!sessionId) throw new Error('startChat succeeded but returned no SessionId — response: ' + JSON.stringify(startResp).slice(0, 300))

      setTestStatus({ state: 'busy', message: `Step 3/4: Sending "${TEST_MESSAGE}"…` })
      await stackChatSend({ ...activeSession, chatbotId: agentIdForChat, sessionId, message: TEST_MESSAGE })

      // Trace recording may lag slightly behind the chat call returning — retry a few times
      // with a short pause before concluding the turn genuinely didn't execute.
      let parsed = []
      for (let attempt = 1; attempt <= 4 && parsed.length === 0; attempt++) {
        setTestStatus({ state: 'busy', message: `Step 4/4: Fetching execution trace${attempt > 1 ? ` (retry ${attempt - 1})` : ''}…` })
        if (attempt > 1) await new Promise(res => setTimeout(res, 1200))
        const traceResp = await stackChatTrace({ ...activeSession, sessionId, turn: 'TURN1' })
        const records = traceResp?.data || []
        parsed = records.map(r => { try { return JSON.parse(r.Trace) } catch { return null } }).filter(Boolean)
      }
      setTestTraces(parsed)
      setTestStatus(parsed.length > 0 ? null : { state: 'error', message: 'Trace query returned no records after 4 attempts — the send call may not have actually executed the turn.' })

      // Best-effort cleanup — a failure here doesn't affect anything the user cares about,
      // the trace is already fetched, so it's not worth surfacing as a test failure.
      stackChatEnd({ ...activeSession, sessionId }).catch(() => {})
    } catch (err) {
      setTestStatus({ state: 'error', message: err.message })
    }
  }

  const handleTestClick = () => {
    if (!session) { setLoginOpen(true); return }
    runTest(session)
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

  const routeActions = testTraces?.[0] ? flattenRouteActions(testTraces[0]) : []

  const handleFixAction = async (seq, errorMessage) => {
    const fixKey = `seq${seq}`
    const flowAction = (flows?.default?.default || [])[seq - 1]
    setFixingKey(fixKey)
    setFixStatusByKey(prev => ({ ...prev, [fixKey]: null }))
    try {
      const prompt = `Fix this flow action error from a live test run. Action "${flowAction?.name || '(unknown)'}" ` +
        `(type: ${flowAction?.type || '(unknown)'}) failed with: ${errorMessage}\n\n` +
        `Current flow actions (full array, in order):\n${JSON.stringify(flows?.default?.default || [], null, 2)}\n\n` +
        `Fix only the broken action(s) using the surgical _action format. If the error is caused by an earlier action ` +
        `never producing the variable this one depends on (e.g. a missing/failed upstream action), fix that upstream ` +
        `action or add the missing dependency instead of just patching this one in isolation.`
      let fullText = ''
      await gleanChat({ conversation: [{ role: 'user', text: prompt }], useDeepResearch: false, onPartial: t => { fullText = t } })
      const fixed = extractJson(fullText)
      if (!Array.isArray(fixed) || fixed.length === 0) {
        setFixStatusByKey(prev => ({ ...prev, [fixKey]: '⚠ Glean did not return an applicable fix' }))
        return
      }
      applySurgicalFix(flows, onFlowsChange, 'default', 'default', fixed)
      setFixStatusByKey(prev => ({ ...prev, [fixKey]: `✓ Applied ${fixed.length} change(s) — re-run Test to verify` }))
    } catch (err) {
      setFixStatusByKey(prev => ({ ...prev, [fixKey]: `⚠ ${err.message}` }))
    } finally {
      setFixingKey(null)
    }
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
            onClick={handleTestClick}
            disabled={testStatus?.state === 'busy'}
            className="px-3 py-1.5 text-xs bg-[#0F766E] text-white rounded font-semibold hover:bg-[#115E59] disabled:opacity-50"
          >
            {testStatus?.state === 'busy' ? '⏳ Testing…' : '🧪 Test'}
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

      {testOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-[720px] max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#E2E8F0]">
              <span className="font-semibold text-[#111827]">🧪 Test Run — {agentId}</span>
              <button onClick={() => setTestOpen(false)} className="text-[#94A3B8] hover:text-[#111827]">✕</button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-4">
              {testStatus && (
                <div className={`rounded px-3 py-2 text-xs mb-3 ${
                  testStatus.state === 'busy' ? 'bg-[#DBEAFE] text-[#1E3A8A]' :
                  testStatus.state === 'error' ? 'bg-[#FEF2F2] text-[#991B1B]' : 'bg-[#F0FDF4] text-[#166534]'
                }`}>
                  {testStatus.state === 'busy' ? '⏳ ' : testStatus.state === 'error' ? '⚠ ' : '✓ '}{testStatus.message}
                </div>
              )}
              {testTraces?.map((root, i) => {
                const acts = flattenRouteActions(root)
                const failedIdx = acts.findIndex(n => actionStatus(n) === 'FAILURE')
                return (
                  <TraceNode
                    key={i}
                    node={root}
                    depth={0}
                    failedFlowAction={failedIdx !== -1 ? (flows?.default?.default || [])[acts[failedIdx].actionExecutionData.sequenceNumber - 1] : null}
                    onFixAction={handleFixAction}
                    fixingKey={fixingKey}
                    fixStatusByKey={fixStatusByKey}
                  />
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
