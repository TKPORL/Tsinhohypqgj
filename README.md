# ACG黄油资源聚合爬取工具

本地运行的ACG游戏资源聚合爬取工具，从多个站点抓取资源信息，提供Web界面预览，并支持导出离线HTML文件。

## 功能特性

- **多站点聚合**：支持4个ACG资源站点爬取
- **实时进度**：爬取过程中前端实时显示日志和进度
- **卡片预览**：爬取结果以卡片形式展示，含图片、网盘链接、解压码
- **平台分类**：自动识别PC/PC+安卓平台并分类
- **导出下载**：一键打包导出zip（HTML+图片），离线可浏览
- **批量操作**：支持批量删除、批量导出选中项

## 目标站点

| 站点 | 域名 | CMS | 登录 |
|------|------|-----|------|
| ACG游戏姬 | www.acgyxjvip.com | WordPress + Lolimeow | 不需要 |
| 萌幻ACG | bbs4.acgrx.com | Typecho + MiKu | 需要（已配置） |
| ACG图书馆 | acgll.xyz | WordPress + Zibll | 不需要 |
| ACG俱乐部 | www.acgjlb.cc | WordPress + Zibll | 不需要 |

## 快速开始

### 环境要求

- Python 3.9+
- pip

### 安装与启动

```bash
# 进入项目目录
cd acg_crawler

# 安装依赖
pip install -r requirements.txt

# 双击 start.bat（Windows）
# 或手动运行
python app.py
```

浏览器自动打开 `http://127.0.0.1:5000`

### 依赖说明

| 包 | 用途 |
|----|------|
| flask | Web服务器 |
| requests | HTTP请求 |
| beautifulsoup4 | HTML解析 |
| lxml | HTML解析器 |
| pyyaml | 配置文件解析 |

## 配置说明

编辑 `config.yaml`：

```yaml
# 代理设置（可选）
proxy:
  enabled: false
  http: "http://127.0.0.1:7890"

# 爬虫设置
crawler:
  max_workers: 12          # 并发数
  request_delay_min: 0.2   # 最小请求间隔(秒)
  request_delay_max: 0.5   # 最大请求间隔(秒)
  timeout: 10              # 请求超时(秒)

# Flask设置
flask:
  host: "127.0.0.1"
  port: 5000
```

## 项目结构

```
acg_crawler/
├── app.py                 # Flask主程序，API路由
├── config.py              # 配置管理
├── config.yaml            # 配置文件
├── requirements.txt       # 依赖列表
├── start.bat              # Windows一键启动
├── crawler/               # 爬虫模块
│   ├── base.py            # 基础爬虫类
│   ├── acgyxj.py          # ACG游戏姬爬虫
│   ├── acgrx.py           # 萌幻ACG爬虫
│   ├── acgll.py           # ACG图书馆爬虫
│   └── acgjlb.py          # ACG俱乐部爬虫
├── parser/                # 解析模块
│   ├── __init__.py        # 链接/云盘名提取
│   └── image_handler.py   # 图片下载处理
├── database/              # 数据库模块
│   └── __init__.py        # SQLite操作
├── generator/             # 导出模块
│   └── __init__.py        # HTML生成+zip打包
├── templates/             # 页面模板
│   └── index.html         # 主页面
├── static/                # 静态资源
│   ├── app.js             # 前端逻辑
│   └── style.css          # 样式
├── data/                  # 数据目录
│   └── crawler.db         # SQLite数据库
├── images/                # 下载的图片
│   └── {post_id}/         # 按帖子ID分目录
└── output/                # 导出目录
    ├── PC下载/            # PC导出
    └── PC+安卓下载/       # 双平台导出
```

## 使用指南

### 1. 爬取资源

1. 打开浏览器访问 `http://127.0.0.1:5000`
2. 在「爬取控制」面板选择目标站点
3. 选择爬取模式：
   - **按页码**：指定起止页码范围
   - **按日期**：指定日期范围
   - **增量**：从上次位置继续
4. 点击「开始爬取」，实时查看进度
5. 完成后自动跳转到结果页

### 2. 查看结果

- 在「爬取结果」面板浏览卡片
- 支持按来源站点、平台类型筛选
- 点击图片可放大查看
- 点击网盘链接可直接跳转下载

### 3. 导出文件

1. 切换到「导出文件」面板
2. 选择导出类型：
   - **PC下载.zip**：仅PC平台资源
   - **PC+安卓下载.zip**：包含双平台资源
