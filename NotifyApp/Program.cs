using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Speech.Synthesis;
using System.Text.Json;

// --hook mode: read JSON from stdin, spawn speech in background, return immediately
if (args.Length > 0 && args[0] == "--hook")
{
    var json = Console.In.ReadToEnd();
    var message = ProcessHook(json, out var cwd);

    // Clean up tmpclaude-* temp files created by Claude Code hooks
    CleanupTempFiles(cwd);

    if (!string.IsNullOrEmpty(message))
    {
        // Only speak if Claude Code window is NOT in focus
        if (!IsTerminalInFocus())
        {
            // Spawn detached process to speak (fire and forget)
            var exePath = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName;
            if (exePath != null)
            {
                var psi = new ProcessStartInfo(exePath, $"\"{message}\"")
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardInput = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                Process.Start(psi);
            }
        }
    }
    return;
}

// --list-voices flag
if (args.Length > 0 && args[0] == "--list-voices")
{
    using var synth = new SpeechSynthesizer();
    Console.WriteLine("Available voices:");
    foreach (var v in synth.GetInstalledVoices().Where(v => v.Enabled))
        Console.WriteLine($"  - {v.VoiceInfo.Name} ({v.VoiceInfo.Gender}, {v.VoiceInfo.Culture})");
    return;
}

// Direct message mode
var messageArgs = args.ToList();
string? requestedVoice = null;

for (int i = 0; i < messageArgs.Count - 1; i++)
{
    if (messageArgs[i] == "--voice")
    {
        requestedVoice = messageArgs[i + 1];
        messageArgs.RemoveRange(i, 2);
        break;
    }
}

var msg = messageArgs.Count > 0 ? string.Join(" ", messageArgs) : "Hello! This is a notification.";
Speak(msg, requestedVoice);

// === Functions ===

static void Speak(string message, string? voice = null)
{
    using var synthesizer = new SpeechSynthesizer();
    synthesizer.SetOutputToDefaultAudioDevice();

    var voices = synthesizer.GetInstalledVoices().Where(v => v.Enabled).ToList();

    if (voice != null)
    {
        var v = voices.FirstOrDefault(x => x.VoiceInfo.Name.Contains(voice, StringComparison.OrdinalIgnoreCase));
        if (v != null) synthesizer.SelectVoice(v.VoiceInfo.Name);
    }
    else
    {
        var preferred = new[] { "Sonia", "Natural", "Jenny Online", "Aria Online", "Ana Online", "Zira", "David" };
        foreach (var p in preferred)
        {
            var v = voices.FirstOrDefault(x => x.VoiceInfo.Name.Contains(p, StringComparison.OrdinalIgnoreCase));
            if (v != null) { synthesizer.SelectVoice(v.VoiceInfo.Name); break; }
        }
    }

    synthesizer.Speak(message);
}

static string? ProcessHook(string json, out string? cwd)
{
    cwd = null;
    try
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        var hookEvent = root.GetProperty("hook_event_name").GetString();
        cwd = root.TryGetProperty("cwd", out var cwdProp) ? cwdProp.GetString() : null;

        // Get context: worktree > branch > folder (fast)
        var context = GetContext(cwd);
        var prefix = !string.IsNullOrEmpty(context) ? $"{context}, " : "";

        return hookEvent switch
        {
            "Notification" => ProcessNotification(root, prefix),
            "Stop" => $"{prefix}done",
            "SubagentStop" => $"{prefix}done",
            "PreToolUse" => ProcessToolUse(root, prefix),
            _ => null
        };
    }
    catch { return null; }
}

static string? ProcessNotification(JsonElement root, string prefix)
{
    var type = root.TryGetProperty("notification_type", out var t) ? t.GetString() : null;
    var msg = root.TryGetProperty("message", out var m) ? m.GetString() : null;

    return type switch
    {
        "permission_prompt" => $"{prefix}permission needed",
        "idle_prompt" => $"{prefix}waiting",
        "auth_success" => $"{prefix}authenticated",
        _ => !string.IsNullOrEmpty(msg) ? $"{prefix}{msg}" : null
    };
}

static string? ProcessToolUse(JsonElement root, string prefix)
{
    var toolName = root.TryGetProperty("tool_name", out var tn) ? tn.GetString() : null;
    if (toolName != "AskUserQuestion") return null;

    if (root.TryGetProperty("tool_input", out var input) &&
        input.TryGetProperty("questions", out var questions) &&
        questions.GetArrayLength() > 0)
    {
        var q = questions[0].GetProperty("question").GetString();
        return $"{prefix}question, {q}";
    }
    return $"{prefix}question";
}

static string? GetContext(string? cwd)
{
    if (string.IsNullOrEmpty(cwd) || !Directory.Exists(cwd)) return null;

    try
    {
        // Check for worktree (fast: just check if .git is a file pointing elsewhere)
        var gitPath = Path.Combine(cwd, ".git");
        if (File.Exists(gitPath)) // Worktree has .git as file
            return Path.GetFileName(cwd);

        // Get branch name (fast git command)
        var psi = new ProcessStartInfo("git", "branch --show-current")
        {
            WorkingDirectory = cwd,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var proc = Process.Start(psi);
        if (proc != null)
        {
            var branch = proc.StandardOutput.ReadToEnd().Trim();
            proc.WaitForExit(500); // Max 500ms
            if (!string.IsNullOrEmpty(branch)) return branch;
        }
    }
    catch { }

    // Fallback: folder name
    return Path.GetFileName(cwd);
}

static void CleanupTempFiles(string? cwd)
{
    if (string.IsNullOrEmpty(cwd) || !Directory.Exists(cwd)) return;

    try
    {
        foreach (var file in Directory.GetFiles(cwd, "tmpclaude-*-cwd"))
        {
            try { File.Delete(file); } catch { }
        }
    }
    catch { }
}

// Windows API for focus detection
[DllImport("user32.dll")]
static extern IntPtr GetForegroundWindow();

[DllImport("user32.dll")]
static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

static bool IsTerminalInFocus()
{
    try
    {
        var foregroundWindow = GetForegroundWindow();
        if (foregroundWindow == IntPtr.Zero) return false;

        GetWindowThreadProcessId(foregroundWindow, out uint foregroundPid);

        // Fast: check if foreground process is a known terminal
        using var proc = Process.GetProcessById((int)foregroundPid);
        var name = proc.ProcessName.ToLowerInvariant();

        // Known terminal process names
        return name switch
        {
            "windowsterminal" => true,
            "cmd" => true,
            "powershell" => true,
            "pwsh" => true,
            "conhost" => true,
            "mintty" => true,
            "git-bash" => true,
            "wezterm-gui" => true,
            "alacritty" => true,
            "wt" => true,
            _ => false
        };
    }
    catch { return false; }
}
