#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Get all Azure DevOps pull requests created by me.

Usage:
    uv run get_my_created_prs.py <organization> <project>

Example:
    uv run get_my_created_prs.py skype scc
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
    resource = "499b84ac-1321-427f-aa17-267ca6975798"

    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource],
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        print(f"Error getting token: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    token_data = json.loads(result.stdout)
    return token_data["accessToken"]


def get_current_user_id(organization, token):
    """Get the current authenticated user's ID."""
    url = f"https://vssps.dev.azure.com/{organization}/_apis/profile/profiles/me?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("id")


def get_pull_requests_by_creator(organization, project, creator_id, token):
    """Get all active pull requests created by user."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "searchCriteria.creatorId": creator_id,
        "searchCriteria.status": "active",
        "$top": 100,
        "api-version": "7.1"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json().get("value", [])


def get_vote_status(vote):
    """Convert vote number to status string."""
    vote_map = {
        10: "Approved",
        5: "Approved with suggestions",
        0: "No vote",
        -5: "Waiting for author",
        -10: "Rejected"
    }
    return vote_map.get(vote, f"Unknown ({vote})")


def get_overall_status(reviewers):
    """Get overall review status from all reviewers."""
    if not reviewers:
        return "No reviewers"

    votes = [r.get("vote", 0) for r in reviewers]

    if any(v == -10 for v in votes):
        return "Rejected"
    if any(v == -5 for v in votes):
        return "Waiting for author"
    if all(v >= 5 for v in votes) and votes:
        return "All approved"
    if any(v >= 5 for v in votes):
        return "Partially approved"
    return "Pending review"


def print_pull_requests(prs):
    """Print pull requests in LLM-friendly markdown format."""
    if not prs:
        print("No PRs created by you.")
        return

    print(f"# My Created PRs ({len(prs)})")
    print("")

    for pr in prs:
        pr_id = pr.get("pullRequestId", "N/A")
        title = pr.get("title", "N/A")
        repo = pr.get("repository", {}).get("name", "N/A")
        source_branch = pr.get("sourceRefName", "").replace("refs/heads/", "")
        target_branch = pr.get("targetRefName", "").replace("refs/heads/", "")

        reviewers = pr.get("reviewers", [])
        overall_status = get_overall_status(reviewers)

        reviewer_summary = ", ".join([f"{r.get('displayName', '?')}: {get_vote_status(r.get('vote', 0))}" for r in reviewers]) or "None"

        print(f"- **PR #{pr_id}**: {title}")
        print(f"  - Repo: {repo} | {source_branch} -> {target_branch}")
        print(f"  - Status: {overall_status} | Reviewers: {reviewer_summary}")


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run get_my_created_prs.py <org> <project>", file=sys.stderr)
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]

    print("Fetching PRs...", file=sys.stderr)
    token = get_azure_token()

    user_id = get_current_user_id(organization, token)
    if not user_id:
        print("Error: Could not get current user ID", file=sys.stderr)
        sys.exit(1)

    prs = get_pull_requests_by_creator(organization, project, user_id, token)
    print_pull_requests(prs)


if __name__ == "__main__":
    main()
