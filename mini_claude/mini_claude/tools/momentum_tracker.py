"""
Momentum Tracker - Detects when Claude stops mid-task

Prevents the pattern where Claude:
1. Starts a multi-step task
2. Completes step 1
3. Stops and reports back instead of continuing to step 2

This is different from loop detection - it's about maintaining forward progress
through a known sequence of steps.

Detection signals:
- Todo list has pending items
- Recent file reads without corresponding edits
- Partial completion patterns (e.g., read server.py, didn't edit it)
"""

import time
from pathlib import Path
from typing import Optional

from ..schema import MiniClaudeResponse, WorkLog


class MomentumTracker:
    """Track task momentum to detect premature stopping."""

    def __init__(self):
        self.task_stack: list[dict] = []  # Stack of active tasks
        self.recent_actions: list[dict] = []  # Recent actions taken
        self.last_momentum_check: Optional[float] = None

    def start_task(self, task_description: str, expected_steps: list[str]) -> None:
        """
        Start tracking a multi-step task.

        Args:
            task_description: What the task is
            expected_steps: List of steps that should be completed
        """
        task = {
            "description": task_description,
            "expected_steps": expected_steps,
            "completed_steps": [],
            "start_time": time.time(),
            "last_action_time": time.time(),
        }
        self.task_stack.append(task)

    def record_action(self, action_type: str, details: str) -> None:
        """
        Record an action taken.

        Args:
            action_type: Type of action (read, edit, bash, etc.)
            details: Details about the action
        """
        action = {
            "type": action_type,
            "details": details,
            "timestamp": time.time(),
        }
        self.recent_actions.append(action)

        # Keep only last 20 actions
        if len(self.recent_actions) > 20:
            self.recent_actions = self.recent_actions[-20:]

        # Update last action time on current task
        if self.task_stack:
            self.task_stack[-1]["last_action_time"] = time.time()

    def complete_step(self, step: str) -> None:
        """Mark a step as completed on the current task."""
        if not self.task_stack:
            return

        current = self.task_stack[-1]
        if step not in current["completed_steps"]:
            current["completed_steps"].append(step)

    def finish_task(self) -> None:
        """Mark the current task as finished."""
        if self.task_stack:
            self.task_stack.pop()

    def check_momentum(self) -> MiniClaudeResponse:
        """
        Check if momentum is being maintained.

        Returns warnings if:
        - Current task has pending steps
        - Recent reads without corresponding edits
        - Inactive for too long (>30s with pending work)
        """
        work_log = WorkLog()
        self.last_momentum_check = time.time()

        if not self.task_stack:
            # No active task - momentum is fine
            return MiniClaudeResponse(
                status="success",
                confidence="high",
                reasoning="No active multi-step task",
                work_log=work_log,
            )

        current_task = self.task_stack[-1]
        expected = set(current_task["expected_steps"])
        completed = set(current_task["completed_steps"])
        pending = expected - completed

        if not pending:
            # All steps complete - momentum maintained!
            work_log.what_worked.append("All task steps completed")
            return MiniClaudeResponse(
                status="success",
                confidence="high",
                reasoning=f"Task '{current_task['description']}' completed all steps",
                work_log=work_log,
                suggestions=["Call finish_task() to mark task complete"],
            )

        # Check for stalling patterns
        warnings = []
        suggestions = []

        # Pattern 1: Pending steps exist
        if pending:
            warnings.append(f"{len(pending)} steps still pending")
            suggestions.append(f"Continue with: {list(pending)[0]}")

        # Pattern 2: Recent reads without edits
        recent_reads = [a for a in self.recent_actions[-10:] if a["type"] == "read"]
        recent_edits = [a for a in self.recent_actions[-10:] if a["type"] == "edit"]

        if len(recent_reads) > len(recent_edits) + 2:
            # More reads than edits - might be planning instead of doing
            warnings.append(f"{len(recent_reads)} reads but only {len(recent_edits)} edits")
            suggestions.append("Stop reading, start editing")

        # Pattern 3: Inactive too long
        time_since_action = time.time() - current_task["last_action_time"]
        if time_since_action > 30 and pending:
            warnings.append(f"Inactive for {int(time_since_action)}s with pending work")
            suggestions.append("Don't stop mid-task - keep going!")

        if warnings:
            work_log.what_failed.append("Momentum loss detected")
            return MiniClaudeResponse(
                status="warning",
                confidence="high",
                reasoning=f"Task '{current_task['description']}' incomplete",
                work_log=work_log,
                warnings=warnings,
                suggestions=suggestions,
                data={
                    "pending_steps": list(pending),
                    "completed_steps": list(completed),
                    "task": current_task["description"],
                },
            )

        # No issues detected
        work_log.what_worked.append("Momentum maintained")
        return MiniClaudeResponse(
            status="success",
            confidence="high",
            reasoning="Task in progress, momentum maintained",
            work_log=work_log,
        )

    def detect_partial_completion(self) -> dict:
        """
        Detect partial completion patterns from recent actions.

        Returns dict with:
        - pattern_detected: bool
        - pattern_type: str (e.g., "read_without_edit")
        - suggestion: str
        """
        if len(self.recent_actions) < 2:
            return {"pattern_detected": False}

        # Pattern: Read file, then stop (no corresponding edit)
        last_action = self.recent_actions[-1]
        if last_action["type"] == "read":
            # Check if there's a matching edit in recent actions
            file_path = last_action.get("details", "")
            recent_edits = [
                a for a in self.recent_actions[-5:]
                if a["type"] == "edit" and file_path in a.get("details", "")
            ]

            if not recent_edits:
                return {
                    "pattern_detected": True,
                    "pattern_type": "read_without_edit",
                    "file": file_path,
                    "suggestion": f"You read {Path(file_path).name} - did you mean to edit it?",
                }

        # Pattern: Multiple reads in sequence
        recent_types = [a["type"] for a in self.recent_actions[-5:]]
        read_count = recent_types.count("read")
        if read_count >= 3:
            return {
                "pattern_detected": True,
                "pattern_type": "excessive_reading",
                "suggestion": "You're reading a lot - make sure you're making progress, not just exploring",
            }

        return {"pattern_detected": False}

    def get_status(self) -> dict:
        """Get current momentum tracking status."""
        if not self.task_stack:
            return {
                "active_task": None,
                "recent_actions_count": len(self.recent_actions),
            }

        current = self.task_stack[-1]
        return {
            "active_task": current["description"],
            "expected_steps": current["expected_steps"],
            "completed_steps": current["completed_steps"],
            "pending_steps": list(set(current["expected_steps"]) - set(current["completed_steps"])),
            "recent_actions_count": len(self.recent_actions),
            "time_since_start": time.time() - current["start_time"],
            "time_since_last_action": time.time() - current["last_action_time"],
        }
