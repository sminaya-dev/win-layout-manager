"""
WindowManager.py
----------------
A robust utility to snapshot and restore window layouts on Windows.
Demonstrates Win32 API interaction, process management, and OOP design in Python.
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import psutil
import win32con
import win32gui
import win32process
from screeninfo import Monitor, get_monitors

# Constants
CONFIG_FILE = "window_layout.json"
IGNORE_PROCESSES = ["python.exe", "cmd.exe", "powershell.exe", "SearchHost.exe"]


class WindowManager:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {"whitelist": [], "layouts": {}}

    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)
        print(f"💾 Configuration saved to {self.config_path}")

    def _get_monitors(self) -> List[Monitor]:
        return get_monitors()

    def _find_window_handle(self, process_name: str) -> Optional[int]:
        """Finds the main window handle (HWND) for a given process name."""
        found_hwnd = None

        def callback(hwnd, _):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)

                    # Special handling for File Explorer
                    if process_name.lower() == "explorer.exe":
                        if win32gui.GetClassName(hwnd) == "CabinetWClass":
                            found_hwnd = hwnd
                    elif proc.name().lower() == process_name.lower():
                        found_hwnd = hwnd
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        win32gui.EnumWindows(callback, None)
        return found_hwnd

    def detect_running_apps(self) -> List[Tuple[int, str]]:
        """Returns a list of (pid, name) for visible apps."""
        visible_apps = set()

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    if proc.name() not in IGNORE_PROCESSES:
                        visible_apps.add((proc.pid, proc.name()))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        win32gui.EnumWindows(callback, None)
        return sorted(list(visible_apps), key=lambda x: x[1].lower())

    def setup_whitelist(self):
        """Interactive wizard to select apps to manage."""
        apps = self.detect_running_apps()
        print("\n=== Detected Running Applications ===")
        for i, (_, name) in enumerate(apps):
            status = "✅" if name in self.config["whitelist"] else "  "
            print(f"{status} [{i}] {name}")

        print("\nEnter comma-separated indices to TOGGLE whitelist (e.g. '1,3,5').")
        print("Press ENTER to finish.")

        selection = input("> ").strip()
        if not selection:
            return

        indices = [int(s) for s in selection.split(",") if s.strip().isdigit()]

        for idx in indices:
            if 0 <= idx < len(apps):
                name = apps[idx][1]
                if name in self.config["whitelist"]:
                    self.config["whitelist"].remove(name)
                else:
                    self.config["whitelist"].append(name)

        self._save_config()

    def snapshot_layout(self):
        """
        Captures the current size and position of all whitelisted apps.
        Calculates relative offsets based on which monitor the app is on.
        """
        whitelist = self.config.get("whitelist", [])
        if not whitelist:
            print("⚠️ Whitelist is empty. Run 'setup' first.")
            return

        monitors = self._get_monitors()
        layouts = {}

        for app_name in whitelist:
            hwnd = self._find_window_handle(app_name)
            if not hwnd:
                print(f"⚠️ {app_name} is not running. Skipping.")
                continue

            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            # Determine which monitor contains the window center
            center_x = left + (width // 2)
            center_y = top + (height // 2)

            matched_monitor_idx = 0
            for i, m in enumerate(monitors):
                if (m.x <= center_x < m.x + m.width) and (
                    m.y <= center_y < m.y + m.height
                ):
                    matched_monitor_idx = i
                    break

            monitor = monitors[matched_monitor_idx]

            # Calculate offset relative to that monitor's top-left
            offset_x = left - monitor.x
            offset_y = top - monitor.y

            layouts[app_name] = {
                "monitor_index": matched_monitor_idx,
                "width": width,
                "height": height,
                "offset_x": offset_x,
                "offset_y": offset_y,
            }
            print(f"📸 Snapshotted {app_name} on Monitor {matched_monitor_idx}")

        self.config["layouts"] = layouts
        self._save_config()

    def restore_layout(self):
        """Applies the saved layout to running applications."""
        layouts = self.config.get("layouts", {})
        if not layouts:
            print("⚠️ No layouts found. Arrange your windows and run 'snapshot' first.")
            return

        monitors = self._get_monitors()

        for app_name, data in layouts.items():
            hwnd = self._find_window_handle(app_name)
            if not hwnd:
                print(f"💤 {app_name} is not running.")
                continue

            monitor_idx = data["monitor_index"]
            if monitor_idx >= len(monitors):
                print(f"❌ Monitor {monitor_idx} not found for {app_name}. Skipping.")
                continue

            monitor = monitors[monitor_idx]

            # Calculate absolute coordinates
            abs_x = monitor.x + data["offset_x"]
            abs_y = monitor.y + data["offset_y"]
            width = data["width"]
            height = data["height"]

            # Win32 API calls to move window
            # SWP_NOZORDER (0x0004) ignores z-order (doesn't force to top)
            # SWP_SHOWWINDOW (0x0040) ensures it's visible
            flags = win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW

            win32gui.SetWindowPos(hwnd, None, abs_x, abs_y, width, height, flags)

            # Force redraw to prevent graphical glitches (common with Electron apps like Discord/VSCode)
            win32gui.InvalidateRect(hwnd, None, True)

            print(f"✨ Restored {app_name} -> Mon {monitor_idx} @ {width}x{height}")


def main():
    parser = argparse.ArgumentParser(description="Windows Layout Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Interactively select apps to manage")
    subparsers.add_parser(
        "snapshot", help="Save current window positions of whitelisted apps"
    )
    subparsers.add_parser("restore", help="Move windows back to saved positions")

    args = parser.parse_args()
    mgr = WindowManager()

    if args.command == "setup":
        mgr.setup_whitelist()
    elif args.command == "snapshot":
        mgr.snapshot_layout()
    elif args.command == "restore":
        mgr.restore_layout()


if __name__ == "__main__":
    main()