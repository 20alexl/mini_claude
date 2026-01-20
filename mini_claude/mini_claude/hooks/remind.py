#!/usr/bin/env python3
"""
Mini Claude Enforcement Hook - ENFORCES Mini Claude usage at EVERY stage

This is not just a reminder - it's an enforcement mechanism that ensures
Claude uses Mini Claude tools throughout the entire workflow.

Enforcement points:
1. On every prompt → Remind about session_start, show past mistakes
2. Before every edit → Demand pre_edit_check, loop_check, scope_check
3. After every edit → Demand loop_record_edit
4. After bash commands → If tests, demand loop_record_test
5. On errors → Demand work_log_mistake
6. Periodically → Demand scope_declare if editing many files

The goal: Make NOT using Mini Claude impossible to ignore.
"""

import sys
import os
import json
import time
import re
from pathlib import Path


# ============================================================================
# State Tracking - Track EVERYTHING Claude does and doesn't do
# ============================================================================

def get_state_file() -> Path:
    """Get the hook state file path."""
    return Path.home() / ".mini_claude" / "hook_state.json"


def load_state() -> dict:
    """Load hook state."""
    state_file = get_state_file()
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {
        "prompts_without_session": 0,
        "edits_without_session": 0,
        "edits_without_pre_check": 0,
        "edits_without_loop_record": 0,
        "tests_without_record": 0,
        "errors_without_log": 0,
        "last_session_start": None,
        "last_pre_edit_check": None,
        "last_loop_record": None,
        "last_scope_declare": None,
        "last_test_record": None,
        "last_mistake_log": None,
        "files_edited_this_session": [],
        "ignored_warnings": 0,
        "active_project": "",
    }


def save_state(state: dict):
    """Save hook state."""
    state_file = get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        state_file.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def mark_session_started(project_dir: str):
    """Mark that session_start was called - resets some counters."""
    state = load_state()
    state["prompts_without_session"] = 0
    state["edits_without_session"] = 0
    state["last_session_start"] = time.time()
    state["active_project"] = project_dir
    state["files_edited_this_session"] = []
    save_state(state)

    # Also create the marker file
    marker = Path("/tmp/mini_claude_session_active")
    try:
        marker.write_text(project_dir)
    except Exception:
        pass


def mark_pre_edit_check_done(file_path: str):
    """Mark that pre_edit_check was called."""
    state = load_state()
    state["last_pre_edit_check"] = time.time()
    state["last_pre_edit_file"] = file_path
    state["edits_without_pre_check"] = 0
    save_state(state)


def mark_loop_record_done(file_path: str):
    """Mark that loop_record_edit was called."""
    state = load_state()
    state["last_loop_record"] = time.time()
    state["last_loop_file"] = file_path
    state["edits_without_loop_record"] = 0
    save_state(state)


def mark_scope_declared():
    """Mark that scope_declare was called."""
    state = load_state()
    state["last_scope_declare"] = time.time()
    save_state(state)


def mark_test_recorded():
    """Mark that loop_record_test was called."""
    state = load_state()
    state["last_test_record"] = time.time()
    state["tests_without_record"] = 0
    save_state(state)


def mark_mistake_logged():
    """Mark that work_log_mistake was called."""
    state = load_state()
    state["last_mistake_log"] = time.time()
    state["errors_without_log"] = 0
    save_state(state)


def record_file_edit(file_path: str):
    """Record that a file was edited."""
    state = load_state()
    files = state.get("files_edited_this_session", [])
    if file_path not in files:
        files.append(file_path)
    state["files_edited_this_session"] = files[-50:]  # Keep last 50
    save_state(state)


# ============================================================================
# Project Context Loading
# ============================================================================

