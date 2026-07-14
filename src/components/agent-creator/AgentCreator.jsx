import { useState, useCallback, useEffect } from 'react'
import ConfigStep from './ConfigStep'
import FlowBuilder from './FlowBuilder'
import ExportStep from './ExportStep'
import ContentsManager from './ContentsManager'
import { buildAgentJson, parseAgentJson } from '../../utils/agentBuilder'

const DEFAULT_CONFIG = {
  agentId: '',
  agentName: '',
  description: '',
  imageUrl: 'assets/converse/assets/images/agent-icons/sparkles.svg',
  category: 'ActiveWarehouse',
  lifecycleStage: 'GENERAL_AVAILABILITY',
  discoverable: true,
  dataAgent: true,
  conversational: false,
  voiceEnabled: false,
  allowAttachment: false,
  resourceControlled: false,
  autoGrantSubAgents: true,
  autoEnablement: true,
  includeSubAgentIntents: true,
  allowSubagentTransition: true,
  resourceId: '',
  agentSequence: '0',
  folders: ['/agents/dataInsights/ext-newAgent'],
  defaults: {
    DefaultMetric: 'Units',
    DefaultGroupBy1: '',
    DefaultGroupBy2: '',
    LinkIdsSize: '500',
    'sql.limit': '200000',
  },
}

const STEP_LABELS = ['1  Configure Agent', '2  Build Flow', '3  Export JSON']

