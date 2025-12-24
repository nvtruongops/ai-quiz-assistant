# AI Quiz Assistant

A Windows desktop application that captures screenshots and uses Google Gemini AI to analyze and answer multiple-choice questions.

## Requirements

- Python 3.8+
- Windows 10/11
- Google Gemini API key

## Installation

```bash
git clone https://github.com/nvtruongops/ai-quiz-assistant.git
cd ai-quiz-assistant
pip install -r requirements.txt
python setup.py
```

## Configuration

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey), then run `python setup.py` to configure.

Alternatively, create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
POPUP_POSITION=cursor
LOG_LEVEL=INFO
```

## Usage

```bash
python run.pyw
```

### Hotkeys

| Hotkey | Action |
|--------|--------|
| Alt + Z | Capture screen and analyze |
| Middle Mouse + Scroll Up | Capture screen and analyze |
| Alt + X | Show/hide results |
| Alt + C | Show answer history |
| Middle Mouse + Scroll Down | Show answer history |
| Alt + R | Reset answer history |
| Alt + S | Open Settings dialog |
| Delete | Clear logs and answers |
| ` (Backtick) | Exit application |

## Building Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed run.pyw
```

Output will be in `dist/QuizAssistant.exe`.

## License

MIT License
