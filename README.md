# 美食UP主的榜单推荐——基于定位的个性化美食地图微工具

按城市选择探店 UP 主，从口味、出发地和地点证据找到值得回看的一期视频。武汉为「员外的觅食人生」，福州为「酷酷的珊文鱼」。推荐顺序由工具计算，作者的实际评价以原视频为准。

## 评审快速复现（10 分钟内）

可下载提交包里的《评审源码.zip》，也可克隆公开仓库以查看完整提交历史。

```console
git clone https://github.com/chllhc-SVG/food-up-map-chuanzhi9.git
cd food-up-map-chuanzhi9
```

准备 Python 3.10+ 和现代浏览器。解压作品源码或克隆完整仓库，在含 `server.py` 的目录打开终端。Windows 可直接双击 `启动.cmd`。macOS/Linux 可把下列命令中的 `python` 换为 `python3`。

```console
python --version
python tests/test_data.py
python server.py
```

用浏览器打开 <http://127.0.0.1:8794/>，默认是福州。首页应显示福州 115 个店铺或品牌条目、36 个坐标、293 条视频。切换武汉后应看到 326 处地点、359 条视频。按 Ctrl+C 退出服务。[福州直达](http://127.0.0.1:8794/?city=fuzhou) · [武汉直达](http://127.0.0.1:8794/?city=wuhan)

运行时依赖只有 Python 标准库和随包的 Leaflet 1.9.4。环境变量模板可留空，用户无需申请密钥。联网街道图和原视频为可选项。可选浏览器验收使用 Microsoft Edge 与 Playwright。若需执行，在测试环境运行 `python -m pip install -r requirements-browser.txt`，另一个终端保持服务运行。[运行依赖](requirements.txt) · [环境变量模板](.env.example) · [复现记录与实测条件](docs/复现验收.md)

## 评审材料入口

- [技术说明 PDF](competition/作品说明.pdf) · [省赛材料清单与演示时间轴](competition/材料清单.md)
- 项目由一名选手与 Codex 协作开发。9 月武汉原型贡献已有数据，本届从双城需求开始新建仓库。使用 `git log --reverse --oneline` 查看实际开发顺序。[原始需求和沿用范围](BRIEF.md)
- 三项核心迭代可按“原话、方案、反馈、修改、验证”的顺序回查。[迭代索引](docs/prompts/迭代索引.md) · [对话历史导出](docs/prompts/核心对话导出.json)

## 三分钟体验

1. 选择武汉，搜索「三怪牛肉炒饭」，查看同一店铺关联的两条原视频。清空搜索，使用设备定位或选择本城出发点，再看「为我推荐」中每个地点的入选理由。
2. 切换福州，搜索「裕莲茶楼」。对照两期原片，查看哪一期能够核实至东百中心 C 馆。视频目录保留作者异地投稿；只有本城已经核对的地点出现在店铺列表。片区参考点和待核地点不能当作确定门店入口。
3. 展开「核对一条探店视频」，输入 `BV1v4VpzgE5h`。程序从福州作者快照检查来源，显示已关联的店铺。提交没有地址证据的新 BV 号时可保存为个人待核记录。线索与收藏保存在当前浏览器，不改变公共地图。

## 来源和复核

- 武汉视频目录更新于 2026-11-17，作者投稿页共 9 页、359 条，含一条合作视频。较 9 月 22 日新增的 17 条投稿可在视频目录查看，店址待核。326 处历史地点沿用 9 月 23 日的核对结果，其中 312 处有坐标。运行 `python scripts/import_wuhan.py "原项目/完整整理数据.json"` 将历史资料与 `docs/wuhan-catalog-update.json` 合并重建；有完整 Git 历史时也可运行 `python scripts/import_wuhan.py --from-git --output .local/wuhan.json` 离线重建当前版。增加 `--historical --output 历史快照.json` 可单独导出旧版。[武汉作者投稿页](https://space.bilibili.com/9433848/upload/video)
- 福州保留 2026-11-17 核对的 8 页作者投稿，共 293 个不同的 BV 号。三列原始目录在 `docs/fuzhou-catalog.json`。原视频关联与地点依据在 `docs/fuzhou-reviewed.json`，可运行 `python scripts/import_fuzhou.py docs/fuzhou-reviewed.json --catalog docs/fuzhou-catalog.json --out data/fuzhou.json` 复现。视频目录完整度和地点核实进度独立展示。
- 排序依据与坐标含义可在页面的「数据说明」中查看。历史探店记录不提供实时营业状态；显示的公里数是直线距离。经主动选择载入的街道底图及视频原站须联网。打开街道底图后，第三方瓦片服务可通过可见范围推知正在查看的区域。设备定位默认不采集，不写入项目服务或浏览器存储。
- 上游作者保留视频与文本权益。此工具保留目录元数据、出处和必要的地点事实。Leaflet 许可证随代码提供，地图及点位数据的对外使用遵循各自来源的条件。

## 工程与范围

`index.html`、`app.js`、`styles.css` 提供双城筛选、推荐及地图。`note.js` 按原视频和已知店名核对用户输入，允许保留待核结果。匹配和排序在浏览器本地计算。运行时没有调用生成式模型。开发过程使用 AI 辅助，见 `BRIEF.md` 和 `docs/开发记录.md`。Python 服务仅监听本机并提供白名单文件。

从项目目录运行 `python tests/test_data.py` 可离线校验数据，含用随包证据重建福州快照。可选的界面验收需要 Playwright、已安装的 Microsoft Edge 和正在运行的本机服务。`python tests/check_locations.py` 覆盖手选起点、坐标精度、拒绝设备定位和跨城收藏；`python tests/check_notes.py` 覆盖原片归属、保存复核记录与福州直达入口。
