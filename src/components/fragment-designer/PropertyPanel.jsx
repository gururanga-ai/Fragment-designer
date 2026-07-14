import { useState } from 'react'
import { ELEMENT_LABELS, COMP_COLORS, COMP_ICONS } from '../../utils/fragmentData'
import JsonEditor from '../shared/JsonEditor'
import Modal from '../shared/Modal'
import { SlotFilterEditor } from './FilterPanel'

// ── ELEM_SCHEMAS — mirrors Python ELEM_SCHEMAS ──────────────────────────────
const ELEM_SCHEMAS = {
  'tab-group': {
    desc: 'Tabbed interface. Each tab Name must match a Slot key in the JSON.',
    cfg: [
      { key: 'preserveContent', label: 'Preserve Tab Content', type: 'bool', desc: 'Keep tab DOM alive when switching' },
      { key: 'SelectedTabName', label: 'Default Active Tab', type: 'str', desc: 'Name of the tab shown on first load' },
      { key: 'Personalizable', label: 'Allow Personalization', type: 'bool', desc: 'Let users reorder/hide tabs' },
      { key: '__onoentab_source', label: 'OnOpenTab → SourceContainerId', type: 'str', desc: 'ContainerId that emits the open-tab event' },
      { key: '__onoentab_event', label: 'OnOpenTab → EventId', type: 'str', desc: 'EventId that triggers tab switching' },
    ],
    arr: { key: 'Tabs', label: 'Tabs — one row per tab', cols: [
      { key: 'Name', label: 'Slot Name (matches JSON Slot key)', width: 180 },
      { key: 'LabelKey', label: 'Display Label / i18n Key', width: 200 },
      { key: 'UID', label: 'UID (required for personalization)', width: 130 },
    ]},
    sty: [
      { key: 'tabHeader.borderColor', label: 'Header Border Color', type: 'str' },
      { key: 'tabHeader.hoverBorderColor', label: 'Hover Border Color', type: 'str' },
      { key: 'tabHeader.hoverTextColor', label: 'Hover Text Color', type: 'str' },
      { key: 'tabAlignment', label: 'Tab Alignment', type: 'enum', options: ['start', 'center', 'end'] },
    ],
  },
  'sticky-header': {
    desc: 'Container that remains fixed at the top during scrolling.',
    cfg: [
      { key: 'title', label: 'Title (ARIA)', type: 'str' },
      { key: 'showDivider', label: 'Show Bottom Divider', type: 'bool' },
    ],
    sty: [
      { key: 'css.backgroundColor', label: 'Background Color', type: 'str' },
      { key: 'css.zIndex', label: 'Z-Index', type: 'int' },
    ],
  },
  'card': {
    desc: 'White card container with header, body and footer slots.',
    cfg: [
      { key: 'title', label: 'Card Title', type: 'str', desc: 'Text shown in the card header bar' },
      { key: 'direction', label: 'Content Direction', type: 'enum', options: ['row', 'column'] },
    ],
    sty: [
      { key: 'css.border', label: 'Border', type: 'str' },
      { key: 'css.borderRadius', label: 'Border Radius', type: 'str' },
      { key: 'css.backgroundColor', label: 'Background', type: 'str' },
      { key: 'css.minHeight', label: 'Min Height', type: 'str' },
    ],
  },
  'banner': {
    desc: 'Notification banner bar. Type controls colour and icon automatically.',
    cfg: [
      { key: 'type', label: 'Banner Type', type: 'enum', options: ['info', 'warning', 'error', 'success'] },
      { key: 'LabelKey', label: 'Message Text', type: 'str' },
    ],
  },
  'accordion': { desc: 'Collapsible sections list.', cfg: [{ key: 'title', label: 'Section Title', type: 'str' }] },
  'expandable': { desc: 'Single collapsible section.', cfg: [{ key: 'title', label: 'Section Title', type: 'str' }] },
  'form': { desc: 'Reactive Angular form wrapper.', cfg: [{ key: 'formId', label: 'Form ID', type: 'str' }] },
  'section': { desc: 'Content section with a title divider line.', cfg: [{ key: 'title', label: 'Section Title', type: 'str' }] },
  'segment-panel': {
    desc: 'Segmented control — simple chips or filter quick-select.',
    cfg: [
      { key: 'EnableSegmentPanel', label: 'Enable Segment Panel', type: 'bool' },
      { key: 'EnableFilter', label: 'Enable Filter Mode', type: 'bool' },
      { key: 'Name', label: 'Filter Attr Name', type: 'str', desc: 'e.g. DATE_RANGE' },
      { key: 'SectionName', label: 'Section Name', type: 'str', desc: 'e.g. Filters' },
      { key: 'Type', label: 'Data Type', type: 'str', desc: 'e.g. string' },
      { key: '__filter_type', label: 'Filter Type', type: 'enum', options: ['Singleselect', 'Multiselect'] },
      { key: '__placeholder_label', label: 'Placeholder Label', type: 'str', desc: "e.g. 'Time Range:'" },
      { key: '__entity_key', label: 'Entity Key Field', type: 'str', desc: 'e.g. AttributeKey' },
      { key: '__entity_value', label: 'Entity Value Field', type: 'str', desc: 'e.g. AttributeValue' },
    ],
    arr: { key: 'Segments', label: 'StaticList — one row per option', cols: [
      { key: 'AttributeKey', label: 'Label (AttributeKey)', width: 200 },
      { key: 'UID', label: 'UID', width: 150 },
      { key: 'AttributeValue', label: 'Value (AttributeValue)', width: 200 },
    ]},
  },
  'button': {
    desc: 'Action button. Configure Events.OnClick for show/hide of containers.',
    cfg: [
      { key: 'LabelKey', label: 'Button Label', type: 'str' },
      { key: 'prefixName', label: 'Icon Prefix (opt.)', type: 'str', desc: 'e.g. far-filter' },
      { key: 'actionKey', label: 'Action Key (opt.)', type: 'str' },
      { key: 'variant', label: 'Variant', type: 'enum', options: ['', 'primary', 'secondary', 'tertiary', 'danger', 'ghost'] },
      { key: '__onclick_container', label: 'OnClick → ContainerId', type: 'str', desc: 'ContainerId targeted by OnClick' },
      { key: '__onclick_event', label: 'OnClick → EventId', type: 'str', desc: 'EventId sent on click' },
    ],
  },
  'actions-popover': {
    desc: 'Popover menu of actions (Export CSV, XLSX, etc.).',
    cfg: [
      { key: 'LabelKey', label: 'Button Label', type: 'str' },
      { key: 'icon', label: 'Chevron Icon', type: 'str', desc: 'e.g. far-chevron-down' },
    ],
  },
  'button-icon': {
    desc: 'Icon-only circular button for inline actions.',
    cfg: [{ key: 'icon', label: 'Icon Name', type: 'str', desc: 'e.g. edit delete search' }, { key: 'actionKey', label: 'Action Key', type: 'str' }],
  },
  'action-button': {
    desc: 'Button bound to a complex river action workflow.',
    cfg: [
      { key: 'LabelKey', label: 'Button Label', type: 'str' },
      { key: 'actionKey', label: 'Action Key', type: 'str' },
      { key: 'variant', label: 'Variant', type: 'enum', options: ['primary', 'secondary', 'tertiary'] },
    ],
  },
  'link': {
    desc: 'Navigation link.',
    cfg: [{ key: 'LabelKey', label: 'Link Text', type: 'str' }, { key: 'href', label: 'URL / Route', type: 'str' }],
  },
  'related-link': { desc: 'Contextual link to a related entity.', cfg: [{ key: 'LabelKey', label: 'Link Text', type: 'str' }] },
  'input': {
    desc: 'Single-line text input.',
    cfg: [
      { key: 'LabelKey', label: 'Field Label', type: 'str' },
      { key: 'name', label: 'Form Name', type: 'str' },
      { key: 'type', label: 'Input Type', type: 'enum', options: ['text', 'email', 'password', 'number', 'tel'] },
      { key: 'required', label: 'Required', type: 'bool' },
    ],
  },
  'textarea': { desc: 'Multi-line text area.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }, { key: 'required', label: 'Required', type: 'bool' }] },
  'combobox': { desc: 'Searchable dropdown.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'dropdown': { desc: 'Select list.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'checkbox': { desc: 'Boolean toggle.', cfg: [{ key: 'LabelKey', label: 'Checkbox Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'date-select': { desc: 'Calendar date picker.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'numeric-stepper': { desc: 'Increment/decrement number.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'currency-input': { desc: 'Monetary input.', cfg: [{ key: 'LabelKey', label: 'Field Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }, { key: 'locale', label: 'Locale', type: 'str', desc: 'e.g. en-US' }] },
  'toggle-button': { desc: 'On/off switch.', cfg: [{ key: 'LabelKey', label: 'Toggle Label', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'search': { desc: 'Search box with debounce.', cfg: [{ key: 'LabelKey', label: 'Placeholder Text', type: 'str' }, { key: 'name', label: 'Form Name', type: 'str' }] },
  'quick-filter': {
    desc: 'Preset filter chips.',
    arr: { key: 'Segments', label: 'Filter Chips', cols: [{ key: 'LabelKey', label: 'Chip Label / i18n Key', width: 220 }, { key: 'Id', label: 'Filter ID', width: 160 }] },
  },
  'filter-panel': { desc: 'Advanced filter panel.' },
  'text': {
    desc: 'Static or localized text display.',
    cfg: [{ key: 'LabelKey', label: 'Text Content', type: 'str' }],
    sty: [
      { key: 'color', label: 'Text Color', type: 'str' },
      { key: 'fontSize', label: 'Font Size', type: 'str' },
      { key: 'fontWeight', label: 'Font Weight', type: 'enum', options: ['normal', 'bold', '600', '700'] },
    ],
  },
  'key-value': {
    desc: 'Labeled data pair.',
    cfg: [
      { key: 'LabelKey', label: 'Label Text', type: 'str' },
      { key: 'AttributeType', label: 'Attribute Type', type: 'enum', options: ['string', 'number', 'date', 'currency'] },
    ],
  },
  'key-value-detail': {
    desc: 'Key-value with collapsible detail panel.',
    cfg: [
      { key: 'LabelKey', label: 'Label Text', type: 'str' },
      { key: 'AttributeType', label: 'Attribute Type', type: 'enum', options: ['string', 'number', 'date', 'currency'] },
    ],
  },
  'pill': { desc: 'Colored badge/tag.', sty: [{ key: 'pillBackgroundColor', label: 'Background Color', type: 'str' }, { key: 'pillTextColor', label: 'Text Color', type: 'str' }] },
  'value': { desc: 'Displays a raw field value. Set Input = field path.' },
  'value-unit': { desc: 'Shows a numeric value with a unit label.', cfg: [{ key: 'unit', label: 'Unit Label', type: 'str', desc: 'e.g. kg ms % items' }] },
  'progress-bar': { desc: 'Visual progress bar (0–100).', cfg: [{ key: 'LabelKey', label: 'Label', type: 'str' }] },
  'currency-format': { desc: 'Formats a numeric field as locale currency.', cfg: [{ key: 'locale', label: 'Locale', type: 'str', desc: 'e.g. en-US de-DE' }] },
  'icon': { desc: 'Visual icon from the MAWC icon library.', cfg: [{ key: 'icon', label: 'Icon Name', type: 'str', desc: 'e.g. info warning edit delete' }] },
  'message': { desc: 'Informational message block.', cfg: [{ key: 'LabelKey', label: 'Message Text', type: 'str' }] },
  'list': { desc: 'Iterates over array data, rendering a slot template per item.' },
  'carousel': {
    desc: 'Scrollable carousel of repeating items.',
    cfg: [
      { key: 'slidesPerPage', label: 'Slides Per Page', type: 'int', desc: 'Number of slides visible at once' },
      { key: 'slidesPerMove', label: 'Slides Per Move', type: 'int', desc: 'Number of slides to advance per click' },
      { key: 'navigation', label: 'Show Nav Arrows', type: 'bool' },
      { key: 'pagination', label: 'Show Pagination Dots', type: 'bool' },
      { key: 'loop', label: 'Loop', type: 'bool' },
      { key: 'autoplay', label: 'Autoplay', type: 'bool' },
      { key: 'autoplayInterval', label: 'Autoplay Interval (ms)', type: 'int' },
      { key: 'orientation', label: 'Orientation', type: 'enum', options: ['horizontal', 'vertical'] },
      { key: 'dataSourcePath', label: 'Data Source Path', type: 'str' },
    ],
    sty: [
      { key: 'width', label: 'Width', type: 'str' },
      { key: 'slideGap', label: 'Slide Gap', type: 'str' },
      { key: 'css.borderRadius', label: 'Border Radius', type: 'str' },
      { key: 'css.backgroundColor', label: 'Background Color', type: 'str' },
      { key: 'css.padding', label: 'Padding', type: 'str' },
    ],
  },
  'stack': { desc: 'Vertical or horizontal stack.', sty: [{ key: 'direction', label: 'Stack Direction', type: 'enum', options: ['vertical', 'horizontal'] }] },
  'flex': {
    desc: 'CSS flexbox container.',
    sty: [
      { key: 'css.flexDirection', label: 'Flex Direction', type: 'enum', options: ['row', 'column', 'row-reverse', 'column-reverse'] },
      { key: 'css.gap', label: 'Gap', type: 'str' },
      { key: 'css.justifyContent', label: 'Justify Content', type: 'enum', options: ['flex-start', 'center', 'flex-end', 'space-between', 'space-around'] },
      { key: 'css.alignItems', label: 'Align Items', type: 'enum', options: ['flex-start', 'center', 'flex-end', 'stretch'] },
      { key: 'css.flexWrap', label: 'Flex Wrap', type: 'enum', options: ['nowrap', 'wrap', 'wrap-reverse'] },
    ],
  },
  'grid': {
    desc: 'CSS grid container.',
    sty: [
      { key: 'css.gridTemplateColumns', label: 'Template Columns', type: 'str', desc: "e.g. 1fr 1fr or repeat(3,1fr)" },
      { key: 'css.gap', label: 'Gap', type: 'str' },
      { key: 'css.gridAutoRows', label: 'Auto Row Height', type: 'str' },
    ],
  },
}

const CHART_TYPES = new Set(['pie','bar','line','column','spline','area','areaspline','scatter','sunburst','waterfall','chart'])

// ── Virtual field helpers for OnOpenTab / OnClick ─────────────────────────
function getVirtualField(node, key) {
  if (key === '__onoentab_source') return node?.Config?.OnOpenTab?.SourceContainerId || ''
  if (key === '__onoentab_event') return node?.Config?.OnOpenTab?.EventId || ''
  if (key === '__onclick_container') {
    try { return node?.Events?.Triggers?.OnClick?.[0]?.ContainerId || '' } catch { return '' }
  }
  if (key === '__onclick_event') {
    try { return node?.Events?.Triggers?.OnClick?.[0]?.EventId || '' } catch { return '' }
  }
  if (key === '__filter_type') {
    return node?.Config?.Filter?.Type || ''
  }
  if (key === '__placeholder_label') {
    return node?.Config?.Filter?.Placeholder?.LabelKey || ''
  }
  if (key === '__entity_key') {
    return node?.Config?.Filter?.EntityKey || ''
  }
  if (key === '__entity_value') {
    return node?.Config?.Filter?.EntityValue || ''
  }
  return ''
}

function setVirtualField(node, key, val) {
  const n = structuredClone(node)
  if (key === '__onoentab_source') {
    n.Config = n.Config || {}
    n.Config.OnOpenTab = { ...(n.Config.OnOpenTab || {}), SourceContainerId: val }
  } else if (key === '__onoentab_event') {
    n.Config = n.Config || {}
    n.Config.OnOpenTab = { ...(n.Config.OnOpenTab || {}), EventId: val }
  } else if (key === '__onclick_container') {
    n.Events = n.Events || {}
    n.Events.Triggers = n.Events.Triggers || {}
    const existing = n.Events.Triggers.OnClick?.[0] || {}
    n.Events.Triggers.OnClick = [{ ...existing, ContainerId: val }]
  } else if (key === '__onclick_event') {
    n.Events = n.Events || {}
    n.Events.Triggers = n.Events.Triggers || {}
    const existing = n.Events.Triggers.OnClick?.[0] || {}
    n.Events.Triggers.OnClick = [{ ...existing, EventId: val }]
  } else if (key === '__filter_type') {
    n.Config = n.Config || {}
    n.Config.Filter = { ...(n.Config.Filter || {}), Type: val }
  } else if (key === '__placeholder_label') {
    n.Config = n.Config || {}
    n.Config.Filter = n.Config.Filter || {}
    n.Config.Filter.Placeholder = { ...(n.Config.Filter.Placeholder || {}), LabelKey: val }
  } else if (key === '__entity_key') {
    n.Config = n.Config || {}
    n.Config.Filter = { ...(n.Config.Filter || {}), EntityKey: val }
  } else if (key === '__entity_value') {
    n.Config = n.Config || {}
    n.Config.Filter = { ...(n.Config.Filter || {}), EntityValue: val }
  }
  return n
}

// ── Getters/setters for nested style properties like css.flexDirection ─────
function getStyVal(sty, key) {
  if (key.startsWith('css.')) {
    return sty?.css?.[key.slice(4)] ?? ''
  }
  return sty?.[key] ?? ''
}
function setStyVal(sty, key, val) {
  const s = structuredClone(sty || {})
  if (key.startsWith('css.')) {
    if (!s.css) s.css = {}
    if (val === '') delete s.css[key.slice(4)]
    else s.css[key.slice(4)] = val
  } else {
    if (val === '') delete s[key]
    else s[key] = val
  }
  return s
}

// ── Main PropertyPanel ──────────────────────────────────────────────────────
export default function PropertyPanel({ fragment, selectedPath, onChange, onDelete, varPool = {}, varSchemas = {} }) {
  const [tab, setTab] = useState('config')

  const node = getNodeAtPath(fragment, selectedPath)
  const type = node?.Container || node?.Element || null
  const color = COMP_COLORS[type] || '#94A3B8'
  const icon = COMP_ICONS[type] || '□'
  const label = type ? (ELEMENT_LABELS[type] || type) : null

  if (!node || selectedPath.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <div className="text-center text-[#94A3B8] mt-8">
          <p className="text-4xl mb-2">☝️</p>
          <p className="text-sm">Click any element on the canvas to edit its properties.</p>
        </div>
        <div className="mt-6">
          <p className="text-xs font-semibold text-[#374151] mb-2">Root Fragment JSON</p>
          <JsonEditor value={fragment} onChange={newVal => onChange(newVal)} height="300px" />
        </div>
      </div>
    )
  }

  const updateNode = updater => {
    const newFrag = structuredClone(fragment)
    const parent = getParentAndKey(newFrag, selectedPath)
    if (!parent) return
    const { obj, key } = parent
    obj[key] = updater(structuredClone(obj[key]))
    onChange(newFrag)
  }

  const setConfig = (k, v) => {
    if (k === '__replace__') {
      updateNode(n => ({ ...n, Config: v }))
    } else {
      updateNode(n => ({ ...n, Config: { ...(n.Config || {}), [k]: v } }))
    }
  }
  const setStyle = (k, v) => updateNode(n => ({ ...n, Style: setStyVal(n.Style, k, v) }))
  const setFullStyle = newSty => updateNode(n => ({ ...n, Style: newSty }))
  const setInput = v => updateNode(n => ({ ...n, Input: v }))
  const setVirtual = (k, v) => updateNode(n => setVirtualField(n, k, v))
  const setFullNode = newNode => updateNode(() => newNode)

  // Mutates the node at selectedPath via mutateNodeFn AND ensures the sidebar Right-slot
  // detail-flyout stack host exists — both applied to the same fragment clone in one onChange,
  // so the column edit and the host wiring can't clobber each other.
  const ensureInsightHost = mutateNodeFn => {
    const newFrag = structuredClone(fragment)
    const parent = getParentAndKey(newFrag, selectedPath)
    if (parent) mutateNodeFn(parent.obj[parent.key])
    const hostFound = ensureDetailFlyoutHostMutate(newFrag)
    onChange(newFrag)
    if (!hostFound) {
      alert('Insights column added, but no "sidebar" container was found in this fragment to host the detail flyout listener. Add a sidebar container (or wire Events.Listeners.Push manually via Align Fix) so the bulb click actually opens the flyout.')
    }
  }

  const cfg = node.Config || {}
  const sty = node.Style || {}
  const inp = node.Input ?? ''
  const schema = ELEM_SCHEMAS[type]
  const isChart = CHART_TYPES.has(type)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#CBD5E1] flex items-center gap-2 shrink-0" style={{ backgroundColor: color + '15' }}>
        <span className="w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold shrink-0" style={{ backgroundColor: color }}>
          {icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold truncate" style={{ color }}>{label}</p>
          <p className="text-xs text-[#94A3B8]">{node.Container ? 'Container' : 'Element'}</p>
        </div>
        <button onClick={onDelete} className="text-xs px-2 py-0.5 bg-[#FEE2E2] text-[#991B1B] rounded hover:bg-red-200">Delete</button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#CBD5E1] shrink-0">
        {['config', 'style', 'events', 'json'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${tab === t ? 'bg-[#1E3A8A] text-white' : 'text-[#64748B] hover:bg-[#F1F5F9]'}`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {tab === 'config' && (
          <>
            {/* Schema description */}
            {schema?.desc && <p className="text-xs text-[#64748B] italic bg-[#F8FAFC] rounded px-2 py-1">{schema.desc}</p>}

            {/* Input field (for Elements) */}
            {node.Element && (
              <Field label="Input (field/variable name)">
                {Object.keys(varPool).length > 0 ? (
                  <div>
                    <select value={inp} onChange={e => setInput(e.target.value)} className="w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
                      <option value="">-- select from pool --</option>
                      {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
                    </select>
                    <input type="text" value={inp} onChange={e => setInput(e.target.value)}
                      className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB] mt-1" placeholder="FIELD_NAME" />
                  </div>
                ) : (
                  <input type="text" value={inp} onChange={e => setInput(e.target.value)}
                    className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="FIELD_NAME" />
                )}
              </Field>
            )}

            {/* Type-specific config editors */}
            {type === 'table' && (
              <TableConfigEditor node={node} cfg={cfg} sty={sty} updateNode={setFullNode} ensureInsightHost={ensureInsightHost} varPool={varPool} varSchemas={varSchemas} />
            )}
            {isChart && (
              <ChartConfigEditor node={node} cfg={cfg} updateNode={setFullNode} chartType={cfg.highchartsOptions?.chart?.type || (type !== 'chart' ? type : 'bar')} varPool={varPool} varSchemas={varSchemas} />
            )}
            {type === 'metrics' && (
              <MetricsEditor cfg={cfg} onSetConfig={setConfig} varPool={varPool} varSchemas={varSchemas} />
            )}
            {type === 'carousel' && (
              <CarouselConfigEditor node={node} cfg={cfg} updateNode={setFullNode} varPool={varPool} varSchemas={varSchemas} />
            )}
            {type === 'tab-group' && (
              <TabGroupConfigEditor node={node} updateNode={setFullNode} />
            )}
            {type === 'filter-panel' && (
              <SlotFilterEditor fpNode={node} onChange={setFullNode} varPool={varPool} />
            )}
            {type === 'segment-panel' && (
              <SegmentPanelConfigEditor node={node} cfg={cfg} updateNode={setFullNode} />
            )}

            {/* Schema-driven cfg fields */}
            {schema?.cfg && !isChart && type !== 'table' && type !== 'metrics' && type !== 'tab-group' && type !== 'carousel' && type !== 'filter-panel' && type !== 'segment-panel' && (
              schema.cfg.map(field => {
                const isVirtual = field.key.startsWith('__')
                const rawVal = isVirtual ? getVirtualField(node, field.key) : (cfg[field.key] ?? '')
                const val = rawVal === null || rawVal === undefined ? '' : rawVal

                if (field.type === 'bool') {
                  return (
                    <div key={field.key} className="flex items-center gap-2">
                      <input type="checkbox" id={field.key} checked={!!val}
                        onChange={e => isVirtual ? setVirtual(field.key, e.target.checked) : setConfig(field.key, e.target.checked)}
                        className="accent-[#1E3A8A]" />
                      <label htmlFor={field.key} className="text-xs text-[#374151]">
                        {field.label}
                        {field.desc && <span className="text-[#94A3B8] ml-1">— {field.desc}</span>}
                      </label>
                    </div>
                  )
                }
                if (field.type === 'enum') {
                  return (
                    <Field key={field.key} label={field.label} desc={field.desc}>
                      <select value={String(val)}
                        onChange={e => isVirtual ? setVirtual(field.key, e.target.value) : setConfig(field.key, e.target.value)}
                        className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB] bg-white">
                        {!field.options.includes('') && <option value="">—</option>}
                        {field.options.map(o => <option key={o} value={o}>{o || '(default)'}</option>)}
                      </select>
                    </Field>
                  )
                }
                if (field.type === 'int') {
                  return (
                    <Field key={field.key} label={field.label} desc={field.desc}>
                      <input type="number" value={String(val)}
                        onChange={e => isVirtual ? setVirtual(field.key, parseInt(e.target.value) || 0) : setConfig(field.key, parseInt(e.target.value) || 0)}
                        className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
                    </Field>
                  )
                }
                return (
                  <Field key={field.key} label={field.label} desc={field.desc}>
                    <input type="text" value={String(val)}
                      onChange={e => isVirtual ? setVirtual(field.key, e.target.value) : setConfig(field.key, e.target.value)}
                      className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
                  </Field>
                )
              })
            )}

            {/* Array editors (Tabs, Segments, etc.) */}
            {schema?.arr && type !== 'tab-group' && (
              <ArrayEditor
                arrKey={schema.arr.key}
                label={schema.arr.label}
                cols={schema.arr.cols}
                value={cfg[schema.arr.key] || []}
                onChange={rows => {
                  // For tab-group: sync Slots when Config.Tabs changes
                  if (type === 'tab-group' && schema.arr.key === 'Tabs') {
                    updateNode(n => {
                      const updated = { ...n, Config: { ...(n.Config || {}), Tabs: rows } }
                      if (!updated.Slots) updated.Slots = {}
                      // Add missing slots for new tabs
                      for (const t of rows) {
                        if (t.Name && !(t.Name in updated.Slots)) {
                          updated.Slots[t.Name] = []
                        }
                      }
                      return updated
                    })
                  } else {
                    setConfig(schema.arr.key, rows)
                  }
                }}
              />
            )}

            {/* Full Config JSON fallback */}
            {!isChart && type !== 'table' && type !== 'tab-group' && type !== 'carousel' && type !== 'filter-panel' && (
              <details className="mt-2">
                <summary className="text-xs font-semibold text-[#374151] cursor-pointer hover:text-[#1E3A8A]">Full Config JSON ▸</summary>
                <div className="mt-1">
                  <JsonEditor value={cfg} onChange={v => setConfig('__replace__', v)} height="150px" />
                </div>
              </details>
            )}

            {/* Visibility Conditions — applies to all element/container types */}
            <SectionHdr label="Visibility Conditions" />
            <p className="text-xs text-[#94A3B8] -mt-1">
              Each rule: when <code className="bg-[#F1F5F9] px-1 rounded">Condition</code> is true, set <code className="bg-[#F1F5F9] px-1 rounded">Visible</code> to that value.
            </p>
            <ConditionsEditor
              conditions={node.Conditions || []}
              onChange={conds => updateNode(n => {
                const updated = { ...n }
                if (conds.length) updated.Conditions = conds
                else delete updated.Conditions
                return updated
              })}
            />
          </>
        )}

        {tab === 'style' && (
          <StyleEditor node={node} sty={sty} schema={schema} onSetStyle={setStyle} onSetFullStyle={setFullStyle} />
        )}

        {tab === 'events' && (
          <div className="space-y-2">
            <p className="text-xs text-[#64748B]">
              Events.Triggers controls OnClick, OnChange etc. Edit the Events object below.
              Common pattern: <code className="bg-[#F1F5F9] px-1 rounded text-[10px]">OnClick → ContainerId + EventId</code>
            </p>
            <JsonEditor value={node.Events || {}} onChange={v => updateNode(n => ({ ...n, Events: v }))} height="300px" />
            <details className="mt-1">
              <summary className="text-xs font-semibold text-[#374151] cursor-pointer hover:text-[#1E3A8A]">
                Common event templates ▸
              </summary>
              <div className="mt-1 space-y-1">
                {[
                  ['OnClick ShowContainer', { Triggers: { OnClick: [{ ContainerId: 'my-container', EventId: 'show' }] } }],
                  ['OnClick with Payload', { Triggers: { OnClick: [{ ContainerId: 'filter-panel', EventId: 'filter', Payload: { filterSection: 'Filters', filterId: 'FIELD_KEY' } }] } }],
                  ['OnOpenTab', { Triggers: { OnOpenTab: { SourceContainerId: 'header-action-fragment', EventId: 'open-tab-detail' } } }],
                ].map(([label, tmpl]) => (
                  <button
                    key={label}
                    onClick={() => updateNode(n => ({ ...n, Events: tmpl }))}
                    className="w-full text-left text-xs px-2 py-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded hover:bg-[#EFF6FF] hover:border-[#DBEAFE]"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </details>
          </div>
        )}

        {tab === 'json' && (
          <div className="space-y-2">
            <p className="text-xs text-[#64748B]">Edit the raw node JSON. Changes apply immediately.</p>
            <JsonEditor value={node} onChange={newVal => updateNode(() => newVal)} height="450px" />
          </div>
        )}
      </div>
    </div>
  )
}

// ── Condition string helpers ──────────────────────────────────────────────────
const COND_OPS = ['==', '!=', '<=', '>=', '<', '>']

function parseConditionString(str) {
  if (!str || !str.trim()) return { clauses: [{ field: '', op: '==', value: '' }], join: '||' }
  const hasAnd = /\s*&&\s*/.test(str)
  const join = hasAnd ? '&&' : '||'
  const parts = str.split(hasAnd ? /\s*&&\s*/ : /\s*\|\|\s*/).map(s => s.trim()).filter(Boolean)
  const clauses = parts.map(part => {
    const m = part.match(/^(.+?)\s*(==|!=|<=|>=|<|>)\s*(.*)$/)
    if (m) return { field: m[1].trim(), op: m[2], value: m[3].trim() }
    return { field: part.trim(), op: '==', value: '' }
  })
  return { clauses: clauses.length ? clauses : [{ field: '', op: '==', value: '' }], join }
}

function buildConditionString({ clauses, join }) {
  const parts = clauses.filter(c => c.field.trim())
  if (!parts.length) return ''
  return parts.map(c => `${c.field} ${c.op} ${c.value}`).join(` ${join} `)
}

// ── Single condition rule builder (one Conditions[] item) ─────────────────────
function ConditionRuleBuilder({ cond, onChange, onRemove }) {
  const [{ clauses, join }, setLocal] = useState(() => parseConditionString(cond.Condition))

  const rebuild = (newClauses, newJoin) => {
    setLocal({ clauses: newClauses, join: newJoin })
    onChange({ ...cond, Condition: buildConditionString({ clauses: newClauses, join: newJoin }) })
  }

  const setClause = (ci, key, val) => {
    const c = [...clauses]; c[ci] = { ...c[ci], [key]: val }; rebuild(c, join)
  }
  const addClause = () => rebuild([...clauses, { field: '', op: '==', value: '' }], join)
  const removeClause = ci => rebuild(clauses.filter((_, i) => i !== ci), join)
  const toggleJoin = () => rebuild(clauses, join === '||' ? '&&' : '||')

  return (
    <div className="border border-[#E2E8F0] rounded bg-[#F8FAFC] p-1.5 space-y-1">
      {clauses.map((cl, ci) => (
        <div key={ci}>
          {ci > 0 && (
            <div className="flex justify-center my-0.5">
              <button onClick={toggleJoin}
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold transition-colors ${join === '||' ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}`}>
                {join === '||' ? 'OR' : 'AND'}
              </button>
            </div>
          )}
          <div className="flex items-center gap-1">
            <input
              value={cl.field}
              onChange={e => setClause(ci, 'field', e.target.value)}
              placeholder="field"
              className="flex-1 min-w-0 border rounded px-1.5 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB]"
            />
            <select
              value={cl.op}
              onChange={e => setClause(ci, 'op', e.target.value)}
              className="border rounded px-1 py-0.5 text-xs bg-white focus:outline-none shrink-0 font-mono font-bold text-[#1E3A8A]"
            >
              {COND_OPS.map(op => <option key={op} value={op}>{op}</option>)}
            </select>
            <input
              value={cl.value}
              onChange={e => setClause(ci, 'value', e.target.value)}
              placeholder='"str" / 0 / null'
              className="flex-1 min-w-0 border rounded px-1.5 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB]"
            />
            <button onClick={() => removeClause(ci)} className="text-red-400 hover:text-red-600 text-xs shrink-0 leading-none px-0.5">✕</button>
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1 border-t border-[#E2E8F0]">
        <button onClick={addClause}
          className="text-xs px-1.5 py-0.5 bg-[#F1F5F9] text-[#374151] rounded hover:bg-[#E2E8F0] font-medium">
          + clause
        </button>
        <label className="flex items-center gap-1 text-xs ml-auto cursor-pointer select-none">
          <input type="checkbox" checked={cond.Visible !== false}
            onChange={e => onChange({ ...cond, Visible: e.target.checked })} className="accent-[#1E3A8A]" />
          <span className={cond.Visible !== false ? 'text-green-700 font-semibold' : 'text-red-600 font-semibold'}>
            {cond.Visible !== false ? 'Visible' : 'Hidden'}
          </span>
        </label>
        <button onClick={onRemove} className="text-red-400 hover:text-red-600 text-xs shrink-0">✕ remove</button>
      </div>
    </div>
  )
}

// ── Conditions editor ─────────────────────────────────────────────────────────
function ConditionsEditor({ conditions, onChange }) {
  const add = () => onChange([...conditions, { Condition: '', Visible: false }])
  const update = (i, newCond) => { const c = [...conditions]; c[i] = newCond; onChange(c) }
  const remove = i => onChange(conditions.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-1.5">
      {conditions.length === 0 && (
        <p className="text-xs text-[#94A3B8] italic">No conditions. Element always visible.</p>
      )}
      {conditions.map((cond, i) => (
        <ConditionRuleBuilder key={i} cond={cond} onChange={newCond => update(i, newCond)} onRemove={() => remove(i)} />
      ))}
      <button onClick={add}
        className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]">
        + Add Condition
      </button>
    </div>
  )
}

// ── Field wrapper ────────────────────────────────────────────────────────────
function Field({ label, desc, children }) {
  return (
    <div>
      <label className="text-xs font-semibold text-[#374151] block mb-1">
        {label}
        {desc && <span className="font-normal text-[#94A3B8] ml-1">— {desc}</span>}
      </label>
      {children}
    </div>
  )
}

// ── Section header ───────────────────────────────────────────────────────────
function SectionHdr({ label }) {
  return <p className="text-xs font-bold text-[#374151] uppercase tracking-wider border-b border-[#E2E8F0] pb-1 mt-3">{label}</p>
}

// ── ArrayEditor — editable table of rows ─────────────────────────────────────
function ArrayEditor({ arrKey, label, cols, value, onChange }) {
  const [editIdx, setEditIdx] = useState(null)
  const [editRow, setEditRow] = useState({})

  const addRow = () => {
    const blank = {}
    cols.forEach(c => blank[c.key] = '')
    onChange([...value, blank])
  }
  const deleteRow = i => onChange(value.filter((_, j) => j !== i))
  const moveRow = (i, dir) => {
    const arr = [...value]
    const t = i + dir
    if (t < 0 || t >= arr.length) return
    ;[arr[i], arr[t]] = [arr[t], arr[i]]
    onChange(arr)
  }
  const startEdit = (i) => { setEditIdx(i); setEditRow({ ...value[i] }) }
  const saveEdit = () => {
    const arr = [...value]
    arr[editIdx] = editRow
    onChange(arr)
    setEditIdx(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold text-[#374151]">{label}</p>
        <button onClick={addRow} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded">+ Add Row</button>
      </div>
      <div className="border border-[#E2E8F0] rounded overflow-hidden">
        {/* Header */}
        <div className="flex bg-[#F1F5F9]">
          {cols.map(c => (
            <div key={c.key} className="text-xs font-semibold text-[#374151] px-2 py-1 border-r border-[#E2E8F0] last:border-0 truncate" style={{ minWidth: Math.min(c.width || 120, 120) }}>
              {c.label}
            </div>
          ))}
          <div className="text-xs text-[#94A3B8] px-2 py-1 ml-auto">Act</div>
        </div>
        {/* Rows */}
        {(value || []).map((row, i) => (
          <div key={i} className="flex items-center border-t border-[#F1F5F9] hover:bg-[#F8FAFC]">
            {editIdx === i ? (
              <>
                {cols.map(c => (
                  <input key={c.key} type="text" value={editRow[c.key] || ''}
                    onChange={e => setEditRow(r => ({ ...r, [c.key]: e.target.value }))}
                    className="px-2 py-0.5 text-xs border-r border-[#E2E8F0] flex-1 outline-none bg-[#EFF6FF]"
                    style={{ minWidth: 60 }} />
                ))}
                <div className="flex px-1 gap-0.5">
                  <button onClick={saveEdit} className="text-green-600 text-xs px-1">✓</button>
                  <button onClick={() => setEditIdx(null)} className="text-[#94A3B8] text-xs px-1">✕</button>
                </div>
              </>
            ) : (
              <>
                {cols.map(c => (
                  <div key={c.key} className="px-2 py-1 text-xs text-[#374151] border-r border-[#F1F5F9] last:border-0 truncate flex-1" style={{ minWidth: 60 }}>
                    {row[c.key] || ''}
                  </div>
                ))}
                <div className="flex px-1 gap-0.5 shrink-0">
                  <button onClick={() => startEdit(i)} className="text-[#2563EB] text-xs px-1" title="Edit">✎</button>
                  <button onClick={() => moveRow(i, -1)} className="text-[#94A3B8] text-xs px-0.5" title="Up">▲</button>
                  <button onClick={() => moveRow(i, 1)} className="text-[#94A3B8] text-xs px-0.5" title="Down">▼</button>
                  <button onClick={() => deleteRow(i)} className="text-red-400 text-xs px-1" title="Delete">✕</button>
                </div>
              </>
            )}
          </div>
        ))}
        {(!value || value.length === 0) && (
          <div className="text-xs text-[#94A3B8] px-3 py-2">No rows — click + Add Row</div>
        )}
      </div>
    </div>
  )
}

// ── TAB GROUP CONFIG EDITOR ───────────────────────────────────────────────────
// ── Sub-component: one slot's filter-panel row (needs own useState) ──────────
function SlotFPRow({ tabName, fp, CB, setSlotFP, update }) {
  const [fpExpanded, setFpExpanded] = useState(false)
  const hasFP = fp !== null
  const pos = fp?.Config?.Position || 'left'
  let attrCount = (fp?.Config?.Attributes || []).length
  for (const s of (fp?.Config?.Sections || [])) attrCount += (s.Attributes || []).length
  return (
    <div className="border border-[#E2E8F0] rounded mb-1.5">
      <div className="flex items-center px-2 py-1.5 bg-[#F8FAFC]">
        <span className="text-xs font-semibold text-[#374151] flex-1">{tabName}</span>
        <input type="checkbox" checked={hasFP}
          onChange={e => { setSlotFP(tabName, e.target.checked, pos); if (!e.target.checked) setFpExpanded(false) }}
          className={CB} title="Enable filter panel" />
        <span className="text-[10px] text-[#94A3B8] mx-1.5">Filter</span>
        {hasFP && (
          <>
            <select value={pos} onChange={e => setSlotFP(tabName, true, e.target.value)}
              className="border rounded px-1 py-0.5 text-xs bg-white focus:outline-none mr-1.5">
              <option value="left">left</option>
              <option value="right">right</option>
              <option value="top">top</option>
            </select>
            <span className="text-[10px] text-[#64748B] mr-2">{attrCount} attr</span>
            <button onClick={() => setFpExpanded(v => !v)} className="text-[10px] text-[#2563EB]">
              {fpExpanded ? '▼ attrs' : '▶ attrs'}
            </button>
          </>
        )}
      </div>
      {hasFP && fpExpanded && (
        <div className="border-t border-[#E2E8F0] px-2 py-2 bg-white">
          <SlotFilterEditor
            fpNode={fp}
            onChange={newFp => update(n => {
              if (!n.Slots) n.Slots = {}
              const items = [...(n.Slots[tabName] || [])]
              const idx = items.findIndex(it => it?.Container === 'filter-panel' || it?.Element === 'filter-panel')
              if (idx !== -1) items[idx] = newFp
              n.Slots[tabName] = items
            })}
          />
        </div>
      )}
    </div>
  )
}

function TabGroupConfigEditor({ node, updateNode }) {
  const [expandedSlot, setExpandedSlot] = useState(null)
  const update = fn => { const n = structuredClone(node); fn(n); updateNode(n) }
  const cfg = node.Config || {}
  const slots = node.Slots || {}
  const tabs = cfg.Tabs || []

  const CI  = 'w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]'
  const CB  = 'accent-[#1E3A8A]'
  const SEL = 'w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]'

  // ── Tabs ──────────────────────────────────────────────────────────────────
  const setTabs = newTabs => update(n => {
    if (!n.Config) n.Config = {}
    n.Config.Tabs = newTabs
    if (!n.Slots) n.Slots = {}
    for (const t of newTabs) if (t.Name && !(t.Name in n.Slots)) n.Slots[t.Name] = []
  })
  const addTab = () => { const i = tabs.length + 1; setTabs([...tabs, { Name: `Tab${i}`, LabelKey: `Tab ${i}`, UID: '' }]) }
  const removeTab = i => setTabs(tabs.filter((_, j) => j !== i))
  const moveTab = (i, dir) => {
    const arr = [...tabs]; const t = i + dir
    if (t < 0 || t >= arr.length) return
    ;[arr[i], arr[t]] = [arr[t], arr[i]]
    setTabs(arr)
  }
  const updateTab = (i, key, val) => setTabs(tabs.map((t, j) => j === i ? { ...t, [key]: val } : t))

  // ── Config ────────────────────────────────────────────────────────────────
  const setCfg = (k, v) => update(n => { if (!n.Config) n.Config = {}; if (v === '' || v === undefined) delete n.Config[k]; else n.Config[k] = v })
  const setOnOpenTab = (k, v) => update(n => {
    if (!n.Config) n.Config = {}
    if (!n.Config.OnOpenTab) n.Config.OnOpenTab = {}
    if (v) n.Config.OnOpenTab[k] = v; else delete n.Config.OnOpenTab[k]
    if (!Object.keys(n.Config.OnOpenTab).length) delete n.Config.OnOpenTab
  })

  // ── Per-slot filter panel ─────────────────────────────────────────────────
  const findFP = sn => (slots[sn] || []).find(it => it?.Container === 'filter-panel' || it?.Element === 'filter-panel') || null
  const setSlotFP = (sn, enabled, position) => update(n => {
    if (!n.Slots) n.Slots = {}
    const items = [...(n.Slots[sn] || [])]
    const cleaned = items.filter(it => !(it?.Container === 'filter-panel' || it?.Element === 'filter-panel'))
    if (enabled && position !== 'none') {
      const existing = items.find(it => it?.Container === 'filter-panel' || it?.Element === 'filter-panel')
      const fp = existing ? JSON.parse(JSON.stringify(existing)) : {
        Element: 'filter-panel',
        Config: { showFooter: true, showApplyButton: true, showClearButton: true,
          Position: position, Sections: [{ Type: 'Object', SectionName: 'Filters', Attributes: [] }] }
      }
      if (!fp.Config) fp.Config = {}
      fp.Config.Position = position
      n.Slots[sn] = [fp, ...cleaned]
    } else { n.Slots[sn] = cleaned }
  })

  // ── Slot content management ───────────────────────────────────────────────
  const addToSlot = (sn, elem) => update(n => {
    if (!n.Slots) n.Slots = {}
    if (!n.Slots[sn]) n.Slots[sn] = []
    n.Slots[sn] = [...n.Slots[sn], elem]
  })
  const removeFromSlot = (sn, idx) => update(n => {
    if (!n.Slots?.[sn]) return
    n.Slots[sn] = n.Slots[sn].filter((_, i) => i !== idx)
  })
  const elemLabel = it => (it?.Container || it?.Element || '?')

  const namedTabs = tabs.filter(t => t.Name)

  return (
    <>
      {/* ── Config Fields ──────────────────────────────────────── */}
      <SectionHdr label="Tab Group Config" />
      <div className="space-y-1.5">
        <div className="flex gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="tg-preserve" checked={!!cfg.preserveContent}
              onChange={e => setCfg('preserveContent', e.target.checked || undefined)} className={CB} />
            <label htmlFor="tg-preserve" className="text-xs text-[#374151]">Preserve Content (keep DOM alive)</label>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="tg-personal" checked={!!cfg.Personalizable}
              onChange={e => setCfg('Personalizable', e.target.checked || undefined)} className={CB} />
            <label htmlFor="tg-personal" className="text-xs text-[#374151]">Allow Personalization</label>
          </div>
        </div>
        <Field label="Default Active Tab">
          <select value={cfg.SelectedTabName || ''} onChange={e => setCfg('SelectedTabName', e.target.value || undefined)} className={SEL}>
            <option value="">— (first tab) —</option>
            {namedTabs.map(t => <option key={t.Name} value={t.Name}>{t.Name}</option>)}
          </select>
        </Field>
        <Field label="OnOpenTab → SourceContainerId">
          <input type="text" value={cfg.OnOpenTab?.SourceContainerId || ''}
            onChange={e => setOnOpenTab('SourceContainerId', e.target.value)} className={CI} placeholder="header-action-fragment" />
        </Field>
        <Field label="OnOpenTab → EventId">
          <input type="text" value={cfg.OnOpenTab?.EventId || ''}
            onChange={e => setOnOpenTab('EventId', e.target.value)} className={CI} placeholder="open-tab-detail" />
        </Field>
      </div>

      {/* ── Tabs List ──────────────────────────────────────────── */}
      <SectionHdr label="Tabs" />
      <button onClick={addTab} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded mb-2">+ Add Tab</button>
      <div className="border border-[#E2E8F0] rounded overflow-hidden">
        <div className="flex bg-[#F1F5F9] text-xs font-semibold text-[#374151]">
          <div className="px-2 py-1 flex-1">Slot Name</div>
          <div className="px-2 py-1" style={{width:120}}>Display Label</div>
          <div className="px-2 py-1" style={{width:80}}>UID</div>
          <div className="px-2 py-1 w-16">Act</div>
        </div>
        {tabs.map((t, i) => (
          <div key={i} className="flex items-center border-t border-[#F1F5F9]">
            <input value={t.Name || ''} onChange={e => updateTab(i, 'Name', e.target.value)}
              className="px-2 py-1 text-xs border-r border-[#E2E8F0] flex-1 outline-none focus:bg-[#EFF6FF]" placeholder="Tab1" />
            <input value={t.LabelKey || ''} onChange={e => updateTab(i, 'LabelKey', e.target.value)}
              className="px-2 py-1 text-xs border-r border-[#E2E8F0] outline-none focus:bg-[#EFF6FF]" style={{width:120}} placeholder="Tab 1" />
            <input value={t.UID || ''} onChange={e => updateTab(i, 'UID', e.target.value)}
              className="px-2 py-1 text-xs border-r border-[#E2E8F0] outline-none focus:bg-[#EFF6FF]" style={{width:80}} placeholder="uid-1" />
            <div className="flex px-1 gap-0.5 w-16 shrink-0">
              <button onClick={() => moveTab(i, -1)} className="text-[#94A3B8] text-xs px-0.5">▲</button>
              <button onClick={() => moveTab(i, 1)} className="text-[#94A3B8] text-xs px-0.5">▼</button>
              <button onClick={() => removeTab(i)} className="text-red-400 text-xs px-1">✕</button>
            </div>
          </div>
        ))}
        {tabs.length === 0 && <div className="text-xs text-[#94A3B8] px-3 py-2">No tabs — click + Add Tab</div>}
      </div>

      {/* ── Per-Slot Filter Panel ───────────────────────────────── */}
      <SectionHdr label="Filter Panel per Slot" />
      <p className="text-xs text-[#94A3B8] mb-2">Enable a filter panel per slot, set position, and edit filter groups/attributes.</p>
      {namedTabs.length === 0 ? (
        <p className="text-xs text-[#94A3B8] italic">Add tabs above first.</p>
      ) : namedTabs.map(t => (
        <SlotFPRow key={t.Name} tabName={t.Name} fp={findFP(t.Name)} CB={CB} setSlotFP={setSlotFP} update={update} />
      ))}

      {/* ── Slot Contents ──────────────────────────────────────── */}
      <SectionHdr label="Slot Contents" />
      <p className="text-xs text-[#94A3B8] mb-2">Manage elements inside each tab slot. Click ▶ to expand.</p>
      {namedTabs.length === 0 ? (
        <p className="text-xs text-[#94A3B8] italic">Add tabs above first.</p>
      ) : namedTabs.map(t => {
        const items = slots[t.Name] || []
        const isExp = expandedSlot === t.Name
        return (
          <div key={t.Name} className="border border-[#E2E8F0] rounded mb-1.5">
            <button onClick={() => setExpandedSlot(isExp ? null : t.Name)}
              className="w-full flex items-center px-2 py-1.5 bg-[#F8FAFC] text-left hover:bg-[#F1F5F9]">
              <span className="text-xs font-semibold text-[#374151] flex-1">{t.Name}</span>
              <span className="text-xs text-[#94A3B8] mr-2">{items.length} item{items.length !== 1 ? 's' : ''}</span>
              <span className="text-xs text-[#94A3B8]">{isExp ? '▼' : '▶'}</span>
            </button>
            {isExp && (
              <div className="px-2 pb-2 space-y-1 pt-1">
                {items.map((it, idx) => (
                  <div key={idx} className="flex items-center gap-2 py-0.5 border-b border-[#F1F5F9] last:border-0">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#DBEAFE] text-[#1E3A8A] font-mono shrink-0">{elemLabel(it)}</span>
                    {it.Config?.Position && <span className="text-[10px] text-[#64748B]">pos:{it.Config.Position}</span>}
                    {it.Config?.title && <span className="text-[10px] text-[#374151] flex-1 truncate">{it.Config.title}</span>}
                    <button onClick={() => removeFromSlot(t.Name, idx)} className="text-red-400 text-xs px-1 ml-auto shrink-0">✕</button>
                  </div>
                ))}
                {items.length === 0 && <p className="text-xs text-[#94A3B8] italic py-1">Empty — add elements below.</p>}
                <div className="flex gap-1 pt-1 flex-wrap">
                  <button onClick={() => setSlotFP(t.Name, true, 'left')}
                    className="text-xs px-2 py-0.5 bg-[#F0FDF4] text-[#15803D] border border-[#86EFAC] rounded">
                    + Filter Panel
                  </button>
                  <button onClick={() => addToSlot(t.Name, { Container: 'card', Config: { title: 'Card' }, Style: {}, Slots: { Default: [] } })}
                    className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD] rounded">
                    + Card
                  </button>
                  <button onClick={() => addToSlot(t.Name, { Container: 'flex', Style: { css: { flexDirection: 'row', gap: '8px' } }, Slots: { Default: [] } })}
                    className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD] rounded">
                    + Flex
                  </button>
                  <button onClick={() => {
                    const key = window.prompt('Container type (card/flex/grid/section) or element type (key-value/text etc.):')
                    if (!key) return
                    const isContainer = ['card','flex','grid','stack','section','banner','accordion','expandable'].includes(key)
                    if (isContainer) addToSlot(t.Name, { Container: key, Config: {}, Style: {}, Slots: { Default: [] } })
                    else addToSlot(t.Name, { Element: key, Config: {}, Input: '' })
                  }} className="text-xs px-2 py-0.5 bg-[#F8FAFC] text-[#374151] border border-[#E2E8F0] rounded">
                    + Custom…
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* ── Style ──────────────────────────────────────────────── */}
      <SectionHdr label="Tab Style" />
      <div className="space-y-1.5">
        {[
          ['tabHeader.borderColor', 'Header Border Color', '#CBD5E1'],
          ['tabHeader.hoverBorderColor', 'Hover Border Color', '#2563EB'],
          ['tabHeader.hoverTextColor', 'Hover Text Color', '#1E3A8A'],
        ].map(([k, lbl, ph]) => {
          const parts = k.split('.'); const sty = node.Style || {}
          const cur = parts.length === 2 ? (sty[parts[0]]?.[parts[1]] || '') : (sty[k] || '')
          return (
            <Field key={k} label={lbl}>
              <input type="text" value={cur}
                onChange={e => updateNode(n => {
                  const nn = structuredClone(n); if (!nn.Style) nn.Style = {}
                  if (parts.length === 2) { if (!nn.Style[parts[0]]) nn.Style[parts[0]] = {}; nn.Style[parts[0]][parts[1]] = e.target.value }
                  else nn.Style[k] = e.target.value
                  return nn
                })} className={CI} placeholder={ph} />
            </Field>
          )
        })}
        <Field label="Tab Alignment">
          <select value={(node.Style || {}).tabAlignment || 'start'}
            onChange={e => updateNode(n => { const nn = structuredClone(n); if (!nn.Style) nn.Style = {}; nn.Style.tabAlignment = e.target.value; return nn })}
            className={SEL}>
            {['start','center','end'].map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </Field>
      </div>
    </>
  )
}

// ── SEGMENT PANEL CONFIG EDITOR ───────────────────────────────────────────────
// Dual-mode control: EnableFilter=true → filter-backed segmented control (Container,
// Config.Filter.StaticList, AttributeKey/AttributeValue rows — drives an agent filter).
// EnableFilter=false → simple chip tabs (Config.Segments, LabelKey/Id rows, no filter wiring).
function SegmentPanelConfigEditor({ node, cfg, updateNode }) {
  const update = fn => { const n = structuredClone(node); fn(n); updateNode(n) }
  const setCfg = (k, v) => update(n => { if (!n.Config) n.Config = {}; if (v === '' || v === undefined) delete n.Config[k]; else n.Config[k] = v })
  const setFilter = (k, v) => update(n => {
    if (!n.Config) n.Config = {}
    if (!n.Config.Filter) n.Config.Filter = { Type: 'Singleselect' }
    if (v === '' || v === undefined) delete n.Config.Filter[k]
    else n.Config.Filter[k] = v
  })

  const enableFilter = cfg.EnableFilter !== false
  const staticList = cfg.Filter?.StaticList || []
  const segments = cfg.Segments || []

  const CI = 'w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]'
  const CB = 'accent-[#1E3A8A]'
  const SEL = 'w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]'

  const toggleFilterMode = checked => update(n => {
    if (!n.Config) n.Config = {}
    n.Config.EnableFilter = checked
    if (checked) {
      // Chip mode → filter mode: LabelKey/Id → AttributeKey/AttributeValue
      const rows = (n.Config.Segments || []).map(s => ({ AttributeKey: s.LabelKey || '', AttributeValue: s.Id || '', UID: s.UID || '' }))
      n.Config.Filter = { Type: 'Singleselect', EntityKey: 'AttributeKey', EntityValue: 'AttributeValue', StaticList: rows.length ? rows : (n.Config.Filter?.StaticList || []) }
      delete n.Config.Segments
      if (!n.Input) n.Input = 'map(*)'
    } else {
      // Filter mode → chip mode: AttributeKey/AttributeValue → LabelKey/Id
      const rows = (n.Config.Filter?.StaticList || []).map(s => ({ LabelKey: s.AttributeKey || '', Id: s.AttributeValue || '', UID: s.UID || '' }))
      n.Config.Segments = rows.length ? rows : (n.Config.Segments || [])
      delete n.Config.Filter
    }
  })

  return (
    <>
      <SectionHdr label="Segment Panel Config" />
      <div className="space-y-1.5">
        <Field label="Input">
          <input type="text" value={node.Input || ''} onChange={e => update(n => { n.Input = e.target.value })} className={CI} placeholder="map(*)" />
        </Field>
        <div className="flex gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="sp-enable" checked={cfg.EnableSegmentPanel !== false}
              onChange={e => setCfg('EnableSegmentPanel', e.target.checked)} className={CB} />
            <label htmlFor="sp-enable" className="text-xs text-[#374151]">Enable Segment Panel</label>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="sp-filter" checked={enableFilter}
              onChange={e => toggleFilterMode(e.target.checked)} className={CB} />
            <label htmlFor="sp-filter" className="text-xs text-[#374151]">Filter Mode (drives an agent filter attribute)</label>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <Field label="Name" desc="Filter attribute name sent to agent, e.g. MetricMode">
            <input type="text" value={cfg.Name || ''} onChange={e => setCfg('Name', e.target.value)} className={CI} placeholder="MetricMode" />
          </Field>
          <Field label="Section Name">
            <input type="text" value={cfg.SectionName || ''} onChange={e => setCfg('SectionName', e.target.value)} className={CI} placeholder="Filters" />
          </Field>
        </div>
      </div>

      {enableFilter ? (
        <>
          <SectionHdr label="Filter Config" />
          <div className="space-y-1.5">
            <div className="grid grid-cols-2 gap-1.5">
              <Field label="Filter Type">
                <select value={cfg.Filter?.Type || 'Singleselect'} onChange={e => setFilter('Type', e.target.value)} className={SEL}>
                  {['Singleselect', 'Multiselect'].map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </Field>
              <Field label="Data Type">
                <input type="text" value={cfg.Type || ''} onChange={e => setCfg('Type', e.target.value)} className={CI} placeholder="string" />
              </Field>
              <Field label="Placeholder Label">
                <input type="text" value={cfg.Filter?.Placeholder?.LabelKey || ''}
                  onChange={e => update(n => { if (!n.Config) n.Config = {}; if (!n.Config.Filter) n.Config.Filter = {}; if (!n.Config.Filter.Placeholder) n.Config.Filter.Placeholder = {}; if (e.target.value) n.Config.Filter.Placeholder.LabelKey = e.target.value; else delete n.Config.Filter.Placeholder })}
                  className={CI} placeholder="Select..." />
              </Field>
              <Field label="Entity Key Field">
                <input type="text" value={cfg.Filter?.EntityKey || ''} onChange={e => setFilter('EntityKey', e.target.value)} className={CI} placeholder="AttributeKey" />
              </Field>
              <Field label="Entity Value Field">
                <input type="text" value={cfg.Filter?.EntityValue || ''} onChange={e => setFilter('EntityValue', e.target.value)} className={CI} placeholder="AttributeValue" />
              </Field>
            </div>
          </div>
          <SectionHdr label="Options (StaticList)" />
          <ArrayEditor
            label="StaticList rows"
            cols={[{ key: 'AttributeKey', label: 'Label', width: 140 }, { key: 'AttributeValue', label: 'Value', width: 140 }, { key: 'UID', label: 'UID', width: 100 }]}
            value={staticList}
            onChange={v => setFilter('StaticList', v)}
          />
        </>
      ) : (
        <>
          <SectionHdr label="Segments (chip tabs)" />
          <ArrayEditor
            label="Segment rows"
            cols={[{ key: 'LabelKey', label: 'Label', width: 160 }, { key: 'Id', label: 'Id', width: 160 }]}
            value={segments}
            onChange={v => setCfg('Segments', v)}
          />
        </>
      )}
    </>
  )
}

// ── CAROUSEL CONFIG EDITOR ────────────────────────────────────────────────────
function CarouselConfigEditor({ node, cfg, updateNode, varPool = {} }) {
  const update = fn => { const n = structuredClone(node); fn(n); updateNode(n) }
  const setCfg = (k, v) => update(n => {
    if (!n.Config) n.Config = {}
    if (v === '' || v === undefined) delete n.Config[k]; else n.Config[k] = v
  })

  const CI  = 'w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]'
  const CB  = 'accent-[#1E3A8A]'
  const SEL = 'w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]'

  return (
    <>
      {/* ── Data ───────────────────────────────────────────────── */}
      <SectionHdr label="Data" />
      <Field label="Data Source Path">
        {Object.keys(varPool).length > 0 ? (
          <div>
            <select value={cfg.dataSourcePath || node.Init?.DataSourcePath || ''}
              onChange={e => update(n => {
                if (!n.Config) n.Config = {}; n.Config.dataSourcePath = e.target.value
                if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = e.target.value
              })} className={SEL}>
              <option value="">-- select from pool --</option>
              {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
            </select>
            <input type="text" value={cfg.dataSourcePath || node.Init?.DataSourcePath || ''}
              onChange={e => update(n => {
                if (!n.Config) n.Config = {}; n.Config.dataSourcePath = e.target.value
                if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = e.target.value
              })} className={`${CI} mt-1`} placeholder="CarouselData" />
          </div>
        ) : (
          <input type="text" value={cfg.dataSourcePath || node.Init?.DataSourcePath || ''}
            onChange={e => update(n => {
              if (!n.Config) n.Config = {}; n.Config.dataSourcePath = e.target.value
              if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = e.target.value
            })} className={CI} placeholder="CarouselData" />
        )}
      </Field>

      {/* ── Slides ─────────────────────────────────────────────── */}
      <SectionHdr label="Slides" />
      <div className="grid grid-cols-2 gap-1.5">
        <Field label="Slides Per Page">
          <input type="number" value={cfg.slidesPerPage ?? 5}
            onChange={e => setCfg('slidesPerPage', parseInt(e.target.value) || 1)} className={CI} />
        </Field>
        <Field label="Slides Per Move">
          <input type="number" value={cfg.slidesPerMove ?? 5}
            onChange={e => setCfg('slidesPerMove', parseInt(e.target.value) || 1)} className={CI} />
        </Field>
      </div>
      <Field label="Orientation">
        <select value={cfg.orientation || 'horizontal'} onChange={e => setCfg('orientation', e.target.value)} className={SEL}>
          <option value="horizontal">horizontal</option>
          <option value="vertical">vertical</option>
        </select>
      </Field>

      {/* ── Controls ───────────────────────────────────────────── */}
      <SectionHdr label="Controls" />
      <div className="space-y-1.5">
        {[['navigation','Show Navigation Arrows'],['pagination','Show Pagination Dots'],['loop','Loop'],['autoplay','Autoplay']].map(([k, lbl]) => (
          <div key={k} className="flex items-center gap-2">
            <input type="checkbox" id={`cr-${k}`} checked={!!cfg[k]}
              onChange={e => setCfg(k, e.target.checked || undefined)} className={CB} />
            <label htmlFor={`cr-${k}`} className="text-xs text-[#374151]">{lbl}</label>
          </div>
        ))}
        {cfg.autoplay && (
          <Field label="Autoplay Interval (ms)">
            <input type="number" value={cfg.autoplayInterval || 3000}
              onChange={e => setCfg('autoplayInterval', parseInt(e.target.value))} className={CI} />
          </Field>
        )}
      </div>

      {/* ── Item Template ──────────────────────────────────────── */}
      <SectionHdr label="Item Template (Config.Fragment)" />
      {cfg.Fragment !== undefined ? (
        <div className="space-y-1">
          <p className="text-xs text-[#64748B]">Fragment node rendered for each data item. Edit structure below.</p>
          <button onClick={() => update(n => { if (!n.Config) n.Config = {}; delete n.Config.Fragment })}
            className="text-xs px-2 py-0.5 bg-[#FEE2E2] text-[#991B1B] rounded">Clear Template</button>
          <JsonEditor value={cfg.Fragment} onChange={v => setCfg('Fragment', v)} height="200px" />
        </div>
      ) : (
        <div className="p-2 bg-[#F8FAFC] border border-dashed border-[#CBD5E1] rounded text-xs text-[#94A3B8] space-y-2">
          <p className="text-[#374151] font-semibold">No template — each data row renders one copy of this fragment.</p>
          <div className="flex gap-1 flex-wrap">
            <button onClick={() => setCfg('Fragment', { Container: 'card', Config: { title: 'Item' }, Style: {}, Slots: { Default: [] } })}
              className="px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded text-xs">+ Card Template</button>
            <button onClick={() => setCfg('Fragment', { Container: 'flex', Style: { css: { flexDirection: 'column', gap: '4px', padding: '8px' } }, Slots: { Default: [] } })}
              className="px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded text-xs">+ Flex Template</button>
          </div>
          <p className="text-[10px] text-[#94A3B8]">Or paste JSON from another fragment node:</p>
          <JsonEditor value={{}} onChange={v => Object.keys(v).length && setCfg('Fragment', v)} height="80px" />
        </div>
      )}

      {/* ── Style ──────────────────────────────────────────────── */}
      <SectionHdr label="Style" />
      <div className="space-y-1.5">
        {[['width','Width','100%'],['slideGap','Slide Gap','16px'],['css.borderRadius','Border Radius',''],['css.padding','Padding','']].map(([k, lbl, ph]) => {
          const sty = node.Style || {}
          const parts = k.split('.'); const cur = parts.length === 2 ? (sty[parts[0]]?.[parts[1]] || '') : (sty[k] || '')
          return (
            <Field key={k} label={lbl}>
              <input type="text" value={cur}
                onChange={e => updateNode(n => {
                  const nn = structuredClone(n); if (!nn.Style) nn.Style = {}
                  if (parts.length === 2) { if (!nn.Style[parts[0]]) nn.Style[parts[0]] = {}; nn.Style[parts[0]][parts[1]] = e.target.value }
                  else nn.Style[k] = e.target.value
                  return nn
                })} className={CI} placeholder={ph} />
            </Field>
          )
        })}
      </div>
    </>
  )
}

// ── Column link / event helpers ───────────────────────────────────────────────
function isInsightsCol(col) {
  try {
    return !!(col.Slots?.Default?.find(e => e?.Element === 'action-button')
              ?.Config?.ActionConfig?.Behavior?.Flyout?.AgentRef?.AgentId)
  } catch { return false }
}

function getColFieldKey(col) {
  try {
    return (col.Slots?.Default?.find(e => e?.Element === 'link')
          || col.Slots?.Default?.find(e => e?.Element === 'key-value'))?.Input || ''
  } catch { return '' }
}

function readColLink(col) {
  try {
    const link = col.Slots?.Default?.find(e => e?.Element === 'link')
    if (!link) return null
    const onClick = link.Events?.Triggers?.OnClick?.[0]
    if (onClick) {
      return {
        event_type: 'event_click',
        event_id: onClick.EventId || '',
        container_id: onClick.ContainerId || '',
        filter_section: onClick.Payload?.filterSection || '',
        filter_id: onClick.Payload?.filterId || '',
        input_expr: onClick.Input || '',
      }
    }
    const lkCfg = link.Config?.LegacyLink || {}
    const relCfg = lkCfg.RelationshipConfig?.[0] || {}
    return {
      event_type: 'legacy',
      menu_id: lkCfg.MenuId || '',
      rel_name: lkCfg.RelationshipName || relCfg.RelationshipName || '',
      from_entity: relCfg.FromEntity || '',
      to_entity: relCfg.ToEntity || '',
      label_key: lkCfg.LabelKey || '',
      id_field: link.Input || '',
      ref_keys: (relCfg.ReferenceKeys || []).map(rk =>
        rk.FromAttribute
          ? { type: 'field', from_attr: rk.FromAttribute, to_attr: rk.ToAttribute }
          : { type: 'filter', to_attr: rk.ToAttribute, from_values: rk.FromValues || [] }
      ),
    }
  } catch { return null }
}

function readColEvent(col) {
  try {
    const kv = col.Slots?.Default?.find(e => e?.Element === 'key-value')
    const ev = kv?.Events?.Triggers?.OnClick?.[0]
    if (!ev) return null
    return {
      event_id: ev.EventId || '',
      container_id: ev.ContainerId || '',
      filter_section: ev.Payload?.filterSection || '',
      filter_id: ev.Payload?.filterId || '',
      input_expr: ev.Input || '',
    }
  } catch { return null }
}

function linkBadge(col) {
  const lk = readColLink(col)
  const ev = readColEvent(col)
  const parts = []
  if (lk) {
    if (lk.event_type === 'event_click') parts.push(`🎯 ${lk.event_id}`)
    else parts.push(`🔗 ${lk.menu_id || lk.to_entity || 'link'}`)
  }
  if (ev && (ev.event_id || ev.container_id)) {
    const tag = `⚡ ${ev.event_id}` + (ev.input_expr ? ' [map]' : ev.filter_id ? ` [${ev.filter_id}]` : '')
    parts.push(lk ? `+${tag}` : tag)
  }
  return parts.join('  ')
}

function applyColLink(col, link) {
  const fieldIn = getColFieldKey(col) || col.Config?.Sort?.SortBy || ''
  if (!col.Slots) col.Slots = {}
  if (!col.Slots.Default) col.Slots.Default = []
  const kvEls = col.Slots.Default.filter(e => e?.Element === 'key-value')
  col.Slots.Default = col.Slots.Default.filter(e => e?.Element !== 'link' && e?.Element !== 'key-value')
  if (!link) {
    col.Slots.Default.push(...(kvEls.length ? kvEls : [{ Element: 'key-value', Input: fieldIn, Config: { AttributeType: 'string' } }]))
    return
  }
  if (link.event_type === 'event_click') {
    const ev = { EventId: link.event_id, ContainerId: link.container_id }
    if (link.filter_section || link.filter_id)
      ev.Payload = { filterSection: link.filter_section || 'Filters', filterId: link.filter_id, filterValue: `<${fieldIn}>` }
    if (link.input_expr) ev.Input = link.input_expr
    col.Slots.Default.push({ Element: 'link', Input: fieldIn, Events: { Triggers: { OnClick: [ev] } } })
  } else {
    const refKeys = (link.ref_keys || []).map(rk =>
      rk.type === 'field'
        ? { FromAttribute: rk.from_attr, ToAttribute: rk.to_attr }
        : { ToAttribute: rk.to_attr, FromValues: rk.from_values || [] }
    )
    col.Slots.Default.push({
      Element: 'link', Input: link.id_field || fieldIn,
      Config: { LegacyLink: {
        MenuId: link.menu_id,
        RelationshipConfig: [{ RelationshipName: link.rel_name, FromEntity: link.from_entity, ToEntity: link.to_entity, ReferenceKeys: refKeys }],
        RelationshipName: link.rel_name, LabelKey: link.label_key || col.Config?.LabelKey || '',
      }},
    })
  }
}

function applyColEvent(col, event) {
  const fieldIn = getColFieldKey(col) || col.Config?.Sort?.SortBy || ''
  if (!col.Slots) col.Slots = {}
  if (!col.Slots.Default) col.Slots.Default = []
  let kv = col.Slots.Default.find(e => e?.Element === 'key-value')
  if (!kv) { kv = { Element: 'key-value', Input: fieldIn, Config: { AttributeType: 'string' } }; col.Slots.Default.push(kv) }
  if (!event || (!event.event_id && !event.container_id)) { delete kv.Events; return }
  const ev = { EventId: event.event_id, ContainerId: event.container_id }
  if (event.filter_section || event.filter_id)
    ev.Payload = { filterSection: event.filter_section, filterId: event.filter_id, filterValue: `<${fieldIn}>` }
  if (event.input_expr) ev.Input = event.input_expr
  kv.Events = { Triggers: { OnClick: [ev] } }
}

function readInsights(cols) {
  const ic = (cols || []).find(c => isInsightsCol(c))
  if (!ic) return { enabled: false, field: 'TicketsList', agentId: 'obe-ticketDetailFlyout' }
  const ab = ic.Slots?.Default?.find(e => e?.Element === 'action-button')
  const agentId = ab?.Config?.ActionConfig?.Behavior?.Flyout?.AgentRef?.AgentId || ''
  const m = (ab?.Input || '').match(/map\(\{(\w+):/)
  return { enabled: true, field: m ? m[1] : 'TicketsList', agentId }
}

function buildInsightsCol(field, agentId) {
  const f = field || 'TicketsList', a = agentId || 'obe-ticketDetailFlyout'
  return {
    UID: `Column${f}`, Config: { LabelKey: 'Insights' },
    Slots: { Default: [
      { Input: 'Dummy', Config: {}, Element: 'key-value', Style: {} },
      {
        Element: 'action-button',
        Conditions: [{ Condition: `${f} == null`, Visible: false }],
        Input: `map({${f}: ${f}})`,
        Config: { LabelKey: '', src: 'assets/river/assets/icons/lightbulb-on.svg',
          ActionConfig: { Behavior: { Flyout: { AgentRef: { AgentId: a } } } } },
        Style: { css: { border: 'none', 'background-color': 'transparent', color: 'var(--fixed-13)',
          'white-space': 'nowrap', 'padding-left': 0, 'justify-self': 'end' } },
        Events: { Triggers: { OnClick: [{ EventId: 'push-details-flyout', ContainerId: 'details-button' }] } },
      },
    ]},
  }
}

function readAgentic(node) {
  const aa = node.Slots?.AgenticActions?.[0]
  if (!aa) return { enabled: false, agentId: 'ext-mhetroubleshoot', question: '', args: [] }
  const action = aa.Slots?.Menu?.[0]?.Emitters?.click?.actions?.[0]
  return {
    enabled: true,
    agentId: action?.config?.agentId || 'ext-mhetroubleshoot',
    question: action?.config?.question || '',
    args: action?.config?.actionArguments || [],
  }
}

function buildAgenticSlot(agentId, question, args) {
  return [{
    Element: 'agentic-actions',
    Slots: { Menu: [{ Element: 'menu-item', Config: { LabelKey: 'Troubleshoot with AI' },
      Emitters: { click: { actions: [{ type: 'agentic', config: {
        agentId: agentId || 'ext-mhetroubleshoot',
        question: question || 'Analyze and troubleshoot failures for this message type',
        actionArguments: args || [],
      }}] }},
    }]},
  }]
}

// ── Column Link Modal ─────────────────────────────────────────────────────────
function ColLinkModal({ field, title, existing, onApply, onClear, onClose }) {
  const isEvt = existing?.event_type === 'event_click'
  const isLeg = existing?.event_type === 'legacy'
  const [mode, setMode] = useState(isEvt ? 'event_click' : 'legacy')
  const [ev, setEv] = useState({
    event_id: isEvt ? (existing.event_id || 'open-tab-detail') : 'open-tab-detail',
    container_id: isEvt ? (existing.container_id || 'header-action-fragment') : 'header-action-fragment',
    filter_section: isEvt ? (existing.filter_section || 'Filters') : 'Filters',
    filter_id: isEvt ? (existing.filter_id || '') : '',
    input_expr: isEvt ? (existing.input_expr || '') : '',
  })
  const [leg, setLeg] = useState({
    menu_id: isLeg ? (existing.menu_id || '') : '',
    rel_name: isLeg ? (existing.rel_name || `${field}_rel`) : `${field}_rel`,
    from_entity: isLeg ? (existing.from_entity || 'outputTable') : 'outputTable',
    to_entity: isLeg ? (existing.to_entity || '') : '',
    label_key: isLeg ? (existing.label_key || title) : title,
    id_field: isLeg ? (existing.id_field || field) : field,
  })
  const [refKeys, setRefKeys] = useState(existing?.ref_keys || [])

  const addFieldKey = () => {
    const fa = prompt('From Attribute (e.g. InPickingTaskIds):')?.trim()
    if (!fa) return
    const ta = prompt('To Attribute (e.g. TaskId):')?.trim()
    if (ta != null) setRefKeys(k => [...k, { type: 'field', from_attr: fa, to_attr: ta }])
  }
  const addFilterKey = () => {
    const ta = prompt('To Attribute (e.g. Status):')?.trim()
    if (!ta) return
    const vs = prompt('From Values — comma-separated (e.g. 1000,7000):')?.trim()
    if (vs != null) setRefKeys(k => [...k, { type: 'filter', to_attr: ta, from_values: vs.split(',').map(s => s.trim()).filter(Boolean) }])
  }

  const handleApply = () => {
    if (mode === 'event_click') onApply({ event_type: 'event_click', ...ev })
    else onApply({ event_type: 'legacy', ...leg, ref_keys: refKeys })
  }

  return (
    <Modal title={`Configure Link — ${title}`} onClose={onClose} width="max-w-xl">
      <div className="p-4 space-y-4 overflow-y-auto" style={{ maxHeight: '80vh' }}>
        <div className="flex gap-6">
          {[['event_click', '🎯 Event Click (EventId / tab navigation)'], ['legacy', '🔗 Legacy Link (drill-through / navigate)']].map(([v, lbl]) => (
            <label key={v} className="flex items-center gap-1.5 cursor-pointer text-xs text-[#374151]">
              <input type="radio" name="lnkMode" value={v} checked={mode === v} onChange={() => setMode(v)} />
              {lbl}
            </label>
          ))}
        </div>

        {mode === 'event_click' ? (
          <div className="space-y-2">
            {[['event_id','EventId'],['container_id','ContainerId'],['filter_section','Payload → filterSection (opt.)'],['filter_id','Payload → filterId (opt.)']].map(([k, lbl]) => (
              <Field key={k} label={lbl}>
                <input type="text" value={ev[k]} onChange={e => setEv(x => ({ ...x, [k]: e.target.value }))}
                  className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
              </Field>
            ))}
            <Field label="Input expression (opt.)">
              <textarea rows={2} value={ev.input_expr} onChange={e => setEv(x => ({ ...x, input_expr: e.target.value }))}
                className="w-full border rounded px-2 py-1 text-xs font-mono resize-none focus:outline-none focus:border-[#2563EB]"
                placeholder="e.g. map({tabName: 'Tab1', filterId: 'X', filterValue: FIELD})" />
            </Field>
            <p className="text-xs text-[#94A3B8]">Generates Element:'link' with Events.Triggers.OnClick → EventId + ContainerId. When filterSection + filterId are set, a Payload is added so the tab-group OnOpenTab listener can set Filters.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {[['menu_id','Menu ID'],['rel_name','Relationship Name'],['from_entity','From Entity'],['to_entity','To Entity'],['label_key','Label Key'],['id_field','ID Field (holds link IDs)']].map(([k, lbl]) => (
              <Field key={k} label={lbl}>
                <input type="text" value={leg[k]} onChange={e => setLeg(x => ({ ...x, [k]: e.target.value }))}
                  className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
              </Field>
            ))}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-[#374151]">Reference Keys</span>
                <div className="flex gap-1">
                  <button onClick={addFieldKey} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded">+ Field</button>
                  <button onClick={addFilterKey} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded">+ Filter</button>
                </div>
              </div>
              <p className="text-xs text-[#94A3B8] mb-1">→ field: maps data field to target attr    = filter: applies fixed filter value</p>
              <div className="border rounded divide-y">
                {refKeys.length === 0 && <p className="p-2 text-xs text-[#94A3B8] italic">No ref keys yet</p>}
                {refKeys.map((rk, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-1.5 text-xs">
                    <span className="font-mono font-bold text-[#374151] w-4">{rk.type === 'field' ? '→' : '='}</span>
                    <span className="flex-1 text-[#374151]">
                      {rk.type === 'field' ? `${rk.from_attr}  →  ${rk.to_attr}` : `${rk.to_attr}  =  ${(rk.from_values || []).join(', ')}`}
                    </span>
                    <button onClick={() => setRefKeys(k => k.filter((_, j) => j !== i))} className="text-red-400">✕</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-2 border-t border-[#E2E8F0]">
          <button onClick={handleApply} className="px-4 py-1.5 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold hover:bg-[#BFDBFE]">Apply</button>
          <button onClick={onClear} className="px-4 py-1.5 bg-[#FEF3C7] text-[#92400E] rounded text-sm hover:bg-[#FDE68A]">Clear Link</button>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Column Event Modal ────────────────────────────────────────────────────────
function ColEventModal({ field, title, existing, onApply, onClear, onClose }) {
  const [ev, setEv] = useState({
    event_id: existing?.event_id || 'open-tab-detail',
    container_id: existing?.container_id || 'header-action-fragment',
    filter_section: existing?.filter_section || 'Filters',
    filter_id: existing?.filter_id || '',
    input_expr: existing?.input_expr || '',
  })

  return (
    <Modal title={`Column Events — ${title}`} onClose={onClose} width="max-w-lg">
      <div className="p-4 space-y-3">
        <p className="text-xs text-[#374151]">OnClick event for column: <strong>{title}</strong></p>
        <p className="text-xs text-[#94A3B8]">Adds Events.Triggers.OnClick to the column's key-value slot element. Use 'Input expression' for map(&#123;tabName:..., filterId:..., filterValue:...&#125;) style events. Or use filterSection/filterId for Payload-based events.</p>
        <div className="space-y-2">
          {[['event_id','EventId'],['container_id','ContainerId'],['filter_section','Payload → filterSection (opt.)'],['filter_id','Payload → filterId (opt.)']].map(([k, lbl]) => (
            <Field key={k} label={lbl}>
              <input type="text" value={ev[k]} onChange={e => setEv(x => ({ ...x, [k]: e.target.value }))}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
            </Field>
          ))}
          <Field label="Input expression (opt.)">
            <textarea rows={2} value={ev.input_expr} onChange={e => setEv(x => ({ ...x, input_expr: e.target.value }))}
              className="w-full border rounded px-2 py-1 text-xs font-mono resize-none focus:outline-none focus:border-[#2563EB]"
              placeholder="e.g. map({tabName: 'Tab1', filterId: 'X', filterValue: FIELD})" />
          </Field>
        </div>
        <div className="flex gap-2 pt-1 border-t border-[#E2E8F0]">
          <button onClick={() => onApply(ev)} className="px-4 py-1.5 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold hover:bg-[#BFDBFE]">Apply</button>
          <button onClick={onClear} className="px-4 py-1.5 bg-[#FEF3C7] text-[#92400E] rounded text-sm hover:bg-[#FDE68A]">Clear Events</button>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Add Column Modal ──────────────────────────────────────────────────────────
function AddColModal({ onApply, onClose, attributes = [], dataSourcePath }) {
  const [field, setField] = useState('')
  const [title, setTitle] = useState('')

  const handleApply = () => {
    if (!field.trim()) return
    const t = title.trim() || field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    onApply(field.trim(), t)
  }

  return (
    <Modal title="Add Data Column" onClose={onClose} width="max-w-sm">
      <div className="p-4 space-y-3">
        <Field label="Data Field Key (Input)">
          {attributes.length > 0 ? (
            <div className="flex flex-col gap-1">
              <select 
                value={field} 
                onChange={e => setField(e.target.value)} 
                className="w-full border rounded px-2 py-1.5 text-xs bg-white text-[#1E3A8A] font-mono focus:outline-none focus:border-[#2563EB]"
              >
                <option value="">-- select attribute --</option>
                {attributes.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
              <input 
                type="text" 
                value={field} 
                onChange={e => setField(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-xs text-[#334155] font-mono focus:outline-none focus:border-[#2563EB]" 
                placeholder="e.g. FAILURE_PCT" 
                autoFocus
              />
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <input 
                type="text" 
                value={field} 
                onChange={e => setField(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-xs text-[#334155] font-mono focus:outline-none focus:border-[#2563EB]" 
                placeholder="e.g. FAILURE_PCT" 
                autoFocus
              />
              <p className="text-[10px] text-[#92400E] leading-tight">
                No child attributes detected for '{dataSourcePath}'. Ensure the upstream flow defines columns for this variable.
              </p>
            </div>
          )}
        </Field>
        <Field label="Display Title (LabelKey)">
          <input 
            type="text" 
            value={title} 
            onChange={e => setTitle(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-[#2563EB]" 
            placeholder="Leave blank to auto-generate" 
          />
        </Field>
        <div className="flex gap-2 pt-2 border-t border-[#E2E8F0]">
          <button onClick={handleApply} className="px-4 py-1.5 bg-[#1E3A8A] text-white rounded text-sm font-semibold hover:bg-[#1E40AF]">Add Column</button>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── TABLE CONFIG EDITOR ──────────────────────────────────────────────────────
function TableConfigEditor({ node, cfg, sty, updateNode, ensureInsightHost, varPool = {}, varSchemas = {} }) {
  const [colEditIdx, setColEditIdx] = useState(null)
  const [linkDlg, setLinkDlg] = useState(null)   // { idx, field, title, existing }
  const [eventDlg, setEventDlg] = useState(null) // { idx, field, title, existing }
  const [showAddCol, setShowAddCol] = useState(false)

  const allCols = cfg.Columns || []
  const cols = allCols.filter(c => !isInsightsCol(c))
  const ins = readInsights(allCols)
  const agenticCfg = readAgentic(node)
  const hasFooter = (node.Slots?.Default || []).some(c => c?.Container === 'footer-container')
  const hasCheckboxes = cfg.SelectionConfig?.ShowSelection ?? false
  const hasMultiselect = cfg.SelectionConfig?.SupportMultiSelect ?? true

  const dsPath = cfg.dataSourcePath || node.Init?.DataSourcePath || ''
  const attributes = varSchemas[dsPath] || []

  const update = fn => { const n = structuredClone(node); fn(n); updateNode(n) }

  const setField = (path, val) => update(n => {
    const parts = path.split('.')
    let obj = n
    for (const p of parts.slice(0, -1)) { if (!obj[p]) obj[p] = {}; obj = obj[p] }
    obj[parts[parts.length - 1]] = val
  })

  const toggleFooter = on => update(n => {
    if (!n.Slots) n.Slots = {}
    if (!n.Slots.Default) n.Slots.Default = []
    const idx = n.Slots.Default.findIndex(c => c?.Container === 'footer-container')
    if (on && idx === -1)
      n.Slots.Default.push({ Container: 'footer-container',
        Slots: { Footer: [{ Container: 'footer', Input: 'map(*)',
          Config: { PaginationConfig: { Paginate: true, Size: [10, 25, 50, 100], Slot: 'footer' } } }] } })
    else if (!on && idx !== -1) n.Slots.Default.splice(idx, 1)
  })

  const setAgentic = (enabled, agentId, question, args) => update(n => {
    if (!n.Slots) n.Slots = {}
    if (enabled) n.Slots.AgenticActions = buildAgenticSlot(agentId, question, args)
    else delete n.Slots.AgenticActions
  })

  const mutateInsightsCol = (n, enabled, field, agentId) => {
    if (!n.Config) n.Config = {}
    if (!n.Config.Columns) n.Config.Columns = []
    n.Config.Columns = n.Config.Columns.filter(c => !isInsightsCol(c))
    if (enabled) n.Config.Columns.unshift(buildInsightsCol(field, agentId))
  }
  const setInsights = (enabled, field, agentId) => {
    if (enabled && ensureInsightHost) {
      // Also ensures the sidebar Right-slot stack listener so the bulb's click actually opens
      // the flyout — a bare column-only toggle leaves the button wired to nothing.
      ensureInsightHost(n => mutateInsightsCol(n, enabled, field, agentId))
    } else {
      update(n => mutateInsightsCol(n, enabled, field, agentId))
    }
  }

  const handleApplyAddCol = (f, t) => {
    update(n => {
      if (!n.Config) n.Config = {}
      if (!n.Config.Columns) n.Config.Columns = []
      n.Config.Columns.push({
        UID: `Col_${f.replace(/\s/g, '_')}`,
        Config: { LabelKey: t, Sort: { Sortable: true, SortBy: f } },
        Slots: { Default: [{ Element: 'key-value', Input: f, Config: { AttributeType: 'string' } }] },
      })
    })
    setShowAddCol(false)
  }

  const addCol = (type) => {
    if (type === 'insight') {
      update(n => {
        if (!n.Config) n.Config = {}; if (!n.Config.Columns) n.Config.Columns = []
        n.Config.Columns.push({ Element: 'insights-cell', Config: { LabelKey: 'New Insight', columnType: 'insight' } })
      })
    } else {
      setShowAddCol(true)
    }
  }

  // Map non-insights column visual index i → actual index in allCols (inside update)
  const updateColByIdx = (i, fn) => update(n => {
    const nc = n.Config?.Columns || []
    const ai = nc.map((c, k) => (!isInsightsCol(c) ? k : -1)).filter(k => k !== -1)
    if (ai[i] !== undefined) fn(nc[ai[i]])
  })

  const removeCol = i => {
    update(n => {
      const nc = n.Config?.Columns || []
      const ai = nc.map((c, k) => (!isInsightsCol(c) ? k : -1)).filter(k => k !== -1)
      if (ai[i] !== undefined) nc.splice(ai[i], 1)
    })
    if (colEditIdx === i) setColEditIdx(null)
  }

  const moveCol = (i, dir) => {
    const t = i + dir
    if (t < 0 || t >= cols.length) return
    update(n => {
      const nc = n.Config?.Columns || []
      const ai = nc.map((c, k) => (!isInsightsCol(c) ? k : -1)).filter(k => k !== -1)
      ;[nc[ai[i]], nc[ai[t]]] = [nc[ai[t]], nc[ai[i]]]
    })
    if (colEditIdx === i) setColEditIdx(t)
    else if (colEditIdx === t) setColEditIdx(i)
  }

  return (
    <>
      {showAddCol && (
        <AddColModal 
          attributes={attributes} 
          dataSourcePath={dsPath}
          onApply={handleApplyAddCol} 
          onClose={() => setShowAddCol(false)} 
        />
      )}
      <SectionHdr label="Data Source" />
      <Field label="Data Source Path">
        {Object.keys(varPool).length > 0 ? (
          <div>
            <select value={cfg.dataSourcePath || ''} onChange={e => { const ds = e.target.value; setField('Config.dataSourcePath', ds); if (varPool[ds] && !cfg.backendVar) setField('Config.backendVar', varPool[ds]) }}
              className="w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
              <option value="">-- select from pool --</option>
              {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
            </select>
            <input type="text" value={cfg.dataSourcePath || ''} onChange={e => setField('Config.dataSourcePath', e.target.value)}
              className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB] mt-1" placeholder="TableData" />
          </div>
        ) : (
          <input type="text" value={cfg.dataSourcePath || ''} onChange={e => setField('Config.dataSourcePath', e.target.value)}
            className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="TableData" />
        )}
      </Field>
      <Field label="Backend Variable">
        {Object.keys(varPool).length > 0 ? (
          <div className="flex flex-col gap-1">
            <select value={cfg.backendVar || ''} onChange={e => setField('Config.backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs bg-white text-[#1E3A8A] font-mono focus:outline-none focus:border-[#2563EB]">
              <option value="">-- select backend variable --</option>
              {[...new Set(Object.values(varPool))].map((v, idx) => <option key={idx} value={v}>{v}</option>)}
            </select>
            <input type="text" value={cfg.backendVar || ''} onChange={e => setField('Config.backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="object::TableDataJs.result" />
          </div>
        ) : (
          <input type="text" value={cfg.backendVar || ''} onChange={e => setField('Config.backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="object::TableDataJs.result" />
        )}
      </Field>
      <Field label="Title">
        <input type="text" value={cfg.title || ''} onChange={e => setField('Config.title', e.target.value)}
          className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
      </Field>

      <SectionHdr label="Table Options" />
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <input type="checkbox" id="tbl-cb" checked={hasCheckboxes}
            onChange={e => setField('Config.SelectionConfig.ShowSelection', e.target.checked)} className="accent-[#1E3A8A]" />
          <label htmlFor="tbl-cb" className="text-xs text-[#374151]">Show Row Checkboxes</label>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="tbl-ms" checked={hasMultiselect}
            onChange={e => setField('Config.SelectionConfig.SupportMultiSelect', e.target.checked)} className="accent-[#1E3A8A]" />
          <label htmlFor="tbl-ms" className="text-xs text-[#374151]">Multi-Select Rows</label>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="tbl-footer" checked={hasFooter}
            onChange={e => toggleFooter(e.target.checked)} className="accent-[#1E3A8A]" />
          <label htmlFor="tbl-footer" className="text-xs font-semibold text-[#374151]">Pagination Footer</label>
        </div>
      </div>
      <Field label="Pagination Page Size">
        <input type="number" value={cfg.PaginationConfig?.PageSize || ''} placeholder="50"
          onChange={e => setField('Config.PaginationConfig.PageSize', parseInt(e.target.value) || 50)}
          className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
      </Field>

      <SectionHdr label="AI / Agentic Actions" />
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <input type="checkbox" id="tbl-ag" checked={agenticCfg.enabled}
            onChange={e => setAgentic(e.target.checked, agenticCfg.agentId, agenticCfg.question, agenticCfg.args)}
            className="accent-[#1E3A8A]" />
          <label htmlFor="tbl-ag" className="text-xs font-semibold text-[#374151]">AI Menu</label>
        </div>
        {agenticCfg.enabled && (
          <div className="pl-3 border-l-2 border-[#C7D2FE] space-y-1.5">
            <Field label="Agent ID">
              <input type="text" value={agenticCfg.agentId}
                onChange={e => setAgentic(true, e.target.value, agenticCfg.question, agenticCfg.args)}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
            </Field>
            <Field label="Question to Agent">
              <input type="text" value={agenticCfg.question}
                onChange={e => setAgentic(true, agenticCfg.agentId, e.target.value, agenticCfg.args)}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]"
                placeholder="Analyze and troubleshoot failures..." />
            </Field>
            <Field label="Action Arguments (comma-sep field names)">
              <input type="text" value={(agenticCfg.args || []).join(', ')}
                onChange={e => setAgentic(true, agenticCfg.agentId, agenticCfg.question,
                  e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]"
                placeholder="field1, field2, field3" />
            </Field>
          </div>
        )}
      </div>

      <SectionHdr label="Insights Column" />
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <input type="checkbox" id="tbl-ins" checked={ins.enabled}
            onChange={e => setInsights(e.target.checked, ins.field, ins.agentId)} className="accent-[#1E3A8A]" />
          <label htmlFor="tbl-ins" className="text-xs font-semibold text-[#374151]">💡 Enable Insights Column</label>
        </div>
        {ins.enabled && (
          <div className="pl-3 border-l-2 border-[#FDE68A] space-y-1.5">
            <Field label="Field">
              <input type="text" value={ins.field} onChange={e => setInsights(true, e.target.value, ins.agentId)}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="TicketsList" />
            </Field>
            <Field label="Agent ID">
              <input type="text" value={ins.agentId} onChange={e => setInsights(true, ins.field, e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="obe-ticketDetailFlyout" />
            </Field>
          </div>
        )}
      </div>

      <SectionHdr label="Table Style Colors" />
      {['textColor','rowEvenBackgroundColor','rowOddBackgroundColor','headerBackgroundColor','tableBorderColor','hoverBackgroundColor'].map(prop => (
        <Field key={prop} label={prop}>
          <div className="flex gap-1">
            <input type="text" value={sty[prop] || ''} onChange={e => setField(`Style.${prop}`, e.target.value)}
              className="flex-1 border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="#..." />
            {sty[prop] && <div className="w-6 h-6 rounded border shrink-0" style={{ backgroundColor: sty[prop] }} />}
          </div>
        </Field>
      ))}

      <SectionHdr label="Columns" />
      <button onClick={addCol} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded mb-2">+ Add Column</button>
      {ins.enabled && (
        <div className="flex items-center gap-2 px-2 py-1.5 bg-[#FFFBEB] border border-[#FDE68A] rounded mb-1.5 text-xs text-[#92400E]">
          <span>💡</span><span className="flex-1 font-medium">Insights (auto-managed via Insights Column section)</span>
        </div>
      )}
      {cols.map((col, i) => {
        const labelKey = col.Config?.LabelKey || `Column ${i + 1}`
        const fk = getColFieldKey(col)
        const badge = linkBadge(col)
        const open = colEditIdx === i
        return (
          <div key={i} className={`border rounded mb-1.5 ${open ? 'border-[#2563EB]' : 'border-[#E2E8F0]'}`}>
            <div className="flex items-center gap-1 px-2 py-1.5 bg-[#F8FAFC] rounded-t cursor-pointer select-none"
              onClick={() => setColEditIdx(open ? null : i)}>
              <span className="text-xs font-mono text-[#94A3B8] shrink-0 truncate" style={{ maxWidth: 72 }}>{fk}</span>
              <span className="text-xs font-semibold text-[#374151] flex-1 truncate">{labelKey}</span>
              {badge && <span className="text-xs text-[#4B5563] shrink-0 truncate" style={{ maxWidth: 120 }} title={badge}>{badge}</span>}
              <button onClick={e => { e.stopPropagation(); moveCol(i, -1) }} className="text-[#94A3B8] text-xs hover:text-[#374151]">▲</button>
              <button onClick={e => { e.stopPropagation(); moveCol(i, 1) }} className="text-[#94A3B8] text-xs hover:text-[#374151]">▼</button>
              <button onClick={e => { e.stopPropagation(); setLinkDlg({ idx: i, field: fk, title: labelKey, existing: readColLink(col) }) }}
                className="text-[#4338CA] text-xs px-0.5 hover:text-[#3730A3]" title="Configure Link">🔗</button>
              <button onClick={e => { e.stopPropagation(); setEventDlg({ idx: i, field: fk, title: labelKey, existing: readColEvent(col) }) }}
                className="text-[#047857] text-xs px-0.5 hover:text-[#065F46]" title="Configure Event">⚡</button>
              <button onClick={e => { e.stopPropagation(); if (confirm(`Delete column "${labelKey}"?`)) removeCol(i) }}
                className="text-red-400 text-xs px-0.5 hover:text-red-600">✕</button>
            </div>
            {open && (
              <div className="px-2 pb-2 space-y-1.5 border-t border-[#E2E8F0]">
                <Field label="Column Header (LabelKey)">
                  <input type="text" value={labelKey}
                    onChange={e => updateColByIdx(i, c => { if (!c.Config) c.Config = {}; c.Config.LabelKey = e.target.value })}
                    className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
                </Field>
                <Field label="Field / Sort By">
                  <input type="text" value={fk}
                    onChange={e => updateColByIdx(i, c => {
                      if (!c.Config) c.Config = {}
                      c.Config.Sort = { ...(c.Config.Sort || {}), SortBy: e.target.value }
                      const kv = c.Slots?.Default?.find(s => s?.Element === 'key-value')
                      if (kv) kv.Input = e.target.value
                      const lk = c.Slots?.Default?.find(s => s?.Element === 'link')
                      if (lk) lk.Input = e.target.value
                    })}
                    className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
                </Field>
                <Field label="Sortable">
                  <input type="checkbox" checked={col.Config?.Sort?.Sortable ?? true}
                    onChange={e => updateColByIdx(i, c => {
                      if (!c.Config) c.Config = {}
                      if (!c.Config.Sort) c.Config.Sort = {}
                      c.Config.Sort.Sortable = e.target.checked
                    })} className="accent-[#1E3A8A]" />
                </Field>
                <Field label="Width CSS (e.g. 120px)">
                  <input type="text" value={col.Config?.Width || ''}
                    onChange={e => updateColByIdx(i, c => { if (!c.Config) c.Config = {}; c.Config.Width = e.target.value || undefined })}
                    className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
                </Field>
                {badge && (
                  <div className="text-xs text-[#374151] bg-[#F1F5F9] rounded px-2 py-1 flex items-center gap-2">
                    <span className="text-[#94A3B8] shrink-0">Link/Event:</span>
                    <span className="flex-1 truncate">{badge}</span>
                    <button onClick={() => updateColByIdx(i, c => { applyColLink(c, null); applyColEvent(c, null) })}
                      className="text-red-400 hover:text-red-600 shrink-0 text-xs">clear</button>
                  </div>
                )}
                {/* Slot elements — shows Conditions on each inner element */}
                {(col.Slots?.Default || []).length > 0 && (
                  <div className="mt-2 border-t border-[#E2E8F0] pt-2 space-y-1.5">
                    <p className="text-xs font-bold text-[#374151] uppercase tracking-wider">Slot Elements</p>
                    {(col.Slots.Default || []).map((el, ei) => {
                      const elType = el.Element || el.Container || '?'
                      const elInput = (el.Input || '')
                      const hasCond = !!(el.Conditions?.length)
                      return (
                        <div key={ei} className={`border rounded ${hasCond ? 'border-yellow-300' : 'border-[#E2E8F0]'}`}>
                          <div className={`flex items-center gap-1.5 px-2 py-1 border-b border-[#E2E8F0] ${hasCond ? 'bg-yellow-50' : 'bg-[#F8FAFC]'}`}>
                            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded text-white shrink-0"
                              style={{ backgroundColor: COMP_COLORS[elType] || '#94A3B8' }}>{elType}</span>
                            {elInput && (
                              <span className="text-xs text-[#64748B] flex-1 truncate font-mono" title={elInput}>
                                {elInput.length > 28 ? elInput.slice(0, 28) + '…' : elInput}
                              </span>
                            )}
                            {hasCond && <span className="text-xs text-yellow-700 font-semibold shrink-0">⚑ {el.Conditions.length}</span>}
                          </div>
                          <div className="px-2 py-1.5">
                            <ConditionsEditor
                              conditions={el.Conditions || []}
                              onChange={conds => updateColByIdx(i, c => {
                                const slot = c.Slots?.Default?.[ei]
                                if (!slot) return
                                if (conds.length) slot.Conditions = conds
                                else delete slot.Conditions
                              })}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
      {cols.length === 0 && !ins.enabled && <p className="text-xs text-[#94A3B8] italic">No columns defined.</p>}

      {linkDlg && (
        <ColLinkModal field={linkDlg.field} title={linkDlg.title} existing={linkDlg.existing}
          onApply={lk => { updateColByIdx(linkDlg.idx, c => applyColLink(c, lk)); setLinkDlg(null) }}
          onClear={() => { updateColByIdx(linkDlg.idx, c => applyColLink(c, null)); setLinkDlg(null) }}
          onClose={() => setLinkDlg(null)}
        />
      )}
      {eventDlg && (
        <ColEventModal field={eventDlg.field} title={eventDlg.title} existing={eventDlg.existing}
          onApply={ev => { updateColByIdx(eventDlg.idx, c => applyColEvent(c, ev)); setEventDlg(null) }}
          onClear={() => { updateColByIdx(eventDlg.idx, c => applyColEvent(c, null)); setEventDlg(null) }}
          onClose={() => setEventDlg(null)}
        />
      )}
    </>
  )
}

// ── CHART CONFIG EDITOR ──────────────────────────────────────────────────────
function ChartConfigEditor({ node, cfg, updateNode, chartType, varPool = {}, varSchemas = {} }) {
  const [seriesEditIdx, setSeriesEditIdx] = useState(null)

  const rawMappings = cfg.dataMapping?.seriesMappings ?? cfg.seriesMappings ?? []
  const dsPath = node.Init?.DataSourcePath || cfg.dataSourcePath || ''
  const attributes = varSchemas[dsPath] || []

  const parseSeries = (mappings) => (mappings || []).map(s => {
    const fm = s.fieldMappings || {}
    const xField = Object.keys(fm).find(k => fm[k] === 'name') || ''
    const yField = Object.keys(fm).find(k => fm[k] === 'y') || ''
    const opts = s.staticOptions || {}
    return {
      name: opts.name || 'Series',
      xField,
      yField,
      color: opts.color || (opts.colorByPoint ? 'colorByPoint' : ''),
      seriesType: s.seriesType || chartType,
      sourceDataPath: s.sourceDataPath || dsPath,
      flip: s.fm_inverted === true,
      yAxis: opts.yAxis ?? 0,
    }
  })

  const buildMappings = (series) => series.map(s => ({
    seriesType: s.seriesType || chartType,
    sourceDataPath: s.sourceDataPath || dsPath,
    fieldMappings: s.flip ? { [s.yField]: 'name', [s.xField]: 'y' } : { [s.xField]: 'name', [s.yField]: 'y' },
    staticOptions: {
      name: s.name,
      color: s.color === 'colorByPoint' ? undefined : s.color,
      colorByPoint: s.color === 'colorByPoint' ? true : undefined,
      yAxis: s.yAxis || 0,
    },
    ...(s.flip ? { fm_inverted: true } : {}),
  }))

  const series = parseSeries(rawMappings)
  const hc = cfg.highchartsOptions || {}
  const hcChart = hc.chart || {}
  const hcXAxis = Array.isArray(hc.xAxis) ? (hc.xAxis[0] || {}) : (hc.xAxis || {})
  const hcYAxisArr = Array.isArray(hc.yAxis) ? hc.yAxis : (hc.yAxis ? [hc.yAxis] : [{}])
  const hcPO = hc.plotOptions?.series || {}
  const hcDL = (hcPO.dataLabels && typeof hcPO.dataLabels === 'object' && !Array.isArray(hcPO.dataLabels)) ? hcPO.dataLabels : {}
  const legend = hc.legend || {}
  const hcTooltip = hc.tooltip || {}
  const onClickEv = node.Events?.Triggers?.OnClick?.[0] || {}
  const stackingMode = hc.plotOptions?.series?.stacking || hc.plotOptions?.[chartType]?.stacking || ''

  const update = fn => { const n = structuredClone(node); fn(n); updateNode(n) }

  const setSeriesArr = newSeries => {
    update(n => {
      if (!n.Config) n.Config = {}
      const mappings = buildMappings(newSeries)
      if (!n.Config.dataMapping) n.Config.dataMapping = {}
      n.Config.dataMapping.seriesMappings = mappings
      n.Config.seriesMappings = mappings
    })
  }
  const setSeries = (i, key, val) => { const arr = [...series]; arr[i] = { ...arr[i], [key]: val }; setSeriesArr(arr) }
  const addSeries = () => setSeriesArr([...series, { name: `Series ${series.length + 1}`, xField: '', yField: '', color: '', seriesType: chartType, flip: false, yAxis: 0 }])
  const removeSeries = i => { setSeriesArr(series.filter((_, j) => j !== i)); if (seriesEditIdx === i) setSeriesEditIdx(null) }

  // Deep set into highchartsOptions; undefined removes the key
  const setHC = (path, val) => {
    update(n => {
      if (!n.Config) n.Config = {}
      if (!n.Config.highchartsOptions) n.Config.highchartsOptions = {}
      const parts = path.split('.')
      let obj = n.Config.highchartsOptions
      for (const p of parts.slice(0, -1)) { if (!obj[p]) obj[p] = {}; obj = obj[p] }
      if (val === '' || val === undefined) delete obj[parts[parts.length - 1]]
      else obj[parts[parts.length - 1]] = val
    })
  }

  // yAxis can be a single object OR an array of axis objects (dual/multi-axis combo charts).
  // setHC alone corrupts array-form yAxis (it would set stray string keys on the array), so
  // this always normalizes to array form and writes into the correct axis index.
  const setYAxis = (axisIdx, key, val) => {
    update(n => {
      if (!n.Config) n.Config = {}
      if (!n.Config.highchartsOptions) n.Config.highchartsOptions = {}
      const hco = n.Config.highchartsOptions
      const arr = Array.isArray(hco.yAxis) ? hco.yAxis : (hco.yAxis ? [hco.yAxis] : [{}])
      while (arr.length <= axisIdx) arr.push({})
      const parts = key.split('.')
      let obj = arr[axisIdx]
      for (const p of parts.slice(0, -1)) { if (!obj[p]) obj[p] = {}; obj = obj[p] }
      if (val === '' || val === undefined) delete obj[parts[parts.length - 1]]
      else obj[parts[parts.length - 1]] = val
      hco.yAxis = arr
    })
  }
  const addYAxis = () => update(n => {
    if (!n.Config) n.Config = {}
    if (!n.Config.highchartsOptions) n.Config.highchartsOptions = {}
    const hco = n.Config.highchartsOptions
    const arr = Array.isArray(hco.yAxis) ? hco.yAxis : (hco.yAxis ? [hco.yAxis] : [{}])
    arr.push({ title: { text: 'Secondary' }, opposite: true, min: 0 })
    hco.yAxis = arr
  })
  const removeYAxis = axisIdx => update(n => {
    const hco = n.Config?.highchartsOptions
    if (!hco) return
    const arr = Array.isArray(hco.yAxis) ? hco.yAxis : (hco.yAxis ? [hco.yAxis] : [{}])
    const next = arr.filter((_, i) => i !== axisIdx)
    hco.yAxis = next.length <= 1 ? (next[0] || {}) : next
  })

  const setStacking = val => {
    update(n => {
      if (!n.Config) n.Config = {}
      if (!n.Config.highchartsOptions) n.Config.highchartsOptions = {}
      if (!n.Config.highchartsOptions.plotOptions) n.Config.highchartsOptions.plotOptions = {}
      const po = n.Config.highchartsOptions.plotOptions
      for (const t of ['series','bar','column','area','areaspline']) if (po[t]?.stacking !== undefined) delete po[t].stacking
      if (val) {
        const ct = n.Config.highchartsOptions.chart?.type || chartType
        if (!po[ct]) po[ct] = {}
        po[ct].stacking = val
        if (!po.series) po.series = {}
        po.series.stacking = val
      }
    })
  }

  const setChartEvent = (field, val) => {
    update(n => {
      if (!n.Events) n.Events = {}
      if (!n.Events.Triggers) n.Events.Triggers = {}
      const ex = { ...(n.Events.Triggers.OnClick?.[0] || {}) }
      if (val) ex[field] = val; else delete ex[field]
      n.Events.Triggers.OnClick = Object.keys(ex).length ? [ex] : undefined
      if (!n.Events.Triggers.OnClick) delete n.Events.Triggers.OnClick
    })
  }

  const setPayload = (key, val) => {
    update(n => {
      if (!n.Events) n.Events = {}
      if (!n.Events.Triggers) n.Events.Triggers = {}
      const ex = { ...(n.Events.Triggers.OnClick?.[0] || {}) }
      const p = { ...(ex.Payload || {}) }
      if (val) p[key] = val; else delete p[key]
      if (Object.keys(p).length) ex.Payload = p; else delete ex.Payload
      n.Events.Triggers.OnClick = Object.keys(ex).length ? [ex] : undefined
      if (!n.Events.Triggers.OnClick) delete n.Events.Triggers.OnClick
    })
  }

  const num = v => v !== '' && v !== undefined && v !== null ? Number(v) : undefined
  const CI = 'w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]'
  const CB = 'accent-[#1E3A8A]'
  const SEL = 'w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]'

  return (
    <>
      {/* ── Data Source ──────────────────────────────────────────── */}
      <SectionHdr label="Data Source" />
      <Field label="Data Source Path">
        {Object.keys(varPool).length > 0 ? (
          <div>
            <select value={dsPath}
              onChange={e => { const ds = e.target.value; update(n => { if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = ds; if (!n.Config) n.Config = {}; n.Config.dataSourcePath = ds; if (varPool[ds] && !n.Config.backendVar) n.Config.backendVar = varPool[ds] }) }}
              className={SEL}>
              <option value="">-- select from pool --</option>
              {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
            </select>
            <p className="text-[10px] text-[#94A3B8] mt-0.5">🗃 {Object.keys(varPool).length} vars in pool · or type below</p>
            <input type="text" value={dsPath}
              onChange={e => update(n => { if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = e.target.value; if (!n.Config) n.Config = {}; n.Config.dataSourcePath = e.target.value })}
              className={`${CI} mt-0.5`} placeholder="ChartData" />
          </div>
        ) : (
          <input type="text" value={dsPath}
            onChange={e => update(n => { if (!n.Init) n.Init = { Type: 'value-array' }; n.Init.DataSourcePath = e.target.value; if (!n.Config) n.Config = {}; n.Config.dataSourcePath = e.target.value })}
            className={CI} placeholder="ChartData" />
        )}
      </Field>
      <Field label="Backend Variable">
        {Object.keys(varPool).length > 0 ? (
          <div className="flex flex-col gap-1">
            <select value={cfg.backendVar || ''} onChange={e => update(n => { if (!n.Config) n.Config = {}; n.Config.backendVar = e.target.value })} className={SEL}>
              <option value="">-- select backend variable --</option>
              {[...new Set(Object.values(varPool))].map((v, idx) => <option key={idx} value={v}>{v}</option>)}
            </select>
            <input type="text" value={cfg.backendVar || ''}
              onChange={e => update(n => { if (!n.Config) n.Config = {}; n.Config.backendVar = e.target.value })}
              className={CI} placeholder="object::ChartDataJs.result" />
          </div>
        ) : (
          <input type="text" value={cfg.backendVar || ''}
            onChange={e => update(n => { if (!n.Config) n.Config = {}; n.Config.backendVar = e.target.value })}
            className={CI} placeholder="object::ChartDataJs.result" />
        )}
      </Field>
      <Field label="Chart Type">
        <select value={chartType}
          onChange={e => update(n => { if (!n.Config) n.Config = {}; if (!n.Config.highchartsOptions) n.Config.highchartsOptions = {}; if (!n.Config.highchartsOptions.chart) n.Config.highchartsOptions.chart = {}; n.Config.highchartsOptions.chart.type = e.target.value })}
          className={SEL}>
          {['pie','bar','line','column','spline','area','areaspline','scatter','waterfall','sunburst'].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </Field>

      {/* ── Series ───────────────────────────────────────────────── */}
      <SectionHdr label="Series" />
      <button onClick={addSeries} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded mb-2">+ Add Series</button>
      {series.map((s, i) => (
        <div key={i} className="border border-[#E2E8F0] rounded mb-1.5">
          <div className="flex items-center gap-1 px-2 py-1.5 bg-[#F8FAFC] rounded">
            <span className="text-xs font-semibold text-[#374151] flex-1 truncate">{s.name || `Series ${i + 1}`}</span>
            {s.seriesType && s.seriesType !== chartType && (
              <span className="text-[9px] px-1 py-0.5 rounded bg-[#EDE9FE] text-[#5B21B6] font-mono shrink-0" title="Series type overrides chart type (combo chart)">{s.seriesType}</span>
            )}
            {hcYAxisArr.length > 1 && (
              <span className={`text-[9px] px-1 py-0.5 rounded font-mono shrink-0 ${s.yAxis ? 'bg-[#FEF3C7] text-[#92400E]' : 'bg-[#DBEAFE] text-[#1E3A8A]'}`} title={s.yAxis ? 'Secondary (right) axis' : 'Primary (left) axis'}>
                axis {s.yAxis || 0}
              </span>
            )}
            {s.color && <div className="w-3 h-3 rounded-full border shrink-0" style={{ backgroundColor: s.color === 'colorByPoint' ? 'transparent' : s.color, borderStyle: s.color === 'colorByPoint' ? 'dashed' : 'solid' }} />}
            <button onClick={() => setSeries(i, 'flip', !s.flip)} title="Flip X↔Y axes (fm_inverted)"
              className={`text-xs px-1 font-bold ${s.flip ? 'text-[#92400E] bg-[#FEF3C7] rounded' : 'text-[#94A3B8]'}`}>↕</button>
            <button onClick={() => setSeriesEditIdx(i)} className="text-[#2563EB] text-xs px-1">✎</button>
            <button onClick={() => removeSeries(i)} className="text-red-400 text-xs px-1">✕</button>
          </div>
        </div>
      ))}

      {seriesEditIdx !== null && (
        <SeriesConfigModal
          series={series[seriesEditIdx]}
          chartType={chartType}
          attributes={attributes}
          axisCount={hcYAxisArr.length}
          onApply={s => {
            const arr = [...series]
            arr[seriesEditIdx] = s
            setSeriesArr(arr)
            setSeriesEditIdx(null)
          }}
          onClose={() => setSeriesEditIdx(null)}
        />
      )}
      {series.length === 0 && <p className="text-xs text-[#94A3B8] italic">No series — click + Add Series.</p>}

      {/* ── Legend ───────────────────────────────────────────────── */}
      <SectionHdr label="Legend" />
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <input type="checkbox" id="legend-enabled" checked={legend.enabled !== false}
            onChange={e => setHC('legend.enabled', e.target.checked)} className={CB} />
          <label htmlFor="legend-enabled" className="text-xs text-[#374151]">Show Legend</label>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <Field label="Layout">
            <select value={legend.layout || 'horizontal'} onChange={e => setHC('legend.layout', e.target.value)} className={SEL}>
              {['horizontal', 'vertical'].map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Vertical Align">
            <select value={legend.verticalAlign || 'bottom'} onChange={e => setHC('legend.verticalAlign', e.target.value)} className={SEL}>
              {['top', 'middle', 'bottom'].map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Align">
            <select value={legend.align || 'center'} onChange={e => setHC('legend.align', e.target.value)} className={SEL}>
              {['left', 'center', 'right'].map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Y Offset">
            <input type="number" value={legend.y ?? ''} onChange={e => setHC('legend.y', e.target.value !== '' ? parseInt(e.target.value) : undefined)} className={CI} placeholder="0" />
          </Field>
        </div>
      </div>

      {/* ── Stacking ─────────────────────────────────────────────── */}
      <SectionHdr label="Stacking" />
      <Field label="Stack Mode">
        <select value={stackingMode} onChange={e => setStacking(e.target.value || undefined)} className={SEL}>
          <option value="">None</option>
          <option value="normal">Normal</option>
          <option value="percent">Percent</option>
        </select>
      </Field>

      {/* ── Chart ────────────────────────────────────────────────── */}
      <SectionHdr label="Chart" />
      <div className="space-y-1.5">
        <div className="grid grid-cols-2 gap-1.5">
          <Field label="Height (px)">
            <input type="number" value={hcChart.height || ''} onChange={e => setHC('chart.height', e.target.value ? parseInt(e.target.value) : undefined)} className={CI} placeholder="auto" />
          </Field>
          <Field label="Zoom Type">
            <select value={hcChart.zoomType || ''} onChange={e => setHC('chart.zoomType', e.target.value || undefined)} className={SEL}>
              <option value="">None</option>
              <option value="xy">xy (both)</option>
              <option value="x">x only</option>
              <option value="y">y only</option>
            </select>
          </Field>
          <Field label="Margin Left">
            <input type="number" value={hcChart.marginLeft ?? ''} onChange={e => setHC('chart.marginLeft', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Margin Right">
            <input type="number" value={hcChart.marginRight ?? ''} onChange={e => setHC('chart.marginRight', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Margin Bottom">
            <input type="number" value={hcChart.marginBottom ?? ''} onChange={e => setHC('chart.marginBottom', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Spacing Bottom">
            <input type="number" value={hcChart.spacingBottom ?? ''} onChange={e => setHC('chart.spacingBottom', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Spacing Left">
            <input type="number" value={hcChart.spacingLeft ?? ''} onChange={e => setHC('chart.spacingLeft', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Spacing Right">
            <input type="number" value={hcChart.spacingRight ?? ''} onChange={e => setHC('chart.spacingRight', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
        </div>
        <div className="flex items-center gap-4 mt-1">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="ch-pan" checked={!!hcChart.panning}
              onChange={e => setHC('chart.panning', e.target.checked || undefined)} className={CB} />
            <label htmlFor="ch-pan" className="text-xs text-[#374151]">Panning</label>
          </div>
          <Field label="Pan Key">
            <select value={hcChart.panKey || 'shift'} onChange={e => setHC('chart.panKey', e.target.value)} className={`${SEL} w-20`}>
              {['shift','ctrl','alt'].map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
        </div>
      </div>

      {/* ── X Axis ───────────────────────────────────────────────── */}
      <SectionHdr label="X Axis" />
      <div className="space-y-1.5">
        <div className="grid grid-cols-2 gap-1.5">
          <Field label="Title">
            <input type="text" value={hcXAxis.title?.text || ''} onChange={e => setHC('xAxis.title.text', e.target.value || undefined)} className={CI} placeholder="X label" />
          </Field>
          <Field label="Type">
            <select value={hcXAxis.type || 'category'} onChange={e => setHC('xAxis.type', e.target.value)} className={SEL}>
              {['category','datetime','linear','logarithmic'].map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Min">
            <input type="number" value={hcXAxis.min ?? ''} onChange={e => setHC('xAxis.min', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Grid Line Width">
            <input type="number" value={hcXAxis.gridLineWidth ?? ''} onChange={e => setHC('xAxis.gridLineWidth', num(e.target.value))} className={CI} placeholder="0" />
          </Field>
          <Field label="Labels Font Size">
            <input type="text" value={hcXAxis.labels?.style?.fontSize || ''} onChange={e => setHC('xAxis.labels.style.fontSize', e.target.value || undefined)} className={CI} placeholder="11px" />
          </Field>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="x-cross" checked={!!hcXAxis.crosshair}
              onChange={e => setHC('xAxis.crosshair', e.target.checked || undefined)} className={CB} />
            <label htmlFor="x-cross" className="text-xs text-[#374151]">Crosshair</label>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="x-scroll"
              checked={!!(typeof hcXAxis.scrollbar === 'object' ? hcXAxis.scrollbar?.enabled : hcXAxis.scrollbar)}
              onChange={e => setHC('xAxis.scrollbar', e.target.checked ? { enabled: true } : undefined)} className={CB} />
            <label htmlFor="x-scroll" className="text-xs text-[#374151]">Scrollbar</label>
          </div>
        </div>
      </div>

      {/* ── Y Axis ───────────────────────────────────────────────── */}
      <SectionHdr label="Y Axis" />
      {hcYAxisArr.map((axis, idx) => (
        <YAxisFields key={idx} axis={axis} idx={idx} isPrimary={idx === 0}
          onSet={(key, val) => setYAxis(idx, key, val)}
          onRemove={hcYAxisArr.length > 1 ? () => removeYAxis(idx) : null}
          CI={CI} CB={CB} num={num} />
      ))}
      {hcYAxisArr.length === 1 && (
        <button onClick={addYAxis} className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded mb-2">
          + Add Secondary Y Axis (dual-axis combo chart)
        </button>
      )}
      {hcYAxisArr.length > 1 && (
        <p className="text-[10px] text-[#94A3B8] mb-2">
          Assign each series to an axis via its ✎ edit → Y Axis field. Axis 0 = primary (left), Axis 1 = secondary (right).
        </p>
      )}

      {/* ── Plot Options ─────────────────────────────────────────── */}
      <SectionHdr label="Plot Options (series)" />
      <div className="space-y-1.5">
        <div className="grid grid-cols-2 gap-1.5">
          <Field label="Point Width">
            <input type="number" value={hcPO.pointWidth ?? ''} onChange={e => setHC('plotOptions.series.pointWidth', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Max Point Width">
            <input type="number" value={hcPO.maxPointWidth ?? ''} onChange={e => setHC('plotOptions.series.maxPointWidth', num(e.target.value))} className={CI} placeholder="auto" />
          </Field>
          <Field label="Point Padding">
            <input type="number" step="0.01" value={hcPO.pointPadding ?? ''} onChange={e => setHC('plotOptions.series.pointPadding', e.target.value !== '' ? parseFloat(e.target.value) : undefined)} className={CI} placeholder="0.1" />
          </Field>
          <Field label="Group Padding">
            <input type="number" step="0.01" value={hcPO.groupPadding ?? ''} onChange={e => setHC('plotOptions.series.groupPadding', e.target.value !== '' ? parseFloat(e.target.value) : undefined)} className={CI} placeholder="0.2" />
          </Field>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="po-dl" checked={!!hcDL.enabled}
              onChange={e => setHC('plotOptions.series.dataLabels.enabled', e.target.checked || undefined)} className={CB} />
            <label htmlFor="po-dl" className="text-xs text-[#374151]">Data Labels</label>
          </div>
          {hcDL.enabled && (
            <div className="flex items-center gap-2">
              <input type="checkbox" id="po-dl-inside" checked={hcDL.inside !== false}
                onChange={e => setHC('plotOptions.series.dataLabels.inside', e.target.checked)} className={CB} />
              <label htmlFor="po-dl-inside" className="text-xs text-[#374151]">Inside</label>
            </div>
          )}
        </div>
        {hcDL.enabled && (
          <div className="pl-3 border-l-2 border-[#E2E8F0] space-y-1.5">
            <Field label="Label Format">
              <input type="text" value={hcDL.format || '{point.y:,.0f}'}
                onChange={e => setHC('plotOptions.series.dataLabels.format', e.target.value || undefined)} className={CI} placeholder="{point.y:,.0f}" />
            </Field>
            <Field label="Label Font Size">
              <input type="text" value={hcDL.style?.fontSize || ''}
                onChange={e => setHC('plotOptions.series.dataLabels.style.fontSize', e.target.value || undefined)} className={CI} placeholder="11px" />
            </Field>
          </div>
        )}
      </div>

      {/* ── Tooltip ──────────────────────────────────────────────── */}
      <SectionHdr label="Tooltip" />
      <div className="space-y-1.5">
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="tt-shared" checked={!!hcTooltip.shared}
              onChange={e => setHC('tooltip.shared', e.target.checked || undefined)} className={CB} />
            <label htmlFor="tt-shared" className="text-xs text-[#374151]">Shared</label>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="tt-html" checked={!!hcTooltip.useHTML}
              onChange={e => setHC('tooltip.useHTML', e.target.checked || undefined)} className={CB} />
            <label htmlFor="tt-html" className="text-xs text-[#374151]">Use HTML</label>
          </div>
        </div>
        <Field label="Header Format">
          <input type="text" value={hcTooltip.headerFormat || ''} onChange={e => setHC('tooltip.headerFormat', e.target.value || undefined)} className={CI} placeholder="<b>{point.key}</b><br/>" />
        </Field>
        <Field label="Point Format">
          <input type="text" value={hcTooltip.pointFormat || ''} onChange={e => setHC('tooltip.pointFormat', e.target.value || undefined)} className={CI} placeholder="{series.name}: {point.y}" />
        </Field>
      </div>

      {/* ── Chart Events ─────────────────────────────────────────── */}
      <SectionHdr label="Chart Events (OnClick)" />
      <p className="text-xs text-[#94A3B8] mb-1.5">Sets Events.Triggers.OnClick on this chart element — fires when user clicks the chart.</p>
      <div className="space-y-1.5">
        <Field label="EventId">
          <input type="text" value={onClickEv.EventId || ''} onChange={e => setChartEvent('EventId', e.target.value)} className={CI} placeholder="open-tab-detail" />
        </Field>
        <Field label="ContainerId">
          <input type="text" value={onClickEv.ContainerId || ''} onChange={e => setChartEvent('ContainerId', e.target.value)} className={CI} placeholder="header-action-fragment" />
        </Field>
        <Field label="Payload filterSection">
          <input type="text" value={onClickEv.Payload?.filterSection || ''} onChange={e => setPayload('filterSection', e.target.value)} className={CI} placeholder="Filters" />
        </Field>
        <Field label="Payload filterId">
          <input type="text" value={onClickEv.Payload?.filterId || ''} onChange={e => setPayload('filterId', e.target.value)} className={CI} placeholder="FILTER_KEY" />
        </Field>
        {(onClickEv.EventId || onClickEv.ContainerId) && (
          <button onClick={() => update(n => { if (n.Events?.Triggers) delete n.Events.Triggers.OnClick })}
            className="text-xs px-2 py-0.5 bg-[#FEE2E2] text-[#991B1B] rounded">Clear Event</button>
        )}
      </div>
    </>
  )
}

// ── Y Axis field group — one Highcharts yAxis[] entry ───────────────────────
function YAxisFields({ axis, idx, isPrimary, onSet, onRemove, CI, CB, num }) {
  return (
    <div className={idx > 0 ? 'pl-3 border-l-2 border-[#E2E8F0] mb-2 space-y-1.5' : 'space-y-1.5 mb-2'}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider">
          Axis {idx} {isPrimary ? '(primary / left)' : '(secondary / right)'}
        </p>
        {onRemove && <button onClick={onRemove} className="text-red-400 text-[10px] hover:text-red-600">✕ Remove Axis</button>}
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <Field label="Title">
          <input type="text" value={axis.title?.text || ''} onChange={e => onSet('title.text', e.target.value || undefined)} className={CI} placeholder="Y label" />
        </Field>
        <Field label="Min">
          <input type="number" value={axis.min ?? ''} onChange={e => onSet('min', num(e.target.value))} className={CI} placeholder="0" />
        </Field>
        <Field label="Grid Line Width">
          <input type="number" value={axis.gridLineWidth ?? ''} onChange={e => onSet('gridLineWidth', num(e.target.value))} className={CI} placeholder="1" />
        </Field>
        <Field label="Labels Format">
          <input type="text" value={axis.labels?.format || ''} onChange={e => onSet('labels.format', e.target.value || undefined)} className={CI} placeholder="{value}" />
        </Field>
      </div>
      <div className="flex gap-4 flex-wrap">
        {!isPrimary && (
          <div className="flex items-center gap-2">
            <input type="checkbox" id={`y-opp-${idx}`} checked={axis.opposite !== false}
              onChange={e => onSet('opposite', e.target.checked)} className={CB} />
            <label htmlFor={`y-opp-${idx}`} className="text-xs text-[#374151]">Opposite side</label>
          </div>
        )}
        <div className="flex items-center gap-2">
          <input type="checkbox" id={`y-showlbl-${idx}`} checked={axis.labels?.enabled !== false}
            onChange={e => onSet('labels.enabled', e.target.checked)} className={CB} />
          <label htmlFor={`y-showlbl-${idx}`} className="text-xs text-[#374151]">Show Labels</label>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id={`y-revstack-${idx}`} checked={!!axis.reversedStacks}
            onChange={e => onSet('reversedStacks', e.target.checked || undefined)} className={CB} />
          <label htmlFor={`y-revstack-${idx}`} className="text-xs text-[#374151]">Reversed Stacks</label>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id={`y-stacklbl-${idx}`} checked={!!axis.stackLabels?.enabled}
            onChange={e => onSet('stackLabels.enabled', e.target.checked || undefined)} className={CB} />
          <label htmlFor={`y-stacklbl-${idx}`} className="text-xs text-[#374151]">Stack Labels</label>
        </div>
      </div>
      {axis.stackLabels?.enabled && (
        <div className="pl-3 border-l-2 border-[#E2E8F0] space-y-1.5">
          <Field label="Stack Format">
            <input type="text" value={axis.stackLabels?.format || '{total:,.0f}'}
              onChange={e => onSet('stackLabels.format', e.target.value || undefined)} className={CI} placeholder="{total:,.0f}" />
          </Field>
          <Field label="Stack Font Size">
            <input type="text" value={axis.stackLabels?.style?.fontSize || ''}
              onChange={e => onSet('stackLabels.style.fontSize', e.target.value || undefined)} className={CI} placeholder="11px" />
          </Field>
        </div>
      )}
    </div>
  )
}

// ── Series Config Modal ─────────────────────────────────────────────────────
const CHART_TYPE_OPTIONS = ['bar','line','column','spline','area','areaspline','scatter','pie','waterfall','sunburst']

function SeriesConfigModal({ series, chartType, attributes = [], axisCount = 1, onApply, onClose }) {
  const [name, setName] = useState(series?.name || '')
  const [xField, setXField] = useState(series?.xField || '')
  const [yField, setYField] = useState(series?.yField || '')
  const [color, setColor] = useState(series?.color || '')
  const [seriesType, setSeriesType] = useState(series?.seriesType || chartType)
  const [sourceDataPath, setSourceDataPath] = useState(series?.sourceDataPath || '')
  const [flip, setFlip] = useState(!!series?.flip)
  const [yAxis, setYAxisIdx] = useState(series?.yAxis || 0)

  const CI = 'w-full border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-[#2563EB]'
  const SEL = 'w-full border rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:border-[#2563EB]'

  const fieldSelect = (value, setValue, placeholder) => (
    <div className="flex flex-col gap-1">
      {attributes.length > 0 && (
        <select value={attributes.includes(value) ? value : ''} onChange={e => setValue(e.target.value)} className={SEL}>
          <option value="">-- select attribute --</option>
          {attributes.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      )}
      <input type="text" value={value} onChange={e => setValue(e.target.value)} className={`${CI} font-mono`} placeholder={placeholder} />
    </div>
  )

  const handleApply = () => {
    onApply({ name: name.trim() || 'Series', xField: xField.trim(), yField: yField.trim(), color, seriesType, sourceDataPath: sourceDataPath.trim(), flip, yAxis })
  }

  return (
    <Modal title="Edit Series" onClose={onClose} width="max-w-sm">
      <div className="p-4 space-y-3">
        <Field label="Series Name">
          <input type="text" value={name} onChange={e => setName(e.target.value)} className={CI} placeholder="Series name" autoFocus />
        </Field>
        <Field label="X Field (name)">
          {fieldSelect(xField, setXField, 'e.g. DATE')}
        </Field>
        <Field label="Y Field (value)">
          {fieldSelect(yField, setYField, 'e.g. QTY')}
        </Field>
        <Field label="Series Type" desc="Overrides the chart's default type for this series only — mix bar + line by giving each series a different type (combo chart).">
          <select value={seriesType} onChange={e => setSeriesType(e.target.value)} className={SEL}>
            {CHART_TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        {axisCount > 1 && (
          <Field label="Y Axis" desc="Which Y axis (defined in the chart's Y Axis section) this series plots against.">
            <select value={yAxis} onChange={e => setYAxisIdx(parseInt(e.target.value))} className={SEL}>
              {Array.from({ length: axisCount }, (_, i) => i).map(i => (
                <option key={i} value={i}>{i === 0 ? 'Axis 0 (primary / left)' : `Axis ${i} (secondary / right)`}</option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Color">
          <div className="flex items-center gap-2">
            <input type="text" value={color === 'colorByPoint' ? '' : color}
              onChange={e => setColor(e.target.value)} className={`${CI} flex-1`} placeholder="#3B82F6" />
            <label className="flex items-center gap-1 text-[10px] text-[#64748B] shrink-0">
              <input type="checkbox" checked={color === 'colorByPoint'}
                onChange={e => setColor(e.target.checked ? 'colorByPoint' : '')} className="accent-[#1E3A8A]" />
              color by point
            </label>
          </div>
        </Field>
        <Field label="Source Data Path (optional override)">
          <input type="text" value={sourceDataPath} onChange={e => setSourceDataPath(e.target.value)} className={`${CI} font-mono`} placeholder="Leave blank to use chart's Data Source Path" />
        </Field>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="series-flip" checked={flip} onChange={e => setFlip(e.target.checked)} className="accent-[#1E3A8A]" />
          <label htmlFor="series-flip" className="text-xs text-[#374151]">Flip X↔Y axes (fm_inverted)</label>
        </div>
        <div className="flex gap-2 pt-2 border-t border-[#E2E8F0]">
          <button onClick={handleApply} className="px-4 py-1.5 bg-[#1E3A8A] text-white rounded text-sm font-semibold hover:bg-[#1E40AF]">Apply</button>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Add Metric Modal ────────────────────────────────────────────────────────
function AddMetricModal({ onApply, onClose, attributes = [], dataSourcePath }) {
  const [field, setField] = useState('')
  const [label, setLabel] = useState('')
  const [unit, setUnit] = useState('')

  const handleApply = () => {
    if (!field.trim()) return
    const l = label.trim() || field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    onApply({ field: field.trim(), label: l, unit: unit.trim() })
  }

  return (
    <Modal title="Add KPI Metric" onClose={onClose} width="max-w-sm">
      <div className="p-4 space-y-3">
        <Field label="Data Field Key">
          {attributes.length > 0 ? (
            <div className="flex flex-col gap-1">
              <select 
                value={field} 
                onChange={e => setField(e.target.value)} 
                className="w-full border rounded px-2 py-1.5 text-xs bg-white text-[#1E3A8A] font-mono focus:outline-none focus:border-[#2563EB]"
              >
                <option value="">-- select attribute --</option>
                {attributes.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
              <input 
                type="text" 
                value={field} 
                onChange={e => setField(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-xs text-[#334155] font-mono focus:outline-none focus:border-[#2563EB]" 
                placeholder="e.g. TOTAL_SALES" 
                autoFocus
              />
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <input 
                type="text" 
                value={field} 
                onChange={e => setField(e.target.value)}
                className="w-full border rounded px-2 py-1.5 text-xs text-[#334155] font-mono focus:outline-none focus:border-[#2563EB]" 
                placeholder="e.g. TOTAL_SALES" 
                autoFocus
              />
              <p className="text-[10px] text-[#92400E] leading-tight">
                No child attributes detected for '{dataSourcePath}'. Ensure the upstream flow defines columns for this variable.
              </p>
            </div>
          )}
        </Field>
        <Field label="Display Label">
          <input 
            type="text" 
            value={label} 
            onChange={e => setLabel(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-[#2563EB]" 
            placeholder="Leave blank to auto-generate" 
          />
        </Field>
        <Field label="Unit (optional)">
          <input 
            type="text" 
            value={unit} 
            onChange={e => setUnit(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-[#2563EB]" 
            placeholder="e.g. $, kg, items" 
          />
        </Field>
        <div className="flex gap-2 pt-2 border-t border-[#E2E8F0]">
          <button onClick={handleApply} className="px-4 py-1.5 bg-[#1E3A8A] text-white rounded text-sm font-semibold hover:bg-[#1E40AF]">Add Metric</button>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#F1F5F9] text-[#374151] rounded text-sm ml-auto hover:bg-[#E2E8F0]">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

// ── METRICS EDITOR ───────────────────────────────────────────────────────────
function MetricsEditor({ cfg, onSetConfig, varPool = {}, varSchemas = {} }) {
  const [showAdd, setShowAdd] = useState(false)
  const metrics = cfg.metricsSpec || []
  const dsPath = cfg.dataSourcePath || ''
  const attributes = varSchemas[dsPath] || []
  const update = (i, key, val) => {
    const m = structuredClone(metrics)
    m[i][key] = val
    onSetConfig('metricsSpec', m)
  }
  return (
    <div>
      {showAdd && (
        <AddMetricModal 
          attributes={attributes} 
          dataSourcePath={dsPath}
          onApply={m => { onSetConfig('metricsSpec', [...metrics, m]); setShowAdd(false) }} 
          onClose={() => setShowAdd(false)} 
        />
      )}
      <SectionHdr label="KPI Tiles" />
      {metrics.map((m, i) => (
        <div key={i} className="flex gap-1 mb-1.5 items-center">
          <input type="text" value={m.label || ''} onChange={e => update(i, 'label', e.target.value)} placeholder="Label" className="flex-1 border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
          <input type="text" value={m.field || ''} onChange={e => update(i, 'field', e.target.value)} placeholder="Field" className="w-24 border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
          <input type="text" value={m.unit || ''} onChange={e => update(i, 'unit', e.target.value)} placeholder="Unit" className="w-12 border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
          <button onClick={() => onSetConfig('metricsSpec', metrics.filter((_, j) => j !== i))} className="text-red-400 text-xs">✕</button>
        </div>
      ))}
      <button onClick={() => setShowAdd(true)}
        className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded mt-1">+ Add Metric</button>

      <div className="mt-3 space-y-1.5">
        <Field label="Data Source Path">
          {Object.keys(varPool).length > 0 ? (
            <div>
              <select value={cfg.dataSourcePath || ''} onChange={e => { const ds = e.target.value; onSetConfig('dataSourcePath', ds); if (varPool[ds] && !cfg.backendVar) onSetConfig('backendVar', varPool[ds]) }}
                className="w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
                <option value="">-- select from pool --</option>
                {Object.keys(varPool).map(k => <option key={k} value={k}>{k}</option>)}
              </select>
              <input type="text" value={cfg.dataSourcePath || ''} onChange={e => onSetConfig('dataSourcePath', e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB] mt-1" />
            </div>
          ) : (
            <input type="text" value={cfg.dataSourcePath || ''} onChange={e => onSetConfig('dataSourcePath', e.target.value)}
              className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
          )}
        </Field>
        <Field label="Backend Variable">
          {Object.keys(varPool).length > 0 ? (
            <div className="flex flex-col gap-1">
              <select value={cfg.backendVar || ''} onChange={e => onSetConfig('backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs bg-white text-[#1E3A8A] font-mono focus:outline-none focus:border-[#2563EB]">
                <option value="">-- select backend variable --</option>
                {[...new Set(Object.values(varPool))].map((v, idx) => <option key={idx} value={v}>{v}</option>)}
              </select>
              <input type="text" value={cfg.backendVar || ''} onChange={e => onSetConfig('backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="object::MetricsDataJs.result" />
            </div>
          ) : (
            <input type="text" value={cfg.backendVar || ''} onChange={e => onSetConfig('backendVar', e.target.value)} className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" placeholder="object::MetricsDataJs.result" />
          )}
        </Field>
      </div>
    </div>
  )
}

// ── STYLE EDITOR ──────────────────────────────────────────────────────────────
const CSS_GROUPS = [
  { label: 'Flex / Display', props: ['display', 'flexDirection', 'justifyContent', 'alignItems', 'alignSelf', 'flexWrap', 'flex', 'flexGrow', 'flexShrink', 'flexBasis'] },
  { label: 'Sizing', props: ['width', 'height', 'minWidth', 'maxWidth', 'minHeight', 'maxHeight', 'boxSizing'] },
  { label: 'Gap / Spacing', props: ['gap', 'rowGap', 'columnGap', 'padding', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'margin', 'marginTop', 'marginRight', 'marginBottom', 'marginLeft'] },
  { label: 'Overflow / Position', props: ['overflow', 'overflowX', 'overflowY', 'position', 'top', 'left', 'right', 'bottom', 'zIndex'] },
  { label: 'Grid', props: ['gridTemplateColumns', 'gridAutoRows', 'gridGap', 'gridColumn', 'gridRow'] },
  { label: 'Visual', props: ['backgroundColor', 'color', 'borderRadius', 'border', 'opacity', 'boxShadow', 'backgroundImage'] },
]

function StyleEditor({ node, sty, schema, onSetStyle, onSetFullStyle }) {
  const css = sty?.css || {}

  const setCssProp = (prop, val) => {
    const newSty = structuredClone(sty || {})
    if (!newSty.css) newSty.css = {}
    if (val.trim() === '') delete newSty.css[prop]
    else newSty.css[prop] = val
    onSetFullStyle(newSty)
  }

  return (
    <div className="space-y-3">
      {/* Schema-driven style fields */}
      {schema?.sty && schema.sty.length > 0 && (
        <div>
          <SectionHdr label="Component Style" />
          {schema.sty.map(field => {
            const val = getStyVal(sty, field.key)
            if (field.type === 'enum') {
              return (
                <Field key={field.key} label={field.label}>
                  <select value={val || ''} onChange={e => onSetStyle(field.key, e.target.value)}
                    className="w-full border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#2563EB]">
                    <option value="">—</option>
                    {(field.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </Field>
              )
            }
            return (
              <Field key={field.key} label={field.label}>
                <input type="text" value={val} onChange={e => onSetStyle(field.key, e.target.value)}
                  className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
              </Field>
            )
          })}
        </div>
      )}

      {/* Top-level style props */}
      <div>
        <SectionHdr label="Style (top-level)" />
        {['width', 'height'].map(prop => (
          <Field key={prop} label={prop}>
            <input type="text" value={sty?.[prop] || ''}
              onChange={e => {
                const newSty = structuredClone(sty || {})
                if (e.target.value === '') delete newSty[prop]
                else newSty[prop] = e.target.value
                onSetFullStyle(newSty)
              }}
              className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]" />
          </Field>
        ))}
      </div>

      {/* CSS groups */}
      <div>
        <SectionHdr label="Style.css" />
        {CSS_GROUPS.map(group => (
          <div key={group.label} className="mb-3">
            <p className="text-[10px] font-semibold text-[#94A3B8] uppercase tracking-wider mb-1">{group.label}</p>
            <div className="grid grid-cols-1 gap-y-1">
              {group.props.map(prop => {
                const val = css[prop] ?? ''
                return (
                  <div key={prop} className="flex items-center gap-2">
                    <label className="text-xs text-[#374151] w-32 shrink-0 font-mono truncate">{prop}</label>
                    <input type="text" value={val} onChange={e => setCssProp(prop, e.target.value)} placeholder="—"
                      className={`flex-1 border rounded px-2 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB] ${val ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#E2E8F0]'}`} />
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <details>
        <summary className="text-xs font-semibold text-[#374151] cursor-pointer hover:text-[#1E3A8A]">Full Style JSON ▸</summary>
        <div className="mt-1">
          <JsonEditor value={sty} onChange={v => onSetFullStyle(v)} height="150px" />
        </div>
      </details>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function getNodeAtPath(root, path) {
  if (!path || path.length === 0) return root
  let node = root
  for (const key of path) {
    if (node == null) return null
    node = node[key]
  }
  return node
}

function getParentAndKey(root, path) {
  if (!path || path.length === 0) return { obj: { _root: root }, key: '_root' }
  let obj = root
  for (const key of path.slice(0, -1)) {
    if (obj == null) return null
    obj = obj[key]
  }
  return { obj, key: path[path.length - 1] }
}

// ── Insight bulb → detail flyout host ─────────────────────────────────────────
// Matches the "Insight bulb / detail flyout pattern" documented in ALIGN_FIX_SYSTEM:
// the action-button's OnClick (push-details-flyout) only does something if a sidebar
// Right-slot "stack" container is listening for it. buildInsightsCol() always wires the
// button; this ensures the listener host exists too, in-place on an already-cloned root.
function ensureDetailFlyoutHostMutate(root) {
  const hasPushListener = node => (node?.Events?.Listeners?.Push || []).some(p => p.EventId === 'push-details-flyout')
  const stackNode = () => ({
    Container: 'stack',
    Config: { MaxSize: 1 },
    Events: {
      Listeners: {
        Push: [{ EventId: 'push-details-flyout', SourceContainerId: 'details-button' }],
        Pop: [{ EventId: 'close-details-flyout', SourceContainerId: 'details-flyout' }],
      },
      Triggers: { StackChanged: [{ EventId: 'stack-changed', ContainerId: 'ool-stack' }] },
    },
    Slots: {},
  })
  function walk(node) {
    if (!node || typeof node !== 'object') return false
    if (node.Container === 'sidebar') {
      if (!node.Slots) node.Slots = {}
      const right = node.Slots.Right || []
      if (!right.some(hasPushListener)) node.Slots.Right = [...right, stackNode()]
      return true
    }
    if (node.Slots) {
      for (const arr of Object.values(node.Slots)) {
        if (Array.isArray(arr)) for (const child of arr) if (walk(child)) return true
      }
    }
    return false
  }
  return walk(root)
}
