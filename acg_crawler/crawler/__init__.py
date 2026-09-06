"""爬虫引擎"""
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.acgyxj import ACGYXJCrawler
from crawler.acgrx import ACGRXCrawler
from crawler.acgll import ACGLLCrawler
from crawler.acgjlb import ACGJLBCrawler
from database import insert_post, create_task, update_task

CRAWLERS = {
    "acgyxj": ACGYXJCrawler,
    "acgrx": ACGRXCrawler,
    "acgll": ACGLLCrawler,
    "acgjlb": ACGJLBCrawler,
}

class CrawlerEngine:
    """爬虫引擎"""

    def __init__(self, config):
        self.config = config
        self.running = False
        self.cancelled = False
        self.task_id = None
        self.progress_callback = None
        self.log_callback = None
        self._lock = threading.Lock()

    def _log(self, site, msg, level="info"):
        if self.log_callback:
            self.log_callback(site, msg, level)

    def _update_progress(self, current, total, success=0, skipped=0, error=0):
        if self.progress_callback:
            self.progress_callback(current, total, success, skipped, error)

    def crawl_by_page(self, sites, start_page, end_page):
        """按页码爬取"""
        self.running = True
        self.cancelled = False

        params = json.dumps({"start_page": start_page, "end_page": end_page})
        sites_str = ",".join(sites)
        self.task_id = create_task("by_page", params, sites_str)
        update_task(self.task_id, status="running", started_at=datetime.now().isoformat())

        total_pages = (end_page - start_page + 1) * len(sites)
        current = 0
        success = 0
        skipped = 0
        error = 0

        def crawl_site(site_key):
            nonlocal current, success, skipped, error
            if self.cancelled:
                return

            try:
                crawler_cls = CRAWLERS.get(site_key)
                if not crawler_cls:
                    return

                crawler = crawler_cls(self.config)
                self._log(crawler.site_name, f"开始爬取第 {start_page}-{end_page} 页")

                for page in range(start_page, end_page + 1):
                    if self.cancelled:
                        break

                    try:
                        items = crawler.get_list_page(page)
                        self._log(crawler.site_name, f"第{page}页: 发现 {len(items)} 个帖子")

                        for item in items:
                            if self.cancelled:
                                break

                            # 兼容新格式(dict with url+category)和旧格式(纯url字符串)
                            if isinstance(item, dict):
                                url = item["url"]
                                category = item.get("category", "")
                            else:
                                url = item
                                category = ""

                            try:
                                post = crawler.parse_detail(url, category=category) if category else crawler.parse_detail(url)
                                if post:
                                    # 过滤空标题
                                    if not post.get("title", "").strip():
                                        skipped += 1
                                        self._log(crawler.site_name, f"✗ 跳过(空标题): {url}")
                                        continue

                                    # 过滤unknown平台
                                    if post.get("platform") == "unknown":
                                        skipped += 1
                                        self._log(crawler.site_name, f"✗ 跳过(未知平台): {post['title'][:50]}...")
                                        continue

                                    # 检查是否有有效链接
                                    has_baidu = bool(post.get("baidu_link"))
                                    has_mobile = bool(post.get("mobile_link"))

                                    if has_baidu or has_mobile:
                                        insert_post(post)
                                        success += 1
                                        self._log(crawler.site_name, f"✓ {post['title'][:50]}...")
                                    else:
                                        skipped += 1
                                        self._log(crawler.site_name, f"✗ 跳过(无网盘链接): {post['title'][:50]}...")
                                else:
                                    error += 1
                            except Exception as e:
                                error += 1
                                self._log(crawler.site_name, f"解析失败: {e}", "error")

                            with self._lock:
                                current += 1
                                self._update_progress(current, total_pages, success, skipped, error)

                    except Exception as e:
                        error += 1
                        self._log(crawler.site_name, f"第{page}页获取失败: {e}", "error")
                        with self._lock:
                            current += 1
                            self._update_progress(current, total_pages, success, skipped, error)

                self._log(crawler.site_name, f"爬取完成")

            except Exception as e:
                self._log(site_key, f"爬取出错: {e}", "error")

        # 多线程爬取
        max_workers = min(self.config.get("crawler", {}).get("max_workers", 8), len(sites))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(crawl_site, site) for site in sites]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    pass

        self.running = False
        status = "cancelled" if self.cancelled else "completed"
        update_task(
            self.task_id,
            status=status,
            finished_at=datetime.now().isoformat(),
            total_posts=total_pages,
            success_posts=success,
            skipped_posts=skipped,
            error_posts=error,
        )

        return {
            "task_id": self.task_id,
            "status": status,
            "success": success,
            "skipped": skipped,
            "error": error,
        }

    def crawl_by_date(self, sites, start_date, end_date):
        """按日期爬取"""
        self.running = True
        self.cancelled = False

        params = json.dumps({"start_date": start_date, "end_date": end_date})
        sites_str = ",".join(sites)
        self.task_id = create_task("by_date", params, sites_str)
        update_task(self.task_id, status="running", started_at=datetime.now().isoformat())

        current = 0
        success = 0
        skipped = 0
        error = 0

        def crawl_site(site_key):
            nonlocal current, success, skipped, error
            if self.cancelled:
                return

            try:
                crawler_cls = CRAWLERS.get(site_key)
                if not crawler_cls:
                    return

                crawler = crawler_cls(self.config)
                self._log(crawler.site_name, f"开始爬取 {start_date} ~ {end_date}")

                posts = crawler.crawl_date_range(start_date, end_date)
                total = len(posts)

                for post in posts:
                    if self.cancelled:
                        break

                    try:
                        # 过滤空标题
                        if not post.get("title", "").strip():
                            skipped += 1
                            continue

                        # 过滤unknown平台
                        if post.get("platform") == "unknown":
                            skipped += 1
                            continue

                        has_baidu = bool(post.get("baidu_link"))
                        has_mobile = bool(post.get("mobile_link"))

                        if has_baidu or has_mobile:
                            insert_post(post)
                            success += 1
                            self._log(crawler.site_name, f"✓ {post['title'][:30]}...")
                        else:
                            skipped += 1
                    except Exception as e:
                        error += 1
                        self._log(crawler.site_name, f"保存失败: {e}", "error")

                    with self._lock:
                        current += 1
                        self._update_progress(current, total, success, skipped, error)

                self._log(crawler.site_name, f"爬取完成")

            except Exception as e:
                self._log(site_key, f"爬取出错: {e}", "error")

        max_workers = min(self.config.get("crawler", {}).get("max_workers", 8), len(sites))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(crawl_site, site) for site in sites]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        self.running = False
        status = "cancelled" if self.cancelled else "completed"
        update_task(
            self.task_id,
            status=status,
            finished_at=datetime.now().isoformat(),
            success_posts=success,
            skipped_posts=skipped,
            error_posts=error,
        )

        return {
            "task_id": self.task_id,
            "status": status,
            "success": success,
            "skipped": skipped,
            "error": error,
        }

    def cancel(self):
        self.cancelled = True

    def crawl_incremental(self, sites):
        """增量爬取：从第1页开始，直到遇到已有数据为止"""
        self.running = True
        self.cancelled = False

        params = json.dumps({"mode": "incremental"})
        sites_str = ",".join(sites)
        self.task_id = create_task("incremental", params, sites_str)
        update_task(self.task_id, status="running", started_at=datetime.now().isoformat())

        current = 0
        success = 0
        skipped = 0
        error = 0

        def crawl_site(site_key):
            nonlocal current, success, skipped, error
            if self.cancelled:
                return

            try:
                crawler_cls = CRAWLERS.get(site_key)
                if not crawler_cls:
                    return

                crawler = crawler_cls(self.config)
                self._log(crawler.site_name, "开始增量爬取")

                page = 1
                max_pages = crawler.get_total_pages()
                found_existing = False

                while page <= max_pages and not found_existing and not self.cancelled:
                    try:
                        items = crawler.get_list_page(page)
                        self._log(crawler.site_name, f"第{page}页: 发现 {len(items)} 个帖子")

                        for item in items:
                            if self.cancelled:
                                break

                            # 兼容新格式(dict with url+category)和旧格式(纯url字符串)
                            if isinstance(item, dict):
                                url = item["url"]
                                category = item.get("category", "")
                            else:
                                url = item
                                category = ""

                            try:
                                post = crawler.parse_detail(url, category=category) if category else crawler.parse_detail(url)
                                if post:
                                    # 过滤空标题
                                    if not post.get("title", "").strip():
                                        skipped += 1
                                        continue

                                    # 过滤unknown平台
                                    if post.get("platform") == "unknown":
                                        skipped += 1
                                        continue

                                    has_baidu = bool(post.get("baidu_link"))
                                    has_mobile = bool(post.get("mobile_link"))

                                    if has_baidu or has_mobile:
                                        # 检查是否已存在
                                        from database import get_conn
                                        with get_conn() as conn:
                                            exists = conn.execute(
                                                "SELECT id FROM posts WHERE source = ? AND source_id = ?",
                                                (post["source"], post["source_id"])
                                            ).fetchone()

                                        if exists:
                                            self._log(crawler.site_name, f"遇到已有数据，增量爬取完成")
                                            found_existing = True
                                            break

                                        insert_post(post)
                                        success += 1
                                        self._log(crawler.site_name, f"✓ {post['title'][:50]}...")
                                    else:
                                        skipped += 1
                            except Exception as e:
                                error += 1
                                self._log(crawler.site_name, f"解析失败: {e}", "error")

                            with self._lock:
                                current += 1
                                self._update_progress(current, 0, success, skipped, error)

                        page += 1
                    except Exception as e:
                        error += 1
                        self._log(crawler.site_name, f"第{page}页获取失败: {e}", "error")
                        page += 1

                self._log(crawler.site_name, f"增量爬取完成")

            except Exception as e:
                self._log(site_key, f"爬取出错: {e}", "error")

        max_workers = min(self.config.get("crawler", {}).get("max_workers", 8), len(sites))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(crawl_site, site) for site in sites]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        self.running = False
        status = "cancelled" if self.cancelled else "completed"
        update_task(
            self.task_id,
            status=status,
            finished_at=datetime.now().isoformat(),
            success_posts=success,
            skipped_posts=skipped,
            error_posts=error,
        )

        return {
            "task_id": self.task_id,
            "status": status,
            "success": success,
            "skipped": skipped,
            "error": error,
        }
