---
name: install-natural-voices
description: Install NaturalVoiceSAPIAdapter to enable high-quality natural voices
---

# Install Natural Voices

This command installs NaturalVoiceSAPIAdapter to unlock Windows natural TTS voices.

## Steps

Run these commands in order:

### 1. Download the adapter

```bash
curl -L -o "$TEMP/NaturalVoiceSAPIAdapter.zip" "https://github.com/gexgd0419/NaturalVoiceSAPIAdapter/releases/download/v0.2.9/NaturalVoiceSAPIAdapter_v0.2.9_x86_x64.zip"
```

### 2. Extract the zip

```powershell
powershell.exe -Command "Expand-Archive -Path \"$env:TEMP\NaturalVoiceSAPIAdapter.zip\" -DestinationPath \"$env:TEMP\NaturalVoiceSAPIAdapter\" -Force"
```

### 3. Register the DLL (requires admin)

If Windows Defender blocks files, tell the user to allow them first in Windows Security → Protection history.

Then register with admin privileges:

```powershell
powershell.exe -Command "Start-Process regsvr32 -ArgumentList '$env:TEMP\NaturalVoiceSAPIAdapter\x64\NaturalVoiceSAPIAdapter.dll' -Verb RunAs"
```

### 4. Verify installation

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/NotifyApp.exe" --list-voices
```

Look for voices with "Online" in the name (e.g., "Microsoft Jenny Online").

## Notes

- **Antivirus warning**: This tool hooks into Windows SAPI - false positives are common
- **Admin required**: DLL registration needs elevated privileges
- **Restart apps**: Apps using TTS need restart after installation
