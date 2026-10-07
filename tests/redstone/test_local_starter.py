"""A fresh API-created React project can run without hand-written setup files."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from preview_support import LiveServer, free_port, managed, preview_host, raw_request
from redstone.agent.service import AgentService
from redstone.api.app import create_app
from redstone.config import PreviewConfig, RedstoneConfig
from redstone.domain.validation import ValidationStatus
from redstone.preview.gateway import create_preview_gateway_app
from redstone.preview.manager import PreviewManager
from redstone.runtime.manager import RuntimeManager
from redstone.runtime.validation import SandboxValidationRunner
from redstone.sandbox.providers.docker_provider import DockerSandboxProvider, docker_available

pytestmark = pytest.mark.skipif(not docker_available(), reason="Docker daemon not reachable")


def test_fresh_api_react_project_previews_and_builds(tmp_path):
    port = free_port()
    config = RedstoneConfig(
        workspaces_root=tmp_path / "workspaces",
        preview=PreviewConfig(public_port=port, listen_port=port, ready_timeout_seconds=90),
    )
    provider = DockerSandboxProvider()
    runtimes = RuntimeManager(provider, max_startup_seconds=240)
    previews = PreviewManager(runtimes, config.preview)
    service = AgentService(config)
    app = create_app(service=service, config=config, runtime_manager=runtimes,
                     preview_manager=previews)
    before_containers, before_networks = managed()
    project_id = None

    try:
        with TestClient(app) as client, LiveServer(
            create_preview_gateway_app(previews, config.preview), port=port
        ):
            created = client.post("/api/projects", json={
                "name": "Local trial", "framework": "react-vite-ts",
            })
            assert created.status_code == 200, created.text
            project_id = created.json()["project_id"]
            assert created.json()["framework"] == "react-vite-ts"
            root = service.get_workspace(project_id).project_root
            assert not (root / "node_modules").exists()

            response = client.post(f"/api/projects/{project_id}/preview")
            assert response.status_code == 200, response.text
            preview = response.json()
            assert preview["status"] == "ready"
            host = preview_host(preview["preview_id"], port)
            status, _, html = raw_request(port, host, "/")
            assert status == 200 and b"Redstone project" in html
            status, _, app_source = raw_request(port, host, "/src/main.tsx")
            assert status == 200 and b"Ready to build" in app_source

            validator = SandboxValidationRunner(provider)
            assert validator.run_typecheck(root).status is ValidationStatus.PASSED
            assert validator.run_build(root).status is ValidationStatus.PASSED
            assert (root / "dist" / "index.html").exists()
            assert client.delete(f"/api/projects/{project_id}/preview").json() == {
                "destroyed": True,
            }
    finally:
        if project_id is not None:
            previews.destroy(project_id)

    after_containers, after_networks = managed()
    assert not after_containers - before_containers
    assert not after_networks - before_networks


def test_missing_native_optional_package_gets_one_restricted_reinstall(tmp_path, monkeypatch):
    config = RedstoneConfig(
        workspaces_root=tmp_path / "workspaces",
        preview=PreviewConfig(ready_timeout_seconds=90),
    )
    provider = DockerSandboxProvider()
    runtimes = RuntimeManager(provider, max_startup_seconds=240)
    previews = PreviewManager(runtimes, config.preview)
    service = AgentService(config)
    app = create_app(service=service, config=config, runtime_manager=runtimes,
                     preview_manager=previews)
    before_containers, before_networks = managed()
    project_id = None
    root = None
    install_count = 0
    original_wait = provider.wait

    def wait_and_remove_native_package(sandbox_id, timeout):
        nonlocal install_count
        result = original_wait(sandbox_id, timeout)
        install_count += 1
        if install_count == 1 and result.ok:
            assert root is not None
            native_packages = list((root / "node_modules" / "@rollup").glob(
                "rollup-linux-*-musl"
            ))
            if native_packages:
                shutil.rmtree(native_packages[0])
        return result

    monkeypatch.setattr(provider, "wait", wait_and_remove_native_package)
    try:
        with TestClient(app) as client:
            project_id = client.post("/api/projects", json={
                "name": "Native dependency recovery", "framework": "react-vite-ts",
            }).json()["project_id"]
            root = service.get_workspace(project_id).project_root
            response = client.post(f"/api/projects/{project_id}/preview")
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "ready"
            assert install_count == 2
            assert list((root / "node_modules" / "@rollup").glob("rollup-linux-*-musl"))
    finally:
        if project_id is not None:
            previews.destroy(project_id)

    after_containers, after_networks = managed()
    assert after_containers == before_containers
    assert after_networks == before_networks
