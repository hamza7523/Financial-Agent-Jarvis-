# ==========================================
# Jarvis Harness — Layer 1: Tool Tests
# ==========================================
# Calls tool functions directly — no Gemini, no dispatch.
# Asserts on raw dict output against known facts in accounts.xlsx.
#
# KNOWN DATA FACTS (ground truth from accounts.xlsx):
#   - Lambda Energies: overdue, 60+ days
#   - Delta Imports: has invoices and payments on record
#   - Starting balance: 50,000.00 (hardcoded in config)
#   - HIGH_EXPENSE_THRESHOLD: 10,000.00
#   - get_monthly_summary returns: total_invoices, total_expenses, total_payments
#   - get_reconciliation_report returns: total_discrepancies, details
#   - get_expense_anomalies returns: anomalies_found, details
#   - get_cashflow_position returns: starting_balance, current_cash_position, status

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import (
    get_aging_report,
    get_monthly_summary,
    get_reconciliation_report,
    get_expense_anomalies,
    get_cashflow_position,
    get_client_history,
    get_month_comparison,
)
from harness.runner import assert_true, assert_equal, assert_type, assert_greater, assert_contains, section, summarize


# ==========================================
# AGING REPORT
# ==========================================
def test_aging_report():
    section("get_aging_report()")
    result = get_aging_report()

    # Structure checks
    assert_type(result, dict, "aging_report returns dict")
    assert_contains(result, "0-30", "aging_report has 0-30 bucket")
    assert_contains(result, "30-60", "aging_report has 30-60 bucket")
    assert_contains(result, "60+", "aging_report has 60+ bucket")

    # Known data: Lambda Energies is 60+ days overdue
    bucket_60 = result.get("60+", [])
    assert_greater(len(bucket_60), 0, "60+ bucket is not empty")

    client_names = [inv.client_name for inv in bucket_60]
    assert_contains(client_names, "Lambda Energies", "Lambda Energies in 60+ bucket")

    # Lambda must be genuinely overdue (days > 60)
    lambda_inv = next((inv for inv in bucket_60 if inv.client_name == "Lambda Energies"), None)
    assert_true(lambda_inv is not None, "Lambda Energies invoice object exists")
    if lambda_inv:
        assert_greater(lambda_inv.days_overdue, 60, f"Lambda Energies days_overdue > 60 (got {lambda_inv.days_overdue})")


# ==========================================
# MONTHLY SUMMARY
# ==========================================
def test_monthly_summary():
    section("get_monthly_summary()")
    result = get_monthly_summary()

    # Structure checks
    assert_type(result, dict, "monthly_summary returns dict")
    assert_contains(result, "total_invoices", "has total_invoices key")
    assert_contains(result, "total_expenses", "has total_expenses key")
    assert_contains(result, "total_payments", "has total_payments key")

    # Values must be numeric and non-negative
    assert_type(result["total_invoices"], (int, float), "total_invoices is numeric")
    assert_type(result["total_expenses"], (int, float), "total_expenses is numeric")
    assert_type(result["total_payments"], (int, float), "total_payments is numeric")

    assert_true(result["total_invoices"] >= 0, "total_invoices non-negative")
    assert_true(result["total_expenses"] >= 0, "total_expenses non-negative")
    assert_true(result["total_payments"] >= 0, "total_payments non-negative")

    # Sanity: we have SOME paid invoices in the dataset
    assert_greater(result["total_invoices"], 0, "total_invoices > 0 (paid invoices exist)")


# ==========================================
# RECONCILIATION REPORT
# ==========================================
def test_reconciliation_report():
    section("get_reconciliation_report()")
    result = get_reconciliation_report()

    # Structure checks
    assert_type(result, dict, "reconciliation_report returns dict")
    assert_contains(result, "total_discrepancies", "has total_discrepancies key")
    assert_contains(result, "details", "has details key")

    # total_discrepancies must match details list length
    assert_equal(
        result["total_discrepancies"],
        len(result["details"]),
        "total_discrepancies matches details count"
    )

    # details must be a list
    assert_type(result["details"], list, "details is a list")

    # Each discrepancy must have an issue field
    for i, disc in enumerate(result["details"]):
        assert_contains(disc, "issue", f"discrepancy[{i}] has issue field")


# ==========================================
# EXPENSE ANOMALIES
# ==========================================
def test_expense_anomalies():
    section("get_expense_anomalies()")
    result = get_expense_anomalies()

    # Structure checks
    assert_type(result, dict, "expense_anomalies returns dict")
    assert_contains(result, "anomalies_found", "has anomalies_found key")
    assert_contains(result, "details", "has details key")

    # Count must match list
    assert_equal(
        result["anomalies_found"],
        len(result["details"]),
        "anomalies_found matches details count"
    )

    # Each anomaly must have type and amount
    for i, anomaly in enumerate(result["details"]):
        assert_contains(anomaly, "type", f"anomaly[{i}] has type field")
        assert_contains(anomaly, "amount", f"anomaly[{i}] has amount field")

    # Known: HIGH_EXPENSE_THRESHOLD is 10,000 — dataset must have at least one high expense
    high_value = [a for a in result["details"] if a.get("type") == "High Value Anomaly"]
    assert_greater(len(high_value), 0, "At least one High Value Anomaly detected")

    # All high value anomalies must actually exceed threshold
    for anomaly in high_value:
        assert_greater(anomaly["amount"], 10000, f"High Value Anomaly amount > 10,000 (got {anomaly['amount']})")


