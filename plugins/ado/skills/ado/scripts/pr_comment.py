#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Add comments to an Azure DevOps pull request.
Can reply to existing threads or create new comments on specific file lines.

Usage:
    Reply to a thread:
        uv run pr_comment.py <org> <project> <pr_id> reply <thread_id> "<comment>"

    Create new comment on file/line:
        uv run pr_comment.py <org> <project> <pr_id> new "<file_path>" <line_number> "<comment>"

    Create general PR comment:
        uv run pr_comment.py <org> <project> <pr_id> general "<comment>"

Examples:
    uv run pr_comment.py skype scc 1329388 reply 12345 "Good point, I'll fix this."
    uv run pr_comment.py skype scc 1329388 new "/src/main.cs" 42 "Consider refactoring this."
    uv run pr_comment.py skype scc 1329388 general "Overall looks good!"
"""

import subprocess
import json
import sys
from datetime import datetime
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


def get_pull_request_by_id(organization, project, pr_id, token):
    """Get pull request details by PR ID."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests/{pr_id}?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def reply_to_thread(organization, project, repo_id, pr_id, thread_id, comment_text, token):
    """Reply to an existing comment thread."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/threads/{thread_id}/comments?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "content": comment_text,
        "parentCommentId": 1,  # Reply to the first comment in the thread
        "commentType": 1  # Text comment
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    return response.json()


def create_file_comment(organization, project, repo_id, pr_id, file_path, start_line, end_line, comment_text, token):
    """Create a new comment thread on a specific file and line range."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/threads?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": comment_text,
                "commentType": 1  # Text comment
            }
        ],
        "status": 1,  # Active
        "threadContext": {
            "filePath": file_path,
            "rightFileStart": {
                "line": start_line,
                "offset": 1
            },
            "rightFileEnd": {
                "line": end_line,
                "offset": 1
            }
        }
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    return response.json()


def create_general_comment(organization, project, repo_id, pr_id, comment_text, token):
    """Create a general comment on the PR (not attached to a file)."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/threads?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": comment_text,
                "commentType": 1  # Text comment
            }
        ],
        "status": 1  # Active
        # No threadContext = general comment
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    return response.json()


def get_pr_threads(organization, project, repo_id, pr_id, token):
    """Get all comment threads for a pull request."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/threads?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("value", [])


def parse_timestamp(timestamp_str):
    """Parse ISO timestamp string to datetime."""
    # Handle various ISO formats
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    return None


def format_comments_for_llm(threads, since_timestamp=None):
    """Format comments in a compact LLM-friendly way."""
    actionable_threads = []

    for thread in threads:
        comments = thread.get("comments", [])
        user_comments = [c for c in comments if c.get("commentType") != "system"]
        if not user_comments:
            continue

        if since_timestamp:
            has_new = any(
                parse_timestamp(c.get("publishedDate", "")) and
                parse_timestamp(c.get("publishedDate", "")) > since_timestamp
                for c in user_comments
            )
            if not has_new:
                continue

        thread_id = thread.get("id")
        thread_context = thread.get("threadContext") or {}
        file_path = thread_context.get("filePath") if thread_context else None

        line_info = None
        if thread_context:
            start = (thread_context.get("rightFileStart") or {}).get("line")
            end = (thread_context.get("rightFileEnd") or {}).get("line")
            if start:
                line_info = f"{start}-{end}" if end and end != start else str(start)

        actionable_threads.append({
            "thread_id": thread_id,
            "file_path": file_path,
            "line_info": line_info,
            "status": thread.get("status", "unknown"),
            "comments": user_comments
        })

    if not actionable_threads:
        return "No comments found."

    output = [f"# PR Comments ({len(actionable_threads)} threads)", ""]

    for t in actionable_threads:
        loc = f"`{t['file_path']}:{t['line_info']}`" if t['file_path'] and t['line_info'] else (f"`{t['file_path']}`" if t['file_path'] else "General")
        output.append(f"## Thread #{t['thread_id']} - {loc} [{t['status']}]")

        for c in t['comments']:
            author = c.get("author", {}).get("displayName", "Unknown")
            text = c.get("content", "").strip()
            output.append(f"- **{author}**: {text}")

        output.append(f"Reply: `reply {t['thread_id']} \"...\"` | Action: `{t['file_path']}:{t['line_info']}`" if t['file_path'] else f"Reply: `reply {t['thread_id']} \"...\"` ")
        output.append("")

    return "\n".join(output)


