"""Real P0 path: API, BYOK gateway, agent, isolated build, preview, browser.

Only provider HTTP is scripted. No model account or real credential is needed;
all project execution and browser requests use real Docker and Chrome.
"""

from __future__ import annotations

import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from preview_support import LiveServer, docker, free_port
from redstone.agent.service import AgentService
from redstone.ai.gateway import AIGateway
from redstone.api.app import create_app
from redstone.config import AIConfig, Limits, PreviewConfig, RedstoneConfig
from redstone.domain.models import Framework
from redstone.preview.gateway import create_preview_gateway_app
from redstone.preview.manager import PreviewManager
from redstone.runtime.manager import RuntimeManager
from redstone.runtime.validation import SandboxValidationRunner
from redstone.sandbox.providers.docker_provider import DockerSandboxProvider, docker_available

playwright_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
pytestmark = pytest.mark.skipif(not docker_available(), reason="Docker daemon not reachable")

REQUEST_KEY = "TEST_BYOK_ACCEPTANCE_KEY_9f8a7c6b"
SERVER_KEY = "TEST_SERVER_KEY_NOT_SELECTED_4e2d"

PACKAGE = {
    "name": "redstone-portfolio-acceptance",
    "version": "1.0.0",
    "private": True,
    "type": "module",
    "scripts": {"dev": "vite", "build": "tsc --noEmit && vite build"},
    "dependencies": {"react": "19.1.0", "react-dom": "19.1.0"},
    "devDependencies": {
        "@types/react": "19.1.0", "@types/react-dom": "19.1.0",
        "typescript": "5.8.3", "vite": "6.3.5",
    },
}
TSCONFIG = {
    "compilerOptions": {
        "target": "ES2020", "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext", "moduleResolution": "Bundler", "jsx": "react-jsx",
        "strict": True, "skipLibCheck": True, "noEmit": True,
        "types": ["vite/client"],
    },
    "include": ["src"],
}
INDEX = "<!doctype html><html><head><title>Portfolio</title></head><body><div id='root'></div><script type='module' src='/src/main.tsx'></script></body></html>"
MAIN = "import { createRoot } from 'react-dom/client'; import './style.css'; createRoot(document.getElementById('root')!).render(<main><section className='hero'><h1>Redstone portfolio</h1><p>Made with Redstone.</p></section></main>);"
LIGHT = "body{margin:0;background:#f6f2ea;color:#18232b;font:18px sans-serif}.hero{min-height:70vh;padding:32px;box-sizing:border-box}"
DARK = "body{margin:0;background:#111827;color:#f9fafb;font:18px sans-serif}.hero{min-height:36vh;padding:32px;box-sizing:border-box}"


def _action(kind: str, **fields: object) -> dict:
    return {"action": kind, **fields}


def _tool(name: str, **arguments: object) -> dict:
    return _action("tool_call", tool=name, arguments=arguments)


def _assert_validated(service: AgentService, task_id: str) -> None:
    task = service.get_task(task_id)
    results = [message.content for message in task.messages if message.role == "user"
               and '"status": "passed"' in message.content]
    assert len(results) == 2, [message.content for message in task.messages]
    assert any("\ntool: run_typecheck\n" in result for result in results)
    assert any("\ntool: run_build\n" in result for result in results)


