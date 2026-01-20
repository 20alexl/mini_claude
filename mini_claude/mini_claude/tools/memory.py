"""
Memory - Persistent Knowledge Store for Mini Claude

Allows mini_claude to remember:
- Project understanding (structure, patterns, key files)
- Previous discoveries and searches
- Priorities and important notes
- Claude's preferences
"""

import json
import time
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry."""
    content: str
    category: str  # "discovery", "priority", "preference", "note"
    created_at: float = Field(default_factory=time.time)
    source: Optional[str] = None  # What operation created this memory
    relevance: int = 5  # 1-10, higher = more important


class ProjectMemory(BaseModel):
    """Memory about a specific project/directory."""
    project_path: str
    project_name: str

    # Core understanding
    summary: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None

    # Key locations
    key_files: dict[str, str] = Field(default_factory=dict)  # path -> description
    key_directories: dict[str, str] = Field(default_factory=dict)

    # Discoveries and notes
    entries: list[MemoryEntry] = Field(default_factory=list)

    # Search history (for avoiding redundant searches)
    recent_searches: list[dict] = Field(default_factory=list)

    last_updated: float = Field(default_factory=time.time)


class MemoryStore:
    """
    Mini Claude's memory system.

    Persists knowledge across sessions so I don't have to rediscover
    the same things repeatedly.
    """

    def __init__(self, storage_dir: str = "~/.mini_claude"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / "memory.json"

        # In-memory cache
        self._projects: dict[str, ProjectMemory] = {}
        self._global_entries: list[MemoryEntry] = []

        # Load existing memory
        self._load()

    def _load(self):
        """Load memory from disk."""
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())

                for path, proj_data in data.get("projects", {}).items():
                    self._projects[path] = ProjectMemory(**proj_data)

                for entry_data in data.get("global", []):
                    self._global_entries.append(MemoryEntry(**entry_data))

            except Exception:
                pass  # Start fresh if corrupted

    def _save(self):
        """Save memory to disk."""
        data = {
            "projects": {
                path: proj.model_dump()
                for path, proj in self._projects.items()
            },
            "global": [e.model_dump() for e in self._global_entries]
        }
        self.memory_file.write_text(json.dumps(data, indent=2))

    def get_project(self, project_path: str) -> Optional[ProjectMemory]:
        """Get memory for a project, if it exists."""
        return self._projects.get(project_path)

    def remember_project(
        self,
        project_path: str,
        summary: Optional[str] = None,
        language: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> ProjectMemory:
        """Create or update project memory."""
        if project_path not in self._projects:
            project_name = Path(project_path).name
            self._projects[project_path] = ProjectMemory(
                project_path=project_path,
                project_name=project_name,
            )

        proj = self._projects[project_path]

        if summary:
            proj.summary = summary
        if language:
            proj.language = language
        if framework:
            proj.framework = framework

        proj.last_updated = time.time()
        self._save()

        return proj

    def remember_key_file(
        self,
        project_path: str,
        file_path: str,
        description: str,
    ):
        """Remember an important file in a project."""
        proj = self.remember_project(project_path)
        proj.key_files[file_path] = description
        proj.last_updated = time.time()
        self._save()

    def remember_discovery(
        self,
        project_path: str,
        content: str,
        source: Optional[str] = None,
        relevance: int = 5,
    ):
        """Remember something discovered about a project."""
        proj = self.remember_project(project_path)
        proj.entries.append(MemoryEntry(
            content=content,
            category="discovery",
            source=source,
            relevance=relevance,
        ))
        proj.last_updated = time.time()
        self._save()

    def add_priority(
        self,
        content: str,
        project_path: Optional[str] = None,
        relevance: int = 8,
    ):
        """Add a priority note (something important to remember)."""
        entry = MemoryEntry(
            content=content,
            category="priority",
            relevance=relevance,
        )

        if project_path:
            proj = self.remember_project(project_path)
            proj.entries.append(entry)
            proj.last_updated = time.time()
        else:
            self._global_entries.append(entry)

        self._save()

    def log_search(
        self,
        project_path: str,
        query: str,
        results_count: int,
        top_files: list[str],
    ):
        """Log a search to avoid redundant future searches."""
        proj = self.remember_project(project_path)

        # Keep only last 20 searches
        proj.recent_searches = proj.recent_searches[-19:]
        proj.recent_searches.append({
            "query": query,
            "results_count": results_count,
            "top_files": top_files[:5],
            "timestamp": time.time(),
        })

        self._save()

    def recall(
        self,
        project_path: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        Recall what we know.

        Returns a summary of memories, optionally filtered by project or category.
        """
        result = {
            "global_priorities": [],
            "project": None,
        }

        # Global priorities (always include top ones)
        priorities = sorted(
            [e for e in self._global_entries if e.category == "priority"],
            key=lambda x: x.relevance,
            reverse=True,
        )
        result["global_priorities"] = [
            {"content": e.content, "relevance": e.relevance}
            for e in priorities[:5]
        ]

        # Project-specific memories
        if project_path and project_path in self._projects:
            proj = self._projects[project_path]

            entries = proj.entries
            if category:
                entries = [e for e in entries if e.category == category]

            # Sort by relevance
            entries = sorted(entries, key=lambda x: x.relevance, reverse=True)

            result["project"] = {
                "name": proj.project_name,
                "summary": proj.summary,
                "language": proj.language,
                "framework": proj.framework,
                "key_files": proj.key_files,
                "key_directories": proj.key_directories,
                "discoveries": [
                    {"content": e.content, "relevance": e.relevance}
                    for e in entries[:limit]
                ],
                "recent_searches": proj.recent_searches[-5:],
            }

        return result

    def forget_project(self, project_path: str):
        """Clear memory for a project."""
        if project_path in self._projects:
            del self._projects[project_path]
            self._save()

    def clear_all(self):
        """Clear all memory (use with caution)."""
        self._projects = {}
        self._global_entries = []
        self._save()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        total_entries = sum(len(p.entries) for p in self._projects.values())
        total_entries += len(self._global_entries)

        return {
            "projects_tracked": len(self._projects),
            "total_entries": total_entries,
            "global_entries": len(self._global_entries),
            "storage_path": str(self.memory_file),
        }
