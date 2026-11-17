"""Build the Fuzhou region from a reviewed public catalog export (no network)."""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re


MID = "3493128128432841"
HOME = f"https://space.bilibili.com/{MID}/upload/video"
BV = re.compile(r"BV[1-9A-HJ-NP-Za-km-z]{10}\Z")
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "fuzhou.json"
DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "docs" / "fuzhou-catalog.json"
DEFAULT_MENTIONS = Path(__file__).resolve().parents[1] / "docs" / "fuzhou-mentions.json"
DEFAULT_COORDINATE_FILES = [
    DEFAULT_MENTIONS.with_name("fuzhou-extra-coordinates.json"),
    DEFAULT_MENTIONS.with_name("fuzhou-more-coordinates.json"),
]


def add_reviewed_mentions(evidence, mentions):
    catalog = {v["bvid"]: v for v in evidence["videos"]}
    places = evidence["places"]
    by_name = {p["name"].casefold(): p for p in places}
    closures = {
        name.casefold() for entry in mentions.values()
        if entry.get("stance") == "historical_closure" for name in entry["places"]
    }
    for bvid, details in mentions.items():
        if bvid not in catalog:
            raise ValueError(f"人工视频索引引用了当前目录中不存在的 BV：{bvid}")
        if details.get("stance"):
            evidence.setdefault("reviewedStances", {})[bvid] = details["stance"]
        catalog[bvid]["namedPlaces"] = details["places"]
        if details.get("reviewNote"):
            catalog[bvid]["reviewNote"] = details["reviewNote"]
        if details.get("catalogOnly"):
            catalog[bvid]["indexStatus"] = details["catalogOnly"]
            continue
        if evidence.get("reviewedStances", {}).get(bvid) in {"negative", "historical_closure"}:
            continue
        for name in details["places"]:
            key = name.casefold()
            if key in closures or name in details.get("unresolvedNames", []):
                continue
            if key not in by_name:
                place = {
                    "name": name, "bvids": [], "precision": "pending",
                    "source": f"https://www.bilibili.com/video/{bvid}/",
                    "note": (details.get("reviewNote", "") + " 原视频提到此店，具体分店或门牌仍待核对。").strip(),
                }
                by_name[key] = place
                places.append(place)
            by_name[key]["bvids"].append(bvid)


def add_reviewed_coordinates(evidence, rows):
    by_name = {place["name"].casefold(): place for place in evidence["places"]}
    for row in rows:
        key = row["name"].casefold()
        existing = by_name.get(key)
        if existing is None:
            evidence["places"].append(row)
            by_name[key] = row
        else:
            refs = list(dict.fromkeys(existing["bvids"] + row["bvids"]))
            if existing["precision"] != "pending":
                raise ValueError(f"同店已有另一位置，请先人工合并：{row['name']}")
            existing.update(row)
            existing["bvids"] = refs


