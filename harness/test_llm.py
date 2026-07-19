# ==========================================
# Jarvis Harness — Test Runner Engine
# ==========================================
# Pure Python assertions. No frameworks.
# Layer 1: deterministic checks against known Excel data.
# Layer 2: DeepEval LLM-as-judge sits on top (test_llm.py, Phase 3 end).

passed = 0
failed = 0
_errors = []


def assert_true(condition: bool, test_name: str, detail: str = "") -> None:
    global passed, failed
    if condition:
        print(f"  ✓  {test_name}")
        passed += 1
    else:
        msg = f"  ✗  {test_name}"
        if detail:
            msg += f"\n       → {detail}"
        print(msg)
        failed += 1
        _errors.append(test_name)


def assert_equal(actual, expected, test_name: str) -> None:
    assert_true(
        actual == expected,
        test_name,
        f"Expected: {expected!r} | Got: {actual!r}"
    )


def assert_contains(container, item, test_name: str) -> None:
    assert_true(
        item in container,
        test_name,
        f"Expected {item!r} in {container!r}"
    )


def assert_greater(actual, threshold, test_name: str) -> None:
    assert_true(
        actual > threshold,
        test_name,
        f"Expected > {threshold} | Got: {actual}"
    )


def assert_type(obj, expected_type, test_name: str) -> None:
    assert_true(
        isinstance(obj, expected_type),
        test_name,
        f"Expected type {expected_type.__name__} | Got: {type(obj).__name__}"
    )


def section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def summarize() -> bool:
    """Print final results. Returns True if all passed."""
    total = passed + failed
    print(f"\n{'=' * 50}")
    if failed == 0:
        print(f"  ALL TESTS PASSED — {passed}/{total}")
    else:
        print(f"  {passed}/{total} passed | {failed} FAILED")
        print(f"\n  Failed tests:")
        for err in _errors:
            print(f"    - {err}")
    print(f"{'=' * 50}\n")
    return failed == 0


def reset() -> None:
    """Reset counters between test runs."""
    global passed, failed, _errors
    passed = 0
    failed = 0
    _errors = []