import { useState, useCallback, useEffect } from 'react'
import ElementPalette from './ElementPalette'
import FragmentCanvas from './FragmentCanvas'
import PropertyPanel from './PropertyPanel'
import FilterPanel, { buildFilterElement, parseFPNode, extractFPFromFragment, makeDefaultSection } from './FilterPanel'
import GleanChat from '../shared/GleanChat'
import AlignFix from './AlignFix'
import JsonEditor from '../shared/JsonEditor'
import { makeDefaultElement } from '../../utils/fragmentData'
import { safeCopyToClipboard, safeReadClipboardText } from '../../utils/clipboard'

const EMPTY_FRAGMENT = {
  Fragment: {
    Container: 'flex',
    Config: { title: 'My Fragment' },
    Style: { css: { flexDirection: 'column', gap: '16px' } },
    Slots: { Default: [] },
  },
}

function cleanJson(str) {
  // Strip BOM + invisible/zero-width Unicode chars
  str = str.replace(/[﻿​‌‍‎‏￾]/g, '').trim()
  // Strip JS comments
  str = str.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')
  // Strip trailing commas before } or ]
  str = str.replace(/,\s*([}\]])/g, '$1')
  // Wrap unquoted {: template vars } with quotes so JSON.parse accepts them
  // Only wrap when preceded by : [ or , (value position), not already quoted
  str = str.replace(/([:\[,]\s*)\{:([^}]+)\}/g, '$1"{:$2}"')
  return str
}

// Restore {: template vars } to unquoted form in final JSON string output
function restoreTemplateVars(str) {
  return str.replace(/"\{:([^}]+)\}"/g, '{:$1}')
}

// ── Glean suggestion path resolver ───────────────────────────────────────────
export function gleanResolvePath(fragmentRoot, path) {
  if (!path) return null
  let p = path.startsWith('Fragment.') ? path.slice(9) : path
  const parts = []
  // Order matters: quoted-bracket keys (for slot names with spaces, e.g. ['Fill Rate']) and
  // numeric indices must be tried before the plain-segment catch-all, or the catch-all's
  // [^.[]+ would swallow the brackets/quotes as part of a garbage literal segment.
  const re = /\['([^']*)'\]|\["([^"]*)"\]|\[(\d+)\]|([^.[]+)/g
  let m
  while ((m = re.exec(p)) !== null) {
    if (m[1] !== undefined) parts.push(m[1])
    else if (m[2] !== undefined) parts.push(m[2])
    else if (m[3] !== undefined) parts.push(parseInt(m[3]))
    else if (m[4] !== undefined) parts.push(m[4])
  }
  if (parts.length === 0) return { parent: { root: fragmentRoot }, key: 'root', target: fragmentRoot }
  let parent = fragmentRoot
  for (const seg of parts.slice(0, -1)) {
    if (parent == null) return null
    parent = parent[seg]
  }
  const key = parts[parts.length - 1]
  return { parent, key, target: parent?.[key] }
}

export function applyGleanSuggestion(fragmentRoot, suggestion) {
  const op = suggestion.op || 'set_props'
  const path = suggestion.path || ''
  const resolved = gleanResolvePath(fragmentRoot, path)
  if (!resolved) return false
  const { parent, key, target } = resolved

  if (op === 'set_props') {
    const node = target || {}
    const updated = { ...node, ...(suggestion.fix_props || {}) }
    for (const rp of (suggestion.remove_props || [])) delete updated[rp]
    parent[key] = updated
    return true
  }
  if (op === 'merge_json') {
    parent[key] = deepMerge(target || {}, suggestion.merge_data || {})
    return true
  }
  if (op === 'replace_node') { parent[key] = suggestion.new_node || target; return true }
  if (op === 'add_child') {
    const slotKey = suggestion.slot_key || 'Default'
    const node = target || {}
    if (!node.Slots) node.Slots = {}
    if (!node.Slots[slotKey]) node.Slots[slotKey] = []
    node.Slots[slotKey].push(suggestion.child_node || makeDefaultElement('card'))
    parent[key] = node
    return true
  }
  if (op === 'delete_node') {
    if (typeof key === 'number' && Array.isArray(parent)) parent.splice(key, 1)
    else delete parent[key]
    return true
  }
  if (op === 'set_fragment') {
    const newFrag = suggestion.fragment || target
    if (newFrag && typeof newFrag === 'object') Object.assign(fragmentRoot, newFrag)
    return true
  }
  if (op === 'set_config') {
    const node = target || {}
    if (!node.Config) node.Config = {}
    Object.assign(node.Config, suggestion.fix_props || {})
    parent[key] = node
    return true
  }
  if (op === 'set_events') {
    const node = target || {}
    node.Events = deepMerge(node.Events || {}, suggestion.fix_props || {})
    parent[key] = node
    return true
  }
  return false
}

function deepMerge(target, source) {
  if (typeof source !== 'object' || source === null) return source
  const out = Array.isArray(target) ? [...target] : { ...target }
  for (const k of Object.keys(source)) {
    if (typeof source[k] === 'object' && source[k] !== null && typeof out[k] === 'object' && out[k] !== null) {
      out[k] = deepMerge(out[k], source[k])
    } else {
      out[k] = source[k]
    }
  }
  return out
}

// ── Locate a bare node returned by Glean (no path) inside the current fragment tree ─────────
// Used when the chat panel replies with just "the container that needs a change" rather than
// the structured {suggestions:[{path,...}]} contract — we have to figure out where it belongs.
function flattenNodePaths(node, path = []) {
  if (!node || typeof node !== 'object') return []
  const out = [{ path, node }]
  if (node.Slots) {
    for (const [slotKey, children] of Object.entries(node.Slots)) {
      if (Array.isArray(children)) {
        children.forEach((child, i) => out.push(...flattenNodePaths(child, [...path, 'Slots', slotKey, i])))
      }
    }
  }
  return out
}

