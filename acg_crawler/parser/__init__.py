"""网盘链接提取模块"""
import re

BAIDU_PATTERNS = [
    r'https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+',
    r'https?://yun\.baidu\.com/s/[A-Za-z0-9_-]+',
    r'https?://pan\.baidu\.com/share/init\?[^\s<"\']+',
]

MOBILE_PATTERNS = [
    r'https?://yun\.139\.com/[A-Za-z0-9_-]+',
    r'https?://139\.com/[A-Za-z0-9_-]+',
]

CODE_PATTERNS = [
    r'(?:提取码|提取密码|密码|code)[：:\s]*([A-Za-z0-9]{4})',
    r'(?:pwd|password)[=：:\s]*([A-Za-z0-9]{4})',
]

def extract_links(text):
    """从文本中提取百度网盘和移动云盘链接"""
    if not text:
        return {}

    result = {
        "baidu_link": None,
        "baidu_code": None,
        "mobile_link": None,
        "mobile_code": None,
    }

    # 提取百度网盘链接
    for pattern in BAIDU_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["baidu_link"] = match.group(0)
            break

    # 提取移动云盘链接
    for pattern in MOBILE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["mobile_link"] = match.group(0)
            break

    # 提取提取码
    if result["baidu_link"]:
        for pattern in CODE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["baidu_code"] = match.group(1)
                break

    if result["mobile_link"]:
        for pattern in CODE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["mobile_code"] = match.group(1)
                break

    return result

def has_valid_link(text):
    """检查文本是否包含有效的百度或移动云盘链接"""
    links = extract_links(text)
    return bool(links.get("baidu_link") or links.get("mobile_link"))
