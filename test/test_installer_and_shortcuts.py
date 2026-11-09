"""
Unit tests for Windows Shortcut Manager, Setup Installer, and Multi-resolution Icon
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src and root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from PIL import Image
from shortcut_manager import (
    get_default_install_dir,
    get_desktop_dir,
    get_start_menu_dir,
    create_windows_shortcut,
    generate_uninstaller_script
)
from installer import get_available_disk_space_gb, SetupInstallerApp


class TestShortcutManager(unittest.TestCase):
    def test_get_default_install_dir(self):
        d = get_default_install_dir()
        self.assertIsInstance(d, str)
        self.assertIn("AI Quiz Assistant", d)
        self.assertTrue(os.path.isabs(d))

    def test_get_desktop_dir(self):
        d = get_desktop_dir()
        self.assertIsInstance(d, str)
        self.assertTrue(os.path.exists(d))

    def test_get_start_menu_dir(self):
        d = get_start_menu_dir()
        self.assertIsInstance(d, str)
        self.assertTrue(os.path.exists(d) or "Programs" in d)

    def test_create_shortcut_nonexistent_target(self):
        ok, msg = create_windows_shortcut("nonexistent_binary_xyz.exe", "test.lnk")
        self.assertFalse(ok)
        self.assertIn("does not exist", msg)

    def test_generate_uninstaller_script(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = generate_uninstaller_script(tmp_dir)
            self.assertTrue(os.path.exists(script_path))
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("AI Quiz Assistant", content)
            self.assertIn("HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall", content)


class TestMultiResolutionIcon(unittest.TestCase):
    def test_icon_resolutions(self):
        ico_path = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
        self.assertTrue(os.path.exists(ico_path), "assets/icon.ico must exist")

        with Image.open(ico_path) as im:
            sizes = im.info.get("sizes", set())
            # Verify essential Windows resolutions are included
            self.assertIn((16, 16), sizes)
            self.assertIn((32, 32), sizes)
            self.assertIn((48, 48), sizes)
            self.assertIn((256, 256), sizes)
            self.assertGreaterEqual(len(sizes), 5)


class TestInstallerApp(unittest.TestCase):
    def test_get_available_disk_space(self):
        space = get_available_disk_space_gb(PROJECT_ROOT)
        self.assertIsInstance(space, float)
        self.assertGreater(space, 0.0)

    def test_installer_init_gui(self):
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            installer_app = SetupInstallerApp(root)
            self.assertEqual(installer_app.current_step, 1)
            self.assertTrue(installer_app.create_desktop_var.get())
            self.assertTrue(installer_app.create_start_menu_var.get())
            self.assertTrue(installer_app.launch_app_var.get())
            root.destroy()
        except tk.TclError:
            # Headless environment fallback
            pass


if __name__ == "__main__":
    unittest.main()