function nodeIdentitySignature(node) {
  const cfg = node.Config || {}
  return {
    type: node.Container || node.Element || '',
    title: cfg.title || cfg.LabelKey || cfg.SectionName || '',
    dataKey: cfg.DataKey || node.Init?.DataSourcePath || cfg.dataSourcePath || '',
    input: node.Input || '',
    slotKeys: node.Slots ? Object.keys(node.Slots).sort().join(',') : '',
  }
}

// Returns { path, confidence } for the best match, or null if no confident match was found.
// Deliberately conservative — a wrong guess corrupts the tree, so ties/weak matches return null
// rather than silently merging into the wrong node.
function findNodePath(root, incoming) {
  if (!incoming || typeof incoming !== 'object') return null
  const target = nodeIdentitySignature(incoming)
  if (!target.type) return null
  const scored = flattenNodePaths(root)
    .filter(({ path }) => path.length > 0) // root itself is handled separately by the caller
    .map(({ path, node }) => {
      const sig = nodeIdentitySignature(node)
      if (sig.type !== target.type) return { path, score: -1 }
      let score = 1 // bare type match
      if (target.title && sig.title === target.title) score += 3
      if (target.dataKey && sig.dataKey === target.dataKey) score += 3
      if (target.input && sig.input === target.input) score += 2
      if (target.slotKeys && sig.slotKeys === target.slotKeys) score += 1
      return { path, score }
    })
    .filter(c => c.score >= 0)
    .sort((a, b) => b.score - a.score)

  if (scored.length === 0) return null
  const [best, second] = scored
  const hasIdentitySignal = best.score > 1
  const isUniqueOfType = second === undefined
  if (!hasIdentitySignal && !isUniqueOfType) return null // ambiguous bare type match, multiple candidates
  if (second && second.score === best.score) return null // tie — can't disambiguate
  return { path: best.path, confidence: hasIdentitySignal ? 'high' : 'medium' }
}

function getByPathFD(root, path) {
  let n = root
  for (const k of path) { if (n == null) return null; n = n[k] }
  return n
}

function setAtPath(root, path, value) {
  if (path.length === 0) return value
  const clone = Array.isArray(root) ? [...root] : { ...root }
  clone[path[0]] = setAtPath(clone[path[0]], path.slice(1), value)
  return clone
}

// ── Parse Action JSON → varPool ──────────────────────────────────────────────
function parseActionJson(raw) {
  raw = raw.replace(/"\{:([^}]+)\}"/g, '"{:$1}"')
  const data = JSON.parse(raw)
  const dm = {}

  function extractVars(obj) {
    if (typeof obj !== 'object' || obj === null) return
    if (obj.type === 'renderUI') {
      if (obj.dataMap && typeof obj.dataMap === 'object') {
        Object.assign(dm, obj.dataMap)
      }
      if (obj.input && typeof obj.input === 'object') {
        for (const [k, v] of Object.entries(obj.input)) {
          if (typeof v === 'string') dm[k] = v
        }
      }
    } else {
      for (const v of Object.values(obj)) {
        extractVars(v)
      }
    }
  }

  // Handle direct objects (not inside an array/flow structure)
  if (data.dataMap && typeof data.dataMap === 'object') Object.assign(dm, data.dataMap)
  if (data.input && typeof data.input === 'object') {
    for (const [k, v] of Object.entries(data.input)) {
      if (typeof v === 'string') dm[k] = v
    }
  }

  extractVars(data)

  if (Object.keys(dm).length === 0) {
    throw new Error("No variables found. Expected renderUI action with 'dataMap' or 'input' object.")
  }
  
  return Object.fromEntries(Object.entries(dm).filter(([k, v]) => k && typeof v === 'string'))
}

// ── Count total filters across sections ─────────────────────────────────────
function countFilters(filterSections) {
  return filterSections.reduce((s, sec) => s + sec.filters.length, 0)
}

// ── Build Action JSON from fragment datasources ───────────────────────────────
function buildActionJson(fragmentName, fragment, filterSections, filterPosition) {
  const dataMap = {}
  const CHART_TYPES = new Set(['pie','bar','line','column','spline','area','areaspline','scatter','sunburst','waterfall','chart'])
  function extract(node) {
    if (!node || typeof node !== 'object') return
    const type = node.Container || node.Element
    if (CHART_TYPES.has(type) || type === 'table' || type === 'metrics') {
      const ds = node.Init?.DataSourcePath || node.Config?.dataSourcePath
      const bv = node.Config?.backendVar
      if (ds && bv) dataMap[ds] = bv
    }
    if (node.Slots) Object.values(node.Slots).forEach(arr => Array.isArray(arr) && arr.forEach(extract))
  }
  extract(fragment)
  if (countFilters(filterSections) > 0 && filterPosition !== 'none') dataMap['Filters'] = 'object::Filters'
  return {
    type: 'renderUI',
    name: fragmentName || 'mheDashboardFragment',
    input: {},
    output: {},
    unsupportedOnUI: true,
    inputJSON: fragmentName || 'mheDashboardFragment',
    dataMap,
    description: 'Render MHE Dashboard UI',
    bundleNames: ['com-manh-cp-dcorder:labels', 'com-manh-cp-dcorder:seeddata'],
    outputVariableName: 'response',
    allowedPostFailure: true,
  }
}

