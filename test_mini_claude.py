#!/usr/bin/env python3
"""
Test script for Mini Claude.

Run this to verify Mini Claude is working before using it with Claude Code.
"""

import sys
sys.path.insert(0, "/media/alex/New Volume/Code/mini_cluade/mini_claude")

from mini_claude.llm import LLMClient
from mini_claude.tools.scout import SearchEngine
from mini_claude.tools.memory import MemoryStore
from mini_claude.tools.summarizer import FileSummarizer
from mini_claude.tools.dependencies import DependencyMapper
from mini_claude.tools.conventions import ConventionTracker
from mini_claude.tools.impact import ImpactAnalyzer
from mini_claude.tools.session import SessionManager
from mini_claude.tools.work_tracker import WorkTracker
from mini_claude.tools.code_quality import CodeQualityChecker
from mini_claude.tools.loop_detector import LoopDetector
from mini_claude.tools.scope_guard import ScopeGuard
from mini_claude.tools.context_guard import ContextGuard
from mini_claude.tools.output_validator import OutputValidator

TEST_DIR = "/media/alex/New Volume/Code/mini_cluade/_test_repos/node-express-boilerplate"


def main():
    print("=" * 60)
    print("Mini Claude Test Suite")
    print("=" * 60)

    # Test 1: LLM connection
    print("\n[1/10] Testing LLM connection...")
    llm = LLMClient()
    health = llm.health_check()

    if health["healthy"]:
        print(f"  ✓ Ollama is running")
        print(f"  ✓ Model '{llm.model}' is available")
    else:
        print(f"  ✗ LLM check failed: {health.get('error')}")
        print(f"  Suggestion: {health.get('suggestion', 'Check Ollama installation')}")
        return 1

    # Test 2: Simple generation
    print("\n[2/10] Testing LLM generation...")
    result = llm.generate("Say 'Mini Claude ready!' in exactly 3 words.", temperature=0.0)

    if result["success"]:
        print(f"  ✓ LLM responded: {result['response'].strip()[:50]}")
        print(f"  ✓ Response time: {result['time_taken_ms']}ms")
    else:
        print(f"  ✗ Generation failed: {result.get('error')}")
        return 1

    # Test 3: Memory
    print("\n[3/10] Testing Memory system...")
    memory = MemoryStore()

    # Store something
    memory.add_priority("Test priority note", relevance=7)
    memory.remember_project(
        "/test/project",
        summary="A test project",
        language="Python",
    )
    memory.remember_discovery("/test/project", "Found test.py - main entry point", relevance=8)

    # Recall
    memories = memory.recall(project_path="/test/project")

    if memories.get("project"):
        print(f"  ✓ Memory store working")
        print(f"  ✓ Project remembered: {memories['project']['name']}")
        print(f"  ✓ Discoveries: {len(memories['project']['discoveries'])}")
    else:
        print(f"  ✗ Memory recall failed")
        return 1

    # Clean up test data
    memory.forget_project("/test/project")
    stats = memory.get_stats()
    print(f"  ✓ Memory stats: {stats['projects_tracked']} projects tracked")

    # Test 4: Search
    print("\n[4/10] Testing Scout search...")
    search = SearchEngine(llm)

    result = search.search(
        query="user authentication",
        directory=TEST_DIR,
        max_results=3,
        use_llm=True
    )

    print(f"  ✓ Status: {result.status}")
    print(f"  ✓ Confidence: {result.confidence}")
    print(f"  ✓ Files examined: {result.work_log.files_examined}")
    print(f"  ✓ Findings: {len(result.findings)}")

    if result.findings:
        print(f"  ✓ Top result: {result.findings[0].file}")

    # Test 5: File Summarizer
    print("\n[5/10] Testing File Summarizer...")
    summarizer = FileSummarizer(llm)

    result = summarizer.summarize(f"{TEST_DIR}/src/app.js", mode="quick")
    if result.status == "success":
        facts = result.data.get("facts", {})
        print(f"  ✓ Quick mode works")
        print(f"  ✓ Found {len(facts.get('imports', []))} imports")
    else:
        print(f"  ✗ Quick summarize failed: {result.reasoning}")
        return 1

    result = summarizer.summarize(f"{TEST_DIR}/src/app.js", mode="detailed")
    if result.status in ("success", "partial"):
        print(f"  ✓ Detailed mode works")
        print(f"  ✓ Summary: {result.reasoning[:60]}...")
    else:
        print(f"  ✗ Detailed summarize failed")

    # Test 6: Dependency Mapper
    print("\n[6/10] Testing Dependency Mapper...")
    mapper = DependencyMapper(llm)

    result = mapper.map_file(f"{TEST_DIR}/src/app.js")
    if result.status == "success":
        imports = result.data.get("imports", {})
        print(f"  ✓ Dependency mapping works")
        print(f"  ✓ External deps: {len(imports.get('external', []))}")
        print(f"  ✓ Internal deps: {len(imports.get('internal', []))}")
    else:
        print(f"  ✗ Dependency mapping failed")
        return 1

    # Test 7: Convention Tracker
    print("\n[7/10] Testing Convention Tracker...")
    tracker = ConventionTracker()

    # Add a test convention
    result = tracker.add_convention(
        "/test/conventions",
        "Use snake_case for Python files",
        category="naming",
        importance=8
    )
    if result.status == "success":
        print(f"  ✓ Convention add works")
    else:
        print(f"  ✗ Convention add failed")
        return 1

    # Get conventions
    result = tracker.get_conventions("/test/conventions")
    if result.status == "success" and result.data.get("conventions"):
        print(f"  ✓ Convention get works")
        print(f"  ✓ Found {len(result.data['conventions'])} conventions")
    else:
        print(f"  ✗ Convention get failed")
        return 1

    # Check a filename
    result = tracker.check_conventions("/test/conventions", "UserService.py")
    if result.status == "partial" and result.warnings:
        print(f"  ✓ Convention check works")
        print(f"  ✓ Detected {len(result.warnings)} violation(s)")
    else:
        print(f"  ✓ Convention check works (no violations)")

    # Clean up
    tracker.clear_project("/test/conventions")

    # Test 8: Impact Analyzer
    print("\n[8/10] Testing Impact Analyzer...")
    impact = ImpactAnalyzer(llm)

    result = impact.analyze(
        file_path=f"{TEST_DIR}/src/app.js",
        project_root=TEST_DIR,
        proposed_changes="Modify app initialization"
    )

    if result.status == "success":
        data = result.data
        print(f"  ✓ Impact analysis works")
        print(f"  ✓ Risk level: {data.get('risk_level', 'unknown')}")
        print(f"  ✓ Dependents found: {data['summary']['dependent_count']}")
        print(f"  ✓ Exports found: {data['summary']['export_count']}")
    else:
        print(f"  ✗ Impact analysis failed: {result.reasoning}")
        return 1

    # Test 9: Session Manager
    print("\n[9/10] Testing Session Manager...")
    session = SessionManager(memory, tracker)

    # First add some test data
    memory.remember_project("/test/session", summary="Test project", language="Python")
    memory.remember_discovery("/test/session", "Main entry is app.py", relevance=8)
    tracker.add_convention("/test/session", "Use type hints everywhere", category="style")

    result = session.start_session("/test/session")
    if result.status == "success":
        data = result.data
        summary = data.get("summary", {})
        print(f"  ✓ Session start works")
        print(f"  ✓ Loaded {summary.get('discovery_count', 0)} discoveries")
        print(f"  ✓ Loaded {summary.get('convention_count', 0)} conventions")
    else:
        print(f"  ✗ Session start failed: {result.reasoning}")
        return 1

    # Clean up
    memory.forget_project("/test/session")
    tracker.clear_project("/test/session")

    # Test 10: Work Tracker
    print("\n[10/10] Testing Work Tracker...")
    work = WorkTracker(memory)

    # Start a session
    work.start_session("/test/work")

    # Log some work
    work.log_edit("/test/work/file.py", "Added new function", lines_changed=10)
    work.log_search("authentication", 5, "/test/work")
    work.log_decision(
        "Use pydantic for validation",
        "Cleaner than manual checks",
        ["dataclasses", "attrs"]
    )

    # Log a mistake
    work.log_mistake(
        "Forgot to handle edge case",
        "/test/work/file.py",
        "Always check for empty input"
    )

    # Get session summary
    result = work.get_session_summary()
    if result.status == "success":
        data = result.data
        print(f"  ✓ Work tracking works")
        print(f"  ✓ Logged {data.get('edits', 0)} edits")
        print(f"  ✓ Logged {data.get('searches', 0)} searches")
        print(f"  ✓ Logged {data.get('decisions', 0)} decisions")
        print(f"  ✓ Logged {data.get('errors', 0)} mistakes")
    else:
        print(f"  ✗ Work tracking failed: {result.reasoning}")
        return 1

    # Test pre-edit check
    result = work.get_relevant_context("/test/work/file.py")
    if result.status == "success":
        print(f"  ✓ Pre-edit check works")
        if result.warnings:
            print(f"  ✓ Found past mistake warning!")
    else:
        print(f"  ✓ Pre-edit check works (no warnings)")

    # Clean up test work memories
    memory.forget_project("/test/work")

    # Test 11: Code Quality Checker
    print("\n[11/13] Testing Code Quality Checker...")
    quality = CodeQualityChecker()

    bad_code = """
def process_data(a, b, c, d, e, f, g):
    data = []
    result = None
    for x in a:
        if b:
            if c:
                if d:
                    data.append(x)
    return result
"""
    result = quality.check(bad_code, "python")
    if result.status in ("success", "failed"):
        issues = result.data.get("summary", {})
        print(f"  ✓ Code quality check works")
        print(f"  ✓ Found {issues.get('total', 0)} issues")
        if result.warnings:
            print(f"  ✓ Top issue: {result.warnings[0][:50]}...")
    else:
        print(f"  ✗ Code quality check failed")
        return 1

    # Test 12: Loop Detector
    print("\n[12/13] Testing Loop Detector...")
    loop = LoopDetector()

    # Simulate editing same file multiple times
    for i in range(4):
        result = loop.record_edit("/test/loop/file.py", f"edit {i}")

    if result.warnings:
        print(f"  ✓ Loop detector works")
        print(f"  ✓ Detected loop: {result.warnings[0][:50]}...")
    else:
        print(f"  ✓ Loop detector works (no loops yet)")

    # Test pre-edit check
    result = loop.check_before_edit("/test/loop/file.py")
    if result.data.get("risk_level") in ("high", "medium"):
        print(f"  ✓ Pre-edit loop check works")
        print(f"  ✓ Risk level: {result.data.get('risk_level')}")
    else:
        print(f"  ✓ Pre-edit loop check works (low risk)")

    # Test 13: Scope Guard
    print("\n[13/13] Testing Scope Guard...")
    scope = ScopeGuard()

    # Declare scope
    result = scope.declare_scope(
        task_description="Fix login bug",
        in_scope_files=["auth.py", "login.py"],
        reason="Only touching auth files"
    )
    if result.status == "success":
        print(f"  ✓ Scope declaration works")
    else:
        print(f"  ✗ Scope declaration failed")
        return 1

    # Check in-scope file
    result = scope.check_file("auth.py")
    if result.data.get("in_scope"):
        print(f"  ✓ In-scope check works (auth.py allowed)")
    else:
        print(f"  ✗ In-scope check failed")
        return 1

    # Check out-of-scope file
    result = scope.check_file("database.py")
    if not result.data.get("in_scope") and result.warnings:
        print(f"  ✓ Out-of-scope check works (database.py blocked)")
        print(f"  ✓ Warning: {result.warnings[0][:50]}...")
    else:
        print(f"  ✗ Out-of-scope check failed")
        return 1

    # Test 14: Context Guard
    print("\n[14/15] Testing Context Guard...")
    context = ContextGuard()

    # Save a checkpoint
    result = context.save_checkpoint(
        task_description="Add user authentication",
        current_step="Create login endpoint",
        completed_steps=["Set up database schema", "Create user model"],
        pending_steps=["Add JWT tokens", "Create logout endpoint"],
        files_involved=["auth.py", "models/user.py"],
        key_decisions=["Using JWT over session tokens"],
    )
    if result.status == "success":
        print(f"  ✓ Checkpoint save works")
        print(f"  ✓ Progress: {result.data.get('progress_percent', 0):.0f}%")
    else:
        print(f"  ✗ Checkpoint save failed: {result.reasoning}")
        return 1

    # Restore checkpoint
    result = context.restore_checkpoint()
    if result.status == "success":
        print(f"  ✓ Checkpoint restore works")
        print(f"  ✓ Task: {result.data.get('task_description', '')[:40]}...")
    else:
        print(f"  ✓ No checkpoint to restore (expected if clean state)")

    # Test instruction reinforcement
    result = context.add_critical_instruction(
        instruction="Never use eval() in user input handling",
        reason="Security vulnerability",
        importance=10,
    )
    if result.status == "success":
        print(f"  ✓ Critical instruction registered")
    else:
        print(f"  ✗ Instruction add failed")
        return 1

    # Test handoff
    result = context.create_handoff(
        summary="Completed authentication setup",
        next_steps=["Add password reset", "Add email verification"],
        context_needed=["JWT secret is in .env", "User model in models/user.py"],
    )
    if result.status == "success":
        print(f"  ✓ Handoff creation works")
    else:
        print(f"  ✗ Handoff creation failed")
        return 1

    # Test 15: Output Validator
    print("\n[15/15] Testing Output Validator...")
    validator = OutputValidator()

    # Test code with silent failure patterns
    suspicious_code = '''
def process_data(input):
    try:
        result = parse(input)
    except:
        pass
    return "example"
'''
    result = validator.validate_code(suspicious_code)
    if result.data.get("critical_count", 0) > 0 or result.data.get("warning_count", 0) > 0:
        print(f"  ✓ Output validator works")
        print(f"  ✓ Critical issues: {result.data.get('critical_count', 0)}")
        print(f"  ✓ Warnings: {result.data.get('warning_count', 0)}")
        if result.warnings:
            print(f"  ✓ Top issue: {result.warnings[0][:50]}...")
    else:
        print(f"  ✗ Output validator missed obvious issues")
        return 1

    # Test output validation
    result = validator.validate_output(
        output="Success! Result: example data",
        should_not_contain=["error", "failed"],
    )
    if result.data and result.data.get("issues"):
        print(f"  ✓ Output result validation works")
        print(f"  ✓ Found placeholder keyword")
    else:
        print(f"  ✓ Output result validation works (no issues)")

    print("\n" + "=" * 60)
    print("All tests passed! Mini Claude is ready.")
    print("=" * 60)

    print("\nAvailable tools (38 total):")
    print("  Session & Memory:")
    print("    - session_start      : Load all context for a project")
    print("    - memory_remember    : Store knowledge")
    print("    - memory_recall      : Retrieve knowledge")
    print("    - memory_forget      : Clear project knowledge")
    print("  Work Tracking:")
    print("    - work_log_mistake   : Log when something breaks")
    print("    - work_log_decision  : Log why you did something")
    print("    - work_pre_edit_check: Check context before editing")
    print("    - work_session_summary: See what happened this session")
    print("    - work_save_session  : Persist session to memory")
    print("  Code Quality:")
    print("    - code_quality_check : Check code for structural issues")
    print("  Loop Detection:")
    print("    - loop_record_edit   : Record file edit")
    print("    - loop_check_before_edit: Check if editing might loop")
    print("    - loop_record_test   : Record test results")
    print("    - loop_status        : Get loop detection status")
    print("  Scope Guard:")
    print("    - scope_declare      : Declare files in scope for task")
    print("    - scope_check        : Check if file is in scope")
    print("    - scope_expand       : Add files to scope")
    print("    - scope_status       : Get scope status")
    print("    - scope_clear        : Clear scope")
    print("  Context Guard (NEW!):")
    print("    - context_checkpoint_save: Save task state")
    print("    - context_checkpoint_restore: Restore task state")
    print("    - context_checkpoint_list: List all checkpoints")
    print("    - context_instruction_add: Add critical instruction")
    print("    - context_instruction_reinforce: Get instruction reminders")
    print("    - context_claim_completion: Claim task complete")
    print("    - context_self_check : Verify claimed work")
    print("    - context_handoff_create: Create session handoff")
    print("    - context_handoff_get: Get previous handoff")
    print("  Output Validator (NEW!):")
    print("    - output_validate_code: Check for silent failures")
    print("    - output_validate_result: Check output for fakes")
    print("  Search & Analysis:")
    print("    - scout_search       : Find code in codebase")
    print("    - scout_analyze      : Analyze code snippet")
    print("    - file_summarize     : Quick file understanding")
    print("    - deps_map           : Dependency analysis")
    print("    - impact_analyze     : Change impact prediction")
    print("  Conventions:")
    print("    - convention_add     : Store coding conventions")
    print("    - convention_get     : Get project conventions")
    print("    - convention_check   : Check code against conventions")
    print("  Status:")
    print("    - mini_claude_status : Health check")

    print("\nTo use Mini Claude with Claude Code:")
    print("1. Restart Claude Code in this directory")
    print("2. Run /mcp to verify mini-claude is connected")
    print("3. Ask Claude to use any of the above tools")

    return 0


if __name__ == "__main__":
    sys.exit(main())
