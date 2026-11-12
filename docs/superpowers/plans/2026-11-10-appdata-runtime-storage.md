# AppData Runtime Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store runtime user data under `%APPDATA%\AI Quiz Assistant`, keep the installed program folder minimal, and leave only `dist\QuizAssistant.exe` (the installer containing the app executable) in the final output.

**Architecture:** Update the shared runtime directory resolver in `src/path_utils.py`; keep source-mode paths and frozen read-only resource paths unchanged. On app launch, copy legacy `.env`, `config.json`, and `logs/` from the installed app directory to AppData only when each destination is absent. Adjust installer copy behavior and make the build pipeline stage the app then embed it in the installer.

**Tech Stack:** Python 3, PyInstaller, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-11-10-appdata-runtime-storage-design.md`

## Global Constraints

- Frozen runtime user data directory is `%APPDATA%\AI Quiz Assistant`.
- Source-mode behavior remains repository-root based.
- Frozen read-only resources remain resolved through PyInstaller `_MEIPASS`.
- Legacy data is copied only when the corresponding AppData destination does not exist; never delete source data or overwrite an existing destination.
- Installer target contains `QuizAssistant.exe` and uninstaller only.
- Final `dist` contains only `QuizAssistant.exe`, which is the installer with app EXE embedded.
- Do not run the installer on the host system during verification.

## Review Focus

- AppData missing/unset: frozen resolver still yields a usable per-user path; test path fallback behavior.
- Existing AppData settings/API: migration must preserve them; test no overwrite.
- Partial legacy data and logs: migrate only absent destinations; test independent paths and source preservation.
- Source-mode developer data: remains at repository root; test existing behavior.
- Build stage failure: do not leave an installer presented as complete or delete the only useful generated app before bundling; test artifact assembly with temporary directories or helper-level tests.

---

### Task 1: AppData resolution and safe legacy migration

**Files:**
- Modify: `src/path_utils.py`
- Test: `test/test_path_utils.py` (create)

**Interfaces:**
- `get_app_dir() -> str` remains the runtime root used by settings, config, logs, screenshots, and answers.
- Add internal migration helper only if needed; avoid new public abstractions unless tests require them.

- [x] **Step 1: Write failing tests** for frozen mode returning `%APPDATA%\AI Quiz Assistant`, source mode returning repository root, legacy app-directory `.env`/`config.json`/`logs` copied without deleting source, and pre-existing AppData targets preserved.
- [x] **Step 2: Run focused tests** and confirm they failed on the original executable-directory behavior.
- [x] **Step 3: Implement the minimal resolver and first-run app-data migration** in `src/path_utils.py`; use `APPDATA` when set, otherwise the per-user `AppData\Roaming` fallback. Copy each legacy item from the installed app directory only when source exists and corresponding destination does not.
- [x] **Step 4: Re-run focused tests**; they pass.

### Task 2: Keep installed program directory lean

**Files:**
- Modify: `installer.py`
- Test: `test/test_installer_minimal_files.py` (focused regression test for installer payload; existing installer/shortcut regression tests are retained)

**Interfaces:**
- Installer continues to install the embedded `QuizAssistant.exe` and generate `uninstall.bat`.

- [x] **Step 1: Add a focused test** asserting installer does not copy `.env.example`, README files, or assets into the installation directory; app EXE and uninstaller remain present where exercised.
- [x] **Step 2: Run focused test** and confirm expected failure against the original copy loop.
- [x] **Step 3: Remove documentation/template/assets deployment** from `run_installation`; bundle only the installer icon, while app resources remain embedded in the app executable.
- [x] **Step 4: Re-run focused tests**; they pass.

### Task 3: Produce one distributable installer in `dist`

**Files:**
- Modify: `build_exe.py`
- Test: `test/test_build_exe.py` (create)

**Interfaces:**
- `run_pyinstaller()` builds app to `build/app-dist/QuizAssistant.exe`, then installer to `build/installer-dist/QuizAssistant-Installer.exe`; `Installer.spec` embeds the app.
- `assemble_distribution()` becomes a cleanup/finalization step leaving only the setup executable in `dist`.

- [x] **Step 1: Write failing tests** for finalization retaining only `QuizAssistant.exe` as the installer and preserving existing `dist` on missing staged installer.
- [x] **Step 2: Run focused tests** and confirm they failed against the previous packaging behavior.
- [x] **Step 3: Replace portable folder/ZIP/checksum assembly with staged build and finalization** after verifying app and installer binaries; leave only `dist/QuizAssistant.exe` and keep intermediates outside `dist`.
- [x] **Step 4: Re-run focused tests**; they pass.

### Task 4: Regression and build verification

**Files:**
- No additional production files.

- [x] **Step 1: Run focused and full regression tests**; latest full-suite result: 102 passed, 1 skipped (warnings remain in legacy UI/test collection).
- [x] **Step 2: Run repository test discovery** with `python -m pytest -q -p no:cacheprovider`; confirmed all restored tracked tests are collected.
- [x] **Step 3: Run the Windows PyInstaller build**; verified `dist` has exactly `QuizAssistant.exe`, and did not execute it.
- [x] **Step 4: Inspect installer archive and staged diff**; confirmed embedded app executable/icon and no test, `.env`, or README payload; `.env` remains ignored and untracked.
- [ ] **Step 5: Interactive install/upgrade/uninstall smoke test on a Windows desktop**; not run in this session, so release readiness remains conditional. No GitHub Release or installer upload was performed.
