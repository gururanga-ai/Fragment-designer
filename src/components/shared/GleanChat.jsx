import { useState, useRef, useEffect, useCallback } from 'react'
import { gleanChat, gleanRunWorkflow, gleanUploadFile } from '../../utils/gleanApi'
import { extractJson } from '../../utils/agentBuilder'
import { safeReadClipboardItems, safeReadClipboardText } from '../../utils/clipboard'

/**
 * Shared Glean streaming chat panel.
 *
 * mode: 'config' | 'flow' | 'agent' (Fragment Designer agent)
 * fragmentJson: optional — injected into prompt in agent mode
 * onActionBar: called with { type, data } when AI returns JSON
 */
export default function GleanChat({
  mode = 'general',
  chatId,
  onChatIdChange,
  history = [],
  onHistoryChange,
  onActionBar,
  title = 'Glean AI',
  systemPrompt,
  fragmentJson,
  selectedPath,
  varPool,
  currentFlow,
  className = '',
}) {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [partialText, setPartialText] = useState('')
  const [actionBar, setActionBar] = useState(null)
  const [suggestions, setSuggestions] = useState(null)  // {items: [], checkedSet: Set}
  const [cookieOverride, setCookieOverride] = useState('')
  const [cookieOpen, setCookieOpen] = useState(false)
  const [cookieSaved, setCookieSaved] = useState(false)
  const [thinkingExpanded, setThinkingExpanded] = useState(false)
  // Fast (default) vs Thinking mode — maps to Glean's own useDeepResearch flag (confirmed via
  // HAR capture of the real glean.com UI). Thinking = slower, more thorough; Fast = quick.
  const [deepResearch, setDeepResearch] = useState(false)
  // Attachments: [{name, fileId, preview}] — preview is dataURL for images
  const [attachments, setAttachments] = useState([])
  const [uploading, setUploading] = useState(false)
  const endRef = useRef(null)
  const abortRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, partialText])

  const buildPrompt = useCallback((text) => text, [])

  // Walk fragmentJson down selectedPath (['Slots','Default',0,...]) to describe what the user
  // is actually looking at in the canvas right now — without this, "fix this"/"correct this
  // container" in the sidebar chat had nothing to anchor to but the full fragment tree + prose,
  // so Glean would guess (or mangle) the wrong node instead of the one on screen.
  const describeSelectedNode = useCallback(() => {
    if (!fragmentJson || !Array.isArray(selectedPath) || selectedPath.length === 0) return null
    let node = fragmentJson
    for (const seg of selectedPath) {
      if (node == null) return null
      node = node[seg]
    }
    if (!node || typeof node !== 'object') return null
    return {
      path: selectedPath,
      type: node.Container || node.Element || '',
      config: node.Config || {},
      css: node.Style?.css || {},
      init: node.Init || undefined,
    }
  }, [fragmentJson, selectedPath])

  const uploadFile = useCallback(async (file) => {
    // Preview the image locally first
    const preview = file.type.startsWith('image/') ? await new Promise(res => {
      const r = new FileReader(); r.onload = e => res(e.target.result); r.readAsDataURL(file)
    }) : null
    setUploading(true)
    try {
      const { fileId, filename } = await gleanUploadFile(file)
      setAttachments(a => [...a, { name: filename || file.name, fileId, preview }])
    } catch (err) {
      alert(`Upload failed: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }, [])

  const handlePaste = useCallback(async (e) => {
    const items = e.clipboardData?.items
    if (!items) return
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) await uploadFile(file)
        return
      }
    }
  }, [uploadFile])

  const handleClipboardPaste = useCallback(async () => {
    // Try full clipboard read (images + text)
    const items = await safeReadClipboardItems()
    if (items) {
      for (const item of items) {
        const imgType = item.types.find(t => t.startsWith('image/'))
        if (imgType) {
          const blob = await item.getType(imgType)
          const file = new File([blob], 'pasted-image.png', { type: imgType })
          await uploadFile(file)
          return
        }
        if (item.types.includes('text/plain')) {
          const blob = await item.getType('text/plain')
          const text = await blob.text()
          if (text.trim()) {
            setInput(prev => prev ? `${prev}\n${text}` : text)
            setTimeout(() => inputRef.current?.focus(), 0)
          }
          return
        }
      }
      return
    }
    // Fallback: text-only read (widely supported)
    const text = await safeReadClipboardText()
    if (text && text.trim()) {
      setInput(prev => prev ? `${prev}\n${text}` : text)
      setTimeout(() => inputRef.current?.focus(), 0)
      return
    }
    alert('Clipboard access unavailable. Use Ctrl+V in the text area instead.')
  }, [uploadFile])

  const send = useCallback(async () => {
    const text = input.trim()
    if ((!text && attachments.length === 0) || streaming) return
    setInput('')
    setActionBar(null)
    setSuggestions(null)
    setPartialText('')
    setThinkingExpanded(false)
    const att = attachments
    setAttachments([])

    const userText = text + (att.length > 0 ? ` [${att.length} attachment(s)]` : '')
    const newHistory = [...history, { role: 'user', text: userText }]
    onHistoryChange?.(newHistory)

    setStreaming(true)
    abortRef.current = new AbortController()

    try {
      let full = ''
      const fn = mode === 'agent' ? gleanRunWorkflow : gleanChat
      const prompt = buildPrompt(text)
      const uploadedFileIds = att.map(a => a.fileId).filter(Boolean)
      const isNonEmptyFrag = fragmentJson && typeof fragmentJson === 'object' && Object.keys(fragmentJson).length > 0
      const selectedNode = describeSelectedNode()
      const isNonEmptyVarPool = varPool && typeof varPool === 'object' && Object.keys(varPool).length > 0
      const args = mode === 'agent'
        ? { prompt, uploadedFileIds, fragment_json: isNonEmptyFrag ? fragmentJson : {}, issues: [], selected_node: selectedNode, var_pool: isNonEmptyVarPool ? varPool : {}, conversation: history.map(m => ({ role: m.role, text: m.text })), useDeepResearch: deepResearch, onPartial: t => { full = t; setPartialText(t) }, signal: abortRef.current.signal }
        : { conversation: newHistory, chatId, agent_context: currentFlow || null, useDeepResearch: deepResearch, onPartial: t => { full = t; setPartialText(t) }, signal: abortRef.current.signal }

      await fn(args)
      setPartialText('')
      const narrative = tryShowActionBar(full)
      // If response has narrative, show it as the AI bubble; otherwise show raw text
      const displayText = narrative || full
      const withAI = [...newHistory, { role: 'ai', text: displayText }]
      onHistoryChange?.(withAI)
    } catch (err) {
      if (err.name !== 'AbortError') {
        const msg = String(err.message)
        const withErr = [...newHistory, { role: 'error', text: msg }]
        onHistoryChange?.(withErr)
      }
      setPartialText('')
    } finally {
      setStreaming(false)
    }
  }, [input, attachments, streaming, history, chatId, mode, onHistoryChange, buildPrompt, fragmentJson, currentFlow, deepResearch, describeSelectedNode, varPool])

  const stop = () => { abortRef.current?.abort(); setStreaming(false); setPartialText('') }

  const tryShowActionBar = text => {
    const parsed = extractJson(text)
    if (!parsed) return null

    if (Array.isArray(parsed) && parsed.length > 0) {
      // Extract _narrative from first element — it's for display only, not an action
      let narrative = null
      let actionData = parsed
      if (parsed[0]?._narrative && typeof parsed[0]._narrative === 'string') {
        narrative = parsed[0]._narrative
        actionData = parsed.slice(1)
        if (actionData.length === 0) {
          // Pure narrative — no action to apply
          return narrative
        }
      }

      // Separate _fragment_update items from flow action items
      const fragmentUpdates = actionData.filter(a => a._fragment_update === true)
      const pureActions = actionData.filter(a => !a._fragment_update)

      // Pure fragment-only response (no flow action changes)
      if (pureActions.length === 0 && fragmentUpdates.length > 0) {
        const fragNames = fragmentUpdates.map(f => f.name || 'fragment').join(', ')
        setActionBar({
          type: 'actions',
          data: { actions: [], fragmentUpdates },
          label: `Fragment update: ${fragNames}`,
          btn: '⚡ Apply Fragment Changes',
        })
        return narrative
      }

      const isRedo = pureActions[0]?._redo === true
      const modifyCount = pureActions.filter(a => a._modify === true || ['modify', 'update', 'change'].includes((a._action || '').toLowerCase())).length
      const removeCount = pureActions.filter(a => a._remove === true || ['remove', 'delete'].includes((a._action || '').toLowerCase())).length
      const addCount = pureActions.filter(a => a._add === true || ['add', 'insert'].includes((a._action || '').toLowerCase())).length
      const hasPosition = !isRedo && pureActions.some(a => a.AfterActionField || a.Beforeactionfield)
      const realCount = isRedo ? pureActions.length - 1 : pureActions.length
      const fragSuffix = fragmentUpdates.length > 0 ? ` + ${fragmentUpdates.length} fragment` : ''

      const label = (isRedo
        ? `Full flow redo — ${realCount} action(s)`
        : removeCount > 0 && modifyCount > 0
        ? `${modifyCount} modify + ${removeCount} remove`
        : removeCount > 0
        ? `${removeCount} action(s) to remove`
        : modifyCount > 0
        ? `${modifyCount} action(s) to modify in place`
        : addCount > 0 && hasPosition
        ? `${addCount} action(s) — positional insert`
        : `${realCount} action(s) detected`) + fragSuffix

      const btn = (isRedo
        ? `⚡ Replace Entire Flow (${realCount})`
        : removeCount > 0 && modifyCount > 0
        ? `⚡ Apply Changes (${modifyCount} modify, ${removeCount} remove)`
        : removeCount > 0
        ? `⚡ Remove ${removeCount} Action(s)`
        : modifyCount > 0
        ? `⚡ Apply ${modifyCount} Modification(s)`
        : addCount > 0
        ? `⚡ Insert ${addCount} Action(s)`
        : `⚡ Insert ${realCount} Action(s)`) + (fragmentUpdates.length > 0 ? ' + Fragment' : '')

      const barData = fragmentUpdates.length > 0 ? { actions: pureActions, fragmentUpdates } : pureActions
      setActionBar({ type: 'actions', data: barData, label, btn })
      return narrative
    }

    if (parsed && typeof parsed === 'object') {
      // Suggestions envelope — Fragment Designer agent
      if (parsed.suggestions && Array.isArray(parsed.suggestions)) {
        const items = parsed.suggestions
        const isActionable = s => (s.fix_props && Object.keys(s.fix_props).length > 0)
          || (s.remove_props && s.remove_props.length > 0)
          || s.child_node || s.new_node || s.merge_data
        const autoSafe = items.filter(s => s.safe_to_auto_apply && isActionable(s))
        setSuggestions({ items, checkedSet: new Set(autoSafe.map((_, i) => items.indexOf(autoSafe[i]))) })
        setActionBar({
          type: 'suggestions',
          data: parsed,
          label: `${items.length} suggestion(s) — ${autoSafe.length} safe to auto-apply`,
          btn: `Apply ${autoSafe.length} Safe`,
        })
        const preview = items.slice(0, 3).map(s => s.suggestion_label || s.message).filter(Boolean).join('; ')
        return `Found ${items.length} suggestion${items.length === 1 ? '' : 's'}${preview ? `: ${preview}` : ''} — see panel below.`
      }

      const m = parsed.mode
      // Fragment handoff (from agent JSON copilot FRAGMENT MODE)
      if (m === 'fragment_handoff') {
        setActionBar({
          type: 'fragment_handoff',
          data: parsed,
          label: `Fragment handoff → ${parsed.targetAgentName || 'Fragment UI Creation'}`,
          btn: 'Open Fragment Agent',
        })
        return
      }
      if (m === 'content_handoff') {
        setActionBar({ type: 'content', data: parsed, label: `Content: ${parsed.fileName || 'script'}`, btn: 'Add to Contents' })
        return
      }
      if (parsed.full_fragment_update || parsed.full_fragment) {
        setActionBar({ type: 'agent', data: parsed, label: 'Full fragment update', btn: '⚡ Apply Fragment' })
        return
      }

      // Content-based config detection: agent JSON copilot CONFIG MODE
      // Detect by presence of canonical config keys regardless of chat mode
      const isConfigShape = parsed.agentId !== undefined
        || parsed.agentName !== undefined
        || parsed.agentRootResourceFolders !== undefined
        || parsed.defaults !== undefined
      if (isConfigShape) {
        const keys = Object.keys(parsed).filter(k => !k.startsWith('_')).slice(0, 4)
        setActionBar({ type: 'config', data: parsed, label: `Config: ${keys.join(', ')}`, btn: 'Apply to Config Form' })
        return
      }

      // Single-action update (flow mode — action object with type field)
      if (parsed.type && (mode === 'flow' || mode === 'general')) {
        setActionBar({ type: 'update_action', data: parsed, label: `Action: ${parsed.name || parsed.type}`, btn: '⚡ Apply to Selected Action' })
        return
      }

      // Fragment agent — any object
      if (mode === 'agent') {
        setActionBar({ type: 'agent', data: parsed, label: 'Fragment update', btn: '⚡ Apply to Fragment' })
        return
      }

      // Fallback: generic config object
      if (mode === 'config' || mode === 'general') {
        const keys = Object.keys(parsed).filter(k => !k.startsWith('_')).slice(0, 4)
        setActionBar({ type: 'config', data: parsed, label: `Config: ${keys.join(', ')}`, btn: 'Apply to Config Form' })
      }
    }
  }

  const handleActionBarBtn = () => {
    onActionBar?.(actionBar)
    setActionBar(null)
  }

  const handleApplySelected = () => {
    if (!suggestions) return
    const selected = suggestions.items.filter((_, i) => suggestions.checkedSet.has(i))
    onActionBar?.({ type: 'suggestions', data: { suggestions: selected } })
    setSuggestions(null)
    setActionBar(null)
  }

  const isActionableSuggestion = s => (s.fix_props && Object.keys(s.fix_props).length > 0)
    || (s.remove_props && s.remove_props.length > 0)
    || s.child_node || s.new_node || s.merge_data

  const handleApplyAllSafe = () => {
    if (!suggestions) return
    const safe = suggestions.items.filter(s => s.safe_to_auto_apply && isActionableSuggestion(s))
    onActionBar?.({ type: 'suggestions', data: { suggestions: safe } })
    setSuggestions(null)
    setActionBar(null)
  }

  const toggleCheck = i => {
    setSuggestions(s => {
      const newSet = new Set(s.checkedSet)
      if (newSet.has(i)) newSet.delete(i)
      else newSet.add(i)
      return { ...s, checkedSet: newSet }
    })
  }

  const clearChat = () => {
    onHistoryChange?.([])
    setActionBar(null)
    setSuggestions(null)
    setPartialText('')
    onChatIdChange?.(null)
  }

  const saveCookieOverride = async () => {
    if (!cookieOverride.trim()) return
    try {
      await fetch('/api/glean/set-cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookie: cookieOverride.trim() }),
      })
      setCookieSaved(true)
      setCookieOpen(false)
      setTimeout(() => setCookieSaved(false), 3000)
    } catch {
      alert('Failed to save cookie override.')
    }
  }

  const welcome = mode === 'config'
    ? 'Hello! I can help fill in the agent configuration.\n\nTry: "Suggest config for a fulfillment agent" or "Autofill this agent".\n\nI\'ll return a JSON object to apply directly to the form.'
    : mode === 'flow'
    ? 'Hello! Describe what this agent flow should do and I\'ll generate the action steps.\n\nExample: "Load order data from DB, filter by open status, group by carrier, then render a summary table."'
    : mode === 'agent'
    ? 'Hello! I\'m the Fragment Designer agent. I can:\n\n• Generate fragment JSON from a description\n• Fix layout / CSS issues\n• Return patch suggestions for specific nodes\n• Suggest component arrangements\n\nI\'ll automatically receive your current fragment for context.'
    : 'Hello! How can I help you with this agent?'

  // Detect "thinking" in partial text — long pre-JSON preamble
  const looksLikeThinking = partialText.length > 60 && !extractJson(partialText)

  return (
    <div className={`flex flex-col bg-[#0F172A] ${className}`} style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Top bar */}
      <div className="flex items-center bg-[#1E293B] px-4 py-2 shrink-0">
        <span className="text-[#60A5FA] font-bold text-sm">glean.</span>
        <span className="text-[#34D399] font-bold text-sm">ai</span>
        <span className="text-[#94A3B8] text-xs ml-2 flex-1 truncate">{title}</span>
        {fragmentJson && <span className="text-[#34D399] text-[10px] mr-2">📎 fragment</span>}
        {cookieSaved && <span className="text-[#34D399] text-xs mr-2">Cookie saved</span>}
        <button
          onClick={() => setDeepResearch(d => !d)}
          title={deepResearch ? 'Thinking mode — slower, more thorough (Glean useDeepResearch)' : 'Fast mode — quick response'}
          className={`text-[10px] px-2 py-0.5 rounded-full mr-2 font-medium border transition-colors ${
            deepResearch
              ? 'bg-[#4C1D95] text-[#DDD6FE] border-[#7C3AED]'
              : 'bg-transparent text-[#94A3B8] border-[#334155] hover:border-[#60A5FA] hover:text-[#60A5FA]'
          }`}
        >
          {deepResearch ? '🧠 Thinking' : '⚡ Fast'}
        </button>
        <button onClick={() => setCookieOpen(o => !o)} title="Set Glean session cookie manually" className="text-[#94A3B8] hover:text-[#60A5FA] text-xs mr-2">🍪</button>
        <button onClick={clearChat} className="text-[#94A3B8] hover:text-white text-xs">Clear</button>
      </div>

      {/* Cookie override panel */}
      {cookieOpen && (
        <div className="bg-[#1E293B] border-b border-[#334155] px-3 py-2 shrink-0">
          <p className="text-[#94A3B8] text-xs mb-1">
            Paste <code className="text-[#60A5FA]">glean-session-store</code> cookie value:
            <span className="text-[#64748B] ml-1">(Chrome → F12 → Application → Cookies)</span>
          </p>
          <div className="flex gap-2">
            <input type="password" value={cookieOverride} onChange={e => setCookieOverride(e.target.value)} placeholder="eyJ..."
              className="flex-1 bg-[#0F172A] text-[#E2E8F0] text-xs px-2 py-1 rounded outline-none border border-[#334155] focus:border-[#60A5FA]" />
            <button onClick={saveCookieOverride} className="text-xs px-3 py-1 bg-[#1E3A8A] text-[#93C5FD] rounded hover:bg-[#2563EB]">Save</button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3 dark-scroll">
        {history.length === 0 && !streaming && <Bubble role="ai" text={welcome} />}
        {history.map((msg, i) => <Bubble key={i} role={msg.role} text={msg.text} />)}

        {/* Streaming: thinking indicator + live text */}
        {streaming && (
          <div>
            {looksLikeThinking ? (
              <>
                <div className="flex items-center gap-1 mb-1 cursor-pointer" onClick={() => setThinkingExpanded(e => !e)}>
                  <span className="text-[#A78BFA] text-xs font-semibold">💭 Thinking</span>
                  <span className="text-[#64748B] text-xs">{thinkingExpanded ? '▼' : '▶'}</span>
                  <div className="flex gap-0.5 ml-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-1 h-1 rounded-full bg-[#6B7280] animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />
                    ))}
                  </div>
                </div>
                {thinkingExpanded && (
                  <div className="bg-[#1E293B] rounded px-3 py-2 text-[#64748B] text-xs whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {partialText}
                  </div>
                )}
              </>
            ) : (
              <>
                {partialText && (
                  <div>
                    <p className="text-[#A78BFA] text-xs font-semibold mb-1">✨ Glean AI</p>
                    <p className="text-[#E2E8F0] text-sm whitespace-pre-wrap leading-relaxed">{partialText}</p>
                  </div>
                )}
                {!partialText && <p className="text-[#64748B] text-xs italic animate-pulse">Glean is thinking…</p>}
              </>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Suggestions panel */}
      {suggestions && (
        <div className="bg-[#0F172A] border-t border-[#334155] px-3 py-2 shrink-0 max-h-52 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[#A78BFA] text-xs font-bold">✨ Suggestions ({suggestions.items.length})</span>
            <div className="flex gap-1">
              <button onClick={handleApplyAllSafe}
                className="text-[10px] px-2 py-0.5 bg-[#166534] text-[#86EFAC] rounded hover:bg-[#14532D]">
                Apply All Safe ({suggestions.items.filter(s => s.safe_to_auto_apply && isActionableSuggestion(s)).length})
              </button>
              <button onClick={handleApplySelected}
                className="text-[10px] px-2 py-0.5 bg-[#1E3A8A] text-[#93C5FD] rounded hover:bg-[#2563EB]">
                Apply Selected ({suggestions.checkedSet.size})
              </button>
              <button onClick={() => setSuggestions(null)} className="text-[#64748B] text-xs hover:text-white">✕</button>
            </div>
          </div>
          {suggestions.items.map((s, i) => {
            const hasFixProps = s.fix_props && Object.keys(s.fix_props).length > 0
            const hasRemoveProps = s.remove_props && Array.isArray(s.remove_props) && s.remove_props.length > 0
            const hasStructuralPayload = !!(s.child_node || s.new_node || s.merge_data)
            const actionable = hasFixProps || hasRemoveProps || hasStructuralPayload
            return (
            <div key={i} className={`flex items-start gap-2 rounded px-2 py-1.5 mb-1 ${!actionable ? 'opacity-60' : suggestions.checkedSet.has(i) ? 'bg-[#1E293B]' : 'bg-[#0F172A]'}`}>
              <input type="checkbox" checked={suggestions.checkedSet.has(i)} disabled={!actionable}
                onChange={() => toggleCheck(i)}
                className="mt-0.5 accent-[#60A5FA] shrink-0 disabled:cursor-not-allowed" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 flex-wrap">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${!actionable ? 'bg-[#334155] text-[#94A3B8]' : s.safe_to_auto_apply ? 'bg-[#14532D] text-[#86EFAC]' : 'bg-[#451A03] text-[#FED7AA]'}`}>
                    {!actionable ? 'info only' : s.safe_to_auto_apply ? 'safe' : 'review'}
                  </span>
                  <span className="text-[10px] px-1 py-0.5 rounded bg-[#1E293B] text-[#60A5FA] font-mono">{s.op || 'set_props'}</span>
                  {s.confidence !== undefined && (
                    <span className="text-[10px] text-[#64748B]">
                      {typeof s.confidence === 'number' ? `${Math.round(s.confidence * 100)}%` : String(s.confidence)}
                    </span>
                  )}
                  <span className="text-[10px] text-[#94A3B8] font-mono truncate">{s.path || ''}</span>
                </div>
                {(s.suggestion_label || s.message) && (
                  <p className="text-[10px] text-[#E2E8F0] mt-0.5">{s.suggestion_label || s.message}</p>
                )}
                {hasFixProps && (
                  <p className="text-[10px] text-[#CBD5E1] mt-0.5 font-mono truncate">
                    {JSON.stringify(s.fix_props).slice(0, 60)}{JSON.stringify(s.fix_props).length > 60 ? '…' : ''}
                  </p>
                )}
                {hasRemoveProps && (
                  <p className="text-[10px] text-[#F87171] mt-0.5">remove: {s.remove_props.join(', ')}</p>
                )}
                {hasStructuralPayload && (
                  <p className="text-[10px] text-[#93C5FD] mt-0.5">{s.op}: structural change ready</p>
                )}
                {!actionable && (
                  <p className="text-[10px] text-[#64748B] mt-0.5 italic">No auto-fix available — needs manual edit.</p>
                )}
              </div>
            </div>
          )})}
        </div>
      )}

      {/* Action bar */}
      {actionBar && !suggestions && (
        <div className="bg-[#1E3A8A] px-3 py-2 flex items-center gap-2 shrink-0">
          <span className="text-[#93C5FD] text-xs flex-1 truncate">{actionBar.label}</span>
          <button onClick={handleActionBarBtn} className="text-xs px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded font-semibold hover:bg-white">
            {actionBar.btn}
          </button>
          <button onClick={() => setActionBar(null)} className="text-[#94A3B8] text-xs hover:text-white">✕</button>
        </div>
      )}
      {/* Suggestions action bar */}
      {actionBar && suggestions && (
        <div className="bg-[#1E293B] border-t border-[#334155] px-3 py-1.5 flex items-center gap-2 shrink-0">
          <span className="text-[#A78BFA] text-xs flex-1">{actionBar.label}</span>
          <button onClick={() => { setActionBar(null); setSuggestions(null) }} className="text-[#64748B] text-xs hover:text-white">Dismiss</button>
        </div>
      )}

      <div className="h-px bg-[#334155] shrink-0" />

      {/* Attachments chips */}
      {attachments.length > 0 && (
        <div className="bg-[#1E293B] px-2 pt-2 flex flex-wrap gap-1 shrink-0">
          {attachments.map((a, i) => (
            <div key={i} className="flex items-center gap-1 bg-[#0F172A] border border-[#334155] rounded px-2 py-0.5">
              {a.preview && <img src={a.preview} alt="" className="w-6 h-6 rounded object-cover" />}
              <span className="text-[#94A3B8] text-[10px] truncate max-w-24">{a.name}</span>
              <button onClick={() => setAttachments(aa => aa.filter((_, j) => j !== i))} className="text-[#F87171] text-[10px] hover:text-white ml-0.5">✕</button>
            </div>
          ))}
          {uploading && <span className="text-[#60A5FA] text-[10px] self-center animate-pulse">Uploading…</span>}
        </div>
      )}

      {/* Input */}
      <div className="bg-[#1E293B] p-2 shrink-0 flex gap-2">
        <input type="file" ref={fileInputRef} accept="image/*,.json,.txt,.csv" className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f); e.target.value = '' }} />
        <textarea
          ref={inputRef}
          rows={3}
          className="flex-1 bg-[#0F172A] text-[#E2E8F0] text-sm p-2 rounded resize-none outline-none leading-relaxed placeholder-[#475569]"
          placeholder={mode === 'agent' ? 'Describe a fragment… (📋 to paste clipboard)' : 'Ask Glean anything… (📋 to paste clipboard)'}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          onPaste={handlePaste}
        />
        <div className="flex flex-col gap-1 self-end">
          <button onClick={() => fileInputRef.current?.click()} title="Attach file / image"
            className="px-2 py-1 bg-[#334155] text-[#94A3B8] rounded text-sm hover:bg-[#475569]">📎</button>
          <button onClick={handleClipboardPaste} title="Paste from clipboard (text or image)"
            className="px-2 py-1 bg-[#334155] text-[#94A3B8] rounded text-sm hover:bg-[#475569]">📋</button>
          {streaming ? (
            <button onClick={stop} className="px-3 py-1 bg-[#7F1D1D] text-[#FCA5A5] rounded text-sm font-bold">■</button>
          ) : (
            <button onClick={send} className="px-3 py-1 bg-[#4C1D95] text-white rounded text-sm font-bold hover:bg-[#5B21B6]">➤</button>
          )}
        </div>
      </div>
    </div>
  )
}

function Bubble({ role, text }) {
  if (role === 'user') {
    return (
      <div>
        <p className="text-[#60A5FA] text-xs font-semibold mb-1">You</p>
        <p className="text-[#CBD5E1] text-sm whitespace-pre-wrap leading-relaxed">{text}</p>
      </div>
    )
  }
  if (role === 'error') {
    return <p className="text-[#F87171] text-sm">⚠ {text}</p>
  }
  return (
    <div>
      <p className="text-[#A78BFA] text-xs font-semibold mb-1">✨ Glean AI</p>
      <p className="text-[#E2E8F0] text-sm whitespace-pre-wrap leading-relaxed">{text}</p>
    </div>
  )
}
