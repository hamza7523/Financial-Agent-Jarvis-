import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import get_client_history, get_month_comparison


def test_get_client_history_handles_missing_client_name_field():
    result = get_client_history("Delta Imports")
    assert result["client"] == "Delta Imports"
    assert "total_invoiced" in result


def test_get_month_comparison_uses_expense_date_field():
    result = get_month_comparison()
    assert "current_month" in result
    assert "expenses" in result
