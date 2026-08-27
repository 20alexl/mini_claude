"""
Benchmark: model calls stay pinned to one thread.

The scorer daemon handles each connection on a fresh thread. That is fine for
socket I/O, but PyTorch keeps per-thread state it never releases when the
thread dies, so encoding on the connection thread leaked ~0.73 MB per request
-- measured dead-linear at +146 MB per 200 requests with no plateau, which
walked the daemon past 4 GB over a long session. The same encode loop on a
single thread is flat.

So every model call goes through _on_model_thread, which runs it on one
long-lived pinned worker. max_workers=1 costs nothing: the GIL and torch
serialized these calls anyway.

What must hold:
  1. _on_model_thread runs work on a thread that is NOT the caller's.
  2. It uses the SAME thread every time, including from many caller threads --
     that is the property that bounds the leak.
  3. Results and exceptions propagate to the caller unchanged.
  4. No model call site in _handle_client bypasses the pool. This is the
     regression guard: adding a bare model.encode() would silently restore
     the leak, and nothing else in the suite would notice.

Run: python tests/bench_scorer_thread_affinity.py
"""

import os
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_engram.hooks import scorer_server as ss

_fails = []


def check(name, cond):
    print(("  [PASS] " if cond else "  [FAIL] ") + name)
    if not cond:
        _fails.append(name)


def test_pinned_to_one_non_caller_thread():
    print("Model work runs on one pinned thread, never the caller's:")
    seen = []

    def who():
        return threading.get_ident()

    caller = threading.get_ident()
    for _ in range(50):
        seen.append(ss._on_model_thread(who))
    check("never runs on the calling thread", caller not in seen)
    check(f"same thread every time ({len(set(seen))} distinct)", len(set(seen)) == 1)

    # The real shape: many short-lived connection threads, one model thread.
    from_threads = []
    lock = threading.Lock()

    def connection():
        tid = ss._on_model_thread(who)
        with lock:
            from_threads.append(tid)

    workers = [threading.Thread(target=connection) for _ in range(40)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    check(
        f"40 separate caller threads share ONE model thread "
        f"({len(set(from_threads))} distinct)",
        len(set(from_threads)) == 1,
    )
    check("same pinned thread as before", set(from_threads) == set(seen))


def test_results_and_errors_propagate():
    print("The pool is transparent to callers:")
    check("returns the value", ss._on_model_thread(lambda a, b=1: a + b, 41) == 42)
    check("passes kwargs", ss._on_model_thread(lambda a, b=1: a + b, 40, b=2) == 42)

    def boom():
        raise ValueError("propagated")

    try:
        ss._on_model_thread(boom)
        check("exception propagates to caller", False)
    except ValueError as e:
        check("exception propagates to caller", str(e) == "propagated")


def test_no_call_site_bypasses_the_pool():
    """Source guard — the leak comes back the moment one call site slips."""
    print("No model call in the request handler bypasses the pool:")
    src = Path(ss.__file__).read_text(encoding="utf-8")
    body = src[src.index("def _handle_client") : src.index("def serve(")]
    bare = re.findall(r"^\s*[^#\n]*\bmodel\.encode\(", body, re.M)
    check(
        f"no bare model.encode() in _handle_client ({len(bare)} found)",
        not bare,
    )
    routed = body.count("_on_model_thread(")
    check(f"model calls routed through the pool ({routed} sites)", routed >= 3)
    # _score_text encodes internally, so it must be submitted whole, not called
    # directly from the connection thread.
    direct_score = re.findall(r"^\s*(?:score, extracted = )?_score_text\(", body, re.M)
    check(
        f"_score_text is not called directly from the handler "
        f"({len(direct_score)} direct)",
        not direct_score,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Scorer Thread Affinity Benchmark")
    print("=" * 60)
    test_pinned_to_one_non_caller_thread()
    test_results_and_errors_propagate()
    test_no_call_site_bypasses_the_pool()
    print("-" * 60)
    print(
        f"RESULTS: {'ALL PASS' if not _fails else str(len(_fails)) + ' FAILED: ' + str(_fails)}"
    )
    sys.exit(1 if _fails else 0)
