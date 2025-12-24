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
                    # Merge with defaults
                    for key in self.DEFAULT_SETTINGS:
                        if key in config:
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
            
            # Update settings
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
    if parent is None:
        root = tk.Tk()
        root.withdraw()
    else:
        root = parent
    
    dialog = tk.Toplevel(root)
    dialog.title("AI Quiz Assistant - Setup Required")
    dialog.geometry("450x200")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    
    # Center dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 450) // 2
    y = (dialog.winfo_screenheight() - 200) // 2
    dialog.geometry(f"+{x}+{y}")
    
    result = {'api_key': None}
    
    # Title
    tk.Label(dialog, text="Gemini API Key Required", 
             font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
    
    tk.Label(dialog, text="Please enter your Google Gemini API key to continue.",
             font=("Segoe UI", 9)).pack(pady=(0, 10))
    
    # API Key entry
    frame = tk.Frame(dialog)
    frame.pack(pady=10, padx=20, fill=tk.X)
    
    tk.Label(frame, text="API Key:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    
    api_entry = tk.Entry(frame, show="*", font=("Segoe UI", 10), width=45)
    api_entry.pack(fill=tk.X, pady=(5, 0))
    api_entry.focus()
    
    # Link to get API key
    link_label = tk.Label(dialog, text="Get API key from Google AI Studio", 
                          font=("Segoe UI", 8), fg="blue", cursor="hand2")
    link_label.pack()
    link_label.bind("<Button-1>", lambda e: os.startfile("https://makersuite.google.com/app/apikey"))
    
    # Buttons
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=15)
    
    def on_save():
        api_key = api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "API key cannot be empty")
            return
        if len(api_key) < 20:
            messagebox.showerror("Error", "API key is too short")
            return
        result['api_key'] = api_key
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    tk.Button(btn_frame, text="Save", command=on_save, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Exit", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    # Handle Enter key
    api_entry.bind("<Return>", lambda e: on_save())
    dialog.bind("<Escape>", lambda e: on_cancel())
    
    dialog.wait_window()
    
    if parent is None:
        root.destroy()
    
    return result['api_key']


def show_settings_dialog(settings_manager: SettingsManager, 
                         on_api_change: callable = None,
                         on_settings_change: callable = None,
                         on_mode_change: callable = None) -> None:
    """
    Show settings dialog with all configuration options
    """
    root = tk.Tk()
    root.withdraw()
    
    dialog = tk.Toplevel(root)
    dialog.title("AI Quiz Assistant - Settings")
    dialog.geometry("420x400")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    
    # Center dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 420) // 2
    y = (dialog.winfo_screenheight() - 400) // 2
    dialog.geometry(f"+{x}+{y}")
    
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
    has_api = bool(os.getenv('GEMINI_API_KEY'))
    if has_api:
        api_entry.insert(0, "********** (configured)")
        api_entry.config(state='disabled')
    
    def change_api():
        api_entry.config(state='normal')
        api_entry.delete(0, tk.END)
        api_entry.focus()
    
    tk.Button(api_frame, text="Change API Key", command=change_api).pack(anchor=tk.W)
    
    # === Question Mode Tab ===
    mode_frame = ttk.Frame(notebook, padding=10)
    notebook.add(mode_frame, text="Question Mode")
    
    tk.Label(mode_frame, text="Select how AI should answer questions:", 
             font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
    mode_var = tk.StringVar(value=settings_manager.get('question_mode', 'multiple_choice'))
    
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
    
    # Font size
    tk.Label(display_frame, text="Font Size:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    font_var = tk.IntVar(value=settings_manager.get('font_size', 9))
    font_scale = tk.Scale(display_frame, from_=6, to=14, orient=tk.HORIZONTAL, 
                          variable=font_var, length=200)
    font_scale.pack(anchor=tk.W, pady=(0, 10))
    
    # Popup width
    tk.Label(display_frame, text="Popup Width:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    width_var = tk.IntVar(value=settings_manager.get('popup_width', 400))
    width_scale = tk.Scale(display_frame, from_=250, to=600, orient=tk.HORIZONTAL,
                           variable=width_var, length=200)
    width_scale.pack(anchor=tk.W, pady=(0, 10))
    
    # Answers per line
    tk.Label(display_frame, text="Answers per line:", font=("Segoe UI", 9)).pack(anchor=tk.W)
    apl_var = tk.IntVar(value=settings_manager.get('answers_per_line', 10))
    apl_scale = tk.Scale(display_frame, from_=5, to=20, orient=tk.HORIZONTAL,
                         variable=apl_var, length=200)
    apl_scale.pack(anchor=tk.W)
    
    # === Hotkeys Tab (Info only) ===
    hotkey_frame = ttk.Frame(notebook, padding=10)
    notebook.add(hotkey_frame, text="Hotkeys")
    
    hotkeys_info = """
Current Hotkeys:

Alt + Z          Capture & Analyze
Alt + X          Show/Hide Results  
Alt + C          Show Answer History
Alt + R          Reset History
Alt + S          Open Settings
Delete           Clear Logs
` (Backtick)     Exit Application

Middle Mouse + Scroll Up    Capture
Middle Mouse + Scroll Down  History
"""
    tk.Label(hotkey_frame, text=hotkeys_info, font=("Consolas", 9), 
             justify=tk.LEFT).pack(anchor=tk.W)
    
    # Buttons
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    
    def on_save():
        # Save API key if changed
        api_key = api_entry.get().strip()
        if api_key and not api_key.startswith("*"):
            # Hash and save
            hashed = hashlib.sha256(api_key.encode()).hexdigest()
            config = {}
            if os.path.exists("config.json"):
                with open("config.json", 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['gemini_api_key_hash'] = hashed
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            os.environ['GEMINI_API_KEY'] = api_key
            if on_api_change:
                on_api_change()
        
        # Check if mode changed
        old_mode = settings_manager.get('question_mode', 'multiple_choice')
        new_mode = mode_var.get()
        
        # Save display settings
        settings_manager.set('font_size', font_var.get())
        settings_manager.set('popup_width', width_var.get())
        settings_manager.set('answers_per_line', apl_var.get())
        settings_manager.set('question_mode', new_mode)
        
        if on_settings_change:
            on_settings_change()
        
        # Notify mode change
        if old_mode != new_mode and on_mode_change:
            on_mode_change(new_mode)
        
        messagebox.showinfo("Success", "Settings saved!")
        dialog.destroy()
        root.destroy()
    
    def on_cancel():
        dialog.destroy()
        root.destroy()
    
    tk.Button(btn_frame, text="Save", command=on_save, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    
    root.mainloop()
