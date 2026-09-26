import io
src = io.open(r'acg_crawler\templates\index.html', encoding='utf-8', newline='').read()
i = src.find('批次管理')
print(repr(src[i-40:i+340]))
