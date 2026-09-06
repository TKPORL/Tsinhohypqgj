"""萌幻ACG爬虫"""
import json
import re
from pathlib import Path
from crawler.base import BaseCrawler
from parser import extract_links, extract_cloud_name, extract_cheat_code
from parser.image_handler import download_images

class ACGRXCrawler(BaseCrawler):
    """萌幻ACG爬虫"""

    def __init__(self, config):
        super().__init__(config)
        self.site_name = "萌幻ACG"
        self.base_url = "https://bbs4.acgrx.com"
        self.logged_in = False
        self._login()

    def _login(self):
        """自动登录"""
        try:
            login_page_url = f"{self.base_url}/adminacgrx/login.php"
            soup = self._soup(login_page_url)

            # 查找登录表单
            form = soup.select_one("form[name='login']")
            if not form:
                print(f"[{self.site_name}] 未找到登录表单")
                return

            # 获取action URL（含CSRF token）
            action = form.get("action", "")
            if not action:
                print(f"[{self.site_name}] 未找到登录action")
                return

            email = self.config.get("acgrx", {}).get("email", "")
            password = self.config.get("acgrx", {}).get("password", "")

            if not email or not password:
                print(f"[{self.site_name}] 未配置登录凭据")
                return

            # 登录 - 使用完整的headers模拟浏览器
            self.session.headers.update({
                "Referer": login_page_url,
                "Origin": self.base_url,
            })

            login_data = {
                "name": email,
                "password": password,
                "remember": "1",
                "referer": "",
            }

            resp = self.session.post(
                action,
                data=login_data,
                timeout=15,
                allow_redirects=True
            )

            # 检查登录是否成功：查看cookie中是否有typecho_uid
            if any("typecho_uid" in c.name for c in self.session.cookies):
                self.logged_in = True
                print(f"[{self.site_name}] 登录成功")
            elif "logout" in resp.text:
                self.logged_in = True
                print(f"[{self.site_name}] 登录成功")
            else:
                print(f"[{self.site_name}] 登录可能失败")

        except Exception as e:
            print(f"[{self.site_name}] 登录出错: {e}")

    def get_list_page(self, page_num):
        if page_num == 1:
            url = self.base_url
        else:
            url = f"{self.base_url}/page/{page_num}"
        soup = self._soup(url)
        results = []
        for item in soup.select("div.post-item"):
            a = item.select_one("a.post-title")
            if not a or not a.get("href"):
                continue

            link = a["href"]
            if not link.startswith("http"):
                link = self.base_url + link

            # 过滤掉广告链接
            if "/go/" in link:
                continue

            # 只保留游戏分类帖子
            cate_el = item.select_one("span.post-cate a")
            category = cate_el.get_text(strip=True) if cate_el else ""
            if category != "游戏":
                continue

            # 从标签提取平台信息
            platform_tag = ""
            for tag_el in item.select("span[class^='article-categories'] a"):
                tag_text = tag_el.get_text(strip=True)
                if tag_text in ("PC",):
                    platform_tag = "PC"
                    break
                elif tag_text in ("安卓",):
                    platform_tag = "AZ"
                    break

            results.append({"url": link, "category": platform_tag})
        return results

    def parse_detail(self, url, category=""):
        soup = self._soup(url)

        # 标题
        title_el = soup.select_one("div.post-contentr h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # 内容
        content_el = soup.select_one("div.post-contentr")
        content = ""
        if content_el:
            # 获取所有文本内容
            content = content_el.get_text(separator="\n", strip=True)

        # 提取图片
        images = []
        if content_el:
            for img in content_el.select("img"):
                src = img.get("data-original") or img.get("data-src") or img.get("src") or ""
                if src and "loading" not in src and "avatar" not in src and "emoji" not in src:
                    if not src.startswith("http"):
                        src = self.base_url + src
                    images.append(src)

        # 提取互动数据 (萌幻ACG没有互动数据)
        likes = 0
        comments = 0
        views = 0

        # 提取发布日期
        post_date = ""
        date_el = soup.select_one("div.post-contentr time[datetime]")
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

        # 提取解压码（萌幻ACG固定为唯ai雪莉酒）
        unzip_code = "唯ai雪莉酒"

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
            "likes": 0,
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
            soup = self._soup(self.base_url)
            page_links = soup.select("div.pagination a, a[href*='/page/']")
            max_page = 1
            for a in page_links:
                href = a.get("href", "")
                match = re.search(r'/page/(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))
            return max_page
        except:
            return 100
