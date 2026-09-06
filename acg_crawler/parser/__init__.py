"""网盘链接提取模块"""
import re

BAIDU_PATTERNS = [
    r'https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<"\']*)?',
    r'https?://pan\.baidu\.com/share/init\?[^\s<"\']+',
    r'https?://yun\.baidu\.com/s/[A-Za-z0-9_-]+',
]

MOBILE_PATTERNS = [
    r'https?://yun\.139\.com/[A-Za-z0-9_/]+',
    r'https?://139\.com/[A-Za-z0-9_/]+',
    r'mobilecloud\.139\.cn[^\s<"\']*',
]

CODE_PATTERNS = [
    r'(?:提取码|提取密码|密码|pwd)[：:=\s]*([A-Za-z0-9]{4})',
    r'[?&]pwd=([A-Za-z0-9]{4})',
]

CLOUD_NAME_PATTERN = re.compile(
    r'(?:百度网盘|移动云盘|百度云|移动云)\s*[:：]\s*([A-Za-z0-9]+)',
    re.IGNORECASE,
)

CHEAT_CODE_PATTERN = re.compile(
    r'作弊码[：:\s]*(\S+)',
    re.IGNORECASE,
)

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
            url = match.group(0)
            # 标准化链接格式
            if "/share/init?" in url:
                # 从 init 链接提取 surl
                surl_match = re.search(r'surl=([A-Za-z0-9_-]+)', url)
                if surl_match:
                    url = f"https://pan.baidu.com/s/{surl_match.group(1)}"
            result["baidu_link"] = url
            break

    # 提取移动云盘链接
    for pattern in MOBILE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            result["mobile_link"] = url
            break

    # 提取百度提取码
    if result["baidu_link"]:
        # 从链接本身提取
        pwd_match = re.search(r'[?&]pwd=([A-Za-z0-9]{4})', result["baidu_link"])
        if pwd_match:
            result["baidu_code"] = pwd_match.group(1)
        else:
            # 从文本中提取
            for pattern in CODE_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["baidu_code"] = match.group(1)
                    break

    # 提取移动云盘提取码
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


def extract_cloud_name(text):
    """从内容中提取网盘文件名（如 C156222）"""
    if not text:
        return ""
    match = CLOUD_NAME_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return ""


def extract_cheat_code(title, content):
    """从内容中提取作弊码（标题含'作弊码'时才提取）"""
    if not content:
        return ""
    if "作弊码" not in (title or ""):
        return ""
    match = CHEAT_CODE_PATTERN.search(content)
    if match:
        return match.group(1).strip()
    return ""
