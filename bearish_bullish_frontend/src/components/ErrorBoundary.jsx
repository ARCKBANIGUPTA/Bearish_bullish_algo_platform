import { Component } from 'react'

/** @extends {Component<{ children: import('react').ReactNode }, { error: Error | null }>} */
export class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('UI error', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-slate-400">
          <p>Something went wrong rendering this panel.</p>
          <code className="text-xs text-rose-300">{this.state.error.message}</code>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-slate-200 hover:bg-slate-700"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
