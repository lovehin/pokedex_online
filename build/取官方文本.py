#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 1.5 步：取官方游戏文本，用来补齐 PokeAPI 缺的中文说明。

PokeAPI 的中文说明来自官方游戏，但它只收录到第 7～8 世代的一部分：
第 8、9 世代有 111 个招式、107 个特性、663 条道具在它那里没有简体中文。
这些条目官方其实是有中文的（游戏里就有），只是 PokeAPI 还没收进去。

所以这里从开源的游戏文本导出仓库里取**官方简中原文**，按名称补上空缺：

  · 宝可梦 朱／紫 1.3.2      tanripj/pokemon_text_dumps   （基底，数组与编号一一对应）
  · 宝可梦 朱／紫 3.0.1      tanripj/pokemon_text_dumps   （含 DLC，说明数组比名称多一条，要错位取）
  · 宝可梦传说 Z-A 2.0.1     tanripj/pokemon_text_dumps   （补超级石一类 Z-A 才有的道具）

产物是 build/人工数据/官方文本补全.json（进仓库），生成数据.py 直接读它。
**只补 PokeAPI 里空缺的条目**，已有中文的一律不动；也绝不自己翻译。

⚠️ 直连不通（墙、代理、公司网关）时，设一下 HTTPS_PROXY / HTTP_PROXY 环境变量即可，不用改这个脚本。

用法：python3 build/取官方文本.py       # 缺什么下什么
     python3 build/取官方文本.py --重下  # 全部重下
