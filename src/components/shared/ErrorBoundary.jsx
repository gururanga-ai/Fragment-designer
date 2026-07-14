import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="h-full flex items-center justify-center p-8">
          <div className="max-w-lg bg-white border border-[#FCA5A5] rounded-lg shadow-lg p-6">
            <p className="text-[#991B1B] font-bold text-sm mb-2">⚠ {this.props.title || 'Something went wrong'}</p>
            <p className="text-xs text-[#7F1D1D] font-mono bg-[#FEF2F2] rounded p-3 mb-4 whitespace-pre-wrap break-words">
              {this.state.error.message || String(this.state.error)}
            </p>
            <p className="text-xs text-[#374151] mb-4">
              This usually means the pasted/imported JSON had an unexpected shape. Fix the data or reset below.
            </p>
            <button
              onClick={() => { this.setState({ error: null }); this.props.onReset?.() }}
              className="px-4 py-2 text-xs bg-[#1E3A8A] text-white rounded-md font-semibold hover:bg-[#1E40AF]"
            >
              Reset
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
