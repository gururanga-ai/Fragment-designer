import { useState } from 'react'
import AgentCreator from './components/agent-creator/AgentCreator'
import FragmentDesigner from './components/fragment-designer/FragmentDesigner'
import ErrorBoundary from './components/shared/ErrorBoundary'

const TABS = [
  { id: 'agent', label: '⚙ Agent Creator' },
  { id: 'fragment', label: '🎨 Fragment Designer' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('agent')
  const [varPool, setVarPool] = useState({})
  const [varSchemas, setVarSchemas] = useState({})
  const [handoffFragment, setHandoffFragment] = useState(null)
  const [agentCreatorKey, setAgentCreatorKey] = useState(0)
  const [fragmentDesignerKey, setFragmentDesignerKey] = useState(0)

  const handleHandoff = (fragment) => {
    setHandoffFragment(fragment)
    setActiveTab('fragment')
  }

  return (
    <div className="flex flex-col h-screen bg-[#F8FAFC]">
      {/* App header */}
      <header className="bg-[#1E3A8A] text-white px-5 py-3 flex items-center gap-4 shrink-0 shadow-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-white/20 rounded flex items-center justify-center text-xl font-bold">A</div>
          <span className="text-lg font-bold tracking-tight">Active Agent Studio</span>
        </div>
        
        <div className="flex gap-1 ml-8">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-t-md text-sm font-semibold transition-all ${
                activeTab === tab.id 
                  ? 'bg-[#F8FAFC] text-[#1E3A8A] shadow-[0_-2px_4px_rgba(0,0,0,0.1)]' 
                  : 'text-white/70 hover:text-white hover:bg-white/10'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 min-h-0 relative">
        <div className={activeTab === 'agent' ? 'h-full' : 'hidden h-full'}>
          <ErrorBoundary
            key={`agent-boundary-${agentCreatorKey}`}
            title="Agent Creator crashed"
            onReset={() => setAgentCreatorKey(k => k + 1)}
          >
            <AgentCreator key={agentCreatorKey} onUpdateVarPool={setVarPool} onUpdateVarSchemas={setVarSchemas} onHandoffToDesigner={handleHandoff} />
          </ErrorBoundary>
        </div>
        <div className={activeTab === 'fragment' ? 'h-full' : 'hidden h-full'}>
          <ErrorBoundary
            key={`fragment-boundary-${fragmentDesignerKey}`}
            title="Fragment Designer crashed"
            onReset={() => setFragmentDesignerKey(k => k + 1)}
          >
            <FragmentDesigner
              key={fragmentDesignerKey}
              varPool={varPool}
              varSchemas={varSchemas}
              setVarPool={setVarPool}
              handoffFragment={handoffFragment}
              onHandoffConsumed={() => setHandoffFragment(null)}
            />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  )
}
