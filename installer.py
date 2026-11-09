#!/usr/bin/env python3
"""
AI Quiz Assistant 2.0 - Windows Graphical Setup & Installation Wizard
- Select installation destination folder (nơi lưu)
- Register Desktop & Start Menu shortcuts with official standard icon (đăng kí icon như các app khác)
- Register Windows Apps & Features (Uninstall registry) and App Paths
- Launch application upon completion, which opens the 3-step setup UI (khi setup xong mở ra có 3 bước setup UI)
"""

import os
import sys
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Add project root and src to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

try:
    from constants import APP_NAME, APP_VERSION, APP_DISPLAY_NAME, GITHUB_REPO_URL
except ImportError:
    APP_NAME = "AI Quiz Assistant"
    APP_VERSION = "2.0.0"
    APP_DISPLAY_NAME = f"{APP_NAME} {APP_VERSION}"
    GITHUB_REPO_URL = "https://github.com/nvtruongops/ai-quiz-assistant"

try:
    from shortcut_manager import (
        get_default_install_dir,
        get_desktop_dir,
        get_start_menu_dir,
        create_windows_shortcut,
        register_windows_app,
        generate_uninstaller_script
    )
except ImportError:
    from src.shortcut_manager import (
        get_default_install_dir,
        get_desktop_dir,
        get_start_menu_dir,
        create_windows_shortcut,
        register_windows_app,
        generate_uninstaller_script
    )


