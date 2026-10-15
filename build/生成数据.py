#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二步：把 PokeAPI 的 CSV 整理成站点要用的 JSON。

产物分两处：
  data/           浏览器要读的轻量索引（搜索、列表筛选用），会进仓库、会部署
  build/_out/     生成页面用的全量数据，不进仓库（体积大）

⚠️ 数据铁律：官方中文说明缺失时**留空**，页面那边会写「暂无官方中文说明」。
   这里绝不自己翻译、绝不从别站抄一段填进去。
   第 8、9 世代有一部分条目 PokeAPI 没中文、官方游戏里其实有 —— 那些由
   build/取官方文本.py 从官方游戏文本里取出来，放在官方文本模块里补空，不是编的。

用法：python3 build/生成数据.py
"""
import csv
import io
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 映射表 as M                                                  # noqa: E402
import 官方文本                                                     # noqa: E402

RAW = os.path.join(BASE, 'build', '_raw')
OUT = os.path.join(BASE, 'build', '_out')
DATA = os.path.join(BASE, 'data')

语言 = {'en': 9, 'ja': 11, 'zh-hans': 12, 'zh-hant': 4}


# ---------------------------------------------------------------- 读表
def 读表(名):
    with io.open(os.path.join(RAW, 名 + '.csv'), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def 索引(行们, 键):
    d = defaultdict(list)
    for 行 in 行们:
        d[行[键]].append(行)
    return d


def 单值索引(行们, 键):
    return {行[键]: 行 for 行 in 行们}


def 取名字(索引表, id_键, id_值, 语文, 字段='name'):
    """从 xx_names.csv 里取某个东西的某种语言的名字。"""
    for 行 in 索引表.get(str(id_值), []):
        if 行['local_language_id'] == str(语言[语文]):
            return 行[字段]
    return ''


def 取说明(索引表, id_值, 语文='zh-hans', 字段='flavor_text', 取最新=True):
    """从 xx_flavor_text.csv 取说明文字。同一语言多个版本时，版本组号最大的优先（最新游戏里的说法）。"""
    候选 = [行 for 行 in 索引表.get(str(id_值), [])
            if 行['language_id'] == str(语言[语文]) and 行.get(字段)]
    if not 候选:
        return ''
    候选.sort(key=lambda r: int(r.get('version_group_id') or 0), reverse=取最新)
    文本 = 候选[0][字段]
    return 清洗(文本)


def 清洗(文本):
    """游戏里的换行符很脏（\n、\u00ad 软连字符、\f 换页），统一成一行；
    [VAR 0102(0000)] 这类是游戏里的占位符（PokeAPI 忘了清），一并不留。"""
    文本 = re.sub(r'\[[^\]]*\]', '', 文本)
    return (文本.replace('\u00ad', '').replace('\x0c', ' ').replace('\n', ' ')
            .replace('\r', ' ').replace('  ', ' ').strip())


# ---------------------------------------------------------------- 拼音
def 读拼音表():
    表 = {}
    路径 = os.path.join(RAW, 'pinyin.txt')
    with io.open(路径, encoding='utf-8') as fh:
        for 行 in fh:
            if not 行.startswith('U+'):
                continue
            码, 拼音 = 行.split('#')[0].split(':', 1)
            字 = chr(int(码.strip()[2:], 16))
            # 多音字取第一个读音（宝可梦名字里够用了），再去掉声调
            音 = 拼音.strip().split(',')[0]
            表[字] = ''.join(c for c in unicodedata.normalize('NFD', 音)
                            if unicodedata.category(c) != 'Mn')
    return 表


拼音表 = 读拼音表()


def 拼音(中文):
    """中文名 → (全拼, 首字母)。非汉字（如「·」）直接跳过。"""
    全 = []
    for 字 in 中文:
        音 = 拼音表.get(字)
        if 音:
            全.append(音)
    return ''.join(全), ''.join(p[0] for p in 全 if p)


def 拼音字段(中文):
    全, 首 = 拼音(中文)
    return {'py': 全, 'pyInit': 首}


# ---------------------------------------------------------------- 主流程
def main():
    print('读表……')
    宝可梦表 = 读表('pokemon')
    物种表 = 读表('pokemon_species')
    物种名表 = 索引(读表('pokemon_species_names'), 'pokemon_species_id')
    物种说明表 = 索引(读表('pokemon_species_flavor_text'), 'species_id')
    种族值表 = 索引(读表('pokemon_stats'), 'pokemon_id')
    属性表 = 索引(读表('pokemon_types'), 'pokemon_id')
    特性表 = 索引(读表('pokemon_abilities'), 'pokemon_id')
    招式表_宝可梦 = 索引(读表('pokemon_moves'), 'pokemon_id')
    形态表 = 读表('pokemon_forms')
    形态按宝可梦 = 索引(形态表, 'pokemon_id')
    宝可梦按id = 单值索引(宝可梦表, 'id')
    进化触发表 = 单值索引(读表('evolution_triggers'), 'id')
    物种按链 = 索引(物种表, 'evolution_chain_id')
    # 形态是按「宝可梦条目」记的（每个形态都是一条 pokemon），所以要先回到物种再找
    形态按物种 = defaultdict(list)
    for _形 in 形态表:
        _种 = (宝可梦按id.get(_形['pokemon_id']) or {}).get('species_id')
        if _种:
            形态按物种[_种].append(_形)
    形态名表 = 索引(读表('pokemon_form_names'), 'pokemon_form_id')
    进化表 = 索引(读表('pokemon_evolution'), 'evolved_species_id')

    属性 = 单值索引(读表('types'), 'id')
    属性名表 = 索引(读表('type_names'), 'type_id')
    相克表 = 读表('type_efficacy')
    能力 = 单值索引(读表('stats'), 'id')
    能力名表 = 索引(读表('stat_names'), 'stat_id')

    # 招式用整数 id 做键：后面按 id 取招式时不用来回转字符串
    招式 = {int(k): v for k, v in 单值索引(读表('moves'), 'id').items()}
    招式名表 = 索引(读表('move_names'), 'move_id')
    招式说明表 = 索引(读表('move_flavor_text'), 'move_id')
    招式效果表 = 索引(读表('move_effect_prose'), 'move_effect_id')
    伤害分类 = 单值索引(读表('move_damage_classes'), 'id')
    学会方式 = 单值索引(读表('pokemon_move_methods'), 'id')

    特性 = 单值索引(读表('abilities'), 'id')
    特性名表 = 索引(读表('ability_names'), 'ability_id')
    特性说明表 = 索引(读表('ability_flavor_text'), 'ability_id')
    特性效果表 = 索引(读表('ability_prose'), 'ability_id')

    道具 = 单值索引(读表('items'), 'id')
    道具名表 = 索引(读表('item_names'), 'item_id')
    道具说明表 = 索引(读表('item_flavor_text'), 'item_id')
    道具分类 = 单值索引(读表('item_categories'), 'id')
    道具分类名表 = 索引(读表('item_category_prose'), 'item_category_id')

    性格 = 单值索引(读表('natures'), 'id')
    性格名表 = 索引(读表('nature_names'), 'nature_id')
    世代名表 = 索引(读表('generation_names'), 'generation_id')
    地点名表 = 索引(读表('location_names'), 'location_id')

    别名 = M._读人工('别名.json', {})

    # ---- 名字查取（进化条件拼句子时要用）----
    物种中文 = {}
    for 行 in 物种表:
        物种中文[行['id']] = 取名字(物种名表, 'pokemon_species_id', 行['id'], 'zh-hans')
    物种名_英 = {}
    for 行 in 物种表:
        物种名_英[行['id']] = 行['identifier']

    def 查名(类型, 值):
        if not 值:
            return ''
        值 = str(值)
        if 类型 == 'item':
            return 取名字(道具名表, 'item_id', 值, 'zh-hans') or (道具.get(值) or {}).get('identifier', '')
        if 类型 == 'move':
            return 取名字(招式名表, 'move_id', 值, 'zh-hans') or (招式.get(值) or {}).get('identifier', '')
        if 类型 == 'species':
            return 物种中文.get(值, '')
        if 类型 == 'location':
            return 取名字(地点名表, 'location_id', 值, 'zh-hans') or ''
        if 类型 == 'type':
            return M.属性名((属性.get(值) or {}).get('identifier', ''))
        return ''

    # ---- 属性相克矩阵 ----
    矩阵 = defaultdict(dict)
    for 行 in 相克表:
        攻 = (属性.get(行['damage_type_id']) or {}).get('identifier')
        守 = (属性.get(行['target_type_id']) or {}).get('identifier')
        if 攻 and 守:
            矩阵[攻][守] = int(行['damage_factor'])

    # ---- 每个物种的默认形态 ----
    物种到默认形态 = {}
    for 行 in 宝可梦表:
        if 行['is_default'] == '1':
            物种到默认形态[行['species_id']] = 行['id']

    宝可梦输出 = []
    搜索索引 = []

    print('组装 %d 只宝可梦……' % len(物种表))
    for 物种 in sorted(物种表, key=lambda r: int(r['id'])):
        物种id = 物种['id']
        形态id = 物种到默认形态.get(物种id)
        if not 形态id:
            continue           # 少数只有非默认形态的物种，跳过
        形态 = 宝可梦按id[形态id]

        zh = 取名字(物种名表, 'pokemon_species_id', 物种id, 'zh-hans')
        zhHant = 取名字(物种名表, 'pokemon_species_id', 物种id, 'zh-hant')
        en = 取名字(物种名表, 'pokemon_species_id', 物种id, 'en')
        ja = 取名字(物种名表, 'pokemon_species_id', 物种id, 'ja')
        genus = 取名字(物种名表, 'pokemon_species_id', 物种id, 'zh-hans', 'genus')
        # 名字兜底：PokeAPI 的英文名直接用 identifier
        slug = 物种['identifier']
        en = en or slug.replace('-', ' ').title()
        zh = zh or en

        # 属性
        类型们 = sorted(((int(r['slot']), (属性.get(r['type_id']) or {}).get('identifier'))
                       for r in 属性表.get(形态id, [])), key=lambda x: x[0])
        类型列表 = [t for _, t in 类型们 if t]

        # 种族值
        种族 = {}
        for 行 in 种族值表.get(形态id, []):
            名 = (能力.get(行['stat_id']) or {}).get('identifier')
            if 名:
                种族[名] = int(行['base_stat'])
        总和 = sum(种族.values())

        # 特性
        特性列表 = []
        for 行 in sorted(特性表.get(形态id, []), key=lambda r: int(r['slot'])):
            特 = 特性.get(行['ability_id'])
            if not 特:
                continue
            名 = 取名字(特性名表, 'ability_id', 行['ability_id'], 'zh-hans') or 特['identifier']
            特性列表.append({'slug': 特['identifier'], 'zh': 名,
                          'hidden': 行['is_hidden'] == '1'})

        # 进化链（同一条链上的全部成员）
        链id = 物种['evolution_chain_id']
        链成员 = 物种按链.get(链id, [])
        链输出 = []
        for 成员 in sorted(链成员, key=lambda r: int(r['id'])):
            # 同一只在不同版本组里可能有好几种进化方式，各自拼一句、去重后并列
            句子 = []
            for 行 in 进化表.get(成员['id'], []):
                行 = dict(行)
                触发 = 进化触发表.get(行['evolution_trigger_id']) or {}
                行['evolution_trigger'] = 触发.get('identifier', 'other')
                句子.append(M.进化条件文本(行, 查名))
            条件 = ' 或 '.join([x for x in dict.fromkeys(句子) if x])
            链输出.append({
                'id': int(成员['id']),
                'slug': 成员['identifier'],
                'zh': 物种中文.get(成员['id'], ''),
                'from': 成员['evolves_from_species_id'] or '',
                'cond': 条件,
            })

        # 招式（按学会方式分组）
        招式分组 = defaultdict(dict)
        for 行 in 招式表_宝可梦.get(形态id, []):
            招 = 招式.get(int(行['move_id']))
            if not 招:
                continue
            方式 = (学会方式.get(行['pokemon_move_method_id']) or {}).get('identifier', 'other')
            if 方式 not in M.学会方式:
                continue
            等级 = int(行['level'] or 0)
            老 = 招式分组[方式].get(行['move_id'])
            if 老 is None or (等级 and (not 老.get('level') or 等级 < 老['level'])):
                招式分组[方式][行['move_id']] = {'id': int(行['move_id']), 'level': 等级}

        def 招式条目(项):
            招 = 招式[项['id']]
            属性标识 = (属性.get(招['type_id']) or {}).get('identifier', '')
            return {
                'slug': 招['identifier'],
                'zh': 取名字(招式名表, 'move_id', 项['id'], 'zh-hans') or 招['identifier'],
                'type': 属性标识,
                'power': int(招['power']) if 招['power'] else 0,
                'pp': int(招['pp']) if 招['pp'] else 0,
                'accuracy': int(招['accuracy']) if 招['accuracy'] else 0,
                'class': (伤害分类.get(招['damage_class_id']) or {}).get('identifier', ''),
                'level': 项['level'],
            }

        招式输出 = {}
        for 方式 in M.学会方式顺序:
            项 = 招式分组.get(方式) or {}
            条目 = [招式条目(v) for v in 项.values()]
            条目.sort(key=lambda m: (m['level'] or 999, m['zh']))
            招式输出[方式] = 条目

        # 相克
        攻守 = {}
        for 攻击属性 in M.属性顺序:
            倍数 = 1.0
            for 守 in 类型列表:
                倍数 *= (矩阵.get(攻击属性, {}).get(守, 100) / 100.0)
            攻守[攻击属性] = 倍数
        弱点 = [k for k in M.属性顺序 if 攻守[k] > 1]
        抵抗 = [k for k in M.属性顺序 if 0 < 攻守[k] < 1]
        免疫 = [k for k in M.属性顺序 if 攻守[k] == 0]

        # 图鉴说明
        说明 = 取说明(物种说明表, 物种id)

        # 形态
        形态们 = [{
            'slug': 形['identifier'],
            'zh': 取名字(形态名表, 'pokemon_form_id', 形['id'], 'zh-hans', 'pokemon_name')
                  or 取名字(形态名表, 'pokemon_form_id', 形['id'], 'zh-hans', 'form_name') or '',
            'mega': 形['is_mega'] == '1',
            'battleOnly': 形['is_battle_only'] == '1',
        } for 形 in 形态按物种.get(物种id, [])
            if 形['form_identifier']
            and (取名字(形态名表, 'pokemon_form_id', 形['id'], 'zh-hans', 'pokemon_name')
                 or 取名字(形态名表, 'pokemon_form_id', 形['id'], 'zh-hans', 'form_name'))]

        条目 = {
            'id': int(物种id),
            'slug': slug,
            'zh': zh,
            'zhHant': zhHant or zh,
            'en': en,
            'ja': ja,
            'genus': genus,
            'gen': int(物种['generation_id']),
            'types': 类型列表,
            'stats': 种族,
            'bst': 总和,
            'height': int(形态['height']) / 10.0,
            'weight': int(形态['weight']) / 10.0,
            'abilities': 特性列表,
            'chain': 链输出,
            'moves': 招式输出,
            'matchups': {'weak': 弱点, 'resist': 抵抗, 'immune': 免疫, 'all': 攻守},
            'flavor': 说明,
            'forms': 形态们,
            'legendary': 物种['is_legendary'] == '1',
            'mythical': 物种['is_mythical'] == '1',
        }
        条目.update(拼音字段(zh))
        宝可梦输出.append(条目)

    # 别名回填
    别名反向 = defaultdict(list)
    for 别名文, 官方 in 别名.items():
        if 别名文.startswith('_'):
            continue
        别名反向[官方].append(别名文)
    for 条目 in 宝可梦输出:
        条目['alias'] = 别名反向.get(条目['zh'], [])
        d = {'id': 条目['id'], 'slug': 条目['slug'], 'zh': 条目['zh'], 'zhHant': 条目['zhHant'],
             'en': 条目['en'], 'ja': 条目['ja'], 'types': 条目['types'], 'bst': 条目['bst'],
             'gen': 条目['gen'], 'py': 条目['py'], 'pyInit': 条目['pyInit'], 'alias': 条目['alias']}
        搜索索引.append(d)

    # ---- 招式 ----
    print('组装招式……')
    招式中文 = {}
    招式输出 = []
    招式使用统计 = defaultdict(list)
    for 条目 in 宝可梦输出:
        for 方式, 列表 in 条目['moves'].items():
            for m in 列表:
                招式使用统计[m['slug']].append((条目['id'], 条目['zh'], 方式, m['level']))
    for mid, 行 in sorted(招式.items(), key=lambda kv: int(kv[0])):
        zh = 取名字(招式名表, 'move_id', mid, 'zh-hans')
        slug = 行['identifier']
        属性标识 = (属性.get(行['type_id']) or {}).get('identifier', '')
        效果id = 行['effect_id']
        # 招式的中文效果：PokeAPI 的官方中文效果说明（没有就留空，页面写「暂无」）
        def 取效果():
            if not 效果id:
                return ''
            for 行2 in 招式效果表.get(str(效果id), []):
                if 行2['local_language_id'] == str(语言['zh-hans']):
                    return 清洗(行2.get('short_effect') or 行2.get('effect') or '')
            return ''
        说明 = 取说明(招式说明表, mid) or 官方文本.查('招式', zh)
        效果 = 取效果()
        # 官方连中文说明都没写过的（GC《暗之旋风》的暗影招式、游戏里压根没写说明的招）：
        # 页面照旧生成、站内搜索照旧搜得到，只是不进招式表、不进 sitemap。
        薄 = not (说明 or 效果)
        d = {
            'id': int(mid),
            'slug': slug,
            'zh': zh or slug,
            'zhHant': 取名字(招式名表, 'move_id', mid, 'zh-hant'),
            'en': 取名字(招式名表, 'move_id', mid, 'en') or slug,
            'ja': 取名字(招式名表, 'move_id', mid, 'ja'),
            'type': 属性标识,
            'power': int(行['power']) if 行['power'] else 0,
            'pp': int(行['pp']) if 行['pp'] else 0,
            'accuracy': int(行['accuracy']) if 行['accuracy'] else 0,
            'priority': int(行['priority'] or 0),
            'class': (伤害分类.get(行['damage_class_id']) or {}).get('identifier', ''),
            'gen': int(行['generation_id']),
            'text': 说明,
            'effect': 效果,
            'thin': 薄,
            'learners': 招式使用统计.get(slug, []),
        }
        d.update(拼音字段(d['zh']))
        招式输出.append(d)
        招式中文[mid] = d['zh']

    # ---- 特性 ----
    print('组装特性……')
    特性输出 = []
    宝可梦含特性 = defaultdict(list)
    for 条目 in 宝可梦输出:
        for a in 条目['abilities']:
            宝可梦含特性[a['slug']].append((条目['id'], 条目['zh'], a['hidden']))
    for aid, 行 in sorted(特性.items(), key=lambda kv: int(kv[0])):
        slug = 行['identifier']
        zh = 取名字(特性名表, 'ability_id', aid, 'zh-hans')
        效果 = ''
        for 行2 in 特性效果表.get(aid, []):
            if 行2['local_language_id'] == str(语言['zh-hans']):
                效果 = 清洗(行2.get('short_effect') or '')
                break
        说明 = 取说明(特性说明表, aid) or 官方文本.查('特性', zh)
        薄 = not (效果 or 说明)          # 见上面招式那段：旁支作品的特性绝大多数属于这种
        d = {
            'id': int(aid),
            'slug': slug,
            'zh': zh or slug,
            'zhHant': 取名字(特性名表, 'ability_id', aid, 'zh-hant'),
            'en': 取名字(特性名表, 'ability_id', aid, 'en') or slug,
            'ja': 取名字(特性名表, 'ability_id', aid, 'ja'),
            'gen': int(行['generation_id']),
            'text': 说明,
            'effect': 效果,
            'thin': 薄,
            'owners': 宝可梦含特性.get(slug, []),
        }
        d.update(拼音字段(d['zh']))
        特性输出.append(d)

    # ---- 道具 ----
    print('组装道具……')
    道具输出 = []
    不生成页面的类别 = {'plot-advancement', 'unused'}
    for iid, 行 in sorted(道具.items(), key=lambda kv: int(kv[0])):
        slug = 行['identifier']
        zh = 取名字(道具名表, 'item_id', iid, 'zh-hans')
        说明 = 取说明(道具说明表, iid) or 官方文本.查('道具', zh)
        分类标识 = (道具分类.get(行['category_id']) or {}).get('identifier', '')
        分类中文 = ''
        for 行2 in 道具分类名表.get(行['category_id'], []):
            if 行2['local_language_id'] == str(语言['zh-hans']):
                分类中文 = 行2['name']
                break
        有条目图 = os.path.exists(os.path.join(RAW, 'items', slug + '.png'))
        生成页面 = bool(说明) and 分类标识 not in 不生成页面的类别
        d = {
            'id': int(iid),
            'slug': slug,
            'zh': zh or slug,
            'zhHant': 取名字(道具名表, 'item_id', iid, 'zh-hant'),
            'en': 取名字(道具名表, 'item_id', iid, 'en') or slug,
            'ja': 取名字(道具名表, 'item_id', iid, 'ja'),
            'category': 分类标识,
            'categoryZh': 分类中文,
            'cost': int(行['cost'] or 0),
            'text': 说明,
            'page': 生成页面,
            'icon': 有条目图,
        }
        d.update(拼音字段(d['zh']))
        道具输出.append(d)

    # ---- 性格 ----
    print('组装性格……')
    味 = {1: '辣', 2: '涩', 3: '甜', 4: '苦', 5: '酸'}
    # 性格只影响 5 项能力里的两项（HP 不受影响，所以中性性格的 stat_id 是 0）
    能力中文 = {行['stat_id']: 行['name'] for 行 in 读表('stat_names')
              if 行['local_language_id'] == str(语言['zh-hans'])}
    性格输出 = []
    for nid, 行 in sorted(性格.items(), key=lambda kv: int(kv[0])):
        d = {
            'id': int(nid),
            'slug': 行['identifier'],
            'zh': 取名字(性格名表, 'nature_id', nid, 'zh-hans') or 行['identifier'],
            'zhHant': 取名字(性格名表, 'nature_id', nid, 'zh-hant'),
            'en': 取名字(性格名表, 'nature_id', nid, 'en') or 行['identifier'],
            'ja': 取名字(性格名表, 'nature_id', nid, 'ja'),
            'plus': 能力中文.get(行['increased_stat_id'], ''),
            'minus': 能力中文.get(行['decreased_stat_id'], ''),
            'likes': 味.get(int(行['likes_flavor_id'] or 0), ''),
            'hates': 味.get(int(行['hates_flavor_id'] or 0), ''),
        }
        d.update(拼音字段(d['zh']))
        性格输出.append(d)

    # ---- 写文件 ----
    print('写文件……')
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    def 写JSON(路径, 内容, 紧凑=True):
        with io.open(路径, 'w', encoding='utf-8') as fh:
            if 紧凑:
                json.dump(内容, fh, ensure_ascii=False, separators=(',', ':'))
            else:
                json.dump(内容, fh, ensure_ascii=False)

    写JSON(os.path.join(DATA, 'index.json'), 搜索索引)
    写JSON(os.path.join(DATA, 'moves-index.json'), [
        {k: m[k] for k in ('id', 'slug', 'zh', 'zhHant', 'en', 'ja', 'type', 'power',
                           'pp', 'accuracy', 'class', 'gen', 'py', 'pyInit')} for m in 招式输出])
    写JSON(os.path.join(DATA, 'abilities-index.json'), [
        {k: a[k] for k in ('id', 'slug', 'zh', 'zhHant', 'en', 'ja', 'gen', 'effect',
                           'py', 'pyInit', 'owners')} for a in 特性输出])
    写JSON(os.path.join(DATA, 'items-index.json'), [
        {k: i[k] for k in ('id', 'slug', 'zh', 'zhHant', 'en', 'ja', 'category', 'categoryZh',
                           'cost', 'text', 'page', 'icon', 'py', 'pyInit')} for i in 道具输出])
    写JSON(os.path.join(DATA, 'natures.json'), 性格输出)

    # 属性相克矩阵单独存一份：聚合页（按属性看宝可梦）要用
    写JSON(os.path.join(OUT, 'type-matrix.json'), {攻: 值 for 攻, 值 in 矩阵.items()})

    写JSON(os.path.join(OUT, 'pokemon.json'), 宝可梦输出)
    写JSON(os.path.join(OUT, 'moves.json'), 招式输出)
    写JSON(os.path.join(OUT, 'abilities.json'), 特性输出)
    写JSON(os.path.join(OUT, 'items.json'), 道具输出)

    print('完成：')
    print('  宝可梦 %d · 招式 %d · 特性 %d · 道具 %d（其中生成静态页 %d）· 性格 %d'
          % (len(宝可梦输出), len(招式输出), len(特性输出), len(道具输出),
             sum(1 for i in 道具输出 if i['page']), len(性格输出)))
    for f in ('index.json', 'moves-index.json', 'abilities-index.json', 'items-index.json'):
        大小 = os.path.getsize(os.path.join(DATA, f))
        print('  data/%-22s %6.1f KB' % (f, 大小 / 1024.0))
    print('\n下一步：python3 build/图片.py')


if __name__ == '__main__':
    main()
