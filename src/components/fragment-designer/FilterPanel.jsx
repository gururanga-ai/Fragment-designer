import { useState } from 'react'

const FILTER_TYPES = ['textbox', 'date', 'dropdown', 'multiselect', 'singleselect']
const FILTER_ICONS = { date: '📅', multiselect: '☑️', singleselect: '🔘', dropdown: '🔽', textbox: '✏️' }

// ── Build filter-panel element from sections ──────────────────────────────────
export function buildFilterElement(filterSections) {
  const sections = filterSections.map(sec => {
    const attrs = sec.filters.map(f => {
      const attr = {
        UID: `Filter_${f.key || 'field'}`,
        Input: f.key,
        AttributeType: 'string',
        LabelKey: f.label,
      }
      const ph = f.placeholder || `Enter ${f.label}`
      if (f.type === 'date') {
        attr.Filter = { Type: 'Date-range', Placeholder: { LabelKey: ph }, RangeSelect: true }
      } else if (f.type === 'multiselect' || f.type === 'singleselect') {
        const filt = {
          Type: f.type === 'multiselect' ? 'Multiselect' : 'Singleselect',
          Placeholder: { LabelKey: ph },
        }
        if (f.staticList) {
          if (f.staticList.startsWith('{:') || f.staticList.startsWith(':')) {
            filt.StaticList = f.staticList
          } else {
            try { filt.StaticList = JSON.parse(f.staticList) } catch { filt.StaticList = f.staticList }
          }
        }
        if (f.entityKey) filt.EntityKey = f.entityKey
        if (f.entityValue) filt.EntityValue = f.entityValue
        attr.Filter = filt
      } else if (f.type === 'dropdown') {
        attr.Filter = {
          Type: 'Select',
          Placeholder: { LabelKey: ph },
          Options: [{ Id: 'OPTION_1', LabelKey: 'Option 1' }, { Id: 'OPTION_2', LabelKey: 'Option 2' }],
        }
      } else {
        attr.Filter = { Type: 'Textbox', Placeholder: { LabelKey: ph } }
      }
      return attr
    })
    return { Type: 'Object', SectionName: sec.name, Attributes: attrs }
  })
  return {
    Element: 'filter-panel',
    // showFooter/showApplyButton/showClearButton are NOT part of this platform's filter-panel
    // schema — a fragment carrying them gets rejected at publish/save time with "Invalid data for
    // the field Content" (fwe::10013), confirmed against real Composer-accepted exports.
    Config: {
      Sections: sections,
    },
  }
}

// ── Parse an existing filter-panel JSON node → filterSections format ──────────
export function parseFPNode(fpNode) {
  if (!fpNode) return null
  const cfg = fpNode.Config || {}
  const sections = cfg.Sections || (cfg.Attributes ? [{ SectionName: 'Filters', Attributes: cfg.Attributes }] : [])
  if (sections.length === 0) return null
  return sections.map((sec, si) => ({
    id: `sec_${si}_${Date.now()}`,
    name: sec.SectionName || 'Filters',
    filters: (sec.Attributes || []).map((attr, ai) => {
      const filt = attr.Filter || {}
      const ft = (() => {
        const t = filt.Type || 'Textbox'
        if (t === 'Date-range') return 'date'
        if (t === 'Multiselect') return 'multiselect'
        if (t === 'Singleselect') return 'singleselect'
        if (t === 'Select') return 'dropdown'
        return 'textbox'
      })()
      let staticList = ''
      if (filt.StaticList) {
        staticList = typeof filt.StaticList === 'string'
          ? filt.StaticList
          : JSON.stringify(filt.StaticList)
      }
      return {
        id: `f_${si}_${ai}_${Date.now()}`,
        type: ft,
        label: attr.LabelKey || '',
        key: attr.Input || '',
        placeholder: filt.Placeholder?.LabelKey || '',
        staticList,
        entityKey: filt.EntityKey || '',
        entityValue: filt.EntityValue || '',
      }
    }),
  }))
}

