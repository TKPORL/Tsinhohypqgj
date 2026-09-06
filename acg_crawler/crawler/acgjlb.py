"""ACG俱乐部爬虫"""
import re
from crawler.base import BaseCrawler
from parser import extract_links

class ACGJLBCrawler(BaseCrawler):
    """ACG俱乐部爬虫"""

    def __init__(self, config):
        super().__init__(config)
        self.site_name = "ACG俱乐部"
        self.base_url = "https://www.acgjlb.cc"

    def get_list_page(self, page_num):
        url = f"{self.base_url}/acggame?page={page_num}"
        soup = self._soup(url)
        links = []
        for item in soup.select("div.post-item, article.post-item, div.list-item"):
            a = item.select_one("h2 a, .post-title a, a.post-title, a.title")
            if a and a.get("href"):
                link = a["href"]
                if not link.startswith("http"):
                    link = self.base_url + link
                links.append(link)

        if not links:
            for a in soup.select("a[href*='/acggame/']"):
                href = a.get("href", "")
                if re.search(r'/acggame/\d+', href):
                    link = href if href.startswith("http") else self.base_url + href
                    if link not in links:
                        links.append(link)

        return links

    def parse_detail(self, url):
        soup = self._soup(url)

        title_el = soup.select_one("h1.entry-title, h1.post-title, .article-title h1, h1")
        title = title_el.get_text(strip=True) if title_el else ""

        content_el = soup.select_one(".entry-content, .post-content, .article-content, .content")
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

        likes_el = soup.select_one(".like-count, .likes-num, .post-like")
        if likes_el:
            try:
                likes = int(re.sub(r'[^\d]', '', likes_el.get_text(strip=True)) or 0)
            except:
                pass

        comments_el = soup.select_one(".comments-num, .comment-count")
        if comments_el:
            try:
                comments = int(re.sub(r'[^\d]', '', comments_el.get_text(strip=True)) or 0)
            except:
                pass

        views_el = soup.select_one(".views-num, .post-views, .view-count")
        if views_el:
            try:
                views_text = views_el.get_text(strip=True).replace("W+", "0000").replace("w+", "0000")
                views = int(re.sub(r'[^\d]', '', views_text) or 0)
            except:
                pass

        # 提取发布日期
        post_date = ""
        date_el = soup.select_one("time.post-date, .entry-date time, .post-time")
        if date_el:
            post_date = date_el.get("datetime", "") or date_el.get_text(strip=True)

        # 提取网盘链接
        links = extract_links(content)
        if not links.get("baidu_link") and not links.get("mobile_link"):
            full_text = str(soup)
            links = extract_links(full_text)

        # 提取解压码
        unzip_code = ""
        cheat_code = ""
        code_match = re.search(r'(?:解压码|解压密码|密码)[：:\s]*(\S+)', content)
        if code_match:
            unzip_code = code_match.group(1)

        # 判断平台
        platform = "unknown"
        title_lower = title.lower()
        if "pc+安卓" in title_lower or "pc&安卓" in title_lower or "pc/安卓" in title_lower:
            platform = "pc_android"
        elif "安卓" in title_lower:
            platform = "android"
        elif "pc" in title_lower or "steam" in title_lower:
            platform = "pc"

        # 提取source_id
        source_id = url.split("/")[-1].replace(".html", "").split("?")[0]

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
            url = f"{self.base_url}/acggame"
            soup = self._soup(url)
            page_links = soup.select("a[href*='page=']")
            max_page = 1
            for a in page_links:
                href = a.get("href", "")
                match = re.search(r'page=(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))
            return max_page
        except:
            return 100
