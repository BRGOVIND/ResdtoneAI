"""Milestone 2 dependency readiness without pretending that a fake is Docker."""

from __future__ import annotations

import asyncio
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from agent_fakes import FailingAIGateway, FakeAIGateway, FakeValidationRunner, action
from redstone.agent.models import AgentStatus
from redstone.agent.service import AgentService
from redstone.api.app import create_app
from redstone.config import AIConfig, Limits, RedstoneConfig
from redstone.ai.errors import AIErrorCode
from redstone.domain.models import Framework
from redstone.runtime.errors import RedstoneRuntimeError, RuntimeErrorCode
from redstone.runtime.manager import RuntimeManager
from redstone.runtime.validation import SandboxValidationRunner
from redstone.sandbox.models import NetworkPolicy
from redstone.sandbox.errors import RedstoneSandboxError, SandboxErrorCode
from redstone.sandbox.providers.docker_provider import DockerSandboxProvider, docker_available
from runtime_fakes import FakeSandboxProvider


def _service(tmp_path, provider, gateway=None, validation_runner=None):
    config = RedstoneConfig(
        workspaces_root=tmp_path / "workspaces",
        limits=Limits(max_agent_iterations=10), ai=AIConfig(),
    )
    manager = RuntimeManager(provider)
    service = AgentService(
        config, gateway=gateway or FakeAIGateway(),
        validation_runner=validation_runner, runtime_manager=manager,
    )
    project = service.create_project("Portfolio", Framework.REACT_VITE_TS)
    return service, manager, project


def test_prepare_uses_existing_isolated_install_path_and_is_idempotent(tmp_path):
    provider = FakeSandboxProvider()
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)

    manager.prepare_dependencies(project.id, workspace, project.framework)
    assert len(provider.configs) == 1
    config = next(iter(provider.configs.values()))
    assert config.network_policy is NetworkPolicy.INSTALL_ONLY
    assert config.command.resolve() == ("npm", "install", "--no-audit", "--no-fund")
    assert config.environment == {"NODE_ENV": "development", "PORT": "5173"}
    assert provider.live_sandbox_ids() == set()
    assert manager.list_for_project(project.id) == ()

    (workspace.project_root / "node_modules").mkdir()
    manager.prepare_dependencies(project.id, workspace, project.framework)
    assert len(provider.configs) == 1

    (workspace.project_root / "package.json").write_text(
        '{"name":"changed","version":"1.0.0"}', encoding="utf-8"
    )
    manager.prepare_dependencies(project.id, workspace, project.framework)
    assert len(provider.configs) == 2


def test_preparation_holds_preview_runtime_admission_slot(tmp_path):
    provider = FakeSandboxProvider(start_delay=0.4)
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)
    thread = threading.Thread(target=manager.prepare_dependencies,
                              args=(project.id, workspace, project.framework))
    thread.start()
    deadline = time.monotonic() + 5
    while not provider.create_calls and time.monotonic() < deadline:
        time.sleep(0.01)
    assert provider.create_calls
    assert manager.reconcile() == 0  # a bounded install is not a crashed dev server
    with pytest.raises(RedstoneRuntimeError) as error:
        manager.create(project.id, workspace, project.framework)
    assert error.value.code is RuntimeErrorCode.BUSY
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert provider.live_sandbox_ids() == set()


def test_failed_install_cleans_up_and_next_attempt_can_retry(tmp_path):
    provider = FakeSandboxProvider(install_ok=False)
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)
    with pytest.raises(RedstoneRuntimeError) as error:
        manager.prepare_dependencies(project.id, workspace, project.framework)
    assert error.value.code is RuntimeErrorCode.START_FAILED
    assert provider.live_sandbox_ids() == set()
    provider.install_ok = True
    manager.prepare_dependencies(project.id, workspace, project.framework)
    assert len(provider.configs) == 2


def test_sandbox_creation_failure_is_reported_not_hidden_as_agent_internal(tmp_path):
    provider = FakeSandboxProvider(create_error=RedstoneSandboxError(SandboxErrorCode.CREATE_FAILED))
    service, manager, project = _service(tmp_path, provider)
    task = service.start_task(project.id, "Build a portfolio")
    assert task.status is AgentStatus.FAILED
    assert task.error["error_code"] == RuntimeErrorCode.CREATE_FAILED.value
    assert manager.list_for_project(project.id) == ()
    provider.create_error = None
    manager.prepare_dependencies(project.id, service.get_workspace(project.id), project.framework)


def test_preview_start_reuses_prepared_dependencies_without_competing_install(tmp_path):
    provider = FakeSandboxProvider()
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)
    manager.prepare_dependencies(project.id, workspace, project.framework)
    (workspace.project_root / "node_modules").mkdir()
    runtime = manager.create(project.id, workspace, project.framework)
    try:
        manager.start(runtime.id, project.id, workspace)
        assert len(provider.wait_calls) == 1
    finally:
        manager.destroy(runtime.id, project.id)


