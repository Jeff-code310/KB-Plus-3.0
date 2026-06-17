import os

from constants import BINARY_EXTENSIONS, FILE_ICONS


def format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def get_file_icon(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return FILE_ICONS.get(ext, "\U0001F4C4")


def is_text_file(filepath: str) -> bool:
    ext = os.path.splitext(filepath)[1].lower()
    return ext not in BINARY_EXTENSIONS


def read_file_chunk(filepath: str, max_bytes: int = 65536) -> str | None:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except Exception:
        return None
