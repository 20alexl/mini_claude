#!/usr/bin/env python3
"""
Mini Claude Reminder Hook

This script runs on every UserPromptSubmit and injects context
to remind Claude to use Mini Claude tools.

It checks:
1. If session_start has been called (by checking a temp file)
2. What files are about to be edited (from the prompt)
3. Recent mistakes that might be relevant
"""

import sys
import os
import json
from pathlib import Path

# Add mini_claude to path
project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "/media/alex/New Volume/Code/mini_cluade")
sys.path.insert(0, f"{project_dir}/mini_claude")

def get_reminder():
    """Generate a dynamic reminder based on current state."""
    lines = ["<mini-claude-reminder>"]

    # Check if we have an active session marker
    session_marker = Path("/tmp/mini_claude_session_active")
    session_active = session_marker.exists()

    if not session_active:
        lines.append("WARNING: You haven't started a Mini Claude session yet!")
        lines.append("Run this FIRST:")
        lines.append(f'  mcp__mini-claude__session_start(project_path="{project_dir}")')
        lines.append("")

    # Always remind about key tools
    lines.append("Mini Claude reminders:")
    lines.append("- BEFORE editing shared files: work_pre_edit_check(file_path)")
    lines.append("- WHEN something breaks: work_log_mistake(description, file_path)")
    lines.append("- WHEN making decisions: work_log_decision(decision, reason)")

    # Try to load recent mistakes from memory
    try:
        memory_file = Path.home() / ".mini_claude" / "memory.json"
        if memory_file.exists():
            data = json.loads(memory_file.read_text())
            project_key = project_dir
            if project_key in data.get("projects", {}):
                project = data["projects"][project_key]
                discoveries = project.get("entries", [])
                mistakes = [d for d in discoveries if d.get("content", "").upper().startswith("MISTAKE:")]
                if mistakes:
                    lines.append("")
                    lines.append(f"Past mistakes to remember ({len(mistakes)}):")
                    for m in mistakes[-3:]:  # Last 3
                        content = m.get("content", "")[9:]  # Remove "MISTAKE: "
                        lines.append(f"  - {content[:80]}")
    except Exception:
        pass  # Fail silently

    lines.append("</mini-claude-reminder>")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_reminder())
