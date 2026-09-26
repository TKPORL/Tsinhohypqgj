import io

p = r'acg_crawler\app.py'
src = io.open(p, encoding='utf-8', newline='').read()

# 1) import 行补齐缺失的三个函数
old_imp = 'from database import init_db, get_posts, get_post_count, delete_post, get_tasks, delete_task, get_conn, get_crawl_batches, get_posts_by_crawl_id, get_batch_post_count, recover_interrupted_tasks'
new_imp = 'from database import (init_db, get_posts, get_post_count, delete_post, get_tasks, delete_task,\n                      get_conn, get_crawl_batches, get_posts_by_crawl_id, get_batch_post_count,\n                      recover_interrupted_tasks, delete_posts_by_ids, delete_posts_by_task,\n                      get_shared_source_ids)'
assert old_imp in src, 'import not found'
src = src.replace(old_imp, new_imp, 1)

# 2) _remove_post_images 换成带共享保护的版本
old_rmi = '''def _remove_post_images(source_ids):
    """删除指定 source_id 列表对应的 images/{source_id}/ 目录。

    目录不存在/删除失败仅记日志，不抛异常。
    """
    import shutil
    if not source_ids:
        return
    for sid in source_ids:
        d = IMAGES_DIR / str(sid)
        if d.exists() and d.is_dir():
            try:
                shutil.rmtree(d)
            except Exception as e:
                log_callback("系统", f"清理图片目录失败 {d}: {e}", "error")'''.replace('\n', '\r\n')

new_rmi = '''def _remove_post_images(source_ids):
    """删除指定 source_id 对应的 images/{source_id}/ 目录。

    各站帖子ID均为纯数字可能撞车：仅当该 source_id 不再被任何帖子
    引用时才删目录，避免删A站帖子误删B站图片。
    目录不存在/删除失败仅记日志，不抛异常。
    """
    import shutil
    if not source_ids:
        return
    unique_ids = {str(s) for s in source_ids if s}
    try:
        still_used = get_shared_source_ids(unique_ids)
    except Exception:
        still_used = set()  # 查询失败时保守跳过删除，防止误删
    for sid in unique_ids - still_used:
        d = IMAGES_DIR / sid
        if d.exists() and d.is_dir():
            try:
                shutil.rmtree(d)
            except Exception as e:
                log_callback("系统", f"清理图片目录失败 {d}: {e}", "error")'''.replace('\n', '\r\n')

if old_rmi not in src:
    raise SystemExit('rmi block not found')
src = src.replace(old_rmi, new_rmi, 1)

io.open(p, 'w', encoding='utf-8', newline='').write(src)
print('app.py import + _remove_post_images fixed')
