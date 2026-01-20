"""
Test Runner - Automatic test execution and verification

Prevents false completion claims by:
1. Auto-detecting test commands based on project type
2. Running tests and capturing results
3. Blocking completion claims if tests fail
4. Tracking test history to detect flaky tests
"""

import subprocess
import time
from pathlib import Path
from typing import Optional

from ..schema import MiniClaudeResponse, WorkLog


class TestRunner:
    """Automatically run and verify tests."""

    def __init__(self):
        self.last_test_result: Optional[dict] = None
        self.test_history: list[dict] = []

    def detect_test_command(self, project_dir: str) -> Optional[str]:
        """
        Auto-detect the test command based on project files.

        Returns the command to run tests, or None if can't detect.
        """
        project_path = Path(project_dir)

        # Python projects
        if (project_path / "pytest.ini").exists() or (project_path / "setup.py").exists():
            return "pytest"
        if (project_path / "pyproject.toml").exists():
            # Check if pytest is configured
            try:
                content = (project_path / "pyproject.toml").read_text()
                if "pytest" in content.lower():
                    return "pytest"
                if "unittest" in content.lower():
                    return "python -m unittest discover"
            except Exception:
                pass

        # Node.js projects
        if (project_path / "package.json").exists():
            try:
                import json
                pkg = json.loads((project_path / "package.json").read_text())
                if "scripts" in pkg and "test" in pkg["scripts"]:
                    return "npm test"
            except Exception:
                pass

        # Go projects
        if (project_path / "go.mod").exists():
            return "go test ./..."

        # Rust projects
        if (project_path / "Cargo.toml").exists():
            return "cargo test"

        # Makefile projects
        if (project_path / "Makefile").exists():
            try:
                content = (project_path / "Makefile").read_text()
                if "test:" in content:
                    return "make test"
            except Exception:
                pass

        return None

    def run_tests(
        self,
        project_dir: str,
        test_command: Optional[str] = None,
        timeout: int = 300,
    ) -> MiniClaudeResponse:
        """
        Run tests and return results.

        Args:
            project_dir: Project directory to run tests in
            test_command: Explicit test command (auto-detect if None)
            timeout: Max time in seconds (default 5 minutes)
        """
        work_log = WorkLog()
        project_path = Path(project_dir)

        # Auto-detect if not provided
        if not test_command:
            test_command = self.detect_test_command(project_dir)
            if not test_command:
                return MiniClaudeResponse(
                    status="failed",
                    confidence="high",
                    reasoning="Could not detect test command for this project",
                    work_log=WorkLog(
                        what_failed=["Test command detection failed"],
                    ),
                    suggestions=[
                        "Provide explicit test_command parameter",
                        "Add test configuration (pytest.ini, package.json scripts, etc.)",
                    ],
                )

        work_log.what_i_tried.append(f"Running: {test_command}")

        # Run the command
        start_time = time.time()
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = time.time() - start_time

            # Store result
            test_result = {
                "command": test_command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_seconds": elapsed,
                "timestamp": time.time(),
            }
            self.last_test_result = test_result
            self.test_history.append(test_result)

            # Keep only last 10 test runs
            if len(self.test_history) > 10:
                self.test_history = self.test_history[-10:]

            work_log.time_taken_ms = int(elapsed * 1000)

            # Parse results
            passed = result.returncode == 0

            if passed:
                work_log.what_worked.append("All tests passed")
                return MiniClaudeResponse(
                    status="success",
                    confidence="high",
                    reasoning=f"Tests passed in {elapsed:.1f}s",
                    work_log=work_log,
                    data={
                        "passed": True,
                        "exit_code": 0,
                        "elapsed_seconds": elapsed,
                        "output": result.stdout[:500] if result.stdout else "",
                    },
                    suggestions=["Tests are passing - safe to claim completion"],
                )
            else:
                # Extract failure info
                output = result.stdout + "\n" + result.stderr
                failure_lines = [line for line in output.split("\n") if "FAILED" in line or "ERROR" in line]

                work_log.what_failed.append(f"Tests failed with exit code {result.returncode}")

                return MiniClaudeResponse(
                    status="failed",
                    confidence="high",
                    reasoning=f"{len(failure_lines)} test failure(s) detected",
                    work_log=work_log,
                    data={
                        "passed": False,
                        "exit_code": result.returncode,
                        "elapsed_seconds": elapsed,
                        "failures": failure_lines[:10],  # First 10 failures
                        "full_output": output[:2000],  # First 2000 chars
                    },
                    warnings=["DO NOT claim completion - tests are failing"],
                    suggestions=[
                        "Fix failing tests before claiming done",
                        "Use work_log_mistake to record what went wrong",
                        "Check the failure output in data.full_output",
                    ],
                )

        except subprocess.TimeoutExpired:
            work_log.what_failed.append(f"Tests timed out after {timeout}s")
            return MiniClaudeResponse(
                status="failed",
                confidence="high",
                reasoning=f"Tests exceeded {timeout}s timeout",
                work_log=work_log,
                warnings=["Tests are hanging - investigate infinite loops or slow tests"],
                suggestions=[
                    "Increase timeout if tests are legitimately slow",
                    "Check for infinite loops in test code",
                    "Run specific slow tests individually",
                ],
            )

        except Exception as e:
            work_log.what_failed.append(f"Test execution failed: {str(e)}")
            return MiniClaudeResponse(
                status="failed",
                confidence="high",
                reasoning=f"Could not run tests: {str(e)}",
                work_log=work_log,
                suggestions=[
                    "Check test command is correct",
                    "Ensure test dependencies are installed",
                    "Try running the command manually",
                ],
            )

    def can_claim_completion(self) -> tuple[bool, str]:
        """
        Check if completion can be claimed based on test history.

        Returns:
            (can_claim, reason)
        """
        if not self.last_test_result:
            return False, "No tests have been run yet"

        if self.last_test_result["exit_code"] != 0:
            return False, f"Last test run failed with exit code {self.last_test_result['exit_code']}"

        # Check for flaky tests (passed now but failed recently)
        if len(self.test_history) >= 2:
            recent_failures = [
                r for r in self.test_history[-5:]
                if r["exit_code"] != 0
            ]
            if recent_failures:
                return False, f"Tests are flaky - {len(recent_failures)} failures in last 5 runs"

        return True, "Tests passing consistently"

    def get_test_summary(self) -> dict:
        """Get summary of test history."""
        if not self.test_history:
            return {
                "total_runs": 0,
                "recent_passes": 0,
                "recent_failures": 0,
                "last_result": None,
            }

        recent = self.test_history[-10:]
        passes = sum(1 for r in recent if r["exit_code"] == 0)
        failures = len(recent) - passes

        return {
            "total_runs": len(self.test_history),
            "recent_passes": passes,
            "recent_failures": failures,
            "last_result": self.last_test_result,
            "can_claim_completion": self.can_claim_completion(),
        }
