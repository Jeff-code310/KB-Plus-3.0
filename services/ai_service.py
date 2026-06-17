import json
import logging

import requests

from constants import AI_CONFIGS


def _build_prompt(question: str, kb_content: str, web_content: str) -> str:
    kb_prefix = "（以下为内部知识库资料，请优先参考）\n\n" if kb_content else ""
    return (
        f"你是一位专业的知识顾问。用户的问题是：{question}\n\n"
        f"以下是参考信息：\n"
        f"{kb_prefix}{web_content}\n\n"
        f"请根据以上信息，详细、专业地回答用户的问题。要求：\n"
        f"1. 优先使用内部知识库资料作为主要依据\n"
        f"2. 结合搜索到的网络信息综合分析\n"
        f"3. 回答要准确、全面、有深度\n"
        f"4. 如有不确定的地方，明确说明\n"
        f"5. 使用清晰的结构组织答案"
    )


def _build_zhipu_system_prompt(kb_content: str) -> str:
    prompt = (
        "你是一名资深阀门管件行业专家，熟悉各类阀门（闸阀、截止阀、球阀、蝶阀、止回阀、"
        "安全阀、减压阀、疏水阀等）和管件（弯头、三通、法兰、异径管、管接头等）的相关标准"
        "与选型知识。请专业、准确地回答用户的问题。"
        "\n\n优先使用以下内部知识库内容回答，如果知识库内容不足，"
        "请结合联网搜索的最新信息进行补充。\n\n"
        "【内部知识库】\n"
    )
    if kb_content and kb_content.strip():
        prompt += kb_content
    else:
        prompt += "（当前无内部知识库资料，请使用联网搜索获取信息）"
    return prompt


def _iter_sse_lines(response):
    buffer = ""
    for chunk in response.iter_content(chunk_size=1, decode_unicode=False):
        if not chunk:
            continue
        buffer += chunk.decode("utf-8", errors="replace")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.startswith("data: "):
                yield line[6:]
                if line[6:].strip() == "[DONE]":
                    return


def call_ollama(question: str, kb_content: str, web_content: str,
                stream_callback: callable = None, cancelled_flag: callable = lambda: False) -> str:
    config = AI_CONFIGS["ollama"]
    prompt = _build_prompt(question, kb_content, web_content)
    data = {
        "model": config["model"],
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": 1024},
    }
    try:
        response = requests.post(config["api_url"], json=data, timeout=60, stream=True)
        if response.status_code == 200:
            full_response: list[str] = []
            last_stream_len = 0
            for line in response.iter_lines():
                if cancelled_flag():
                    break
                if line:
                    try:
                        line_str = line.decode("utf-8").lstrip("data: ").strip()
                        if line_str:
                            chunk_json = json.loads(line_str)
                            token = chunk_json.get("response", "")
                            if token:
                                full_response.append(token)
                                current = "".join(full_response)
                                new_chars = len(current) - last_stream_len
                                if new_chars >= 3 or token in "。！？!?；，、\n" or len(current) - last_stream_len >= 15:
                                    last_stream_len = len(current)
                                    if stream_callback:
                                        stream_callback(current)
                    except Exception:
                        pass
            result_text = "".join(full_response)
            if stream_callback:
                stream_callback(result_text)
            return result_text
        else:
            return f"Ollama返回异常（状态码{response.status_code}）"
    except requests.exceptions.ConnectionError:
        return "无法连接到Ollama服务（http://localhost:11434），请确认Ollama已启动"
    except Exception as e:
        return f"Ollama调用失败: {e}"


def call_openai_compat(provider: str, question: str, kb_content: str,
                       web_content: str, api_key: str = "",
                       stream_callback: callable = None,
                       cancelled_flag: callable = lambda: False) -> str:
    config = AI_CONFIGS.get(provider)
    if not config:
        return "AI服务配置错误，请检查设置"

    prompt = _build_prompt(question, kb_content, web_content)
    headers = {"Content-Type": "application/json"}
    if config.get("need_key"):
        if not api_key:
            return "当前服务需要API Key，请在设置菜单中填写"
        headers["Authorization"] = f"Bearer {api_key}"

    data = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": True,
    }

    try:
        response = requests.post(config["api_url"], headers=headers, json=data, timeout=60, stream=True)
        if response.status_code == 200:
            full_response: list[str] = []
            last_stream_len = 0
            for line in response.iter_lines():
                if cancelled_flag():
                    break
                if line:
                    try:
                        line_str = line.decode("utf-8", errors="replace").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response.append(content)
                                current = "".join(full_response)
                                new_chars = len(current) - last_stream_len
                                if new_chars >= 3 or content in "。！？!?；，、\n" or len(current) - last_stream_len >= 15:
                                    last_stream_len = len(current)
                                    if stream_callback:
                                        stream_callback(current)
                    except json.JSONDecodeError:
                        pass
                    except Exception:
                        pass
            result_text = "".join(full_response)
            if stream_callback:
                stream_callback(result_text)
            return result_text
        elif response.status_code == 401:
            return "API Key错误或无权限，请检查设置"
        elif response.status_code == 429:
            return "API调用频率限制，请稍后再试"
        else:
            return f"AI返回异常（状态码{response.status_code}），请检查API配置"
    except requests.exceptions.ConnectionError:
        return f"无法连接到AI服务（{config['api_url']}），请确认服务已启动"
    except Exception as e:
        return f"AI调用失败: {e}"


def call_zhipu_websearch(question: str, kb_content: str, api_key: str,
                         stream_callback: callable = None,
                         cancelled_flag: callable = lambda: False) -> str:
    config = AI_CONFIGS.get("zhipu_cloud")
    if not config:
        return ""
    if not api_key:
        return ""

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": _build_zhipu_system_prompt(kb_content)},
            {"role": "user", "content": question},
        ],
        "tools": [{"type": "web_search", "web_search": {}}],
        "stream": True,
        "temperature": 0.7,
    }

    try:
        response = requests.post(config["api_url"], headers=headers, json=payload,
                                 stream=True, timeout=120)
        if response.status_code != 200:
            err_msg = response.text[:200] if response.text else "未知错误"
            if response.status_code == 401:
                err_msg = "API Key错误或无权限"
            elif response.status_code == 429:
                err_msg = "API调用频率限制"
            if stream_callback:
                stream_callback(f"[错误] {err_msg}")
            return ""

        full_response: list[str] = []
        last_stream_len = 0

        for line in response.iter_lines():
            if cancelled_flag():
                break
            if line:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_response.append(content)
                            current = "".join(full_response)
                            new_chars = len(current) - last_stream_len
                            if new_chars >= 3 or content in "。！？!?；，、\n" or len(current) - last_stream_len >= 15:
                                last_stream_len = len(current)
                                if stream_callback:
                                    stream_callback(current)
                    except Exception:
                        pass

        answer_text = "".join(full_response)
        if answer_text and stream_callback:
            stream_callback(answer_text)
        return answer_text

    except requests.exceptions.ConnectionError:
        if stream_callback:
            stream_callback("[错误] 无法连接到智谱API，请检查网络")
        return ""
    except Exception as e:
        if stream_callback:
            stream_callback(f"[错误] {e}")
        return ""