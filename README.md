# 知识库+3.0 — 文件搜索与 AI 问答助手

企业级知识库全量文件搜索工具，支持本地知识库与 NAS 网盘双源搜索，集成 AI 问答（Ollama / 云端 API）与网页搜索。

---

## 功能

| 功能 | 说明 |
|------|------|
| **文件搜索** | 按文件名或文件内容搜索，关键词精准匹配，结果毫秒级返回 |
| **双源搜索** | 搜索范围可选「本地知识库」「NAS网盘」「全部搜索」，互不干扰 |
| **AI 问答** | 支持本地 Ollama 模型 + 云端 API（阿里通义千问 / 百度文心 / DeepSeek / 腾讯混元 / 硅基流动） |
| **网页搜索** | 集成 Bing 搜索，结果可发送给 AI 做二次分析 |
| **知识库文件** | 随安装包附带 55 个完整知识库文档（阀门 / 水表 / 客户服务等） |

---

## 快速开始

### 下载安装包

从 [Releases](../../releases) 下载 `知识库+3.0_Installer.exe`，双击安装即用。

### 手动运行（开发）

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 搜索

1. 输入关键词，在搜索框右侧下拉选择搜索范围（默认只搜本地）
2. 勾选「含内容」可搜索文件内容
3. 点击「搜索」或按 `Enter`

---

## 项目结构

```
知识库+3.0/
├── main.py                 # 程序入口
├── config.py               # 配置管理（用户配置存 %APPDATA%）
├── constants.py            # 常量
├── requirements.txt        # Python 依赖
├── installer/
│   └── 知识库+3.0.iss      # Inno Setup 安装脚本
├── sample_files/
│   └── 知识库文件/          # 55 个知识库文档（打包时随安装包部署）
├── services/
│   ├── ai_service.py       # AI 问答服务
│   ├── file_searcher.py    # 知识库文件检索（KB 匹配）
│   └── web_searcher.py     # Bing 网页搜索
├── ui/
│   ├── main_window.py      # 主窗口（header 85px，AI 检测线程化）
│   ├── search_panel.py     # 搜索面板（含范围选择器）
│   ├── settings_window.py  # 设置窗口（AI 配置 / 搜索路径）
│   ├── web_panel.py        # 网页搜索面板
│   └── widgets.py          # UI 组件
└── utils/
    ├── helpers.py           # 工具函数（文件图标 / 大小格式化 / 文本检测）
    └── logger.py            # 日志
```

---

## 技术栈

- **Python 3.12** — 语言
- **Tkinter** — 桌面 GUI
- **PyInstaller** — 打包为单文件 exe
- **Inno Setup** — Windows 安装包制作
- **requests / Ollama API** — AI 问答

---

## 许可证

[MIT](./LICENSE)

Copyright (c) 2026 Jeff-code310