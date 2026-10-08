import { useState } from 'react'
import type { FormEvent } from 'react'
import type { BYOKConfig } from '../../api/types'
import { Glyph } from '../../components/Glyph'
import { providers } from '../../state/providers'

interface Props {
  connected: boolean
  onTest: (config: BYOKConfig) => Promise<boolean>
  onClear: () => void
}

export function ProviderPage({ connected, onTest, onClear }: Props) {
  const [provider, setProvider] = useState<BYOKConfig['provider']>('gemini')
  const [model, setModel] = useState('gemini-3.8-flash')
  const [key, setKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const changed = () => { onClear(); setResult(null) }
  const test = async (event: FormEvent) => {
    event.preventDefault()
    if (!key.trim() || !model.trim() || testing) return
    setTesting(true); setResult(null)
    try {
      const config: BYOKConfig = {
        provider, model: model.trim(), api_key: key,
        ...(provider === 'openai-compatible' && baseUrl.trim() ? { base_url: baseUrl.trim() } : {}),
      }
      const ready = await onTest(config)
      setResult(ready ? 'Connected. Key ready for one build request.' : 'Provider rejected connection. Check key, model, and endpoint.')
      if (ready) setKey('')
    } catch {
      onClear()
      setResult('Connection failed. Check provider, model, and endpoint. Your key was not saved.')
    } finally { setTesting(false) }
  }
  return <main className="interior-page provider-page">
    <div className="eyebrow">The power source</div>
    <div className="interior-heading"><div><h1>Choose your intelligence.</h1><p>Redstone is designed for your infrastructure, your models, your terms.</p></div></div>
    <div className="section-bar"><span>Local provider connection</span><span>Key stays in memory for one build request</span></div>
    <form className="provider-connect" onSubmit={test} autoComplete="off">
      <label htmlFor="byok-provider">Provider</label>
      <select id="byok-provider" value={provider} onChange={event => { const next = event.target.value as BYOKConfig['provider']; setProvider(next); setModel(next === 'gemini' ? 'gemini-3.8-flash' : ''); changed() }} disabled={testing}>
        <option value="gemini">Gemini</option><option value="openai-compatible">OpenAI-compatible</option>
      </select>
      <label htmlFor="byok-model">Model</label>
      <input id="byok-model" value={model} maxLength={128} onChange={event => { setModel(event.target.value); changed() }} disabled={testing} spellCheck={false}/>
      {provider === 'openai-compatible' && <><label htmlFor="byok-base-url">Provider base URL</label><input id="byok-base-url" type="url" value={baseUrl} onChange={event => { setBaseUrl(event.target.value); changed() }} disabled={testing} placeholder="https://api.example.com/v1" spellCheck={false}/></>}
      <label htmlFor="byok-key">API key</label>
      <input id="byok-key" type="password" value={key} onChange={event => { setKey(event.target.value); changed() }} minLength={8} maxLength={4096} disabled={testing} autoComplete="new-password" spellCheck={false}/>
      <button className="primary-button" type="submit" disabled={testing || !key.trim() || !model.trim()}>{testing ? 'Testing…' : 'Test connection'}</button>
      <p role="status">{result ?? (connected ? 'Connected. Key ready for one build request.' : 'No key connected. Enter one to test before building.')}</p>
      <p>Local session only. No account or credential storage. Close or reload this page to discard key.</p>
    </form>
    <div className="provider-grid">{providers.map(provider => <article className="provider-row" key={provider.id}>
      <div className="provider-mark"><Glyph name={provider.kind === 'local' ? 'orbit' : 'spark'}/></div>
      <div className="provider-copy"><h2>{provider.name}</h2><p>{provider.note}</p><div className="provider-modes">{provider.modes.map(mode => <span key={mode}>{mode === 'byok' ? 'Bring your key' : mode === 'local' ? 'On your machine' : 'Server managed'}</span>)}</div></div>
      <span className="availability">{provider.availability === 'backend-supported' ? 'Gateway adapter' : 'Planned'}</span>
    </article>)}</div>
    <aside className="security-note"><Glyph name="orbit"/><div><strong>Your key is used only for provider test and next build.</strong><p>It is not saved to disk or sent to project code. Redstone sends it in request bodies to its local API, never in URLs. Local providers remain planned.</p></div></aside>
  </main>
}
