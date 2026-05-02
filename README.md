# win-layout-manager

*Snapshot and restore your desktop window layout on Windows*

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows) ![Win32 API](https://img.shields.io/badge/Win32-API-orange)

---

## About

Multi-monitor setups often require repositioning the same apps every time you sit down — browser on the left monitor, terminal on the right, chat apps tucked in the corner. `WindowManager.py` eliminates that friction.

It uses the Win32 API to capture the exact position and size of your chosen apps relative to their monitor, saves that layout to a config file, and restores everything to its saved position with a single command. Window coordinates are stored as monitor-relative offsets, so the layout stays correct even if monitor positions shift.

---

## Features

- **Snapshot & restore** — capture your current window layout and restore it anytime with one command
- **Interactive setup wizard** — scans for visible desktop apps and lets you toggle which ones to manage
- **Multi-monitor aware** — stores positions relative to each monitor's top-left, not absolute screen coordinates
- **Electron app support** — forces a redraw after repositioning to prevent graphical glitches in apps like VS Code and Discord
- **File Explorer handling** — special-cases `explorer.exe` to target File Explorer windows specifically rather than the shell process
- **Persistent config** — layout is saved to `window_layout.json` alongside the script for easy portability

---

## Requirements

- Windows 10/11
- Python 3.8+
- Dependencies (install via pip):

```
pip install -r requirements.txt
```

---

## Usage

**Step 1 — Run setup to choose which apps to manage:**
```
python WindowManager.py setup
```
This scans for all visible desktop apps and presents a numbered list. Enter comma-separated indices to toggle apps in or out of your managed list.

**Step 2 — Arrange your windows, then snapshot the layout:**
```
python WindowManager.py snapshot
```
Captures the current size and position of all managed apps that are running.

**Step 3 — Restore your layout anytime:**
```
python WindowManager.py restore
```
Moves all managed apps back to their saved positions. Apps that aren't currently running are skipped gracefully.

---

## Technical Highlights

**Win32 API via pywin32**

Window discovery uses `win32gui.EnumWindows()` to walk all top-level windows, filtering for those that are both visible and enabled. Each window's process is resolved via `win32process.GetWindowThreadProcessId()` and `psutil.Process()`. Repositioning is done with `win32gui.SetWindowPos()` using `SWP_NOZORDER | SWP_SHOWWINDOW` flags to move windows without disrupting z-order.

**Monitor-relative coordinate storage**

Rather than storing absolute screen coordinates, the script calculates which monitor each window lives on by comparing the window's center point against each monitor's bounding rectangle. The saved offset is relative to that monitor's top-left corner — meaning layouts remain valid even if the OS reorders monitors or their virtual positions change.

**Electron app redraw fix**

Apps built on Electron (VS Code, Discord, Spotify) are known to render graphical artifacts after being programmatically repositioned. The script handles this by calling `win32gui.InvalidateRect()` and `win32gui.RedrawWindow()` after each `SetWindowPos()` call, forcing a clean repaint of the window surface.

**OOP design**

All functionality is encapsulated in a `WindowManager` class, keeping config management, window discovery, and layout logic cleanly separated. The CLI entry point is a thin `main()` function that delegates to class methods, making the core logic independently testable.

---

## Configuration

`window_layout.json` is auto-generated on first run and lives alongside the script. It is excluded from version control via `.gitignore` since it contains layout data specific to your personal setup.

Example structure:
```json
{
    "whitelist": ["brave.exe", "Code.exe", "Discord.exe"],
    "layouts": {
        "brave.exe": {
            "monitor_index": 0,
            "width": 1280,
            "height": 950,
            "offset_x": 15,
            "offset_y": 15
        }
    }
}
```

---

## License

[MIT](LICENSE)