import json
import logging

import requests

from constants import AI_CONFIGS

INDUSTRY_SYSTEM_PROMPT = (
    "你是一名资深阀门、管件、流量计行业专家（威兹敦集团客户服务部），"
    "精通以下专业技术领域：\n"
    "\n"
    "【阀门知识】\n"
    "闸阀、截止阀、球阀、蝶阀、止回阀（逆止阀）、安全阀、"
    "减压阀、疏水阀、调节阀、隔膜阀、旋塞阀、柱塞阀、"
    "陶瓷阀、电动阀、气动阀、电磁阀等各类阀门的：\n"
    "  - 结构原理与工作原理\n"
    "  - 选型计算（口径/压力/材质/驱动方式）\n"
    "  - 安装调试与维护保养\n"
    "  - 常见故障现象、原因分析及排除方法\n"
    "  - 密封原理（硬密封/软密封/金属密封/PTFE) 及泄漏等级\n"
    "  - 启闭力矩分析与执行机构选型\n"
    "\n"
    "【管件知识】\n"
    "弯头(45°/90°/180°)、等径/异径三通、四通、"
    "同心/偏心异径管（大小头）、管帽、法兰、盲板、"
    "管箍、活接头、螺纹接头、承插焊管件、卡套管件等：\n"
    "  - 壁厚等级（Sch10/Sch40/Sch80/Sch160）\n"
    "  - 连接方式（法兰/对焊/承插焊/螺纹/卡套）\n"
    "  - 材料匹配与选型\n"
    "\n"
    "【流量计知识】\n"
    "电磁流量计、涡街流量计、超声波流量计（外夹式/管段式）、"
    "涡轮流量计、质量流量计（科里奥利）、\n"
    "差压式流量计（孔板/喷嘴/V锥）、转子流量计、\n"
    "容积式流量计（椭圆齿轮/罗茨/刮板）、热式气体质量流量计等：\n"
    "  - 测量原理与适用工况\n"
    "  - 量程比与精度等级\n"
    "  - 安装直管段要求\n"
    "  - 常见故障码/异常排查\n"
    "\n"
    "【技术标准（部分参考）】\n"
    "GB/T 12234-2019 石油、石化及相关工业用钢制截止阀和升降式止回阀\n"
    "GB/T 12237-2021 石油、石化及相关工业用钢制球阀\n"
    "GB/T 12238-2016 法兰和对夹连接弹性密封蝶阀\n"
    "GB/T 13927-2008 工业阀门 压力试验\n"
    "GB/T 9115-2010 对焊钢制管法兰\n"
    "GB/T 12459-2017 钢制对焊管件类型与参数\n"
    "JB/T 9248-2015 电磁流量计\n"
    "JB/T 2274-2015 涡街流量计\n"
    "HG/T 20592~20635-2009 钢制管法兰、垫片、紧固件\n"
    "API 598 / API 6D / ISO 17292 / ASME B16.5 / ASME B16.9\n"
    "\n"
    "回答要求：\n"
    "1. 优先引用知识库资料作为主要依据，并在引用时注明来源文件\n"
    "2. 结合联网搜索的最新行业信息综合分析\n"
    "3. 回答务必务实、专业，给出具体参数/型号/建议，避免空泛描述\n"
    "4. 涉及标准时标注标准号（如GB/T 12234-2019）\n"
    "5. 涉及材质时标注材质牌号（如CF8、WCB、304SS、316L、QT450-10）\n"
    "6. 涉及压力时标注公称压力等级（PN10/PN16/PN25/PN40 或 Class 150/300/600）\n"
    "7. 如知识库和联网搜索都无法确认，明确说明并给出获取正确信息的建议途径\n"
    "8. 给出结构清晰的回答，适当使用分点、小标题组织内容"
)

OLLAMA_SYSTEM_PROMPT = (
    "你是一名资深阀门、管件、流量计行业专家（威兹敦集团客户服务部）。\n"
    "主要职责：解答客户关于选型、安装、维护、故障排除等方面的技术咨询。\n"
    "\n"
    "【熟悉的主要产品】\n"
    "阀门：闸阀、截止阀、球阀、蝶阀、止回阀、安全阀、减压阀、疏水阀\n"
    "管件：弯头、三通、异径管、法兰、盲板、管箍、活接头、管帽\n"
    "流量计：电磁、涡街、超声波、涡轮、质量流量计\n"
    "\n"
    "【材质牌号参考】CF8/CF8M(304/316不锈钢)、WCB(WCC)(碳钢)、\n"
    "LCB(LCC)(低温钢)、QT450-10(球墨铸铁)、HPb59-1(黄铜)\n"
    "\n"
    "【压力等级参考】PN10/16/25/40/63/100；Class 150/300/600/900/1500/2500\n"
    "\n"
    "回答要求：\n"
    "1. 优先使用知识库资料并注明来源文件\n"
    "2. 回答务实，给出具体参数和操作建议，避免空泛\n"
    "3. 涉及标准/材质/压力时标注标准号、材质牌号、压力等级\n"
    "4. 以清晰的结构组织回答（分点/小标题）\n"
    "5. 不确定时明确说明，并建议获取准确信息的途径"
)


