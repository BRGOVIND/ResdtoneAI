# Redstone frontend foundation

## Boundary and information architecture

`frontend/` is a separate TypeScript application. It does not replace the root
BhashaSub translation page or import Python internals. During local development,
Vite proxies `/api` to the loopback Redstone API. Deploying it requires an
authenticated API boundary; the current API has no user authentication.

The shell has Workspace (the primary artifact and agent), Providers,
Ecosystem (category structure, no fake installs), Help, and Legal routes.
Unknown paths render a branded 404 with a route home. Workspace opens with an
prompt-first introduction and a short, factual project-agent-preview explanation;
the "Open the workbench" link jumps to the working controls. The workbench keeps
the preview on the left and the project and agent controls on the right. Below
desktop width, these become selectable
surfaces, with preview first. A command palette indexes navigation and available
actions; disabled future actions never simulate success.

Unknown client routes use the shared circuit-break error scene. An uncaught
React render error uses the same scene with a reload and workspace link, but
neither page exposes exception details. API failures remain inline, so a
disconnected backend does not hide the useful workspace. Scrollbars on
fine-pointer devices use a thin Redstone-colored native rail; touch scrolling
and reduced-motion behavior retain platform defaults.

The landing composer and agent panel share a local, unsaved request draft.
Continuing from the landing page opens project controls (or the agent if a
project already exists); it never sends a task. Only the explicit agent submit
uses the existing API. Imported idea text also appears in both draft fields.

For production hosting, route `/api` to the Redstone API and rewrite other
frontend paths to `index.html` so direct `/help`, `/legal`, and unknown-route
visits reach the client router. The client 404 is visual; the SPA host may
still return HTTP 200 unless a server-side routing layer is added.

## Data and component boundaries

`src/api/` owns HTTP and public response types. Components never call `fetch`.
`src/state/` owns neutral provider descriptors. The app coordinator owns
ephemeral UI state and server-response state. Events are real backend events
read from the task history endpoint after the synchronous task returns; a
future stream transport can feed the same event state. No fabricated agent
timeline is rendered. Runtime and preview state can be refreshed through the
existing project GET endpoints; a 404 means that resource has not started.

Project creation returns only an ID, not a project listing or detail view. The
current session can display the created project, but it does not invent a
durable project library. There are no file-tree or file-content API endpoints;
the project rail labels that surface unavailable. An agent task POST is
synchronous, so no progress events can arrive until it returns. Runtime and
preview APIs exist. The UI now explicitly requests a `react-vite-ts` starter
and offers start/stop controls for its isolated preview. A running app is shown
only after the backend reports a ready preview URL. First preview start may
install pinned dependencies through the restricted Docker install path.

## Security and preview

The user-entered BYOK key remains in React memory only between a successful
connection test and one agent request; it is then cleared. It is not saved to
browser storage, URLs, telemetry, workspace files, or generated code. No
analytics or service worker. API
errors are mapped to fixed, safe messages. Preview URLs are accepted only
from the API, and rendered only as an iframe on a separate origin with a
restrictive `sandbox` attribute. The gateway's default `frame-ancestors 'self'`
blocks embedding until the operator explicitly sets the UI origin. Production
also needs a distinct registrable preview domain and authentication. The
completed local P0 checks do not make the current frontend a public service.

## Visual system

Interface-led workspace: quiet neutral surfaces, dark ink, muted teal, and
terracotta actions, with a soft warm-red CSS atmosphere at the entrance.
The right-hand hero is a compact editable request composer, not
a decorative picture or simulated chat. The empty preview states that no app
is running; it never substitutes artwork for a real application. Earlier
sculptural assets remain unused under `frontend/public/art/`. The dust-inspired
mark and favicon remain original SVG, not game assets. No image service or
hero image download is required at runtime.

