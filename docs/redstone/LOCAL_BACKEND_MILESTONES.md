# Local backend milestones

Scope: one operator on the loopback-only development server. Keep Docker
isolation, request-scoped BYOK, workspace limits, and preview-origin separation.
These milestones do not claim public multi-user readiness or add authentication.
Connect the existing frontend and run a hands-on local trial **after milestone
1**, then use that trial to validate the order and acceptance criteria of 2–3.

## 1. Runnable project creation — smallest milestone

Status: implemented and verified locally; frontend connection is the next
checkpoint, not part of this milestone.

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
