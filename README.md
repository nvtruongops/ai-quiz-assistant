# AI Quiz Assistant

An AI-powered application that helps answer multiple-choice questions by capturing screenshots and analyzing them with Google Gemini or AWS Bedrock.

## 🚀 Installation

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AI Provider
Run the setup script to configure the AI provider:
```bash
python setup.py
```

The script will ask you to choose:
- **1. Setup Google Gemini**: Free, easy setup (only needs API key)
- **2. Setup AWS Bedrock**: Higher quality, requires AWS credentials
- **3. View current configuration**: Display status of both providers
- **4. Switch AI Provider**: Switch between Gemini and Bedrock

**Setup will automatically test API** after you enter information to ensure correct configuration.

### 3. Run the application
```bash
python run.pyw
```

## 🎮 Usage

### Hotkeys:
- **Alt + Z** or **Middle Mouse Button + Scroll Up**: Capture screen and analyze
- **Alt + X**: Show/hide analysis results
- **Alt + C** or **Middle Mouse Button + Scroll Down**: Show all saved answers
- **Alt + R**: Reset answer history
- **Alt + S**: Switch AI provider (Gemini ↔ Bedrock)
- **Delete**: Clear all logs and answers
- **Backtick (`)**: Exit program

### Usage workflow:
1. Open the exam/questions on screen
2. Press **Alt + Z** to capture and analyze
3. Press **Alt + X** to view results
4. Press **Alt + C** to view saved answers

## ⚙️ Configuration

### Quick setup (Recommended)
Run `python setup.py` and set up each provider one by one. You can set up both Gemini and Bedrock without losing the configuration of the other provider. Then you can switch between the two providers anytime with Alt+S.

### Google Gemini (Recommended for beginners)
1. Visit: https://makersuite.google.com/app/apikey
2. Create a new API key
3. Run `python setup.py` and choose option 1
4. Enter API key (will be hashed and stored securely)

### AWS Bedrock (For advanced users)
1. Need AWS account with Bedrock access
2. Run `python setup.py` and choose option 2
3. Enter AWS Access Key ID and Secret Access Key
4. Choose region (default: us-east-1)

### Switch Provider
- Press **Alt+S** in the application to switch
- Or run `python setup.py` → option 4
- **Note**: Need to set up both providers before switching

### Test API Connection
- Run `python setup.py` and choose option 6
- Or setup will automatically test after configuration
- Test sends a sample question to check API functionality

## 📁 Directory Structure

```
├── src/                    # Source code
├── logs/                   # Log files and answers.txt
├── config.json             # AI configuration (auto-generated)
├── setup.py               # Configuration script
├── run.pyw                # Entry point
└── requirements.txt       # Dependencies
```

## 🔒 Security

- API keys are hashed before storage
- `config.json` file is ignored in git
- AWS credentials stored locally only, not synced to git

## 🐛 Troubleshooting

### "Invalid API key" error
- Run `python setup.py` again to reconfigure

### AWS credentials error
- Check if AWS credentials are correct
- Ensure region is supported by Bedrock

### App not responding
- Check `logs/app.log` file for errors
- Restart the application

## 📝 License

MIT License