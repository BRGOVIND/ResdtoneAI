import { ErrorScene } from '../errors/ErrorScene'

export function NotFoundPage({ onHome }: { onHome: () => void }) {
  return <ErrorScene
    code="404"
    eyebrow="No signal here"
    title="This route isn't on the map."
    description="The address may have changed, or this page does not exist. Your workspace is still here."
    actions={<a href="/" onClick={event => { event.preventDefault(); onHome() }}>Return to workspace</a>}
  />
}
