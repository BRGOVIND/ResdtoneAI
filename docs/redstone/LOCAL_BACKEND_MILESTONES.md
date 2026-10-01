# Local backend milestones

Scope: one operator on the loopback-only development server. Keep Docker
isolation, request-scoped BYOK, workspace limits, and preview-origin separation.
These milestones do not claim public multi-user readiness or add authentication.
Connect the existing frontend and run a hands-on local trial **after milestone
1**, then use that trial to validate the order and acceptance criteria of 2–3.

## 1. Runnable project creation — smallest milestone

Status: implemented and verified locally. The frontend connection and local
trial are the separate checkpoint before milestone 2.

An explicit `react-vite-ts` project request creates a minimal, editable app in
its new workspace. The old `static` default stays empty. Files are written
through the existing workspace safety/quotas; any partial creation is removed.
Project creation does not install packages, run project code, or start a
container. The response identifies the selected framework. A real-Docker test
must prove fresh API creation → restricted npm install on preview start → Vite
gateway response → isolated typecheck/build → cleanup, without hand-preparing
files. No frontend changes belong to this milestone.

Checkpoint: connect the frontend to this explicit framework choice and try the
local project/agent/preview flow. Do not treat a simulated provider or a
decorative empty preview as a success. Record the actual first-run friction.

### Local connection checkpoint (2026-10-02)

The existing frontend now requests `react-vite-ts` and exposes explicit
preview start/stop controls. In a real local browser trial, project creation
returned a real project ID; preview start installed dependencies in Docker;
the gateway served the starter app in the isolated iframe; and preview stop
removed the managed containers. The UI uses the backend's preview status,
not a simulated artifact. The local API used a temporary workspace root and
explicit `frame-ancestors` permission for `http://127.0.0.1:5173` only.

An agent request reached the backend but failed with `AI_NOT_CONFIGURED`:
this machine had no AI provider key configured. The frontend now explains that
case without displaying upstream detail and keeps the draft for retry. An
agent-first success with a configured provider remains unverified in this
trial; the dependency-readiness gap described in milestone 2 still needs its
own real-Docker acceptance test. Current sessions are ephemeral, and the UI
has no file explorer or agent-output view, so the preview is the only visual
inspection path. Those limitations remain scope for the later milestones,
not reasons to claim this is a public service.

## 2. First-task readiness

Close the first-agent-task gap the trial exposes: validation currently expects
`node_modules`, while dependency installation happens only when a runtime or
preview starts. Design one bounded preparation path using the existing
install-only egress policy, with no host execution or competing installs.
Make missing Docker, install failure, retries, and in-progress state honest in
the API. Preserve request-scoped BYOK and test install denial, concurrent
requests, failure cleanup, and an agent-first local flow against real Docker.

## 3. Local session continuity and control

Make project identity and task state usable across a local server restart
without exposing workspace paths or credentials. Review persistence, startup
reconciliation, stale previews, cancellation, bounded progress reporting,
retention, deletion, and resource limits together. Test restart, crash,
timeout, repeated lifecycle calls, and cleanup. Keep the server loopback-only;
public authentication, account isolation, hosting, and legal policy remain a
separate decision, not an implicit outcome of these milestones.
