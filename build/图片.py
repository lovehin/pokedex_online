#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三步：把官方图鉴图压成网页用的尺寸，再顺手画分享图和 PWA 图标。

产物：
  img/pokemon/<id>.webp     详情页用（240px）
  img/pokemon/s/<id>.webp   列表页用（96px）
  img/items/<名字>.png      道具图标（上游本来就是 30px 的小图，直接搬）
  icons/*.png               PWA 图标
  og/default.jpg            通用分享图（1200×630）
  og/type-<属性>.jpg        18 张按属性的分享图

⚠️ 分享图**不逐只宝可梦生成**：1025 只就是 1025 张图，几十兆，不值当。
   通用一张 + 按属性 18 张就够用，也够搜索引擎抓。

用法：python3 build/图片.py
"""
import io
import os
import sys
import shutil
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 映射表 as M                                                   # noqa: E402

RAW = os.path.join(BASE, 'build', '_raw')
IMG = os.path.join(BASE, 'img')
OG = os.path.join(BASE, 'og')
ICONS = os.path.join(BASE, 'icons')

详情尺寸 = 240
列表尺寸 = 96
V = '1'

# 中文字体：macOS 自带的就行。找不到字体时分享图上不写字（不能因为这个让整站构建失败）。
字体候选 = [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
]


def 取字体(大小):
    for 路径 in 字体候选:
        if os.path.exists(路径):
            try:
                return ImageFont.truetype(路径, 大小)
            except Exception:
                continue
    return None


def 已是最新(源, 目标):
    return (os.path.exists(目标)
            and os.path.getmtime(目标) >= os.path.getmtime(源)
            and os.path.getsize(目标) > 0)


def 转webp(源, 目标, 边长):
    if 已是最新(源, 目标):
        return '命中'
    os.makedirs(os.path.dirname(目标), exist_ok=True)
    with Image.open(源) as im:
        im = im.convert('RGBA')
        比 = 边长 / float(max(im.size))
        新尺寸 = (max(1, int(round(im.size[0] * 比))), max(1, int(round(im.size[1] * 比))))
        im = im.resize(新尺寸, Image.LANCZOS)
        底 = Image.new('RGBA', (边长, 边长), (255, 255, 255, 0))
        底.paste(im, ((边长 - 新尺寸[0]) // 2, (边长 - 新尺寸[1]) // 2), im)
        底.save(目标, 'WEBP', quality=82, method=5)
    return '转好'


def main():
    统计 = {'命中': 0, '转好': 0, '缺源': 0}
    原图目录 = os.path.join(RAW, 'artwork')
    if not os.path.isdir(原图目录):
        print('没有找到 build/_raw/artwork/，先跑一次 python3 build/取数据.py')
        return
    print('一、宝可梦图（%d 张 × 2 档）' % len(os.listdir(原图目录)))
    for 文件名 in sorted(os.listdir(原图目录)):
        if not 文件名.endswith('.png'):
            continue
        编号 = 文件名[:-4]
        源 = os.path.join(原图目录, 文件名)
        for 边长, 子目录 in ((详情尺寸, ''), (列表尺寸, 's')):
            目标 = os.path.join(IMG, 'pokemon', 子目录, 编号 + '.webp') if 子目录 \
                else os.path.join(IMG, 'pokemon', 编号 + '.webp')
            统计[转webp(源, 目标, 边长)] += 1
    print('   命中 %d · 新转 %d' % (统计['命中'], 统计['转好']))

    print('二、道具图标')
    道具源 = os.path.join(RAW, 'items')
    道具数 = 0
    if os.path.isdir(道具源):
        os.makedirs(os.path.join(IMG, 'items'), exist_ok=True)
        for 文件名 in os.listdir(道具源):
            if not 文件名.endswith('.png'):
                continue
            目标 = os.path.join(IMG, 'items', 文件名)
            if not os.path.exists(目标):
                shutil.copyfile(os.path.join(道具源, 文件名), 目标)
            道具数 += 1
    print('   共 %d 个' % 道具数)

    print('三、PWA 图标')
    画图标()

    print('四、分享图（通用 1 张 + 属性 18 张）')
    画分享图()

    print('\n完成。下一步：python3 build/生成页面.py')


# ---------------------------------------------------------------- 画图
def _球(d, cx, cy, r, 线='#16233c'):
    """画一个精灵球（就是 favicon 那个的样子，放大版）。"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#ffffff', outline=线, width=max(3, r // 12))
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill='#e8453c')
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=线, width=max(3, r // 12))
    d.line([cx - r, cy, cx + r, cy], fill=线, width=max(3, r // 12))
    d.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], fill='#ffffff',
              outline=线, width=max(3, r // 12))


def 画图标():
    os.makedirs(ICONS, exist_ok=True)
    for 尺寸, 名字 in ((192, 'icon-192.png'), (512, 'icon-512.png'), (180, 'apple-touch-icon.png')):
        路径 = os.path.join(ICONS, 名字)
        if os.path.exists(路径):
            continue
        im = Image.new('RGB', (尺寸, 尺寸), '#ffffff')
        d = ImageDraw.Draw(im)
        _球(d, 尺寸 // 2, 尺寸 // 2, int(尺寸 * 0.42))
        im.save(路径)


def 画分享图():
    os.makedirs(OG, exist_ok=True)
    宽, 高 = 1200, 630
    总名 = '究极宝可梦图鉴'
    副标 = '宝可梦 · 招式 · 特性 · 道具 · 性格 在线查'
    目标 = os.path.join(OG, 'default.jpg')
    if not os.path.exists(目标):
        im = Image.new('RGB', (宽, 高), '#ffffff')
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 宽, 10], fill='#1f7a63')
        _球(d, 1060, 470, 150)
        f1, f2 = 取字体(84), 取字体(38)
        if f1:
            d.text((90, 210), 总名, font=f1, fill='#16233c')
        if f2:
            d.text((94, 330), 副标, font=f2, fill='#5a6a80')
        im.save(目标, quality=88)

    for key in M.属性顺序:
        名, 色 = M.属性[key]
        目标 = os.path.join(OG, 'type-%s.jpg' % key)
        if os.path.exists(目标):
            continue
        im = Image.new('RGB', (宽, 高), '#ffffff')
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 宽, 14], fill=色)
        d.ellipse([820, 120, 1180, 480], fill=色)
        f1, f2, f3 = 取字体(76), 取字体(40), 取字体(30)
        if f1:
            d.text((90, 180), '%s属性宝可梦' % 名, font=f1, fill='#16233c')
        if f2:
            d.text((94, 300), '属性相克 · 种族值 · 特性 · 进化一览', font=f2, fill='#5a6a80')
        if f3:
            d.text((94, 500), 总名, font=f3, fill=色)
        im.save(目标, quality=88)


if __name__ == '__main__':
    main()
