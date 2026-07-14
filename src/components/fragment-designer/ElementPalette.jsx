import { useState } from 'react'
import { ELEMENT_CATEGORIES, ELEMENT_LABELS, COMP_COLORS, COMP_ICONS } from '../../utils/fragmentData'

// Mirrors Python TOOLTIPS dict — shown on hover in the palette
const TOOLTIPS = {
  pie:             "Pie Chart\nDonut/pie chart. Maps STATUS_GROUP→name, MSG_COUNT→y.\nSet dataSourcePath + backendVar in Config.",
  bar:             "Bar Chart\nHorizontal bar chart with stacked series support.\nSet dataSourcePath + configure seriesMappings.",
  line:            "Line Chart\nLine trend chart. Maps HOUR_SLOT→name, MSG_COUNT→y.\nSet dataSourcePath for the time-series data.",
  column:          "Column Chart\nVertical column chart. Good for timeline summaries.\nSupports stacking. Set dataSourcePath.",
  spline:          "Spline Chart\nSmooth curved line chart variant.\nSame data mapping as line chart.",
  area:            "Area Chart\nFilled area line chart for volume trends.\nSupports fillOpacity for shading.",
  areaspline:      "Area Spline Chart\nSmooth filled area chart.\nCombines spline smoothing with area fill.",
  scatter:         "Scatter Chart\nX/Y scatter plot for correlation data.\nMaps X_VAL→x, Y_VAL→y.",
  sunburst:        "Sunburst Chart\nHierarchical donut chart. Maps ID, PARENT, VALUE.\nRequires parent-child data structure.",
  waterfall:       "Waterfall Chart\nCumulative bar chart showing incremental changes.\nMaps CATEGORY→name, VALUE→y.",
  table:           "Data Table\nFull-featured data grid with sort, filter, pagination.\nConfigure Columns array with field mappings.",
  metrics:         "Metrics Panel\nKPI tile row (number cards). Set metricsSpec array\nwith label, field, unit per tile.",
  button:          "Button\nStandard action button. Set LabelKey for the text.\nConfigure Events.OnClick for show/hide behavior.",
  'button-icon':   "Icon Button\nCompact icon-only circular button. Set icon + actionKey.\nGood for edit/delete/expand in-line actions.",
  'action-button': "Action Button\nButton bound to a complex river action workflow.\nSet actionKey to the registered river-action key.",
  link:            "Link\nNavigation link with routing support.\nSet LabelKey for display text + href or route path.",
  'related-link':  "Related Link\nLinks to a related entity record. Input = ID field\nfor the relationship (navigates on click).",
  'key-value':     "Key-Value\nLabeled data pair display. Set LabelKey as the label.\nSet Input = field path for the value.",
  'key-value-detail':"Key-Value Detail\nKey-value with collapsible detail panel.\nSet LabelKey + AttributeType in Config.",
  value:           "Value Display\nShows a raw field value. Set Input = field path.\nNo label — raw data only.",
  'value-unit':    "Value + Unit\nShows a numeric value with a unit label.\nSet unit in Config (e.g. kg ms % items).",
  pill:            "Pill / Badge\nColored status badge. Set Input = status field.\nStyle.pillBackgroundColor + pillTextColor.",
  text:            "Text Display\nStatic or i18n localized text. Set LabelKey.\nSupports fontWeight, fontSize, color in Style.",
  'progress-bar':  "Progress Bar\nVisual 0-100 progress bar. Set Input = progress field.\nSet LabelKey as the label text.",
  message:         "Message\nInformational message block. Set LabelKey.\nGood for empty states or instructions.",
  'currency-format':"Currency Display\nFormats a numeric field as locale currency.\nSet locale in Config (e.g. en-US de-DE).",
  icon:            "Icon\nVisual icon from the MAWC icon library.\nSet icon name in Config (e.g. info warning edit).",
  input:           "Text Input\nSingle-line text input for forms.\nSet LabelKey, name, type, required in Config.",
  combobox:        "Combobox\nSearchable dropdown with autocomplete.\nSet name + data source for options.",
  'toggle-button': "Toggle Button\nOn/off switch control. Emits OnChange events.\nSet name + LabelKey.",
  search:          "Search Box\nText search with debounce. Triggers EFW filter on input.\nSet name + LabelKey.",
  textarea:        "Text Area\nMulti-line text input. Set LabelKey + name.\nIntegrates with Angular reactive forms.",
  checkbox:        "Checkbox\nBoolean toggle for forms. Set name + LabelKey.\nIntegrates with Angular reactive forms.",
  dropdown:        "Dropdown\nSelect list. Set LabelKey + name.\nSupports static or dynamic options.",
  'date-select':   "Date Picker\nCalendar date input with locale formatting.\nSet name + LabelKey.",
  'numeric-stepper':"Numeric Stepper\nIncrement/decrement number input.\nSet name, LabelKey and optional step size.",
  'currency-input':"Currency Input\nLocale-aware monetary input with $ formatting.\nSet name + locale (e.g. en-US) in Config.",
  'quick-filter':  "Quick Filter\nPreset filter chip row for fast filtering.\nConfigure Segments array with LabelKey + Id.",
  'segment-panel': "Segment Panel\nTab-like segmented control for switching sections.\nSet Segments array: [{AttributeKey, AttributeValue}].",
  'filter-panel':  "Filter Panel\nAdvanced filter UI with multiple attribute filters.\nSet Attributes array with Input + Filter sub-config.",
  card:            "Card Container\nWhite card with header, content and footer slots.\nSet title in Config.",
  banner:          "Banner\nNotification banner bar. Set type (info/warning/error/success)\n+ LabelKey for the message.",
  accordion:       "Accordion\nCollapsible sections list. Each section is a slot.\nGood for grouping settings or detail fields.",
  expandable:      "Expandable\nSingle collapsible section with a title header.\nSet title in Config. Collapsed by default.",
  form:            "Form Container\nWraps form elements in a reactive Angular form.\nSet formId in Config.",
  section:         "Section\nContent section with a title divider line.\nGroups related elements visually and semantically.",
  list:            "List Container\nIterates over array data, rendering a slot template per item.\nSet Init to the array data source.",
  stack:           "Stack Layout\nVertical or horizontal stack of child elements.\nSet direction: vertical | horizontal in Style.",
  flex:            "Flex Layout\nCSS flexbox container for responsive layouts.\nSet flexDirection, gap, justifyContent in Style.css.",
  grid:            "Grid Layout\nCSS grid container. Set gridTemplateColumns\nand gap in Style.css (e.g. '1fr 1fr').",
  'tab-group':     "Tab Group\nTabbed interface with named slot tabs.\nEach tab is a slot key. Supports personalization.",
  carousel:        "Carousel\nScrollable slide show for repeating items.\nSet slidesPerPage, slidesPerMove, navigation. Use Config.Fragment for item template.",
  'actions-popover':"Actions Popover\nPopover menu of actions (Export CSV, XLSX, etc.).\nConfigure via ActionConfig.",
}

