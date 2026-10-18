"""Unit tests for WEX HSA CLI and exporter."""

import unittest
import tempfile
import os
from wex_hsa_to_monarch.parser import WexAccountData
from wex_hsa_to_monarch.exporter import Exporter


class TestCLIAndExporter(unittest.TestCase):
    """Test suite for exporter and CLI flows."""

    def test_exporter_writes_all_files(self):
        """Test exporter writes balance and transaction CSVs to output directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            exporter = Exporter(output_dir=tmp_dir)

            cash = WexAccountData("WEX HSA Cash Account", "cash", account_number="1234")
            cash.transactions.append({
                "date": "09/15/2026",
                "description": "Payroll Deduction",
                "method": "EFT",
                "amount": 250.00,
                "balance": 250.00,
                "order_index": 0,
            })

            investment = WexAccountData("WEX HSA Investment Account", "investment", account_number="1234")
            investment.transactions.append({
                "date": "10/01/2026",
                "description": "Transfer from WEX HSA Cash Account",
                "method": "None",
                "amount": 100.00,
                "balance": 100.00,
                "order_index": 0,
            })

            accounts = {"cash": cash, "investment": investment}
            results = exporter.export_all(accounts)

            self.assertEqual(len(results["balance_files"]), 2)
            self.assertEqual(len(results["transaction_files"]), 2)
            self.assertTrue(os.path.exists(results["combined_transaction_file"]))

            for f in results["balance_files"] + results["transaction_files"]:
                self.assertTrue(os.path.exists(f))
                self.assertGreater(os.path.getsize(f), 0)


if __name__ == "__main__":
    unittest.main()