def get_bundle_dir() -> str:
    """Return the base directory where installer assets reside (sys._MEIPASS when frozen)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return PROJECT_ROOT


def get_available_disk_space_gb(path: str) -> float:
    """Calculate free disk space in GB for the drive containing path."""
    try:
        drive = os.path.splitdrive(os.path.abspath(path))[0]
        if not drive:
            drive = "C:"
        drive = drive + "\\"
        free_bytes = shutil.disk_usage(drive).free
        return round(free_bytes / (1024 ** 3), 1)
    except Exception:
        return 0.0


class SetupInstallerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION} Setup")
        self.root.geometry("580x490")
        self.root.minsize(560, 470)
        self.root.configure(bg="#f8fafc")

        self.bundle_dir = get_bundle_dir()
        self.current_step = 1
        self.installed_exe_path = ""

        # Setup icon
        self.icon_path = self.locate_icon()
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        # Variables
        self.install_dir_var = tk.StringVar(master=self.root, value=get_default_install_dir())
        self.create_desktop_var = tk.BooleanVar(master=self.root, value=True)
        self.create_start_menu_var = tk.BooleanVar(master=self.root, value=True)
        self.register_windows_var = tk.BooleanVar(master=self.root, value=True)
        self.register_app_paths_var = tk.BooleanVar(master=self.root, value=True)
        self.launch_app_var = tk.BooleanVar(master=self.root, value=True)

        self._build_header()
        self._build_body()
        self._build_footer()

        self.show_step(1)

    def locate_icon(self) -> str:
        candidates = [
            os.path.join(self.bundle_dir, "assets", "icon.ico"),
            os.path.join(PROJECT_ROOT, "assets", "icon.ico"),
            os.path.join(self.bundle_dir, "icon.ico")
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return ""

    def _build_header(self):
        self.header_frame = tk.Frame(self.root, bg="#0f172a", height=70, padx=20, pady=12)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)

        header_content = tk.Frame(self.header_frame, bg="#0f172a")
        header_content.pack(fill=tk.BOTH, expand=True)

        self.hdr_title = tk.Label(
            header_content,
            text=f"{APP_NAME} {APP_VERSION} — Setup Wizard",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        self.hdr_title.pack(anchor=tk.W)

        self.hdr_subtitle = tk.Label(
            header_content,
            text="Select Destination Location & Options",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.hdr_subtitle.pack(anchor=tk.W, pady=(2, 0))

    def _build_body(self):
        self.body_container = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=16)
        self.body_container.pack(fill=tk.BOTH, expand=True)

        # Step 1: Destination Location Frame
        self.step1_frame = tk.Frame(self.body_container, bg="#f8fafc")
        self._build_step1_ui()

        # Step 2: Shortcuts & Windows Registration Frame
        self.step2_frame = tk.Frame(self.body_container, bg="#f8fafc")
        self._build_step2_ui()

        # Step 3: Installation Progress Frame
        self.step3_frame = tk.Frame(self.body_container, bg="#f8fafc")
        self._build_step3_ui()

        # Step 4: Finished Frame
        self.step4_frame = tk.Frame(self.body_container, bg="#f8fafc")
        self._build_step4_ui()

    def _build_step1_ui(self):
        tk.Label(
            self.step1_frame,
            text="Where should AI Quiz Assistant 2.0 be installed?",
            font=("Segoe UI", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 6))

        tk.Label(
            self.step1_frame,
            text="Setup will install the application and default configurations into the following folder.\n"
                 "To choose a different folder, click Browse.",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#f8fafc",
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 14))

        dest_box = tk.LabelFrame(
            self.step1_frame,
            text=" Destination Folder ",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff",
            padx=12,
            pady=12,
            bd=1,
            relief=tk.SOLID
        )
        dest_box.pack(fill=tk.X, pady=(0, 16))

        row = tk.Frame(dest_box, bg="#ffffff")
        row.pack(fill=tk.X)

        self.dir_entry = tk.Entry(
            row,
            textvariable=self.install_dir_var,
            font=("Segoe UI", 9),
            bd=1,
            relief=tk.SOLID
        )
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)

        browse_btn = tk.Button(
            row,
            text="📁 Browse...",
            command=self.browse_destination,
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            padx=12,
            pady=3,
            cursor="hand2"
        )
        browse_btn.pack(side=tk.RIGHT)

        # Disk space indicator
        space_frame = tk.Frame(self.step1_frame, bg="#f8fafc")
        space_frame.pack(fill=tk.X)

        tk.Label(
            space_frame,
            text="• At least 65.0 MB of free disk space is required.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#f8fafc"
        ).pack(anchor=tk.W)

        self.disk_space_lbl = tk.Label(
            space_frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#0284c7",
            bg="#f8fafc"
        )
        self.disk_space_lbl.pack(anchor=tk.W, pady=(2, 0))
        self.update_disk_space_label()

    def update_disk_space_label(self):
        path = self.install_dir_var.get().strip() or "C:\\"
        free_gb = get_available_disk_space_gb(path)
        drive = os.path.splitdrive(os.path.abspath(path))[0] or "C:"
        self.disk_space_lbl.config(text=f"• Available space: {free_gb} GB free on drive {drive}")

    def browse_destination(self):
        curr = self.install_dir_var.get().strip()
        selected = filedialog.askdirectory(
            parent=self.root,
            title="Select AI Quiz Assistant Installation Directory",
            initialdir=curr if os.path.exists(curr) else os.path.expanduser("~")
        )
        if selected:
            self.install_dir_var.set(os.path.abspath(selected))
            self.update_disk_space_label()

    def _build_step2_ui(self):
        tk.Label(
            self.step2_frame,
            text="Select Additional Tasks & Shell Registration:",
            font=("Segoe UI", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 6))

        tk.Label(
            self.step2_frame,
            text="Select the shortcuts and system integration tasks you want Setup to perform:",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 12))

        tasks_box = tk.LabelFrame(
            self.step2_frame,
            text=" Shortcuts & Official Icon Registration ",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff",
            padx=14,
            pady=12,
            bd=1,
            relief=tk.SOLID
        )
        tasks_box.pack(fill=tk.X, pady=(0, 10))

        cb_desk = tk.Checkbutton(
            tasks_box,
            text="Create a Desktop shortcut (with official application icon)",
            variable=self.create_desktop_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff"
        )
        cb_desk.pack(anchor=tk.W, pady=4)

        cb_start = tk.Checkbutton(
            tasks_box,
            text="Create a Start Menu shortcut for quick access",
            variable=self.create_start_menu_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff"
        )
        cb_start.pack(anchor=tk.W, pady=4)

        cb_reg = tk.Checkbutton(
            tasks_box,
            text="Register in Windows Apps & Features (Add/Remove Programs with icon & uninstaller)",
            variable=self.register_windows_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff"
        )
        cb_reg.pack(anchor=tk.W, pady=4)

        cb_path = tk.Checkbutton(
            tasks_box,
            text="Register App Path (allows launching via Win+R > QuizAssistant)",
            variable=self.register_app_paths_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff"
        )
        cb_path.pack(anchor=tk.W, pady=4)

        info_lbl = tk.Label(
            self.step2_frame,
            text="💡 The application icon is officially registered in high-definition (16x16 to 256x256)\n"
                 "and will appear properly on your Desktop, Start Menu, and Windows Taskbar.",
            font=("Segoe UI", 8, "italic"),
            fg="#64748b",
            bg="#f8fafc",
            justify=tk.LEFT
        )
        info_lbl.pack(anchor=tk.W, pady=(6, 0))

    def _build_step3_ui(self):
        tk.Label(
            self.step3_frame,
            text="Installing AI Quiz Assistant 2.0...",
            font=("Segoe UI", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 6))

        self.install_status_lbl = tk.Label(
            self.step3_frame,
            text="Preparing installation...",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#f8fafc"
        )
        self.install_status_lbl.pack(anchor=tk.W, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(
            self.step3_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            length=500
        )
        self.progress_bar.pack(fill=tk.X, pady=(10, 16))

        self.install_log_box = tk.Text(
            self.step3_frame,
            height=8,
            font=("Consolas", 8),
            bg="#1e293b",
            fg="#f8fafc",
            bd=1,
            relief=tk.SOLID
        )
        self.install_log_box.pack(fill=tk.BOTH, expand=True)

    def _build_step4_ui(self):
        tk.Label(
            self.step4_frame,
            text="🎉 Setup Completed Successfully!",
            font=("Segoe UI", 12, "bold"),
            fg="#16a34a",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 6))

        tk.Label(
            self.step4_frame,
            text=f"AI Quiz Assistant 2.0 has been installed on your computer.\n"
                 f"Official shortcuts and Windows integrations have been configured.",
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#f8fafc",
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 14))

        summary_box = tk.LabelFrame(
            self.step4_frame,
            text=" Installation Summary ",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff",
            padx=14,
            pady=10,
            bd=1,
            relief=tk.SOLID
        )
        summary_box.pack(fill=tk.X, pady=(0, 14))

        self.sum_dest_lbl = tk.Label(summary_box, text="", font=("Segoe UI", 8), bg="#ffffff", anchor=tk.W)
        self.sum_dest_lbl.pack(fill=tk.X, pady=2)

        self.sum_sc_lbl = tk.Label(summary_box, text="", font=("Segoe UI", 8), bg="#ffffff", anchor=tk.W)
        self.sum_sc_lbl.pack(fill=tk.X, pady=2)

        cb_launch = tk.Checkbutton(
            self.step4_frame,
            text="Launch AI Quiz Assistant 2.0 now (opens 3-step setup wizard)",
            variable=self.launch_app_var,
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
            activebackground="#f8fafc"
        )
        cb_launch.pack(anchor=tk.W, pady=(0, 8))

        tk.Label(
            self.step4_frame,
            text="💡 On first launch, the 3-step Initial Setup Wizard will guide you to:\n"
                 "1. Configure AI Vision Provider (Google Gemini or Local Ollama/vLLM)\n"
                 "2. Select floating HUD theme & live transparency\n"
                 "3. Choose quiz solving mode & customize keyboard shortcuts",
            font=("Segoe UI", 8, "italic"),
            fg="#64748b",
            bg="#f8fafc",
            justify=tk.LEFT
        ).pack(anchor=tk.W)

    def _build_footer(self):
        footer_frame = tk.Frame(self.root, bg="#f1f5f9", height=54, padx=20, pady=10, bd=1, relief=tk.GROOVE)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.cancel_btn = tk.Button(
            footer_frame,
            text="Cancel",
            command=self.on_cancel,
            font=("Segoe UI", 9),
            padx=14,
            pady=3
        )
        self.cancel_btn.pack(side=tk.LEFT)

        self.next_btn = tk.Button(
            footer_frame,
            text="Next >",
            command=self.on_next,
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            padx=18,
            pady=3,
            cursor="hand2"
        )
        self.next_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.back_btn = tk.Button(
            footer_frame,
            text="< Back",
            command=self.on_back,
            font=("Segoe UI", 9),
            padx=14,
            pady=3
        )
        self.back_btn.pack(side=tk.RIGHT)

    def show_step(self, step_num: int):
        self.current_step = step_num
        self.step1_frame.pack_forget()
        self.step2_frame.pack_forget()
        self.step3_frame.pack_forget()
        self.step4_frame.pack_forget()

        if step_num == 1:
            self.hdr_subtitle.config(text="Step 1/3: Select Destination Location")
            self.step1_frame.pack(fill=tk.BOTH, expand=True)
            self.back_btn.config(state=tk.DISABLED)
            self.next_btn.config(text="Next >", state=tk.NORMAL, bg="#0284c7")
            self.cancel_btn.config(state=tk.NORMAL)
        elif step_num == 2:
            self.hdr_subtitle.config(text="Step 2/3: Shortcuts & Shell Integration")
            self.step2_frame.pack(fill=tk.BOTH, expand=True)
            self.back_btn.config(state=tk.NORMAL)
            self.next_btn.config(text="Install", state=tk.NORMAL, bg="#16a34a")
            self.cancel_btn.config(state=tk.NORMAL)
        elif step_num == 3:
            self.hdr_subtitle.config(text="Installing AI Quiz Assistant 2.0...")
            self.step3_frame.pack(fill=tk.BOTH, expand=True)
            self.back_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)
            threading.Thread(target=self.run_installation, daemon=True).start()
        elif step_num == 4:
            self.hdr_subtitle.config(text="Setup Complete")
            self.step4_frame.pack(fill=tk.BOTH, expand=True)
            self.back_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)
            self.next_btn.config(text="Finish", state=tk.NORMAL, bg="#16a34a")

    def on_back(self):
        if self.current_step > 1:
            self.show_step(self.current_step - 1)

    def on_next(self):
        if self.current_step == 1:
            dest = self.install_dir_var.get().strip()
            if not dest:
                messagebox.showerror("Invalid Location", "Please enter a valid destination folder.", parent=self.root)
                return
            self.show_step(2)
        elif self.current_step == 2:
            self.show_step(3)
        elif self.current_step == 4:
            self.finish_and_exit()

    def on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Are you sure you want to cancel the installation?", parent=self.root):
            self.root.destroy()

    def append_log(self, text: str):
        def _a():
            self.install_log_box.insert(tk.END, text + "\n")
            self.install_log_box.see(tk.END)
        self.root.after(0, _a)

    def set_progress(self, pct: int, text: str):
        def _u():
            self.progress_bar['value'] = pct
            self.install_status_lbl.config(text=text)
        self.root.after(0, _u)

    def run_installation(self):
        dest_dir = os.path.abspath(self.install_dir_var.get().strip())
        self.set_progress(10, f"Creating destination directory: {dest_dir}...")
        self.append_log(f"[*] Destination: {dest_dir}")

        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            self.append_log(f"[ERROR] Could not create destination directory: {e}")
            self.root.after(0, lambda: messagebox.showerror("Install Error", f"Could not create folder: {e}", parent=self.root))
            return

        # 1. Locate source executable and files
        self.set_progress(25, "Locating application binaries and assets...")
        candidates_exe = [
            os.path.join(self.bundle_dir, "QuizAssistant.exe"),
            os.path.join(PROJECT_ROOT, "dist", "QuizAssistant.exe"),
            os.path.join(PROJECT_ROOT, "QuizAssistant.exe")
        ]
        source_exe = ""
        for c in candidates_exe:
            if os.path.exists(c):
                source_exe = c
                break

        dest_exe = os.path.join(dest_dir, "QuizAssistant.exe")
        self.installed_exe_path = dest_exe

        if source_exe and os.path.exists(source_exe):
            self.set_progress(40, "Copying QuizAssistant.exe to destination...")
            self.append_log(f"[*] Copying {os.path.basename(source_exe)} -> {dest_exe}")
            try:
                shutil.copy2(source_exe, dest_exe)
                self.append_log("  -> Copied QuizAssistant.exe successfully")
            except Exception as e:
                self.append_log(f"  [ERROR] Failed to copy exe: {e}")
        else:
            # If running in source/dev mode without compiled exe, create a launcher runner
            self.append_log("[!] Standalone QuizAssistant.exe not found. Installing source launcher...")
            runner_bat = os.path.join(dest_dir, "QuizAssistant.bat")
            self.installed_exe_path = runner_bat
            with open(runner_bat, "w", encoding="utf-8") as f:
                f.write(f'@echo off\ncd /d "{PROJECT_ROOT}"\nstart pythonw run.pyw\n')
            self.append_log(f"  -> Created launcher at {runner_bat}")

        # 2. Copy Assets (icon.ico, icon.png)
        self.set_progress(55, "Deploying application icons and documentation...")
        dest_assets = os.path.join(dest_dir, "assets")
        os.makedirs(dest_assets, exist_ok=True)

        for icon_file in ["icon.ico", "icon.png"]:
            src_i = os.path.join(self.bundle_dir, "assets", icon_file)
            if not os.path.exists(src_i):
                src_i = os.path.join(PROJECT_ROOT, "assets", icon_file)
            if os.path.exists(src_i):
                dest_i = os.path.join(dest_assets, icon_file)
                try:
                    shutil.copy2(src_i, dest_i)
                    self.append_log(f"  -> Deployed {icon_file}")
                except Exception as e:
                    self.append_log(f"  [!] Failed to copy {icon_file}: {e}")

        # Copy .env.example & README.txt
        for doc_file in [".env.example", "README.md", "README.txt"]:
            src_d = os.path.join(self.bundle_dir, doc_file)
            if not os.path.exists(src_d):
                src_d = os.path.join(PROJECT_ROOT, doc_file)
            if os.path.exists(src_d):
                dest_d = os.path.join(dest_dir, doc_file)
                try:
                    shutil.copy2(src_d, dest_d)
                except Exception:
                    pass

        # 3. Generate clean uninstaller
        self.set_progress(70, "Generating uninstallation utility...")
        try:
            uninst_path = generate_uninstaller_script(dest_dir)
            self.append_log(f"[*] Uninstaller generated at: {uninst_path}")
        except Exception as e:
            self.append_log(f"  [!] Could not generate uninstaller: {e}")

        # 4. Create Shortcuts with official icon
        self.set_progress(80, "Creating Windows shortcuts & registering icon...")
        dest_icon = os.path.join(dest_assets, "icon.ico")
        if not os.path.exists(dest_icon):
            dest_icon = self.icon_path

        sc_summary = []
        if self.create_desktop_var.get():
            desk_path = os.path.join(get_desktop_dir(), f"{APP_NAME}.lnk")
            ok, msg = create_windows_shortcut(self.installed_exe_path, desk_path, icon_path=dest_icon)
            if ok:
                self.append_log(f"  ✅ Desktop shortcut created: {desk_path}")
                sc_summary.append("Desktop")
            else:
                self.append_log(f"  ⚠️ Desktop shortcut notice: {msg}")

        if self.create_start_menu_var.get():
            start_path = os.path.join(get_start_menu_dir(), f"{APP_NAME}.lnk")
            ok, msg = create_windows_shortcut(self.installed_exe_path, start_path, icon_path=dest_icon)
            if ok:
                self.append_log(f"  ✅ Start Menu shortcut created: {start_path}")
                sc_summary.append("Start Menu")
            else:
                self.append_log(f"  ⚠️ Start Menu shortcut notice: {msg}")

        # 5. Register in Windows Registry (Apps & Features + App Paths)
        if self.register_windows_var.get():
            self.set_progress(90, "Registering in Windows Apps & Features...")
            ok, msg = register_windows_app(dest_dir, self.installed_exe_path, icon_path=dest_icon)
            if ok:
                self.append_log("  ✅ Registered in Windows Apps & Features (with icon)")
            else:
                self.append_log(f"  ⚠️ Windows registration notice: {msg}")

        self.set_progress(100, "Installation completed!")
        self.append_log("[*] All setup tasks finished successfully.")

        # Update Step 4 summary labels
        def _finish_ui():
            self.sum_dest_lbl.config(text=f"• Location: {dest_dir}")
            sc_text = ", ".join(sc_summary) if sc_summary else "None"
            self.sum_sc_lbl.config(text=f"• Shortcuts Created: {sc_text} (with high-res app icon)")
            self.show_step(4)

        self.root.after(400, _finish_ui)

    def finish_and_exit(self):
        if self.launch_app_var.get() and self.installed_exe_path and os.path.exists(self.installed_exe_path):
            try:
                working_dir = os.path.dirname(self.installed_exe_path)
                subprocess.Popen(
                    [self.installed_exe_path],
                    cwd=working_dir,
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                )
            except Exception as e:
                messagebox.showwarning("Launch Notice", f"Could not launch application automatically: {e}", parent=self.root)

        self.root.destroy()


def main():
    root = tk.Tk()
    app = SetupInstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
