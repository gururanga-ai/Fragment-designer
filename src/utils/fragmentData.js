/**
 * Fragment Designer element/container definitions — mirrored from Python COMP_DEFS / RIVER_ELEM_DEFS.
 */

// ── Python COMP_DEFS — exact chart defaults with seriesMappings + highchartsOptions ──
const COMP_DEFS = {
  pie: {
    dataSourcePath: 'StatusSummary', backendVar: 'object::StatusSummaryJs.result',
    seriesMappings: [{ fieldMappings: { STATUS_GROUP: 'name', MSG_COUNT: 'y' }, seriesType: 'pie', sourceDataPath: 'StatusSummary', staticOptions: { name: 'Messages', colorByPoint: true } }],
    highchartsOptions: { chart: { type: 'pie', marginTop: 30 }, title: { text: '' }, tooltip: { pointFormat: '<b>{point.name}</b>: {point.y}' }, plotOptions: { pie: { allowPointSelect: true, cursor: 'pointer', showInLegend: true, dataLabels: { enabled: true, format: '<b>{point.name}</b>: {point.y}' } } }, legend: { enabled: true, layout: 'horizontal' }, series: [{ name: 'Messages' }] },
  },
  bar: {
    dataSourcePath: 'TypeDistribution', backendVar: 'object::TypeDistributionJs.result',
    seriesMappings: [
      { fieldMappings: { MESSAGE_TYPE: 'name', MSG_COUNT: 'y' }, seriesType: 'bar', sourceDataPath: 'TypeDistribution', staticOptions: { color: '#1E3A8A', name: 'Total' } },
      { fieldMappings: { MESSAGE_TYPE: 'name', FAIL_COUNT: 'y' }, seriesType: 'bar', sourceDataPath: 'TypeDistribution', staticOptions: { color: '#DC2626', name: 'Failed' } },
    ],
    highchartsOptions: { chart: { type: 'bar', marginLeft: 180, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category', title: { text: 'Type', style: { fontSize: '11px' } } }, yAxis: { min: 0, title: { text: 'Count', style: { fontSize: '11px' } } }, plotOptions: { series: { borderWidth: 0, stacking: 'normal' } }, tooltip: { shared: true, useHTML: true, headerFormat: '<b>{point.key}</b><br/>', pointFormat: '<span style="color:{series.color}">●</span> <b>{series.name}</b>: {point.y}<br/>' }, legend: { enabled: true, layout: 'horizontal' }, series: [{ name: 'Total' }, { name: 'Failed' }] },
  },
  line: {
    dataSourcePath: 'HourlyTrend', backendVar: 'object::HourlyTrendJs.result',
    seriesMappings: [{ fieldMappings: { HOUR_SLOT: 'name', MSG_COUNT: 'y' }, seriesType: 'line', sourceDataPath: 'HourlyTrend', staticOptions: { color: '#1E3A8A', name: 'Total' } }],
    highchartsOptions: { chart: { type: 'line', marginLeft: 50, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { min: 0 }, plotOptions: { line: { marker: { enabled: true, radius: 4 } } }, tooltip: { shared: true }, legend: { enabled: true }, series: [{ name: 'Total' }] },
  },
  column: {
    dataSourcePath: 'TimelineSummary', backendVar: 'object::TimelineSummaryJs.result',
    seriesMappings: [{ fieldMappings: { TIME_SLOT: 'name', MSG_COUNT: 'y' }, seriesType: 'column', sourceDataPath: 'TimelineSummary', staticOptions: { color: '#EA580C', name: 'Value' } }],
    highchartsOptions: { chart: { type: 'column', marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { min: 0 }, plotOptions: { column: { borderWidth: 0, stacking: 'normal' } }, legend: { enabled: true }, series: [{ name: 'Value' }] },
  },
  spline: {
    dataSourcePath: 'HourlyTrend', backendVar: 'object::HourlyTrendJs.result',
    seriesMappings: [{ fieldMappings: { HOUR_SLOT: 'name', MSG_COUNT: 'y' }, seriesType: 'spline', sourceDataPath: 'HourlyTrend', staticOptions: { color: '#7C3AED', name: 'Total' } }],
    highchartsOptions: { chart: { type: 'spline', marginLeft: 50, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { min: 0 }, plotOptions: { spline: { marker: { enabled: true, radius: 4 } } }, legend: { enabled: true }, series: [{ name: 'Total' }] },
  },
  area: {
    dataSourcePath: 'HourlyTrend', backendVar: 'object::HourlyTrendJs.result',
    seriesMappings: [{ fieldMappings: { HOUR_SLOT: 'name', MSG_COUNT: 'y' }, seriesType: 'area', sourceDataPath: 'HourlyTrend', staticOptions: { color: '#0EA5E9', name: 'Total' } }],
    highchartsOptions: { chart: { type: 'area', marginLeft: 50, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { min: 0 }, plotOptions: { area: { fillOpacity: 0.3, marker: { enabled: false } } }, legend: { enabled: true }, series: [{ name: 'Total' }] },
  },
  areaspline: {
    dataSourcePath: 'HourlyTrend', backendVar: 'object::HourlyTrendJs.result',
    seriesMappings: [{ fieldMappings: { HOUR_SLOT: 'name', MSG_COUNT: 'y' }, seriesType: 'areaspline', sourceDataPath: 'HourlyTrend', staticOptions: { color: '#10B981', name: 'Total' } }],
    highchartsOptions: { chart: { type: 'areaspline', marginLeft: 50, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { min: 0 }, plotOptions: { areaspline: { fillOpacity: 0.3, marker: { enabled: false } } }, legend: { enabled: true }, series: [{ name: 'Total' }] },
  },
  scatter: {
    dataSourcePath: 'ScatterData', backendVar: 'object::ScatterDataJs.result',
    seriesMappings: [{ fieldMappings: { X_VAL: 'name', Y_VAL: 'y' }, seriesType: 'scatter', sourceDataPath: 'ScatterData', staticOptions: { color: '#F59E0B', name: 'Data' } }],
    highchartsOptions: { chart: { type: 'scatter', marginLeft: 50, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { title: { text: 'X' } }, yAxis: { title: { text: 'Y' } }, plotOptions: { scatter: { marker: { radius: 5 }, tooltip: { pointFormat: '{point.x}, {point.y}' } } }, legend: { enabled: true }, series: [{ name: 'Data' }] },
  },
  sunburst: {
    dataSourcePath: 'HierarchyData', backendVar: 'object::HierarchyDataJs.result',
    seriesMappings: [{ fieldMappings: { ID: 'name', PARENT: 'parent', VALUE: 'y' }, seriesType: 'sunburst', sourceDataPath: 'HierarchyData', staticOptions: { colorByPoint: true, name: 'Hierarchy' } }],
    highchartsOptions: { chart: { type: 'sunburst', marginTop: 30 }, title: { text: '' }, tooltip: { pointFormat: '<b>{point.name}</b>: {point.value}' }, series: [{ name: 'Hierarchy', allowDrillToNode: true, cursor: 'pointer', dataLabels: { format: '{point.name}', filter: { property: 'innerArcLength', operator: '>', value: 8 } } }] },
  },
  waterfall: {
    dataSourcePath: 'WaterfallData', backendVar: 'object::WaterfallDataJs.result',
    seriesMappings: [{ fieldMappings: { CATEGORY: 'name', VALUE: 'y' }, seriesType: 'waterfall', sourceDataPath: 'WaterfallData', staticOptions: { color: '#3B82F6', name: 'Change' } }],
    highchartsOptions: { chart: { type: 'waterfall', marginLeft: 60, marginRight: 50, marginTop: 30 }, title: { text: '' }, xAxis: { type: 'category' }, yAxis: { title: { text: 'Value' } }, plotOptions: { waterfall: { lineWidth: 1 } }, legend: { enabled: true }, series: [{ name: 'Change' }] },
  },
}

const _DEFAULT_CHART_METADATA = {
  applyAspectRatio: false,
  chartWidth: '100%',
  showChartHeader: false,
  showChartTitle: false,
  showHighchartsTitle: false,
  showLegend: true,
}

export const COMP_COLORS = {
  chart: '#1E3A8A',
  pie: '#16A34A', bar: '#1E3A8A', line: '#7C3AED', column: '#EA580C',
  spline: '#7C3AED', area: '#2563EB', areaspline: '#16A34A', scatter: '#EA580C',
  sunburst: '#1E3A8A', waterfall: '#16A34A',
  table: '#111827', metrics: '#2563EB',
  button: '#2563EB', pill: '#16A34A', 'key-value': '#111827', 'progress-bar': '#EA580C',
  text: '#374151', banner: '#7C3AED', card: '#1E3A8A', input: '#2563EB',
  combobox: '#2563EB', 'toggle-button': '#16A34A', search: '#111827',
  'segment-panel': '#7C3AED', 'tab-group': '#1E3A8A', 'sticky-header': '#111827',
  textarea: '#2563EB', checkbox: '#16A34A', dropdown: '#2563EB', 'date-select': '#7C3AED',
  'numeric-stepper': '#EA580C', 'currency-input': '#16A34A',
  value: '#111827', 'value-unit': '#374151', icon: '#1E3A8A', message: '#7C3AED',
  'currency-format': '#16A34A', 'key-value-detail': '#111827',
  'button-icon': '#2563EB', 'action-button': '#EA580C', link: '#1E3A8A', 'related-link': '#7C3AED',
  'quick-filter': '#16A34A', 'filter-panel': '#111827',
  accordion: '#1E3A8A', expandable: '#2563EB', form: '#16A34A', section: '#111827',
  list: '#374151', stack: '#1E3A8A', flex: '#7C3AED', grid: '#EA580C',
  'actions-popover': '#111827', carousel: '#1E3A8A',
}

export const COMP_ICONS = {
  chart: '📊',
  pie: '🥧', bar: '📊', line: '📈', column: '📉', spline: '〜', area: '▲',
  areaspline: '∿', scatter: '⁘', sunburst: '☀', waterfall: '⬇',
  table: '📋', metrics: '🏷',
  button: '🔘', pill: '🏷️', 'key-value': '🔑', 'progress-bar': '▰',
  text: '🔤', banner: '📢', card: '🃏', input: '✏️', combobox: '🔽',
  'toggle-button': '🔄', search: '🔍', 'segment-panel': '📑', 'tab-group': '📂',
  textarea: '📝', checkbox: '☑', dropdown: '▼', 'date-select': '📅', 'sticky-header': '🔝',
  'numeric-stepper': '🔢', 'currency-input': '💵',
  value: '🏷', 'value-unit': '📏', icon: '✦', message: '💬',
  'currency-format': '💲', 'key-value-detail': '🗝',
  'button-icon': '●', 'action-button': '⚡', link: '🔗', 'related-link': '↗',
  'quick-filter': '⚡', 'filter-panel': '🔎',
  accordion: '▸', expandable: '⊞', form: '📋', section: '▦', list: '≡',
  stack: '■', flex: '↔', grid: '⊟', 'actions-popover': '⬡', carousel: '🎠',
}

export const CHART_TYPES = new Set(['pie','bar','line','column','spline','area','areaspline','scatter','sunburst','waterfall'])

export const ELEMENT_CATEGORIES = [
  {
    label: 'Charts',
    types: ['pie','bar','line','column','spline','area','areaspline','scatter','sunburst','waterfall'],
  },
  {
    label: 'Data Display',
    types: ['table','metrics','key-value','key-value-detail','value','value-unit','pill','text','progress-bar','message','currency-format','icon'],
  },
  {
    label: 'Actions',
    types: ['button','action-button','button-icon','link','related-link'],
  },
  {
    label: 'Form Inputs',
    types: ['input','combobox','dropdown','textarea','checkbox','date-select','numeric-stepper','currency-input','search','toggle-button'],
  },
  {
    label: 'Filters',
    types: ['filter-panel','quick-filter','segment-panel','tab-group'],
  },
  {
    label: 'Containers',
    types: ['card','banner','flex','stack','grid','accordion','expandable','form','section','list','carousel','actions-popover'],
  },
]

export const ELEMENT_LABELS = {
  chart: 'Chart',
  pie: 'Pie Chart', bar: 'Bar Chart', line: 'Line Chart', column: 'Column Chart',
  spline: 'Spline Chart', area: 'Area Chart', areaspline: 'Area Spline', scatter: 'Scatter Chart',
  sunburst: 'Sunburst', waterfall: 'Waterfall',
  table: 'Data Table', metrics: 'Metrics Panel',
  button: 'Button', pill: 'Pill/Badge', 'key-value': 'Key-Value', 'progress-bar': 'Progress Bar',
  text: 'Text Display', banner: 'Banner', card: 'Card Container', input: 'Text Input',
  combobox: 'Combobox', 'toggle-button': 'Toggle Button', search: 'Search Box',
  'segment-panel': 'Segment Panel', 'tab-group': 'Tab Group',
  textarea: 'Text Area', checkbox: 'Checkbox', dropdown: 'Dropdown', 'date-select': 'Date Picker',
  'numeric-stepper': 'Numeric Stepper', 'currency-input': 'Currency Input',
  value: 'Value Display', 'value-unit': 'Value + Unit', icon: 'Icon', message: 'Message',
  'currency-format': 'Currency Display', 'key-value-detail': 'KV Detail',
  'button-icon': 'Icon Button', 'action-button': 'Action Button', link: 'Link', 'related-link': 'Related Link',
  'quick-filter': 'Quick Filter', 'filter-panel': 'Filter Panel', 'sticky-header': 'Sticky Header',
  accordion: 'Accordion', expandable: 'Expandable', form: 'Form', section: 'Section',
  list: 'List', stack: 'Stack', flex: 'Flex Layout', grid: 'Grid Layout',
  'actions-popover': 'Actions Popover', carousel: 'Carousel',
}

/** Whether a given type is a container (can have children in Slots) */
export function isContainer(type) {
  return ['card','banner','tab-group','accordion','expandable','form','section',
          'list','stack','flex','grid','actions-popover','carousel','sticky-header',
          'segment-panel'].includes(type)
}

/**
 * Create a default new element node for the Fragment JSON.
 * Mirrors Python COMP_DEFS and RIVER_ELEM_DEFS exactly.
 */
export function makeDefaultElement(type) {
  // ── Charts: Container: 'chart' with Init, dataMapping.seriesMappings, highchartsOptions ──
  if (CHART_TYPES.has(type)) {
    const def = COMP_DEFS[type]
    return {
      Container: 'chart',
      Init: { Type: 'value-array', DataSourcePath: def.dataSourcePath },
      Style: { contentPadding: '0', css: { flex: '1' } },
      Config: {
        chartMetadata: { ..._DEFAULT_CHART_METADATA },
        dataMapping: { seriesMappings: JSON.parse(JSON.stringify(def.seriesMappings)) },
        highchartsOptions: JSON.parse(JSON.stringify(def.highchartsOptions)),
        dataSourcePath: def.dataSourcePath,
        backendVar: def.backendVar,
      },
    }
  }

  // ── Data Table ────────────────────────────────────────────────────────────
  if (type === 'table') {
    return {
      Container: 'table',
      Config: {
        dataSourcePath: 'JournalData',
        backendVar: 'object::JournalDataJs.result',
        SelectionConfig: { ShowSelection: false, SupportMultiSelect: true },
        Columns: [
          { Config: { LabelKey: 'Message Type', Sort: { Sortable: true, SortBy: 'MESSAGE_TYPE' } }, Slots: { Default: [{ Element: 'key-value', Input: 'MESSAGE_TYPE', Config: {} }] } },
          { Config: { LabelKey: 'Total', Sort: { Sortable: true, SortBy: 'TOTAL' } }, Slots: { Default: [{ Element: 'key-value', Input: 'TOTAL', Config: {} }] } },
          { Config: { LabelKey: 'Failed', Sort: { Sortable: true, SortBy: 'FAILED' } }, Slots: { Default: [{ Element: 'key-value', Input: 'FAILED', Config: {} }] } },
        ],
      },
      Style: { width: '100%' },
    }
  }

  // ── Metrics Panel ─────────────────────────────────────────────────────────
  if (type === 'metrics') {
    return {
      Container: 'metrics',
      Config: {
        dataSourcePath: 'MetricsSummary',
        backendVar: 'object::MetricsSummaryJs.result',
        metricsSpec: [
          { label: 'Total Messages', field: 'TOTAL_MSG', unit: '' },
          { label: 'Failures', field: 'FAILURES', unit: '' },
          { label: 'Failure %', field: 'FAILURE_PCT', unit: '%' },
        ],
      },
      Style: {},
    }
  }

  // ── Segment Panel ── dual-mode: filter-backed (Container, common in real fragments) ─────────
  // vs simple chip tabs (Element). Default to filter mode — matches production usage where
  // segment-panel drives an agent filter (e.g. MetricMode/TimeBucket segmented controls).
  if (type === 'segment-panel') {
    return {
      Container: 'segment-panel',
      Input: 'map(*)',
      Config: {
        EnableSegmentPanel: true,
        EnableFilter: true,
        Name: '',
        SectionName: 'Filters',
        Type: 'string',
        Filter: {
          Type: 'Singleselect',
          Placeholder: { LabelKey: '' },
          EntityKey: 'AttributeKey',
          EntityValue: 'AttributeValue',
          StaticList: [
            { AttributeKey: 'Option 1', AttributeValue: 'opt1', UID: 'Seg1' },
            { AttributeKey: 'Option 2', AttributeValue: 'opt2', UID: 'Seg2' },
          ],
        },
      },
      Style: { css: { display: 'flex', alignItems: 'center' } },
      Slots: {},
    }
  }

  // ── All other types from RIVER_ELEM_DEFS ─────────────────────────────────
  const riverDefs = {
    button:           { cfg: { LabelKey: 'Click Me', actionKey: 'btn-action' }, sty: { variant: 'primary', size: 'small' }, inp: '' },
    pill:             { cfg: { LabelKey: '' }, sty: { pillBackgroundColor: '#E0F2FE', pillTextColor: '#0369A1' }, inp: 'STATUS_FIELD' },
    'key-value':      { cfg: { LabelKey: 'Field Label', AttributeType: 'string' }, sty: { color: '#111827' }, inp: 'FIELD_NAME' },
    'progress-bar':   { cfg: { LabelKey: 'Progress' }, sty: {}, inp: 'PROGRESS_FIELD' },
    text:             { cfg: { LabelKey: 'Static Text' }, sty: { color: '#111827' }, inp: '' },
    banner:           { cfg: { type: 'info', LabelKey: 'Banner Message' }, sty: {}, inp: '', container: true },
    card:             { cfg: { title: 'Card Title' }, sty: {}, inp: '', container: true },
    input:            { cfg: { LabelKey: 'Input Label', name: 'fieldName', required: false }, sty: {}, inp: '' },
    combobox:         { cfg: { LabelKey: 'Select Option', name: 'comboField' }, sty: {}, inp: '' },
    'toggle-button':  { cfg: { LabelKey: 'Toggle', name: 'toggleField' }, sty: {}, inp: '' },
    search:           { cfg: { LabelKey: 'Search...', name: 'searchField' }, sty: {}, inp: '' },
    'tab-group':      { cfg: { title: 'Tabs', Tabs: [{ Name: 'Tab1', LabelKey: 'Tab 1' }, { Name: 'Tab2', LabelKey: 'Tab 2' }] }, sty: {}, inp: '', container: true, slots: { Tab1: [], Tab2: [] } },
    textarea:         { cfg: { LabelKey: 'Text Area', name: 'textareaField' }, sty: {}, inp: '' },
    checkbox:         { cfg: { LabelKey: 'Check Option', name: 'checkField' }, sty: {}, inp: '' },
    dropdown:         { cfg: { LabelKey: 'Select', name: 'dropField' }, sty: {}, inp: '' },
    'date-select':    { cfg: { LabelKey: 'Select Date', name: 'dateField' }, sty: {}, inp: '' },
    'numeric-stepper':{ cfg: { LabelKey: 'Quantity', name: 'numField' }, sty: {}, inp: '' },
    'currency-input': { cfg: { LabelKey: 'Amount', name: 'currField', locale: 'en-US' }, sty: {}, inp: '' },
    value:            { cfg: {}, sty: {}, inp: 'FIELD_NAME' },
    'value-unit':     { cfg: { unit: 'kg' }, sty: {}, inp: 'FIELD_NAME' },
    icon:             { cfg: { icon: 'info' }, sty: {}, inp: '' },
    message:          { cfg: { LabelKey: 'Message text' }, sty: {}, inp: '' },
    'currency-format':{ cfg: { locale: 'en-US' }, sty: {}, inp: 'AMOUNT_FIELD' },
    'key-value-detail':{ cfg: { LabelKey: 'Detail Label', AttributeType: 'string' }, sty: {}, inp: 'FIELD_NAME' },
    'button-icon':    { cfg: { icon: 'edit', actionKey: 'icon-action' }, sty: {}, inp: '' },
    'action-button':  { cfg: { LabelKey: 'Action', actionKey: 'main-action' }, sty: { variant: 'secondary' }, inp: '' },
    link:             { cfg: { LabelKey: 'Click Here', href: '/route' }, sty: {}, inp: '' },
    'related-link':   { cfg: { LabelKey: 'View Related' }, sty: {}, inp: 'ID_FIELD' },
    'quick-filter':   { cfg: { LabelKey: 'Filter' }, sty: {}, inp: '' },
    'filter-panel':   { cfg: { Attributes: [] }, sty: {}, inp: '' },
    accordion:        { cfg: { title: 'Accordion' }, sty: {}, inp: '', container: true },
    expandable:       { cfg: { title: 'Expandable Section' }, sty: {}, inp: '', container: true },
    form:             { cfg: { formId: 'myForm' }, sty: {}, inp: '', container: true },
    section:          { cfg: { title: 'Section Title' }, sty: {}, inp: '', container: true },
    list:             { cfg: {}, sty: {}, inp: '', container: true },
    stack:            { cfg: {}, sty: { direction: 'vertical' }, inp: '', container: true },
    flex:             { cfg: {}, sty: { css: { flexDirection: 'row', gap: '16px' } }, inp: '', container: true },
    grid:             { cfg: {}, sty: { css: { gridTemplateColumns: '1fr 1fr', gap: '16px' } }, inp: '', container: true },
    'actions-popover':{ cfg: { LabelKey: 'Export', icon: 'far-chevron-down' }, sty: { css: { height: '40px' } }, inp: '', container: true },
    carousel:         { cfg: { slidesPerPage: 5, slidesPerMove: 5, navigation: true, pagination: false, loop: false, autoplay: false, orientation: 'horizontal' }, sty: { width: '100%', slideGap: '16px', css: {} }, inp: '', container: true },
  }

  const def = riverDefs[type]
  if (def) {
    if (def.container) {
      return {
        Container: type,
        Config: { ...def.cfg },
        Style: { ...def.sty },
        Slots: def.slots || { Default: [] },
      }
    }
    return {
      Element: type,
      Input: def.inp,
      Config: { ...def.cfg },
      Style: { ...def.sty },
    }
  }

  // fallback
  const label = ELEMENT_LABELS[type] || type
  if (isContainer(type)) {
    return { Container: type, Config: { title: label }, Style: {}, Slots: { Default: [] } }
  }
  return { Element: type, Input: '', Config: { LabelKey: label }, Style: {} }
}
