import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from './App'
import { ErrorBoundary } from '../features/errors/ErrorBoundary'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

beforeEach(() => { window.history.replaceState({}, '', '/'); vi.stubGlobal('fetch', vi.fn(async () => json({ status: 'ok', runtime: { provider: 'docker', available: true, isolated: true } }))) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('Redstone foundation', () => {
  it('keeps disconnected workspace useful without inventing project data', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network') }))
    render(<App />)
    expect(screen.getByRole('heading', { name: /make the thing you need/i })).toBeTruthy()
    expect(screen.getByRole('textbox', { name: /what are you building/i })).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText('No app is running yet.')).toBeTruthy()
    expect(screen.getByRole('heading', { name: /a draft is only the beginning/i })).toBeTruthy()
    const path = within(screen.getByRole('region', { name: 'Redstone signal path' }))
    expect(path.getByText('Waiting for an idea')).toBeTruthy()
    expect(path.getByText('Not created')).toBeTruthy()
    expect(path.getByText('Not running')).toBeTruthy()
    expect(screen.getByRole('link', { name: /open the workbench/i }).getAttribute('href')).toBe('#workbench')
    await screen.findByText('API offline', { selector: '.workspace-meta span' })
    expect(screen.queryByText(/preview ready/i)).toBeNull()
  })

  it('carries the landing draft into the workbench without sending it', async () => {
    const user = userEvent.setup()
    render(<App />)
    const draft = screen.getByRole('textbox', { name: /what are you building/i })
    await user.type(draft, 'Build a reading tracker')
    expect(within(screen.getByRole('region', { name: 'Redstone signal path' })).getByText('Ready to review')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /continue to project/i }))
    expect((screen.getByLabelText('Describe a change') as HTMLTextAreaElement).value).toBe('Build a reading tracker')
    expect((screen.getByRole('button', { name: 'Send request' }) as HTMLButtonElement).disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Agent' }))
    await user.type(screen.getByLabelText('Describe a change'), ' with notes')
    expect((draft as HTMLTextAreaElement).value).toBe('Build a reading tracker with notes')
    expect(vi.mocked(fetch).mock.calls.every(([path]) => path === '/api/health')).toBe(true)
  })

  it('creates real project and sends request to that project only', async () => {
    const calls: { path: string; body?: string }[] = []
    vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
      calls.push({ path, body: init?.body as string | undefined })
      if (path === '/api/health') return json({ status: 'ok', runtime: { provider: 'docker', available: true, isolated: true } })
      if (path === '/api/projects') return json({ project_id: 'prj_test', workspace_id: 'ws_private', status: 'created' })
      if (path === '/api/projects/prj_test/agent') return json({ task_id: 'task_test', status: 'completed' })
      if (path === '/api/agent/tasks/task_test') return json({ task_id: 'task_test', project_id: 'prj_test', status: 'completed', current_step: 'completion', iterations_used: 1, changeset_id: null, error: null, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' })
      if (path === '/api/agent/tasks/task_test/events') return json({ events: [{ id: 'evt_test', type: 'agent.completed', project_id: 'prj_test', task_id: 'task_test', payload: {}, created_at: '2026-01-01T00:00:00Z' }] })
      return json({}, 404)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Project' }))
    await user.type(screen.getByLabelText('Project name'), 'Atlas portfolio')
    await user.click(screen.getByRole('button', { name: /create project/i }))
    await screen.findByText('Atlas portfolio')
    expect(within(screen.getByRole('region', { name: 'Redstone signal path' })).getByText('Created')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Agent' }))
    await user.type(screen.getByLabelText('Describe a change'), 'Build a portfolio')
    await user.click(screen.getByRole('button', { name: 'Send request' }))
    await screen.findByText('agent / completed')
    expect(calls.find(call => call.path.endsWith('/agent'))?.body).toBe(JSON.stringify({ message: 'Build a portfolio' }))
    expect(calls.some(call => call.path.includes('ws_private'))).toBe(false)
    expect(calls.some(call => call.body?.includes('credential'))).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Preview' }))
    await user.click(screen.getByRole('button', { name: 'Refresh runtime and preview status' }))
    await waitFor(() => expect(calls.some(call => call.path === '/api/projects/prj_test/runtime')).toBe(true))
    expect(calls.some(call => call.path === '/api/projects/prj_test/preview')).toBe(true)
    expect(screen.getByText('Not started')).toBeTruthy()
    expect(within(screen.getByRole('region', { name: 'Redstone signal path' })).getByText('Not running')).toBeTruthy()
  })

  it('lights the preview signal only for a safe reported preview URL', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn(async (path: string) => {
      if (path === '/api/health') return json({ status: 'ok', runtime: { provider: 'docker', available: true, isolated: true } })
      if (path === '/api/projects') return json({ project_id: 'prj_live', workspace_id: 'ws_private', status: 'created' })
      if (path === '/api/projects/prj_live/preview') return json({ preview_id: 'prev_live', project_id: 'prj_live', status: 'ready', url: 'https://preview.example.test/app', last_error: null, created_at: '2026-01-01T00:00:00Z', last_activity: '2026-01-01T00:00:00Z' })
      return json({}, 404)
    }))
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Project' }))
    await user.type(screen.getByLabelText('Project name'), 'Signal test')
    await user.click(screen.getByRole('button', { name: /create project/i }))
    await screen.findByText('Signal test')
    await user.click(screen.getByRole('button', { name: 'Preview' }))
    await user.click(screen.getByRole('button', { name: 'Refresh runtime and preview status' }))
    expect(await within(screen.getByRole('region', { name: 'Redstone signal path' })).findByText('Live app')).toBeTruthy()
  })

  it('shows safe error without rendering upstream response text', async () => {
    vi.stubGlobal('fetch', vi.fn(async (path: string) => path === '/api/health' ? json({ status: 'ok', runtime: { provider: 'none', available: false, isolated: false } }) : json({ error: 'SECRET: upstream traceback' }, 500)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Project' }))
    await user.type(screen.getByLabelText('Project name'), 'Broken')
    await user.click(screen.getByRole('button', { name: /create project/i }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Request failed (500)'))
    expect(screen.queryByText(/SECRET/)).toBeNull()
  })

  it('shows a safe recovery page for an uncaught render error', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const Broken = () => { throw new Error('SECRET: internal render detail') }
    try {
      render(<ErrorBoundary><Broken /></ErrorBoundary>)
      expect(screen.getByRole('heading', { name: 'The workspace hit an error.' })).toBeTruthy()
      expect(screen.getByRole('button', { name: 'Reload page' })).toBeTruthy()
      expect(screen.getByRole('link', { name: 'Return to workspace' }).getAttribute('href')).toBe('/')
      expect(document.body.textContent).not.toContain('SECRET')
    } finally {
      consoleSpy.mockRestore()
    }
  })

  it('shows ecosystem, legal notice, and a recoverable custom 404 route', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('link', { name: 'Ecosystem' }))
    expect(window.location.pathname).toBe('/ecosystem')
    expect(screen.getByRole('heading', { name: 'Skills' })).toBeTruthy()
    expect(screen.getByText(/Nothing to install yet/)).toBeTruthy()
    await user.click(screen.getByRole('link', { name: 'Privacy & legal' }))
    expect(screen.getByRole('heading', { name: 'Privacy note' })).toBeTruthy()
    window.history.pushState({}, '', '/unmapped-route')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(await screen.findByRole('heading', { name: /isn't on the map/i })).toBeTruthy()
    await user.click(screen.getByRole('link', { name: 'Return to workspace' }))
    expect(window.location.pathname).toBe('/')
  }, 15000)

  it('uses starting points as editable local drafts, never automatic tasks', async () => {
    const user = userEvent.setup()
    render(<App />)
    for (const label of ['A small app', 'A new feature', 'Fix a bug']) {
      await user.click(screen.getByRole('button', { name: label }))
      const draft = screen.getByLabelText('What are you building?') as HTMLTextAreaElement
      expect(draft.value.length).toBeGreaterThan(0)
      expect((screen.getByLabelText('Describe a change') as HTMLTextAreaElement).value).toBe(draft.value)
    }
    expect(vi.mocked(fetch).mock.calls.every(([path]) => path === '/api/health')).toBe(true)
  })

  it('reads a text idea into draft locally without submitting it', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (path: string) => path === '/api/health'
      ? json({ status: 'ok', runtime: { provider: 'none', available: false, isolated: false } })
      : json({}, 404))
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    const file = new File(['Build a garden planner'], 'idea.md', { type: 'text/markdown' })
    Object.defineProperty(file, 'text', { value: async () => 'Build a garden planner' })
    await user.upload(screen.getByLabelText('Add idea file'), file)
    expect(await screen.findAllByDisplayValue('Build a garden planner')).toHaveLength(2)
    expect(fetchMock.mock.calls.some(call => String(call[0]).includes('/agent'))).toBe(false)
  }, 15000)
})
