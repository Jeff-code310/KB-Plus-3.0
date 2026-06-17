import logging
import os
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox as messagebox

from config import load_config, save_config, get_valid_scopes, detect_local_ai_services
from constants import AI_CONFIGS, COLORS


class SettingsWindow:
    def __init__(self, parent: tk.Tk, config: dict, ai_provider: str, api_key: str,
                 available_services: list[dict], on_save: callable):
        self._parent = parent
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key
        self._available_services = available_services
        self._on_save = on_save

        self._win = tk.Toplevel(parent)
        self._win.title("搜索路径设置")
        self._win.geometry("600x650")
        self._win.minsize(500, 500)
        self._win.configure(bg="white")
        self._win.resizable(True, True)

        self._ai_service_var = tk.StringVar(value=self._ai_provider)
        self._api_key_var = tk.StringVar(value=self._api_key)
        self._local_path_var = tk.StringVar(
            value=self._config.get("kb_local_path", "")
        )
        self._public_path_var = tk.StringVar(
            value=self._config.get("kb_nas_path", "")
        )
        self._ai_frame: tk.Frame | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        self._build_ai_section()
        self._build_api_key_section()
        self._build_path_section()
        self._build_buttons()

    def _build_ai_section(self) -> None:
        tk.Label(
            self._win, text="AI服务设置:",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white", fg="#1E293B",
        ).pack(anchor="w", padx=20, pady=(20, 5))

        self._ai_frame = tk.Frame(self._win, bg="white")
        self._ai_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            self._ai_frame, text="选择AI服务:",
            font=("Microsoft YaHei UI", 10), bg="white",
        ).pack(anchor="w")

        self._create_ai_radios()

        ollama_btn_frame = tk.Frame(self._win, bg="white")
        ollama_btn_frame.pack(fill="x", padx=20, pady=(5, 10))
        tk.Button(
            ollama_btn_frame,
            text="\U0001F4BE 安装 Ollama",
            font=("Microsoft YaHei UI", 9), bg="#10B981", fg="white",
            bd=0, padx=15, pady=5, cursor="hand2",
            command=self._install_ollama,
        ).pack(anchor="w")

    def _create_ai_radios(self) -> None:
        if self._ai_frame:
            for widget in self._ai_frame.winfo_children():
                widget.destroy()

        available_ids = [s["id"] for s in self._available_services]
        for service_id, conf in AI_CONFIGS.items():
            provider_frame = tk.Frame(self._ai_frame, bg="white")
            provider_frame.pack(fill="x", padx=20, pady=2)

            is_available = service_id in available_ids
            need_key = conf.get("need_key")
            state = "normal" if (is_available or need_key) else "disabled"
            if need_key:
                text = conf["name"]
            elif is_available:
                text = f"{conf['name']} (已检测)"
            else:
                text = f"{conf['name']} (未安装)"
            tk.Radiobutton(
                provider_frame, text=text,
                variable=self._ai_service_var,
                value=service_id, state=state, bg="white",
            ).pack(side="left")

            tk.Button(
                provider_frame, text="\u2699 配置",
                font=("Microsoft YaHei UI", 8),
                bg="#E2E8F0", fg="#475569",
                bd=1, relief="solid", cursor="hand2",
                padx=6, pady=1,
                command=lambda sid=service_id: self._edit_provider_config(sid),
            ).pack(side="right", padx=(8, 0))

    def _edit_provider_config(self, provider_id: str) -> None:
        sub = tk.Toplevel(self._win)
        sub.title(f"配置 - {AI_CONFIGS[provider_id]['name']}")
        sub.geometry("500x250")
        sub.configure(bg="white")
        sub.resizable(False, False)

        custom_config = self._config.get("ai_custom_config", {}).get(provider_id, {})
        default_conf = AI_CONFIGS[provider_id]

        api_url_var = tk.StringVar(value=custom_config.get("api_url", default_conf["api_url"]))
        model_var = tk.StringVar(value=custom_config.get("model", default_conf["model"]))

        tk.Label(sub, text="API 接口地址:",
                 font=("Microsoft YaHei UI", 10), bg="white",
                 anchor="w").pack(fill="x", padx=20, pady=(20, 5))
        tk.Entry(sub, textvariable=api_url_var,
                 font=("Microsoft YaHei UI", 10)).pack(fill="x", padx=20)

        tk.Label(sub, text="模型名称:",
                 font=("Microsoft YaHei UI", 10), bg="white",
                 anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        tk.Entry(sub, textvariable=model_var,
                 font=("Microsoft YaHei UI", 10)).pack(fill="x", padx=20)

        tk.Label(sub,
                 text="\u24D8 修改后需要保存设置才能生效",
                 font=("Microsoft YaHei UI", 9), fg="#94A3B8", bg="white",
                 anchor="w").pack(fill="x", padx=20, pady=(10, 0))

        btn_frame = tk.Frame(sub, bg="white")
        btn_frame.pack(fill="x", padx=20, pady=(15, 0))

        def do_save():
            if "ai_custom_config" not in self._config:
                self._config["ai_custom_config"] = {}
            self._config["ai_custom_config"][provider_id] = {
                "api_url": api_url_var.get().strip(),
                "model": model_var.get().strip(),
            }
            sub.destroy()

        def do_reset():
            api_url_var.set(default_conf["api_url"])
            model_var.set(default_conf["model"])

        tk.Button(btn_frame, text="保存",
                  font=("Microsoft YaHei UI", 10, "bold"),
                  bg=COLORS["primary"], fg="white",
                  bd=0, padx=20, pady=4, cursor="hand2",
                  command=do_save).pack(side="right", padx=(5, 0))
        tk.Button(btn_frame, text="恢复默认",
                  font=("Microsoft YaHei UI", 10),
                  bg="#E2E8F0", fg="#475569",
                  bd=0, padx=16, pady=4, cursor="hand2",
                  command=do_reset).pack(side="right", padx=(5, 0))
        tk.Button(btn_frame, text="取消",
                  font=("Microsoft YaHei UI", 10),
                  bg="#64748B", fg="white",
                  bd=0, padx=16, pady=4, cursor="hand2",
                  command=sub.destroy).pack(side="right")

    def refresh_ai_ui(self, available_services: list[dict]) -> None:
        self._available_services = available_services
        self._create_ai_radios()
        logging.info(f"刷新AI服务UI: 可用服务={[s['id'] for s in self._available_services]}")

    def _build_api_key_section(self) -> None:
        api_frame = tk.Frame(self._win, bg="white")
        api_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(
            api_frame, text="API Key（云端服务需要）:",
            font=("Microsoft YaHei UI", 10), bg="white",
        ).pack(anchor="w")
        tk.Entry(
            api_frame, textvariable=self._api_key_var,
            font=("Microsoft YaHei UI", 10), width=50, show="*",
        ).pack(fill="x", pady=5)

    def _build_path_section(self) -> None:
        tk.Label(
            self._win, text="本地文件夹:",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white", fg="#1E293B",
        ).pack(anchor="w", padx=20, pady=(20, 5))

        local_frame = tk.Frame(self._win, bg="white")
        local_frame.pack(fill="x", padx=20, pady=5)
        local_entry = tk.Entry(
            local_frame, textvariable=self._local_path_var,
            font=("Microsoft YaHei UI", 10), width=50,
        )
        local_entry.pack(side="left", fill="x", expand=True)
        local_entry.bind("<FocusOut>", lambda e: self._auto_save())
        local_entry.bind("<Return>", lambda e: self._auto_save())
        tk.Button(
            local_frame, text="浏览", font=("Microsoft YaHei UI", 9),
            bg="#0EA5E9", fg="white", bd=0, padx=15, pady=3,
            cursor="hand2",
            command=lambda: self._browse_path(self._local_path_var),
        ).pack(side="left", padx=(10, 0))

        tk.Label(
            self._win, text="NAS网盘路径:",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white", fg="#1E293B",
        ).pack(anchor="w", padx=20, pady=(20, 5))

        tk.Label(
            self._win, text="建议填写具体子目录（如 Z:\\知识库文件），避免填整个盘符（Z:\\）以免扫描缓慢",
            font=("Microsoft YaHei UI", 9),
            bg="white", fg="#EF4444",
            wraplength=520, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 5))

        public_frame = tk.Frame(self._win, bg="white")
        public_frame.pack(fill="x", padx=20, pady=5)
        public_entry = tk.Entry(
            public_frame, textvariable=self._public_path_var,
            font=("Microsoft YaHei UI", 10), width=50,
        )
        public_entry.pack(side="left", fill="x", expand=True)
        public_entry.bind("<FocusOut>", lambda e: self._auto_save())
        public_entry.bind("<Return>", lambda e: self._auto_save())
        tk.Button(
            public_frame, text="浏览", font=("Microsoft YaHei UI", 9),
            bg="#0EA5E9", fg="white", bd=0, padx=15, pady=3,
            cursor="hand2",
            command=lambda: self._browse_path(self._public_path_var),
        ).pack(side="left", padx=(10, 0))

    def _build_buttons(self) -> None:
        btn_frame = tk.Frame(self._win, bg="white")
        btn_frame.pack(fill="x", padx=20, pady=20)
        tk.Button(
            btn_frame, text="保存", font=("Microsoft YaHei UI", 11, "bold"),
            bg="#0EA5E9", fg="white", bd=0, padx=30, pady=8,
            cursor="hand2", command=self._save,
        ).pack(side="right", padx=5)
        tk.Button(
            btn_frame, text="取消", font=("Microsoft YaHei UI", 11),
            bg="#64748B", fg="white", bd=0, padx=30, pady=8,
            cursor="hand2", command=self._win.destroy,
        ).pack(side="right", padx=5)

    def _browse_path(self, string_var: tk.StringVar) -> None:
        try:
            path = tk.filedialog.askdirectory(title="选择搜索目录", mustexist=True)
            if path:
                string_var.set(path)
                logging.info(f"用户选择了目录: {path}")
        except Exception as e:
            logging.error(f"浏览目录失败: {e}")
            try:
                from tkinter import simpledialog
                path = simpledialog.askstring(
                    "输入目录", "请输入完整路径:\n(例如: C:\\Users\\Administrator\\Desktop)"
                )
                if path and os.path.isdir(path):
                    string_var.set(path)
                    logging.info(f"用户手动输入了目录: {path}")
                elif path:
                    messagebox.showerror("错误", f"目录不存在: {path}")
            except Exception as e2:
                logging.error(f"备用输入框也失败: {e2}")

    def _auto_save(self) -> None:
        try:
            self._config["ai_provider"] = self._ai_service_var.get()
            self._config["api_key"] = self._api_key_var.get()
            self._config["kb_local_path"] = self._local_path_var.get()
            self._config["kb_nas_path"] = self._public_path_var.get()

            if save_config(self._config):
                logging.info("设置已自动保存")
            else:
                logging.error("自动保存失败")
        except Exception as e:
            logging.error(f"自动保存出错: {e}")

    def _save(self) -> None:
        self._config["ai_provider"] = self._ai_service_var.get()
        self._config["api_key"] = self._api_key_var.get()
        self._config["kb_local_path"] = self._local_path_var.get()
        self._config["kb_nas_path"] = self._public_path_var.get()

        if save_config(self._config):
            self._on_save(
                self._config,
                self._config["ai_provider"],
                self._config["api_key"],
            )
            messagebox.showinfo("成功", "设置已保存！")
            self._win.destroy()
        else:
            messagebox.showerror("错误", "保存失败，请检查权限")

    def _install_ollama(self) -> None:
        import subprocess
        import tempfile
        import requests

        try:
            progress_win = tk.Toplevel(self._parent)
            progress_win.title("安装Ollama")
            progress_win.geometry("400x150")
            progress_win.configure(bg="white")
            progress_win.resizable(False, False)

            progress_label = tk.Label(
                progress_win, text="[1/4] 准备下载...",
                font=("Microsoft YaHei UI", 10), bg="white",
            )
            progress_label.pack(pady=20)

            progress_label.config(text="[1/4] 下载Ollama安装包...")
            progress_win.update()

            ollama_url = "https://ollama.com/download/OllamaSetup.exe"
            ollama_installer = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")

            response = requests.get(ollama_url, stream=True, timeout=300)
            with open(ollama_installer, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            progress_label.config(text="[2/4] 安装Ollama...")
            progress_win.update()

            subprocess.run([ollama_installer, "/S"], check=True)
            import time
            time.sleep(5)

            progress_label.config(text="[3/4] 下载AI模型（约2GB，请耐心等待）...")
            progress_win.update()

            subprocess.run(["ollama", "pull", "qwen2.5:3b"], check=True)

            progress_label.config(text="[4/4] 安装完成！")
            messagebox.showinfo(
                "安装完成",
                "Ollama及AI模型已安装完成！\n\n现在您可以使用AI智能问答功能了。",
            )
            progress_win.destroy()

            self._available_services = detect_local_ai_services()
            self.refresh_ai_ui(self._available_services)

        except Exception as e:
            messagebox.showerror(
                "安装失败",
                f"自动安装失败：{str(e)}\n\n请手动安装Ollama：https://ollama.com",
            )
            if "progress_win" in locals():
                progress_win.destroy()