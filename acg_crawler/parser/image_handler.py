"""图片下载处理模块"""
import os
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

IMAGES_DIR = Path(__file__).parent.parent / "images"

def _source_hash(source):
    """生成来源名的短hash，用于目录名（避免中文路径编码问题）"""
    return hashlib.md5(source.encode("utf-8")).hexdigest()[:10]

def get_image_dir(source):
    """获取图片存储目录（用hash命名）"""
    dir_path = IMAGES_DIR / _source_hash(source)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def get_image_filename(url, source):
    """生成纯ASCII图片文件名（用URL的MD5 hash）"""
    ext = ".jpg"
    if ".png" in url:
        ext = ".png"
    elif ".gif" in url:
        ext = ".gif"
    elif ".webp" in url:
        ext = ".webp"

    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    return f"{url_hash}{ext}"

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
    """批量下载图片，返回本地路径列表"""
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

def get_web_path(local_path, source):
    """将本地路径转为Flask可服务的web路径：/images/<hash>/<filename>"""
    from pathlib import Path as _P
    filename = _P(local_path).name
    return f"/images/{_source_hash(source)}/{filename}"
