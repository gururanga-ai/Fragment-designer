import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import Modal from '../shared/Modal'
import { COMP_COLORS, COMP_ICONS, ELEMENT_LABELS, CHART_TYPES } from '../../utils/fragmentData'
import { HtmlNodeRenderer, collectSegments } from './FragmentCanvas'
import { gleanRunWorkflow } from '../../utils/gleanApi'
import { safeCopyToClipboard } from '../../utils/clipboard'

// ── Python _AF_NEW_NODES node templates ──────────────────────────────────────
const AF_NEW_NODES = {
  'flex-col':     { Container: 'flex', Style: { css: { flexDirection: 'column', gap: '16px', flex: '1', minHeight: '0' } }, Slots: { Default: [] } },
  'flex-row':     { Container: 'flex', Style: { css: { flexDirection: 'row', gap: '16px', flex: '1', overflow: 'hidden' } }, Slots: { Default: [] } },
  'grid':         { Container: 'grid', Style: { css: { flex: '1', display: 'grid', gridTemplateAreas: '"header" "content"', gridTemplateRows: 'auto 1fr' } }, Slots: { header: [], content: [] } },
  'table':        { Container: 'table', Config: { title: 'New Table', pageSize: 25, AutoGenerateColumns: false, SelectionConfig: { ShowSelection: false, SupportMultiSelect: false }, Columns: [], FilterConfig: { filters: [] } }, Style: { flex: '1' }, Slots: { Default: [] } },
  'chart':        { Container: 'chart', Init: { Type: 'value-array', DataSourcePath: '' }, Style: { contentPadding: '0', css: { flex: '1' } }, Config: { chartMetadata: { applyAspectRatio: false, chartWidth: '100%', showChartHeader: false, showChartTitle: false, showHighchartsTitle: false, showLegend: true }, dataMapping: { seriesMappings: [] }, highchartsOptions: { chart: { type: 'column' }, plotOptions: { column: { stacking: 'normal', borderWidth: 0 } }, legend: { enabled: true } } } },
  'header-action':{ Container: 'header-action', Style: { padding: '10px', css: { background: 'var(--manh-summary-bar-background-color)' }, leftActionsCss: { css: { gap: '0rem' } } }, Slots: { Left: [], Right: [] } },
  'card':         { Container: 'card', Config: { title: 'New Card' }, Style: {}, Slots: { Default: [] } },
  'section':      { Container: 'section', Config: { title: 'New Section' }, Style: {}, Slots: { Default: [] } },
}

