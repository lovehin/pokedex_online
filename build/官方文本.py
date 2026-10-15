#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PokeAPI 缺的官方中文说明 —— 读取 build/人工数据/官方文本补全.json。

那份 JSON 由 build/取官方文本.py 从官方游戏文本导出里生成，
里面只有 PokeAPI 没中文、但官方游戏里确实有中文的条目。

用法：import 官方文本;  官方文本.查('招式', 中文名)
"""
import io
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
路径 = os.path.join(BASE, 'build', '人工数据', '官方文本补全.json')

补全 = {}
if os.path.exists(路径):
    with io.open(路径, encoding='utf-8') as fh:
        补全 = json.load(fh)


def 查(类别, 中文名):
    """类别取'招式'/'特性'/'道具'；查不到就返回空字符串。"""
    return (补全.get(类别) or {}).get(中文名 or '', '')
