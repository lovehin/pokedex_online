/* ============================================================
   究极宝可梦图鉴 · 前端交互
   ------------------------------------------------------------
   只做三件事：
     1. 搜索（中文 / 繁体 / 英文 / 日文 / 编号 / 拼音全拼 / 拼音首字母 / 民间译名）
     2. 各总览页的筛选与卡片渲染
     3. 没有静态页的道具，点一下用弹层展示说明
   索引是构建时生成的静态 JSON，一次加载后搜索零请求、输入即出，不需要后端。
   ============================================================ */
(function () {
  'use strict';

  var 内嵌 = document.body.classList.contains('is-embed');
  var 索引 = {};                       // 已经拿到的索引数据
  var 等待 = {};                       // 正在下载的索引（Promise），避免同一个文件下两次
  var 分类 = [
    { 键: 'index', 文件: 'index.json', 名: '宝可梦', 址: '/pokemon/', 图: true },
    { 键: 'moves', 文件: 'moves-index.json', 名: '招式', 址: '/moves/', 图: false },
    { 键: 'abilities', 文件: 'abilities-index.json', 名: '特性', 址: '/abilities/', 图: false },
    { 键: 'items', 文件: 'items-index.json', 名: '道具', 址: '/items/', 图: false },
    { 键: 'natures', 文件: 'natures.json', 名: '性格', 址: '/natures/', 图: false }
  ];

  function 取(地址) {
    return fetch(地址, { credentials: 'same-origin' }).then(function (r) {
      return r.ok ? r.json() : [];
    }).catch(function () { return []; });
  }

  function 加载(名) {
    if (索引[名]) { return Promise.resolve(索引[名]); }
    if (!等待[名]) {
      var c = 分类.filter(function (x) { return x.键 === 名; })[0];
      等待[名] = 取('/data/' + c.文件).then(function (数据) {
        索引[名] = 数据 || [];
        return 索引[名];
      });
    }
    return 等待[名];
  }

  function 载入全部() { return Promise.all(分类.map(function (c) { return 加载(c.键); })); }

  /* ---------------------------------------------------------- 搜索 */
  function 规整(s) {
    return String(s == null ? '' : s).toLowerCase().replace(/[\s·・.\-'’]/g, '');
  }

  function 词表(项, 类型) {
    var 词 = [项.zh, 项.zhHant, 项.en, 项.ja, 项.py, 项.pyInit];
    if (类型 === 'index') { 词.push(String(项.id)); (项.alias || []).forEach(function (a) { 词.push(a); }); }
    return 词;
  }

  // 命中打分：完全匹配 > 首字母 > 前缀 > 包含。返回 0 表示没命中。
  function 打分(项, 类型, q) {
    var 主 = [项.zh, 项.zhHant, 项.en, 项.ja].map(规整);
    var 拼 = [规整(项.py), 规整(项.pyInit)];
    var 名 = 主.concat(拼);
    var i;
    for (i = 0; i < 名.length; i++) { if (名[i] === q) { return i < 4 ? 100 : 92; } }
    if (类型 === 'index' && String(项.id) === q) { return 96; }
    if (规整(项.pyInit) === q) { return 90; }
    for (i = 0; i < 名.length; i++) { if (名[i].indexOf(q) === 0) { return 70; } }
    if (类型 === 'index') {
      var 别 = 项.alias || [];
      for (i = 0; i < 别.length; i++) { if (规整(别[i]) === q) { return 94; } }
    }
    for (i = 0; i < 名.length; i++) { if (名[i].indexOf(q) >= 0) { return 50; } }
    if (类型 === 'index' && String(项.id).indexOf(q) === 0) { return 60; }
    return 0;
  }

  function 副标题(项, 类型) {
    if (类型 === 'index') {
      return '#' + ('00' + 项.id).slice(-3) + ' · ' + (项.types || []).map(属性名).join('/') +
        (项.bst ? ' · 种族值 ' + 项.bst : '');
    }
    if (类型 === 'moves') {
      return 属性名(项.type) + ' · ' + (项.power ? '威力 ' + 项.power : '变化') +
        (项.pp ? ' · PP ' + 项.pp : '');
    }
    if (类型 === 'abilities') { return '拥有者 ' + (项.owners || []).length + ' 只'; }
    if (类型 === 'items') { return 项.categoryZh || ''; }
    return 项.plus ? ('+' + 项.plus + ' / −' + 项.minus) : '中性性格';
  }

  var 属性中文 = {
    normal: '一般', fire: '火', water: '水', grass: '草', electric: '电', ice: '冰',
    fighting: '格斗', poison: '毒', ground: '地面', flying: '飞行', psychic: '超能力',
    bug: '虫', rock: '岩石', ghost: '幽灵', dragon: '龙', dark: '恶', steel: '钢', fairy: '妖精'
  };
  function 属性名(k) { return 属性中文[k] || k || ''; }

  function 检索(q) {
    q = 规整(q);
    if (!q) { return []; }
    var 结果 = [];
    分类.forEach(function (c) {
      var 表 = 索引[c.键] || [];
      var 命中 = [];
      for (var i = 0; i < 表.length; i++) {
        var s = 打分(表[i], c.键, q);
        if (s) { 命中.push({ 项: 表[i], 分: s, 型: c.键, 类: c }); }
      }
      命中.sort(function (a, b) { return b.分 - a.分 || (a.项.id - b.项.id); });
      if (命中.length) { 结果.push({ 类: c, 命中: 命中.slice(0, 8) }); }
    });
    return 结果;
  }

  function 行HTML(项, 型, 类) {
    var 址 = 类.址 + 项.slug;
    var 图 = (类.图 && 型 === 'index')
      ? '<img src="/img/pokemon/s/' + 项.id + '.webp" width="32" height="32" alt="" loading="lazy">' : '';
    var 新窗 = 内嵌 ? ' target="_blank" rel="noopener"' : '';
    return '<a class="search-hit" href="' + 址 + '"' + 新窗 + '>' + 图 +
      '<span>' + 转义(项.zh) + '</span>' +
      '<span class="hit-sub">' + 转义(副标题(项, 型)) + '</span></a>';
  }

  function 转义(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function 渲染结果(面板, 结果, q) {
    if (!结果.length) {
      面板.innerHTML = '<div class="search-empty">没找到「' + 转义(q) + '」。' +
        '换个说法试试：拼音首字母（pkq）、英文名（pikachu）、或者图鉴编号（25）。</div>';
    } else {
      面板.innerHTML = 结果.map(function (组) {
        return '<div class="search-group"><h3>' + 组.类.名 + '</h3>' +
          组.命中.map(function (h) { return 行HTML(h.项, h.型, h.类); }).join('') + '</div>';
      }).join('');
    }
    面板.hidden = false;
    面板.setAttribute('data-open', '');
  }

  var 防抖 = null;
  function 绑定搜索(输入, 面板) {
    if (!输入 || !面板) { return; }
    var 已载 = false;
    输入.addEventListener('focus', function () {
      if (已载) { return; }
      已载 = true;
      加载('index').then(function () { if (输入.value) { 输入.dispatchEvent(new Event('input')); } });
      setTimeout(function () { 载入全部(); }, 400);   // 其余几类悄悄加载，等用户真打了字就已经好了
    });
    输入.addEventListener('input', function () {
      clearTimeout(防抖);
      var q = 输入.value;
      防抖 = setTimeout(function () {
        if (!规整(q)) { 面板.hidden = true; 面板.removeAttribute('data-open'); return; }
        加载('index').then(function () { 渲染结果(面板, 检索(q), q); });
      }, 60);
    });
    输入.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { 面板.hidden = true; 面板.removeAttribute('data-open'); }
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter') { return; }
      var 项们 = [].slice.call(面板.querySelectorAll('.search-hit'));
      if (!项们.length) { return; }
      var 当前 = 项们.findIndex(function (a) { return a.getAttribute('aria-selected') === 'true'; });
      if (e.key === 'Enter') {
        if (当前 >= 0) { e.preventDefault(); 项们[当前].click(); }
        return;
      }
      e.preventDefault();
      if (当前 >= 0) { 项们[当前].removeAttribute('aria-selected'); }
      当前 = e.key === 'ArrowDown' ? (当前 + 1) % 项们.length : (当前 - 1 + 项们.length) % 项们.length;
      项们[当前].setAttribute('aria-selected', 'true');
      项们[当前].scrollIntoView({ block: 'nearest' });
    });
    document.addEventListener('click', function (e) {
      if (!面板.contains(e.target) && e.target !== 输入) {
        面板.hidden = true; 面板.removeAttribute('data-open');
      }
    });
  }

  /* ---------------------------------------------------------- 宝可梦总览：筛选与卡片 */
  function 初始化图鉴() {
    var 网格 = document.getElementById('dex-grid');
    if (!网格) { return; }
    var 计数 = document.getElementById('dex-count');
    var 更多 = document.getElementById('dex-more');
    var 排序 = document.getElementById('dex-sort');
    var 世代 = document.getElementById('dex-gen');
    var 属性钮 = [].slice.call(document.querySelectorAll('#dex-filters .chip'));
    var 全表 = [];
    var 显示数 = 60;
    var 当前属性 = '';
    var 每页 = 60;

    function 画() {
      var 组 = 全表.filter(function (p) {
        return (!当前属性 || (p.types || []).indexOf(当前属性) >= 0) &&
          (!世代.value || String(p.gen) === 世代.value);
      });
      var 法 = 排序.value;
      组.sort(function (a, b) {
        if (法 === 'bst') { return b.bst - a.bst; }
        if (法 === 'name') { return String(a.zh).localeCompare(String(b.zh), 'zh'); }
        return a.id - b.id;
      });
      计数.textContent = '共 ' + 组.length + ' 只' + (组.length > 显示数 ? '，已显示前 ' + 显示数 + ' 只' : '');
      网格.innerHTML = 组.slice(0, 显示数).map(function (p) {
        return '<li><a class="card" href="/pokemon/' + p.slug + '">' +
          '<img src="/img/pokemon/s/' + p.id + '.webp" width="96" height="96" alt="" loading="lazy">' +
          '<span class="no">#' + ('00' + p.id).slice(-3) + '</span>' +
          '<span class="nm">' + 转义(p.zh) + '</span>' +
          '<span class="sub">' + (p.types || []).map(属性名).join('/') + ' · ' + p.bst + '</span></a></li>';
      }).join('');
      更多.hidden = 组.length <= 显示数;
    }

    属性钮.forEach(function (b) {
      b.addEventListener('click', function () {
        属性钮.forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        当前属性 = b.getAttribute('data-type');
        显示数 = 每页;
        画();
      });
    });
    [排序, 世代].forEach(function (el) { el.addEventListener('change', function () { 显示数 = 每页; 画(); }); });
    更多.addEventListener('click', function () { 显示数 += 每页 * 2; 画(); });

    加载('index').then(function (表) { 全表 = 表; 画(); });
  }

  /* ---------------------------------------------------------- 招式总览：筛选 */
  function 初始化招式() {
    var 网格 = document.getElementById('move-grid');
    if (!网格) { return; }
    var 计数 = document.getElementById('move-count');
    var 分类选 = document.getElementById('move-class');
    var 属性钮 = [].slice.call(document.querySelectorAll('#move-filters .chip'));
    var 全表 = [];
    var 当前属性 = '';
    var 每页 = 60;
    var 显示数 = 每页;

    function 画() {
      var 组 = 全表.filter(function (m) {
        return (!当前属性 || m.type === 当前属性) && (!分类选.value || m.class === 分类选.value);
      });
      组.sort(function (a, b) { return a.id - b.id; });
      计数.textContent = '共 ' + 组.length + ' 个' + (组.length > 显示数 ? '，已显示前 ' + 显示数 + ' 个' : '');
      网格.innerHTML = 组.slice(0, 显示数).map(function (m) {
        return '<li><a class="card" href="/moves/' + m.slug + '">' +
          '<span class="no">' + 转义(属性名(m.type)) + '</span>' +
          '<span class="nm">' + 转义(m.zh) + '</span>' +
          '<span class="sub">' + (m.power ? '威力 ' + m.power : '变化') + ' · PP ' + m.pp + '</span></a></li>';
      }).join('');
    }
    属性钮.forEach(function (b) {
      b.addEventListener('click', function () {
        属性钮.forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        当前属性 = b.getAttribute('data-type');
        显示数 = 每页;
        画();
      });
    });
    分类选.addEventListener('change', function () { 显示数 = 每页; 画(); });
    加载('moves').then(function (表) { 全表 = 表; 画(); });
  }

  /* ---------------------------------------------------------- 道具总览：页内筛选 + 弹层 */
  function 初始化道具() {
    var 输入 = document.getElementById('item-search');
    var 计数 = document.getElementById('item-count');
    if (!输入) { return; }
    加载('items').then(function () {
      var 表 = {};
      (索引.items || []).forEach(function (it) { 表[it.slug] = it; });
      var 全部 = 计数 ? document.querySelectorAll('[data-item-group]') : null;

      function 筛() {
        var q = 规整(输入.value);
        var 可见 = 0;
        (索引.items || []).forEach(function (it) { it._匹配 = !q || 打分(it, 'items', q) > 0; });
        document.querySelectorAll('li[data-slug]').forEach(function (li) {
          var it = 表[li.getAttribute('data-slug')];
          var ok = !it || it._匹配;
          li.hidden = !ok;
          if (ok) { 可见++; }
        });
        计数.textContent = q ? ('筛出 ' + 可见 + ' 条') : ('共 ' + (索引.items || []).length + ' 条道具');
      }
      输入.addEventListener('input', 筛);
      var 清空 = document.getElementById('item-clear');
      if (清空) { 清空.addEventListener('click', function () { 输入.value = ''; 筛(); }); }
      筛();

      document.addEventListener('click', function (e) {
        var a = e.target.closest ? e.target.closest('.item-pop') : null;
        if (!a) { return; }
        e.preventDefault();
        var it = 表[a.getAttribute('data-slug')];
        if (it) { 弹层(it); }
      });
    });
  }

  function 弹层(it) {
    var d = document.createElement('div');
    d.className = 'modal';
    d.style.cssText = 'position:fixed;inset:0;background:rgba(22,35,60,.45);display:flex;' +
      'align-items:center;justify-content:center;padding:20px;z-index:60';
    d.innerHTML = '<div style="background:var(--bg);border-radius:14px;max-width:440px;width:100%;' +
      'padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.3)">' +
      '<h3 style="margin:0 0 8px">' + 转义(it.zh) + '</h3>' +
      '<p style="margin:0 0 6px;color:var(--fg-soft)">' +
      (it.text ? 转义(it.text) : '暂无官方中文说明。') + '</p>' +
      '<p class="muted" style="font-size:.82rem">' + 转义(it.categoryZh || '') +
      (it.cost ? ' · 售价 ' + it.cost : '') + '</p>' +
      '<p style="margin:14px 0 0"><button class="btn" type="button">关闭</button></p></div>';
    d.addEventListener('click', function (e) {
      if (e.target === d || e.target.tagName === 'BUTTON') { d.remove(); }
    });
    document.body.appendChild(d);
  }

  /* ---------------------------------------------------------- 内嵌页：把 ?q= 直接搜出来 */
  function 初始化内嵌() {
    if (!内嵌) { return; }
    var 输入 = document.getElementById('embed-q');
    var 面板 = document.getElementById('embed-results');
    if (!输入 || !面板) { return; }
    面板.hidden = false;
    面板.setAttribute('data-open', '');
    var q = new URLSearchParams(location.search).get('q');
    载入全部().then(function () {
      if (q) { 输入.value = q; 渲染结果(面板, 检索(q), q); }
      else { 输入.focus(); }
    });
  }

  /* ---------------------------------------------------------- 启动 */
  function 启动() {
    绑定搜索(document.getElementById('q'), document.getElementById('home-results'));
    绑定搜索(document.getElementById('q2'), document.getElementById('search-results'));
    绑定搜索(document.getElementById('embed-q'), document.getElementById('embed-results'));
    初始化图鉴();
    初始化招式();
    初始化道具();
    初始化内嵌();
    // 首页和内嵌页的搜索要「打开就能用」，所以提前把最常用的索引load好
    if (document.getElementById('home-search')) { 加载('index'); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', 启动);
  } else {
    启动();
  }
})();
