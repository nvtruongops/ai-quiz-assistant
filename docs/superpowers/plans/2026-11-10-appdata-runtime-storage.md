# AppData Runtime Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store runtime user data under `%APPDATA%\AI Quiz Assistant`, keep the installed program folder minimal, and leave only the setup installer executable in the final `dist` output.

**Architecture:** Update the shared runtime directory resolver in `src/path_utils.py`; keep source-mode paths and frozen read-only resource paths unchanged. Copy legacy `.env`, `config.json`, and `logs/` into AppData only when the respective destination is absent. Adjust installer copy behavior and make the build pipeline clean intermediate and portable outputs only after bundling the app executable into the installer.

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

- [ ] **Step 1: Write failing tests** for frozen mode returning `%APPDATA%\AI Quiz Assistant`, source mode returning repository root, legacy `.env`/`config.json`/`logs` copied without deleting source, and pre-existing target preserved.
- [ ] **Step 2: Run focused tests** with `python -m pytest test/test_path_utils.py -q`; confirm failures assert current exe-directory behavior/missing migration.
- [ ] **Step 3: Implement the minimal resolver and first-run copy** in `src/path_utils.py`; use `APPDATA` when set, otherwise `LOCALAPPDATA` as per-user fallback. Copy each legacy item only when source exists and destination does not.
- [ ] **Step 4: Re-run focused tests**; expected all pass.

### Task 2: Keep installed program directory lean

**Files:**
- Modify: `installer.py`
- Test: `test/test_installer_and_shortcuts.py` (existing file was deleted in current worktree; do not restore user-deleted tests—create focused test if needed)

**Interfaces:**
- Installer continues to install the embedded `QuizAssistant.exe` and generate `uninstall.bat`.

- [ ] **Step 1: Add a focused test** asserting installer does not copy `.env.example`, README files, or assets into the installation directory; app EXE and uninstaller remain present (test through extracted copy logic if practical).
- [ ] **Step 2: Run focused test** and confirm expected failure against current copy loop.
- [ ] **Step 3: Remove only the documentation/template/assets deployment block** from `run_installation`; no asset copy needed because bundled app resources are internal and data is moved to AppData.
- [ ] **Step 4: Re-run focused test**; expected pass.

### Task 3: Produce one distributable installer in `dist`

**Files:**
- Modify: `build_exe.py`
- Test: `test/test_build_exe.py` (create)

**Interfaces:**
- `run_pyinstaller()` still builds app first, then installer which embeds `dist/QuizAssistant.exe` via `Installer.spec`.
- `assemble_distribution()` becomes a cleanup/finalization step leaving only the setup executable in `dist`.

- [ ] **Step 1: Write failing tests** for finalization retaining only `QuizAssistant.exe` as the installer, refusing to claim success without installer EXE, and not deleting/interfering with artifacts before installer creation.
- [ ] **Step 2: Run focused tests**; confirm current portable packaging behavior fails.
- [ ] **Step 3: Replace portable folder/ZIP/checksum assembly with safe final cleanup** after confirming both source executables exist; leave only `dist/QuizAssistant.exe` (the installer) and keep app build intermediates outside `dist`.
- [ ] **Step 4: Re-run focused tests**; expected pass.

### Task 4: Regression and build verification

**Files:**
- No additional production files.

- [ ] **Step 1: Run focused test suite** for path resolver, installer behavior, and build output.
- [ ] **Step 2: Run repository test discovery** with `python -m pytest -q`; report failures explicitly, noting existing tracked test deletions were present before changes.
- [ ] **Step 3: Run build pipeline if installed dependencies permit**; verify `dist` has exactly `QuizAssistant.exe` and do not execute it.
- [ ] **Step 4: Review `git diff`** to confirm no deleted user files were restored, no existing config/log data was removed, and scope matches spec.
