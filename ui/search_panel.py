import logging
import os
import threading
import time
import tkinter as tk

from constants import COLORS, SUGGESTIONS, N_KB
from utils.helpers import get_file_icon, format_file_size, is_text_file, read_file_chunk
from services.file_searcher import FileSearcher


SCOPE_OPTIONS = ["本地知识库", "NAS网盘", "全部搜索"]


class SearchPanel:
    def __init__(self, parent: tk.Frame, open_file_callback: callable,
                 open_folder_callback: callable):
        self._parent = parent
        self._open_file_callback = open_file_callback
        self._open_folder_callback = open_folder_callback
        self._searcher = FileSearcher()

        self._search_results: list[dict] = []
        self._is_searching: bool = False
        self._search_cancelled: bool = False
        self._cache_valid: bool = False
        self._file_cache: dict[str, list[tuple[str, str]]] = {}

        self.search_var = tk.StringVar()
        self.content_search_var = tk.BooleanVar(value=False)
        self.scope_var = tk.StringVar(value=SCOPE_OPTIONS[0])

        self.search_entry: tk.Entry | None = None
        self.search_btn: tk.Button | None = None
        self.result_listbox: tk.Listbox | None = None
        self.result_count: tk.Label | None = None
        self.scope_label: tk.Label | None = None
        self.detail_label: tk.Label | None = None
        self.suggestion_text: tk.Label | None = None
        self.open_btn: tk.Button | None = None

        self._frame = tk.Frame(parent, bg=COLORS["bg"])
        self._build_search_bar()
        self._build_content_area()

    @property
    def frame(self) -> tk.Frame:
        return self._frame

    def invalidate_cache(self) -> None:
        self._cache_valid = False
        self._file_cache.clear()
        self._searcher.invalidate_cache()

    def _build_search_bar(self) -> None:
        sa = tk.Frame(self._frame, bg=COLORS["bg"], pady=20)
        sa.pack(fill=tk.X, padx=30)

        sc = tk.Frame(sa, bg="white")
        sc.pack(fill=tk.X)

        tk.Label(
            sc, text="\U0001F50D",
            font=("Segoe UI Emoji", 18), bg="white",
        ).pack(side=tk.LEFT, padx=(20, 10), pady=15)

        self.search_entry = tk.Entry(
            sc, textvariable=self.search_var,
            font=("Microsoft YaHei UI", 16),
            bg=COLORS["search_bg"], fg=COLORS["text"],
            bd=0, relief="flat",
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=15)
        self.search_entry.insert(0, "输入关键词搜索文件...")
        self.search_entry.config(fg=COLORS["text_light"])
        self.search_entry.bind("<Return>", lambda e: self.search_files())
        self.search_entry.bind("<FocusIn>", self._on_search_focus)
        self.search_entry.bind("<FocusOut>", self._on_search_blur)

        scope_frame = tk.Frame(sc, bg="white")
        scope_frame.pack(side=tk.RIGHT, padx=(0, 5), pady=12)
        tk.Label(
            scope_frame, text="\U0001F4E1",
            font=("Segoe UI Emoji", 12), bg="white",
        ).pack(side=tk.LEFT)
        tk.OptionMenu(
            scope_frame, self.scope_var, *SCOPE_OPTIONS,
        ).pack(side=tk.LEFT)
        # 美化 OptionMenu
        for child in scope_frame.winfo_children():
            if isinstance(child, tk.Menubutton):
                child.config(
                    font=("Microsoft YaHei UI", 10),
                    bg="white", fg=COLORS["text"],
                    bd=1, relief="solid",
                    padx=8, pady=2,
                    highlightthickness=0,
                )

        self.search_btn = tk.Button(
            sc, text="搜索",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=COLORS["primary"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            padx=30, pady=10,
            command=self._on_search_btn_click,
        )
        self.search_btn.pack(side=tk.RIGHT, padx=(0, 5), pady=12)

        self.content_search_cb = tk.Checkbutton(
            sc, text="含内容", variable=self.content_search_var,
            font=("Microsoft YaHei UI", 10),
            bg="white", fg=COLORS["text"],
            activebackground="white",
            selectcolor=COLORS["search_bg"], bd=0,
        )
        self.content_search_cb.pack(side=tk.RIGHT, padx=(5, 0), pady=12)

    def _build_content_area(self) -> None:
        ct = tk.Frame(self._frame, bg=COLORS["bg"])
        ct.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))

        self._build_left_panel(ct)
        self._build_right_panel(ct)

    def _build_left_panel(self, parent: tk.Frame) -> None:
        lc = tk.Frame(parent, bg="white")
        lc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        self._build_result_header(lc)
        self._build_result_list(lc)
        self._build_detail_bar(lc)

    def _build_result_header(self, parent: tk.Frame) -> None:
        rh = tk.Frame(parent, bg="white")
        rh.pack(fill=tk.X, pady=(15, 10), padx=20)

        self.result_title = tk.Label(
            rh, text="\U0001F4CB 搜索结果",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg=COLORS["text"], bg="white",
        )
        self.result_title.pack(side=tk.LEFT)

        self.scope_label = tk.Label(
            rh, text="",
            font=("Microsoft YaHei UI", 10),
            fg=COLORS["text_light"], bg="white",
        )
        self.scope_label.pack(side=tk.LEFT, padx=(10, 0))

        self.result_count = tk.Label(
            rh, text="0 个文件",
            font=("Microsoft YaHei UI", 11),
            fg=COLORS["text_light"], bg="white",
        )
        self.result_count.pack(side=tk.RIGHT)

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=20)

    def _build_result_list(self, parent: tk.Frame) -> None:
        lc2 = tk.Frame(parent, bg="white")
        lc2.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 15))

        sb = tk.Scrollbar(lc2)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.result_listbox = tk.Listbox(
            lc2,
            font=("Microsoft YaHei UI", 11),
            bg="white", fg=COLORS["text"],
            bd=0, relief="flat", highlightthickness=0,
            selectbackground=COLORS["primary"],
            selectforeground="white",
            selectborderwidth=0, activestyle="none",
            yscrollcommand=sb.set,
        )
        self.result_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.result_listbox.yview)

        self.result_listbox.bind("<Double-Button-1>", lambda e: self._open_file_callback())
        self.result_listbox.bind("<<ListboxSelect>>", self._on_result_select)

        self._ctx_menu = tk.Menu(parent, tearoff=0, font=("Microsoft YaHei UI", 10))
        self._ctx_menu.add_command(label="复制路径", command=self._ctx_copy_path)
        self._ctx_menu.add_command(label="打开所在文件夹", command=self._ctx_open_folder)
        self._ctx_menu.add_command(label="打开文件", command=self._open_file_callback)
        self.result_listbox.bind("<Button-3>", self._show_ctx_menu)

    def _build_detail_bar(self, parent: tk.Frame) -> None:
        self.detail_frame = tk.Frame(parent, bg=COLORS["search_bg"], height=60)
        self.detail_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.detail_label = tk.Label(
            self.detail_frame, text="",
            font=("Microsoft YaHei UI", 10),
            fg=COLORS["text_light"], bg=COLORS["search_bg"],
            wraplength=600, justify="left", anchor="w",
        )
        self.detail_label.pack(fill=tk.X, padx=10, pady=8)

    def _build_right_panel(self, parent: tk.Frame) -> None:
        from datetime import datetime

        rc = tk.Frame(parent, bg="white", width=300)
        rc.pack(side=tk.RIGHT, fill=tk.BOTH)
        rc.pack_propagate(False)

        tk.Frame(rc, bg=COLORS["secondary"], height=50).pack(fill=tk.X)
        tk.Label(
            rc, text="\U0001F4A1 智能建议",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg="white", bg=COLORS["secondary"],
        ).place(x=20, y=12)

        self.suggestion_text = tk.Label(
            rc,
            text="\U0001F4A1 输入关键词开始搜索\n\n支持搜索所有文件类型：\n• Word/Excel 文档\n• PDF 文件\n• 图片文件",
            font=("Microsoft YaHei UI", 11),
            fg=COLORS["text_light"], bg="white",
            wraplength=250, justify="left", anchor="nw",
        )
        self.suggestion_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        bf = tk.Frame(rc, bg="white", pady=15)
        bf.pack(fill=tk.X, side=tk.BOTTOM, padx=20)

        self.open_btn = tk.Button(
            bf, text="\U0001F4C2 打开文件",
            font=("Microsoft YaHei UI", 11),
            bg=COLORS["primary"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            pady=12, state="disabled",
            command=self._open_file_callback,
        )
        self.open_btn.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            bf, text="\U0001F4C1 打开文件夹",
            font=("Microsoft YaHei UI", 11),
            bg=COLORS["text_light"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            pady=12,
            command=self._open_folder_callback,
        ).pack(fill=tk.X)

    def _on_search_focus(self, event: tk.Event) -> None:
        if self.search_entry and self.search_entry.get() == "输入关键词搜索文件...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=COLORS["text"])

    def _on_search_blur(self, event: tk.Event) -> None:
        if self.search_entry and not self.search_entry.get():
            self.search_entry.insert(0, "输入关键词搜索文件...")
            self.search_entry.config(fg=COLORS["text_light"])

    def _on_search_btn_click(self) -> None:
        if self._is_searching:
            self._search_cancelled = True
            self._is_searching = False
            if self.search_btn:
                self.search_btn.config(text="搜索", bg=COLORS["primary"])
            if self.result_count:
                self.result_count.config(text=f"{len(self._search_results)} 个文件 (已中止)")
        else:
            self.search_files()

    def search_files(self) -> None:
        keyword = self.search_var.get().strip()
        if keyword in ("输入关键词搜索文件...", "") or keyword == "":
            return

        self._search_cancelled = True
        if self.result_listbox:
            self.result_listbox.delete(0, tk.END)
        self._search_results = []
        if self.detail_label:
            self.detail_label.config(text="")
        if self.result_count:
            self.result_count.config(text="正在搜索...")
        if self.suggestion_text:
            self.suggestion_text.config(
                text="\U0001F50D 正在搜索目录中，请稍候...",
                fg=COLORS["text"],
            )

        from config import load_config
        config = load_config()
        local_path = config.get("kb_local_path", "")
        nas_path = config.get("kb_nas_path", "")

        scope_choice = self.scope_var.get()
        all_paths: list[str] = []
        if scope_choice == "NAS网盘":
            if nas_path and os.path.exists(nas_path):
                all_paths.append(nas_path)
        elif scope_choice == "全部搜索":
            if local_path and os.path.exists(local_path):
                all_paths.append(local_path)
            if nas_path and os.path.exists(nas_path):
                all_paths.append(nas_path)
        else:
            if local_path and os.path.exists(local_path):
                all_paths.append(local_path)

        if not all_paths:
            from config import get_valid_scopes
            fallback = get_valid_scopes(config)
            if fallback:
                all_paths = [p for p in fallback[0].get("paths", []) if p]
            if not all_paths:
                if self.result_count:
                    self.result_count.config(text="未配置可用路径")
                return

        scope_label_text = f"[{scope_choice}" + (f" · {len(all_paths)}目录" if len(all_paths) > 1 else "") + "]"
        if self.scope_label:
            self.scope_label.config(text=scope_label_text)
        self._is_searching = True
        if self.search_btn:
            self.search_btn.config(text="停止", bg="#EF4444")
        self._search_cancelled = False

        threading.Thread(
            target=self._search_thread,
            args=(keyword, scope_choice, all_paths),
            daemon=True,
        ).start()

    def _search_thread(self, keyword: str, scope_name: str,
                       search_paths: list[str]) -> None:
        results: list[dict] = []
        batch_size = 20
        last_update_count = 0
        keyword_lower = keyword.lower()
        search_content = False
        try:
            search_content = self.content_search_var.get()
        except Exception as e:
            logging.error(f"搜索异常: 获取content_search_var失败 {e}")

        logging.info(f"搜索开始 keyword={keyword} paths={search_paths} content={search_content}")

        try:
            for search_path in search_paths:
                if self._search_cancelled:
                    logging.info(f"搜索取消 path={search_path}")
                    break
                if not search_path or not os.path.exists(search_path):
                    logging.warning(f"搜索路径不存在: {search_path}")
                    continue

                logging.info(f"扫描路径: {search_path}")
                path_start = time.time()
                path_timeout = 30.0

                cache_key = search_path
                if self._cache_valid and cache_key in self._file_cache:
                    for filepath, filename in self._file_cache[cache_key]:
                        if self._search_cancelled:
                            break
                        is_match = keyword_lower in filename.lower()
                        if not is_match and search_content:
                            is_match = self._match_content(filepath, keyword_lower)
                        if is_match:
                            icon = get_file_icon(filename)
                            results.append({"filepath": filepath, "filename": filename,
                                            "size": "", "date": "", "icon": icon,
                                            "scope": scope_name, "detail_loaded": False})
                            if len(results) - last_update_count >= batch_size:
                                self._parent.after(0, lambda r=list(results): self._update_results(r, keyword, True))
                                last_update_count = len(results)
                else:
                    file_list: list[tuple[str, str]] = []
                    try:
                        for root, dirs, files in os.walk(search_path):
                            if self._search_cancelled:
                                break
                            if time.time() - path_start > path_timeout:
                                logging.warning(f"搜索路径超时（{path_timeout}秒），已跳过: {search_path}")
                                break
                            dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("$")]
                            for filename in files:
                                if self._search_cancelled:
                                    break
                                filepath = os.path.join(root, filename)
                                file_list.append((filepath, filename))
                                is_match = keyword_lower in filename.lower()
                                if not is_match and search_content:
                                    is_match = self._match_content(filepath, keyword_lower)
                                if is_match:
                                    icon = get_file_icon(filename)
                                    results.append({"filepath": filepath, "filename": filename,
                                                    "size": "", "date": "", "icon": icon,
                                                    "scope": scope_name, "detail_loaded": False})
                                    if len(results) - last_update_count >= batch_size:
                                        self._parent.after(0, lambda r=list(results): self._update_results(r, keyword, True))
                                        last_update_count = len(results)
                    except PermissionError:
                        pass
                    except Exception as e:
                        logging.warning(f"扫描异常 {search_path}: {e}")
                    self._file_cache[cache_key] = file_list

            self._cache_valid = True
            logging.info(f"搜索完成: {len(results)} 个结果 keyword={keyword}")
        except Exception as e:
            logging.error(f"搜索出错: {e}")

        if not self._search_cancelled:
            self._parent.after(0, lambda: self._update_results(results, keyword, False))

    def _match_content(self, filepath: str, keyword_lower: str) -> bool:
        try:
            if not is_text_file(filepath):
                return False
            content = read_file_chunk(filepath, 65536)
            if content is None:
                return False
            return keyword_lower in content.lower()
        except Exception:
            return False

    def _update_results(self, results: list[dict], keyword: str,
                        incremental: bool = False) -> None:
        if not incremental:
            results.sort(key=lambda r: r["filename"].lower())
        self._search_results = results
        if self.result_listbox:
            self.result_listbox.delete(0, tk.END)
            for r in results:
                self.result_listbox.insert(tk.END, f"{r['icon']} {r['filename']}")

        count = len(results)
        if self._is_searching and incremental:
            if count > 0:
                if self.result_count:
                    self.result_count.config(text=f"{count} 个文件 (搜索中...)")
            else:
                if self.result_count:
                    self.result_count.config(text="搜索中...")
        else:
            if self.result_count:
                self.result_count.config(text=f"{count} 个文件")
            self._is_searching = False
            if self.search_btn:
                self.search_btn.config(text="搜索", bg=COLORS["primary"])

        if count > 0 and self.open_btn:
            self.open_btn.config(state="normal", bg=COLORS["primary"])
            if not incremental:
                self._update_suggestions(keyword)
        elif not incremental and self.open_btn:
            self.open_btn.config(state="disabled", bg=COLORS["border"])
            if self.suggestion_text:
                self.suggestion_text.config(
                    text="\u274C 未找到匹配文件\n\n\U0001F4A1 建议：\n• 检查关键词拼写\n• 尝试更简短的关键词",
                    fg="#EF4444",
                )

    def _update_suggestions(self, keyword: str) -> None:
        suggestions: list[str] = []
        for key, values in SUGGESTIONS.items():
            if key.lower() in keyword.lower():
                suggestions.extend(values)
        if not suggestions:
            suggestions = SUGGESTIONS["default"]
        suggestions = list(dict.fromkeys(suggestions))[:6]
        if self.suggestion_text:
            self.suggestion_text.config(
                text=f"\U0001F4CC 基于「{keyword}」的建议：\n\n" + "\n".join(suggestions),
                fg=COLORS["text"],
            )

    def clear_results(self) -> None:
        if self.result_listbox:
            self.result_listbox.delete(0, tk.END)
        self._search_results = []
        if self.result_count:
            self.result_count.config(text="0 个文件")
        if self.scope_label:
            self.scope_label.config(text="")
        if self.detail_label:
            self.detail_label.config(text="")
        if self.open_btn:
            self.open_btn.config(state="disabled", bg=COLORS["border"])
        if self.suggestion_text:
            self.suggestion_text.config(
                text="\U0001F4A1 输入关键词开始搜索\n\n支持搜索所有文件类型：\n• Word/Excel 文档\n• PDF 文件\n• 图片文件",
                fg=COLORS["text_light"],
            )

    def get_current_results(self) -> list[dict]:
        return self._search_results

    def _on_result_select(self, event: tk.Event) -> None:
        if not self.result_listbox:
            return
        selection = self.result_listbox.curselection()
        if selection:
            from datetime import datetime
            result = self._search_results[selection[0]]
            if not result.get("detail_loaded"):
                try:
                    size = os.path.getsize(result["filepath"])
                    mtime = datetime.fromtimestamp(os.path.getmtime(result["filepath"]))
                    result["size"] = format_file_size(size)
                    result["date"] = mtime.strftime("%Y-%m-%d")
                    result["detail_loaded"] = True
                except Exception:
                    result["size"] = "N/A"
                    result["date"] = "N/A"
                    result["detail_loaded"] = True
            if self.detail_label:
                self.detail_label.config(
                    text=f"\U0001F4C8 路径: {result['filepath']}    |    "
                         f"\U0001F4CF 大小: {result['size']}    |    "
                         f"\U0001F4C5 日期: {result['date']}",
                    fg=COLORS["text"],
                )

    def _show_ctx_menu(self, event: tk.Event) -> None:
        if not self.result_listbox:
            return
        sel = self.result_listbox.nearest(event.y)
        self.result_listbox.selection_clear(0, tk.END)
        self.result_listbox.selection_set(sel)
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_copy_path(self) -> None:
        if not self.result_listbox:
            return
        sel = self.result_listbox.curselection()
        if sel:
            path = self._search_results[sel[0]]["filepath"]
            self.result_listbox.clipboard_clear()
            self.result_listbox.clipboard_append(path)

    def _ctx_open_folder(self) -> None:
        if not self.result_listbox:
            return
        sel = self.result_listbox.curselection()
        if sel:
            path = self._search_results[sel[0]]["filepath"]
            try:
                os.startfile(os.path.dirname(path))
            except Exception:
                pass