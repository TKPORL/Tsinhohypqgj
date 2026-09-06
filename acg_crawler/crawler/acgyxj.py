"""ACG游戏姬爬虫"""
import json
import re
from pathlib import Path
from crawler.base import BaseCrawler
from parser import extract_links, extract_cloud_name, extract_cheat_code
from parser.image_handler import download_images

class ACGYXJCrawler(BaseCrawler):
    """ACG游戏姬爬虫"""

    def __init__(self, config):
        super().__init__(config)
        self.site_name = "ACG游戏姬"
        self.base_url = "https://www.acgyxjvip.com"

    def get_list_page(self, page_num):
        url = f"{self.base_url}/page/{page_num}"
        soup = self._soup(url)
        results = []
        for article in soup.select("article.post-list"):
            a = article.select_one("h3.post-title a")
            if a and a.get("href"):
                link = a["href"]
                if not link.startswith("http"):
                    link = self.base_url + link

                # 从分类标签提取平台信息
                category = ""
                cat_el = article.select_one("div.category div.tags a")
                if cat_el:
                    category = cat_el.get_text(strip=True)

                results.append({"url": link, "category": category})
        return results

    def _format_title(self, title, category=""):
        """格式化标题：[新作/类型/标签] 游戏名 [PC 大小] [C码]"""
        import re as _re
        if not title:
            return title

        # 提取前缀（新作/更新/等）
        prefix = ""
        m = _re.match(r'^(新作|更新|汉化|原创)\s*', title)
        if m:
            prefix = m.group(1)
            title = title[m.end():]

        # 提取第一个 [] 里的分类标签
        tags = ""
        m = _re.match(r'[\[【]([^]】]+)[\]】]', title)
        if m:
            tags = m.group(1).replace("/", "/")
            title = title[m.end():].strip()

        # 提取下载码 [C157555] 或 [PCC155555]
        code = ""
        m = _re.search(r'\s*[\[【]([CPcp]?\d{5,})[\]】]\s*$', title)
        if m:
            code = m.group(1)
            title = title[:m.start()].strip()

        # 提取大小 [1.10G] [3.75GB] [840M] 或 683MB]
        size = ""
        m = _re.search(r'(?:[\[【])?(\d+\.?\d*\s*[GMgm][Bb]?)(?:[\]】])?\s*(?:[\[【][CPcp]?\d{5,}[\]】])?\s*$', title)
        if m:
            size = m.group(1)
            title = title[:m.start()].strip()

        # 构建新标题
        parts = []
        if prefix or tags:
            tag_str = "/".join(filter(None, [prefix, tags]))
            parts.append(f"[{tag_str}]")
        parts.append(title)
        if size:
            all_text = (prefix + " " + tags + " " + title).upper()
            if "安卓" in all_text or "ANDROID" in all_text:
                plat = ""
            elif "PC" in all_text:
                plat = "PC"
            else:
                plat = "PC"
            parts.append(f"[{plat} {size}]".strip() if plat else f"[{size}]")
        if code:
            parts.append(f"[{code}]")

        result = " ".join(parts)
        return result if result.strip() else title
        soup = self._soup(url)

        # 标题 - ACG游戏姬使用 h1（无特定class）
        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # 标题格式化：提取各部分重新组合
        title = self._format_title(title, category)

        # 内容 - ACG游戏姬使用 div.single-content
        content_el = soup.select_one("div.single-content")
        content = content_el.get_text(separator="\n", strip=True) if content_el else ""

        # 提取图片 - 排除头像和emoji
        images = []
        if content_el:
            for img in content_el.select("img"):
                src = img.get("data-src") or img.get("src") or ""
                if src and "loading" not in src and "avatar" not in src and "emoji" not in src and "cravatar" not in src:
                    if not src.startswith("http"):
                        src = self.base_url + src
                    images.append(src)

        # 提取互动数据
        likes = 0
        comments = 0
        views = 0

        views_el = soup.select_one("span.list-post-view")
        if views_el:
            views_text = views_el.get_text(strip=True).replace("k", "000").replace(".", "")
            try:
                views = int(re.sub(r'[^\d]', '', views_text) or 0)
            except:
                pass

        comments_el = soup.select_one("span.list-post-comment, .comments-number")
        if comments_el:
            try:
                comments = int(re.sub(r'[^\d]', '', comments_el.get_text(strip=True)) or 0)
            except:
                pass

        likes_el = soup.select_one(".post-like .like-count, .likes-count")
        if likes_el:
            try:
                likes = int(re.sub(r'[^\d]', '', likes_el.get_text(strip=True)) or 0)
            except:
                pass

        # 提取发布日期
        post_date = ""
        date_el = soup.select_one("time.post-date, .post-meta time, .entry-date")
        if date_el:
            post_date = date_el.get("datetime", "") or date_el.get_text(strip=True)

        # 提取网盘链接
        links = extract_links(content)
        if not links.get("baidu_link") and not links.get("mobile_link"):
            full_text = str(soup)
            links = extract_links(full_text)

        # 提取下载名追加到标题
        cloud_name = extract_cloud_name(content)
        if cloud_name and cloud_name not in title:
            title = f"{title} [{cloud_name}]"

        # 提取作弊码
        cheat_code = extract_cheat_code(title, content)

        # 提取解压码
        unzip_code = ""

        # 判断平台 - 优先从分类标签判断
        platform = "unknown"
        category_lower = (category or "").lower()
        title_lower = title.lower()

        if category_lower == "pc":
            platform = "pc"
        elif category_lower == "az":
            platform = "android"
        elif "pc+安卓" in title_lower or "pc&安卓" in title_lower or "pc/安卓" in title_lower:
            platform = "pc_android"
        elif "安卓" in title_lower:
            platform = "android"
        elif "pc" in title_lower or "steam" in title_lower:
            platform = "pc"

        # 提取source_id
        source_id = url.split("/")[-1].replace(".html", "")

        # 下载图片到本地（用source_id作为临时目录名）
        proxy = None
        if self.config.get("proxy", {}).get("enabled"):
            proxy = self.config["proxy"]["http"]
        local_images = download_images(images[:3], source_id, proxy=proxy)
        if local_images:
            images = local_images

        return {
            "source": self.site_name,
            "source_id": source_id,
            "source_url": url,
            "title": title,
            "platform": platform,
            "content": content[:5000],
            "likes": likes,
            "comments": comments,
            "views": views,
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
            soup = self._soup(self.base_url)
            page_links = soup.select("ul.pagination li a.page-link")
            max_page = 1
            for a in page_links:
                text = a.get_text(strip=True)
                if text.isdigit():
                    max_page = max(max_page, int(text))
            return max_page
        except:
            return 100
