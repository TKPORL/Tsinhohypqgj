"""爬虫引擎：站点并发 + 站内详情并发 + 独立站点状态"""
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.acgyxj import ACGYXJCrawler
from crawler.acgrx import ACGRXCrawler
from crawler.acgll import ACGLLCrawler
from crawler.acgjlb import ACGJLBCrawler
from database import insert_post, create_task, update_task, get_conn
from config import get_speed_profile, get_site_detail_workers

CRAWLERS = {
    "acgyxj": ACGYXJCrawler,
    "acgrx": ACGRXCrawler,
    "acgll": ACGLLCrawler,
    "acgjlb": ACGJLBCrawler,
}

# 站点键 -> 中文名（面板显示用，不依赖爬虫实例）
SITE_NAMES = {
    "acgyxj": "ACG游戏姬",
    "acgrx": "萌幻ACG",
    "acgll": "ACG图书馆",
    "acgjlb": "ACG俱乐部",
}


class CrawlerEngine:
    """爬虫引擎"""

    def __init__(self, config):
        self.config = config
        self.running = False
        self.cancelled = False
        self.task_id = None
        self.speed_name = "balanced"
        self.progress_callback = None
        self.log_callback = None
        self.site_status_callback = None
        self._lock = threading.Lock()
        # 每站独立状态：{site_key: {status, current, total, success, skipped, error, page, logs: []}}
        self.site_states = {}
        self.site_logs = {}

    def _log(self, site, msg, level="info"):
        if self.log_callback:
            self.log_callback(site, msg, level)
        # 按站点名记录日志（键与site_states的site_key通过名字反查兼容）
        with self._lock:
            if site not in self.site_logs:
                self.site_logs[site] = []
            self.site_logs[site].append({"text": msg, "level": level})
            if len(self.site_logs[site]) > 200:
                self.site_logs[site] = self.site_logs[site][-100:]

    # 站点名 -> site_key 反查表（懒加载，用于站点日志与面板对齐）
    _NAME_TO_KEY = None

    @classmethod
    def _get_name_to_key(cls):
        if cls._NAME_TO_KEY is None:
            cls._NAME_TO_KEY = {v: k for k, v in SITE_NAMES.items()}
        return cls._NAME_TO_KEY

    def _site_log(self, site_key, msg, level="info"):
        """站点专属日志（面板显示用）"""
        site_name = SITE_NAMES.get(site_key, site_key)
        self._log(site_name, msg, level)

    def _update_site_state(self, site_key, **kwargs):
        with self._lock:
            if site_key not in self.site_states:
                self.site_states[site_key] = {
                    "status": "waiting", "current": 0, "total": 0,
                    "success": 0, "skipped": 0, "error": 0, "page": 0
                }
            self.site_states[site_key].update(kwargs)
            state = dict(self.site_states[site_key])
        if self.site_status_callback:
            self.site_status_callback(site_key, state)

    def _init_site_states(self, sites):
        self.site_states = {}
        self.site_logs = {}
        for site in sites:
            self._update_site_state(site, status="waiting", current=0, total=0,
                                    success=0, skipped=0, error=0, page=0)

    def _aggregate_progress(self):
        """汇总所有站点进度"""
        with self._lock:
            states = list(self.site_states.values())
        current = sum(s.get("current", 0) for s in states)
        total = sum(s.get("total", 0) for s in states)
        success = sum(s.get("success", 0) for s in states)
        skipped = sum(s.get("skipped", 0) for s in states)
        error = sum(s.get("error", 0) for s in states)
        if self.progress_callback:
            self.progress_callback(current, total, success, skipped, error)

    def _process_post(self, site_key, crawler, post, counters, task_id):
        """处理单个帖子：过滤+入库，返回 'success'/'skipped'/'error'"""
        try:
            if self.cancelled:
                return "skipped"
            if not post:
                return "error"
            if not post.get("title", "").strip():
                return "skipped"
            if post.get("platform") == "unknown":
                return "skipped"
            has_baidu = bool(post.get("baidu_link"))
            has_mobile = bool(post.get("mobile_link"))
            if not (has_baidu or has_mobile):
                return "skipped"
            post["crawl_id"] = task_id
            insert_post(post)
            return "success"
        except Exception:
            return "error"

    def _crawl_detail_and_count(self, site_key, crawler, item, counters, task_id):
        """解析单个详情页并更新站点计数"""
        url = item["url"] if isinstance(item, dict) else item
        category = item.get("category", "") if isinstance(item, dict) else ""
        result = "error"
        try:
            if self.cancelled:
                return "skipped"
            post = crawler.parse_detail(url, category=category) if category else crawler.parse_detail(url)
            result = self._process_post(site_key, crawler, post, counters, task_id)
            if result == "success":
                self._site_log(site_key, f"✓ {post['title'][:50]}...")
            elif result == "skipped" and post:
                self._site_log(site_key, f"✗ 跳过(无链接/平台未知): {(post.get('title') or '')[:50]}...")
        except Exception as e:
            result = "error"
            self._site_log(site_key, f"解析失败: {e}", "error")

        # 更新站点计数
        with self._lock:
            st = self.site_states.get(site_key, {})
            st["current"] = st.get("current", 0) + 1
            if result == "success":
                st["success"] = st.get("success", 0) + 1
            elif result == "skipped":
                st["skipped"] = st.get("skipped", 0) + 1
            else:
                st["error"] = st.get("error", 0) + 1
        self._aggregate_progress()
        return result

    def _crawl_site_by_page(self, site_key, start_page, end_page, task_id):
        """单站点按页码爬取（站内详情并发）"""
        detail_workers = get_site_detail_workers(self.speed_name, site_key)
        crawler_cls = CRAWLERS.get(site_key)
        if not crawler_cls:
            return
        crawler = crawler_cls(self.config)
        self._update_site_state(site_key, status="running")
        self._site_log(site_key, f"开始爬取第 {start_page}-{end_page} 页（详情并发{detail_workers}）")

        try:
            for page in range(start_page, end_page + 1):
                if self.cancelled:
                    break
                try:
                    items = crawler.get_list_page(page)
                    with self._lock:
                        self.site_states[site_key]["page"] = page
                        self.site_states[site_key]["total"] += len(items)
                    self._site_log(site_key, f"第{page}页: 发现 {len(items)} 个帖子")
                    self._aggregate_progress()

                    if detail_workers <= 1:
                        for item in items:
                            if self.cancelled:
                                break
                            self._crawl_detail_and_count(site_key, crawler, item, None, task_id)
                    else:
                        with ThreadPoolExecutor(max_workers=detail_workers) as executor:
                            futures = []
                            for item in items:
                                if self.cancelled:
                                    break
                                futures.append(executor.submit(
                                    self._crawl_detail_and_count, site_key, crawler, item, None, task_id))
                            for f in as_completed(futures):
                                try:
                                    f.result()
                                except Exception:
                                    pass
                except Exception as e:
                    with self._lock:
                        self.site_states[site_key]["error"] = self.site_states[site_key].get("error", 0) + 1
                    self._site_log(site_key, f"第{page}页获取失败: {e}", "error")
                    self._aggregate_progress()

            final_status = "cancelled" if self.cancelled else "completed"
            self._update_site_state(site_key, status=final_status)
            self._site_log(site_key, "爬取完成" if not self.cancelled else "已停止")
        except Exception as e:
            self._update_site_state(site_key, status="failed")
            self._site_log(site_key, f"爬取出错: {e}", "error")

    def _check_existing(self, post):
        """检查帖子是否已存在（增量爬取用）"""
        with get_conn() as conn:
            return conn.execute(
                "SELECT id FROM posts WHERE source = ? AND source_id = ?",
                (post.get("source"), post.get("source_id"))
            ).fetchone()

    def _crawl_site_incremental(self, site_key, task_id):
        """单站点增量爬取（站内详情并发）"""
        detail_workers = get_site_detail_workers(self.speed_name, site_key)
        crawler_cls = CRAWLERS.get(site_key)
        if not crawler_cls:
            return
        crawler = crawler_cls(self.config)
        self._update_site_state(site_key, status="running")
        self._site_log(site_key, f"开始增量爬取（详情并发{detail_workers}）")

        try:
            page = 1
            max_pages = crawler.get_total_pages()
            found_existing = False

            while page <= max_pages and not found_existing and not self.cancelled:
                try:
                    items = crawler.get_list_page(page)
                    self._site_log(site_key, f"第{page}页: 发现 {len(items)} 个帖子")

                    if detail_workers <= 1:
                        for item in items:
                            if self.cancelled or found_existing:
                                break
                            url = item["url"] if isinstance(item, dict) else item
                            category = item.get("category", "") if isinstance(item, dict) else ""
                            try:
                                post = crawler.parse_detail(url, category=category) if category else crawler.parse_detail(url)
                                if post and self._check_existing(post):
                                    self._site_log(site_key, "遇到已有数据，增量爬取完成")
                                    found_existing = True
                                    break
                                result = self._process_post(site_key, crawler, post, None, task_id)
                                with self._lock:
                                    st = self.site_states[site_key]
                                    st["current"] += 1
                                    st["total"] += 1
                                    if result == "success":
                                        st["success"] += 1
                                    elif result == "skipped":
                                        st["skipped"] += 1
                                    else:
                                        st["error"] += 1
                                self._aggregate_progress()
                            except Exception as e:
                                self._site_log(site_key, f"解析失败: {e}", "error")
                    else:
                        with ThreadPoolExecutor(max_workers=detail_workers) as executor:
                            futures = []
                            for item in items:
                                if self.cancelled or found_existing:
                                    break
                                url = item["url"] if isinstance(item, dict) else item
                                category = item.get("category", "") if isinstance(item, dict) else ""
                                futures.append(executor.submit(
                                    self._incremental_check_and_process, site_key, crawler, url, category, task_id))
                            for f in as_completed(futures):
                                try:
                                    if f.result() == "existing":
                                        found_existing = True
                                except Exception:
                                    pass
                    page += 1
                except Exception as e:
                    self._site_log(site_key, f"第{page}页获取失败: {e}", "error")
                    page += 1

            final_status = "cancelled" if self.cancelled else "completed"
            self._update_site_state(site_key, status=final_status)
            self._site_log(site_key, "增量爬取完成" if not self.cancelled else "已停止")
        except Exception as e:
            self._update_site_state(site_key, status="failed")
            self._site_log(site_key, f"爬取出错: {e}", "error")

    def _incremental_check_and_process(self, site_key, crawler, url, category, task_id):
        """增量模式单帖处理：存在则返回existing"""
        try:
            if self.cancelled:
                return "existing"
            post = crawler.parse_detail(url, category=category) if category else crawler.parse_detail(url)
            if post and self._check_existing(post):
                self._site_log(site_key, "遇到已有数据，增量爬取完成")
                return "existing"
            result = self._process_post(site_key, crawler, post, None, task_id)
            with self._lock:
                st = self.site_states[site_key]
                st["current"] += 1
                st["total"] += 1
                if result == "success":
                    st["success"] += 1
                elif result == "skipped":
                    st["skipped"] += 1
                else:
                    st["error"] += 1
            self._aggregate_progress()
            return result
        except Exception as e:
            self._site_log(site_key, f"解析失败: {e}", "error")
            return "error"

    def _run_sites_parallel(self, sites, site_runner, mode_name, params):
        """并行运行各站点任务，返回汇总统计"""
        self.running = True
        self.cancelled = False
        self._init_site_states(sites)

        sites_str = ",".join(sites)
        self.task_id = create_task(mode_name, params, sites_str)
        update_task(self.task_id, status="running", started_at=datetime.now().isoformat())

        max_workers = min(self.config.get("crawler", {}).get("site_workers", 4), len(sites))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(site_runner, site): site for site in sites}
            for future in as_completed(futures):
                site = futures[future]
                try:
                    future.result()
                except Exception as e:
                    # 不再静默吞掉站点线程异常
                    self._update_site_state(site, status="failed")
                    self._site_log(site, f"站点线程异常退出: {e}", "error")

        self.running = False
        status = "cancelled" if self.cancelled else "completed"

        # 汇总站点统计
        with self._lock:
            states = list(self.site_states.values())
        success = sum(s.get("success", 0) for s in states)
        skipped = sum(s.get("skipped", 0) for s in states)
        error = sum(s.get("error", 0) for s in states)

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

    def set_speed(self, speed_name):
        """设置速度档位（带白名单校验）"""
        name, _profile = get_speed_profile(speed_name)
        self.speed_name = name
        return name

    def crawl_by_page(self, sites, start_page, end_page, speed_name=None):
        """按页码爬取"""
        if speed_name:
            self.set_speed(speed_name)
        params = json.dumps({"start_page": start_page, "end_page": end_page})
        return self._run_sites_parallel(
            sites,
            lambda site: self._crawl_site_by_page(site, start_page, end_page, self.task_id),
            "by_page", params
        )

    def crawl_by_date(self, sites, start_date, end_date, speed_name=None):
        """按日期爬取"""
        if speed_name:
            self.set_speed(speed_name)
        params = json.dumps({"start_date": start_date, "end_date": end_date})
        return self._run_sites_parallel(
            sites,
            lambda site: self._make_site_runner_by_date(site, start_date, end_date)(),
            "by_date", params
        )

    def crawl_incremental(self, sites, speed_name=None):
        """增量爬取"""
        if speed_name:
            self.set_speed(speed_name)
        params = json.dumps({"mode": "incremental"})
        return self._run_sites_parallel(
            sites,
            lambda site: self._crawl_site_incremental(site, self.task_id),
            "incremental", params
        )

    def cancel(self):
        self.cancelled = True

    # ===== 兼容旧接口 =====
    def _make_site_runner_by_date(self, site, start_date, end_date):
        """旧版按日期站点运行器（保持兼容）"""
        detail_workers = get_site_detail_workers(self.speed_name, site)
        crawler_cls = CRAWLERS.get(site)
        if not crawler_cls:
            return lambda: None

        def runner():
            crawler = crawler_cls(self.config)
            self._update_site_state(site, status="running")
            self._site_log(site, f"开始爬取 {start_date} ~ {end_date}（详情并发{detail_workers}）")
            try:
                posts = crawler.crawl_date_range(start_date, end_date)
                with self._lock:
                    self.site_states[site]["total"] = len(posts)
                self._aggregate_progress()
                # 逐条处理（按日期模式帖子已由crawler批量解析）
                with ThreadPoolExecutor(max_workers=detail_workers) as executor:
                    futures = []
                    for post in posts:
                        if self.cancelled:
                            break
                        futures.append(executor.submit(self._process_and_count, site, post))
                    for f in as_completed(futures):
                        try:
                            f.result()
                        except Exception:
                            pass
                final_status = "cancelled" if self.cancelled else "completed"
                self._update_site_state(site, status=final_status)
                self._site_log(site, "爬取完成" if not self.cancelled else "已停止")
            except Exception as e:
                self._update_site_state(site, status="failed")
                self._site_log(site, f"爬取出错: {e}", "error")

        return runner

    def _process_and_count(self, site, post):
        """按日期模式的单帖处理+计数"""
        try:
            result = self._process_post(site, None, post, None, self.task_id)
        except Exception:
            result = "error"
        with self._lock:
            st = self.site_states[site]
            st["current"] += 1
            if result == "success":
                st["success"] += 1
            elif result == "skipped":
                st["skipped"] += 1
            else:
                st["error"] += 1
        self._aggregate_progress()
        return result
