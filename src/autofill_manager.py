"""
Auto-Fill Manager Module
Executes automated screen recognition, cursor navigation, and answer filling.
Supports multi-question, multi-answer sequential clicking with human-like smooth movement.
"""

import math
import time
import threading
import logging
from typing import Optional, List, Tuple, Callable, Dict, Any
from pynput.mouse import Controller as MouseController, Button

try:
    from models import QuizResult, QuizQuestion
    from logger import Logger
except ImportError:
    from src.models import QuizResult, QuizQuestion
    from src.logger import Logger


class AutoFillManager:
    """Manages automatic detection of answer coordinates and automated mouse clicking"""

    def __init__(
        self,
        logger: Optional[Logger] = None,
        settings_manager=None,
        mouse_controller: Optional[MouseController] = None
    ):
        self.logger = logger
        self.settings_manager = settings_manager
        self.mouse_controller = mouse_controller or MouseController()
        self.is_running = False
        self._abort_requested = False
        self._lock = threading.Lock()

    def abort(self) -> None:
        """Emergency abort current auto-fill operation"""
        self._abort_requested = True
        if self.logger:
            self.logger.warning("AutoFill abort requested by user")

    def is_enabled(self) -> bool:
        """Check if auto-fill feature is enabled in settings"""
        if self.settings_manager:
            return bool(self.settings_manager.get('enable_autofill', True))
        return True

    def get_click_delay(self) -> float:
        """Get delay between consecutive answer clicks in seconds"""
        if self.settings_manager:
            ms = self.settings_manager.get('autofill_click_delay_ms', 200)
            try:
                return max(0.05, min(2.0, float(ms) / 1000.0))
            except Exception:
                return 0.2
        return 0.2

    def should_restore_cursor(self) -> bool:
        """Check if cursor should be returned to starting position after filling"""
        if self.settings_manager:
            return bool(self.settings_manager.get('autofill_restore_cursor', True))
        return True

    def should_use_smooth_movement(self) -> bool:
        """Check if natural mouse interpolation should be used"""
        if self.settings_manager:
            return bool(self.settings_manager.get('autofill_smooth_movement', True))
        return True

    def move_to(self, target_x: int, target_y: int, smooth: bool = True) -> None:
        """
        Move mouse cursor to target coordinates.
        Uses cosine interpolation for natural, human-like motion.
        """
        target_x = int(target_x)
        target_y = int(target_y)

        if not smooth:
            self.mouse_controller.position = (target_x, target_y)
            return

        cur_x, cur_y = self.mouse_controller.position
        dist = math.hypot(target_x - cur_x, target_y - cur_y)

        if dist < 8:
            self.mouse_controller.position = (target_x, target_y)
            return

        steps = max(3, min(14, int(dist / 35)))
        for i in range(1, steps + 1):
            if self._abort_requested:
                break
            t = i / float(steps)
            ease = (1.0 - math.cos(t * math.pi)) / 2.0
            nx = int(cur_x + (target_x - cur_x) * ease)
            ny = int(cur_y + (target_y - cur_y) * ease)
            self.mouse_controller.position = (nx, ny)
            time.sleep(0.007)

        self.mouse_controller.position = (target_x, target_y)

    def click(self) -> None:
        """Perform a left mouse button click at current cursor position"""
        try:
            self.mouse_controller.press(Button.left)
            time.sleep(0.035)
            self.mouse_controller.release(Button.left)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error executing auto-fill click: {e}")

    def compute_screen_coordinates(
        self,
        point: List[float],
        capture_bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[int, int]:
        """
        Convert normalized AI coordinates [y, x] (0 to 1000) to actual desktop screen pixels.
        
        Args:
            point: [y, x] coordinate from AI model (range 0..1000 or 0.0..1.0)
            capture_bbox: (x, y, width, height) of the captured screen region
            
        Returns:
            (screen_x, screen_y) in desktop coordinates
        """
        y_val, x_val = float(point[0]), float(point[1])

        # Normalize to 0.0 - 1.0 range
        norm_y = y_val / 1000.0 if y_val > 1.0 else y_val
        norm_x = x_val / 1000.0 if x_val > 1.0 else x_val

        # Clamp normalized values
        norm_y = max(0.0, min(1.0, norm_y))
        norm_x = max(0.0, min(1.0, norm_x))

        if capture_bbox and len(capture_bbox) >= 4:
            base_x, base_y, width, height = capture_bbox
        else:
            base_x, base_y = 0, 0
            width, height = 1920, 1080
            try:
                import screeninfo
                primary = next((m for m in screeninfo.get_monitors() if getattr(m, 'is_primary', False)), None)
                if not primary:
                    monitors = screeninfo.get_monitors()
                    primary = monitors[0] if monitors else None
                if primary:
                    base_x, base_y = primary.x, primary.y
                    width, height = primary.width, primary.height
            except Exception:
                pass

        screen_x = int(base_x + norm_x * width)
        screen_y = int(base_y + norm_y * height)
        return screen_x, screen_y

    def fill_answers(
        self,
        quiz_result: QuizResult,
        capture_bbox: Optional[Tuple[int, int, int, int]] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_finished: Optional[Callable[[int, int, List[str]], None]] = None
    ) -> Tuple[int, int]:
        """
        Execute automated clicks for all questions and answers found in QuizResult.
        
        Args:
            quiz_result: QuizResult object containing questions with clicks coordinates
            capture_bbox: (x, y, width, height) of the screen region that was captured
            on_progress: Optional callback(current_index, total_clicks, description)
            on_finished: Optional callback(success_clicks, total_clicks, filled_summary)
            
        Returns:
            (successful_clicks, total_targets)
        """
        with self._lock:
            self.is_running = True
            self._abort_requested = False

        if not self.is_enabled():
            if self.logger:
                self.logger.warning("AutoFill requested but feature is disabled in settings")
            if on_finished:
                on_finished(0, 0, [])
            return 0, 0

        # Collect all click targets across all questions
        all_targets = []
        for q in quiz_result.questions:
            q_clicks = getattr(q, 'clicks', []) or []
            for target in q_clicks:
                pt = target.get('point')
                if pt and len(pt) >= 2:
                    all_targets.append({
                        'q_num': q.number,
                        'option': target.get('option', q.option_letter),
                        'answer_text': q.answer,
                        'point': pt
                    })

        total_targets = len(all_targets)
        if total_targets == 0:
            if self.logger:
                self.logger.info("AutoFill: No clickable coordinates identified in quiz result")
            if on_finished:
                on_finished(0, 0, [])
            with self._lock:
                self.is_running = False
            return 0, 0

        # Record initial mouse position
        orig_x, orig_y = self.mouse_controller.position
        smooth = self.should_use_smooth_movement()
        click_delay = self.get_click_delay()
        success_clicks = 0
        filled_summary = []

        if self.logger:
            self.logger.info(f"AutoFill starting: {total_targets} click targets to execute (delay={click_delay}s, smooth={smooth})")

        try:
            for idx, target in enumerate(all_targets, 1):
                if self._abort_requested:
                    if self.logger:
                        self.logger.warning(f"AutoFill aborted after {success_clicks}/{total_targets} clicks")
                    break

                sx, sy = self.compute_screen_coordinates(target['point'], capture_bbox)
                desc = f"Q{target['q_num']} ({target['option']})"
                
                if self.logger:
                    self.logger.info(f"AutoFill [{idx}/{total_targets}]: Moving to ({sx}, {sy}) for {desc}")

                if on_progress:
                    try:
                        on_progress(idx, total_targets, desc)
                    except Exception:
                        pass

                # Move cursor to option button
                self.move_to(sx, sy, smooth=smooth)
                if self._abort_requested:
                    break

                # Small settle pause before click
                time.sleep(0.04)

                # Click answer choice
                self.click()
                success_clicks += 1
                filled_summary.append(desc)

                # Delay before next question
                if idx < total_targets:
                    time.sleep(click_delay)

            # Restore cursor to original position if configured
            if self.should_restore_cursor() and not self._abort_requested:
                time.sleep(0.08)
                self.move_to(orig_x, orig_y, smooth=smooth)

        except Exception as e:
            if self.logger:
                self.logger.error(f"AutoFill execution error: {e}", exc_info=True)
        finally:
            with self._lock:
                self.is_running = False

            if on_finished:
                try:
                    on_finished(success_clicks, total_targets, filled_summary)
                except Exception:
                    pass

        return success_clicks, total_targets

    def fill_answers_async(
        self,
        quiz_result: QuizResult,
        capture_bbox: Optional[Tuple[int, int, int, int]] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_finished: Optional[Callable[[int, int, List[str]], None]] = None
    ) -> threading.Thread:
        """Execute fill_answers in a background worker thread"""
        th = threading.Thread(
            target=self.fill_answers,
            args=(quiz_result, capture_bbox, on_progress, on_finished),
            daemon=True,
            name="AutoFillWorkerThread"
        )
        th.start()
        return th
