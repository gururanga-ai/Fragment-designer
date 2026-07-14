import { useState, useEffect } from 'react'

export default function JsonEditor({ value, onChange, height = '300px', readOnly = false }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    try {
      setText(typeof value === 'string' ? value : JSON.stringify(value, null, 2))
    } catch (_) {
      setText('')
    }
    setError('')
  }, [value])

  const handleChange = e => {
    setText(e.target.value)
    setError('')
    try {
      const parsed = JSON.parse(e.target.value)
      onChange?.(parsed, e.target.value)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(text)
      const formatted = JSON.stringify(parsed, null, 2)
      setText(formatted)
      setError('')
      onChange?.(parsed, formatted)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <textarea
        className="font-mono text-sm bg-[#1E293B] text-[#E2E8F0] p-3 rounded resize-none outline-none border border-transparent focus:border-[#3B82F6] leading-relaxed"
        style={{ height }}
        value={text}
        onChange={handleChange}
        readOnly={readOnly}
        spellCheck={false}
      />
      <div className="flex items-center gap-2">
        {!readOnly && (
          <button
            onClick={handleFormat}
            className="text-xs px-3 py-1 bg-[#FEF3C7] text-[#92400E] rounded hover:bg-[#FDE68A] font-medium"
          >
            Format JSON
          </button>
        )}
        {error && (
          <span className="text-xs text-red-500 flex-1">⚠ {error}</span>
        )}
        {!error && text && (
          <span className="text-xs text-green-600">✓ Valid JSON</span>
        )}
      </div>
    </div>
  )
}
