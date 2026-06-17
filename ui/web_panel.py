import re
import threading
import tkinter as tk

from constants import COLORS
from services.ai_service import call_ollama, call_openai_compat, call_zhipu_websearch
from services.web_searcher import search_bing
from services.file_searcher import FileSearcher

_conv_counter = 0


def _next_conv_id() -> str:
    global _conv_counter
    _conv_counter += 1
    return f"conv_{_conv_counter}"


def _clean_text(text: str) -> str:
    text = re.sub(r'[*#`_~]', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class WebPanel:
    def __init__(self, parent: tk.Frame, config: dict, ai_provider: str, api_key: str):
        self._parent = parent
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key
        self._searcher = FileSearcher()
        self._is_answering: bool = False
        self._answer_cancelled: bool = False
        self._stream_buffer: str = ""

        self._chat_widget: tk.Text | None = None
        self._loading_running: bool = False
        self._loading_frame: int = 0
        self._loading_pos: str | None = None
        self._ai_start_pos: str | None = None
        self._first_chunk: bool = True

        self.web_var = tk.StringVar()
        self._conversations: dict[str, dict] = {}
        self._active_conv_id: str | None = None

        self._frame = tk.Frame(parent, bg=COLORS["bg"])
        self._build_sidebar()
        self._build_right_panel()

    @property
    def frame(self) -> tk.Frame:
        return self._frame

    def update_config(self, config: dict, ai_provider: str, api_key: str) -> None:
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key

    # ── Sidebar ──────────────────────────────────────

    def _build_sidebar(self) -> None:
        self._sidebar = tk.Frame(self._frame, bg="#F8FAFC", width=180)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        self._sidebar.pack_propagate(False)

        tk.Label(
            self._sidebar, text="\U0001F916 对话列表",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg="#64748B", bg="#F8FAFC",
        ).pack(fill=tk.X, padx=12, pady=(14, 6))

        tk.Button(
            self._sidebar, text="\U00002795 新对话",
            font=("Microsoft YaHei UI", 10),
            bg=COLORS["primary"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            padx=8, pady=4,
            command=self._new_conversation,
        ).pack(fill=tk.X, padx=12, pady=(0, 6))

        self._conv_listbox = tk.Listbox(
            self._sidebar,
            font=("Microsoft YaHei UI", 10),
            bg="#F8FAFC", fg="#334155",
            bd=0, highlightthickness=0,
            selectbackground="#DBEAFE",
            selectforeground="#1E293B",
            activestyle="none",
            exportselection=False,
        )
        self._conv_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._conv_listbox.bind("<<ListboxSelect>>", self._on_conv_select)

    # ── Right panel ──────────────────────────────────

    def _build_right_panel(self) -> None:
        right = tk.Frame(self._frame, bg=COLORS["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_chat_area(right)
        self._build_input_bar(right)

    def _build_chat_area(self, parent: tk.Frame) -> None:
        container = tk.Frame(parent, bg=COLORS["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 0))

        self._canvas = tk.Canvas(
            container, bg=COLORS["bg"],
            highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(
            container, orient="vertical",
            command=self._canvas.yview,
        )
        self._scrollable_frame = tk.Frame(self._canvas, bg=COLORS["bg"])

        self._scrollable_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all"),
            ),
        )
        self._canvas.create_window(
            (0, 0), window=self._scrollable_frame, anchor="nw", tags="inner",
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig("inner", width=e.width - 8),
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_chat_widget()

    def _build_chat_widget(self) -> None:
        self._chat_widget = tk.Text(
            self._scrollable_frame,
            font=("Microsoft YaHei UI", 11),
            bg=COLORS["bg"], fg=COLORS["text"],
            wrap="word", bd=0, relief="flat",
            padx=16, pady=12,
            spacing1=4, spacing3=8,
        )
        self._chat_widget.pack(fill=tk.BOTH, expand=True)

        self._chat_widget.tag_configure("user", justify="right", foreground=COLORS["text"],
                                         font=("Microsoft YaHei UI", 11), spacing3=12,
                                         background=COLORS["bg"])
        self._chat_widget.tag_configure("ai", justify="left", foreground=COLORS["text"],
                                        font=("Microsoft YaHei UI", 11), spacing3=8,
                                        background=COLORS["bg"])
        self._chat_widget.tag_configure("loading", justify="left", foreground="#94A3B8",
                                        font=("Microsoft YaHei UI", 11, "italic"),
                                        background=COLORS["bg"])
        self._chat_widget.tag_configure("ai_icon", justify="left", foreground="#0EA5E9",
                                        font=("Segoe UI Emoji", 10), background=COLORS["bg"])

        self._show_welcome()

    def _show_welcome(self) -> None:
        self._chat_widget.insert("end", "\n\n\n\n\n")
        self._chat_widget.insert("end", "  \U0001F31F\n\n", "loading")
        self._chat_widget.insert("end", "  向你提问\n\n", "ai")
        self._chat_widget.insert("end", "  AI 会结合知识库与联网搜索为你提供专业回答", "loading")
        self._chat_widget.config(state="disabled")

    def _build_input_bar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg="white", height=56)
        bar.pack(fill=tk.X, padx=20, pady=(8, 12))
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg="white")
        inner.pack(fill=tk.BOTH, padx=12, pady=8)

        self.web_entry = tk.Entry(
            inner, textvariable=self.web_var,
            font=("Microsoft YaHei UI", 13),
            bg="#F8FAFC", fg=COLORS["text"],
            bd=0, relief="flat",
        )
        self.web_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        self.web_entry.insert(0, "向 AI 提问...")
        self.web_entry.config(fg="#64748B")
        self.web_entry.bind("<Return>", lambda e: self._answer_question())
        self.web_entry.bind("<FocusIn>", self._on_entry_focus)
        self.web_entry.bind("<FocusOut>", self._on_entry_blur)

        self.send_btn = tk.Button(
            inner, text="\u25B6 发送",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=COLORS["primary"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._on_send_click,
        )
        self.send_btn.pack(side=tk.RIGHT)

    # ── Events ───────────────────────────────────────

    def _on_entry_focus(self, _: tk.Event) -> None:
        if self.web_var.get() == "向 AI 提问...":
            self.web_entry.delete(0, tk.END)
            self.web_entry.config(fg=COLORS["text"])

    def _on_entry_blur(self, _: tk.Event) -> None:
        if not self.web_var.get():
            self.web_entry.insert(0, "向 AI 提问...")
            self.web_entry.config(fg="#64748B")

    def _on_mousewheel(self, event: tk.Event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_send_click(self) -> None:
        if self._is_answering:
            self._answer_cancelled = True
        else:
            self._answer_question()

    # ── Conversation management ───────────────────────

    def _new_conversation(self) -> None:
        if self._is_answering:
            self._answer_cancelled = True
        self._is_answering = False
        self._answer_cancelled = False
        self.send_btn.config(text="\u25B6 发送", bg=COLORS["primary"])
        self._stream_buffer = ""
        self._first_chunk = True
        self._loading_pos = None
        self._ai_start_pos = None

        conv_id = _next_conv_id()
        self._conversations[conv_id] = {
            "title": "新对话",
            "messages": [],
            "history": [],
        }
        self._active_conv_id = conv_id

        self._sync_listbox()
        self._chat_widget.config(state="normal")
        self._chat_widget.delete("1.0", "end")
        self._show_welcome()
        self._chat_widget.config(state="disabled")

    def _on_conv_select(self, _: tk.Event = None) -> None:
        sel = self._conv_listbox.curselection()
        if not sel:
            return
        conv_ids = list(self._conversations.keys())
        idx = sel[0]
        if idx >= len(conv_ids):
            return
        conv_id = conv_ids[idx]
        if conv_id == self._active_conv_id:
            return

        self._save_current_messages()
        self._active_conv_id = conv_id
        self._load_conv_messages(conv_id)

    def _sync_listbox(self) -> None:
        self._conv_listbox.delete(0, tk.END)
        for cid, conv in self._conversations.items():
            title = conv["title"]
            icon = "\U0001F4AC" if cid == self._active_conv_id else "\U0001F4DD"
            self._conv_listbox.insert(tk.END, f"  {icon}  {title}")

    def _save_current_messages(self) -> None:
        if not self._active_conv_id:
            return
        conv = self._conversations.get(self._active_conv_id)
        if conv is None:
            return
        if conv["messages"] and conv["messages"][-1]["role"] == "assistant":
            if self._ai_start_pos:
                text = self._chat_widget.get(self._ai_start_pos, "end-1c")
                conv["messages"][-1]["text"] = text

    def _load_conv_messages(self, conv_id: str) -> None:
        self._first_chunk = True
        self._loading_pos = None
        self._ai_start_pos = None
        conv = self._conversations.get(conv_id)
        if conv is None:
            return

        self._chat_widget.config(state="normal")
        self._chat_widget.delete("1.0", "end")

        if not conv["messages"]:
            self._show_welcome()
            self._chat_widget.config(state="disabled")
            return

        for msg in conv["messages"]:
            role = msg.get("role", "")
            text = msg.get("text", "")
            if role == "user":
                self._chat_widget.insert("end", text + "\n", "user")
            elif role == "assistant":
                if text:
                    self._chat_widget.insert("end", "\U0001F916  ", "ai_icon")
                    self._chat_widget.insert("end", text + "\n", "ai")

        self._chat_widget.config(state="disabled")
        self._auto_scroll()

    # ── Answer flow ───────────────────────────────────

    def _answer_question(self) -> None:
        question = self.web_var.get().strip()
        if question in ("", "向 AI 提问..."):
            return

        self.web_entry.delete(0, tk.END)

        if not self._active_conv_id:
            self._new_conversation()
        elif not self._conversations.get(self._active_conv_id):
            self._new_conversation()

        conv = self._conversations[self._active_conv_id]
        if conv["title"] == "新对话":
            conv["title"] = question[:14] + ("..." if len(question) > 14 else "")
            self._sync_listbox()

        self._is_answering = True
        self._answer_cancelled = False
        self.send_btn.config(text="\u25A0 停止", bg="#EF4444")

        conv["messages"].append({"role": "user", "text": question})

        self._chat_widget.config(state="normal")
        self._chat_widget.delete("1.0", "end")
        for msg in conv["messages"]:
            role = msg.get("role", "")
            text = msg.get("text", "")
            if role == "user":
                self._chat_widget.insert("end", text + "\n", "user")
            elif role == "assistant":
                if text:
                    self._chat_widget.insert("end", "\U0001F916  ", "ai_icon")
                    self._chat_widget.insert("end", text + "\n", "ai")

        self._ai_start_pos = None
        self._first_chunk = True
        self._stream_buffer = ""
        self._insert_loading()
        self._start_loading_animation()

        threading.Thread(target=self._background_flow, args=(question,), daemon=True).start()

    def _insert_loading(self) -> None:
        self._chat_widget.insert("end", "\U0001F916  ", "ai_icon")
        self._loading_pos = self._chat_widget.index("end-1c")
        self._chat_widget.insert("end", "思考中", "loading")
        self._auto_scroll()

    def _start_loading_animation(self) -> None:
        self._loading_running = True
        self._loading_frame = 0
        self._animate_loading()

    def _animate_loading(self) -> None:
        if not self._loading_running or not self._loading_pos:
            return
        frames = ["思考中", "思考中.", "思考中..", "思考中..."]
        self._loading_frame = (self._loading_frame + 1) % 4
        try:
            self._chat_widget.config(state="normal")
            self._chat_widget.delete(self._loading_pos, "end-1c")
            self._chat_widget.insert(self._loading_pos, frames[self._loading_frame], "loading")
            self._chat_widget.config(state="disabled")
        except Exception:
            pass
        self._parent.after(400, self._animate_loading)

    def _stop_loading(self) -> None:
        self._loading_running = False

    def _background_flow(self, question: str) -> None:
        kb_content = ""
        web_results: list[dict] = []
        web_parts: list[str] = []

        def do_kb():
            nonlocal kb_content
            kb_content = self._searcher.search_kb_for_question(question, self._config)

        def do_web():
            nonlocal web_results, web_parts
            web_results = search_bing(question, num_results=3)
            parts = []
            for i, r in enumerate(web_results, 1):
                if r.get("title") and r.get("url"):
                    parts.append(f"[网页{i}] 标题: {r['title']}\n内容摘要: {r.get('description', '')}\n链接: {r['url']}")
            web_parts = parts

        t_kb = threading.Thread(target=do_kb, daemon=True)
        t_web = threading.Thread(target=do_web, daemon=True)
        t_kb.start()
        t_web.start()
        t_kb.join(timeout=8)
        t_web.join(timeout=8)

        web_content = "\n\n".join(web_parts) if web_parts else ""
        self._do_ai_call(question, kb_content, web_content, web_results)

    def _do_ai_call(self, question: str, kb_content: str, web_content: str,
                    web_results: list[dict]) -> None:
        conv = self._conversations.get(self._active_conv_id) if self._active_conv_id else None
        history = conv["history"].copy() if conv and conv["history"] else None

        def stream_callback(raw_text: str) -> None:
            if self._answer_cancelled:
                return
            text = _clean_text(raw_text)
            self._parent.after(20, lambda: self._stream_update(text))

        def ai_call() -> str:
            if self._ai_provider == "ollama":
                return call_ollama(
                    question, kb_content, web_content,
                    stream_callback=stream_callback,
                    cancelled_flag=lambda: self._answer_cancelled,
                    history=history,
                )
            if self._ai_provider == "zhipu_cloud":
                return call_zhipu_websearch(
                    question, kb_content, self._api_key,
                    stream_callback=stream_callback,
                    cancelled_flag=lambda: self._answer_cancelled,
                )
            if self._ai_provider in ("lm_studio", "gpt4all", "deepseek_api"):
                return call_openai_compat(
                    self._ai_provider, question, kb_content, web_content,
                    api_key=self._api_key,
                    stream_callback=stream_callback,
                    cancelled_flag=lambda: self._answer_cancelled,
                    history=history,
                )
            return "请先在设置中选择一个可用的AI服务"

        try:
            final_text = ai_call()
            cleaned = _clean_text(final_text) if final_text else ""
            if cleaned and not self._answer_cancelled:
                self._parent.after(0, lambda: self._finalize_answer(cleaned))
            elif self._answer_cancelled:
                self._parent.after(0, lambda: self._finalize_answer(""))
        except Exception as e:
            self._parent.after(0, lambda: self._finalize_answer(""))

    def _stream_update(self, text: str) -> None:
        try:
            self._chat_widget.config(state="normal")

            if self._first_chunk:
                self._stop_loading()
                if self._loading_pos:
                    self._chat_widget.delete(self._loading_pos, "end-1c")
                    self._ai_start_pos = self._chat_widget.index("end-1c")
                else:
                    self._chat_widget.insert("end", "\U0001F916  ", "ai_icon")
                    self._ai_start_pos = self._chat_widget.index("end-1c")
                self._chat_widget.insert(self._ai_start_pos, text, "ai")
                self._stream_buffer = text
                self._first_chunk = False
            else:
                self._chat_widget.delete(self._ai_start_pos, "end-1c")
                self._chat_widget.insert(self._ai_start_pos, text, "ai")
                self._stream_buffer = text

            self._chat_widget.config(state="disabled")
            self._auto_scroll()
        except Exception:
            pass

    def _finalize_answer(self, text: str) -> None:
        self._is_answering = False
        self.send_btn.config(text="\u25B6 发送", bg=COLORS["primary"])

        self._stop_loading()
        if not text:
            if self._loading_pos:
                try:
                    self._chat_widget.config(state="normal")
                    self._chat_widget.delete(self._loading_pos, "end-1c")
                    self._chat_widget.config(state="disabled")
                except Exception:
                    pass
            return

        if self._active_conv_id:
            conv = self._conversations.get(self._active_conv_id)
            if conv:
                conv["messages"].append({"role": "assistant", "text": text})
                conv["history"].append({"role": "user", "content": self._stream_buffer or ""})
                conv["history"].append({"role": "assistant", "content": text[:2000]})
                if len(conv["history"]) > 12:
                    conv["history"] = conv["history"][2:]

        self._loading_pos = None