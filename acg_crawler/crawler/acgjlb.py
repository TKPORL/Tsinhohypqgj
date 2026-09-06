"""ACG俱乐部爬虫"""
import json
import re
from pathlib import Path
from crawler.base import BaseCrawler
from parser import extract_links, extract_cloud_name, extract_cheat_code
from parser.image_handler import download_images

class ACGJLBCrawler(BaseCrawler):
    """ACG俱乐部爬虫"""

    def __init__(self, config):
        super().__init__(config)
        self.site_name = "ACG俱乐部"
        self.base_url = "https://www.acgjlb.cc"

    def get_list_page(self, page_num):
        url = f"{self.base_url}/acggame?page={page_num}"
        soup = self._soup(url)
        results = []
        # ACG俱乐部使用Zibll主题，帖子在 div.posts-item 或 article 元素中
        for item in soup.select("div.posts-item, article.post-item, .post-item"):
            # 跳过置顶帖子
            item_class = " ".join(item.get("class", []))
            if "sticky" in item_class or "pinned" in item_class:
                continue
            if item.select_one(".pin-badge, .sticky-label, .post-pin"):
                continue

            a = item.select_one("h2.item-heading > a, h2 a, .item-title a")
            if a and a.get("href"):
                link = a["href"]
                if not link.startswith("http"):
                    link = self.base_url + link

                # 从标签提取平台信息
                category = ""
                tag_els = item.select(".item-meta a, .item-tag a, a[rel='tag']")
                for tag_el in tag_els:
                    tag_text = tag_el.get_text(strip=True).lower()
                    if tag_text in ("pc", "pc版", "windows"):
                        category = "PC"
                        break
                    elif tag_text in ("安卓", "android", "az"):
                        category = "AZ"
                        break

                results.append({"url": link, "category": category})

        # 备用选择器
        if not results:
            for a in soup.select("a[href*='/acggame/']"):
                href = a.get("href", "")
                if re.search(r'/acggame/\d+', href):
                    link = href if href.startswith("http") else self.base_url + href
                    if not any(r["url"] == link for r in results):
                        results.append({"url": link, "category": ""})

        return results

    def parse_detail(self, url, category=""):
        soup = self._soup(url)

        # 标题 - ACG俱乐部使用 h1.article-title
        title_el = soup.select_one("h1.article-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # 标题开头的数字移到末尾（如 16495[RPG/...] → [RPG/...] 16495）
        title_match = re.match(r'^(\d{4,6})(\[.+)', title)
        if title_match:
            num = title_match.group(1)
            rest = title_match.group(2)
            title = f"{rest} {num}"

        # 标题末尾]后面的数字移到标题区后面（如 ...joi]5286 1648 → ...joi] 5286 1648）
        end_match = re.search(r'\](\d[\d\s]*\d)\s*$', title)
        if end_match:
            nums = end_match.group(1).strip()
            title = title[:end_match.start(1)].rstrip() + " " + nums

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

        # 提取互动数据 - ACG俱乐部在列表页就有互动数据
        likes = 0
        comments = 0
        views = 0

        likes_el = soup.select_one(".content-footer-zan-cai .like-count, .meta-like")
        if likes_el:
            try:
                likes = int(re.sub(r'[^\d]', '', likes_el.get_text(strip=True)) or 0)
            except:
                pass

        comments_el = soup.select_one(".comments-number, .meta-comm")
        if comments_el:
            try:
                comments = int(re.sub(r'[^\d]', '', comments_el.get_text(strip=True)) or 0)
            except:
                pass

        views_el = soup.select_one(".meta-view, .views-num")
        if views_el:
            try:
                views_text = views_el.get_text(strip=True).replace("W+", "0000").replace("w+", "0000")
                views = int(re.sub(r'[^\d]', '', views_text) or 0)
            except:
                pass

        # 提取发布日期
        post_date = ""
        date_el = soup.select_one("time.post-date, .entry-date time, .post-meta time")
        if date_el:
            post_date = date_el.get("datetime", "")[:10]

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

        # 提取解压码（ACG俱乐部固定为007721）
        unzip_code = "007721"

        # 判断平台 - 优先从分类标签判断
        platform = "unknown"
        category_lower = (category or "").lower()
        title_lower = title.lower()

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

        # 提取source_id
        source_id = url.split("/")[-1].replace(".html", "").split("?")[0]

        # 下载图片到本地（用source_id作为临时目录名）
        proxy = None
        if self.config.get("proxy", {}).get("enabled"):
            proxy = self.config["proxy"]["http"]
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
            url = f"{self.base_url}/acggame"
            soup = self._soup(url)
            # ACG俱乐部使用Zibll主题分页
            page_links = soup.select("div.pagenav a, a[href*='page=']")
            max_page = 1
            for a in page_links:
                href = a.get("href", "")
                match = re.search(r'page=(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))
            return max_page
        except:
            return 100
