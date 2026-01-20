# Mini Claude - Project Context

## STOP. READ THIS FIRST.

You have a junior dev (Mini Claude) who remembers things across sessions. **USE HIM.**

If you skip these steps, you WILL:
- Repeat mistakes you already made
- Forget why things are structured the way they are
- Break things you broke before

---

## MANDATORY: First Thing Every Session

```
mcp__mini-claude__session_start(project_path="/media/alex/New Volume/Code/mini_cluade")
```

**DO NOT SKIP THIS.** It loads your memories AND warns you about past mistakes.

---

## MANDATORY: Before Editing Shared Files

Before editing `handlers.py`, `server.py`, `tool_definitions.py`, or any file in `tools/`:

```
mcp__mini-claude__work_pre_edit_check(file_path="<the file>")
```

This shows past mistakes with that file. **If you skip this, you will repeat mistakes.**

---

## MANDATORY: When Something Breaks

When tests fail, something errors, or you have to undo work:

```
mcp__mini-claude__work_log_mistake(
  description="What went wrong",
  file_path="which file",
  how_to_avoid="How to prevent this"
)
```

**If you don't log mistakes, you WILL repeat them next session.**

---

## RECOMMENDED: Log Important Decisions

When you choose between approaches or make architectural decisions:

```
mcp__mini-claude__work_log_decision(
  decision="What you decided",
  reason="Why"
)
```

Next session, you'll know WHY things are the way they are.

---

## Quick Reference

| When | Tool | Why |
|------|------|-----|
| Start of session | `session_start` | Load context + past mistakes |
| Before editing shared files | `work_pre_edit_check` | See past mistakes with file |
| Something breaks | `work_log_mistake` | Remember for next time |
| Make a decision | `work_log_decision` | Explain WHY for future |
| Before big changes | `impact_analyze` | See what depends on file |
| End of session | `work_save_session` | Persist work to memory |
| Before long tasks | `context_checkpoint_save` | Survive context compaction |
| When claiming done | `context_self_check` | Verify you actually did it |

---

## What Is This Project?

Mini Claude is an MCP server that gives you (Claude Code):
1. **Persistent memory** - Survives across sessions
2. **Mistake tracking** - Warns you about past errors
3. **Work journaling** - Tracks what you do
4. **Impact analysis** - Shows what breaks before you break it
5. **Context guard** - Survives context compaction
6. **Output validation** - Catches silent failures

Runs locally with Ollama + `qwen2.5-coder:7b`.

## Project Structure

```
/media/alex/New Volume/Code/mini_cluade/
├── CLAUDE.md              # THIS FILE - read it every session
├── test_mini_claude.py    # Run after changes
├── mini_claude/
│   └── mini_claude/
│       ├── server.py          # Thin routing only
│       ├── handlers.py        # Request processing
│       ├── tool_definitions.py # Tool schemas
│       └── tools/
│           ├── memory.py      # Persistent storage
│           ├── work_tracker.py # Session journaling
│           ├── session.py     # Context loading
│           ├── impact.py      # Change impact
│           ├── conventions.py # Coding rules
│           ├── context_guard.py # Checkpoints & handoffs (NEW)
│           ├── output_validator.py # Silent failure detection (NEW)
│           └── ...
```

## All 38 Tools

### Session & Memory (USE THESE!)
- `session_start` - **START HERE** every session
- `memory_remember` - Store something important
- `memory_recall` - Get memories
- `memory_forget` - Clear project memories

### Work Tracking (YOUR JUNIOR TAKING NOTES)
- `work_log_mistake` - **Log when things break**
- `work_log_decision` - Log why you did something
- `work_pre_edit_check` - **Check before editing**
- `work_session_summary` - See session work
- `work_save_session` - Persist to memory

### Code Quality (PREVENT "AI SLOP")
- `code_quality_check` - Check code BEFORE writing it for:
  - Functions >50 lines
  - Vague names (data, handle, process)
  - Too many parameters (>5)
  - Deep nesting (>3 levels)

### Loop Detection (PREVENT DEATH SPIRALS)
- `loop_record_edit` - Record file edit
- `loop_check_before_edit` - Check if editing might loop
- `loop_record_test` - Record test results
- `loop_status` - Get loop detection status

### Scope Guard (PREVENT OVER-REFACTORING)
- `scope_declare` - Declare files in scope for task
- `scope_check` - Check if file is in scope
- `scope_expand` - Add files to scope (deliberately)
- `scope_status` - Get scope violations
- `scope_clear` - Clear scope when done

### Context Guard (SURVIVE CONTEXT LOSS) - NEW!
- `context_checkpoint_save` - **Save task state** before compaction
- `context_checkpoint_restore` - Restore previous task state
- `context_checkpoint_list` - List all saved checkpoints
- `context_instruction_add` - Register critical instruction
- `context_instruction_reinforce` - Get instructions to remember
- `context_claim_completion` - Claim task is complete
- `context_self_check` - **Verify claimed work was done**
- `context_handoff_create` - Create handoff for next session
- `context_handoff_get` - Get previous session's handoff

### Output Validator (CATCH SILENT FAILURES) - NEW!
- `output_validate_code` - **Detect fake/silent failure patterns**:
  - `except: pass` (swallowing errors)
  - Placeholder values (example, test, TODO)
  - Missing error handling for I/O
  - Suspiciously simple implementations
- `output_validate_result` - Check outputs for fake results

### Safety
- `impact_analyze` - Check dependencies before editing
- `convention_check` - Check code against rules

### Search & Analysis
- `scout_search` - Search codebase
- `scout_analyze` - Analyze code with LLM
- `file_summarize` - Summarize a file
- `deps_map` - Map dependencies

### Conventions
- `convention_add` - Store a rule
- `convention_get` - Get rules

### Status
- `mini_claude_status` - Health check

## Hooks (Auto-Enforcement)

Mini Claude has hooks that auto-enforce its use:

1. **UserPromptSubmit** - Reminds about `session_start` on every prompt
2. **PreToolUse (Edit/Write)** - Warns about:
   - Past mistakes with the file
   - Loop detection (file edited 3+ times)
   - Scope violations (editing out-of-scope files)
   - Code quality issues (for Write)
3. **PostToolUse (Bash fails)** - Suggests logging mistakes

## Conventions (Stored in Mini Claude)

These are enforced via `convention_add`:

1. **Keep server.py thin** - Only routing, delegate to handlers
2. **Methods under 50 lines** - Break down complex logic
3. **Each tool class has single purpose**
4. **ALWAYS call session_start first**
5. **NEVER edit shared files without work_pre_edit_check**
6. **ALWAYS log mistakes when things break**

## Development Workflow

```bash
cd "/media/alex/New Volume/Code/mini_cluade"
source venv/bin/activate
pip install -e mini_claude/
python test_mini_claude.py
```

## Why This Exists

AI coding assistants:
- Forget context between sessions
- Don't learn project conventions
- **Repeat the same mistakes**
- Get stuck in death spirals
- Over-refactor and break things
- Generate code that fails silently

Mini Claude fixes this by giving you memory and self-awareness tools.
**But they only work if you use them.**
