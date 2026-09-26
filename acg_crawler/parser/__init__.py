"""网盘链接提取模块"""
import re
import html as _html

BAIDU_PATTERNS = [
    r'https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<"\']*)?',
    r'https?://pan\.baidu\.com/share/init\?[^\s<"\']+',
    r'https?://yun\.baidu\.com/s/[A-Za-z0-9_-]+',
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
    """从文本中提取百度网盘链接（自动反转义HTML实体）。

    保留旧接口语义：从全文中取**一条**百度链接（取最先匹配到的）。
    新代码建议改用 :func:`extract_links_multi`，可以保留每个网盘下 PC/安卓双链接。
    移动云盘已于 2026-09-24 下线，不再采集（mobile_* 字段保留但恒为 None）。
    """
    if not text:
        return {}

    # 处理HTML转义：& " 等
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

    return result


# 云名前缀：用于识别每条链接对应的平台标记
# 形如 PCC148888 / AZC148888 / PCC148888 / PCCC148888 / AC148888 / PC148888 等
_CLOUD_NAME_TOKEN_RE = re.compile(
    r'\b(?P<prefix>(?:PCC|PC|pc|Pc|AZC|AZ|az|Az|ACC|AC|ac)(?:C|c)?)'
    r'(?P<num>\d{4,})\b'
)


def _split_link_blocks(text):
    """将正文按"链接 + 紧邻上文云名标签"切成块。

    站点的常见排版是::

        百度网盘：PCC148888
        链接:
        https://pan.baidu.com/s/xxx
        提取码: e3th
        百度网盘：AZC148888
        ...

    返回 ``[{"label": str|None, "url": str, "code": str|None, "start": int, "end": int}, ...]``。
    """
    if not text:
        return []

    blocks = []
    for pattern in BAIDU_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            blocks.append({"url": m.group(0), "start": m.start(), "end": m.end()})

    if not blocks:
        return []

    blocks.sort(key=lambda b: b["start"])
    deduped = []
    seen = set()
    for b in blocks:
        if b["url"] in seen:
            continue
        seen.add(b["url"])
        deduped.append(b)

    for b in deduped:
        # 标签行：从 URL 前 ~120 字符里找最近的云名
        ctx_start = max(0, b["start"] - 120)
        context = text[ctx_start:b["start"]]
        label = None
        for lm in _CLOUD_NAME_TOKEN_RE.finditer(context):
            label = lm.group(0).upper()
        b["label"] = label

        # 提取码：先看链接自身 pwd=xxx，再从 URL 之后 30 字符里找"提取码: xxxx"
        # 注意窗口要小，避免跨段误取上一条链接的提取码
        code = None
        pwd_match = re.search(r'[?&]pwd=([A-Za-z0-9]{4})', b["url"])
        if pwd_match:
            code = pwd_match.group(1)
        else:
            after_ctx = text[b["end"]:b["end"] + 40]
            cm = re.search(r'提取(?:码|密码)?\s*[:：]?\s*([A-Za-z0-9]{4})', after_ctx)
            if cm:
                code = cm.group(1)
        b["code"] = code

    return deduped


def _classify_platform_by_label(label):
    """根据云名标签分类平台：``PC/CPC/PCC`` → ``pc``，``AZ/AZC`` → ``android``，其他 ``unknown``。"""
    if not label:
        return "unknown"
    upper = label.upper()
    if upper.startswith("PC"):
        return "pc"
    if upper.startswith("AZ"):
        return "android"
    return "unknown"


def _is_baidu(url):
    if not url:
        return False
    u = url.lower()
    return ("pan.baidu.com" in u) or ("yun.baidu.com" in u)


def extract_links_multi(text):
    """提取帖子中**全部**百度云盘下载项并标记每条链接对应的平台。

    移动云盘已于 2026-09-24 下线，不再采集（mobile_* 字段保留但恒为 None）。

    返回结构::

        {
            "items": [
                {"provider": "baidu",
                 "url": "...",
                 "code": "..." | None,
                 "platform": "pc"|"android"|"unknown",
                 "label": "PCC148888" | None},
                ...
            ],
            "baidu_link": ...,   "baidu_code": ...,
            "baidu_pc": ...,     "baidu_pc_code": ...,
            "baidu_android": ..., "baidu_android_code": ...,
            "mobile_link": ...,  "mobile_code": ...,
            "mobile_pc": ...,    "mobile_pc_code": ...,
            "mobile_android": ..., "mobile_android_code": ...,
        }
    """
    if not text:
        return _empty_multi_result()

    text = _html.unescape(text)
    blocks = _split_link_blocks(text)

    items = []
    seen = set()
    for b in blocks:
        url = b["url"]
        if "/share/init?" in url:
            surl_match = re.search(r'surl=([A-Za-z0-9_-]+)', url)
            if surl_match:
                url = f"https://pan.baidu.com/s/{surl_match.group(1)}"

        if not _is_baidu(url):
            continue

        key = ("baidu", url)
        if key in seen:
            continue
        seen.add(key)

        platform = _classify_platform_by_label(b.get("label"))
        items.append({
            "provider": "baidu",
            "url": url,
            "code": b.get("code"),
            "platform": platform,
            "label": b.get("label"),
        })

    return _aggregate_multi(items)


def _empty_multi_result():
    return {
        "items": [],
        "baidu_link": None, "baidu_code": None,
        "baidu_pc": None, "baidu_pc_code": None,
        "baidu_android": None, "baidu_android_code": None,
        "mobile_link": None, "mobile_code": None,
        "mobile_pc": None, "mobile_pc_code": None,
        "mobile_android": None, "mobile_android_code": None,
    }


def _aggregate_multi(items):
    """从 items 中汇总出兼容字段（每个网盘保留一条链接 + 每平台各一条）。"""
    result = _empty_multi_result()
    result["items"] = items

    buckets = {
        "baidu": {"pc": [], "android": [], "unknown": []},
    }
    for it in items:
        bucket = buckets.get(it["provider"])
        if not bucket:
            continue
        bucket[it["platform"]].append(it)

    first_baidu = next((i for i in items if i["provider"] == "baidu"), None)
    if first_baidu:
        result["baidu_link"] = first_baidu["url"]
        result["baidu_code"] = first_baidu["code"]

    for provider, key, code_key in [
        ("baidu", "baidu_pc", "baidu_pc_code"),
        ("baidu", "baidu_android", "baidu_android_code"),
    ]:
        plat = "pc" if key.endswith("_pc") else "android"
        candidates = buckets[provider][plat] or buckets[provider]["unknown"]
        if candidates:
            first = candidates[0]
            result[key] = first["url"]
            result[code_key] = first["code"]

    return result


def has_valid_link(text):
    """检查文本是否包含有效的百度网盘链接（移动云盘已下线）"""
    res = extract_links(text)
    return bool(res.get("baidu_link"))


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


# 匹配形如 【PCC148888】 / 【AZC148888】 / 【PCC 148888】 / 【CCC148888】 / 【C148888】 / 【AC148888】
# 前面会被替换为统一格式 【C148888】（去掉 PC/AZ/CC 等平台/网盘前缀）
_CLOUD_NAME_BRACKET_RE = re.compile(
    r'[\[【]\s*'
    r'(?P<prefix>(?:PCC|PC|pc|Pc|AZC|AZ|az|Az|ACC|AC|ac|CCC|cc)(?:C|c)?)'
    r'\s*'
    r'(?P<num>\d{4,})'
    r'\s*[\]】]'
)


def fix_title_cloud_name(title):
    """规范化标题中的网盘云名标签：``【PCC148888】/【AZC148888】 → 【C148888】``。

    原站点的命名规则是把平台前缀拼到云名前：PC 版本前缀是 ``PCC``，安卓版本前缀是 ``AZC``。
    标题里只需要保留纯云名 ``C148888``，避免显示冗余的平台信息。
    """
    if not title:
        return title

    def _replace(m):
        num = m.group("num")
        return f"【C{num}】"

    title = _CLOUD_NAME_BRACKET_RE.sub(_replace, title)
    return title


# ======================================================================
# 标题归一化管线（2026-09-26 重写）
#
# 用户要求（本轮）：
#   1. 所有"游离标签"（AI汉化/汉化/官中/步兵/更新/DLC/存档…）必须收进最前面的【】，
#      不能留在标题中段；
#   2. 平台+大小必须合成一个括号【PC+安卓 1.70G】，不能拆成【1.70G】【PC+安卓盖世】；
#   3. "更新"这类词要放开头【】里，不能跑到平台/大小括号里；
#   4. 标题里出现两个"数字编号"（帖子ID）时，只保留最新的那个（较大值），
#      并且统一放到标题最末尾。
# ======================================================================

# 游离标签词表（顺序有讲究：长的在前面，避免"内嵌AI汉化版"被"汉化"先吃掉）
STRAY_TAG_PATTERNS = [
    r'内嵌(?:AI)?汉化(?:版)?',
    r'(?:动态)?AI汉化(?:版)?',
    r'AI汉化版',
    r'半AI汉化',
    r'官方中文(?:步兵版|正式版|版)?',
    r'官中步兵版',
    r'官中(?:步兵)?(?:版)?',
    r'官方中文',
    r'民间汉化(?:版)?',
    r'完整汉化(?:版)?',
    r'完全汉化(?:版)?',
    r'精翻汉化(?:版)?',
    r'汉化(?:版)?',
    r'步兵(?:版)?',
    r'去码(?:版|步兵版)?',
    r'破解(?:版)?',
    r'全CG存档',
    r'全CG',
    r'全回想',
    r'存档(?:版)?',
    r'动态(?:版)?',
    r'重制版',
    r'DL官方中文版',
    r'DL版',
    r'steam(?:官方中文)?(?:步兵版|版)?',
    r'中文(?:版)?',
    r'完全版',
    r'豪华版',
    r'追加(?:版)?',
    r'DLC\d*',
    r'更新',
    r'新作',
]
_STRAY_TAG_RE = re.compile('|'.join(f'(?:{p})' for p in STRAY_TAG_PATTERNS), re.IGNORECASE)
# 收进开头【】时要去掉的冗余前缀（"DL官方中文版" → "官方中文版"）
_TAG_NOISE_PREFIX_RE = re.compile(r'^(?:DL|STEAM|Steam)\s*', re.IGNORECASE)

# 开头标签括号：【xxx】 或 [xxx]
_HEAD_BRACKET_RE = re.compile(r'^\s*[【\[]([^】\]]+)[】\]]\s*')
# 平台+大小的括号，三种形态都要认：
#   【PC+安卓 1.70G】  【PC+安卓盖世 1.70G】  【PC+安卓/1.70G】
#   【1.70G】+ 后面的【PC+安卓盖世】  → 后一种由 _merge_size_bracket 处理
_SIZE_BRACKET_RE = re.compile(
    r'[【\[]\s*'
    r'(?P<plat>(?:PC|pc|安卓|Android|android|双端)?'
    r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
    r'\s*(?P<extra>盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?'
    r'\s*[/\s]\s*'
    r'(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)'
    r'\s*[】\]]',
    re.IGNORECASE)
# 纯大小括号：【1.70G】 / [1.70G]
_SIZE_ONLY_BRACKET_RE = re.compile(
    r'[【\[]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]]', re.IGNORECASE)
# 纯平台括号：【PC+安卓盖世】
_PLAT_ONLY_BRACKET_RE = re.compile(
    r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
    r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
    r'\s*(?P<extra>盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?\s*[】\]]',
    re.IGNORECASE)
# 尾部裸数字（帖子编号）
# 注意：必须要求数字前是"空白/开头"或"】结束"，否则 "存档16661" 这种
# 文字和数字粘在一起的情况会被误当成编号切掉
_TRAILING_NUMS_RE = re.compile(r'(?:(?<=[\s】\]])|^)((?:\d{4,7}[\s]+)*\d{4,7})\s*$')


def _norm_plat(plat):
    """平台词归一化：pc→PC，android→安卓，保留 + 连接顺序（PC 在前）"""
    if not plat:
        return ""
    has_pc = bool(re.search(r'pc', plat, re.IGNORECASE))
    has_az = ("安卓" in plat) or bool(re.search(r'android', plat, re.IGNORECASE))
    if has_pc and has_az:
        return "PC+安卓"
    if has_pc:
        return "PC"
    if has_az:
        return "安卓"
    return ""


def _build_size_bracket(plat, extra, size):
    """拼装【平台(空格)后缀(空格)大小】。

    规则：平台和后缀之间不留空格（"PC+安卓盖世"），后缀和大小之间留空格
    （用户截图写法："【PC+安卓 2.64G】"、"【PC+安卓盖世 1.70G】"）。
    plat 为空时不要留下多余前导空格。
    """
    plat = _norm_plat(plat or "")
    extra = (extra or "").strip()
    size = re.sub(r'\s+', '', size or "")
    head = f"{plat}{extra}" if (plat and extra) else (plat or extra)
    return f"【{head} {size}】" if head else f"【{size}】"


def merge_size_brackets(title):
    """把被拆开的 "【大小】+【平台】" 合并成一个【平台 大小】。

    用户举例：``【1.70G】【PC+安卓盖世】`` → ``【PC+安卓盖世 1.70G】``
    已经写对的 ``【PC+安卓 2.64G】`` 原样保留。
    """
    if not title:
        return title
    # 形态一：大小在前，平台在后
    title = re.sub(
        r'[【\[]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]][\s]*'
        r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
        r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
        r'\s*(?P<extra>盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?\s*[】\]]',
        lambda m: _build_size_bracket(m.group("plat"), m.group("extra"), m.group("size")),
        title, flags=re.IGNORECASE)
    # 形态二：平台在前，大小在后（【PC+安卓盖世】【1.70G】）
    title = re.sub(
        r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
        r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
        r'\s*(?P<extra>盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?\s*[】\]][\s]*'
        r'[【\[]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]]',
        lambda m: _build_size_bracket(m.group("plat"), m.group("extra"), m.group("size")),
        title, flags=re.IGNORECASE)
    return title


def normalize_platform_bracket(title):
    """平台+大小括号内部归一：``【PC+安卓盖世/1.70G】`` → ``【PC+安卓盖世 1.70G】``"""
    if not title:
        return title
    return _SIZE_BRACKET_RE.sub(
        lambda m: _build_size_bracket(m.group("plat"), m.group("extra"), m.group("size")),
        title)


def _split_head_tags(title):
    """拆出开头的【标签】正文，返回 (标签列表, 剩余标题)"""
    m = _HEAD_BRACKET_RE.match(title or "")
    if not m:
        return [], (title or "")
    tags = [x.strip() for x in re.split(r'[/／]', m.group(1)) if x.strip()]
    return tags, title[m.end():]


def _join_head_tags(tags):
    return "【" + "/".join(tags) + "】"


# 开头连续两个标签括号之间的连接词（"【汉化版/动态】新 【日式ADV】" 里的"新"）
_OPEN_BR = r'[【\[]'
_CLOSE_BR = r'[】\]]'
_HEAD_TAG_LINK_RE = re.compile(
    r'^\s*' + _OPEN_BR + r'([^】\]]+)' + _CLOSE_BR + r'\s*(?P<link>[\u4e00-\u9fff]{0,3})\s*'
    + _OPEN_BR + r'([^】\]]+)' + _CLOSE_BR)


def _looks_like_tags(segs):
    """判断一组片段是不是"标签"（而不是游戏名）。

    标签特征：短（≤6 字）、基本是中文、不含数字/英文/书名号/括号，
    或本身就是已知标签词（AI汉化版、全CG存档…）。
    """
    if not segs:
        return False
    for s in segs:
        if _STRAY_TAG_RE.fullmatch(s):
            continue
        if len(s) > 6:
            return False
        if re.search(r'[\dA-Za-z《》〈〉「」（）()\[\]【】]', s):
            return False
        # 纯中日文短词才算
        if not re.fullmatch(r'[\u4e00-\u9fff]+', s):
            return False
    return True


def merge_head_tag_brackets(title):
    """合并开头相邻的两个标签括号。

    ACG游戏姬等站点原文形如 ``【汉化版/动态】新 【日式ADV/ 】游戏名…``，
    两个括号其实都是标签，应并成一个 ``【汉化版/动态/新/日式ADV】``。

    注意：第二段必须"长得像标签"才并 —— 像 ``【PC/官中/SLG/去码版】【H版杀戮之塔】``
    里的 ``【H版杀戮之塔】`` 是游戏名，不能并进来。
    """
    if not title:
        return title
    m = _HEAD_TAG_LINK_RE.match(title)
    if not m:
        return title
    a = [x.strip() for x in re.split(r'[/／]', m.group(1)) if x.strip()]
    link = (m.group("link") or "").strip()
    b = [x.strip() for x in re.split(r'[/／]', m.group(3)) if x.strip()]
    # 第二段必须是"标签样"，否则别乱并
    if not _looks_like_tags(b):
        return title
    tags = a + ([link] if link else []) + b
    tags = _tag_dedupe(tags)
    return _join_head_tags(tags) + title[m.end():]


def normalize_platform_only_bracket(title):
    """只有平台没大小的括号也归一：``【PC+安卓mtool】`` → ``【PC+安卓 mtool】``

    这类写法在 ACG俱乐部 很常见（"【PC+安卓盖世】"），平台词后缀要紧贴平台，
    中间不留空格，和带体积时的写法保持一致。
    """
    if not title:
        return title

    def _fix(m):
        plat = _norm_plat(m.group("plat"))
        extra = (m.group("extra") or "").strip()
        head = f"{plat}{extra}" if (plat and extra) else (plat or extra)
        return f"【{head}】"

    return _PLAT_ONLY_BRACKET_RE.sub(_fix, title)


def _tag_dedupe(tags):
    """标签去重：已经存在 "AI汉化版" 时不再加 "AI汉化"（反之亦然）"""
    out = []
    for t in tags:
        base = re.sub(r'(版|步兵版)$', '', t)
        if any(re.sub(r'(版|步兵版)$', '', x) == base for x in out):
            # 保留更长的那一个（"AI汉化版" 比 "AI汉化" 信息更全）
            for i, x in enumerate(out):
                if re.sub(r'(版|步兵版)$', '', x) == base and len(t) > len(x):
                    out[i] = t
            continue
        out.append(t)
    return out


def dedupe_head_tags(title):
    """对开头【】里的标签去重：``【SLG/官中/3D动态/官中版】`` → ``【SLG/官中版/3D动态】``。

    站点原文（尤其旧数据）常有 "官中" 和 "官中版" 同时出现，归拢后要去掉冗余。
    """
    if not title:
        return title
    m = _HEAD_BRACKET_RE.match(title)
    if not m:
        return title
    tags = [x.strip() for x in re.split(r'[/／]', m.group(1)) if x.strip()]
    if len(tags) < 2:
        return title
    tags = _tag_dedupe(tags)
    return _join_head_tags(tags) + title[m.end():]


def collect_stray_tags(title):
    """把标题中段游离的标签词收进开头【】。

    用户举例：``【RPG/催眠】魔法少女希尔菲娜 … AI汉化【PC+安卓mtool】``
    → ``【AI汉化/RPG/催眠】魔法少女希尔菲娜 …【PC+安卓 mtool】``

    注意：只在"开头【】之后、平台大小括号之前"的正文里找标签，
    避免把游戏名里的词（如"官中"出现在名字里）误收。
    """
    if not title:
        return title
    tags, rest = _split_head_tags(title)
    if not rest:
        return title

    # 正文区间 = 到第一个平台/大小括号为止
    stop = len(rest)
    for rex in (_SIZE_BRACKET_RE, _PLAT_ONLY_BRACKET_RE, _SIZE_ONLY_BRACKET_RE):
        m = rex.search(rest)
        if m and m.start() < stop:
            stop = m.start()
    head, tail = rest[:stop], rest[stop:]

    found = []
    def _grab(m):
        tag = m.group(0).strip()
        tag = _TAG_NOISE_PREFIX_RE.sub('', tag).strip()
        # "更新"这类词可能已被塞进平台括号里（【PC+安卓 8.46G】更新】），
        # 这种残留也要认；长度 < 2 的碎片忽略
        if len(tag) >= 2 and tag not in found:
            found.append(tag)
        return " "

    head = _STRAY_TAG_RE.sub(_grab, head)
    if not found:
        return title

    head = re.sub(r'\s{2,}', ' ', head).strip()
    head = re.sub(r'^[\s\-–—·.。、+,，+＋]+', '', head).strip()
    for tag in found:
        if tag not in tags:
            tags.append(tag)
    tags = _tag_dedupe(tags)
    return _join_head_tags(tags) + head + tail


def strip_platform_bracket_trailing_tags(title):
    """把平台/大小括号后面残留的 "更新】" 之类尾巴清掉，并把标签补进开头【】。

    用户举例：``…【PC+安卓 8.46G】更新】 14845 16612``
    → ``【更新/国风SLG/直播】…【PC+安卓 8.46G】 【16612】``

    实现：先定位"平台/大小括号"的结束位置，再看它后面紧跟的是不是一个标签词
    （可能还带一个多余的 】
    """
    if not title:
        return title
    # 找到所有"平台/大小括号"，取最后一个（标题里可能有一个开头的纯标签括号）
    last = None
    for rex in (_SIZE_BRACKET_RE, _SIZE_ONLY_BRACKET_RE):
        for m in rex.finditer(title):
            if last is None or m.end() > last.end():
                last = m
    if last is None:
        return title
    after = title[last.end():]
    m = re.match(r'[ \t]*(?P<stray>[\u4e00-\u9fff]{2,6}(?:版|CG)?)[ \t]*[】\]]?', after)
    if not m:
        return title
    stray = m.group("stray")
    if not _STRAY_TAG_RE.fullmatch(stray):
        return title
    tags, rest = _split_head_tags(title[:last.start()])
    if stray not in tags:
        tags.append(stray)
    return _join_head_tags(tags) + rest + title[last.start():last.end()] + after[m.end():]


def normalize_trailing_numbers(title):
    """标题尾部数字编号处理（用户 2026-09-26）：

    - 出现两个及以上编号时，只保留**最新**的（数值最大），其余删除；
    - 保留的那个统一加【】放到标题最末尾。

    例：``…【PC+安卓】 15342 16759`` → ``…【PC+安卓】 【16759】``
    """
    if not title:
        return title
    m = _TRAILING_NUMS_RE.search(title)
    if not m:
        return title
    nums = [int(x) for x in re.findall(r'\d{4,7}', m.group(1))]
    if not nums:
        return title
    # 站点的"帖子ID"是递增的，取最大值 = 最新那条
    latest = max(nums)
    body = title[:m.start()].rstrip()
    return f"{body} 【{latest}】"


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


# 标题开头的"裸帖子编号"：紧贴后面的【/[ 或者带空格（ACG俱乐部站点原文形如 "15395[RPG/…]…"）
_LEADING_ID_RE = re.compile(r'^\s*(?P<id>\d{4,7})\s*(?=[\[【])')
# 被抽走标签后残留的空斜杠（【触摸SLG/ 】→【触摸SLG】）
_EMPTY_SLASH_RE = re.compile(r'[/／]\s*(?=[】\]])')
# 开头括号里只剩空白/斜杠的形态
_EMPTY_HEAD_RE = re.compile(r'^\s*[【\[]\s*[/／\s]*[】\]]\s*')


def _pull_leading_id(title):
    """把标题开头的裸帖子编号摘出来，返回 (编号 or None, 去掉编号后的标题)。

    站点原文形如 ``15395[RPG/百合/纯爱]…``：编号紧贴【】，会挡住
    `_HEAD_BRACKET_RE` 对开头标签括号的识别，导致标签被从中段"掏走"。
    先摘掉编号，让归一化管线正常工作，最后再当作尾部编号统一处理。
    """
    if not title:
        return None, title
    m = _LEADING_ID_RE.match(title)
    if not m:
        return None, title
    return int(m.group("id")), title[m.end():].lstrip()


def normalize_title(title):
    """标题归一化总入口（各站点 parse_detail 末尾统一调用）。

    管线顺序不能乱：
      0. 摘掉开头的裸帖子编号          —— "15395【RPG…】" → 编号暂存，末尾统一处理
      1. []→【】、斜杠换空格          —— 先把括号形态统一，后面正则才好写
      2. 合并被拆开的 大小/平台 括号   —— 【1.70G】【PC+安卓盖世】→【PC+安卓盖世 1.70G】
      3. 平台括号内部归一              —— 【PC+安卓盖世/1.70G】→【PC+安卓盖世 1.70G】
      4. 清掉平台括号后面的"更新】"残留 + 补进开头【】
      5. 把中段游离标签收进开头【】    —— …AI汉化【PC+安卓】→【AI汉化/…】…【PC+安卓】
      6. 尾部编号只留最新一个，加【】  —— … 15342 16759 → …【16759】
      7. 云名前缀归一                  —— 【PCC148888】→【C148888】
    """
    if not title:
        return title
    lead_id, title = _pull_leading_id(title)
    title = fix_title_brackets(title)
    title = fix_title_slash(title)
    title = merge_size_brackets(title)
    title = normalize_platform_bracket(title)
    title = normalize_platform_only_bracket(title)
    title = strip_platform_bracket_trailing_tags(title)
    title = merge_head_tag_brackets(title)
    title = collect_stray_tags(title)
    title = collect_stray_tags(title)      # 跑第二遍：前一步把括号换位置后可能露出新的游离标签
    title = merge_head_tag_brackets(title)
    title = dedupe_head_tags(title)
    title = _prune_empty_tag_slots(title)
    # 开头摘下的编号补回尾部，参与"只留最新"的位次判断
    if lead_id is not None:
        title = f"{title.rstrip()} {lead_id}"
    title = normalize_trailing_numbers(title)
    title = fix_title_cloud_name(title)
    title = _prune_empty_tag_slots(title)
    title = re.sub(r'\s{2,}', ' ', title).strip()
    return title


def _prune_empty_tag_slots(title):
    """清掉标签被抽走后留下的空洞：``【触摸SLG/ 】`` → ``【触摸SLG】``。

    同时处理整块变空的 ``【/】``（直接删掉），以及旧数据里的
    ``【PC+安卓/2.4G/ ``（缺右括号、用斜杠分隔平台与大小）这类残缺括号。
    """
    if not title:
        return title
    # 已闭合的 【平台/大小】 → 【平台 大小】（旧数据里斜杠当分隔符）
    title = re.sub(
        r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
        r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
        r'\s*[/／]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)'
        r'\s*[/／\s]*[】\]]',
        lambda m: f"【{_norm_plat(m.group('plat'))} "
                  f"{re.sub(r'\\s+', '', m.group('size'))}】",
        title, flags=re.IGNORECASE)
    # 残缺括号：全角【开头但后面没有】、且内含 平台/大小 → 补成规范形式
    title = re.sub(
        r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
        r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
        r'\s*[/／]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)'
        r'\s*[/／\s]*(?![^【\[]*[】\]])',
        lambda m: f"【{_norm_plat(m.group('plat'))} "
                  f"{re.sub(r'\\s+', '', m.group('size'))}】",
        title, flags=re.IGNORECASE)
    title = _EMPTY_SLASH_RE.sub('', title)
    title = re.sub(r'[【\[]\s*[/／]\s*([^】\]]+)[】\]]', r'【\1】', title)
    title = _EMPTY_HEAD_RE.sub('', title)
    title = re.sub(r'[【\[]\s*[/／、,，+＋]+\s*[】\]]', '', title)
    # 重复的右括号
    title = re.sub(r'[】\]]\s*[】\]]', '】', title)
    return title


# ======================================================================
# 体积过滤（全站统一，2026-09-26 用户要求：10G 以内的游戏才爬，超出自动过滤）
# ======================================================================

MAX_SIZE_GB = 10.0
_SIZE_TEXT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(TB|GB|MB|KB|G|M|K)\b', re.IGNORECASE)
_UNIT_TO_GB = {
    "TB": 1024.0, "GB": 1.0, "MB": 1.0 / 1024, "KB": 1.0 / 1024 / 1024,
    "G": 1.0, "M": 1.0 / 1024, "K": 1.0 / 1024 / 1024,
}


def size_to_gb(text):
    """从 "1.70G" / "510M" / "2.64GB" 这类文本里取体积，换算成 GB。
    解析不出来返回 None（表示"无法判断"，不做过滤，避免误杀）。
    """
    if not text:
        return None
    m = _SIZE_TEXT_RE.search(str(text))
    if not m:
        return None
    try:
        return float(m.group(1)) * _UNIT_TO_GB[m.group(2).upper()]
    except (ValueError, KeyError):
        return None


# 标题里所有"平台/大小"括号，用来抽取体积
_TITLE_SIZE_RE = re.compile(
    r'[【\[]\s*(?:PC|pc|安卓|Android|android|双端)?'
    r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*'
    r'\s*(?:盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?'
    r'\s*[/\s]\s*(\d+\.?\d*\s*[GMgm][Bb]?)'
    r'\s*[】\]]',
    re.IGNORECASE)
# 纯大小括号
_TITLE_SIZE_ONLY_RE = re.compile(
    r'[【\[]\s*(\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]]', re.IGNORECASE)


def extract_title_size(title):
    """从改写后的标题里取体积文本（如 "1.70G"），取不到返回 ""。"""
    if not title:
        return ""
    for rex in (_TITLE_SIZE_RE, _TITLE_SIZE_ONLY_RE):
        m = rex.search(title)
        if m:
            return re.sub(r'\s+', '', m.group(1))
    return ""


def oversize_reason(title):
    """标题体积超过 MAX_SIZE_GB 时返回原因文本，否则返回 None。

    爬取阶段用它统一过滤：超出的游戏整条不入库（用户 2026-09-26 要求）。
    体积提不出来（None）时不过滤，避免站点写法变化导致大面积误杀。
    """
    size_text = extract_title_size(title)
    gb = size_to_gb(size_text)
    if gb is not None and gb > MAX_SIZE_GB:
        return f"体积 {size_text} 超过 {MAX_SIZE_GB:g}G 上限"
    return None


# ======================================================================
# 游戏名提取（2026-09-26 用户要求：卡片上加「游戏名」按钮，点一下复制）
#
# 用户要的格式举例：``药丸王【PC+安卓 8.80G】``
#   —— 游戏名 + 平台/大小括号（这正是该游戏在百度网盘里的名字，方便去网盘里找）
# 做法：把标题拆开，剥掉开头【标签】、尾部【编号】、尾部平台括号，
#       剩下的中间部分就是游戏名，再把平台/大小括号拼回去。
# ======================================================================

# 尾部「平台 大小」括号（带大小），用于回拼
_GAME_SIZE_BRACKET_RE = re.compile(
    r'[【\[]\s*(?:PC|pc|安卓|Android|android|双端)'
    r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*'
    r'\s*(?:盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?'
    r'\s*[\s/／]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]]',
    re.IGNORECASE)
# 纯平台括号（无大小），用于回拼（如 kup 的 【PC】）
_GAME_PLAT_ONLY_RE = re.compile(
    r'[【\[]\s*(?P<plat>(?:PC|pc|安卓|Android|android|双端)'
    r'(?:\s*[+＋&、]\s*(?:PC|pc|安卓|Android|android))*)'
    r'\s*(?P<extra>盖世|joi|JOI|joiplay|mtool|MTool|mTool|吉里吉里|krkr|KRKR)?\s*[】\]]',
    re.IGNORECASE)
# 纯体积括号
_GAME_SIZE_ONLY_RE = re.compile(
    r'[【\[]\s*(?P<size>\d+\.?\d*\s*[GMgm][Bb]?)\s*[】\]]', re.IGNORECASE)
# 尾部【编号】（纯数字）
_TRAILING_ID_BRACKET_RE = re.compile(r'\s*[【\[]\s*[A-Za-z]{0,2}\d{4,7}\s*[】\]]\s*$')
# 版本号尾巴（v0.37 / 1.0.2 / 0.4.2b 等），提取游戏名时要留着
_VERSION_TAIL_RE = re.compile(r'\s*(?:v|V|Ver\.?|版本)?\s*\d+(?:\.\d+)+[a-zA-Z]?\s*$')


def extract_game_name(title):
    """从归一化后的标题里抽出「游戏名【平台 大小】」。

    举例：
        '【更新/欧美SLG/动态/汉化版】药丸王 Pill King v0.37【PC+安卓 8.80G】 【C224444】'
        → '药丸王 Pill King v0.37【PC+安卓 8.80G】'

        '真·恋姬†无双～萌将传～ 【PC+安卓】【PC】【简体中文】'
        → '真·恋姬†无双～萌将传～【PC+安卓】'

    取不到平台括号时，只返回游戏名本体（不硬编造）。
    """
    if not title:
        return ""
    t = title.strip()

    # 1) 摘掉结尾的【编号】（如 【C224444】 / 【16759】）
    t = _TRAILING_ID_BRACKET_RE.sub('', t).strip()

    # 2) 取出「平台 大小」括号内容，并从标题里删掉它
    plat_size = ""
    m = _GAME_SIZE_BRACKET_RE.search(t)
    if m:
        plat_size = f"【{re.sub(r'\\s+', ' ', m.group(0)[1:-1]).strip()}】"
        t = (t[:m.start()] + t[m.end():]).strip()
    else:
        # 只有体积
        m2 = _GAME_SIZE_ONLY_RE.search(t)
        if m2:
            plat_size = f"【{re.sub(r'\\s+', '', m2.group('size'))}】"
            t = (t[:m2.start()] + t[m2.end():]).strip()
        else:
            # 只有平台（如 鲲 的 【PC+安卓】）
            m3 = _GAME_PLAT_ONLY_RE.search(t)
            if m3:
                plat = _norm_plat(m3.group("plat"))
                extra = (m3.group("extra") or "").strip()
                head = f"{plat}{extra}" if (plat and extra) else (plat or extra)
                plat_size = f"【{head}】" if head else ""
                t = (t[:m3.start()] + t[m3.end():]).strip()

    # 3) 剥掉开头的【标签】（分类/AI汉化/更新…）
    t = _HEAD_BRACKET_RE.sub('', t).strip()

    # 4) 清理尾部残留的其它括号（如末尾的【简体中文】【附全CG存档】）
    #    只清"明显是标签/说明"的短括号，保留游戏名里的括号
    for _ in range(4):
        m = re.search(r'[【\[]([^【】\]]{1,12})[】\]]\s*$', t)
        if not m:
            break
        inner = m.group(1).strip()
        # 看起来像游戏名一部分的（含书名号/括号/较长的）就保留
        if len(inner) > 10 or re.search(r'[《》〈〉「」]', inner):
            break
        t = t[:m.start()].strip()

    # 5) 去掉首尾杂符
    t = t.strip(' -–—·.。、,，/／')
    if not t:
        return ""
    return f"{t}{plat_size}"


def game_name_from_title(title):
    """对外别名：给卡片/导出用，拿不到时回退到原标题。"""
    name = extract_game_name(title)
    return name or (title or "")
