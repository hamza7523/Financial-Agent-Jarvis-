#tool 1 get_current_date_time
from datetime import datetime, date
import json
from data_layer import load_invoices, load_expenses, load_payments
from config import CONFIDENCE_THRESHOLD, HIGH_EXPENSE_THRESHOLD, STARTING_BALANCE


def get_aging_report():
    invoices = load_invoices()
    invoices = [inv for inv in invoices if inv.status == "Overdue"]
    
    bucket1 = []
    bucket2 = []
    bucket3 = []
    
    for invoice in invoices:
        if 0 < invoice.days_overdue < 30:
            bucket1.append(invoice)
        elif 30 <= invoice.days_overdue < 60:
            bucket2.append(invoice)
        else:
            bucket3.append(invoice)
    
    return {"0-30": bucket1, "30-60": bucket2, "60+": bucket3}

def get_monthly_summary():
    invoices = load_invoices()
    expenses = load_expenses()
    payments = load_payments()

    # Calculate monthly totals
    total_invoices = sum(inv.amount for inv in invoices if inv.status == "Paid")
    total_expenses = sum(exp.amount for exp in expenses)
    total_payments = sum(pay.amount_paid for pay in payments)

    return {
        "total_invoices": total_invoices,
        "total_expenses": total_expenses,
        "total_payments": total_payments
    }

def get_reconciliation_report():
    invoices = load_invoices()
    payments = load_payments()
    
    discrepancies = []
    paid_invoices = {inv.invoice_id: inv for inv in invoices}    
    # Check for zero-amount payments (dirty data check)
    zero_payments = [pay.payment_id for pay in payments if getattr(pay, 'amount_paid', 0) == 0]
    if zero_payments:
        discrepancies.append({
            "issue": "Zero-dollar payment recorded",
            "payment_ids": zero_payments
        })
        
    # Check for mismatched payment vs invoice amounts
    for pay in payments:
        inv_id = getattr(pay, 'invoice_id', None)
        if inv_id and inv_id in paid_invoices:
            inv = paid_invoices[inv_id]
            if pay.amount_paid != inv.amount:
                discrepancies.append({
                    "issue": "Amount Mismatch",
                    "invoice_id": inv_id,
                    "expected_amount": inv.amount,
                    "actual_payment": pay.amount_paid
                })
                
    return {
        "total_discrepancies": len(discrepancies),
        "details": discrepancies
    }


def get_client_history(client_name: str | None = None) -> dict:
    invoices = load_invoices()
    payments = load_payments()
    invoice_lookup = {inv.invoice_id: inv for inv in invoices}

    if client_name:
        normalized_name = client_name.strip().lower()
        client_invoices = [inv for inv in invoices if inv.client_name.lower() == normalized_name]
        client_payments = []
        for pay in payments:
            inv = invoice_lookup.get(pay.invoice_id)
            if inv and inv.client_name.lower() == normalized_name:
                client_payments.append(pay)

        if not client_invoices and not client_payments:
            return {"error": f"No records found for client '{client_name}'"}

        total_invoiced = sum(inv.amount for inv in client_invoices)
        total_paid = sum(pay.amount_paid for pay in client_payments)
        overdue = [inv for inv in client_invoices if inv.status == "Overdue"]

        return {
            "client": client_name,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": total_invoiced - total_paid,
            "overdue_invoices": len(overdue),
            "overdue_amounts": [{"invoice_id": inv.invoice_id, "amount": inv.amount, "days_overdue": inv.days_overdue} for inv in overdue],
            "invoice_count": len(client_invoices),
            "payment_count": len(client_payments)
        }

    client_summaries = {}
    for inv in invoices:
        entry = client_summaries.setdefault(inv.client_name, {
            "client": inv.client_name,
            "total_invoiced": 0.0,
            "total_paid": 0.0,
            "invoice_count": 0,
            "payment_count": 0,
            "overdue_invoices": []
        })
        entry["total_invoiced"] += inv.amount
        entry["invoice_count"] += 1
        if inv.status == "Overdue":
            entry["overdue_invoices"].append({
                "invoice_id": inv.invoice_id,
                "amount": inv.amount,
                "days_overdue": inv.days_overdue
            })

    for pay in payments:
        inv = invoice_lookup.get(pay.invoice_id)
        if inv:
            entry = client_summaries.setdefault(inv.client_name, {
                "client": inv.client_name,
                "total_invoiced": 0.0,
                "total_paid": 0.0,
                "invoice_count": 0,
                "payment_count": 0,
                "overdue_invoices": []
            })
            entry["total_paid"] += pay.amount_paid
            entry["payment_count"] += 1

    return {
        "client_count": len(client_summaries),
        "clients": [
            {
                **entry,
                "outstanding": entry["total_invoiced"] - entry["total_paid"]
            }
            for entry in client_summaries.values()
        ]
    }


