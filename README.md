<p align="center">
  <img src="assets/icon.png" alt="AI Quiz Assistant Logo" width="100" height="100">
</p>

<h1 align="center">AI Quiz Assistant 2.0</h1>

<p align="center">
  <b>Smart background quiz solver, instant OCR analysis, and customizable HUD interface</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0-0284c7.svg?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d4.svg?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/AI%20Providers-Gemini%20%7C%20OpenAI%20Compatible-8a2be2.svg?style=flat-square" alt="AI Providers">
  <img src="https://img.shields.io/badge/License-MIT-10b981.svg?style=flat-square" alt="License">
</p>

---

A high-performance Windows desktop assistant that silently captures exam questions from your screen, solves them using multimodal AI (**Google Gemini AI Studio** or **Custom Local / OpenAI-compatible API**), and presents answers in an elegant, non-intrusive floating HUD.

---

## 🌟 Key Features

- 🤖 **Dual AI Provider Architecture & Dynamic Model Fetching**:
  - **Google Gemini AI Studio**: High-speed multimodal vision analysis with live model retrieval (`gemini-2.5-flash`, `gemini-2.5-pro`, etc.).
  - **Custom Local / Proxy**: Full OpenAI Chat Completion compatibility (Ollama, vLLM, LM Studio, Claude Proxy, or self-hosted models) with dynamic model listing via `/v1/models` and `/api/tags`.
  - **Dynamic Model Discovery**: One-click `[ 🔄 Fetch Models ]` live query directly from your API key or endpoint into combobox selection menus—no hardcoded models.
  - **Instant Hot-Switching**: Switch providers live via the Settings window without restarting the app.

- 🔄 **Automatic Provider Failover & Rotation (Zero-Downtime Resilience)**:
  - **Seamless Rate Limit / Quota Failover**: If your primary provider exhausts its token quota (HTTP 429 ResourceExhausted), times out, or encounters a server error, requests automatically rotate to your configured alternate provider (e.g., Gemini ➡️ Local Ollama/vLLM or vice versa) without dropping captured questions.
  - **Uninterrupted Auto-Fill**: Automated clicking seamlessly continues even if a failover occurred mid-analysis.
  - **HUD Transparency**: Badges automatically tag fallback results with `(Backup)` so you always know which model resolved your question.
  - **Smart Token Conservation**: Bypasses rotation when a screenshot genuinely contains no questions (`NoQuestionsFoundError`), preserving alternate quota.
  - **Configurable in Settings**: Easily toggled on or off with live backup readiness indicators in Tab 1 (AI Provider).

- 📸 **Silent Background Processing**:
  - Activated by hotkey `Alt + Z` or optional middle-mouse scroll up.
  - **Zero auto-popups**: Processing runs completely silently in the background. Popups never appear unprompted during an exam.
  - View results only when you choose by pressing `Alt + C` (latest question) or `Alt + H` (full history).

- ⚡ **Automated Screen Recognition & Auto-Fill (`Alt + X`)**:
  - **End-to-End Hands-Free**: Captures the quiz screen, recognizes questions and options using multimodal spatial coordinates (`normalized [y, x]`), solves the quiz, and automatically guides the mouse cursor to click the correct answer choices.
  - **Multi-Question & Multi-Select Support**: Seamlessly executes sequential clicks in order for exams containing multiple questions or multi-option checkboxes.
  - **Human-like Smooth Movement & Cursor Restore**: Configurable cosine ease movement, inter-click delay (default 200ms), and automatic cursor return to its original position upon completion.
  - **Safety Abort Mechanism**: Can be safely aborted at any moment or disabled entirely in the Settings dialog.

- ⚡ **FIFO Queue & dHash Deduplication**:
  - Rapid successive captures are enqueued into a sequential FIFO worker thread to prevent race conditions.
  - Perceptual image hashing (`dHash` + SHA-256): Re-capturing the same question immediately returns cached answers from RAM without making an external AI call.

- 🎓 **3 Specialized Quiz Modes**:
  - **Multiple Choice (`multiple_choice`)**: Clean questions with highlighted choices (`A`, `B`, `C`, `D`) and text.
  - **Multiple Choice + Explanation (`multiple_choice_explanation`)**: Questions and choices with collapsible interactive explanations and one-click copy.
  - **Essay / Detailed Solutions (`essay`)**: Step-by-step mathematical, analytical, and written solutions.

