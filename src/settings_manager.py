"""
Settings Manager Module
Manages application settings with GUI
"""

import os
import json
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Dict, Any


class SettingsManager:
    """Manages application settings"""
    
    DEFAULT_SETTINGS = {
        'font_size': 9,
        'popup_width': 400,
        'popup_opacity': 1.0,
        'answers_per_line': 10,
        'question_mode': 'multiple_choice',  # multiple_choice or essay
        # Hotkey settings (lowercase letter for Alt+key combinations)
        'hotkey_capture': 'z',      # Alt+Z - Capture screen
        'hotkey_results': 'x',      # Alt+X - Show/Hide results
        'hotkey_answers': 'c',      # Alt+C - Show answers history
        'hotkey_reset': 'r',        # Alt+R - Reset answers
        'hotkey_settings': 's',     # Alt+S - Open settings
    }
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load settings from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Load all settings from config, use defaults for missing keys
                    for key in self.DEFAULT_SETTINGS:
                        if key in config:
                            self.settings[key] = config[key]
                    # Also load non-default settings (like gemini_api_key)
                    for key in config:
                        if key not in self.settings:
                            self.settings[key] = config[key]
            except Exception:
                pass
    
    def save_settings(self) -> None:
        """Save settings to config file"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Update all settings
            config.update(self.settings)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set setting value"""
        self.settings[key] = value
        self.save_settings()


def show_api_key_dialog(parent: Optional[tk.Tk] = None) -> Optional[str]:
    """
    Show dialog to enter API key
    Returns API key if entered, None if cancelled
    """
    root = tk.Tk()
    root.title("AI Quiz Assistant - Setup Required")
    root.geometry("450x220")
    root.resizable(False, False)
    
    # Center dialog
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 450) // 2
    y = (root.winfo_screenheight() - 220) // 2
    root.geometry(f"+{x}+{y}")
    
    # Bring to front
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    root.focus_force()
    
    result = {'api_key': None}
    
    # Title
    tk.Label(root, text="Gemini API Key Required", 
             font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
    
    tk.Label(root, text="Please enter your Google Gemini API key to continue.",
             font=("Segoe UI", 9)).pack(pady=(0, 10))
    
    # API Key entry
    frame = tk.Frame(root)
    frame.pack(pady=10, padx=20, fill=tk.X)
    
    tk.Label(frame, text="API Key:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    
    api_entry = tk.Entry(frame, show="*", font=("Segoe UI", 10), width=45)
    api_entry.pack(fill=tk.X, pady=(5, 0))
    api_entry.focus()
    
    # Link to get API key
    link_label = tk.Label(root, text="Get API key from Google AI Studio", 
                          font=("Segoe UI", 8), fg="blue", cursor="hand2")
    link_label.pack()
    link_label.bind("<Button-1>", lambda e: os.startfile("https://makersuite.google.com/app/apikey"))
    
    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=15)
    
    def on_save():
        api_key = api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "API key cannot be empty", parent=root)
            return
        if len(api_key) < 20:
            messagebox.showerror("Error", "API key is too short", parent=root)
            return
        result['api_key'] = api_key
        root.destroy()
    
    def on_cancel():
        root.destroy()
    
    tk.Button(btn_frame, text="Save", command=on_save, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Exit", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    # Handle Enter key
    api_entry.bind("<Return>", lambda e: on_save())
    root.bind("<Escape>", lambda e: on_cancel())
    
    # Handle window close
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    
    root.mainloop()
    
    return result['api_key']


def test_api_key(api_key: str) -> tuple[bool, str]:
    """
    Test if API key is valid by making a simple request
    
    Returns:
        (success: bool, message: str)
    """
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # Simple test request
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'OK' if you can read this.",
            config=types.GenerateContentConfig(
                max_output_tokens=10,
            )
        )
        
        if response and response.text:
            return True, "API key is valid and working!"
        else:
            return False, "API returned empty response"
            
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return False, "Invalid API key"
        elif "quota" in error_msg.lower():
            return False, "API quota exceeded"
        elif "permission" in error_msg.lower():
            return False, "API key lacks permission"
        else:
            return False, f"Error: {error_msg[:100]}"


