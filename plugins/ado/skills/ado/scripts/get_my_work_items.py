#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Get all Azure DevOps work items assigned to the current user.
Uses Azure CLI token for authentication.

Usage:
    uv run get_my_work_items.py <organization> <project>

Example:
    uv run get_my_work_items.py mycompany MyProject
"""

import subprocess
import json
import sys
import requests

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_azure_token():
    """Get access token from Azure CLI for Azure DevOps."""
    # Azure DevOps resource ID
    resource = "499b84ac-1321-427f-aa17-267ca6975798"

    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource],
        capture_output=True,
        text=True,
        shell=True  # Required on Windows for .cmd files
    )

    if result.returncode != 0:
        print(f"Error getting token: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    token_data = json.loads(result.stdout)
    return token_data["accessToken"]


def query_work_items_wiql(organization, project, token):
    """Query work items assigned to the current user using WIQL."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/wiql?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # WIQL query to get work items assigned to @me
    wiql = {
        "query": """
            SELECT [System.Id]
            FROM workitems
            WHERE [System.AssignedTo] = @me
              AND [System.State] <> 'Closed'
              AND [System.State] <> 'Resolved'
              AND [System.State] <> 'Removed'
            ORDER BY [System.ChangedDate] DESC
        """
    }

    response = requests.post(url, headers=headers, json=wiql)
    response.raise_for_status()

    return response.json()


def get_work_item_details(organization, project, work_item_ids, token):
    """Get full details for a list of work item IDs using batch API."""
    if not work_item_ids:
        return []

    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitemsbatch?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Request specific fields
    body = {
        "ids": work_item_ids,
        "fields": [
            "System.Id",
            "System.Title",
            "System.State",
            "System.WorkItemType",
            "System.AssignedTo",
            "System.CreatedDate",
            "System.ChangedDate",
            "System.IterationPath",
            "System.AreaPath",
            "Microsoft.VSTS.Common.Priority"
        ]
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    return response.json().get("value", [])


def print_work_items(work_items):
    """Print work items in LLM-friendly markdown format."""
    if not work_items:
        print("No work items found.")
        return

    print(f"# My Work Items ({len(work_items)})")
    print("")

    for item in work_items:
        fields = item.get("fields", {})
        item_id = fields.get("System.Id", item.get("id", "N/A"))
        title = fields.get("System.Title", "N/A")
        state = fields.get("System.State", "N/A")
        work_type = fields.get("System.WorkItemType", "N/A")
        priority = fields.get("Microsoft.VSTS.Common.Priority", "-")

        print(f"- **#{item_id}** [{work_type}] {title} ({state}, P{priority})")


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run get_my_work_items.py <org> <project>", file=sys.stderr)
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]

    print(f"Fetching work items...", file=sys.stderr)
    token = get_azure_token()

    wiql_result = query_work_items_wiql(organization, project, token)
    work_item_refs = wiql_result.get("workItems", [])

    if not work_item_refs:
        print("No work items found.")
        return

    work_item_ids = [ref["id"] for ref in work_item_refs]

    # Get full details (batch API limit: 200)
    all_work_items = []
    for i in range(0, len(work_item_ids), 200):
        chunk = work_item_ids[i:i + 200]
        work_items = get_work_item_details(organization, project, chunk, token)
        all_work_items.extend(work_items)

    print_work_items(all_work_items)


if __name__ == "__main__":
    main()
