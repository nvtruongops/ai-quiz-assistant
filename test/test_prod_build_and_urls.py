import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import constants
import path_utils
import build_exe


class TestProdBuildAndUrls(unittest.TestCase):

    def test_constants_defined(self):
        """Verify production URLs and metadata constants are properly defined"""
        self.assertEqual(constants.APP_VERSION, "2.0.0")
        self.assertTrue(constants.GITHUB_REPO_URL.startswith("https://github.com/"))
        self.assertTrue(constants.GITHUB_RELEASES_URL.startswith("https://github.com/"))
        self.assertTrue(constants.GOOGLE_AI_STUDIO_API_KEY_URL.startswith("https://aistudio.google.com/"))
        self.assertEqual(constants.DEFAULT_LOCAL_ENDPOINT_URL, "http://localhost:11434/v1")
        self.assertEqual(constants.DEFAULT_LOCAL_VISION_MODEL, "llama3.2-vision")
        self.assertIn("llama3.2-vision", constants.POPULAR_LOCAL_MODELS)

    def test_path_utils_normal_mode(self):
        """Verify path_utils returns expected paths in development mode"""
        self.assertFalse(path_utils.is_frozen())
        app_dir = path_utils.get_app_dir()
        self.assertTrue(os.path.isdir(app_dir))
        self.assertTrue(os.path.exists(os.path.join(app_dir, "run.pyw")))

        res_path = path_utils.get_resource_path(os.path.join("assets", "icon.png"))
        self.assertTrue(os.path.exists(res_path))

    def test_path_utils_frozen_simulation(self):
        """Verify path_utils behaves correctly in simulated PyInstaller frozen bundle"""
        fake_exe = r"C:\Program Files\QuizAssistant\QuizAssistant.exe"
        fake_temp = r"C:\Users\User\AppData\Local\Temp\_MEI123456"

        expected_app_dir = r"C:\Users\User\AppData\Roaming\AI Quiz Assistant"
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe), \
             patch.object(sys, '_MEIPASS', fake_temp, create=True), \
             patch.dict(os.environ, {"APPDATA": r"C:\Users\User\AppData\Roaming"}):

            self.assertTrue(path_utils.is_frozen())
            self.assertEqual(path_utils.get_app_dir(), expected_app_dir)

            res_path = path_utils.get_resource_path("assets/icon.png")
            expected_res = os.path.normpath(os.path.join(fake_temp, "assets/icon.png"))
            self.assertEqual(res_path, expected_res)

    def test_build_exe_sha256_calculation(self):
        """Verify calculate_sha256 computes consistent and valid hex digest"""
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"AI Quiz Assistant Production Build Test")
            temp_path = tf.name

        try:
            h = build_exe.calculate_sha256(temp_path)
            self.assertEqual(len(h), 64)
            # Precomputed SHA-256 of "AI Quiz Assistant Production Build Test"
            import hashlib
            expected = hashlib.sha256(b"AI Quiz Assistant Production Build Test").hexdigest()
            self.assertEqual(h, expected)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_prerequisites_check(self):
        """Verify check_prerequisites finds all repository build assets"""
        ok = build_exe.check_prerequisites()
        self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main()
