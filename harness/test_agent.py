# ==========================================
# Jarvis Harness — Layer 1: Agent Dispatch Tests
# ==========================================
# Tests semantic dispatch correctness.
# Does the right query hit the right tool?
# Does a nonsense query get rejected?
# No Gemini calls — tests dispatch layer only.

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import torch
from sentence_transformers import SentenceTransformer, util
from tools import TOOLS
from harness.runner import assert_true, assert_equal, section, summarize

# ==========================================
# SETUP — embed tool descriptions once
# ==========================================
print("[Harness] Loading embedding model for dispatch tests...")
_model = SentenceTransformer('all-MiniLM-L6-v2')
_descriptions = [tool["description"] for tool in TOOLS]
_tool_embeddings = _model.encode(_descriptions, convert_to_tensor=True)
_tool_names = [tool["name"] for tool in TOOLS]
CONFIDENCE_THRESHOLD = 0.30


def dispatch(query: str) -> tuple[str, float]:
    """Run semantic dispatch and return (tool_name, score)."""
    query_embedding = _model.encode(query, convert_to_tensor=True)
    similarities = util.cos_sim(query_embedding, _tool_embeddings)[0]
    best_idx = torch.argmax(similarities).item()
    best_score = similarities[best_idx].item()
    return _tool_names[best_idx], best_score


# ==========================================
# DISPATCH CORRECTNESS TESTS
# ==========================================
def test_aging_dispatch():
    section("Dispatch — Aging Report Queries")

    tool, score = dispatch("Who owes us money and how overdue are they?")
    assert_equal(tool, "get_aging_report", "direct aging query hits get_aging_report")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Which clients are late on payments?")
    assert_equal(tool, "get_aging_report", "late payments query hits get_aging_report")

    tool, score = dispatch("Show me overdue invoices broken down by days")
    assert_equal(tool, "get_aging_report", "overdue breakdown query hits get_aging_report")


def test_monthly_summary_dispatch():
    section("Dispatch — Monthly Summary Queries")

    tool, score = dispatch("Give me a summary of this month's finances")
    assert_equal(tool, "get_monthly_summary", "monthly summary query hits get_monthly_summary")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("What's our revenue and expenses this month?")
    assert_equal(tool, "get_monthly_summary", "revenue/expenses query hits get_monthly_summary")


def test_reconciliation_dispatch():
    section("Dispatch — Reconciliation Queries")

    tool, score = dispatch("Do our books match the bank statements?")
    assert_equal(tool, "get_reconciliation_report", "books match query hits get_reconciliation_report")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Are there any payment discrepancies?")
    assert_equal(tool, "get_reconciliation_report", "discrepancies query hits get_reconciliation_report")


def test_expense_anomalies_dispatch():
    section("Dispatch — Expense Anomaly Queries")

    tool, score = dispatch("Any unusual or suspicious expenses?")
    assert_equal(tool, "get_expense_anomalies", "suspicious expenses query hits get_expense_anomalies")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Flag any duplicate or high value spending")
    assert_equal(tool, "get_expense_anomalies", "duplicate spending query hits get_expense_anomalies")


def test_cashflow_dispatch():
    section("Dispatch — Cashflow Queries")

    tool, score = dispatch("What is our current cash position?")
    assert_equal(tool, "get_cashflow_position", "cash position query hits get_cashflow_position")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Do we have enough cash to cover payroll?")
    assert_equal(tool, "get_cashflow_position", "payroll query hits get_cashflow_position")


def test_client_history_dispatch():
    section("Dispatch — Client History Queries")

    tool, score = dispatch("Pull up everything on Delta Imports")
    assert_equal(tool, "get_client_history", "client lookup hits get_client_history")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Show me Lambda Energies full account history")
    assert_equal(tool, "get_client_history", "client history query hits get_client_history")


def test_month_comparison_dispatch():
    section("Dispatch — Month Comparison Queries")

    tool, score = dispatch("Are we doing better or worse than last month?")
    assert_equal(tool, "get_month_comparison", "month comparison query hits get_month_comparison")
    assert_true(score >= CONFIDENCE_THRESHOLD, f"confidence above threshold (got {score:.4f})")

    tool, score = dispatch("Compare this month to last month")
    assert_equal(tool, "get_month_comparison", "compare months query hits get_month_comparison")


# ==========================================
# CONFIDENCE GUARDRAIL TESTS
# ==========================================
def test_confidence_guardrail():
    section("Dispatch — Confidence Guardrail")

    # These should all score BELOW threshold — not finance queries
    irrelevant_queries = [
        "What is the weather today?",
        "Tell me a joke",
        "Who won the football match?",
        "Book me a flight to Dubai",
        "What is the capital of France?",
    ]

    for query in irrelevant_queries:
        _, score = dispatch(query)
        assert_true(
            score < CONFIDENCE_THRESHOLD,
            f"Non-finance query rejected: '{query[:40]}...' (score: {score:.4f})"
        )


# ==========================================
# RUN ALL
# ==========================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  JARVIS HARNESS — LAYER 1: DISPATCH TESTS")
    print("=" * 50)

    test_aging_dispatch()
    test_monthly_summary_dispatch()
    test_reconciliation_dispatch()
    test_expense_anomalies_dispatch()
    test_cashflow_dispatch()
    test_client_history_dispatch()
    test_month_comparison_dispatch()
    test_confidence_guardrail()

    summarize()