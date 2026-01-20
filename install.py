#!/usr/bin/env python3
"""
Mini Claude Installer

Sets up Mini Claude for use with Claude Code:
1. Creates virtual environment (if needed)
2. Installs the mini_claude package
3. Shows how to enable in your projects

Usage:
  cd mini_claude_repo
  python -m venv venv
  source venv/bin/activate  # or venv\\Scripts\\activate on Windows
  pip install -e mini_claude/
  python install.py

Requirements:
  - Python 3.10+
  - Ollama running with qwen2.5-coder:7b (or another model)
  - Claude Code installed
"""

import json
import os
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


def print_warning(message: str):
    """Print a warning message."""
    print(f"  ⚠ {message}")


def check_venv():
    """Check if running in a virtual environment."""
    return sys.prefix != sys.base_prefix


def check_ollama():
    """Check if Ollama is running."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def check_package_installed():
    """Check if mini_claude package is installed."""
    try:
        import mini_claude
        return True
    except ImportError:
        return False


def install_package():
    """Install the mini_claude package."""
    script_dir = Path(__file__).parent.resolve()
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


def create_memory_dir():
    """Create the Mini Claude memory directory."""
    memory_dir = Path.home() / ".mini_claude"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return str(memory_dir)


def get_mcp_config():
    """Generate the .mcp.json configuration."""
    script_dir = Path(__file__).parent.resolve()

    # Find the Python executable - prefer venv
    venv_python = script_dir / "venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = script_dir / "venv" / "Scripts" / "python.exe"  # Windows

    if venv_python.exists():
        python_path = str(venv_python)
    else:
        python_path = sys.executable

    return {
        "mcpServers": {
            "mini-claude": {
                "command": python_path,
                "args": ["-m", "mini_claude.server"]
            }
        }
    }


def create_project_mcp_config(target_dir: Path):
    """Create .mcp.json in a target project directory."""
    config = get_mcp_config()
    mcp_file = target_dir / ".mcp.json"

    try:
        mcp_file.write_text(json.dumps(config, indent=2))
        return True, str(mcp_file)
    except Exception as e:
        return False, str(e)


def copy_claude_md(target_dir: Path):
    """Copy CLAUDE.md template to target project."""
    script_dir = Path(__file__).parent.resolve()
    source = script_dir / "CLAUDE.md"
    target = target_dir / "CLAUDE.md"

    if not source.exists():
        return False, "CLAUDE.md not found in mini_claude repo"

    if target.exists():
        return False, "CLAUDE.md already exists in target (not overwriting)"

    try:
        # Read and customize the template
        content = source.read_text()
        # Replace the hardcoded path with the target path
        content = content.replace(
            '/media/alex/New Volume/Code/mini_cluade',
            str(target_dir)
        )
        target.write_text(content)
        return True, str(target)
    except Exception as e:
        return False, str(e)


def setup_project(target_dir: str):
    """Set up Mini Claude for a specific project."""
    target = Path(target_dir).resolve()

    if not target.exists():
        return False, f"Directory does not exist: {target}"

    print(f"\nSetting up Mini Claude for: {target}")

    # Create .mcp.json
    success, result = create_project_mcp_config(target)
    if success:
        print_success(f"Created {result}")
    else:
        print_error(f"Failed to create .mcp.json: {result}")
        return False, result

    # Copy CLAUDE.md
    success, result = copy_claude_md(target)
    if success:
        print_success(f"Created {result}")
    else:
        print_warning(result)

    return True, None


def main():
    print("=" * 60)
    print("Mini Claude Installer")
    print("=" * 60)
    print("\nMini Claude gives Claude Code persistent memory and")
    print("self-awareness tools to help avoid repeating mistakes.")

    total_steps = 5
    script_dir = Path(__file__).parent.resolve()

    # Step 1: Check virtual environment
    print_step(1, total_steps, "Checking virtual environment...")
    if check_venv():
        print_success("Running in virtual environment")
    else:
        print_error("Not running in a virtual environment!")
        print("\n  Please create and activate a venv first:")
        print(f"    cd \"{script_dir}\"")
        print("    python -m venv venv")
        print("    source venv/bin/activate  # Linux/Mac")
        print("    # or: venv\\Scripts\\activate  # Windows")
        print("\n  Then run this script again.")
        return 1

    # Step 2: Check Ollama
    print_step(2, total_steps, "Checking Ollama...")
    if check_ollama():
        print_success("Ollama is running")
    else:
        print_error("Ollama is not running")
        print("  Please start Ollama and pull the model:")
        print("    ollama serve")
        print("    ollama pull qwen2.5-coder:7b")
        response = input("\n  Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1

    # Step 3: Install package
    print_step(3, total_steps, "Installing mini_claude package...")
    if check_package_installed():
        print_success("Package already installed")
    else:
        success, error = install_package()
        if success:
            print_success("Package installed")
        else:
            print_error(f"Failed to install package: {error}")
            print("\n  Try manually:")
            print(f"    pip install -e \"{script_dir / 'mini_claude'}\"")
            return 1

    # Step 4: Create memory directory
    print_step(4, total_steps, "Creating memory directory...")
    memory_dir = create_memory_dir()
    print_success(f"Memory directory: {memory_dir}")

    # Step 5: Create .mcp.json in this directory
    print_step(5, total_steps, "Creating MCP configuration...")
    success, result = create_project_mcp_config(script_dir)
    if success:
        print_success(f"Created {result}")
    else:
        print_error(f"Failed: {result}")

    # Summary
    print("\n" + "=" * 60)
    print("Installation complete!")
    print("=" * 60)

    config = get_mcp_config()
    mcp_json = json.dumps(config, indent=2)

    print("\n" + "-" * 60)
    print("HOW TO USE IN YOUR PROJECTS")
    print("-" * 60)

    print("\nOption 1: Copy .mcp.json to your project (recommended)")
    print("  Copy the .mcp.json file from this directory to your project root.")
    print(f"  Location: {script_dir / '.mcp.json'}")

    print("\nOption 2: Run setup command")
    print("  python install.py --setup /path/to/your/project")
    print("  This creates .mcp.json and copies CLAUDE.md template.")

    print("\nOption 3: Create .mcp.json manually")
    print("  Create a file named .mcp.json in your project root with:")
    print(mcp_json)

    print("\n" + "-" * 60)
    print("AFTER SETUP")
    print("-" * 60)
    print("\n1. Open your project in VSCode")
    print("2. Start Claude Code")
    print("3. Approve the mini-claude MCP server when prompted")
    print("4. Claude should use: session_start(project_path=\"/your/project\")")

    print("\n" + "-" * 60)
    print("38 TOOLS AVAILABLE")
    print("-" * 60)
    print("""
  Session & Memory:
    session_start, memory_remember, memory_recall, memory_forget

  Work Tracking:
    work_log_mistake, work_log_decision, work_pre_edit_check
    work_session_summary, work_save_session

  Safety Guards:
    code_quality_check, loop_record_edit, loop_check_before_edit
    scope_declare, scope_check, scope_expand, scope_status

  Context Protection:
    context_checkpoint_save, context_checkpoint_restore
    context_instruction_add, context_handoff_create
    context_self_check, output_validate_code

  Analysis:
    scout_search, scout_analyze, file_summarize, deps_map
    impact_analyze, convention_add, convention_check
""")

    return 0


def main_with_args():
    """Main entry point with argument handling."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--setup":
        # Setup a specific project
        target_dir = sys.argv[2]

        # Quick check that mini_claude is importable
        if not check_package_installed():
            print("Error: mini_claude package not installed.")
            print("Run 'python install.py' first to install.")
            return 1

        success, error = setup_project(target_dir)
        if success:
            print("\nSetup complete!")
            print("1. Open the project in VSCode")
            print("2. Start Claude Code")
            print("3. Approve the mini-claude MCP server when prompted")
            return 0
        else:
            return 1
    else:
        return main()


if __name__ == "__main__":
    sys.exit(main_with_args())
