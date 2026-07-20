import { useState, useEffect, useRef, useCallback } from 'react'
import GleanChat from '../shared/GleanChat'
import Modal from '../shared/Modal'
import { gleanChat, gleanRunWorkflow, gleanUploadFile } from '../../utils/gleanApi'
import { extractJson } from '../../utils/agentBuilder'
import { cleanJson, restoreTemplateVars } from '../fragment-designer/FragmentDesigner'
import { safeReadClipboardItems, safeReadClipboardText } from '../../utils/clipboard'

const LIFECYCLE_OPTS = ['GENERAL_AVAILABILITY', 'BETA', 'ALPHA', 'DEPRECATED']

// Layout archetypes offered in Full Autofill's layout-picker step — patterns confirmed against
// real reference fragments (References/*.json: MHE Dashboard, ticket/fulfillment agents, etc.).
// "blueprint" is fed directly into fragment GENERATION MODE as a concrete container/slot spec so
// the model has an actual structural target instead of inferring layout from prose alone.
const LAYOUT_OPTIONS = [
  {
    id: 'table-filters',
    icon: '📋',
    label: 'Table + Filters',
    desc: 'Sidebar filter panel + single data table. Best for a simple record list/search.',
    blueprint: 'Follow SIDEBAR + FILTER + TABLE LAYOUT — REQUIRED SHAPE in the system prompt: header-action with a Filters toggle button, sidebar with flyout-card+filter-panel in Left and a single table in Default. Fill in real columns matching the flow\'s transformTable output field names and a real Filters Init round-trip.',
  },
  {
    id: 'kpi-charts-table',
    icon: '📊',
    label: 'KPI + Charts + Table',
    desc: 'KPI tiles row, one or two charts, and a detail table below — the standard analytics dashboard.',
    blueprint: 'This has charts/KPIs, so follow CHART/KPI LAYOUTS — DESIGN FREELY in the system prompt: design the composition yourself (a filter sidebar if useful, a KPI tiles row, one or two charts, a detail table — in whatever arrangement best fits the data), but the functional contracts listed there (real chart Init/highchartsOptions/seriesMappings, real KPI tile pattern, filter-panel Init contract, table ShowFilter/Columns) are mandatory regardless of composition.',
  },
  {
    id: 'tabbed-dashboard',
    icon: '🗂️',
    label: 'Tabbed Dashboard',
    desc: 'Multiple views in tabs, each with its own charts/KPIs/table — for agents covering several related breakdowns.',
    blueprint: 'This has tabs/charts/KPIs, so follow CHART/KPI LAYOUTS — DESIGN FREELY in the system prompt: design a tab-group keyed by the agent\'s real distinct breakdowns, each tab holding its own KPI/chart/table combination — composition is yours to decide, but the functional contracts listed there (chart/KPI/table/filter-panel correctness) are mandatory regardless.',
  },
  {
    id: 'card-grid',
    icon: '🗃️',
    label: 'Card / List Grid',
    desc: 'Repeating card list bound to a dataset — for browsing many similar records without a strict table grid.',
    blueprint: 'A grid container of repeating card nodes bound to a listOfMap dataset (one card per row), each card showing a few key-value fields for that record. If a filter sidebar is needed, follow SIDEBAR + FILTER + TABLE LAYOUT for the header-action/sidebar structure, with the card grid in place of the table in the sidebar\'s Default slot. Optional small KPI/chart summary row above the grid (follow CHART/KPI LAYOUTS\' functional contracts for that part).',
  },
  {
    id: 'master-detail',
    icon: '🔍',
    label: 'Master-Detail / Flyout',
    desc: 'Table with row-click opening a detail flyout panel — for ticket/record drill-down.',
    blueprint: 'Follow SIDEBAR + FILTER + TABLE LAYOUT — REQUIRED SHAPE in the system prompt, including the sidebar\'s Right slot stack host (required here, unlike the default "omit if unused" guidance). The table\'s columns include an action-button "Insights" column (Events.Triggers.OnClick -> {EventId:"push-details-flyout", ContainerId:"details-button"}) wired to that stack host\'s Push/Pop listeners.',
  },
  {
    id: 'none',
    icon: '💬',
    label: 'No Fragment (Conversational)',
    desc: 'No UI — the agent answers in chat only. Skips fragment generation entirely.',
    blueprint: null,
  },
]

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

  // The agent won't load on the real platform without both /agents/dataInsights/<agentId> and
  // /ext/agents/<agentId> present in agentRootResourceFolders — confirmed against a real working
  // agent export. Relying on Glean to remember to include both (via the Root Folders quick-fill
  // or Full Autofill) is unreliable, so guarantee them here whenever agentId changes: add whatever
  // canonical paths are missing, drop stale ones left over from a previous agentId, and leave any
  // other custom folder entries the user added alone.
  useEffect(() => {
    const id = (config.agentId || '').trim()
    if (!id) return
    const canonical = [`/agents/dataInsights/${id}`, `/ext/agents/${id}`]
    onConfigChange(prev => {
      const current = prev.folders || []
      const stale = current.filter(f => /^\/agents\/dataInsights\/|^\/ext\/agents\//.test(f) && !canonical.includes(f))
      const missing = canonical.filter(c => !current.includes(c))
      if (stale.length === 0 && missing.length === 0) return prev
      return { ...prev, folders: [...current.filter(f => !stale.includes(f)), ...missing] }
    })
  }, [config.agentId, onConfigChange])

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
        AgentContentType: h.contentType || 'scripts',
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

  const runFullAutofill = async (desc, deepResearch, layoutChoice, setStatus, onDone, uploadedFileIds = [], skipResearch = false) => {
    // New autofill = new Glean context
    onGleanChatIdChange(null)
    onGleanHistoryChange([])

    const noFragment = layoutChoice?.id === 'none'

    let configApplied = 0, flowApplied = 0
    let latestAgentId = config.agentId
    let latestAgentName = config.agentName
    let latestConversational = config.conversational
    const errors = []

    // Step 0: research once, in its own isolated call, instead of leaving every one of the 3
    // generation calls below to independently re-research the same links/entities in `desc`
    // (e.g. a Confluence page) — that tripling of slow lookup work was what pushed config/flow/
    // fragment each past the extension relay's hard lifetime cap. One grounded rewrite here means
    // the downstream calls are pure "generate JSON from an already-detailed spec" — fast.
    // If the user already gave everything needed (or attached it), skipResearch bypasses this
    // call entirely — company-knowledge search is consistently the slowest single Glean
    // operation and the one most likely to outlive the relay's hard lifetime cap regardless of
    // retries, so when it isn't actually needed the fastest fix is to just not make the call.
    let groundedDesc = desc
    if (skipResearch) {
      setStatus('⏳ Step 1/4: Skipped (using description as provided)...')
    } else {
      setStatus('⏳ Step 1/4: Researching company knowledge...')
      try {
        let researchText = ''
        await gleanChat({
          conversation: [{ role: 'user', text: buildEnhancePrompt(desc) }],
          mode: 'enhance',
          useDeepResearch: deepResearch,
          uploadedFileIds,
          onPartial: t => { researchText = t },
        })
        if (researchText.trim()) groundedDesc = researchText.trim()
      } catch (e) {
        errors.push(`Research: ${e.message} — continuing with the description as typed, ungrounded`)
      }
    }

    // Call 1: configure agent (triggers CONFIG MODE)
    setStatus('⏳ Step 2/4: Generating configuration...')
    try {
      const configPrompt = `Autofill this agent — configure agent properties for: ${groundedDesc}`
        + (noFragment ? ' This must be a conversational, chat-only agent with no dashboard/UI — set conversational: true.' : '')
      let configText = ''
      await gleanChat({ conversation: [{ role: 'user', text: configPrompt }], useDeepResearch: deepResearch, onPartial: t => { configText = t } })
      const configData = extractJson(configText)
      if (configData && !Array.isArray(configData)) {
        applyGleanConfig(configData)
        // applyGleanConfig schedules the config state update async — the outer `config` closure
        // still holds the value from before this call. Step 3 needs the REAL new agentId (not a
        // stale/empty one) to derive a sensible fragment content name, so capture it directly from
        // Glean's own CONFIG MODE response rather than reading the stale `config` prop.
        latestAgentId = configData.agentId || config.agentId
        latestAgentName = configData.agentName || config.agentName
        if (configData.conversational !== undefined) latestConversational = !!configData.conversational
        configApplied = Object.keys(configData).length
        onGleanHistoryChange(prev => [...prev,
          { role: 'user', text: configPrompt },
          { role: 'ai', text: configText },
        ])
      } else { errors.push('Config: no JSON object found in response') }
    } catch (e) { errors.push(`Config: ${e.message}`) }

    // Call 2: build flow (triggers FLOW MODE)
    setStatus('⏳ Step 3/4: Generating flow actions...')
    let flowData = null
    try {
      const conversationalNote = (noFragment || latestConversational)
        ? ' This is a conversational, chat-only agent — do NOT include a renderUI action; end the flow with addDataResponse/addTextResponse/addStreamResponse instead.'
        : ''
      // Tie flow generation to the chosen layout — the transformTable/renderUI dataMap shape
      // needs to actually match what that layout will bind to (KPI scalars, chart series fields,
      // table columns), not be guessed independently of the fragment that will render it.
      const layoutNote = (!noFragment && layoutChoice?.blueprint)
        ? ` The generated UI will use this layout: ${layoutChoice.blueprint} Shape transformTable outputs and the renderUI dataMap to match exactly what this layout needs (KPI tiles need row-0 scalar extraction, charts need named series fields, tables need column-matching field names).`
        : ''
      const flowPrompt = `Build flow — generate actions for the default task: ${groundedDesc}${conversationalNote}${layoutNote}`
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
    // Whether this step runs at all is now decided by the user's explicit layout-picker choice
    // (including "No Fragment") rather than a fuzzy soft/hard-UI-word regex guess over the prompt.
    const hasRenderUI = Array.isArray(flowData) && flowData.some(a => a.type === 'renderUI')
    if (!noFragment && (hasRenderUI || layoutChoice)) {
      // If the flow step's renderUI action already names an inputJSON, that name IS the contract —
      // it must be used as-is, or the flow references a content item that doesn't exist. Inventing
      // a different name here (as this used to do) produces a mismatch: renderUI.inputJSON points
      // at one name, agentContentsCustom has the fragment under a completely different one.
      const existingRenderUI = Array.isArray(flowData) ? flowData.find(a => a.type === 'renderUI' && a.inputJSON) : null
      const rawId = (latestAgentId || '').replace(/^ext-/, '') || (latestAgentName || '').replace(/\s+/g, '') || 'agent'
      const derivedName = rawId.charAt(0).toUpperCase() + rawId.slice(1) + 'Fragment'
      const contentName = existingRenderUI?.inputJSON || derivedName

      // Step 2 (flow/SQL) and this step are two independent Glean calls with no shared knowledge
      // of field names — without this, each guesses its own, so a table's DataSourcePath rarely
      // matches what renderUI's dataMap actually calls it, and filter-panel Input keys rarely
      // match the {:Filters.X} references the flow's SQL/WHERE/conditions already use, so Apply
      // renders a UI that looks right but never actually filters anything. Ground both explicitly
      // in what the flow we JUST generated actually produces.
      const renderUIAction = Array.isArray(flowData) ? flowData.find(a => a.type === 'renderUI') : null
      const varPool = (renderUIAction?.dataMap && typeof renderUIAction.dataMap === 'object') ? renderUIAction.dataMap : {}
      const filterKeyMatches = Array.isArray(flowData)
        ? [...new Set([...JSON.stringify(flowData).matchAll(/\{:Filters\.([A-Za-z0-9_]+)/g)].map(m => m[1]))]
        : []
      const dataBindingNote = Object.keys(varPool).length > 0
        ? ` The flow's renderUI action produces exactly these dataMap keys — bind every table/chart/segment-panel Init.DataSourcePath to one of these real keys (matching by meaning), never invent a different DataSourcePath name: ${Object.keys(varPool).join(', ')}.`
        : ''
      const filterKeyNote = filterKeyMatches.length > 0
        ? ` The flow's SQL/WHERE/conditions already read filters via these exact keys: ${filterKeyMatches.join(', ')} (i.e. {:Filters.<key>}). Every filter-panel Attribute's "Input" MUST be exactly one of these names — using a different name means Apply changes the UI state but the flow never sees it, so filtering silently does nothing.`
        : ''
      // varPool only grounds the TOP-LEVEL dataMap key (e.g. "TableData") — it says nothing about
      // the actual ROW-LEVEL field names inside that dataset (e.g. BatchId, BatchStatus), which
      // live in the upstream transformTable/sql action, not in renderUI itself. Without this,
      // Init.DataSourcePath comes out correct but every table column Input/SortBy and chart
      // fieldMappings key is still an independent guess — exactly the failure mode that survived
      // the var_pool fix (right DataSourcePath, invented columns).
      const rowFieldsByDataKey = {}
      if (Array.isArray(flowData)) {
        for (const [dataKey, expr] of Object.entries(varPool)) {
          if (dataKey === 'Filters' || typeof expr !== 'string') continue
          const varMatch = expr.match(/object::([A-Za-z0-9_]+)/)
          if (!varMatch) continue
          const producer = flowData.find(a => a.outputVariableName === varMatch[1])
          if (!producer) continue
          let fields = []
          if (producer.type === 'transformTable') {
            const allFields = [...(producer.fields || []), ...(producer.conditionalFields || []).map(cf => cf.field).filter(Boolean)]
            fields = allFields.map(f => f.targetFieldName).filter(Boolean)
          } else if (producer.type === 'sql' && typeof producer.sql === 'string') {
            fields = [...producer.sql.matchAll(/\bAS\s+([A-Za-z0-9_]+)/gi)].map(m => m[1])
          }
          if (fields.length > 0) rowFieldsByDataKey[dataKey] = [...new Set(fields)]
        }
      }
      const rowFieldNote = Object.keys(rowFieldsByDataKey).length > 0
        ? ' ' + Object.entries(rowFieldsByDataKey).map(([k, fields]) =>
            `The dataset bound via DataSourcePath:"${k}" has EXACTLY these row fields, case-exact, and no others: ${fields.join(', ')}. Every table column Input/Sort.SortBy and chart dataMapping.seriesMappings.fieldMappings key bound to this dataset MUST be one of these names — inventing a column/field name outside this list renders empty with no error.`
          ).join(' ')
        : ''
      // The user already picked a concrete layout in the picker step — go straight to that
      // blueprint instead of making a separate "suggest a layout" round trip first.
      let layoutIntent = (layoutChoice?.blueprint
        ? `${groundedDesc}\n\nRequired layout pattern (user-selected: ${layoutChoice.label}): ${layoutChoice.blueprint}`
        : groundedDesc) + dataBindingNote + filterKeyNote + rowFieldNote
      let generatedFragment = null

      setStatus('⏳ Step 4/4: Generating fragment layout...')
      let lastGenText = ''
      try {
        // Actually generate the fragment JSON (ALIGN_FIX_SYSTEM GENERATION MODE —
        // triggered by an empty fragment_json), instead of leaving a Content:'{}' stub that only
        // got filled in if the user separately clicked "Edit in Designer" and waited for Glean.
        // Generation is observed to occasionally return non-fragment output (suggestions/prose)
        // for the exact same prompt — retrying meaningfully improves the odds of a real result.
        for (let attempt = 1; attempt <= 3 && !generatedFragment; attempt++) {
          setStatus(`⏳ Step 4/4: Generating fragment JSON${attempt > 1 ? ' (retry)' : ''}...`)
          let genText = ''
          await gleanRunWorkflow({
            prompt: layoutIntent,
            fragment_json: {},
            issues: [],
            var_pool: varPool,
            conversation: [],
            useDeepResearch: deepResearch,
            onPartial: t => { genText = t },
          })
          lastGenText = genText
          // Real fragment JSON legitimately contains bare, unquoted {:VarName} template tokens
          // as object values (e.g. "Filters": {:Filters}) — that's the platform's real syntax,
          // but it isn't valid standalone JSON, so a plain extractJson/JSON.parse silently fails
          // on virtually every generated fragment (any of them using the near-universal Filters
          // Init pattern). cleanJson (proven in FragmentDesigner.jsx for the same problem) wraps
          // those tokens in quotes first so JSON.parse can succeed.
          const generated = extractJson(genText) || extractJson(cleanJson(genText))
          if (generated?.Fragment) generatedFragment = generated
        }
      } catch (e) {
        errors.push(`Fragment: ${e.message}`)
      }

      const newContent = {
        Name: contentName,
        // Valid AgentContentType values are flows/genAIPrompts/inputs/scripts — no "fragment" type
        // exists on the platform. renderUI.inputJSON loads from the agent's inputs repository, so
        // fragment content is stored as 'inputs' like any other input JSON.
        AgentContentType: 'inputs',
        language: '',
        // restoreTemplateVars undoes cleanJson's quoting of {:VarName} tokens — the platform
        // needs the bare/unquoted form, quoting was only ever a parse-time accommodation.
        Content: generatedFragment ? restoreTemplateVars(JSON.stringify(generatedFragment, null, 2)) : '{}',
        description: layoutIntent,
      }
      if (!generatedFragment) {
        // Surface what Glean actually returned instead of swallowing it — a generic "no usable
        // layout" message gives no way to tell prose/explanation apart from truncated/malformed
        // JSON apart from a genuine backend error, which made every real failure indistinguishable
        // from every other one and impossible to root-cause from the UI alone.
        const preview = (lastGenText || '(empty response)').trim().slice(0, 300)
        errors.push(`Fragment: generation returned no usable layout. Raw response: ${preview}${lastGenText.length > 300 ? '…' : ''} — open "Edit in Designer" on the renderUI card to generate manually`)
      }

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
    onDone()
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
          onRun={(desc, deepResearch, layoutChoice, setStatus, onDone, uploadedFileIds, skipResearch) => runFullAutofill(desc, deepResearch, layoutChoice, setStatus, onDone, uploadedFileIds, skipResearch)}
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
  const [layoutPickerOpen, setLayoutPickerOpen] = useState(false)
  const [lastLayoutChoice, setLastLayoutChoice] = useState(null)
  const [hasRun, setHasRun] = useState(false)
  const [attachments, setAttachments] = useState([]) // { name, fileId, preview }
  const [uploading, setUploading] = useState(false)
  const [skipResearch, setSkipResearch] = useState(false)
  const fileInputRef = useRef(null)

  // "Run Autofill" no longer generates a fragment blind — it first asks the user to pick a
  // concrete layout (or "No Fragment"), and that choice drives both flow shaping and fragment
  // generation downstream instead of a fuzzy word-guess over the prompt text.
  const handleRun = () => {
    if (!desc.trim() || running) return
    setLayoutPickerOpen(true)
  }

  const fileIds = () => attachments.map(a => a.fileId).filter(Boolean)

  const handleLayoutChosen = (layoutChoice) => {
    setLayoutPickerOpen(false)
    setLastLayoutChoice(layoutChoice)
    setHasRun(true)
    setRunning(true)
    // Stays open on completion — the run can partially fail (e.g. flow ok, fragment 401)
    // and closing on a timer buried that. onDone here just stops the spinner; the user
    // reviews the status line and explicitly Confirms (closes) or Retries.
    onRun(desc.trim(), deepResearch, layoutChoice, setStatus, () => setRunning(false), fileIds(), skipResearch)
  }

  const handleRetry = () => {
    if (!lastLayoutChoice || running) return
    setRunning(true)
    onRun(desc.trim(), deepResearch, lastLayoutChoice, setStatus, () => setRunning(false), fileIds(), skipResearch)
  }

  const uploadFile = useCallback(async (file) => {
    const preview = file.type.startsWith('image/') ? await new Promise(res => {
      const r = new FileReader(); r.onload = e => res(e.target.result); r.readAsDataURL(file)
    }) : null
    setUploading(true)
    try {
      const { fileId, filename } = await gleanUploadFile(file)
      setAttachments(a => [...a, { name: filename || file.name, fileId, preview }])
    } catch (err) {
      setStatus(`⚠ Attach failed: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }, [])

  const handleDescPaste = useCallback(async (e) => {
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

  const handleClipboardAttach = useCallback(async () => {
    const items = await safeReadClipboardItems()
    if (items) {
      for (const item of items) {
        const imgType = item.types.find(t => t.startsWith('image/'))
        if (imgType) {
          const blob = await item.getType(imgType)
          await uploadFile(new File([blob], 'pasted-image.png', { type: imgType }))
          return
        }
        if (item.types.includes('text/plain')) {
          const blob = await item.getType('text/plain')
          const text = await blob.text()
          if (text.trim()) setDesc(prev => prev ? `${prev}\n${text}` : text)
          return
        }
      }
      return
    }
    const text = await safeReadClipboardText()
    if (text && text.trim()) setDesc(prev => prev ? `${prev}\n${text}` : text)
  }, [uploadFile])

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
        uploadedFileIds: fileIds(),
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
            {' '}Paste the actual details (field names, layout, entities) rather than just a link — having Glean fetch a page live routinely runs long enough to break the browser relay.
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
        <label className="flex items-center gap-1.5 text-xs text-[#374151] -mt-1">
          <input type="checkbox" checked={skipResearch} onChange={e => setSkipResearch(e.target.checked)} className="accent-[#1E3A8A]" />
          Skip company knowledge search — I've already given all the details needed below
        </label>
        <div className="relative">
          <textarea
            rows={7}
            autoFocus
            value={desc}
            onChange={e => { setDesc(e.target.value); setEnhanced(false) }}
            onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleRun() }}
            onPaste={handleDescPaste}
            placeholder="e.g. A fulfillment progress agent that shows open orders grouped by carrier, with SQL from the warehouse DB, filters for date range and facility, and a rendered table UI with pagination"
            disabled={enhancing}
            className="w-full border border-[#CBD5E1] rounded p-3 text-sm resize-none focus:outline-none focus:border-[#2563EB] disabled:bg-[#F8FAFC] disabled:text-[#64748B]"
          />
          {/https?:\/\//.test(desc) && (
            <span className="absolute bottom-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] font-semibold">
              ⚠ link detected — paste the page's content instead for a reliable run
            </span>
          )}
          {enhanced && !enhancing && (
            <span className="absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-[#F3E8FF] text-[#6B21A8] font-semibold">
              ✨ Enhanced
            </span>
          )}
        </div>
        <input type="file" ref={fileInputRef} accept="image/*,.json,.txt,.csv,.pdf,.docx" className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f); e.target.value = '' }} />
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {attachments.map((a, i) => (
              <div key={i} className="flex items-center gap-1 bg-[#F1F5F9] border border-[#CBD5E1] rounded px-2 py-0.5">
                {a.preview && <img src={a.preview} alt="" className="w-5 h-5 rounded object-cover" />}
                <span className="text-[#374151] text-[10px] truncate max-w-32">{a.name}</span>
                <button onClick={() => setAttachments(aa => aa.filter((_, j) => j !== i))} className="text-red-500 text-[10px] hover:text-red-700 ml-0.5">✕</button>
              </div>
            ))}
            {uploading && <span className="text-[#2563EB] text-[10px] self-center animate-pulse">Uploading…</span>}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleEnhance}
            disabled={!desc.trim() || enhancing || running}
            className="flex-1 text-xs px-3 py-2 bg-[#F3E8FF] text-[#6B21A8] rounded font-semibold hover:bg-[#E9D5FF] disabled:opacity-50 disabled:cursor-not-allowed border border-[#D8B4FE]"
          >
            {enhancing ? '🔎 Researching Confluence, Bitbucket, Jira, Salesforce…' : '✨ Enhance Prompt (research company knowledge)'}
          </button>
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading || running} title="Attach file (doc/image/json/csv)"
            className="px-3 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0] disabled:opacity-50 disabled:cursor-not-allowed">
            📎
          </button>
          <button onClick={handleClipboardAttach} disabled={uploading || running} title="Paste from clipboard (text or image)"
            className="px-3 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0] disabled:opacity-50 disabled:cursor-not-allowed">
            📋
          </button>
        </div>
        {status && (
          <div className={`rounded px-3 py-2 text-xs font-medium ${status.startsWith('✓') ? 'bg-[#DCFCE7] text-[#166534]' : status.startsWith('⚠') || status.includes('Error') ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#DBEAFE] text-[#1E3A8A]'}`}>
            {status}
          </div>
        )}
        <div className="flex gap-2 items-center">
          {hasRun ? (
            <>
              <button
                onClick={handleRetry}
                disabled={running || enhancing}
                className="px-4 py-2 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold hover:bg-[#BFDBFE] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {running ? '⏳ Retrying...' : '🔁 Retry'}
              </button>
              <button
                onClick={onClose}
                disabled={running}
                className="px-4 py-2 bg-[#166534] text-[#86EFAC] rounded text-sm font-semibold hover:bg-[#15803D] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ✓ Confirm & Close
              </button>
            </>
          ) : (
            <>
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
            </>
          )}
          <span className="text-xs text-[#94A3B8] ml-auto">Ctrl+Enter to run</span>
        </div>
      </div>
      {layoutPickerOpen && (
        <LayoutPickerModal
          onClose={() => setLayoutPickerOpen(false)}
          onChoose={handleLayoutChosen}
        />
      )}
    </Modal>
  )
}

function LayoutPickerModal({ onClose, onChoose }) {
  return (
    <Modal title="Choose a UI Layout" onClose={onClose} width="max-w-2xl">
      <div className="p-4">
        <p className="text-sm text-[#374151] mb-3">
          Pick the layout that best matches what this agent should show. Glean will design the flow and fragment to match it.
        </p>
        <div className="grid grid-cols-2 gap-2">
          {LAYOUT_OPTIONS.filter(o => o.id !== 'none').map(o => (
            <button
              key={o.id}
              onClick={() => onChoose(o)}
              className="text-left border border-[#CBD5E1] rounded-lg p-3 hover:border-[#2563EB] hover:bg-[#EFF6FF] transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">{o.icon}</span>
                <span className="text-sm font-semibold text-[#111827]">{o.label}</span>
              </div>
              <p className="text-xs text-[#64748B]">{o.desc}</p>
            </button>
          ))}
        </div>
        <button
          onClick={() => onChoose(LAYOUT_OPTIONS.find(o => o.id === 'none'))}
          className="w-full text-left border border-dashed border-[#94A3B8] rounded-lg p-3 mt-2 hover:border-[#475569] hover:bg-[#F1F5F9] transition-colors"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">💬</span>
            <span className="text-sm font-semibold text-[#111827]">No Fragment (Conversational)</span>
          </div>
          <p className="text-xs text-[#64748B]">No UI — the agent answers in chat only. Skips fragment generation entirely.</p>
        </button>
        <button onClick={onClose} className="mt-3 px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0]">
          Cancel
        </button>
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