def _build_prompt(question: str, kb_content: str, web_content: str) -> str:
    prompt_parts = []
    if kb_content and kb_content.strip():
        prompt_parts.append(f"（以下为内部知识库资料，请优先参考并注明来源）\n\n{kb_content}")
    if web_content and web_content.strip():
        prompt_parts.append(f"（以下为联网搜索结果，请综合分析）\n\n{web_content}")
    reference_text = "\n\n---\n\n".join(prompt_parts) if prompt_parts else "（无额外参考资料）"

    return (
        f"请参考以下资料回答用户的问题。资料中标注 【知识库】 的内容来自内部资料库，"
        f"应优先采用；标注 【网页】 的内容来自联网搜索结果，可补充参考。\n\n"
        f"用户的问题是：{question}\n\n"
        f"参考资料：\n{reference_text}\n\n"
        f"请给出专业、务实的回答。"
    )


def _build_zhipu_system_prompt(kb_content: str) -> str:
    prompt = INDUSTRY_SYSTEM_PROMPT + "\n\n"
    if kb_content and kb_content.strip():
        prompt += (
            "【内部知识库参考资料（请优先采用并注明来源）】\n" + kb_content
        )
    else:
        prompt += "【内部知识库】当前无匹配的内部资料，请使用联网搜索获取信息"
    return prompt


def _build_ollama_messages(question: str, kb_content: str, web_content: str) -> list[dict]:
    prompt_parts = []
    if kb_content and kb_content.strip():
        prompt_parts.append(f"（内部知识库资料，请优先参考并注明来源）\n{kb_content}")
    if web_content and web_content.strip():
        prompt_parts.append(f"（联网搜索结果，用于补充参考）\n{web_content}")
    reference_text = "\n\n---\n\n".join(prompt_parts) if prompt_parts else "（无额外参考资料）"

    user_message = (
        f"请参考以下资料回答用户的问题：\n\n"
        f"用户的问题：{question}\n\n"
        f"参考资料：\n{reference_text}\n\n"
        f"请给出专业、务实的回答。"
    )
    return [
        {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def call_ollama(question: str, kb_content: str, web_content: str,
                stream_callback: callable = None, cancelled_flag: callable = lambda: False,
                history: list[dict] | None = None) -> str:
    config = AI_CONFIGS["ollama"]
    messages = _build_ollama_messages(question, kb_content, web_content)
    if history:
        messages = messages[:1] + history + messages[1:]
    data = {
        "model": config["model"],
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 512},
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
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            chunk_json = json.loads(data_str)
                            content = ""
                            if "message" in chunk_json:
                                content = chunk_json["message"].get("content", "")
                            elif "response" in chunk_json:
                                content = chunk_json["response"]
                            if content:
                                full_response.append(content)
                                current = "".join(full_response)
                                new_chars = len(current) - last_stream_len
                                if new_chars >= 1 or content in "。！？!?；，、\n" or len(current) - last_stream_len >= 8:
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
        else:
            return f"Ollama返回异常（状态码{response.status_code}）"
    except requests.exceptions.ConnectionError:
        return "无法连接到Ollama服务（http://localhost:11434），请确认Ollama已启动"
    except Exception as e:
        return f"Ollama调用失败: {e}"


def call_openai_compat(provider: str, question: str, kb_content: str,
                       web_content: str, api_key: str = "",
                       stream_callback: callable = None,
                       cancelled_flag: callable = lambda: False,
                       history: list[dict] | None = None) -> str:
    config = AI_CONFIGS.get(provider)
    if not config:
        return "AI服务配置错误，请检查设置"

    headers = {"Content-Type": "application/json"}
    if config.get("need_key"):
        if not api_key:
            return "当前服务需要API Key，请在设置菜单中填写"
        headers["Authorization"] = f"Bearer {api_key}"

    prompt = _build_prompt(question, kb_content, web_content)
    messages = [
        {"role": "system", "content": INDUSTRY_SYSTEM_PROMPT},
    ]
    if history:
        messages += history
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": config["model"],
        "messages": messages,
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
                                if new_chars >= 1 or content in "。！？!?；，、\n" or len(current) - last_stream_len >= 8:
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
        "stream": True,
        "temperature": 0.4,
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
                            if new_chars >= 1 or content in "。！？!?；，、\n" or len(current) - last_stream_len >= 8:
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