- 🎨 **Adaptive HUD & Interactive Scaling**:
  - **Interactive Drag Resizing**: Resize HUD result cards (`Alt + C` & `Alt + H`) interactively using corner drag grippers (`◢`) or borders.
  - **Dynamic Size Memory**: A dynamic `💾 Save Size` button appears when resized, allowing you to persist your custom width and height across sessions.
  - **Built-in Screen Eyedropper**: Sample any screen pixel to match HUD background color with exam portal themes.
  - **Smart Contrast Engine**: Automatically calculates WCAG-compliant text, border, and badge colors for light and dark themes.
  - **Quick HUD Presets**: One-click styling including `White`, `Gray`, `Cream`, `Blue`, `Dark`, and `👻 Stealth` (borderless, pure white matching, muted slate-gray text, and non-bold font for ultra-discreet viewing).
  - Frameless, draggable, mouse-wheel scrollable, with configurable window width, font size, and opacity (50% - 100%).

- ⌨️ **Fully Configurable Shortcuts**:
  - All hotkeys (`Alt + [Z/X/C/H/R/S/Q]`) are fully remappable from Settings without hardcoded locks.
  - Toggleable middle-mouse scroll gestures.

- 📁 **Complete Privacy, Safe Data Management & System Tray Quick-Access**:
  - **System Tray Quick Folders**: One-click tray menu actions to open Logs and Screenshots directories directly in Windows Explorer.
  - **One-Click Data Wipe**: Clear in-memory history, deduplication cache, on-disk logs, and screenshot captures simultaneously.
  - **Zero Secrets / Zero Leaks**: Strict `.gitignore` enforcement for `.env`, `config.json`, logs, and cache; all keys masked with zero hardcoded paths or credentials.

---

## 💻 System Requirements

- **Operating System**: Windows 10 / Windows 11 (64-bit)
- **Python**: 3.10 - 3.13+
- **Internet connection** for Google Gemini AI Studio, or a local inference server for Custom Provider.

---

## 🚀 Installation & Quick Start

### 📦 Option 1: Official Windows Installer (Recommended)
Download and run **`QuizAssistant.exe`** (the installer; the app executable is installed afterward):
1. **Choose Destination Folder**: Select your preferred installation directory (`%LOCALAPPDATA%\Programs\AI Quiz Assistant` or custom).
2. **Register Official Icon**: Automatically creates Desktop and Start Menu shortcuts with the official high-resolution icon (16x16 to 256x256), and registers in Windows Apps & Features.
3. **Launch & 3-Step Setup**: Automatically launches the app upon finish, opening the 3-step setup onboarding wizard.

---

### 💻 Option 2: Run from Python Source

```bash
# 1. Clone repository
git clone https://github.com/nvtruongops/ai-quiz-assistant.git
cd ai-quiz-assistant

# 2. Run setup wizard (interactive CLI & GUI tools)
python setup.py

# Or run specific setup options:
python setup.py --install-deps    # Install or upgrade dependencies only
python setup.py --setup-ai        # Configure AI credentials & dynamically fetch models only
python setup.py --gui             # Open the Graphical 3-Step Setup Wizard
python setup.py --shortcuts       # Register Desktop & Start Menu shortcuts with App Icon
python setup.py --installer       # Open Graphical Windows Setup Installer
python setup.py --all             # Install dependencies + run setup + register shortcuts
```

### Running the Application

- **Background mode (Recommended, hidden console window)**:
  ```bash
  python run.pyw
  ```
  *(Automatically detects and installs any missing dependencies on first run)*
- **Console debug mode**:
  ```bash
  python src/main.py
  ```

### 🧙 First-Time Setup Wizard (3-Step Onboarding)
When launching the application for the first time, a streamlined 3-step setup wizard guides you:
1. 🤖 **AI Provider Configuration**: Choose between Google Gemini AI Studio or Custom Local / Proxy (Ollama, vLLM, LM Studio, OpenAI-compatible). Includes one-click `[ 🔄 Fetch Models ]` and `[ ⚡ Test Connection ]`. **Can be skipped** (`⏭️ Skip AI`) if you want to explore the interface before entering API keys.
2. 🎨 **HUD Appearance & Theme**: Select your result card theme with real-time live preview (`👻 Stealth`, `⚪ Pure White`, `🌙 Dark Mode`, `🍦 Warm Cream`, `🔵 Soft Blue`, `🌫️ Modern Gray`) and configure HUD opacity.
3. 🎯 **Quiz Mode & Hotkeys Reference**: Select your default solving mode (Quick Multiple Choice, MC + Explanation, or Essay) and review the core shortcut cheat sheet.

---

## ⌨️ Default Keyboard Shortcuts

