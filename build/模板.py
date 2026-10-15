#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面骨架与可复用的小组件。

「页脚」和「页头」只在这里维护一份 —— 生成脚本只管往中间塞正文。
页脚那段赞赏块 + 回链主站是站群统一约定（AGENTS.md 第十节），照抄，不要自己发挥。
"""
import datetime
import html
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 映射表 as M                                                   # noqa: E402

V = '1'          # 改过 assets/ 下的 css/js 之后把这个数字加 1，再重新生成


def esc(文本):
    return html.escape(str(文本 if 文本 is not None else ''), quote=True)


def 数字(n):
    """给数字加千分位；0 显示成「—」，免得表格里一片 0 分不清是「没有」还是「为零」。"""
    if n is None or n == '':
        return '—'
    try:
        n = int(n)
    except (TypeError, ValueError):
        return esc(n)
    return '{:,}'.format(n) if n else '—'


class 站点:
    """站点级配置。由 生成页面.py 用 assets/config.js 的内容构造。"""

    def __init__(self, 配置):
        self.配置 = 配置
        域 = str(配置.get('domain') or 'pokedex.suilang.net').rstrip('/')
        self.域名 = 域
        self.网址 = 'https://' + 域
        self.站名 = 配置.get('name') or '究极宝可梦图鉴'
        self.短名 = 配置.get('shortName') or self.站名
        self.tagline = 配置.get('tagline') or ''
        self.描述 = 配置.get('description') or ''
        self.keywords = 配置.get('keywords') or ''
        self.验证 = 配置.get('verify') or {}
        self.统计 = 配置.get('analytics') or {}
        self.广告 = 配置.get('ads') or {}
        self.gba = str(配置.get('gbaSite') or '').rstrip('/')
        self.起始年 = int(配置.get('startYear') or datetime.date.today().year)

    def U(self, 路径):
        """站内地址 → 完整网址（路径不带 .html）。"""
        if 路径 in ('', '/'):
            return self.网址 + '/'
        return self.网址 + 路径

    def 版权年份(self):
        今 = datetime.date.today().year
        return str(self.起始年) if self.起始年 >= 今 else '%s–%s' % (self.起始年, 今)

    # ------------------------------------------------------------ 页头
    def head(self, 标题, 描述, 路径, og='og/default.jpg', jsonld=None,
             keywords=None, noindex=False):
        p = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>%s</title>' % esc(标题),
            '<meta name="description" content="%s">' % esc(描述),
            '<link rel="canonical" href="%s">' % esc(self.U(路径)),
            '<meta name="robots" content="%s">' % ('noindex,follow' if noindex else 'index,follow'),
            '<meta name="theme-color" content="#ffffff">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="%s">' % esc(self.站名),
            '<meta property="og:title" content="%s">' % esc(标题),
            '<meta property="og:description" content="%s">' % esc(描述),
            '<meta property="og:url" content="%s">' % esc(self.U(路径)),
            '<meta property="og:image" content="%s">' % esc(self.U('/' + og)),
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:title" content="%s">' % esc(标题),
            '<meta name="twitter:description" content="%s">' % esc(描述),
            '<meta name="twitter:image" content="%s">' % esc(self.U('/' + og)),
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
            '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">',
            '<link rel="manifest" href="/manifest.webmanifest">',
            '<link rel="stylesheet" href="/assets/style.css?v=%s">' % V,
        ]
        if keywords:
            p.append('<meta name="keywords" content="%s">' % esc(keywords))
        for 键, 属性名 in (('baidu', 'baidu-site-verification'),
                        ('bytedance', 'bytedance-verification-code'),
                        ('google', 'google-site-verification'),
                        ('bing', 'msvalidate.01')):
            if self.验证.get(键):
                p.append('<meta name="%s" content="%s">' % (属性名, esc(self.验证[键])))
        if self.统计.get('baidu'):
            p.append('<script>var _hmt=_hmt||[];(function(){var hm=document.createElement("script");'
                     'hm.src="https://hm.baidu.com/hm.js?%s";var s=document.getElementsByTagName("script")[0];'
                     's.parentNode.insertBefore(hm,s);})();</script>' % esc(self.统计['baidu']))
        if self.广告.get('enabled') and self.广告.get('head'):
            p.append(self.广告['head'])
        if jsonld:
            p.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(jsonld, ensure_ascii=False, separators=(',', ':')))
        return '\n'.join(p)

    def 广告位(self, 名字, 类名='ad-slot'):
        """广告位：没接广告联盟之前整块不输出，页面上不留空框。"""
        if not (self.广告.get('enabled') and self.广告.get(名字)):
            return ''
        return '<div class="%s no-print">%s</div>' % (类名, self.广告[名字])

    # ------------------------------------------------------------ 页头导航
    def 页头(self, 当前=''):
        导航 = [('/', '首页'), ('/pokemon/', '宝可梦'), ('/moves/', '招式'),
              ('/abilities/', '特性'), ('/items/', '道具'), ('/natures/', '性格')]
        链接 = ''.join(
            '<a href="%s"%s>%s</a>' % (址, ' aria-current="page"' if 址 == 当前 else '', esc(名))
            for 址, 名 in 导航)
        return ('<a class="skip" href="#main">跳到主要内容</a>'
                '<header class="site-header"><div class="wrap">'
                '<a class="brand" href="/"><span class="brand-mark" aria-hidden="true"></span>%s</a>'
                '<nav class="nav" aria-label="主导航">%s</nav>'
                '</div></header>' % (esc(self.站名), 链接))

    # ------------------------------------------------------------ 页脚
    def 页脚(self):
        return (
            '<footer class="site-footer no-print"><div class="wrap"><div class="cols">'
            '<div><h2>%s</h2>'
            '<p style="font-size:.82rem;margin:8px 0 0">本站是 '
            '<a href="https://suilang.net/">随浪工具站</a> 的一员 —— '
            '还有 GBA 改版在线玩、图片转换等更多免费小工具。</p>'
            '<p style="margin:10px 0 0">%s</p>'
            '</div>'
            '<div><h2>资料库</h2><ul>'
            '<li><a href="/pokemon/">宝可梦图鉴</a></li>'
            '<li><a href="/moves/">招式表</a></li>'
            '<li><a href="/abilities/">特性大全</a></li>'
            '<li><a href="/items/">道具图鉴</a></li>'
            '<li><a href="/natures/">性格表</a></li>'
            '</ul></div>'
            '<div><h2>关于</h2><ul>'
            '<li><a href="/about">关于本站</a></li>'
            '<li><a href="/privacy">隐私说明</a></li>'
            '<li><a href="/terms">使用条款</a></li>'
            '<li><a href="/dmca">版权与投诉</a></li>'
            '<li><a href="mailto:%s">联系我</a></li>'
            '</ul></div></div>%s'
            '<div class="legal"><span>© %s %s</span>'
            '<span>数据来源 PokeAPI · 宝可梦相关商标与版权归任天堂 / Creatures / GAME FREAK 所有</span>'
            '</div></div></footer>' % (
                esc(self.站名), esc(self.tagline), esc(self.配置.get('contactEmail') or ''),
                赞赏块(), self.版权年份(), esc(self.站名)))

    def 页面(self, 标题, 描述, 路径, 正文, og='og/default.jpg', jsonld=None,
           keywords=None, 当前='', noindex=False):
        return ('<!doctype html>\n<html lang="zh-CN">\n<head>\n%s\n</head>\n<body>\n%s\n'
                '<main id="main"><div class="wrap">\n%s\n</div></main>\n%s\n'
                '<script src="/assets/config.js?v=%s"></script>\n'
                '<script src="/assets/app.js?v=%s" defer></script>\n</body>\n</html>\n'
                % (self.head(标题, 描述, 路径, og, jsonld, keywords, noindex),
                   self.页头(当前), 正文, self.页脚(), V, V))


# ---------------------------------------------------------------- 页脚赞赏块
def 赞赏块():
    """站群统一约定（AGENTS.md 第十节第 3 条）—— 照抄，别改文案。"""
    return (
        '<div class="no-print" style="border-top:1px solid rgba(22,35,60,.10);margin-top:22px;padding-top:18px">'
        '<details><summary>❤️ 支持随浪 · 请我喝杯奶茶</summary>'
        '<div style="margin-top:14px;font-size:.85rem;line-height:1.75">'
        '<p style="margin:0 0 14px">这个站一直免费，也没有注册墙。如果它帮到了你，可以请我喝杯奶茶 ☕ '
        '你的支持就是它继续更新的动力。</p>'
        '<div class="pay-row">'
        '<figure><img class="pay-img" src="https://suilang.net/assets/pay/wechat.jpg" '
        'alt="微信赞赏码" width="540" height="733" loading="lazy">'
        '<figcaption style="margin-top:6px;font-size:.78rem">微信</figcaption></figure>'
        '<figure><img class="pay-img" src="https://suilang.net/assets/pay/alipay.jpg" '
        'alt="支付宝收款码" width="540" height="810" loading="lazy">'
        '<figcaption style="margin-top:6px;font-size:.78rem">支付宝</figcaption></figure>'
        '</div>'
        '<p style="margin:14px 0 0;font-size:.8rem;opacity:.72">放个收款码不是打赏墙 —— '
        '一分钱不花也能用全部功能。想让我知道是谁支持了，付款时留个称呼就行。</p>'
        '</div></details></div>')


# ---------------------------------------------------------------- 组件
def 属性徽章(键):
    if not 键:
        return ''
    名 = M.属性名(键)
    return '<span class="type type-%s">%s</span>' % (esc(键), esc(名))


def 属性徽章组(键们):
    return ''.join(属性徽章(k) for k in (键们 or []))


def 表格(表头, 行们, 类名='tbl'):
    """行们：每行是一个字符串列表；单元格内容已经是可以直接放的 HTML。"""
    if not 行们:
        return ''
    头 = ''.join('<th%s>%s</th>' % (' class="num"' if i else '', esc(h))
               for i, h in enumerate(表头))
    if 表头 and 表头[0] == '':
        头 = ''.join('<th%s>%s</th>' % (' class="num"', esc(h)) for h in 表头)
    体 = []
    for 行 in 行们:
        格 = ''.join('<td%s>%s</td>' % (' class="num"' if i else '', c)
                   for i, c in enumerate(行))
        体.append('<tr>%s</tr>' % 格)
    return ('<div class="tbl-scroll"><table class="%s"><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></div>' % (类名, 头, ''.join(体)))


def FAQ区块(问答们):
    if not 问答们:
        return ''
    return ('<dl class="faq">%s</dl>'
            % ''.join('<dt>%s</dt><dd>%s</dd>' % (esc(问), 答) for 问, 答 in 问答们))


def FAQ结构化数据(问答们, 页面网址):
    return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [{
            '@type': 'Question',
            'name': 问,
            'acceptedAnswer': {'@type': 'Answer', 'text': 答.replace('<', ' ').replace('>', ' ')},
        } for 问, 答 in 问答们],
    }


def 面包屑(项们, 站点):
    """项们：[(名称, 地址)]，地址为空表示当前页（不可点）。"""
    片段 = []
    for 名, 址 in 项们:
        片段.append('<a href="%s">%s</a>' % (址, esc(名)) if 址 else esc(名))
    return '<nav class="crumbs">%s</nav>' % ' / '.join(片段)


def 面包屑结构化数据(项们, 站点):
    元素 = []
    for i, (名, 址) in enumerate(项们, 1):
        项 = {'@type': 'ListItem', 'position': i, 'name': 名}
        if 址:
            项['item'] = 站点.U(址)
        元素.append(项)
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': 元素}


def 站点结构化数据(站点):
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': 站点.站名,
        'url': 站点.网址 + '/',
        'description': 站点.描述,
        'inLanguage': 'zh-CN',
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {'@type': 'EntryPoint', 'urlTemplate': 站点.网址 + '/search?q={search_term_string}'},
            'query-input': 'required name=search_term_string',
        },
        'publisher': {'@type': 'Organization', 'name': '随浪工具站', 'url': 'https://suilang.net/'},
    }
