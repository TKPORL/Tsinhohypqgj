"""ACG游戏姬爬虫"""
import re
from crawler.base import BaseCrawler
from parser import extract_links, extract_cloud_name, extract_cheat_code

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

    def parse_detail(self, url, category=""):
        soup = self._soup(url)

        title_el = soup.select_one("h1.entry-title, h1.post-title, .article-title h1")
        title = title_el.get_text(strip=True) if title_el else ""

        content_el = soup.select_one(".entry-content, .post-content, .article-content")
        content = content_el.get_text(strip=True) if content_el else ""

        # 提取图片
        images = []
        if content_el:
            for img in content_el.select("img"):
                src = img.get("data-src") or img.get("src") or ""
                if src and "loading" not in src and "avatar" not in src and "emoji" not in src:
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

        return {
            "source": self.site_name,
            "source_id": source_id,
            "source_url": url,
            "title": title,
            "platform": platform,
            "content": content[:2000],
            "likes": likes,
            "comments": comments,
            "views": views,
            "unzip_code": unzip_code,
            "cheat_code": cheat_code,
            "baidu_link": links.get("baidu_link"),
            "baidu_code": links.get("baidu_code"),
            "mobile_link": links.get("mobile_link"),
            "mobile_code": links.get("mobile_code"),
            "images": str(images),
            "original_images": str(images),
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
