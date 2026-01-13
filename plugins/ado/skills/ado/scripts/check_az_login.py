#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
Check if user is logged in to Azure CLI with access to Azure DevOps.

Usage:
    uv run check_az_login.py

Exit codes:
    0 - Logged in and has Azure DevOps access
    1 - Not logged in or no Azure DevOps access
"""

import subprocess
import json
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check_az_cli_installed():
    """Check if Azure CLI is installed."""
    result = subprocess.run(
        ["az", "--version"],
        capture_output=True,
        text=True,
        shell=True
    )
    return result.returncode == 0


def check_az_logged_in():
    """Check if user is logged in to Azure CLI."""
    result = subprocess.run(
        ["az", "account", "show"],
        capture_output=True,
        text=True,
        shell=True
    )
    if result.returncode != 0:
        return False, None

    try:
        account = json.loads(result.stdout)
        return True, account
    except json.JSONDecodeError:
        return False, None


def check_devops_access():
    """Check if user has Azure DevOps access by getting a token."""
    resource = "499b84ac-1321-427f-aa17-267ca6975798"

    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource],
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        return False, None

    try:
        token_data = json.loads(result.stdout)
        return True, token_data.get("expiresOn")
    except json.JSONDecodeError:
        return False, None


def main():
    # Check if az CLI is installed
    if not check_az_cli_installed():
        print("STATUS: NOT_INSTALLED")
        print("ACTION: Install Azure CLI from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)

    # Check if logged in
    logged_in, account = check_az_logged_in()
    if not logged_in:
        print("STATUS: NOT_LOGGED_IN")
        print("ACTION: Run `az login`")
        sys.exit(1)

    user_name = account.get("user", {}).get("name", "Unknown")

    # Check Azure DevOps access
    has_devops, _ = check_devops_access()
    if not has_devops:
        print("STATUS: NO_DEVOPS_ACCESS")
        print(f"USER: {user_name}")
        print("ACTION: Run `az login` with an account that has Azure DevOps access")
        sys.exit(1)

    print("STATUS: READY")
    print(f"USER: {user_name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
