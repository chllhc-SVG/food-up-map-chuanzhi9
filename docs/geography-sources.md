# 离线河流水系来源

坐标数组采用 WGS84（EPSG:4326），顺序为经度、纬度。浏览器仅加载本地 `geography.js`。线条宽度是制图符号，不代表河道实宽。店铺与水系使用不同来源，概化河线仅用于城市方位参考，不作过江、路程或店址判断。

## 武汉

[官方数据页](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-rivers-lake-centerlines/) · [官方数据 ZIP](https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_rivers_lake_centerlines.zip) · [公共领域条款](https://www.naturalearthdata.com/about/terms-of-use/)

Natural Earth 1:10,000,000 Rivers + Lake Centerlines v5.0.0。下载包 SHA-256 为 `ded71b01870855ccfe19b51f2ec14c9bb48fae23c0e9f3c11974d426433b5c38`。使用 长江（Yangtze，ne_id 1159113707）、汉江（Han，源中文名“汉水”，ne_id 1159115755）。裁切框西南 (113.25, 29.70)、东北 (115.40, 31.45)。对裁切结果做拓扑合并，按 0.0008° 容差简化。数据是小比例尺成果，高倍放大时不绘制，以免出现虚假细节。

## 福州

© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)。福建局部水系数据及其在 `geography.js` 中的改编以 [Open Data Commons Open Database License v1.0](https://opendatacommons.org/licenses/odbl/1-0/) 提供。可直接提取源代码中 `fuzhou` 字段的全部数组，不需要联网。

数据为 [Geofabrik 福建下载页](https://download.geofabrik.de/asia/china/fujian.html) 的 [2026-11-01 福建省快照](https://download.geofabrik.de/asia/china/fujian-261101-free.shp.zip) 中 `gis_osm_waterways_free_1` 图层，筛选 `fclass=river`，裁切框西南 (119.05, 25.86)、东北 (119.57, 26.23)。合并连通线段，在原坐标系内按 0.00017° 容差简化，输出保留五位小数，短于 0.002° 的独立片段未纳入。保留有数据的河段，没有推测连接缺口。北港亦称“白龙江”，名称参照[福州市志·主要江河](https://data.fjdsfzw.org.cn/upload/Annals/2011/%E7%A6%8F%E5%B7%9E%E5%B8%82%E5%BF%97%28%E7%AC%AC1%E5%86%8C%29/epub/ops/145.htm)。

| 源名称 | OSM way ID |
|---|---|
| 闽江 | 45169270, 436511909, 697287423, 1372209402, 1372209403 |
| 白龙江 | 437226610, 783379039, 783379040 |
| 乌龙江 | 436511910, 809650532 |
| 晋安河 | 209804035, 1375540278, 1375540279 |
| 白马河 | 442694353 |
