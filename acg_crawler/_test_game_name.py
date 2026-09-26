# -*- coding: utf-8 -*-
"""游戏名 / 纯名字 提取的单测（用户 2026-09-26 需求）。

两个函数：
  extract_game_name(title)  → 「游戏名【平台 大小】」= 网盘文件夹名
  extract_bare_name(title)  → 「纯游戏名」= 发帖表单「游戏名称」栏
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from parser import extract_game_name, extract_bare_name  # noqa: E402

# (原文, 期望的网盘名, 期望的纯名字)
CASES = [
    # 用户截图里的例子（半角括号 + 平台后缀 + 编号紧贴）
    ("[爆款互动SLG/3D动态/官方中文去码版+DLC] 傲娇少女与看不见的幽灵 なまいき娘と見えない幽霊 v2.7.1[PC+安卓盖世]15864",
     "傲娇少女与看不见的幽灵 なまいき娘と見えない幽霊 v2.7.1【PC+安卓】",
     "傲娇少女与看不见的幽灵 なまいき娘と見えない幽霊 v2.7.1"),
    # 带体积的标准写法
    ("【更新/欧美SLG/动态/汉化版】药丸王 Pill King v0.37【PC+安卓 8.80G】 【C224444】",
     "药丸王 Pill King v0.37【PC+安卓 8.80G】",
     "药丸王 Pill King v0.37"),
    # 多个平台括号 → 取信息最全的（含安卓优先），不是取最后一个
    ("真·恋姬†无双～萌将传～ 【PC+安卓】【PC】【简体中文】",
     "真·恋姬†无双～萌将传～【PC+安卓】",
     "真·恋姬†无双～萌将传～"),
    # 套娃括号（鲲站旧数据）
    ("越界恋人!! 【【PC/盖世/Winlator】附全CG存档+特典】【PC+安卓】",
     "越界恋人!!【PC+安卓】",
     "越界恋人!!"),
    # 裸编号紧贴方括号标签在开头（ACG俱乐部）
    ("15395[RPG/百合/纯爱]我们还是好朋友的时候 私たちがまだ親友だった頃 AI汉化[PC+安卓]",
     "我们还是好朋友的时候 私たちがまだ親友だった頃 AI汉化【PC+安卓】",
     "我们还是好朋友的时候 私たちがまだ親友だった頃 AI汉化"),
    # 前缀词 + 标签括号
    ("新DLC【爆款RPG/拘束调教/动态】 诅咒铠甲2：灵魔女传奇 呪いの鎧II(霊魔女傳奇) v7.27 Steam官中步兵版+DLC【独角兽牧场】+补丁+存档",
     "诅咒铠甲2：灵魔女传奇 呪いの鎧II(霊魔女傳奇) v7.27 Steam官中步兵版",
     "诅咒铠甲2：灵魔女传奇 呪いの鎧II(霊魔女傳奇) v7.27 Steam官中步兵版"),
    ("增添AZ【日式SRPG/战斗H/调教扶她】 扶她女骑士塞蕾娜之被诅咒的榨精迷宫 ふたなり女騎士セレナ v1.10 内嵌AI汉化版+作弊码",
     "扶她女骑士塞蕾娜之被诅咒的榨精迷宫 ふたなり女騎士セレナ v1.10 内嵌AI汉化版",
     "扶她女骑士塞蕾娜之被诅咒的榨精迷宫 ふたなり女騎士セレナ v1.10 内嵌AI汉化版"),
    # 词表没覆盖全的平台括号（含直装/TY）
    ("密语-Silver Snow Sister- 【PC/安卓直装/TY/盖世/Winlator】",
     "密语-Silver Snow Sister【PC+安卓】",
     "密语-Silver Snow Sister"),
    # 带编号的尾巴
    ("我的乡村日常生活！ Daily Livesof My Countryside v0.3.5.2 full AI汉化步兵版+画廊mod【PC+安卓3.30G】 14295 16375",
     "我的乡村日常生活！ Daily Livesof My Countryside v0.3.5.2 full AI汉化步兵版",
     "我的乡村日常生活！ Daily Livesof My Countryside v0.3.5.2 full AI汉化步兵版"),
    # 纯名字不能误删开头的 '404'
    ("新步兵【互动3D/抚摸触摸/动态】 404号室的性感按摩 404号室の性感マッサージ v26.09.17 官中版 去码版+DLC+存档",
     "404号室的性感按摩 404号室の性感マッサージ v26.09.17 官中版 去码版",
     "404号室的性感按摩 404号室の性感マッサージ v26.09.17 官中版 去码版"),
    # 版本号括号要保留
    ("死神诱惑 Shinigami Seductions 【v0.15】 AI更新】",
     "死神诱惑 Shinigami Seductions 【v0.15】 AI更新",
     "死神诱惑 Shinigami Seductions 【v0.15】 AI更新"),
    # 名字里的方括号（中文单字）要保留
    ("恋姫†英雄譚4 ～乙女耀乱☆三国志演義[呉]～ 简体中文",
     "恋姫†英雄譚4 ～乙女耀乱☆三国志演義[呉]～ 简体中文",
     "恋姫†英雄譚4 ～乙女耀乱☆三国志演義[呉]～ 简体中文"),
    # 最基本的两种
    ("魔法少女的魔女审判【PC】", "魔法少女的魔女审判【PC】", "魔法少女的魔女审判"),
    ("永不枯萎的世界与终结之花【PC+安卓】", "永不枯萎的世界与终结之花【PC+安卓】", "永不枯萎的世界与终结之花"),
]

fails = 0
for raw, exp_net, exp_bare in CASES:
    g = extract_game_name(raw)
    b = extract_bare_name(raw)
    ok = (g == exp_net) and (b == exp_bare)
    if not ok:
        fails += 1
    print(("PASS " if ok else "FAIL ") + raw[:46])
    if not ok:
        if g != exp_net:
            print("   网盘名 期望:", exp_net)
            print("   网盘名 实际:", g)
        if b != exp_bare:
            print("   纯名字 期望:", exp_bare)
            print("   纯名字 实际:", b)

print()
print("用例数:", len(CASES), " 失败数:", fails)
sys.exit(1 if fails else 0)