"""
import csv
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'build', '_raw')
官方文本目录 = os.path.join(RAW, '官方文本')
人工数据 = os.path.join(BASE, 'build', '人工数据')
产物 = os.path.join(人工数据, '官方文本补全.json')

# 不显式传 ProxyHandler 时，urllib 会退回默认处理器并自动认环境变量
# （HTTP_PROXY / HTTPS_PROXY），所以要挂代理不用改这里。
try:
    import certifi
    _CA = certifi.where()
except Exception:
    _CA = '/etc/ssl/cert.pem'
_SSL = ssl.create_default_context(cafile=_CA)
OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL))
OPENER.addheaders = [('User-Agent', 'pokedex-online-build/1.0')]

上游 = 'https://raw.githubusercontent.com/tanripj/pokemon_text_dumps/main/'
文件 = [
    ('sv132', 'sv/1.3.2/gametext/sv-1.3.2_gametext_chinese_simplified.txt'),
    ('sv301', 'sv/3.0.1/gametext/sv-3.0.1_gametext_chinese_simplified.txt'),
    ('za201', 'za/2.0.1/gametext/za-2.0.1_gametext_chinese_simplified.txt'),
]


def 下载(url, 目标, 重试=3, 超时=90):
    if os.path.exists(目标) and os.path.getsize(目标) > 0:
        return '命中'
    os.makedirs(os.path.dirname(目标), exist_ok=True)
    for i in range(重试):
        try:
            with OPENER.open(url, timeout=超时) as resp:
                data = resp.read()
            if not data:
                raise IOError('空响应')
            with open(目标 + '.part', 'wb') as fh:
                fh.write(data)
            os.replace(目标 + '.part', 目标)
            return '下好'
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return '没有'
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return '失败'


# ---------------------------------------------------------------- 解析
def 读文本(路径):
    """把导出的文本文件切成 节名 → 行列表。文件是 UTF-8（带 BOM）、CRLF。"""
    with io.open(路径, encoding='utf-8-sig', newline='') as fh:
        原文 = fh.read()
    节们 = {}
    当前 = None
    for 行 in 原文.split('\n'):
        行 = 行.rstrip('\r')
        if 行.startswith('Text File : '):
            当前 = 行[len('Text File : '):].strip()
            if 当前.endswith('.dat'):
                当前 = 当前[:-4]
            节们[当前] = []
        elif 行.startswith('~~~~'):
            continue
        elif 当前 is not None:
            节们[当前].append(行)
    return 节们


def 清洗(文本):
    """游戏文本里的换行写成字面量 \\n；[VAR xx] 之类是占位符，一并收拾干净。"""
    if not 文本:
        return ''
    文本 = 文本.replace('\\n', ' ').replace('\\r', ' ')
    文本 = re.sub(r'\[[^\]]*\]', '', 文本)
    return re.sub(r'\s+', ' ', 文本).strip()


def 是占位(文本):
    """游戏里没写说明的条目会填一串破折号、长音符或 N/A，这种当没有处理。"""
    if re.fullmatch(r'[\s―—–-─·。、，．.,:：;；ー－？！]+', 文本):
        return True
    return 文本.strip().upper() in ('N/A', 'NA', 'NONE', '--', '？？？')


def 配对(节们, 名节, 文节, 错位=None):
    """名称数组和说明数组成对读出来：名称第 k 条配说明第 k 条。
    错位 是 V3.0.1 那种「说明数组多一条」的修正函数。"""
    名们 = 节们.get(名节) or []
    文们 = 节们.get(文节) or []
    结果 = {}
    for k in range(len(名们)):
        名 = 名们[k].strip()
        if not 名 or 名 in ('―', '―――――', '---'):
            continue
        j = 错位(k) if 错位 else k
        if not (0 <= j < len(文们)):
            continue
        文 = 清洗(文们[j])
        if not 文 or 是占位(文) or 文.startswith('['):
            continue
        旧 = 结果.get(名)
        if 旧 is None:
            结果[名] = 文
        elif is_配方(旧) and not is_配方(文):
            结果[名] = 文              # 配方文案排在正说明前面，优先留正说明
    return 结果


def is_配方(文本):
    """朱紫 / Z-A 里球类可以自己制作，同名的「材料单」不是这个道具的说明。"""
    return '材料单' in 文本


def 朱紫错位(k):
    """朱紫 3.0.1 的 wazainfo 比 wazaname 多一条（太晶爆发的说明占了两格），
    从下标 852 起要往后挪一格。已用 1.3.2 与英文版逐条核对过。"""
    return k if k < 852 else k + 1


# ---------------------------------------------------------------- 缺什么
def 读表(名):
    with io.open(os.path.join(RAW, 名 + '.csv'), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def 有简中(行们, id键, 文键):
    """返回「已经有简体中文说明」的 id 集合，口径和生成数据.py 完全一致。"""
    有 = set()
    for 行 in 行们:
        if 行.get('language_id') == '12' and (行.get(文键) or '').strip():
            有.add(行[id键])
    return 有


def 简中名(行们, id键, 字段='name'):
    表 = {}
    for 行 in 行们:
        if 行.get('local_language_id') == '12':
            表[行[id键]] = 行[字段]
    return 表


def 挑缺的(全表, 已存在, 名表, 词表):
    """全表里还缺中文说明、且词表里能查到的条目 → {中文名: 官方说明}"""
    结果 = {}
    for 键 in sorted(全表, key=lambda x: int(x)):
        if 键 in 已存在:
            continue
        名 = (名表.get(键) or '').strip()
        if 名 and 名 in 词表:
            结果[名] = 词表[名]
    return 结果


def main():
    if '--重下' in sys.argv:
        import shutil
        shutil.rmtree(官方文本目录, ignore_errors=True)
        print('已清空官方文本缓存，全部重下。\n')

    print('一、下载官方文本导出')
    节 = {}
    for 键, 路径 in 文件:
        状态 = 下载(上游 + 路径, os.path.join(官方文本目录, 键 + '.txt'))
        print('  %-8s %s' % (键, 状态))
        if 状态 in ('命中', '下好'):
            节[键] = 读文本(os.path.join(官方文本目录, 键 + '.txt'))

    if 'sv301' not in 节:
        print('\n没拿到朱紫 3.0.1 的文本，没法补。检查一下代理和网络再跑一次。')
        return 1

    print('\n二、配对名称与说明（新版本优先）')
    招式词表 = {}
    for 源, 修正 in (('sv301', 朱紫错位), ('sv132', None), ('za201', None)):
        if 源 in 节:
            招式词表.update({k: v for k, v in 配对(节[源], 'wazaname', 'wazainfo', 修正).items()
                          if k not in 招式词表})
    特性词表 = {}
    for 源 in ('sv301', 'za201', 'sv132'):
        if 源 in 节:
            特性词表.update({k: v for k, v in 配对(节[源], 'tokusei', 'tokuseiinfo').items()
                          if k not in 特性词表})
    道具词表 = {}
    for 源 in ('sv301', 'za201', 'sv132'):
        if 源 in 节:
            道具词表.update({k: v for k, v in 配对(节[源], 'itemname', 'iteminfo').items()
                          if k not in 道具词表})
    print('  官方说明可用：招式 %d 条 · 特性 %d 条 · 道具 %d 条'
          % (len(招式词表), len(特性词表), len(道具词表)))

    if not os.path.exists(os.path.join(RAW, 'moves.csv')):
        print('\n还没跑过 build/取数据.py，缺 PokeAPI 的表格，没法判断哪些条目要补。')
        return 1

    print('\n三、挑出 PokeAPI 里缺中文的条目')
    招式 = 挑缺的({行['id'] for 行 in 读表('moves')},
                有简中(读表('move_flavor_text'), 'move_id', 'flavor_text'),
                简中名(读表('move_names'), 'move_id'), 招式词表)
    特性名表 = 简中名(读表('ability_names'), 'ability_id')
    特性 = 挑缺的({行['id'] for 行 in 读表('abilities')},
                有简中(读表('ability_flavor_text'), 'ability_id', 'flavor_text'),
                特性名表, 特性词表)
    道具 = 挑缺的({行['id'] for 行 in 读表('items')},
                有简中(读表('item_flavor_text'), 'item_id', 'flavor_text'),
                简中名(读表('item_names'), 'item_id'), 道具词表)
    print('  能补：招式 %d 条 · 特性 %d 条 · 道具 %d 条'
          % (len(招式), len(特性), len(道具)))

    结果 = {
        '_备注': 'PokeAPI 缺中文说明的条目，用官方游戏简中原文补齐（只补空的，不覆盖已有）。'
                 '由 build/取官方文本.py 生成，不要手改。',
        '_来源': [上游 + p for _, p in 文件],
        '招式': 招式,
        '特性': 特性,
        '道具': 道具,
    }
    os.makedirs(人工数据, exist_ok=True)
    with io.open(产物, 'w', encoding='utf-8') as fh:
        json.dump(结果, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write('\n')
    print('\n写好 %s（%.0f KB）' % (os.path.relpath(产物, BASE), os.path.getsize(产物) / 1024.0))
    print('下一步：python3 build/生成数据.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
