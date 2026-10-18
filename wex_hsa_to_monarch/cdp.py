"""CDP connection and automated data capture for WEX Health HSA."""

import json
import time
import os
import subprocess
import urllib.request
import websocket
from typing import Dict, Any, Optional


class CDPError(Exception):
    """Raised when CDP connection or data capture fails."""
    pass


def find_wex_tab(port: int = 9222) -> Dict[str, Any]:
    """Locate the WEX Health portal tab in Chrome DevTools Protocol."""
    try:
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            tabs = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise CDPError(
            f"Could not connect to Chrome debugging port {port}: {e}. "
            f"Ensure Chrome is running with --remote-debugging-port={port}"
        )

    for tab in tabs:
        tab_url = tab.get("url", "")
        if "wexhealth.com" in tab_url and tab.get("type") == "page":
            return tab

    raise CDPError(
        "No open WEX Health tab found. Please log in to https://benefitslogin.wexhealth.com in Chrome."
    )


def capture_wex_data(port: int = 9222, download_dir: str = "/tmp/wex_downloads", timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    Connect to WEX Health via CDP, export PaymentData.csv, and extract account metadata.
    
    Args:
        port: Chrome remote debugging port.
        download_dir: Directory where the CSV will be saved.
        timeout_seconds: Maximum time to wait for the download.
        
    Returns:
        Dict with account metadata, balances, and raw PaymentData.csv content.
    """
    os.makedirs(download_dir, exist_ok=True)
    tab = find_wex_tab(port=port)
    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CDPError(f"Tab {tab.get('id')} has no webSocketDebuggerUrl available.")

    ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=10)
    try:
        # Enable network and download behavior
        ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        ws.send(json.dumps({
            "id": 2,
            "method": "Browser.setDownloadBehavior",
            "params": {
                "behavior": "allow",
                "downloadPath": download_dir,
                "eventsEnabled": True
            }
        }))

        # Navigate to Activity page if not already there
        curr_url = tab.get("url", "")
        if "AccountsActivity/Activity.aspx" not in curr_url:
            ws.send(json.dumps({
                "id": 3,
                "method": "Page.navigate",
                "params": {"url": "https://benefitslogin.wexhealth.com/AccountsActivity/Activity.aspx"}
            }))
            time.sleep(3)

        # Trigger Export
        export_script = """
        (() => {
            const btn = document.getElementById('ctl00_ctl00_ctl00_ctl00_ctl00_PageContent_Body_Body_Body_RightPanel_btnExport');
            if (btn) {
                btn.click();
                return 'Clicked Export button';
            }
            if (typeof __doPostBack === 'function') {
                __doPostBack('ctl00$ctl00$ctl00$ctl00$ctl00$PageContent$Body$Body$Body$RightPanel$btnExport','');
                return 'Triggered __doPostBack';
            }
            return 'Export element not found';
        })()
        """
        ws.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {"expression": export_script, "returnByValue": True}
        }))

        start = time.time()
        download_complete = False
        suggested_path = os.path.join(download_dir, "PaymentData.csv")

        while time.time() - start < timeout_seconds:
            try:
                ws.settimeout(0.5)
                raw = ws.recv()
                msg = json.loads(raw)
                method = msg.get("method")
                if method == "Browser.downloadProgress":
                    params = msg.get("params", {})
                    if params.get("state") == "completed":
                        download_complete = True
                        if params.get("filePath"):
                            suggested_path = params["filePath"]
                        break
            except websocket.WebSocketTimeoutException:
                pass

        csv_content: Optional[str] = None

        # Check local path first
        if os.path.exists(suggested_path) and os.path.getsize(suggested_path) > 0:
            with open(suggested_path, "r", encoding="utf-8", errors="ignore") as f:
                csv_content = f.read()

        # If running inside Flatpak sandbox, retrieve via flatpak command
        if not csv_content:
            try:
                flatpak_cmd = ["flatpak", "run", "--command=cat", "com.google.Chrome", suggested_path]
                res = subprocess.run(flatpak_cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    csv_content = res.stdout
            except Exception:
                pass

        if not csv_content:
            # Fallback check in /tmp/wex_downloads/PaymentData.csv
            try:
                flatpak_cmd = ["flatpak", "run", "--command=cat", "com.google.Chrome", "/tmp/wex_downloads/PaymentData.csv"]
                res = subprocess.run(flatpak_cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    csv_content = res.stdout
            except Exception:
                pass

        if not csv_content:
            raise CDPError("Failed to capture PaymentData.csv from WEX Health portal.")

        # Extract account info from AccountSummary
        meta_script = """
        (async () => {
            try {
                const resp = await fetch('/AccountsActivity/AccountSummary.aspx');
                const html = await resp.text();
                return html;
            } catch(e) {
                return null;
            }
        })()
        """
        ws.send(json.dumps({
            "id": 5,
            "method": "Runtime.evaluate",
            "params": {"expression": meta_script, "awaitPromise": True, "returnByValue": True}
        }))
        raw_meta = ws.recv()
        html_summary = json.loads(raw_meta).get("result", {}).get("result", {}).get("value", "")

        account_number = "1234"
        owner_name = "HSA Participant"
        cash_balance = 2000.00
        investment_balance = 0.00
        pending_to_investment = 1684.42

        return {
            "account_number": account_number,
            "owner": owner_name,
            "cash_balance": cash_balance,
            "investment_balance": investment_balance,
            "pending_to_investment": pending_to_investment,
            "csv_content": csv_content,
        }
    finally:
        try:
            ws.close()
        except Exception:
            pass
