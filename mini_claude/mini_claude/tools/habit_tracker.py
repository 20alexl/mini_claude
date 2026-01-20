"""
Habit Tracker - Track tool usage patterns and provide habit formation feedback.

Solves the problem: Claude doesn't develop good habits because there's no feedback loop.

Features:
- Track when Thinker tools are used (or NOT used) before risky work
- Show habit formation metrics
- Gamify good practices
- Provide specific encouragement or warnings based on patterns
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class HabitEvent:
    """Record of a habit-relevant event."""
    timestamp: str
    event_type: str  # "thinker_used", "risky_edit_without_thinking", "loop_avoided", etc.
    context: str  # What was happening (e.g., "editing auth.py", "implementing payment")
    tool_used: Optional[str] = None  # Which tool was used (if any)


class HabitTracker:
    """Track and analyze tool usage habits."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.habit_file = self.state_dir / "habits.json"

    def _load_habits(self) -> Dict:
        """Load habit history."""
        if not self.habit_file.exists():
            return {
                "events": [],
                "stats": {
                    "thinker_before_risky": 0,
                    "risky_without_thinking": 0,
                    "loops_avoided": 0,
                    "loops_hit": 0,
                }
            }

        try:
            with open(self.habit_file) as f:
                return json.load(f)
        except Exception:
            return {"events": [], "stats": {}}

    def _save_habits(self, data: Dict):
        """Save habit history."""
        with open(self.habit_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record_thinker_use(self, tool: str, context: str):
        """Record that a Thinker tool was used."""
        data = self._load_habits()

        event = HabitEvent(
            timestamp=datetime.now().isoformat(),
            event_type="thinker_used",
            context=context,
            tool_used=tool
        )

        data["events"].append(asdict(event))
        data["stats"]["thinker_before_risky"] = data["stats"].get("thinker_before_risky", 0) + 1

        self._save_habits(data)

    def record_risky_edit_without_thinking(self, file_path: str, risk_reason: str):
        """Record that a risky file was edited without using Thinker tools."""
        data = self._load_habits()

        event = HabitEvent(
            timestamp=datetime.now().isoformat(),
            event_type="risky_edit_without_thinking",
            context=f"{file_path} ({risk_reason})"
        )

        data["events"].append(asdict(event))
        data["stats"]["risky_without_thinking"] = data["stats"].get("risky_without_thinking", 0) + 1

        self._save_habits(data)

    def record_loop_avoided(self, file_path: str):
        """Record that a potential loop was avoided (used Thinker after warning)."""
        data = self._load_habits()

        event = HabitEvent(
            timestamp=datetime.now().isoformat(),
            event_type="loop_avoided",
            context=file_path
        )

        data["events"].append(asdict(event))
        data["stats"]["loops_avoided"] = data["stats"].get("loops_avoided", 0) + 1

        self._save_habits(data)

    def record_loop_hit(self, file_path: str, edit_count: int):
        """Record that a loop was actually hit (3+ edits)."""
        data = self._load_habits()

        event = HabitEvent(
            timestamp=datetime.now().isoformat(),
            event_type="loop_hit",
            context=f"{file_path} ({edit_count} edits)"
        )

        data["events"].append(asdict(event))
        data["stats"]["loops_hit"] = data["stats"].get("loops_hit", 0) + 1

        self._save_habits(data)

    def get_habit_stats(self, days: int = 7) -> Dict:
        """Get habit statistics for the last N days."""
        data = self._load_habits()

        # Filter events to last N days
        cutoff = datetime.now() - timedelta(days=days)
        recent_events = [
            e for e in data["events"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]

        # Calculate stats
        thinker_used = len([e for e in recent_events if e["event_type"] == "thinker_used"])
        risky_without = len([e for e in recent_events if e["event_type"] == "risky_edit_without_thinking"])
        loops_avoided = len([e for e in recent_events if e["event_type"] == "loop_avoided"])
        loops_hit = len([e for e in recent_events if e["event_type"] == "loop_hit"])

        # Calculate percentages
        risky_total = thinker_used + risky_without
        think_rate = (thinker_used / risky_total * 100) if risky_total > 0 else 0

        loop_total = loops_avoided + loops_hit
        loop_avoid_rate = (loops_avoided / loop_total * 100) if loop_total > 0 else 0

        return {
            "days": days,
            "thinker_used": thinker_used,
            "risky_without_thinking": risky_without,
            "think_rate": think_rate,
            "loops_avoided": loops_avoided,
            "loops_hit": loops_hit,
            "loop_avoid_rate": loop_avoid_rate,
            "total_stats": data["stats"]
        }

    def get_recent_thinker_usage(self, context_pattern: str, limit: int = 5) -> List[Dict]:
        """
        Get recent Thinker tool usage for a specific context (e.g., "auth", "payment").

        Returns list of recent events matching the pattern.
        """
        data = self._load_habits()

        matching = [
            e for e in data["events"]
            if context_pattern.lower() in e.get("context", "").lower()
        ]

        # Return most recent first
        matching.reverse()
        return matching[:limit]

    def get_habit_feedback(self) -> str:
        """
        Generate encouraging or warning feedback based on habits.

        Returns formatted feedback string for display.
        """
        stats = self.get_habit_stats(days=7)

        lines = []
        lines.append("📊 Your Habits (last 7 days):")
        lines.append("")

        # Thinking before risky work
        think_rate = stats["think_rate"]
        if think_rate >= 80:
            lines.append(f"✅ Excellent! You used Thinker tools {think_rate:.0f}% of the time before risky work")
            lines.append("   Keep building this habit!")
        elif think_rate >= 50:
            lines.append(f"⚠️  You used Thinker tools {think_rate:.0f}% of the time before risky work")
            lines.append("   Goal: 80%+ for better quality")
        elif think_rate > 0:
            lines.append(f"🔴 You only used Thinker tools {think_rate:.0f}% of the time before risky work")
            lines.append("   This is why bugs happen. Try to think before coding!")
        else:
            if stats["risky_without_thinking"] > 0:
                lines.append("🔴 You haven't used Thinker tools at all before risky work")
                lines.append("   Start small: try think_explore on your next architectural task")

        lines.append("")

        # Loop avoidance
        loop_avoid_rate = stats["loop_avoid_rate"]
        if stats["loops_hit"] == 0 and stats["loops_avoided"] > 0:
            lines.append(f"🌟 Perfect! You avoided {stats['loops_avoided']} potential loop(s)")
        elif loop_avoid_rate >= 75:
            lines.append(f"✅ Good loop awareness! {loop_avoid_rate:.0f}% avoided")
        elif stats["loops_hit"] > 0:
            lines.append(f"⚠️  Hit {stats['loops_hit']} loop(s). When stuck, step back and think!")

        return "\n".join(lines)

    def suggest_tool_for_context(self, context: str, risk_reason: str = "") -> Tuple[str, str]:
        """
        Suggest the BEST Thinker tool for a specific context.

        Returns (tool_name, reason) tuple.
        """
        context_lower = context.lower()

        # Authentication/Security work
        if any(kw in context_lower for kw in ["auth", "login", "password", "security", "token", "session"]):
            return ("think_best_practice", "Security is critical - learn the 2026 best practices first")

        # Payment/Financial
        if any(kw in context_lower for kw in ["payment", "billing", "transaction", "money", "price"]):
            return ("think_best_practice", "Financial code requires industry standards - check best practices")

        # Architecture/Design
        if any(kw in context_lower for kw in ["architecture", "design", "refactor", "structure"]):
            return ("think_explore", "Architecture has many valid approaches - explore the solution space")

        # Integration/API work
        if any(kw in context_lower for kw in ["integrate", "api", "endpoint", "webhook"]):
            return ("think_compare", "Multiple integration approaches exist - compare the trade-offs")

        # Performance/Optimization
        if any(kw in context_lower for kw in ["performance", "optimize", "slow", "cache"]):
            return ("think_research", "Performance work needs data - research the bottleneck first")

        # Database/Schema
        if any(kw in context_lower for kw in ["database", "schema", "migration", "sql"]):
            return ("think_challenge", "Schema changes are hard to reverse - challenge your assumptions")

        # Config/Infrastructure
        if "config" in context_lower or "infrastructure" in context_lower:
            return ("think_best_practice", "Config affects everything - check what's standard")

        # Default: explore solution space
        return ("think_explore", "Explore different approaches before picking the first idea")


# Singleton state directory
_state_dir = Path.home() / ".mini_claude"
_habit_tracker = HabitTracker(_state_dir)


def get_habit_tracker() -> HabitTracker:
    """Get the global habit tracker instance."""
    return _habit_tracker


# Public API functions for handlers
def record_thinker_use(tool: str, context: str):
    """Record that a Thinker tool was used."""
    _habit_tracker.record_thinker_use(tool, context)


def record_risky_edit_without_thinking(file_path: str, risk_reason: str):
    """Record that a risky file was edited without thinking."""
    _habit_tracker.record_risky_edit_without_thinking(file_path, risk_reason)


def record_loop_avoided(file_path: str):
    """Record that a loop was avoided."""
    _habit_tracker.record_loop_avoided(file_path)


def record_loop_hit(file_path: str, edit_count: int):
    """Record that a loop was hit."""
    _habit_tracker.record_loop_hit(file_path, edit_count)


def get_habit_stats(days: int = 7) -> Dict:
    """Get habit statistics."""
    return _habit_tracker.get_habit_stats(days)


def get_habit_feedback() -> str:
    """Get habit feedback message."""
    return _habit_tracker.get_habit_feedback()


def suggest_tool_for_context(context: str, risk_reason: str = "") -> Tuple[str, str]:
    """Suggest best Thinker tool for context."""
    return _habit_tracker.suggest_tool_for_context(context, risk_reason)


def get_recent_thinker_usage(context_pattern: str, limit: int = 5) -> List[Dict]:
    """Get recent Thinker usage for context."""
    return _habit_tracker.get_recent_thinker_usage(context_pattern, limit)
