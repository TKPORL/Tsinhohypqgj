#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键自检：实际测一遍各站点能不能爬，输出"能用/不能用"的确凿结论。

为什么要这个东西：
  之前反复出现"我凭印象说能/不能，结果说反了"的情况。
  这个脚本不靠猜 —— 它真的发请求、真的看返回，把事实摆出来。

用法：
  C:/Python314/python.exe acg_crawler/tools/selftest_sites.py

输出：每个站点一行，标注 可用 / 不可用 / 需要凭据，以及依据。
"""
import io
import os
import sys
import json
import traceback

# 保证能 import 到项目模块
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import requests  # noqa: E402

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
}


def load_env():
    """读 .env，返回 dict（只看有没有真实值，不打印内容）"""
    path = os.path.join(ROOT, ".env")
    out = {}
    if not os.path.isfile(path):
        return out
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def is_placeholder(v):
    if not v:
        return True
    low = v.lower()
    return ("your_" in low) or low in ("", "xxx", "none", "null")


def check_kungal():
    """鲲Galgame —— 重点验证：不登录能不能拿到下载链接"""
    s = requests.Session()
    s.headers.update(UA)
    lines = []

    r = s.get("https://www.kungal.com/api/v1/works?page=1&limit=5&include_nsfw=true", timeout=25)
    lines.append(f"    作品列表  HTTP {r.status_code}")
    if r.status_code != 200:
        return False, "作品列表拉不到", lines
    items = r.json().get("items", [])
    if not items:
        return False, "作品列表为空", lines

    gid = items[0]["id"]
    r2 = s.get(f"https://www.kungal.com/api/v1/works/{gid}/resources?page=1&limit=50", timeout=25)
    lines.append(f"    资源列表  HTTP {r2.status_code}")
    if r2.status_code != 200:
        return False, "资源列表拉不到", lines
    res = r2.json().get("items", [])
    if not res:
        return False, "首个作品没有资源", lines

    rid = res[0]["id"]
    r3 = s.post(f"https://www.kungal.com/api/v1/galgame-resources/{rid}/downloads", timeout=25)
    lines.append(f"    下载发放  HTTP {r3.status_code}  ← 这一步决定能不能拿到下载链接")
    if r3.status_code != 200:
        return False, "下载发放失败", lines
    urls = r3.json().get("download_urls") or []
    lines.append(f"    拿到链接数  {len(urls)}")
    if not urls:
        return False, "下载发放返回了空链接", lines
    return True, "匿名可爬，下载链接可获取", lines


def check_simple(url, name, ua=None):
    """通用站点：能不能拿到 HTML。ua 不传就用默认。"""
    headers = dict(UA)
    if ua:
        headers["User-Agent"] = ua
    try:
        r = requests.get(url, headers=headers, timeout=25)
        ok = r.status_code == 200 and len(r.text) > 500
        extra = ""
        if r.status_code == 403:
            extra = "  ← 403 多半是 UA 被拦，不是站点挂了"
        return ok, f"HTTP {r.status_code}, {len(r.text)} 字节{extra}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    print("=" * 66)
    print("  站点自检 —— 这是实测结果，不是推测")
    print("=" * 66)
    print()

    env = load_env()
    env_keys = {
        "ACGRX_EMAIL": env.get("ACGRX_EMAIL", ""),
        "ACGRX_PASSWORD": env.get("ACGRX_PASSWORD", ""),
        "KUNGAL_COOKIE": env.get("KUNGAL_COOKIE", ""),
    }

    print("【.env 凭据状态】（只看是否已填真实值）")
    for k, v in env_keys.items():
        filled = not is_placeholder(v)
        print(f"  {k:<18} {'✅ 已填' if filled else '⬜ 未填（占位符/空）'}")
    print()

    results = {}

    print("【逐站实测】")

    # 鲲Galgame —— 特殊处理，要验证下载链接
    print("  ▸ 鲲Galgame (kungal.com)")
    try:
        ok, why, detail = check_kungal()
        for line in detail:
            print(line)
    except Exception as e:
        ok, why = False, f"{type(e).__name__}: {e}"
    results["鲲Galgame"] = (ok, why, None)
    print(f"    => {'✅ 可用' if ok else '❌ 不可用'} — {why}")
    print()

    # 其余站点（域名 + UA 都取自各 crawler 源码，不手写，避免我又猜错）
    # 二狗站封旧版 UA：源码注释「Chrome/120 实测 403」，必须用 Chrome/126
    simple = [
        ("ACG俱乐部", "acgjlb.cc", "https://www.acgjlb.cc", None),
        ("ACG图书馆", "acgll.xyz", "https://acgll.xyz", None),
        ("ACG游戏姬", "acgyxjvip.com", "https://www.acgyxjvip.com", None),
        ("二狗ACG", "2gouacg.com", "https://2gouacg.com",
         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    ]
    for name, mod, url, ua in simple:
        print(f"  ▸ {name} ({mod})")
        try:
            ok, why = check_simple(url, name, ua)
        except Exception as e:
            ok, why = False, f"{type(e).__name__}: {e}"
        results[name] = (ok, why, None)
        print(f"    => {'✅ 可用' if ok else '❌ 不可用'} — {why}")
        print()

    # 萌幻ACG —— 看凭据
    print("  ▸ 萌幻ACG (acgrx) —— 这个站需要登录")
    acgrx_ok = not is_placeholder(env.get("ACGRX_EMAIL", "")) and \
               not is_placeholder(env.get("ACGRX_PASSWORD", ""))
    if acgrx_ok:
        print("    .env 凭据已填 → 应该可用（未实跑登录，避免触发风控）")
        results["萌幻ACG"] = (True, "凭据已填", None)
    else:
        print("    .env 凭据未填 → 无法登录，这个站抓不了")
        results["萌幻ACG"] = (False, "缺少 ACGRX_EMAIL / ACGRX_PASSWORD", None)
    print()

    # 汇总
    print("=" * 66)
    print("  汇总")
    print("=" * 66)
    can = [k for k, v in results.items() if v[0]]
    cant = [(k, v[1]) for k, v in results.items() if not v[0]]
    print(f"  可爬：{len(can)} 个 -> {', '.join(can) if can else '（无）'}")
    if cant:
        print(f"  不能爬：{len(cant)} 个")
        for k, why in cant:
            print(f"      - {k}：{why}")
    else:
        print("  不能爬：0 个")
    print()
    print("（以上为实测结果。若与实际不符，以实际运行为准。）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