def test_portfolio_build_and_edit_through_real_backend(tmp_path):
    actions = [
        _tool("list_files"),
        _tool("read_file", path="package.json"),
        _tool("write_file", path="index.html", content=INDEX),
        _tool("write_file", path="src/main.tsx", content=MAIN),
        _tool("write_file", path="src/style.css", content=LIGHT),
        _tool("run_typecheck"),
        _tool("run_build"),
        _action("complete", summary="Portfolio built and validated."),
        _tool("read_file", path="src/style.css"),
        _tool("write_file", path="src/style.css", content=DARK),
        _tool("run_typecheck"),
        _tool("run_build"),
        _action("complete", summary="Hero reduced and dark mode added."),
    ]
    seen: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["authorization"] == f"Bearer {REQUEST_KEY}"
        assert REQUEST_KEY not in request.content.decode("utf-8")
        assert SERVER_KEY not in str(request.headers)
        assert actions, "agent made an unexpected provider request"
        return httpx.Response(200, json={
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps(actions.pop(0))},
                         "finish_reason": "stop"}],
        })

    port = free_port()
    preview_config = PreviewConfig(public_port=port, listen_port=port,
                                   ready_timeout_seconds=90)
    config = RedstoneConfig(
        workspaces_root=tmp_path / "workspaces", preview=preview_config,
        limits=Limits(max_agent_iterations=12),
        ai=AIConfig(api_key=SERVER_KEY, max_retries=0),
    )
    provider = DockerSandboxProvider()
    runtimes = RuntimeManager(provider, max_startup_seconds=240)
    previews = PreviewManager(runtimes, preview_config)
    gateway = AIGateway(config.ai, transport=httpx.MockTransport(upstream))
    service = AgentService(config, gateway=gateway,
                           validation_runner=SandboxValidationRunner(provider),
                           runtime_manager=runtimes)
    app = create_app(service=service, config=config, runtime_manager=runtimes,
                     preview_manager=previews)
    project_id = None

    try:
        with TestClient(app) as client:
            created = client.post("/api/projects", json={
                "name": "Portfolio", "framework": Framework.REACT_VITE_TS.value,
            })
            assert created.status_code == 200, created.text
            project_id = created.json()["project_id"]
            workspace = service.get_workspace(project_id)
            (workspace.project_root / "package.json").write_text(
                json.dumps(PACKAGE), encoding="utf-8")
            (workspace.project_root / "tsconfig.json").write_text(
                json.dumps(TSCONFIG), encoding="utf-8")
            assert not (workspace.project_root / "node_modules").exists()

            byok = {"provider": "openai-compatible", "model": "test-model",
                    "api_key": REQUEST_KEY}
            first = client.post(f"/api/projects/{project_id}/agent", json={
                "message": "Build me a portfolio website.", "byok": byok,
            })
            assert first.status_code == 200, first.text
            assert first.json()["status"] == "completed", first.text
            _assert_validated(service, first.json()["task_id"])
            assert (workspace.project_root / "dist" / "index.html").exists()

            with LiveServer(create_preview_gateway_app(previews, preview_config), port=port):
                started = client.post(f"/api/projects/{project_id}/preview")
                assert started.status_code == 200, started.text
                preview = started.json()
                assert preview["status"] == "ready"
                with playwright_api.sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel="chrome", headless=True)
                    try:
                        page = browser.new_page()
                        page.goto(preview["url"])
                        assert page.locator("h1").inner_text() == "Redstone portfolio"
                        original_height = page.locator(".hero").bounding_box()["height"]

                        second = client.post(f"/api/projects/{project_id}/agent", json={
                            "message": "Make the hero section smaller and add dark mode.",
                            "byok": byok,
                        })
                        assert second.status_code == 200, second.text
                        assert second.json()["status"] == "completed", second.text
                        _assert_validated(service, second.json()["task_id"])
                        assert (workspace.project_root / "src" / "style.css").read_text(encoding="utf-8") == DARK
                        deadline = time.monotonic() + 20
                        while time.monotonic() < deadline:
                            page.reload()
                            if page.locator(".hero").bounding_box()["height"] < original_height:
                                break
                            time.sleep(0.5)
                        assert page.locator(".hero").bounding_box()["height"] < original_height
                        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(17, 24, 39)"
                        assert REQUEST_KEY not in page.content()

                        runtime = runtimes.get(previews.get_for_project(project_id).runtime_id,
                                               project_id)
                        for name in (runtime.sandbox_id, f"{runtime.sandbox_id}-relay"):
                            inspected = docker("inspect", name)
                            assert inspected.returncode == 0
                            assert REQUEST_KEY not in inspected.stdout
                    finally:
                        browser.close()

            for task_id in (first.json()["task_id"], second.json()["task_id"]):
                assert REQUEST_KEY not in client.get(f"/api/agent/tasks/{task_id}").text
                assert REQUEST_KEY not in client.get(f"/api/agent/tasks/{task_id}/events").text
            for path in (workspace.root / ".redstone").rglob("*"):
                if path.is_file():
                    assert REQUEST_KEY not in path.read_text(encoding="utf-8", errors="ignore")
            assert len(seen) == 13 and not actions
            assert client.delete(f"/api/projects/{project_id}/preview").json() == {"destroyed": True}
    finally:
        if project_id is not None:
            previews.destroy(project_id)
