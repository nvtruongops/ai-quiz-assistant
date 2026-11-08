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
    """Remove previous build and temporary directories."""
    print("\n🧹 [2/5] Cleaning previous build artifacts...")
    dirs_to_clean = ["build", "dist"]
    for d in dirs_to_clean:
        p = os.path.join(PROJECT_ROOT, d)
        if os.path.exists(p):
            try:
                shutil.rmtree(p)
                print(f"  ✅ Removed {d}/")
            except Exception as e:
                print(f"  ⚠️ Could not completely remove {d}/: {e}")


def run_pyinstaller() -> bool:
    """Execute PyInstaller using QuizAssistant.spec."""
    print(f"\n⚙️ [3/5] Compiling {APP_DISPLAY_NAME} into standalone executable...")
    spec_path = os.path.join(PROJECT_ROOT, "QuizAssistant.spec")
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_path
    ]
    
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        duration = round(time.time() - t0, 1)
        print(f"  ✅ PyInstaller compilation finished in {duration}s!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ PyInstaller build failed with exit code {e.returncode}")
        return False
    except Exception as ex:
        print(f"  ❌ PyInstaller execution error: {ex}")
        return False


def assemble_distribution() -> bool:
    """Assemble final distribution package and zip archive."""
    print("\n📦 [4/5] Assembling production distribution package...")
    
    exe_source = os.path.join(PROJECT_ROOT, "dist", "QuizAssistant.exe")
    if not os.path.exists(exe_source):
        print(f"  ❌ Output executable not found at {exe_source}")
        return False

    exe_size_mb = round(os.path.getsize(exe_source) / (1024 * 1024), 2)
    print(f"  ✅ Verified executable: QuizAssistant.exe ({exe_size_mb} MB)")

    # Create portable release directory
    release_dir_name = f"AI-Quiz-Assistant-v{APP_VERSION}"
    release_dir = os.path.join(PROJECT_ROOT, "dist", release_dir_name)
    os.makedirs(release_dir, exist_ok=True)

    # 1. Copy executable
    shutil.copy2(exe_source, os.path.join(release_dir, "QuizAssistant.exe"))

    # 2. Copy template .env.example
    env_ex = os.path.join(PROJECT_ROOT, ".env.example")
    if os.path.exists(env_ex):
        shutil.copy2(env_ex, os.path.join(release_dir, ".env.example"))

    # 3. Create README_DIST.txt
    dist_readme_path = os.path.join(release_dir, "README.txt")
    with open(dist_readme_path, "w", encoding="utf-8") as f:
        f.write(f"""================================================================================
{APP_DISPLAY_NAME} - Portable Release
================================================================================

🚀 QUICK START:
1. Double-click `QuizAssistant.exe` to launch.
2. On first launch, the 3-step setup wizard will appear:
   - Configure Google Gemini API (Free key at: https://aistudio.google.com/app/apikey)
     OR Custom local AI endpoint (e.g. Ollama: http://localhost:11434/v1).
   - Choose HUD popup theme and transparency.
   - Review or customize keyboard shortcuts.
3. The app runs silently in your Windows System Tray (bottom-right taskbar).

⌨️ DEFAULT SHORTCUTS:
  Alt + Z : Silent screen capture & background AI solve
  Alt + X : Auto-fill / click correct answer choices
  Alt + C : Show floating HUD card with latest question result
  Alt + H : View full question history (1..N)
  Alt + S : Open Settings dialog (adjust keys, theme, API credentials)
  Alt + R : Reset session history for a new test

🌐 OFFICIAL LINKS:
  Repository:     {GITHUB_REPO_URL}
  Releases:       {GITHUB_RELEASES_URL}
  Documentation:  {DOCUMENTATION_URL}

License: MIT License
================================================================================
""")

    print(f"  ✅ Portable package created at dist/{release_dir_name}/")

    # 4. Create ZIP Archive
    zip_dest = os.path.join(PROJECT_ROOT, "dist", f"{release_dir_name}-Windows")
    shutil.make_archive(zip_dest, "zip", root_dir=os.path.join(PROJECT_ROOT, "dist"), base_dir=release_dir_name)
    zip_file = f"{zip_dest}.zip"
    zip_size_mb = round(os.path.getsize(zip_file) / (1024 * 1024), 2)
    print(f"  ✅ Created ZIP archive: {os.path.basename(zip_file)} ({zip_size_mb} MB)")

    # 5. Calculate Checksums
    exe_hash = calculate_sha256(exe_source)
    zip_hash = calculate_sha256(zip_file)

    checksum_file = os.path.join(PROJECT_ROOT, "dist", "SHA256SUMS.txt")
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{exe_hash} *QuizAssistant.exe\n")
        f.write(f"{zip_hash} *{os.path.basename(zip_file)}\n")

    print("\n🔐 [5/5] Release Integrity Hashes (SHA-256):")
    print(f"  QuizAssistant.exe: {exe_hash}")
    print(f"  {os.path.basename(zip_file)}: {zip_hash}")
    print(f"  Checksums saved to: dist/SHA256SUMS.txt")

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
    print("  📁 dist/QuizAssistant.exe (Standalone executable)")
    print(f"  📁 dist/AI-Quiz-Assistant-v{APP_VERSION}/ (Portable folder)")
    print(f"  📦 dist/AI-Quiz-Assistant-v{APP_VERSION}-Windows.zip (Distribution package)")
    print("  📄 dist/SHA256SUMS.txt (Verification checksums)")


if __name__ == "__main__":
    main()