| Shortcut | Action | Description |
|---|---|---|
| **Alt + Z** | Capture & Analyze Screen | Silent background capture, extracts single or multiple questions |
| **Alt + X** | Auto-Fill & Click Answers | Captures screen, solves questions, and moves mouse to click answers |
| **Alt + C** | Show Latest Question Result | Displays current question with answer and navigation buttons |
| **Alt + H** | View Question History (1..x) | Displays full sequential session history (questions 1 to N + pending queue) |
| **Alt + R** | Reset Quiz Session History | Resets in-memory counter back to Question 1 (silent reset) |
| **Alt + S** | Open Settings Dialog | Configure AI Provider, Quiz Mode, HUD appearance, and shortcuts |
| **Alt + Q** | Exit Application | Gracefully shuts down tray icon, background workers, and listeners |
| **Escape** | Close Active Popup | Instantly dismisses visible HUD popup |
| **Ctrl + C** | Copy Result to Clipboard | Copies formatted question and answer text from active popup |

*Note: All `Alt + [Key]` combinations are customizable in the Settings Dialog (`Alt + S`) -> Hotkeys tab.*

---

## ⚙️ Configuration File (`.env`)

You can edit `.env` directly or use the graphical Settings Dialog (`Alt + S`):

```ini
# AI Provider Selection: 'gemini' or 'custom'
API_PROVIDER=gemini

# Google Gemini AI Studio Credentials
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Custom Local / Proxy API Configuration (OpenAI-compatible)
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=your_key_if_required
CUSTOM_MODEL=llama3.2-vision

# HUD Popup Placement & Logging
POPUP_POSITION=cursor
LOG_LEVEL=INFO
```

---

## 🧪 Verification & Automated Tests

Run the full automated test suite located in `/test` to verify all core components:

```bash
# Run all automated tests via standard test discovery
python -m unittest discover -s test -p "test_*.py"

# Or run specific test suites in the test/ directory:
# Verify FIFO queue, silent processing, and image deduplication
python test/test_queue_and_image_cache.py

# Verify navigation, reload, and silent queue mechanics
python test/test_fix_jump_and_silent_queue.py

# Verify settings dialog and GUI components
python test/test_settings_dialog_gui.py

# Verify scaling, interactive resizing, and tray folder opening
python test/test_scaling_and_folder_opening.py
```

---

## 📦 Building Standalone Executable (.EXE)

AI Quiz Assistant provides an automated production build pipeline that compiles the app into a single standalone Windows executable (`QuizAssistant.exe`) with all dependencies, assets, and version metadata bundled.

### Option 1: One-Click Build Script (Recommended)
Simply run the included build script:
```bash
# Via Windows Command Prompt or PowerShell:
build.bat

# Or directly via Python:
python build_exe.py
```

The automated pipeline will:
1. Verify required prerequisites and PyInstaller installation.
2. Clean intermediate compilation artifacts.
3. Compile the app executable into a temporary build folder.
4. Embed the app executable in the graphical installer.
5. Leave only `dist/QuizAssistant.exe` (the installer) for distribution.

### Option 2: Manual PyInstaller Build
```bash
pip install pyinstaller
pyinstaller --clean --noconfirm QuizAssistant.spec
```
The app executable is only an intermediate build artifact; use `build.bat` to create the distributable installer at `dist/QuizAssistant.exe`.

---

## 🌐 Official Production URLs & Endpoints

| Resource | Official Production URL | Description |
|---|---|---|
| **GitHub Repository** | [github.com/nvtruongops/ai-quiz-assistant](https://github.com/nvtruongops/ai-quiz-assistant) | Source code, updates, and branch management |
| **Releases & Downloads** | [github.com/nvtruongops/ai-quiz-assistant/releases](https://github.com/nvtruongops/ai-quiz-assistant/releases) | Pre-built Windows binaries, portable zip packages, changelogs |
| **Documentation & Guides** | [github.com/nvtruongops/ai-quiz-assistant#readme](https://github.com/nvtruongops/ai-quiz-assistant#readme) | Full installation, configuration, and troubleshooting documentation |
| **Issues & Feedback** | [github.com/nvtruongops/ai-quiz-assistant/issues](https://github.com/nvtruongops/ai-quiz-assistant/issues) | Bug reports, feature suggestions, and community support |
| **Google AI Studio API Key** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | Official portal to generate free Gemini multimodal API keys |
| **Default Local Vision Endpoint** | `http://localhost:11434/v1` | Standard OpenAI-compatible endpoint for Ollama / vLLM / LM Studio |
| **Default Local Vision Model** | `llama3.2-vision` | Lightweight, high-accuracy multimodal model for 100% offline quiz solving |

---

## 🛡️ License

This project is open-source software licensed under the **[MIT License](LICENSE)**:

```text
MIT License

Copyright (c) 2025-2026 nvtruongops

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
