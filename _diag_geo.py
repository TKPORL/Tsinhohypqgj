# -*- coding: utf-8 -*-
"""CDP 几何诊断：打开首页，等待渲染，输出卡片及祖先链的几何信息"""
import json, subprocess, time, urllib.request, socket, sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
proc = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=%d" % PORT,
    "--remote-allow-origins=*", "--user-data-dir=C:/Users/Administrator/AppData/Local/Temp/chrome_diag_geo",
    "--window-size=1400,900", "--no-first-run", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    ws_url = None
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json" % PORT, timeout=1) as r:
                tabs = json.loads(r.read().decode())
            page = [t for t in tabs if t.get("type") == "page"]
            if page:
                ws_url = page[0]["webSocketDebuggerUrl"]; break
        except Exception:
            time.sleep(0.5)
    if not ws_url:
        print("NO_CDP"); sys.exit(1)

    try:
        import websocket
    except ImportError:
        subprocess.check_call([r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe",
                               "-m", "pip", "install", "-q", "websocket-client"])
        import websocket

    ws = websocket.create_connection(ws_url, timeout=15, origin="http://127.0.0.1:%d" % PORT)
    mid = [0]

    def cmd(method, params=None):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid[0]:
                return msg

    cmd("Page.enable")
    cmd("Page.navigate", {"url": "http://127.0.0.1:5000/"})
    time.sleep(4)
    cmd("Runtime.evaluate", {"expression":
        "document.querySelector('.nav-btn[data-panel=result]').click()", "returnByValue": True})
    time.sleep(3)
    cmd("Runtime.evaluate", {"expression":
        "typeof toggleGroup==='function' ? (toggleGroup(0), 'ok') : 'no-fn'", "returnByValue": True})
    time.sleep(2)

    js = r"""
    (function(){
      var out = [];
      var gr = document.getElementById('groupedResults');
      var pr = document.getElementById('panel-result');
      var fc = gr ? gr.querySelector('.card') : null;
      function rc(el){ if(!el) return 'null'; var r = el.getBoundingClientRect();
        return Math.round(r.width)+'x'+Math.round(r.height)+'@('+Math.round(r.left)+','+Math.round(r.top)+')'; }
      out.push('gr=' + rc(gr) + ' pr=' + rc(pr) + ' card=' + rc(fc));
      var el = fc, i = 0;
      while (el && i < 12) {
        var cs = getComputedStyle(el);
        out.push(i + ' ' + el.tagName + ' id=' + el.id + ' class=' + el.className + ' ' + rc(el)
          + ' d=' + cs.display + ' pos=' + cs.position + ' ov=' + cs.overflow
          + ' vis=' + cs.visibility + ' fs=' + cs.fontSize + ' h=' + cs.height);
        el = el.parentElement; i++;
      }
      var prr = document.getElementById('panel-result');
      if (prr) out.push('panel-result.parent=' + prr.parentElement.tagName + '#' + prr.parentElement.id + '.' + prr.parentElement.className);
      var contentKids = [];
      document.querySelectorAll('.content > *').forEach(function(c){ contentKids.push(c.tagName + '#' + c.id + '.' + c.className + ':' + getComputedStyle(c).display); });
      out.push('content.children= ' + contentKids.join(' | '));
      if (fc) out.push('CARD_HTML: ' + fc.outerHTML.slice(0, 500));
      var probe = document.elementFromPoint(Math.round(innerWidth*0.6), 400);
      out.push('probe(648,400)=' + (probe ? probe.tagName + '.' + probe.className : 'null'));
      return out.join('\n');
    })()
    """
    res = cmd("Runtime.evaluate", {"expression": js, "returnByValue": True})
    val = res.get("result", {}).get("result", {}).get("value", "EVAL_FAIL")
    print(val)
    ws.close()
finally:
    proc.kill()
