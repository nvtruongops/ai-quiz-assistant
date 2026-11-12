import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
import path_utils


class TestAppDataRuntimePaths(unittest.TestCase):
    def test_frozen_runtime_migrates_legacy_data_without_deleting_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdata = os.path.join(tmp, "Roaming")
            install_dir = os.path.join(tmp, "Program Files", "QuizAssistant")
            os.makedirs(install_dir)
            for name, content in ((".env", "GEMINI_API_KEY=legacy\n"), ("config.json", '{"theme":"legacy"}')):
                with open(os.path.join(install_dir, name), "w", encoding="utf-8") as f:
                    f.write(content)
            os.makedirs(os.path.join(install_dir, "logs"))
            with open(os.path.join(install_dir, "logs", "app.log"), "w", encoding="utf-8") as f:
                f.write("legacy log")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", os.path.join(install_dir, "QuizAssistant.exe")), \
                 patch.dict(os.environ, {"APPDATA": appdata}, clear=False):
                app_dir = path_utils.get_app_dir()

            self.assertEqual(app_dir, os.path.join(appdata, "AI Quiz Assistant"))
            self.assertTrue(os.path.isfile(os.path.join(app_dir, ".env")))
            self.assertTrue(os.path.isfile(os.path.join(app_dir, "config.json")))
            self.assertTrue(os.path.isfile(os.path.join(app_dir, "logs", "app.log")))
            self.assertTrue(os.path.isfile(os.path.join(install_dir, ".env")))

    def test_existing_appdata_config_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = os.path.join(tmp, "Install")
            appdata = os.path.join(tmp, "Roaming")
            target = os.path.join(appdata, "AI Quiz Assistant")
            os.makedirs(install_dir)
            os.makedirs(target)
            with open(os.path.join(install_dir, ".env"), "w", encoding="utf-8") as f:
                f.write("GEMINI_API_KEY=old\n")
            with open(os.path.join(target, ".env"), "w", encoding="utf-8") as f:
                f.write("GEMINI_API_KEY=current\n")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", os.path.join(install_dir, "QuizAssistant.exe")), \
                 patch.dict(os.environ, {"APPDATA": appdata}, clear=False):
                path_utils.get_app_dir()

            with open(os.path.join(target, ".env"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "GEMINI_API_KEY=current\n")

    def test_source_mode_uses_repository_root(self):
        self.assertEqual(path_utils.get_app_dir(), os.path.dirname(os.path.dirname(os.path.abspath(path_utils.__file__))))

    def test_frozen_resources_remain_in_meipass(self):
        with tempfile.TemporaryDirectory() as tmp:
            meipass = os.path.join(tmp, "_MEI")
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", os.path.join(tmp, "QuizAssistant.exe")), \
                 patch.object(sys, "_MEIPASS", meipass, create=True), \
                 patch.dict(os.environ, {"APPDATA": os.path.join(tmp, "Roaming")}, clear=False):
                self.assertEqual(path_utils.get_resource_path("assets/icon.png"), os.path.join(meipass, "assets", "icon.png"))


if __name__ == "__main__":
    unittest.main()
