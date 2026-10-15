#!/bin/bash
# ============================================
#  把网站的最新版本传到网上（Cloudflare）
#
#  线上地址： https://pokedex.suilang.net
#
#  什么时候用：改过网站里的东西之后，双击一次这个文件，
#  等它跑完，线上就是最新的了。
#
#  第一次运行会打开浏览器让你登录 Cloudflare，点一下允许就行。
# ============================================
cd "$(dirname "$0")/.." || exit 1

echo "=========================================="
echo "  究极宝可梦图鉴 —— 上传最新版"
echo "=========================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "这台电脑还没有 python3，没法生成页面。"
  read -r -p "按回车键关闭…"
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "这台电脑还没有 Node.js，没法读取配置和上传。"
  echo "到 https://nodejs.org/zh-cn 下载安装（一路点下一步），装完再双击这个文件。"
  read -r -p "按回车键关闭…"
  exit 1
fi

# 上游数据只在第一次需要下载（约 130MB），之后都在 build/_raw/ 缓存着
if [ ! -f build/_raw/pokemon.csv ]; then
  echo "第一次运行，正在下载上游数据（大约一百多兆，要等一会儿）……"
  python3 build/取数据.py || { echo; echo "下载数据出错，先看看上面的提示。"; read -r -p "按回车键关闭…"; exit 1; }
  echo
fi

if [ ! -d img/pokemon ] || [ -z "$(ls -A img/pokemon 2>/dev/null)" ]; then
  echo "正在处理图片（第一次比较慢）……"
  python3 build/图片.py || { echo; echo "处理图片出错，先看看上面的提示。"; read -r -p "按回车键关闭…"; exit 1; }
  echo
fi

# 官方游戏文本只在第一次（或补全文件丢了）需要下载，平时读的是仓库里那份
if [ ! -f build/人工数据/官方文本补全.json ]; then
  echo "正在取官方中文说明（几兆而已）……"
  python3 build/取官方文本.py || { echo; echo "取官方文本出错，先看看上面的提示。"; read -r -p "按回车键关闭…"; exit 1; }
  echo
fi

echo "正在整理数据……"
python3 build/生成数据.py || { echo; echo "整理数据出错，先看看上面的提示。"; read -r -p "按回车键关闭…"; exit 1; }
echo
echo "正在生成页面（三千多个）……"
python3 build/生成页面.py || { echo; echo "生成页面出错，先看看上面的提示。"; read -r -p "按回车键关闭…"; exit 1; }
echo
echo "正在自测……"
python3 build/自测.py > /tmp/pokedex_自测.txt 2>&1
tail -3 /tmp/pokedex_自测.txt
echo

# 你的网络连不上 Cloudflare / GitHub 时，在上面加一行
#   export HTTPS_PROXY=http://你的代理地址:端口
# 即可，其余不用改。

if ! npx --yes wrangler@latest whoami >/dev/null 2>&1; then
  echo "第一次使用，需要先登录 Cloudflare。马上会打开浏览器，点「允许 / Allow」就好。"
  echo
  npx --yes wrangler@latest login || { echo; echo "登录没成功，再试一次这个文件。"; read -r -p "按回车键关闭…"; exit 1; }
  echo
fi

echo "正在上传……"
echo
npx --yes wrangler@latest deploy
status=$?
echo
if [ "$status" -eq 0 ]; then
  echo "上传完成 ✔"
  echo "线上地址：https://pokedex.suilang.net"
  echo "（如果还看到旧内容，按 ⌘ + Shift + R 强制刷新一下）"
else
  echo "上传失败（错误码 $status）。把窗口里的红字截图发我，我来处理。"
fi
echo
read -r -p "按回车键关闭…"
