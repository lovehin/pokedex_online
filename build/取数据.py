#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一步：把上游数据取到本地。

数据来源全部是 PokeAPI 官方仓库（开源，来源干净）：
  · 表格数据  https://github.com/PokeAPI/pokeapi    的 data/v2/csv/
  · 图片数据  https://github.com/PokeAPI/sprites
  · 拼音数据  https://github.com/mozillazg/pinyin-data

下载下来的东西放在 build/_raw/ 里（已在 .gitignore 中排除，不进仓库）。
已经下好且非空的文件会自动跳过，所以这个脚本可以反复跑。

⚠️ 直连不通（墙、代理、公司网关）时，设一下 HTTPS_PROXY / HTTP_PROXY 环境变量即可，不用改这个脚本。

用法：python3 build/取数据.py            # 缺什么下什么
     python3 build/取数据.py --重下      # 全部重下
"""
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'build', '_raw')
# 不显式传 ProxyHandler 时，urllib 会退回默认处理器并自动认环境变量
# （HTTP_PROXY / HTTPS_PROXY），所以要挂代理不用改这里。

# ⚠️ 这台机器上的 python.org 版 Python 没有自带根证书，不指定 cafile 会报
#    「CERTIFICATE_VERIFY_FAILED」。优先用 certifi，退而用 macOS 自带的证书包。
try:
    import certifi
    _CA = certifi.where()
except Exception:
    _CA = '/etc/ssl/cert.pem'
_SSL = ssl.create_default_context(cafile=_CA)

OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL))
OPENER.addheaders = [('User-Agent', 'pokedex-online-build/1.0')]

CSV_BASE = 'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'
SPRITE_BASE = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/'

# 需要的 CSV —— 加一列要改的不只是这里，还要改 生成数据.py
CSVS = [
    'languages',
    'generations', 'generation_names',
    'pokemon', 'pokemon_species', 'pokemon_species_names', 'pokemon_species_flavor_text',
    'pokemon_names', 'pokemon_stats', 'pokemon_types', 'pokemon_abilities', 'pokemon_moves',
    'pokemon_forms', 'pokemon_form_names', 'evolution_chains', 'pokemon_evolution',
    'evolution_triggers', 'locations', 'location_names', 'pokemon_move_methods',
    'moves', 'move_names', 'move_flavor_text', 'move_effect_prose', 'move_damage_classes',
    'abilities', 'ability_names', 'ability_flavor_text', 'ability_prose',
    'items', 'item_names', 'item_flavor_text', 'item_categories', 'item_category_prose',
    'natures', 'nature_names',
    'types', 'type_names', 'type_efficacy',
    'stats', 'stat_names',
]


def 下载(url, 目标, 重试=3, 超时=60):
    """下到目标路径；已存在且非空就直接跳过（缓存）。返回 '命中' / '下好' / '失败'。"""
    if os.path.exists(目标) and os.path.getsize(目标) > 0:
        return '命中'
    os.makedirs(os.path.dirname(目标), exist_ok=True)
    for i in range(重试):
        try:
            with OPENER.open(url, timeout=超时) as resp:
                data = resp.read()
            if not data:
                raise IOError('空响应')
            tmp = 目标 + '.part'
            with open(tmp, 'wb') as fh:
                fh.write(data)
            os.replace(tmp, 目标)
            return '下好'
        except urllib.error.HTTPError as e:
            if e.code == 404:            # 上游本来就没有这个东西，正常
                return '没有'
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return '失败'


def 取CSV():
    print('一、表格数据（%d 个 CSV）' % len(CSVS))
    统计 = {'命中': 0, '下好': 0, '没有': 0, '失败': []}
    for 名 in CSVS:
        结果 = 下载(CSV_BASE + 名 + '.csv', os.path.join(RAW, 名 + '.csv'))
        if 结果 == '失败':
            统计['失败'].append(名)
        else:
            统计[结果] += 1
        print('  %-32s %s' % (名 + '.csv', 结果))
    return 统计


def 取拼音():
    print('二、拼音数据')
    print('  pinyin.txt                       %s'
          % 下载('https://raw.githubusercontent.com/mozillazg/pinyin-data/master/pinyin.txt',
                 os.path.join(RAW, 'pinyin.txt')))


def 取图鉴图():
    print('三、官方图鉴图（1025 张，约 100MB，第一次比较慢）')
    目标s = []
    for i in range(1, 1026):
        目标s.append((SPRITE_BASE + 'pokemon/other/official-artwork/%d.png' % i,
                     os.path.join(RAW, 'artwork', '%d.png' % i)))
    return _批量(目标s, '图鉴图')


def 取道具图():
    print('四、道具图标')
    名字 = []
    路径 = os.path.join(RAW, 'items.csv')
    if os.path.exists(路径):
        import csv
        with open(路径, encoding='utf-8') as fh:
            for 行 in csv.DictReader(fh):
                名字.append(行['identifier'])
    目标s = [(SPRITE_BASE + 'items/%s.png' % n, os.path.join(RAW, 'items', n + '.png'))
             for n in 名字]
    return _批量(目标s, '道具图标')


def _批量(目标s, 标签, 并发=8):
    结果 = {'命中': 0, '下好': 0, '没有': 0, '失败': 0}
    def 一个(t):
        return 下载(t[0], t[1])
    with ThreadPoolExecutor(max_workers=并发) as 池:
        for i, r in enumerate(池.map(一个, 目标s), 1):
            结果[r] = 结果.get(r, 0) + 1
            if i % 100 == 0 or i == len(目标s):
                print('  %s %d/%d（命中 %d · 新下 %d · 失败 %d）'
                      % (标签, i, len(目标s), 结果['命中'], 结果['下好'], 结果['失败']),
                      end='\r' if i < len(目标s) else '\n')
    return 结果


def main():
    重下 = '--重下' in sys.argv
    if 重下:
        import shutil
        shutil.rmtree(RAW, ignore_errors=True)
        print('已清空缓存，全部重下。\n')
    os.makedirs(RAW, exist_ok=True)

    表 = 取CSV()
    取拼音()
    图 = 取图鉴图()
    道 = 取道具图()

    print('\n完成。')
    print('  CSV   命中缓存 %d · 新下载 %d · 失败 %s'
          % (表.get('命中', 0), 表.get('下好', 0), 表.get('失败') or '无'))
    print('  图鉴图 命中 %d · 新下 %d · 缺失 %d · 失败 %d'
          % (图['命中'], 图['下好'], 图['没有'], 图['失败']))
    print('  道具图 命中 %d · 新下 %d · 缺失 %d · 失败 %d'
          % (道['命中'], 道['下好'], 道['没有'], 道['失败']))
    print('\n下一步：python3 build/生成数据.py')


if __name__ == '__main__':
    main()
