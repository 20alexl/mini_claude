# Mini Claude

A junior agent for Claude Code, powered by a local LLM (Ollama).

Mini Claude provides persistent memory, intelligent code search, and analysis capabilities that help Claude Code work more effectively.

## Features

- **Scout (Search)** - Find code using literal and semantic search
- **Memory** - Remember discoveries, priorities, and project context
- **File Summarizer** - Quick understanding of what files do
- **Dependency Mapper** - Map imports and reverse dependencies
- **Convention Tracker** - Remember and enforce project coding rules
- **Code Analyzer** - Analyze code snippets with LLM

## Requirements

- Python 3.10+
- Ollama running locally with `qwen2.5-coder:7b` model
- Claude Code

## Setup

1. Install Ollama and pull the model:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

2. Create a virtual environment and install:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -e .
   ```

3. Add to your `.mcp.json`:
   ```json
   {
     "mcpServers": {
       "mini-claude": {
         "command": "/path/to/venv/bin/python",
         "args": ["-m", "mini_claude.server"],
         "env": {}
       }
     }
   }
   ```

4. Restart Claude Code

## Available Tools (11)

| Tool | Description |
|------|-------------|
| `mini_claude_status` | Check health and see memory stats |
| `scout_search` | Search for code in a directory |
| `scout_analyze` | Analyze a code snippet |
| `memory_remember` | Store a discovery or priority |
| `memory_recall` | Retrieve stored memories |
| `memory_forget` | Clear memories for a project |
| `file_summarize` | Get quick/detailed file summary |
| `deps_map` | Map file dependencies |
| `convention_add` | Store a project coding convention |
| `convention_get` | Retrieve project conventions |
| `convention_check` | Check code against conventions |

## Architecture

```
mini_claude/
├── server.py          # MCP server entry point
├── llm.py             # Ollama client
├── schema.py          # Response schemas
└── tools/
    ├── scout.py       # Search engine
    ├── memory.py      # Persistent memory
    ├── summarizer.py  # File summarization
    ├── dependencies.py # Dependency mapping
    └── conventions.py # Coding rules
```

## Storage

Mini Claude stores data in `~/.mini_claude/`:
- `memory.json` - Discoveries, priorities, search history
- `conventions.json` - Project coding rules

## Testing

Run the test suite:
```bash
python test_mini_claude.py
```
