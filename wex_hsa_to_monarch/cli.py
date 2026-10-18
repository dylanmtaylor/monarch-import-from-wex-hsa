"""Command Line Interface for wex-hsa-to-monarch."""

import argparse
import sys
import os

from wex_hsa_to_monarch.cdp import capture_wex_data, CDPError
from wex_hsa_to_monarch.parser import parse_payment_data_csv
from wex_hsa_to_monarch.exporter import Exporter


def run_pipeline(
    port: int = 9222,
    output_dir: str = "output",
    input_file: str = None,
):
    """Run full automated pipeline from Chrome CDP or local file to Monarch CSVs."""
    os.makedirs(output_dir, exist_ok=True)
    csv_content = None
    account_number = "1234"

    if input_file and os.path.exists(input_file):
        print(f"Reading WEX payment data from '{input_file}'...")
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            csv_content = f.read()
    else:
        print(f"Connecting to Chrome on port {port} to capture WEX Health HSA data...")
        try:
            session = capture_wex_data(port=port)
            csv_content = session["csv_content"]
            account_number = session.get("account_number", "1234")
            print(f"Captured WEX HSA data for account {account_number} ({session.get('owner', '')}).")
        except CDPError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print("Parsing transactions and computing daily balance histories...")
    accounts = parse_payment_data_csv(csv_content, account_number=account_number)

    exporter = Exporter(output_dir=output_dir)
    exporter.export_all(accounts)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="wex-hsa-to-monarch",
        description="Extract WEX Health HSA transactions and daily balance history into Monarch Money CSV format.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: all
    p_all = subparsers.add_parser("all", help="Full automated capture and export pipeline")
    p_all.add_argument("--port", type=int, default=9222, help="Chrome remote debugging port (default: 9222)")
    p_all.add_argument("--output-dir", type=str, default="output", help="Directory for Monarch CSVs (default: output)")
    p_all.add_argument("--input-file", type=str, default=None, help="Path to an existing PaymentData.csv")

    # Command: convert
    p_convert = subparsers.add_parser("convert", help="Convert an existing PaymentData.csv into Monarch CSVs")
    p_convert.add_argument("input_file", type=str, help="Path to PaymentData.csv")
    p_convert.add_argument("--output-dir", type=str, default="output", help="Directory for Monarch CSVs")
    p_convert.add_argument("--account-number", type=str, default="1234", help="Masked account number suffix")

    args = parser.parse_args()

    if args.command in (None, "all"):
        run_pipeline(
            port=getattr(args, "port", 9222),
            output_dir=getattr(args, "output_dir", "output"),
            input_file=getattr(args, "input_file", None),
        )
    elif args.command == "convert":
        if not os.path.exists(args.input_file):
            print(f"File not found: {args.input_file}", file=sys.stderr)
            sys.exit(1)

        with open(args.input_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        accounts = parse_payment_data_csv(content, account_number=args.account_number)
        exporter = Exporter(output_dir=args.output_dir)
        exporter.export_all(accounts)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
