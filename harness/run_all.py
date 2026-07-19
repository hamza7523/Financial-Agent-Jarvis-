# ==========================================
# Jarvis Harness — Master Runner
# ==========================================
# Run everything: python harness/run_all.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import harness.runner as runner

# Import all test modules
from harness.test_tools import (
    test_aging_report,
    test_monthly_summary,
    test_reconciliation_report,
    test_expense_anomalies,
    test_cashflow_position,
    test_client_history_specific,
    test_client_history_unknown,
    test_client_history_all,
    test_month_comparison,
)
from harness.test_agent import (
    test_aging_dispatch,
    test_monthly_summary_dispatch,
    test_reconciliation_dispatch,
    test_expense_anomalies_dispatch,
    test_cashflow_dispatch,
    test_client_history_dispatch,
    test_month_comparison_dispatch,
    test_confidence_guardrail,
)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  JARVIS HARNESS — FULL SUITE")
    print("=" * 50)

    # ── Layer 1a: Tool output tests ──
    print("\n▶ LAYER 1A — TOOL OUTPUT TESTS")
    test_aging_report()
    test_monthly_summary()
    test_reconciliation_report()
    test_expense_anomalies()
    test_cashflow_position()
    test_client_history_specific()
    test_client_history_unknown()
    test_client_history_all()
    test_month_comparison()

    # ── Layer 1b: Dispatch correctness tests ──
    print("\n▶ LAYER 1B — DISPATCH CORRECTNESS TESTS")
    test_aging_dispatch()
    test_monthly_summary_dispatch()
    test_reconciliation_dispatch()
    test_expense_anomalies_dispatch()
    test_cashflow_dispatch()
    test_client_history_dispatch()
    test_month_comparison_dispatch()
    test_confidence_guardrail()

    # Final summary
    all_passed = runner.summarize()
    sys.exit(0 if all_passed else 1)