import { useState, useMemo } from 'react'
import { COMP_COLORS, COMP_ICONS, ELEMENT_LABELS, CHART_TYPES } from '../../utils/fragmentData'
import { makeDefaultElement } from '../../utils/fragmentData'

// A Config field like LabelKey is meant to be a plain string, but malformed/foreign JSON (or a
// bad Glean response) can put a whole nested object there instead. Rendering that object directly
// as JSX children throws "Objects are not valid as a React child" and crashes the whole canvas —
// this wraps every risky render site so a bad value degrades to the fallback instead of crashing.
function safeText(v, fallback = '') {
  return (v && typeof v === 'object') ? fallback : (v ?? fallback)
}

// Distinct Config.SectionName values across the whole tree — powers the "Segment" datalist
// so users can pick an existing segment or type a new one (mirrors Python's card.segment tagging).
export function collectSegments(node, out = new Set()) {
  if (!node || typeof node !== 'object') return out
  if (node.Config?.SectionName) out.add(node.Config.SectionName)
  if (node.Slots) {
    for (const arr of Object.values(node.Slots)) {
      if (Array.isArray(arr)) for (const child of arr) collectSegments(child, out)
    }
  }
  return out
}

// ── HoverBadge — floats a type label on hover ────────────────────────────────
function HoverBadge({ label, color }) {
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, zIndex: 20,
      backgroundColor: color, color: 'white',
      fontSize: 9, fontWeight: 700, padding: '1px 5px',
      borderRadius: '0 0 4px 0', pointerEvents: 'none', whiteSpace: 'nowrap',
    }}>
      {label}
    </div>
  )
}

