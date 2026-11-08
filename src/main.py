"""
Main Application Module
Entry point and coordinator for AI Quiz Assistant application.
"""

import sys
import os

# Ensure src directory and project root are in sys.path
_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
try:
    if os.getcwd() != _root_dir:
        os.chdir(_root_dir)
except Exception:
    pass

# Ensure Windows DPI awareness is established at the very beginning of the process
if sys.platform == 'win32':
    try:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
    except Exception:
        pass

import threading
import time
import json
import re
import queue
from typing import Optional, Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, Future

try:
    from config_manager import ConfigManager
    from logger import Logger
    from screenshot_manager import ScreenshotManager
    from gemini_client import GeminiAPIClient
    from custom_client import CustomAPIClient
    from base_client import (
        BaseAIClient,
        MODE_MULTIPLE_CHOICE,
        MODE_ESSAY,
        DISPLAY_LETTER_AND_TEXT,
        DISPLAY_LETTER_ONLY,
        NoQuestionsFoundError,
        AuthenticationError,
        AIClientError
    )
    from request_manager import RequestManager
    from popup_manager import PopupManager
    from autofill_manager import AutoFillManager
    from hotkey_listener import HotkeyListener
    from system_tray import SystemTray
    from models import QuizResult, QuizQuestion
    from settings_manager import (
        SettingsManager,
        show_api_key_dialog,
        show_settings_dialog,
        show_initial_setup_dialog
    )
except ImportError:
    from src.config_manager import ConfigManager
    from src.logger import Logger
    from src.screenshot_manager import ScreenshotManager
    from src.gemini_client import GeminiAPIClient
    from src.custom_client import CustomAPIClient
    from src.base_client import (
        BaseAIClient,
        MODE_MULTIPLE_CHOICE,
        MODE_ESSAY,
        DISPLAY_LETTER_AND_TEXT,
        DISPLAY_LETTER_ONLY,
        NoQuestionsFoundError,
        AuthenticationError,
        AIClientError
    )
    from src.request_manager import RequestManager
    from src.popup_manager import PopupManager
    from src.autofill_manager import AutoFillManager
    from src.hotkey_listener import HotkeyListener
    from src.system_tray import SystemTray
    from src.models import QuizResult, QuizQuestion
    from src.settings_manager import (
        SettingsManager,
        show_api_key_dialog,
        show_settings_dialog,
        show_initial_setup_dialog
    )


