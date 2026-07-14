import { useState } from 'react'
import Modal from '../shared/Modal'
import JsonEditor from '../shared/JsonEditor'

const STARTER = { Name: 'myContent', AgentContentType: 'inputs', Content: '' }

export default function ContentsManager({ contents, onContentsChange, onClose }) {
  const [selIdx, setSelIdx] = useState(null)
  const [editing, setEditing] = useState(null) // { idx: number|null, json: object }

  const sel = selIdx !== null ? contents[selIdx] : null

  const openAdd = () => setEditing({ idx: null, json: STARTER })
  const openEdit = () => {
    if (selIdx === null) return
    setEditing({ idx: selIdx, json: structuredClone(contents[selIdx]) })
  }

  const saveEdit = json => {
    if (editing.idx === null) {
      onContentsChange([...contents, json])
      setSelIdx(contents.length)
    } else {
      const updated = [...contents]
      updated[editing.idx] = json
      onContentsChange(updated)
    }
    setEditing(null)
  }

  const handleDelete = () => {
    if (selIdx === null) return
    const name = contents[selIdx]?.Name || `item ${selIdx + 1}`
    if (!confirm(`Delete '${name}'?`)) return
    onContentsChange(contents.filter((_, i) => i !== selIdx))
    setSelIdx(null)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async e => {
      const file = e.target.files[0]
      if (!file) return
      try {
        const data = JSON.parse(await file.text())
        onContentsChange([...contents, ...(Array.isArray(data) ? data : [data])])
      } catch (err) { alert(`Import error: ${err.message}`) }
    }
    input.click()
  }

  return (
    <Modal title="Contents Manager — agentContentsCustom" onClose={onClose} width="max-w-4xl">
      {/* Toolbar */}
      <div className="bg-[#F1F5F9] px-4 py-2 flex gap-2 border-b border-[#CBD5E1]">
        <Btn label="+ Add Item" onClick={openAdd} />
        <Btn label="Edit Selected" onClick={openEdit} disabled={selIdx === null} amber />
        <Btn label="Delete Selected" onClick={handleDelete} disabled={selIdx === null} red />
        <Btn label="Import JSON Array" onClick={handleImport} />
      </div>

      <div className="flex h-[500px]">
        {/* List */}
        <div className="w-64 border-r border-[#CBD5E1] flex flex-col shrink-0">
          <p className="px-3 pt-3 pb-1 text-xs font-semibold text-[#94A3B8]">Items ({contents.length})</p>
          <div className="flex-1 overflow-y-auto">
            {contents.length === 0 && (
              <p className="px-3 py-4 text-sm text-[#94A3B8]">No contents yet.</p>
            )}
            {contents.map((item, i) => {
              const name = item.Name || item.name || `item_${i + 1}`
              const type = item.AgentContentType || item.contentType || ''
              return (
                <button
                  key={i}
                  onClick={() => setSelIdx(i)}
                  onDoubleClick={() => openEdit()}
                  className={`w-full text-left px-3 py-2 text-sm border-b border-[#F1F5F9] ${
                    selIdx === i ? 'bg-[#DBEAFE] text-[#1E3A8A]' : 'hover:bg-[#F8FAFC]'
                  }`}
                >
                  <p className="font-medium truncate">{name}</p>
                  {type && <p className="text-xs text-[#94A3B8]">[{type}]</p>}
                </button>
              )
            })}
          </div>
        </div>

        {/* Preview */}
        <div className="flex-1 flex flex-col min-w-0">
          <p className="px-4 pt-3 pb-1 text-xs font-semibold text-[#94A3B8]">
            {sel ? `Item ${selIdx + 1}: ${sel.Name || sel.name || '?'}` : 'Select an item to preview its JSON'}
          </p>
          <div className="flex-1 overflow-auto bg-[#1E293B] mx-4 mb-4 rounded p-3">
            <pre className="text-[#E2E8F0] text-xs font-mono leading-relaxed">
              {sel ? JSON.stringify(sel, null, 2) : '// Select an item to preview'}
            </pre>
          </div>
        </div>
      </div>

      {editing && (
        <ContentEditorModal
          json={editing.json}
          isNew={editing.idx === null}
          onSave={saveEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </Modal>
  )
}

function ContentEditorModal({ json, isNew, onSave, onClose }) {
  const [current, setCurrent] = useState(null)
  const [error, setError] = useState('')

  const handleSave = () => {
    if (!current) { onSave(json); onClose(); return }
    onSave(current)
    onClose()
  }

  return (
    <Modal title={isNew ? 'New Content Item' : 'Edit Content Item'} onClose={onClose}>
      <div className="p-4 space-y-3">
        <JsonEditor
          value={json}
          onChange={(parsed, _) => { setCurrent(parsed); setError('') }}
          height="320px"
        />
        {error && <p className="text-red-500 text-xs">⚠ {error}</p>}
        <div className="flex gap-2">
          <button onClick={handleSave} className="px-4 py-2 bg-[#DBEAFE] text-[#1E3A8A] rounded text-sm font-semibold">Save</button>
          <button onClick={onClose} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm">Cancel</button>
        </div>
      </div>
    </Modal>
  )
}

function Btn({ label, onClick, disabled, red, amber }) {
  const bg = red ? '#FEE2E2' : amber ? '#FEF3C7' : '#DBEAFE'
  const fg = red ? '#991B1B' : amber ? '#92400E' : '#1E3A8A'
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-3 py-1 text-xs rounded font-medium disabled:opacity-40"
      style={{ backgroundColor: bg, color: fg }}
    >
      {label}
    </button>
  )
}
