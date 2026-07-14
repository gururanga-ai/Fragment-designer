/**
 * Assembles the final agent JSON from the app state — mirrors Python _build_agent_json().
 */
export function buildAgentJson(config, flows, agentContentsCustom) {
  const agentId = (config.agentId || 'ext-newAgent').trim()

  const seen = new Set()
  const contents = []

  for (const item of agentContentsCustom) {
    const n = item.Name || item.name
    if (n && !seen.has(n)) { contents.push(structuredClone(item)); seen.add(n) }
  }

  const flowsOut = {}
  for (const [flowId, tasks] of Object.entries(flows)) {
    const tasksOut = {}
    for (const [taskId, actions] of Object.entries(tasks)) {
      const cleanActions = []
      for (const action of actions) {
        if (action._disabled) continue
        const frag = action._fragment_json
        if (frag && typeof frag === 'object') {
          const n = frag.Name || frag.name
          if (n && !seen.has(n)) { contents.push(structuredClone(frag)); seen.add(n) }
        }
        const clean = Object.fromEntries(
          Object.entries(action).filter(([k]) => !k.startsWith('_'))
        )
        cleanActions.push(clean)
      }
      tasksOut[taskId] = {
        taskId,
        shortName: taskId,
        description: `${taskId} task`,
        exitAtEnd: taskId !== 'default',
        cleanupFlowTagsAndVariables: false,
        cleanupTaskTagsAndVariables: false,
        collectParamUsingForm: false,
        minimumOptionalParams: 0,
        routes: [{
          condition: null,
          routeId: 'Default',
          actions: cleanActions,
          oncePerEntry: false,
          exitTask: false,
          proceedToNextRouteWhenFailure: true,
          requiredTags: '',
          exclusionTags: '',
        }],
        parameters: [],
        questions: [],
        cacheMinutes: 0,
        cacheKeyValues: {},
      }
    }
    flowsOut[flowId] = {
      id: flowId,
      shortName: `${flowId.charAt(0).toUpperCase() + flowId.slice(1)} flow`,
      description: `${flowId} flow`,
      tasks: tasksOut,
      primaryIntent: { intentId: 'default', description: 'Default intent' },
    }
  }

  const defaultsOut = {}
  for (const [k, v] of Object.entries(config.defaults || {})) {
    if (!k.trim()) continue
    const num = Number(v)
    defaultsOut[k] = isNaN(num) || v === '' ? v : num
  }

  return {
    agentId,
    agentName: (config.agentName || '').trim(),
    description: (config.description || '').trim(),
    imageUrl: (config.imageUrl || '').trim(),
    tags: [],
    category: (config.category || '').split(',').map(s => s.trim()).filter(Boolean),
    agentDiscoverable: !!config.discoverable,
    lifecycleStage: config.lifecycleStage || 'GENERAL_AVAILABILITY',
    conversational: !!config.conversational,
    voiceEnabled: !!config.voiceEnabled,
    allowAttachmentFromChat: !!config.allowAttachment,
    resourceControlled: !!config.resourceControlled,
    resourceId: config.resourceId || null,
    dataAgent: !!config.dataAgent,
    importedAgents: {},
    includeSubAgentIntents: !!config.includeSubAgentIntents,
    allowSubagentTransition: !!config.allowSubagentTransition,
    requiredParameters: [],
    agentRootResourceFolders: (config.folders || []).filter(f => f.trim()),
    importedFlows: [],
    autoGrantSubAgents: !!config.autoGrantSubAgents,
    autoEnablement: !!config.autoEnablement,
    promptsAvailable: {},
    derivedFromTemplate: false,
    agentTemplateFolders: ['/cpr/agents'],
    agentSequence: parseInt(config.agentSequence || '0', 10) || 0,
    hasEnablementFlow: false,
    implicitTags: [],
    defaults: defaultsOut,
    flows: flowsOut,
    hasExtensionPoint: true,
    agentContentsCustom: contents,
  }
}

/**
 * Builds the payload for POST {{url}}/commonui-facade/api/commonui-facade/chatbot/agent/save —
 * the stack's "publish agent" endpoint. Distinct shape from buildAgentJson's output: PascalCase
 * top-level fields, contents pulled out as their own array, and the full agent definition
 * embedded as a stringified "Content" field (contents/hasExtensionPoint stripped from it since
 * they're represented separately as AgentContentsCustom).
 */
export function buildPublishPayload(config, flows, agentContentsCustom) {
  const agentJson = buildAgentJson(config, flows, agentContentsCustom)
  const { agentContentsCustom: _contents, hasExtensionPoint: _hep, ...contentBody } = agentJson

  return {
    AgentId: agentJson.agentId,
    Description: agentJson.description,
    AgentDiscoverable: agentJson.agentDiscoverable,
    Conversational: agentJson.conversational,
    HasEnablementFlow: agentJson.hasEnablementFlow,
    LifecycleStage: agentJson.lifecycleStage,
    ImageUrl: agentJson.imageUrl,
    AgentContentsCustom: (agentContentsCustom || []).map(item => ({
      Content: typeof (item.Content ?? item.content) === 'string'
        ? (item.Content ?? item.content)
        : JSON.stringify(item.Content ?? item.content),
      AgentContentType: item.AgentContentType || item.agentContentType || 'inputs',
      Name: item.Name || item.name,
    })),
    Content: JSON.stringify(contentBody),
    Actions: { AgentContentsCustom: 'RESET', AgentCustom: 'RESET' },
  }
}

