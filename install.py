#!/usr/bin/env python3
"""
Mini Claude Installer

Sets up Mini Claude for use with Claude Code:
1. Installs the mini_claude package
2. Configures MCP server in Claude Code
3. Installs global hooks for reminders

Usage:
  python install.py

Requirements:
  - Python 3.10+
  - Ollama running with qwen2.5-coder:7b (or another model)
  - Claude Code installed
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def print_step(step: int, total: int, message: str):
    """Print a step message."""
    print(f"\n[{step}/{total}] {message}")


def print_success(message: str):
    """Print a success message."""
    print(f"  ✓ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"  ✗ {message}")


def check_ollama():
    """Check if Ollama is running."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def install_package():
    """Install the mini_claude package."""
    script_dir = Path(__file__).parent
    package_dir = script_dir / "mini_claude"

    if not package_dir.exists():
        return False, "mini_claude package directory not found"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(package_dir)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, None
    except Exception as e:
        return False, str(e)


def configure_mcp():
    """Configure MCP server in Claude Code settings."""
    # Find Claude Code config location
    home = Path.home()
    possible_configs = [
        home / ".claude" / "settings.json",
        home / ".config" / "claude" / "settings.json",
    ]

    config_path = None
    for p in possible_configs:
        if p.parent.exists():
            config_path = p
            break

    if not config_path:
        # Create the default location
        config_path = home / ".claude" / "settings.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            config = {}
    else:
        config = {}

    # Add MCP server configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Get the path to mini_claude
    script_dir = Path(__file__).parent
    venv_python = script_dir / "venv" / "bin" / "python"

    if venv_python.exists():
        python_path = str(venv_python)
    else:
        python_path = sys.executable

    config["mcpServers"]["mini-claude"] = {
        "command": python_path,
        "args": ["-m", "mini_claude.server"]
    }

    # Save config
    try:
        config_path.write_text(json.dumps(config, indent=2))
        return True, str(config_path)
    except Exception as e:
        return False, str(e)


def install_hooks():
    """Install global hooks for Mini Claude reminders."""
    home = Path.home()
    config_path = home / ".claude" / "settings.json"

    # Load existing config
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            config = {}
    else:
        config = {}
        config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load hooks config from package
    script_dir = Path(__file__).parent
    hooks_config_path = script_dir / "mini_claude" / "hooks_config.json"

    if hooks_config_path.exists():
        try:
            hooks_config = json.loads(hooks_config_path.read_text())
            config["hooks"] = hooks_config.get("hooks", {})
        except Exception as e:
            return False, str(e)

    # Save config
    try:
        config_path.write_text(json.dumps(config, indent=2))
        return True, str(config_path)
    except Exception as e:
        return False, str(e)


def create_memory_dir():
    """Create the Mini Claude memory directory."""
    memory_dir = Path.home() / ".mini_claude"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return str(memory_dir)


def main():
    print("=" * 60)
    print("Mini Claude Installer")
    print("=" * 60)
    print("\nMini Claude gives Claude Code persistent memory and")
    print("self-awareness tools to help avoid repeating mistakes.")

    total_steps = 5

    # Step 1: Check Ollama
    print_step(1, total_steps, "Checking Ollama...")
    if check_ollama():
        print_success("Ollama is running")
    else:
        print_error("Ollama is not running")
        print("  Please start Ollama and ensure qwen2.5-coder:7b is available:")
        print("    ollama serve")
        print("    ollama pull qwen2.5-coder:7b")
        response = input("\n  Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1

    # Step 2: Install package
    print_step(2, total_steps, "Installing mini_claude package...")
    success, error = install_package()
    if success:
        print_success("Package installed")
    else:
        print_error(f"Failed to install package: {error}")
        return 1

    # Step 3: Configure MCP
    print_step(3, total_steps, "Configuring MCP server...")
    success, result = configure_mcp()
    if success:
        print_success(f"MCP configured in {result}")
    else:
        print_error(f"Failed to configure MCP: {result}")
        return 1

    # Step 4: Install hooks
    print_step(4, total_steps, "Installing reminder hooks...")
    success, result = install_hooks()
    if success:
        print_success(f"Hooks installed in {result}")
    else:
        print_error(f"Failed to install hooks: {result}")
        print("  You can still use Mini Claude, but won't get automatic reminders")

    # Step 5: Create memory directory
    print_step(5, total_steps, "Creating memory directory...")
    memory_dir = create_memory_dir()
    print_success(f"Memory directory: {memory_dir}")

    print("\n" + "=" * 60)
    print("Installation complete!")
    print("=" * 60)

    print("\nNext steps:")
    print("1. Restart Claude Code to load the MCP server")
    print("2. In any project, start with:")
    print('   mcp__mini-claude__session_start(project_path="<your project>")')
    print("\nMini Claude will:")
    print("- Remember what you learn across sessions")
    print("- Warn you about past mistakes")
    print("- Remind you to use its tools (via hooks)")

    print("\n38 Tools Available:")
    print("\n  Session & Memory:")
    print("    session_start, memory_remember, memory_recall, memory_forget")
    print("\n  Work Tracking:")
    print("    work_log_mistake, work_log_decision, work_pre_edit_check")
    print("    work_session_summary, work_save_session")
    print("\n  Safety Guards:")
    print("    code_quality_check, loop_record_edit, loop_check_before_edit")
    print("    scope_declare, scope_check, scope_expand, scope_status")
    print("\n  Context Protection:")
    print("    context_checkpoint_save, context_checkpoint_restore")
    print("    context_instruction_add, context_handoff_create")
    print("    context_self_check, output_validate_code")
    print("\n  Analysis:")
    print("    scout_search, scout_analyze, file_summarize, deps_map")
    print("    impact_analyze, convention_add, convention_check")

    print("\nEnforcement:")
    print("  - Hooks will remind Claude to use session_start on every prompt")
    print("  - Warnings ESCALATE if Claude ignores Mini Claude")
    print("  - After 5+ ignored prompts: Maximum annoyance mode activates")

    return 0


if __name__ == "__main__":
    sys.exit(main())
