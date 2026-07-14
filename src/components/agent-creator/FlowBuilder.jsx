import { useState, useRef, useMemo, useEffect } from 'react'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors, DragOverlay,
} from '@dnd-kit/core'
import {
  SortableContext, horizontalListSortingStrategy, arrayMove, useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import GleanChat from '../shared/GleanChat'
import JsonEditor from '../shared/JsonEditor'
import Modal from '../shared/Modal'
import { safeReadClipboardText } from '../../utils/clipboard'

// ── Action info ──────────────────────────────────────────────────────
const ACTION_INFO = {
  setValue:        { icon: 'V',   color: '#7C3AED', label: 'Set Value' },
  stringBuilder:   { icon: 'S',   color: '#6B21A8', label: 'String Builder' },
  sql:             { icon: 'SQL', color: '#0369A1', label: 'SQL Query' },
  callService:     { icon: 'CS',  color: '#0C4A6E', label: 'Call Service' },
  transformTable:  { icon: 'T',   color: '#065F46', label: 'Transform Table' },
  editTable:       { icon: 'E',   color: '#047857', label: 'Edit Table' },
  joinTables:      { icon: 'J',   color: '#1D4ED8', label: 'Join Tables' },
  addTags:         { icon: '#',   color: '#991B1B', label: 'Add Tags' },
  callAgent:       { icon: '>A',  color: '#1D4ED8', label: 'Call Agent' },
  storeTaskResult: { icon: 'ST',  color: '#374151', label: 'Store Task Result' },
  storeResponse:   { icon: 'SR',  color: '#374151', label: 'Store Response' },
  profileLookup:   { icon: 'PL',  color: '#047857', label: 'Profile Lookup' },
  userExit:        { icon: 'UX',  color: '#92400E', label: 'User Exit' },
  processDateTime: { icon: 'DT',  color: '#1E3A8A', label: 'Process DateTime' },
  runJavaScript:   { icon: 'JS',  color: '#B45309', label: 'Run JavaScript' },
  addStreamResponse: { icon: 'AS', color: '#0F766E', label: 'Add Stream Response' },
  addDataResponse: { icon: 'DR',  color: '#166534', label: 'Add Data Response' },
  modifyUI:        { icon: 'MU',  color: '#6D28D9', label: 'Modify UI' },
  renderUI:        { icon: 'UI',  color: '#B45309', label: 'Render UI' },
  createUIFragment:{ icon: 'CF',  color: '#B45309', label: 'Create UI Fragment' },
  callFlow:        { icon: '>F',  color: '#0369A1', label: 'Call Flow' },
  addMessage:      { icon: 'M',   color: '#374151', label: 'Add Message' },
  extractEntities: { icon: 'EE',  color: '#374151', label: 'Extract Entities' },
}
const ALL_ACTION_TYPES = Object.keys(ACTION_INFO).sort()

function makeDefaultAction(type) {
  const base = { type, name: type, input: {}, output: {}, description: ACTION_INFO[type]?.label || type }
  if (type === 'setValue') return { ...base, functionName: 'assignValue', outputVariableName: '', value: '' }
  if (type === 'sql') return { ...base, sql: 'SELECT ...', outputVariableName: 'result' }
  if (type === 'renderUI') return { ...base, inputJSON: 'myFragment', bundleNames: [], dataMap: {}, outputVariableName: 'renderUIData', singleTurn: true, unsupportedOnUI: true }
  if (type === 'createUIFragment') return { ...base, metadata: { type: 'table', columns: [] }, inputVariableName: 'data', outputVariableName: 'fragment' }
  return base
}

// ── Sortable action card ─────────────────────────────────────────────
function ActionCard({ id, action, index, selected, highlighted, onSelect, onDoubleClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: action._id })
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }
  const info = ACTION_INFO[action.type] || { icon: '?', color: '#374151', label: action.type }
  const isDisabled = action._disabled
  const hasFrag = (action.type === 'renderUI' && !!action._fragment_json) || (action.type === 'createUIFragment' && !!action.metadata)
  const name = (action.name || action.type || '').slice(0, 18)

  return (
    <div
      id={id}
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onSelect(index)}
      onDoubleClick={() => onDoubleClick(index)}
      className={`relative shrink-0 w-48 h-24 rounded-lg cursor-pointer select-none transition-shadow
        ${selected ? 'ring-2 ring-[#3B82F6] shadow-lg' : highlighted ? 'ring-2 ring-yellow-400 shadow-md' : 'shadow hover:shadow-md'}
        ${isDisabled ? 'opacity-60 border-2 border-dashed border-red-400 bg-gray-50' : 'bg-white border border-[#E2E8F0]'}
      `}
    >
      {/* Color strip */}
      <div
        className="rounded-t-lg px-3 py-1 flex items-center gap-2"
        style={{ backgroundColor: isDisabled ? '#94A3B8' : info.color }}
      >
        <span className="text-white text-xs font-bold font-mono">{info.icon}</span>
        <span className="text-white text-xs font-semibold truncate">{name}</span>
        <span className="ml-auto text-white/60 text-xs">{index + 1}</span>
      </div>
      {/* Body */}
      <div className="px-3 pt-1">
        <p className="text-xs font-semibold" style={{ color: isDisabled ? '#94A3B8' : info.color }}>{info.label}</p>
        <p className="text-xs text-[#374151] truncate mt-0.5">{action.description || action.name || ''}</p>
        {isDisabled && <p className="text-xs text-red-500 mt-1 font-semibold">⊘ disconnected</p>}
        {(action.type === 'renderUI' || action.type === 'createUIFragment') && (
          <p className={`text-xs mt-1 font-semibold ${hasFrag ? 'text-green-600' : 'text-orange-500'}`}>
            {hasFrag ? 'Fragment linked/defined' : 'No fragment yet'}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Add action type picker ────────────────────────────────────────────
function ActionTypePicker({ onAdd, onClose, onCustom }) {
  const [search, setSearch] = useState('')
  const filtered = ALL_ACTION_TYPES.filter(t => t.includes(search.toLowerCase()))
  return (
    <Modal title="Choose Action Type" onClose={onClose} width="max-w-sm">
      <div className="p-4">
        <input
          autoFocus
          type="text"
          placeholder="Filter..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full border rounded px-3 py-1.5 text-sm mb-3 focus:outline-none focus:border-[#2563EB]"
        />
        <div className="max-h-72 overflow-y-auto space-y-1">
          {filtered.map(t => {
            const info = ACTION_INFO[t]
            return (
              <button
                key={t}
                onClick={() => { onAdd(t); onClose() }}
                className="w-full text-left px-3 py-2 rounded hover:bg-[#F1F5F9] text-sm flex items-center gap-2"
              >
                <span className="font-mono text-xs font-bold rounded px-1.5 py-0.5 text-white" style={{ backgroundColor: info.color }}>{info.icon}</span>
                <span className="font-medium">{t}</span>
                <span className="text-[#64748B] text-xs ml-auto">{info.label}</span>
              </button>
            )
          })}
          <button
            onClick={() => { onCustom(); onClose() }}
            className="w-full text-left px-3 py-2 rounded hover:bg-[#FEF3C7] text-sm flex items-center gap-2 border-t border-[#E2E8F0] mt-1 pt-2"
          >
            <span className="font-mono text-xs font-bold rounded px-1.5 py-0.5 bg-[#374151] text-white">{'{}'}</span>
            <span className="font-medium text-[#92400E]">── Custom (paste JSON) ──</span>
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── JSON paste modal ─────────────────────────────────────────────────
// ── Edit single action JSON modal ─────────────────────────────────────
function EditActionModal({ action, onSave, onClose }) {
  // strip internal _id / _fragment_json from editing surface
  const { _id, _fragment_json, ...editable } = action
  const [text, setText] = useState(() => JSON.stringify(editable, null, 2))
  const [error, setError] = useState('')

  const handleSave = () => {
    try {
      const parsed = JSON.parse(text)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setError('Must be a single action object {}')
        return
      }
      onSave(parsed)
      onClose()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleFormat = () => {
    try { setText(JSON.stringify(JSON.parse(text), null, 2)); setError('') }
    catch (e) { setError(e.message) }
  }

  return (
    <Modal title={`Edit Action — ${action.name || action.type || '?'}`} onClose={onClose} width="max-w-2xl">
      <div className="p-4 space-y-3">
        <textarea
          autoFocus
          rows={20}
          value={text}
          onChange={e => { setText(e.target.value); setError('') }}
          className="w-full font-mono text-sm bg-[#1E293B] text-[#E2E8F0] p-3 rounded resize-none"
          spellCheck={false}
        />
        {error && <p className="text-red-500 text-xs">⚠ {error}</p>}
        <div className="flex gap-2">
          <button onClick={handleSave} className="px-4 py-2 bg-[#1E3A8A] text-white rounded text-sm font-semibold hover:bg-[#1E40AF]">Save Action</button>
          <button onClick={handleFormat} className="px-4 py-2 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold hover:bg-[#BFDBFE]">Format JSON</button>
          <button onClick={onClose} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

function PasteJsonModal({ onInsert, onClose }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const handleInsert = () => {
    try {
      let data = JSON.parse(text)
      if (data && typeof data === 'object' && data.actions) data = data.actions
      if (!Array.isArray(data)) data = [data]
      onInsert(data.filter(d => d && typeof d === 'object'))
      onClose()
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <Modal title="Paste Action JSON Array" onClose={onClose}>
      <div className="p-4 space-y-3">
        <textarea
          autoFocus
          rows={12}
          value={text}
          onChange={e => { setText(e.target.value); setError('') }}
          className="w-full font-mono text-sm bg-[#1E293B] text-[#E2E8F0] p-3 rounded resize-none"
          placeholder='[{"type":"setValue","name":"..."}]'
        />
        {error && <p className="text-red-500 text-xs">⚠ {error}</p>}
        <div className="flex gap-2">
          <button onClick={handleInsert} className="px-4 py-2 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold hover:bg-[#BFDBFE]">Insert Actions</button>
          <button onClick={onClose} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Fragment paste modal ──────────────────────────────────────────────
function FragmentModal({ action, onSave, onClose }) {
  const [text, setText] = useState(() => {
    const ex = action?._fragment_json
    return ex ? JSON.stringify(ex, null, 2) : ''
  })
  const [error, setError] = useState('')
  const name = action?.inputJSON || action?.name || 'fragment'

  const handleSave = () => {
    if (!text.trim()) { onSave(null); onClose(); return }
    try {
      const parsed = JSON.parse(text)
      let frag = parsed
      if (!parsed.Content && !parsed.AgentContentType) {
        const inner = parsed.Fragment ? parsed : { Fragment: parsed }
        frag = { Content: JSON.stringify(inner, null, 2), AgentContentType: 'inputs', Name: name }
      }
      onSave(frag)
      onClose()
    } catch (e) {
      setError(e.message)
    }
  }
  const fmt = () => {
    try { setText(JSON.stringify(JSON.parse(text), null, 2)); setError('') }
    catch (e) { setError(e.message) }
  }

  return (
    <Modal title={`Design Fragment — ${name}`} onClose={onClose} width="max-w-3xl">
      <div className="p-4 space-y-3">
        <div className="bg-[#F1F5F9] rounded p-3 text-sm text-[#374151]">
          Open Fragment Designer, design your layout, Export → Copy Fragment JSON and paste below. Will be bundled as agentContentsCustom with name <strong>'{name}'</strong>.
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Fragment JSON:</span>
          <button
            onClick={() => safeReadClipboardText().then(t => {
              if (t == null) { alert('Clipboard access unavailable — paste manually into the box below (Cmd/Ctrl+V).'); return }
              setText(t)
            })}
            className="text-xs px-2 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded"
          >
            Paste from Clipboard
          </button>
        </div>
        <textarea
          rows={16}
          value={text}
          onChange={e => { setText(e.target.value); setError('') }}
          className="w-full font-mono text-sm bg-[#1E293B] text-[#E2E8F0] p-3 rounded resize-none"
        />
        {error && <p className="text-red-500 text-xs">⚠ {error}</p>}
        <div className="flex gap-2">
          <button onClick={handleSave} className="px-4 py-2 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold">Save Fragment</button>
          <button onClick={fmt} className="px-4 py-2 bg-[#FEF3C7] text-[#92400E] rounded text-sm">Format JSON</button>
          <button onClick={() => setText('')} className="px-4 py-2 bg-[#FEE2E2] text-[#991B1B] rounded text-sm">Clear</button>
          <button onClick={onClose} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Convert createUIFragment metadata to visual Fragment ─────────────────────
function buildFragmentFromMetadata(action) {
  const meta = action.metadata || {}
  const type = meta.type || 'table'
  const dsPath = action.inputVariableName || 'data'

  // Build the core component (Table or Metrics)
  const comp = {
    Container: type === 'metrics' ? 'metrics' : 'table',
    Config: {
      dataSourcePath: dsPath,
      backendVar: dsPath, // Generic assumption for preview
    },
    Slots: { Default: [] }
  }

  if (type === 'table') {
    comp.Config.Columns = (meta.columns || []).map(c => ({
      UID: `Col_${c.value || c.labelKey}`,
      Config: { LabelKey: c.labelKey, Sort: { Sortable: c.sortable !== false, SortBy: c.value } },
      Slots: { Default: [{ Element: 'key-value', Input: c.value }] }
    }))
    if (meta.paginate) {
      comp.Slots.Default.push({ Container: 'footer-container', Slots: { Footer: [{ Container: 'footer' }] } })
    }
  } else if (type === 'metrics') {
    comp.Config.metricsSpec = (meta.metrics?.values || []).map(m => ({
      label: m.labelKey, field: m.value, unit: ''
    }))
  }

  // Wrap in a layout and attach filters if they exist
  const root = {
    Fragment: {
      Container: 'flex',
      Style: { css: { flexDirection: 'column', gap: '16px' } },
      Slots: { Default: [] }
    }
  }

  if (meta.filters && meta.filters.length > 0) {
    // Generate a basic FilterPanel JSON structure matching our internal format
    const fp = {
      Element: 'filter-panel',
      Config: { layout: 'horizontal' },
      Slots: {
        Filters: meta.filters.map(f => {
          if (f.type === 'Singleselect' || f.type === 'Multiselect') {
            const arr = f.values || []
            const mapStr = JSON.stringify(arr.map(v => ({ k: v.labelKey, v: v.value })))
            return { Element: 'dropdown', Input: f.fieldName, Config: { LabelKey: f.labelKey, StaticList: mapStr } }
          }
          return { Element: 'input', Input: f.fieldName, Config: { LabelKey: f.labelKey } }
        })
      }
    }
    root.Fragment.Slots.Default.push(fp)
  }

  root.Fragment.Slots.Default.push(comp)
  return root
}

// ── Main FlowBuilder ──────────────────────────────────────────────────
export default function FlowBuilder({
  flows, onFlowsChange,
  gleanHistory, onGleanHistoryChange,
  gleanChatId, onGleanChatIdChange,
  contents, onContentsChange,
  onHandoffToDesigner,
}) {
  const [flowId, setFlowId] = useState('default')
  const [taskId, setTaskId] = useState('default')

  // Reset Glean chat session when switching flow/task so context is re-injected fresh
  const prevFlowKeyRef = useRef('default::default')
  useEffect(() => {
    const key = `${flowId}::${taskId}`
    if (prevFlowKeyRef.current !== key) {
      prevFlowKeyRef.current = key
      onGleanChatIdChange?.(null)
      onGleanHistoryChange?.([])
    }
  }, [flowId, taskId, onGleanChatIdChange, onGleanHistoryChange])
  const [selIdx, setSelIdx] = useState(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [modal, setModal] = useState(null) // 'picker' | 'paste' | 'edit' | 'fragment'
  const [search, setSearch] = useState('')
  const [searchHitIdx, setSearchHitIdx] = useState(0)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  const flowKeys = Object.keys(flows)
  const taskKeys = Object.keys(flows[flowId] || {})
  const actions = (flows[flowId]?.[taskId] || []).map((a, i) => ({ ...a, _id: a._id || `${i}-${a.type}` }))

  // Hits across every task of every flow — {flowId, taskId, idx} in flow/task/action order.
  // Lets search hop between tasks instead of only matching within the currently open one.
  const globalHits = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return []
    const hits = []
    for (const [fId, tasks] of Object.entries(flows)) {
      for (const [tId, acts] of Object.entries(tasks)) {
        ;(acts || []).forEach((a, i) => {
          if (JSON.stringify(a).toLowerCase().includes(term)) hits.push({ flowId: fId, taskId: tId, idx: i })
        })
      }
    }
    return hits
  }, [search, flows])

  // Hits within the currently visible task only — used for the yellow-ring card highlight.
  const searchHits = useMemo(
    () => globalHits.filter(h => h.flowId === flowId && h.taskId === taskId).map(h => h.idx),
    [globalHits, flowId, taskId]
  )

  const [pendingScroll, setPendingScroll] = useState(null)
  useEffect(() => {
    if (pendingScroll === null) return
    requestAnimationFrame(() => {
      document.getElementById(`flow-card-${pendingScroll}`)?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
    })
    setPendingScroll(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowId, taskId, pendingScroll])

  const jumpToHit = hit => {
    if (hit.flowId !== flowId) setFlowId(hit.flowId)
    if (hit.taskId !== taskId) setTaskId(hit.taskId)
    setSelIdx(hit.idx)
    setPendingScroll(hit.idx)
  }

  // Auto-jump to first hit (anywhere) when search term changes
  useEffect(() => {
    if (!search.trim()) return
    setSearchHitIdx(0)
    if (globalHits.length > 0) jumpToHit(globalHits[0])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const searchNav = dir => {
    if (!globalHits.length) return
    const next = ((searchHitIdx + dir) + globalHits.length) % globalHits.length
    setSearchHitIdx(next)
    jumpToHit(globalHits[next])
  }

  const clearSearch = () => { setSearch(''); setSearchHitIdx(0) }

  const setActions = newActions => {
    onFlowsChange(prev => ({
      ...prev,
      [flowId]: { ...(prev[flowId] || {}), [taskId]: newActions },
    }))
  }

  const addFlow = () => {
    const name = prompt('Flow ID:')
    if (!name?.trim()) return
    onFlowsChange(prev => ({ ...prev, [name.trim()]: { default: [] } }))
    setFlowId(name.trim()); setTaskId('default')
  }

  const addTask = () => {
    const name = prompt('Task ID:')
    if (!name?.trim()) return
    onFlowsChange(prev => ({
      ...prev,
      [flowId]: { ...(prev[flowId] || {}), [name.trim()]: [] },
    }))
    setTaskId(name.trim())
  }

  const delFlow = () => {
    if (flowKeys.length <= 1) { alert('Must keep at least one flow.'); return }
    if (!confirm(`Delete flow '${flowId}'?`)) return
    onFlowsChange(prev => { const f = { ...prev }; delete f[flowId]; return f })
    setFlowId(flowKeys.find(k => k !== flowId))
    setSelIdx(null)
  }

  const delTask = () => {
    if (taskKeys.length <= 1) { alert('Must keep at least one task per flow.'); return }
    if (!confirm(`Delete task '${taskId}'?`)) return
    onFlowsChange(prev => {
      const f = { ...prev }; const t = { ...f[flowId] }; delete t[taskId]; f[flowId] = t; return f
    })
    setTaskId(taskKeys.find(k => k !== taskId))
    setSelIdx(null)
  }

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return
    const olds = actions.map(a => a._id)
    const oldIdx = olds.indexOf(active.id)
    const newIdx = olds.indexOf(over.id)
    const reordered = arrayMove(actions, oldIdx, newIdx).map(({ _id, ...rest }) => rest)
    setActions(reordered)
    setSelIdx(newIdx)
  }

  const addAction = type => {
    const a = makeDefaultAction(type)
    const newActions = [...actions.map(({ _id, ...r }) => r), a]
    setActions(newActions)
    setSelIdx(newActions.length - 1)
  }

  const deleteSelected = () => {
    if (selIdx === null) return
    if (!confirm(`Delete '${actions[selIdx]?.name || 'this action'}'?`)) return
    const newActions = actions.filter((_, i) => i !== selIdx).map(({ _id, ...r }) => r)
    setActions(newActions)
    setSelIdx(null)
  }

  const moveLeft = () => {
    if (selIdx === null || selIdx === 0) return
    const a = actions.map(({ _id, ...r }) => r)
    ;[a[selIdx - 1], a[selIdx]] = [a[selIdx], a[selIdx - 1]]
    setActions(a); setSelIdx(selIdx - 1)
  }

  const moveRight = () => {
    if (selIdx === null || selIdx >= actions.length - 1) return
    const a = actions.map(({ _id, ...r }) => r)
    ;[a[selIdx], a[selIdx + 1]] = [a[selIdx + 1], a[selIdx]]
    setActions(a); setSelIdx(selIdx + 1)
  }

  const moveTo = () => {
    if (selIdx === null) return
    const input = prompt(`Move to position (1–${actions.length}):`)
    if (!input) return
    const pos = parseInt(input, 10) - 1
    if (isNaN(pos) || pos < 0 || pos >= actions.length) { alert('Invalid position.'); return }
    const a = actions.map(({ _id, ...r }) => r)
    const [item] = a.splice(selIdx, 1)
    a.splice(pos, 0, item)
    setActions(a); setSelIdx(pos)
  }

  const toggleDisconnect = () => {
    if (selIdx === null) return
    const a = actions.map(({ _id, ...r }) => r)
    a[selIdx] = { ...a[selIdx], _disabled: !a[selIdx]._disabled }
    setActions(a)
  }

  const saveEditedAction = updated => {
    const a = actions.map(({ _id, ...r }, i) => {
      if (i !== selIdx) return r
      const internals = Object.fromEntries(Object.entries(r).filter(([k]) => k.startsWith('_')))
      return { ...updated, ...internals }
    })
    setActions(a)
  }

  const saveFragment = frag => {
    const a = actions.map(({ _id, ...r }, i) => {
      if (i !== selIdx) return r
      return frag ? { ...r, _fragment_json: frag } : (({ _fragment_json, ...rest }) => rest)(r)
    })
    setActions(a)
  }

  const insertActions = (data) => {
    if (!Array.isArray(data)) data = [data]

    const cleanIncoming = ({ AfterActionField, Beforeactionfield, _redo, _modify, _remove, _add, _action, _narrative, ...a }) => ({
      ...a, input: a.input || {}, output: a.output || {},
    })

    // ── Full redo: first element is {"_redo": true} ──
    // Apply as surgical diff to preserve original actions not mentioned by Glean
    if (data[0]?._redo === true) {
      const incoming = data.slice(1).map(cleanIncoming)
      // Only replace if flow is empty — otherwise apply as surgical diff
      const clean = actions.map(({ _id, ...r }) => r)
      if (clean.length === 0) {
        setActions(incoming)
        setSelIdx(incoming.length > 0 ? incoming.length - 1 : null)
        return
      }
      // Non-empty: merge by name — update existing, add new, keep unlisted
      let updated = [...clean]
      for (const inc of incoming) {
        const idx = updated.findIndex(a =>
          a.name === inc.name || (inc.name && a.name?.toLowerCase() === inc.name.toLowerCase())
        )
        if (idx !== -1) updated[idx] = inc
        else updated.push(inc)
      }
      setActions(updated)
      setSelIdx(updated.length > 0 ? updated.length - 1 : null)
      return
    }

    const clean = actions.map(({ _id, ...r }) => r)
    const hasSurgicalFlags = data.some(a => a._remove || a._modify || a._add || a._action)

    // ── If ANY surgical flags are present, process them action by action ──
    if (hasSurgicalFlags) {
      let updated = [...clean]
      let lastIdx = null

      // 1. Process Removals — case-insensitive name match
      data.filter(a => a._remove || ['remove', 'delete'].includes((a._action || '').toLowerCase())).forEach(incoming => {
        const nameLower = (incoming.name || '').toLowerCase()
        const idx = updated.findIndex(a =>
          a.name === incoming.name || (nameLower && a.name?.toLowerCase() === nameLower)
        )
        if (idx !== -1) updated.splice(idx, 1)
      })

      // 2. Process Modifications — match by name (case-insensitive fallback), skip if not found
      data.filter(a => a._modify || ['modify', 'update', 'change'].includes((a._action || '').toLowerCase())).forEach(incoming => {
        const cleaned = cleanIncoming(incoming)
        const nameLower = (incoming.name || '').toLowerCase()
        const idx = updated.findIndex(a =>
          a.name === incoming.name || (nameLower && a.name?.toLowerCase() === nameLower)
        )
        if (idx !== -1) {
          updated[idx] = cleaned
          lastIdx = idx
        }
        // no match → skip (don't duplicate)
      })

      // 3. Process Additions (only explicit _add / _action:"add" — no catch-all)
      data.filter(a => a._add || ['add', 'insert'].includes((a._action || '').toLowerCase())).forEach(incoming => {
        const cleaned = cleanIncoming(incoming)
        
        let insertIdx = updated.length
        if (incoming.AfterActionField) {
          const idx = updated.findIndex(a => a.name === incoming.AfterActionField || a.outputVariableName === incoming.AfterActionField)
          if (idx !== -1) insertIdx = idx + 1
        } else if (incoming.Beforeactionfield) {
          const idx = updated.findIndex(a => a.name === incoming.Beforeactionfield || a.outputVariableName === incoming.Beforeactionfield)
          if (idx !== -1) insertIdx = idx
        }
        
        updated.splice(insertIdx, 0, cleaned)
        lastIdx = insertIdx
      })

      setActions(updated)
      if (lastIdx !== null) setSelIdx(lastIdx)
      else setSelIdx(null)
      return
    }

    // ── No surgical flags: Positional insert OR full replace ──
    const incoming = data.map(cleanIncoming)
    const first = data[0] || {}

    if (first.AfterActionField || first.Beforeactionfield) {
      let insertIdx = clean.length
      if (first.AfterActionField) {
        const idx = clean.findIndex(a => a.name === first.AfterActionField || a.outputVariableName === first.AfterActionField)
        if (idx !== -1) insertIdx = idx + 1
      } else {
        const idx = clean.findIndex(a => a.name === first.Beforeactionfield || a.outputVariableName === first.Beforeactionfield)
        if (idx !== -1) insertIdx = idx
      }
      const newActions = [
        ...clean.slice(0, insertIdx),
        ...incoming,
        ...clean.slice(insertIdx),
      ]
      setActions(newActions)
      setSelIdx(insertIdx + incoming.length - 1)
    } else {
      // Smart merge: update-in-place by name if exists, append if new.
      // Full replace only via explicit {"_redo": true} sentinel.
      const merged = [...clean]
      let lastIdx = merged.length - 1
      for (const action of incoming) {
        const existingIdx = action.name
          ? merged.findIndex(a => a.name === action.name)
          : -1
        if (existingIdx !== -1) {
          merged[existingIdx] = action
          lastIdx = existingIdx
        } else {
          merged.push(action)
          lastIdx = merged.length - 1
        }
      }
      setActions(merged)
      setSelIdx(lastIdx >= 0 ? lastIdx : null)
    }
  }

  const updateSelectedAction = data => {
    if (selIdx === null) {
      insertActions([data])
    } else {
      const a = actions.map(({ _id, ...r }, i) => {
        if (i !== selIdx) return r
        const internals = Object.fromEntries(Object.entries(r).filter(([k]) => k.startsWith('_')))
        return { ...data, input: data.input || {}, output: data.output || {}, ...internals }
      })
      setActions(a)
    }
  }

  const handleGleanActionBar = ({ type, data }) => {
    if (type === 'actions') {
      // data is either a plain action array OR { actions: [...], fragmentUpdates: [...] }
      const rawActions = Array.isArray(data) ? data : (data?.actions ?? [])
      const fragmentUpdates = Array.isArray(data) ? [] : (data?.fragmentUpdates ?? [])

      if (rawActions.length > 0) insertActions(rawActions)

      for (const fu of fragmentUpdates) {
        const fuName = fu.name
        const fuContent = fu.content
        if (!fuName || !fuContent) continue

        const contentStr = typeof fuContent === 'string' ? fuContent : JSON.stringify(fuContent, null, 2)
        const updatedItem = { Name: fuName, Content: contentStr, AgentContentType: 'inputs', ContentType: 'json' }

        // Merge into contents — update existing by name, or append
        onContentsChange(prev => {
          const list = prev || []
          const idx = list.findIndex(c => (c.Name || c.name) === fuName)
          if (idx !== -1) {
            const next = [...list]
            next[idx] = { ...next[idx], Content: contentStr }
            return next
          }
          return [...list, updatedItem]
        })

        // Keep _fragment_json on matching renderUI actions in sync
        setActions(prev => prev.map(a =>
          a.type === 'renderUI' && a.inputJSON === fuName
            ? { ...a, _fragment_json: { ...updatedItem } }
            : a
        ))

        // Switch to Fragment Designer and load the updated fragment
        onHandoffToDesigner?.({ ...updatedItem })
      }
    }
    if (type === 'update_action') updateSelectedAction(data)
    if (type === 'fragment_handoff') {
      const url = data.targetAgentUrl || 'https://app.glean.com/chat/agents/2491a8dae7254256975430b2c635a26b'
      window.open(url, '_blank')
    }
    if (type === 'fragment') {
      const url = data.targetAgentUrl || 'https://app.glean.com/chat/agents/2491a8dae7254256975430b2c635a26b'
      window.open(url, '_blank')
    }
  }

  const sel = selIdx !== null ? actions[selIdx] : null
  const selDisplay = sel ? Object.fromEntries(Object.entries(sel).filter(([k]) => !k.startsWith('_'))) : null

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="bg-[#F1F5F9] px-3 py-2 flex items-center gap-2 flex-wrap border-b border-[#CBD5E1] shrink-0">
        <label className="text-xs font-semibold text-[#111827]">Flow:</label>
        <select value={flowId} onChange={e => { setFlowId(e.target.value); setTaskId(Object.keys(flows[e.target.value] || { default: [] })[0] || 'default'); setSelIdx(null) }} className="border rounded px-2 py-1 text-xs bg-white">
          {flowKeys.map(k => <option key={k}>{k}</option>)}
        </select>
        <label className="text-xs font-semibold text-[#111827] ml-2">Task:</label>
        <select value={taskId} onChange={e => { setTaskId(e.target.value); setSelIdx(null) }} className="border rounded px-2 py-1 text-xs bg-white">
          {taskKeys.map(k => <option key={k}>{k}</option>)}
        </select>
        <Btn label="+ Flow" bg="#DBEAFE" fg="#1E3A8A" onClick={addFlow} />
        <Btn label="Del Flow" bg="#FEE2E2" fg="#991B1B" onClick={delFlow} />
        <Btn label="+ Task" bg="#DBEAFE" fg="#1E3A8A" onClick={addTask} />
        <Btn label="Del Task" bg="#FEE2E2" fg="#991B1B" onClick={delTask} />
        <span className="mx-2 text-[#CBD5E1]">|</span>
        <Btn label="Ask Glean" bg="#4C1D95" fg="white" onClick={() => setChatOpen(o => !o)} />
        <Btn label="+ Add Action" bg="#DBEAFE" fg="#1E3A8A" onClick={() => setModal('picker')} />
        <Btn label="Paste JSON" bg="#FEF3C7" fg="#92400E" onClick={() => setModal('paste')} />
        <Btn label="Delete Action" bg="#FEE2E2" fg="#991B1B" onClick={deleteSelected} />
        <span className="mx-2 text-[#CBD5E1]">|</span>
        <input
          type="text"
          placeholder="Search actions…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border rounded px-2 py-1 text-xs w-36 bg-white focus:outline-none focus:border-[#2563EB]"
        />
        {globalHits.length > 0 && (
          <span className="text-xs font-semibold text-[#1E3A8A] bg-[#DBEAFE] px-2 py-0.5 rounded-full" title="Matches across all flows/tasks">
            {searchHitIdx + 1}/{globalHits.length}
            {globalHits[searchHitIdx] && (globalHits[searchHitIdx].flowId !== flowId || globalHits[searchHitIdx].taskId !== taskId) && (
              <> — {globalHits[searchHitIdx].flowId}/{globalHits[searchHitIdx].taskId}</>
            )}
          </span>
        )}
        {search && globalHits.length === 0 && (
          <span className="text-xs text-[#EF4444] font-medium">no match</span>
        )}
        <Btn label="◀ Prev" bg="#F1F5F9" fg="#374151" onClick={() => searchNav(-1)} />
        <Btn label="Next ▶" bg="#F1F5F9" fg="#374151" onClick={() => searchNav(1)} />
        {search && <Btn label="✕ Clear" bg="#FEE2E2" fg="#991B1B" onClick={clearSearch} />}
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Main canvas area */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Canvas */}
          <div className="canvas-scroll bg-[#F0F4F8] border-b border-[#CBD5E1] shrink-0" style={{ height: 200 }}>
            <div className="flex items-center gap-0 px-5 h-full">
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={actions.map(a => a._id)} strategy={horizontalListSortingStrategy}>
                  <div className="flex items-center gap-2">
                    {actions.map((a, i) => (
                      <ActionCard
                        key={a._id}
                        id={`flow-card-${i}`}
                        action={a}
                        index={i}
                        selected={selIdx === i}
                        highlighted={searchHits.length > 0 && searchHits.includes(i) && selIdx !== i}
                        onSelect={setSelIdx}
                        onDoubleClick={() => setModal('edit')}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
              {/* Add zone */}
              <button
                onClick={() => setModal('picker')}
                className="shrink-0 ml-4 w-10 h-10 rounded-full bg-[#DBEAFE] border-2 border-[#2563EB] text-[#2563EB] text-xl font-bold hover:bg-[#BFDBFE] flex items-center justify-center"
              >
                +
              </button>
            </div>
          </div>

          {/* Detail header */}
          <div className="bg-[#1E3A8A] px-4 py-2 flex items-center gap-3 shrink-0">
            <span className="text-white text-sm font-semibold">Action Detail</span>
            <span className="text-[#93C5FD] text-xs">
              {sel ? `[${selIdx + 1}/${actions.length}]  ${sel.name || sel.type}  (${sel.type})` : 'Click a card to select'}
            </span>
            <div className="ml-auto flex gap-2">
              <SmBtn label="< Left" onClick={moveLeft} />
              <SmBtn label="Right >" onClick={moveRight} />
              <SmBtn label="Move To…" onClick={moveTo} />
              {sel && (
                <>
                  <SmBtn label={sel._disabled ? 'Re-connect' : 'Disconnect'} onClick={toggleDisconnect} red />
                  <SmBtn label="Edit JSON" onClick={() => setModal('edit')} />
                  <SmBtn label="Delete" onClick={deleteSelected} red />
                  {sel.type === 'renderUI' && (
                    <>
                      <SmBtn label="Design Fragment" onClick={() => setModal('fragment')} amber />
                      <SmBtn label="🎨 Edit in Designer" onClick={() => {
                        // Prefer live content item over potentially stale _fragment_json
                        const liveContent = sel.inputJSON && Array.isArray(contents)
                          ? contents.find(c => (c.Name || c.name) === sel.inputJSON)
                          : null
                        onHandoffToDesigner(liveContent || sel._fragment_json)
                      }} blue />
                    </>
                  )}
                  {sel.type === 'createUIFragment' && (
                    <SmBtn label="🎨 Preview in Designer" onClick={() => onHandoffToDesigner(buildFragmentFromMetadata(sel))} blue />
                  )}
                </>
              )}
            </div>
          </div>

          {/* Detail JSON */}
          <div className="flex-1 min-h-0 overflow-auto bg-[#1E293B] p-3">
            <pre className="text-[#E2E8F0] text-xs font-mono leading-relaxed">
              {selDisplay ? JSON.stringify(selDisplay, null, 2) : '// Click a card to inspect its JSON'}
            </pre>
          </div>
        </div>

        {/* Glean chat panel */}
        {chatOpen && (
          <GleanChat
            mode="flow"
            chatId={gleanChatId}
            onChatIdChange={onGleanChatIdChange}
            history={gleanHistory}
            onHistoryChange={onGleanHistoryChange}
            onActionBar={handleGleanActionBar}
            title="Flow Builder"
            currentFlow={{
              flowId,
              taskId,
              actions: actions.map(({ _id, ...a }) => a),
              fragments: (contents || []).map(c => ({ name: c.Name || c.name, content: c.Content || c.content || '' })),
            }}
            className="w-80 shrink-0 border-l border-[#334155]"
          />
        )}
      </div>

      {/* Modals */}
      {modal === 'picker' && <ActionTypePicker onAdd={addAction} onClose={() => setModal(null)} onCustom={() => setModal('paste')} />}
      {modal === 'paste' && <PasteJsonModal onInsert={insertActions} onClose={() => setModal(null)} />}
      {modal === 'edit' && sel && <EditActionModal action={sel} onSave={saveEditedAction} onClose={() => setModal(null)} />}
      {modal === 'fragment' && sel && <FragmentModal action={sel} onSave={saveFragment} onClose={() => setModal(null)} />}
    </div>
  )
}

function Btn({ label, bg, fg, onClick }) {
  return (
    <button
      onClick={onClick}
      className="px-2 py-1 rounded text-xs font-medium"
      style={{ backgroundColor: bg, color: fg }}
    >
      {label}
    </button>
  )
}

function SmBtn({ label, onClick, red, amber, blue }) {
  const bg = red ? '#FEE2E2' : amber ? '#FEF3C7' : blue ? '#DBEAFE' : '#F1F5F9'
  const fg = red ? '#991B1B' : amber ? '#92400E' : blue ? '#1E3A8A' : '#374151'
  return (
    <button onClick={onClick} className="px-2 py-0.5 rounded text-xs font-medium border border-black/5" style={{ backgroundColor: bg, color: fg }}>
      {label}
    </button>
  )
}
