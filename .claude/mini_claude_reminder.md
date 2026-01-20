<mini-claude-reminder>
You have a junior dev (Mini Claude) with persistent memory. USE HIM.

BEFORE editing handlers.py, server.py, tool_definitions.py, or tools/*.py:
  mcp__mini-claude__work_pre_edit_check(file_path="<file>")

WHEN something breaks or tests fail:
  mcp__mini-claude__work_log_mistake(description="what went wrong", file_path="<file>")

If you haven't called session_start this session, do it NOW:
  mcp__mini-claude__session_start(project_path="/media/alex/New Volume/Code/mini_cluade")
</mini-claude-reminder>
