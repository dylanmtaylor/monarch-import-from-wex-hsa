"""Unit tests for WEX HSA parser and balance generator."""

import unittest
from datetime import date
from wex_hsa_to_monarch.parser import (
    parse_wex_amount,
    parse_date,
    parse_payment_data_csv,
    WexAccountData,
)

SAMPLE_SYNTHETIC_CSV = """Requested Date,Processed Date,Description,Method,Amount,Available Cash Balance,Applied to Contribution Maximum,Check Number,Check Date,Date of Service,Merchant Name,Adjustment Reason,Consumer Note,Tax Year,Tax Detail
10/16/2026,10/16/2026,"Transfer Cash to Investment",None,"($500.00)","$1,500.00",No,,,,,,,,
09/30/2026,09/30/2026,"Interest",None,"$0.50","$2,000.00",No,,,,,,,,
09/15/2026,09/15/2026,"09/15/2026 Payroll Deduction",EFT,"$1,000.00","$1,999.50",Yes,12345,9/15/2026,,,,"Payroll Deduction",2026,"2026_5498SABox2:$1000.00"
09/01/2026,09/01/2026,"09/01/2026 Employer Contribution",EFT,"$999.50","$999.50",Yes,67890,9/1/2026,,,,"Employer Contribution",2026,"2026_5498SABox2:$999.50"
"""


class TestParser(unittest.TestCase):
    """Test suite for WEX HSA parser."""

    def test_parse_wex_amount(self):
        """Test dollar parsing for positive, negative parenthesized, and zero amounts."""
        self.assertEqual(parse_wex_amount("$141.67"), 141.67)
        self.assertEqual(parse_wex_amount("($1,684.42)"), -1684.42)
        self.assertEqual(parse_wex_amount("$0.00"), 0.0)
        self.assertEqual(parse_wex_amount(""), 0.0)

    def test_parse_date(self):
        """Test date parsing for multiple formats."""
        self.assertEqual(parse_date("10/16/2026"), date(2026, 10, 16))
        self.assertEqual(parse_date("2026-10-16"), date(2026, 10, 16))
        self.assertEqual(parse_date("2026-10-16T15:00:00Z"), date(2026, 10, 16))
        with self.assertRaises(ValueError):
            parse_date("invalid-date")

    def test_parse_synthetic_csv(self):
        """Test parsing synthetic WEX PaymentData.csv into Cash and Investment accounts."""
        accounts = parse_payment_data_csv(SAMPLE_SYNTHETIC_CSV, account_number="9999")
        self.assertIn("cash", accounts)
        self.assertIn("investment", accounts)

        cash = accounts["cash"]
        investment = accounts["investment"]

        self.assertEqual(len(cash.transactions), 4)
        self.assertEqual(cash.account_number, "9999")
        self.assertEqual(cash.slug, "wex_hsa_cash_9999")

        # Investment account should receive the $500 transfer
        self.assertEqual(len(investment.transactions), 1)
        self.assertEqual(investment.transactions[0]["amount"], 500.00)
        self.assertEqual(investment.transactions[0]["date"], "10/16/2026")

    def test_compute_daily_balances_continuous(self):
        """Test continuous daily balances for both cash and investment accounts."""
        accounts = parse_payment_data_csv(SAMPLE_SYNTHETIC_CSV, account_number="9999")
        cash = accounts["cash"]
        investment = accounts["investment"]

        # Compute from 2026-09-01 to 2026-10-17
        cash_daily = cash.compute_daily_balances(
            start_date=date(2026, 9, 1), end_date=date(2026, 10, 17)
        )
        self.assertEqual(len(cash_daily), 47)  # Sept (30) + Oct 1-17 (17) = 47 days

        # Check key balance points
        # On 09/01: $999.50
        day_sept1 = [d for d in cash_daily if d["date"] == "2026-09-01"][0]
        self.assertEqual(day_sept1["balance"], 999.50)

        # On 09/15: $1,999.50
        day_sept15 = [d for d in cash_daily if d["date"] == "2026-09-15"][0]
        self.assertEqual(day_sept15["balance"], 1999.50)

        # On 09/30: $2,000.00
        day_sept30 = [d for d in cash_daily if d["date"] == "2026-09-30"][0]
        self.assertEqual(day_sept30["balance"], 2000.00)

        # On 10/16 after transfer: $1,500.00
        day_oct16 = [d for d in cash_daily if d["date"] == "2026-10-16"][0]
        self.assertEqual(day_oct16["balance"], 1500.00)

        # Investment daily balances
        inv_daily = investment.compute_daily_balances(
            start_date=date(2026, 9, 1), end_date=date(2026, 10, 17)
        )
        self.assertEqual(len(inv_daily), 47)

        # Before 10/16: 0.00
        day_inv_oct15 = [d for d in inv_daily if d["date"] == "2026-10-15"][0]
        self.assertEqual(day_inv_oct15["balance"], 0.00)

        # On 10/16: 500.00
        day_inv_oct16 = [d for d in inv_daily if d["date"] == "2026-10-16"][0]
        self.assertEqual(day_inv_oct16["balance"], 500.00)


if __name__ == "__main__":
    unittest.main()
