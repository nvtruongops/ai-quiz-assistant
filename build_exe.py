#!/usr/bin/env python3
"""
Production Build Script for AI Quiz Assistant 2.0
- Validates build environment and dependencies
- Compiles standalone Windows executable (QuizAssistant.exe) via PyInstaller
- Bundles assets, version metadata, and production configuration
- Assembles clean portable distribution package with SHA-256 checksums
"""

import os
import sys
import shutil
import hashlib
import subprocess
import time
from pathlib import Path

# Add src to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

try:
    from constants import APP_NAME, APP_VERSION, APP_DISPLAY_NAME, GITHUB_REPO_URL, GITHUB_RELEASES_URL, DOCUMENTATION_URL
except ImportError:
    APP_NAME = "AI Quiz Assistant"
    APP_VERSION = "2.0.0"
    APP_DISPLAY_NAME = f"{APP_NAME} {APP_VERSION}"
    GITHUB_REPO_URL = "https://github.com/nvtruongops/ai-quiz-assistant"
    GITHUB_RELEASES_URL = "https://github.com/nvtruongops/ai-quiz-assistant/releases"
    DOCUMENTATION_URL = "https://github.com/nvtruongops/ai-quiz-assistant#readme"


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_prerequisites() -> bool:
    """Verify build tools and required assets exist."""
    print("🔍 [1/5] Checking prerequisites...")
    
    # 1. PyInstaller check
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__} detected")
    except ImportError:
        print("  ❌ PyInstaller not found. Installing via pip...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print("  ✅ PyInstaller installed successfully")
        except Exception as e:
            print(f"  ❌ Failed to install PyInstaller: {e}")
            return False

    # 2. Required files check
    required_files = [
        "run.pyw",
        "QuizAssistant.spec",
        "installer.py",
        "Installer.spec",
        os.path.join("assets", "icon.ico"),
        os.path.join("assets", "icon.png"),
        os.path.join("packaging", "version_info.txt"),
        ".env.example"
    ]
    for rf in required_files:
        p = os.path.join(PROJECT_ROOT, rf)
        if not os.path.exists(p):
            print(f"  ❌ Missing required build file: {rf}")
            return False
        print(f"  ✅ Found {rf}")

    return True


def clean_previous_builds():
    """Clean intermediate builds while preserving the previous release until replacement is ready."""
    print("\n🧹 [2/5] Cleaning previous build artifacts...")
    build_dir = os.path.join(PROJECT_ROOT, "build")
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir)
            print("  ✅ Removed build/")
        except Exception as e:
            print(f"  ⚠️ Could not completely remove build/: {e}")


def has_required_app_executable(app_exe: str) -> bool:
    """Return whether the app executable required for embedding exists."""
    return os.path.isfile(app_exe)


def run_pyinstaller() -> bool:
    """Build the app in a staging directory, then embed it in the installer."""
    app_dist = os.path.join(PROJECT_ROOT, "build", "app-dist")
    app_work = os.path.join(PROJECT_ROOT, "build", "app")
    app_spec = os.path.join(PROJECT_ROOT, "QuizAssistant.spec")
    print(f"\n⚙️ [3/5] Building {APP_DISPLAY_NAME} for embedding...")
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
            "--distpath", app_dist, "--workpath", app_work, app_spec
        ], cwd=PROJECT_ROOT, check=True)
    except Exception as ex:
        print(f"  ❌ App compilation failed: {ex}")
        return False

    app_exe = os.path.join(app_dist, "QuizAssistant.exe")
    if not has_required_app_executable(app_exe):
        print(f"  ❌ App executable required for embedding was not built: {app_exe}")
        return False

    installer_dist = os.path.join(PROJECT_ROOT, "build", "installer-dist")
    installer_work = os.path.join(PROJECT_ROOT, "build", "installer")
    installer_spec = os.path.join(PROJECT_ROOT, "Installer.spec")
    print("\n⚙️ [3/5] Building setup executable...")
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--noconfirm",
            "--distpath", installer_dist, "--workpath", installer_work, installer_spec
        ], cwd=PROJECT_ROOT, check=True)
        return True
    except Exception as ex:
        print(f"  ❌ Installer compilation failed: {ex}")
        return False


def finalize_distribution(dist_dir: str, staged_installer: str) -> bool:
    """Leave only the setup executable, named QuizAssistant.exe, in dist."""
    if not os.path.isfile(staged_installer):
        print(f"  ❌ Installer executable not found at {staged_installer}")
        return False

    final_installer = os.path.join(dist_dir, "QuizAssistant.exe")
    os.makedirs(dist_dir, exist_ok=True)
    temporary_installer = os.path.join(dist_dir, ".QuizAssistant.exe.tmp")
    try:
        shutil.copy2(staged_installer, temporary_installer)
        os.replace(temporary_installer, final_installer)
        for name in os.listdir(dist_dir):
            path = os.path.join(dist_dir, name)
            if os.path.abspath(path) == os.path.abspath(final_installer):
                continue
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        return True
    except OSError as e:
        if os.path.exists(temporary_installer):
            os.remove(temporary_installer)
        print(f"  ❌ Could not finalize installer distribution: {e}")
        return False


def assemble_distribution() -> bool:
    """Finalize the single-file installer distribution."""
    print("\n📦 [4/5] Assembling single-installer distribution...")
    dist_dir = os.path.join(PROJECT_ROOT, "dist")
    staged_installer = os.path.join(PROJECT_ROOT, "build", "installer-dist", "QuizAssistant-Installer.exe")
    if not finalize_distribution(dist_dir, staged_installer):
        return False
    print(f"  ✅ Final installer: {os.path.join(dist_dir, 'QuizAssistant.exe')}")
    return True


def main():
    print("=" * 70)
    print(f"🔨 {APP_DISPLAY_NAME.upper()} - PRODUCTION BUILD PIPELINE")
    print("=" * 70)

    if not check_prerequisites():
        sys.exit(1)

    clean_previous_builds()

    if not run_pyinstaller():
        print("\n❌ Build aborted due to compilation errors.")
        sys.exit(1)

    if not assemble_distribution():
        print("\n❌ Failed to assemble distribution package.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print(f"🎉 BUILD SUCCESSFUL! {APP_DISPLAY_NAME} is ready for production.")
    print("=" * 70)
    print("Outputs available in 'dist/' directory:")
    print("  📁 dist/QuizAssistant.exe (Windows installer; app executable is embedded)")


if __name__ == "__main__":
    main()
