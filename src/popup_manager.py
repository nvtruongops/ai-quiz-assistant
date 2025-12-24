"""
Popup Manager Module
Manages popup window to display question results
"""

import tkinter as tk
import threading
import queue

from typing import Optional, Tuple
from pynput.mouse import Controller as MouseController


class PopupManager:
    """Manages popup window to display question analysis results"""
    
    def __init__(self, config_manager):
        """
        Initialize PopupManager
        
        Args:
            config_manager: ConfigManager instance to get configuration
        """
        self.config = config_manager
        self.current_popup = None
        self.mouse_controller = MouseController()
        self._is_visible = False
        self._current_content = ""
        
        # Queue to send commands from other threads to Tkinter thread
        self.command_queue = queue.Queue()
        
        # Create root window and run in separate thread
        self.root = None
        self.tk_ready = threading.Event()
        self.tk_thread = threading.Thread(target=self._run_tkinter, daemon=True)
        self.tk_thread.start()
        
        # Wait for Tkinter to be ready
        self.tk_ready.wait()
    
    def _run_tkinter(self):
        """Run Tkinter mainloop in separate thread"""
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.attributes('-alpha', 0)
        self.root.geometry('1x1+0+0')
        
        # Mark Tkinter as ready
        self.tk_ready.set()
        
        # Check command queue every 100ms
        self._process_commands()
        
        # Run mainloop
        self.root.mainloop()
    
    def _process_commands(self):
        """Process commands from queue"""
        try:
            while not self.command_queue.empty():
                command, args = self.command_queue.get_nowait()
                if command == "show":
                    self._create_popup_internal(args[0])
                elif command == "hide":
                    self._hide_internal()
        except queue.Empty:
            pass
        finally:
            # Schedule again after 100ms
            if self.root:
                self.root.after(100, self._process_commands)
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """
        Get current mouse cursor position
        
        Returns:
            Tuple (x, y) of cursor position
        """
        position = self.mouse_controller.position
        return (int(position[0]), int(position[1]))
    
    def calculate_position(self, cursor_pos: Tuple[int, int], window_size: Tuple[int, int]) -> Tuple[int, int]:
        """
        Calculate popup position (5px below-right of cursor - CLOSER)
        Adjust if popup goes outside screen
        
        Args:
            cursor_pos: Mouse cursor position (x, y)
            window_size: Popup size (width, height)
            
        Returns:
            Tuple (x, y) of adjusted popup position
        """
        # Default position: 5px below-right of cursor - CLOSER
        x = cursor_pos[0] + 5
        y = cursor_pos[1] + 5
        
        # Get screen size - use screeninfo or default values
        try:
            from screeninfo import get_monitors
            monitor = get_monitors()[0]
            screen_width = monitor.width
            screen_height = monitor.height
        except:
            # Fallback: use default Full HD size
            screen_width = 1920
            screen_height = 1080
        
        window_width, window_height = window_size
        
        # Adjust if goes beyond right edge of screen
        if x + window_width > screen_width:
            x = screen_width - window_width - 10
        
        # Adjust if goes beyond bottom edge of screen
        if y + window_height > screen_height:
            y = screen_height - window_height - 10
        
        # Ensure not negative
        x = max(10, x)
        y = max(10, y)
        
        return (x, y)

    def show(self, content: str):
        """
        Display popup with content (status or result)
        CLEAR queue first to avoid old commands being processed
        
        Args:
            content: Display content (status message or formatted result)
        """
        self._current_content = content
        
        # CLEAR queue to avoid old commands
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except:
                break
        
        # Send show command to queue for Tkinter thread to process
        self.command_queue.put(("show", (content,)))
    
    def _create_popup_internal(self, content: str):
        """
        Create new popup window (runs in Tkinter thread)
        ALWAYS DESTROY old popup before creating new one to avoid toggle errors
        
        Args:
            content: Content to display
        """
        # ALWAYS destroy old popup before creating new one
        if self.current_popup:
            try:
                self.current_popup.destroy()
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.current_popup = None
                self._is_visible = False
        
        # Get mouse position RIGHT from the beginning
        cursor_pos = self.get_cursor_position()
        
        # Create toplevel window from root
        popup = tk.Toplevel(self.root)
        
        # Remove title bar and decorations
        popup.overrideredirect(True)
        
        # Configure window with transparent/blur background - modern UI
        popup.attributes('-topmost', True)  # Always on top
        popup.attributes('-alpha', 1.0)  # Transparency (94% opacity)
        popup.resizable(False, False)
        
        # Set temporary position near cursor to avoid flicker
        popup.geometry(f"+{cursor_pos[0]+5}+{cursor_pos[1]+5}")
        
        # NO BORDER - ONLY TEXT
        # White background, no border
        popup.config(bg="white")
        
        # Frame containing text - small padding, compact
        main_frame = tk.Frame(popup, bg="white", padx=6, pady=4)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create text widget - white background, no border, readable font
        text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            bg="white",
            fg="#000000",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            spacing1=0,
            spacing2=0,
            spacing3=1,
            cursor="arrow"
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags - black text, compact
        text_widget.tag_configure("question", 
                                 font=("Segoe UI", 9),
                                 foreground="#000000", 
                                 spacing1=1,
                                 spacing3=0)
        text_widget.tag_configure("answer", 
                                 font=("Segoe UI", 9, "bold"),
                                 foreground="#000000",
                                 spacing3=1)
        text_widget.tag_configure("normal", 
                                 font=("Segoe UI", 9), 
                                 foreground="#000000")
        
        # Insert and format content
        self._insert_formatted_content(text_widget, content)
        
        # Disable editing
        text_widget.config(state=tk.DISABLED)
        
        # Update to get actual size
        popup.update_idletasks()
        
        # AUTO SCALE - Calculate size based on content
        lines = content.split('\n')
        line_count = len(lines)
        
        # Height: minimum 4 lines, maximum 20 lines
        text_height = max(4, min(20, line_count + 1))
        text_widget.config(height=text_height)
        
        # Auto adjust width based on longest line
        max_line_length = max((len(line) for line in lines), default=20)
        # Font size 9: 1 character ≈ 7 pixels
        estimated_width = max(250, min(600, max_line_length * 7 + 40))
        
        # Set popup size
        popup_width = max(280, estimated_width)
        popup_height = max(80, text_height * 18 + 30)
        
        popup.update_idletasks()
        
        # Calculate final position based on cursor position from beginning
        popup_pos = self.calculate_position(cursor_pos, (popup_width, popup_height))
        
        # Set popup position and size FINAL (must be integer)
        popup.geometry(f"{int(popup_width)}x{int(popup_height)}+{int(popup_pos[0])}+{int(popup_pos[1])}")
        
        # Force update to ensure position is applied
        popup.update()
        
        # Save reference
        self.current_popup = popup
        self._is_visible = True
        
        # Bind close event
        popup.protocol("WM_DELETE_WINDOW", self.close)
    
    def _insert_formatted_content(self, text_widget: tk.Text, content: str):
        """
        Insert and format content into text widget
        
        Args:
            text_widget: ScrolledText widget
            content: Content to format
        """
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('Câu ') and ':' in line:
                # Question line - bold
                text_widget.insert(tk.END, line + '\n', "question")
            elif line.startswith('→ Đáp án:'):
                # Answer line - bold and blue
                text_widget.insert(tk.END, line + '\n', "answer")
            else:
                # Normal line
                text_widget.insert(tk.END, line + '\n', "normal")
        
        text_widget.config(state=tk.DISABLED)
    
    def _update_popup_content(self, content: str):
        """
        Update current popup content (without creating new one)
        
        Args:
            content: New content
        """
        if not self.current_popup:
            return
        
        try:
            # Find text widget in popup
            for widget in self.current_popup.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Text):
                            self._insert_formatted_content(child, content)
                            self._is_visible = True
                            return
        except tk.TclError:
            # Popup was destroyed
            self.current_popup = None
            self._is_visible = False
    
    def _update_content(self, content: str):
        """
        Update current popup content (legacy method)
        
        Args:
            content: New content
        """
        self._update_popup_content(content)
    
    def hide(self):
        """
        Hide popup and destroy to have no remaining windows
        CLEAR queue first to avoid old commands being processed
        """
        # CLEAR queue to avoid old commands
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except:
                break
        
        # Send hide command to queue
        self.command_queue.put(("hide", ()))
    
    def _hide_internal(self):
        """Hide popup (runs in Tkinter thread)"""
        if self.current_popup:
            try:
                self.current_popup.destroy()
            except tk.TclError:
                pass
            finally:
                self.current_popup = None
                self._is_visible = False
                self._current_content = ""
    
    def close(self):
        """
        Close popup and release resources
        """
        if self.current_popup:
            try:
                self.current_popup.destroy()
            except tk.TclError:
                pass
            finally:
                self.current_popup = None
                self._is_visible = False
                self._current_content = ""
    
    def is_visible(self) -> bool:
        """
        Check if popup is currently visible
        Check both state and popup object
        
        Returns:
            True if popup is visible, False otherwise
        """
        # Check if popup exists and is alive
        if self.current_popup:
            try:
                # If popup is alive, check winfo_exists
                if self.current_popup.winfo_exists():
                    return self._is_visible
                else:
                    # Popup was destroyed but reference not cleared
                    self.current_popup = None
                    self._is_visible = False
                    return False
            except (tk.TclError, AttributeError):
                # Popup was destroyed
                self.current_popup = None
                self._is_visible = False
                return False
        
        return False
