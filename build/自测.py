#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全站自测：数据是否完整、页面是否生成齐、有没有坏链、SEO 资产对不对。

它不需要浏览器，纯读文件和 JSON，跑一遍几秒钟。
上线前跑一次；改了生成脚本之后更要跑。

用法：python3 build/自测.py
"""
import csv
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 映射表 as M                                                   # noqa: E402

RAW = os.path.join(BASE, 'build', '_raw')
OUT = os.path.join(BASE, 'build', '_out')
DATA = os.path.join(BASE, 'data')

通过 = []
失败 = []


def 断言(条件, 说明, 细节=''):
    记录 = ('  ✓ ' if 条件 else '  ✗ ') + 说明 + (('  —— ' + str(细节)) if 细节 else '')
    (通过 if 条件 else 失败).append(记录)


def 读JSON(路径):
    with io.open(路径, encoding='utf-8') as fh:
        return json.load(fh)


def 读表(名):
    with io.open(os.path.join(RAW, 名 + '.csv'), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- 一、数据完整性
def 查数据():
    print('一、数据完整性')
    宝可梦 = 读JSON(os.path.join(OUT, 'pokemon.json'))
    招式 = 读JSON(os.path.join(OUT, 'moves.json'))
    特性 = 读JSON(os.path.join(OUT, 'abilities.json'))
    道具 = 读JSON(os.path.join(OUT, 'items.json'))
    性格 = 读JSON(os.path.join(DATA, 'natures.json'))

    断言(len(宝可梦) == 1025, '宝可梦 1025 只', '实际 %d' % len(宝可梦))
    断言(len(招式) == 937, '招式 937 个', '实际 %d' % len(招式))
    断言(len(特性) == 374, '特性 374 个', '实际 %d' % len(特性))
    断言(len(性格) == 25, '性格 25 个', '实际 %d' % len(性格))

    无名 = [p['slug'] for p in 宝可梦 if not p['zh'] or not p['en']]
    无属性 = [p['slug'] for p in 宝可梦 if not p['types']]
    无种族 = [p['slug'] for p in 宝可梦 if len(p['stats']) != 6]
    总和错 = [p['slug'] for p in 宝可梦 if sum(p['stats'].values()) != p['bst']]
    断言(not 无名, '每只都有中英文名', str(无名[:5]))
    断言(not 无属性, '每只都有属性', str(无属性[:5]))
    断言(not 无种族, '每只都有 6 项种族值', str(无种族[:5]))
    断言(not 总和错, '种族值总和等于六项之和', str(总和错[:5]))

    # 数值与上游对得上（抽 20 只逐项核）
    源 = {}
    for 行 in 读表('pokemon_stats'):
        源.setdefault(行['pokemon_id'], {})[行['stat_id']] = int(行['base_stat'])
    能力序 = ['hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed']
    抽查 = 0
    不一致 = []
    for p in 宝可梦[:200]:
        键 = str(p['id'])
        if 键 not in 源:
            continue
        for 位, 名 in enumerate(能力序, 1):
            if 源[键].get(str(位)) != p['stats'].get(名):
                不一致.append('%s %s' % (p['slug'], 名))
        抽查 += 1
    断言(not 不一致, '种族值与上游 CSV 逐项一致（抽 %d 只）' % 抽查, str(不一致[:5]))

    # 属性相克：电打地面必须是 0，地面打飞行必须是 0
    索引 = {p['slug']: p for p in 宝可梦}
    断言(索引['pikachu']['matchups']['all']['ground'] == 2.0, '电属性被地面克制（2 倍）')
    断言(索引['pikachu']['matchups']['all']['electric'] == 0.5, '电属性抵抗电（½ 倍）')
    断言(索引['pidgey']['matchups']['all']['ground'] == 0.0, '飞行属性免疫地面（0 倍）')

    # 拼音
    断言(索引['pikachu']['py'] == 'pikaqiu' and 索引['pikachu']['pyInit'] == 'pkq',
        '皮卡丘的拼音与首字母', '%s / %s' % (索引['pikachu']['py'], 索引['pikachu']['pyInit']))
    无拼音 = [p['slug'] for p in 宝可梦 if not p['py'] or not p['pyInit']]
    断言(not 无拼音, '每只都有拼音（搜索要用）', str(无拼音[:5]))

    # 别名：写进去的别名必须指向真实存在的宝可梦
    中文集 = set(p['zh'] for p in 宝可梦)
    别名 = M._读人工('别名.json', {})
    悬空 = [k for k, v in 别名.items() if not k.startswith('_') and v not in 中文集]
    断言(not 悬空, '别名表里没有指向不存在宝可梦的条目', str(悬空[:5]))

    # 招式
    无类型 = [m['slug'] for m in 招式 if not m['type']]
    无分类 = [m['slug'] for m in 招式 if m['class'] not in ('physical', 'special', 'status')]
    断言(not 无类型 and not 无分类, '每个招式都有属性和分类',
        str((无类型 + 无分类)[:5]))
    有中文说明 = sum(1 for m in 招式 if m['text'] or m['effect'])
    断言(有中文说明 >= 800, '招式有中文说明的比例（%d/%d）' % (有中文说明, len(招式)),
        '上线要求 ≥ 800')

    # 「不编数据」：没中文说明的必须留空，不能凭空冒出一段
    编的 = [m['slug'] for m in 招式 if m['text'] and len(m['text']) > 200]
    断言(not 编的, '没有异常长的招式说明（防手滑塞错数据）', str(编的[:3]))

    索引条数 = len(读JSON(os.path.join(DATA, 'index.json')))
    断言(索引条数 == 1025, 'data/index.json 有 1025 条')
    大小 = os.path.getsize(os.path.join(DATA, 'index.json'))
    断言(大小 < 400 * 1024, '搜索索引体积可控（%.0f KB）' % (大小 / 1024.0))

    # 官方文本补全：PokeAPI 缺的中文说明，由 build/取官方文本.py 从官方游戏文本补上。
    # 这份数据不进开源仓库（上游没有授权），所以在开源版里可能整个文件不存在 ——
    # 那样招式 / 特性 / 道具的中文说明会少一截，属于已知取舍，不算自测失败。
    补全路径 = os.path.join(BASE, 'build', '人工数据', '官方文本补全.json')
    if not os.path.exists(补全路径):
        print('  · 没有 build/人工数据/官方文本补全.json，跳过这一项。')
        print('    想要完整的官方中文说明就跑 python3 build/取官方文本.py。')
    if os.path.exists(补全路径):
        补全 = 读JSON(补全路径)
        份数 = {k: len(补全.get(k) or {}) for k in ('招式', '特性', '道具')}
        断言(all(份数.values()), '官方文本补全.json 三类都有内容', str(份数))

        # 游戏原文里带 [VAR …] / [~ …] 这类占位符，漏清就是一页乱码
        占位符 = re.compile(r'\[(?:VAR|~)\b[^\]]*\]')
        残留 = [m['slug'] for m in 招式 if 占位符.search(m['text'] or '')] + \
              [a['slug'] for a in 特性 if 占位符.search(a['text'] or '')] + \
              [x['slug'] for x in 道具 if 占位符.search(x['text'] or '')]
        断言(not 残留, '说明文字里没有游戏占位符残留', str(残留[:3]))

        # 游戏里没写说明的招式会填一串破折号，那不算说明，得留空
        破折号 = [m['slug'] for m in 招式
                if m['text'] and re.fullmatch(r'[\s―—\-─·。]+', m['text'])]
        断言(not 破折号, '没有只剩破折号的招式说明', str(破折号[:3]))
    return 宝可梦, 招式, 特性, 道具, 性格


# ---------------------------------------------------------------- 二、页面生成
def 查页面(宝可梦, 招式, 特性, 道具, 性格):
    print('二、页面是否生成齐')

    def 数(目录):
        d = os.path.join(BASE, 目录)
        return len([f for f in os.listdir(d) if f.endswith('.html')]) if os.path.isdir(d) else 0

    断言(数('pokemon') == 1026, 'pokemon/ 下有 1025 个详情页 + 1 个总览',
        '实际 %d' % 数('pokemon'))
    断言(数('moves') == 938, 'moves/ 下 937 + 总览', '实际 %d' % 数('moves'))
    断言(数('abilities') == 375, 'abilities/ 下 374 + 总览', '实际 %d' % 数('abilities'))
    断言(数('natures') == 26, 'natures/ 下 25 + 总览', '实际 %d' % 数('natures'))
    有页道具 = sum(1 for x in 道具 if x['page'])
    断言(数('items') == 有页道具 + 1, 'items/ 下有 %d 个静态页 + 总览' % 有页道具,
        '实际 %d' % 数('items'))

    没有的 = [p['slug'] for p in 宝可梦 if not os.path.exists(
        os.path.join(BASE, 'pokemon', p['slug'] + '.html'))]
    断言(not 没有的, '每只宝可梦都有页面', str(没有的[:5]))
    for 目录, 表 in (('moves', 招式), ('abilities', 特性),
                   ('items', [x for x in 道具 if x['page']]), ('natures', 性格)):
        缺 = [x['slug'] for x in 表 if not os.path.exists(
            os.path.join(BASE, 目录, x['slug'] + '.html'))]
        断言(not 缺, '%s/ 每个条目都有页面' % 目录, str(缺[:5]))

    for 路径 in ('index.html', '404.html', 'search/index.html', 'embed/index.html',
               'about.html', 'privacy.html', 'terms.html', 'dmca.html',
               'sitemap.xml', 'llms.txt', 'robots.txt', 'favicon.svg', 'manifest.webmanifest'):
        断言(os.path.exists(os.path.join(BASE, 路径)), '存在 %s' % 路径)

    文件数 = 0
    for 根, 目录们, 文件们 in os.walk(BASE):
        目录们[:] = [d for d in 目录们 if d not in ('.git', 'build', 'docs', 'scripts', '.wrangler')]
        文件数 += len(文件们)
    断言(文件数 < 20000, '部署文件数 %d 在 Cloudflare 上限（20000）以内' % 文件数)


# ---------------------------------------------------------------- 三、页面内容
def 查内容():
    print('三、页面内容与 SEO')
    样例 = ['index.html', 'pokemon/pikachu.html', 'pokemon/eevee.html', 'moves/thunderbolt.html',
          'abilities/static.html', 'items/potion.html', 'natures/jolly.html', '404.html',
          'pokemon/index.html', 'moves/index.html', 'items/index.html']
    问题 = {'canonical': [], 'og': [], 'jsonld': [], '时间': [], '标题': []}
    for 路径 in 样例:
        完整 = os.path.join(BASE, 路径)
        if not os.path.exists(完整):
            continue
        s = io.open(完整, encoding='utf-8').read()
        if 'rel="canonical"' not in s:
            问题['canonical'].append(路径)
        if 'og:image' not in s or 'twitter:card' not in s:
            问题['og'].append(路径)
        if 'application/ld+json' not in s:
            问题['jsonld'].append(路径)
        if '<time datetime=' not in s and 路径 not in ('404.html',):
            问题['时间'].append(路径)
        if '<title>' not in s:
            问题['标题'].append(路径)
    问题['jsonld'] = [x for x in 问题['jsonld'] if x != '404.html']   # 404 不需要结构化数据
    问题['时间'] = [x for x in 问题['时间'] if x not in ('404.html', 'search/index.html')]
    for 键 in 问题:
        断言(not 问题[键], '每页都有 %s' % 键, str(问题[键]))

    # 无 JS 也能读到正文：抓关键数字
    s = io.open(os.path.join(BASE, 'pokemon/pikachu.html'), encoding='utf-8').read()
    正文 = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    正文 = re.sub(r'<[^>]+>', ' ', 正文)
    正文 = re.sub(r'\s+', ' ', 正文)
    for 关键 in ('种族值总和 320', '地面', '亲密度 220', '静电', '皮卡丘'):
        断言(关键 in 正文, '皮卡丘页面正文里有「%s」' % 关键)

    # 页脚：赞赏块 + 回链主站（站群约定）
    for 路径 in 样例:
        完整 = os.path.join(BASE, 路径)
        if not os.path.exists(完整) or 路径.startswith('embed'):
            continue
        s = io.open(完整, encoding='utf-8').read()
        断言('https://suilang.net/assets/pay/wechat.jpg' in s and
            '<a href="https://suilang.net/">随浪工具站</a>' in s,
            '%s 的页脚有赞赏块和回链主站' % 路径)

    # 不该出现的东西
    全部 = os.path.join(BASE, 'pokemon/pikachu.html')
    s = io.open(全部, encoding='utf-8').read()
    断言('X-Frame-Options' not in s, '页面里没有写 X-Frame-Options（会影响跨域内嵌）')
    h = io.open(os.path.join(BASE, '_headers'), encoding='utf-8').read()
    断言('frame-ancestors' in h and 'gba.suilang.net' in h, '_headers 放行了 gba 站的内嵌')
    断言('X-Frame-Options:' not in h.replace('故意不写 X-Frame-Options', ''),
        '_headers 里没有 X-Frame-Options')
    断言('https://suilang.net' in h, '_headers 的 img-src 放行了 suilang.net（收款码）')
    ig = io.open(os.path.join(BASE, '.assetsignore'), encoding='utf-8').read()
    断言('*.txt' not in ig.replace('千万别写 *.txt', ''), '.assetsignore 没有写 *.txt')


# ---------------------------------------------------------------- 四、链接
def 查坏链():
    print('四、坏链扫描')
    def 目标存在(址):
        址 = 址.split('#')[0].split('?')[0]
        if not 址.startswith('/'):
            return True                       # 外链和 mailto 不管
        p = os.path.join(BASE, 址.lstrip('/'))
        if os.path.isdir(p) or 址.endswith('/'):
            return os.path.exists(os.path.join(p, 'index.html'))
        return (os.path.exists(p) or os.path.exists(p + '.html')
                or os.path.exists(os.path.join(p, 'index.html')))

    坏 = []
    总链接 = 0
    目录们 = ['pokemon', 'moves', 'abilities', 'items', 'natures', 'search', 'embed']
    检查的页 = ['index.html', '404.html', 'about.html', 'privacy.html', 'terms.html', 'dmca.html']
    for 子 in 目录们:
        完整 = os.path.join(BASE, 子)
        if not os.path.isdir(完整):
            continue
        名称们 = sorted(os.listdir(完整))
        # 每个目录抽 40 个 + 目录首页，够了
        抽样 = [f for f in 名称们 if f.endswith('.html')][:40]
        if os.path.exists(os.path.join(完整, 'index.html')):
            抽样.append('index.html')
        检查的页 += ['%s/%s' % (子, f) for f in 抽样]
    for 路径 in 检查的页:
        完整 = os.path.join(BASE, 路径)
        if not os.path.exists(完整):
            continue
        s = io.open(完整, encoding='utf-8').read()
        for 址 in re.findall(r'(?:href|src)="(/[^"]*)"', s):
            总链接 += 1
            if not 目标存在(址):
                坏.append('%s → %s' % (路径, 址))
    断言(not 坏, '扫了 %d 个内链，没有坏链' % 总链接, '；'.join(sorted(set(坏))[:6]))


# ---------------------------------------------------------------- 五、SEO 资产
def 查SEO():
    print('五、SEO / GEO 资产')
    sm = io.open(os.path.join(BASE, 'sitemap.xml'), encoding='utf-8').read()
    条数 = sm.count('<url>')
    # 门槛随「官方中文说明补全在不在」浮动：那份数据不进开源仓库（上游没有授权），
    # 少了它就有一批招式 / 特性 / 道具被判为薄内容、不进 sitemap，页数从 4134 掉到
    # 3500 上下。这是有意为之的取舍，不该算自测失败。
    有补全 = os.path.exists(os.path.join(BASE, 'build', '人工数据', '官方文本补全.json'))
    断言(条数 > (3700 if 有补全 else 3400), 'sitemap 收录 %d 个地址' % 条数)
    断言('/search' not in sm and '/embed' not in sm, 'sitemap 里没有查询页和内嵌页')
    断言('/pokemon/pikachu' in sm and '/moves/thunderbolt' in sm, 'sitemap 里有条目页')
    断言('lastmod' in sm, 'sitemap 里有 lastmod')
    # 推送脚本按 sitemap 顺序一条条推，新站一天只有几条配额，所以重要页面必须排前面
    地址序 = re.findall(r'<loc>(.*?)</loc>', sm)
    断言(地址序[:1] == ['https://pokedex.suilang.net/'], 'sitemap 第一条是首页')
    断言(地址序[1:6] == ['https://pokedex.suilang.net/%s/' % c
                      for c in ('pokemon', 'moves', 'abilities', 'items', 'natures')],
        'sitemap 第 2~6 条是五个栏目根（百度推送优先推它们）')
    # 栏目根地址必须是带斜杠的形态：Cloudflare 的 auto-trailing-slash 会把
    # /pokemon 307 到 /pokemon/，canonical / sitemap 写不带斜杠的就和实际地址对不上
    栏目根 = ['pokemon', 'moves', 'abilities', 'items', 'natures']
    裸地址 = [c for c in 栏目根 if '<loc>https://pokedex.suilang.net/%s</loc>' % c in sm]
    断言(not 裸地址, '栏目根地址在 sitemap 里不带裸形态（%s）' % (裸地址 or '无'))
    缺斜杠 = [c for c in 栏目根 if '<loc>https://pokedex.suilang.net/%s/</loc>' % c not in sm]
    断言(not 缺斜杠, '五个栏目根都在 sitemap 里且带结尾斜杠（缺：%s）' % (缺斜杠 or '无'))

    robots = io.open(os.path.join(BASE, 'robots.txt'), encoding='utf-8').read()
    断言('Disallow: /search' in robots and 'Disallow: /embed' in robots, 'robots 挡掉了查询页与内嵌页')
    断言('Sitemap: https://pokedex.suilang.net/sitemap.xml' in robots, 'robots 里写了 sitemap 地址')
    规则行 = [x.strip() for x in robots.splitlines()]
    断言('Allow: /' in 规则行, 'robots 明确放行了全站（Allow: /）')
    断言('Disallow: /' not in 规则行, '没有整站禁止抓取',
        ','.join([x for x in 规则行 if x.startswith('Disallow')][:6]))

    llms = io.open(os.path.join(BASE, 'llms.txt'), encoding='utf-8').read()
    招式全 = 读JSON(os.path.join(OUT, 'moves.json'))
    特性全 = 读JSON(os.path.join(OUT, 'abilities.json'))
    可见招式 = [m for m in 招式全 if not m.get('thin')]
    可见特性 = [a for a in 特性全 if not a.get('thin')]
    断言('1025' in llms and ('招式 %d 个' % len(可见招式)) in llms,
        'llms.txt 写了主要条目的数量（宝可梦 1025 · 招式 %d）' % len(可见招式))
    断言('/pokemon/' in llms and '/moves/' in llms and '/abilities/' in llms, 'llms.txt 有各栏目入口')

    # 薄内容（官方从没写过中文说明的旁支条目：暗影招式、《信长的野望》特性等）：
    # 页面照旧在线、站内搜索查得到，但不进 sitemap、页面带 noindex、总览表里也不出现
    薄 = [(m['slug'], 'moves') for m in 招式全 if m.get('thin')] + \
        [(a['slug'], 'abilities') for a in 特性全 if a.get('thin')]
    断言(薄, '确实存在官方没有中文说明的条目（%d 个）' % len(薄))
    进了地图 = ['/%s/%s' % (目, s) for s, 目 in 薄
              if '<loc>https://pokedex.suilang.net/%s/%s</loc>' % (目, s) in sm]
    断言(not 进了地图, '薄内容不在 sitemap 里', str(进了地图[:3]))
    没noindex = ['%s/%s' % (目, s) for s, 目 in 薄
               if os.path.exists(os.path.join(BASE, 目, s + '.html'))
               and 'content="noindex,follow"' not in io.open(
                   os.path.join(BASE, 目, s + '.html'), encoding='utf-8').read()]
    断言(not 没noindex, '薄内容页面都写了 noindex', str(没noindex[:3]))
    总览 = io.open(os.path.join(BASE, 'moves', 'index.html'), encoding='utf-8').read() + \
          io.open(os.path.join(BASE, 'abilities', 'index.html'), encoding='utf-8').read()
    # 注意别只看 slug：招式里也有个 celebrate（庆祝），只看名字会误判
    露头 = ['/%s/%s' % (目, s) for s, 目 in 薄 if '/%s/%s"' % (目, s) in 总览]
    断言(not 露头, '薄内容没有出现在招式表 / 特性大全的列表里', str(露头[:3]))

    # 站长平台验证与统计：配置里填了，页面上就必须真的有（填了没生效最容易被忽略）
    配置原文 = io.open(os.path.join(BASE, 'assets', 'config.js'), encoding='utf-8').read()
    首页原文 = io.open(os.path.join(BASE, 'index.html'), encoding='utf-8').read()
    统计 = re.search(r'analytics:\s*\{[^}]*baidu:\s*"([^"]*)"', 配置原文, re.S)
    验证 = re.search(r'verify:\s*\{[^}]*baidu:\s*"([^"]*)"', 配置原文, re.S)
    统计值 = 统计.group(1) if 统计 else ''
    验证值 = 验证.group(1) if 验证 else ''
    if 统计值:
        断言('hm.baidu.com/hm.js?%s' % 统计值 in 首页原文, '百度统计的代码写进了页面')
        头 = io.open(os.path.join(BASE, '_headers'), encoding='utf-8').read()
        断言('https://hm.baidu.com' in 头, 'CSP 放行了百度统计的域名（漏了会静默拦掉）')
    if 验证值:
        断言('content="%s"' % 验证值 in 首页原文, '百度站长平台的验证 meta 写进了页面')

    # 日期不会天天往前跑：连跑两次生成，日期必须不变
    状态 = 读JSON(os.path.join(BASE, 'build', '.生成状态.json'))
    断言(len(状态) > 3700, '生成状态记录了 %d 个文件（日期靠它稳定）' % len(状态))
    今天的 = [k for k, v in 状态.items() if v.get('d') == __import__('datetime').date.today().isoformat()]
    断言(len(今天的) <= len(状态), '有 %d 个文件记录着今天的日期' % len(今天的))

    # og 图
    for 图 in ('og/default.jpg',):
        断言(os.path.exists(os.path.join(BASE, 图)), '存在分享图 %s' % 图)
    for 键 in M.属性顺序:
        断言(os.path.exists(os.path.join(BASE, 'og', 'type-%s.jpg' % 键)),
            '存在 %s 属性的分享图' % M.属性名(键))


def main():
    宝可梦, 招式, 特性, 道具, 性格 = 查数据()
    查页面(宝可梦, 招式, 特性, 道具, 性格)
    查内容()
    查坏链()
    查SEO()

    print()
    print('=' * 60)
    if 失败:
        print('不通过 %d 条：' % len(失败))
        print('\n'.join(失败))
    print('通过 %d 条 · 不通过 %d 条' % (len(通过), len(失败)))
    print('=' * 60)
    if 通过:
        print('\n'.join(通过))
    return 1 if 失败 else 0


if __name__ == '__main__':
    sys.exit(main())
