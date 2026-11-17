# 福州条目如何复核

本城已核地点及逐条来源保存在同目录的 `fuzhou-reviewed.json` 中。在项目根目录运行 `python scripts/import_fuzhou.py docs/fuzhou-reviewed.json` 会读取 `docs/fuzhou-catalog.json` 的完整目录、`docs/fuzhou-mentions.json` 的人工门店索引，并重建发布数据。更新公开投稿页快照时，可加 `--catalog` 指定逐页记录的目录数组。快照中分别统计投稿数、已识别店铺数及能在地图显示的数量。

作者是[酷酷的珊文鱼](https://space.bilibili.com/3493128128432841/upload/video)，MID 为 `3493128128432841`。2026-11-17 在该账号主页看到 293 个投稿，这个数字也包括异地或与单一门店无关的内容。项目的 `catalog` 只收录可核对 BV 号与作者归属的投稿，`places` 只收录能从来源识别福州地点的记录。

例如，2026-02-14 的千元牛排视频简介点名「狼群斯」。米其林福州指南核实了横江路融侨外滩壹号F栋1楼48号铺，携程与360地图也把福州门店标在同一处。公开坐标能支持门店点，实际入口仍需到场辨认。[原视频](https://www.bilibili.com/video/BV1Z5chzTEVg/) · [米其林指南](https://guide.michelin.com/sg/zh_CN/fujian-province/fuzhou_1026814/restaurant/j-a-steak-house) · [携程门店](https://gs.ctrip.com/html5/you/foods/fooddetail/164/136245453.html) · [360地图门店](https://map.360.cn/shenghuo/detail?pguid=4e140aba4450a3cd&src=pc_shenbian)

来自携程 GDCoord 或高德的 GCJ-02 原坐标以 `originalCoordinate` 保存，并沿用武汉项目的五步迭代近似逆变换生成发布的 WGS84 坐标。东百中心C馆使用馆内另一柜位作同建筑地址参考。街区或学校的参考点沿用 `area` 精度。公开信息所载的地址或原视频体验均以资料日期为准。

完整目录保留异地和停业投稿。明确表达不满意的八个标题标为 `negative`，提到停业或闭店的两个历史标题标为 `historical_closure`。这些视频均未纳入门店推荐。没有明确表态的标题不推定为好评。饭团线索未能从原投稿文字核实名为秋英，仍只收录在视频目录。

维护时可直接从公开主页核对投稿与原视频。若官方公开作品详情服务可访问，`python scripts/fetch_fuzhou_video_details.py --out 本地核查.jsonl BV号...` 会逐条比对作者 MID，低速保留临时核查材料。该命令不需登录或 Cookie，遇到接口限制会停止。请将原始简介缓存放在发布目录之外。2026-11-17 的公开投稿目录接口返回 -799，批次作品详情请求返回 HTTP 412；不要把失败响应解释为零投稿。

编制经人工审核的后续快照时，`python scripts/import_fuzhou.py reviewed.json --out preview.json` 可生成同结构文件。输入需含 `mid`、`asOf`（YYYY-MM-DD）、`upName`、`reportedTotal`、`videos`（含 bvid、title、published）与 `places`（含 name、source、bvids）。已核实坐标需提供 `lat`、`lon`、`crs: "WGS84"`、`precision` 和 `coordinateSource`。待定位条目将坐标留空。只有逐页核查完毕且去重总数与公开计数一致时，才设置 `allPagesReviewed: true`；这表示目录已核齐，不表示所有视频都含店名或已定位。
