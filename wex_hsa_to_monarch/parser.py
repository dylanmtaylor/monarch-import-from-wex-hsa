"""Parser for WEX Health PaymentData.csv and balance series generator."""

import csv
import io
import os
import re
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from collections import defaultdict


def parse_wex_amount(amt_str: str) -> float:
    """Parse WEX dollar string into a float, handling parentheses for negative values."""
    s = amt_str.replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    if s.startswith("(") and s.endswith(")"):
        return -float(s[1:-1])
    return float(s)


def parse_date(date_str: str) -> date:
    """Parse MM/DD/YYYY or YYYY-MM-DD date string."""
    s = date_str.strip()
    if "/" in s:
        return datetime.strptime(s, "%m/%d/%Y").date()
    elif "-" in s:
        if "T" in s:
            s = s.split("T")[0]
        return datetime.strptime(s, "%Y-%m-%d").date()
    raise ValueError(f"Unrecognized date: {date_str}")


class WexAccountData:
    """Holds parsed transactions and continuous daily balance history for an account."""

    def __init__(self, account_name: str, account_type: str, account_number: str = "1234"):
        self.account_name = account_name
        self.account_type = account_type  # "cash" or "investment"
        self.account_number = account_number
        self.transactions: List[Dict[str, Any]] = []

    @property
    def slug(self) -> str:
        clean = self.account_type.lower()
        return f"wex_hsa_{clean}_{self.account_number}"

    @property
    def display_name(self) -> str:
        if self.account_type.lower() == "cash":
            return f"WEX HSA - Cash Account ({self.account_number})"
        return f"WEX HSA - Investment Account ({self.account_number})"

    def compute_daily_balances(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Compute continuous daily balance points forward-filled from start_date to end_date."""
        if end_date is None:
            end_date = date.today()

        if self.account_type == "investment":
            # For investment account, balance is 0.00 until transfer date
            if start_date is None:
                start_date = date(2026, 1, 1)

            curr_bal = 0.0
            daily_balances = []
            curr_d = start_date

            transfer_date = None
            transfer_amount = 0.0
            if self.transactions:
                t = self.transactions[0]
                transfer_date = parse_date(t["date"])
                transfer_amount = t["amount"]

            while curr_d <= end_date:
                if transfer_date and curr_d >= transfer_date:
                    curr_bal = transfer_amount
                daily_balances.append({
                    "date": curr_d.strftime("%Y-%m-%d"),
                    "balance": round(curr_bal, 2)
                })
                curr_d += timedelta(days=1)

            return daily_balances

        # For Cash Account:
        if not self.transactions:
            return []

        # Sort transactions chronologically
        sorted_txns = sorted(
            self.transactions,
            key=lambda t: (parse_date(t["date"]), t.get("order_index", 0))
        )

        daily_activity = defaultdict(float)
        end_of_day_balances: Dict[date, float] = {}

        for t in sorted_txns:
            d = parse_date(t["date"])
            daily_activity[d] += t["amount"]
            if t.get("balance") is not None:
                end_of_day_balances[d] = t["balance"]

        first_txn_d = parse_date(sorted_txns[0]["date"])
        if start_date is None:
            # Start at beginning of the year or account opening
            start_date = min(date(first_txn_d.year, 1, 1), first_txn_d)

        daily_balances = []
        curr_bal = 0.0
        curr_d = start_date

        while curr_d <= end_date:
            if curr_d in daily_activity:
                curr_bal += daily_activity[curr_d]
            if curr_d in end_of_day_balances:
                curr_bal = end_of_day_balances[curr_d]

            daily_balances.append({
                "date": curr_d.strftime("%Y-%m-%d"),
                "balance": round(curr_bal, 2)
            })
            curr_d += timedelta(days=1)

        return daily_balances


def parse_payment_data_csv(csv_text_or_path, account_number: str = "1234") -> Dict[str, WexAccountData]:
    """
    Parse WEX PaymentData.csv and return Cash and Investment WexAccountData objects.
    """
    if os.path.exists(str(csv_text_or_path)):
        with open(csv_text_or_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    else:
        content = str(csv_text_or_path)

    reader = list(csv.DictReader(io.StringIO(content)))
    # Original file is newest-to-oldest, reverse to process oldest-to-newest
    chronological_rows = list(reversed(reader))

    cash_account = WexAccountData("WEX HSA Cash Account", "cash", account_number=account_number)
    investment_account = WexAccountData("WEX HSA Investment Account", "investment", account_number=account_number)

    investment_transfer_amount = 0.0
    investment_transfer_date = None

    for idx, row in enumerate(chronological_rows):
        proc_date_str = row.get("Processed Date") or row.get("Requested Date") or ""
        desc = row.get("Description", "").strip()
        amt = parse_wex_amount(row.get("Amount", "0"))
        bal = parse_wex_amount(row.get("Available Cash Balance", "0"))

        txn_record = {
            "date": proc_date_str,
            "description": desc,
            "method": row.get("Method", ""),
            "amount": amt,
            "balance": bal,
            "check_number": row.get("Check Number", ""),
            "consumer_note": row.get("Consumer Note", ""),
            "tax_year": row.get("Tax Year", ""),
            "tax_detail": row.get("Tax Detail", ""),
            "order_index": idx,
        }
        cash_account.transactions.append(txn_record)

        if "transfer cash to investment" in desc.lower():
            investment_transfer_amount = abs(amt)
            investment_transfer_date = proc_date_str

    # Create corresponding transfer record in Investment account
    if investment_transfer_amount > 0 and investment_transfer_date:
        investment_account.transactions.append({
            "date": investment_transfer_date,
            "description": "Transfer from WEX HSA Cash Account",
            "method": "None",
            "amount": investment_transfer_amount,
            "balance": investment_transfer_amount,
            "consumer_note": "Automatic sweep to investment account",
            "order_index": 0,
        })

    return {
        "cash": cash_account,
        "investment": investment_account,
    }
