#tool 1 get_current_date_time
from datetime import datetime, date
import json
from tkinter.tix import STATUS
from data_layer import load_invoices, load_expenses, load_payments

def get_current_datetime():
    # Get current local date and time
    now = datetime.now()

    return f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    # Output: 2026-07-06



def remember(key: str, value: str ):


    file_path = "memory.json"
    
    
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    data[key] = value

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

    return f"Remembered: {key} = {value}"
def list_memories():
    file_path = "memory.json"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        if not data:
            return "No memories stored yet."
        keys = list(data.keys())
        return f"Stored memory keys: {keys}"
    except FileNotFoundError:
        return "No memories stored yet."



def recall(key:str):
    file_path = "memory.json"
    try:
        # 1. Try to read the existing file
        with open(file_path, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        # 2. If missing, create it with default data
        return f"you cant recall as no memory exists for now"
    return f"Remembered: {key} = {data[key]}"


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

TOOLS = [
    {
        "name": "get_current_datetime",
        "description": "Get the exact time of the day in the universal format",
        "parameters": {
            "type": "object",
            "properties":{
            },
            "required": []
        }
    },
    
    {
           "name": "remember",
        "description": "Store the key inside the json file with its adjacent value",
        "parameters": {
            "type":"object",

        "properties": {
            "key": {
                "type": "string",
                "description": "The label to store the memory under"
        },
            "value": {
                "type": "string", 
                "description": "The information to remember"
            }
        },
        "required": ["key", "value"]
        }
    },
    {
            "name": "recall",
        "description": "Retrieve the value adjacent to the key",
        "parameters":{
        "type":"object",
        "properties": {
            "key": {
                "type": "string",
                "description": "The label of the memory to retrieve"
            }
        },
        "required": ["key"]
        }
    }
    
    
]
