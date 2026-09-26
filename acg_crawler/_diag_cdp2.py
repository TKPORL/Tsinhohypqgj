# -*- coding: utf-8 -*-
"""CDP 诊断：连接已运行的 5000 实例，点击'爬取结果'，抓 JS 报错与渲染结果"""
import json, subprocess, time, urllib.request, websocket

CH = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
PORT = 9333
proc = subprocess.Popen([CH, "--headless=new", "--disable-gpu", "--no-proxy-server",
    "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
    "--user-data-dir=" + __import__("tempfile").gettempdir() + "/cdp_diag2"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
    page = next(t for t in tabs if t["type"] == "page")
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=20)
    mid = [0]
    def cmd(method, params=None):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid[0]:
                return msg
    cmd("Page.enable"); cmd("Runtime.enable")
    cmd("Page.navigate", {"url": "http://127.0.0.1:5000/"})
    time.sleep(6)
    expr = r"""(async () => {
      const errs = [];
      window.addEventListener('error', e => errs.push('ERR:' + e.message + ' @' + String(e.filename).slice(-14) + ':' + e.lineno));
      window.addEventListener('unhandledrejection', e => errs.push('REJ:' + e.reason));
      const btn = document.querySelector('[data-panel="result"]');
      if (!btn) return JSON.stringify({errs, noBtn: true, tabs: [...document.querySelectorAll('[data-panel]')].map(b=>b.textContent.trim())});
      btn.click();
      await new Promise(r => setTimeout(r, 6000));
      const gr = document.getElementById('groupedResults');
      return JSON.stringify({
        errs,
        cards: document.querySelectorAll('#groupedResults .card').length,
        groups: document.querySelectorAll('#groupedResults .date-group').length,
        containerHtmlLen: gr ? gr.innerHTML.length : -1,
        containerText: gr ? gr.textContent.trim().slice(0, 120) : ''
      });
    })()"""
    r = cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
    val = r.get("result", {}).get("result", {})
    print("value:", val.get("value") or json.dumps(r, ensure_ascii=False)[:600])
    # 顺带抓 console 输出
    ws.close()
finally:
    proc.kill()
    print("(诊断浏览器已关)")
