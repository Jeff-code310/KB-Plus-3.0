import logging
import os
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as messagebox

from config import detect_local_ai_services, load_config
from constants import COLORS, N_KB, N_WEB
from ui.search_panel import SearchPanel
from ui.settings_window import SettingsWindow
from ui.web_panel import WebPanel


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("知识库+")
        self.root.geometry("1150x850")
        self.root.minsize(800, 600)
        self.root.configure(bg=COLORS["bg"])

        self.config = load_config()
        self.ai_provider = self.config.get("ai_provider", "")
        self.api_key = self.config.get("api_key", "")

        self.current_view = "search"
        self.search_tab: tk.Button | None = None
        self.web_tab: tk.Button | None = None

        self.available_services = []

        self._build_header()
        self._build_tabs()

        self.main_container = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.search_panel = SearchPanel(
            self.main_container,
            open_file_callback=self._on_open_file,
            open_folder_callback=self._on_open_folder,
        )
        self.web_panel = WebPanel(
            self.main_container,
            config=self.config,
            ai_provider=self.ai_provider,
            api_key=self.api_key,
        )

        self.search_panel.frame.pack(fill=tk.BOTH, expand=True)
        self._update_tab_styles(self.current_view)

        threading.Thread(target=self._detect_ai_thread, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg="white", height=85)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        left_header = tk.Frame(header, bg="white")
        left_header.pack(side=tk.LEFT, padx=30, pady=15)
        tk.Label(
            left_header, text="\U0001F50D",
            font=("Segoe UI Emoji", 24),
            bg="white", fg=COLORS["primary"],
        ).pack(side=tk.LEFT, padx=(0, 12))

        t = tk.Frame(left_header, bg="white")
        t.pack(side=tk.LEFT, pady=0)
        tk.Label(
            t, text="知识库+",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg="white", fg=COLORS["text"],
        ).pack(anchor="w")
        tk.Label(
            t, text="文件搜索与AI问答助手",
            font=("Microsoft YaHei UI", 10),
            bg="white", fg=COLORS["text_light"],
        ).pack(anchor="w")

        right_header = tk.Frame(header, bg="white")
        right_header.pack(side=tk.RIGHT, padx=30, pady=15)
        tk.Button(
            right_header, text="\u2699\ufe0f 设置",
            font=("Microsoft YaHei UI", 10),
            bg="white", fg=COLORS["text"],
            bd=0, relief="flat", cursor="hand2",
            command=self._open_settings,
        ).pack(side=tk.LEFT, padx=(0, 20))
        tk.Button(
            right_header, text="\u2753 帮助",
            font=("Microsoft YaHei UI", 10),
            bg="white", fg=COLORS["text"],
            bd=0, relief="flat", cursor="hand2",
            command=self._show_help,
        ).pack(side=tk.LEFT)

    def _build_tabs(self) -> None:
        tab_bar = tk.Frame(self.root, bg="white")
        tab_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 0))
        tk.Frame(tab_bar, bg=COLORS["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        self.search_tab = tk.Button(
            tab_bar, text="\U0001F4CB 文件搜索",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white", fg=COLORS["primary"], bd=0,
            relief="flat", cursor="hand2",
            pady=12, padx=25,
            command=lambda: self._switch_view("search"),
        )
        self.search_tab.pack(side=tk.LEFT, padx=(30, 0))

        self.web_tab = tk.Button(
            tab_bar, text="\u2728 AI问答",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white", fg=COLORS["text_light"], bd=0,
            relief="flat", cursor="hand2",
            pady=12, padx=25,
            command=lambda: self._switch_view("web"),
        )
        self.web_tab.pack(side=tk.LEFT, padx=(0, 0))

    def _switch_view(self, view: str) -> None:
        self.current_view = view
        self._update_tab_styles(view)

        if view == "search":
            self.web_panel.frame.pack_forget()
            self.search_panel.frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.search_panel.frame.pack_forget()
            self.web_panel.frame.pack(fill=tk.BOTH, expand=True)

    def _update_tab_styles(self, active: str) -> None:
        active_font = ("Microsoft YaHei UI", 11, "bold")
        if active == "search":
            if self.search_tab:
                self.search_tab.config(fg=COLORS["primary"], font=active_font)
            if self.web_tab:
                self.web_tab.config(fg=COLORS["text_light"],
                                    font=("Microsoft YaHei UI", 11))
        else:
            if self.search_tab:
                self.search_tab.config(fg=COLORS["text_light"],
                                       font=("Microsoft YaHei UI", 11))
            if self.web_tab:
                self.web_tab.config(fg=COLORS["primary"], font=active_font)

    def _detect_ai_thread(self) -> None:
        try:
            services = detect_local_ai_services()
            self.root.after(0, lambda: self._on_ai_detected(services))
        except Exception:
            pass

    def _on_ai_detected(self, services: list) -> None:
        self.available_services = services

    def _on_open_file(self) -> None:
        results = self.search_panel.get_current_results()
        if not results:
            return
        idx = self.search_panel.result_listbox.curselection()
        if not idx:
            return
        filepath = results[idx[0]]["filepath"]
        try:
            if os.name == "nt":
                os.startfile(filepath)
            else:
                subprocess.call(["xdg-open", filepath])
        except Exception as e:
            logging.error(f"打开文件失败: {e}")
            messagebox.showerror("错误", f"无法打开文件：{filepath}")

    def _on_open_folder(self) -> None:
        results = self.search_panel.get_current_results()
        if not results:
            msg = "请在知识库文件目录中浏览"
            kb_path = self.config.get("kb_local_path", "")
            if kb_path and os.path.exists(kb_path):
                try:
                    if os.name == "nt":
                        os.startfile(kb_path)
                    else:
                        subprocess.call(["xdg-open", kb_path])
                except Exception:
                    messagebox.showinfo("文件夹", msg)
            else:
                messagebox.showinfo("提示", msg)
            return
        idx = self.search_panel.result_listbox.curselection()
        if idx:
            filepath = results[idx[0]]["filepath"]
        else:
            filepath = results[0]["filepath"]
        try:
            folder = os.path.dirname(filepath)
            if os.name == "nt":
                os.startfile(folder)
            else:
                subprocess.call(["xdg-open", folder])
        except Exception:
            messagebox.showerror("错误", f"无法打开文件夹：{os.path.dirname(filepath)}")

    def _open_settings(self) -> None:
        SettingsWindow(
            self.root, self.config, self.ai_provider, self.api_key,
            self.available_services, on_save=self._on_settings_saved,
        )

    def _on_settings_saved(self, config: dict, ai_provider: str, api_key: str) -> None:
        self.config = config
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.search_panel.invalidate_cache()
        self.search_panel.clear_results()
        self.web_panel.update_config(self.config, self.ai_provider, self.api_key)

    def _show_help(self) -> None:
        help_text = (
            "=== 知识库+ 使用帮助 ===\n\n"
            "文件搜索：\n"
            "• 在输入框中输入关键词\n"
            "• 点击搜索按钮或按Enter开始搜索\n"
            "• 双击搜索结果打开文件\n"
            "• 勾选『含内容』可搜索文件内容\n\n"
            "AI问答：\n"
            "• 点击『AI问答』标签\n"
            "• 输入问题，系统会结合知识库和网络信息回答\n"
            "• 需要先在设置中选择可用的AI服务\n\n"
            "设置：\n"
            "• 配置本地文件夹和NAS路径\n"
            "• 选择AI服务（Ollama/LM Studio/智谱云端等）\n"
            "• 云端服务需要输入对应的API Key\n\n"
            "提示：\n"
            "• 首次使用推荐安装Ollama\n"
            "• 如搜索不到文件，请检查搜索路径设置\n"
            "• 文件搜索会自动缓存，第二次搜索更快"
        )
        messagebox.showinfo("使用帮助", help_text)

    def _on_close(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()
