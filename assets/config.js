/* ============================================================
   究极宝可梦图鉴 · 全站唯一配置入口
   ------------------------------------------------------------
   改站名、换域名、加统计、加站长验证、开广告，都只改这里，
   然后双击 scripts/重新上线.command 重新生成一遍。
   生成脚本：build/生成页面.py（直接读本文件，不重复维护第二份）
   ============================================================ */
window.SITE = {

  /* ---------- 基本信息 ---------- */
  domain: "pokedex.suilang.net",          // 不带 https:// 和结尾斜杠
  name: "究极宝可梦图鉴",
  shortName: "究极图鉴",
  nameEn: "PokeDex",
  tagline: "宝可梦图鉴 · 招式 / 特性 / 道具 / 性格 在线查",
  description: "究极宝可梦图鉴：1025 只宝可梦、937 个招式、374 个特性、2000 多条道具和 25 个性格的中文资料库。每只宝可梦都有属性相克、种族值、特性和进化方式，支持中文、英文、日文、繁体和拼音首字母查询。免费、免注册、打开就能查。",
  keywords: "宝可梦图鉴,口袋妖怪图鉴,精灵宝可梦,种族值,属性相克,招式表,特性大全,道具图鉴,性格表,皮卡丘,究极绿宝石,宝可梦查询",
  contactEmail: "contact@suilang.net",    // 联系 / 反馈邮箱（Cloudflare 邮件路由转发）
  legalEmail: "dmca@suilang.net",         // 版权投诉邮箱
  startYear: 2026,
  brandColor: "#1f7a63",

  /* ---------- 联动 ---------- */
  gbaSite: "https://gba.suilang.net",     // 兄弟站：玩 GBA 改版的地方（P2 互链用）

  /* ---------- 统计（填了才会加载） ---------- */
  analytics: {
    baidu: "",   // 百度统计 hm.js 的 hash
    cloudflareToken: ""                   // Cloudflare Web Analytics
  },

  /* ---------- 站长平台验证（留空则不输出对应 meta 标签） ---------- */
  verify: {
    google: "",                           // Google 已用 DNS TXT 验证网域资源的话不用填
    bing: "",
    baidu: "",           // baidu-site-verification
    bytedance: ""                         // 头条搜索站长平台
  },

  /* ---------- 广告位 ---------- */
  // 拿到广告联盟代码后：把 enabled 改成 true，再把代码片段贴进对应字段。
  // 没填之前页面不会加载任何外部脚本，页面上也不留空框。
  ads: {
    enabled: false,
    head: "",                             // 注入 <head>（例如 AdSense 的 loader）
    topBanner: "",                        // 列表页 / 首页顶部通栏
    inArticle: "",                        // 条目页正文中
    sideRail: ""                          // 宽屏侧边竖幅
  }
};
