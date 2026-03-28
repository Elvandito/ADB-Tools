import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import sys

# Windows-specific flag to prevent the console window from popping up
CREATE_NO_WINDOW = 0x08000000

class ModernButton(tk.Button):
    """Custom Button class for a modern look with hover effect"""
    def __init__(self, master, hover_bg="#005f9e", default_bg="#007acc", fg_color="white", **kwargs):
        tk.Button.__init__(self, master, **kwargs)
        self.default_bg = default_bg
        self.hover_bg = hover_bg
        self.config(
            bg=self.default_bg, 
            fg=fg_color, 
            relief="flat", 
            borderwidth=0, 
            cursor="hand2", 
            font=("Segoe UI", 9, "bold"),
            activebackground=self.hover_bg,
            activeforeground=fg_color,
            padx=12,
            pady=6
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self.config(bg=self.hover_bg)

    def on_leave(self, e):
        self.config(bg=self.default_bg)


class ADBDesktopApp:
    def __init__(self, root):
        # --- FIX FOR WINDOWS TASKBAR ---
        # Tell Windows this is a standalone application, not generic Python
        if os.name == 'nt':
            try:
                import ctypes
                myappid = 'elvan.adbtools.desktop.1' # Unique ID for your application
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except:
                pass
        # ---------------------------------

        self.root = root
        self.root.title("ADB Tools")
        self.root.geometry("1100x780")

        # --- SET WINDOW AND TASKBAR ICON ---
        try:
            # If running from .exe (PyInstaller), look in the temp folder _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # If running from a regular python script, look in the current folder
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_path, "app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        # ------------------------------------
        
        # Color Palette (VS Code / Fluent UI Dark)
        self.colors = {
            "bg_main": "#1e1e1e",      
            "bg_panel": "#252526",     
            "bg_card": "#2d2d30",      
            "bg_sidebar": "#18181a",   
            "bg_input": "#1e1e1e",     
            "accent": "#007acc",       
            "accent_hover": "#005f9e", 
            "text": "#cccccc",
            "text_light": "#ffffff",
            "text_muted": "#858585",
            "term_bg": "#0c0c0c",      
            "term_header": "#333333",  
            "term_green": "#4af626",
            "term_red": "#f44747",
            "term_blue": "#569cd6",
            "border": "#3e3e42"        
        }
        
        self.root.configure(bg=self.colors["bg_main"])
        
        # State & Process Tracking
        self.selected_push_file = ""
        self.selected_pull_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.in_adb_shell = False
        self.device_codename = "android"  
        self.android_cwd = "/" # Tracking Android directory in real-time
        self.active_processes = []
        
        # Point to the directory where this script/.exe is located
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        
        os.chdir(script_dir)
        self.default_prompt = self.get_display_prompt()
        self.prompt_text = tk.StringVar(value=self.default_prompt)

        self.setup_ui()
        self.append_terminal("ADB Tools Terminal v1.0 (Stateful Android Shell)\n", "sys")
        self.append_terminal("INFO: The 'cd' command inside ADB Shell is now fully functional!\n", "success")
        
        # Clean up processes when the application is closed (Click X)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.entry_cmd.bind("<Control-c>", self.handle_ctrl_c)
        self.entry_cmd.bind("<Control-d>", self.exit_shell_mode)
        
        self.run_startup_checks()
        # Start Background Poller to check connection silently
        self.start_silent_poller()

    def get_creationflags(self):
        """Returns the flag to hide the console window completely on Windows"""
        return CREATE_NO_WINDOW if os.name == 'nt' else 0

    def get_display_prompt(self):
        """Shorten the path string if it's too long so it doesn't break the UI"""
        cwd = os.getcwd()
        if len(cwd) > 35:
            folder_name = os.path.basename(cwd)
            if not folder_name:  # Just in case it's in the root (e.g., C:\)
                return f"{cwd}>"
            if len(folder_name) > 20: # If the folder name itself is too long
                folder_name = folder_name[:17] + "..."
            return f"{cwd[:3]}...\\{folder_name}>"
        return f"{cwd}>"

    def setup_ui(self):
        # ==========================================
        # 1. LEFT SIDEBAR
        # ==========================================
        sidebar = tk.Frame(self.root, bg=self.colors["bg_sidebar"], width=260)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="⚡ ADB Tools", fg=self.colors["text_light"], bg=self.colors["bg_sidebar"], 
                 font=("Segoe UI", 16, "bold")).pack(pady=(25, 15))
                 
        tk.Frame(sidebar, height=1, bg=self.colors["border"]).pack(fill=tk.X, padx=20, pady=(0, 15))

        status_frame = tk.Frame(sidebar, bg=self.colors["bg_panel"], highlightbackground=self.colors["border"], highlightthickness=1)
        status_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        tk.Label(status_frame, text="DEVICE STATUS", fg=self.colors["text_muted"], bg=self.colors["bg_panel"], font=("Segoe UI", 8, "bold")).pack(pady=(10, 2))
        
        status_inner = tk.Frame(status_frame, bg=self.colors["bg_panel"])
        status_inner.pack(pady=(0, 10))
        self.lbl_status_dot = tk.Label(status_inner, text="●", fg="gray", bg=self.colors["bg_panel"], font=("Segoe UI", 12))
        self.lbl_status_dot.pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_status = tk.Label(status_inner, text="Checking...", fg=self.colors["text"], bg=self.colors["bg_panel"], font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.LEFT)
        self.lbl_device_id = tk.Label(status_frame, text="", fg=self.colors["text_muted"], bg=self.colors["bg_panel"], font=("Segoe UI", 9))
        self.lbl_device_id.pack(pady=(0, 10))

        menu_container = tk.Frame(sidebar, bg=self.colors["bg_sidebar"])
        menu_container.pack(fill=tk.BOTH, expand=True)

        menu_canvas = tk.Canvas(menu_container, bg=self.colors["bg_sidebar"], highlightthickness=0)
        menu_scrollbar = tk.Scrollbar(menu_container, orient="vertical", command=menu_canvas.yview)
        
        self.menu_frame = tk.Frame(menu_canvas, bg=self.colors["bg_sidebar"])
        self.menu_frame.bind("<Configure>", lambda e: menu_canvas.configure(scrollregion=menu_canvas.bbox("all")))
        canvas_window = menu_canvas.create_window((0, 0), window=self.menu_frame, anchor="nw")
        
        def configure_canvas_width(event):
            menu_canvas.itemconfig(canvas_window, width=event.width)
            
        menu_canvas.bind('<Configure>', configure_canvas_width)
        menu_canvas.configure(yscrollcommand=menu_scrollbar.set)
        menu_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        menu_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            menu_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        menu_canvas.bind('<Enter>', lambda _: menu_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        menu_canvas.bind('<Leave>', lambda _: menu_canvas.unbind_all("<MouseWheel>"))

        def add_header(text):
            tk.Label(self.menu_frame, text=text, fg=self.colors["text_muted"], bg=self.colors["bg_sidebar"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=20, pady=(15, 5))

        def add_menu_btn(text, command, icon=""):
            btn_text = f"{icon}  {text}" if icon else text
            ModernButton(self.menu_frame, text=btn_text, command=command, default_bg="#252526", hover_bg="#3e3e42", font=("Segoe UI", 9), anchor="w", padx=20).pack(fill=tk.X, padx=15, pady=2)

        add_header("GENERAL")
        add_menu_btn("Check Devices", lambda: self.run_command_async("adb devices"), "📱")
        add_menu_btn("ADB Shell", self.enter_shell_mode, "🐚")
        add_menu_btn("Clear Terminal", self.clear_terminal, "🧹")

        # Scrcpy Options
        add_header("SCRCPY (MIRRORING)")
        add_menu_btn("Scrcpy (Video + Audio)", lambda: self.start_scrcpy("scrcpy"), "📺")
        add_menu_btn("Scrcpy (No Audio)", lambda: self.start_scrcpy("scrcpy --no-audio"), "🔇")
        add_menu_btn("Scrcpy (Audio Only)", lambda: self.start_scrcpy("scrcpy --no-video"), "🎵")
        add_menu_btn("Scrcpy (Screen Off)", lambda: self.start_scrcpy("scrcpy --turn-screen-off"), "🔋")

        add_header("ADB REBOOT")
        add_menu_btn("Reboot System", lambda: self.run_command_async("adb reboot"), "🔄")
        add_menu_btn("Reboot Recovery", lambda: self.run_command_async("adb reboot recovery"), "🔄")
        add_menu_btn("Reboot Bootloader", lambda: self.run_command_async("adb reboot bootloader"), "🔄")
        add_menu_btn("Reboot FastbootD", lambda: self.run_command_async("adb reboot fastboot"), "🔄")

        add_header("FASTBOOT")
        add_menu_btn("Check Fastboot", lambda: self.run_command_async("fastboot devices"), "⚡")
        add_menu_btn("Reboot System", lambda: self.run_command_async("fastboot reboot"), "⚡")
        add_menu_btn("Reboot Bootloader", lambda: self.run_command_async("fastboot reboot bootloader"), "⚡")
        add_menu_btn("Reboot Recovery", lambda: self.run_command_async("fastboot reboot recovery"), "⚡")
        add_menu_btn("Reboot FastbootD", lambda: self.run_command_async("fastboot reboot fastboot"), "⚡")
        add_menu_btn("Reboot EDL", lambda: self.run_command_async("fastboot oem edl"), "⚡")

        # ==========================================
        # 2. RIGHT MAIN AREA
        # ==========================================
        main_area = tk.Frame(self.root, bg=self.colors["bg_main"])
        main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        transfer_frame = tk.Frame(main_area, bg=self.colors["bg_main"])
        transfer_frame.pack(fill=tk.X, pady=(0, 15))

        def style_entry(parent):
            return tk.Entry(parent, bg=self.colors["bg_input"], fg=self.colors["text_light"], 
                            insertbackground="white", relief="flat", font=("Consolas", 10), 
                            highlightthickness=1, highlightbackground=self.colors["border"], highlightcolor=self.colors["accent"])

        def create_card(parent, title, icon):
            card = tk.Frame(parent, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
            tk.Frame(card, bg=self.colors["accent"], height=3).pack(fill=tk.X, side=tk.TOP)
            tk.Label(card, text=f"{icon} {title}", fg=self.colors["text_light"], bg=self.colors["bg_card"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 10))
            return card

        # PUSH CARD
        push_card = create_card(transfer_frame, "ADB Push (PC ➔ Phone)", "📤")
        push_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        file_frame = tk.Frame(push_card, bg=self.colors["bg_card"])
        file_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        self.lbl_push_file = tk.Label(file_frame, text="Select file from PC...", bg=self.colors["bg_card"], fg=self.colors["text_muted"], font=("Segoe UI", 9))
        self.lbl_push_file.pack(side=tk.LEFT)
        ModernButton(file_frame, text="Browse", command=self.browse_file, default_bg="#3e3e42", hover_bg="#4e4e52", font=("Segoe UI", 8, "bold"), padx=10, pady=3).pack(side=tk.RIGHT)

        tk.Label(push_card, text="Destination Path (Android):", bg=self.colors["bg_card"], fg=self.colors["text"], font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(0, 5))
        self.entry_push_dest = style_entry(push_card)
        self.entry_push_dest.insert(0, "/sdcard/Download/")
        self.entry_push_dest.pack(anchor="w", fill=tk.X, padx=20, pady=(0, 20), ipady=6)
        ModernButton(push_card, text="Push File", command=self.execute_push).pack(fill=tk.X, padx=20, pady=(0, 20), ipady=2)

        # PULL CARD
        pull_card = create_card(transfer_frame, "ADB Pull (Phone ➔ PC)", "📥")
        pull_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(pull_card, text="Source Path (Android):", bg=self.colors["bg_card"], fg=self.colors["text"], font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(0, 5))
        self.entry_pull_src = style_entry(pull_card)
        self.entry_pull_src.insert(0, "/sdcard/Download/test.txt")
        self.entry_pull_src.pack(anchor="w", fill=tk.X, padx=20, pady=(0, 15), ipady=6)

        folder_frame = tk.Frame(pull_card, bg=self.colors["bg_card"])
        folder_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        self.lbl_pull_dest = tk.Label(folder_frame, text="Save to: Downloads", bg=self.colors["bg_card"], fg=self.colors["text_muted"], font=("Segoe UI", 9))
        self.lbl_pull_dest.pack(side=tk.LEFT)
        ModernButton(folder_frame, text="Change", command=self.browse_folder, default_bg="#3e3e42", hover_bg="#4e4e52", font=("Segoe UI", 8, "bold"), padx=10, pady=3).pack(side=tk.RIGHT)
        ModernButton(pull_card, text="Pull File", command=self.execute_pull).pack(fill=tk.X, padx=20, pady=(0, 20), ipady=2)

        # -- Terminal Input Line
        input_frame = tk.Frame(main_area, bg=self.colors["term_bg"], highlightbackground=self.colors["border"], highlightthickness=1)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))
        
        self.lbl_prompt = tk.Label(input_frame, textvariable=self.prompt_text, bg=self.colors["term_bg"], fg=self.colors["term_green"], font=("Consolas", 11, "bold"), cursor="hand2")
        self.lbl_prompt.pack(side=tk.LEFT, padx=(15, 5), pady=12)         
        self.lbl_prompt.bind("<Button-1>", self.change_working_directory)
        
        # Tools & Buttons
        tools_frame = tk.Frame(input_frame, bg=self.colors["term_bg"])
        tools_frame.pack(side=tk.RIGHT, padx=(5, 10), pady=8)

        self.btn_exit_shell = ModernButton(tools_frame, text="🚪 Exit Shell (Ctrl+D)", command=self.exit_shell_mode, default_bg="#b07d0b", hover_bg="#d49a11", font=("Segoe UI", 8, "bold"), padx=10, pady=4)
        self.btn_file = ModernButton(tools_frame, text="📎 File Path", command=self.insert_file_to_term, default_bg="#3e3e42", hover_bg="#4e4e52", font=("Segoe UI", 8, "bold"), padx=8, pady=4)
        self.btn_dir = ModernButton(tools_frame, text="📁 Dir Path", command=self.insert_dir_to_term, default_bg="#3e3e42", hover_bg="#4e4e52", font=("Segoe UI", 8, "bold"), padx=8, pady=4)
        self.btn_stop = ModernButton(tools_frame, text="🛑 Stop", command=self.stop_processes, default_bg="#c50f1f", hover_bg="#f44747", font=("Segoe UI", 8, "bold"), padx=10, pady=4)

        self.btn_file.pack(side=tk.LEFT, padx=2)
        self.btn_dir.pack(side=tk.LEFT, padx=2)

        self.entry_cmd = tk.Entry(input_frame, bg=self.colors["term_bg"], fg=self.colors["text_light"], font=("Consolas", 11), insertbackground="white", relief="flat")
        self.entry_cmd.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=12)
        self.entry_cmd.bind("<Return>", self.on_cmd_enter)
        self.entry_cmd.focus()

        # -- Terminal Area
        term_wrapper = tk.Frame(main_area, bg=self.colors["term_bg"], highlightbackground=self.colors["border"], highlightthickness=1)
        term_wrapper.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        term_header = tk.Frame(term_wrapper, bg=self.colors["term_header"], height=25)
        term_header.pack(fill=tk.X)
        term_header.pack_propagate(False)
        tk.Label(term_header, text="TERMINAL CONSOLE", fg="#aaaaaa", bg=self.colors["term_header"], font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=10)

        self.text_term = tk.Text(term_wrapper, bg=self.colors["term_bg"], fg=self.colors["text"], font=("Consolas", 10), 
                                 state=tk.DISABLED, wrap=tk.WORD, relief="flat", padx=15, pady=10, selectbackground="#264f78")
        self.text_term.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(term_wrapper, command=self.text_term.yview, bg="#333", troughcolor=self.colors["term_bg"])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_term.config(yscrollcommand=scrollbar.set)

        self.text_term.tag_config("cmd", foreground="#d7ba7d", font=("Consolas", 10, "bold")) 
        self.text_term.tag_config("out", foreground=self.colors["text"])
        self.text_term.tag_config("err", foreground=self.colors["term_red"])
        self.text_term.tag_config("sys", foreground=self.colors["term_blue"])
        self.text_term.tag_config("success", foreground=self.colors["term_green"])


    # --- PROCESS MANAGEMENT (STOP & EXIT) ---
    def update_stop_button(self):
        """Show or hide the Stop button based on running processes"""
        # Clear finished/dead processes from the list
        self.active_processes = [p for p in self.active_processes if p.poll() is None]
        if len(self.active_processes) > 0:
            if not self.btn_stop.winfo_ismapped():
                self.btn_stop.pack(side=tk.LEFT, padx=5)
        else:
            if self.btn_stop.winfo_ismapped():
                self.btn_stop.pack_forget()

    def stop_processes(self, event=None):
        if self.active_processes:
            self.append_terminal("\n[!] Force stopping process...\n", "err")
            for p in self.active_processes:
                try:
                    # On Windows, kill the process and all its children (Scrcpy, Logcat)
                    if os.name == 'nt':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)], stdin=subprocess.DEVNULL, startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
                    else:
                        p.terminate()
                except Exception:
                    pass
            self.active_processes.clear()
            self.append_terminal("[✓] Process terminated.\n", "sys")
            self.update_stop_button()

    def handle_ctrl_c(self, event):
        # If there is an active process, Ctrl+C will kill it (like native CMD)
        if self.active_processes:
            self.stop_processes()
            return "break" # Prevent text from being copied when used to stop

    def on_closing(self):
        # Clear list from processes that might have finished instantly
        self.active_processes = [p for p in self.active_processes if p.poll() is None]
        
        # Check if there are still running processes
        if self.active_processes:
            ans = messagebox.askyesno(
                "Active Processes Detected", 
                "There are still active processes running (e.g., Scrcpy, file transfer).\nClosing the application will forcefully terminate them.\n\nAre you sure you want to exit?"
            )
            if not ans:
                return  # Cancel closing if the user chooses 'No'

        # Called when the user closes the application and agrees to close
        for p in self.active_processes:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)], stdin=subprocess.DEVNULL, startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
                else:
                    p.terminate()
            except Exception:
                pass
        self.root.destroy()

    # --- HELPER & WINGET FUNCTIONS ---
    def get_startupinfo(self):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0 # Ensure window is hidden
        return startupinfo

    def check_dependency(self, command):
        try:
            result = subprocess.run(f"where {command}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
            return result.returncode == 0
        except Exception:
            return False

    def prompt_and_install(self, name, winget_id):
        if not self.check_dependency("winget"):
            messagebox.showerror("Winget Not Found", "Your system does not have 'winget'. Please install manually.")
            return

        ans = messagebox.askyesno("Missing Dependency", f"The application '{name}' was not detected.\n\nWould you like to auto-install it using Winget?")
        if ans:
            self.append_terminal(f"Starting automatic installation of {name}...\n", "sys")
            threading.Thread(target=self._run_winget_install, args=(winget_id, name), daemon=True).start()
        else:
            self.append_terminal(f"Installation of {name} cancelled.\n", "err")

    def _run_winget_install(self, winget_id, name):
        cmd = f"winget install --id {winget_id} -e --accept-package-agreements --accept-source-agreements"
        self.root.after(0, self.append_terminal, f"\n{self.prompt_text.get()} {cmd}\n", "cmd")
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace', bufsize=1, startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
            self.active_processes.append(process)
            self.root.after(0, self.update_stop_button)

            for line in iter(process.stdout.readline, ''):
                self.root.after(0, self._process_output_line, line)
                
            process.stdout.close()
            process.wait()

            if process in self.active_processes:
                self.active_processes.remove(process)
            self.root.after(0, self.update_stop_button)

            if process.returncode == 0:
                self.root.after(0, self.append_terminal, f"\n[SUCCESS] {name} installed successfully!\n", "success")
                msg = f"{name} installed! Please restart the app."
                self.root.after(0, messagebox.showinfo, "Success", msg)
            else:
                self.root.after(0, self.append_terminal, f"\n[FAILED] Error code: {process.returncode}\n", "err")
        except Exception as e:
            self.root.after(0, self.append_terminal, f"Error: {str(e)}\n", "err")

    def run_startup_checks(self):
        self.append_terminal("Checking ADB availability...\n", "sys")
        if not self.check_dependency("adb"):
            self.prompt_and_install("Android Platform Tools (ADB)", "Google.PlatformTools")
        else:
            self.run_command_async("adb --version", show_cmd=False)
            self.run_command_async("adb devices", show_cmd=False)

    # --- BACKGROUND SILENT POLLER ---
    def start_silent_poller(self):
        """Start background loop to check device connection without interrupting terminal"""
        self.root.after(2000, self._silent_poll_task)

    def _silent_poll_task(self):
        def task():
            try:
                si = self.get_startupinfo()
                cf = self.get_creationflags()
                res_adb = subprocess.run(["adb", "devices"], capture_output=True, text=True, stdin=subprocess.DEVNULL, startupinfo=si, creationflags=cf)
                lines = res_adb.stdout.strip().split('\n')
                adb_devices = [line.split('\t')[0] for line in lines[1:] if 'device' in line and not 'devices' in line]
                
                if adb_devices:
                    self.root.after(0, self._update_silent_status, "adb", adb_devices[0])
                else:
                    res_fb = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, stdin=subprocess.DEVNULL, startupinfo=si, creationflags=cf)
                    fb_devices = [line.split('\t')[0] for line in res_fb.stdout.strip().split('\n') if 'fastboot' in line]
                    if fb_devices:
                        self.root.after(0, self._update_silent_status, "fastboot", fb_devices[0])
                    else:
                        self.root.after(0, self._update_silent_status, "disconnected", "")
            except Exception:
                pass
            finally:
                self.root.after(3000, self._silent_poll_task)
        threading.Thread(target=task, daemon=True).start()

    def _update_silent_status(self, mode, dev_id):
        if mode == "disconnected":
            self.lbl_status_dot.config(fg="gray")
            self.lbl_status.config(text="Disconnected", fg=self.colors["text_muted"])
            self.lbl_device_id.config(text="")
            self.device_codename = "android"
            if self.in_adb_shell:
                self.append_terminal("\n[!] Device disconnected. Auto-exiting shell.\n", "err")
                self.exit_shell_mode()
        elif mode == "adb":
            self.lbl_status_dot.config(fg=self.colors["term_green"])
            self.lbl_status.config(text="Connected (ADB)", fg=self.colors["text_light"])
            self.lbl_device_id.config(text=f"ID: {dev_id}")
            if self.device_codename == "android":
                threading.Thread(target=self._fetch_codename_async, args=(dev_id,), daemon=True).start()
        elif mode == "fastboot":
            self.lbl_status_dot.config(fg=self.colors["term_blue"])
            self.lbl_status.config(text="Fastboot Mode", fg=self.colors["text_light"])
            self.lbl_device_id.config(text=f"ID: {dev_id}")

    # --- LOGIC FUNCTIONS ---
    def append_terminal(self, text, tag="out"):
        self.text_term.config(state=tk.NORMAL)
        self.text_term.insert(tk.END, text, tag)
        self.text_term.see(tk.END)
        self.text_term.config(state=tk.DISABLED)

    def clear_terminal(self):
        self.text_term.config(state=tk.NORMAL)
        self.text_term.delete(1.0, tk.END)
        self.text_term.config(state=tk.DISABLED)

    def _fetch_codename_async(self, dev_id):
        try:
            cmd = f'adb -s {dev_id} shell getprop ro.product.device'
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace', startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
            stdout, _ = process.communicate()
            
            if stdout and "error" not in stdout.lower() and "not found" not in stdout.lower():
                codename = stdout.strip()
                if codename:
                    self.device_codename = codename
                    if self.in_adb_shell:
                        self.prompt_text.set(f"shell@{self.device_codename}:{self.android_cwd}$")
                    return
            self.device_codename = "android"
        except Exception:
            self.device_codename = "android"

    def change_working_directory(self, event=None):
        if self.in_adb_shell:
            self.append_terminal("\n[!] Cannot change PC directory while in ADB Shell mode.\n", "err")
            return
            
        new_dir = filedialog.askdirectory(title="Select Working Directory")
        if new_dir:
            try:
                os.chdir(new_dir)
                self.default_prompt = self.get_display_prompt()
                self.prompt_text.set(self.default_prompt)
                self.append_terminal(f"\n[✓] Working directory changed to:\n    {os.getcwd()}\n", "success")
            except Exception as e:
                self.append_terminal(f"\n[!] Failed to change directory: {str(e)}\n", "err")

    def insert_file_to_term(self):
        filepath = filedialog.askopenfilename(title="Select File for Terminal")
        if filepath:
            current_text = self.entry_cmd.get()
            if current_text and not current_text.endswith(" "):
                self.entry_cmd.insert(tk.END, " ")
            self.entry_cmd.insert(tk.END, f'"{filepath}" ')
            self.entry_cmd.focus_set()
            self.entry_cmd.icursor(tk.END)

    def insert_dir_to_term(self):
        folderpath = filedialog.askdirectory(title="Select Folder for Terminal")
        if folderpath:
            current_text = self.entry_cmd.get()
            if current_text and not current_text.endswith(" "):
                self.entry_cmd.insert(tk.END, " ")
            self.entry_cmd.insert(tk.END, f'"{folderpath}" ')
            self.entry_cmd.focus_set()
            self.entry_cmd.icursor(tk.END)

    # --- SIMULATED STATEFUL ADB SHELL ---
    def enter_shell_mode(self):
        self.in_adb_shell = True
        self.android_cwd = "/" # Reset to android root
        self.prompt_text.set(f"shell@{self.device_codename}:{self.android_cwd}$")
        self.append_terminal("\n======================================================\n", "sys")
        self.append_terminal("⚡ Entered ADB Shell session.\n", "success")
        self.append_terminal("Type commands in the input below (e.g., cd sdcard, ls).\nType 'exit' to quit.\n", "sys")
        self.append_terminal("======================================================\n", "sys")
        # Show Exit Shell button when entering shell mode
        self.btn_exit_shell.pack(side=tk.LEFT, padx=2, before=self.btn_file)
        self.entry_cmd.focus()

    def exit_shell_mode(self, event=None):
        if self.in_adb_shell:
            self.in_adb_shell = False
            self.prompt_text.set(self.default_prompt)
            self.append_terminal("\n🚪 Exited ADB Shell.\n", "sys")
            # Hide the Exit Shell button again
            self.btn_exit_shell.pack_forget()

    def change_android_directory(self, target_dir):
        """Verify and change Android directory state"""
        self.append_terminal(f"\n{self.prompt_text.get()} cd {target_dir}\n", "cmd")
        
        def task():
            try:
                si = self.get_startupinfo()
                cf = self.get_creationflags()
                # Execute 'cd' then 'pwd' to ensure path exists and get absolute path
                test_cmd = f'adb shell "cd \'{self.android_cwd}\' && cd \'{target_dir}\' && pwd"'
                res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, startupinfo=si, creationflags=cf)
                
                out = res.stdout.strip()
                err = res.stderr.strip()
                
                # Check if directory change failed
                if res.returncode != 0 or "can't cd" in out or "No such file" in out or "Not a directory" in out or "not found" in err:
                    error_msg = err if err else out
                    if not error_msg:
                        error_msg = f"sh: cd: {target_dir}: No such file or directory"
                    self.root.after(0, self.append_terminal, f"{error_msg}\n", "err")
                else:
                    # Successfully changed, update prompt
                    self.android_cwd = out.split('\n')[-1].strip() # Get last line from pwd
                    new_prompt = f"shell@{self.device_codename}:{self.android_cwd}$"
                    self.root.after(0, self.prompt_text.set, new_prompt)
            except Exception as e:
                self.root.after(0, self.append_terminal, f"Error: {str(e)}\n", "err")
                
        threading.Thread(target=task, daemon=True).start()

    def start_scrcpy(self, cmd="scrcpy"):
        if not self.check_dependency("scrcpy"):
            self.prompt_and_install("Scrcpy (Screen Mirroring)", "Genymobile.scrcpy")
            return
            
        # --- AUTO TERMINATE PREVIOUS SCRCPY ---
        self.append_terminal("Terminating previous Scrcpy instances (if any)...\n", "sys")
        try:
            if os.name == 'nt':
                # Silently kill scrcpy.exe process on Windows
                subprocess.call(['taskkill', '/F', '/IM', 'scrcpy.exe'], 
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
            else:
                subprocess.call(['pkill', 'scrcpy'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        # --------------------------------------
            
        self.append_terminal(f"Starting Scrcpy: {cmd}...\n", "sys")
        self.run_command_async(cmd)

    def on_cmd_enter(self, event):
        cmd = self.entry_cmd.get().strip()
        if not cmd:
            return

        self.entry_cmd.delete(0, tk.END)

        if cmd.lower() in ["clear", "cls"]:
            self.clear_terminal()
            return

        if not self.in_adb_shell and cmd.lower().startswith("cd "):
            try:
                new_dir = cmd[3:].strip()
                os.chdir(new_dir)
                self.default_prompt = self.get_display_prompt()
                self.prompt_text.set(self.default_prompt)
            except Exception as e:
                self.append_terminal(f"The system cannot find the path specified: {str(e)}\n", "err")
            return

        if self.in_adb_shell:
            if cmd.lower() == "exit":
                self.exit_shell_mode()
            elif cmd.startswith("cd "):
                # Handle cd command inside android shell
                self.change_android_directory(cmd[3:].strip())
            elif cmd == "cd":
                # If only 'cd' is typed, go back to root (like Linux/Mac)
                self.change_android_directory("/")
            else:
                # Modify command to always execute inside current Android directory
                real_cmd = f'adb shell "cd \'{self.android_cwd}\' && {cmd}"'
                self.run_command_async(real_cmd, show_cmd=True, display_cmd=cmd)
        else:
            if cmd.lower() == "adb shell":
                self.enter_shell_mode()
            elif cmd.lower().startswith("scrcpy"):
                self.start_scrcpy(cmd)
            else:
                self.run_command_async(cmd)

    def run_command_async(self, cmd, show_cmd=True, display_cmd=None):
        if show_cmd:
            # Show original command typed by user (e.g. 'ls'), not background command ('adb shell cd ... && ls')
            cmd_str = display_cmd if display_cmd else (cmd if isinstance(cmd, str) else " ".join(cmd))
            self.append_terminal(f"\n{self.prompt_text.get()} {cmd_str}\n", "cmd")
            
        threading.Thread(target=self._exec_cmd, args=(cmd,), daemon=True).start()

    def _exec_cmd(self, cmd):
        try:
            use_shell = isinstance(cmd, str)
            process = subprocess.Popen(cmd, shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace', bufsize=1, startupinfo=self.get_startupinfo(), creationflags=self.get_creationflags())
            
            self.active_processes.append(process)
            self.root.after(0, self.update_stop_button)

            full_output = []
            for line in iter(process.stdout.readline, ''):
                full_output.append(line)
                self.root.after(0, self._process_output_line, line)
                
            process.stdout.close()
            process.wait()

            if process in self.active_processes:
                self.active_processes.remove(process)
            self.root.after(0, self.update_stop_button)

            cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
            if "adb devices" in cmd_str and not "adb shell" in cmd_str:
                self.root.after(0, self._update_device_status, "".join(full_output), False)
            elif "fastboot devices" in cmd_str:
                self.root.after(0, self._update_device_status, "".join(full_output), True)

        except Exception as e:
            self.root.after(0, self.append_terminal, f"Error executing command: {str(e)}\n", "err")

    def _process_output_line(self, line):
        lower_line = line.lower()
        if "error: no devices/emulators found" in lower_line or "error: device offline" in lower_line or "error: device not found" in lower_line:
            self.append_terminal(line, "err")
            if self.in_adb_shell:
                self.exit_shell_mode()
                self.append_terminal("[!] Device disconnected. Automatically exited shell mode.\n", "err")
                self.root.after(0, lambda: self.lbl_status.config(text="Disconnected", fg=self.colors["text_muted"]))
                self.root.after(0, lambda: self.lbl_status_dot.config(fg="gray"))
                self.root.after(0, lambda: self.lbl_device_id.config(text=""))
        elif "daemon" in lower_line or "connected" in lower_line or "scrcpy" in lower_line or "info:" in lower_line:
            self.append_terminal(line, "sys")
        else:
            self.append_terminal(line, "out")

    def _update_device_status(self, stdout, is_fastboot=False):
        lines = stdout.strip().split('\n')
        devices = []
        
        if is_fastboot:
            for line in lines:
                if 'fastboot' in line and not 'devices' in line:
                    parts = line.split()
                    if parts:
                        devices.append(parts[0])
            
            if devices:
                self.lbl_status_dot.config(fg=self.colors["term_blue"])
                self.lbl_status.config(text="Fastboot Mode", fg=self.colors["text_light"])
                self.lbl_device_id.config(text=f"ID: {devices[0]}")
            else:
                self.lbl_status_dot.config(fg="gray")
                self.lbl_status.config(text="Disconnected", fg=self.colors["text_muted"])
                self.lbl_device_id.config(text="")
        else:
            for line in lines[1:]:
                if 'device' in line and not 'devices' in line:
                    dev_id = line.split('\t')[0]
                    devices.append(dev_id)
            
            if devices:
                self.lbl_status_dot.config(fg=self.colors["term_green"])
                self.lbl_status.config(text="Connected (ADB)", fg=self.colors["text_light"])
                self.lbl_device_id.config(text=f"ID: {devices[0]}")
                threading.Thread(target=self._fetch_codename_async, args=(devices[0],), daemon=True).start()
            else:
                self.lbl_status_dot.config(fg="gray")
                self.lbl_status.config(text="Disconnected", fg=self.colors["text_muted"])
                self.lbl_device_id.config(text="")
                self.device_codename = "android" 
                if self.in_adb_shell:
                    self.exit_shell_mode()
                    self.append_terminal("[!] Device disconnected. Automatically exited shell mode.\n", "err")

    def browse_file(self):
        filepath = filedialog.askopenfilename(title="Select File to Push")
        if filepath:
            self.selected_push_file = filepath
            filename = os.path.basename(filepath)
            display_name = (filename[:30] + '...') if len(filename) > 33 else filename
            self.lbl_push_file.config(text=display_name, fg=self.colors["term_blue"])

    def browse_folder(self):
        folderpath = filedialog.askdirectory(title="Select Destination Folder for Pull")
        if folderpath:
            self.selected_pull_folder = folderpath
            foldername = os.path.basename(folderpath) or folderpath
            display_name = (foldername[:25] + '...') if len(foldername) > 28 else foldername
            self.lbl_pull_dest.config(text=f"Save to: {display_name}", fg=self.colors["term_blue"])

    def execute_push(self):
        if not self.selected_push_file:
            messagebox.showwarning("Warning", "Select a local file on your PC first!")
            return
        
        dest = self.entry_push_dest.get().strip()
        cmd = f'adb push "{self.selected_push_file}" "{dest}"'
        self.run_command_async(cmd)

    def execute_pull(self):
        src = self.entry_pull_src.get().strip()
        if not src:
            messagebox.showwarning("Warning", "Enter the source path from Android!")
            return
        
        cmd = f'adb pull "{src}" "{self.selected_pull_folder}"'
        self.run_command_async(cmd)

# ======= SAFETY GUARD FOR INFINITE LOOP (FORK BOMB) =======
if __name__ == "__main__":
    # Check current executable file name
    exe_name = os.path.basename(sys.executable).lower()
    
    # Prevent users from using 'adb.exe', 'fastboot.exe', or 'scrcpy.exe'
    if exe_name in ["adb.exe", "fastboot.exe", "scrcpy.exe"]:
        import ctypes
        error_msg = (
            "CRITICAL ERROR: Please rename your executable file.\n\n"
            "Do NOT name this application 'adb.exe', 'fastboot.exe', or 'scrcpy.exe'. "
            "This conflicts with the actual Android SDK tools and causes an infinite loop (Fork Bomb)!\n\n"
            "Please rename it to something like 'ADB_Tools.exe'."
        )
        # Show native Windows error pop-up without fully initializing Tkinter
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Fatal Configuration Error", 0x10)
        sys.exit(1)
        
    root = tk.Tk()
    app = ADBDesktopApp(root)
    root.mainloop()