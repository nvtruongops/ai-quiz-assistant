import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_exe
import setup


class TestSingleInstallerOutput(unittest.TestCase):
    def test_final_output_is_single_quizassistant_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = os.path.join(tmp, "dist")
            staging = os.path.join(tmp, "staging")
            os.makedirs(dist)
            os.makedirs(staging)
            staged = os.path.join(staging, "QuizAssistant-Installer.exe")
            with open(staged, "wb") as f:
                f.write(b"installer")
            for name in ("QuizAssistant.exe", "AI-Quiz-Assistant-Setup.exe", "portable.zip", "SHA256SUMS.txt"):
                with open(os.path.join(dist, name), "wb") as f:
                    f.write(b"old output")
            self.assertTrue(build_exe.finalize_distribution(dist, staged))
            self.assertEqual(os.listdir(dist), ["QuizAssistant.exe"])

    def test_missing_staged_installer_preserves_existing_dist(self):
        with tempfile.TemporaryDirectory() as dist:
            existing = os.path.join(dist, "old.txt")
            with open(existing, "w") as f:
                f.write("preserve")
            self.assertFalse(build_exe.finalize_distribution(dist, os.path.join(dist, "missing.exe")))
            self.assertTrue(os.path.isfile(existing))

    def test_clean_previous_builds_preserves_dist_until_new_build_exists(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "build"))
            dist = os.path.join(root, "dist")
            os.makedirs(dist)
            old_exe = os.path.join(dist, "QuizAssistant.exe")
            with open(old_exe, "wb") as f:
                f.write(b"old release")
            with patch.object(build_exe, "PROJECT_ROOT", root):
                build_exe.clean_previous_builds()
            self.assertTrue(os.path.isfile(old_exe))
            self.assertFalse(os.path.exists(os.path.join(root, "build")))

    def test_missing_app_executable_is_not_accepted(self):
        self.assertFalse(build_exe.has_required_app_executable("missing-app.exe"))

    def test_setup_shortcuts_do_not_target_distribution_installer(self):
        with open(setup.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn('os.path.join(PROJECT_ROOT, "dist", "QuizAssistant.exe")', source)
        self.assertIn('os.path.join(PROJECT_ROOT, "build", "app-dist", "QuizAssistant.exe")', source)


if __name__ == "__main__":
    unittest.main()
