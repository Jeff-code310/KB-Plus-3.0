import json
import logging
import os
import sys

import requests

from constants import APP_DIR

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", APP_DIR), "知识库+3.0")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: dict = {
    "kb_local_path": os.path.join(APP_DIR, "知识库文件") if getattr(sys, 'frozen', False) else os.path.join(APP_DIR, "sample_files", "知识库文件"),
    "kb_nas_path": "",
    "recent_searches": [],
    "ai_custom_config": {},
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            for key, default_val in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = default_val
                elif key in ("kb_local_path", "kb_nas_path"):
                    if not config[key] or not os.path.exists(config[key]):
                        config[key] = default_val
                elif key == "recent_searches":
                    if not config[key]:
                        config[key] = default_val
            return config
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
    save_config(dict(DEFAULT_CONFIG))
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> bool:
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")
        return False


def _is_root_path(path: str) -> bool:
    path = path.strip().rstrip(os.sep).rstrip("/")
    return len(path) <= 3 and (path.endswith(":") or len(path) <= 2)


def get_valid_scopes(config: dict) -> list[dict]:
    kb_paths: list[str] = []
    local_path = config.get("kb_local_path") or os.path.join(APP_DIR, "知识库文件")
    if os.path.exists(local_path) and not _is_root_path(local_path):
        kb_paths.append(local_path)

    nas_path = config.get("kb_nas_path", "")
    if nas_path and os.path.exists(nas_path):
        kb_paths.append(nas_path)

    if kb_paths:
        return [{"name": "知识库搜索", "paths": kb_paths}]
    return [{"name": "知识库搜索", "paths": [os.path.join(APP_DIR, "知识库文件")]}]


def detect_local_ai_services() -> list[dict]:
    import requests
    services: list[dict] = []

    ollama_available = False
    ollama_models = []
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            ollama_models = [m["name"] for m in r.json().get("models", [])]
            ollama_available = True
            logging.info(f"检测到Ollama服务，模型: {ollama_models}")
    except Exception as e:
        logging.warning(f"Ollama检测失败: {e}")
    services.append({
        "id": "ollama", "name": "Ollama (本地)",
        "api_url": "http://localhost:11434/api/chat",
        "models": ollama_models or ["qwen2.5:3b"],
        "available": ollama_available,
    })

    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=2)
        if r.status_code == 200:
            models = [m["id"] for m in r.json().get("data", [])]
            services.append({
                "id": "lm_studio", "name": "LM Studio (本地)",
                "api_url": "http://localhost:1234/v1/chat/completions",
                "models": models, "available": True,
            })
            logging.info(f"检测到LM Studio服务，模型: {models}")
    except Exception as e:
        logging.warning(f"LM Studio检测失败: {e}")

    try:
        r = requests.get("http://localhost:4891/v1/models", timeout=2)
        if r.status_code == 200:
            services.append({
                "id": "gpt4all", "name": "GPT4All (本地)",
                "api_url": "http://localhost:4891/v1/chat/completions",
                "models": ["gpt4all"], "available": True,
            })
    except Exception:
        pass

    return services