def build(evidence):
    if str(evidence["mid"]) != MID:
        raise ValueError("上传账号与福州项目指定的 MID 不一致")
    snap = date.fromisoformat(evidence["asOf"]).isoformat()
    videos = {}
    stances = evidence.get("reviewedStances", {})
    for item in evidence["videos"]:
        bvid = item["bvid"]
        if not BV.fullmatch(bvid) or not item["title"].strip() or bvid in videos:
            raise ValueError(f"视频 BV、标题或唯一性有误：{bvid}")
        published = item.get("published") or None
        if type(published) is int:
            published = datetime.fromtimestamp(published, timezone(timedelta(hours=8))).date().isoformat()
        elif published:
            date.fromisoformat(published[:10])
        videos[bvid] = {
            "bvid": bvid, "title": item["title"].strip(),
            "url": f"https://www.bilibili.com/video/{bvid}/", "published": published,
        }
        if item.get("source"):
            videos[bvid]["source"] = item["source"]
        if bvid in stances:
            videos[bvid]["stance"] = stances[bvid]
        if item.get("namedPlaces"):
            videos[bvid]["namedPlaces"] = item["namedPlaces"]
        if item.get("reviewNote"):
            videos[bvid]["reviewNote"] = item["reviewNote"]
        if item.get("indexStatus"):
            videos[bvid]["indexStatus"] = item["indexStatus"]

    places = []
    for row in evidence.get("places", []):
        refs = [videos[bvid] for bvid in dict.fromkeys(row["bvids"])]
        if not refs or not row["name"].strip() or not row["source"].startswith("https://"):
            raise ValueError("地点缺少名称、原视频或公开出处")
        lat, lon = row.get("lat"), row.get("lon")
        precision = row.get("precision", "pending")
        if precision not in {"poi", "address", "area", "pending"}:
            raise ValueError("未知的坐标精度")
        if precision == "pending":
            if lat is not None or lon is not None:
                raise ValueError("待定位记录不可带有坐标")
        elif (lat is None or lon is None or not (25.1 <= lat <= 26.7 and 118.3 <= lon <= 120.6)
              or row.get("crs") != "WGS84" or not row.get("coordinateSource")):
            raise ValueError("已定位记录须提供福州范围内 WGS84 坐标及来源")
        place = {
            "name": row["name"].strip(), "address": row.get("address") or "",
            "district": row.get("district") or "", "lat": lat, "lon": lon,
            "precision": precision, "videos": [
                {k: v[k] for k in ("bvid", "title", "url", "stance", "reviewNote") if k in v} for v in refs
            ],
            "source": row["source"], "note": row.get("note", ""),
        }
        for name in ("addressSource", "coordinateSource", "coordinateCrosscheck", "originalCoordinate",
                     "derivedGeographicCoordinate", "conversionSource", "stance"):
            if row.get(name):
                place[name] = row[name]
        places.append(place)

    reported = evidence.get("reportedTotal")
    if reported is not None and (type(reported) is not int or reported < len(videos)):
        raise ValueError("目录计数大于已核实原始总数")
    complete = bool(evidence.get("allPagesReviewed")) and reported is not None and reported == len(videos)
    description_count = evidence.get("descriptionReviewedCount")
    if description_count is not None and not 0 <= description_count <= len(videos):
        raise ValueError("简介复核数量须在当前目录计数内")
    precision_counts = {
        key: sum(place["precision"] == key for place in places) for key in ("poi", "address", "area", "pending")
    }
    return {
        "region": "福州", "up": {"name": evidence.get("upName"), "mid": MID, "url": HOME},
        "catalog": list(videos.values()), "places": places,
        "coverage": {
            "asOf": snap, "status": "complete_catalog" if complete else ("partial_catalog" if videos else "awaiting_public_catalog"),
            "catalogComplete": complete, "reportedTotal": reported, "catalogCount": len(videos),
            "placeCount": len(places), "mappedCount": sum(row["lat"] is not None for row in places),
            "descriptionReviewedCount": description_count,
            "linkedVideoCount": len({v["bvid"] for place in places for v in place["videos"]}),
            "precisionCounts": precision_counts,
            "source": HOME, "note": evidence.get("note", ""),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewed_json", type=Path)
    parser.add_argument("--catalog", type=Path, help="由指定账号公开投稿页逐页核对的目录 JSON 数组")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mentions", type=Path, default=DEFAULT_MENTIONS)
    parser.add_argument("--coordinates", nargs="+", type=Path, default=DEFAULT_COORDINATE_FILES)
    args = parser.parse_args()
    evidence = json.loads(args.reviewed_json.read_text(encoding="utf-8-sig"))
    catalog_path = args.catalog or DEFAULT_CATALOG
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    if isinstance(catalog, dict) and str(catalog["up"]["mid"]) != MID:
        raise ValueError("已有地区快照并非指定福州作者")
    rows = catalog["catalog"] if isinstance(catalog, dict) else catalog
    indexed = {r["bvid"] for r in rows}
    evidence["allPagesReviewed"] = len(indexed) == evidence.get("reportedTotal") and len(rows) == len(indexed)
    missing = [r for r in evidence["videos"] if r["bvid"] not in indexed]
    if evidence["allPagesReviewed"] and missing:
        raise ValueError("完整目录缺少已有核实视频，请人工复核")
    evidence["videos"] = rows + missing
    for coordinate_file in args.coordinates:
        add_reviewed_coordinates(evidence, json.loads(coordinate_file.read_text(encoding="utf-8-sig")))
    add_reviewed_mentions(evidence, json.loads(args.mentions.read_text(encoding="utf-8-sig")))
    output = build(evidence)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
