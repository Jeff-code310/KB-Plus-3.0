import threading
import tkinter as tk

from constants import COLORS, N_WEB
from services.ai_service import call_ollama, call_openai_compat, call_zhipu_websearch
from services.web_searcher import search_bing
from services.file_searcher import FileSearcher
from ui.widgets import ThinkingAnimation, configure_answer_tags, render_rich_text, append_references


class WebPanel:
    def __init__(self, parent: tk.Frame, config: dict, ai_provider: str, api_key: str):
        self._parent = parent
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key
        self._searcher = FileSearcher()
        self._is_answering: bool = False
        self._answer_cancelled: bool = False
        self._kb_cache: str = ""
        self._kb_cached: bool = False

        self.web_var = tk.StringVar()

        self._frame = tk.Frame(parent, bg=COLORS["bg"])
        self._build_web_bar()
        self._build_web_content()

    @property
    def frame(self) -> tk.Frame:
        return self._frame

    def update_config(self, config: dict, ai_provider: str, api_key: str) -> None:
        self._config = config
        self._ai_provider = ai_provider
        self._api_key = api_key

    def _build_web_bar(self) -> None:
        wa = tk.Frame(self._frame, bg=COLORS["bg"], pady=20)
        wa.pack(fill=tk.X, padx=30)

        wc = tk.Frame(wa, bg="white")
        wc.pack(fill=tk.X)

        tk.Label(
            wc, text="\u2728",
            font=("Segoe UI Emoji", 18), bg="white",
        ).pack(side=tk.LEFT, padx=(20, 10), pady=15)

        self.web_entry = tk.Entry(
            wc, textvariable=self.web_var,
            font=("Microsoft YaHei UI", 16),
            bg=COLORS["search_bg"], fg=COLORS["text"],
            bd=0, relief="flat",
        )
        self.web_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=15)
        self.web_entry.insert(0, "向AI助手提问，例如：最新的行业标准有哪些？")
        self.web_entry.config(fg=COLORS["text_light"])
        self.web_entry.bind("<Return>", lambda e: self._answer_question())
        self.web_entry.bind("<FocusIn>", self._on_web_focus)
        self.web_entry.bind("<FocusOut>", self._on_web_blur)

        self.answer_btn = tk.Button(
            wc, text="生成回答",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=COLORS["primary"], fg="white",
            bd=0, relief="flat", cursor="hand2",
            padx=30, pady=10,
            command=self._on_answer_click,
        )
        self.answer_btn.pack(side=tk.RIGHT, padx=(0, 5), pady=12)

    def _build_web_content(self) -> None:
        self.web_content = tk.Frame(self._frame, bg=COLORS["bg"])
        self.web_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))

        self.thinking_frame = tk.Frame(self.web_content, bg="white")
        self.thinking_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.answer_frame = tk.Frame(self.web_content, bg="white")
        self._build_answer_initial(self.answer_frame)

    def _build_answer_initial(self, parent: tk.Frame) -> None:
        for w in parent.winfo_children():
            w.destroy()

        tk.Label(
            parent, text="\U0001F31F AI智能问答",
            font=("Microsoft YaHei UI", 14, "bold"),
            fg=COLORS["text"], bg="white",
        ).pack(pady=(80, 10))

        tk.Label(
            parent,
            text="\U0001F4A1 输入问题，AI将结合知识库和网络信息为您提供专业回答",
            font=("Microsoft YaHei UI", 11),
            fg=COLORS["text_light"], bg="white", wraplength=600,
            justify="center",
        ).pack(pady=10)

        tk.Label(
            parent,
            text="\u25CF 整合知识库+  \u25CF 联网搜索+  \u25CF 智能分析",
            font=("Microsoft YaHei UI", 10),
            fg=COLORS["text_light"], bg="white",
        ).pack(pady=10)

    def _on_web_focus(self, event: tk.Event) -> None:
        if self.web_var.get() == "向AI助手提问，例如：最新的行业标准有哪些？":
            self.web_entry.delete(0, tk.END)
            self.web_entry.config(fg=COLORS["text"])

    def _on_web_blur(self, event: tk.Event) -> None:
        if not self.web_var.get():
            self.web_entry.insert(0, "向AI助手提问，例如：最新的行业标准有哪些？")
            self.web_entry.config(fg=COLORS["text_light"])

    def _on_answer_click(self) -> None:
        if self._is_answering:
            self._answer_cancelled = True
        else:
            self._answer_question()

    def _answer_question(self) -> None:
        question = self.web_var.get().strip()
        if question in ("", "向AI助手提问，例如：最新的行业标准有哪些？"):
            return

        self._is_answering = True
        self._answer_cancelled = False
        self.answer_btn.config(text="停止", bg="#EF4444")

        self.answer_frame.pack_forget()
        self.thinking_frame.pack(fill=tk.BOTH, expand=True)
        self.thinking = ThinkingAnimation(self.thinking_frame)
        self.thinking.start()

        threading.Thread(target=self._answer_thread, args=(question,), daemon=True).start()

    def _answer_thread(self, question: str) -> None:
        kb_content = self._kb_cache if self._kb_cached else ""
        web_results: list[dict] = []
        web_parts: list[str] = []

        def do_kb():
            nonlocal kb_content
            kb_content = self._searcher.search_kb_for_question(question, self._config)
            self._kb_cache = kb_content
            self._kb_cached = True

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

        self._parent.after(0, lambda: self._show_stage_hint("\U0001F50D 正在检索知识库 + 联网搜索..."))
        t_kb.join(timeout=8)
        t_web.join(timeout=8)

        web_content = "\n\n".join(web_parts) if web_parts else ""

        self._parent.after(200, lambda: self._render_answer(question, kb_content, web_content, web_results))

    def _show_stage_hint(self, text: str) -> None:
        try:
            if not hasattr(self, "thinking_frame") or not self.thinking_frame.winfo_exists():
                return
            for w in self.thinking_frame.winfo_children():
                if isinstance(w, tk.Label) and getattr(w, "_is_hint", False):
                    w.config(text=text)
                    return
            hint = tk.Label(
                self.thinking_frame, text=text,
                font=("Microsoft YaHei UI", 11),
                fg=COLORS["text_light"], bg="white",
            )
            hint._is_hint = True
            hint.pack()
        except Exception:
            pass

    def _render_answer(self, question: str, kb_content: str, web_content: str,
                       web_results: list[dict]) -> None:
        if self._answer_cancelled:
            self._is_answering = False
            self.answer_btn.config(text="生成回答", bg=COLORS["primary"])
            return

        self.thinking.stop()
        self.thinking_frame.pack_forget()
        self.answer_frame.pack(fill=tk.BOTH, expand=True)

        for w in self.answer_frame.winfo_children():
            w.destroy()

        qh = tk.Frame(self.answer_frame, bg=COLORS["primary"])
        qh.pack(fill=tk.X, padx=0, pady=(0, 0))
        tk.Label(
            qh, text=f"Q: {question}",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg="white", bg=COLORS["primary"],
            wraplength=800, justify="left",
        ).pack(fill=tk.X, padx=20, pady=15)

        self.answer_text = tk.Text(
            self.answer_frame,
            font=("Microsoft YaHei UI", 11),
            bg="white", fg=COLORS["text"],
            wrap="word", bd=0, relief="flat",
            padx=25, pady=20,
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True)
        configure_answer_tags(self.answer_text)
        self.answer_text.insert("end", "\u2728 正在生成专业回答...", "para")
        self.answer_text.config(state="disabled")

        self._call_ai_service(question, kb_content, web_content, web_results)

    def _call_ai_service(self, question: str, kb_content: str, web_content: str,
                         web_results: list[dict]) -> None:
        def stream_callback(current_text: str) -> None:
            if self._answer_cancelled:
                return
            self._parent.after(50, lambda: self._update_answer_text(current_text, web_results))

        def ai_call() -> str:
            if self._ai_provider == "ollama":
                return call_ollama(
                    question, kb_content, web_content,
                    stream_callback=stream_callback,
                    cancelled_flag=lambda: self._answer_cancelled,
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
                )
            return "请先在设置中选择一个可用的AI服务"

        def run_in_thread() -> None:
            try:
                final_text = ai_call()
                if final_text and not self._answer_cancelled:
                    self._parent.after(0, lambda: self._finalize_answer(final_text, web_results))
                elif self._answer_cancelled:
                    self._parent.after(0, lambda: self._finalize_answer("[用户已停止]", []))
            except Exception as e:
                err = f"[错误] AI调用失败：{str(e)}"
                self._parent.after(0, lambda: self._finalize_answer(err, []))

        threading.Thread(target=run_in_thread, daemon=True).start()

    def _update_answer_text(self, text: str, web_results: list[dict]) -> None:
        try:
            self.answer_text.config(state="normal")
            self.answer_text.delete("1.0", "end")
            render_rich_text(self.answer_text, text)
            if web_results:
                self.answer_text.insert("end", "\n", "para")
                self.answer_text.insert("end", "─" * 22 + "\n", "para")
                self.answer_text.insert("end", "参考来源（点击打开）：\n", "ref_title")
                for i, r in enumerate(web_results[:5], 1):
                    title = r.get("title", "")
                    url = r.get("url", "")
                    if title and url:
                        self.answer_text.insert("end", f"{i}. {title[:60]}", "link")
                        self.answer_text.insert("end", "\n", "para")
            self.answer_text.config(state="disabled")
        except Exception:
            pass

    def _finalize_answer(self, text: str, web_results: list[dict]) -> None:
        self._is_answering = False
        self.answer_btn.config(text="生成回答", bg=COLORS["primary"])

        try:
            self.answer_text.config(state="normal")
            self.answer_text.delete("1.0", "end")
            render_rich_text(self.answer_text, text)
            if web_results:
                self.answer_text.insert("end", "\n", "para")
                self.answer_text.insert("end", "─" * 22 + "\n", "para")
                self.answer_text.insert("end", "参考来源（点击打开）：\n", "ref_title")
                for i, r in enumerate(web_results[:5], 1):
                    title = r.get("title", "")
                    url = r.get("url", "")
                    if title and url:
                        self.answer_text.insert("end", f"{i}. {title[:60]}", "link")
                        self.answer_text.insert("end", "\n", "para")
            self.answer_text.config(state="disabled")
        except Exception:
            pass

    def clear_answer(self) -> None:
        self._build_answer_initial(self.answer_frame)