// ── Build full export fragment (wraps with filter if needed) ──────────────────
function buildExportFragment(fragment, filterSections, filterPosition, wrapFlyout, sidebarRightSlot) {
  const hasFilters = countFilters(filterSections) > 0 && filterPosition !== 'none'
  let inner = fragment

  if (hasFilters) {
    const filterEl = buildFilterElement(filterSections)

    if (filterPosition === 'top') {
      inner = {
        Container: 'flex',
        Style: { css: { flexDirection: 'column', gap: '0' } },
        Slots: { Default: [filterEl, fragment] },
      }
    } else if (filterPosition === 'left' || filterPosition === 'right') {
      const flyoutCard = {
        Container: 'flyout-card',
        Config: { closeButtonPosition: 'right' },
        Style: { padding: '0px', width: '23vw' },
        Slots: { Default: [filterEl] },
      }
      const sideKey = filterPosition === 'left' ? 'Left' : 'Right'
      const slots = {
        [sideKey]: [flyoutCard],
        Default: [fragment],
      }
      // Passthrough existing right slot content if exporting a left sidebar
      if (sideKey === 'Left' && sidebarRightSlot && sidebarRightSlot.length > 0) {
        slots.Right = sidebarRightSlot
      }

      inner = {
        Container: 'sidebar',
        Style: {},
        Slots: slots,
      }
    }
  }

  // Final Wrap: Flyout-Card Wrapper Mode (100vw Drill-Down)
  if (wrapFlyout) {
    return {
      Fragment: {
        Container: 'flyout-card',
        Init: fragment.Init || { Type: 'agentic-api', DefaultValues: { Filters: '{:Filters}' } },
        Config: { closeButtonPosition: 'left', showCloseButton: true, hideFlyoutCardByDefault: false },
        Style: { width: '100vw', padding: '0px' },
        Events: {
          Triggers: {
            CloseFlyout: [{ EventId: 'close-details-flyout', ContainerId: 'details-flyout' }]
          }
        },
        Slots: { Default: [inner] }
      }
    }
  }

  return { Fragment: inner }
}

