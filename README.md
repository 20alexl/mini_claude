# Mini Claude

A junior AI agent that gives Claude Code **persistent memory** and **mistake tracking** across all your projects.

**Now with automatic tool injection!** Tools run automatically - no manual calls needed.

## The Problem

Claude Code forgets everything between sessions:
- Repeats the same mistakes
- Forgets why things are structured a certain way
- Loses context about project conventions
- Gets stuck in loops editing the same file
- Over-refactors beyond the requested scope

## The Solution

Mini Claude is your junior developer who:
- **Remembers** what you learned across sessions
- **Warns** you about past mistakes before you repeat them
- **Tracks** your work and detects loops
- **Guards** scope to prevent over-refactoring
- **Reminds** you to use the right tools (via hooks)

## Quick Install

```bash
# 1. Clone the repository
git clone https://github.com/20alexl/mini_claude.git
cd mini_claude

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install Ollama and the model
# See https://ollama.ai for installation
ollama pull qwen2.5-coder:7b

# 4. Run the installer
python install.py
```

## Setting Up Your Projects

Mini Claude uses a `.mcp.json` file in each project to connect. After installation:

### Option 1: Use the setup command (recommended)

```bash
# From the mini_claude directory, with venv activated:
python install.py --setup /path/to/your/project
```

This creates:
- `.mcp.json` - MCP server configuration
- `CLAUDE.md` - Instructions for Claude (optional)

### Option 2: Copy manually

Copy the `.mcp.json` file from the mini_claude directory to your project root.

### Option 3: Create manually

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mini-claude": {
      "command": "/path/to/mini_claude/venv/bin/python",
      "args": ["-m", "mini_claude.server"]
    }
  }
}
```

**Important:** Replace `/path/to/mini_claude` with the actual path where you cloned this repo.

## After Setup

1. Open your project in VSCode
2. Start Claude Code (Ctrl+Shift+P → "Claude: Open")
3. **Approve the mini-claude MCP server** when prompted
4. Ask Claude to run: `session_start(project_path="/your/project")`

## How It Works

### 1. Session Memory

Each project gets its own memory. When Claude starts working:

```
mcp__mini-claude__session_start(project_path="/your/project")
```

This loads:
- Past discoveries about the project
- Coding conventions to follow
- **Past mistakes** (shown as warnings!)

### 2. Mistake Tracking

When something breaks:

```
mcp__mini-claude__work_log_mistake(
  description="Forgot to handle empty input",
  file_path="handlers.py",
  how_to_avoid="Always validate input first"
)
```

Next session, Claude sees:
```
### Warnings
- Past mistakes to remember:
  - Forgot to handle empty input - Fix: Always validate input first
