import logging
import os
import re

from utils.helpers import read_file_chunk
from constants import TEXT_CONTENT_EXTENSIONS

SKIP_DIRS = frozenset({
    "node_modules", ".git", ".svn", "__pycache__", "venv", ".venv",
    ".env", "build", "dist", ".next", ".nuxt", "target", "bin", "obj",
    "vendor", ".idea", ".vscode", ".hg", ".gradle",
})


class FileSearcher:
    def __init__(self):
        self._cache_valid: bool = False
        self._file_cache: dict[str, list[tuple[str, str]]] = {}

    def invalidate_cache(self) -> None:
        self._cache_valid = False
        self._file_cache.clear()

    def search_kb_for_question(self, question: str, config: dict) -> str:
        from config import get_valid_scopes
        scopes = get_valid_scopes(config)
        if not scopes:
            return ""
        paths = scopes[0]["paths"]
        if not paths:
            return ""

        words = [w for w in re.findall(r"[\u4e00-\u9fff\w]+", question.lower()) if len(w) >= 2]
        if not words:
            return ""

        kb_parts: list[tuple[int, str, str]] = []
        seen_files: set[str] = set()
        MAX_RESULTS = 10

        for base_path in paths:
            if not os.path.exists(base_path):
                continue

            if self._cache_valid and base_path in self._file_cache:
                file_list = self._file_cache[base_path]
            else:
                file_list: list[tuple[str, str, str]] = []
                try:
                    for root, dirs, files in os.walk(base_path):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("$")]
                        for fname in files:
                            ext = os.path.splitext(fname)[1].lower()
                            if ext not in TEXT_CONTENT_EXTENSIONS:
                                continue
                            fpath = os.path.join(root, fname)
                            if fpath in seen_files:
                                continue
                            seen_files.add(fpath)
                            content = read_file_chunk(fpath, 1500)
                            if content is None:
                                continue
                            file_list.append((fpath, fname, content))
                except PermissionError:
                    pass
                except Exception as e:
                    logging.warning(f"扫描目录异常 {base_path}: {e}")
                self._file_cache[base_path] = file_list
            self._cache_valid = True

            for fpath, fname, content in file_list:
                fname_lower = fname.lower()
                name_match = sum(1 for w in words if w in fname_lower)
                content_lower = content.lower()
                content_match = sum(1 for w in words if w in content_lower)
                score = name_match * 5 + content_match
                if score > 0:
                    snippet = content[:800]
                    kb_parts.append((score, fname, snippet))

        if not kb_parts:
            return ""
        kb_parts.sort(key=lambda x: -x[0])
        result_parts = []
        for score, fname, snippet in kb_parts[:3]:
            result_parts.append(f"【KB】【知识库 - {fname}】{snippet}")
        return "\n\n---\n".join(result_parts)