def get_month_comparison() -> dict:
    invoices = load_invoices()
    expenses = load_expenses()
    payments = load_payments()

    today = date.today()
    current_month = today.month
    current_year = today.year

    # Previous month logic
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    def in_month(d, m, y):
        if d is None:
            return False
        return d.month == m and d.year == y

    # Current month
    curr_invoices = sum(inv.amount for inv in invoices if in_month(inv.issue_date, current_month, current_year))
    curr_expenses = sum(exp.amount for exp in expenses if in_month(exp.expense_date, current_month, current_year))
    curr_payments = sum(pay.amount_paid for pay in payments if in_month(pay.payment_date, current_month, current_year))

    # Previous month
    prev_invoices = sum(inv.amount for inv in invoices if in_month(inv.issue_date, prev_month, prev_year))
    prev_expenses = sum(exp.amount for exp in expenses if in_month(exp.expense_date, prev_month, prev_year))
    prev_payments = sum(pay.amount_paid for pay in payments if in_month(pay.payment_date, prev_month, prev_year))

    def delta(curr, prev):
        if prev == 0:
            return None
        return round(((curr - prev) / prev) * 100, 1)

    return {
        "current_month": today.strftime("%B %Y"),
        "previous_month": f"{prev_month}/{prev_year}",
        "invoices": {"current": curr_invoices, "previous": prev_invoices, "change_pct": delta(curr_invoices, prev_invoices)},
        "expenses": {"current": curr_expenses, "previous": prev_expenses, "change_pct": delta(curr_expenses, prev_expenses)},
        "payments": {"current": curr_payments, "previous": prev_payments, "change_pct": delta(curr_payments, prev_payments)}
    }
def get_expense_anomalies():
    expenses = load_expenses()
    anomalies = []
    seen_amounts = set()
    
    # Define thresholds
    HIGH_EXPENSE_THRESHOLD = 10000.00
    
    for exp in expenses:
        exp_id = exp.expense_id
        
        # 1. Unusually high expenses
        if exp.amount > HIGH_EXPENSE_THRESHOLD:
            anomalies.append({
                "type": "High Value Anomaly",
                "expense_id": exp_id,
                "amount": exp.amount
            })
            
        # 2. Duplicate detection (checking exact matching amounts as a basic heuristic)
        if exp.amount in seen_amounts:
            anomalies.append({
                "type": "Potential Duplicate",
                "expense_id": exp_id,
                "amount": exp.amount
            })
        seen_amounts.add(exp.amount)
        
    return {
        "anomalies_found": len(anomalies),
        "details": anomalies
    }

def get_cashflow_position():
    invoices = load_invoices()
    expenses = load_expenses()
    
    # Calculate inflows vs outflows
    cash_inflow = sum(inv.amount for inv in invoices if inv.status == "Paid")
    cash_outflow = sum(exp.amount for exp in expenses)
    
    # Mocking a starting balance for working capital calculation
    starting_balance = 50000.00 
    current_cash = starting_balance + cash_inflow - cash_outflow
    
    # Basic runway calculation (Assuming average monthly burn is total expenses)
    average_burn = cash_outflow if cash_outflow > 0 else 1 
    runway_months = round(current_cash / average_burn, 1)
    
    return {
        "starting_balance": starting_balance,
        "cash_inflow": cash_inflow,
        "cash_outflow": cash_outflow,
        "current_cash_position": current_cash,
        "runway_months": runway_months,
        "status": "Healthy" if runway_months >= 3 else "Warning - Low Runway"
    }

TOOLS = [
   
    
    {
        "name": "get_monthly_summary",
        "description": "How are we doing this month? Give me the high-level monthly numbers. What's our actual revenue from paid invoices, how much have we spent in expenses, and what payments have cleared? Summarize our current monthly financial health.",
        "fn": get_monthly_summary,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_aging_report",
        "description": "Who owes us money and who is really late on payments? Which clients should I chase down first? Give me the breakdown of overdue invoices categorized by 0-30, 30-60, and 60+ days past due so I know where our cash is stuck.",
        "fn": get_aging_report,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_reconciliation_report",
        "description": "Do our books actually match the bank statements? Are there any missing payments, mismatched invoice amounts, or reconciliation issues I need to worry about today? Show me the discrepancies between our records and the bank.",
        "fn": get_reconciliation_report,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_expense_anomalies",
        "description": "Did someone overspend or double-bill us? Find me any weird, unusually high, or duplicate expenses. Flag anything that looks out of the ordinary, anomalous, or sketchy in our recent spending.",
        "fn": get_expense_anomalies,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_cashflow_position",
        "description": "Do we have enough cash to make payroll and cover our upcoming bills? What is our actual cash position right now? Show me our working capital, total cash on hand, and current runway.",
        "fn": get_cashflow_position,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_client_history",
        "description": "Pull up everything on a specific client. Show me the full history for Delta Imports — all their invoices, payments, and how much they still owe us. I need a complete picture of one client's account.",
        "fn": get_client_history,
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "The exact name of the client to look up"
                }
            },
            "required": ["client_name"]
        }
    },
    {
        "name": "get_month_comparison",
        "description": "Are we doing better or worse than last month? Compare this month versus last month across invoices, expenses, and payments. Show me the month-over-month trend and whether our financial position is improving.",
        "fn": get_month_comparison,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    
]