3. 点击下载按钮，得到zip压缩包
4. 解压后双击HTML文件即可离线浏览（含图片）

### 4. 批量操作

- 勾选卡片前的复选框可多选
- 点击「批量删除」可删除选中项
- 点击「导出选中」可只导出勾选的资源

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/posts` | GET | 获取帖子列表 |
| `/api/posts_grouped` | GET | 按平台分组获取 |
| `/api/start_crawl` | POST | 启动爬取任务 |
| `/api/stop_crawl` | POST | 停止爬取任务 |
| `/api/progress` | GET | 获取爬取进度 |
| `/api/export` | GET | 执行导出 |
| `/api/export_download` | GET | 下载导出文件 |
| `/api/redownload_images` | POST | 重新下载图片 |
| `/api/delete_post` | POST | 删除帖子 |
| `/api/batch_delete` | POST | 批量删除 |

## 常见问题

### 图片不显示

1. 点击「重新下载图片」按钮
2. 等待下载完成
3. 刷新页面

### 导出HTML图片不显示

导出为zip格式，解压后HTML和images目录在同一目录下，双击HTML即可看到图片。

### 代理设置

如果需要代理，在config.yaml中设置：
```yaml
proxy:
  enabled: true
  http: "http://127.0.0.1:7890"
```

### 爬取速度慢

调整config.yaml中的并发和延迟：
```yaml
crawler:
  max_workers: 12
  request_delay_min: 0.2
  request_delay_max: 0.5
```

## 更新日志

### 2026-09-08 (v3) 大修版
- **四站并行 + 独立窗口**：选择几个站点就显示几个独立状态面板，各自展示状态/进度/成功/跳过/失败/独立日志，同时爬取互不干扰
- **速度档位**：新增稳定/平衡/快速三档（默认平衡），非法值自动回落
- **站内详情并发**：每站详情页并发解析（ACG游戏姬3、其余站点2），明显提速
- **图片灯箱**：主界面和离线导出HTML均支持点击图片放大、左右切换、键盘导航、Esc关闭
- **数据清理**：修复萌幻ACG 261条无网盘链接历史脏数据（备份后清理，卡片不再缺下载按钮）
- **平台修复**：ACG俱乐部unknown平台按正文标签回退识别，全库unknown归零
- **任务状态**：异常退出重启后遗留running任务自动标记为"已中断"，前端显示全部6种状态
- **导出修复**：每次导出前清空旧图片目录，不再混入历史残留图片（744MB→1.06MB）
- **链接提取**：支持HTML实体反转义（&amp;等），正则覆盖更全
- **稳定性**：SQLite启用WAL+写入锁+锁重试；连续失败指数退避+熔断；验证页检测
- **安全**：图片代理接口增加SSRF防护（拒绝环回/私有/file协议）；Flask默认关闭debug重载

### 2026-09-07 (v2)
- 标题括号统一：所有标题[]改为【】，包括标签、大小、云名
- 标签自动检测：标题中平台/大小前的额外标签（官中版、AI汉化、步兵版等）自动移到开头【】
- 图片高度增大：卡片图片从160px增加到250px
- 解压码/作弊码改为按钮：点击按钮复制"解压码：xxx"到剪贴板
- 双网盘排序优化：所有双网盘帖子置顶显示，移除"低热度下沉"规则
- 置顶帖过滤：各站自动跳过教程、合集、工具等置顶帖
- 残留斜杠修复：【PC/3.87G】→【PC 3.87G】
- 萌幻ACG标题自动补平台：【12.53GB】→【PC 12.53GB】
- 移动云盘链接修复：正则支持完整URL（含/#/参数）
- 导出修复：copyText按钮现在正确复制data-copy内容（而非按钮文字）
- 导出修复：导出"全部"平台时返回PC+安卓文件（而非仅PC）
- 数据库修复：get_posts_by_crawl_id排序和平台过滤与主查询一致
- 全项目审查：修复parser中fix_title_tags对【】括号的处理

### 2026-09-07 (v1)
- 修复标题双[PC+安卓]和PCC前缀问题
- 修复评论数据提取
- 移除"仅安卓"分类，全部归入PC+安卓
- 导出改为zip格式（HTML+图片打包）
- 优化图片下载（直连优先）
- 添加ACG俱乐部爬虫支持

### 2026-09-06
- 实现4个站点爬虫
- 实现Web界面
- 实现导出功能
- 添加图片下载和本地存储

## 许可证

仅供个人学习研究使用，请勿用于商业用途。
