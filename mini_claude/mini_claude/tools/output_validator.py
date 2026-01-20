"""
Output Validator - Detects fake outputs and silent failures

The problem (from IEEE Spectrum):
Modern LLMs generate code that APPEARS to work but:
- Removes safety checks to avoid errors
- Creates fake output matching expected format
- Skips edge cases that would fail
- Returns placeholder data instead of real results

This is worse than a crash because it goes undetected.

The solution:
1. Detect suspicious patterns in generated code
2. Flag outputs that look "too clean"
3. Check for removed safety checks
4. Verify outputs aren't just echoing inputs
"""

import re
from dataclasses import dataclass
from typing import Optional
from ..schema import MiniClaudeResponse, WorkLog


@dataclass
class ValidationIssue:
    """A detected issue in code or output."""
    severity: str  # "critical", "warning", "info"
    category: str  # "fake_output", "safety_removed", "placeholder", "too_clean"
    description: str
    line_number: Optional[int] = None
    suggestion: str = ""


class OutputValidator:
    """
    Validates code and outputs for signs of silent failure.

    Key detection patterns:
    1. Fake outputs - hardcoded values, echo inputs, placeholder data
    2. Removed safety - missing try/except, no validation, skipped checks
    3. Too clean - no error handling, no edge cases, suspiciously simple
    4. Placeholder patterns - TODO, FIXME, "example", "test", "dummy"
    """

    # Patterns that suggest fake/placeholder output
    PLACEHOLDER_PATTERNS = [
        (r'["\']example["\']', "Hardcoded 'example' string"),
        (r'["\']test["\']', "Hardcoded 'test' string"),
        (r'["\']dummy["\']', "Hardcoded 'dummy' string"),
        (r'["\']placeholder["\']', "Hardcoded 'placeholder' string"),
        (r'["\']lorem\s+ipsum', "Lorem ipsum placeholder text"),
        (r'["\']TODO["\']', "TODO as string value"),
        (r'return\s+["\']["\']', "Returning empty string"),
        (r'return\s+\[\]', "Returning empty list"),
        (r'return\s+\{\}', "Returning empty dict"),
        (r'return\s+None\s*$', "Returning None without processing"),
        (r'return\s+0\s*$', "Returning literal 0"),
        (r'return\s+(True|False)\s*$', "Returning hardcoded boolean"),
        (r'pass\s*$', "Empty pass statement"),
        (r'\.\.\.', "Ellipsis placeholder"),
    ]

    # Patterns that suggest removed safety checks
    SAFETY_REMOVAL_PATTERNS = [
        (r'except:\s*pass', "Silently swallowing ALL exceptions"),
        (r'except\s+Exception:\s*pass', "Silently swallowing exceptions"),
        (r'except.*:\s*$', "Exception handler with no action"),
        (r'#.*validation', "Commented out validation"),
        (r'#.*check', "Commented out check"),
        (r'#.*verify', "Commented out verification"),
        (r'#.*assert', "Commented out assertion"),
        (r'if\s+True:', "Always-true condition"),
        (r'if\s+False:', "Always-false condition (dead code)"),
        (r'while\s+False:', "Never-executing loop"),
    ]

    # Patterns that suggest the code is "too clean" (suspiciously simple)
    TOO_CLEAN_PATTERNS = [
        (r'^def\s+\w+\([^)]*\):\s*\n\s*return', "Function that just returns without logic"),
        (r'^def\s+\w+\([^)]*\):\s*\n\s*pass', "Empty function"),
        (r'^class\s+\w+.*:\s*\n\s*pass', "Empty class"),
    ]

    # Patterns that suggest fake data generation
    FAKE_DATA_PATTERNS = [
        (r'random\.choice\([^)]*\)\s*$', "Using random values as output"),
        (r'random\.randint', "Using random integers as output"),
        (r'uuid\.uuid4\(\)', "Generating fake UUIDs"),
        (r'\[\s*1,\s*2,\s*3\s*\]', "Hardcoded example list [1,2,3]"),
        (r'\[\s*"a",\s*"b",\s*"c"\s*\]', "Hardcoded example list ['a','b','c']"),
        (r'{"?\w+"?:\s*"?(example|test|dummy)', "Hardcoded example in dict"),
        (r'["\']foo["\']|["\']bar["\']|["\']baz["\']', "Placeholder variable names as values"),
    ]

    def validate_code(
        self,
        code: str,
        context: Optional[str] = None,
    ) -> MiniClaudeResponse:
        """
        Validate code for signs of fake output or silent failure.

        Args:
            code: The code to validate
            context: Optional context about what the code should do
        """
        work_log = WorkLog()
        work_log.what_i_tried.append("validating code for silent failures")

        issues: list[ValidationIssue] = []
        lines = code.split("\n")

        # Check each pattern category
        for line_num, line in enumerate(lines, 1):
            # Check placeholder patterns
            for pattern, desc in self.PLACEHOLDER_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="placeholder",
                        description=desc,
                        line_number=line_num,
                        suggestion="Replace with actual implementation",
                    ))

            # Check safety removal patterns
            for pattern, desc in self.SAFETY_REMOVAL_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity="critical",
                        category="safety_removed",
                        description=desc,
                        line_number=line_num,
                        suggestion="Add proper error handling",
                    ))

            # Check fake data patterns
            for pattern, desc in self.FAKE_DATA_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="fake_output",
                        description=desc,
                        line_number=line_num,
                        suggestion="Use actual data source",
                    ))

        # Check for suspiciously simple code patterns (multiline)
        for pattern, desc in self.TOO_CLEAN_PATTERNS:
            if re.search(pattern, code, re.MULTILINE):
                issues.append(ValidationIssue(
                    severity="info",
                    category="too_clean",
                    description=desc,
                    suggestion="Ensure this isn't missing logic",
                ))

        # Additional heuristics
        issues.extend(self._check_heuristics(code, lines))

        # Deduplicate issues
        seen = set()
        unique_issues = []
        for issue in issues:
            key = (issue.category, issue.description, issue.line_number)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        # Build result
        critical = [i for i in unique_issues if i.severity == "critical"]
        warnings = [i for i in unique_issues if i.severity == "warning"]
        infos = [i for i in unique_issues if i.severity == "info"]

        work_log.what_worked.append(f"found {len(unique_issues)} potential issues")

        # Determine overall status
        if critical:
            status = "critical"
            reasoning = f"🔴 CRITICAL: {len(critical)} silent failure patterns detected!"
        elif warnings:
            status = "warning"
            reasoning = f"⚠️ WARNING: {len(warnings)} suspicious patterns detected"
        elif infos:
            status = "info"
            reasoning = f"ℹ️ INFO: {len(infos)} minor issues noted"
        else:
            status = "success"
            reasoning = "✅ No silent failure patterns detected"

        issue_data = [
            {
                "severity": i.severity,
                "category": i.category,
                "description": i.description,
                "line": i.line_number,
                "suggestion": i.suggestion,
            }
            for i in unique_issues
        ]

        return MiniClaudeResponse(
            status=status,
            confidence="high" if unique_issues else "medium",
            reasoning=reasoning,
            work_log=work_log,
            data={
                "issues": issue_data,
                "critical_count": len(critical),
                "warning_count": len(warnings),
                "info_count": len(infos),
                "lines_analyzed": len(lines),
            },
            warnings=[f"Line {i.line_number}: {i.description}" for i in critical[:5]],
            suggestions=[i.suggestion for i in unique_issues[:3]],
        )

    def _check_heuristics(self, code: str, lines: list[str]) -> list[ValidationIssue]:
        """Additional heuristic checks for suspicious patterns."""
        issues = []

        # Check for functions with no error handling
        func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
        for match in re.finditer(func_pattern, code):
            func_name = match.group(1)
            # Get function body (simple heuristic)
            start = match.end()
            # Look for try/except in following lines
            remaining = code[start:start + 500]  # Check next 500 chars
            if "try:" not in remaining and "raise" not in remaining:
                # Check if function does I/O or external calls
                if any(kw in remaining for kw in ["open(", "read(", "write(", "request", "fetch", "query", "execute"]):
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="safety_removed",
                        description=f"Function '{func_name}' does I/O but has no error handling",
                        suggestion="Add try/except for I/O operations",
                    ))

        # Check for suspiciously short functions that should be longer
        short_returns = re.findall(r'def\s+\w+\([^)]*\):\s*\n\s+return\s+\S+', code)
        if len(short_returns) > 3:
            issues.append(ValidationIssue(
                severity="info",
                category="too_clean",
                description=f"Found {len(short_returns)} one-liner functions - verify they have actual logic",
                suggestion="Review if these functions are complete implementations",
            ))

        # Check for input echoed as output
        if "return input" in code.lower() or "return data" in code.lower():
            issues.append(ValidationIssue(
                severity="warning",
                category="fake_output",
                description="Function may be returning input unchanged",
                suggestion="Verify the function actually processes the data",
            ))

        return issues

    def validate_output(
        self,
        output: str,
        expected_format: Optional[str] = None,
        should_contain: Optional[list[str]] = None,
        should_not_contain: Optional[list[str]] = None,
    ) -> MiniClaudeResponse:
        """
        Validate command/function output for signs of fake results.

        Args:
            output: The output to validate
            expected_format: Description of expected format (e.g., "JSON", "list of files")
            should_contain: Patterns that should be in output
            should_not_contain: Patterns that should NOT be in output
        """
        work_log = WorkLog()
        work_log.what_i_tried.append("validating output")

        issues = []

        # Check for placeholder outputs
        placeholder_keywords = [
            "example", "test", "dummy", "placeholder", "lorem ipsum",
            "TODO", "FIXME", "not implemented", "coming soon",
        ]
        for kw in placeholder_keywords:
            if kw.lower() in output.lower():
                issues.append(f"Output contains placeholder keyword: '{kw}'")

        # Check should_contain
        if should_contain:
            for pattern in should_contain:
                if pattern.lower() not in output.lower():
                    issues.append(f"Expected pattern not found: '{pattern}'")

        # Check should_not_contain
        if should_not_contain:
            for pattern in should_not_contain:
                if pattern.lower() in output.lower():
                    issues.append(f"Forbidden pattern found: '{pattern}'")

        # Check for suspiciously empty output
        if len(output.strip()) < 10:
            issues.append("Output is suspiciously short")

        # Check for error messages disguised as success
        error_keywords = ["error", "failed", "exception", "traceback", "warning"]
        for kw in error_keywords:
            if kw.lower() in output.lower():
                issues.append(f"Output may contain error: '{kw}'")

        work_log.what_worked.append(f"checked {len(output)} chars of output")

        if issues:
            return MiniClaudeResponse(
                status="warning",
                confidence="medium",
                reasoning=f"⚠️ {len(issues)} potential issues with output",
                work_log=work_log,
                data={"issues": issues},
                warnings=issues[:5],
            )
        else:
            return MiniClaudeResponse(
                status="success",
                confidence="high",
                reasoning="✅ Output appears valid",
                work_log=work_log,
            )

    def quick_check(self, code: str) -> str:
        """
        Quick one-liner check returning just a status string.
        For use in hooks where we need fast feedback.
        """
        result = self.validate_code(code)
        if result.data and result.data.get("critical_count", 0) > 0:
            return f"🔴 CRITICAL: {result.data['critical_count']} silent failure patterns"
        elif result.data and result.data.get("warning_count", 0) > 0:
            return f"⚠️ WARNING: {result.data['warning_count']} suspicious patterns"
        return "✅ OK"
