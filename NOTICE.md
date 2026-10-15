# NOTICE

## MIT 许可覆盖什么

`LICENSE` 里的 MIT 只覆盖**代码**，也就是本仓库中的：

- `build/` 下的生成脚本
- `assets/` 下的样式与前端脚本
- `scripts/` 下的 `.command`
- `wrangler.jsonc` / `_headers` / `_redirects` / `.assetsignore`
- `build/人工数据/` 下手工维护的别名与属性中文名

## 哪些东西不在授权范围内

以下内容**没有**被授权，本仓库也**不包含**它们。它们由 `build/取数据.py`
在运行时从上游下载，请自行遵守各上游的条款。

| 素材 | 来源 | 授权情况 |
| --- | --- | --- |
| 表格数据、名称、种族值、进化链、官方说明 | [PokeAPI/pokeapi](https://github.com/PokeAPI/pokeapi) | BSD-3-Clause（其许可写明「宝可梦及角色名称是任天堂的商标」） |
| 精灵图、道具图标 | [PokeAPI/sprites](https://github.com/PokeAPI/sprites) | **无许可文件**，图片自游戏提取 |
| 拼音 | [mozillazg/pinyin-data](https://github.com/mozillazg/pinyin-data) | MIT |

精灵图那一行是本仓库**不打包图片**的直接原因。

使用 PokeAPI 的数据时，请遵守它的 BSD-3-Clause 许可：保留版权声明与免责条款，
并且不要用「PokéAPI」的名字为其背书。

## 商标与免责声明

宝可梦（Pokémon）及相关角色名称、商品名称是**任天堂**的商标。
本项目与任天堂、Creatures、GAME FREAK **没有任何**从属、赞助或授权关系。

本项目为无关联的非官方工具：

- 不提供、不分发任何 ROM、游戏文件、密钥或破解相关内容
- 不用于任何商业转售用途
- 商标与美术作品的知识产权归各自权利人所有

## 数据准确性

站内数据以 PokeAPI 与官方游戏文本为准，不自行翻译、不编造。
官方没有中文说明的条目会明确标注「暂无官方中文说明」，而不是自行补写。

如果你发现某条数据有误，欢迎提 issue 指正。