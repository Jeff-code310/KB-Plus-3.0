import os
import re
import tkinter as tk
import webbrowser

from constants import COLORS


class ThinkingAnimation:
    def __init__(self, parent_frame: tk.Frame):
        self._parent = parent_frame
        self._active: bool = False
        self._step: int = 0
        self._label: tk.Label | None = None

    def start(self) -> None:
        self._active = True
        for w in self._parent.winfo_children():
            w.destroy()

        container = tk.Frame(self._parent, bg="white")
        container.pack(pady=100, padx=40)

        self._label = tk.Label(
            container,
            text="正在思考",
            font=("Microsoft YaHei UI", 13),
            fg="#94A3B8", bg="white",
        )
        self._label.pack()

        sub = tk.Label(
            container,
            text="正在检索知识库并联网搜索",
            font=("Microsoft YaHei UI", 10),
            fg="#CBD5E1", bg="white",
        )
        sub.pack(pady=(10, 0))

        self._step = 0
        self._breathe()

    def stop(self) -> None:
        self._active = False

    def _breathe(self) -> None:
        if not self._active:
            return
        try:
            dots = [".", "..", "...", "   ", "."]
            idx = (self._step // 4) % len(dots)
            if self._label:
                self._label.config(text=f"正在思考{dots[idx]}")
            cycle = self._step % 32
            brightness = int(148 + 30 * ((cycle / 16) * (2 - cycle / 16)))
            color = f"#{brightness:02x}{brightness + 10:02x}{brightness + 27:02x}"
            if self._label:
                self._label.config(fg=color)
        except Exception:
            pass
        self._step += 1
        self._parent.after(200, self._breathe)


def configure_answer_tags(text_widget: tk.Text) -> None:
    text_widget.tag_configure(
        "summary",
        font=("Microsoft YaHei UI", 12, "bold"),
        foreground="#0369A1", spacing1=8, spacing2=4, spacing3=8,
    )
    text_widget.tag_configure(
        "list_num",
        font=("Microsoft YaHei UI", 11, "bold"),
        foreground="#0F172A", lmargin1=22, lmargin2=30,
    )
    text_widget.tag_configure(
        "list_content",
        foreground="#475569", lmargin1=40, lmargin2=48, spacing1=4,
    )
    text_widget.tag_configure(
        "bullet",
        foreground="#475569", lmargin1=30, lmargin2=40,
    )
    text_widget.tag_configure(
        "code",
        font=("Consolas", 10), background="#F8FAFC",
        foreground="#475569", lmargin1=18, lmargin2=26,
        spacing1=6, spacing2=3, spacing3=6,
    )
    text_widget.tag_configure(
        "para",
        foreground="#334155", spacing1=8, spacing2=3, spacing3=8,
    )
    text_widget.tag_configure(
        "ref_title",
        font=("Microsoft YaHei UI", 10),
        foreground="#94A3B8", spacing1=12,
    )
    text_widget.tag_configure(
        "link",
        foreground="#3B82F6", underline=1,
    )


def render_rich_text(text_widget: tk.Text, text: str) -> None:
    clean = re.sub(r"\*+", "", text)
    lines = clean.split("\n")
    first_para = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            text_widget.insert(tk.END, "\n", "para")
            continue
        if stripped.startswith("```") or stripped.endswith("```"):
            code_text = stripped.strip("`")
            text_widget.insert(tk.END, code_text + "\n", "code")
        elif first_para and len(stripped) < 50 and (
            stripped.endswith("：") or stripped.endswith(":") or stripped.endswith("。")
        ):
            text_widget.insert(tk.END, stripped + "\n", "summary")
            text_widget.insert(tk.END, "─" * 24 + "\n", "para")
            first_para = False
        elif re.match(r"^[\u4e00-\u9fa5a-zA-Z]{1,20}：$", stripped) or (
            re.match(r"^[\u4e00-\u9fa5]{2,12}$", stripped) and len(stripped) < 15
        ):
            text_widget.insert(tk.END, stripped + "\n", "summary")
        elif re.match(r"^[0-9]+[\.、]\s", stripped):
            m = re.match(r"^([0-9]+[\.、]\s*)(.+)$", stripped)
            if m:
                text_widget.insert(tk.END, m.group(1), "list_num")
                text_widget.insert(tk.END, m.group(2) + "\n", "list_content")
            else:
                text_widget.insert(tk.END, stripped + "\n", "list_num")
        elif stripped.startswith(("-", "•", "∗", "▪")):
            text_widget.insert(tk.END, stripped + "\n", "bullet")
        else:
            text_widget.insert(tk.END, stripped + "\n", "para")
            first_para = False


def append_references(parent_frame: tk.Frame, search_results: list[dict]) -> None:
    if not search_results:
        return

    ref_frame = tk.Frame(parent_frame, bg="white")
    ref_frame.pack(fill=tk.X, padx=25, pady=(5, 10))
    tk.Frame(ref_frame, bg="#BAE6FD", height=2).pack(fill=tk.X, pady=(0, 10))
    tk.Label(
        ref_frame,
        text="\U0001F4DA 参考来源（点击可打开）：",
        font=("Microsoft YaHei UI", 11, "bold"),
        fg=COLORS["text"], bg="white",
    ).pack(fill=tk.X, pady=(5, 5))

    for i, r in enumerate(search_results[:5], 1):
        btn_text = f"{i}. {r['title'][:60]}{'...' if len(r['title']) > 60 else ''}"
        btn = tk.Button(
            ref_frame,
            text=btn_text,
            font=("Microsoft YaHei UI", 9),
            fg="#3B82F6", bg="white", bd=0, relief="flat",
            cursor="hand2", anchor="w", justify="left", wraplength=700,
            command=lambda url=r["url"]: webbrowser.open(url),
        )
        btn.pack(fill=tk.X, pady=2)