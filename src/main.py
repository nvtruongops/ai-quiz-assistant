"""
Main Application Module
Entry point for AI Quiz Assistant application
"""

import sys
import threading
import time
import os
import json
import hashlib
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future

# Try different import paths for development vs bundled exe
try:
    from config_manager import ConfigManager
    from logger import Logger
    from screenshot_manager import ScreenshotManager
    from gemini_client import GeminiAPIClient, NoQuestionsFoundError
    from request_manager import RequestManager
    from popup_manager import PopupManager
    from hotkey_listener import HotkeyListener
    from system_tray import SystemTray
    from models import QuizResult
    from settings_manager import SettingsManager, show_api_key_dialog, show_settings_dialog
except ImportError:
    # Fallback for bundled exe where modules are at root level
    from src.config_manager import ConfigManager
    from src.logger import Logger
    from src.screenshot_manager import ScreenshotManager
    from src.gemini_client import GeminiAPIClient, NoQuestionsFoundError
    from src.request_manager import RequestManager
    from src.popup_manager import PopupManager
    from src.hotkey_listener import HotkeyListener
    from src.system_tray import SystemTray
    from src.models import QuizResult
    from src.settings_manager import SettingsManager, show_api_key_dialog, show_settings_dialog


class QuizAssistantApp:
    """Main application class for AI Quiz Assistant"""
    
    def __init__(self):
        """
        Initialize all application components
        """
        # Initialize logger first
        self.logger = Logger()
        self.logger.info("Initializing AI Quiz Assistant...")
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Initialize config manager
        try:
            self.config_manager = ConfigManager()
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}", exc_info=True)
            raise
        
        # Check and prompt for API key if not configured
        if not self._check_api_key():
            self.logger.info("API key not found, showing setup dialog...")
            api_key = show_api_key_dialog()
            if api_key:
                self._save_api_key(api_key)
            else:
                self.logger.error("No API key provided, exiting...")
                sys.exit(1)
        
        # Initialize other components
        self.request_manager = RequestManager()
        self.screenshot_manager = ScreenshotManager(logger=self.logger)
        
        # Initialize Gemini AI client
        self._initialize_ai_client()
        
        # Initialize UI components
        self.popup_manager = PopupManager(config_manager=self.config_manager, 
                                          settings_manager=self.settings_manager)
        
        # Initialize hotkey listener with callbacks
        self.hotkey_listener = HotkeyListener(
            on_capture_key=self.on_capture_hotkey,
            on_check_key=self.on_check_hotkey,
            on_hide_key=self.on_hide_hotkey,
            on_exit_key=self.on_exit_hotkey,
            on_clear_logs=self.on_clear_logs_hotkey,
            on_show_answers=self.on_show_answers_hotkey,
            on_reset_answers=self.on_reset_answers_hotkey,
            on_setup=self.on_setup_hotkey
        )
        
        # Initialize system tray
        self.system_tray = SystemTray(app=self)
        
        # Thread pool executor for async processing
        self._thread_pool = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="APIWorker"
        )
        
        # Dictionary to track active future tasks
        self._active_futures: Dict[str, Future] = {}
        
        # Running flag
        self._running = False
        
        # Debounce flag to avoid multiple captures
        self._last_capture_time = 0
        self._capture_cooldown = 2.0
        
        # Answer history
        self._answer_history = []
        self._answer_file = os.path.join("logs", "answers.txt")
        self._load_answers_from_file()
        
        self.logger.info("All components initialized successfully")
    
    def _check_api_key(self) -> bool:
        """Check if API key is configured"""
        api_key = os.getenv('GEMINI_API_KEY', '')
        return bool(api_key and api_key.strip() and api_key != 'YOUR_GEMINI_API_KEY_HERE')
    
    def _save_api_key(self, api_key: str) -> None:
        """Save API key to config and environment"""
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        
        config = {}
        if os.path.exists("config.json"):
            with open("config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        config['gemini_api_key_hash'] = hashed_key
        
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        os.environ['GEMINI_API_KEY'] = api_key
        self.logger.info("API key saved successfully")
    
    def _initialize_ai_client(self):
        """Initialize Gemini AI client"""
        try:
            api_key = os.getenv('GEMINI_API_KEY', '')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            self.ai_client = GeminiAPIClient(api_key=api_key, logger=self.logger)
            self.logger.info("Gemini API client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI client: {str(e)}", exc_info=True)
            raise
    
    def start(self):
        """
        Start the application
        Start logger, config, system tray, hotkey listener
        """
        if self._running:
            self.logger.warning("Application is already running")
            return
        
        self._running = True
        self.logger.info("Starting AI Quiz Assistant...")
        
        try:
            # Start system tray (in separate thread)
            self.logger.info("Starting system tray...")
            self.system_tray.start()
            
            # Start hotkey listener
            self.logger.info("Starting hotkey listener...")
            self.hotkey_listener.start()
            
            self.logger.info("AI Quiz Assistant started successfully")
            self.logger.info("Hotkeys:")
            self.logger.info("  Alt+Z or MIDDLE + Scroll UP : Capture screen and send analysis")
            self.logger.info("  Alt+X : Show/Hide detailed results")
            self.logger.info("  Alt+C or MIDDLE + Scroll DOWN : Show all saved answers")
            self.logger.info("  Alt+R : Reset answer history")
            self.logger.info("  Alt+S : Setup Menu (configure Gemini API)")
            self.logger.info("  Delete : Clear all log files and answers")
            self.logger.info("  ` (backtick) : Exit program")
            
            # Show notification
            self.system_tray.show_notification(
                "AI Quiz Assistant",
                "Application started. Hold middle mouse button + scroll up to capture screen."
            )
            
            # Keep main thread alive
            while self._running:
                time.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error starting application: {str(e)}", exc_info=True)
            self.stop()
            raise
    
    def on_capture_hotkey(self):
        """
        Handle Alt+Z hotkey - Capture screen and send API async
        DO NOT SHOW NOTIFICATION - Process silently in background
        """
        # Debounce: Block if capture too fast
        current_time = time.time()
        if current_time - self._last_capture_time < self._capture_cooldown:
            self.logger.info(f"Capture ignored (cooldown: {self._capture_cooldown}s)")
            return
        
        self._last_capture_time = current_time
        self.logger.info("Capture hotkey triggered")
        
        # Close previous popup if showing
        if self.popup_manager.is_visible():
            self.popup_manager.hide()
            self.logger.info("Closed previous popup before new capture")
        
        try:
            # Capture screen (DO NOT show notification)
            screenshot = self.screenshot_manager.capture_screen()
            
            if screenshot is None:
                self.logger.error("Failed to capture screenshot")
                return
            
            # Convert to bytes
            image_bytes = self.screenshot_manager.save_to_memory(screenshot)
            
            if image_bytes is None:
                self.logger.error("Failed to save screenshot to memory")
                return
            
            # Create new request
            request_id = self.request_manager.create_request()
            self.logger.info(f"Created new request: {request_id}")
            
            # Submit task to thread pool to not block UI
            future = self._thread_pool.submit(
                self._process_screenshot_async,
                image_bytes,
                request_id
            )
            
            # Save future to track
            self._active_futures[request_id] = future
            
            # Add callback to handle exception from thread
            future.add_done_callback(
                lambda f: self._handle_thread_completion(f, request_id)
            )
            
            self.logger.info(f"Screenshot captured and submitted for async processing: {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error in capture hotkey handler: {str(e)}", exc_info=True)
            try:
                self.request_manager.set_error(f"Screenshot capture error: {str(e)}")
            except:
                pass
    
    def _process_screenshot_async(self, image_bytes: bytes, request_id: str):
        """
        Process screenshot in separate thread
        Send to Gemini API and update results through callback
        
        Args:
            image_bytes: Screenshot in bytes
            request_id: ID of request being processed
        """
        try:
            self.logger.info(f"Processing screenshot in background thread for request: {request_id}")
            
            # Send to AI API (Gemini or Bedrock)
            result = self.ai_client.analyze_quiz(image_bytes)
            
            # Callback: Update successful result
            self._on_api_success(result, request_id)
            
        except NoQuestionsFoundError as e:
            # Callback: No questions found - not a serious error
            self.logger.info(f"No questions found for request {request_id}: {str(e)}")
            self._on_api_error("No questions found in image", request_id, is_no_question=True)
            
        except TimeoutError as e:
            # Callback: Handle timeout error
            self.logger.error(f"API timeout for request {request_id}: {str(e)}")
            self._on_api_error("Timeout: API not responding", request_id)
            
        except ValueError as e:
            # Callback: Handle parsing error
            error_str = str(e)
            self.logger.error(f"Parse error for request {request_id}: {error_str}")
            self._on_api_error(f"Data analysis error: {error_str}", request_id)
            
        except Exception as e:
            # Callback: Handle other errors
            self.logger.error(f"Error processing screenshot for request {request_id}: {str(e)}", exc_info=True)
            self._on_api_error(f"Processing error: {str(e)}", request_id)
    
    def _on_api_success(self, result: 'QuizResult', request_id: str):
        """
        Callback called when API returns successful result
        
        Args:
            result: QuizResult object containing questions and answers
            request_id: Request ID
        """
        try:
            # Update result to request manager
            self.request_manager.set_result(result)
            
            # Save answers to history AND FILE (with sequential number)
            for q in result.questions:
                # Skip questions without answers
                if not q.answer or q.answer.strip() == '':
                    self.logger.warning(f"Skipping question {q.number} - no answer provided")
                    continue
                
                # Format: "13A", "14B", "15C"
                answer_with_number = f"{q.number}{q.answer}"
                self._answer_history.append(answer_with_number)
            
            # Save to file
            self._save_answers_to_file()
            
            # DO NOT show notification - let user press Alt+X or Alt+C
            
            self.logger.info(
                f"Successfully analyzed {len(result.questions)} questions "
                f"for request {request_id}"
            )
            
        except Exception as e:
            self.logger.error(
                f"Error in success callback for request {request_id}: {str(e)}", 
                exc_info=True
            )
    
    def _on_api_error(self, error_message: str, request_id: str, is_no_question: bool = False):
        """
        Callback called when an error occurs during API processing
        
        Args:
            error_message: Error message
            request_id: Request ID
            is_no_question: True if error is due to no questions found (not serious error)
        """
        try:
            # Update error to request manager
            self.request_manager.set_error(error_message)
            
            # Log with different level depending on error type
            if is_no_question:
                self.logger.info(f"No questions found for request {request_id}: {error_message}")
            else:
                self.logger.error(f"API error for request {request_id}: {error_message}")
            
        except Exception as e:
            self.logger.error(
                f"Error in error callback for request {request_id}: {str(e)}", 
                exc_info=True
            )
    
    def _handle_thread_completion(self, future: Future, request_id: str):
        """
        Callback called when processing thread completes (success or error)
        Handle uncaught exceptions from thread
        
        Args:
            future: Future object from ThreadPoolExecutor
            request_id: Request ID
        """
        try:
            # Check if thread raised exception
            exception = future.exception()
            
            if exception is not None:
                # Thread raised uncaught exception
                self.logger.error(
                    f"Unhandled exception in thread for request {request_id}: {str(exception)}",
                    exc_info=exception
                )
                
                # Update error status
                self._on_api_error(
                    f"Unknown error: {str(exception)}",
                    request_id
                )
            else:
                # Thread completed successfully
                self.logger.info(f"Thread completed successfully for request {request_id}")
            
            # Cleanup: Remove future from active futures
            if request_id in self._active_futures:
                del self._active_futures[request_id]
                
        except Exception as e:
            self.logger.error(
                f"Error in thread completion handler for request {request_id}: {str(e)}",
                exc_info=True
            )
    
    def on_check_hotkey(self):
        """
        Handle Alt+X hotkey - TOGGLE hide/show popup with detailed results
        Automatically hide other popup (Alt+C) if showing
        """
        self.logger.info("Check hotkey triggered (Alt+X)")
        
        try:
            # If popup showing → Hide
            if self.popup_manager.is_visible():
                self.popup_manager.hide()
                self.logger.info("Popup hidden")
                return
            
            # If popup hidden → Show with content
            status_info = self.request_manager.get_current_status()
            status = status_info['status']
            
            self.logger.info(f"Current status: {status}")
            
            if status == "NONE":
                self.popup_manager.show("📸 No data yet\nPress Alt+Z to capture screen")
                
            elif status == "PROCESSING":
                elapsed_time = status_info.get('elapsed_time', 0)
                self.popup_manager.show(f"⏳ Processing... ({elapsed_time:.1f}s)\nPlease wait...")
                
            elif status == "COMPLETED":
                result = status_info['result']
                if result:
                    formatted_result = result.format_display()
                    self.popup_manager.show(formatted_result)
                else:
                    self.popup_manager.show("❌ No results")
                    
            elif status == "ERROR":
                error_message = status_info.get('error', 'Unknown error')
                
                if "No questions found" in error_message:
                    self.popup_manager.show("❌ No questions found in image\nTry capturing again with Alt+Z")
                else:
                    self.popup_manager.show(f"❌ Error: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error in check hotkey handler: {str(e)}", exc_info=True)
            self.popup_manager.show(f"❌ Error: {str(e)}")
    
    def on_hide_hotkey(self):
        """
        Handle "F11" hotkey - Hide popup
        """
        self.logger.info("Hide hotkey triggered")
        
        try:
            if self.popup_manager.is_visible():
                self.popup_manager.hide()
                self.logger.info("Popup hidden")
            else:
                self.logger.info("Popup is not visible")
                
        except Exception as e:
            self.logger.error(f"Error in hide hotkey handler: {str(e)}", exc_info=True)
    
    def on_clear_logs_hotkey(self):
        """
        Handle "Delete" hotkey - Clear all log files AND ANSWER FILE
        """
        try:
            self.logger.info("Clear logs and answers hotkey triggered")
            
            import glob
            import os
            
            # Close all handlers to free files
            if self.logger.logger:
                for handler in self.logger.logger.handlers[:]:
                    handler.close()
                    self.logger.logger.removeHandler(handler)
            
            # Delete log files
            log_files = glob.glob("logs/*.log*")
            deleted_logs = 0
            for log_file in log_files:
                try:
                    os.remove(log_file)
                    deleted_logs += 1
                except Exception as e:
                    print(f"Failed to delete {log_file}: {e}")
            
            # Delete answer file
            deleted_answers = False
            if os.path.exists(self._answer_file):
                try:
                    os.remove(self._answer_file)
                    deleted_answers = True
                    self._answer_history.clear()
                except Exception as e:
                    print(f"Failed to delete {self._answer_file}: {e}")
            
            # Recreate logger with new file
            self.logger.setup_logger(self.logger.log_file)
            
            message = f"🗑️ Cleared:\n"
            if deleted_logs > 0:
                message += f"- {deleted_logs} log file(s)\n"
            if deleted_answers:
                message += f"- Answer file"
            else:
                message += "- No answer file"
            
            print(message)
            self.logger.info(f"Cleared: {deleted_logs} logs, answers: {deleted_answers}")
            self.popup_manager.show(message)
            
        except Exception as e:
            error_msg = f"Error clearing logs: {str(e)}"
            print(error_msg)
            try:
                self.logger.setup_logger(self.logger.log_file)
            except:
                pass
            if self.popup_manager:
                self.popup_manager.show(f"❌ Error: {str(e)}")
    
    def on_show_answers_hotkey(self):
        """
        Handle Alt+C hotkey - TOGGLE hide/show all saved answers
        """
        self.logger.info("Show answers hotkey triggered (Alt+C)")
        
        try:
            if self.popup_manager.is_visible():
                self.popup_manager.hide()
                self.logger.info("Answers popup hidden")
                return
            
            if not self._answer_history:
                self.popup_manager.show("No answers saved yet\nPress Alt+Z to capture questions")
                return
            
            # Get answers per line from settings
            answers_per_line = self.settings_manager.get('answers_per_line', 10)
            lines = []
            for i in range(0, len(self._answer_history), answers_per_line):
                chunk = self._answer_history[i:i+answers_per_line]
                lines.append(" ".join(chunk))
            
            answers_text = "\n".join(lines)
            self.popup_manager.show(answers_text)
            self.logger.info(f"Showed {len(self._answer_history)} answers")
            
        except Exception as e:
            self.logger.error(f"Error in show answers hotkey: {str(e)}", exc_info=True)
            self.popup_manager.show(f"Error: {str(e)}")
    
    def on_reset_answers_hotkey(self):
        """
        Handle Alt+R hotkey - Reset answer history
        """
        self.logger.info("Reset answers hotkey triggered (Alt+R)")
        
        try:
            import os
            
            # Delete answer file
            if os.path.exists(self._answer_file):
                os.remove(self._answer_file)
            
            # Clear history in memory
            count = len(self._answer_history)
            self._answer_history.clear()
            
            message = f"🗑️ Cleared {count} answers"
            self.popup_manager.show(message)
            self.logger.info(f"Reset {count} answers")
            
        except Exception as e:
            self.logger.error(f"Error resetting answers: {str(e)}", exc_info=True)
            self.popup_manager.show(f"❌ Error: {str(e)}")
    
    def on_setup_hotkey(self):
        """
        Handle Alt+S hotkey - Show Settings Dialog
        """
        self.logger.info("Settings hotkey triggered (Alt+S)")
        
        try:
            def on_api_change():
                self._initialize_ai_client()
                self.logger.info("AI client re-initialized after API change")
            
            def on_settings_change():
                self.logger.info("Settings changed, reloading...")
                self.settings_manager.load_settings()
            
            show_settings_dialog(
                self.settings_manager,
                on_api_change=on_api_change,
                on_settings_change=on_settings_change
            )
            
        except Exception as e:
            self.logger.error(f"Error showing settings dialog: {str(e)}", exc_info=True)
            self.popup_manager.show(f"Error: {str(e)}")
    
    def _save_answers_to_file(self):
        """
        Save all answers to answers.txt file
        Format: A B D AE C... (each answer separated by space)
        """
        try:
            # Create logs directory if not exists
            os.makedirs(os.path.dirname(self._answer_file), exist_ok=True)
            
            with open(self._answer_file, 'w', encoding='utf-8') as f:
                f.write(" ".join(self._answer_history))
            self.logger.info(f"Saved {len(self._answer_history)} answers to {self._answer_file}")
        except Exception as e:
            self.logger.error(f"Error saving answers to file: {str(e)}", exc_info=True)
    
    def _load_answers_from_file(self):
        """
        Load answers from answers.txt file on startup
        Format: A B D AE C... (each answer separated by space)
        """
        try:
            import os
            if os.path.exists(self._answer_file):
                with open(self._answer_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self._answer_history = content.split()
                        self.logger.info(f"Loaded {len(self._answer_history)} answers from {self._answer_file}")
                    else:
                        self.logger.info("Answer file is empty")
            else:
                self.logger.info("No answer file found")
        except Exception as e:
            self.logger.error(f"Error loading answers from file: {str(e)}", exc_info=True)
    
    def on_exit_hotkey(self):
        """
        Handle "F12" hotkey - Exit program
        """
        self.logger.info("Exit hotkey triggered")
        self.stop()
    
    def stop(self):
        """
        Stop all components and cleanup
        """
        if not self._running:
            return
        
        self.logger.info("Stopping AI Quiz Assistant...")
        self._running = False
        
        try:
            # Close popup if showing
            if self.popup_manager and self.popup_manager.is_visible():
                self.popup_manager.close()
                self.logger.info("Popup closed")
            
            # Stop hotkey listener
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                self.logger.info("Hotkey listener stopped")
            
            # Shutdown thread pool and wait for threads to complete
            if hasattr(self, '_thread_pool'):
                self.logger.info("Shutting down thread pool...")
                
                # Don't accept new tasks
                self._thread_pool.shutdown(wait=False)
                
                # Wait maximum 5 seconds for running threads
                # Then force shutdown
                try:
                    # Cancel pending futures
                    for request_id, future in list(self._active_futures.items()):
                        if not future.done():
                            future.cancel()
                            self.logger.info(f"Cancelled pending request: {request_id}")
                    
                    self.logger.info("Thread pool shutdown completed")
                except Exception as e:
                    self.logger.error(f"Error shutting down thread pool: {str(e)}")
            
            # Stop system tray
            if self.system_tray:
                self.system_tray.stop()
                self.logger.info("System tray stopped")
            
            self.logger.info("AI Quiz Assistant stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping application: {str(e)}", exc_info=True)
        
        finally:
            # Exit application
            sys.exit(0)


def main():
    """
    Application entry point
    """
    try:
        # Create and start application
        app = QuizAssistantApp()
        app.start()
        
    except ValueError as e:
        # Configuration error (missing API key)
        print(f"Configuration error: {str(e)}")
        print("Please check .env file and add GEMINI_API_KEY")
        sys.exit(1)
        
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\nExiting...")
        sys.exit(0)
        
    except Exception as e:
        # Unknown error
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
