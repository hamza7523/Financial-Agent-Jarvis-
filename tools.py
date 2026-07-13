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
    total_payments = sum(pay.amount for pay in payments)

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
            if pay.amount != inv.amount:
                discrepancies.append({
                    "issue": "Amount Mismatch",
                    "invoice_id": inv_id,
                    "expected_amount": inv.amount,
                    "actual_payment": pay.amount
                })
                
    return {
        "total_discrepancies": len(discrepancies),
        "details": discrepancies
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
    }
]

