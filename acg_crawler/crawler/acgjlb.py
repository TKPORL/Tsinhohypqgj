"""ACG俱乐部爬虫"""
import json
import re
from pathlib import Path
from crawler.base import BaseCrawler
from parser import (extract_links_multi, extract_links, extract_cloud_name, extract_cheat_code,
                    normalize_title, oversize_reason, size_to_gb, MAX_SIZE_GB)
from parser.image_handler import download_images

class ACGJLBCrawler(BaseCrawler):
    """ACG俱乐部爬虫"""

    def __init__(self, config):
        super().__init__(config)
        self.site_name = "ACG俱乐部"
        self.base_url = "https://www.acgjlb.cc"

    def get_list_page(self, page_num):
        # 该站使用 /page/N 路径分页，?page=N 实际仍返回第一页
        url = (f"{self.base_url}/acggame" if page_num == 1
               else f"{self.base_url}/acggame/page/{page_num}")
        soup = self._soup(url)
        results = []
        # ACG俱乐部使用Zibll主题，帖子在 div.item-body 容器中
        for item in soup.select("div.item-body"):
            a = item.select_one("h2.item-heading > a")
            if not a or not a.get("href"):
                continue

            link = a["href"]
            if not link.startswith("http"):
                link = self.base_url + link

            # 只保留数字ID的帖子（如 /86396.html），跳过置顶/分类帖
            if not re.search(r'/\d+\.html', link):
                continue

            # 跳过置顶帖子（标题以特定关键词开头）
            title_text = a.get_text(strip=True)
            skip_keywords = ["本站专用", "教程", "模拟器", "合集", "TOP", "解压", "冷月白狐", "必看"]
            if any(kw in title_text for kw in skip_keywords):
                continue

            # 从标签提取平台信息
            category = ""
            tag_els = item.select(".item-tags a, a[rel='tag']")
            for tag_el in tag_els:
                tag_text = tag_el.get_text(strip=True).lower()
                if tag_text in ("pc", "pc版", "windows"):
                    category = "PC"
                    break
                elif tag_text in ("安卓", "android", "az"):
                    category = "AZ"
                    break

            results.append({"url": link, "category": category})

        # 备用选择器：直接找数字ID链接
        if not results:
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if re.search(r'/\d+\.html$', href):
                    link = href if href.startswith("http") else self.base_url + href
                    if not any(r["url"] == link for r in results):
                        results.append({"url": link, "category": ""})

        return results

    def parse_detail(self, url, category=""):
        soup = self._soup(url)

        # 标题 - ACG俱乐部使用 h1.article-title
        # 站点原文形如 "15395[RPG/百合]游戏名 v1.0 AI汉化[PC+安卓]"：
        # 开头的帖子编号、方括号标签、末尾编号统一交给 normalize_title 处理
        title_el = soup.select_one("h1.article-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # 内容 - ACG俱乐部使用 div.wp-posts-content
        content_el = soup.select_one("div.wp-posts-content")
        content = content_el.get_text(separator="\n", strip=True) if content_el else ""

        # 提取图片
        images = []
        if content_el:
            for img in content_el.select("img"):
                src = img.get("data-src") or img.get("src") or ""
                if src and "loading" not in src and "avatar" not in src and "emoji" not in src:
                    if not src.startswith("http"):
                        src = self.base_url + src
                    images.append(src)

        # 提取点赞数
        likes = 0
        likes_el = soup.select_one(".content-footer-zan-cai .like-count, .meta-like")
        if likes_el:
            try:
                likes = int(re.sub(r'[^\d]', '', likes_el.get_text(strip=True)) or 0)
            except:
                pass

        # 提取发布日期
        post_date = ""
        # Zibll 主题：日期在 tooltip 的 title 属性里（title="2026年09月11日 02:59发布"）
        date_el = soup.select_one("[data-toggle='tooltip'][title*='发布']")
        if date_el:
            m = re.search(r'(\d{4})年(\d{2})月(\d{2})日', date_el.get("title", ""))
            if m:
                post_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # 提取网盘链接
        links = extract_links_multi(content)
        if not links.get("baidu_link"):  # 移动云盘已下线，只认百度
            full_text = str(soup)
            links = extract_links_multi(full_text)

        # 提取下载名追加到标题
        cloud_name = extract_cloud_name(content)
        if cloud_name and cloud_name not in title:
            title = f"{title} 【{cloud_name}】"

        # 标题归一化总入口（2026-09-26）：
        #   标签归拢进开头【】、平台/大小括号合并、更新挪位置、云名去前缀、尾部数字只留最新
        title = normalize_title(title)

        # 体积过滤：超过 10G 的游戏整条不入库（用户 2026-09-26 要求）
        reason = oversize_reason(title)
        if reason:
            return {
                "source": self.site_name,
                "source_id": url.split("/")[-1].replace(".html", "").split("?")[0],
                "source_url": url, "title": title, "platform": "unknown", "content": "",
                "images": "[]", "original_images": "[]", "post_date": post_date,
                "skip_reason": reason,
            }

        # 提取作弊码
        cheat_code = extract_cheat_code(title, content)

        # 提取解压码（ACG俱乐部固定为007721）
        unzip_code = "解压码007721"

        # 判断平台 - 优先从分类标签判断，正文标签兜底
        platform = "unknown"
        category_lower = (category or "").lower()
        title_lower = title.lower()
        content_lower = content.lower()

        if category_lower == "pc":
            platform = "pc"
        elif category_lower in ("az", "安卓", "android"):
            platform = "android"
        elif "pc+安卓" in title_lower or "pc&安卓" in title_lower or "pc/安卓" in title_lower:
            platform = "pc_android"
        elif "安卓" in title_lower:
            platform = "android"
        elif "pc" in title_lower or "steam" in title_lower:
            platform = "pc"
        else:
            # 兜底：正文中的平台标签（如 #PC #安卓）
            has_pc = "pc" in content_lower or "windows" in content_lower
            has_az = "安卓" in content_lower or "android" in content_lower
            if has_pc and has_az:
                platform = "pc_android"
            elif has_az:
                platform = "android"
            elif has_pc:
                platform = "pc"

        # 提取source_id
        source_id = url.split("/")[-1].replace(".html", "").split("?")[0]

        # 下载图片到本地（用source_id作为临时目录名）
        proxy = None
        if self.config.get("proxy", {}).get("enabled"):
            proxy = self.config["proxy"]["http"]
        import json as _json_dl
        local_images = download_images(images, source_id, proxy=proxy)
        if local_images:
            images = local_images

        return {
            "source": self.site_name,
            "source_id": source_id,
            "source_url": url,
            "title": title,
            "platform": platform,
            "content": content[:5000],
            "download_items_json": _json_dl.dumps(links.get("items", []), ensure_ascii=False),
            "likes": likes,
            "comments": 0,
            "views": 0,
            "unzip_code": unzip_code,
            "cheat_code": cheat_code,
            "baidu_link": links.get("baidu_link"),
            "baidu_code": links.get("baidu_code"),
            "mobile_link": links.get("mobile_link"),
            "mobile_code": links.get("mobile_code"),
            "images": json.dumps(images),
            "original_images": json.dumps(images),
            "post_date": post_date,
        }

    def get_total_pages(self):
        try:
            url = f"{self.base_url}/acggame"
            soup = self._soup(url)
            # ACG俱乐部使用Zibll主题分页
            page_links = soup.select("div.pagenav a, a[href*='/page/'], a[href*='page=']")
            max_page = 1
            for a in page_links:
                href = a.get("href", "")
                match = re.search(r'(?:/page/|[?&]page=)(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))
            return max_page
        except:
            return 100
