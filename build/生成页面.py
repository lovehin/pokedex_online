#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第四步：把 data/ 和 build/_out/ 里的数据变成一整个静态站。

每个条目（宝可梦 / 招式 / 特性 / 道具 / 性格）都生成页面，首屏就有完整内容，
不依赖 JS —— 搜索引擎和 AI 爬虫读到的不是空壳，这是和竞品最大的区别。

⚠️ 日期规矩：页面里用 <!--DATE--> 占位，写文件前先比内容。
   只有正文真的变了，才把「最后更新」和 sitemap 的 lastmod 推到今天；
   没变就沿用上一次的日期。否则日期天天往前跑，等于告诉搜索引擎天天更新。

用法：python3 build/生成页面.py
"""
import datetime
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 映射表 as M                                                   # noqa: E402
import 模板 as T                                                     # noqa: E402

OUT = os.path.join(BASE, 'build', '_out')
DATA = os.path.join(BASE, 'data')
STATE_FILE = os.path.join(BASE, 'build', '.生成状态.json')
TODAY = datetime.date.today().isoformat()

# 招式表最多列这么多行，超了就截断并说明（免得个别宝可梦的页面撑到几百 KB）
招式表上限 = 200


# ---------------------------------------------------------------- 站点配置
def 读配置():
    """直接读 assets/config.js —— 全站唯一的一份配置，不重复维护第二份。"""
    脚本 = ("global.window={};"
           "eval(require('fs').readFileSync(process.argv[1],'utf8'));"
           "process.stdout.write(JSON.stringify(window.SITE));")
    try:
        输出 = subprocess.check_output(['node', '-e', 脚本, os.path.join(BASE, 'assets', 'config.js')],
                                    cwd=BASE, stderr=subprocess.DEVNULL)
        return json.loads(输出.decode('utf-8'))
    except Exception as 错:
        sys.stderr.write('读取 assets/config.js 失败（%s），改用默认配置。\n' % 错)
        原文 = io.open(os.path.join(BASE, 'assets', 'config.js'), encoding='utf-8').read()
        域 = re.search(r'domain:\s*"([^"]+)"', 原文)
        return {'domain': 域.group(1) if 域 else 'pokedex.suilang.net'}


SITE = T.站点(读配置())

# ---------------------------------------------------------------- 生成状态
_状态 = {}
try:
    _状态 = json.load(io.open(STATE_FILE, encoding='utf-8'))
except Exception:
    _状态 = {}
_脏 = {'值': False}
页面清单 = []          # [(地址, 日期)] —— 给 sitemap 用


def 写页(路径, 标题, 描述, 正文, og='og/default.jpg', jsonld=None, keywords=None,
       当前='', noindex=False, 收录=True):
    """路径形如 'pokemon/pikachu'（不带 .html）。正文里的 <!--DATE--> 会被换成日期。"""
    rel = 路径 + '.html'
    站内 = '/' + 路径
    if 站内.endswith('/index'):
        # 目录首页：Cloudflare 的 auto-trailing-slash 会把 /pokemon 307 到 /pokemon/，
        # 所以 canonical / og:url 一律用带斜杠的形态，省掉一次跳转（站点地图里也是这个形态）。
        站内 = 站内[:-len('index')] or '/'
    网页 = SITE.页面(标题, 描述, 站内, 正文, og, jsonld, keywords, 当前, noindex)
    # 先按「不含日期」的内容算指纹，决定这一页的日期
    指纹 = hashlib.sha1(网页.encode('utf-8')).hexdigest()
    老 = _状态.get(rel) or {}
    日期 = 老.get('d') if 老.get('h') == 指纹 and 老.get('d') else TODAY
    if 老.get('h') != 指纹:
        _脏['值'] = True
    正文最终 = 网页.replace('<!--DATE-->', 日期)
    落盘(rel, 正文最终)
    _状态[rel] = {'h': 指纹, 'd': 日期}
    if 收录 and not noindex:
        页面清单.append((站内, 日期))
    return 日期


def 落盘(rel, 内容):
    路径 = os.path.join(BASE, rel)
    目录 = os.path.dirname(路径)
    if 目录:
        os.makedirs(目录, exist_ok=True)
    数据 = 内容.encode('utf-8')
    if os.path.exists(路径):
        with open(路径, 'rb') as fh:
            if fh.read() == 数据:
                return
    with open(路径, 'wb') as fh:
        fh.write(数据)
    _脏['值'] = True


def 日期片段(日期):
    return '最后更新：<time datetime="%s">%s</time>' % (T.esc(日期), T.esc(日期))


# ---------------------------------------------------------------- 组装页面
def 属性相克表(条目):
    行 = []
    for 攻 in M.属性顺序:
        倍 = 条目['matchups']['all'][攻]
        类 = ('mult-%s' % (str(倍).replace('0.5', '05').replace('0.25', '025').replace('.0', ''))
             if 倍 != 1 else '')
        显示 = {4.0: '4×', 2.0: '2×', 1.0: '1×', 0.5: '½×', 0.25: '¼×', 0.0: '0×'}.get(倍, '%g×' % 倍)
        说明 = {4.0: '4 倍伤害', 2.0: '2 倍伤害', 1.0: '正常伤害', 0.5: '减半',
               0.25: '四分之一', 0.0: '完全无效'}.get(倍, '')
        行.append([T.属性徽章(攻), '<span class="mult %s">%s</span>' % (类, 显示),
                  '<span class="muted">%s</span>' % 说明])
    return T.表格(['攻击属性', '倍率', '效果'], 行)


def 种族值表(条目):
    行 = []
    for 键, 名 in M.能力:
        值 = 条目['stats'].get(键, 0)
        宽 = min(100, 值 / 180.0 * 100)
        行.append([名, '<div class="stat-row" style="margin:0"><span class="bar">'
                      '<i style="width:%.1f%%"></i></span></div>' % 宽, T.数字(值)])
    行.append(['<b>总和</b>', '', '<b>%s</b>' % T.数字(条目['bst'])])
    return ('<div class="tbl-scroll"><table class="tbl"><thead><tr><th style="width:64px">能力</th>'
            '<th></th><th class="num" style="width:52px">数值</th></tr></thead><tbody>%s</tbody></table></div>'
            % ''.join('<tr><td>%s</td><td>%s</td><td class="num">%s</td></tr>' % tuple(r) for r in 行))


def 招式表(条目, 招式们, 带等级=False):
    if not 招式们:
        return '<p class="muted">这一档没有可学的招式。</p>'
    截断 = len(招式们) > 招式表上限
    显示 = 招式们[:招式表上限]
    表头 = ['招式', '属性', '分类', '威力', '命中', 'PP'] + (['等级'] if 带等级 else [])
    行 = []
    for m in 显示:
        行.append([
            '<a href="/moves/%s">%s</a>' % (T.esc(m['slug']), T.esc(m['zh'])),
            T.属性徽章(m['type']),
            T.esc(M.伤害分类.get(m['class'], m['class'] or '—')),
            T.数字(m['power']) if m['power'] else '<span class="muted">—</span>',
            (str(m['accuracy']) + '%') if m['accuracy'] else '<span class="muted">—</span>',
            T.数字(m['pp']),
        ] + ([T.数字(m['level'])] if 带等级 else []))
    尾巴 = ('<p class="muted">另外还有 %d 个招式没列出来，避免页面太长。</p>' % (len(招式们) - 招式表上限)) if 截断 else ''
    return T.表格(表头, 行) + 尾巴


def 进化区块(条目):
    链 = 条目['chain']
    if len(链) <= 1 and not 链[0].get('cond'):
        return '<p class="muted">这只宝可梦不在任何进化链里（没有进化形态）。</p>'
    片段 = []
    for c in 链:
        名 = c['zh'] or c['slug']
        当前 = c['id'] == 条目['id']
        标签 = ('<b>%s</b>' % T.esc(名)) if 当前 else ('<a href="/pokemon/%s">%s</a>'
                                                % (T.esc(c['slug']), T.esc(名)))
        条件 = ('<span class="muted">（%s）</span>' % T.esc(c['cond'])) if c['cond'] else ''
        片段.append('<li>%s %s%s</li>' % ('▶' if 当前 else '·', 标签, 条件))
    return '<ul style="margin:0;padding-left:20px;line-height:2">%s</ul>' % ''.join(片段)


def 宝可梦FAQ(条目):
    名 = 条目['zh']
    最强 = max(M.能力, key=lambda kv: 条目['stats'].get(kv[0], 0))
    属名 = '／'.join(M.属性名(t) for t in 条目['types'])
    弱点 = [M.属性名(t) for t in 条目['matchups']['weak']]
    抵抗 = [M.属性名(t) for t in 条目['matchups']['resist']]
    免疫 = [M.属性名(t) for t in 条目['matchups']['immune']]
    问答 = []
    问答.append(('%s 的种族值总和是多少？' % 名,
               '%s 的种族值总和是 %d：HP %d、攻击 %d、防御 %d、特攻 %d、特防 %d、速度 %d。'
               '其中最高的是%s（%d）。' % (
                   名, 条目['bst'], 条目['stats'].get('hp', 0), 条目['stats'].get('attack', 0),
                   条目['stats'].get('defense', 0), 条目['stats'].get('special-attack', 0),
                   条目['stats'].get('special-defense', 0), 条目['stats'].get('speed', 0),
                   最强[1], 条目['stats'].get(最强[0], 0))))
    相克 = ('弱点（受到 2 倍以上伤害）有：%s；' % '、'.join(弱点)) if 弱点 else '它没有属性弱点；'
    相克 += ('抗性（受到伤害减半及以下）有：%s；' % '、'.join(抵抗)) if 抵抗 else ''
    相克 += ('完全免疫：%s。' % '、'.join(免疫)) if 免疫 else ''
    问答.append(('%s 是什么属性？怕什么？' % 名,
               '%s 是%s属性。%s' % (名, 属名, 相克)))
    进化 = [c for c in 条目['chain'] if c['id'] == 条目['id']]
    上级 = [c for c in 条目['chain'] if c.get('from') and str(c['from']) == str(条目['id'])]
    前 = 进化[0]['from'] if 进化 and 进化[0]['from'] else ''
    前名 = ''
    if 前:
        for c in 条目['chain']:
            if str(c['id']) == str(前):
                前名 = c['zh'] or c['slug']
    句子 = []
    if 前名:
        句子.append('自身由%s进化而来（%s）。' % (前名, 进化[0]['cond'] or '条件见上方进化图'))
    if 上级:
        句子.append('升级方向：' + '；'.join('%s（%s）' % (c['zh'] or c['slug'], c['cond'] or '特殊条件')
                                        for c in 上级))
    if not 句子:
        句子.append('这只宝可梦没有进化形态，也不会由别的宝可梦进化而来。')
    问答.append(('%s 怎么进化？' % 名, ''.join(句子)))
    隐藏 = [a for a in 条目['abilities'] if a['hidden']]
    普通 = [a for a in 条目['abilities'] if not a['hidden']]
    问4 = '%s 的特性是什么？' % 名
    答4 = ('普通特性：%s。' % '、'.join(a['zh'] for a in 普通)) if 普通 else ''
    答4 += ('隐藏特性：%s。' % '、'.join(a['zh'] for a in 隐藏)) if 隐藏 else '这只宝可梦没有隐藏特性。'
    问答.append((问4, 答4))
    问答.append(('%s 首次登场于哪个世代？' % 名,
               '%s 首次登场于%s，全国图鉴编号 #%03d。' % (名, M.世代名(条目['gen']), 条目['id'])))
    return 问答


def 改版联动区块():
    """宝可梦页尾的一句导流：玩改版遇到不认识的，去兄弟站边玩边查。
    配置里没写 gbaSite 就整块不出现。"""
    if not SITE.gba:
        return ''
    return ('<section class="block"><h2>在 GBA 改版里遇到它？</h2>'
            '<div class="tip-box">玩改版时碰到不认识的宝可梦，可以对着这一页看属性、相克、种族值和招式。'
            '想在浏览器里直接玩中文改版（究极绿宝石、漆黑的魅影等），'
            '去兄弟站 <a href="%s/">宝可梦改版 GBA 在线玩</a> —— 免安装、手机也能玩，'
            '玩的时候点播放页工具栏的「🔍 图鉴」就能随时回来查资料。</div></section>'
            % SITE.gba)


def 宝可梦页(条目, 上一只, 下一只):
    名 = 条目['zh']
    属名 = '／'.join(M.属性名(t) for t in 条目['types'])
    首段 = ('%s（%s／%s），%s属性，图鉴编号 #%03d。种族值总和 %d，首次登场于%s。'
         % (名, 条目['en'], 条目['ja'] or '—', 属名, 条目['id'], 条目['bst'], M.世代名(条目['gen'])))
    图片 = '/img/pokemon/%d.webp' % 条目['id']
    别名行 = ('<p class="factline"><span>又叫：%s</span></p>'
            % '、'.join(条目.get('alias') or [])) if 条目.get('alias') else ''
    正文 = [T.面包屑([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), (名, '')], SITE)]
    正文.append('<header class="entry-head">')
    正文.append('<img class="entry-art" src="%s" width="240" height="240" alt="%s" '
              'fetchpriority="high">' % (图片, T.esc(名)))
    正文.append('<div><h1>%s<span class="dex-no">#%03d</span></h1>'
              '<p class="type-row">%s</p><p class="lede">%s</p>%s'
              '<p class="factline"><span>分类 %s</span><span>身高 %s m</span><span>体重 %s kg</span>'
              '<span>图鉴编号 %03d</span></p>'
              '<p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              '</div></header>'
              % (T.esc(名), 条目['id'], T.属性徽章组(条目['types']), T.esc(首段), 别名行,
                 T.esc(条目['genus'] or '—'), 条目['height'], 条目['weight'], 条目['id']))
    if 条目['flavor']:
        正文.append('<div class="tip-box">图鉴说明：%s</div>' % T.esc(条目['flavor']))
    正文.append(SITE.广告位('topBanner'))
    正文.append('<section class="block"><h2>属性相克</h2>%s</section>' % 属性相克表(条目))
    正文.append('<section class="block"><h2>种族值</h2>%s</section>' % 种族值表(条目))
    if 条目['abilities']:
        行 = []
        for a in 条目['abilities']:
            行.append(['<a href="/abilities/%s">%s</a>%s' % (T.esc(a['slug']), T.esc(a['zh']),
                                                      '（隐藏特性）' if a['hidden'] else ''),
                      T.esc(特性说明短(a['slug']))])
        正文.append('<section class="block"><h2>特性</h2>%s</section>'
                  % T.表格(['特性', '效果'], 行))
    正文.append('<section class="block"><h2>进化</h2>%s</section>' % 进化区块(条目))
    正文.append(SITE.广告位('inArticle'))
    正文.append('<section class="block"><h2>能学的招式</h2>'
              '<p class="muted">下表汇总各世代能学会的招式，具体以你玩的那个版本为准。</p>')
    for 方式 in ('level-up', 'machine', 'egg', 'tutor'):
        列表 = 条目['moves'].get(方式) or []
        if not 列表:
            continue
        正文.append('<h3>%s（%d）</h3>%s' % (M.学会方式[方式], len(列表),
                                       招式表(条目, 列表, 带等级=(方式 == 'level-up'))))
    正文.append('</section>')
    if 条目['forms']:
        行 = [[f['zh'], '超级进化' if f['mega'] else ('仅对战中' if f['battleOnly'] else '其他形态')]
             for f in 条目['forms']]
        正文.append('<section class="block"><h2>其他形态</h2>%s</section>' % T.表格(['形态', '说明'], 行))
    联动 = 改版联动区块()
    if 联动:
        正文.append(联动)
    问答 = 宝可梦FAQ(条目)
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    正文.append('<nav class="pager">%s%s</nav>' % (
        上一只 and '<a href="/pokemon/%s">← #%03d %s</a>' % (T.esc(上一只['slug']), 上一只['id'], T.esc(上一只['zh'])) or '<span>已经是第一只</span>',
        下一只 and '<a href="/pokemon/%s">#%03d %s →</a>' % (T.esc(下一只['slug']), 下一只['id'], T.esc(下一只['zh'])) or '<span>已经是最后一只</span>'))

    标题 = '%s 的属性、种族值、进化与招式 - %s' % (名, SITE.站名)
    描述 = ('%s（%s）是%s属性的宝可梦，图鉴编号 #%03d，种族值总和 %d。这一页有属性相克表、'
         '种族值、特性、进化方式、能学的招式，以及常见问题解答。'
         % (名, 条目['en'], 属名, 条目['id'], 条目['bst']))
    路径 = 'pokemon/%s' % 条目['slug']
    结构化 = [T.FAQ结构化数据(问答, SITE.U('/' + 路径)),
            T.面包屑结构化数据([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), (名, '')], SITE),
            {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 标题,
             'url': SITE.U('/' + 路径), 'inLanguage': 'zh-CN',
             'dateModified': '<!--DATE-->', 'isPartOf': {'@type': 'WebSite', 'url': SITE.网址 + '/'}}]
    og = 'og/type-%s.jpg' % 条目['types'][0] if 条目['types'] else 'og/default.jpg'
    if not os.path.exists(os.path.join(BASE, og)):
        og = 'og/default.jpg'
    return 写页(路径, 标题, 描述, '\n'.join(正文), og, 结构化,
               '%s,属性,种族值,进化,招式,%s' % (名, 条目['en']), '/pokemon/')


def 特性说明短(slug):
    a = 特性索引.get(slug)
    if not a:
        return ''
    文本 = a.get('effect') or a.get('text') or ''
    return 文本[:60] + ('…' if len(文本) > 60 else '')


def 招式页(m):
    属名 = M.属性名(m['type'])
    分类 = M.伤害分类.get(m['class'], m['class'])
    首段 = '%s（%s／%s），%s属性%s招式。威力 %s、命中 %s、PP %s，首次登场于%s。' % (
        m['zh'], m['en'], m['ja'] or '—', 属名, 分类,
        m['power'] or '—', (str(m['accuracy']) + '%') if m['accuracy'] else '—',
        m['pp'], M.世代名(m['gen']))
    说明 = m['text'] or m['effect'] or ''
    正文 = [T.面包屑([('首页', '/'), ('招式表', '/moves/'), (m['zh'], '')], SITE)]
    正文.append('<h1>%s</h1><p class="type-row">%s <span class="muted">%s</span></p>'
              '<p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (T.esc(m['zh']), T.属性徽章(m['type']), T.esc(分类), T.esc(首段)))
    行 = [['属性', T.属性徽章(m['type'])],
         ['分类', T.esc(分类)],
         ['威力', T.数字(m['power']) if m['power'] else '—（变化招式）'],
         ['命中', (str(m['accuracy']) + '%') if m['accuracy'] else '—'],
         ['PP', T.数字(m['pp'])],
         ['优先度', ('+%d' % m['priority']) if m['priority'] > 0 else str(m['priority'])],
         ['首次登场', M.世代名(m['gen'])]]
    正文.append('<section class="block"><h2>招式数据</h2>%s</section>' % T.表格(['项目', '数值'], 行))
    正文.append('<section class="block"><h2>招式说明</h2><p>%s</p></section>'
              % (T.esc(说明) if 说明 else '<span class="muted">暂无官方中文说明。</span>'))
    正文.append(SITE.广告位('inArticle'))
    升级 = sorted([x for x in m['learners'] if x[2] == 'level-up'], key=lambda x: x[3])
    其他 = [x for x in m['learners'] if x[2] != 'level-up']
    if 升级:
        行 = [[宝可梦链接(x[0], x[1]), T.数字(x[3])] for x in 升级]
        正文.append('<section class="block"><h2>升级能学会这招的宝可梦（%d）</h2>%s</section>'
                  % (len(升级), T.表格(['宝可梦', '等级'], 行)))
    if 其他:
        汇总 = {}
        for x in 其他:
            汇总[x[2]] = 汇总.get(x[2], 0) + 1
        正文.append('<section class="block"><h2>其他学会方式</h2><p>%s</p></section>'
                  % '、'.join('%s %d 只' % (M.学会方式.get(k, k), v) for k, v in sorted(汇总.items())))
    问答 = [('%s 的威力是多少？' % m['zh'],
            '%s 是%s属性的%s招式，威力 %s、命中 %s、PP %s。'
            % (m['zh'], 属名, 分类, m['power'] or '—',
               (str(m['accuracy']) + '%') if m['accuracy'] else '必中', m['pp'])),
           ('%s 是什么效果？' % m['zh'], 说明 or '本站暂未收录这招的官方中文说明。'),
           ('哪些宝可梦能学会 %s？' % m['zh'],
            '本站收录到 %d 条学会记录，其中 %s能通过升级学会。'
            % (len(m['learners']), '%d 只宝可梦' % len(升级) if 升级 else '没有宝可梦'))]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '%s - 威力 %s 的%s%s招式 - %s' % (m['zh'], m['power'] or '—', 属名, 分类, SITE.站名)
    描述 = ('%s（%s）是%s属性的%s招式，威力 %s、命中 %s、PP %s。%s'
         % (m['zh'], m['en'], 属名, 分类, m['power'] or '—',
            (str(m['accuracy']) + '%') if m['accuracy'] else '必中', m['pp'],
            (说明[:70] + '…') if len(说明) > 70 else 说明))
    结构化 = [T.FAQ结构化数据(问答, SITE.U('/moves/' + m['slug'])),
            {'@context': 'https://schema.org', '@type': 'WebPage',
             'name': 标题, 'url': SITE.U('/moves/' + m['slug']),
             'dateModified': '<!--DATE-->', 'inLanguage': 'zh-CN'}]
    # 官方没写过中文说明的招式（暗影招式等）：页面照旧，但不进招式表、不进 sitemap，
    # 免得一堆只有英文名的空页影响整站的内容质量；站内搜索仍然找得到。
    return 写页('moves/%s' % m['slug'], 标题, 描述, '\n'.join(正文),
               'og/type-%s.jpg' % m['type'] if os.path.exists(os.path.join(BASE, 'og/type-%s.jpg' % m['type']))
               else 'og/default.jpg', 结构化, '%s,招式,威力,属性,%s' % (m['zh'], m['en']), '/moves/',
               noindex=bool(m.get('thin')))


def 特性页(a):
    说明 = a['effect'] or a['text'] or ''
    拥有 = a['owners']
    首段 = '%s（%s）是%s登场的宝可梦特性，共有 %d 只宝可梦拥有它。' % (
        a['zh'], a['en'], M.世代名(a['gen']), len(拥有))
    正文 = [T.面包屑([('首页', '/'), ('特性大全', '/abilities/'), (a['zh'], '')], SITE)]
    正文.append('<h1>%s</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (T.esc(a['zh']), T.esc(首段)))
    正文.append('<section class="block"><h2>特性效果</h2><p>%s</p></section>'
              % (T.esc(说明) if 说明 else '<span class="muted">暂无官方中文说明。</span>'))
    正文.append(SITE.广告位('inArticle'))
    普通 = [x for x in 拥有 if not x[2]]
    隐藏 = [x for x in 拥有 if x[2]]
    if 普通:
        行 = [['<a href="/pokemon/%s">%s</a>' % (T.esc(宝可梦slug映射.get(x[0], '')), T.esc(x[1]))] for x in 普通]
        正文.append('<section class="block"><h2>拥有这个特性的宝可梦（%d）</h2>%s</section>'
                  % (len(普通), T.表格(['宝可梦'], 行)))
    if 隐藏:
        行 = [['<a href="/pokemon/%s">%s</a>' % (T.esc(宝可梦slug映射.get(x[0], '')), T.esc(x[1]))] for x in 隐藏]
        正文.append('<section class="block"><h2>作为隐藏特性拥有（%d）</h2>%s</section>'
                  % (len(隐藏), T.表格(['宝可梦'], 行)))
    问答 = [('%s 是什么效果？' % a['zh'], 说明 or '本站暂未收录这个特性的官方中文说明。'),
           ('哪些宝可梦有 %s？' % a['zh'],
            '共 %d 只：%s。' % (len(拥有), '、'.join(x[1] for x in 拥有[:20])
                             + ('等' if len(拥有) > 20 else '')) if 拥有 else '暂无记录。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '%s - 宝可梦特性效果与拥有者 - %s' % (a['zh'], SITE.站名)
    描述 = '%s（%s）的完整效果，以及拥有这个特性的 %d 只宝可梦。%s' % (
        a['zh'], a['en'], len(拥有), (说明[:60] + '…') if len(说明) > 60 else 说明)
    结构化 = [T.FAQ结构化数据(问答, SITE.U('/abilities/' + a['slug'])),
            {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 标题,
             'url': SITE.U('/abilities/' + a['slug']), 'dateModified': '<!--DATE-->'}]
    return 写页('abilities/%s' % a['slug'], 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               结构化, '%s,特性,%s' % (a['zh'], a['en']), '/abilities/',
               noindex=bool(a.get('thin')))


def 道具页(it):
    说明 = it['text']
    首段 = '%s（%s）属于%s，售价 %s。' % (
        it['zh'], it['en'], it['categoryZh'] or it['category'] or '未分类',
        ('%d 元' % it['cost']) if it['cost'] else '非卖品')
    图标 = ('<img src="/img/items/%s.png" width="48" height="48" alt="%s" '
          'style="width:48px;height:48px;image-rendering:pixelated">' % (T.esc(it['slug']), T.esc(it['zh']))
          ) if it['icon'] else ''
    正文 = [T.面包屑([('首页', '/'), ('道具图鉴', '/items/'), (it['zh'], '')], SITE)]
    正文.append('<h1>%s</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              '<p>%s</p>' % (T.esc(it['zh']), T.esc(首段), 图标))
    正文.append('<section class="block"><h2>道具说明</h2><p>%s</p></section>' % T.esc(说明))
    正文.append('<section class="block"><h2>基本信息</h2>%s</section>'
              % T.表格(['项目', '数值'], [['分类', T.esc(it['categoryZh'] or '—')],
                                      ['售价', T.数字(it['cost'])],
                                      ['英文名', T.esc(it['en'])],
                                      ['日文名', T.esc(it['ja'] or '—')]]))
    问答 = [('%s 有什么用？' % it['zh'], 说明),
           ('%s 属于哪一类道具？' % it['zh'], '它属于%s。' % (it['categoryZh'] or '未分类道具'))]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '%s - 道具效果与说明 - %s' % (it['zh'], SITE.站名)
    描述 = '%s：%s' % (it['zh'], 说明[:90])
    结构化 = [T.FAQ结构化数据(问答, SITE.U('/items/' + it['slug'])),
            {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 标题,
             'url': SITE.U('/items/' + it['slug']), 'dateModified': '<!--DATE-->'}]
    return 写页('items/%s' % it['slug'], 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               结构化, '%s,道具,%s' % (it['zh'], it['en']), '/items/')


def 性格页(n):
    中性 = not n['plus'] or n['plus'] == n['minus']
    首段 = ('%s（%s）是宝可梦的性格之一。' % (n['zh'], n['en'])
          + ('它不改变任何能力值（中性性格）。' if 中性
             else '它会让%s提高 10%%，让%s降低 10%%。' % (n['plus'], n['minus'])))
    正文 = [T.面包屑([('首页', '/'), ('性格表', '/natures/'), (n['zh'], '')], SITE)]
    正文.append('<h1>%s</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (T.esc(n['zh']), T.esc(首段)))
    正文.append('<section class="block"><h2>能力变化</h2>%s</section>'
              % T.表格(['项目', '数值'],
                      [['提升（×1.1）', T.esc(n['plus'] or '无')],
                       ['降低（×0.9）', T.esc(n['minus'] or '无')],
                       ['喜欢的口味', T.esc(n['likes'] or '—')],
                       ['讨厌的口味', T.esc(n['hates'] or '—')]]))
    问答 = [('%s 性格加什么减什么？' % n['zh'], 首段),
           ('哪些宝可梦适合 %s 性格？' % n['zh'],
            ('这是中性性格，任何宝可梦都能用，不会影响能力值。' if 中性 else
             '任何需要%s、又不在意%s的宝可梦都适合，具体看你要练什么方向。' % (n['plus'], n['minus'])))]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    正文.append('<p style="margin-top:20px"><a href="/natures/">← 返回 25 个性格总表</a></p>')
    标题 = '%s 性格加什么减什么 - %s' % (n['zh'], SITE.站名)
    描述 = '%s（%s）：%s' % (n['zh'], n['en'], 首段)
    结构化 = [T.FAQ结构化数据(问答, SITE.U('/natures/' + n['slug'])),
            {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 标题,
             'url': SITE.U('/natures/' + n['slug']), 'dateModified': '<!--DATE-->'}]
    return 写页('natures/%s' % n['slug'], 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               结构化, '%s,性格,%s' % (n['zh'], n['en']), '/natures/')


# ---------------------------------------------------------------- 列表页
def 宝可梦链接(编号, 名字=None):
    """按图鉴编号给一只宝可梦的链接（名字给省一次查表）。"""
    slug = 宝可梦slug映射.get(编号)
    if not slug:
        return T.esc(名字 or str(编号))
    return '<a href="/pokemon/%s">%s</a>' % (T.esc(slug), T.esc(名字 or slug))


def 宝可梦总览():
    总数 = len(宝可梦们)
    首段 = ('这里是全部 %d 只宝可梦的图鉴，按全国图鉴编号排列。'
         '每只都能查到属性相克、种族值、特性、进化方式和能学的招式。'
         '也可以用上面的搜索框直接打名字、编号、拼音或日文名。' % 总数)
    正文 = [T.面包屑([('首页', '/'), ('宝可梦图鉴', '')], SITE)]
    正文.append('<h1>宝可梦图鉴</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>' % T.esc(首段))
    正文.append('<p class="crumbs">按属性看：%s</p>'
              % ' '.join('<a href="/pokemon/type/%s">%s</a>' % (k, T.esc(M.属性名(k)))
                        for k in M.属性顺序))
    正文.append(SITE.广告位('topBanner'))
    # ① 无 JS 也能用的紧凑索引：爬虫靠它发现全部条目页，人也能直接扫
    正文.append('<section class="block"><h2>全部 %d 只（按世代）</h2>' % 总数)
    for 代 in range(1, 10):
        组 = [p for p in 宝可梦们 if p['gen'] == 代]
        if not 组:
            continue
        正文.append('<h3 class="gen-title">%s（%d 只）<a href="/pokemon/gen/%d" '
                  'style="font-size:.82rem;margin-left:8px">单独看这一世代 →</a></h3>' % (M.世代名(代), len(组), 代))
        正文.append('<ul class="index-list">%s</ul>' % ''.join(
            '<li><span class="no">#%03d</span><a href="/pokemon/%s">%s</a></li>' % (p['id'], p['slug'], T.esc(p['zh']))
            for p in 组))
    正文.append('</section>')
    # ② 有 JS 时增强成可筛选的卡片网格
    正文.append('<section class="block"><h2>卡片浏览</h2>'
              '<div class="filters" id="dex-filters">'
              '<button class="chip" data-type="" aria-pressed="true">全部属性</button>%s'
              '<select id="dex-gen"><option value="">全部世代</option>%s</select>'
              '<select id="dex-sort"><option value="id">按图鉴编号</option>'
              '<option value="bst">按种族值总和</option><option value="name">按名字</option></select>'
              '</div><p class="count-line" id="dex-count"></p>'
              '<ul class="grid" id="dex-grid"></ul>'
              '<p class="toolbar"><button class="btn" id="dex-more" hidden>显示更多</button></p></section>'
              % (''.join('<button class="chip" data-type="%s">%s</button>' % (k, T.esc(M.属性名(k)))
                        for k in M.属性顺序),
                 ''.join('<option value="%d">%s</option>' % (i, M.世代名(i)) for i in range(1, 10))))
    问答 = [('这个图鉴收录了多少只宝可梦？', '收录了 %d 只，覆盖第 1 到第 9 世代。' % 总数),
           ('怎么快速找到一只宝可梦？',
            '用页面顶部的搜索框：中文名、英文名、日文名、图鉴编号、拼音全拼、拼音首字母都能搜到。'
            '比如打「pkq」「pikaqiu」「皮卡丘」「25」都会出皮卡丘。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '宝可梦图鉴 - 全部 %d 只宝可梦的属性、种族值与招式 - %s' % (总数, SITE.站名)
    描述 = ('宝可梦图鉴全集：%d 只宝可梦的属性相克、种族值、特性、进化方式和可学招式，'
         '支持中文、英文、日文、编号和拼音搜索。' % 总数)
    return 写页('pokemon/index', 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.FAQ结构化数据(问答, SITE.U('/pokemon/')),
                T.面包屑结构化数据([('首页', '/'), ('宝可梦图鉴', '')], SITE)],
               '宝可梦图鉴,宝可梦列表,种族值,属性相克,口袋妖怪图鉴', '/pokemon/')


def 属性聚合页(键, 组):
    名 = M.属性名(键)
    首段 = ('%s属性的宝可梦一共 %d 只。它们共享同一套属性相克关系：%s属性招式打出去时，'
         '对付不同属性会有不同倍率。' % (名, len(组), 名))
    正文 = [T.面包屑([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), ('%s属性' % 名, '')], SITE)]
    正文.append('<h1>%s属性宝可梦</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (T.esc(名), T.esc(首段)))
    行 = [[T.属性徽章(键), M.属性名(守), '<span class="mult %s">%s</span>' % (
        '', {4.0: '4×', 2.0: '2×', 1.0: '1×', 0.5: '½×', 0.25: '¼×', 0.0: '0×'}.get(
            相克矩阵.get(键, {}).get(守, 1.0), '1×'))] for 守 in M.属性顺序]
    正文.append('<section class="block"><h2>%s属性招式的攻守倍率</h2>%s</section>'
              % (T.esc(名), T.表格(['攻击属性', '被攻击属性', '倍率'], 行)))
    正文.append('<section class="block"><h2>%s属性的宝可梦（%d 只）</h2><ul class="index-list">%s</ul></section>'
              % (T.esc(名), len(组), ''.join(
                  '<li><span class="no">#%03d</span><a href="/pokemon/%s">%s</a></li>'
                  % (p['id'], p['slug'], T.esc(p['zh'])) for p in 组)))
    正文.append('<p class="toolbar">%s</p>' % ' '.join(
        '<a class="btn" href="/pokemon/type/%s">%s</a>' % (k, T.esc(M.属性名(k))) for k in M.属性顺序))
    标题 = '%s属性宝可梦大全（%d 只）- %s' % (名, len(组), SITE.站名)
    描述 = ('%s属性的宝可梦共 %d 只，含属性相克倍率表、种族值与招式。' % (名, len(组)))
    return 写页('pokemon/type/%s' % 键, 标题, 描述, '\n'.join(正文),
               'og/type-%s.jpg' % 键 if os.path.exists(os.path.join(BASE, 'og/type-%s.jpg' % 键)) else 'og/default.jpg',
               [T.面包屑结构化数据([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), ('%s属性' % 名, '')], SITE)],
               '%s属性,宝可梦,%s属性宝可梦' % (名, 名), '/pokemon/')


def 世代聚合页(代, 组):
    首段 = '第 %d 世代一共有 %d 只宝可梦，按全国图鉴编号排列如下。' % (代, len(组))
    正文 = [T.面包屑([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), (M.世代名(代), '')], SITE)]
    正文.append('<h1>%s的宝可梦</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (M.世代名(代), T.esc(首段)))
    正文.append('<ul class="index-list">%s</ul>' % ''.join(
        '<li><span class="no">#%03d</span><a href="/pokemon/%s">%s</a></li>'
        % (p['id'], p['slug'], T.esc(p['zh'])) for p in 组))
    正文.append('<p class="toolbar">%s</p>' % ' '.join(
        '<a class="btn" href="/pokemon/gen/%d">%s</a>' % (i, M.世代名(i)) for i in range(1, 10)))
    标题 = '%s的宝可梦大全（%d 只）- %s' % (M.世代名(代), len(组), SITE.站名)
    描述 = '%s共 %d 只宝可梦，附属性、种族值与招式入口。' % (M.世代名(代), len(组))
    return 写页('pokemon/gen/%d' % 代, 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.面包屑结构化数据([('首页', '/'), ('宝可梦图鉴', '/pokemon/'), (M.世代名(代), '')], SITE)],
               '%s,宝可梦列表' % M.世代名(代), '/pokemon/')


def 招式总览():
    首段 = ('这里收录了 %d 个宝可梦招式，按属性分组。每一招都能查到威力、命中、PP、'
         '物理/特殊/变化的分类，以及哪些宝可梦能学会。' % len(可见招式))
    正文 = [T.面包屑([('首页', '/'), ('招式表', '')], SITE)]
    正文.append('<h1>宝可梦招式表</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % T.esc(首段))
    招式薄注 = 薄内容说明('招式', len(招式们),
                     '比如 GC《暗之旋风》系列的暗影招式，以及游戏里就没写说明的招')
    if 招式薄注:
        正文.append('<p class="muted">%s</p>' % 招式薄注)
    正文.append(SITE.广告位('topBanner'))
    正文.append('<div class="filters" id="move-filters">'
              '<button class="chip" data-type="" aria-pressed="true">全部属性</button>%s'
              '<select id="move-class"><option value="">全部分类</option>'
              '<option value="physical">物理</option><option value="special">特殊</option>'
              '<option value="status">变化</option></select></div>'
              '<p class="count-line" id="move-count"></p><ul class="grid" id="move-grid"></ul>'
              % ''.join('<button class="chip" data-type="%s">%s</button>' % (k, T.esc(M.属性名(k)))
                        for k in M.属性顺序))
    正文.append('<section class="block"><h2>全部招式（按属性）</h2>')
    for k in M.属性顺序:
        组 = [m for m in 可见招式 if m['type'] == k]
        if not 组:
            continue
        正文.append('<h3 class="gen-title">%s属性（%d）</h3><ul class="index-list">%s</ul>'
                  % (T.esc(M.属性名(k)), len(组), ''.join(
                      '<li><a href="/moves/%s">%s</a> <span class="muted">%s</span></li>'
                      % (m['slug'], T.esc(m['zh']), (('威力 %d' % m['power']) if m['power'] else '变化'))
                      for m in sorted(组, key=lambda x: x['id']))))
    正文.append('</section>')
    问答 = [('一共收录了多少个招式？', '%d 个，覆盖第 1 到第 9 世代。' % len(可见招式)),
           ('招式表里的威力 0 是什么意思？', '威力为 0 表示这是变化招式（比如「剑舞」），本身不造成伤害。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '宝可梦招式表 - %d 个招式的威力、命中与学习者 - %s' % (len(可见招式), SITE.站名)
    描述 = '宝可梦招式大全：%d 个招式的属性、分类、威力、命中、PP，以及能学会它的宝可梦。' % len(可见招式)
    return 写页('moves/index', 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.FAQ结构化数据(问答, SITE.U('/moves/')),
                T.面包屑结构化数据([('首页', '/'), ('招式表', '')], SITE)],
               '宝可梦招式表,招式大全,招式威力', '/moves/')


def 特性总览():
    首段 = '这里收录了 %d 个宝可梦特性，含隐藏特性。点进去能看到完整效果和拥有它的宝可梦。' % len(可见特性)
    正文 = [T.面包屑([('首页', '/'), ('特性大全', '')], SITE)]
    正文.append('<h1>宝可梦特性大全</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % T.esc(首段))
    特性薄注 = 薄内容说明('特性', len(特性们), '比如《信长的野望》里的那些特性')
    if 特性薄注:
        正文.append('<p class="muted">%s</p>' % 特性薄注)
    正文.append('<ul class="index-list">%s</ul>' % ''.join(
        '<li><a href="/abilities/%s">%s</a> <span class="muted">%d</span></li>'
        % (a['slug'], T.esc(a['zh']), len(a['owners'])) for a in sorted(可见特性, key=lambda x: x['id'])))
    标题 = '宝可梦特性大全 - %d 个特性的效果与拥有者 - %s' % (len(可见特性), SITE.站名)
    描述 = '宝可梦特性一览：%d 个特性的中文效果说明，以及哪些宝可梦拥有它。' % len(可见特性)
    return 写页('abilities/index', 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.面包屑结构化数据([('首页', '/'), ('特性大全', '')], SITE)], '宝可梦特性,特性大全', '/abilities/')


def 道具总览():
    有页 = [it for it in 道具们 if it['page']]
    首段 = ('这里收录了 %d 条道具。其中 %d 条有官方中文说明的会生成单独的页面，'
         '其余的在下面点一下就能看说明。' % (len(道具们), len(有页)))
    正文 = [T.面包屑([('首页', '/'), ('道具图鉴', '')], SITE)]
    正文.append('<h1>宝可梦道具图鉴</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % T.esc(首段))
    正文.append(SITE.广告位('topBanner'))
    正文.append('<div class="filters"><input id="item-search" type="search" '
              'placeholder="在这一页里筛道具（支持拼音首字母）" style="min-width:260px">'
              '<button class="btn" id="item-clear" type="button">清空</button></div>'
              '<p class="count-line" id="item-count"></p>')

    # 按道具分类分组。有静态页的是链接，没有的是「点一下弹层」
    按类 = {}
    for it in 道具们:
        按类.setdefault(it['categoryZh'] or '其他', []).append(it)
    正文.append('<section class="block">')
    for 序号, 类名 in enumerate(sorted(按类)):
        组 = sorted(按类[类名], key=lambda x: x['id'])
        项 = []
        for it in 组:
            属性 = 'data-slug="%s" data-py="%s" data-pyinit="%s"' % (
                T.esc(it['slug']), T.esc(it['py']), T.esc(it['pyInit']))
            if it['page']:
                项.append('<li %s><a href="/items/%s">%s</a></li>' % (属性, T.esc(it['slug']), T.esc(it['zh'])))
            else:
                项.append('<li %s><a href="#" class="item-pop" data-slug="%s">%s</a></li>'
                          % (属性, T.esc(it['slug']), T.esc(it['zh'])))
        正文.append('<h3 class="gen-title">%s（%d）</h3>'
                  '<ul class="index-list" data-item-group="%d">%s</ul>'
                  % (T.esc(类名), len(组), 序号, ''.join(项)))
    正文.append('</section>')
    问答 = [('一共收录了多少道具？',
            '%d 条。有官方中文说明的会生成单独的页面，其余点一下就能看说明。' % len(道具们)),
           ('为什么有些道具点开不是新页面？',
            '这类道具只有名字、没有官方中文说明，单独做页面就是「薄内容」，对搜索引擎不友好。'
            '所以它们用弹层展示，不影响你查。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '宝可梦道具图鉴 - %d 条道具的效果说明 - %s' % (len(道具们), SITE.站名)
    描述 = '宝可梦道具大全：%d 条道具的中文效果说明、分类与售价。' % len(道具们)
    return 写页('items/index', 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.FAQ结构化数据(问答, SITE.U('/items/')),
                T.面包屑结构化数据([('首页', '/'), ('道具图鉴', '')], SITE)], '宝可梦道具,道具图鉴', '/items/')


def 性格总览():
    首段 = ('宝可梦一共 25 种性格。每种性格会让两项能力分别提高和降低 10%%，'
         '另外还有 5 种中性性格不改变任何能力值。')
    行 = []
    for n in sorted(性格们, key=lambda x: x['id']):
        中性 = not n['plus'] or n['plus'] == n['minus']
        行.append(['<a href="/natures/%s">%s</a>' % (n['slug'], T.esc(n['zh'])),
                  T.esc(n['plus'] or '—'), T.esc(n['minus'] or '—'),
                  T.esc(n['likes'] or '—'), T.esc(n['hates'] or '—'),
                  '<span class="muted">中性</span>' if 中性 else ''])
    正文 = [T.面包屑([('首页', '/'), ('性格表', '')], SITE)]
    正文.append('<h1>宝可梦性格表</h1><p class="lede">%s</p><p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % T.esc(首段))
    正文.append('<section class="block"><h2>25 个性格对照表</h2>%s</section>'
              % T.表格(['性格', '提升', '降低', '喜欢', '讨厌', '备注'], 行))
    问答 = [('性格对能力值影响多少？', '被提升的能力 ×1.1，被降低的能力 ×0.9，其余不变。'),
           ('哪些性格不改变能力值？', '勤奋、坦率、害羞、浮躁、认真这 5 种是中性性格，不改变任何能力值。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '宝可梦性格表 - 25 个性格加什么减什么 - %s' % SITE.站名
    描述 = '宝可梦 25 个性格的完整对照表：每种性格提升和降低哪项能力、喜欢和讨厌什么口味。'
    return 写页('natures/index', 标题, 描述, '\n'.join(正文), 'og/default.jpg',
               [T.FAQ结构化数据(问答, SITE.U('/natures/')),
                T.面包屑结构化数据([('首页', '/'), ('性格表', '')], SITE)], '宝可梦性格,性格表', '/natures/')


# ---------------------------------------------------------------- 首页与静态页
def 改版联动首页区块():
    """首页的兄弟站互推：说清「图鉴 + 改版在线玩」怎么配合用。"""
    if not SITE.gba:
        return ''
    return ('<section class="block"><h2>边玩边查：和 GBA 改版站是一家</h2>'
            '<p>本站是 <a href="https://suilang.net/">随浪工具站</a> 的一员。'
            '兄弟站 <a href="%s/">宝可梦改版 GBA 在线玩</a> 收录究极绿宝石、漆黑的魅影等中文改版，'
            '安装包、模拟器都不用，浏览器打开就能玩。</p>'
            '<p>两边是配着用的：玩到一半遇到不认识的宝可梦、拿不准招式效果和属性相克，'
            '点播放页工具栏的「🔍 图鉴」，不用退出游戏、不用切标签页就能当场查完。</p>'
            '<p><a class="btn" href="%s/">去看看有哪些改版 →</a></p></section>'
            % (SITE.gba, SITE.gba))


def 首页():
    正文 = [T.面包屑([], SITE)]
    正文.append('<h1>%s</h1><p class="lede">%s</p>'
              '<p class="updated">最后更新：<time datetime="<!--DATE-->"><!--DATE--></time></p>'
              % (T.esc(SITE.站名), T.esc(SITE.tagline)))
    正文.append('<form class="search" id="home-search" role="search" action="/search/" method="get">'
              '<input class="search-input" type="search" name="q" id="q" autocomplete="off" '
              'placeholder="搜宝可梦 / 招式 / 特性 / 道具 / 性格 —— 中文、日文、英文、编号、拼音都行" '
              'aria-label="搜索">'
              '<p class="search-hint">打「皮卡丘」「pikachu」「ピカチュウ」「25」「pikaqiu」'
              '「pkq」都会出结果；没装 JS 也能用下面的入口。</p>'
              '<div class="search-panel" id="home-results" hidden></div></form>')
    栏目 = [('/pokemon/', '宝可梦图鉴', '1025 只，含属性相克、种族值、进化与招式'),
           ('/moves/', '招式表', '%d 个招式的威力、命中、PP 与学习者' % len(可见招式)),
           ('/abilities/', '特性大全', '%d 个特性的效果与拥有者' % len(可见特性)),
           ('/items/', '道具图鉴', '2000 多条道具的说明、分类与售价'),
           ('/natures/', '性格表', '25 个性格加什么减什么，一张表看完')]
    正文.append('<ul class="grid" style="margin-top:18px">%s</ul>'
              % ''.join('<li class="card" style="align-items:flex-start;text-align:left">'
                        '<a href="%s" style="font-weight:700">%s</a>'
                        '<span class="sub">%s</span></li>' % (址, T.esc(名), T.esc(注))
                        for 址, 名, 注 in 栏目))
    正文.append('<section class="block"><h2>这个站能帮你做什么</h2>'
              '<ul style="line-height:1.9">'
              '<li><b>打不出中文也能查</b>：拼音全拼（pikaqiu）、首字母（pkq）、英文名、'
              '日文名、图鉴编号都能搜到同一只宝可梦。</li>'
              '<li><b>查得到相克</b>：每只宝可梦都有一张完整的 18 属性攻守倍率表，'
              '2 倍、4 倍、减半、免疫写得清清楚楚。</li>'
              '<li><b>看得懂说明</b>：招式、特性、道具都优先用游戏里的官方中文说明；'
              '官方没写中文的会明确告诉你「暂无官方中文说明」，不会瞎编一段糊上去。</li>'
              '<li><b>找得到进化条件</b>：等级、道具、亲密度、白天夜里、地点、交换，'
              '一句一句写明白。</li>'
              '</ul></section>')
    联动块 = 改版联动首页区块()
    if 联动块:
        正文.append(联动块)
    正文.append('<section class="block"><h2>数据从哪来</h2>'
              '<p>本站数据全部来自开源项目 <a href="https://pokeapi.co/" rel="nofollow noopener" '
              'target="_blank">PokeAPI</a> 的公开数据快照，覆盖第 1 到第 9 世代，'
              '中文名称与说明取自游戏内的官方文本。页面上的每个数字都能在数据源里对上，'
              '我们不自己编数值，也不从别的图鉴站搬运。</p>'
              '<p class="muted">宝可梦相关的商标与版权归任天堂 / Creatures / GAME FREAK 所有，'
              '本站与上述公司没有关联。</p></section>')
    问答 = [('这个图鉴收录了哪些内容？',
            '宝可梦 1025 只、招式 937 个、特性 374 个、道具 %d 条、性格 25 个，覆盖第 1 到第 9 世代。' % len(道具们)),
           ('可以不注册直接用吗？', '可以。不用注册、不用登录，所有页面直接打开就能看。'),
           ('打不出中文怎么查宝可梦？',
            '用拼音。比如「皮卡丘」可以打 pikaqiu 或首字母 pkq；也可以打英文 pikachu、日文 ピカチュウ，'
            '或者直接打图鉴编号 25。'),
           ('这个站和 GBA 改版在线玩有什么关系？',
            '两个站都是随浪工具站旗下的，配着用最顺手：在 GBA 改版玩的时候，'
            '播放页工具栏有「🔍 图鉴」按钮，点开就能查宝可梦、招式、特性和道具，不用退出游戏。'),
           ('数据会更新吗？',
            '会。跟着上游 PokeAPI 的数据更新，页面上有「最后更新」时间；内容没变就不会乱改日期。')]
    正文.append('<section class="block"><h2>常见问题</h2>%s</section>' % T.FAQ区块(问答))
    标题 = '%s - 宝可梦图鉴 / 招式 / 特性 / 道具 / 性格 在线查' % SITE.站名
    结构化 = [T.站点结构化数据(SITE), T.FAQ结构化数据(问答, SITE.网址 + '/'),
            {'@context': 'https://schema.org', '@type': 'Organization', 'name': '随浪工具站',
             'url': 'https://suilang.net/', 'email': SITE.配置.get('contactEmail') or ''}]
    return 写页('index', 标题, SITE.描述, '\n'.join(正文), 'og/default.jpg', 结构化,
               SITE.keywords, '')


def 搜索页():
    正文 = ['<h1>搜索</h1><p class="lede">在下面的框里输入宝可梦、招式、特性、道具或性格的名字。'
          '中文、繁体、英文、日文、图鉴编号、拼音全拼和首字母都能搜。</p>']
    正文.append('<form class="search" role="search" action="/search/" method="get">'
              '<input class="search-input" type="search" name="q" id="q2" autocomplete="off" '
              'placeholder="例如：皮卡丘 / pikachu / pkq / 25" aria-label="搜索">'
              '<div class="search-panel" id="search-results" hidden></div></form>')
    正文.append('<p>没有 JS 时可以从这些入口进去：%s</p>'
              % ' '.join('<a class="btn" href="%s">%s</a>' % (址, 名)
                        for 址, 名 in [('/pokemon/', '宝可梦'), ('/moves/', '招式'), ('/abilities/', '特性'),
                                     ('/items/', '道具'), ('/natures/', '性格')]))
    return 写页('search/index', '搜索 - %s' % SITE.站名,
               '搜索宝可梦、招式、特性、道具和性格，支持拼音首字母。',
               '\n'.join(正文), 'og/default.jpg', None, None, '', noindex=True)


def 内嵌页():
    """给 gba.suilang.net 用 iframe 嵌的极简查询页：没有页头页脚，白底，一个搜索框。"""
    正文 = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>查宝可梦 - %s</title>'
          '<meta name="robots" content="noindex,follow">'
          '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
          '<link rel="stylesheet" href="/assets/style.css?v=%s">'
          '</head>\n<body class="is-embed">\n'
          '<main id="main"><div class="wrap">'
          '<form class="search" role="search" action="/search/" method="get" style="margin-top:10px">'
          '<input class="search-input" type="search" name="q" id="embed-q" autocomplete="off" '
          'placeholder="查宝可梦 / 招式 / 特性 / 道具（支持拼音，如 pkq）" aria-label="搜索">'
          '<div class="search-panel" id="embed-results" hidden></div></form>'
          '<p class="search-hint">边玩边查：输入名字或拼音，点结果可以新窗口打开完整资料。</p>'
          '<div id="embed-body"></div>'
          '</div></main>\n'
          '<script src="/assets/config.js?v=%s"></script>\n'
          '<script src="/assets/app.js?v=%s" defer></script>\n</body>\n</html>\n'
          % (T.esc(SITE.站名), T.V, T.V, T.V))
    落盘('embed/index.html', 正文)
    # 内嵌页不进 sitemap（noindex）
    _状态['embed/index.html'] = {'h': hashlib.sha1(正文.encode('utf-8')).hexdigest(), 'd': TODAY}


def 一般页面(路径, 标题, 描述, 段落们):
    正文 = [T.面包屑([('首页', '/'), (标题.split(' - ')[0], '')], SITE)]
    正文.append('<h1>%s</h1>' % T.esc(标题.split(' - ')[0]))
    正文.append(''.join('<section class="block">%s</section>' % p for p in 段落们))
    return 写页(路径, 标题, 描述, '\n'.join(正文), 'og/default.jpg', None, None, '')


def 关于页():
    return 一般页面('about', '关于本站 - %s' % SITE.站名,
                 '究极宝可梦图鉴是什么、数据从哪来、为什么做这个站。',
                 ['<h2>这是什么</h2><p>一个免费、免注册的中文宝可梦资料库，'
                  '收录宝可梦、招式、特性、道具、性格五类资料，覆盖第 1 到第 9 世代。</p>'
                  '<p>它也是 <a href="https://suilang.net/">随浪工具站</a> 的一员。'
                  '如果你在 <a href="%s">GBA 改版在线玩</a>那边玩游戏，可以在这里随手查资料。</p>'
                  % T.esc(SITE.gba or 'https://gba.suilang.net'),
                  '<h2>数据从哪来</h2><p>全部来自开源项目 '
                  '<a href="https://pokeapi.co/" rel="nofollow noopener" target="_blank">PokeAPI</a> '
                  '的公开数据快照。中文名称与说明取自游戏内的官方文本。</p>'
                  '<p><b>我们不编数据。</b>官方没有中文说明的地方，页面上会写「暂无官方中文说明」，'
                  '而不是自己翻译一段或者从别的站抄一段填上去。你看到的每个数字都能在数据源里找到出处。</p>',
                  '<h2>怎么用</h2><p>顶部的搜索框支持中文、繁体、英文、日文、图鉴编号，'
                  '以及拼音全拼（pikaqiu）和首字母（pkq）。也可以从五个栏目页慢慢翻。</p>',
                  '<h2>联系我</h2><p>发现问题、想补充内容，或者有版权方面的疑问，'
                  '可以发邮件到 <a href="mailto:%s">%s</a>。</p>'
                  % (T.esc(SITE.配置.get('contactEmail') or ''), T.esc(SITE.配置.get('contactEmail') or ''))])


def 隐私页():
    return 一般页面('privacy', '隐私说明 - %s' % SITE.站名, '本站收集哪些数据、cookie 怎么用。',
                 ['<h2>本站不收集你的个人信息</h2><p>本站是纯静态网站，没有注册、没有登录，'
                  '不需要你填任何个人资料。</p>',
                  '<h2>Cookie 与第三方统计</h2><p>本站可能使用访问统计服务（如百度统计、'
                  'Cloudflare Web Analytics）来了解页面访问量。这些服务会用到 cookie，'
                  '统计的是页面访问情况，不用于识别你个人。</p>',
                  '<h2>广告</h2><p>如果本站将来展示广告，广告联盟可能会使用 cookie 来投放广告。'
                  '你可以在浏览器里关闭 cookie，不影响使用本站的查询功能。</p>',
                  '<h2>外链</h2><p>本站部分链接指向站外网站，那些网站的隐私做法不由本站负责。</p>'])


def 条款页():
    return 一般页面('terms', '使用条款 - %s' % SITE.站名, '使用本站需要知道的几条规矩。',
                 ['<h2>免费使用</h2><p>本站免费开放，不需要注册。你可以自由地查阅和分享页面链接。</p>',
                  '<h2>关于数据</h2><p>本站数据来自公开的开源数据源（PokeAPI）。'
                  '我们会尽力保证准确，但不保证与任何一款具体游戏完全一致 —— '
                  '不同世代、不同改版的数据本来就有差异，页面上也会提醒你以自己玩的版本为准。</p>',
                  '<h2>不要滥用</h2><p>请不要用脚本高频抓取本站，或者把本站内容整体搬运后再声称是原创。'
                  '想引用某一页的结论，附上来源链接就行。</p>'])


def 版权页():
    return 一般页面('dmca', '版权与投诉 - %s' % SITE.站名,
                 '版权归属说明与投诉渠道。',
                 ['<h2>版权归属</h2><p>宝可梦（Pokémon）相关的名称、图像、商标与游戏内容，'
                  '版权归任天堂（Nintendo）、Creatures Inc. 与 GAME FREAK Inc. 所有。'
                  '本站与上述公司没有任何关联，也不代表它们。</p>'
                  '<p>本站是一个非官方的资料整理站，只做数据查询，不提供任何游戏文件、ROM 或下载。</p>',
                  '<h2>数据来源</h2><p>数据来自开源项目 '
                  '<a href="https://pokeapi.co/" rel="nofollow noopener" target="_blank">PokeAPI</a>。</p>',
                  '<h2>投诉与下架</h2><p>如果你是权利人，认为本站的某部分内容侵犯了你的权益，'
                  '请发邮件到 <a href="mailto:%s">%s</a>，说明具体页面地址和理由，'
                  '我们会在核实后尽快处理。</p>'
                  % (T.esc(SITE.配置.get('legalEmail') or ''), T.esc(SITE.配置.get('legalEmail') or ''))])


def 错误页():
    正文 = ['<h1>页面走丢了</h1><p class="lede">这个地址没有对应的页面。'
          '可能是链接打错了，也可能是这一条我们还没收录。</p>']
    正文.append('<form class="search" role="search" action="/search/" method="get">'
              '<input class="search-input" type="search" name="q" autocomplete="off" '
              'placeholder="试试直接搜名字，比如「皮卡丘」或 pkq" aria-label="搜索"></form>')
    正文.append('<p class="toolbar">%s</p>' % ' '.join(
        '<a class="btn" href="%s">%s</a>' % (址, 名) for 址, 名 in
        [('/', '回首页'), ('/pokemon/', '宝可梦图鉴'), ('/moves/', '招式表'), ('/abilities/', '特性大全'),
         ('/items/', '道具图鉴'), ('/natures/', '性格表')]))
    写页('404', '页面走丢了 - %s' % SITE.站名, '没有找到这个页面。', '\n'.join(正文),
        'og/default.jpg', None, None, '', noindex=True, 收录=False)


# ---------------------------------------------------------------- SEO 资产
def 站点地图次序(地址):
    """首页 → 五个栏目根 → 其余条目。

    百度不支持 sitemap 提交，只能靠 API 一条条推，而新站一天只有几条配额
    （普通收录接口一般是 10 条/天）。推送脚本是按站点地图的顺序推的，
    所以最重要的页面必须排在最前面，否则首页要等到一年后才轮得到。"""
    if 地址 == '/':
        return 0
    if 地址 in ('/pokemon/', '/moves/', '/abilities/', '/items/', '/natures/'):
        return 1
    return 2


def 生成站点地图(额外):
    清单 = 额外 + 页面清单
    # Python 的 sort 是稳定的：同一个优先级里保持原来的顺序
    清单.sort(key=lambda x: 站点地图次序(x[0]))
    行 = []
    for 址, 日期 in 清单:
        行.append('  <url><loc>%s</loc><lastmod>%s</lastmod></url>' % (SITE.U(址), 日期))
    内容 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
          % '\n'.join(行))
    落盘('sitemap.xml', 内容)
    return len(行)


def 生成llms():
    行 = ['# %s' % SITE.站名, '',
        '> 免费的中文宝可梦资料库：宝可梦 %d 只、招式 %d 个、特性 %d 个、道具 %d 条、性格 %d 个，'
        '覆盖第 1 到第 9 世代。支持中文、繁体、英文、日文、图鉴编号与拼音查询，免注册。'
        % (len(宝可梦们), len(可见招式), len(可见特性), len(道具们), len(性格们)), '',
        '## 主要栏目', '',
        '- 宝可梦图鉴（%d 只，含属性相克表、种族值、特性、进化方式、可学招式）：%s'
        % (len(宝可梦们), SITE.U('/pokemon/')),
        '- 招式表（%d 个，含威力/命中/PP/分类与学习者）：%s' % (len(可见招式), SITE.U('/moves/')),
        '- 特性大全（%d 个，含中文效果与拥有者）：%s' % (len(可见特性), SITE.U('/abilities/')),
        '- 道具图鉴（%d 条，含中文说明、分类与售价）：%s' % (len(道具们), SITE.U('/items/')),
        '- 性格表（25 个性格加什么减什么）：%s' % SITE.U('/natures/'), '',
        '## 按属性与世代', '',
        '- 按属性：%s' % '、'.join('%s %s' % (M.属性名(k), SITE.U('/pokemon/type/%s' % k)) for k in M.属性顺序[:6]),
        '- 按世代：%s' % '、'.join('%s %s' % (M.世代名(i), SITE.U('/pokemon/gen/%d' % i)) for i in range(1, 10)), '',
        '## 数据口径', '',
        '- 数据来源：PokeAPI 的公开数据快照（https://pokeapi.co/），中文名称与说明取自游戏内官方文本。',
        '- 官方没有中文说明的条目，页面上会明确标注「暂无官方中文说明」，本站不做自行翻译或补写。',
        '- 还有 %d 个招式、%d 个特性官方从来没写过中文说明（多是旁支作品：GC《暗之旋风》的暗影招式、'
        '《信长的野望》的特性）。这些页面照旧存在、站内搜索查得到，但不列入招式表 / 特性大全，'
        '也不进 sitemap（页面带 noindex）。' % (len(招式们) - len(可见招式), len(特性们) - len(可见特性)),
        '- 每只宝可梦页面的「属性相克」给出完整的 18 属性攻守倍率，可直接引用。',
        '- 页面上的「最后更新」只在内容真的改动时才推进。',
        '- 宝可梦相关商标与版权归任天堂 / Creatures / GAME FREAK 所有，本站为无关联的非官方资料站。', '',
        '## 常用查询', '',
        '- 皮卡丘（#025，电属性，种族值总和 320）：%s' % SITE.U('/pokemon/pikachu'),
        '- 十万伏特（威力 90 的电属性特殊招式）：%s' % SITE.U('/moves/thunderbolt'),
        '- 25 个性格对照表：%s' % SITE.U('/natures/'), '']
    落盘('llms.txt', '\n'.join(行))


def 生成robots():
    落盘('robots.txt', '\n'.join([
        'User-agent: *',
        'Allow: /',
        '',
        '# 不限制任何爬虫（含 GPTBot、ClaudeBot、PerplexityBot 等 AI 搜索）：',
        '# 先被爬到，才有可能被引用。',
        '# 只挡掉查询页、内嵌页和纯资源目录 —— 这些内容在别的地址上都有，',
        '# 让爬虫把配额花在真正的条目页上。',
        'Disallow: /search',
        'Disallow: /embed',
        'Disallow: /data/',
        'Disallow: /assets/',
        'Disallow: /img/',
        '',
        'Sitemap: %s/sitemap.xml' % SITE.网址,
        '']))


# ---------------------------------------------------------------- 主流程
宝可梦们 = []
招式们 = []
特性们 = []
道具们 = []
性格们 = []
可见招式 = []        # 有官方中文说明的招式：招式表只列这些（其余见「薄内容」说明）
可见特性 = []
特性索引 = {}
宝可梦slug映射 = {}
相克矩阵 = {}


def 载入():
    global 宝可梦们, 招式们, 特性们, 道具们, 性格们, 可见招式, 可见特性
    global 特性索引, 宝可梦slug映射, 相克矩阵
    需要 = ['pokemon.json', 'moves.json', 'abilities.json', 'items.json', 'type-matrix.json']
    for 名 in 需要:
        if not os.path.exists(os.path.join(OUT, 名)):
            sys.stderr.write('缺少 build/_out/%s —— 先跑一次 python3 build/生成数据.py\n' % 名)
            sys.exit(1)
    读 = lambda 名: json.load(io.open(os.path.join(OUT, 名), encoding='utf-8'))
    宝可梦们 = 读('pokemon.json')
    招式们 = 读('moves.json')
    特性们 = 读('abilities.json')
    道具们 = 读('items.json')
    性格们 = json.load(io.open(os.path.join(DATA, 'natures.json'), encoding='utf-8'))
    相克矩阵 = 读('type-matrix.json')
    特性索引 = {a['slug']: a for a in 特性们}
    宝可梦slug映射 = {str(p['id']): p['slug'] for p in 宝可梦们}
    可见招式 = [m for m in 招式们 if not m.get('thin')]
    可见特性 = [a for a in 特性们 if not a.get('thin')]


def 薄内容说明(单位, 总数, 例子):
    """总览页下方那句话：还有几个官方没写过中文说明的，没列进来，但搜得到。"""
    隐藏 = 总数 - len(可见招式 if 单位 == '招式' else 可见特性)
    if not 隐藏:
        return ''
    return ('另外还有 <b>%d 个%s</b>官方从来没有写过中文说明（%s），'
            '页面上如实标着「暂无官方中文说明」。它们没列在下面，'
            '但用站内搜索照样能查到。' % (隐藏, 单位, 例子))


def main():
    载入()
    print('数据：宝可梦 %d · 招式 %d · 特性 %d · 道具 %d（生成页面 %d）· 性格 %d'
          % (len(宝可梦们), len(招式们), len(特性们), len(道具们),
             sum(1 for x in 道具们 if x['page']), len(性格们)))

    print('一、宝可梦页……')
    for i, p in enumerate(宝可梦们):
        宝可梦页(p, 宝可梦们[i - 1] if i else None,
              宝可梦们[i + 1] if i + 1 < len(宝可梦们) else None)
    print('二、招式页……')
    for m in 招式们:
        招式页(m)
    print('三、特性页……')
    for a in 特性们:
        特性页(a)
    print('四、道具页……')
    for it in 道具们:
        if it['page']:
            道具页(it)
    print('五、性格页……')
    for n in 性格们:
        性格页(n)
    print('六、总览与聚合页……')
    宝可梦总览()
    for k in M.属性顺序:
        属性聚合页(k, [p for p in 宝可梦们 if k in p['types']])
    for 代 in range(1, 10):
        世代聚合页(代, [p for p in 宝可梦们 if p['gen'] == 代])
    招式总览()
    特性总览()
    道具总览()
    性格总览()
    print('七、首页与静态页……')
    首页()
    搜索页()
    内嵌页()
    关于页()
    隐私页()
    条款页()
    版权页()
    错误页()
    print('八、SEO 资产……')
    条数 = 生成站点地图([])
    生成llms()
    生成robots()

    json.dump(_状态, io.open(STATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False)
    print('\n完成：共 %d 个页面进了 sitemap。' % 条数)
    print('  内容%s。' % ('有变化' if _脏['值'] else '没有变化（日期不会往前跑）'))
    print('\n下一步：双击 scripts/本地预览.command 看效果，或 scripts/重新上线.command 上线。')


if __name__ == '__main__':
    main()