def show_settings_dialog(settings_manager: SettingsManager, 
                         on_api_change: callable = None,
                         on_settings_change: callable = None,
                         on_mode_change: callable = None,
                         on_hotkey_change: callable = None) -> None:
    """
    Show settings dialog with all configuration options
    """
    dialog = tk.Tk()
    dialog.title("AI Quiz Assistant - Settings")
    dialog.geometry("450x450")
    dialog.resizable(False, False)
    
    # Center dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 450) // 2
    y = (dialog.winfo_screenheight() - 450) // 2
    dialog.geometry(f"+{x}+{y}")
    
    # Bring to front - CRITICAL for visibility
    dialog.lift()
    dialog.attributes('-topmost', True)
    dialog.after(100, lambda: dialog.attributes('-topmost', False))
    dialog.focus_force()
    
    # Title
    tk.Label(dialog, text="Settings", 
             font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))
    
    # Notebook for tabs
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # === API Tab ===
    api_frame = ttk.Frame(notebook, padding=10)
    notebook.add(api_frame, text="API")
    
    tk.Label(api_frame, text="Gemini API Key:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    api_entry = tk.Entry(api_frame, show="*", font=("Segoe UI", 10), width=40)
    api_entry.pack(fill=tk.X, pady=(5, 10))
    
    # Check if API key exists
    current_api_key = os.getenv('GEMINI_API_KEY', '')
    has_api = bool(current_api_key)
    if has_api:
        api_entry.insert(0, "********** (configured)")
        api_entry.config(state='disabled')
    
    # Status label for API test
    api_status_label = tk.Label(api_frame, text="", font=("Segoe UI", 8))
    api_status_label.pack(anchor=tk.W)
    
    def change_api():
        api_entry.config(state='normal')
        api_entry.delete(0, tk.END)
        api_entry.focus()
        api_status_label.config(text="", fg="black")
    
    def do_test_api():
        api_status_label.config(text="Testing...", fg="blue")
        dialog.update()
        
        # Get API key to test
        api_key = api_entry.get().strip()
        if api_key.startswith("*"):
            api_key = current_api_key
        
        if not api_key:
            api_status_label.config(text="❌ No API key to test", fg="red")
            return
        
        success, message = test_api_key(api_key)
        if success:
            api_status_label.config(text=f"✅ {message}", fg="green")
        else:
            api_status_label.config(text=f"❌ {message}", fg="red")
    
    btn_row = tk.Frame(api_frame)
    btn_row.pack(anchor=tk.W, pady=(5, 0))
    tk.Button(btn_row, text="Change API Key", command=change_api).pack(side=tk.LEFT, padx=(0, 5))
    tk.Button(btn_row, text="Test API", command=do_test_api).pack(side=tk.LEFT)
    
    # === Question Mode Tab ===
    mode_frame = ttk.Frame(notebook, padding=10)
    notebook.add(mode_frame, text="Question Mode")
    
    tk.Label(mode_frame, text="Select how AI should answer questions:", 
             font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
    # Get current mode value
    current_mode = settings_manager.get('question_mode')
    print(f"DEBUG Question Mode - current_mode: {repr(current_mode)}")
    
    if not current_mode:
        current_mode = 'multiple_choice'
    
    mode_var = tk.StringVar(master=dialog)
    mode_var.set(current_mode)
    print(f"DEBUG After set - mode_var: {repr(mode_var.get())}")
    
    # Multiple Choice option
    mc_frame = ttk.LabelFrame(mode_frame, text="Multiple Choice (A, B, C, D)", padding=10)
    mc_frame.pack(fill=tk.X, pady=5)
    
    ttk.Radiobutton(mc_frame, text="For exams with options A, B, C, D", 
                    variable=mode_var, value="multiple_choice").pack(anchor=tk.W)
    tk.Label(mc_frame, text="Returns: 1A, 2B, 3C...", 
             font=("Segoe UI", 8), fg="gray").pack(anchor=tk.W)
    
    # Essay option
    essay_frame = ttk.LabelFrame(mode_frame, text="Essay / Open-ended", padding=10)
    essay_frame.pack(fill=tk.X, pady=5)
    
    ttk.Radiobutton(essay_frame, text="For questions requiring detailed answers", 
                    variable=mode_var, value="essay").pack(anchor=tk.W)
    tk.Label(essay_frame, text="Returns: Full explanation and solution", 
             font=("Segoe UI", 8), fg="gray").pack(anchor=tk.W)
    
    # === Display Tab ===
    display_frame = ttk.Frame(notebook, padding=10)
    notebook.add(display_frame, text="Display")
    
    # Get current values with debug
    current_font_size = settings_manager.get('font_size')
    current_popup_width = settings_manager.get('popup_width')
    current_apl = settings_manager.get('answers_per_line')
    
    print(f"DEBUG Display - font_size: {current_font_size}, popup_width: {current_popup_width}, apl: {current_apl}")
    
    if not current_font_size or current_font_size == 0:
        current_font_size = 9
    if not current_popup_width or current_popup_width == 0:
        current_popup_width = 400
    if not current_apl or current_apl == 0:
        current_apl = 10
    
    # Font size
    tk.Label(display_frame, text="Font Size:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    font_var = tk.IntVar(master=dialog)
    font_var.set(int(current_font_size))
    font_scale = tk.Scale(display_frame, from_=6, to=14, orient=tk.HORIZONTAL, 
                          variable=font_var, length=200)
    font_scale.pack(anchor=tk.W, pady=(0, 10))
    
    # Popup width
    tk.Label(display_frame, text="Popup Width:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    width_var = tk.IntVar(master=dialog)
    width_var.set(int(current_popup_width))
    width_scale = tk.Scale(display_frame, from_=250, to=600, orient=tk.HORIZONTAL,
                           variable=width_var, length=200)
    width_scale.pack(anchor=tk.W, pady=(0, 10))
    
    # Answers per line
    tk.Label(display_frame, text="Answers per line:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    apl_var = tk.IntVar(master=dialog)
    apl_var.set(int(current_apl))
    apl_scale = tk.Scale(display_frame, from_=5, to=20, orient=tk.HORIZONTAL,
                         variable=apl_var, length=200)
    apl_scale.pack(anchor=tk.W)
    
    print(f"DEBUG After set - font_var: {font_var.get()}, width_var: {width_var.get()}, apl_var: {apl_var.get()}")
    
    # === Hotkeys Tab (Editable) ===
    hotkey_frame = ttk.Frame(notebook, padding=10)
    notebook.add(hotkey_frame, text="Hotkeys")
    
    tk.Label(hotkey_frame, text="Customize hotkeys (Alt + key):", 
             font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
    # Hotkey defaults
    hotkey_defaults = {
        'hotkey_capture': 'z',
        'hotkey_results': 'x',
        'hotkey_answers': 'c',
        'hotkey_reset': 'r',
        'hotkey_settings': 's',
    }
    
    # Store entries for later access
    hotkey_entries = {}
    
    hotkey_labels = [
        ('hotkey_capture', 'Capture Screen:'),
        ('hotkey_results', 'Show/Hide Results:'),
        ('hotkey_answers', 'Show Answers:'),
        ('hotkey_reset', 'Reset Answers:'),
        ('hotkey_settings', 'Open Settings:'),
    ]
    
    for key, label in hotkey_labels:
        row = tk.Frame(hotkey_frame)
        row.pack(fill=tk.X, pady=2)
        
        tk.Label(row, text=label, font=("Segoe UI", 9), width=18, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(row, text="Alt +", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        # Get current value from settings, fallback to default
        current_value = settings_manager.get(key)
        if not current_value:
            current_value = hotkey_defaults[key]
        
        entry = tk.Entry(row, font=("Consolas", 10), width=3, justify=tk.CENTER)
        entry.insert(0, current_value.upper())
        entry.pack(side=tk.LEFT)
        
        hotkey_entries[key] = entry
        
        # Limit to single character and auto uppercase
        def make_handler(ent):
            def on_key_input(event):
                char = event.char.lower()
                if char.isalpha() and len(char) == 1:
                    ent.delete(0, tk.END)
                    ent.insert(0, char.upper())
                return "break"
            return on_key_input
        
        entry.bind("<Key>", make_handler(entry))
    
    # Fixed hotkeys info
    tk.Label(hotkey_frame, text="\nFixed hotkeys (cannot change):", 
             font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
    fixed_info = """Delete          Clear Logs & Answers
` (Backtick)    Exit Application
Middle + Scroll Up     Capture
Middle + Scroll Down   Show Answers"""
    tk.Label(hotkey_frame, text=fixed_info, font=("Consolas", 9), 
             justify=tk.LEFT).pack(anchor=tk.W)
    
    # Buttons
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    
    def on_save():
        # Save API key if changed
        api_key = api_entry.get().strip()
        if api_key and not api_key.startswith("*"):
            import base64
            # Encode API key (simple obfuscation)
            encoded_key = base64.b64encode(api_key.encode()).decode()
            # Update in settings_manager (will be saved with other settings)
            settings_manager.settings['gemini_api_key'] = encoded_key
            os.environ['GEMINI_API_KEY'] = api_key
            if on_api_change:
                on_api_change()
        
        # Check if mode changed
        old_mode = settings_manager.get('question_mode', 'multiple_choice')
        new_mode = mode_var.get()
        
        # Check if hotkeys changed
        hotkeys_changed = False
        for key, entry in hotkey_entries.items():
            old_val = settings_manager.get(key) or hotkey_defaults.get(key, '')
            new_val = entry.get().lower()
            if old_val.lower() != new_val:
                hotkeys_changed = True
            settings_manager.settings[key] = new_val
        
        # Save display settings
        settings_manager.settings['font_size'] = font_var.get()
        settings_manager.settings['popup_width'] = width_var.get()
        settings_manager.settings['answers_per_line'] = apl_var.get()
        settings_manager.settings['question_mode'] = new_mode
        
        # Save all settings to file at once
        settings_manager.save_settings()
        
        if on_settings_change:
            on_settings_change()
        
        # Notify mode change
        if old_mode != new_mode and on_mode_change:
            on_mode_change(new_mode)
        
        # Notify hotkey change
        if hotkeys_changed and on_hotkey_change:
            on_hotkey_change()
        
        msg = "Settings saved!"
        if hotkeys_changed:
            msg += "\nHotkey changes will apply after restart."
        messagebox.showinfo("Success", msg, parent=dialog)
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    tk.Button(btn_frame, text="Save", command=on_save, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    
    dialog.mainloop()
