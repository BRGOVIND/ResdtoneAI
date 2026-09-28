import type { ReactNode } from 'react'
import { BrandMark } from '../../components/BrandMark'

interface Props {
  code: string
  eyebrow: string
  title: string
  description: string
  actions: ReactNode
}

export function ErrorScene({ code, eyebrow, title, description, actions }: Props) {
  return <main className="error-page">
    <div className="error-page-copy">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="error-page-actions">{actions}</div>
    </div>
    <div className="error-page-visual" aria-hidden="true">
      <span className="error-page-code">{code}</span>
      <span className="error-page-line"><BrandMark/></span>
      <span className="error-page-caption">Redstone / signal interrupted</span>
    </div>
  </main>
}
