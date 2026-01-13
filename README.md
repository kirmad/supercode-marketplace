# Claude Code Notify

Voice notifications for Claude Code - speaks alerts when the terminal window is not in focus.

## Features

- **Natural voices** - Uses Microsoft natural TTS voices (Jenny, Aria, Sonia)
- **Smart focus detection** - Only speaks when Claude Code window is not in focus
- **Context aware** - Announces worktree/branch/folder name
- **Fast** - Async speech, minimal latency
- **Short phrases** - Quick notifications like "notify, done" or "main, question"

## Events

| Event | Voice Output |
|-------|--------------|
| Stop | "{context}, done" |
| AskUserQuestion | "{context}, question, {question}" |
| Notification (permission) | "{context}, permission needed" |
| Notification (idle) | "{context}, waiting" |

## Installation

### From Marketplace

```
/plugin marketplace add kirmad/supercode-marketplace
/plugin install notify-windows@supercode-marketplace
```

### Manual

1. Clone this repo
2. Run `dotnet publish -c Release -r win-x64 --no-self-contained -o bin` in NotifyApp folder
3. Copy to your Claude Code plugins directory

## Requirements

- Windows 10/11
- .NET 9 Runtime

## Enabling Natural Voices

By default, Windows only exposes basic voices (David, Zira) to apps. To use high-quality natural voices (Jenny, Aria, Sonia):

### Step 1: Install Natural Voices in Windows

1. Open **Settings > Time & Language > Speech**
2. Under "Manage voices", click **Add voices**
3. Install voices like:
   - Microsoft Jenny Online (Natural)
   - Microsoft Aria Online (Natural)
   - Microsoft Sonia Online (Natural, British)

### Step 2: Install NaturalVoiceSAPIAdapter

Windows restricts natural voices to Narrator only. This tool unlocks them for all apps:

1. Download from [NaturalVoiceSAPIAdapter](https://github.com/gexgd0419/NaturalVoiceSAPIAdapter/releases)
2. Run the installer
3. Restart any apps using TTS

After installation, natural voices like "Microsoft Jenny Online" will be available to the notify plugin.

## Skills

- `notify-windows:notify-user` - Guides Claude to send crisp voice notifications

## Configuration

The plugin uses these voice preferences (in order):
1. Sonia (British Natural)
2. Natural voices
3. Jenny Online
4. Aria Online
5. Ana Online
6. Zira (fallback)
7. David (fallback)

## License

MIT