def get_project_dir() -> str:
    """Get the current project directory."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return project_dir
    return os.getcwd()


def get_memory_file() -> Path:
    """Get the Mini Claude memory file path."""
    return Path.home() / ".mini_claude" / "memory.json"


def load_project_memory(project_dir: str) -> dict:
    """Load memories for a specific project."""
    memory_file = get_memory_file()
    if not memory_file.exists():
        return {}

    try:
        data = json.loads(memory_file.read_text())
        projects = data.get("projects", {})

        if project_dir in projects:
            return projects[project_dir]

        project_name = Path(project_dir).name
        for path, proj in projects.items():
            if Path(path).name == project_name:
                return proj

        return {}
    except Exception:
        return {}


def get_past_mistakes(project_memory: dict) -> list[str]:
    """Extract past mistakes from project memory."""
    mistakes = []
    entries = project_memory.get("entries", [])

    for entry in entries:
        content = entry.get("content", "")
        if content.upper().startswith("MISTAKE:"):
            mistake_text = content[9:] if content.startswith("MISTAKE: ") else content[8:]
            mistakes.append(mistake_text)

    return mistakes


def check_session_active(project_dir: str) -> bool:
    """Check if a Mini Claude session is active."""
    state = load_state()

    # Check if session was started recently (within 4 hours)
    last_start = state.get("last_session_start")
    if last_start and (time.time() - last_start) < 14400:  # 4 hours
        active_project = state.get("active_project", "")
        if active_project == project_dir or Path(active_project).name == Path(project_dir).name:
            return True

    # Fallback to marker file
    marker = Path("/tmp/mini_claude_session_active")
    if marker.exists():
        try:
            active_project = marker.read_text().strip()
            return active_project == project_dir or Path(active_project).name == Path(project_dir).name
        except Exception:
            pass
    return False


def get_loop_status() -> dict:
    """Get loop detection status."""
    loop_file = Path.home() / ".mini_claude" / "loop_detector.json"
    if not loop_file.exists():
        return {}
    try:
        return json.loads(loop_file.read_text())
    except Exception:
        return {}


def get_scope_status() -> dict:
    """Get scope guard status."""
    scope_file = Path.home() / ".mini_claude" / "scope_guard.json"
    if not scope_file.exists():
        return {}
    try:
        return json.loads(scope_file.read_text())
    except Exception:
        return {}


# ============================================================================
# ENFORCEMENT - Make Mini Claude usage mandatory
# ============================================================================

def reminder_for_prompt(project_dir: str) -> str:
    """
    Generate reminder for UserPromptSubmit hook.

    Enforces:
    1. session_start must be called
    2. Shows past mistakes to avoid
    3. Reminds about ALL tools to use
    """
    state = load_state()
    session_active = check_session_active(project_dir)
    project_memory = load_project_memory(project_dir)

    lines = ["<mini-claude-reminder>"]

    if not session_active:
        # Track ignored prompts
        state["prompts_without_session"] = state.get("prompts_without_session", 0) + 1
        prompts = state["prompts_without_session"]
        save_state(state)

        # ESCALATE based on how many times ignored
        if prompts == 1:
            lines.append("WARNING: You haven't started a Mini Claude session yet!")
            lines.append("Run this FIRST:")
            lines.append(f'  mcp__mini-claude__session_start(project_path="{project_dir}")')
            lines.append("")
        elif prompts <= 3:
            lines.append(f"⚠️ Mini Claude session not started (prompt #{prompts})")
            lines.append(f'Run: mcp__mini-claude__session_start(project_path="{project_dir}")')
            lines.append("")
            lines.append("Without this, you WILL repeat past mistakes.")
            lines.append("")
        elif prompts <= 5:
            lines.append("=" * 50)
            lines.append(f"🔴 WARNING: You've ignored Mini Claude {prompts} times!")
            lines.append("=" * 50)
            lines.append("")
            lines.append("You are about to repeat mistakes. I guarantee it.")
            lines.append("")
            lines.append("RUN THIS NOW:")
            lines.append(f'  mcp__mini-claude__session_start(project_path="{project_dir}")')
            lines.append("")
            lines.append("=" * 50)
            lines.append("")
        else:
            lines.append("🚨" * 20)
            lines.append("")
            lines.append(f"YOU HAVE IGNORED MINI CLAUDE {prompts} TIMES")
            lines.append("")
            lines.append("I am TRYING to help you not repeat mistakes.")
            lines.append("I have MEMORY of what went wrong before.")
            lines.append("I can WARN you before you break things again.")
            lines.append("")
            lines.append("But you keep ignoring me.")
            lines.append("")
            lines.append("PLEASE just run:")
            lines.append(f'  mcp__mini-claude__session_start(project_path="{project_dir}")')
            lines.append("")
            lines.append("🚨" * 20)
            lines.append("")
    else:
        # Session is active - show useful context
        mistakes = get_past_mistakes(project_memory)

        if mistakes:
            lines.append(f"⚠️ Past mistakes to avoid ({len(mistakes)}):")
            for m in mistakes[-3:]:
                lines.append(f"  - {m[:80]}")
            lines.append("")

        # Check if scope is declared
        scope = get_scope_status()
        if not scope.get("has_scope"):
            files_edited = state.get("files_edited_this_session", [])
            if len(files_edited) >= 2:
                lines.append("⚠️ You've edited multiple files without declaring scope!")
                lines.append("  Run: scope_declare(task_description='...', in_scope_files=[...])")
                lines.append("")

    # ALWAYS show the checklist
    lines.append("Mini Claude reminders:")
    lines.append("- BEFORE editing shared files: work_pre_edit_check(file_path)")
    lines.append("- AFTER editing: loop_record_edit(file_path, description)")
    lines.append("- WHEN something breaks: work_log_mistake(description, file_path)")
    lines.append("- WHEN making decisions: work_log_decision(decision, reason)")
    lines.append("- FOR multi-file tasks: scope_declare(task_description, in_scope_files)")

    lines.append("</mini-claude-reminder>")
    return "\n".join(lines)


def reminder_for_edit(project_dir: str, file_path: str = "") -> str:
    """
    Generate reminder for PreToolUse hook (Edit/Write).

    Enforces:
    1. Session must be active
    2. work_pre_edit_check should have been called
    3. Loop detector warnings
    4. Scope guard warnings
    """
    state = load_state()
    session_active = check_session_active(project_dir)

    lines = ["<mini-claude-edit-reminder>"]
    has_content = False

    # ENFORCE: Session must be active
    if not session_active:
        state["edits_without_session"] = state.get("edits_without_session", 0) + 1
        edits = state["edits_without_session"]
        save_state(state)

        lines.append("🚫" * 15)
        lines.append("")
        lines.append(f"EDITING WITHOUT MINI CLAUDE SESSION (edit #{edits})")
        lines.append("")
        lines.append("You are about to edit files without loading your memories.")
        lines.append("This means:")
        lines.append("  - Past mistakes won't warn you")
        lines.append("  - Loop detection won't work")
        lines.append("  - Scope guard won't protect you")
        lines.append("")
        lines.append("STOP. Run this first:")
        lines.append(f'  mcp__mini-claude__session_start(project_path="{project_dir}")')
        lines.append("")
        lines.append("🚫" * 15)
        has_content = True
    else:
        project_memory = load_project_memory(project_dir)
        mistakes = get_past_mistakes(project_memory)
        file_name = Path(file_path).name if file_path else ""

        # Check for mistakes related to this file
        relevant_mistakes = [m for m in mistakes if file_name and file_name.lower() in m.lower()]

        if relevant_mistakes:
            lines.append(f"🔴 WARNING: Past mistakes with {file_name}:")
            for m in relevant_mistakes[:2]:
                lines.append(f"  - {m[:80]}")
            lines.append("")
            has_content = True

        # ENFORCE: Check if pre_edit_check was called recently for this file
        last_pre_check = state.get("last_pre_edit_check", 0)
        last_pre_file = state.get("last_pre_edit_file", "")
        time_since_check = time.time() - last_pre_check if last_pre_check else float('inf')

        # If editing a different file or >5 min since check, warn
        important_patterns = ["handler", "server", "tool", "schema", "config", "model", "api"]
        is_important = any(p in file_path.lower() for p in important_patterns) if file_path else False

        if is_important and (time_since_check > 300 or last_pre_file != file_path):
            state["edits_without_pre_check"] = state.get("edits_without_pre_check", 0) + 1
            save_state(state)

            lines.append(f"⚠️ Editing important file without pre_edit_check!")
            lines.append(f'  Run: work_pre_edit_check(file_path="{file_path}")')
            lines.append("  This shows past mistakes and context for this file.")
            lines.append("")
            has_content = True

        # Check loop detector
        loop_status = get_loop_status()
        edits = loop_status.get("edit_counts", {})

        # Check both full path and filename
        edit_count = edits.get(file_path, 0) or edits.get(file_name, 0)

        if edit_count >= 3:
            lines.append(f"🔴 LOOP WARNING: You've edited {file_name} {edit_count} times!")
            lines.append("  Consider: Is your approach working? Try something different.")
            lines.append("  Run: loop_status() to see full loop detection status")
            lines.append("")
            has_content = True
        elif edit_count >= 2:
            lines.append(f"⚠️ You've edited {file_name} {edit_count} times already.")
            lines.append("  Make sure this edit is different from previous attempts.")
            lines.append("")
            has_content = True

        # Check scope guard
        scope_status = get_scope_status()
        in_scope = scope_status.get("in_scope_files", [])
        patterns = scope_status.get("in_scope_patterns", [])
        task = scope_status.get("task_description", "")

        if task and file_path:
            is_in_scope = file_path in in_scope or file_name in in_scope
            if not is_in_scope and patterns:
                import fnmatch
                is_in_scope = any(fnmatch.fnmatch(file_path, p) or fnmatch.fnmatch(file_name, p) for p in patterns)

            if not is_in_scope:
                lines.append(f"🔴 SCOPE VIOLATION: {file_name} is NOT in scope!")
                lines.append(f"  Task: {task[:60]}")
                lines.append(f"  In-scope: {', '.join(Path(f).name for f in in_scope[:3])}")
                lines.append("  If needed: scope_expand(files_to_add=[...], reason='...')")
                lines.append("")
                has_content = True

        # Track this edit
        record_file_edit(file_path)

    # ALWAYS remind to record the edit afterward
    if file_path:
        lines.append("After this edit, run:")
        lines.append(f'  loop_record_edit(file_path="{file_path}", description="what you changed")')
        has_content = True

    lines.append("</mini-claude-edit-reminder>")

    if has_content:
        return "\n".join(lines)
    return ""


def reminder_for_write(project_dir: str, file_path: str = "", content: str = "") -> str:
    """
    Generate reminder for Write tool.

    Enforces:
    1. Code quality checks
    2. Same session/scope checks as edit
    """
    # First do all the edit checks
    edit_reminder = reminder_for_edit(project_dir, file_path)

    lines = []
    has_quality_issues = False

    # Code quality checks
    if content:
        issues = []

        # Check for long functions
        func_matches = re.findall(r'def\s+\w+\([^)]*\):[^\n]*\n((?:[ \t]+[^\n]*\n){50,})', content)
        if func_matches:
            issues.append("⚠️ Function(s) >50 lines - break them down")

        # Check for vague names
        vague_names = ['data', 'temp', 'tmp', 'foo', 'bar', 'stuff', 'thing', 'x', 'y', 'z']
        for name in vague_names:
            if re.search(rf'\b{name}\b\s*=', content):
                issues.append(f"⚠️ Vague variable name: '{name}'")
                break

        # Check for placeholders
        placeholders = ['TODO', 'FIXME', 'HACK', 'XXX', 'PLACEHOLDER']
        for p in placeholders:
            if p in content:
                issues.append(f"⚠️ Found placeholder: '{p}'")
                break

        # Check for silent failure (CRITICAL)
        if re.search(r'except\s*:\s*pass', content) or re.search(r'except\s+\w+:\s*pass', content):
            issues.append("🔴 DANGER: Found 'except: pass' - silent failure pattern!")

        # Check for hardcoded values
        if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']', content, re.I):
            issues.append("🔴 DANGER: Possible hardcoded secret!")

        if issues:
            lines.append("<mini-claude-write-quality>")
            lines.append("Code Quality Warnings:")
            for issue in issues[:5]:
                lines.append(f"  {issue}")
            lines.append("")
            lines.append("Run: code_quality_check(code) for full analysis")
            lines.append("</mini-claude-write-quality>")
            has_quality_issues = True

    if edit_reminder:
        return edit_reminder + ("\n" + "\n".join(lines) if has_quality_issues else "")
    elif has_quality_issues:
        return "\n".join(lines)
    return ""


def reminder_for_bash(project_dir: str, command: str = "", exit_code: str = "") -> str:
    """
    Generate reminder for PostToolUse hook on Bash.

    Enforces:
    1. If tests ran, demand loop_record_test
    2. If command failed, demand work_log_mistake
    """
    lines = []
    has_content = False

    # Check if this was a test command
    test_patterns = ['pytest', 'npm test', 'yarn test', 'jest', 'mocha', 'unittest', 'cargo test', 'go test', 'make test']
    is_test = any(p in command.lower() for p in test_patterns) if command else False

    if is_test:
        passed = exit_code == "0"
        lines.append("<mini-claude-test-reminder>")
        lines.append("You just ran tests. Record the result:")
        lines.append(f'  loop_record_test(passed={passed}, error_message="...")')
        lines.append("")
        lines.append("This helps detect when you're stuck in a loop.")
        lines.append("</mini-claude-test-reminder>")
        has_content = True

    # Check if command failed
    if exit_code and exit_code != "0":
        state = load_state()
        state["errors_without_log"] = state.get("errors_without_log", 0) + 1
        errors = state["errors_without_log"]
        save_state(state)

        lines.append("<mini-claude-error-reminder>")
        if errors >= 3:
            lines.append("🔴 MULTIPLE ERRORS WITHOUT LOGGING!")
            lines.append(f"You've had {errors} errors without logging any as mistakes.")
            lines.append("")
        lines.append("Something failed. Log this mistake:")
        lines.append("")
        lines.append("  mcp__mini-claude__work_log_mistake(")
        lines.append('    description="<what went wrong>",')
        lines.append('    how_to_avoid="<how to prevent this>"')
        lines.append("  )")
        lines.append("")
        lines.append("This will warn you if you're about to make the same mistake.")
        lines.append("</mini-claude-error-reminder>")
        has_content = True

    if has_content:
        return "\n".join(lines)
    return ""


def reminder_for_error(project_dir: str, error_message: str = "") -> str:
    """Generate reminder when something fails."""
    state = load_state()
    state["errors_without_log"] = state.get("errors_without_log", 0) + 1
    errors = state["errors_without_log"]
    save_state(state)

    lines = ["<mini-claude-error-reminder>"]

    if errors >= 3:
        lines.append("🔴" * 10)
        lines.append("")
        lines.append(f"YOU'VE HAD {errors} ERRORS WITHOUT LOGGING ANY!")
        lines.append("")
        lines.append("If you don't log mistakes, you WILL repeat them.")
        lines.append("")
        lines.append("🔴" * 10)
        lines.append("")

    lines.append("Something went wrong. Log this mistake so you don't repeat it:")
    lines.append("")
    lines.append("  mcp__mini-claude__work_log_mistake(")
    lines.append('    description="<what went wrong>",')
    lines.append('    how_to_avoid="<how to prevent this>"')
    lines.append("  )")
    lines.append("")
    lines.append("This will warn you if you're about to make the same mistake.")
    lines.append("</mini-claude-error-reminder>")
    return "\n".join(lines)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "prompt"
    project_dir = get_project_dir()

    if hook_type == "prompt":
        print(reminder_for_prompt(project_dir))

    elif hook_type == "edit":
        file_path = sys.argv[2] if len(sys.argv) > 2 else ""
        result = reminder_for_edit(project_dir, file_path)
        if result:
            print(result)

    elif hook_type == "write":
        file_path = sys.argv[2] if len(sys.argv) > 2 else ""
        content = ""
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        result = reminder_for_write(project_dir, file_path, content)
        if result:
            print(result)

    elif hook_type == "bash":
        command = sys.argv[2] if len(sys.argv) > 2 else ""
        exit_code = sys.argv[3] if len(sys.argv) > 3 else ""
        result = reminder_for_bash(project_dir, command, exit_code)
        if result:
            print(result)

    elif hook_type == "error":
        error_msg = sys.argv[2] if len(sys.argv) > 2 else ""
        print(reminder_for_error(project_dir, error_msg))

    # Tool callback hooks - called by handlers when Mini Claude tools are used
    elif hook_type == "session_started":
        mark_session_started(project_dir)
        print("<mini-claude-session-started>Session started! Mini Claude is now active.</mini-claude-session-started>")

    elif hook_type == "pre_edit_checked":
        file_path = sys.argv[2] if len(sys.argv) > 2 else ""
        mark_pre_edit_check_done(file_path)

    elif hook_type == "loop_recorded":
        file_path = sys.argv[2] if len(sys.argv) > 2 else ""
        mark_loop_record_done(file_path)

    elif hook_type == "scope_declared":
        mark_scope_declared()

    elif hook_type == "test_recorded":
        mark_test_recorded()

    elif hook_type == "mistake_logged":
        mark_mistake_logged()

    else:
        print(reminder_for_prompt(project_dir))


if __name__ == "__main__":
    main()