const CSS_GROUPS = [
  { label: 'Flex / Display', props: ['display', 'flexDirection', 'justifyContent', 'alignItems', 'alignSelf', 'flexWrap', 'flex', 'flexGrow', 'flexShrink', 'flexBasis'] },
  { label: 'Sizing', props: ['width', 'height', 'minWidth', 'maxWidth', 'minHeight', 'maxHeight', 'boxSizing'] },
  { label: 'Gap', props: ['gap', 'rowGap', 'columnGap'] },
  { label: 'Padding', props: ['padding', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft'] },
  { label: 'Margin', props: ['margin', 'marginTop', 'marginRight', 'marginBottom', 'marginLeft'] },
  { label: 'Overflow / Position', props: ['overflow', 'overflowX', 'overflowY', 'position', 'top', 'left', 'right', 'bottom', 'zIndex'] },
  { label: 'Grid', props: ['gridTemplateColumns', 'gridAutoRows', 'gridGap', 'gridColumn', 'gridRow', 'gridTemplateRows'] },
  { label: 'Visual', props: ['backgroundColor', 'color', 'borderRadius', 'border', 'opacity', 'boxShadow', 'backgroundImage'] },
]

// ── Flatten the fragment tree into a list ───────────────────────────────
function flattenTree(node, path = [], depth = 0) {
  if (!node || typeof node !== 'object') return []
  const type = node.Container || node.Element
  const cfg = node.Config || {}
  const rows = [{
    path,
    depth,
    type: type || '?',
    isElement: !!node.Element,
    title: cfg.title || cfg.LabelKey || cfg.SectionName || '',
  }]
  if (node.Slots) {
    for (const [slotKey, children] of Object.entries(node.Slots)) {
      if (Array.isArray(children)) {
        children.forEach((child, i) =>
          rows.push(...flattenTree(child, [...path, 'Slots', slotKey, i], depth + 1))
        )
      }
    }
  }
  return rows
}

function getByPath(root, path) {
  let n = root
  for (const k of path) { if (n == null) return null; n = n[k] }
  return n
}

function deepSet(root, path, value) {
  if (path.length === 0) return value
  const clone = Array.isArray(root) ? [...root] : { ...root }
  clone[path[0]] = deepSet(clone[path[0]], path.slice(1), value)
  return clone
}

// ── Compute diff between original and current fragment ───────────────────
function computeDiff(orig, curr) {
  const diffs = []
  function walk(oNode, cNode, path) {
    if (!oNode && !cNode) return
    if (oNode && !cNode) { diffs.push({ path, type: 'deleted', label: oNode.Container || oNode.Element || '?', title: oNode.Config?.title || '' }); return }
    if (!oNode && cNode) { diffs.push({ path, type: 'added', label: cNode.Container || cNode.Element || '?', title: cNode.Config?.title || '' }); return }
    // CSS diff
    const oC = oNode.Style?.css || {}, cC = cNode.Style?.css || {}
    const cssChanges = []
    for (const p of new Set([...Object.keys(oC), ...Object.keys(cC)])) {
      if (oC[p] !== cC[p]) cssChanges.push({ prop: p, from: oC[p] ?? '(none)', to: cC[p] ?? '(removed)' })
    }
    // Non-CSS Style diff (e.g. padding, width at top-level Style)
    const oS = { ...oNode.Style }, cS = { ...cNode.Style }
    delete oS.css; delete cS.css
    const styleChanges = []
    for (const p of new Set([...Object.keys(oS), ...Object.keys(cS)])) {
      if (JSON.stringify(oS[p]) !== JSON.stringify(cS[p])) styleChanges.push({ prop: p, from: oS[p], to: cS[p] })
    }
    if (cssChanges.length > 0 || styleChanges.length > 0) {
      diffs.push({ path, type: 'modified', label: oNode.Container || oNode.Element || '?', title: oNode.Config?.title || '', cssChanges, styleChanges })
    }
    // Recurse into slots
    const oSlots = oNode.Slots || {}, cSlots = cNode.Slots || {}
    for (const slot of new Set([...Object.keys(oSlots), ...Object.keys(cSlots)])) {
      const oArr = oSlots[slot] || [], cArr = cSlots[slot] || []
      for (let i = 0; i < Math.max(oArr.length, cArr.length); i++) {
        walk(oArr[i], cArr[i], [...path, 'Slots', slot, i])
      }
    }
  }
  walk(orig, curr, [])
  return diffs
}

// ── AlignPreview — live visual preview of selected node ──────────────────
function AlignPreview({ node, css }) {
  if (!node || typeof node !== 'object') {
    return <p className="text-xs text-[#94A3B8] p-2">No node selected</p>
  }

  const type = node.Container || node.Element || '?'
  const color = COMP_COLORS[type] || '#94A3B8'
  const icon = COMP_ICONS[type] || '□'
  const label = ELEMENT_LABELS[type] || type
  const cfg = node.Config || {}
  const slots = node.Slots || {}
  const slotKeys = Object.keys(slots)

  // Build inline style from current css
  const inlineStyle = {}
  if (css.display) inlineStyle.display = css.display
  if (css.flexDirection) inlineStyle.flexDirection = css.flexDirection
  if (css.gap) inlineStyle.gap = css.gap
  if (css.flexWrap) inlineStyle.flexWrap = css.flexWrap
  if (css.justifyContent) inlineStyle.justifyContent = css.justifyContent
  if (css.alignItems) inlineStyle.alignItems = css.alignItems
  if (css.padding) inlineStyle.padding = css.padding
  if (css.backgroundColor) inlineStyle.backgroundColor = css.backgroundColor
  if (css.borderRadius) inlineStyle.borderRadius = css.borderRadius
  if (css.border) inlineStyle.border = css.border
  if (css.width) inlineStyle.width = css.width
  if (css.height) inlineStyle.height = css.height
  if (css.overflow) inlineStyle.overflow = css.overflow

  return (
    <div>
      {/* Node badge */}
      <div className="flex items-center gap-1.5 mb-2 px-1">
        <span className="w-5 h-5 rounded flex items-center justify-center text-white text-xs font-bold shrink-0" style={{ backgroundColor: color }}>
          {icon}
        </span>
        <span className="text-xs font-semibold truncate" style={{ color }}>{label}</span>
      </div>

      {/* CSS applied preview */}
      <div className="rounded border border-[#E2E8F0] mb-2 overflow-hidden" style={{ ...inlineStyle, minHeight: 40, maxHeight: 120, position: 'relative' }}>
        {/* Show child slot count tiles */}
        {slotKeys.map(sk => {
          const children = slots[sk] || []
          return children.slice(0, 4).map((child, i) => {
            const ct = child?.Container || child?.Element || '?'
            const cc = COMP_COLORS[ct] || '#94A3B8'
            const childCss = child?.Style?.css || {}
            return (
              <div key={`${sk}-${i}`} className="rounded text-[9px] text-white font-bold flex items-center justify-center shrink-0"
                style={{
                  backgroundColor: cc,
                  width: childCss.width || 'auto',
                  flex: childCss.flex || (childCss.width ? undefined : 1),
                  minWidth: childCss.minWidth || 20,
                  height: childCss.height || 28,
                  margin: 1,
                  opacity: 0.85,
                }}>
                {ct?.slice(0, 3)}
              </div>
            )
          })
        })}
        {slotKeys.length === 0 && !node.Element && (
          <div className="text-[10px] text-[#94A3B8] p-2 text-center w-full">empty</div>
        )}
        {node.Element && (
          <div className="text-[10px] text-[#374151] px-2 py-1 w-full truncate">
            {cfg.LabelKey || node.Input || type}
          </div>
        )}
      </div>

      {/* CSS summary */}
      <div className="space-y-0.5">
        {Object.entries(css).filter(([, v]) => v && v !== '').map(([k, v]) => (
          <div key={k} className="flex gap-1 text-[10px]">
            <span className="text-[#94A3B8] font-mono w-20 shrink-0 truncate">{k}</span>
            <span className="text-[#374151] font-mono truncate">{v}</span>
          </div>
        ))}
        {Object.keys(css).filter(k => css[k]).length === 0 && (
          <p className="text-[10px] text-[#CBD5E1] italic">No CSS set</p>
        )}
      </div>

      {/* Children count */}
      {slotKeys.length > 0 && (
        <div className="mt-2 pt-1 border-t border-[#F1F5F9]">
          {slotKeys.map(sk => (
            <p key={sk} className="text-[10px] text-[#64748B]">
              <span className="font-semibold">{sk}</span>: {(slots[sk] || []).length} children
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

// ── DiffPanel — shows what changed vs original ───────────────────────────
function DiffPanel({ diffs, onJump }) {
  if (diffs.length === 0) return (
    <div className="text-center pt-8">
      <p className="text-2xl">✅</p>
      <p className="text-xs text-[#166534] font-semibold mt-2">No changes vs original</p>
      <p className="text-[10px] text-[#94A3B8] mt-1">Fragment matches imported JSON</p>
    </div>
  )
  const modified = diffs.filter(d => d.type === 'modified')
  const added = diffs.filter(d => d.type === 'added')
  const deleted = diffs.filter(d => d.type === 'deleted')
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider mb-2">
        {diffs.length} change{diffs.length !== 1 ? 's' : ''} vs original
      </p>
      {deleted.map((d, i) => (
        <div key={i} className="rounded border border-[#FCA5A5] bg-[#FEF2F2] p-1.5 text-[10px]">
          <span className="text-red-600 font-bold">− {d.label}</span>
          {d.title && <span className="text-red-400 ml-1 truncate">({d.title})</span>}
          <div className="text-red-400 mt-0.5">{d.path.join(' › ')}</div>
        </div>
      ))}
      {added.map((d, i) => (
        <div key={i} className="rounded border border-[#86EFAC] bg-[#F0FDF4] p-1.5 text-[10px]">
          <span className="text-green-700 font-bold">+ {d.label}</span>
          {d.title && <span className="text-green-500 ml-1">({d.title})</span>}
          <div className="text-green-400 mt-0.5">{d.path.join(' › ')}</div>
        </div>
      ))}
      {modified.map((d, i) => (
        <div key={i} className="rounded border border-[#BFDBFE] bg-[#EFF6FF] p-1.5 text-[10px] cursor-pointer hover:bg-[#DBEAFE]"
          onClick={() => onJump(d.path)}>
          <div className="flex items-center gap-1 mb-1">
            <span className="text-[#1E3A8A] font-bold">~ {d.label}</span>
            {d.title && <span className="text-[#60A5FA]">({d.title})</span>}
            <span className="ml-auto text-[#2563EB] text-[9px]">→ jump</span>
          </div>
          {[...(d.cssChanges || []), ...(d.styleChanges || [])].map((c, j) => (
            <div key={j} className="font-mono text-[9px] mt-0.5">
              <span className="text-[#64748B]">{c.prop}: </span>
              <span className="text-red-500 line-through mr-1">{String(c.from)}</span>
              <span className="text-green-600">→ {String(c.to)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

// ── TreeItem ─────────────────────────────────────────────────────────────
function TreeItem({ item, selected, onClick }) {
  const { depth, type, title, isElement } = item
  const color = isElement ? '#64748B' : '#1E3A8A'
  return (
    <div
      onClick={onClick}
      className={`cursor-pointer flex items-center gap-1 px-2 py-1 text-xs rounded mx-1 my-0.5
        ${selected ? 'bg-[#DBEAFE] font-semibold' : 'hover:bg-[#F1F5F9]'}`}
      style={{ paddingLeft: 8 + depth * 14 }}
    >
      <span className="shrink-0 text-[10px] font-bold rounded px-1" style={{ backgroundColor: color + '20', color }}>
        {isElement ? 'E' : 'C'}
      </span>
      <span className="truncate" style={{ color }}>{type}</span>
      {title && <span className="text-[#94A3B8] truncate ml-1">— {title}</span>}
    </div>
  )
}

// ── Insert Node dialog ───────────────────────────────────────────────────
function InsertNodeDialog({ slotNames, onInsert, onClose }) {
  const [nodeType, setNodeType] = useState('flex-col')
  const [title, setTitle] = useState('')
  const [slot, setSlot] = useState(slotNames.includes('Default') ? 'Default' : slotNames[0] || 'Default')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-80 p-5 space-y-3">
        <p className="text-sm font-bold text-[#1E3A8A]">Add Container Node</p>
        <div>
          <label className="text-xs font-semibold text-[#374151] block mb-1">Node Type</label>
          <select value={nodeType} onChange={e => setNodeType(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
            {Object.keys(AF_NEW_NODES).map(k => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-[#374151] block mb-1">Title / Label (optional)</label>
          <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="My Container"
            className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
        </div>
        {slotNames.length > 1 && (
          <div>
            <label className="text-xs font-semibold text-[#374151] block mb-1">Add to Slot</label>
            <select value={slot} onChange={e => setSlot(e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
              {slotNames.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}
        <div className="flex gap-2 pt-1">
          <button onClick={() => onInsert(nodeType, title, slot)}
            className="flex-1 py-1.5 text-xs bg-[#1E3A8A] text-white rounded font-semibold hover:bg-[#1E40AF]">Add ✓</button>
          <button onClick={onClose} className="px-4 py-1.5 text-xs bg-[#F1F5F9] text-[#374151] rounded">Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ── AlignGlean — inline Glean chat for CSS auto-fix ─────────────────────
function extractJson(text) {
  const m = text.match(/```(?:json)?\s*([\s\S]*?)```/) || text.match(/(\{[\s\S]*\})/)
  if (!m) return null
  try { return JSON.parse(m[1] || m[0]) } catch { return null }
}

// Deep-merge Style.css from `incoming` into `existing` by tree position.
// All Config, Conditions, Attributes, Slots structure, Element/Container type
// are preserved from `existing`. Only Style.css keys are patched from incoming.
function deepMergeStyleOnly(existing, incoming) {
  if (!existing || typeof existing !== 'object') return existing
  if (!incoming || typeof incoming !== 'object') return existing
  const merged = structuredClone(existing)
  if (incoming.Style?.css && typeof incoming.Style.css === 'object') {
    if (!merged.Style) merged.Style = {}
    if (!merged.Style.css) merged.Style.css = {}
    Object.assign(merged.Style.css, incoming.Style.css)
  }
  if (incoming.Slots && merged.Slots) {
    for (const slotName of Object.keys(incoming.Slots)) {
      if (!Array.isArray(incoming.Slots[slotName])) continue
      if (!Array.isArray(merged.Slots[slotName])) continue
      const inSlot = incoming.Slots[slotName]
      const exSlot = merged.Slots[slotName]
      for (let i = 0; i < Math.min(inSlot.length, exSlot.length); i++) {
        exSlot[i] = deepMergeStyleOnly(exSlot[i], inSlot[i])
      }
    }
  }
  return merged
}

function fragIsEmpty(frag) {
  if (!frag) return true
  const f = frag.Fragment ?? frag
  return !f || typeof f !== 'object' || Object.keys(f).length === 0
}

function applyGleanFixes(existingFrag, result) {
  // When Glean returns { Fragment: {...} }:
  // - If existing is empty → full replace (generation mode, safe)
  // - If existing is non-empty → CSS-only deep merge to preserve Config/Conditions/Attributes
  if (result?.Fragment && typeof result.Fragment === 'object') {
    if (fragIsEmpty(existingFrag)) {
      return { newFrag: result.Fragment, count: 1, mode: 'replace' }
    }
    const merged = deepMergeStyleOnly(existingFrag, result.Fragment)
    return { newFrag: merged, count: 1, mode: 'css-merge' }
  }
  if (!Array.isArray(result?.suggestions)) return null
  const safe = result.suggestions.filter(s => s.fix_props || s.remove_props)
  if (!safe.length) return null
  let newFrag = structuredClone(existingFrag)
  let count = 0
  for (const s of safe) {
    const path = Array.isArray(s.path) ? s.path : []
    const node = path.length > 0 ? getByPath(newFrag, path) : newFrag
    if (!node) continue
    if (!node.Style) node.Style = {}
    if (!node.Style.css) node.Style.css = {}
    if (s.fix_props) Object.assign(node.Style.css, s.fix_props)
    if (s.remove_props) for (const k of s.remove_props) delete node.Style.css[k]
    if (s.fix_config) {
      if (!node.Config) node.Config = {}
      // Merge config keys individually — never wipe the whole Config object
      Object.assign(node.Config, s.fix_config)
    }
    count++
  }
  return { newFrag, count, mode: 'suggestions' }
}

function AlignGlean({ frag, selPath, selNode, onApply }) {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState('')
  const [status, setStatus] = useState('') // 'loading' | 'done' | 'error' | ''
  const [lastApply, setLastApply] = useState(null) // { count, mode }
  // Prior turns in this Align Fix session — replayed on every call (same pattern as the main
  // GleanChat/Agent Creator chat) so follow-ups like "no, the other one" have something to refer
  // to. Without this each send() was a fresh, context-free call with zero memory of earlier turns.
  const [history, setHistory] = useState([])
  const [deepResearch, setDeepResearch] = useState(false)
  const abortRef = useRef(null)
  const responseRef = useRef('')
  const bottomRef = useRef(null)

  useEffect(() => {
    if (streaming) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streaming])

  const sendPrompt = async (promptText) => {
    if (!promptText.trim() || status === 'loading') return
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setStatus('loading')
    setStreaming('')
    setLastApply(null)
    responseRef.current = ''
    const nodeType = selNode?.Container || selNode?.Element || 'root'
    const nodePath = selPath.length > 0 ? selPath.join(' › ') : '(root)'
    const nodeCss = JSON.stringify(selNode?.Style?.css || {}, null, 2)
    const nodeConfig = JSON.stringify(selNode?.Config || {}, null, 2)
    const fullPrompt = `User request: ${promptText.trim()}

Currently selected node:
  path: ${nodePath}
  type: ${nodeType}
  css: ${nodeCss}
  config: ${nodeConfig}

Fix/adjust the selected node (path: ${JSON.stringify(selPath)}) based on the user request. Return suggestions or full Fragment per mode rules.`
    const priorTurns = history
    setHistory(h => [...h, { role: 'user', text: promptText.trim() }])
    try {
      await gleanRunWorkflow({
        prompt: fullPrompt,
        fragment_json: frag,
        issues: [],
        conversation: priorTurns,
        useDeepResearch: deepResearch,
        onPartial: (t) => { responseRef.current = t; setStreaming(t) },
        signal: ctrl.signal,
      })
      setHistory(h => [...h, { role: 'ai', text: responseRef.current }])
      setStreaming('')
      const parsed = extractJson(responseRef.current)
      if (parsed) {
        const result = applyGleanFixes(frag, parsed)
        if (result) {
          onApply(result.newFrag)
          setLastApply({ count: result.count, mode: result.mode })
        }
      }
      setStatus('done')
    } catch (e) {
      if (e.name !== 'AbortError') setStatus('error')
    }
  }

  const send = () => { sendPrompt(input); setInput('') }
  const handleKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  const chips = [
    { label: 'Auto-tune layout', prompt: 'Auto-tune the CSS layout of the selected node — fix flex alignment, sizing, gaps and spacing for best fit.' },
    { label: 'Fix overflow', prompt: 'Fix any overflow or clipping issues on the selected node and its children.' },
    { label: 'Equal columns', prompt: 'Make all slot children of the selected node equal width columns.' },
    { label: 'Center content', prompt: 'Center the content inside the selected node using flexbox.' },
    { label: 'Fix spacing', prompt: 'Fix padding, margin and gap values on the selected node for consistent spacing.' },
  ]

  return (
    <div className="border-t border-[#E2E8F0] flex flex-col bg-[#F0F4FF]" style={{ minHeight: 0 }}>
      {/* header */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#1E3A8A]">
        <span className="text-[#93C5FD] text-xs font-bold tracking-wide">✨ Glean AI Fix</span>
        <button
          onClick={() => setDeepResearch(d => !d)}
          title={deepResearch ? 'Thinking mode — slower, more thorough' : 'Fast mode — quick response'}
          className={`text-[10px] px-2 py-0.5 rounded-full font-medium border transition-colors ${
            deepResearch ? 'bg-[#4C1D95] text-[#DDD6FE] border-[#7C3AED]' : 'bg-transparent text-[#93C5FD] border-[#3B5998] hover:border-[#93C5FD]'
          }`}
        >
          {deepResearch ? '🧠 Thinking' : '⚡ Fast'}
        </button>
        {lastApply && (
          <span className="ml-auto text-[10px] bg-green-600 text-white rounded px-1.5 py-0.5 font-semibold">
            {lastApply.mode === 'replace' ? '🔄 Fragment replaced' : `✓ ${lastApply.count} fix${lastApply.count !== 1 ? 'es' : ''} applied`}
          </span>
        )}
        {status === 'loading' && <span className="ml-auto text-[10px] text-[#93C5FD] animate-pulse">Glean thinking…</span>}
        {status === 'error' && <span className="ml-auto text-[10px] text-red-300">Error — try again</span>}
        {history.length > 0 && (
          <button onClick={() => setHistory([])} className="ml-auto text-[10px] text-[#93C5FD] hover:text-white">Clear history</button>
        )}
      </div>

      {/* quick chips */}
      <div className="flex flex-wrap gap-1 px-2 pt-1.5">
        {chips.map(c => (
          <button key={c.label}
            onClick={() => { setInput(c.prompt); sendPrompt(c.prompt) }}
            className="text-[10px] px-2 py-0.5 rounded-full bg-[#DBEAFE] text-[#1E3A8A] hover:bg-[#BFDBFE] font-medium border border-[#BFDBFE]"
          >{c.label}</button>
        ))}
      </div>

      {/* conversation history — replayed to Glean on every send() so it has memory of prior turns */}
      {(history.length > 0 || streaming) && (
        <div className="mx-2 mt-1.5 rounded bg-white border border-[#E2E8F0] text-[10px] font-mono text-[#374151] px-2 py-1.5 max-h-28 overflow-y-auto whitespace-pre-wrap space-y-1.5">
          {history.map((m, i) => (
            <div key={i}>
              <span className={`font-bold ${m.role === 'user' ? 'text-[#1E3A8A]' : 'text-[#7C3AED]'}`}>{m.role === 'user' ? 'You: ' : 'Glean: '}</span>
              {m.text}
            </div>
          ))}
          {streaming && (
            <div>
              <span className="font-bold text-[#7C3AED]">Glean: </span>{streaming}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* input row */}
      <div className="flex gap-1.5 px-2 py-1.5 items-end">
        <textarea
          rows={2}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder={`Ask Glean to fix selected node (${selNode?.Container || selNode?.Element || 'root'})… Enter to send`}
          className="flex-1 text-xs rounded border border-[#CBD5E1] px-2 py-1 resize-none focus:outline-none focus:ring-1 focus:ring-[#3B82F6] bg-white"
        />
        <button
          onClick={send}
          disabled={status === 'loading' || !input.trim()}
          className="px-3 py-1.5 text-xs rounded bg-[#1E3A8A] text-white font-semibold hover:bg-[#1E40AF] disabled:opacity-40 shrink-0"
        >Send</button>
      </div>
    </div>
  )
}

// ── ScaledHtmlPreview — scales full fragment to fit container width ──────
function ScaledHtmlPreview({ frag, selPath, onSelect }) {
  const containerRef = useRef(null)
  const [scale, setScale] = useState(0.3)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const NATURAL_W = 1200
    const setS = () => setScale(el.offsetWidth / NATURAL_W)
    setS()
    const ro = new ResizeObserver(setS)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const NATURAL_W = 1200
  const NATURAL_H = 700

  return (
    <div ref={containerRef} style={{ width: '100%', height: Math.round(NATURAL_H * scale), overflow: 'hidden', position: 'relative', backgroundColor: '#E8EDF2' }}>
      <div style={{
        width: NATURAL_W,
        height: NATURAL_H,
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
        backgroundColor: 'white',
        position: 'absolute',
        top: 0,
        left: 0,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <HtmlNodeRenderer
          node={frag}
          path={[]}
          selectedPath={selPath}
          onSelect={onSelect}
        />
      </div>
    </div>
  )
}

// ── Main AlignFix dialog ─────────────────────────────────────────────────
export default function AlignFix({ fragment, onClose, onSave, originalFragment = null }) {
  const [frag, setFrag] = useState(() => structuredClone(fragment))
  const [selPath, setSelPath] = useState([])
  const [jsonMode, setJsonMode] = useState(false)
  const [jsonStr, setJsonStr] = useState('')
  const [jsonErr, setJsonErr] = useState('')
  const [saved, setSaved] = useState(false)
  const [showInsert, setShowInsert] = useState(false)
  const [rightPanel, setRightPanel] = useState('preview') // 'preview' | 'diff'
  const [maximized, setMaximized] = useState(false)
  const [gleanOpen, setGleanOpen] = useState(false)
  const [treeWidth, setTreeWidth] = useState(224)
  const treeWidthRef = useRef(224)
  const [previewWidth, setPreviewWidth] = useState(384)
  const previewWidthRef = useRef(384)

  const makeDragHandler = useCallback((getRef, setWidth, minW, maxW, dir = 1) => (e) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = getRef()
    const onMove = (ev) => {
      const delta = (ev.clientX - startX) * dir
      const next = Math.max(minW, Math.min(maxW, startW + delta))
      setWidth(next)
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [])

  const startTreeDrag = useCallback(
    makeDragHandler(() => treeWidthRef.current, (v) => { treeWidthRef.current = v; setTreeWidth(v) }, 120, 420, 1),
    [makeDragHandler]
  )
  const startPreviewDrag = useCallback(
    makeDragHandler(() => previewWidthRef.current, (v) => { previewWidthRef.current = v; setPreviewWidth(v) }, 200, 1100, -1),
    [makeDragHandler]
  )

  const tree = flattenTree(frag)
  const selNode = selPath.length > 0 ? getByPath(frag, selPath) : frag
  const css = selNode?.Style?.css || {}
  const selCtype = selNode?.Container || null
  const selEtype = selNode?.Element || null
  const selType = selCtype || selEtype
  const selIsChart = CHART_TYPES.has(selType) || selType === 'chart'
  const selIsDataBound = selIsChart || selType === 'table' || selType === 'metrics' || selType === 'carousel'
  const segmentOptions = useMemo(() => [...collectSegments(frag)].sort(), [frag])

  const updateCss = (prop, val) => {
    const newFrag = structuredClone(frag)
    const node = selPath.length > 0 ? getByPath(newFrag, selPath) : newFrag
    if (!node) return
    if (!node.Style) node.Style = {}
    if (!node.Style.css) node.Style.css = {}
    if (val.trim() === '') delete node.Style.css[prop]
    else node.Style.css[prop] = val
    setFrag(newFrag)
  }

  const updateConfig = (key, val) => {
    const newFrag = structuredClone(frag)
    const node = selPath.length > 0 ? getByPath(newFrag, selPath) : newFrag
    if (!node) return
    if (!node.Config) node.Config = {}
    if (val === '' || val === undefined) delete node.Config[key]
    else node.Config[key] = val
    setFrag(newFrag)
  }

  const updateDataSourcePath = val => {
    const newFrag = structuredClone(frag)
    const node = selPath.length > 0 ? getByPath(newFrag, selPath) : newFrag
    if (!node) return
    if (!node.Init) node.Init = { Type: 'value-array' }
    node.Init.DataSourcePath = val
    if (!node.Config) node.Config = {}
    node.Config.dataSourcePath = val
    setFrag(newFrag)
  }

  const moveInSlot = (dir) => {
    if (selPath.length < 1) return
    const idx = selPath[selPath.length - 1]
    if (typeof idx !== 'number') return
    const slotPath = selPath.slice(0, -1)
    const newFrag = structuredClone(frag)
    const slot = getByPath(newFrag, slotPath)
    if (!Array.isArray(slot)) return
    const target = idx + dir
    if (target < 0 || target >= slot.length) return
    ;[slot[idx], slot[target]] = [slot[target], slot[idx]]
    setFrag(newFrag)
    setSelPath([...selPath.slice(0, -1), target])
  }

  const cleanEmpty = () => {
    const strip = node => {
      if (!node || typeof node !== 'object') return
      if (node.Style?.css) {
        for (const k of Object.keys(node.Style.css)) {
          const v = node.Style.css[k]
          if (v === '' || v === null || v === undefined) delete node.Style.css[k]
        }
        if (!Object.keys(node.Style.css).length) delete node.Style.css
        if (!Object.keys(node.Style || {}).length) delete node.Style
      }
      if (node.Slots) for (const s of Object.values(node.Slots)) if (Array.isArray(s)) s.forEach(strip)
    }
    const newFrag = structuredClone(frag)
    strip(newFrag)
    setFrag(newFrag)
  }

  const autoTune = () => {
    // Distribute equal widths to all slot children in a flex-row container
    if (!selNode) return
    const newFrag = structuredClone(frag)
    const node = selPath.length > 0 ? getByPath(newFrag, selPath) : newFrag
    if (!node?.Slots) return
    const flexDir = node.Style?.css?.flexDirection || 'row'
    const isRow = !flexDir || flexDir === 'row' || flexDir === 'row-reverse'
    for (const slot of Object.values(node.Slots)) {
      if (!Array.isArray(slot) || slot.length === 0) continue
      const pct = Math.round(10000 / slot.length) / 100
      slot.forEach(child => {
        if (!child || typeof child !== 'object') return
        if (!child.Style) child.Style = {}
        if (!child.Style.css) child.Style.css = {}
        if (isRow) {
          child.Style.css.width = `${pct}%`
          delete child.Style.css.flex
        } else {
          child.Style.css.width = '100%'
        }
      })
    }
    setFrag(newFrag)
  }

  const openNodeJson = () => {
    setJsonStr(JSON.stringify(selNode, null, 2))
    setJsonErr('')
    setJsonMode(true)
  }

  const saveNodeJson = () => {
    try {
      const parsed = JSON.parse(jsonStr)
      const newFrag = selPath.length > 0
        ? deepSet(structuredClone(frag), selPath, parsed)
        : parsed
      setFrag(newFrag)
      setJsonMode(false)
    } catch (e) { setJsonErr(e.message) }
  }

  const insertNode = (templateKey, title, slotName) => {
    const tpl = AF_NEW_NODES[templateKey]
    if (!tpl) return
    const newNode = JSON.parse(JSON.stringify(tpl))
    if (title.trim()) {
      if (!newNode.Config) newNode.Config = {}
      newNode.Config.title = title.trim()
    }
    const newFrag = structuredClone(frag)
    const target = selPath.length > 0 ? getByPath(newFrag, selPath) : newFrag
    if (!target) return
    if (!target.Slots) target.Slots = {}
    if (!target.Slots[slotName]) target.Slots[slotName] = []
    target.Slots[slotName].push(newNode)
    setFrag(newFrag)
    setShowInsert(false)
  }

  const deleteNode = () => {
    if (selPath.length === 0) return
    const label = selNode?.Container || selNode?.Element || 'this node'
    const title = selNode?.Config?.title || selNode?.Config?.LabelKey
    if (!window.confirm(`Delete "${label}"${title ? ` (${title})` : ''} at ${selPath.join(' › ')}? This cannot be undone.`)) return
    // Find parent path: last segment is array index
    const idx = selPath[selPath.length - 1]
    if (typeof idx !== 'number') return
    const slotPath = selPath.slice(0, -1)
    const newFrag = structuredClone(frag)
    const slot = getByPath(newFrag, slotPath)
    if (!Array.isArray(slot)) return
    slot.splice(idx, 1)
    setFrag(newFrag)
    setSelPath([])
  }

  const handleSave = () => {
    onSave(frag)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const copyJson = async () => {
    const ok = await safeCopyToClipboard(JSON.stringify({ Fragment: frag }, null, 2))
    alert(ok ? 'Fragment JSON copied.' : 'Could not copy automatically — select and copy the JSON manually.')
  }

  // Slots of the currently selected node (for insert dialog)
  const selSlotNames = selNode?.Slots ? Object.keys(selNode.Slots).filter(k => Array.isArray(selNode.Slots[k])) : []

  return (
    <Modal title="Align Fix — CSS Layout Editor" onClose={onClose} width="max-w-7xl" maximized={maximized} onMaximize={() => setMaximized(m => !m)} resizable defaultWidth={1100} defaultHeight={640}>
      {showInsert && selSlotNames.length > 0 && (
        <InsertNodeDialog slotNames={selSlotNames} onInsert={insertNode} onClose={() => setShowInsert(false)} />
      )}
      <div className="flex" style={{ height: maximized ? 'calc(100vh - 110px)' : '100%' }}>
        {/* ── Left: Tree ── */}
        <div className="shrink-0 border-r border-[#E2E8F0] overflow-y-auto bg-[#F8FAFC] py-2" style={{ width: treeWidth }}>
          <p className="text-xs font-bold text-[#64748B] px-3 mb-1 uppercase tracking-wider">Fragment Tree</p>
          <div
            onClick={() => setSelPath([])}
            className={`cursor-pointer flex items-center gap-1 px-2 py-1 text-xs rounded mx-1 my-0.5
              ${selPath.length === 0 ? 'bg-[#DBEAFE] font-semibold text-[#1E3A8A]' : 'hover:bg-[#F1F5F9]'}`}
          >
            <span className="shrink-0 text-[10px] font-bold rounded px-1 bg-[#DBEAFE] text-[#1E3A8A]">C</span>
            <span className="truncate">{frag.Container || 'root'}</span>
            {frag.Config?.title && <span className="text-[#94A3B8] truncate ml-1">— {frag.Config.title}</span>}
          </div>
          {tree.slice(1).map((item, i) => (
            <TreeItem key={i} item={item}
              selected={JSON.stringify(item.path) === JSON.stringify(selPath)}
              onClick={() => setSelPath(item.path)} />
          ))}
        </div>

        {/* ── Drag handle: tree / editor ── */}
        <div
          onMouseDown={startTreeDrag}
          className="w-1.5 shrink-0 cursor-col-resize hover:bg-[#3B82F6] bg-[#E2E8F0] transition-colors"
          title="Drag to resize tree"
        />

        {/* ── Center: CSS Editor ── */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="sticky top-0 z-10 bg-[#1E3A8A] px-4 py-2 flex items-center gap-2 shrink-0">
            <span className="text-white text-sm font-semibold">
              {selPath.length === 0 ? frag.Container || 'Root' : (selNode?.Container || selNode?.Element || '?')}
            </span>
            <span className="text-[#93C5FD] text-xs font-mono truncate flex-1">
              {selPath.length > 0 ? selPath.join(' › ') : '(root)'}
            </span>
            <button onClick={openNodeJson} className="text-xs px-2 py-0.5 bg-[#334155] text-[#93C5FD] rounded hover:bg-[#475569]">
              Edit JSON
            </button>
            <button
              onClick={() => setGleanOpen(o => !o)}
              className={`text-xs px-2 py-0.5 rounded font-semibold border ${gleanOpen ? 'bg-[#7C3AED] text-white border-[#7C3AED]' : 'bg-transparent text-[#C4B5FD] border-[#7C3AED] hover:bg-[#7C3AED] hover:text-white'}`}
            >
              ✨ Glean
            </button>
            {selSlotNames.length > 0 && (
              <button onClick={() => setShowInsert(true)} className="text-xs px-2 py-0.5 bg-[#065F46] text-[#6EE7B7] rounded hover:bg-[#047857]">
                ➕ Add Child
              </button>
            )}
            {selPath.length > 0 && typeof selPath[selPath.length - 1] === 'number' && (
              <>
                <span className="w-px self-stretch bg-[#3B5998] mx-1" />
                <button onClick={deleteNode} className="text-xs px-2 py-0.5 bg-[#7F1D1D] text-[#FCA5A5] rounded hover:bg-[#991B1B]">
                  🗑 Delete
                </button>
              </>
            )}
          </div>

          <div className="flex-1 overflow-y-auto min-h-0">

          {jsonMode ? (
            <div className="p-4 space-y-2">
              <textarea rows={18} value={jsonStr} onChange={e => { setJsonStr(e.target.value); setJsonErr('') }}
                className="w-full font-mono text-sm bg-[#1E293B] text-[#E2E8F0] p-3 rounded resize-none" />
              {jsonErr && <p className="text-red-500 text-xs">⚠ {jsonErr}</p>}
              <div className="flex gap-2">
                <button onClick={saveNodeJson} className="px-4 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-semibold">Apply</button>
                <button onClick={() => setJsonMode(false)} className="px-4 py-1.5 text-xs bg-[#F1F5F9] text-[#374151] rounded">Cancel</button>
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-5">
              <datalist id="align-fix-segment-options">
                {segmentOptions.map(s => <option key={s} value={s} />)}
              </datalist>
              {selCtype && (
                <div>
                  <p className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-2 border-b border-[#F1F5F9] pb-1">General</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-[#374151] w-36 shrink-0 font-mono">title</label>
                      <input type="text" value={selNode.Config?.title || ''} onChange={e => updateConfig('title', e.target.value)} placeholder="—"
                        className="flex-1 border rounded px-2 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB] border-[#E2E8F0] bg-white" />
                    </div>
                    {selIsDataBound && (
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-[#374151] w-36 shrink-0 font-mono">dataSourcePath</label>
                        <input type="text" value={selNode.Init?.DataSourcePath || selNode.Config?.dataSourcePath || ''} onChange={e => updateDataSourcePath(e.target.value)} placeholder="—"
                          className="flex-1 border rounded px-2 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB] border-[#E2E8F0] bg-white" />
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-[#374151] w-36 shrink-0 font-mono">segment</label>
                      <input type="text" list="align-fix-segment-options" value={selNode.Config?.SectionName || ''} onChange={e => updateConfig('SectionName', e.target.value)}
                        placeholder="Type new or pick existing…"
                        className="flex-1 border rounded px-2 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB] border-[#E2E8F0] bg-white" />
                    </div>
                  </div>
                </div>
              )}
              {CSS_GROUPS.map(group => (
                <div key={group.label}>
                  <p className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-2 border-b border-[#F1F5F9] pb-1">{group.label}</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {group.props.map(prop => {
                      const val = css[prop] ?? ''
                      return (
                        <div key={prop} className="flex items-center gap-2">
                          <label className="text-xs text-[#374151] w-36 shrink-0 font-mono">{prop}</label>
                          <input type="text" value={val} onChange={e => updateCss(prop, e.target.value)} placeholder="—"
                            className={`flex-1 border rounded px-2 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB]
                              ${val ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#E2E8F0] bg-white'}`} />
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
              <div>
                <p className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-2 border-b border-[#F1F5F9] pb-1">Raw Style.css</p>
                <pre className="text-xs font-mono bg-[#F8FAFC] rounded p-3 text-[#374151] overflow-x-auto max-h-40">
                  {JSON.stringify(css, null, 2) || '{}'}
                </pre>
              </div>
            </div>
          )}
          </div>{/* end scrollable editor area */}

          {gleanOpen && (
            <AlignGlean
              frag={frag}
              selPath={selPath}
              selNode={selNode}
              onApply={(newFrag) => setFrag(newFrag)}
            />
          )}
        </div>

        {/* ── Drag handle ── */}
        <div
          onMouseDown={startPreviewDrag}
          className="w-1.5 shrink-0 cursor-col-resize hover:bg-[#3B82F6] bg-[#E2E8F0] transition-colors"
          title="Drag to resize preview"
        />

        {/* ── Right: HTML Preview / Diff ── */}
        <div className="shrink-0 border-l border-[#E2E8F0] bg-white flex flex-col" style={{ width: previewWidth }}>
          <div className="bg-[#1E3A8A] px-2 py-1.5 flex items-center gap-1">
            <button onClick={() => setRightPanel('preview')}
              className={`text-xs px-2 py-0.5 rounded font-semibold ${rightPanel === 'preview' ? 'bg-white text-[#1E3A8A]' : 'text-[#93C5FD] hover:bg-[#1E40AF]'}`}>
              🖥 Preview
            </button>
            {originalFragment && (
              <button onClick={() => setRightPanel('diff')}
                className={`text-xs px-2 py-0.5 rounded font-semibold ${rightPanel === 'diff' ? 'bg-white text-[#1E3A8A]' : 'text-[#93C5FD] hover:bg-[#1E40AF]'}`}>
                📊 Diff
              </button>
            )}
            <span className="ml-auto flex items-center gap-1">
              <button
                onClick={() => { const next = previewWidth < 600 ? 800 : 384; previewWidthRef.current = next; setPreviewWidth(next) }}
                title={previewWidth < 600 ? 'Expand preview' : 'Shrink preview'}
                className="text-[#60A5FA] hover:text-white text-xs px-1"
              >
                {previewWidth < 600 ? '⟩⟩' : '⟨⟨'}
              </button>
              <span className="text-[9px] text-[#60A5FA]">{previewWidth}px</span>
            </span>
          </div>
          <div className="flex-1 overflow-hidden" style={{ backgroundColor: '#E8EDF2' }}>
              {rightPanel === 'preview' || !originalFragment ? (
                <ScaledHtmlPreview
                  frag={frag}
                  selPath={selPath}
                  onSelect={path => setSelPath(path)}
                />
              ) : (
                <div className="p-2 overflow-auto h-full">
                  <DiffPanel diffs={computeDiff(originalFragment, frag)} onJump={path => setSelPath(path)} />
                </div>
              )}
          </div>
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="border-t border-[#E2E8F0] px-4 py-2.5 flex items-center gap-2 bg-[#F8FAFC]">
        <button onClick={() => moveInSlot(-1)} className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]">▲ Move Up</button>
        <button onClick={() => moveInSlot(1)} className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]">▼ Move Down</button>
        <button onClick={autoTune} className="px-3 py-1.5 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-medium hover:opacity-90">Auto-tune Widths</button>
        <button onClick={cleanEmpty} className="px-3 py-1.5 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-medium hover:opacity-90">Clean Empty CSS</button>
        <span className="flex-1" />
        {saved && <span className="text-green-600 text-xs font-semibold">Saved ✓</span>}
        <button onClick={handleSave} className="px-4 py-1.5 text-xs bg-[#1E3A8A] text-white rounded font-semibold hover:bg-[#1E40AF]">Save & Apply</button>
        <button onClick={copyJson} className="px-3 py-1.5 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-medium">Copy JSON</button>
        <button onClick={onClose} className="px-3 py-1.5 text-xs bg-[#F1F5F9] text-[#374151] rounded">Close</button>
      </div>
    </Modal>
  )
}