def test_cleanup_failure_keeps_workspace_busy_until_explicit_retry(tmp_path):
    class FailCleanupTwice(FakeSandboxProvider):
        remaining = 2

        def destroy(self, sandbox_id):
            if self.remaining:
                self.remaining -= 1
                raise RedstoneSandboxError(SandboxErrorCode.DESTROY_FAILED)
            super().destroy(sandbox_id)

    provider = FailCleanupTwice()
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)
    with pytest.raises(RedstoneRuntimeError) as error:
        manager.prepare_dependencies(project.id, workspace, project.framework)
    assert error.value.code is RuntimeErrorCode.DESTROY_FAILED
    stranded = manager.list_for_project(project.id)
    assert len(stranded) == 1
    with pytest.raises(RedstoneRuntimeError) as busy:
        manager.create(project.id, workspace, project.framework)
    assert busy.value.code is RuntimeErrorCode.BUSY
    manager.destroy(stranded[0].id, project.id)
    assert provider.live_sandbox_ids() == set()
    assert manager.dependency_status(workspace, project.framework)["status"] == "failed"


class _CancellableInstall(FakeSandboxProvider):
    def __init__(self):
        super().__init__()
        self.wait_started = threading.Event()
        self.killed = threading.Event()

    def wait(self, sandbox_id, timeout):
        self.wait_started.set()
        assert self.killed.wait(5), "install was not cancelled"
        return super().wait(sandbox_id, timeout)

    def kill(self, sandbox_id):
        super().kill(sandbox_id)
        self.killed.set()


def test_cancel_during_preparation_kills_install_and_releases_lease(tmp_path):
    provider = _CancellableInstall()
    service, manager, project = _service(tmp_path, provider)
    task = service.start_task(project.id, "Build a portfolio", background=True)
    assert provider.wait_started.wait(5)
    assert service.get_task(task.id).status is AgentStatus.PREPARING
    service.cancel_task(task.id)
    deadline = time.monotonic() + 5
    while not service.get_task(task.id).is_terminal and time.monotonic() < deadline:
        time.sleep(0.02)
    assert service.get_task(task.id).status is AgentStatus.CANCELLED
    assert provider.live_sandbox_ids() == set()
    assert manager.list_for_project(project.id) == ()


def test_cancel_remains_cancelled_if_wait_reports_a_sandbox_error(tmp_path):
    class FailingWaitAfterKill(_CancellableInstall):
        def wait(self, sandbox_id, timeout):
            self.wait_started.set()
            assert self.killed.wait(5)
            raise RedstoneSandboxError(SandboxErrorCode.EXEC_FAILED)

    provider = FailingWaitAfterKill()
    service, _, project = _service(tmp_path, provider)
    task = service.start_task(project.id, "Build a portfolio", background=True)
    assert provider.wait_started.wait(5)
    service.cancel_task(task.id)
    deadline = time.monotonic() + 5
    while not service.get_task(task.id).is_terminal and time.monotonic() < deadline:
        time.sleep(0.02)
    assert service.get_task(task.id).status is AgentStatus.CANCELLED
    assert provider.live_sandbox_ids() == set()


def test_dependency_status_api_reports_in_progress_and_retryable_state(tmp_path):
    provider = _CancellableInstall()
    service, manager, project = _service(tmp_path, provider)
    app = create_app(service=service, config=service._config, runtime_manager=manager)
    path = f"/api/projects/{project.id}/dependencies"
    with TestClient(app) as client:
        assert client.get(path).json() == {"status": "needed"}
        task = service.start_task(project.id, "Build a portfolio", background=True)
        assert provider.wait_started.wait(5)
        assert client.get(path).json() == {"status": "preparing"}
        service.cancel_task(task.id)
        deadline = time.monotonic() + 5
        while not service.get_task(task.id).is_terminal and time.monotonic() < deadline:
            time.sleep(0.02)
        assert client.get(path).json() == {"status": "needed"}
        provider.available = False
        assert client.get(path).json() == {"status": "unavailable"}


def test_http_status_stays_responsive_while_agent_post_prepares(tmp_path):
    provider = _CancellableInstall()
    service, manager, project = _service(tmp_path, provider)
    app = create_app(service=service, config=service._config, runtime_manager=manager)

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            post = asyncio.create_task(client.post(
                f"/api/projects/{project.id}/agent", json={"message": "Build a portfolio"}
            ))
            assert await asyncio.to_thread(provider.wait_started.wait, 5)
            status = await asyncio.wait_for(
                client.get(f"/api/projects/{project.id}/dependencies"), timeout=2,
            )
            assert status.json() == {"status": "preparing"}
            service.cancel_task(next(iter(service._tasks)))
            response = await asyncio.wait_for(post, timeout=5)
            assert response.json()["status"] == "cancelled"

    asyncio.run(exercise())


def test_agent_failure_when_installer_unavailable_is_retryable(tmp_path):
    provider = FakeSandboxProvider()
    provider.available = False
    service, manager, project = _service(tmp_path, provider)
    failed = service.start_task(project.id, "Build a portfolio")
    assert failed.status is AgentStatus.FAILED
    assert failed.error["error_code"] == RuntimeErrorCode.CREATE_FAILED.value
    assert not provider.create_calls
    provider.available = True
    retried = service.start_task(project.id, "Build a portfolio")
    assert retried.id != failed.id
    assert retried.error["error_code"] == "AGENT_VALIDATION_REQUIRED"