/**
 * Loads an imported agent JSON into config/flows/contents state.
 * Accepts either shape: our own flat lowercase export (buildAgentJson's output — agentId,
 * agentName, flows, agentContentsCustom, all top-level) OR the "publish to stack" shape
 * (buildPublishPayload's output — PascalCase AgentId/Description/etc, with the real flat
 * definition nested as a JSON string in "Content", and contents in a separate top-level
 * "AgentContentsCustom" array). The second shape is exactly what round-trips back from a
 * stack, so pasting it back in must work the same as pasting our own export.
 */
export function parseAgentJson(data) {
  if (typeof data.Content === 'string' && data.AgentId) {
    try {
      const inner = JSON.parse(data.Content)
      if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
        data = { ...inner, agentContentsCustom: inner.agentContentsCustom || data.AgentContentsCustom }
      }
    } catch { /* Content wasn't actually nested JSON — fall through and parse data as-is */ }
  }

  const config = {
    agentId: data.agentId || '',
    agentName: data.agentName || '',
    description: data.description || '',
    imageUrl: data.imageUrl || 'assets/converse/assets/images/agent-icons/sparkles.svg',
    category: Array.isArray(data.category) ? data.category.join(', ') : (data.category || ''),
    lifecycleStage: data.lifecycleStage || 'GENERAL_AVAILABILITY',
    discoverable: !!data.agentDiscoverable,
    dataAgent: !!data.dataAgent,
    conversational: !!data.conversational,
    voiceEnabled: !!data.voiceEnabled,
    allowAttachment: !!data.allowAttachmentFromChat,
    resourceControlled: !!data.resourceControlled,
    autoGrantSubAgents: data.autoGrantSubAgents !== false,
    autoEnablement: data.autoEnablement !== false,
    includeSubAgentIntents: data.includeSubAgentIntents !== false,
    allowSubagentTransition: data.allowSubagentTransition !== false,
    resourceId: data.resourceId || '',
    agentSequence: String(data.agentSequence || 0),
    folders: Array.isArray(data.agentRootResourceFolders) ? data.agentRootResourceFolders : [],
    defaults: Object.fromEntries(
      Object.entries(data.defaults || {}).map(([k, v]) => [k, String(v)])
    ),
  }

  const agentContentsCustom = data.agentContentsCustom || data.AgentContentsCustom || []
  const contentsByName = {}
  for (const item of agentContentsCustom) {
    const n = item.Name || item.name
    if (n) contentsByName[n] = item
  }

  const flows = {}
  for (const [flowId, flowObj] of Object.entries(data.flows || {})) {
    flows[flowId] = {}
    for (const [taskId, taskObj] of Object.entries(flowObj.tasks || {})) {
      const actions = []
      for (const route of taskObj.routes || []) {
        for (const action of route.actions || []) {
          const a = { ...action }
          if (a.type === 'renderUI' && a.inputJSON && contentsByName[a.inputJSON]) {
            a._fragment_json = contentsByName[a.inputJSON]
          }
          actions.push(a)
        }
      }
      flows[flowId][taskId] = actions
    }
  }
  if (Object.keys(flows).length === 0) flows.default = { default: [] }

  return { config, flows, agentContentsCustom }
}

/**
 * Extracts the outermost JSON value from a response string.
 */
export function extractJson(text) {
  const fb = text.indexOf('{')
  const ab = text.indexOf('[')
  if (fb === -1 && ab === -1) return null

  const candidates = []
  if (fb !== -1 && (ab === -1 || fb <= ab)) candidates.push(['{', '}', fb])
  if (ab !== -1 && (fb === -1 || ab < fb)) candidates.unshift(['[', ']', ab])
  if (fb !== -1 && ab !== -1 && ab < fb) candidates.push(['{', '}', fb])
  if (fb !== -1 && ab !== -1 && fb < ab) candidates.push(['[', ']', ab])

  for (const [open, close, start] of candidates) {
    let depth = 0, inStr = false, esc = false, end = start
    for (let i = start; i < text.length; i++) {
      const ch = text[i]
      if (esc) { esc = false; continue }
      if (ch === '\\' && inStr) { esc = true; continue }
      if (ch === '"') { inStr = !inStr; continue }
      if (inStr) continue
      if (ch === open) depth++
      else if (ch === close) { depth--; if (depth === 0) { end = i; break } }
    }
    if (depth === 0 && end > start) {
      try { return JSON.parse(text.slice(start, end + 1)) } catch (_) {}
    }
  }
  return null
}
