/**
 * Manhattan Active stack login + publish.
 *
 * The access token is kept in this browser's localStorage only — the backend routes are
 * stateless pass-throughs (see backend/main.py's /api/stack/* comment). Same reasoning as the
 * Glean extension rework: a shared backend must never hold one person's credentials on behalf
 * of everyone using it.
 */

const STORAGE_KEY = 'mawm-stack-session'

// The two domain families confirmed in this repo's other tools (elastic-analysis-tool's
// ensure_main_driver tries both, in this order, as fallbacks for the nexus subdomain).
// "Custom" covers everything else — Omni stacks, or any other product line's domain — since
// there's no single confirmed pattern for those to hardcode.
export const STACK_DOMAIN_PRESETS = [
  { value: 'sce.manh.com', label: '.sce.manh.com (SCE)' },
  { value: 'cp.manh.cloud', label: '.cp.manh.cloud (Cloud Platform)' },
]

export function getStoredStackSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

export function setStoredStackSession(session) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export function clearStoredStackSession() {
  localStorage.removeItem(STORAGE_KEY)
}

/** Retrieves an access token via password grant. Does not store anything. */
export async function stackLogin({ stackName, domain, username, password }) {
  const resp = await fetch('/api/stack/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stackName, domain, username, password }),
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(data.detail || `Login failed (${resp.status})`)
  return data // { access_token, expires_in }
}

/** Publishes an assembled agent payload (see agentBuilder.js buildPublishPayload). */
export async function stackPublish({ stackName, domain, accessToken, org, facilityId, businessUnit, agent }) {
  const resp = await fetch('/api/stack/publish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stackName, domain, accessToken, org, facilityId, businessUnit, agent }),
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data)
    throw new Error(detail || `Publish failed (${resp.status})`)
  }
  return data
}
