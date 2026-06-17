import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

COLORS = {
    "bg": "#F0F4F8",
    "card": "#FFFFFF",
    "primary": "#0EA5E9",
    "secondary": "#06B6D4",
    "text": "#1E293B",
    "text_light": "#64748B",
    "border": "#E2E8F0",
    "search_bg": "#F8FAFC",
    "answer_bg": "#F0F9FF",
    "chat_user": "#DBEAFE",
    "chat_ai": "#FFFFFF",
    "chat_border": "#E2E8F0",
    "chat_input_bg": "#FFFFFF",
}

AI_CONFIGS = {
    "ollama": {
        "name": "本地Ollama",
        "api_url": "http://localhost:11434/api/chat",
        "model": "qwen2.5:3b",
    },
    "lm_studio": {
        "name": "LM Studio",
        "api_url": "http://localhost:1234/v1/chat/completions",
        "model": "local-model",
    },
    "gpt4all": {
        "name": "GPT4All",
        "api_url": "http://localhost:4891/v1/chat/completions",
        "model": "gpt4all",
    },
    "deepseek_api": {
        "name": "DeepSeek API",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "need_key": True,
    },
    "zhipu_cloud": {
        "name": "智谱云端",
        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
        "need_key": True,
    },
    "sensenova": {
        "name": "SenseNova (商汤)",
        "api_url": "https://token.sensenova.cn/v1/chat/completions",
        "model": "SenseChat-5",
        "need_key": True,
    },
}

TEXT_CONTENT_EXTENSIONS = frozenset({
    ".txt", ".md", ".csv", ".py", ".json", ".xml", ".ini", ".cfg", ".log",
    ".html", ".htm", ".css", ".js", ".yaml", ".yml", ".toml", ".conf",
})

BINARY_EXTENSIONS = frozenset({
    ".exe", ".dll", ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".ico", ".zip", ".rar", ".7z", ".tar", ".gz", ".mp3", ".mp4", ".avi",
    ".mkv", ".pyc", ".pyd", ".woff", ".woff2", ".ttf", ".eot", ".pdf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
})

FILE_ICONS = {
    ".docx": "\U0001F4DD",
    ".xlsx": "\U0001F4CA",
    ".pdf": "\U0001F4D5",
    ".jpg": "\U0001F5BC",
    ".jpeg": "\U0001F5BC",
    ".png": "\U0001F5BC",
    ".txt": "\U0001F4C3",
    ".zip": "\U0001F4E6",
    ".pptx": "\U0001F4FD",
}

N_KB = "知识库搜索"
N_WEB = "问题解答"

SUGGESTIONS: dict[str, list[str]] = {
    "客户": ["\U0001F4CA 汇总客户数据", "\U0001F4CB 提取清单", "\U0001F4C8 趋势分析"],
    "default": ["\U0001F4C4 查看文件"],
}