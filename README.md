# 🤖 AI Quiz Assistant

<div align="center">

**An intelligent screenshot analyzer that helps you answer multiple-choice questions using AI**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

*Capture screenshots, analyze questions, get instant AI-powered answers*

[📥 Download Latest Release](#-installation) • [📖 Documentation](#-usage) • [🐛 Report Issues](https://github.com/nvtruongops/ai-quiz-assistant/issues)

</div>

---

## ✨ Features

### 🎯 **Smart Question Analysis**
- **Screenshot Capture**: Instant screen capture with hotkeys
- **AI-Powered Analysis**: Uses Google Gemini or AWS Bedrock for accurate answers
- **Multiple Choice Detection**: Automatically identifies and analyzes MCQ questions
- **Context Preservation**: Maintains question context for better accuracy

### 🚀 **Dual AI Provider Support**
- **Google Gemini 2.5 Flash**: Free, fast, and reliable (recommended for beginners)
- **AWS Bedrock with Claude**: Premium quality with advanced reasoning capabilities
- **Seamless Switching**: Switch between providers with a single hotkey (Alt+S)

### 🎮 **User-Friendly Interface**
- **System Tray Integration**: Runs quietly in background
- **Hotkey Controls**: Full keyboard shortcuts for all functions
- **Popup Results**: Clean, readable answer display
- **Answer History**: Save and review previous answers

### 🔒 **Security First**
- **Hashed API Keys**: API keys are hashed before storage
- **Environment Variables**: Sensitive data stored securely
- **Git-Safe**: No credentials committed to version control

---

## 📋 Table of Contents

- [🚀 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [🎮 Usage](#-usage)
- [🏗️ Building Executable](#️-building-executable)
- [🔧 Advanced Configuration](#-advanced-configuration)
- [🐛 Troubleshooting](#-troubleshooting)
- [🛠️ Development](#️-development)
- [📁 Project Structure](#-project-structure)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)

---

## 🚀 Installation

### Prerequisites

- **Python 3.8 or higher**
- **Windows 10/11** (primary platform)
- **Internet connection** for AI API calls

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/nvtruongops/ai-quiz-assistant.git
   cd ai-quiz-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AI Provider**
   ```bash
   python setup.py
   ```
   Choose your preferred AI provider and follow the setup wizard.

4. **Run the application**
   ```bash
   python run.pyw
   ```

### 📥 Download Pre-built Executable

For users who prefer not to install Python:

1. Go to [Releases](https://github.com/nvtruongops/ai-quiz-assistant/releases)
2. Download the latest `QuizAssistant.exe`
3. Copy `.env.example` to `.env` and configure your API keys
4. Run `QuizAssistant.exe`

---

## ⚙️ Configuration

### AI Provider Setup

The application supports two AI providers. You can configure both and switch between them anytime.

#### Google Gemini (Recommended)

**Free, fast, and easy to set up**

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Run setup:
   ```bash
   python setup.py
   # Choose option 1: Setup Google Gemini
   ```

#### AWS Bedrock (Premium)

**Higher quality answers with Claude**

1. Ensure you have an AWS account with Bedrock access
2. Run setup:
   ```bash
   python setup.py
   # Choose option 2: Setup AWS Bedrock
   ```

### Environment Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```env
# AI Provider Configuration
AI_PROVIDER=gemini  # or "bedrock"

# Gemini API Configuration
GEMINI_API_KEY=your_actual_gemini_api_key_here

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20240620-v1:0

# Application Settings
POPUP_POSITION=cursor  # or "fixed:x,y"
LOG_LEVEL=INFO
```

---

## 🎮 Usage

### Basic Workflow

1. **Launch the application**: `python run.pyw`
2. **Open your quiz/exam** in a web browser or application
3. **Position the question** on screen
4. **Press hotkey** to capture and analyze
5. **View results** in the popup window

### Hotkey Reference

| Hotkey | Function | Description |
|--------|----------|-------------|
| `Alt + Z` | 📸 Capture & Analyze | Capture screen and get AI answer |
| `Middle Mouse + Scroll Up` | 📸 Capture & Analyze | Alternative capture method |
| `Alt + X` | 👁️ Show Results | Display analysis results |
| `Alt + C` | 📚 Show History | View all saved answers |
| `Middle Mouse + Scroll Down` | 📚 Show History | Alternative history view |
| `Alt + R` | 🔄 Reset History | Clear answer history |
| `Alt + S` | 🔄 Switch Provider | Toggle between Gemini/Bedrock |
| `Delete` | 🗑️ Clear Logs | Clear all logs and answers |
| `` ` `` (Backtick) | ❌ Exit | Close the application |

### Advanced Usage

#### Screenshot Selection
- The app captures the area around your cursor
- Position cursor near the question for best results
- Avoid capturing unnecessary UI elements

#### Answer History
- All answers are saved to `logs/answers.txt`
- Use `Alt + C` to review previous answers
- History persists between sessions

#### Provider Switching
- Switch between Gemini and Bedrock with `Alt + S`
- Each provider has different strengths:
  - **Gemini**: Faster, good for straightforward questions
  - **Bedrock**: Better reasoning for complex questions

---

## 🏗️ Building Executable

To create a standalone executable for distribution:

### Prerequisites
```bash
pip install pyinstaller
```

### Build Process

1. **Clean previous builds** (optional)
   ```bash
   rm -rf build/ dist/
   ```

2. **Build executable**
   ```bash
   pyinstaller --onefile --windowed run.pyw
   ```

3. **Find executable**
   - Executable will be in `dist/QuizAssistant.exe`
   - Copy `.env.example` to `dist/` for user configuration

### Custom Build Options

For development builds with console:
```bash
pyinstaller --onefile --console run.pyw
```

---

## 🔧 Advanced Configuration

### Configuration Files

- **`config.json`**: Auto-generated by setup.py (gitignored)
- **`.env`**: User environment variables (gitignored)
- **`config_backup.json`**: Template with placeholder values

### Logging Configuration

Logs are stored in `logs/app.log`. Configure log level in `.env`:

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Custom Hotkeys

Currently hardcoded. To modify, edit `src/hotkey_listener.py`.

### System Tray Icon

The app runs in system tray. Double-click icon to show/hide main window.

---

## 🐛 Troubleshooting

### Common Issues

#### ❌ "Invalid API key" Error
```
Solution:
1. Run: python setup.py
2. Reconfigure your API provider
3. Test connection with option 6
```

#### ❌ "Module not found" Error
```
Solution:
1. Ensure all dependencies are installed: pip install -r requirements.txt
2. Check Python version: python --version (must be 3.8+)
3. Try virtual environment: python -m venv venv && venv\Scripts\activate
```

#### ❌ AWS Credentials Error
```
Solution:
1. Verify AWS credentials are correct
2. Check region supports Bedrock: us-east-1, us-west-2, eu-west-1
3. Ensure Bedrock is enabled in your AWS account
```

#### ❌ Application Won't Start
```
Check logs/app.log for errors:
1. Open logs/app.log
2. Look for error messages at startup
3. Common issues: missing dependencies, invalid config
```

#### ❌ Screenshot Capture Issues
```
Solution:
1. Ensure application has screen capture permissions
2. Try running as administrator
3. Check if other screenshot tools are interfering
```

### Performance Optimization

- **Use Gemini** for faster responses
- **Close unnecessary applications** during capture
- **Position questions clearly** on screen
- **Use wired internet** for stable API calls

### Getting Help

1. **Check logs**: `logs/app.log` and `logs/answers.txt`
2. **Run diagnostics**: `python test_security.py`
3. **Create issue**: [GitHub Issues](https://github.com/nvtruongops/ai-quiz-assistant/issues)

---

## 🛠️ Development

### Setting Up Development Environment

1. **Clone repository**
   ```bash
   git clone https://github.com/nvtruongops/ai-quiz-assistant.git
   cd ai-quiz-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install development dependencies**
   ```bash
   pip install pytest black flake8 mypy
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gemini_client.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Architecture Overview

```
src/
├── main.py              # Main application logic
├── config_manager.py    # Configuration management
├── gemini_client.py     # Google Gemini API client
├── bedrock_client.py    # AWS Bedrock API client
├── screenshot_manager.py # Screen capture functionality
├── popup_manager.py     # Result display system
├── hotkey_listener.py   # Keyboard shortcuts
├── system_tray.py       # System tray integration
├── request_manager.py   # API request handling
├── logger.py           # Logging system
└── models.py           # Data models
```

---

## 📁 Project Structure

```
ai-quiz-assistant/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py            # Main application
│   ├── config_manager.py  # Configuration management
│   ├── gemini_client.py   # Gemini API client
│   ├── bedrock_client.py  # Bedrock API client
│   ├── screenshot_manager.py # Screen capture
│   ├── popup_manager.py   # Result display
│   ├── hotkey_listener.py # Hotkey handling
│   ├── system_tray.py     # System tray
│   ├── request_manager.py # API requests
│   ├── logger.py          # Logging
│   └── models.py          # Data structures
├── tests/                 # Unit tests
├── logs/                  # Application logs
├── build/                 # PyInstaller build files
├── dist/                  # Built executables (gitignored)
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── config_backup.json    # Config template
├── requirements.txt      # Python dependencies
├── setup.py             # Configuration script
├── run.pyw              # Application entry point
├── QuizAssistant.spec    # PyInstaller spec
├── README.md            # This file
└── requirements.txt     # Python dependencies
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

### 1. Fork the Repository
Click the "Fork" button at the top right of this page.

### 2. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes
- Follow the existing code style
- Add tests for new features
- Update documentation as needed

### 4. Run Tests
```bash
pytest
black src/ tests/
flake8 src/ tests/
```

### 5. Commit Your Changes
```bash
git commit -m "Add: Brief description of your changes"
```

### 6. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

### 7. Create a Pull Request
Open a pull request with a clear description of your changes.

### Development Guidelines

- **Code Style**: Follow PEP 8
- **Commits**: Use conventional commit format
- **Tests**: Maintain >80% test coverage
- **Documentation**: Update README for new features

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

- ✅ **Commercial use**: Allowed
- ✅ **Modification**: Allowed
- ✅ **Distribution**: Allowed
- ✅ **Private use**: Allowed
- ❌ **Liability**: No warranty
- ❌ **Trademark use**: Not allowed

---

## 🙏 Acknowledgments

- **Google Gemini** for providing excellent AI capabilities
- **AWS Bedrock** for premium AI services
- **Python Community** for amazing libraries
- **Open Source Contributors** for their valuable work

---

## 📞 Support

- 📧 **Email**: nvtruongops@gmail.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/nvtruongops/ai-quiz-assistant/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/nvtruongops/ai-quiz-assistant/discussions)

---

<div align="center">

**Made with ❤️ for students and learners worldwide**

⭐ Star this repo if you find it helpful!

[⬆️ Back to Top](#-ai-quiz-assistant)

</div>