def test_dependency_status_api_reports_failed_install(tmp_path):
    provider = FakeSandboxProvider(install_ok=False)
    service, manager, project = _service(tmp_path, provider)
    app = create_app(service=service, config=service._config, runtime_manager=manager)
    with TestClient(app) as client:
        task = service.start_task(project.id, "Build a portfolio")
        assert task.status is AgentStatus.FAILED
        assert client.get(f"/api/projects/{project.id}/dependencies").json() == {
            "status": "failed", "error_code": RuntimeErrorCode.START_FAILED.value,
        }


def test_react_completion_requires_real_validation_results_after_last_edit(tmp_path):
    provider = FakeSandboxProvider()
    gateway = FakeAIGateway([
        action("tool_call", tool="write_file", arguments={"path": "src/main.tsx", "content": "export {};"}),
        action("tool_call", tool="run_typecheck", arguments={}),
        action("complete", summary="done"),
    ])
    service, _, project = _service(tmp_path, provider, gateway, FakeValidationRunner())
    task = service.start_task(project.id, "Build a portfolio")
    assert task.status is AgentStatus.FAILED
    assert task.error["error_code"] == "AGENT_VALIDATION_REQUIRED"
    assert task.changeset_id is None


def test_failed_validation_cannot_be_reported_as_completed(tmp_path):
    provider = FakeSandboxProvider()
    gateway = FakeAIGateway([
        action("tool_call", tool="run_typecheck", arguments={}),
        action("tool_call", tool="run_build", arguments={}),
        action("complete", summary="all good"),
    ])
    service, _, project = _service(
        tmp_path, provider, gateway, FakeValidationRunner(build_ok=False)
    )
    task = service.start_task(project.id, "Build a portfolio")
    assert task.status is AgentStatus.FAILED
    assert task.error["error_code"] == "AGENT_VALIDATION_REQUIRED"
    assert task.changeset_id is None


def test_provider_failure_after_preparation_is_safe_and_retryable(tmp_path):
    provider = FakeSandboxProvider()
    service, _, project = _service(
        tmp_path, provider, FailingAIGateway(AIErrorCode.PROVIDER_UNAVAILABLE)
    )
    first = service.start_task(project.id, "Build a portfolio")
    second = service.start_task(project.id, "Try again")
    assert first.status is second.status is AgentStatus.FAILED
    assert first.error["error_code"] == second.error["error_code"]
    assert provider.live_sandbox_ids() == set()


def test_malformed_model_response_exhausts_bound_without_false_success(tmp_path):
    provider = FakeSandboxProvider()
    service, _, project = _service(
        tmp_path, provider, FakeAIGateway(default="not JSON")
    )
    task = service.start_task(project.id, "Build a portfolio")
    assert task.status is AgentStatus.TIMED_OUT
    assert task.changeset_id is None
    assert provider.live_sandbox_ids() == set()


def test_no_server_key_fails_before_install_and_preserves_retry(tmp_path):
    from redstone.ai.gateway import AIGateway

    provider = FakeSandboxProvider()
    service, _, project = _service(tmp_path, provider, gateway=AIGateway(AIConfig()))
    task = service.start_task(project.id, "Build a portfolio")
    assert task.status is AgentStatus.FAILED
    assert task.error["error_code"] == "AI_NOT_CONFIGURED"
    assert not provider.create_calls


@pytest.mark.skipif(not docker_available(), reason="Docker daemon not reachable")
def test_fresh_starter_preparation_and_validation_use_real_docker(tmp_path):
    provider = DockerSandboxProvider()
    service, manager, project = _service(tmp_path, provider)
    workspace = service.get_workspace(project.id)
    assert not (workspace.project_root / "node_modules").exists()

    try:
        # No host npm: first install must fail in a no-network sandbox, and
        # its container must be removed before the retry.
        npmrc = workspace.project_root / ".npmrc"
        npmrc.write_text("fetch-retries=0\nfetch-timeout=5000\n", encoding="utf-8")
        manager._install_network_enabled = False
        with pytest.raises(RedstoneRuntimeError):
            manager.prepare_dependencies(project.id, workspace, project.framework)
        assert manager.list_for_project(project.id) == ()
        assert not provider.list_managed()

        npmrc.unlink()
        manager._install_network_enabled = True
        manager.prepare_dependencies(project.id, workspace, project.framework)
        assert (workspace.project_root / "node_modules").is_dir()
        validator = SandboxValidationRunner(provider)
        assert validator.run_typecheck(workspace.project_root).status == "passed"
        assert validator.run_build(workspace.project_root).status == "passed"
        package = workspace.project_root / "package.json"
        original = package.read_text(encoding="utf-8")
        package.write_text('{"name":"no-build","version":"1.0.0"}', encoding="utf-8")
        assert validator.run_build(workspace.project_root).status == "failed"
        package.write_text(original, encoding="utf-8")
        assert not provider.list_managed()
    finally:
        manager.reconcile_orphaned_containers()
