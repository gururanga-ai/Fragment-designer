import { useState } from 'react'
import GleanChat from '../shared/GleanChat'
import Modal from '../shared/Modal'
import { gleanChat, gleanRunWorkflow } from '../../utils/gleanApi'
import { extractJson } from '../../utils/agentBuilder'

const LIFECYCLE_OPTS = ['GENERAL_AVAILABILITY', 'BETA', 'ALPHA', 'DEPRECATED']

function Field({ label, children, hint }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <label className="text-sm font-medium text-[#111827] w-44 shrink-0 pt-1.5">{label}</label>
      <div className="flex-1">
        {children}
        {hint && <p className="text-xs text-[#94A3B8] mt-0.5">{hint}</p>}
      </div>
    </div>
  )
}

function TextInput({ value, onChange, placeholder }) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full border border-[#CBD5E1] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-[#2563EB] bg-white"
    />
  )
}

function Toggle({ value, onChange, label }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={!!value}
        onChange={e => onChange(e.target.checked)}
        className="w-4 h-4 rounded accent-[#1E3A8A]"
      />
      <span className="text-sm text-[#374151]">{label}</span>
    </label>
  )
}

export default function ConfigStep({
  config, onConfigChange,
  gleanHistory, onGleanHistoryChange,
  gleanChatId, onGleanChatIdChange,
  flows, onFlowsChange,
  contents, onContentsChange,
  onHandoffToDesigner,
  onSyncFragmentSilently,
}) {
  const [chatOpen, setChatOpen] = useState(false)
  const [autofillOpen, setAutofillOpen] = useState(false)
  const [autofillStatus, setAutofillStatus] = useState('')

  const set = (key, val) => onConfigChange(prev => ({ ...prev, [key]: val }))

  const setFolder = (i, val) => {
    const f = [...(config.folders || [])]
    f[i] = val
    set('folders', f)
  }
  const addFolder = () => set('folders', [...(config.folders || []), ''])
  const removeFolder = i => set('folders', (config.folders || []).filter((_, j) => j !== i))

  const setDefault = (oldKey, newKey, val) => {
    const d = { ...(config.defaults || {}) }
    if (oldKey !== newKey) { delete d[oldKey] }
    d[newKey] = val
    set('defaults', d)
  }
  const addDefault = () => {
    const d = { ...(config.defaults || {}), '': '' }
    set('defaults', d)
  }
  const removeDefault = key => {
    const d = { ...(config.defaults || {}) }
    delete d[key]
    set('defaults', d)
  }

  const applyGleanConfig = data => {
    const updates = {}
    if (data._content_handoff) {
      const h = data._content_handoff
      const item = {
        Name: h.fileName || 'content',
        AgentContentType: h.contentType || 'script',
        language: h.language || '',
        Content: (h.payload || {}).content || '',
        description: (h.payload || {}).description || '',
      }
      onContentsChange(prev => [...prev, item])
      alert(`Added '${item.Name}' to Contents.`)
      return
    }
    if (data.agentId) updates.agentId = String(data.agentId)
    if (data.agentName) updates.agentName = String(data.agentName)
    if (data.description) updates.description = String(data.description)
    if (data.category) updates.category = Array.isArray(data.category) ? data.category.join(', ') : String(data.category)
    if (data.agentRootResourceFolders) updates.folders = data.agentRootResourceFolders
    if (data.defaults) updates.defaults = Object.fromEntries(Object.entries(data.defaults).map(([k, v]) => [k, String(v)]))

    // Optional fields the prompt only includes when the user explicitly asked for that specific
    // behavior (e.g. "make it conversational") — must check !== undefined, not truthiness, since
    // these are booleans and "false" is a real, intentional value (e.g. "not discoverable").
    for (const key of [
      'discoverable', 'dataAgent', 'conversational', 'voiceEnabled', 'allowAttachment',
      'resourceControlled', 'autoGrantSubAgents', 'autoEnablement', 'includeSubAgentIntents',
      'allowSubagentTransition',
    ]) {
      if (data[key] !== undefined) updates[key] = !!data[key]
    }
    if (data.lifecycleStage) updates.lifecycleStage = String(data.lifecycleStage)
    if (data.imageUrl) updates.imageUrl = String(data.imageUrl)
    if (data.resourceId) updates.resourceId = String(data.resourceId)
    if (data.agentSequence !== undefined) updates.agentSequence = String(data.agentSequence)

    onConfigChange(prev => ({ ...prev, ...updates }))
  }

  const handleGleanActionBar = async ({ type, data }) => {
    if (type === 'config') applyGleanConfig(data)
    if (type === 'content') applyGleanConfig({ _content_handoff: data })
    if (type === 'actions') {
      onFlowsChange(prev => {
        const f = { ...prev }
        if (!f.default) f.default = { default: [] }
        const isRedo = data[0]?._redo === true
        const raw = isRedo ? data.slice(1) : data
        const cleaned = raw.map(({ AfterActionField, Beforeactionfield, _redo, _modify, ...a }) => ({
          ...a, input: a.input || {}, output: a.output || {},
        }))
        // Always replace — prevents duplication when re-generating from config panel
        f.default.default = cleaned
        return f
      })
      alert(`${data[0]?._redo ? 'Replaced' : 'Loaded'} ${data.filter(a => !a._redo).length} action(s) into default flow. Switch to Build Flow to reorder.`)
    }
    if (type === 'fragment_handoff') {
      const userPrompt = data.payload?.user_prompt || ''
      if (onHandoffToDesigner && userPrompt) {
        onHandoffToDesigner({ _fragmentPrompt: userPrompt, _fragmentJson: data.payload?.fragment_json || {}, _issues: data.payload?.issues || [] })
      } else {
        window.open(data.targetAgentUrl || 'https://app.glean.com/chat/agents/2491a8dae7254256975430b2c635a26b', '_blank')
      }
    }
  }

  const runFullAutofill = async (desc, deepResearch, setStatus, onDone) => {
    // New autofill = new Glean context
    onGleanChatIdChange(null)
    onGleanHistoryChange([])

    let configApplied = 0, flowApplied = 0
    const errors = []

    // Call 1: configure agent (triggers CONFIG MODE)
    setStatus('⏳ Step 1/3: Generating configuration...')
    try {
      const configPrompt = `Autofill this agent — configure agent properties for: ${desc}`
      let configText = ''
      await gleanChat({ conversation: [{ role: 'user', text: configPrompt }], useDeepResearch: deepResearch, onPartial: t => { configText = t } })
      const configData = extractJson(configText)
      if (configData && !Array.isArray(configData)) {
        applyGleanConfig(configData)
        configApplied = Object.keys(configData).length
        onGleanHistoryChange(prev => [...prev,
          { role: 'user', text: configPrompt },
          { role: 'ai', text: configText },
        ])
      } else { errors.push('Config: no JSON object found in response') }
    } catch (e) { errors.push(`Config: ${e.message}`) }

    // Call 2: build flow (triggers FLOW MODE)
    setStatus('⏳ Step 2/3: Generating flow actions...')
    let flowData = null
    try {
      const flowPrompt = `Build flow — generate actions for the default task: ${desc}`
      let flowText = ''
      await gleanChat({ conversation: [{ role: 'user', text: flowPrompt }], useDeepResearch: deepResearch, onPartial: t => { flowText = t } })
      flowData = extractJson(flowText)
      if (Array.isArray(flowData) && flowData.length > 0) {
        onFlowsChange(prev => {
          const f = { ...prev }
          if (!f.default) f.default = { default: [] }
          const cleaned = flowData.map(({ AfterActionField, Beforeactionfield, _redo, _modify, ...a }) => ({
            ...a, input: a.input || {}, output: a.output || {},
          }))
          f.default.default = cleaned
          return f
        })
        flowApplied = flowData.length
        onGleanHistoryChange(prev => [...prev,
          { role: 'user', text: flowPrompt },
          { role: 'ai', text: flowText },
        ])
      } else { errors.push('Flow: no JSON array found in response') }
    } catch (e) { errors.push(`Flow: ${e.message}`) }

    // Call 3: actually generate the fragment UI (not just a placeholder) + link renderUI + make
    // it visible in Fragment Designer without forcing a tab switch away from this review screen.
    const hasRenderUI = Array.isArray(flowData) && flowData.some(a => a.type === 'renderUI')
    // Broad on purpose: "display/show X" often gets flow-generated as a chat data response
    // (addDataResponse) rather than a renderUI action, since that's a valid conversational-agent
    // answer too — but a user asking to "display"/"show" something usually wants an actual
    // rendered UI, not just raw data in the chat reply, so treat these as a fragment request too.
    const wantsFragment = /fragment|render\s*ui|dashboard|ui\s*layout|display|shows?\b|showing|screen|table|grid|chart|report|card/i.test(desc)
    if (hasRenderUI || wantsFragment) {
      const rawId = (config.agentId || '').replace(/^ext-/, '') || (config.agentName || '').replace(/\s+/g, '') || 'agent'
      const contentName = rawId.charAt(0).toUpperCase() + rawId.slice(1) + 'Fragment'
      let layoutIntent = desc
      let generatedFragment = null

      setStatus('⏳ Step 3/3: Designing fragment layout...')
      try {
        // First pass: turn the (possibly vague) description into a concrete, specific layout
        // intent — container types, data bindings, filters, columns — GENERATION MODE below
        // relies on this level of detail to produce a real fragment rather than a stub.
        const fragPrompt = `Create fragment UI — suggest a fragment layout for this agent: ${desc}`
        let fragText = ''
        await gleanChat({ conversation: [{ role: 'user', text: fragPrompt }], useDeepResearch: deepResearch, onPartial: t => { fragText = t } })
        const fragData = extractJson(fragText)
        if (fragData?.mode === 'fragment_handoff' && fragData.payload?.user_prompt) {
          layoutIntent = fragData.payload.user_prompt
        }

        // Second pass: actually generate the fragment JSON (ALIGN_FIX_SYSTEM GENERATION MODE —
        // triggered by an empty fragment_json), instead of leaving a Content:'{}' stub that only
        // got filled in if the user separately clicked "Edit in Designer" and waited for Glean.
        // Generation is observed to occasionally return non-fragment output (suggestions/prose)
        // for the exact same prompt — one retry meaningfully improves the odds of a real result.
        for (let attempt = 1; attempt <= 2 && !generatedFragment; attempt++) {
          setStatus(`⏳ Step 3/3: Generating fragment JSON${attempt > 1 ? ' (retry)' : ''}...`)
          let genText = ''
          await gleanRunWorkflow({
            prompt: layoutIntent,
            fragment_json: {},
            issues: [],
            conversation: [],
            useDeepResearch: deepResearch,
            onPartial: t => { genText = t },
          })
          const generated = extractJson(genText)
          if (generated?.Fragment) generatedFragment = generated
        }
      } catch (e) {
        errors.push(`Fragment: ${e.message}`)
      }

      const newContent = {
        Name: contentName,
        AgentContentType: 'fragment',
        language: '',
        Content: generatedFragment ? JSON.stringify(generatedFragment, null, 2) : '{}',
        description: layoutIntent,
      }
      if (!generatedFragment) errors.push('Fragment: generation returned no usable layout — open "Edit in Designer" on the renderUI card to generate manually')

      // Add/replace fragment content item (dedupe by name — a rerun shouldn't leave two copies)
      onContentsChange(prev => {
        const idx = prev.findIndex(c => (c.Name || c.name) === contentName)
        if (idx === -1) return [...prev, newContent]
        const next = [...prev]; next[idx] = newContent; return next
      })

      // Link renderUI action → content name + embed _fragment_json for Edit in Designer.
      // If the flow step didn't produce a renderUI action at all (e.g. it chose a chat-style
      // addDataResponse instead), append one so the fragment is actually wired into the flow —
      // a fragment with nothing rendering it would just sit unused in the Contents library.
      {
        onFlowsChange(prev => {
          const f = JSON.parse(JSON.stringify(prev))
          if (!f.default?.default) return prev
          const already = f.default.default.some(a => a.type === 'renderUI' && !a.inputJSON)
          f.default.default = f.default.default.map(a =>
            (a.type === 'renderUI' && !a.inputJSON)
              ? { ...a, inputJSON: contentName, _fragment_json: newContent }
              : a
          )
          if (!hasRenderUI && !already) {
            f.default.default.push({
              type: 'renderUI',
              name: 'showResults',
              description: 'Render the generated fragment UI.',
              inputJSON: contentName,
              input: {},
              output: {},
              _fragment_json: newContent,
            })
          }
          return f
        })
      }

      // Load it into Fragment Designer in the background (no tab switch) so it's already there
      // whenever the user clicks over — matches "Edit in Designer" showing the exact same content.
      if (generatedFragment) onSyncFragmentSilently?.(newContent)
    }

    const parts = []
    if (configApplied > 0) parts.push(`${configApplied} config field(s)`)
    if (flowApplied > 0) parts.push(`${flowApplied} flow action(s)`)
    if (errors.length) parts.push(...errors.map(e => `⚠ ${e}`))
    setStatus(`✓ Done — ${parts.join(' · ') || 'No data applied'}`)
    setTimeout(onDone, 2000)
  }

  const handleQuickFill = async (key) => {
    const name = config.agentName?.trim()
    const desc = config.description?.trim()
    const cat = config.category?.trim()
    const ctx = name ? `For a MAWM data agent named '${name}'${cat ? ` in category '${cat}'` : ''}${desc ? ` — ${desc}` : ''}: ` : ''

    const prompts = {
      config: ctx + 'autofill this agent — configure agent properties.',
      flow: ctx + 'build flow — generate actions for the default task.',
      root_folders: ctx + 'suggest agentRootResourceFolders paths.',
      defaults: ctx + 'suggest default config values (DefaultMetric, DefaultGroupBy1, DefaultGroupBy2, LinkIdsSize, sql.limit).',
      fragment: ctx + 'create fragment UI — suggest a fragment layout for this agent\'s main dashboard view.',
    }

    setChatOpen(true)
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('glean-prefill', { detail: prompts[key] }))
    }, 100)
  }

  return (
    <div className="flex h-full">
      {/* Form */}
      <div className="flex-1 min-w-0 overflow-y-auto px-6 py-4">
        {/* General */}
        <Section title="General">
          <Field label="Agent ID *"><TextInput value={config.agentId} onChange={v => set('agentId', v)} placeholder="ext-myAgent" /></Field>
          <Field label="Agent Name *"><TextInput value={config.agentName} onChange={v => set('agentName', v)} /></Field>
          <Field label="Description">
            <textarea
              rows={3}
              value={config.description}
              onChange={e => set('description', e.target.value)}
              className="w-full border border-[#CBD5E1] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-[#2563EB] bg-white resize-none"
            />
          </Field>
          <Field label="Image URL"><TextInput value={config.imageUrl} onChange={v => set('imageUrl', v)} /></Field>
          <Field label="Category (comma-sep)"><TextInput value={config.category} onChange={v => set('category', v)} placeholder="ActiveWarehouse" /></Field>
        </Section>

        {/* Lifecycle */}
        <Section title="Lifecycle & Discovery">
          <Field label="Lifecycle Stage *">
            <select
              value={config.lifecycleStage}
              onChange={e => set('lifecycleStage', e.target.value)}
              className="border border-[#CBD5E1] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-[#2563EB] bg-white"
            >
              {LIFECYCLE_OPTS.map(o => <option key={o}>{o}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-2 py-2">
            {[
              ['discoverable', 'Discoverable'],
              ['dataAgent', 'Data Agent'],
              ['conversational', 'Conversational'],
              ['voiceEnabled', 'Voice Enabled'],
              ['allowAttachment', 'Allow Attachment'],
              ['resourceControlled', 'Resource Controlled'],
              ['autoGrantSubAgents', 'Auto Grant Sub-Agents'],
              ['autoEnablement', 'Auto Enablement'],
              ['includeSubAgentIntents', 'Include Sub-Agent Intents'],
              ['allowSubagentTransition', 'Allow Sub-Agent Transition'],
            ].map(([k, lbl]) => (
              <Toggle key={k} value={config[k]} onChange={v => set(k, v)} label={lbl} />
            ))}
          </div>
        </Section>

        {/* Resource */}
        <Section title="Resource">
          <Field label="Resource ID"><TextInput value={config.resourceId} onChange={v => set('resourceId', v)} /></Field>
          <Field label="Agent Sequence"><TextInput value={config.agentSequence} onChange={v => set('agentSequence', v)} /></Field>
        </Section>

        {/* Folders */}
        <Section title="Root Resource Folders">
          <p className="text-xs text-[#94A3B8] mb-2">e.g. /agents/dataInsights/ext-myAgent</p>
          {(config.folders || []).map((f, i) => (
            <div key={i} className="flex gap-2 mb-1">
              <input
                type="text"
                value={f}
                onChange={e => setFolder(i, e.target.value)}
                className="flex-1 border border-[#CBD5E1] rounded px-2 py-1 text-sm focus:outline-none focus:border-[#2563EB]"
              />
              <button onClick={() => removeFolder(i)} className="px-2 text-red-600 hover:bg-[#FEE2E2] rounded text-sm">×</button>
            </div>
          ))}
          <button onClick={addFolder} className="text-xs px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded mt-1 hover:bg-[#BFDBFE]">+ Add Folder</button>
        </Section>

        {/* Defaults */}
        <Section title="Default Config Values">
          {Object.entries(config.defaults || {}).map(([k, v]) => (
            <div key={k} className="flex gap-2 mb-1 items-center">
              <input
                type="text"
                value={k}
                onChange={e => setDefault(k, e.target.value, v)}
                placeholder="key"
                className="w-40 border border-[#CBD5E1] rounded px-2 py-1 text-sm focus:outline-none focus:border-[#2563EB]"
              />
              <input
                type="text"
                value={v}
                onChange={e => setDefault(k, k, e.target.value)}
                placeholder="value"
                className="flex-1 border border-[#CBD5E1] rounded px-2 py-1 text-sm focus:outline-none focus:border-[#2563EB]"
              />
              <button onClick={() => removeDefault(k)} className="px-2 text-red-600 hover:bg-[#FEE2E2] rounded text-sm">×</button>
            </div>
          ))}
          <button onClick={addDefault} className="text-xs px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded mt-1 hover:bg-[#BFDBFE]">+ Add Default</button>
        </Section>
      </div>

      {/* Glean sidebar */}
      <div className={`w-72 shrink-0 border-l border-[#CBD5E1] flex flex-col bg-[#F1F5F9] transition-all ${chatOpen ? '' : ''}`}>
        <div className="p-4 border-b border-[#CBD5E1]">
          <p className="text-sm font-semibold text-[#1E3A8A] mb-1">Glean Assistant</p>
          <p className="text-xs text-[#64748B]">Describe the agent and Glean will fill the form and generate flow actions.</p>
        </div>
        <div className="p-3 border-b border-[#CBD5E1] space-y-2">
          <button
            onClick={() => setAutofillOpen(true)}
            className="w-full text-xs px-3 py-2 bg-[#166534] text-[#86EFAC] rounded font-semibold hover:bg-[#15803D] text-left"
          >
            ⚡ Full Autofill (Config + Flow)
          </button>
          {autofillStatus && (
            <p className="text-xs text-[#86EFAC] bg-[#14532D] rounded px-2 py-1 mt-1">{autofillStatus}</p>
          )}
          <button
            onClick={() => setChatOpen(o => !o)}
            className="w-full text-xs px-3 py-2 bg-[#4C1D95] text-white rounded font-semibold hover:bg-[#5B21B6] text-left"
          >
            {chatOpen ? 'Close' : 'Open'} Glean Chat
          </button>
        </div>
        <div className="p-3 space-y-1">
          <p className="text-xs text-[#94A3B8] mb-1">Quick fills:</p>
          {[
            ['Config autofill', 'config', '#DBEAFE', '#1E3A8A'],
            ['Generate actions', 'flow', '#DBEAFE', '#1E3A8A'],
            ['Root folders?', 'root_folders', '#DBEAFE', '#1E3A8A'],
            ['Suggest defaults?', 'defaults', '#DBEAFE', '#1E3A8A'],
            ['Fragment UI handoff', 'fragment', '#F3E8FF', '#6B21A8'],
          ].map(([lbl, key, bg, fg]) => (
            <button
              key={key}
              onClick={() => handleQuickFill(key)}
              className="w-full text-xs px-3 py-1.5 rounded hover:opacity-80 text-left font-medium"
              style={{ backgroundColor: bg, color: fg }}
            >
              {lbl}
            </button>
          ))}
        </div>

        {chatOpen && (
          <GleanChat
            mode="config"
            chatId={gleanChatId}
            onChatIdChange={onGleanChatIdChange}
            history={gleanHistory}
            onHistoryChange={onGleanHistoryChange}
            onActionBar={handleGleanActionBar}
            title="Agent Configuration"
            className="flex-1 min-h-0"
          />
        )}
      </div>
      {autofillOpen && (
        <FullAutofillModal
          onClose={() => { setAutofillOpen(false); setAutofillStatus('') }}
          onRun={(desc, deepResearch, setStatus, onDone) => runFullAutofill(desc, deepResearch, setStatus, onDone)}
        />
      )}
    </div>
  )
}

// Meta-prompt for "Enhance" — asks Glean to research company knowledge (Confluence/Bitbucket/
// entity schemas — enableCompanyTools/enableWebSearch are already on for this chat route) and
// turn a rough one-liner into the kind of grounded, specific description the autofill steps
// actually need (real field/entity names instead of invented ones, concrete layout, etc.).
function buildEnhancePrompt(desc) {
  return `Research company knowledge (Confluence, Bitbucket, entity/data schemas, similar existing agents) relevant to building this agent, then rewrite the request below as a detailed, implementation-ready agent description.

Cover, grounded in what you actually find (never invent names you can't confirm):
- Overall purpose and business context
- The exact business entities, fields, and SQL/table columns involved
- UI layout pattern (sidebar, tabs, table, chart, KPI cards, filters)
- Filter fields needed and their data types
- Any business logic, calculations, or aggregations involved
- Data sources / services to pull from

Be specific and concrete — this description is fed directly into config generation, flow action generation, and fragment UI generation, so vague or generic statements are not useful. If you cannot confirm something with high confidence, say what's uncertain rather than inventing it.

Return ONLY the rewritten description as plain text. No JSON, no markdown headers, no preamble like "Here is..." — just the description itself, ready to paste back into an autofill box.

Original request: ${desc}`
}

function FullAutofillModal({ onClose, onRun }) {
  const [desc, setDesc] = useState('')
  const [status, setStatus] = useState('')
  const [running, setRunning] = useState(false)
  const [deepResearch, setDeepResearch] = useState(false)
  const [enhancing, setEnhancing] = useState(false)
  const [enhanced, setEnhanced] = useState(false)

  const handleRun = () => {
    if (!desc.trim() || running) return
    setRunning(true)
    onRun(desc.trim(), deepResearch, setStatus, () => { setRunning(false); onClose() })
  }

  const handleEnhance = async () => {
    if (!desc.trim() || enhancing || running) return
    setEnhancing(true)
    setEnhanced(false)
    const original = desc.trim()
    try {
      let text = ''
      let fellBack = false
      await gleanChat({
        conversation: [{ role: 'user', text: buildEnhancePrompt(original) }],
        mode: 'enhance',
        useDeepResearch: deepResearch,
        onPartial: t => { text = t; setDesc(t) },
        onFallback: () => { fellBack = true },
      })
      setDesc(text.trim() || original)
      setEnhanced(true)
      if (fellBack) setStatus('⚠ Extension relay dropped mid-request (long research call) — finished via shared fallback session instead of your own login.')
    } catch (e) {
      setStatus(`⚠ Enhance failed: ${e.message}`)
      setDesc(original)
    } finally {
      setEnhancing(false)
    }
  }

  return (
    <Modal title="⚡ Full Autofill — Config + Flow" onClose={onClose} width="max-w-lg">
      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm text-[#374151] flex-1">
            Describe the agent in plain English. Glean will automatically fill the configuration form and generate flow actions — no manual steps required.
          </p>
          <button
            onClick={() => setDeepResearch(d => !d)}
            title={deepResearch ? 'Thinking mode — slower, more thorough' : 'Fast mode — quick response'}
            className={`shrink-0 text-[10px] px-2 py-1 rounded-full font-medium border transition-colors ${
              deepResearch ? 'bg-[#4C1D95] text-white border-[#4C1D95]' : 'bg-white text-[#64748B] border-[#CBD5E1] hover:border-[#94A3B8]'
            }`}
          >
            {deepResearch ? '🧠 Thinking' : '⚡ Fast'}
          </button>
        </div>
        <div className="relative">
          <textarea
            rows={7}
            autoFocus
            value={desc}
            onChange={e => { setDesc(e.target.value); setEnhanced(false) }}
            onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleRun() }}
            placeholder="e.g. A fulfillment progress agent that shows open orders grouped by carrier, with SQL from the warehouse DB, filters for date range and facility, and a rendered table UI with pagination"
            disabled={enhancing}
            className="w-full border border-[#CBD5E1] rounded p-3 text-sm resize-none focus:outline-none focus:border-[#2563EB] disabled:bg-[#F8FAFC] disabled:text-[#64748B]"
          />
          {enhanced && !enhancing && (
            <span className="absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-[#F3E8FF] text-[#6B21A8] font-semibold">
              ✨ Enhanced
            </span>
          )}
        </div>
        <button
          onClick={handleEnhance}
          disabled={!desc.trim() || enhancing || running}
          className="w-full text-xs px-3 py-2 bg-[#F3E8FF] text-[#6B21A8] rounded font-semibold hover:bg-[#E9D5FF] disabled:opacity-50 disabled:cursor-not-allowed border border-[#D8B4FE]"
        >
          {enhancing ? '🔎 Researching Confluence, Bitbucket, entity knowledge…' : '✨ Enhance Prompt (research company knowledge)'}
        </button>
        {status && (
          <div className={`rounded px-3 py-2 text-xs font-medium ${status.startsWith('✓') ? 'bg-[#DCFCE7] text-[#166534]' : status.startsWith('⚠') || status.includes('Error') ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#DBEAFE] text-[#1E3A8A]'}`}>
            {status}
          </div>
        )}
        <div className="flex gap-2 items-center">
          <button
            onClick={handleRun}
            disabled={running || enhancing || !desc.trim()}
            className="px-4 py-2 bg-[#166534] text-[#86EFAC] rounded text-sm font-semibold hover:bg-[#15803D] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? '⏳ Running...' : '⚡ Run Autofill'}
          </button>
          <button onClick={onClose} disabled={running} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0]">
            {running ? 'Please wait...' : 'Cancel'}
          </button>
          <span className="text-xs text-[#94A3B8] ml-auto">Ctrl+Enter to run</span>
        </div>
      </div>
    </Modal>
  )
}

function Section({ title, children }) {
  return (
    <div className="mb-4">
      <div className="bg-[#F1F5F9] text-[#1E3A8A] font-semibold text-sm px-4 py-2 rounded mb-2">{title}</div>
      <div className="px-2">{children}</div>
    </div>
  )
}
