import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './app/App'
import { ErrorBoundary } from './features/errors/ErrorBoundary'
import './styles.css'
import './accessibility.css'
import './theme.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ErrorBoundary><App /></ErrorBoundary></React.StrictMode>,
)
