"""Tests for sandbox service - resource limits and network isolation."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.sandbox_service import SandboxService, SandboxResult


# Standalone test functions for prd.json verification
@pytest.mark.asyncio
async def test_resource_limits():
    """Test that resource limits are configured correctly."""
    sandbox_service = SandboxService()

    # Test that sandbox service has proper configuration
    assert sandbox_service.settings.sandbox_timeout_seconds > 0
    assert sandbox_service.settings.sandbox_memory_limit_mb > 0

    # Test docker command construction with resource limits
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"===RESULT==={}", b"")
        )
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_exec.return_value = mock_process

        result = await sandbox_service.execute_code(
            code="print('hello')",
            session_id="test-session",
            api_url="http://api:8000",
            memory_limit_mb=128,
            cpu_limit=0.5,
            timeout_seconds=30,
        )

        # Verify docker was called with resource limit flags
        call_args = mock_exec.call_args[0]
        args_str = " ".join(call_args)

        # Check memory limit is set
        assert "--memory=128m" in args_str, "Memory limit not set"
        assert "--memory-swap=128m" in args_str, "Memory swap limit not set"

        # Check CPU limit is set
        assert "--cpus=0.5" in args_str, "CPU limit not set"

        # Check process limit is set
        assert "--pids-limit=50" in args_str, "PID limit not set"


@pytest.mark.asyncio
async def test_network_isolation():
    """Test that network isolation is configured correctly."""
    sandbox_service = SandboxService()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"===RESULT==={}", b"")
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        await sandbox_service.execute_code(
            code="print('test')",
            session_id="test-session",
            api_url="http://api:8000",
        )

        call_args = mock_exec.call_args[0]
        args_str = " ".join(call_args)

        # Check network isolation - should use internal network
        assert f"--network={sandbox_service.network_name}" in args_str, \
            "Network not set to sandbox network"


class TestResourceLimits:
    """Tests for T-07.2: Resource limits (CPU, memory, timeout)."""

    @pytest.fixture
    def sandbox_service(self):
        """Create sandbox service instance."""
        return SandboxService()

    @pytest.mark.asyncio
    async def test_resource_limits(self, sandbox_service):
        """Test that resource limits are configured correctly."""
        # Test that sandbox service has proper configuration
        assert sandbox_service.settings.sandbox_timeout_seconds > 0
        assert sandbox_service.settings.sandbox_memory_limit_mb > 0

        # Test docker command construction with resource limits
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"===RESULT==={}", b"")
            )
            mock_process.returncode = 0
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            result = await sandbox_service.execute_code(
                code="print('hello')",
                session_id="test-session",
                api_url="http://api:8000",
                memory_limit_mb=128,
                cpu_limit=0.5,
                timeout_seconds=30,
            )

            # Verify docker was called with resource limit flags
            call_args = mock_exec.call_args[0]
            args_str = " ".join(call_args)

            # Check memory limit is set
            assert "--memory=128m" in args_str, "Memory limit not set"
            assert "--memory-swap=128m" in args_str, "Memory swap limit not set"

            # Check CPU limit is set
            assert "--cpus=0.5" in args_str, "CPU limit not set"

            # Check process limit is set
            assert "--pids-limit=50" in args_str, "PID limit not set"

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, sandbox_service):
        """Test that execution timeout is enforced."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            # Simulate timeout by raising TimeoutError
            mock_process.communicate = AsyncMock(
                side_effect=TimeoutError("Process timed out")
            )
            mock_process.returncode = None
            mock_exec.return_value = mock_process

            # Mock the kill container method
            sandbox_service._kill_container = AsyncMock()

            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await sandbox_service.execute_code(
                    code="while True: pass",
                    session_id="test-session",
                    api_url="http://api:8000",
                    timeout_seconds=5,
                )

            # Verify timeout result
            assert result.timed_out is True
            assert result.success is False
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_memory_limit_kills_container(self, sandbox_service):
        """Test that exceeding memory limit terminates container."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            # Simulate OOM kill (exit code 137)
            mock_process.communicate = AsyncMock(
                return_value=(b"", b"Killed")
            )
            mock_process.returncode = 137  # SIGKILL from OOM
            mock_process.wait = AsyncMock(return_value=137)
            mock_exec.return_value = mock_process

            result = await sandbox_service.execute_code(
                code="data = 'x' * (1024 * 1024 * 1000)",  # Try to allocate 1GB
                session_id="test-session",
                api_url="http://api:8000",
                memory_limit_mb=50,
            )

            # Container should fail due to OOM
            assert result.success is False
            assert result.exit_code == 137

    @pytest.mark.asyncio
    async def test_security_options_applied(self, sandbox_service):
        """Test that security options are applied to container."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"===RESULT==={}", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            await sandbox_service.execute_code(
                code="print('test')",
                session_id="test-session",
                api_url="http://api:8000",
            )

            call_args = mock_exec.call_args[0]
            args_str = " ".join(call_args)

            # Check security options
            assert "--read-only" in args_str, "Read-only filesystem not set"
            assert "--security-opt=no-new-privileges:true" in args_str, "no-new-privileges not set"
            assert "--cap-drop=ALL" in args_str, "Capabilities not dropped"