```

### 3. Loop Detection

Mini Claude tracks how many times each file is edited:
- **2 edits**: Warning shown
- **3+ edits**: Loud warning - "Try a different approach"

### 4. Scope Guard

Declare what files Claude is allowed to edit:

```
mcp__mini-claude__scope_declare(
  task_description="Fix login bug",
  in_scope_files=["auth.py", "login.py"]
)
```

If Claude tries to edit other files, it gets a warning.

## All 52 Tools

### Session & Memory
| Tool | What It Does |
|------|--------------|
| `session_start` | **Start here** - loads memories + warnings |
| `memory_remember` | Store something important |
| `memory_recall` | Get what Mini Claude remembers |
| `memory_forget` | Clear project memories |

### Work Tracking
| Tool | What It Does |
|------|--------------|
| `work_log_mistake` | **Log when things break** |
| `work_log_decision` | Log why you did something |
| `work_pre_edit_check` | Check context before editing |
| `work_session_summary` | See what happened this session |
| `work_save_session` | Persist session to memory |

### Safety Guards
| Tool | What It Does |
|------|--------------|
| `code_quality_check` | Check code for issues before writing |
| `loop_record_edit` | Record file edit for loop detection |
| `loop_check_before_edit` | Check if editing might cause loop |
| `loop_record_test` | Record test results |
| `loop_status` | Get loop detection status |
| `scope_declare` | Declare files in scope for task |
| `scope_check` | Check if file is in scope |
| `scope_expand` | Add files to scope |
| `scope_status` | Get scope status |
| `scope_clear` | Clear scope when done |

### Context Protection
| Tool | What It Does |
|------|--------------|
| `context_checkpoint_save` | Save task state |
| `context_checkpoint_restore` | Restore task state |
| `context_checkpoint_list` | List saved checkpoints |
| `context_instruction_add` | Add critical instruction |
| `context_instruction_reinforce` | Get instruction reminders |
| `context_claim_completion` | Claim task complete |
| `context_self_check` | Verify claimed work |
| `context_handoff_create` | Create session handoff |
| `context_handoff_get` | Get previous handoff |

### Output Validation
| Tool | What It Does |
|------|--------------|
| `output_validate_code` | Detect silent failure patterns |
| `output_validate_result` | Check outputs for fakes |

### Search & Analysis
| Tool | What It Does |
|------|--------------|
| `scout_search` | Search codebase semantically |
| `scout_analyze` | Analyze code with LLM |
| `file_summarize` | Summarize a file |
| `deps_map` | Map dependencies |
| `impact_analyze` | Check what depends on a file |

### Conventions
| Tool | What It Does |
|------|--------------|
| `convention_add` | Store a coding rule |
| `convention_get` | Get project rules |
| `convention_check` | Check code against rules |

### Testing & Git
| Tool | What It Does |
|------|--------------|
| `test_run` | Auto-detect and run tests |
| `test_can_claim_completion` | Check if tests allow completion |
| `git_generate_commit_message` | Generate commit from work logs |
| `git_auto_commit` | Auto-commit with context |

### Momentum Tracking
| Tool | What It Does |
|------|--------------|
| `momentum_start_task` | Start tracking multi-step task |
| `momentum_complete_step` | Mark step complete |
| `momentum_check` | Check if momentum maintained |
| `momentum_finish_task` | Mark task complete |
| `momentum_status` | Get momentum status |

### Thinking Partner (NEW!)
| Tool | What It Does |
|------|--------------|
| `think_research` | Deep research (web + codebase + LLM) |
| `think_compare` | Compare options with pros/cons |
| `think_challenge` | Challenge assumptions (devil's advocate) |
| `think_explore` | Explore solution space |
| `think_best_practice` | Find current best practices (2026) |

### Status
| Tool | What It Does |
|------|--------------|
| `mini_claude_status` | Health check |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Claude Code                         │
│            (The main AI assistant)                  │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐           ┌─────────────────┐
│  MCP Server   │           │     Hooks       │
│ (Mini Claude) │           │  (Reminders)    │
└───────┬───────┘           └────────┬────────┘
        │                            │
        ▼                            ▼
┌───────────────────────────────────────────────────┐
│              ~/.mini_claude/                       │
│  memory.json - Per-project memories               │
│  conventions.json - Per-project rules             │
│  hook_state.json - Enforcement tracking           │
│  loop_detector.json - Edit tracking               │
│  scope_guard.json - Scope tracking                │
└───────────────────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) with any coding model
- Claude Code (VSCode extension)

## Configuration

### Choosing a Different Model

By default, Mini Claude uses `qwen2.5-coder:7b`. You can use any Ollama model by setting environment variables:

```bash
# Use a different model
export MINI_CLAUDE_MODEL="codellama:7b"

# Or use a larger model for better results
export MINI_CLAUDE_MODEL="qwen2.5-coder:14b"

# Custom Ollama URL (if not localhost)
export MINI_CLAUDE_OLLAMA_URL="http://192.168.1.100:11434"
```

**Recommended models:**
- `qwen2.5-coder:7b` (default) - Good balance of speed and quality
- `qwen2.5-coder:14b` - Better quality, slower
- `codellama:7b` - Alternative coding model
- `deepseek-coder:6.7b` - Another good option

To make the change permanent, add the export to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.).

## Troubleshooting

### MCP server not connecting

1. Check `.mcp.json` exists in your project root
2. Check the python path in `.mcp.json` is correct
3. Restart Claude Code (reload VSCode window)
4. Look for "Approve MCP server" prompt

### Ollama not running

```bash
ollama serve  # Start Ollama
ollama pull qwen2.5-coder:7b  # Pull the model
```

### Package not found

```bash
cd /path/to/mini_claude
source venv/bin/activate
pip install -e mini_claude/
```

## Why Local LLM?

- **Privacy** - Code never leaves your machine
- **Speed** - No network latency
- **Cost** - No API fees
- **Reliability** - Works offline

The 7B model is sufficient for search ranking, file summaries, and pattern recognition.

## Contributing

PRs welcome! The goal is to make Claude Code more reliable by helping it remember and learn.

## License

MIT
