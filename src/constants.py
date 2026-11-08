"""
Application Constants & Production URLs
Single source of truth for versions, endpoints, and external links.
"""

APP_NAME = "AI Quiz Assistant"
APP_VERSION = "2.0.0"
APP_DISPLAY_NAME = f"{APP_NAME} {APP_VERSION}"
COPYRIGHT = "MIT License"

# Official Production URLs
GITHUB_REPO_URL = "https://github.com/nvtruongops/ai-quiz-assistant"
GITHUB_RELEASES_URL = "https://github.com/nvtruongops/ai-quiz-assistant/releases"
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/nvtruongops/ai-quiz-assistant/releases/latest"
GITHUB_ISSUES_URL = "https://github.com/nvtruongops/ai-quiz-assistant/issues"
DOCUMENTATION_URL = "https://github.com/nvtruongops/ai-quiz-assistant#readme"

# AI Provider Official Portals & Production Endpoints
GOOGLE_AI_STUDIO_API_KEY_URL = "https://aistudio.google.com/app/apikey"
DEFAULT_LOCAL_ENDPOINT_URL = "http://localhost:11434/v1"
DEFAULT_LOCAL_VISION_MODEL = "llama3.2-vision"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# Fallback vision models for local Ollama / OpenAI-compatible servers
POPULAR_LOCAL_MODELS = [
    "llama3.2-vision",
    "qwen2.5-vl:latest",
    "llama3.2-vision:11b",
    "minicpm-v:latest"
]
