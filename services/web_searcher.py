import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests


def search_bing(query: str, num_results: int = 5) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    results: list[dict] = []
    encoded_q = urllib.parse.quote(query)

    try:
        url = f"https://www.bing.com/search?q={encoded_q}&mkt=zh-cn&format=rss"
        response = requests.get(url, headers=headers, timeout=15)
        content = response.content
        if content[:3] == b"\xef\xbb\xbf":
            content = content[3:]
        root = ET.fromstring(content)
        items = root.findall(".//item")
        for item in items[:num_results]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            title_text = title_elem.text if title_elem is not None else ""
            link_text = link_elem.text if link_elem is not None else ""
            desc_text = desc_elem.text if desc_elem is not None else ""
            if desc_text:
                desc_text = re.sub(r"<[^>]+>", "", desc_text)[:300]
            results.append({"title": title_text, "url": link_text, "description": desc_text.strip()})
    except ET.ParseError as e:
        logging.warning(f"Bing RSS解析失败: {e}")
    except Exception as e:
        logging.warning(f"Bing RSS请求失败: {e}")

    if not results:
        try:
            url = f"https://www.bing.com/search?q={encoded_q}&mkt=zh-cn"
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = "utf-8"
            h2_matches = re.findall(
                r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a></h2>',
                response.text, re.DOTALL,
            )
            for link, title_html in h2_matches[:num_results]:
                title_text = re.sub(r"<[^>]+>", "", title_html).strip()
                title_text = (title_text.replace("&amp;", "&").replace("&lt;", "<")
                              .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
                results.append({"title": title_text, "url": link, "description": ""})
        except Exception as e:
            logging.error(f"Bing HTML回退搜索失败: {e}")

    return results