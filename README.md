# monarch-import-from-wex-hsa

Automated extraction and conversion tool for **WEX Health HSA** accounts (**Cash Account** and **Investment Account**) into **Monarch Money**-compatible CSV imports.

Connects to an authenticated WEX Health portal session in Google Chrome via Chrome DevTools Protocol (CDP), triggers the official transaction export, parses payroll deductions, employer contributions, interest, and investment sweep transfers, and exports:
1. **Continuous Daily Balance History** (`Date,Balance`) across all calendar days back to account inception, integrating verified end-of-day balances.
2. **Standard Transactions** (`Date,Merchant,Category,Account,Original Statement,Notes,Amount`) with automatic merchant cleaning and categorization for **Employee Payroll Deductions** (`HSA Contribution`), **Employer Contributions** (`Employer Match`), **Interest** (`Interest`), and **Investment Sweeps** (`Transfer`).
3. **Dual-Account Separation**: Accurately splits and reconciles the **WEX HSA Cash Account** and **WEX HSA Investment Account** (tracking cash sweeps into investment elections like HCB Interest Bearing Account / investments above cash thresholds).

---

## Features

- **Full Cash & Investment Support**:
  - Reconciles both the HSA Cash Account and HSA Investment Account into separate, dedicated Monarch CSVs.
  - Matches double-entry transfer records between cash and investment accounts.
- **Continuous Daily Balance Interpolation**:
  - Reconstructs uninterrupted daily balances forward-filled from account open date up to the present day, perfectly aligning with statement checkpoints.
- **Chrome CDP Session Extraction**:
  - Reuses your active, authenticated Chrome browser session via CDP (port `9222`) without requiring credential storage or password exposure.
- **Monarch Money Import Ready**:
  - Strict compliance with Monarch's CSV specifications for Balances (`Date,Balance`) and Transactions (`Date,Merchant,Category,Account,Original Statement,Notes,Amount`).
- **Zero PII Committed**:
  - All account numbers, financial amounts, raw JSON/CSV captures, and exported CSVs are safely excluded via `.gitignore`.

---

## Installation

```bash
git clone https://github.com/dylanmtaylor/monarch-import-from-wex-hsa.git
cd monarch-import-from-wex-hsa
pip install -e .
```

### Dependencies
- Python 3.9+
- `websocket-client>=1.6.0`

---

## Quickstart

### 1. Launch Chrome with Remote Debugging
Ensure Chrome is running with `--remote-debugging-port=9222` and log into [WEX Health](https://benefitslogin.wexhealth.com):

```bash
google-chrome --remote-debugging-port=9222
# or on Flatpak:
flatpak run com.google.Chrome --remote-debugging-port=9222
```

### 2. Run Capture & Convert
Run the automated pipeline to capture transaction data and generate Monarch CSVs:

```bash
wex-hsa-to-monarch all
# or directly via python:
python3 -m wex_hsa_to_monarch.cli all
```

To convert an existing `PaymentData.csv` export file:

```bash
wex-hsa-to-monarch convert PaymentData.csv --output-dir output
```

---

## Output Files

The tool generates separate CSVs for each account in the `output/` directory:

| File | Type | Description |
|---|---|---|
| `output/wex_hsa_balances_wex_hsa_cash_<suffix>.csv` | Balances | Daily balance series (`Date,Balance`) forward-filled from inception to today for Cash Account. |
| `output/wex_hsa_balances_wex_hsa_investment_<suffix>.csv` | Balances | Daily balance series (`Date,Balance`) for Investment Account. |
| `output/wex_hsa_transactions_wex_hsa_cash_<suffix>.csv` | Transactions | Cash Account transactions formatted for Monarch Money. |
| `output/wex_hsa_transactions_wex_hsa_investment_<suffix>.csv` | Transactions | Investment Account transactions formatted for Monarch Money. |
| `output/wex_hsa_transactions_all.csv` | Combined | All transactions across all WEX accounts sorted chronologically. |

---

## Importing into Monarch Money

1. **Daily Balances**:
   - Go to **Accounts** in Monarch Money.
   - Select your WEX HSA Cash or Investment account.
   - Click **Edit** -> **Upload balance history** and upload the corresponding balances CSV.
2. **Transactions**:
   - In the account page, click **Edit** -> **Upload transactions** and select the transactions CSV.

---

## Testing

Run the unit test suite (100% synthetic fixtures, zero network or PII dependencies):

```bash
python3 -m unittest discover tests -v
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
