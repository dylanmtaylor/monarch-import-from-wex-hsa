"""Converts parsed WEX HSA transactions and balances to Monarch Money CSV format."""

import csv
import io
import re
from typing import List, Dict, Any
from datetime import datetime


def clean_merchant_name(desc: str) -> str:
    """Extract a concise, human-friendly merchant name from WEX statement text."""
    desc_lower = desc.lower()

    if "interest" in desc_lower:
        return "WEX HSA Interest"
    if "payroll deduction" in desc_lower:
        return "WEX HSA Payroll Contribution"
    if "employer contribution" in desc_lower:
        return "WEX HSA Employer Contribution"
    if "transfer cash to investment" in desc_lower:
        return "Transfer to WEX HSA Investment"
    if "transfer from wex hsa cash" in desc_lower:
        return "Transfer from WEX HSA Cash"

    return desc[:40].strip()


def infer_category(desc: str, amount: float) -> str:
    """Infer standard Monarch category from transaction description and amount."""
    desc_lower = desc.lower()

    if "interest" in desc_lower:
        return "Interest"
    if "employer contribution" in desc_lower:
        return "Employer Match"
    if "payroll deduction" in desc_lower:
        return "HSA Contribution"
    if "transfer" in desc_lower:
        return "Transfer"
    if "distribution" in desc_lower or "reimbursement" in desc_lower:
        return "Medical"

    return "Transfer"


def convert_balances_to_csv(daily_balances: List[Dict[str, Any]]) -> str:
    """Format daily balances into Monarch Money CSV format (Date,Balance)."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Date", "Balance"])

    for row in daily_balances:
        writer.writerow([row["date"], f"{row['balance']:.2f}"])

    return output.getvalue()


def convert_transactions_to_csv(
    transactions: List[Dict[str, Any]], account_display_name: str
) -> str:
    """
    Format transactions into Monarch Money CSV format.
    Header: Date,Merchant,Category,Account,Original Statement,Notes,Amount
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Date", "Merchant", "Category", "Account", "Original Statement", "Notes", "Amount"])

    for txn in transactions:
        raw_date = txn["date"].strip()
        if "/" in raw_date:
            d_obj = datetime.strptime(raw_date, "%m/%d/%Y")
            iso_date = d_obj.strftime("%Y-%m-%d")
        else:
            iso_date = raw_date

        desc = txn.get("description", "").strip()
        merchant = clean_merchant_name(desc)
        category = infer_category(desc, txn["amount"])
        notes = f"WEX HSA {txn.get('method', '').strip()} {txn.get('check_number', '').strip()}".strip()
        amount_str = f"{txn['amount']:.2f}"

        writer.writerow([
            iso_date,
            merchant,
            category,
            account_display_name,
            desc,
            notes,
            amount_str,
        ])

    return output.getvalue()
