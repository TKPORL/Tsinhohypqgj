"""网盘链接提取模块"""
import re
import html as _html

BAIDU_PATTERNS = [
    r'https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<"\']*)?',
    r'https?://pan\.baidu\.com/share/init\?[^\s<"\']+',
    r'https?://yun\.baidu\.com/s/[A-Za-z0-9_-]+',
]

MOBILE_PATTERNS = [
    r'https?://yun\.139\.com/[^\s<"\']*',
    r'https?://139\.com/[^\s<"\']*',
    r'mobilecloud\.139\.cn[^\s<"\']*',
]

CODE_PATTERNS = [
    r'(?:提取码|提取密码|密码|pwd)[：:=\s]*([A-Za-z0-9]{4})',
    r'[?&]pwd=([A-Za-z0-9]{4})',
]

CLOUD_NAME_PATTERNS = [
    # 匹配 "分享文件：XXXX" 和 "通过网盘分享的文件：XXXX" 格式
    re.compile(r'分享文件[：:]\s*([A-Za-z0-9]+)', re.IGNORECASE),
    re.compile(r'通过(?:百度|移动|阿里)?网盘分享的文件[：:]\s*([A-Za-z0-9]+)', re.IGNORECASE),
    re.compile(r'分享的文件[：:]\s*([A-Za-z0-9]+)', re.IGNORECASE),
    # 百度网盘：XXXX（排除URL，只匹配纯文件名）
    re.compile(r'(?:百度网盘|移动云盘|百度云|移动云)\s*[:：]\s*(?!https?://)([A-Za-z0-9]{4,})', re.IGNORECASE),
    re.compile(r'文件[名码称]\s*[:：]?\s*(?!https?://)([A-Za-z0-9]{4,})', re.IGNORECASE),
]

CHEAT_CODE_PATTERN = re.compile(
    r'作弊码[：:\s]*[\n\r\s|]*(\d{4,})',
    re.IGNORECASE,
)

def extract_links(text):
    """从文本中提取百度网盘和移动云盘链接（自动反转义HTML实体）"""
    if not text:
        return {}

    # 处理HTML转义：&amp; &quot; 等
    text = _html.unescape(text)

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
    """从内容中提取网盘文件名（如 C156222, 24917, A1326）"""
    if not text:
        return ""
    for pattern in CLOUD_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            if len(name) >= 3:
                return name
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


# 标签词：标题中平台/大小前面需要移到开头[]的词
EXTRA_TAG_PATTERNS = [
    r'(?:动态)?AI汉化(?:版)?',
    r'动态(?:AI)?喊话(?:版)?',
    r'官中(?:步兵)?(?:版)?',
    r'步兵(?:版)?',
    r'存档(?:版)?',
    r'全CG',
    r'生肉',
    r'汉化(?:版)?',
    r'官中',
    r'动态(?:版)?',
    r'内嵌(?:AI)?汉化(?:版)?',
    r'steam版',
    r'DLC',
    r'中文(?:版)?',
]
_EXTRA_TAG_RE = re.compile('|'.join(f'(?:{p})' for p in EXTRA_TAG_PATTERNS), re.IGNORECASE)


def fix_title_slash(title):
    """修复标题中平台和大小之间的斜杠：[PC/3.87G]→[PC 3.87G]"""
    if not title:
        return title
    # 同时处理【】和[]，支持MG/GM等变体
    title = re.sub(
        r'([\[【])(PC\+安卓|PC|安卓|android)/(\d+\.?\d*\s*[GMgm][Bb]?[Bb]?)([\]】])',
        r'\1\2 \3\4',
        title,
        flags=re.IGNORECASE
    )
    return title


def fix_title_brackets(title):
    """把标题中所有 [] 改为 【】"""
    if not title:
        return title
    title = title.replace('[', '【').replace(']', '】')
    return title


def fix_title_tags(title):
    """自动检测标题中平台/大小前面的额外标签，移到开头【】。

    例: 【SLG/动态】游戏名 官中版【PC 548M】 → 【SLG/动态/官中版】游戏名【PC 548M】
    也处理: 游戏名 步兵版】PC+安卓/517MG】 → 【步兵版】游戏名【PC+安卓 517MG】
    """
    if not title:
        return title

    # 修复格式: "标签名】平台/大小】" → 把标签移到开头【】
    # 匹配: 中文词+】+平台信息
    stray_tag = re.search(r'([\u4e00-\u9fff]{2,6}(?:版|CG)?)[】\]]\s*([\[【]?)', title)
    if stray_tag:
        tag_text = stray_tag.group(1)
        before = title[:stray_tag.start()]

        # 检查】是否在【...】括号对内部（统计未闭合的【数量）
        open_count = before.count('【') - before.count('】')
        is_inside_bracket = open_count > 0

        # 检查】后面是否紧跟平台信息（真正的游离标签）
        after_pos = stray_tag.end()
        has_platform_after = bool(re.match(r'(?:PC|安卓|android)', title[after_pos:], re.IGNORECASE))

        if not is_inside_bracket and has_platform_after:
            # 这是一个游离的标签，移到开头
            tag_match = re.match(r'([\[【][^]】]+[\]】])', title)
            if tag_match:
                inner = tag_match.group(1).strip('[]【】')
                if tag_text not in inner:
                    inner = inner.rstrip('/') + '/' + tag_text
                new_tag = f'【{inner}】'
                # 移除游离标签
                rest = title[:stray_tag.start()] + title[stray_tag.end():]
                # 清理开头标签（同时支持【】和[]）
                rest = re.sub(r'^[[【][^]】]+[]】]\s*', '', rest)
                title = new_tag + ' ' + rest.strip()

    # 找大小括号位置（支持【】和[]，支持G/M/GB/MG）
    size_match = re.search(r'[\[【](PC\+安卓|PC|安卓|android)[/\s](\d+\.?\d*\s*[GMgm][Bb]?[Bb]?)\s*[\]】]', title, re.IGNORECASE)
    if not size_match:
        return title

    # 找开头标签括号
    tag_match = re.match(r'([\[【][^]】]+[\]】])', title)
    if not tag_match:
        return title

    tag_bracket = tag_match.group(1)
    between = title[tag_match.end():size_match.start()]

    # 在 between 中查找标签词
    found_tags = []
    remaining = between
    for m in _EXTRA_TAG_RE.finditer(between):
        tag = m.group(0)
        if len(tag) < 2:
            continue
        found_tags.append(tag)
        remaining = remaining.replace(m.group(0), '', 1)

    if not found_tags:
        return title

    # 把标签加到开头[]里
    inner = tag_bracket.strip('[]【】')
    for tag in found_tags:
        if tag not in inner:
            inner = inner.rstrip('/') + '/' + tag
    new_tag_bracket = f'【{inner}】'

    # 重建标题：清理between中的多余空格
    clean_between = re.sub(r'\s+', ' ', remaining).strip()
    clean_between = re.sub(r'^[\s\-–—·.。、]+', '', clean_between).strip()

    result = new_tag_bracket + clean_between + title[size_match.start():]
    return result