class QuizAssistantApp:
    """Main application controller for AI Quiz Assistant"""

    def __init__(self):
        # 1. Initialize Logger
        self.logger = Logger()
        self.logger.info("Initializing AI Quiz Assistant 2.0...")
        self.project_root = _root_dir

        # 2. Initialize Settings & Config
        self.settings_manager = SettingsManager()
        self.config_manager = ConfigManager()

        # 3. Check credentials and setup if needed
        self._ensure_credentials()

        # 4. Initialize Core Managers
        self.request_manager = RequestManager()
        self.screenshot_manager = ScreenshotManager(
            logger=self.logger,
            save_screenshots=self.settings_manager.get('save_screenshots', True)
        )

        # 5. Initialize UI Popup Manager & AutoFill Manager
        self.popup_manager = PopupManager(
            config_manager=self.config_manager,
            settings_manager=self.settings_manager,
            on_prev=self.on_nav_prev,
            on_next=self.on_nav_next,
            on_reload=self.on_nav_reload
        )
        self.autofill_manager = AutoFillManager(
            logger=self.logger,
            settings_manager=self.settings_manager
        )

        # 6. Initialize AI Client
        self.ai_client: Optional[BaseAIClient] = None
        self._initialize_ai_client()

        # 7. Initialize Hotkey Listener
        self.hotkey_listener = HotkeyListener(
            on_capture_key=self.on_capture_hotkey,
            on_autofill_key=self.on_autofill_hotkey,
            on_hide_key=self.on_hide_hotkey,
            on_exit_key=self.on_exit_hotkey,
            on_clear_logs=self.on_clear_logs_hotkey,
            on_show_answers=self.on_show_answers_hotkey,
            on_show_detailed_history=self.on_show_detailed_history_hotkey,
            on_reset_answers=self.on_reset_answers_hotkey,
            on_setup=self.on_setup_hotkey,
            settings_manager=self.settings_manager
        )

        # 8. Initialize System Tray
        self.system_tray = SystemTray(app=self)

        # 9. Queue & Worker Thread for Sequential Processing & Deduplication
        self._capture_queue: queue.Queue = queue.Queue()
        self._image_cache: Dict[str, QuizResult] = {}
        self._is_queue_processing: bool = False
        self._latest_error: Optional[str] = None
        self._queue_worker_thread = threading.Thread(
            target=self._queue_worker_loop,
            daemon=True,
            name="CaptureQueueWorker"
        )
        self._queue_worker_thread.start()

        # 10. Async Worker ThreadPool (kept for auxiliary tasks)
        self._thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="QuizWorker")
        self._active_futures: Dict[str, Future] = {}

        # 11. Runtime state & Navigation tracking
        self._running = False
        self._last_capture_time = 0.0
        self._capture_cooldown = 0.15  # Fast capture cooldown to allow queuing rapid captures
        self._answer_history = []
        self._latest_result: Optional[QuizResult] = None
        self._current_view_index = -1
        self._last_viewed_history_index = -1
        self._is_showing_history = False
        self._settings_open = False
        self._answer_file = os.path.join(_root_dir, "logs", "answers.json")
        self._answer_txt_file = os.path.join(_root_dir, "logs", "answers.txt")
        self._load_answers_from_file()

        self.logger.info("QuizAssistantApp initialized successfully")

    def _ensure_credentials(self) -> None:
        """Verify API keys exist, prompting initial setup dialog if credentials missing"""
        if not self.config_manager.is_valid():
            self.logger.info("API credentials not found or incomplete, prompting initial setup dialog...")
            success = show_initial_setup_dialog(
                config_manager=self.config_manager,
                settings_manager=self.settings_manager
            )
            if success:
                self.config_manager.reload()
                self.settings_manager.load_settings()
                self.logger.info("Credentials configured successfully via setup dialog")
            else:
                self.logger.error("No valid credentials provided, exiting")
                sys.exit(1)
        else:
            self.logger.info(f"Loaded valid credentials for provider '{self.config_manager.get('API_PROVIDER', 'gemini')}'")

    def _initialize_ai_client(self) -> None:
        """Initialize or dynamically re-initialize AI client based on current settings"""
        try:
            self.config_manager.reload()
            provider = self.config_manager.get('API_PROVIDER', 'gemini')
            mode = self.settings_manager.get('question_mode', 'multiple_choice')
            ans_disp = self.settings_manager.get('answer_display_mode', 'letter_and_text')

            if provider == 'custom':
                custom_url = self.config_manager.get('CUSTOM_API_URL', 'http://localhost:11434/v1')
                custom_key = self.config_manager.get('CUSTOM_API_KEY', '')
                custom_model = self.config_manager.get('CUSTOM_MODEL', '')

                self.ai_client = CustomAPIClient(
                    api_url=custom_url,
                    api_key=custom_key,
                    model=custom_model,
                    logger=self.logger,
                    mode=mode,
                    answer_display_mode=ans_disp
                )
                if hasattr(self, 'popup_manager') and self.popup_manager:
                    self.popup_manager.set_provider_info(f"Custom ({custom_model or 'model'})", mode)
                self.logger.info(f"Initialized Custom AI client: {custom_url} [{custom_model}] (mode: {mode}, ans_display: {ans_disp})")

            else:
                gemini_key = self.config_manager.get('GEMINI_API_KEY', '')
                gemini_model = self.config_manager.get('GEMINI_MODEL', '')

                self.ai_client = GeminiAPIClient(
                    api_key=gemini_key,
                    logger=self.logger,
                    mode=mode,
                    model_name=gemini_model,
                    answer_display_mode=ans_disp
                )
                if hasattr(self, 'popup_manager') and self.popup_manager:
                    self.popup_manager.set_provider_info(f"Gemini ({gemini_model})", mode)
                self.logger.info(f"Initialized Gemini AI client [{gemini_model}] (mode: {mode}, ans_display: {ans_disp})")

        except Exception as e:
            self.logger.error(f"Failed to initialize AI client: {e}", exc_info=True)

    def start(self):
        """Start application services and enter event loop"""
        if self._running:
            return
        self._running = True
        self.logger.info("Starting AI Quiz Assistant background services...")

        try:
            self.system_tray.start()
            self.hotkey_listener.start()

            provider = self.config_manager.get('API_PROVIDER', 'gemini')
            p_text = "Google Gemini" if provider == 'gemini' else "Custom Local"
            hk_cap = self.settings_manager.get('hotkey_capture', 'z').upper()
            hk_fill = self.settings_manager.get('hotkey_autofill', 'x').upper()
            hk_ans = self.settings_manager.get('hotkey_answers', 'c').upper()
            hk_his = self.settings_manager.get('hotkey_history', 'h').upper()
            self.system_tray.show_notification(
                "AI Quiz Assistant",
                f"Using {p_text}.\nAlt+{hk_cap}: Capture | Alt+{hk_fill}: Auto-Fill | Alt+{hk_ans}: Latest | Alt+{hk_his}: History"
            )

            while self._running:
                time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error in main app loop: {e}", exc_info=True)
            self.stop()

    def on_capture_hotkey(self):
        """
        Handle Capture hotkey (Alt+Z or Middle Scroll Up)
        Enqueues screenshot for sequential processing without automatically opening UI popup.
        """
        now = time.time()
        if now - self._last_capture_time < self._capture_cooldown:
            self.logger.info("Capture suppressed (cooldown active)")
            return
        self._last_capture_time = now

        self.logger.info("Capture hotkey triggered")

        # If user had any open popup, close it on capture to clear view
        if self.popup_manager.is_visible():
            self.popup_manager.hide()

        try:
            screenshot = self.screenshot_manager.capture_screen()
            if screenshot is None:
                self.logger.error("Screenshot capture failed: screenshot is None")
                self._latest_error = "Could not capture screen. Please try again."
                return

            image_bytes = self.screenshot_manager.save_to_memory(screenshot)
            if not image_bytes:
                self.logger.error("Failed to convert screenshot to memory bytes")
                self._latest_error = "Failed to process screenshot."
                return

            img_hash = self.screenshot_manager.compute_image_hash(screenshot)
            req_id = self.request_manager.create_request()

            # Enqueue task for sequential background worker
            item = {
                "req_id": req_id,
                "screenshot": screenshot,
                "image_bytes": image_bytes,
                "img_hash": img_hash,
                "captured_at": now
            }
            self._capture_queue.put(item)
            q_size = self._capture_queue.qsize()
            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
            self.logger.info(
                f"Screenshot enqueued [req_id={req_id}, hash={img_hash[:16]}..., queue_size={q_size}]. "
                "Background processing active (silent)."
            )

        except Exception as e:
            self.logger.error(f"Capture error: {e}", exc_info=True)
            self._latest_error = f"Screenshot error: {str(e)[:80]}"

    def on_autofill_hotkey(self):
        """
        Handle Auto-Fill hotkey (Alt+X)
        Captures screen, solves questions via AI, and automatically navigates cursor to click answer choices.
        """
        if hasattr(self, 'autofill_manager') and not self.autofill_manager.is_enabled():
            self.logger.warning("Auto-fill hotkey triggered but feature is disabled in settings")
            return

        now = time.time()
        if now - self._last_capture_time < self._capture_cooldown:
            self.logger.info("Auto-fill capture suppressed (cooldown active)")
            return
        self._last_capture_time = now

        self.logger.info("⚡ Auto-fill hotkey triggered (Alt+X)")

        # Hide any open popup
        if self.popup_manager.is_visible():
            self.popup_manager.hide()

        try:
            screenshot = self.screenshot_manager.capture_screen()
            if screenshot is None:
                self.logger.error("Auto-fill screenshot capture failed: screenshot is None")
                self._latest_error = "Could not capture screen for auto-fill. Please try again."
                return

            capture_bbox = self.screenshot_manager.get_last_capture_bbox()
            image_bytes = self.screenshot_manager.save_to_memory(screenshot)
            if not image_bytes:
                self.logger.error("Failed to convert screenshot to memory bytes for auto-fill")
                self._latest_error = "Failed to process screenshot."
                return

            img_hash = self.screenshot_manager.compute_image_hash(screenshot)
            req_id = self.request_manager.create_request()

            item = {
                "req_id": req_id,
                "screenshot": screenshot,
                "image_bytes": image_bytes,
                "img_hash": img_hash,
                "captured_at": now,
                "is_autofill": True,
                "capture_bbox": capture_bbox
            }
            self._capture_queue.put(item)
            q_size = self._capture_queue.qsize()

            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass

            self.logger.info(
                f"Auto-fill task enqueued [req_id={req_id}, hash={img_hash[:16]}..., queue_size={q_size}]. "
                "Background AI analysis and automated clicking will follow."
            )

        except Exception as e:
            self.logger.error(f"Auto-fill capture error: {e}", exc_info=True)
            self._latest_error = f"Auto-fill error: {str(e)[:80]}"

    def _queue_worker_loop(self):
        """Dedicated background thread that processes screenshot captures sequentially (FIFO)"""
        self.logger.info("Capture queue worker loop started")
        while True:
            try:
                item = self._capture_queue.get()
                if item is None:
                    # Termination sentinel
                    self._capture_queue.task_done()
                    break

                self._is_queue_processing = True
                self._process_queue_item(item)
                self._capture_queue.task_done()
                self._is_queue_processing = False

            except Exception as e:
                self.logger.error(f"Error in queue worker loop: {e}", exc_info=True)
                self._is_queue_processing = False

    def _process_queue_item(self, item: dict):
        """Process a single queued screenshot item with deduplication caching and optional auto-fill"""
        req_id = item["req_id"]
        img_hash = item["img_hash"]
        image_bytes = item["image_bytes"]
        is_autofill = item.get("is_autofill", False)
        capture_bbox = item.get("capture_bbox") or self.screenshot_manager.get_last_capture_bbox()

        # 1. Deduplication check: Has this exact image been processed in this session?
        if img_hash and img_hash in self._image_cache:
            cached_result = self._image_cache[img_hash]
            self.logger.info(
                f"⚡ [Deduplication Hit] Image hash {img_hash[:16]}... matched session cache! "
                f"Reusing cached result ({len(cached_result.questions)} questions) immediately without AI call."
            )
            self._latest_result = cached_result
            self._latest_error = None
            self.request_manager.set_result(cached_result)

            if is_autofill and hasattr(self, 'autofill_manager') and self.autofill_manager.is_enabled():
                self._execute_autofill(cached_result, capture_bbox)
            return

        # 2. Cache miss: Call AI client
        self.logger.info(f"Processing screenshot via AI (req_id={req_id}, hash={img_hash[:16]}..., autofill={is_autofill})")
        try:
            if not self.ai_client:
                self._initialize_ai_client()

            result = self.ai_client.analyze_quiz(image_bytes)
            self._handle_api_success(result, req_id, img_hash)

            if is_autofill and hasattr(self, 'autofill_manager') and self.autofill_manager.is_enabled():
                self._execute_autofill(result, capture_bbox)

        except NoQuestionsFoundError:
            err_msg = "No questions found in the screenshot."
            self.logger.info(f"No questions found for request {req_id}")
            self._latest_error = err_msg
            self.request_manager.set_error(err_msg)

        except AuthenticationError as e:
            err_msg = f"API Key Authentication Error: {str(e)}"
            self.logger.error(f"Authentication error: {e}")
            self._latest_error = err_msg
            self.request_manager.set_error(err_msg)

        except TimeoutError as e:
            err_msg = f"AI response timeout ({str(e)})."
            self.logger.error(f"Timeout error: {e}")
            self._latest_error = err_msg
            self.request_manager.set_error(err_msg)

        except Exception as e:
            err_msg = f"Processing error: {str(e)[:120]}"
            self.logger.error(f"API processing error: {e}", exc_info=True)
            self._latest_error = err_msg
            self.request_manager.set_error(err_msg)

    def _execute_autofill(self, result: QuizResult, capture_bbox: Optional[Tuple[int, int, int, int]] = None):
        """Execute automated answer clicking in background"""
        def on_finished(success_clicks: int, total_targets: int, filled_summary: List[str]):
            self.logger.info(
                f"⚡ Auto-fill completed: {success_clicks}/{total_targets} answers filled. "
                f"Items: {', '.join(filled_summary) if filled_summary else 'None'}"
            )
            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK if success_clicks > 0 else winsound.MB_ICONHAND)
                except Exception:
                    pass

        self.logger.info(f"Starting auto-fill execution for {len(result.questions)} questions...")
        self.autofill_manager.fill_answers_async(
            quiz_result=result,
            capture_bbox=capture_bbox,
            on_finished=on_finished
        )

    def _handle_api_success(self, result: QuizResult, request_id: str, img_hash: str):
        """
        Handle successful AI response:
        - Re-numbers questions sequentially (1..x)
        - Caches result by image hash for deduplication
        - Appends to history and saves to file
        - SILENT: Does NOT automatically display popup UI! (User opens via hotkey)
        """
        try:
            provider = self.config_manager.get('API_PROVIDER', 'gemini')
            result.provider_name = "Gemini" if provider == 'gemini' else "Custom Local"
            result.mode = self.settings_manager.get('question_mode', 'multiple_choice')

            # Re-number questions sequentially based on history length!
            # Avoids exam numbers (e.g. screen has 'Question 3' on 1st capture -> becomes 'Question 1')
            start_num = len(self._answer_history) + 1
            for idx, q in enumerate(result.questions):
                q.exam_number = q.number
                q.number = str(start_num + idx)
                if not q.answer or not q.answer.strip():
                    q.answer = "[Answer not identified]"

            self._latest_result = result
            self._latest_error = None
            self.request_manager.set_result(result)

            # Store in session image cache for deduplication
            if img_hash:
                self._image_cache[img_hash] = result

            # Append to history with sequential numbering
            for q in result.questions:
                self._answer_history.append({
                    "number": q.number,
                    "exam_number": q.exam_number,
                    "question": q.question,
                    "answer": q.answer,
                    "explanation": getattr(q, 'explanation', ''),
                    "timestamp": time.time(),
                    "provider": result.provider_name
                })

            self._save_answers_to_file()
            self.logger.info(
                f"Successfully processed request {request_id}: {len(result.questions)} questions "
                f"(numbered {start_num}..{start_num+len(result.questions)-1}). Cached silently."
            )

            # NOTE: Result is cached 100% silently in history.
            # Do NOT automatically pop up or refresh the UI on AI completion.
            # The UI is only opened when the user presses the hotkey (Alt+C / Alt+H)
            # or updated when the user clicks the reload button (🔄) inside the popup.

        except Exception as e:
            self.logger.error(f"Error handling API success: {e}", exc_info=True)

    def _on_api_success(self, result: QuizResult, request_id: str):
        """Backward-compatible wrapper for _handle_api_success"""
        self._handle_api_success(result, request_id, "")

    def _handle_future_completion(self, future: Future, request_id: str):
        """Cleanup completed background futures"""
        if request_id in self._active_futures:
            del self._active_futures[request_id]

    def on_hide_hotkey(self):
        """Hide popup"""
        if self.popup_manager.is_visible():
            self.popup_manager.hide()

    def _show_question_at_index(self, idx: int):
        """Display question and answers at a specific index from history, with navigation context"""
        self._is_showing_history = False

        hk_cap = self.settings_manager.get('hotkey_capture', 'z').upper() if self.settings_manager else 'Z'
        if not self._answer_history:
            q_size = self._capture_queue.qsize()
            if self._is_queue_processing or q_size > 0:
                total_pending = q_size + (1 if self._is_queue_processing else 0)
                prov = "Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom"
                self.popup_manager.show(
                    f"⏳ Analyzing screenshot... ({total_pending} images pending in queue)\n\n"
                    f"🤖 AI: {prov}\n"
                    f"Results will update automatically once completed (or click 🔄).",
                    title="Queue Processing",
                    provider=prov
                )
                self._current_view_index = -1
            else:
                self.popup_manager.show(
                    f"📸 No quiz questions recorded yet.\n\nPress Alt+{hk_cap} to capture and analyze a question.",
                    title="No Questions"
                )
            return

        if idx < 0:
            idx = 0

        # If user navigates past the end of history, check if queue is still working on new questions
        if idx >= len(self._answer_history):
            q_size = self._capture_queue.qsize()
            if self._is_queue_processing or q_size > 0:
                total_pending = q_size + (1 if self._is_queue_processing else 0)
                prov = "Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom"
                self.popup_manager.show(
                    f"⏳ Analyzing next question... ({total_pending} images pending in queue)\n\n"
                    f"🤖 AI: {prov}\n"
                    f"Answer will update automatically once completed (or click 🔄).",
                    title=f"Question {len(self._answer_history) + 1} (Processing)",
                    provider=prov
                )
                self._current_view_index = idx
                return
            else:
                idx = len(self._answer_history) - 1

        self._current_view_index = idx
        self._last_viewed_history_index = max(self._last_viewed_history_index, idx)

        raw_item = self._answer_history[idx]
        total = len(self._answer_history)
        if isinstance(raw_item, dict):
            item = QuizQuestion(
                number=str(raw_item.get("number", idx + 1)),
                question=str(raw_item.get("question", "")),
                answer=str(raw_item.get("answer", "")),
                explanation=str(raw_item.get("explanation", "")),
                exam_number=str(raw_item.get("exam_number", ""))
            )
            prov = raw_item.get("provider") or ("Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom")
        else:
            item = raw_item
            prov = getattr(item, "provider", None) or ("Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom")
        mode = self.settings_manager.get('question_mode', 'multiple_choice')
        mode_title = "Essay" if mode == "essay" else ("MC+Exp" if mode == "multiple_choice_explanation" else "Multiple Choice")

        pending_hint = " ⏳" if (self._is_queue_processing or self._capture_queue.qsize() > 0) else ""
        title = f"Question {idx + 1}/{total}{pending_hint}"

        self.popup_manager.show_questions(
            [item],
            title=title,
            provider=prov,
            mode=mode_title,
            is_history=False
        )
        self.logger.info(f"Displayed question index {idx} ({title})")

    def on_nav_prev(self):
        """Navigate to previous question in history (▲ button or Up arrow in single question mode)"""
        if getattr(self, '_is_showing_history', False):
            return
        if not self._answer_history:
            return
        if self._current_view_index > 0:
            self._show_question_at_index(self._current_view_index - 1)
        else:
            self.logger.info("Already at first question")

    def on_nav_next(self):
        """Navigate to next question in history or queue (▼ button or Down arrow in single question mode)"""
        if getattr(self, '_is_showing_history', False):
            return
        if not self._answer_history and not self._is_queue_processing and self._capture_queue.empty():
            return

        next_idx = self._current_view_index + 1
        if next_idx < len(self._answer_history):
            self._show_question_at_index(next_idx)
        else:
            q_size = self._capture_queue.qsize()
            if self._is_queue_processing or q_size > 0:
                self._show_question_at_index(next_idx)
            else:
                self.logger.info("Already at newest question")

    def on_nav_reload(self):
        """Reload current view (🔄 button or F5)"""
        self.logger.info("Manual reload triggered")
        if getattr(self, '_is_showing_history', False):
            self.on_show_detailed_history_hotkey(toggle=False)
        elif self._current_view_index >= 0:
            self._show_question_at_index(self._current_view_index)
        else:
            self.on_show_answers_hotkey()

    def on_show_answers_hotkey(self):
        """
        Handle Alt+C hotkey - Show first unviewed question or next question in queue.
        If user previously hid UI at question x, and new questions arrived, opens question x+1 (first unviewed).
        """
        self.logger.info("Show answers hotkey triggered (Alt+C)")

        try:
            if self.popup_manager.is_visible() and not getattr(self, '_is_showing_history', False):
                self.popup_manager.hide()
                self.logger.info("Popup hidden by Alt+C")
                return

            self._is_showing_history = False

            if not self._answer_history:
                q_size = self._capture_queue.qsize()
                if self._is_queue_processing or q_size > 0:
                    total_pending = q_size + (1 if self._is_queue_processing else 0)
                    prov = "Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom"
                    hk_cap = self.settings_manager.get('hotkey_capture', 'z').upper() if self.settings_manager else 'Z'
                    self.popup_manager.show(
                        f"⏳ Analyzing images in queue... ({total_pending} pending)\n\n"
                        f"🤖 AI: {prov}\n"
                        f"Results will update automatically once completed.",
                        title="Queue Processing",
                        provider=prov
                    )
                    self._current_view_index = -1
                elif self._latest_error:
                    prov = "Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom"
                    hk_cap = self.settings_manager.get('hotkey_capture', 'z').upper() if self.settings_manager else 'Z'
                    self.popup_manager.show(
                        f"⚠️ Notice from previous capture:\n{self._latest_error}\n\n"
                        f"Press Alt+{hk_cap} to capture screen again.",
                        title="Processing Notice",
                        provider=prov
                    )
                else:
                    hk_cap = self.settings_manager.get('hotkey_capture', 'z').upper() if self.settings_manager else 'Z'
                    self.popup_manager.show(
                        f"📸 No quiz questions recorded yet.\n\nPress Alt+{hk_cap} to capture and analyze a question.",
                        title="No Questions"
                    )
                return

            # Determine target index:
            # If there are questions beyond _last_viewed_history_index, show the FIRST unviewed question (_last_viewed_history_index + 1)
            if self._last_viewed_history_index < len(self._answer_history) - 1:
                target_idx = self._last_viewed_history_index + 1
            else:
                q_size = self._capture_queue.qsize()
                if self._is_queue_processing or q_size > 0:
                    target_idx = len(self._answer_history)
                else:
                    target_idx = len(self._answer_history) - 1

            self._show_question_at_index(target_idx)

        except Exception as e:
            self.logger.error(f"Error in Alt+C handler: {e}", exc_info=True)
            self.popup_manager.show(f"❌ Error: {str(e)}")

    def on_show_detailed_history_hotkey(self, toggle: bool = True):
        """
        Handle Alt+H hotkey - Show complete question & answer history (strictly 1 to x)
        AND include any pending queue items!
        """
        self.logger.info("Show detailed history hotkey triggered (Alt+H)")

        try:
            if toggle and self.popup_manager.is_visible() and getattr(self, '_is_showing_history', False):
                self.popup_manager.hide()
                self._is_showing_history = False
                self.logger.info("History popup hidden by Alt+H")
                return

            self._is_showing_history = True

            q_size = self._capture_queue.qsize()
            is_processing = self._is_queue_processing
            total_pending = q_size + (1 if is_processing else 0)

            if not self._answer_history and total_pending == 0:
                self.popup_manager.show(
                    "📖 No quiz questions recorded yet.\n\nPress hotkey to capture and analyze questions.",
                    title="History Empty"
                )
                return

            # Combine finished history + pending queue items
            full_list = []
            for item in self._answer_history:
                full_list.append(dict(item))

            start_pending = len(full_list) + 1

            if is_processing:
                full_list.append({
                    "number": str(start_pending),
                    "question": "Captured screenshot in progress",
                    "answer": "⏳ Analyzing... (AI processing in background)",
                    "explanation": "",
                    "is_pending": True
                })
                start_pending += 1

            for i in range(q_size):
                full_list.append({
                    "number": str(start_pending + i),
                    "question": f"Screenshot #{i+1} in queue",
                    "answer": f"⏳ Waiting for processing ({i+1}/{q_size})...",
                    "explanation": "",
                    "is_pending": True
                })

            prov = self.config_manager.get('API_PROVIDER', 'gemini').title()
            title = f"History (1 - {len(self._answer_history)})"
            if total_pending > 0:
                title += f" + {total_pending} pending"

            self.popup_manager.show_questions(
                full_list,
                title=title,
                provider=prov,
                mode="History",
                is_history=True
            )
            self.logger.info(f"Displayed history 1..{len(full_list)} (including {total_pending} pending) via Alt+H")

        except Exception as e:
            self.logger.error(f"Error in Alt+H handler: {e}", exc_info=True)
            self.popup_manager.show(f"❌ Error: {str(e)}")

    def on_reset_answers_hotkey(self):
        """Reset answer history and deduplication cache (Alt+R) - COMPLETELY SILENT (NO POPUP)"""
        count = len(self._answer_history)
        self._answer_history.clear()
        self._latest_result = None
        self._latest_error = None
        self._image_cache.clear()
        self._current_view_index = -1
        self._last_viewed_history_index = -1
        self._is_showing_history = False

        for fpath in [self._answer_file, self._answer_txt_file]:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

        # Hide any open popup silently
        if self.popup_manager.is_visible():
            self.popup_manager.hide()

        self.logger.info(f"Answer history and image cache cleared ({count} entries), counter reset to 1 (silent)")

    def on_clear_all_data(self) -> Tuple[int, int]:
        """
        Completely clear in-memory history, deduplication cache, active popups,
        and delete all logs, answers, and screenshots from disk.
        Returns: (deleted_logs_count, deleted_screenshots_count)
        """
        import glob
        # 1. Clear in-memory history & caches
        count = len(self._answer_history)
        self._answer_history.clear()
        self._latest_result = None
        self._latest_error = None
        self._image_cache.clear()
        self._current_view_index = -1
        self._last_viewed_history_index = -1
        self._is_showing_history = False

        # 2. Immediately close and hide any open popup window
        if hasattr(self, 'popup_manager') and self.popup_manager:
            try:
                self.popup_manager.hide()
            except Exception:
                pass

        # 3. Clean files from disk
        del_logs = 0
        del_screens = 0
        for f in glob.glob(os.path.join(self.project_root, "logs", "*.log*")):
            try:
                os.remove(f)
                del_logs += 1
            except Exception:
                pass

        for fname in ["answers.json", "answers.txt"]:
            f = os.path.join(self.project_root, "logs", fname)
            if os.path.exists(f):
                try:
                    os.remove(f)
                    del_logs += 1
                except Exception:
                    pass

        for f in glob.glob(os.path.join(self.project_root, "logs", "screenshots", "*.png")):
            try:
                os.remove(f)
                del_screens += 1
            except Exception:
                pass

        self.logger.info(
            f"All application data cleared: {count} in-memory questions reset, "
            f"{del_logs} log/answer files deleted, {del_screens} screenshots deleted. Popup closed."
        )
        return del_logs, del_screens

    def on_clear_logs_hotkey(self):
        """Clear all session data and log files"""
        self.on_clear_all_data()

    def on_setup_hotkey(self):
        """Show Settings Dialog (Alt+S) safely in separate thread with singleton protection"""
        if self._settings_open:
            self.logger.info("Settings dialog is already open, ignoring duplicate trigger")
            return

        self._settings_open = True

        def run_dialog():
            def on_api_change():
                self.logger.info("Provider settings modified, hot-reloading AI client...")
                self._initialize_ai_client()
                if hasattr(self, 'system_tray') and self.system_tray.icon:
                    self.system_tray.icon.menu = self.system_tray.create_menu()

            def on_settings_change():
                self.logger.info("UI settings modified, reloading...")
                self.settings_manager.load_settings()
                if self.popup_manager:
                    self.popup_manager.settings = self.settings_manager.settings

            def on_mode_change(new_mode):
                self.logger.info(f"Question mode switched to: {new_mode}")
                if self.ai_client:
                    self.ai_client.set_mode(new_mode)
                    ans_disp = self.settings_manager.get('answer_display_mode', 'letter_and_text')
                    self.ai_client.set_answer_display_mode(ans_disp)
                if self.popup_manager:
                    prov = "Gemini" if self.config_manager.get('API_PROVIDER') == 'gemini' else "Custom"
                    self.popup_manager.set_provider_info(prov, new_mode)

            def on_hotkey_change():
                self.logger.info("Hotkeys modified, reloading listener...")
                if self.hotkey_listener:
                    self.hotkey_listener.reload_hotkeys()

            def on_close():
                self._settings_open = False

            try:
                show_settings_dialog(
                    self.settings_manager,
                    on_api_change=on_api_change,
                    on_settings_change=on_settings_change,
                    on_mode_change=on_mode_change,
                    on_hotkey_change=on_hotkey_change,
                    on_close=on_close,
                    on_clear_data=self.on_clear_all_data
                )
            finally:
                self._settings_open = False

        thread = threading.Thread(target=run_dialog, daemon=True, name="SettingsDialogThread")
        thread.start()

    def _save_answers_to_file(self):
        """Persist answer history to disk (JSON & compact TXT)"""
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self._answer_file, 'w', encoding='utf-8') as f:
                json.dump(self._answer_history, f, ensure_ascii=False, indent=2)

            compact_items = []
            for ans in self._answer_history:
                if isinstance(ans, dict):
                    compact_items.append(f"{ans['number']}{ans['answer']}")
                else:
                    compact_items.append(str(ans))
            with open(self._answer_txt_file, 'w', encoding='utf-8') as f:
                f.write(" ".join(compact_items))

        except Exception as e:
            self.logger.error(f"Error saving answers to file: {e}")

    def _load_answers_from_file(self):
        """Restore answer history from file on startup with strict validation against corrupted data"""
        if os.path.exists(self._answer_file):
            try:
                with open(self._answer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        valid_items = []
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            ans = str(item.get('answer', '')).strip()
                            q = str(item.get('question', '')).strip()

                            # Discard corrupt punctuation tokens and malformed answers
                            if ans in ['[', '{', '}', ']', ':', ',', '"', "'", '']:
                                continue
                            if not ans and not q:
                                continue

                            valid_items.append(item)

                        # Enforce strictly sequential numbering 1..N
                        for idx, item in enumerate(valid_items):
                            item['number'] = str(idx + 1)

                        self._answer_history = valid_items
                        self.logger.info(f"Loaded {len(self._answer_history)} valid answers from {self._answer_file}")
                        return
            except Exception as e:
                self.logger.warning(f"Error loading {self._answer_file}: {e}")

        if os.path.exists(self._answer_txt_file):
            try:
                with open(self._answer_txt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        valid_items = []
                        for token in content.split():
                            # Only accept valid quiz tokens like '1A', '2B', etc.
                            m = re.match(r'^(\d+)([A-Ea-e])$', token)
                            if m:
                                valid_items.append({
                                    "number": str(len(valid_items) + 1),
                                    "question": "",
                                    "answer": m.group(2).upper(),
                                    "timestamp": time.time()
                                })
                        self._answer_history = valid_items
                        self.logger.info(f"Loaded {len(self._answer_history)} valid answers from {self._answer_txt_file}")
            except Exception as e:
                self.logger.warning(f"Error loading {self._answer_txt_file}: {e}")

    def on_exit_hotkey(self):
        """Handle Exit hotkey (`)"""
        self.logger.info("Exit hotkey triggered, stopping app...")
        self.stop()

    def stop(self):
        """Stop all background services and exit cleanly"""
        if not self._running:
            return
        self._running = False
        self.logger.info("Stopping AI Quiz Assistant...")

        try:
            if hasattr(self, 'autofill_manager') and self.autofill_manager:
                self.autofill_manager.abort()
            if hasattr(self, 'settings_manager') and self.settings_manager:
                self.settings_manager.save_settings()
            if hasattr(self, '_capture_queue'):
                self._capture_queue.put(None)
            if self.popup_manager:
                self.popup_manager.close()
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=False)
            if self.system_tray:
                self.system_tray.stop()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            self.logger.info("AI Quiz Assistant shutdown complete")
            sys.exit(0)


def main():
    """Application entrypoint"""
    try:
        app = QuizAssistantApp()
        app.start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
