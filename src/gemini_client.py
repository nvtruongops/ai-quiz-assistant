"""
Gemini API Client Module
Communicate with Google Gemini API using google-genai SDK
"""

import time
from typing import Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import ClientError, APIError

try:
    from base_client import (
        BaseAIClient,
        MODE_MULTIPLE_CHOICE,
        MODE_MC_EXPLANATION,
        MODE_ESSAY,
        DISPLAY_LETTER_AND_TEXT,
        DISPLAY_LETTER_ONLY,
        NoQuestionsFoundError,
        AuthenticationError,
        AIClientError
    )
    from models import QuizResult
    from logger import Logger
except ImportError:
    from src.base_client import (
        BaseAIClient,
        MODE_MULTIPLE_CHOICE,
        MODE_MC_EXPLANATION,
        MODE_ESSAY,
        DISPLAY_LETTER_AND_TEXT,
        DISPLAY_LETTER_ONLY,
        NoQuestionsFoundError,
        AuthenticationError,
        AIClientError
    )
    from src.models import QuizResult
    from src.logger import Logger

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"


class GeminiAPIClient(BaseAIClient):
    """Client to communicate with Google Gemini API"""

    def __init__(
        self,
        api_key: str,
        logger: Optional[Logger] = None,
        mode: str = MODE_MULTIPLE_CHOICE,
        model_name: str = DEFAULT_GEMINI_MODEL,
        answer_display_mode: str = DISPLAY_LETTER_AND_TEXT
    ):
        super().__init__(logger=logger, mode=mode, answer_display_mode=answer_display_mode)
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key cannot be empty")

        self.api_key = api_key.strip()
        self.model_name = model_name or DEFAULT_GEMINI_MODEL
        self.client: Optional[genai.Client] = None
        self.initialize()

    def initialize(self) -> None:
        """Initialize Google GenAI client"""
        try:
            self.client = genai.Client(api_key=self.api_key)
            if self.logger:
                self.logger.info(f"Gemini API client initialized successfully (model: {self.model_name})")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Gemini API client: {e}", exc_info=True)
            raise

    def set_model(self, model_name: str) -> None:
        """Update active Gemini model name"""
        if model_name and model_name.strip():
            self.model_name = model_name.strip()
            if self.logger:
                self.logger.info(f"Gemini model changed to: {self.model_name}")

    @staticmethod
    def list_models(api_key: str, timeout: int = 10) -> Tuple[bool, list, str]:
        """Fetch list of available models from Google Gemini API.
        Filters for models supporting generateContent (vision / multimodal).
        Returns: (success: bool, model_names: list[str], message: str)
        """
        if not api_key or not api_key.strip():
            return False, [], "API key cannot be empty"

        try:
            client = genai.Client(api_key=api_key.strip())
            models = []
            for m in client.models.list():
                actions = getattr(m, 'supported_actions', []) or getattr(m, 'supported_generation_methods', [])
                name = m.name.replace('models/', '') if m.name else ''
                if 'generateContent' in actions and name:
                    if 'embedding' not in name.lower() and 'imagen' not in name.lower():
                        models.append(name)

            if models:
                def sort_key(name):
                    n = name.lower()
                    if '3.1-flash-lite' in n:
                        return (0, 0, n)
                    if '3.5-flash-lite' in n:
                        return (0, 1, n)
                    if 'flash-lite' in n:
                        return (0, 2, n)
                    if '3.1-flash' in n:
                        return (1, 0, n)
                    if '3.5-flash' in n:
                        return (1, 1, n)
                    if 'flash' in n:
                        return (1, 2, n)
                    if 'pro' in n:
                        return (2, 0, n)
                    return (3, 0, n)
                models.sort(key=sort_key)
                return True, models, f"Loaded {len(models)} models from Google Gemini"
            return False, [], "No generateContent models found for this API key"
        except ClientError as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "API key not valid" in err:
                return False, [], "Invalid API key"
            return False, [], f"Gemini error: {err[:100]}"
        except Exception as e:
            return False, [], f"Connection error: {str(e)[:100]}"

    def test_connection(self) -> Tuple[bool, str, float]:
        """
        Test API connection and credentials
        Returns: (success: bool, message: str, latency: float)
        """
        start_time = time.time()
        try:
            if not self.client:
                self.initialize()

            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Reply with exactly 'OK'",
                config=types.GenerateContentConfig(
                    max_output_tokens=10,
                    temperature=0.1,
                    http_options=types.HttpOptions(timeout=10000)
                )
            )
            latency = time.time() - start_time
            if response and response.text:
                return True, f"Gemini connection successful ({self.model_name})", latency
            return False, "Gemini returned empty response", latency

        except ClientError as e:
            latency = time.time() - start_time
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                return False, "Invalid API key", latency
            elif "NOT_FOUND" in err_str:
                return False, f"Model '{self.model_name}' not found", latency
            elif "RESOURCE_EXHAUSTED" in err_str:
                return False, "Quota exceeded", latency
            elif "DEADLINE_EXCEEDED" in err_str or "504" in err_str:
                return False, f"Connection timed out ({self.model_name})", latency
            elif "UNAVAILABLE" in err_str or "503" in err_str:
                return False, f"Model overloaded (503): try a flash-lite model", latency
            return False, f"Gemini error: {err_str[:120]}", latency

        except Exception as e:
            latency = time.time() - start_time
            err_str = str(e)
            if "DEADLINE_EXCEEDED" in err_str or "504" in err_str or "timeout" in err_str.lower():
                return False, f"Connection timed out ({self.model_name})", latency
            return False, f"Connection error: {err_str[:120]}", latency

    def analyze_quiz(self, image_bytes: bytes, timeout: int = 35) -> QuizResult:
        """
        Send screenshot to Gemini API and parse quiz questions.
        Enforces timeout in milliseconds via http_options.
        """
        if not self.client:
            raise AIClientError("Gemini client not initialized")

        if self.logger:
            self.logger.info(f"Sending quiz image to Gemini API ({self.model_name}, mode={self.mode}, answer_display={self.answer_display_mode})")

        start_time = time.time()
        prompt = self.build_prompt()

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            types.Part.from_text(text=prompt)
        ]

        try:
            timeout_ms = int(timeout * 1000) if timeout else 35000
            gen_config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                http_options=types.HttpOptions(timeout=timeout_ms)
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config
            )

            elapsed_time = time.time() - start_time
            if self.logger:
                self.logger.info(f"Received Gemini response in {elapsed_time:.2f}s")

            if not response or not response.text:
                raise AIClientError("Gemini returned empty response text")

            result = self.parse_quiz_response(response.text)
            result.provider_name = "Gemini"
            result.model_name = self.model_name
            result.mode = self.mode
            return result

        except NoQuestionsFoundError:
            raise

        except TimeoutError:
            raise

        except (ClientError, APIError) as e:
            err_str = str(e)
            if self.logger:
                self.logger.error(f"Gemini ClientError: {err_str}", exc_info=True)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                raise AuthenticationError("Gemini API key is invalid")
            elif "NOT_FOUND" in err_str:
                raise AIClientError(f"Model '{self.model_name}' not available. Please switch model in settings.")
            elif "DEADLINE_EXCEEDED" in err_str or "504" in err_str:
                raise TimeoutError(f"Gemini API timed out after {timeout}s ({self.model_name}). Please switch to a faster model (e.g. gemini-3.1-flash-lite) in Settings (Alt+S).")
            elif "UNAVAILABLE" in err_str or "503" in err_str:
                raise AIClientError(f"Gemini model '{self.model_name}' is currently overloaded (503). Please switch to gemini-3.1-flash-lite in Settings (Alt+S).")
            raise AIClientError(f"Gemini API error: {err_str[:120]}")

        except Exception as e:
            err_str = str(e)
            if "DEADLINE_EXCEEDED" in err_str or "504" in err_str or "timeout" in err_str.lower():
                raise TimeoutError(f"Gemini API timed out after {timeout}s ({self.model_name}). Please switch to gemini-3.1-flash-lite.")
            if self.logger:
                self.logger.error(f"Gemini request failed: {e}", exc_info=True)
            raise AIClientError(f"Error calling Gemini API: {str(e)}")
