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

### Install reliability gate (2026-10-07)

Real Docker reproduced a product-side case on the pinned Node 24 image with
npm 11.19: npm exited zero but omitted `@rollup/rollup-linux-x64-musl` from a
fresh starter. Vite then crashed before health check. A second install through
the same registry-only egress policy fetched the missing optional package and
the preview ran. Runtime startup now performs one bounded reinstall and retry
only when the failed dev server emits Rollup's specific diagnostic. A real
Docker fault-injection test removes that package after an otherwise successful
install and proves recovery without widening network access. The full egress
suite and repeated fresh-install runs passed after this change. Earlier
`ECONNRESET` and timeout failures were not reproduced in this run; they remain
possible external or Docker-network transients, not claimed fixed by the
Rollup-specific retry.

### Milestone 2 implementation plan

1. Add a single dependency-preparation operation through the existing
   `RuntimeManager` install-only sandbox path. Share workspace admission with
   runtime/preview creation so preparation cannot race another install or a
   running preview. Do not install on the host or in `SandboxValidationRunner`.
2. Run preparation before the first agent validation, preserving the existing
   agent task lease and request-scoped BYOK. Report preparing, ready, busy,
   unavailable, and failed states honestly; keep the task/draft retryable when
   Docker or an AI provider is unavailable. Never report agent success before
   real tool, validation, and build results exist.
3. Accept only a real end-to-end local flow: fresh project, restricted install,
   agent inspection and file edit, isolated typecheck/build, and isolated
   preview. Test concurrent requests, failed-install cleanup, denied egress,
   and retry after failure with real Docker. A configured AI provider is needed
   before claiming the full agent-first path verified.

### Milestone 2 progress (2026-10-08)

Status: **in progress, not accepted**. `RuntimeManager.prepare_dependencies()` now
uses its existing bounded install sandbox and workspace admission slot before a
React agent task begins. It does not invoke host npm. A process-local manifest
digest avoids a redundant install when dependencies already exist; a changed
manifest or missing `node_modules` triggers preparation again. Failure and
cancellation leave the task retryable, and preparation runtimes are hidden from
the public runtime history. The task exposes `preparing` and emits
`agent.preparing` / `agent.ready` events. A read-only project dependency
endpoint reports `needed`, `preparing`, `ready`, `busy`, `unavailable` or
`failed` without starting work. A React task cannot be marked
completed unless isolated typecheck and build both passed after its last edit.
The build operation no longer uses npm's `--if-present`: a missing build
script is a failure, not an apparent pass.

This does **not** establish full first-task acceptance. The frontend has no
BYOK input yet, and the Redstone server process used for the final acceptance
attempt did not receive `AI_API_KEY`, so a real provider-driven portfolio task
remains unverified. The Docker-backed tests exercise actual install, validation,
and preview isolation; scripted AI
responses in existing tests do not count as a real model acceptance run.
Transient registry failures and the optional Rollup package issue remain
subject to the bounded runtime retry described above.

Verification on this checkout: 218 focused agent/runtime/preview tests passed,
including real-Docker first-task preparation, denied-network cleanup and retry,
isolated typecheck/build, the missing-build-script failure, and browser/API
preview. Frontend typecheck, build and 11 tests passed. The broad Python run
reached 1,085 passed / 1 failed; that failure was an older preview fixture
expecting an unvalidated React task to complete. The fixture was corrected and
passed in the focused rerun. The entire broad suite was not rerun after that
correction, and no real model/provider acceptance was possible without a key.

### Final acceptance attempt (2026-10-08)

The documented `python -m redstone.api.serve` command started the API and
preview gateway on loopback using a new temporary workspace root. `/api/health`
reported Docker available and isolated. A static project probe reached the
backend agent route and ended `failed` with `AI_NOT_CONFIGURED`. The Codex
task process, Windows User, and Machine environment scopes did not expose
`AI_API_KEY`; the repository contains only `.env.example`, and the Redstone
configuration loader reads `AI_API_KEY` from the process environment. This
does not establish where an operator may have configured a credential in a
different process. No real model call occurred, so the React portfolio
acceptance task was not started. Milestone 2 remains **in progress**.

