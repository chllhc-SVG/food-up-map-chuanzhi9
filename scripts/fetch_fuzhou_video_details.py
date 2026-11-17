"""Review public video details for known catalog IDs. No credentials or catalog scraping."""

import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import time
from urllib.request import urlopen


def collect(ids, path):
    # The local JSONL is a review cache. Do not put full video descriptions in the distributed dataset.
    existing = set()
    if path.exists():
        existing = {json.loads(s)["bvid"] for s in path.read_text(encoding="utf-8").splitlines() if s}
    with path.open("a", encoding="utf-8") as out:
        for key in dict.fromkeys(ids):
            if key in existing:
                continue
            if not re.fullmatch(r"BV[0-9A-Za-z]{10}", key):
                raise ValueError(f"无效的 BV：{key}")
            url = "https://api.bilibili.com/x/web-interface/view?bvid=" + key
            with urlopen(url, timeout=15) as response:
                payload = json.load(response)
            if payload["code"] != 0:
                raise RuntimeError(f"{key} 返回 {payload['code']}，停止，请稍后人工核查。")
            data = payload["data"]
            if data["bvid"] != key or str(data["owner"]["mid"]) != "3493128128432841":
                raise ValueError(f"视频归属不一致：{key}")
            row = {
                "bvid": key, "title": data["title"], "mid": str(data["owner"]["mid"]),
                "upName": data["owner"]["name"], "desc": data.get("desc", ""),
                "published": datetime.fromtimestamp(data["pubdate"], timezone(timedelta(hours=8))).date().isoformat(),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(1.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="本地核验用 JSONL 缓存")
    parser.add_argument("bvid", nargs="+")
    args = parser.parse_args()
    collect(args.bvid, args.out)