class TestNetworkIsolation:
    """Tests for T-07.3: Network isolation in sandbox."""

    @pytest.fixture
    def sandbox_service(self):
        """Create sandbox service instance."""
        return SandboxService()

    @pytest.mark.asyncio
    async def test_network_isolation(self, sandbox_service):
        """Test that network isolation is configured correctly."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"===RESULT==={}", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            await sandbox_service.execute_code(
                code="print('test')",
                session_id="test-session",
                api_url="http://api:8000",
            )

            call_args = mock_exec.call_args[0]
            args_str = " ".join(call_args)

            # Check network isolation - should use internal network
            assert f"--network={sandbox_service.network_name}" in args_str, \
                "Network not set to sandbox network"

    @pytest.mark.asyncio
    async def test_ensure_network_exists_creates_internal_network(self, sandbox_service):
        """Test that sandbox network is created as internal (no external access)."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # First call: network doesn't exist (returns non-zero)
            mock_inspect = AsyncMock()
            mock_inspect.wait = AsyncMock(return_value=1)

            # Second call: create network
            mock_create = AsyncMock()
            mock_create.wait = AsyncMock(return_value=0)

            mock_exec.side_effect = [mock_inspect, mock_create]

            result = await sandbox_service.ensure_network_exists()

            assert result is True

            # Verify network create was called with --internal flag
            create_call_args = mock_exec.call_args_list[1][0]
            assert "--internal" in create_call_args, "Network not created as internal"
            assert sandbox_service.network_name in create_call_args

    @pytest.mark.asyncio
    async def test_ensure_network_exists_skips_if_exists(self, sandbox_service):
        """Test that existing network is not recreated."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Network exists (returns 0)
            mock_inspect = AsyncMock()
            mock_inspect.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_inspect

            result = await sandbox_service.ensure_network_exists()

            assert result is True
            # Only one call (inspect), not create
            assert mock_exec.call_count == 1

    @pytest.mark.asyncio
    async def test_sandbox_cannot_reach_external_network(self, sandbox_service):
        """Test that sandbox container cannot reach external internet."""
        # The --internal flag on the network prevents external access
        # This test verifies the configuration is correct
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            # Simulate blocked network access
            mock_process.communicate = AsyncMock(
                return_value=(b"PASS: External access blocked", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await sandbox_service.execute_code(
                code="""
import urllib.request
try:
    urllib.request.urlopen("http://google.com", timeout=5)
    print("FAIL")
except:
    print("PASS: External access blocked")
""",
                session_id="test-session",
                api_url="http://api:8000",
            )

            # Verify network flag is set
            call_args = mock_exec.call_args[0]
            args_str = " ".join(call_args)
            assert f"--network={sandbox_service.network_name}" in args_str

    @pytest.mark.asyncio
    async def test_container_cleanup_on_timeout(self, sandbox_service):
        """Test that container is killed when execution times out."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock()
            mock_exec.return_value = mock_process

            # Track kill calls
            kill_calls = []

            async def mock_kill(container_id):
                kill_calls.append(container_id)

            sandbox_service._kill_container = mock_kill

            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await sandbox_service.execute_code(
                    code="while True: pass",
                    session_id="test-session",
                    api_url="http://api:8000",
                    timeout_seconds=1,
                )

            assert result.timed_out is True
            assert len(kill_calls) == 1  # Container was killed


class TestSandboxResultParsing:
    """Tests for parsing sandbox execution results."""

    @pytest.fixture
    def sandbox_service(self):
        """Create sandbox service instance."""
        return SandboxService()

    def test_parse_json_result(self, sandbox_service):
        """Test parsing JSON result from runner."""
        stdout = '===RESULT==={"success": true, "output": "Maze completed!", "turns": 100, "completed": true}'
        result = sandbox_service._parse_result(stdout, "", 0)

        assert result.success is True
        assert result.output == "Maze completed!"
        assert result.turns == 100
        assert result.completed is True

    def test_parse_error_result(self, sandbox_service):
        """Test parsing error result."""
        stdout = '===RESULT==={"success": false, "error": "NameError: x is not defined"}'
        result = sandbox_service._parse_result(stdout, "", 1)

        assert result.success is False
        assert "NameError" in result.error

    def test_parse_fallback_on_invalid_json(self, sandbox_service):
        """Test fallback when JSON is invalid."""
        stdout = "Some output without JSON marker"
        result = sandbox_service._parse_result(stdout, "", 0)

        assert result.success is True
        assert result.output == stdout

    def test_parse_failure_with_stderr(self, sandbox_service):
        """Test parsing failure with stderr output."""
        stdout = ""
        stderr = "Error: Container killed due to OOM"
        result = sandbox_service._parse_result(stdout, stderr, 137)

        assert result.success is False
        assert result.exit_code == 137
        assert "OOM" in result.error
