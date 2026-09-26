"""临时预览服务：把某个导出目录挂在 / 上，方便浏览器打开（避开 file:// 中文路径问题）。

用法: python _preview_dir.py <目录> [端口]
"""
import http.server
import os
import socketserver
import sys

root = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5098

names = [f for f in os.listdir(root) if f.endswith(".html") and "备份" not in f]
target = names[0]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=root, **kw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/" + target
        return super().do_GET()

    def log_message(self, *a):
        pass


with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
    print("serving %s as /%s on %s" % (root, target, port), flush=True)
    httpd.serve_forever()
