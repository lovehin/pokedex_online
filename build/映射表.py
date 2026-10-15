#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各种「对不上号」的映射表，以及进化条件的文字拼装。

为什么单独一份：这些是**人工判断**的东西（属性中文名、进化条件怎么写才像人话），
不适合散落在生成逻辑里。改这里不用动别的脚本。
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
人工数据 = os.path.join(BASE, 'build', '人工数据')


def _读人工(文件名, 默认):
    """人工维护的数据（如别名、属性中文名）放在 build/人工数据/，不会被生成脚本覆盖。"""
    路径 = os.path.join(人工数据, 文件名)
    if os.path.exists(路径):
        with open(路径, encoding='utf-8') as fh:
            return json.load(fh)
    return 默认


# ---------------------------------------------------------------- 属性
# 官方 18 属性：PokeAPI 的标识 → 中文名、色值（色值取自宝可梦官方的属性配色）
属性 = {
    'normal':   ('一般',   '#A8A77A'),
    'fighting': ('格斗',   '#C22E28'),
    'flying':   ('飞行',   '#A98FF3'),
    'poison':   ('毒',     '#A33EA1'),
    'ground':   ('地面',   '#E2BF65'),
    'rock':     ('岩石',   '#B6A136'),
    'bug':      ('虫',     '#A6B91A'),
    'ghost':    ('幽灵',   '#735797'),
    'steel':    ('钢',     '#B7B7CE'),
    'fire':     ('火',     '#EE8130'),
    'water':    ('水',     '#6390F0'),
    'grass':    ('草',     '#7AC74C'),
    'electric': ('电',     '#F7D02C'),
    'psychic':  ('超能力', '#F95587'),
    'ice':      ('冰',     '#96D9D6'),
    'dragon':   ('龙',     '#6F35FC'),
    'dark':     ('恶',     '#705746'),
    'fairy':    ('妖精',   '#D685AD'),
}
# 人工数据里可以覆盖上面的中文名（值就是中文名，例如 {"normal": "普通"}）
for _k, _v in _读人工('属性中文名.json', {}).items():
    if _k in 属性:
        属性[_k] = (_v, 属性[_k][1])
属性中文 = {k: v[0] for k, v in 属性.items()}
属性色 = {k: v[1] for k, v in 属性.items()}
# 属性在站内列表里的固定展示顺序（攻守表、筛选器都按这个顺序，别用字母序）
属性顺序 = ['normal', 'fire', 'water', 'grass', 'electric', 'ice', 'fighting', 'poison',
          'ground', 'flying', 'psychic', 'bug', 'rock', 'ghost', 'dragon', 'dark',
          'steel', 'fairy']


def 属性名(key):
    return 属性中文.get(key, key)


# ---------------------------------------------------------------- 种族值
# PokeAPI 的 stat 标识 → 中文名。顺序就是游戏里能力值的顺序。
能力 = [
    ('hp',              'HP'),
    ('attack',          '攻击'),
    ('defense',         '防御'),
    ('special-attack',  '特攻'),
    ('special-defense', '特防'),
    ('speed',           '速度'),
]
能力名 = dict(能力)

# ---------------------------------------------------------------- 招式分类
伤害分类 = {'physical': '物理', 'special': '特殊', 'status': '变化'}

# 招式的学会方式（PokeAPI 的 pokemon_move_methods）
学会方式 = {
    'level-up': '升级',
    'machine': '招式学习器',
    'egg': '遗传',
    'tutor': '教学',
    'form-change': '形态变化',
    'light-ball-egg': '电气球遗传',
    'colosseum-purification': '净化',
    'xd-shadow': '闇之招式',
    'xd-purification': '净化',
    'zygarde-cube': '基格尔德之核',
}
学会方式顺序 = ['level-up', 'machine', 'egg', 'tutor', 'form-change']

# ---------------------------------------------------------------- 世代
def 世代名(n):
    return '第 %d 世代' % int(n)


# ---------------------------------------------------------------- 进化条件
# PokeAPI 的 evolution_trigger → 中文说法
进化方式 = {
    'level-up': '升级',
    'trade': '交换',
    'use-item': '使用道具',
    'shed': '特殊',
    'spin': '特殊',
    'tower-of-darkness': '特殊',
    'tower-of-waters': '特殊',
    'three-critical-hits': '特殊',
    'take-damage': '特殊',
    'agile-style': '特殊',
    'strong-style': '特殊',
    'other': '特殊',
}