function PasteAgentJsonModal({ onImport, onClose }) {
  const [raw, setRaw] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    navigator.clipboard.readText().then(text => {
      if (text && text.trim().startsWith('{')) setRaw(text)
    }).catch(() => {})
  }, [])

  const handleLoad = () => {
    try {
      const data = JSON.parse(raw.trim())
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
          <span className="text-white font-bold text-sm tracking-tight uppercase">📋 Paste Agent JSON</span>
          <button onClick={onClose} className="text-white/60 hover:text-white text-lg px-1 transition-colors">✕</button>
        </div>

        <div className="bg-[#F1F5F9] px-5 py-2.5 border-b border-[#CBD5E1]">
          <p className="text-xs text-[#1E3A8A] font-medium italic">
            ⓘ Paste your full Agent JSON below.
          </p>
        </div>

        <div className="flex-1 min-h-0 overflow-auto p-5 bg-[#F8FAFC]">
          <textarea
            value={raw}
            onChange={e => { setRaw(e.target.value); setStatus('') }}
            rows={18}
            className="w-full border border-[#CBD5E1] rounded-lg px-4 py-3 text-xs font-mono focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-blue-200 bg-white text-[#334155] shadow-inner resize-none"
            placeholder={'{\n  "agentId": "...",\n  "agentName": "...",\n  "flows": [...]\n}'}
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
            Load Agent →
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AgentCreator({ onUpdateVarPool, onUpdateVarSchemas, onHandoffToDesigner }) {
  const [step, setStep] = useState(0)
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [flows, setFlows] = useState({ default: { default: [] } })
  const [contents, setContents] = useState([])
  const [gleanHistory, setGleanHistory] = useState([])
  const [gleanChatId, setGleanChatId] = useState(null)
  const [showContents, setShowContents] = useState(false)
  const [pasteModalOpen, setPasteModalOpen] = useState(false)

  // Listen for fragment-saved-to-agent events from FragmentDesigner
  useEffect(() => {
    const handler = (e) => {
      const { name, fragment } = e.detail || {}
      if (!name || !fragment) return
      const contentStr = JSON.stringify({ Fragment: fragment }, null, 2)
      // Update content item Content field
      setContents(prev => prev.map(c =>
        (c.Name || c.name) === name ? { ...c, Content: contentStr } : c
      ))
      // Update _fragment_json on any renderUI action pointing to this content item
      setFlows(prev => {
        const next = JSON.parse(JSON.stringify(prev))
        for (const flowObj of Object.values(next)) {
          for (const taskActions of Object.values(flowObj)) {
            if (!Array.isArray(taskActions)) continue
            for (const a of taskActions) {
              if (a.type === 'renderUI' && a.inputJSON === name) {
                a._fragment_json = { Name: name, AgentContentType: 'fragment', Content: contentStr }
              }
            }
          }
        }
        return next
      })
    }
    window.addEventListener('fragment-saved-to-agent', handler)
    return () => window.removeEventListener('fragment-saved-to-agent', handler)
  }, [])

  // Sync dataMap to global varPool and extract child attributes (varSchemas)
  useEffect(() => {
    const newPool = {}
    const allActions = []
    Object.values(flows).forEach(taskMap => {
      Object.values(taskMap).forEach(actions => {
        allActions.push(...actions)
        actions.forEach(action => {
          if (action.type === 'renderUI') {
            if (action.dataMap && typeof action.dataMap === 'object') {
              Object.assign(newPool, action.dataMap)
            }
            if (action.input && typeof action.input === 'object') {
              for (const [k, v] of Object.entries(action.input)) {
                if (typeof v === 'string') newPool[k] = v
              }
            }
          } else if (action.type === 'createUIFragment') {
             // For createUIFragment, we assume the input table name is the data source path
             const dsPath = action.inputVariableName || 'data'
             newPool[dsPath] = action.outputVariableName || action.name
          }
        })
      })
    })
    
    // Extract child attributes/columns for each mapped variable
    const newSchemas = {}
    const getActionNameFromVar = (v) => {
      if (typeof v !== 'string') return ''
      return v.replace(/^object::/, '').replace(/^[\s@]+/, '').replace(/\.result$/, '').trim()
    }

    for (const [poolKey, backendVar] of Object.entries(newPool)) {
      const actionName = getActionNameFromVar(backendVar)
      const attrs = new Set()

      const extractCols = (obj) => {
        if (!obj || typeof obj !== 'object') return
        if (Array.isArray(obj.columns)) obj.columns.forEach(c => { if (c.name) attrs.add(c.name) })
        if (Array.isArray(obj.addColumns)) obj.addColumns.forEach(c => { if (c.name) attrs.add(c.name) })
        if (Array.isArray(obj.renameColumns)) obj.renameColumns.forEach(c => { if (c.newName) attrs.add(c.newName) })
        if (Array.isArray(obj.keepColumns)) obj.keepColumns.forEach(c => attrs.add(c))
        if (Array.isArray(obj.fields)) obj.fields.forEach(f => { if (typeof f === 'string') attrs.add(f); else if (f.name) attrs.add(f.name) })
        
        // Sometimes actions define mappings in 'input' or 'output'
        if (obj.output && typeof obj.output === 'object') {
          Object.keys(obj.output).forEach(k => attrs.add(k))
        }

        // Support createUIFragment metadata extraction
        if (obj.type === 'createUIFragment' && obj.metadata) {
          if (Array.isArray(obj.metadata.columns)) {
            obj.metadata.columns.forEach(c => { if (c.value) attrs.add(c.value) })
          }
          if (obj.metadata.metrics && Array.isArray(obj.metadata.metrics.values)) {
            obj.metadata.metrics.values.forEach(m => { if (m.value) attrs.add(m.value) })
          }
        }
      }

      // 1. Check if the source action itself defines columns
      const sourceAction = allActions.find(a => a.name === actionName || a.outputVariableName === actionName)
      if (sourceAction) {
        extractCols(sourceAction)
        
        if (sourceAction.type === 'sql' && sourceAction.sql) {
          const match = sourceAction.sql.match(/SELECT\s+([\s\S]*?)\s+FROM/i)
          if (match) {
            const colsPart = match[1]
            const cols = []
            let depth = 0, current = ''
            for (let i = 0; i < colsPart.length; i++) {
              const char = colsPart[i]
              if (char === '(') depth++
              if (char === ')') depth--
              if (char === ',' && depth === 0) { cols.push(current.trim()); current = '' }
              else current += char
            }
            if (current.trim()) cols.push(current.trim())
            cols.forEach(c => {
              const m = c.match(/\s+(?:AS\s+)?([a-zA-Z0-9_]+)$/i)
              let name = m ? m[1] : c.trim()
              if (name.includes('.')) name = name.split('.').pop()
              attrs.add(name.replace(/['"`]/g, ''))
            })
          }
        }
      }

      // 2. Check downstream actions that shape or reference this variable
      allActions.forEach(a => {
        if (a.inputVariableName === actionName || a.tableName === actionName || a.outputVariableName === actionName) {
          extractCols(a)
        }
      })

      const arr = Array.from(attrs).filter(Boolean)
      if (arr.length > 0) newSchemas[poolKey] = arr
    }

    onUpdateVarPool(newPool)
    if (onUpdateVarSchemas) onUpdateVarSchemas(newSchemas)
  }, [flows, onUpdateVarPool, onUpdateVarSchemas])

  const applyImportedAgent = useCallback((data) => {
    try {
      const { config: c, flows: f, agentContentsCustom: ac } = parseAgentJson(data)
      setConfig(c)
      setFlows(f)
      setContents(ac)
      setStep(0)
      // New agent = new Glean context; don't carry over previous conversation
      setGleanChatId(null)
      setGleanHistory([])
      const contentsMsg = ac.length > 0
        ? `\n\n${ac.length} content item(s) loaded into Contents library:\n${ac.map(i => `  • ${i.Name || i.name || '?'}`).join('\n')}\n\nClick the "Contents" button to view/edit them.`
        : ''
      alert(`Agent '${data.agentId || '?'}' loaded. Review properties and proceed to Build Flow.${contentsMsg}`)
    } catch (err) {
      alert(`Import error: ${err.message}`)
    }
  }, [])

  const handleImport = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async e => {
      const file = e.target.files[0]
      if (!file) return
      try {
        const text = await file.text()
        const data = JSON.parse(text)
        applyImportedAgent(data)
      } catch (err) {
        alert(`Import error: ${err.message}`)
      }
    }
    input.click()
  }, [applyImportedAgent])

  const agentJson = buildAgentJson(config, flows, contents)

  return (
    <div className="flex flex-col h-full">
      {pasteModalOpen && (
        <PasteAgentJsonModal 
          onImport={applyImportedAgent} 
          onClose={() => setPasteModalOpen(false)} 
        />
      )}
      {/* Tab bar + actions */}
      <div className="bg-[#F1F5F9] border-b border-[#CBD5E1] px-4 flex items-center gap-1 shrink-0">
        {STEP_LABELS.map((lbl, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            className={`px-5 py-3 text-sm font-medium transition-colors ${
              step === i
                ? 'bg-[#1E3A8A] text-white'
                : 'text-[#374151] hover:text-[#1E3A8A]'
            }`}
          >
            {lbl}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setShowContents(true)}
            className="px-3 py-1.5 text-xs bg-[#FEF3C7] text-[#92400E] rounded font-medium hover:bg-[#FDE68A]"
          >
            Contents
          </button>
          <button
            onClick={handleImport}
            className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]"
          >
            Import JSON
          </button>
          <button
            onClick={() => setPasteModalOpen(true)}
            className="px-3 py-1.5 text-xs bg-[#DBEAFE] text-[#1E3A8A] rounded font-medium hover:bg-[#BFDBFE]"
          >
            Paste JSON
          </button>
        </div>
      </div>

      {/* Steps */}
      <div className="flex-1 min-h-0">
        {step === 0 && (
          <ConfigStep
            config={config}
            onConfigChange={setConfig}
            gleanHistory={gleanHistory}
            onGleanHistoryChange={setGleanHistory}
            gleanChatId={gleanChatId}
            onGleanChatIdChange={setGleanChatId}
            flows={flows}
            onFlowsChange={setFlows}
            contents={contents}
            onContentsChange={setContents}
            onHandoffToDesigner={onHandoffToDesigner}
          />
        )}
        {step === 1 && (
          <FlowBuilder
            flows={flows}
            onFlowsChange={setFlows}
            gleanHistory={gleanHistory}
            onGleanHistoryChange={setGleanHistory}
            gleanChatId={gleanChatId}
            onGleanChatIdChange={setGleanChatId}
            contents={contents}
            onContentsChange={setContents}
            onHandoffToDesigner={onHandoffToDesigner}
          />
        )}
        {step === 2 && (
          <ExportStep agentJson={agentJson} />
        )}
      </div>

      {showContents && (
        <ContentsManager
          contents={contents}
          onContentsChange={setContents}
          onClose={() => setShowContents(false)}
        />
      )}
    </div>
  )
}