def print_usage():
    """Print usage instructions."""
    print("Usage:")
    print("  Get comments (LLM-friendly format):")
    print('    uv run pr_comment.py <org> <project> <pr_id> get')
    print('    uv run pr_comment.py <org> <project> <pr_id> get --since "2026-01-13 10:00:00"')
    print("")
    print("  Reply to a thread:")
    print('    uv run pr_comment.py <org> <project> <pr_id> reply <thread_id> "<comment>"')
    print("")
    print("  Create new comment on file/line range:")
    print('    uv run pr_comment.py <org> <project> <pr_id> new "<file_path>" <start_line> <end_line> "<comment>"')
    print("")
    print("  Create general PR comment:")
    print('    uv run pr_comment.py <org> <project> <pr_id> general "<comment>"')
    print("")
    print("Examples:")
    print('  uv run pr_comment.py skype scc 1329388 get')
    print('  uv run pr_comment.py skype scc 1329388 get --since "2026-01-13"')
    print('  uv run pr_comment.py skype scc 1329388 reply 12345 "Good point!"')
    print('  uv run pr_comment.py skype scc 1329388 new "src/main.cs" 42 42 "Single line comment"')
    print('  uv run pr_comment.py skype scc 1329388 new "src/main.cs" 10 15 "Comment on lines 10-15"')
    print('  uv run pr_comment.py skype scc 1329388 general "LGTM!"')


def main():
    if len(sys.argv) < 5:
        print_usage()
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]
    pr_id = sys.argv[3]
    action = sys.argv[4].lower()

    # Get authentication token
    token = get_azure_token()

    # Get PR to find repo ID
    print(f"Fetching PR #{pr_id}...", file=sys.stderr)
    pr = get_pull_request_by_id(organization, project, pr_id, token)
    repo_id = pr.get("repository", {}).get("id")
    repo_name = pr.get("repository", {}).get("name")

    print(f"Repository: {repo_name}", file=sys.stderr)

    if action == "get":
        # Parse optional --since argument
        since_timestamp = None
        if len(sys.argv) >= 7 and sys.argv[5] == "--since":
            since_str = sys.argv[6]
            since_timestamp = parse_timestamp(since_str)
            if not since_timestamp:
                print(f"Error: Invalid timestamp format: {since_str}", file=sys.stderr)
                print("Use format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS", file=sys.stderr)
                sys.exit(1)

        threads = get_pr_threads(organization, project, repo_id, pr_id, token)
        output = format_comments_for_llm(threads, since_timestamp)
        print(output)

    elif action == "reply":
        if len(sys.argv) < 7:
            print("Error: reply requires <thread_id> and <comment>", file=sys.stderr)
            sys.exit(1)

        thread_id = sys.argv[5]
        comment_text = sys.argv[6]

        result = reply_to_thread(organization, project, repo_id, pr_id, thread_id, comment_text, token)
        print(f"OK: Comment #{result.get('id')} in thread #{thread_id}")

    elif action == "new":
        if len(sys.argv) < 9:
            print("Error: new requires <file_path> <start_line> <end_line> <comment>", file=sys.stderr)
            sys.exit(1)

        file_path = sys.argv[5]
        start_line = int(sys.argv[6])
        end_line = int(sys.argv[7])
        comment_text = sys.argv[8]

        # Fix Git Bash path expansion
        if ":" in file_path and "/" in file_path:
            for prefix in ["Program Files/Git", "Program Files (x86)/Git"]:
                if prefix in file_path:
                    file_path = file_path.split(prefix)[-1]
                    break

        if not file_path.startswith("/"):
            file_path = "/" + file_path

        result = create_file_comment(organization, project, repo_id, pr_id, file_path, start_line, end_line, comment_text, token)
        line_info = f"{start_line}" if start_line == end_line else f"{start_line}-{end_line}"
        print(f"OK: Thread #{result.get('id')} at {file_path}:{line_info}")

    elif action == "general":
        if len(sys.argv) < 6:
            print("Error: general requires <comment>", file=sys.stderr)
            sys.exit(1)

        comment_text = sys.argv[5]
        result = create_general_comment(organization, project, repo_id, pr_id, comment_text, token)
        print(f"OK: Thread #{result.get('id')} (general comment)")

    else:
        print(f"Error: Unknown action '{action}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
