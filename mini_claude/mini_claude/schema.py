"""
Mini Claude Response Schema

Every tool response follows this structure to ensure rich communication
back to Claude Code. No silent failures, always context.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class WorkLog(BaseModel):
    """What mini_claude did during this operation."""
    what_i_tried: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    files_examined: int = 0
    time_taken_ms: int = 0


class SearchResult(BaseModel):
    """A single search finding."""
    file: str
    line: Optional[int] = None
    relevance: str = "medium"  # high, medium, low
    summary: str
    snippet: Optional[str] = None


class MiniClaudeResponse(BaseModel):
    """
    The structured response every mini_claude tool returns.

    This is the core of the "junior agent" pattern - rich communication
    that tells Claude not just WHAT was found, but HOW and WHY.
    """
    # Core result
    status: str = "success"  # success, partial, failed, needs_clarification

    # What happened (always provided)
    work_log: WorkLog = Field(default_factory=WorkLog)

    # Communication back to Claude
    confidence: str = "medium"  # high, medium, low
    reasoning: str = ""  # "I chose approach X because..."

    # The actual findings (for search operations)
    findings: list[SearchResult] = Field(default_factory=list)
    connections: Optional[str] = None  # How findings relate to each other

    # Generic data payload for other tools
    data: Optional[Any] = None

    # Proactive collaboration
    questions: list[str] = Field(default_factory=list)  # "Should I also check...?"
    suggestions: list[str] = Field(default_factory=list)  # "I noticed X might be related..."
    warnings: list[str] = Field(default_factory=list)  # "This code has a potential issue..."

    # For Claude to decide next steps
    follow_up_options: list[dict] = Field(default_factory=list)

    def to_formatted_string(self) -> str:
        """Convert response to a readable format for Claude."""
        lines = []

        # Status and confidence
        lines.append(f"## Mini Claude Report")
        lines.append(f"**Status:** {self.status} | **Confidence:** {self.confidence}")
        lines.append("")

        # Reasoning
        if self.reasoning:
            lines.append(f"**Reasoning:** {self.reasoning}")
            lines.append("")

        # Findings
        if self.findings:
            lines.append("### Findings")
            for i, f in enumerate(self.findings, 1):
                loc = f"{f.file}:{f.line}" if f.line else f.file
                lines.append(f"{i}. **[{f.relevance.upper()}]** `{loc}`")
                lines.append(f"   {f.summary}")
                if f.snippet:
                    lines.append(f"   ```")
                    lines.append(f"   {f.snippet}")
                    lines.append(f"   ```")
            lines.append("")

        # Data (for non-search tools)
        if self.data:
            lines.append("### Data")
            if isinstance(self.data, dict):
                for key, value in self.data.items():
                    if isinstance(value, list):
                        lines.append(f"**{key}:**")
                        for item in value[:10]:  # Limit display
                            lines.append(f"  - {item}")
                    elif isinstance(value, dict):
                        lines.append(f"**{key}:** {json.dumps(value, indent=2)}")
                    else:
                        lines.append(f"**{key}:** {value}")
            else:
                lines.append(str(self.data))
            lines.append("")

        # Connections
        if self.connections:
            lines.append(f"### Connections")
            lines.append(self.connections)
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("### Warnings")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        # Suggestions
        if self.suggestions:
            lines.append("### Suggestions")
            for s in self.suggestions:
                lines.append(f"- {s}")
            lines.append("")

        # Questions
        if self.questions:
            lines.append("### Questions for You")
            for q in self.questions:
                lines.append(f"- {q}")
            lines.append("")

        # Work log
        lines.append("### Work Log")
        lines.append(f"- Files examined: {self.work_log.files_examined}")
        lines.append(f"- Time taken: {self.work_log.time_taken_ms}ms")
        if self.work_log.what_i_tried:
            lines.append(f"- Tried: {', '.join(self.work_log.what_i_tried)}")
        if self.work_log.what_failed:
            lines.append(f"- Failed: {', '.join(self.work_log.what_failed)}")

        return "\n".join(lines)


# Need to import json for the data formatting
import json