export default function FragmentDesigner({ varPool, setVarPool, varSchemas = {}, handoffFragment, onHandoffConsumed }) {
  const [fragment, setFragment] = useState(EMPTY_FRAGMENT)
  const [selectedPath, setSelectedPath] = useState([])
  const [gleanHistory, setGleanHistory] = useState([])
  const [chatOpen, setChatOpen] = useState(false)
  const [exportVisible, setExportVisible] = useState(false)
  const [alignFixOpen, setAlignFixOpen] = useState(false)
  const [strictMode, setStrictMode] = useState(false)
  const [importedRoot, setImportedRoot] = useState(null)
  const [gleanApplyStatus, setGleanApplyStatus] = useState(null)
  const [handoffSourceName, setHandoffSourceName] = useState(null) // content item Name from Agent Creator

  // Consuming handoff from Agent Creator
  useEffect(() => {
    if (!handoffFragment) return

    // New fragment loaded = new Glean context
    setGleanHistory([])

    // Fragment prompt handoff — open chat pre-filled with the layout prompt
    if (handoffFragment._fragmentPrompt) {
      setChatOpen(true)
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('glean-prefill', { detail: handoffFragment._fragmentPrompt }))
      }, 150)
      onHandoffConsumed()
      return
    }

    // Capture source name BEFORE consuming (for "Save to Agent" round-trip)
    const sourceName = handoffFragment.Name || handoffFragment.name || null
    setHandoffSourceName(sourceName)

    // Parse fragment data from content object or direct fragment
    // Content key may be uppercase (AgentCreator state) or lowercase (parseAgentJson output)
    const rawContent = handoffFragment.Content || handoffFragment.content
    let fragData = handoffFragment
    if (rawContent && typeof rawContent === 'string') {
      // Content object from AgentContentsCustom — parse the Content JSON string
      const tryParse = (str) => {
        try {
          const p = JSON.parse(str)
          // Unwrap if needed: { Fragment: {...} } or direct node { Container: ... }
          if (p && typeof p === 'object' && !Array.isArray(p)) {
            if (p.Fragment) return p
            if (p.Container || p.Element) return { Fragment: p }
          }
        } catch (_) {}
        return null
      }
      const direct = tryParse(rawContent)
      const sanitized = direct || tryParse(rawContent.replace(/\{:\w+\}/g, 'null'))
      if (sanitized) {
        fragData = sanitized
      } else {
        // Content unparseable — treat as empty, let user generate
        fragData = { Fragment: {} }
        console.warn('Could not parse fragment Content, starting empty', rawContent)
      }
    } else if (handoffFragment.Fragment) {
      fragData = handoffFragment
    } else if (!rawContent) {
      // Direct node or unknown shape — wrap
      fragData = { Fragment: handoffFragment }
    }

    setFragment(fragData)
    setImportedRoot(fragData.Fragment ? structuredClone(fragData.Fragment) : null)
    setSelectedPath([])
    if (sourceName) setFragmentName(sourceName)
    else if (fragData.Fragment?.Config?.title) setFragmentName(fragData.Fragment.Config.title)

    // Empty fragment + description → open chat pre-filled so user can generate
    const isEmpty = !fragData.Fragment || Object.keys(fragData.Fragment).length === 0
    if (isEmpty && (handoffFragment.description || sourceName)) {
      setChatOpen(true)
      setTimeout(() => {
        const prompt = handoffFragment.description || `Generate fragment layout for ${sourceName}`
        window.dispatchEvent(new CustomEvent('glean-prefill', { detail: prompt }))
      }, 150)
    }

    onHandoffConsumed()
  }, [handoffFragment, onHandoffConsumed])

  // Sync importedRoot whenever fragment changes in strict mode so tab-group slot
  // changes (eject / reassign) and any canvas edits are reflected in the export.
  const updateFragment = useCallback((newFragObj) => {
    setFragment(newFragObj)
    if (strictMode && importedRoot) setImportedRoot(structuredClone(newFragObj.Fragment))
  }, [strictMode, importedRoot])

  // ── New state ──────────────────────────────────────────────────────────────
  const [fragmentName, setFragmentName] = useState('My Dashboard Fragment')
  const [filterSections, setFilterSections] = useState([makeDefaultSection()])
  const [filterPosition, setFilterPosition] = useState('top')
  const [screenSize, setScreenSize] = useState('Desktop (1920)')
  const [canvasZoom, setCanvasZoom] = useState(1.0)
  const [showVarPoolModal, setShowVarPoolModal] = useState(false)
  const [exportMode, setExportMode] = useState('fragment') // 'fragment' | 'action'
  const [pasteModalOpen, setPasteModalOpen] = useState(false)
  const [wrapFlyout, setWrapFlyout] = useState(false)
  const [sidebarRightSlot, setSidebarRightSlot] = useState([])

  const applyImportedFragment = (wrapped) => {
    setFragment(wrapped)
    setImportedRoot(structuredClone(wrapped.Fragment))
    setSelectedPath([])
    if (wrapped.Fragment?.Config?.title) setFragmentName(wrapped.Fragment.Config.title)

    // Preserve sidebar right slot if any
    if (wrapped.Fragment?.Container === 'sidebar' && wrapped.Fragment?.Slots?.Right) {
      setSidebarRightSlot(wrapped.Fragment.Slots.Right)
    }

    // Detect wrapFlyout mode
    if (wrapped.Fragment?.Container === 'flyout-card' && wrapped.Fragment?.Style?.width === '100vw') {
      setWrapFlyout(true)
    } else {
      setWrapFlyout(false)
    }

    // Load filter-panel from imported JSON into filter sections UI
    const fpNode = extractFPFromFragment(wrapped.Fragment)
    if (fpNode) {
      const parsed = parseFPNode(fpNode)
      if (parsed && parsed.length > 0) setFilterSections(parsed)
    }
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async e => {
      const file = e.target.files[0]
      if (!file) return
      try {
        const raw = cleanJson(await file.text())
        const data = JSON.parse(raw)
        if (data.type === 'renderUI') throw new Error('Paste the Fragment JSON, not the Action JSON.')
        const wrapped = data.Fragment ? data : { Fragment: data }
        applyImportedFragment(wrapped)
      } catch (err) {
        alert(`Import error: ${err.message}`)
      }
    }
    input.click()
  }

  const handlePasteImport = () => setPasteModalOpen(true)

  const exportFragmentObj = strictMode && importedRoot ? importedRoot : fragment.Fragment
  const exportObj = buildExportFragment(exportFragmentObj, filterSections, filterPosition, wrapFlyout, sidebarRightSlot)
  const exportStr = restoreTemplateVars(JSON.stringify(exportObj, null, 2))
  const actionJsonStr = JSON.stringify(buildActionJson(fragmentName, exportFragmentObj, filterSections, filterPosition), null, 2)

  const handleCopyExport = async () => {
    const str = exportMode === 'action' ? actionJsonStr : exportStr
    const ok = await safeCopyToClipboard(str)
    alert(ok ? `${exportMode === 'action' ? 'Action' : 'Fragment'} JSON copied to clipboard.` : 'Could not copy automatically — select and copy the JSON manually.')
  }

  const handleDownload = () => {
    const str = exportMode === 'action' ? actionJsonStr : exportStr
    const fname = exportMode === 'action' ? `${fragmentName || 'action'}.json` : `${fragmentName || 'fragment'}.json`
    const blob = new Blob([str], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = fname; a.click()
    URL.revokeObjectURL(url)
  }

  // CSS-only deep merge: patches Style.css from `incoming` into `existing` by tree position.
  // Config, Conditions, Attributes, Slots structure — all preserved from existing.
  const deepMergeStyleOnly = useCallback((existing, incoming) => {
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
  }, [])

  const handleGleanActionBar = useCallback(({ type, data }) => {
    if (type === 'suggestions' && data?.suggestions) {
      const suggestions = data.suggestions
      const newFrag = structuredClone(fragment)
      let ok = 0
      const errors = []
      for (const s of suggestions) {
        const hasPayload = (s.fix_props && Object.keys(s.fix_props).length > 0)
          || (s.remove_props && s.remove_props.length > 0)
          || s.child_node || s.new_node || s.merge_data
        if (!hasPayload) {
          errors.push(`Skipped "${s.suggestion_label || s.issue_id || s.path}" — no fix payload (informational only)`)
          continue
        }
        try {
          const applied = applyGleanSuggestion(newFrag.Fragment, s)
          if (applied) ok++
          else errors.push(`Unhandled op "${s.op}" at path "${s.path}"`)
        } catch (err) {
          errors.push(`Error applying "${s.op}" at "${s.path}": ${err.message}`)
        }
      }
      if (ok > 0) updateFragment(newFrag)
      setGleanApplyStatus({ count: suggestions.length, ok, errors })
      if (ok === 0) setTimeout(() => setGleanApplyStatus(null), 6000)
      return
    }
    if (type === 'agent' || data?.full_fragment_update || data?.full_fragment) {
      const raw = data.full_fragment_update || data.full_fragment || data
      if (raw && typeof raw === 'object') {
        const incomingNode = raw.Fragment ?? raw
        const existingNode = fragment.Fragment
        const existingIsEmpty = !existingNode || Object.keys(existingNode).length === 0
        if (existingIsEmpty) {
          // Empty canvas — safe to do full replacement
          updateFragment(raw.Fragment ? raw : { Fragment: raw })
          setGleanApplyStatus(null)
          return
        }
        // Explicit {Fragment:{...}} wrapper, or the node's own shape mirrors the current root
        // (same container type + has slots) — treat as a full-tree CSS-only merge at the root.
        const looksLikeRoot = !!raw.Fragment || (
          incomingNode.Container && incomingNode.Container === existingNode.Container
          && incomingNode.Slots && Object.keys(incomingNode.Slots).length > 0
        )
        if (looksLikeRoot) {
          const merged = deepMergeStyleOnly(existingNode, incomingNode)
          updateFragment({ Fragment: merged })
          setGleanApplyStatus(null)
          return
        }
        // Otherwise Glean handed back just "the container/element that needs a change" with no
        // path — locate where it actually belongs in the tree and merge it there, not at root.
        const match = findNodePath(existingNode, incomingNode)
        if (match) {
          const existingSub = getByPathFD(existingNode, match.path)
          const mergedSub = deepMergeStyleOnly(existingSub, incomingNode)
          const newRoot = setAtPath(existingNode, match.path, mergedSub)
          updateFragment({ Fragment: newRoot })
          setGleanApplyStatus({
            count: 1, ok: 1,
            errors: match.confidence === 'medium' ? [`Applied at best-guess path ${match.path.join('.')} — verify it landed on the right node.`] : [],
          })
          if (match.confidence === 'medium') setTimeout(() => setGleanApplyStatus(null), 8000)
        } else {
          setGleanApplyStatus({
            count: 1, ok: 0,
            errors: [`Couldn't identify which node this JSON belongs to (no matching or ambiguous container found) — nothing was changed. Try "Align Fix" and ask Glean there, or select the node first and paste it via Edit JSON.`],
          })
          setTimeout(() => setGleanApplyStatus(null), 8000)
        }
      }
    }
  }, [fragment, updateFragment, deepMergeStyleOnly])

  return (
    <div className="flex flex-col h-full bg-[#F8FAFC]">
      {/* ── Top Toolbar ── */}
      <div className="bg-[#F1F5F9] h-14 flex items-center shrink-0 border-b border-[#CBD5E1] shadow-sm">
        <div className="bg-[#1E3A8A] px-4 h-full flex items-center gap-2 shrink-0">
          <span className="text-white text-sm">⬡</span>
          <span className="text-white text-xs font-bold uppercase tracking-wider">Fragment Designer</span>
        </div>

        {/* Fragment name + draft badge */}
        <div className="flex items-center gap-2 px-4">
          <input
            value={fragmentName}
            onChange={e => setFragmentName(e.target.value)}
            className="bg-transparent text-[#1E3A8A] text-sm font-bold border-none outline-none w-48 focus:bg-white focus:px-2 focus:rounded transition-all"
            placeholder="Fragment name..."
          />
          <span className="px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] text-[10px] font-bold rounded">Draft</span>
        </div>

        <div className="flex-1" />

        <NavSection label="FILE">
          <TBtn label="📥 Import" onClick={handleImport} />
          <TBtn label="📋 Paste" onClick={handlePasteImport} />
          <TBtn label="📤 Export ▾" onClick={() => setExportVisible(v => !v)} />
          <TBtn label="💾 Copy Fragment" onClick={() => { setExportMode('fragment'); setExportVisible(true); handleCopyExport() }} blue />
          {handoffSourceName && (
            <TBtn
              label="⬆ Save to Agent"
              title={`Save fragment back to Agent Creator content item "${handoffSourceName}"`}
              onClick={() => {
                const fragObj = exportFragmentObj
                if (!fragObj) return
                window.dispatchEvent(new CustomEvent('fragment-saved-to-agent', {
                  detail: { name: handoffSourceName, fragment: fragObj }
                }))
                alert(`Fragment saved back to "${handoffSourceName}" in Agent Creator.`)
              }}
              style={{ backgroundColor: '#F59E0B', color: '#1E293B', borderColor: '#F59E0B' }}
            />
          )}
        </NavSection>

        <NavSection label="VARIABLES">
          <TBtn label="🗃 Pool" onClick={() => setShowVarPoolModal(true)}
            title="Variables extracted from Agent Creator or imported JSON"
            style={Object.keys(varPool).length > 0 ? { backgroundColor: '#DCFCE7', color: '#166534', borderColor: '#BBF7D0' } : {}}
          />
          {Object.keys(varPool).length > 0 && (
            <div className="flex flex-col -ml-1">
               <span className="text-[10px] text-[#166534] font-bold leading-none">{Object.keys(varPool).length}</span>
               <span className="text-[8px] text-[#166534] opacity-70 font-bold uppercase">vars</span>
            </div>
          )}
        </NavSection>

        <NavSection label="AI CO-PILOT">
          <TBtn label="✨ Ask Glean" onClick={() => setChatOpen(o => !o)} purple />
        </NavSection>

        <NavSection label="LAYOUT FIX">
          <TBtn label="🔧 Align Fix" onClick={() => setAlignFixOpen(true)} amber />
          <TBtn label={strictMode ? '🔒 Strict ON' : '🔓 Strict OFF'}
            onClick={() => setStrictMode(m => !m)}
            style={strictMode ? { backgroundColor: '#DCFCE7', color: '#166534', borderColor: '#BBF7D0' } : {}}
          />
        </NavSection>

        <NavSection label="MODES">
          <TBtn label={wrapFlyout ? '🚀 Full Screen ON' : '🚀 Full Screen OFF'} 
            onClick={() => setWrapFlyout(v => !v)}
            style={wrapFlyout ? { backgroundColor: '#F3E8FF', color: '#6D28D9', borderColor: '#DDD6FE' } : {}}
          />
          <TBtn label="⚡ Action JSON" onClick={() => { setExportMode('action'); setExportVisible(true) }} blue />
          <TBtn label="🗑 Clear" onClick={() => { if(confirm('Clear fragment?')) { setFragment(EMPTY_FRAGMENT); setSelectedPath([]); setImportedRoot(null) } }} red />
        </NavSection>
      </div>

      {/* ── Export panel ── */}
      {exportVisible && (
        <div className="bg-[#1E293B] px-4 py-3 flex gap-3 items-start border-b border-[#334155] shrink-0 max-h-64">
          <div className="flex flex-col gap-1 shrink-0">
            <button
              onClick={() => setExportMode('fragment')}
              className={`text-xs px-2 py-1 rounded ${exportMode === 'fragment' ? 'bg-[#2563EB] text-white' : 'bg-[#334155] text-[#94A3B8]'}`}
            >Fragment JSON</button>
            <button
              onClick={() => setExportMode('action')}
              className={`text-xs px-2 py-1 rounded ${exportMode === 'action' ? 'bg-[#F59E0B] text-[#1E293B]' : 'bg-[#334155] text-[#94A3B8]'}`}
            >⚡ Action JSON</button>
          </div>
          <div className="flex-1 min-w-0 overflow-auto max-h-52">
            {strictMode && exportMode === 'fragment' && (
              <p className="text-[#86EFAC] text-xs font-semibold mb-1">🔒 Strict mode — exporting original imported JSON verbatim</p>
            )}
            {countFilters(filterSections) > 0 && exportMode === 'fragment' && (
              <p className="text-[#FCD34D] text-xs mb-1">
                ⚠ {countFilters(filterSections)} filter(s) in {filterSections.length} section(s) injected as filter-panel — position: {filterPosition}
              </p>
            )}
            <pre className="text-[#E2E8F0] text-xs font-mono leading-relaxed">
              {exportMode === 'action' ? actionJsonStr : exportStr}
            </pre>
          </div>
          <div className="flex flex-col gap-1 shrink-0">
            <button onClick={handleCopyExport} className="text-xs px-3 py-1 bg-[#FEF3C7] text-[#92400E] rounded">Copy</button>
            <button onClick={handleDownload} className="text-xs px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded">Download</button>
            <button onClick={() => setExportVisible(false)} className="text-xs px-3 py-1 bg-[#334155] text-[#94A3B8] rounded">✕</button>
          </div>
        </div>
      )}

      {/* ── Glean apply status ── */}
      {gleanApplyStatus && (
        <div className={`px-4 py-2 text-xs flex gap-3 items-center shrink-0 border-b ${gleanApplyStatus.errors.length > 0 ? 'bg-[#FEF2F2] border-[#FECACA]' : 'bg-[#F0FDF4] border-[#BBF7D0]'}`}>
          <span className={gleanApplyStatus.errors.length > 0 ? 'text-[#991B1B]' : 'text-[#166534]'}>
            ✨ Applied {gleanApplyStatus.ok}/{gleanApplyStatus.count} suggestion(s)
          </span>
          {gleanApplyStatus.errors.length > 0 && (
            <span className="text-[#DC2626]">{gleanApplyStatus.errors[0]}</span>
          )}
          {gleanApplyStatus.ok > 0 && (
            <button
              onClick={() => { setAlignFixOpen(true); setGleanApplyStatus(null) }}
              className="px-2 py-0.5 bg-[#166534] text-white rounded hover:bg-[#15803D] font-semibold shrink-0"
            >
              🔧 Open Align Fix to Validate
            </button>
          )}
          <button onClick={() => setGleanApplyStatus(null)} className="ml-auto text-[#94A3B8] hover:text-[#374151] shrink-0 text-sm">✕</button>
        </div>
      )}

      {/* ── Filter panel ── */}
      <FilterPanel
        filterSections={filterSections}
        setFilterSections={setFilterSections}
        varPool={varPool}
        filterPosition={filterPosition}
        setFilterPosition={setFilterPosition}
      />

      {/* ── Main 3-panel layout ── */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Element palette + Data tab */}
        <ElementPalette
          varPool={varPool}
          onAddElement={type => {
            const frag = structuredClone(fragment)
            addElementAtPath(frag.Fragment, selectedPath, type)
            updateFragment(frag)
          }}
        />

        {/* Center: Canvas */}
        <FragmentCanvas
          fragment={fragment.Fragment}
          selectedPath={selectedPath}
          onSelect={setSelectedPath}
          onChange={newFrag => updateFragment({ Fragment: newFrag })}
          screenSize={screenSize}
          onScreenSizeChange={setScreenSize}
          canvasZoom={canvasZoom}
          onZoomChange={setCanvasZoom}
          varPool={varPool}
        />

        {/* Right: Properties or Glean */}
        <div className="w-80 shrink-0 border-l border-[#CBD5E1] flex flex-col">
          {chatOpen ? (
            <GleanChat
              mode="agent"
              history={gleanHistory}
              onHistoryChange={setGleanHistory}
              onActionBar={handleGleanActionBar}
              title="Fragment Designer Agent"
              fragmentJson={fragment.Fragment}
              selectedPath={selectedPath}
              varPool={varPool}
              className="flex-1"
            />
          ) : (
            <PropertyPanel
              fragment={fragment.Fragment}
              selectedPath={selectedPath}
              onChange={newFrag => updateFragment({ Fragment: newFrag })}
              varPool={varPool}
              varSchemas={varSchemas}
              onDelete={() => {
                const frag = structuredClone(fragment)
                deleteAtPath(frag.Fragment, selectedPath)
                updateFragment(frag)
                setSelectedPath([])
              }}
              gleanHistory={gleanHistory}
              onGleanHistoryChange={setGleanHistory}
              onGleanActionBar={handleGleanActionBar}
            />
          )}
        </div>
      </div>

      {/* ── Align Fix modal ── */}
      {alignFixOpen && (
        <AlignFix
          fragment={fragment.Fragment}
          originalFragment={importedRoot}
          onClose={() => setAlignFixOpen(false)}
          onSave={newFrag => updateFragment({ Fragment: newFrag })}
        />
      )}

      {/* ── Paste JSON Modal ── */}
      {pasteModalOpen && (
        <PasteJsonModal
          onImport={applyImportedFragment}
          onClose={() => setPasteModalOpen(false)}
        />
      )}

      {/* ── Variable Pool Import Modal ── */}
      {showVarPoolModal && (
        <VarPoolModal
          varPool={varPool}
          onSave={pool => { setVarPool(pool); setShowVarPoolModal(false) }}
          onClose={() => setShowVarPoolModal(false)}
        />
      )}
    </div>
  )
}

