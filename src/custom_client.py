"""
Custom API Client Module
Support OpenAI-compatible API endpoints (Local LLMs, Claude proxy, vLLM, Ollama, etc.)
"""

import time
import base64
import requests
from typing import Optional, Tuple

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


class CustomAPIClient(BaseAIClient):
    """Client to communicate with OpenAI-compatible vision API"""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        logger: Optional[Logger] = None,
        mode: str = MODE_MULTIPLE_CHOICE,
        answer_display_mode: str = DISPLAY_LETTER_AND_TEXT
    ):
        super().__init__(logger=logger, mode=mode, answer_display_mode=answer_display_mode)
        if not api_url or not api_url.strip():
            raise ValueError("Custom API URL cannot be empty")
        if not api_key or not api_key.strip():
            raise ValueError("Custom API key cannot be empty")
        if not model or not model.strip():
            raise ValueError("Custom Model name cannot be empty")

        self.api_url = api_url.strip().rstrip('/')
        self.api_key = api_key.strip()
        self.model = model.strip()

        if self.logger:
            self.logger.info(f"Custom API client initialized: {self.api_url}, model: {self.model}, mode: {self.mode}, answer_display: {self.answer_display_mode}")

    def update_config(self, api_url: str, api_key: str, model: str) -> None:
        """Update API URL, key, or model configuration dynamically"""
        if api_url:
            self.api_url = api_url.strip().rstrip('/')
        if api_key:
            self.api_key = api_key.strip()
        if model:
            self.model = model.strip()

    @staticmethod
    def list_models(api_url: str, api_key: str = "", timeout: int = 10) -> Tuple[bool, list, str]:
        """Fetch list of available models from an OpenAI-compatible endpoint.
        Returns: (success: bool, model_ids: list[str], message: str)
        """
        if not api_url or not api_url.strip():
            return False, [], "API URL cannot be empty"

        clean_url = api_url.strip().rstrip('/')
        headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        endpoints = []
        if clean_url.endswith('/v1'):
            endpoints.append(f"{clean_url}/models")
        else:
            endpoints.append(f"{clean_url}/v1/models")
            endpoints.append(f"{clean_url}/models")

        if '11434' in clean_url:
            base_host = clean_url.split('/v1')[0]
            endpoints.append(f"{base_host}/api/tags")

        last_error = ""
        for ep in endpoints:
            try:
                resp = requests.get(ep, headers=headers, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    if isinstance(data, dict):
                        if 'data' in data and isinstance(data['data'], list):
                            for item in data['data']:
                                if isinstance(item, dict) and 'id' in item:
                                    models.append(item['id'])
                                elif isinstance(item, str):
                                    models.append(item)
                        elif 'models' in data and isinstance(data['models'], list):
                            for item in data['models']:
                                if isinstance(item, dict):
                                    models.append(item.get('name', item.get('model', '')))
                                elif isinstance(item, str):
                                    models.append(item)
                    if models:
                        seen = set()
                        unique_models = []
                        for m in models:
                            if m and m not in seen:
                                seen.add(m)
                                unique_models.append(m)
                        return True, unique_models, f"Loaded {len(unique_models)} models from endpoint"
                elif resp.status_code == 401:
                    return False, [], "Unauthorized: Invalid API Key"
                else:
                    last_error = f"HTTP {resp.status_code}"
            except requests.exceptions.Timeout:
                last_error = "Connection timeout"
            except requests.exceptions.ConnectionError:
                last_error = f"Cannot connect to {clean_url}"
            except Exception as e:
                last_error = str(e)

        return False, [], f"Failed to fetch models: {last_error or 'Endpoint did not return models'}"

    def test_connection(self) -> Tuple[bool, str, float]:
        """
        Test endpoint connectivity and authentication
        Returns: (success: bool, message: str, latency: float)
        """
        start_time = time.time()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Reply with 'OK'"}],
            "max_tokens": 10
        }

        try:
            resp = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=12
            )
            latency = time.time() - start_time

            if resp.status_code == 200:
                return True, f"Custom API connection successful ({self.model})", latency
            elif resp.status_code == 401:
                return False, "Custom API key invalid (401 Unauthorized)", latency
            elif resp.status_code == 404:
                return False, f"Endpoint or model '{self.model}' not found (404)", latency
            else:
                try:
                    err_msg = resp.json().get('error', {}).get('message', f'Status {resp.status_code}')
                except Exception:
                    err_msg = f"Status {resp.status_code}: {resp.text[:80]}"
                return False, f"Custom API error: {err_msg[:120]}", latency

        except requests.exceptions.Timeout:
            latency = time.time() - start_time
            return False, "Connection timeout to Custom API", latency
        except requests.exceptions.ConnectionError:
            latency = time.time() - start_time
            return False, f"Could not connect to {self.api_url} (Connection Error)", latency
        except Exception as e:
            latency = time.time() - start_time
            return False, f"Custom API connection error: {str(e)[:120]}", latency

    def analyze_quiz(self, image_bytes: bytes, timeout: int = 60) -> QuizResult:
        """
        Send screenshot to OpenAI-compatible API and parse quiz questions
        """
        if self.logger:
            self.logger.info(f"Sending request to Custom API ({self.model}, mode={self.mode}, answer_display={self.answer_display_mode})")

        start_time = time.time()
        prompt = self.build_prompt()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )

            elapsed_time = time.time() - start_time
            if self.logger:
                self.logger.info(f"Received Custom API response in {elapsed_time:.2f}s (status: {response.status_code})")

            if response.status_code == 401:
                raise AuthenticationError("Custom API key is invalid (401 Unauthorized)")
            elif response.status_code != 200:
                err_msg = f"Custom API returned status {response.status_code}"
                try:
                    err_json = response.json()
                    if "error" in err_json:
                        err_msg += f": {err_json['error']}"
                except Exception:
                    pass
                raise AIClientError(err_msg)

            resp_text = response.text.strip()
            response_text = ""

            if resp_text.startswith("data:") or "\ndata:" in resp_text:
                # Server sent SSE / chunked streaming format
                chunks = []
                for line in resp_text.splitlines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        for choice in chunk.get("choices", []):
                            delta = choice.get("delta", {})
                            if "content" in delta and delta["content"]:
                                chunks.append(delta["content"])
                            elif "text" in delta and delta["text"]:
                                chunks.append(delta["text"])
                    except Exception:
                        pass
                response_text = "".join(chunks)
            else:
                response_data = response.json()
                if "choices" not in response_data or not response_data["choices"]:
                    raise AIClientError("Custom API returned empty choices")

                choice = response_data["choices"][0]
                response_text = choice.get("message", {}).get("content", "")

            if not response_text:
                raise AIClientError("Custom API returned empty message content")

            result = self.parse_quiz_response(response_text)
            result.provider_name = "Custom"
            result.model_name = self.model
            result.mode = self.mode
            return result

        except NoQuestionsFoundError:
            raise
        except AuthenticationError:
            raise
        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.error(f"Custom API request timed out after {timeout}s")
            raise TimeoutError(f"Custom API timed out after {timeout} seconds")
        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.error(f"Custom API HTTP request failed: {e}", exc_info=True)
            raise AIClientError(f"HTTP request failed: {str(e)}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in Custom API processing: {e}", exc_info=True)
            raise AIClientError(f"Error calling Custom API: {str(e)}")
