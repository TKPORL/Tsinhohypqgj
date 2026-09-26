import io

def patch(path, pairs, crlf):
    src = io.open(path, encoding='utf-8', newline='').read()
    for i, (old, new) in enumerate(pairs):
        oc = old.replace('\r\n', '\n').replace('\n', '\r\n') if crlf else old.replace('\r\n', '\n')
        nc = new.replace('\r\n', '\n').replace('\n', '\r\n') if crlf else new.replace('\r\n', '\n')
        if oc not in src:
            raise SystemExit(f'{path}: block {i} not found')
        src = src.replace(oc, nc, 1)
    io.open(path, 'w', encoding='utf-8', newline='').write(src)
    print('patched', path)

def is_crlf(path):
    return '\r\n' in io.open(path, encoding='utf-8', newline='').read()

HTML = r'acg_crawler\templates\index.html'
patch(HTML, [
    ('''                <div id="batchDeleteList" class="batch-list">
                        <p class="loading-text">加载中...</p>
                    </div>
                </div>''',
     '''                <div id="batchDeleteList" class="batch-list">
                        <p class="loading-text">加载中...</p>
                    </div>
                </div>

                <!-- 数据管理：一键清理 -->
                <div class="export-section">
                    <h3>数据管理</h3>
                    <p class="help-text">清理不再使用的数据释放磁盘空间，操作不可恢复。</p>
                    <div id="cleanupInfo" class="cleanup-list">
                        <p class="loading-text">加载中...</p>
                    </div>
                    <button class="btn btn-danger" id="cleanupBtn" onclick="doCleanup()">执行清理</button>
                </div>'''),
], is_crlf(HTML))
print('html done')