// ── Toolbar components ────────────────────────────────────────────────────────
function NavSection({ label, children }) {
  return (
    <div className="flex flex-col items-center px-3 h-full justify-center border-l border-[#CBD5E1]">
      <div className="flex gap-1.5 items-center">{children}</div>
      <span className="text-[#64748B] text-[10px] font-bold mt-0.5 tracking-tight">{label}</span>
    </div>
  )
}

function TBtn({ label, onClick, amber, purple, red, blue, green, title, style: extraStyle }) {
  // Manhattan Active Palette
  const bg = amber ? '#FEF3C7' : purple ? '#F3E8FF' : red ? '#FEE2E2' : blue ? '#DBEAFE' : green ? '#DCFCE7' : '#FFFFFF'
  const fg = amber ? '#92400E' : purple ? '#6D28D9' : red ? '#991B1B' : blue ? '#1E3A8A' : green ? '#166534' : '#374151'
  const border = amber ? '#FDE68A' : purple ? '#DDD6FE' : red ? '#FECACA' : blue ? '#BFDBFE' : green ? '#BBF7D0' : '#E2E8F0'

  return (
    <button
      onClick={onClick}
      title={title}
      className="text-[11px] px-2.5 py-1.5 rounded-md font-semibold border transition-all hover:brightness-95 active:scale-95 whitespace-nowrap shadow-sm"
      style={{ backgroundColor: bg, color: fg, borderColor: border, ...extraStyle }}
    >
      {label}
    </button>
  )
}