The public [Lovable landing page](https://lovable.dev/) informed the compact
composer, spacious entry, and simple product hierarchy. Redstone keeps its
own split layout, dust mark, warm palette, copy, and existing workbench.
Starting-point buttons only fill the shared editable draft; they never create
a project or submit a task. No third-party visual assets or site code are used.
The original Redstone signal path below the hero responds to actual in-memory
draft text, the current project's presence, and a ready preview with an
accepted separate-origin URL. Its disconnected and unavailable states stay
unlit; it does not imply task progress or make network requests.
Typography is temporary and fully tokenized (`--font-display`,
`--font-body`, `--font-mono`; semantic size tokens). Color, spacing, borders,
and motion are CSS variables. System sans-serif display type and restrained
headings keep the interface primary rather than making it a presentation.

One-shot panel/mark entrances and small control transitions give the
interface motion without a JavaScript animation loop. `prefers-reduced-motion`
disables them. Focus rings, semantic links and buttons,
labels, live status, and keyboard command access are built in. Navigation
becomes a compact rail on smaller screens; workspace surfaces are chosen by
tabs instead of simply stacking three columns.

## Growth points

Provider descriptors are neutral records (`server`, `byok`, `local` modes).
The two existing gateway adapters can be selected for request-scoped BYOK;
future local providers remain informational, not live connections. Skills,
plugins, tools, models, and
Markdown docs share a future discovery taxonomy; no catalog endpoint, install
operation, pricing, or fake item is implemented yet. Future commands should
carry capability checks and route to typed API methods, not bespoke component
fetches.

The agent panel accepts a local `.txt` or `.md` idea file up to 16 KB. Reading
it fills the editable draft; no upload occurs on file selection. Only pressing
Send uses the existing agent API. The user should inspect the draft and remove
secrets before sending. Other media need a future reviewed backend contract.

## Art-direction prompt

> Make Redstone feel like a useful AI development workspace. Put a real,
> editable request draft on the right of a short introduction, then show the
> project-agent-preview workbench. Use quiet neutral surfaces, readable system
> type, muted teal, and terracotta actions. Keep the copy plain and specific.
> Use sentence-case labels, open spacing, and restrained motion with
> reduced-motion support. No decorative pictures, generic AI slogans,
> simulated conversations, fake events, or placeholder installs. Never send
> a task from the introduction or make an empty preview look like a running app.

## Public-launch boundary

This site deliberately has `noindex,nofollow` while authentication, P0 security,
operator identification, hosting, retention, third-party processing, and
public service terms remain unresolved. The Legal route is a current-state
notice, **not** a completed privacy policy or hosted-service agreement.
GitHub `@BRGOVIND` is the only approved public contact; the git-config email
is not published. Remove `noindex` and review actual disclosures only when
the production deployment and legal/operator details are known.
The [ICO privacy-notice guide](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/)
is a useful checklist, not a substitute for jurisdiction-specific legal review.
The logo is deliberately original rather than copying game art; see the
[Minecraft usage guidelines](https://www.minecraft.net/en-us/usage-guidelines)
when evaluating any closer game-brand resemblance.

## Local use

From `frontend/`, run `npm install` then `npm run dev`. Separately run
`$env:REDSTONE_PREVIEW_FRAME_ANCESTORS='http://127.0.0.1:5173'` and
`python -m redstone.api.serve` in the API terminal. This allows only the
loopback Vite origin to frame local previews; the gateway's secure default
remains `'self'`. On **Providers**, select a provider and model, enter your
own key, and use **Test connection**. A successful test keeps the key in this
page's memory for one agent request; it is never written to browser storage.
Create a project and send a build request from the workbench. Redstone passes
the key in the request body to its existing request-scoped BYOK gateway, not
to generated project code. Reloading the page or sending the request clears
the key; enter it again for another request. Choose **Start preview** to view
the real Docker-backed app, and stop it when finished. Do not use this
loopback-only development UI as a public service. Run `npm test`, `npm run
typecheck`, and `npm run build` before committing. The frontend can render
its disconnected state without Docker or an API process.
