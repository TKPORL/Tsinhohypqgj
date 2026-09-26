# 旧版视觉风格存档 —— 「Origin 深色编辑风」

> 存档时间：2026-09-26
> 来源：git 提交 `b9f5769`（2026-09-23 换上，2026-09-26 被替换）
> 替换为：**深色 · 粉紫**（当前风格）

## 为什么换掉

用户反馈「风格看着有点怪，不太喜欢」。排查后确认问题不在深色，而在**这套排版是照着英文财经网站做的，直接套在中文工具上**：

1. **中文被当英文排** —— 全站小标签都套了 `font-mono + letter-spacing: 0.182em + text-transform: uppercase`。中文没有大小写，`uppercase` 对它无效，但 `letter-spacing` 实打实生效，于是「目 标 站 点」「爬 取 模 式」被撑得松散别扭。
2. **中文大标题掉到衬线字体上** —— `--font-display` 是 `Playfair Display`（无中文字形），实际回退到 `Noto Serif SC` / `SimSun`，细笔画带衬线，像杂志印刷品。
3. **满屏英文装饰** —— `header h1::before` 硬编码 `LOCAL ARCHIVE · 2026`、导出卡图标写死 `PC` / `PC+安卓`、所有标签统一大写。
4. **冷色 + 大色块抢戏** —— 白灰加紫偏冷；结果页三条满幅色块（`.date-group-header[data-plat]`）面积大、比游戏封面还抢眼。

## 文件清单

| 文件 | 作用 | 说明 |
|------|------|------|
| `主界面-style.css` | 主界面样式（旧版） | 纯样式，可直接覆盖回 `acg_crawler/static/style.css` |
| `主界面-index.html` | 主界面模板（旧版） | ⚠️ 仅作参考。旧版的站点列表是硬编码的，且「重新下载图片」在爬取操作区、批次删除在导出页 |
| `导出模块-style段.css` | 导出 HTML 的 `<style>` 段（旧版） | ⚠️ 只能手工替换 `generator/__init__.py` 里 `HTML_TEMPLATE` 的 `<style>` 段，不能整文件覆盖 |

## 旧风格的视觉规格（关键参数）

```css
/* 调色板 */
--iris: #847dff;  --cyan: #00b3dd;  --orchid: #dd90d8;  --deep-iris: #4b49aa;
--obsidian: #0f1011;  /* 画布 */
--abyss: #090a0b;     /* 最底层 */
--graphite: #2e2e2e;  /* 卡片 */
--steel: #3f4041;     /* hover */
--fog: #6a6b6b; --ash: #9f9fa0; --cloud: #f5f5f7; --pure: #ffffff; --void: #000000;
--danger: #c0574e;

/* 字体 */
--font-display: 'Playfair Display', 'Noto Serif SC', ..., serif;   /* 标题 */
--font-ui: 'Geist', 'Inter', ..., sans-serif;                      /* 正文 */
--font-mono: 'Roboto Mono', ..., monospace;                        /* 标签，大写 + 0.182em */

/* 特征 */
- 明暗靠表面色阶区分，卡片无 box-shadow、无上浮
- 彩色只用于满幅分类色块；主操作永远是白底黑字（带 → 箭头）
- 结果页平台分组头 = 满幅大色块（.date-group-header[data-plat]）
- 芯片统一胶囊（白 12% 底 + 15% 描边）
- 顶栏吸顶 + backdrop-filter: blur(24px)
```

## 怎么切回旧风格

⚠️ **不要直接 `git checkout HEAD -- <文件>` 全量覆盖** —— 这会把 2026-09-26 之后新增的功能一起回退（站点动态渲染、总览条、日期动态默认值等）。

正确做法：

### 只换主界面样式

```bash
cd "D:/Tsinho文件夹/新Tsinho黄油爬取工具"
cp "docs/风格存档/旧版-Origin深色编辑风/主界面-style.css" "acg_crawler/static/style.css"
```

⚠️ 但当前 `index.html` 已经改了结构（总览条、结果页两行工具栏、批量条移到 `main` 外、历史表格包了 `.table-wrap`）。旧 `style.css` 里没有这些新结构的样式，切回去会出现裸样式。**要完整回退，必须连 `index.html` 一起换**，而那样会丢掉站点动态渲染。

### 导出 HTML

只能手工替换 `acg_crawler/generator/__init__.py` 里 `HTML_TEMPLATE` 的 `<style>` 段，保留功能部分（`{note}` 备注占位、卡片模板结构、备注折叠 JS）。

## 相关文档

- 视觉系统现状：`【项目全解】说明文档.md` → 「五、视觉系统」
- 变更来龙去脉：`【变更记录】修改日志.md`
- 另一份更早的存档：`docs/风格存档/旧版-粉紫渐变/`（2026-09-08 之前的风格）
