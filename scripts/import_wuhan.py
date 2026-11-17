"""Extract public catalog metadata from the original Wuhan map's 完整整理数据.json.

Run: python scripts/import_wuhan.py "path/to/完整整理数据.json"
Reads an existing snapshot and never fetches Bilibili or map APIs.
"""

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PRECISIONS = ("poi", "address", "area", "pending")
UP_URL = "https://space.bilibili.com/9433848/upload/video"
CATALOG_UPDATE = Path(__file__).resolve().parents[1] / "docs" / "wuhan-catalog-update.json"


def video_info(record):
    bvid = record["bvid"]
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid):
        raise ValueError(f"Invalid BV identifier: {bvid!r}")
    return {
        "bvid": bvid,
        "title": record["title"].strip(),
        "url": f"https://www.bilibili.com/video/{bvid}/",
    }


def map_link(raw_link):
    parts = urlsplit(raw_link)
    if parts.scheme != "https" or parts.hostname not in {
        "www.amap.com", "uri.amap.com", "ditu.amap.com",
    }:
        raise ValueError("Unknown coordinate source in Wuhan snapshot")
    query = [(k, v) for k, v in parse_qsl(parts.query) if k in {"query", "keyword", "city"}]
    return urlunsplit(("https", parts.hostname, parts.path, urlencode(query), ""))


def extract(raw):
    if raw["source"].rstrip("/") != UP_URL or not raw["coordinateSystem"].startswith("WGS84"):
        raise ValueError("Expected the WGS84 Wuhan catalog of UP 9433848")
    catalog = []
    index = {}
    for record in raw["videos"]:
        info = video_info(record)
        if info["bvid"] in index:
            raise ValueError(f"Duplicate video {info['bvid']}")
        index[info["bvid"]] = info
        catalog.append({**info, "published": record["publishedAt"]})
    places = []
    linked = set()
    for old in raw["places"]:
        precision = old["precision"]
        lat, lon = old["lat"], old["lng"]
        if precision not in PRECISIONS:
            raise ValueError(f"Unknown location precision: {precision}")
        if precision == "pending":
            if lat is not None or lon is not None:
                raise ValueError("Pending location cannot have coordinates")
        elif not (29.7 < lat < 31.5 and 113.5 < lon < 115.2):
            raise ValueError(f"Outside Wuhan snapshot bounds: {(lat, lon)}")
        videos = [index[v["bvid"]] for v in old["videos"]]
        if not videos:
            raise ValueError(f"Location has no video source: {old['name']}")
        linked.update(v["bvid"] for v in videos)
        places.append({
            "name": old["name"], "address": old["address"], "district": old["district"] or "",
            "lat": lat, "lon": lon, "precision": precision, "videos": videos,
            "source": map_link(old["geo_source"]) if old.get("geo_source") else videos[0]["url"],
            "note": old.get("note", "").strip(),
        })
    counts = Counter(place["precision"] for place in places)
    unlinked_reasons = Counter(v["reasonCode"] for v in raw["otherVideos"])
    if set(index) - linked != {v["bvid"] for v in raw["otherVideos"]}:
        raise ValueError("Unlinked-video list does not reconcile with catalog and places")
    return {
        "region": "武汉", "up": {"name": "员外的觅食人生", "mid": 9433848, "url": UP_URL},
        "catalog": catalog, "places": places,
        "coverage": {
            "catalogVideos": len(catalog), "linkedVideos": len(linked),
            "unlinkedVideos": len(catalog) - len(linked), "places": len(places),
            "mappedPlaces": len(places) - counts["pending"],
            "precisionCounts": {key: counts[key] for key in PRECISIONS},
            "unlinkedReasons": dict(sorted(unlinked_reasons.items())),
            "snapshotDate": raw["catalogSnapshot"], "reviewedOn": raw["updated"],
            "coordinateSystem": "WGS84",
            "coordinateNote": "高德 GCJ-02 地理编码经近似逆变换；保留旧快照精度。门牌与区域参考点不保证是店铺入口。",
            "statusNote": "历史视频目录及地点快照，门店当前营业状态未逐店核实。",
        },
    }


def update_catalog(result, update):
    coverage = result["coverage"]
    if update["source"] != UP_URL or update["previousSnapshotDate"] != coverage["snapshotDate"]:
        raise ValueError("武汉投稿增量与历史快照不匹配")
    base_date = date.fromisoformat(coverage["snapshotDate"])
    as_of = date.fromisoformat(update["snapshotDate"])
    catalog = result["catalog"]
    ids = {v["bvid"] for v in catalog}
    for row in update["added"]:
        info = video_info(row)
        published = date.fromisoformat(row["published"])
        if info["bvid"] in ids or not info["title"] or not base_date < published <= as_of:
            raise ValueError(f"新增投稿 BV、标题或日期不正确：{row['bvid']}")
        catalog.append({**info, "published": row["published"]})
        ids.add(info["bvid"])

    if len(catalog) != update["reportedTotal"] or update["coPublishedBvid"] not in ids:
        raise ValueError("武汉投稿总数或合作稿与核实结果不一致")
    catalog.sort(key=lambda row: row["published"], reverse=True)
    coverage["snapshotDate"] = update["snapshotDate"]
    coverage["catalogVideos"] = len(catalog)
    coverage["reportedTotal"] = update["reportedTotal"]
    coverage["unlinkedVideos"] = len(catalog) - coverage["linkedVideos"]
    coverage["unlinkedReasons"]["awaiting_place_review"] = len(update["added"])
    coverage["statusNote"] = (
        f"视频目录含合作稿。地点沿用 {coverage['reviewedOn']} 核对结果，"
        f"{len(update['added'])} 条新增视频的店址待核。门店当前营业状态未逐店核实。"
    )


def encode(result):
    # One row per repeated record keeps the snapshot both compact and diffable.
    dump = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    fields = []
    for key, value in result.items():
        payload = "[\n" + ",\n".join(map(dump, value)) + "\n]" if isinstance(value, list) else dump(value)
        fields.append(dump(key) + ":" + payload)
    return ("{\n" + ",\n".join(fields) + "\n}\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", help="武汉原型导出的完整整理数据.json")
    parser.add_argument("--from-git", action="store_true", help="从本仓库最初导入的武汉快照离线重建")
    parser.add_argument("--historical", action="store_true", help="仅重建 2026-09-22 的历史快照")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data" / "wuhan.json")
    args = parser.parse_args()
    if bool(args.source) == args.from_git:
        parser.error("请选择一个输入：原始 JSON 路径，或 --from-git")
    if args.from_git:
        repo = Path(__file__).resolve().parents[1]
        try:
            raw = subprocess.check_output(["git", "-C", str(repo), "show", "1c5d780:data/wuhan.json"],
                                          stderr=subprocess.DEVNULL)
        except (FileNotFoundError, subprocess.CalledProcessError):
            parser.error("需要含完整开发历史的 Git 仓库。可用随包的 Git bundle 克隆，或使用原始 JSON 路径。")
        result = json.loads(raw)
    else:
        result = extract(json.loads(args.source.read_text(encoding="utf-8-sig")))
    if not args.historical:
        update_catalog(result, json.loads(CATALOG_UPDATE.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encode(result))
    print(json.dumps(result["coverage"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
