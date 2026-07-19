# ==========================================
# Jarvis Harness — Test Runner Utilities
# ==========================================
# Common assertions and reporting for all test layers

import sys
from typing import Any, Union, Type, Callable


# Test stats
tests_run = 0
tests_passed = 0
tests_failed = 0
failures = []


def assert_true(condition: bool, message: str) -> None:
    """Assert that condition is True."""
    global tests_run, tests_passed, tests_failed, failures
    tests_run += 1
    if condition:
        tests_passed += 1
        print(f"  ✓ {message}")
    else:
        tests_failed += 1
        failures.append(message)
        print(f"  ✗ {message}")


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    """Assert that actual == expected."""
    assert_true(actual == expected, f"{message} (expected {expected}, got {actual})")


def assert_type(obj: Any, expected_type: Union[Type, tuple], message: str) -> None:
    """Assert that obj is an instance of expected_type."""
    if isinstance(expected_type, tuple):
        result = isinstance(obj, expected_type)
        type_names = " or ".join(t.__name__ for t in expected_type)
    else:
        result = isinstance(obj, expected_type)
        type_names = expected_type.__name__
    
    assert_true(result, f"{message} (expected {type_names}, got {type(obj).__name__})")


def assert_greater(value: Any, threshold: Any, message: str) -> None:
    """Assert that value > threshold."""
    assert_true(value > threshold, f"{message}")


def assert_contains(container: Any, item: Any, message: str) -> None:
    """Assert that item is in container."""
    if isinstance(container, dict):
        result = item in container
    elif isinstance(container, (list, tuple, set, str)):
        result = item in container
    else:
        result = False
    
    assert_true(result, f"{message}")


def section(name: str) -> None:
    """Print a test section header."""
    print(f"\n{name}")
    print("-" * 50)


def summarize() -> None:
    """Print final test summary."""
    global tests_run, tests_passed, tests_failed, failures
    
    print("\n" + "=" * 50)
    print(f"RESULTS: {tests_passed}/{tests_run} passed")
    
    if tests_failed > 0:
        print(f"\n{tests_failed} test(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 50)
    else:
        print("All tests passed!")
        print("=" * 50)
