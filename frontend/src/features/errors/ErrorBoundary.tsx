import { Component } from 'react'
import type { ReactNode } from 'react'
import { ErrorScene } from './ErrorScene'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return <ErrorScene
      code="!"
      eyebrow="Interface interrupted"
      title="The workspace hit an error."
      description="The page could not finish rendering. Reload to try again. An unsaved draft may be lost."
      actions={<><button type="button" onClick={() => window.location.reload()}>Reload page</button><a href="/">Return to workspace</a></>}
    />
  }
}
