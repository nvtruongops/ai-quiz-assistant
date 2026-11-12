import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import installer


class TestInstallerPayload(unittest.TestCase):
    def test_installer_does_not_deploy_docs_or_assets(self):
        with open(installer.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn('for icon_file in ["icon.ico", "icon.png"]', source)
        self.assertNotIn('for doc_file in [".env.example", "README.md", "README.txt"]', source)

    def test_frozen_installer_does_not_select_itself_as_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "QuizAssistant.exe")
            with open(exe, "wb") as f:
                f.write(b"installer")
            with patch.object(installer.sys, "executable", exe):
                self.assertEqual(installer.find_application_executable(tmp, tmp, frozen=True), "")

    def test_copy_application_executable_installs_app_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.exe")
            with open(source, "wb") as f:
                f.write(b"application")
            destination = os.path.join(tmp, "install")
            installed = installer.copy_application_executable(source, destination)
            self.assertEqual(installed, os.path.join(destination, "QuizAssistant.exe"))
            with open(installed, "rb") as f:
                self.assertEqual(f.read(), b"application")

    def test_copy_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.exe")
            with open(source, "wb") as f:
                f.write(b"application")
            with patch("installer.shutil.copy2", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    installer.copy_application_executable(source, os.path.join(tmp, "install"))


if __name__ == "__main__":
    unittest.main()
