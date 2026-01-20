# Mini Claude

A junior AI agent that gives Claude Code **persistent memory** and **mistake tracking** across all your projects.

## The Problem

Claude Code forgets everything between sessions:
- Repeats the same mistakes
- Forgets why things are structured a certain way
- Loses context about project conventions
- Can't learn from past errors

## The Solution

Mini Claude is your junior developer who:
- **Remembers** what you learned across sessions
- **Warns** you about past mistakes before you repeat them
- **Tracks** your work automatically
- **Reminds** you to use the right tools (via hooks)

## Quick Install

```bash
# 1. Clone and enter directory
git clone https://github.com/yourname/mini-claude.git
cd mini-claude

# 2. Install Ollama and the model
ollama pull qwen2.5-coder:7b

# 3. Run the installer
python install.py
```

The installer will:
- Install the mini_claude package
- Configure the MCP server for Claude Code
- Set up hooks that remind Claude to use the tools

**Restart Claude Code** after installation.

## How It Works

### 1. Automatic Reminders (Hooks)

Mini Claude installs hooks that inject reminders into Claude's context:

- **On every prompt** - Reminds Claude about session_start and past mistakes
- **Before editing files** - Warns about past mistakes with that file
- **When commands fail** - Suggests logging the mistake

### 2. Session Memory

Each project gets its own memory. When Claude starts working:

```
mcp__mini-claude__session_start(project_path="/your/project")
```

This loads:
- Past discoveries about the project
- Coding conventions to follow
- **Past mistakes** (shown as warnings!)

### 3. Mistake Tracking

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

## All 18 Tools

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

### Safety Checks
| Tool | What It Does |
|------|--------------|
| `impact_analyze` | Check what depends on a file |
| `convention_check` | Check code against rules |

### Search & Analysis
| Tool | What It Does |
|------|--------------|
| `scout_search` | Search codebase semantically |
| `scout_analyze` | Analyze code with LLM |
| `file_summarize` | Summarize a file |
| `deps_map` | Map dependencies |

### Conventions
| Tool | What It Does |
|------|--------------|
| `convention_add` | Store a coding rule |
| `convention_get` | Get project rules |

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
└───────────────────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) with `qwen2.5-coder:7b`
- Claude Code

## Manual Installation

If you prefer not to use the installer:

### 1. Install the package

```bash
cd mini-claude
python -m venv venv
source venv/bin/activate
pip install -e mini_claude/
```

### 2. Configure MCP Server

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "mini-claude": {
      "command": "/path/to/mini-claude/venv/bin/python",
      "args": ["-m", "mini_claude.server"]
    }
  }
}
```

### 3. Configure Hooks (Optional but recommended)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m mini_claude.hooks.remind prompt 2>/dev/null || echo ''",
            "timeout": 2000
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m mini_claude.hooks.remind edit 2>/dev/null || echo ''",
            "timeout": 1000
          }
        ]
      }
    ]
  }
}
```

## Usage

### First time with a project

```
You: "Start working on this project"
Claude: *calls session_start*
        Loaded 0 memories, 0 conventions.
        No past mistakes recorded.
```

### After you've used it for a while

```
You: "Let's continue working"
Claude: *calls session_start*

        ### Warnings
        - Past mistakes to remember:
          - Forgot to run tests after editing handlers.py
          - Passed None to warnings field in MiniClaudeResponse

        ### Conventions
        - Keep server.py thin (routing only)
        - Methods under 50 lines
```

### When something breaks

```
You: "The tests are failing"
Claude: *calls work_log_mistake*
        Logged: "Tests failing due to missing import"

        This will warn you next session.
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
