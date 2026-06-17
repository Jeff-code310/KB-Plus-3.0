import threading
import tkinter as tk

from constants import COLORS
from services.ai_service import call_ollama, call_openai_compat, call_zhipu_websearch
from services.web_searcher import search_bing
from services.file_searcher import FileSearcher
from ui.widgets import configure_answer_tags, render_rich_text

_conv_counter = 0


def _next_conv_id() -> str:
    global _conv_counter
    _conv_counter += 1
    return f"conv_{_conv_counter}"


class WebPanel:
    def __init__(self, parent: tk.Frame, config: dict, ai_provider: str, api_key: str):
        self._parent = parent
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key
        self._searcher = FileSearcher()
        self._is_answering: bool = False
        self._answer_cancelled: bool = False
        self._current_answer_entry: tk.Text | None = None
        self._stream_initialized: bool = False

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
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_welcome()

    def _build_welcome(self) -> None:
        f = tk.Frame(self._scrollable_frame, bg=COLORS["bg"])
        f.pack(expand=True, pady=(100, 0))
        tk.Label(
            f, text="\U0001F31F",
            font=("Segoe UI Emoji", 36), bg=COLORS["bg"],
        ).pack()
        tk.Label(
            f, text="向你提问",
            font=("Microsoft YaHei UI", 14, "bold"),
            fg=COLORS["text"], bg=COLORS["bg"],
        ).pack(pady=(8, 4))
        tk.Label(
            f, text="AI 会结合知识库与联网搜索为你提供专业回答",
            font=("Microsoft YaHei UI", 10),
            fg=COLORS["text_light"], bg=COLORS["bg"],
        ).pack()

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
        self._current_answer_entry = None
        self._stream_initialized = False

        conv_id = _next_conv_id()
        self._conversations[conv_id] = {
            "title": "新对话",
            "messages": [],
            "history": [],
        }
        self._active_conv_id = conv_id

        self._sync_listbox()
        for w in self._scrollable_frame.winfo_children():
            w.destroy()
        self._build_welcome()

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

        msgs = []
        for child in self._scrollable_frame.winfo_children():
            role = getattr(child, "_role", "")
            text = getattr(child, "_text", "")
            if role and text:
                msgs.append({"role": role, "text": text})
        conv["messages"] = msgs

    def _load_conv_messages(self, conv_id: str) -> None:
        self._current_answer_entry = None
        self._stream_initialized = False
        conv = self._conversations.get(conv_id)
        if conv is None:
            return

        for w in self._scrollable_frame.winfo_children():
            w.destroy()

        if not conv["messages"]:
            self._build_welcome()
            return

        for msg in conv["messages"]:
            role = msg.get("role", "")
            text = msg.get("text", "")
            if role == "user":
                self._rebuild_user_bubble(text)
            elif role == "assistant":
                self._rebuild_ai_bubble(text)

        self._auto_scroll()

    def _rebuild_user_bubble(self, text: str) -> None:
        self._add_user_bubble(text)
        for child in self._scrollable_frame.winfo_children():
            txt = getattr(child, "_question_text", "")
            if txt == text:
                child._text = text
                break

    def _rebuild_ai_bubble(self, text: str) -> None:
        row = tk.Frame(self._scrollable_frame, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=(4, 8))
        row._role = "assistant"
        row._text = text

        icon = tk.Label(
            row, text="\U0001F916",
            font=("Segoe UI Emoji", 16), bg=COLORS["bg"],
        )
        icon.pack(side=tk.LEFT, padx=(4, 8))
        icon.pack_propagate(False)
        icon.configure(width=28, height=28)

        bubble = tk.Frame(row, bg="white")
        bubble.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        aw = tk.Text(
            bubble,
            font=("Microsoft YaHei UI", 11),
            bg="white", fg=COLORS["text"],
            wrap="word", bd=0, relief="flat",
            padx=16, pady=10,
            height=4,
        )
        aw.pack(fill=tk.X)
        configure_answer_tags(aw)
        render_rich_text(aw, text)
        aw.config(state="disabled")

    # ── Answer flow ───────────────────────────────────

    def _answer_question(self) -> None:
        question = self.web_var.get().strip()
        if question in ("", "向 AI 提问..."):
            return

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

        self._add_user_bubble(question)
        self._add_ai_bubble()

        self._answer_thread(question)

    def _add_user_bubble(self, text: str) -> None:
        row = tk.Frame(self._scrollable_frame, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=(4, 0))
        row._role = "user"
        row._text = text
        row._question_text = text

        spacer = tk.Frame(row, bg=COLORS["bg"], width=60)
        spacer.pack(side=tk.LEFT)

        bubble = tk.Frame(row, bg="#DBEAFE")
        bubble.pack(side=tk.RIGHT, padx=(50, 0))

        lbl = tk.Label(
            bubble, text=text,
            font=("Microsoft YaHei UI", 11),
            fg=COLORS["text"], bg="#DBEAFE",
            wraplength=500, justify="left",
        )
        lbl.pack(padx=16, pady=10)

    def _add_ai_bubble(self) -> None:
        row = tk.Frame(self._scrollable_frame, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=(4, 8))
        row._role = "assistant"
        row._text = ""

        icon = tk.Label(
            row, text="\U0001F916",
            font=("Segoe UI Emoji", 16), bg=COLORS["bg"],
        )
        icon.pack(side=tk.LEFT, padx=(4, 8))
        icon.pack_propagate(False)
        icon.configure(width=28, height=28)

        bubble = tk.Frame(row, bg="white")
        bubble.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self._current_answer_entry = tk.Text(
            bubble,
            font=("Microsoft YaHei UI", 11),
            bg="white", fg=COLORS["text"],
            wrap="word", bd=0, relief="flat",
            padx=16, pady=10,
            height=4,
        )
        self._current_answer_entry.pack(fill=tk.X)
        configure_answer_tags(self._current_answer_entry)
        self._current_answer_entry.insert("end", "\U0001F4AD 正在思考...", "para")
        self._current_answer_entry.config(state="disabled")
        self._stream_initialized = False

        self._auto_scroll()

    def _answer_thread(self, question: str) -> None:
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
        self._call_ai_service(question, kb_content, web_content, web_results)

    def _call_ai_service(self, question: str, kb_content: str, web_content: str,
                         web_results: list[dict]) -> None:
        conv = self._conversations.get(self._active_conv_id) if self._active_conv_id else None
        history = conv["history"].copy() if conv and conv["history"] else None

        def stream_callback(current_text: str) -> None:
            if self._answer_cancelled:
                return
            self._parent.after(30, lambda: self._update_answer_text(current_text))

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

        def run_in_thread() -> None:
            try:
                final_text = ai_call()
                if final_text and not self._answer_cancelled:
                    self._parent.after(0, lambda: self._finalize_answer(final_text))
                elif self._answer_cancelled:
                    self._parent.after(0, lambda: self._finalize_answer("[用户已停止]"))
            except Exception as e:
                self._parent.after(0, lambda: self._finalize_answer(f"[错误] AI调用失败：{str(e)}"))

        threading.Thread(target=run_in_thread, daemon=True).start()

    def _update_answer_text(self, text: str) -> None:
        widget = self._current_answer_entry
        if not widget:
            return
        try:
            widget.config(state="normal")
            if not self._stream_initialized:
                widget.delete("1.0", "end")
                self._stream_initialized = True
            else:
                widget.delete("1.0", "end")
            render_rich_text(widget, text)
            widget.config(state="disabled")
            self._auto_scroll()
        except Exception:
            pass

    def _finalize_answer(self, text: str) -> None:
        self._is_answering = False
        self.send_btn.config(text="\u25B6 发送", bg=COLORS["primary"])

        widget = self._current_answer_entry
        if not widget:
            return

        try:
            widget.config(state="normal")
            widget.delete("1.0", "end")
            render_rich_text(widget, text)
            widget.config(state="disabled")
            self._auto_scroll()
        except Exception:
            pass

        if text and "[错误]" not in text and self._active_conv_id:
            conv = self._conversations.get(self._active_conv_id)
            if conv:
                conv["history"].append({"role": "user", "content": self._get_last_question()})
                conv["history"].append({"role": "assistant", "content": text[:2000]})
                if len(conv["history"]) > 12:
                    conv["history"] = conv["history"][2:]
                self._save_current_messages()

    def _get_last_question(self) -> str:
        for child in reversed(self._scrollable_frame.winfo_children()):
            txt = getattr(child, "_question_text", "")
            if txt:
                return txt
        return ""

    def _auto_scroll(self) -> None:
        try:
            self._canvas.yview_moveto(1.0)
        except Exception:
            pass