// ── Walk fragment tree looking for first top-level filter-panel ───────────────
export function extractFPFromFragment(fragment) {
  if (!fragment) return null
  // Check if root is filter-panel
  if (fragment.Element === 'filter-panel' || fragment.Container === 'filter-panel') return fragment
  // Check sidebar/flyout patterns
  if (fragment.Slots) {
    for (const slot of Object.values(fragment.Slots)) {
      if (!Array.isArray(slot)) continue
      for (const child of slot) {
        if (child?.Element === 'filter-panel' || child?.Container === 'filter-panel') return child
        // Inside flyout-card
        if (child?.Container === 'flyout-card') {
          for (const s2 of Object.values(child.Slots || {})) {
            if (!Array.isArray(s2)) continue
            for (const c2 of s2) {
              if (c2?.Element === 'filter-panel' || c2?.Container === 'filter-panel') return c2
            }
          }
        }
      }
    }
  }
  return null
}

// ── Default empty section ─────────────────────────────────────────────────────
export function makeDefaultSection(name = 'Filters') {
  return { id: `sec_${Date.now()}`, name, filters: [] }
}

// ── StaticList Modal ──────────────────────────────────────────────────────────
function StaticListModal({ filter, onSave, onClose }) {
  const isVar = !filter.staticList || filter.staticList.startsWith('{:') || filter.staticList.startsWith(':')
  const [mode, setMode] = useState(isVar ? 'var' : 'inline')
  const [varRef, setVarRef] = useState(
    isVar ? (filter.staticList || '') : ''
  )
  const [entityKey, setEntityKey] = useState(filter.entityKey || 'key')
  const [entityValue, setEntityValue] = useState(filter.entityValue || 'value')
  const [rows, setRows] = useState(() => {
    if (!isVar && filter.staticList) {
      try {
        const parsed = JSON.parse(filter.staticList)
        if (Array.isArray(parsed)) {
          const ek = filter.entityKey || Object.keys(parsed[0] || {})[0] || 'key'
          const ev = filter.entityValue || Object.keys(parsed[0] || {})[1] || 'value'
          return parsed.map(item => ({ k: String(item[ek] ?? ''), v: String(item[ev] ?? '') }))
        }
      } catch {}
    }
    return [{ k: '', v: '' }]
  })

  const save = () => {
    if (mode === 'var') {
      let val = varRef.trim()
      if (val && !val.startsWith('{') && !val.startsWith(':')) val = '{:' + val + '}'
      onSave({ staticList: val, entityKey, entityValue })
    } else {
      const items = rows.filter(r => r.k || r.v).map(r => ({ [entityKey || 'key']: r.k, [entityValue || 'value']: r.v }))
      onSave({ staticList: items.length ? JSON.stringify(items) : '', entityKey: entityKey || 'key', entityValue: entityValue || 'value' })
    }
    onClose()
  }

  const slSummary = () => {
    if (!filter.staticList) return '(none)'
    if (filter.staticList.startsWith('{:') || filter.staticList.startsWith(':')) return `🔗 ${filter.staticList}`
    try {
      const arr = JSON.parse(filter.staticList)
      return `📋 ${arr.length} inline item${arr.length !== 1 ? 's' : ''}`
    } catch { return filter.staticList.slice(0, 30) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-[520px] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-[#1E3A8A] px-5 py-3 rounded-t-xl">
          <p className="text-white text-sm font-bold">⚙ Configure Static List</p>
          <p className="text-[#93C5FD] text-xs mt-0.5">Current: {slSummary()}</p>
        </div>

        <div className="p-5 flex-1 overflow-y-auto space-y-4">
          {/* Mode selector */}
          <div className="flex gap-4">
            {[['var','Variable Reference  (runtime injection)'],['inline','Inline Items  (hardcoded list)']].map(([m, lbl]) => (
              <label key={m} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" checked={mode === m} onChange={() => setMode(m)} className="accent-[#1E3A8A]" />
                <span className="text-sm font-semibold text-[#374151]">{lbl}</span>
              </label>
            ))}
          </div>

          {/* Variable Reference panel */}
          {mode === 'var' && (
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-4 space-y-2">
              <label className="text-xs font-semibold text-[#374151]">Variable (e.g. {'{:businessUnitData}'})</label>
              <input type="text" value={varRef} onChange={e => setVarRef(e.target.value)}
                className="w-full border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-[#2563EB]"
                placeholder="{:myVarName}" />
              <p className="text-xs text-[#64748B]">
                Framework replaces <code className="bg-[#F1F5F9] px-1 rounded">{'{:varName}'}</code> with the actual list at runtime. Use when the list comes from a server-side data binding.
              </p>
            </div>
          )}

          {/* Inline Items panel */}
          {mode === 'inline' && (
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-4 space-y-3">
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-xs font-semibold text-[#374151]">EntityKey field name</label>
                  <input type="text" value={entityKey} onChange={e => setEntityKey(e.target.value)}
                    className="w-full border rounded px-2 py-1 text-xs font-mono mt-0.5 focus:outline-none focus:border-[#2563EB]" placeholder="key" />
                </div>
                <div className="flex-1">
                  <label className="text-xs font-semibold text-[#374151]">EntityValue field name</label>
                  <input type="text" value={entityValue} onChange={e => setEntityValue(e.target.value)}
                    className="w-full border rounded px-2 py-1 text-xs font-mono mt-0.5 focus:outline-none focus:border-[#2563EB]" placeholder="value" />
                </div>
              </div>
              <div className="border border-[#E2E8F0] rounded overflow-hidden">
                <div className="flex bg-[#1E293B] text-xs font-semibold text-[#94A3B8]">
                  <div className="flex-1 px-3 py-1.5">Key ({entityKey})</div>
                  <div className="flex-1 px-3 py-1.5">Value ({entityValue})</div>
                  <div className="w-8" />
                </div>
                {rows.map((row, i) => (
                  <div key={i} className="flex items-center border-t border-[#F1F5F9]">
                    <input value={row.k} onChange={e => setRows(rs => rs.map((r, j) => j === i ? { ...r, k: e.target.value } : r))}
                      className="flex-1 px-3 py-1 text-xs border-r border-[#E2E8F0] focus:outline-none focus:bg-[#EFF6FF]" placeholder={`${entityKey} label`} />
                    <input value={row.v} onChange={e => setRows(rs => rs.map((r, j) => j === i ? { ...r, v: e.target.value } : r))}
                      className="flex-1 px-3 py-1 text-xs border-r border-[#E2E8F0] focus:outline-none focus:bg-[#EFF6FF]" placeholder={`${entityValue} value`} />
                    <button onClick={() => setRows(rs => rs.filter((_, j) => j !== i))} className="w-8 text-red-400 text-xs hover:text-red-600">✕</button>
                  </div>
                ))}
              </div>
              <button onClick={() => setRows(rs => [...rs, { k: '', v: '' }])}
                className="text-xs px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded hover:bg-[#BFDBFE]">+ Add Row</button>
            </div>
          )}
        </div>

        <div className="border-t border-[#E2E8F0] px-5 py-3 flex justify-end gap-2 bg-[#F8FAFC] rounded-b-xl">
          <button onClick={onClose} className="px-4 py-1.5 text-xs bg-[#F1F5F9] text-[#374151] rounded hover:bg-[#E2E8F0]">Cancel</button>
          <button onClick={save} className="px-5 py-1.5 text-xs bg-[#1E3A8A] text-white rounded font-semibold hover:bg-[#1E40AF]">OK</button>
        </div>
      </div>
    </div>
  )
}

// ── FilterRow ─────────────────────────────────────────────────────────────────
function FilterRow({ filter, poolKeys, onUpdate, onRemove, onMoveUp, onMoveDown }) {
  const [slModal, setSlModal] = useState(false)
  const needsSL = filter.type === 'multiselect' || filter.type === 'singleselect'

  const slSummary = () => {
    const sl = filter.staticList
    if (!sl) return '(no list — click Edit List…)'
    if (sl.startsWith('{:') || sl.startsWith(':')) return `🔗 ${sl}`
    try { const arr = JSON.parse(sl); return `📋 ${arr.length} item${arr.length !== 1 ? 's' : ''}` } catch { return sl.slice(0, 30) }
  }

  return (
    <>
      {slModal && (
        <StaticListModal
          filter={filter}
          onSave={upd => onUpdate('__sl', upd)}
          onClose={() => setSlModal(false)}
        />
      )}
      <div className="bg-[#F8FAFC] rounded border border-[#E2E8F0] p-2 mb-1.5">
        {/* Row 1: type / label / key / placeholder / actions */}
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-sm w-5 shrink-0">{FILTER_ICONS[filter.type] || '✏️'}</span>
          <select value={filter.type} onChange={e => onUpdate('type', e.target.value)}
            className="border rounded px-1 py-0.5 text-xs bg-white text-[#374151] focus:outline-none focus:border-[#2563EB]">
            {FILTER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={filter.label} onChange={e => onUpdate('label', e.target.value)} placeholder="Label"
            className="flex-1 min-w-16 border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:border-[#2563EB]" />
          {poolKeys.length > 0 ? (
            <div className="flex-1 flex flex-col min-w-24 gap-1">
              <select value={filter.key} onChange={e => onUpdate('key', e.target.value)}
                className="w-full border rounded px-1.5 py-0.5 text-xs bg-white font-mono focus:outline-none focus:border-[#2563EB]">
                <option value="">-- select from pool --</option>
                {poolKeys.map(k => <option key={k} value={k}>{k}</option>)}
              </select>
              <input value={filter.key} onChange={e => onUpdate('key', e.target.value)} placeholder="BACKEND_KEY"
                className="w-full border rounded px-1.5 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB]" />
            </div>
          ) : (
            <input value={filter.key} onChange={e => onUpdate('key', e.target.value)} placeholder="BACKEND_KEY"
              className="flex-1 min-w-24 border rounded px-1.5 py-0.5 text-xs font-mono focus:outline-none focus:border-[#2563EB]" />
          )}
          <input value={filter.placeholder} onChange={e => onUpdate('placeholder', e.target.value)} placeholder="Placeholder"
            className="flex-1 min-w-16 border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:border-[#2563EB]" />
          <div className="flex gap-0.5 shrink-0">
            {onMoveUp && <button onClick={onMoveUp} className="text-[#94A3B8] text-xs px-0.5 hover:text-[#374151]">▲</button>}
            {onMoveDown && <button onClick={onMoveDown} className="text-[#94A3B8] text-xs px-0.5 hover:text-[#374151]">▼</button>}
            <button onClick={onRemove} className="px-1.5 py-0.5 bg-[#FEE2E2] text-[#991B1B] rounded text-xs hover:bg-red-200 ml-1">✕</button>
          </div>
        </div>

        {/* Row 2: StaticList editor (multiselect / singleselect only) */}
        {needsSL && (
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-xs text-[#64748B] font-semibold">List:</span>
            <button onClick={() => setSlModal(true)}
              className="text-xs px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded hover:bg-[#BFDBFE]">
              📋 Edit List…
            </button>
            <span className="text-[10px] text-[#64748B] truncate max-w-32">{slSummary()}</span>
          </div>
        )}
      </div>
    </>
  )
}

// ── Section editor ────────────────────────────────────────────────────────────
function SectionEditor({ section, poolKeys, onUpdate, onRemove, canRemove }) {
  const updateFilter = (fid, field, val) => {
    if (field === '__sl') {
      // val is { staticList, entityKey, entityValue }
      onUpdate({ ...section, filters: section.filters.map(f => f.id === fid ? { ...f, ...val } : f) })
    } else {
      onUpdate({ ...section, filters: section.filters.map(f => f.id === fid ? { ...f, [field]: val } : f) })
    }
  }
  const removeFilter = fid => onUpdate({ ...section, filters: section.filters.filter(f => f.id !== fid) })
  const moveFilter = (i, dir) => {
    const arr = [...section.filters]; const t = i + dir
    if (t < 0 || t >= arr.length) return
    ;[arr[i], arr[t]] = [arr[t], arr[i]]
    onUpdate({ ...section, filters: arr })
  }
  const addFilter = type => onUpdate({
    ...section,
    filters: [...section.filters, { id: `f_${Date.now()}`, type, label: 'Field Label', key: 'BACKEND_KEY', placeholder: '', staticList: '', entityKey: '', entityValue: '' }],
  })

  return (
    <div className="border border-[#E2E8F0] rounded-lg mb-2 overflow-hidden">
      {/* Section header */}
      <div className="bg-[#1E3A8A] px-3 py-1.5 flex items-center gap-2">
        <span className="text-white text-xs font-bold shrink-0">📂 Section:</span>
        <input value={section.name} onChange={e => onUpdate({ ...section, name: e.target.value })}
          className="flex-1 bg-transparent text-white text-xs font-semibold border-b border-[#3B82F6] outline-none placeholder-[#93C5FD]"
          placeholder="Section Name (e.g. Filters)" />
        {canRemove && (
          <button onClick={onRemove} className="text-[#FCA5A5] text-xs hover:text-white ml-2 shrink-0">✕ Remove Section</button>
        )}
      </div>

      <div className="p-2">
        {/* Add filter type buttons */}
        <div className="flex gap-1 flex-wrap mb-2">
          {[['date','📅','Date'],['dropdown','🔽','Dropdown'],['multiselect','☑️','Multi'],['singleselect','🔘','Single'],['textbox','✏️','Text']].map(([t, ico, lbl]) => (
            <button key={t} onClick={() => addFilter(t)}
              className="text-[10px] px-1.5 py-0.5 bg-[#F1F5F9] text-[#374151] rounded hover:bg-[#DBEAFE] hover:text-[#1E3A8A] border border-[#E2E8F0]">
              {ico} +{lbl}
            </button>
          ))}
        </div>

        {section.filters.length === 0 && (
          <p className="text-xs text-[#94A3B8] italic py-1">No filters in this section. Click above to add.</p>
        )}

        {section.filters.map((f, i) => (
          <FilterRow key={f.id} filter={f} poolKeys={poolKeys}
            onUpdate={(field, val) => updateFilter(f.id, field, val)}
            onRemove={() => removeFilter(f.id)}
            onMoveUp={i > 0 ? () => moveFilter(i, -1) : null}
            onMoveDown={i < section.filters.length - 1 ? () => moveFilter(i, 1) : null}
          />
        ))}
      </div>
    </div>
  )
}

// ── Main FilterPanel ──────────────────────────────────────────────────────────
export default function FilterPanel({ filterSections, setFilterSections, varPool = {}, filterPosition, setFilterPosition }) {
  const [visible, setVisible] = useState(false)
  const poolKeys = Object.keys(varPool)
  const totalFilters = filterSections.reduce((s, sec) => s + sec.filters.length, 0)

  const addSection = () => setFilterSections(prev => [...prev, { id: `sec_${Date.now()}`, name: `Section ${prev.length + 1}`, filters: [] }])
  const updateSection = (id, updated) => setFilterSections(prev => prev.map(s => s.id === id ? updated : s))
  const removeSection = id => setFilterSections(prev => prev.filter(s => s.id !== id))

  return (
    <div className="border-b border-[#E2E8F0] bg-white shrink-0">
      {/* Toggle header */}
      <div className="flex items-center px-3 py-2 cursor-pointer hover:bg-[#F8FAFC] select-none" onClick={() => setVisible(v => !v)}>
        <span className="text-xs font-bold text-[#374151] flex items-center gap-1.5">
          <span>{visible ? '▼' : '▶'}</span>
          <span>🔍 Filters</span>
          {totalFilters > 0 && (
            <span className="px-1.5 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] rounded-full text-[10px] font-bold">{totalFilters}</span>
          )}
          {filterSections.length > 1 && (
            <span className="px-1.5 py-0.5 bg-[#F0FDF4] text-[#15803D] rounded-full text-[10px]">{filterSections.length} sections</span>
          )}
        </span>
        {visible && (
          <div className="ml-auto flex items-center gap-2" onClick={e => e.stopPropagation()}>
            <span className="text-xs text-[#94A3B8]">Position:</span>
            <select value={filterPosition} onChange={e => setFilterPosition(e.target.value)}
              className="text-xs border rounded px-1 py-0.5 text-[#374151] bg-white focus:outline-none">
              <option value="top">Top</option>
              <option value="left">Left Sidebar</option>
              <option value="right">Right Sidebar</option>
              <option value="none">None (exclude)</option>
            </select>
          </div>
        )}
      </div>

      {visible && (
        <div className="px-3 pb-3">
          {filterSections.map(sec => (
            <SectionEditor key={sec.id} section={sec} poolKeys={poolKeys}
              onUpdate={updated => updateSection(sec.id, updated)}
              onRemove={() => removeSection(sec.id)}
              canRemove={filterSections.length > 1}
            />
          ))}
          <button onClick={addSection}
            className="text-xs px-3 py-1 bg-[#F0FDF4] text-[#15803D] border border-[#86EFAC] rounded hover:bg-[#DCFCE7]">
            + Add Section
          </button>
        </div>
      )}
    </div>
  )
}

// ── Standalone slot filter panel editor (used in TabGroupConfigEditor) ─────────
export function SlotFilterEditor({ fpNode, onChange, varPool = {} }) {
  const poolKeys = Object.keys(varPool)
  const [localSections, setLocalSections] = useState(() => {
    if (!fpNode) return [{ id: 'sec_0', name: 'Filters', filters: [] }]
    return parseFPNode(fpNode) || [{ id: 'sec_0', name: 'Filters', filters: [] }]
  })

  const apply = (sections) => {
    setLocalSections(sections)
    const built = buildFilterElement(sections)
    // Merge back into the existing fpNode to preserve unrecognized fields — but drop
    // showFooter/showApplyButton/showClearButton if a legacy/imported fragment already had them;
    // they're not part of this platform's filter-panel schema and get rejected at publish time
    // with "Invalid data for the field Content" (fwe::10013), so any edit here also cleans them up.
    const { showFooter, showApplyButton, showClearButton, ...cleanConfig } = fpNode?.Config || {}
    const merged = {
      ...fpNode,
      Element: fpNode?.Element || 'filter-panel',
      Config: {
        ...cleanConfig,
        Sections: built.Config.Sections,
      },
    }
    onChange(merged)
  }

  return (
    <div className="space-y-1 mt-1">
      {localSections.map((sec, si) => (
        <SectionEditor key={sec.id} section={sec} poolKeys={poolKeys}
          onUpdate={updated => { const arr = localSections.map((s, i) => i === si ? updated : s); apply(arr) }}
          onRemove={() => { const arr = localSections.filter((_, i) => i !== si); apply(arr) }}
          canRemove={localSections.length > 1}
        />
      ))}
      <button onClick={() => {
        const arr = [...localSections, { id: `sec_${Date.now()}`, name: `Section ${localSections.length + 1}`, filters: [] }]
        apply(arr)
      }} className="text-xs px-3 py-1 bg-[#F0FDF4] text-[#15803D] border border-[#86EFAC] rounded hover:bg-[#DCFCE7]">
        + Add Section
      </button>
    </div>
  )
}
