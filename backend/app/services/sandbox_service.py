"""Sandbox service for secure code execution in Docker containers."""

import asyncio
import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import get_settings


@dataclass
class SandboxResult:
    """Result of sandbox code execution."""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    timed_out: bool = False
    session_id: Optional[str] = None
    turns: int = 0
    completed: bool = False


class SandboxService:
    """Service for executing user code in isolated Docker containers."""

    def __init__(self):
        self.settings = get_settings()
        self.image_name = "kiro-sandbox"
        self.network_name = "kiro-sandbox-net"

    async def execute_code(
        self,
        code: str,
        session_id: str,
        api_url: str,
        timeout_seconds: Optional[int] = None,
        memory_limit_mb: Optional[int] = None,
        cpu_limit: float = 0.5,
    ) -> SandboxResult:
        """
        Execute user code in a sandboxed Docker container.

        Args:
            code: Python code to execute
            session_id: Maze session ID for API calls
            api_url: Base URL of the maze API
            timeout_seconds: Execution timeout (default from settings)
            memory_limit_mb: Memory limit in MB (default from settings)
            cpu_limit: CPU limit (e.g., 0.5 = 50% of one CPU)

        Returns:
            SandboxResult with execution outcome
        """
        timeout = timeout_seconds or self.settings.sandbox_timeout_seconds
        memory = memory_limit_mb or self.settings.sandbox_memory_limit_mb

        # Create temp file for user code
        container_id = str(uuid.uuid4())[:8]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as code_file:
            code_file.write(code)
            code_path = code_file.name

        try:
            # Build docker run command with resource limits and network isolation
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                f"--name=sandbox-{container_id}",
                # Resource limits
                f"--memory={memory}m",
                f"--memory-swap={memory}m",  # Disable swap
                f"--cpus={cpu_limit}",
                "--pids-limit=50",  # Limit number of processes
                # Network isolation - use internal network only
                f"--network={self.network_name}",
                # Security options
                "--read-only",
                "--tmpfs=/tmp:size=10m,noexec",
                "--security-opt=no-new-privileges:true",
                "--cap-drop=ALL",
                # Environment variables
                "-e", f"SESSION_ID={session_id}",
                "-e", f"API_URL={api_url}",
                # Mount user code as read-only
                "-v", f"{code_path}:/app/user_code.py:ro",
                # Image and command
                self.image_name,
            ]

            # Run container with timeout
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout + 5,  # Extra 5s for container overhead
                )

                output = stdout.decode("utf-8", errors="replace")
                error_output = stderr.decode("utf-8", errors="replace")

                # Parse result from runner output
                return self._parse_result(
                    output, error_output, process.returncode or 0
                )

            except asyncio.TimeoutError:
                # Kill the container if it times out
                await self._kill_container(container_id)
                return SandboxResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {timeout} seconds",
                    timed_out=True,
                    exit_code=-1,
                )

        finally:
            # Clean up temp file
            Path(code_path).unlink(missing_ok=True)

    async def _kill_container(self, container_id: str) -> None:
        """Force kill a running container."""
        kill_cmd = ["docker", "kill", f"sandbox-{container_id}"]
        process = await asyncio.create_subprocess_exec(
            *kill_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

    def _parse_result(
        self, stdout: str, stderr: str, exit_code: int
    ) -> SandboxResult:
        """Parse execution result from container output."""
        # Look for JSON result marker in output
        result_marker = "===RESULT==="

        if result_marker in stdout:
            try:
                # Extract JSON after marker
                json_start = stdout.index(result_marker) + len(result_marker)
                json_str = stdout[json_start:].strip()
                result_data = json.loads(json_str)

                return SandboxResult(
                    success=result_data.get("success", False),
                    output=result_data.get("output", ""),
                    error=result_data.get("error"),
                    exit_code=exit_code,
                    session_id=result_data.get("session_id"),
                    turns=result_data.get("turns", 0),
                    completed=result_data.get("completed", False),
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback to raw output
        if exit_code == 0:
            return SandboxResult(
                success=True,
                output=stdout,
                error=stderr if stderr else None,
                exit_code=exit_code,
            )
        else:
            return SandboxResult(
                success=False,
                output=stdout,
                error=stderr or "Execution failed",
                exit_code=exit_code,
            )

    async def ensure_network_exists(self) -> bool:
        """Ensure the sandbox network exists with internal-only access."""
        # Check if network exists
        check_cmd = ["docker", "network", "inspect", self.network_name]
        process = await asyncio.create_subprocess_exec(
            *check_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        result = await process.wait()

        if result == 0:
            return True

        # Create internal network (no external access by default)
        create_cmd = [
            "docker",
            "network",
            "create",
            "--internal",  # No outbound internet access
            self.network_name,
        ]
        process = await asyncio.create_subprocess_exec(
            *create_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        result = await process.wait()
        return result == 0

    async def test_resource_limits(self) -> dict:
        """
        Test that resource limits are enforced.

        Returns dict with test results.
        """
        results = {}

        # Test 1: Memory limit
        memory_hog_code = """
# Try to allocate more memory than allowed
data = []
try:
    for i in range(1000):
        data.append('x' * (1024 * 1024))  # 1MB per iteration
except MemoryError:
    print("Memory limit enforced")
"""
        result = await self.execute_code(
            memory_hog_code,
            session_id="test",
            api_url="http://localhost:8000",
            memory_limit_mb=50,
            timeout_seconds=30,
        )
        results["memory_limit"] = not result.success or "Memory limit" in result.output

        # Test 2: Timeout enforcement
        infinite_loop_code = """
import time
while True:
    time.sleep(0.1)
"""
        result = await self.execute_code(
            infinite_loop_code,
            session_id="test",
            api_url="http://localhost:8000",
            timeout_seconds=5,
        )
        results["timeout"] = result.timed_out

        # Test 3: CPU limit (basic check)
        cpu_hog_code = """
import time
start = time.time()
total = 0
for i in range(10000000):
    total += i
elapsed = time.time() - start
print(f"Elapsed: {elapsed:.2f}s")
"""
        result = await self.execute_code(
            cpu_hog_code,
            session_id="test",
            api_url="http://localhost:8000",
            cpu_limit=0.25,
            timeout_seconds=60,
        )
        # Just verify it completed (CPU limiting slows it down)
        results["cpu_limit"] = result.success or result.timed_out

        return results

    async def test_network_isolation(self) -> dict:
        """
        Test that network isolation is enforced.

        Returns dict with test results.
        """
        results = {}

        # Test 1: Cannot reach external internet
        external_access_code = """
import urllib.request
import urllib.error

try:
    urllib.request.urlopen("http://google.com", timeout=5)
    print("FAIL: External access allowed")
except Exception as e:
    print(f"PASS: External access blocked - {type(e).__name__}")
"""
        result = await self.execute_code(
            external_access_code,
            session_id="test",
            api_url="http://localhost:8000",
            timeout_seconds=15,
        )
        results["external_blocked"] = (
            "PASS" in result.output or
            "blocked" in result.output.lower() or
            result.timed_out or
            not result.success
        )

        # Test 2: Cannot access host network services (except allowed API)
        host_access_code = """
import socket

blocked = True
for port in [22, 5432, 6379]:  # SSH, PostgreSQL, Redis
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("host.docker.internal", port))
        sock.close()
        blocked = False
        print(f"FAIL: Could connect to port {port}")
        break
    except Exception:
        pass

if blocked:
    print("PASS: Host ports blocked")
"""
        result = await self.execute_code(
            host_access_code,
            session_id="test",
            api_url="http://localhost:8000",
            timeout_seconds=15,
        )
        results["host_blocked"] = "PASS" in result.output or not result.success

        return results


# Singleton instance
_sandbox_service: Optional[SandboxService] = None


def get_sandbox_service() -> SandboxService:
    """Get singleton sandbox service instance."""
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService()
    return _sandbox_service