The probe server was stopped. Its isolated temporary workspace was moved to
the Recycle Bin; no managed Docker containers or networks, preview, or API
listeners remained. No source files or secrets were changed. The complete
Python suite was not rerun in this attempt because the required real-provider
acceptance prerequisite failed; the previous broad-run result above is not
treated as green.

### Local provider configuration follow-up (2026-10-08)

Redstone has no `.env` loader. `python -m redstone.api.serve` calls
`load_config()`, which reads `AI_API_KEY` from its inherited process environment
and passes `AIConfig` through `create_app()` and `AgentService` to `AIGateway`.
The `GEMINI_API_KEY` / `.env` instructions in the root README apply to the
separate older BhashaSub service. The [Redstone AI provider guide](AI_PROVIDERS.md#configuration)
now gives a same-terminal PowerShell setup and a credential-free presence
check; no second configuration mechanism was added.

A synthetic, non-provider credential passed from PowerShell into a Python
child and reached `load_config()` and `AgentService`'s `AIGateway`; the provider
name was registered and a model string was present. This verifies process
inheritance and local wiring only. In this task's process and Windows User and
Machine environment scopes, `AI_API_KEY` and `GEMINI_API_KEY` were absent.
No real credential was located, backend provider detection with a real key
was not possible, and no real model or portfolio task was run. Milestone 2
therefore remained **in progress** under that server-key approach; full
acceptance was not run in that attempt. Seven
focused configuration tests passed; no backend, preview, managed Docker
container, or managed Docker network was left running by this follow-up.

### BYOK acceptance path (2026-10-08)

The operator clarified that Milestone 2 must be accepted through an end-user
credential entered in the Redstone browser, not a personal server-side
`AI_API_KEY`. The server-environment blocker above describes the earlier
attempt only; it is **not** a prerequisite for the BYOK path. The existing
agent API already accepts `byok` per request and routes it through
`EphemeralBYOK`, `AgentService`, and `AIGateway`. Frontend code previously
omitted that field. The Providers page now offers provider, model, key, and a
bounded connection test using the same gateway. It retains a successful key
only in browser memory until one build request, then clears it; no browser
storage or server credential store was added. Workbench blocks agent sends
until a provider was tested.

Mock-transport backend tests verify the BYOK key reaches the upstream auth
header, never task/events/workspace output, and provider rejection stays
bounded. Frontend tests verify the key appears only in the two intended POST
bodies, never URLs or rendered text, and is consumed after one agent request.
The focused backend API suite passed 20 tests; combined agent, gateway, and
API checks passed 106 tests. The frontend passed 12 tests,
typecheck, build, and lint. A browser accessibility check found no violations
in the provider page's main content. These are **not** a real provider/model
call or portfolio acceptance. Milestone 2 remains **in progress** until the
user enters a real key through the UI and the complete Docker-backed flow and
full Python suite pass.

## 3. Local session continuity and control

Make project identity and task state usable across a local server restart
without exposing workspace paths or credentials. Review persistence, startup
reconciliation, stale previews, cancellation, bounded progress reporting,
retention, deletion, and resource limits together. Test restart, crash,
timeout, repeated lifecycle calls, and cleanup. Keep the server loopback-only;
public authentication, account isolation, hosting, and legal policy remain a
separate decision, not an implicit outcome of these milestones.

## Security backlog outside the local milestones

- No authentication: keep API and preview listeners loopback-only. Public
  exposure remains unsupported.
- Workspace secret filtering is primarily path/name based, not content-aware.
  Do not claim arbitrary credential strings can never persist in project files.
- `EventBus` filters top-level forbidden keys, but nested lists can retain
  nested credential-shaped data. Add recursive, bounded sanitization and tests
  before treating event payloads as safe for wider exposure.
