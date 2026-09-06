"""图片下载处理模块"""
import os
import re
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

IMAGES_DIR = Path(__file__).parent.parent / "images"


def get_image_dir(post_id):
    """获取图片存储目录：images/{post_id}/"""
    dir_path = IMAGES_DIR / str(post_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def _url_hash(url):
    """URL的纯ASCII哈希"""
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _guess_ext(url):
    """从URL猜扩展名"""
    lower = url.lower().split("?")[0]
    for ext in (".webp", ".png", ".gif", ".jpg", ".jpeg"):
        if lower.endswith(ext):
            return ext
    return ".jpg"


def download_image(url, post_id, proxy=None, timeout=15):
    """下载单张图片，成功返回本地相对路径，失败返回原始URL"""
    try:
        img_dir = get_image_dir(post_id)
        filename = _url_hash(url) + _guess_ext(url)
        local_path = img_dir / filename

        if local_path.exists():
            return f"images/{post_id}/{filename}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": url,
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }

        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        resp = requests.get(url, headers=headers, proxies=proxies,
                            timeout=timeout, stream=True, verify=False)
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        data = resp.content
        if len(data) < 500:
            return url

        with open(local_path, "wb") as f:
            f.write(data)

        return f"images/{post_id}/{filename}"

    except Exception:
        return url


def download_images(urls, post_id, proxy=None, max_workers=3):
    """批量下载图片，返回路径列表（本地相对路径或原始URL）"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_image, url, post_id, proxy)
            for url in urls
        ]
        for future in futures:
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except Exception:
                pass
    return results


def img_src(path_or_url):
    """前端用：本地相对路径 → 绝对路径；远程URL原样返回"""
    if not path_or_url:
        return ""
    s = str(path_or_url)
    if s.startswith("images/"):
        return "/" + s
    return s
