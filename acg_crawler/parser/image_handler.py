"""图片下载处理模块"""
import os
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

IMAGES_DIR = Path(__file__).parent.parent / "images"

def get_image_dir(source):
    """获取图片存储目录"""
    dir_path = IMAGES_DIR / source
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def get_image_filename(url, source):
    """生成图片文件名"""
    ext = ".jpg"
    if ".png" in url:
        ext = ".png"
    elif ".gif" in url:
        ext = ".gif"
    elif ".webp" in url:
        ext = ".webp"

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{source}_{url_hash}{ext}"

def download_image(url, source, proxy=None, timeout=30):
    """下载单张图片，返回本地路径"""
    try:
        img_dir = get_image_dir(source)
        filename = get_image_filename(url, source)
        local_path = img_dir / filename

        if local_path.exists():
            return str(local_path)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": url,
        }

        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        resp = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and len(resp.content) < 1000:
            return None

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        return str(local_path)

    except Exception as e:
        return None

def download_images(urls, source, proxy=None, max_workers=4):
    """批量下载图片"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_image, url, source, proxy)
            for url in urls
        ]
        for future in futures:
            try:
                result = future.result(timeout=60)
                if result:
                    results.append(result)
            except Exception:
                pass
    return results
