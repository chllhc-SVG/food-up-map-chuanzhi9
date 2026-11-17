# 福州数据复核与重建

2026-11-17 在「酷酷的珊文鱼」的投稿页逐页核对出 293 个不同 BV，并逐条查看 293 个原视频页面的公开简介摘要。创作者既发福州探店，也发异地旅行、早餐和日常生活。[作者投稿页](https://space.bilibili.com/3493128128432841/upload/video)

| 本次快照 | 数量 | 口径 |
| --- | ---: | --- |
| 视频目录 | 293 | 所有投稿，按 BV 去重 |
| 人工索引记录 | 144 | 142 条写明店名、品牌或市集名，另外两条记录无店名或负面体验 |
| 关联到本地条目的投稿 | 115 | 一条视频探访多店仍只计一次 |
| 本地条目 | 115 | 含可识别的品牌与分店，按审核结果合并重复提及 |
| 店铺与视频的关联 | 123 | 每对“条目、BV”计一次 |
| 地图标记 | 36 | 32 个商户点、1 个同建筑地址参考、3 个片区参考 |
| 待定位条目 | 79 | 可回看原视频，坐标为空 |

### 从随项目提供的材料重建

1. 在作品根目录运行 `python scripts/import_fuzhou.py docs/fuzhou-reviewed.json`。默认读入 `docs/fuzhou-catalog.json` 的完整作者目录、`docs/fuzhou-mentions.json` 的人工视频索引、`docs/fuzhou-reviewed.json` 的分店和片区定位依据，以及 `docs/fuzhou-extra-coordinates.json`、`docs/fuzhou-more-coordinates.json` 的两批商户点位。输出为 `data/fuzhou.json`，重建过程无需联网。
2. 需要回看来源时，从发布数据的 `catalog[].url` 打开原视频。为刷新本地核对摘录，可在 PowerShell 运行 `./scripts/review_public_pages.ps1 -Limit 293`。它逐个读取清单里的公开视频网页，提取页面公开简介，写入 `.local/fz-pages` 并跳过已有缓存；遇到网页拒绝访问或无简介元数据时停止。缓存仅供本地复核。
3. 如需更新账号目录，先核对全部投稿页和总数，保存包含 `bvid`、`title`、`published` 的数组。调整审核文件中的日期、总数和已读简介数量。运行 `python scripts/import_fuzhou.py docs/fuzhou-reviewed.json --catalog 路径 --out 预览.json` 预览。应逐一检查新增的同名分店、负评、迁址或停业。快照的 `coverage` 可检查目录数、关联视频数与各档精度。

### 怎样判断视频与门店的关系

作者原简介常先给出店名，再写体验。一店多期按 BV 关联；多店同一期可以分别链接。142 条带名称的索引也保留明确的异地店、未核拍摄城市的连锁品牌及只写到夜市的投稿，目录中的 `indexStatus` 说明相应原因。仅见品牌时不会把视频挂到某个特定分店。福四中旁的饭团在原文没有名字，未据周边攻略推定为秋英饭团。

裕莲茶楼 2025 年 5 月首店开业数日后的视频对应到东百中心C馆。6 月另一条同品牌投稿只在目录中保留品牌提及。2024 年银河隧道的奶茶和甜品视频也未绑定到 2025 年提拉米苏流动摊的位置。[福州市鼓楼区政府](https://www.gl.gov.cn/xjwz/ztzl/fgfggyhyshjzt/jrbffw/202505/t20250514_5018504.htm) · [裕莲茶楼首期](https://www.bilibili.com/video/BV1v4VpzgE5h/) · [同品牌第二期](https://www.bilibili.com/video/BV1afNJzGE9z/)

10 个明确负面体验用 `negative` 标记，2 个有停业叙述的投稿用 `historical_closure` 标记；这 12 个视频均不用于店铺推荐关联。16 个好恶并存的投稿标作 `mixed`。仅在文本足以支持时添加简短点评。花潮一期的认可针对海鲜，对熟食评价较低；“玩的开心咖啡”获认可的是拿破仑；扁肉食堂获认可的是炸芋泥、荔枝田鸡。[花潮原视频](https://www.bilibili.com/video/BV1fodeBqEZX/) · [玩的开心咖啡](https://www.bilibili.com/video/BV1xHcHewETJ/) · [扁肉食堂](https://www.bilibili.com/video/BV1E7BZYwEQb/)

### 坐标从哪里来

狼群斯的视频简介点名门店。米其林福州指南核实了横江路融侨外滩壹号F栋1楼48号铺，携程与360地图也给出相同商户位置。地图库保留原坐标和坐标系，携程 GDCoord 和高德 GCJ-02 由武汉项目同一近似逆变换换算到 WGS84。百度地图的 28 个商户位置另保留公开 UID、BD09MC 原值和中间 BD09LL 坐标，再换算至 WGS84。商户平台标注点仍可能与现场入口有距离。[原视频](https://www.bilibili.com/video/BV1Z5chzTEVg/) · [米其林指南](https://guide.michelin.com/sg/zh_CN/fujian-province/fuzhou_1026814/restaurant/j-a-steak-house) · [携程商户](https://gs.ctrip.com/html5/you/foods/fooddetail/164/136245453.html) · [360地图商户](https://map.360.cn/shenghuo/detail?pguid=4e140aba4450a3cd&src=pc_shenbian) · [百度坐标转换依据](https://github.com/hujiulong/gcoord)

东百中心C馆使用同馆柜台作同建筑地址参考。不吃面包使用东街口地区的公开拍摄坐标，清口清汤面使用学校的片区参考点，银河隧道使用达明路与鼓西路路口参考点。所有片区点只表示所在街区。营业状态和摊位位置随时间变化。

2026-11-17 官方匿名投稿接口曾返回 -799，批次详情接口曾返回 HTTP 412。当日完整目录来自公开投稿网页，简介来自原视频网页。从这两次 API 错误不能推得账号投稿数。