# ==========================================
# CASHFLOW POSITION
# ==========================================
def test_cashflow_position():
    section("get_cashflow_position()")
    result = get_cashflow_position()

    # Structure checks
    assert_type(result, dict, "cashflow_position returns dict")
    assert_contains(result, "starting_balance", "has starting_balance key")
    assert_contains(result, "cash_inflow", "has cash_inflow key")
    assert_contains(result, "cash_outflow", "has cash_outflow key")
    assert_contains(result, "current_cash_position", "has current_cash_position key")
    assert_contains(result, "runway_months", "has runway_months key")
    assert_contains(result, "status", "has status key")

    # Known: starting balance is hardcoded to 50,000
    assert_equal(result["starting_balance"], 50000.00, "starting_balance is 50,000.00")

    # Math integrity: current = starting + inflow - outflow
    expected_cash = result["starting_balance"] + result["cash_inflow"] - result["cash_outflow"]
    assert_true(
        abs(result["current_cash_position"] - expected_cash) < 0.01,
        f"current_cash_position math integrity (expected {expected_cash:.2f})"
    )

    # Status must be one of two valid values
    assert_true(
        result["status"] in ["Healthy", "Warning - Low Runway"],
        f"status is valid value (got '{result['status']}')"
    )


# ==========================================
# CLIENT HISTORY — WITH NAME (parametered)
# ==========================================
def test_client_history_specific():
    section("get_client_history('Delta Imports')")
    result = get_client_history("Delta Imports")

    # Must not return an error
    assert_true("error" not in result, "No error for Delta Imports lookup")

    # Structure checks
    assert_contains(result, "client", "has client key")
    assert_contains(result, "total_invoiced", "has total_invoiced key")
    assert_contains(result, "total_paid", "has total_paid key")
    assert_contains(result, "outstanding", "has outstanding key")
    assert_contains(result, "invoice_count", "has invoice_count key")

    # Must have at least one invoice
    assert_greater(result["invoice_count"], 0, "Delta Imports has at least one invoice")

    # Outstanding math: total_invoiced - total_paid
    expected_outstanding = result["total_invoiced"] - result["total_paid"]
    assert_true(
        abs(result["outstanding"] - expected_outstanding) < 0.01,
        f"outstanding math integrity (expected {expected_outstanding:.2f})"
    )


def test_client_history_unknown():
    section("get_client_history('Unknown Client XYZ')")
    result = get_client_history("Unknown Client XYZ")

    # Must return error for unknown client
    assert_contains(result, "error", "Unknown client returns error key")


# ==========================================
# CLIENT HISTORY — NO NAME (all clients)
# ==========================================
def test_client_history_all():
    section("get_client_history() — all clients")
    result = get_client_history()

    assert_type(result, dict, "all clients returns dict")
    assert_contains(result, "client_count", "has client_count key")
    assert_contains(result, "clients", "has clients key")
    assert_greater(result["client_count"], 0, "at least one client exists")
    assert_equal(result["client_count"], len(result["clients"]), "client_count matches clients list")


# ==========================================
# MONTH COMPARISON
# ==========================================
def test_month_comparison():
    section("get_month_comparison()")
    result = get_month_comparison()

    assert_type(result, dict, "month_comparison returns dict")
    assert_contains(result, "current_month", "has current_month key")
    assert_contains(result, "previous_month", "has previous_month key")
    assert_contains(result, "invoices", "has invoices key")
    assert_contains(result, "expenses", "has expenses key")
    assert_contains(result, "payments", "has payments key")

    # Each section must have current, previous, change_pct
    for section_name in ["invoices", "expenses", "payments"]:
        s = result[section_name]
        assert_contains(s, "current", f"{section_name} has current key")
        assert_contains(s, "previous", f"{section_name} has previous key")
        assert_contains(s, "change_pct", f"{section_name} has change_pct key")

        # Values must be numeric
        assert_type(s["current"], (int, float), f"{section_name}.current is numeric")
        assert_type(s["previous"], (int, float), f"{section_name}.previous is numeric")


# ==========================================
# RUN ALL
# ==========================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  JARVIS HARNESS — LAYER 1: TOOL TESTS")
    print("=" * 50)

    test_aging_report()
    test_monthly_summary()
    test_reconciliation_report()
    test_expense_anomalies()
    test_cashflow_position()
    test_client_history_specific()
    test_client_history_unknown()
    test_client_history_all()
    test_month_comparison()

    summarize()