// ── HtmlElementBody — leaf element content ────────────────────────────────────
function HtmlElementBody({ type, cfg, node }) {
  const input = node.Input || ''
  const s = (extra) => ({ padding: '4px 8px', ...extra })
  switch (type) {
    case 'key-value': case 'key-value-detail':
      return <div style={s({ display: 'flex', alignItems: 'baseline', gap: 6 })}><span style={{ fontSize: 10, color: '#64748B' }}>{safeText(cfg.LabelKey, 'Label')}</span><span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{safeText(input, '—')}</span></div>
    case 'button': case 'action-button': {
      const v = cfg.variant || 'primary'
      const [bg, fg] = v === 'secondary' ? ['#F1F5F9','#374151'] : v === 'danger' ? ['#FEE2E2','#991B1B'] : v === 'ghost' ? ['transparent','#374151'] : ['#1E3A8A','white']
      return <div style={s()}><span style={{ display: 'inline-block', padding: '4px 12px', borderRadius: 3, backgroundColor: bg, color: fg, fontSize: 10, fontWeight: 600 }}>{safeText(cfg.LabelKey, 'Button')}</span></div>
    }
    case 'text': case 'message':
      return <div style={s({ fontSize: 11, color: '#374151' })}>{safeText(cfg.LabelKey, 'Text')}</div>
    case 'pill':
      return <div style={s()}><span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 12, backgroundColor: '#E0F2FE', color: '#0369A1', fontSize: 10, fontWeight: 600 }}>{input || 'Status'}</span></div>
    case 'search':
      return <div style={s()}><div style={{ display: 'flex', gap: 4, border: '1px solid #CBD5E1', borderRadius: 3, padding: '3px 8px', backgroundColor: 'white' }}><span style={{ fontSize: 10, color: '#94A3B8' }}>🔍</span><span style={{ fontSize: 10, color: '#94A3B8' }}>{safeText(cfg.LabelKey, 'Search...')}</span></div></div>
    case 'input': case 'textarea':
      return <div style={s()}><div style={{ border: '1px solid #CBD5E1', borderRadius: 3, padding: '4px 8px', fontSize: 10, color: '#94A3B8', backgroundColor: 'white' }}>{safeText(cfg.LabelKey, 'Input...')}</div></div>
    case 'combobox': case 'dropdown':
      return <div style={s()}><div style={{ border: '1px solid #CBD5E1', borderRadius: 3, padding: '4px 8px', fontSize: 10, color: '#374151', backgroundColor: 'white', display: 'flex', justifyContent: 'space-between' }}><span>{safeText(cfg.LabelKey, 'Select...')}</span><span>▾</span></div></div>
    case 'banner': {
      const bc = { info: ['#EFF6FF','#1D4ED8'], warning: ['#FFFBEB','#92400E'], error: ['#FEF2F2','#991B1B'], success: ['#F0FDF4','#166534'] }
      const [bg, fg] = bc[cfg.type] || bc.info
      const icons = { info: 'ℹ️', warning: '⚠️', error: '❌', success: '✅' }
      return <div style={{ margin: '4px 8px', padding: '6px 10px', borderRadius: 4, backgroundColor: bg, color: fg, fontSize: 10, display: 'flex', alignItems: 'center', gap: 6 }}><span>{icons[cfg.type] || 'ℹ️'}</span>{safeText(cfg.LabelKey, 'Banner')}</div>
    }
    case 'link': case 'related-link':
      return <div style={s({ fontSize: 10, color: '#2563EB', textDecoration: 'underline', cursor: 'pointer' })}>{safeText(cfg.LabelKey || cfg.href, 'Link')}</div>
    case 'filter-panel': {
      const rawSections = (cfg.Attributes || node.Attributes || [])
      const attrs = rawSections.flatMap(g => g.filters || g.items || [g]).filter(f => f && (f.LabelKey || f.label || f.SectionName))
      const sections = attrs.length > 0 ? attrs : rawSections.length > 0 ? rawSections : null
      const renderSection = (f, i) => (
        <div key={i} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
            <span style={{ fontSize: 9, fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{safeText(f.LabelKey || f.label || f.SectionName, `Filter ${i + 1}`)}</span>
            <span style={{ fontSize: 9, color: '#6B7280' }}>Clear All</span>
          </div>
          <div style={{ height: 24, border: '1px solid #CBD5E1', borderRadius: 3, backgroundColor: 'white', display: 'flex', alignItems: 'center', padding: '0 6px' }}>
            <span style={{ fontSize: 9, color: '#9CA3AF' }}>{f.placeholder || f.InputField || 'Enter...'}</span>
          </div>
        </div>
      )
      return (
        <div style={{ padding: '6px 8px', minWidth: 160 }}>
          {sections
            ? sections.slice(0, 6).map(renderSection)
            : (
              <>
                {['Metric', 'Group By', 'Filter'].map((label, i) => (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                      <span style={{ fontSize: 9, fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
                      <span style={{ fontSize: 9, color: '#6B7280' }}>Clear All</span>
                    </div>
                    <div style={{ height: 24, border: '1px solid #CBD5E1', borderRadius: 3, backgroundColor: 'white', display: 'flex', alignItems: 'center', padding: '0 6px' }}>
                      <span style={{ fontSize: 9, color: '#9CA3AF' }}>Select...</span>
                    </div>
                  </div>
                ))}
              </>
            )
          }
        </div>
      )
    }
    default:
      return <div style={s({ fontSize: 10, color: '#94A3B8' })}>{safeText(input || cfg.LabelKey, type)}</div>
  }
}

// ── HtmlNodeRenderer — HTML-preview mode renderer (exported for AlignFix) ─────
export function HtmlNodeRenderer({ node, path = [], selectedPath = [], onSelect }) {
  const [hovered, setHovered] = useState(false)
  const [activeTab, setActiveTab] = useState(null)

  if (!node || typeof node !== 'object') return null

  const ctype = node.Container
  const etype = node.Element
  const type = ctype || etype
  const cfg = node.Config || {}
  const slots = node.Slots || {}
  const nodeCss = node.Style?.css || {}
  const color = COMP_COLORS[type] || '#94A3B8'
  const label = ELEMENT_LABELS[type] || type || '?'

  const isSelected = path.length > 0 && JSON.stringify(path) === JSON.stringify(selectedPath)
  const selOutline = isSelected ? { outline: '2px solid #3B82F6', outlineOffset: 1 }
    : hovered ? { outline: `1px dashed ${color}80`, outlineOffset: 1 } : {}

  const click = e => { e.stopPropagation(); onSelect?.(path) }
  const hover = { onMouseEnter: () => setHovered(true), onMouseLeave: () => setHovered(false) }

  // ── Leaf element ──────────────────────────────────────────────────────
  if (etype) {
    return (
      <div style={{ ...nodeCss, ...selOutline, position: 'relative', cursor: 'pointer', minHeight: 20, boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label={label} color={color} />}
        <HtmlElementBody type={etype} cfg={cfg} node={node} />
      </div>
    )
  }

  // ── Chart ─────────────────────────────────────────────────────────────
  if (CHART_TYPES.has(type) || type === 'chart') {
    const sm = cfg.dataMapping?.seriesMappings ?? cfg.seriesMappings ?? []
    const ct = cfg.highchartsOptions?.chart?.type || type
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 120, borderRadius: 4, backgroundColor: color + '12', border: `1px solid ${color}30`, ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label={label} color={color} />}
        <div style={{ fontSize: 28 }}>{COMP_ICONS[type] || '📊'}</div>
        <div style={{ fontSize: 11, fontWeight: 600, color }}>{cfg.title || ct}</div>
        {sm.length > 0 && <div style={{ fontSize: 9, color: '#94A3B8' }}>{sm.map(s => s.staticOptions?.name || 'Series').join(', ')}</div>}
        {node.Init?.DataSourcePath && <div style={{ fontSize: 9, color: '#CBD5E1', fontFamily: 'monospace' }}>{node.Init.DataSourcePath}</div>}
      </div>
    )
  }

  // ── Table ─────────────────────────────────────────────────────────────
  if (ctype === 'table') {
    const cols = cfg.Columns || []
    return (
      <div style={{ border: '1px solid #E2E8F0', borderRadius: 4, overflow: 'hidden', ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="table" color={color} />}
        {cfg.title && <div style={{ padding: '5px 10px', backgroundColor: '#1E3A8A', color: 'white', fontSize: 11, fontWeight: 600 }}>{cfg.title}</div>}
        <div style={{ display: 'flex', backgroundColor: '#F1F5F9', borderBottom: '1px solid #E2E8F0' }}>
          {cols.slice(0, 6).map((col, i) => (
            <div key={i} style={{ flex: 1, padding: '4px 8px', fontSize: 10, fontWeight: 600, color: '#374151', borderRight: '1px solid #E2E8F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {safeText(col.Config?.LabelKey, `Col ${i + 1}`)}
            </div>
          ))}
          {cols.length === 0 && <div style={{ padding: '4px 8px', fontSize: 10, color: '#94A3B8' }}>No columns</div>}
        </div>
        {[0, 1, 2].map(r => (
          <div key={r} style={{ display: 'flex', borderBottom: '1px solid #F1F5F9' }}>
            {(cols.length ? cols : Array(3).fill(null)).slice(0, 6).map((_, i) => (
              <div key={i} style={{ flex: 1, padding: '3px 8px', fontSize: 9, color: '#CBD5E1', borderRight: '1px solid #F8FAFC', fontFamily: 'monospace' }}>···</div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  // ── Tab-group ─────────────────────────────────────────────────────────
  if (ctype === 'tab-group') {
    const tabsDef = cfg.Tabs || []
    const slotKeys = Object.keys(slots)
    const orderedKeys = tabsDef.length > 0 ? tabsDef.map(t => t.Name).filter(n => slotKeys.includes(n)) : slotKeys
    const curTab = activeTab && slotKeys.includes(activeTab) ? activeTab : orderedKeys[0] || slotKeys[0] || ''
    return (
      <div style={{ border: '1px solid #E2E8F0', borderRadius: 4, display: 'flex', flexDirection: 'column', overflow: 'hidden', ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="tab-group" color={color} />}
        <div style={{ display: 'flex', borderBottom: '1px solid #E2E8F0', backgroundColor: '#F8FAFC', overflowX: 'auto', flexShrink: 0 }}>
          {orderedKeys.map(key => {
            const tDef = tabsDef.find(t => t.Name === key)
            // See getTabLabel in TabGroupPreview below for why this guards against LabelKey
            // being an object instead of a string — same crash, same fix, different component.
            const rawLabel = tDef?.LabelKey
            const tabLabel = (rawLabel && typeof rawLabel === 'object') ? key : (rawLabel || key)
            return (
              <button key={key}
                onClick={e => { e.stopPropagation(); setActiveTab(key) }}
                style={{ padding: '5px 14px', fontSize: 11, fontWeight: 500, border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', outline: 'none', borderBottom: curTab === key ? '2px solid #2563EB' : '2px solid transparent', backgroundColor: curTab === key ? 'white' : 'transparent', color: curTab === key ? '#1E3A8A' : '#64748B' }}>
                {tabLabel}
              </button>
            )
          })}
        </div>
        <div style={{ flex: 1, minHeight: 40 }}>
          {(slots[curTab] || []).map((child, i) => (
            <HtmlNodeRenderer key={i} node={child} path={[...path, 'Slots', curTab, i]} selectedPath={selectedPath} onSelect={onSelect} />
          ))}
        </div>
      </div>
    )
  }

  // ── Filter-panel ──────────────────────────────────────────────────────
  if (ctype === 'filter-panel') {
    const attrs = (node.Attributes || []).flatMap(g => g.filters || g.items || [])
    return (
      <div style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 4, padding: 8, ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="filter-panel" color={color} />}
        <div style={{ fontSize: 10, fontWeight: 700, color: '#374151', marginBottom: 6 }}>🔍 Filters</div>
        {attrs.slice(0, 5).map((f, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <div style={{ fontSize: 9, color: '#64748B', width: 60, flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{safeText(f.LabelKey || f.label, `Filter ${i + 1}`)}</div>
            <div style={{ flex: 1, height: 18, backgroundColor: 'white', border: '1px solid #CBD5E1', borderRadius: 3 }} />
          </div>
        ))}
        {attrs.length === 0 && <div style={{ fontSize: 9, color: '#94A3B8' }}>No filters configured</div>}
        {attrs.length > 5 && <div style={{ fontSize: 9, color: '#94A3B8' }}>+{attrs.length - 5} more</div>}
      </div>
    )
  }

  // ── Sidebar ───────────────────────────────────────────────────────────
  if (ctype === 'sidebar') {
    return (
      <div style={{ display: 'flex', flexDirection: 'row', flex: 1, minHeight: 0, ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="sidebar" color={color} />}
        {slots.Left?.length > 0 && <div style={{ flexShrink: 0 }}>{slots.Left.map((c, i) => <HtmlNodeRenderer key={i} node={c} path={[...path, 'Slots', 'Left', i]} selectedPath={selectedPath} onSelect={onSelect} />)}</div>}
        <div style={{ flex: 1, minWidth: 0 }}>{(slots.Default || []).map((c, i) => <HtmlNodeRenderer key={i} node={c} path={[...path, 'Slots', 'Default', i]} selectedPath={selectedPath} onSelect={onSelect} />)}</div>
        {slots.Right?.length > 0 && <div style={{ flexShrink: 0 }}>{slots.Right.map((c, i) => <HtmlNodeRenderer key={i} node={c} path={[...path, 'Slots', 'Right', i]} selectedPath={selectedPath} onSelect={onSelect} />)}</div>}
      </div>
    )
  }

  // ── Header-action ─────────────────────────────────────────────────────
  if (ctype === 'header-action') {
    const haBg = (nodeCss.background || '').startsWith('var(') ? '#F1F5F9' : (nodeCss.background || '#F1F5F9')
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', backgroundColor: haBg, ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="header-action" color={color} />}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{(slots.Left || []).map((c, i) => <HtmlNodeRenderer key={i} node={c} path={[...path, 'Slots', 'Left', i]} selectedPath={selectedPath} onSelect={onSelect} />)}</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{(slots.Right || []).map((c, i) => <HtmlNodeRenderer key={i} node={c} path={[...path, 'Slots', 'Right', i]} selectedPath={selectedPath} onSelect={onSelect} />)}</div>
      </div>
    )
  }

  // ── Flyout-card (collapsible left sidebar panel) ──────────────────────────
  if (ctype === 'flyout-card') {
    return (
      <div style={{ width: 220, flexShrink: 0, alignSelf: 'stretch', backgroundColor: 'white', borderRight: '1px solid #E2E8F0', overflow: 'auto', ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="flyout-card" color={color} />}
        {Object.entries(slots).map(([sk, children]) =>
          Array.isArray(children) ? children.map((c, i) => (
            <HtmlNodeRenderer key={`${sk}-${i}`} node={c} path={[...path, 'Slots', sk, i]} selectedPath={selectedPath} onSelect={onSelect} />
          )) : null
        )}
      </div>
    )
  }

  // ── Actions-popover (dropdown button) ─────────────────────────────────────
  if (ctype === 'actions-popover') {
    const hasChildren = Object.values(slots).some(s => Array.isArray(s) && s.length > 0)
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="actions-popover" color={color} />}
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', border: '1px solid #CBD5E1', borderRadius: 3, backgroundColor: 'white', fontSize: 11, fontWeight: 500, color: '#374151' }}>
          <span>{safeText(cfg.LabelKey, 'Actions')}</span>
          <span style={{ fontSize: 9, color: '#6B7280' }}>▾</span>
        </div>
        {hasChildren && (
          <div style={{ display: 'none' }}>
            {Object.entries(slots).map(([sk, children]) =>
              Array.isArray(children) ? children.map((c, i) => (
                <HtmlNodeRenderer key={`${sk}-${i}`} node={c} path={[...path, 'Slots', sk, i]} selectedPath={selectedPath} onSelect={onSelect} />
              )) : null
            )}
          </div>
        )}
      </div>
    )
  }

  // ── Segment-panel (segmented control — filter-backed or simple chips) ─────
  if (ctype === 'segment-panel') {
    const enableFilter = cfg.EnableFilter !== false
    const options = enableFilter
      ? (cfg.Filter?.StaticList || []).map(o => o.AttributeKey || o.Label || o.UID || '?')
      : (cfg.Segments || []).map(o => safeText(o.LabelKey || o.AttributeKey || o.Id, '?'))
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
        onClick={click} {...hover}>
        {hovered && <HoverBadge label="segment-panel" color={color} />}
        <div style={{ display: 'inline-flex', border: '1px solid #CBD5E1', borderRadius: '5rem', overflow: 'hidden', backgroundColor: 'white' }}>
          {options.length > 0 ? options.slice(0, 6).map((label, i) => (
            <span key={i} style={{ padding: '4px 12px', fontSize: 11, fontWeight: 500, color: i === 0 ? 'white' : '#374151', backgroundColor: i === 0 ? color : 'transparent', borderRight: i < options.length - 1 ? '1px solid #CBD5E1' : 'none' }}>
              {label}
            </span>
          )) : <span style={{ padding: '4px 12px', fontSize: 10, color: '#94A3B8' }}>No options configured</span>}
        </div>
      </div>
    )
  }

  // ── Generic container (flex / grid / card / section / etc.) ───────────────
  const defaultCss = {}
  if (ctype === 'flex') defaultCss.display = 'flex'
  if (ctype === 'grid') defaultCss.display = 'grid'
  if (ctype === 'card') { defaultCss.backgroundColor = 'white'; defaultCss.border = '1px solid #E2E8F0'; defaultCss.borderRadius = 4 }

  return (
    <div style={{ ...defaultCss, ...nodeCss, ...selOutline, cursor: 'pointer', position: 'relative', boxSizing: 'border-box' }}
      onClick={click} {...hover}>
      {hovered && <HoverBadge label={label} color={color} />}
      {cfg.title && ctype === 'card' && (
        <div style={{ padding: '5px 12px', borderBottom: '1px solid #F1F5F9', fontSize: 11, fontWeight: 600, color: '#1E3A8A' }}>{cfg.title}</div>
      )}
      {Object.entries(slots).map(([slotKey, children]) =>
        Array.isArray(children) ? children.map((c, i) => (
          <HtmlNodeRenderer key={`${slotKey}-${i}`} node={c} path={[...path, 'Slots', slotKey, i]} selectedPath={selectedPath} onSelect={onSelect} />
        )) : null
      )}
    </div>
  )
}

const SCREEN_SIZES = {
  'Desktop (1920)': { w: 1920, label: '🖥 1920' },
  'Desktop (1280)': { w: 1280, label: '🖥 1280' },
  'Tablet (768)':   { w: 768,  label: '📱 768' },
  'Mobile (390)':   { w: 390,  label: '📲 390' },
}

export default function FragmentCanvas({
  fragment, selectedPath, onSelect, onChange,
  screenSize = 'Desktop (1920)', onScreenSizeChange,
  canvasZoom = 1.0, onZoomChange,
  varPool = {},
}) {
  const [previewMode, setPreviewMode] = useState(false)
  const segmentOptions = useMemo(() => [...collectSegments(fragment)].sort(), [fragment])

  if (!fragment) {
    return (
      <div className="flex-1 flex flex-col">
        <CanvasToolbar screenSize={screenSize} onScreenSizeChange={onScreenSizeChange} canvasZoom={canvasZoom} onZoomChange={onZoomChange} previewMode={previewMode} onTogglePreview={() => setPreviewMode(m => !m)} />
        <div className="flex-1 flex items-center justify-center text-[#94A3B8] text-sm">
          No fragment loaded. Add elements from the palette or import JSON.
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <datalist id="segment-options">
        {segmentOptions.map(s => <option key={s} value={s} />)}
      </datalist>
      <CanvasToolbar screenSize={screenSize} onScreenSizeChange={onScreenSizeChange} canvasZoom={canvasZoom} onZoomChange={onZoomChange} previewMode={previewMode} onTogglePreview={() => setPreviewMode(m => !m)} />

      <div
        className={`flex-1 overflow-auto ${previewMode ? 'bg-[#E8EDF2]' : 'bg-[#F0F4F8] p-4'}`}
        onDrop={e => {
          if (previewMode) return
          e.preventDefault()
          const type = e.dataTransfer.getData('elementType')
          if (!type) return
          const newFrag = structuredClone(fragment)
          if (!newFrag.Slots) newFrag.Slots = { Default: [] }
          if (!newFrag.Slots.Default) newFrag.Slots.Default = []
          newFrag.Slots.Default.push(makeDefaultElement(type))
          onChange(newFrag)
        }}
        onDragOver={e => { if (!previewMode) e.preventDefault() }}
      >
        <div
          style={{
            transformOrigin: 'top left',
            transform: canvasZoom !== 1 ? `scale(${canvasZoom})` : undefined,
            width: canvasZoom !== 1 ? `${100 / canvasZoom}%` : undefined,
            maxWidth: SCREEN_SIZES[screenSize]?.w ? `${SCREEN_SIZES[screenSize].w}px` : undefined,
            ...(previewMode
              ? { backgroundColor: 'white', minHeight: 600, display: 'flex', flexDirection: 'column' }
              : {}),
          }}
        >
          {previewMode ? (
            <HtmlNodeRenderer
              node={fragment}
              path={[]}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ) : (
            <NodeRenderer
              node={fragment}
              path={[]}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onChange={newNode => onChange(newNode)}
              depth={0}
              varPool={varPool}
            />
          )}
        </div>
      </div>

      {/* Bottom breadcrumb */}
      <div className="border-t border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1 text-xs text-[#94A3B8] shrink-0 flex items-center gap-2">
        <span>Fragment › {fragment.Container || 'flex'} · {SCREEN_SIZES[screenSize]?.label || screenSize} · {Math.round(canvasZoom * 100)}%</span>
        {previewMode && <span className="text-[#F59E0B] font-semibold">● Preview Mode — click to select, drag-drop disabled</span>}
      </div>
    </div>
  )
}

function CanvasToolbar({ screenSize, onScreenSizeChange, canvasZoom, onZoomChange, previewMode, onTogglePreview }) {
  const sizes = Object.keys(SCREEN_SIZES)
  return (
    <div className="flex items-center gap-1 px-3 py-1.5 border-b border-[#E2E8F0] bg-white shrink-0 flex-wrap">
      {/* Screen size label */}
      <span className="text-xs text-[#94A3B8] font-semibold mr-1">Screen</span>
      <select
        value={screenSize}
        onChange={e => onScreenSizeChange?.(e.target.value)}
        className="text-xs border rounded px-1.5 py-0.5 focus:outline-none focus:border-[#2563EB] bg-white text-[#374151]"
      >
        {sizes.map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      {/* Device icon shortcuts */}
      <div className="flex gap-0.5 ml-1 border-l border-[#E2E8F0] pl-2">
        {[['Desktop (1920)','🖥'],['Tablet (768)','📱'],['Mobile (390)','📲']].map(([s, ico]) => (
          <button
            key={s}
            onClick={() => onScreenSizeChange?.(s)}
            title={s}
            className={`text-sm px-1.5 py-0.5 rounded hover:bg-[#F1F5F9] ${screenSize === s ? 'bg-[#DBEAFE]' : ''}`}
          >
            {ico}
          </button>
        ))}
      </div>

      {/* Zoom */}
      <div className="flex items-center gap-0.5 border-l border-[#E2E8F0] pl-2 ml-1">
        <button
          onClick={() => onZoomChange?.(Math.max(0.25, Math.round((canvasZoom - 0.25) * 100) / 100))}
          className="text-sm px-1.5 py-0.5 rounded hover:bg-[#F1F5F9] font-bold text-[#374151]"
        >−</button>
        <span className="text-xs font-bold text-[#374151] w-10 text-center">{Math.round(canvasZoom * 100)}%</span>
        <button
          onClick={() => onZoomChange?.(Math.min(2.0, Math.round((canvasZoom + 0.25) * 100) / 100))}
          className="text-sm px-1.5 py-0.5 rounded hover:bg-[#F1F5F9] font-bold text-[#374151]"
        >+</button>
        <button
          onClick={() => onZoomChange?.(1.0)}
          className="text-xs px-1.5 py-0.5 rounded hover:bg-[#F1F5F9] text-[#94A3B8]"
        >1:1</button>
      </div>

      {/* Preview mode toggle */}
      <div className="border-l border-[#E2E8F0] pl-2 ml-1">
        <button
          onClick={onTogglePreview}
          title={previewMode ? 'Switch to Schema view' : 'Switch to HTML Preview'}
          className={`text-xs px-2.5 py-0.5 rounded font-semibold transition-colors ${
            previewMode
              ? 'bg-[#F59E0B] text-[#1E293B] hover:bg-[#D97706]'
              : 'bg-[#1E293B] text-[#94A3B8] hover:bg-[#334155]'
          }`}
        >
          {previewMode ? '📐 Schema' : '🖥 Preview'}
        </button>
      </div>
    </div>
  )
}

function NodeRenderer({ node, path, selectedPath, onSelect, onChange, depth, varPool = {} }) {
  if (!node || typeof node !== 'object') return null

  const ctype = node.Container || null
  const etype = node.Element || null
  const type = ctype || etype
  const color = COMP_COLORS[type] || '#94A3B8'
  const icon = COMP_ICONS[type] || '□'
  const label = ELEMENT_LABELS[type] || type || 'node'

  const isSelected = JSON.stringify(path) === JSON.stringify(selectedPath)
  const isChart = CHART_TYPES.has(type) || type === 'chart'
  const isTable = ctype === 'table'
  const isTabGroup = ctype === 'tab-group'

  const slots = node.Slots || {}
  const slotKeys = Object.keys(slots)

  const handleSelect = e => {
    e.stopPropagation()
    onSelect(path)
  }

  const handleDrop = (e, slotKey) => {
    e.preventDefault()
    e.stopPropagation()
    const elType = e.dataTransfer.getData('elementType')
    if (!elType) return
    const newNode = structuredClone(node)
    if (!newNode.Slots) newNode.Slots = {}
    if (!newNode.Slots[slotKey]) newNode.Slots[slotKey] = []
    newNode.Slots[slotKey].push(makeDefaultElement(elType))
    onChange(newNode)
  }

  const moveChild = (slotKey, idx, dir) => {
    const newNode = structuredClone(node)
    const arr = newNode.Slots[slotKey]
    const target = idx + dir
    if (target < 0 || target >= arr.length) return
    ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
    onChange(newNode)
  }

  const deleteChild = (slotKey, idx) => {
    const newNode = structuredClone(node)
    newNode.Slots[slotKey].splice(idx, 1)
    onChange(newNode)
  }

  return (
    <div
      onClick={handleSelect}
      className={`rounded-lg border-2 transition-all cursor-pointer mb-2
        ${isSelected ? 'border-[#3B82F6] shadow-lg shadow-blue-100 bg-[#F8FAFC]' : 'border-[#E2E8F0] hover:border-[#CBD5E1] bg-white'}`}
      style={{ marginLeft: depth * 12, minWidth: 200 }}
    >
      {/* Header strip */}
      <div
        className="rounded-t flex items-center gap-2 px-3 py-1.5"
        style={{ backgroundColor: color + '20', borderBottom: `2px solid ${color}30` }}
      >
        <span className="w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold shrink-0" style={{ backgroundColor: color }}>
          {icon}
        </span>
        <span className="text-xs font-semibold" style={{ color }}>{label}</span>
        {node.Config?.title && <span className="text-xs text-[#64748B] ml-1 truncate">— {node.Config.title}</span>}
        {node.Config?.LabelKey && typeof node.Config.LabelKey !== 'object' && <span className="text-xs text-[#64748B] ml-1 truncate">— {node.Config.LabelKey}</span>}
        {node.Input && <span className="text-xs text-[#94A3B8] ml-auto font-mono truncate">{node.Input}</span>}
      </div>

      {/* ── Inline Editor for WYSIWYG configuration ── */}
      {isSelected && (
        <div className="bg-[#EFF6FF] border-b border-[#BFDBFE] p-2 flex flex-wrap gap-3 items-end" onClick={e => e.stopPropagation()}>
          {(node.Config?.title !== undefined || ctype) && (
            <div className="flex flex-col flex-1 min-w-[150px]">
              <label className="text-[9px] font-bold text-[#1E3A8A] mb-0.5 uppercase tracking-wider">Title / Label</label>
              <input value={node.Config?.title || node.Config?.LabelKey || ''} 
                onChange={e => {
                  const n = structuredClone(node)
                  if (!n.Config) n.Config = {}
                  if (ctype) n.Config.title = e.target.value; else n.Config.LabelKey = e.target.value
                  onChange(n)
                }} 
                placeholder={ctype ? 'Container Title' : 'Display Label'}
                className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs text-[#1E3A8A] font-semibold focus:border-[#2563EB] focus:ring-1 focus:ring-blue-200 outline-none shadow-inner" 
              />
            </div>
          )}

          {(isChart || isTable || type === 'metrics' || type === 'carousel') && (
            <div className="flex flex-col flex-1 min-w-[200px]">
              <label className="text-[9px] font-bold text-[#1E3A8A] mb-0.5 uppercase tracking-wider">Data Source Path</label>
              <div className="flex flex-col gap-1">
                {Object.keys(varPool).length > 0 && (
                  <select 
                    value={node.Init?.DataSourcePath || node.Config?.dataSourcePath || ''} 
                    onChange={e => {
                      const v = e.target.value; const n = structuredClone(node)
                      if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = v
                      if (!n.Config) n.Config = {}; n.Config.dataSourcePath = v
                      if (varPool[v] && !n.Config.backendVar) n.Config.backendVar = varPool[v]
                      onChange(n)
                    }} 
                    className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs bg-white text-[#1E3A8A] font-mono focus:border-[#2563EB] outline-none shadow-sm"
                  >
                    <option value="">-- select variable --</option>
                    {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                )}
                <input value={node.Init?.DataSourcePath || node.Config?.dataSourcePath || ''} 
                  onChange={e => {
                    const v = e.target.value; const n = structuredClone(node)
                    if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = v
                    if (!n.Config) n.Config = {}; n.Config.dataSourcePath = v
                    onChange(n)
                  }} 
                  className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs text-[#334155] font-mono focus:border-[#2563EB] outline-none shadow-inner" placeholder="DataSourcePath" 
                />
              </div>
            </div>
          )}

          {ctype && (
            <div className="flex flex-col flex-1 min-w-[160px]">
              <label className="text-[9px] font-bold text-[#1E3A8A] mb-0.5 uppercase tracking-wider">Segment</label>
              <input
                list="segment-options"
                value={node.Config?.SectionName || ''}
                onChange={e => {
                  const n = structuredClone(node)
                  if (!n.Config) n.Config = {}
                  if (e.target.value) n.Config.SectionName = e.target.value
                  else delete n.Config.SectionName
                  onChange(n)
                }}
                placeholder="Type new or pick existing…"
                className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs text-[#334155] focus:border-[#2563EB] outline-none shadow-inner"
              />
            </div>
          )}

          {etype && !isChart && type !== 'metrics' && (
            <div className="flex flex-col flex-1 min-w-[200px]">
              <label className="text-[9px] font-bold text-[#1E3A8A] mb-0.5 uppercase tracking-wider">Input Field</label>
              <div className="flex flex-col gap-1">
                {Object.keys(varPool).length > 0 && (
                  <select 
                    value={node.Input || ''} 
                    onChange={e => { const n = structuredClone(node); n.Input = e.target.value; onChange(n) }} 
                    className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs bg-white text-[#1E3A8A] font-mono focus:border-[#2563EB] outline-none shadow-sm"
                  >
                    <option value="">-- select variable --</option>
                    {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
                  </select>
                )}
                <input value={node.Input || ''} 
                  onChange={e => { const n = structuredClone(node); n.Input = e.target.value; onChange(n) }} 
                  className="w-full border border-[#BFDBFE] rounded px-2 py-1 text-xs text-[#334155] font-mono focus:border-[#2563EB] outline-none shadow-inner" placeholder="FIELD_NAME" 
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Chart visualization */}
      {isChart && (
        <ChartPreview node={node} type={type} color={color} icon={icon} label={label} />
      )}

      {/* Table visualization */}
      {isTable && (
        <TablePreview node={node} />
      )}

      {/* Tab-group with expand/collapse per slot */}
      {isTabGroup && (
        <TabGroupPreview
          node={node}
          path={path}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onChange={onChange}
          depth={depth}
        />
      )}

      {/* Metrics placeholder */}
      {type === 'metrics' && (
        <div className="px-3 py-3 flex gap-3 flex-wrap">
          {(node.Config?.metricsSpec || [{ label: 'Metric', field: 'FIELD' }]).map((m, i) => (
            <div key={i} className="bg-[#F1F5F9] rounded px-3 py-2 text-center min-w-20">
              <p className="text-xs text-[#64748B]">{m.label}</p>
              <p className="text-lg font-bold text-[#111827]">—</p>
              <p className="text-xs text-[#94A3B8]">{m.unit || ''}</p>
            </div>
          ))}
        </div>
      )}

      {/* Element body preview */}
      {etype && !isChart && <ElementPreview node={node} type={etype} />}

      {/* Slot children — skip chart/table/tab-group (handled above) */}
      {slotKeys.length > 0 && !isChart && !isTable && !isTabGroup && (
        <div className="p-2 space-y-1">
          {slotKeys.map(slotKey => (
            <SlotGroup
              key={slotKey}
              slotKey={slotKey}
              children={slots[slotKey] || []}
              parentPath={path}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onChildChange={(idx, newChild) => {
                const newNode = structuredClone(node)
                newNode.Slots[slotKey][idx] = newChild
                onChange(newNode)
              }}
              onMove={(idx, dir) => moveChild(slotKey, idx, dir)}
              onDelete={idx => deleteChild(slotKey, idx)}
              onDrop={e => handleDrop(e, slotKey)}
              depth={depth}
            />
          ))}
        </div>
      )}

      {/* No children — drop zone for containers */}
      {ctype && slotKeys.length === 0 && !isChart && (
        <div
          className="mx-2 mb-2 border-2 border-dashed border-[#CBD5E1] rounded p-3 text-center text-xs text-[#94A3B8] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
          onDrop={e => handleDrop(e, 'Default')}
          onDragOver={e => e.preventDefault()}
        >
          Drop elements here or click + in palette
        </div>
      )}
    </div>
  )
}

// ── Chart preview with series info ───────────────────────────────────────────
function ChartPreview({ node, type, color, icon, label }) {
  const cfg = node.Config || {}
  // Support both Python nested (dataMapping.seriesMappings) and flat (seriesMappings)
  const series = cfg.dataMapping?.seriesMappings ?? cfg.seriesMappings ?? []
  const dsPath = node.Init?.DataSourcePath || cfg.dataSourcePath || ''
  const chartSubType = cfg.highchartsOptions?.chart?.type || (type !== 'chart' ? type : '')
  const hcTitle = cfg.highchartsOptions?.title?.text || ''

  return (
    <div className="px-3 py-3" style={{ backgroundColor: color + '08' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="text-3xl">{icon}</div>
        <div>
          <p className="text-sm font-semibold" style={{ color }}>{hcTitle || label}{chartSubType ? ` (${chartSubType})` : ''}</p>
          <p className="text-xs text-[#94A3B8]">{dsPath || 'DataSourcePath not set'}</p>
        </div>
      </div>
      {/* Mini series list */}
      {series.length > 0 ? (
        <div className="mt-1 space-y-0.5">
          {series.map((s, i) => {
            const fm = s.fieldMappings || {}
            const opts = s.staticOptions || {}
            const yField = Object.keys(fm).find(k => fm[k] === 'y') || ''
            const xField = Object.keys(fm).find(k => fm[k] === 'name') || ''
            const serColor = opts.color || (i === 0 ? color : '#94A3B8')
            return (
              <div key={i} className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: serColor }} />
                <span className="text-[#374151]">{opts.name || `Series ${i + 1}`}</span>
                <span className="text-[#94A3B8] font-mono text-[10px]">{xField && yField ? `${xField} → ${yField}` : '(fields not set)'}</span>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-xs text-[#94A3B8] italic">No series configured — edit properties →</p>
      )}
    </div>
  )
}

// ── Table preview ─────────────────────────────────────────────────────────────
function TablePreview({ node }) {
  const cols = node.Config?.Columns || []
  return (
    <div className="px-3 py-3">
      <div className="rounded border border-[#E2E8F0] overflow-hidden">
        <div className="flex bg-[#F1F5F9]">
          {cols.slice(0, 6).map((col, ci) => (
            <div key={ci} className="flex-1 px-2 py-1 text-xs font-semibold text-[#374151] border-r border-[#E2E8F0] last:border-0 truncate">
              {safeText(col.Config?.LabelKey, `Col ${ci + 1}`)}
            </div>
          ))}
          {cols.length === 0 && <div className="px-2 py-1 text-xs text-[#94A3B8]">No columns — edit properties →</div>}
          {cols.length > 6 && <div className="px-2 py-1 text-xs text-[#94A3B8]">+{cols.length - 6} more</div>}
        </div>
        <div className="flex text-[#94A3B8]">
          {cols.slice(0, 6).map((_, ci) => (
            <div key={ci} className="flex-1 px-2 py-1 text-xs border-r border-[#F1F5F9] last:border-0 font-mono">
              {cols[ci]?.Config?.Sort?.SortBy || '…'}
            </div>
          ))}
        </div>
      </div>
      {node.Config?.dataSourcePath && (
        <p className="text-[10px] text-[#94A3B8] mt-1 font-mono">{node.Config.dataSourcePath}</p>
      )}
    </div>
  )
}

// ── Quick container templates for slot insertion ────────────────────────────
const SLOT_CONTAINER_TEMPLATES = {
  'flex-col':  { Container: 'flex', Style: { css: { flexDirection: 'column', gap: '16px', flex: '1', minHeight: '0' } }, Slots: { Default: [] } },
  'flex-row':  { Container: 'flex', Style: { css: { flexDirection: 'row', gap: '16px', flex: '1', overflow: 'hidden' } }, Slots: { Default: [] } },
  'card':      { Container: 'card', Config: { title: 'New Card' }, Style: {}, Slots: { Default: [] } },
  'section':   { Container: 'section', Config: { title: 'New Section' }, Style: {}, Slots: { Default: [] } },
  'grid':      { Container: 'grid', Style: { css: { flex: '1', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' } }, Slots: { Default: [] } },
  'header-action': { Container: 'header-action', Style: { padding: '10px' }, Slots: { Left: [], Right: [] } },
}

// ── Tab-group preview with per-slot expand/collapse, eject, and insert ────────
function TabGroupPreview({ node, path, selectedPath, onSelect, onChange, depth }) {
  const slots = node.Slots || {}
  const tabsDef = node.Config?.Tabs || []
  const slotKeys = Object.keys(slots)
  const orderedKeys = tabsDef.length > 0
    ? tabsDef.map(t => t.Name).filter(n => slotKeys.includes(n))
    : slotKeys

  const [activeTab, setActiveTab] = useState(orderedKeys[0] || slotKeys[0] || '')
  const [expandedSlots, setExpandedSlots] = useState({})
  const [insertPickerSlot, setInsertPickerSlot] = useState(null) // slot name being picked for

  const toggleSlot = (key, e) => {
    e.stopPropagation()
    setExpandedSlots(s => ({ ...s, [key]: !s[key] }))
  }

  const ejectSlot = (key, e) => {
    e.stopPropagation()
    if (!window.confirm(`Eject all content from slot "${key}"? Slot will become empty.`)) return
    const newNode = structuredClone(node)
    newNode.Slots[key] = []
    onChange(newNode)
  }

  const insertContainerIntoSlot = (slotKey, templateKey) => {
    const tpl = SLOT_CONTAINER_TEMPLATES[templateKey]
    if (!tpl) return
    const newNode = structuredClone(node)
    if (!newNode.Slots[slotKey]) newNode.Slots[slotKey] = []
    newNode.Slots[slotKey].push(JSON.parse(JSON.stringify(tpl)))
    onChange(newNode)
    setInsertPickerSlot(null)
    setExpandedSlots(s => ({ ...s, [slotKey]: true }))
    setActiveTab(slotKey)
  }

  const getTabLabel = key => {
    const def = tabsDef.find(t => t.Name === key)
    // A tab's LabelKey is meant to be a plain string, but malformed/foreign JSON can put a whole
    // nested object there instead — rendering that directly as JSX children crashes the canvas
    // with "Objects are not valid as a React child", taking down the whole editor with it.
    const label = def?.LabelKey
    return (label && typeof label === 'object') ? key : (label || key)
  }

  const children = slots[activeTab] || []

  const moveChild = (idx, dir) => {
    const newNode = structuredClone(node)
    const arr = newNode.Slots[activeTab]
    const target = idx + dir
    if (target < 0 || target >= arr.length) return
    ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
    onChange(newNode)
  }

  const deleteChild = idx => {
    const newNode = structuredClone(node)
    newNode.Slots[activeTab].splice(idx, 1)
    onChange(newNode)
  }

  const handleChildChange = (idx, newChild) => {
    const newNode = structuredClone(node)
    newNode.Slots[activeTab][idx] = newChild
    onChange(newNode)
  }

  const handleDrop = (e, slotKey) => {
    e.preventDefault()
    e.stopPropagation()
    const elType = e.dataTransfer.getData('elementType')
    if (!elType) return
    const newNode = structuredClone(node)
    if (!newNode.Slots[slotKey]) newNode.Slots[slotKey] = []
    newNode.Slots[slotKey].push(makeDefaultElement(elType))
    onChange(newNode)
  }

  if (orderedKeys.length === 0) {
    return (
      <div className="px-3 py-2 text-xs text-[#94A3B8] italic">
        No slots — add Tabs in Properties panel and create matching Slot keys.
      </div>
    )
  }

  const allKeys = [...orderedKeys, ...slotKeys.filter(k => !orderedKeys.includes(k))]

  return (
    <div onClick={e => e.stopPropagation()}>
      {/* Insert container picker dropdown */}
      {insertPickerSlot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={e => { e.stopPropagation(); setInsertPickerSlot(null) }}>
          <div className="bg-white rounded-lg shadow-xl w-64 p-4 space-y-2"
            onClick={e => e.stopPropagation()}>
            <p className="text-xs font-bold text-[#1E3A8A]">Insert container into "{insertPickerSlot}"</p>
            {Object.keys(SLOT_CONTAINER_TEMPLATES).map(k => (
              <button key={k}
                onClick={() => insertContainerIntoSlot(insertPickerSlot, k)}
                className="w-full text-left px-3 py-1.5 text-xs rounded hover:bg-[#DBEAFE] text-[#374151] font-mono">
                {k}
              </button>
            ))}
            <button onClick={() => setInsertPickerSlot(null)}
              className="w-full text-center px-3 py-1 text-xs rounded bg-[#F1F5F9] text-[#374151] mt-1">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Tab header row */}
      <div className="flex border-b border-[#E2E8F0] bg-[#F8FAFC] overflow-x-auto">
        {allKeys.map(key => {
          const isOrdered = orderedKeys.includes(key)
          const isActive = activeTab === key
          return (
            <div key={key} className="flex items-center shrink-0 border-r border-[#F1F5F9]">
              {/* Tab label button */}
              <button
                onClick={e => { e.stopPropagation(); setActiveTab(key) }}
                className={`px-2 py-1.5 text-xs font-medium transition-colors whitespace-nowrap
                  ${isActive
                    ? isOrdered ? 'bg-white border-b-2 border-[#2563EB] text-[#1E3A8A]' : 'bg-white border-b-2 border-[#9333EA] text-[#6B21A8]'
                    : 'text-[#64748B] hover:bg-white'}`}
              >
                {getTabLabel(key)}
                <span className="ml-1 text-[10px] text-[#94A3B8]">({(slots[key] || []).length})</span>
              </button>

              {/* Expand/collapse */}
              <button
                onClick={e => toggleSlot(key, e)}
                className="px-1 py-1.5 text-[10px] text-[#94A3B8] hover:text-[#374151]"
                title={expandedSlots[key] ? 'Collapse slot' : 'Expand slot'}
              >
                {expandedSlots[key] ? '⬢' : '⬡'}
              </button>

              {/* Assign new container */}
              <button
                onClick={e => { e.stopPropagation(); setInsertPickerSlot(key) }}
                className="px-1 py-1.5 text-[10px] text-[#059669] hover:text-[#047857]"
                title={`Insert container into slot "${key}"`}
              >
                ➕
              </button>

              {/* Eject (clear slot) */}
              {(slots[key] || []).length > 0 && (
                <button
                  onClick={e => ejectSlot(key, e)}
                  className="px-1 py-1.5 text-[10px] text-[#DC2626] hover:text-[#991B1B]"
                  title={`Eject — clear all content from slot "${key}"`}
                >
                  ⊗
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Active tab content — expanded inline */}
      {expandedSlots[activeTab] ? (
        <div
          className="p-2 space-y-1 min-h-8 bg-[#FAFBFC]"
          onDrop={e => handleDrop(e, activeTab)}
          onDragOver={e => e.preventDefault()}
        >
          {children.map((child, i) => (
            <div key={i} className="flex items-start gap-1">
              <div className="flex-1 min-w-0">
                <NodeRenderer
                  node={child}
                  path={[...path, 'Slots', activeTab, i]}
                  selectedPath={selectedPath}
                  onSelect={onSelect}
                  onChange={newChild => handleChildChange(i, newChild)}
                  depth={depth + 1}
                />
              </div>
              <div className="flex flex-col gap-0.5 shrink-0 mt-2">
                <button onClick={() => moveChild(i, -1)} className="text-[#94A3B8] hover:text-[#374151] text-xs">▲</button>
                <button onClick={() => moveChild(i, 1)} className="text-[#94A3B8] hover:text-[#374151] text-xs">▼</button>
                <button onClick={() => deleteChild(i)} className="text-red-300 hover:text-red-500 text-xs">✕</button>
              </div>
            </div>
          ))}
          {children.length === 0 && (
            <div className="text-center py-3">
              <p className="text-xs text-[#CBD5E1]">Empty slot — drop elements or use ➕ to insert a container</p>
            </div>
          )}
        </div>
      ) : (
        <div className="px-3 py-2 text-xs text-[#94A3B8]">
          {children.length > 0
            ? `${children.length} element(s) — click ⬡ to expand`
            : 'Empty slot — click ➕ to insert container or ⬡ to expand for drop'}
        </div>
      )}
    </div>
  )
}

function SlotGroup({ slotKey, children, parentPath, selectedPath, onSelect, onChildChange, onMove, onDelete, onDrop, depth }) {
  return (
    <div>
      {slotKey !== 'Default' && (
        <p className="text-xs text-[#94A3B8] font-semibold mb-1 px-1">{slotKey}</p>
      )}
      <div
        className="min-h-8 rounded border border-dashed border-[#E2E8F0] p-1 space-y-1"
        onDrop={onDrop}
        onDragOver={e => e.preventDefault()}
      >
        {children.map((child, i) => (
          <div key={i} className="flex items-start gap-1">
            <div className="flex-1 min-w-0">
              <NodeRenderer
                node={child}
                path={[...parentPath, 'Slots', slotKey, i]}
                selectedPath={selectedPath}
                onSelect={onSelect}
                onChange={newChild => onChildChange(i, newChild)}
                depth={depth + 1}
              />
            </div>
            <div className="flex flex-col gap-0.5 shrink-0 mt-2">
              <button onClick={() => onMove(i, -1)} className="text-[#94A3B8] hover:text-[#374151] text-xs leading-none" title="Move up">▲</button>
              <button onClick={() => onMove(i, 1)} className="text-[#94A3B8] hover:text-[#374151] text-xs leading-none" title="Move down">▼</button>
              <button onClick={() => onDelete(i)} className="text-red-300 hover:text-red-500 text-xs leading-none" title="Delete">✕</button>
            </div>
          </div>
        ))}
        {children.length === 0 && (
          <p className="text-xs text-[#CBD5E1] p-1">Empty — drop or add from palette</p>
        )}
      </div>
    </div>
  )
}

function ElementPreview({ node, type }) {
  const cfg = node.Config || {}
  const input = node.Input || ''

  switch (type) {
    case 'key-value':
    case 'key-value-detail':
      return (
        <div className="px-3 py-2 flex gap-3">
          <span className="text-xs text-[#64748B]">{safeText(cfg.LabelKey, 'Label')}</span>
          <span className="text-xs font-medium text-[#111827]">{input || '—'}</span>
        </div>
      )
    case 'button':
    case 'action-button': {
      const variant = cfg.variant || 'primary'
      const varBg = variant === 'secondary' ? '#F1F5F9' : variant === 'danger' ? '#FEE2E2' : variant === 'ghost' ? 'transparent' : '#1E3A8A'
      const varFg = variant === 'secondary' ? '#374151' : variant === 'danger' ? '#991B1B' : variant === 'ghost' ? '#374151' : 'white'
      return (
        <div className="px-3 py-2">
          <span className="inline-block px-3 py-1 rounded text-xs font-medium border" style={{ backgroundColor: varBg, color: varFg }}>
            {safeText(cfg.LabelKey, 'Button')}
          </span>
        </div>
      )
    }
    case 'text':
    case 'message':
      return <div className="px-3 py-2 text-sm text-[#374151]">{safeText(cfg.LabelKey, 'Text')}</div>
    case 'pill':
      return (
        <div className="px-3 py-2">
          <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-[#E0F2FE] text-[#0369A1]">
            {input || 'Status'}
          </span>
        </div>
      )
    case 'banner': {
      const bannerColors = { info: ['#EFF6FF', '#1D4ED8'], warning: ['#FFFBEB', '#92400E'], error: ['#FEF2F2', '#991B1B'], success: ['#F0FDF4', '#166534'] }
      const [bg, fg] = bannerColors[cfg.type] || bannerColors.info
      const icons = { info: 'ℹ️', warning: '⚠️', error: '❌', success: '✅' }
      return (
        <div className="px-3 py-2 mx-2 mb-1 rounded flex items-center gap-2" style={{ backgroundColor: bg, color: fg }}>
          <span>{icons[cfg.type] || 'ℹ️'}</span>
          <span className="text-xs">{safeText(cfg.LabelKey, 'Banner message')}</span>
        </div>
      )
    }
    case 'progress-bar':
      return (
        <div className="px-3 py-2">
          <p className="text-xs text-[#64748B] mb-1">{safeText(cfg.LabelKey, 'Progress')}</p>
          <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-[#EA580C] rounded-full" />
          </div>
        </div>
      )
    case 'input':
    case 'textarea':
      return (
        <div className="px-3 py-2">
          <input type="text" disabled placeholder={cfg.LabelKey || 'Input'} className="w-full border rounded px-2 py-1 text-xs bg-[#F8FAFC]" />
        </div>
      )
    case 'combobox':
    case 'dropdown':
      return (
        <div className="px-3 py-2">
          <select disabled className="w-full border rounded px-2 py-1 text-xs bg-[#F8FAFC]">
            <option>{safeText(cfg.LabelKey, 'Select...')}</option>
          </select>
        </div>
      )
    case 'link':
    case 'related-link':
      return (
        <div className="px-3 py-2 text-xs text-[#2563EB] underline cursor-pointer">
          {safeText(cfg.LabelKey || cfg.href, 'Link')}
        </div>
      )
    case 'search':
      return (
        <div className="px-3 py-2">
          <div className="flex gap-1 border rounded px-2 py-1 bg-[#F8FAFC]">
            <span className="text-xs text-[#94A3B8]">🔍</span>
            <input type="text" disabled placeholder={cfg.LabelKey || 'Search...'} className="flex-1 text-xs bg-transparent outline-none" />
          </div>
        </div>
      )
    case 'segment-panel': {
      const segs = cfg.Segments || []
      return (
        <div className="px-3 py-2 flex gap-1 flex-wrap">
          {segs.slice(0, 4).map((s, i) => (
            <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-[#F1F5F9] text-[#374151]">{s.AttributeKey || s.label || `Seg ${i + 1}`}</span>
          ))}
          {segs.length === 0 && <span className="text-xs text-[#94A3B8] italic">No segments</span>}
        </div>
      )
    }
    default:
      return (
        <div className="px-3 py-2 text-xs text-[#94A3B8]">
          {safeText(input || cfg.LabelKey, type)}
        </div>
      )
  }
}
