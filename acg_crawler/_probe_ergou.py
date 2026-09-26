# -*- coding: utf-8 -*-
"""临时探针：二狗站 直连 vs 代理（requests TLS 指纹与 curl 不同，结果更接近爬虫真实情况）"""
import sys, time
sys.path.insert(0, '.')
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
url = 'https://2gouacg.com/?cat=3'

for name, proxies in [("direct", None),
                      ("proxy7890", {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"})]:
    try:
        t0 = time.time()
        r = requests.get(url, headers={"User-Agent": UA}, proxies=proxies, timeout=20)
        print('%s: %s (%.1fs, len=%d)' % (name, r.status_code, time.time()-t0, len(r.text)))
    except Exception as e:
        print('%s: FAIL %s' % (name, type(e).__name__), str(e)[:120])
    time.sleep(3)