// ── Paste JSON Modal ──────────────────────────────────────────────────────────
function PasteJsonModal({ onImport, onClose }) {
  const [raw, setRaw] = useState('')
  const [status, setStatus] = useState('')

  // Pre-populate from clipboard on open
  useEffect(() => {
    safeReadClipboardText().then(text => {
      if (text && text.trim().startsWith('{')) setRaw(text)
    })
  }, [])

  const handleLoad = () => {
    try {
      const cleaned = cleanJson(raw)
      const data = JSON.parse(cleaned)
      if (data.type === 'renderUI') {
        setStatus('✕ Paste the Fragment JSON, not the Action JSON.')
        return
      }
      if (!data.Fragment) {
        setStatus('✕ JSON must have a top-level "Fragment" key.')
        return
      }
      onImport(data)
      onClose()
    } catch (err) {
      setStatus(`✕ Parse error: ${err.message}`)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[780px] max-h-[85vh] flex flex-col overflow-hidden">
        <div className="bg-[#1E3A8A] px-5 py-3.5 flex items-center justify-between">
          <span className="text-white font-bold text-sm tracking-tight uppercase">📋 Paste Fragment JSON</span>
          <button onClick={onClose} className="text-white/60 hover:text-white text-lg px-1 transition-colors">✕</button>
        </div>

        <div className="bg-[#F1F5F9] px-5 py-2.5 border-b border-[#CBD5E1]">
          <p className="text-xs text-[#1E3A8A] font-medium italic">
            ⓘ Paste your Manhattan Active Fragment JSON below. Unquoted template vars like{' '}
            <code className="bg-[#DBEAFE] px-1.5 py-0.5 rounded text-[#1E3A8A] font-bold font-mono">{'{:Filters}'}</code> are handled automatically.
          </p>
        </div>

        <div className="flex-1 min-h-0 overflow-auto p-5 bg-[#F8FAFC]">
          <textarea
            value={raw}
            onChange={e => { setRaw(e.target.value); setStatus('') }}
            rows={18}
            className="w-full border border-[#CBD5E1] rounded-lg px-4 py-3 text-xs font-mono focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-blue-200 bg-white text-[#334155] shadow-inner resize-none"
            placeholder={'{\n  "Fragment": {\n    "Container": "...",\n    ...\n  }\n}'}
            autoFocus
          />
          {status && (
            <div className={`mt-3 px-3 py-2 rounded text-xs font-semibold ${status.startsWith('✓') ? 'bg-[#DCFCE7] text-[#166534]' : 'bg-[#FEE2E2] text-[#991B1B]'}`}>
              {status}
            </div>
          )}
        </div>

        <div className="px-5 py-4 bg-white border-t border-[#E2E8F0] flex gap-3 justify-end">
          <button onClick={onClose} className="px-5 py-2 text-sm bg-[#F1F5F9] text-[#374151] rounded-md font-semibold hover:bg-[#E2E8F0] transition-colors border border-[#CBD5E1]">
            Cancel
          </button>
          <button
            onClick={handleLoad}
            className="px-6 py-2 text-sm bg-[#1E3A8A] text-white rounded-md font-bold hover:bg-[#1E40AF] shadow-md active:scale-95 transition-all"
          >
            Load Fragment →
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Variable Pool Import Modal ────────────────────────────────────────────────
function VarPoolModal({ varPool, onSave, onClose }) {
  const [raw, setRaw] = useState(Object.keys(varPool).length > 0
    ? JSON.stringify({ type: 'renderUI', name: 'myFragment', dataMap: varPool }, null, 2)
    : ''
  )
  const [status, setStatus] = useState('')
  const [parsed, setParsed] = useState(varPool)

  const tryParse = () => {
    try {
      const pool = parseActionJson(raw)
      setParsed(pool)
      setStatus(`✓ Found ${Object.keys(pool).length} dataMap variable(s).`)
    } catch (e) {
      setStatus(`✕ ${e.message}`)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[700px] max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-[#1E3A8A] px-5 py-3.5 flex items-center justify-between">
          <div>
            <span className="text-white font-bold text-sm tracking-tight uppercase">🗃 Action JSON → Variable Pool</span>
            {Object.keys(varPool).length > 0 && (
              <span className="ml-3 px-2 py-0.5 bg-[#DCFCE7] text-[#166534] text-[10px] font-bold rounded-full">POOL ACTIVE: {Object.keys(varPool).length} VARS</span>
            )}
          </div>
          <button onClick={onClose} className="text-white/60 hover:text-white text-lg px-1 transition-colors">✕</button>
        </div>

        {/* Info */}
        <div className="bg-[#F3E8FF] px-5 py-2.5 border-b border-[#DDD6FE]">
          <p className="text-xs text-[#6D28D9] font-medium">
            ⓘ Paste your <code className="bg-[#E9D5FF] px-1.5 py-0.5 rounded text-[#6D28D9] font-bold">renderUI</code> Action JSON below. The <code className="bg-[#E9D5FF] px-1.5 py-0.5 rounded text-[#6D28D9] font-bold italic">dataMap</code> or <code className="bg-[#E9D5FF] px-1.5 py-0.5 rounded text-[#6D28D9] font-bold italic">input</code> keys
            become available as dropdown choices in every Data Source field.
          </p>
        </div>

        <div className="flex-1 min-h-0 overflow-auto p-5 space-y-4 bg-[#F8FAFC]">
          {/* JSON input */}
          <textarea
            value={raw}
            onChange={e => { setRaw(e.target.value); setStatus('') }}
            rows={12}
            className="w-full border border-[#CBD5E1] rounded-lg px-4 py-3 text-xs font-mono focus:outline-none focus:border-[#6D28D9] focus:ring-1 focus:ring-purple-200 bg-white text-[#334155] shadow-inner resize-none"
            placeholder={example}
          />

          {status && (
            <p className={`px-3 py-2 rounded text-xs font-bold ${status.startsWith('✓') ? 'bg-[#DCFCE7] text-[#166534]' : 'bg-[#FEE2E2] text-[#991B1B]'}`}>{status}</p>
          )}

          {/* Pool preview */}
          {Object.keys(parsed).length > 0 && (
            <div>
              <p className="text-xs font-bold text-[#475569] uppercase tracking-wider mb-2">Variable Pool Preview ({Object.keys(parsed).length} entries):</p>
              <div className="border border-[#CBD5E1] rounded-lg divide-y divide-[#E2E8F0] max-h-40 overflow-auto shadow-sm bg-white">
                {Object.entries(parsed).map(([k, v]) => (
                  <div key={k} className="flex px-3 py-2 text-xs hover:bg-[#F8FAFC] transition-colors group">
                    <span className="font-mono text-[#1E3A8A] font-bold w-44 shrink-0 truncate">{k}</span>
                    <span className="text-[#94A3B8] mx-2 group-hover:text-[#1E3A8A] transition-colors">→</span>
                    <span className="font-mono text-[#64748B] truncate italic">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-5 py-4 bg-white border-t border-[#E2E8F0] flex gap-3 justify-end">
          <button onClick={tryParse} className="px-5 py-2 text-sm bg-[#F3E8FF] text-[#6D28D9] rounded-md font-bold hover:bg-[#E9D5FF] transition-colors border border-[#DDD6FE]">
            Validate JSON
          </button>
          <button
            onClick={() => {
              try {
                const pool = parseActionJson(raw)
                onSave(pool)
              } catch (e) {
                setStatus(`✕ ${e.message}`)
              }
            }}
            className="px-6 py-2 text-sm bg-[#1E3A8A] text-white rounded-md font-bold hover:bg-[#1E40AF] shadow-md active:scale-95 transition-all"
          >
            Update Pool ({Object.keys(parsed).length})
          </button>
          <button onClick={onClose} className="px-5 py-2 text-sm bg-[#F1F5F9] text-[#374151] rounded-md font-semibold hover:bg-[#E2E8F0] border border-[#CBD5E1]">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Fragment path helpers ─────────────────────────────────────────────────────
function addElementAtPath(frag, path, type) {
  const newEl = makeDefaultElement(type)
  
  if (!path || path.length === 0) {
    if (!frag.Slots) frag.Slots = {}
    if (!frag.Slots.Default) frag.Slots.Default = []
    frag.Slots.Default.push(newEl)
    return
  }

  // Traverse to the selected node
  let node = frag
  for (const key of path) {
    if (node == null) return
    node = node[key]
  }

  // 1. If the selected node is a container (has Slots), append to its Default slot
  if (node && (node.Container || node.Slots)) {
    if (!node.Slots) node.Slots = {}
    if (!node.Slots.Default) node.Slots.Default = []
    node.Slots.Default.push(newEl)
    return
  }

  // 2. If the selected node is an Element (no Slots), insert as a sibling
  // Walk back to the parent array
  let parent = frag
  for (const key of path.slice(0, -2)) {
    parent = parent[key]
  }
  
  // path.slice(-2) should be something like ['Default', index]
  const slotKey = path[path.length - 2]
  const insertIndex = path[path.length - 1]

  if (parent && parent[slotKey] && Array.isArray(parent[slotKey])) {
    parent[slotKey].splice(insertIndex + 1, 0, newEl)
  }
}

function deleteAtPath(frag, path) {
  if (path.length === 0) return
  let node = frag
  for (const key of path.slice(0, -2)) node = node[key]
  const parent = path.length >= 2 ? node[path[path.length - 2]] : frag
  const last = path[path.length - 1]
  if (typeof last === 'number' && Array.isArray(parent)) parent.splice(last, 1)
  else if (parent?.Slots?.Default) {
    const idx = parent.Slots.Default.indexOf(parent.Slots.Default[last])
    if (idx !== -1) parent.Slots.Default.splice(idx, 1)
  }
}
