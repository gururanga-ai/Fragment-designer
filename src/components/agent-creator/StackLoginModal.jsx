import { useState } from 'react'
import { stackLogin, setStoredStackSession } from '../../utils/stackApi'

// Two ways in, matching what the user asked for: retrieve a token via username/password
// (POST https://<stackName>-auth.sce.manh.com/oauth/token), or paste an already-obtained token
// directly. Either way the result is stored client-side only (see stackApi.js).
export default function StackLoginModal({ onLogin, onClose }) {
  const [mode, setMode] = useState('credentials') // 'credentials' | 'token'
  const [stackName, setStackName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pastedToken, setPastedToken] = useState('')
  const [org, setOrg] = useState('')
  const [facilityId, setFacilityId] = useState('')
  const [businessUnit, setBusinessUnit] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = stackName.trim() && org.trim() && facilityId.trim() &&
    (mode === 'token' ? pastedToken.trim() : username.trim() && password.trim())

  const submit = async () => {
    if (!canSubmit || busy) return
    setBusy(true)
    setError('')
    try {
      let accessToken = pastedToken.trim()
      if (mode === 'credentials') {
        const { access_token } = await stackLogin({ stackName: stackName.trim(), username: username.trim(), password })
        accessToken = access_token
      }
      const session = {
        stackName: stackName.trim(),
        accessToken,
        org: org.trim(),
        facilityId: facilityId.trim(),
        businessUnit: businessUnit.trim() || undefined,
      }
      setStoredStackSession(session)
      onLogin(session)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const CI = 'w-full border rounded px-2 py-1.5 text-sm focus:outline-none focus:border-[#2563EB]'

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[420px] max-h-[85vh] overflow-y-auto">
        <div className="bg-[#1E3A8A] px-5 py-3.5 flex items-center justify-between">
          <span className="text-white font-bold text-sm tracking-tight uppercase">🔐 Log in to Stack</span>
          <button onClick={onClose} className="text-white/60 hover:text-white text-lg px-1">✕</button>
        </div>

        <div className="p-5 space-y-3">
          <div>
            <label className="text-xs font-semibold text-[#374151] block mb-1">Stack Name</label>
            <input value={stackName} onChange={e => setStackName(e.target.value)} className={CI} placeholder="e.g. cotys" />
            <p className="text-[10px] text-[#94A3B8] mt-1">
              Used as <code>https://{stackName || '&lt;stack&gt;'}-auth.sce.manh.com/oauth/token</code> for login
              and <code>https://{stackName || '&lt;stack&gt;'}.sce.manh.com</code> for publish.
            </p>
          </div>

          <div className="flex gap-2 border-b border-[#E2E8F0]">
            {[['credentials', 'Username / Password'], ['token', 'Paste Token']].map(([m, label]) => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px ${mode === m ? 'border-[#1E3A8A] text-[#1E3A8A]' : 'border-transparent text-[#94A3B8]'}`}>
                {label}
              </button>
            ))}
          </div>

          {mode === 'credentials' ? (
            <>
              <div>
                <label className="text-xs font-semibold text-[#374151] block mb-1">Username</label>
                <input value={username} onChange={e => setUsername(e.target.value)} className={CI} autoComplete="username" />
              </div>
              <div>
                <label className="text-xs font-semibold text-[#374151] block mb-1">Password</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} className={CI} autoComplete="current-password" />
              </div>
            </>
          ) : (
            <div>
              <label className="text-xs font-semibold text-[#374151] block mb-1">Access Token</label>
              <textarea value={pastedToken} onChange={e => setPastedToken(e.target.value)} rows={4}
                className={`${CI} font-mono text-xs resize-none`} placeholder="eyJhbGciOi..." />
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold text-[#374151] block mb-1">Org</label>
              <input value={org} onChange={e => setOrg(e.target.value)} className={CI} placeholder="e.g. INO" />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#374151] block mb-1">Facility ID</label>
              <input value={facilityId} onChange={e => setFacilityId(e.target.value)} className={CI} placeholder="e.g. INDC" />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#374151] block mb-1">Business Unit (optional)</label>
            <input value={businessUnit} onChange={e => setBusinessUnit(e.target.value)} className={CI} />
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">⚠ {error}</p>}

          <div className="flex gap-2 pt-1">
            <button onClick={submit} disabled={!canSubmit || busy}
              className="flex-1 px-4 py-2 bg-[#1E3A8A] text-white rounded text-sm font-semibold hover:bg-[#1E40AF] disabled:opacity-40">
              {busy ? 'Logging in…' : mode === 'credentials' ? 'Log In' : 'Save Token'}
            </button>
            <button onClick={onClose} className="px-4 py-2 bg-[#F1F5F9] text-[#374151] rounded text-sm">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  )
}