export default function ElementPalette({ onAddElement, varPool = {} }) {
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState({})
  const [activeTab, setActiveTab] = useState('Components')

  const toggle = label => setCollapsed(p => ({ ...p, [label]: !p[label] }))

  const filtered = search.trim()
    ? ELEMENT_CATEGORIES.map(cat => ({
        ...cat,
        types: cat.types.filter(t =>
          t.includes(search.toLowerCase()) || ELEMENT_LABELS[t]?.toLowerCase().includes(search.toLowerCase())
        ),
      })).filter(cat => cat.types.length > 0)
    : ELEMENT_CATEGORIES

  const poolEntries = Object.entries(varPool)

  return (
    <div className="w-52 shrink-0 border-r border-[#CBD5E1] flex flex-col bg-white">
      {/* Tabs: Components | Data */}
      <div className="flex border-b border-[#CBD5E1] shrink-0">
        {['Components', 'Data'].map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`flex-1 py-2 text-xs font-semibold transition-colors ${activeTab === t ? 'text-[#2563EB] border-b-2 border-[#2563EB]' : 'text-[#374151] hover:text-[#1E3A8A]'}`}
          >
            {t}{t === 'Data' && poolEntries.length > 0 && (
              <span className="ml-1 px-1 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded-full text-[9px]">{poolEntries.length}</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'Data' ? (
        <div className="flex-1 overflow-y-auto p-3">
          <p className="text-xs font-semibold text-[#374151] mb-2">Variable Pool</p>
          {poolEntries.length === 0 ? (
            <div className="text-xs text-[#94A3B8] text-center mt-6">
              <p className="text-2xl mb-2">🗃</p>
              <p>No variables loaded.</p>
              <p className="mt-1">Import Action JSON via the toolbar.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {poolEntries.map(([key, val]) => (
                <div key={key} className="bg-[#F8FAFC] rounded border border-[#E2E8F0] px-2 py-1.5">
                  <p className="text-xs font-mono font-semibold text-[#1E3A8A] truncate">{key}</p>
                  <p className="text-[10px] font-mono text-[#94A3B8] truncate mt-0.5">{val}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <>
      <div className="px-3 pt-3 pb-2 border-b border-[#CBD5E1]">
        <input
          type="text"
          placeholder="Search elements..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:border-[#2563EB]"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {filtered.map(cat => (
          <div key={cat.label}>
            <button
              onClick={() => toggle(cat.label)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-[#374151] bg-[#F8FAFC] hover:bg-[#F1F5F9] border-b border-[#E2E8F0]"
            >
              <span>{cat.label}</span>
              <span className="text-[#94A3B8]">{collapsed[cat.label] ? '▶' : '▼'}</span>
            </button>

            {!collapsed[cat.label] && (
              <div className="py-1">
                {cat.types.map(type => (
                  <ElementItem key={type} type={type} onAdd={onAddElement} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
        </>
      )}
    </div>
  )
}

function ElementItem({ type, onAdd }) {
  const color = COMP_COLORS[type] || '#374151'
  const icon = COMP_ICONS[type] || '□'
  const label = ELEMENT_LABELS[type] || type

  return (
    <button
      onClick={() => onAdd(type)}
      draggable
      onDragStart={e => e.dataTransfer.setData('elementType', type)}
      className="w-full flex items-center gap-2.5 px-3 py-2 text-left text-[11px] font-medium hover:bg-[#F1F5F9] active:bg-[#E2E8F0] group transition-all border-b border-transparent hover:border-[#CBD5E1]/30"
      title={TOOLTIPS[type] || `Add ${label}`}
    >
      <span
        className="w-7 h-7 rounded-md flex items-center justify-center text-white text-sm shrink-0 shadow-sm group-hover:scale-105 transition-transform"
        style={{ backgroundColor: color }}
      >
        {icon}
      </span>
      <span className="text-[#334155] group-hover:text-[#1E3A8A] truncate leading-tight">{label}</span>
      <span className="ml-auto text-[#CBD5E1] group-hover:text-[#2563EB] text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity">+</span>
    </button>
  )
}
