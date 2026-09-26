import io
src = io.open(r'acg_crawler\app.py', encoding='utf-8', newline='').read()
i = src.find('def _remove_post_images')
print(repr(src[i:i+700]))
