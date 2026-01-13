---
name: notify-user
description: Use to send voice notifications to user. Notifications must be crisp and short.
---

# Voice Notification Skill

Send voice notifications to get the user's attention when they're not looking at the terminal.

## When to Use

- Task completed
- Question needs answering
- Permission required
- Error occurred that needs attention

## How to Notify

Run the NotifyApp with a **crisp, short message**:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/NotifyApp.exe" "<message>"
```

## Message Guidelines

**Keep messages SHORT and CRISP:**

| Good | Bad |
|------|-----|
| "done" | "The task has been completed successfully" |
| "question" | "I have a question for you" |
| "permission needed" | "I need your permission to proceed" |
| "error, check logs" | "An error occurred, please check the logs" |
| "tests passed" | "All tests have passed successfully" |
| "build failed" | "The build process has failed" |

**Format:** `"{context}, {action}"` where context is branch/folder name.

Examples:
- `"main, done"`
- `"feature-auth, question"`
- `"notify, tests passed"`

## List Available Voices

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/NotifyApp.exe" --list-voices
```

## Notes

- Notifications only play when terminal is NOT in focus
- Uses natural Windows TTS voices (Jenny, Aria, Sonia)
- Messages are spoken, not displayed - brevity is critical
