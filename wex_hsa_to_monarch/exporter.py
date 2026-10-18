"""Exports converted WEX HSA balances and transactions to disk."""

import os
import csv
from typing import Dict, List, Any
from wex_hsa_to_monarch.parser import WexAccountData
from wex_hsa_to_monarch.converter import convert_balances_to_csv, convert_transactions_to_csv


class Exporter:
    """Exports Monarch CSV files and displays summary reports."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    def export_all(self, accounts: Dict[str, WexAccountData]) -> Dict[str, Any]:
        """
        Export balance and transaction CSVs for all WEX accounts.
        
        Returns:
            Dict containing file paths and summary metrics.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        results = {
            "balance_files": [],
            "transaction_files": [],
            "combined_transaction_file": None,
            "metrics": {},
        }

        all_transactions_rows = []

        print("\n" + "=" * 70)
        print("WEX Health HSA to Monarch Money Export Summary")
        print("=" * 70)

        for acct_key in ["cash", "investment"]:
            if acct_key not in accounts:
                continue
            acct = accounts[acct_key]
            slug = acct.slug
            display_name = acct.display_name

            # 1. Compute and export daily balances
            daily_balances = acct.compute_daily_balances()
            bal_csv = convert_balances_to_csv(daily_balances)
            bal_file = os.path.join(self.output_dir, f"wex_hsa_balances_{slug}.csv")
            with open(bal_file, "w", encoding="utf-8") as f:
                f.write(bal_csv)
            results["balance_files"].append(bal_file)

            # 2. Export account transactions
            txn_csv = convert_transactions_to_csv(acct.transactions, display_name)
            txn_file = os.path.join(self.output_dir, f"wex_hsa_transactions_{slug}.csv")
            with open(txn_file, "w", encoding="utf-8") as f:
                f.write(txn_csv)
            results["transaction_files"].append(txn_file)

            # Accumulate rows for combined file
            reader = csv.reader(txn_csv.strip().splitlines())
            next(reader, None)  # Skip header
            for r in reader:
                all_transactions_rows.append(r)

            first_bal_date = daily_balances[0]["date"] if daily_balances else "N/A"
            last_bal_date = daily_balances[-1]["date"] if daily_balances else "N/A"
            current_bal = daily_balances[-1]["balance"] if daily_balances else 0.0

            results["metrics"][acct_key] = {
                "name": acct.account_name,
                "number": acct.account_number,
                "transactions_count": len(acct.transactions),
                "daily_balance_days": len(daily_balances),
                "daily_balance_range": f"{first_bal_date} to {last_bal_date}",
                "current_balance": current_bal,
            }

            print(f"\nAccount: {acct.display_name}")
            print(f"  Transactions:      {len(acct.transactions)}")
            print(f"  Balance History:   {len(daily_balances):,} daily points ({first_bal_date} to {last_bal_date})")
            print(f"  Current Balance:   ${current_bal:,.2f}")
            print(f"  -> Balances CSV:     {bal_file}")
            print(f"  -> Transactions CSV: {txn_file}")

        # 3. Export combined transactions CSV
        if all_transactions_rows:
            all_transactions_rows.sort(key=lambda r: r[0])
            combined_file = os.path.join(self.output_dir, "wex_hsa_transactions_all.csv")
            with open(combined_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Merchant", "Category", "Account", "Original Statement", "Notes", "Amount"])
                writer.writerows(all_transactions_rows)
            results["combined_transaction_file"] = combined_file
            print(f"\nCombined Transactions CSV ({len(all_transactions_rows)} records):")
            print(f"  -> {combined_file}")

        print("\n" + "=" * 70)
        print("Export completed successfully.")
        print("=" * 70 + "\n")

        return results