性别 = {1: '雄性', 2: '雌性', 3: '无性别'}
相对能力 = {-1: '攻击 小于 防御', 0: '攻击 等于 防御', 1: '攻击 大于 防御'}
时间 = {'day': '白天', 'night': '夜晚', 'dusk': '傍晚'}


def _有(值):
    """CSV 里的布尔是小整数，'0' 在 Python 里是**真值**，必须单独判掉，
    否则「要不要下雨」「要不要倒置主机」这类开关会全都被当成打开。"""
    值 = str(值 if 值 is not None else '').strip()
    return 值 not in ('', '0', 'None')


def 进化条件文本(行, 查名):
    """把 pokemon_evolution.csv 的一行拼成一句人话。

    查名 是一个函数：查名('item', 5) → '雷之石'，查名('move', 85) → '十万伏特'。
    拼不出来就老实说「满足特殊条件」——**宁可含糊，也不编**。
    """
    if not 行:
        return ''
    触发 = 行.get('evolution_trigger') or 'other'
    片段 = []

    if _有(行.get('gender_id')):
        片段.append(性别.get(int(行['gender_id']), ''))
    if _有(行.get('time_of_day')):
        片段.append(时间.get(行['time_of_day'], 行['time_of_day']))
    if _有(行.get('needs_overworld_rain')):
        片段.append('下雨时')
    if _有(行.get('turn_upside_down')):
        片段.append('把主机倒过来')

    前置 = ''
    if _有(行.get('known_move_id')):
        前置 = '学会「%s」后' % 查名('move', 行['known_move_id'])
    if _有(行.get('known_move_type_id')):
        片段.append('学会 %s 属性招式后' % 属性名(查名('type', 行['known_move_type_id'])))
    if _有(行.get('location_id')):
        片段.append('在「%s」' % 查名('location', 行['location_id']))
    if _有(行.get('party_species_id')):
        片段.append('队伍里带着「%s」' % 查名('species', 行['party_species_id']))
    if _有(行.get('party_type_id')):
        片段.append('队伍里有 %s 属性的宝可梦' % 属性名(查名('type', 行['party_type_id'])))
    if _有(行.get('relative_physical_stats')):
        片段.append(相对能力.get(int(行['relative_physical_stats']), ''))
    if _有(行.get('minimum_affection')):
        片段.append('友好度 %d 以上' % int(行['minimum_affection']))
    if _有(行.get('minimum_beauty')):
        片段.append('美丽度 %d 以上' % int(行['minimum_beauty']))
    if _有(行.get('minimum_happiness')):
        片段.append('亲密度 %d 以上' % int(行['minimum_happiness']))

    if 触发 == 'level-up':
        if _有(行.get('minimum_level')):
            片段.append('升到 %d 级' % int(行['minimum_level']))
        主干 = 前置 + ('，'.join([p for p in 片段 if p]) or '升级')
        return 主干
    if 触发 == 'use-item':
        道具 = 查名('item', 行.get('trigger_item_id') or 行.get('item_id')) if _有(行.get('trigger_item_id') or 行.get('item_id')) else ''
        return '使用「%s」' % 道具 if 道具 else '使用特定道具'
    if 触发 == 'trade':
        持 = 查名('item', 行.get('held_item_id')) if _有(行.get('held_item_id')) else ''
        if _有(行.get('trade_species_id')):
            return '与「%s」交换' % 查名('species', 行['trade_species_id'])
        return '携带「%s」交换' % 持 if 持 else '通信交换'
    if 触发 == 'shed':
        return '队伍中有空位、且精灵球里有第 5 世代的宝可梦时升级'
    if 触发 == 'spin':
        return '在特定地点原地旋转'
    if 触发 == 'tower-of-darkness':
        return '击败「恶之塔」的馆主'
    if 触发 == 'tower-of-waters':
        return '击败「水之塔」的馆主'
    if 触发 == 'three-critical-hits':
        return '一场战斗中命中 3 次要害'
    if 触发 == 'take-damage':
        return '受伤后走到特定地点'
    if 触发 == 'agile-style':
        return '使用「迅疾」招式'
    if 触发 == 'strong-style':
        return '使用「刚猛」招式'

    尾巴 = '，'.join([p for p in 片段 if p])
    return '满足特殊条件' + ('（%s）' % 尾巴 if 尾巴 else '')
