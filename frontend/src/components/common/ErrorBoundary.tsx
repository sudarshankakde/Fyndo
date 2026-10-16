import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled runtime error in Fyndo UI:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-6 font-sans text-stone-900">
          <div className="max-w-md w-full bg-white rounded-3xl border border-stone-200/80 p-8 shadow-card text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto shadow-inner">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-stone-900">Something went wrong</h1>
              <p className="text-xs text-stone-500 mt-1 leading-relaxed">
                An unexpected display error occurred. Please refresh the page or return to the home screen.
              </p>
            </div>
            <div className="pt-2 flex gap-3">
              <Button onClick={() => (window.location.href = '/')} variant="outline" className="flex-1 text-xs">
                Go to Home
              </Button>
              <Button onClick={this.handleReset} variant="primary" className="flex-1 text-xs gap-1.5">
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reload App</span>
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
