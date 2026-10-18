"""Unit tests for Monarch Money CSV converter."""

import unittest
import csv
from wex_hsa_to_monarch.converter import (
    clean_merchant_name,
    infer_category,
    convert_balances_to_csv,
    convert_transactions_to_csv,
)


class TestConverter(unittest.TestCase):
    """Test suite for Monarch CSV conversions."""

    def test_clean_merchant_name(self):
        """Test merchant cleaning rules."""
        self.assertEqual(clean_merchant_name("Interest"), "WEX HSA Interest")
        self.assertEqual(
            clean_merchant_name("09/08/2026 Payroll Deduction"),
            "WEX HSA Payroll Contribution",
        )
        self.assertEqual(
            clean_merchant_name("05/29/2026 Employer Contribution"),
            "WEX HSA Employer Contribution",
        )
        self.assertEqual(
            clean_merchant_name("Transfer Cash to Investment"),
            "Transfer to WEX HSA Investment",
        )
        self.assertEqual(
            clean_merchant_name("Transfer from WEX HSA Cash Account"),
            "Transfer from WEX HSA Cash",
        )

    def test_infer_category(self):
        """Test category mapping."""
        self.assertEqual(infer_category("Interest", 0.25), "Interest")
        self.assertEqual(infer_category("09/08/2026 Payroll Deduction", 141.67), "HSA Contribution")
        self.assertEqual(infer_category("05/29/2026 Employer Contribution", 141.67), "Employer Match")
        self.assertEqual(infer_category("Transfer Cash to Investment", -500.00), "Transfer")
        self.assertEqual(infer_category("Medical Claim Distribution", -75.00), "Medical")

    def test_convert_balances_to_csv(self):
        """Test balance history CSV formatting."""
        daily_balances = [
            {"date": "2026-01-01", "balance": 0.0},
            {"date": "2026-01-20", "balance": 283.34},
        ]
        csv_str = convert_balances_to_csv(daily_balances)
        rows = list(csv.reader(csv_str.strip().splitlines()))

        self.assertEqual(rows[0], ["Date", "Balance"])
        self.assertEqual(rows[1], ["2026-01-01", "0.00"])
        self.assertEqual(rows[2], ["2026-01-20", "283.34"])

    def test_convert_transactions_to_csv(self):
        """Test transactions CSV formatting."""
        transactions = [
            {
                "date": "09/30/2026",
                "description": "Interest",
                "method": "None",
                "amount": 0.21,
                "check_number": "",
            },
            {
                "date": "09/10/2026",
                "description": "09/08/2026 Payroll Deduction",
                "method": "EFT",
                "amount": 566.68,
                "check_number": "262529CE97595",
            },
        ]
        csv_str = convert_transactions_to_csv(transactions, "WEX HSA - Cash Account (1234)")
        rows = list(csv.reader(csv_str.strip().splitlines()))

        self.assertEqual(
            rows[0],
            ["Date", "Merchant", "Category", "Account", "Original Statement", "Notes", "Amount"],
        )
        self.assertEqual(rows[1][0], "2026-09-30")
        self.assertEqual(rows[1][1], "WEX HSA Interest")
        self.assertEqual(rows[1][2], "Interest")
        self.assertEqual(rows[1][3], "WEX HSA - Cash Account (1234)")
        self.assertEqual(rows[1][6], "0.21")

        self.assertEqual(rows[2][0], "2026-09-10")
        self.assertEqual(rows[2][1], "WEX HSA Payroll Contribution")
        self.assertEqual(rows[2][2], "HSA Contribution")
        self.assertEqual(rows[2][6], "566.68")


if __name__ == "__main__":
    unittest.main()
