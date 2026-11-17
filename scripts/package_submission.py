"""Package the reviewed competition files alongside the exact, recoverable Git history."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "评审源码.zip"
HISTORY = "完整开发历史.bundle"
FINAL_ZIP = "传智杯AI创新应用挑战赛-美食UP主的榜单推荐.zip"
PRODUCT_VIDEO = "演示视频.mp4"
CONTEST_VIDEO = "赛事规定版（含AI协作）.mp4"


def run_git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, encoding="utf-8")


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def package(repository):
    delivery = ROOT / "参赛交付"
    delivery.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=delivery) as directory:
        stage = Path(directory)
        run_git("archive", "--format=zip", "--output=" + str(stage / SOURCE), "HEAD")
        run_git("bundle", "create", str(stage / HISTORY), "--branches", "--tags", "HEAD")
        run_git("bundle", "verify", str(stage / HISTORY))
        for name in ("作品说明.pdf", PRODUCT_VIDEO, CONTEST_VIDEO, "报名表作品简介.txt"):
            shutil.copy2(ROOT / "competition" / name, stage / name)
        if digest(stage / PRODUCT_VIDEO) == digest(stage / CONTEST_VIDEO):
            raise ValueError("两部视频内容相同，请复核产品演示和赛事规定版的文件。")
        commit = run_git("rev-parse", "HEAD").strip()
        access = repository or "仓库访问方式请与选手确认。离线复核可使用完整开发历史.bundle。"
        entry = stage / "评审入口.txt"
        entry.write_text(
            f"美食UP主的榜单推荐——基于定位的个性化美食地图微工具\n\n"
            f"参赛代码仓库\n{access}\n版本 {commit}\n\n"
            f"打开地图\n解压《{SOURCE}》，在有 Python 3.10+ 的电脑上双击「启动.cmd」，"
            "或运行 python server.py，访问 http://127.0.0.1:8794/ 。运行不需要密钥。\n\n"
            f"视频入口\n《{PRODUCT_VIDEO}》展示桌面端与手机端怎样查找附近美食、回看测评、"
            f"挑选旅行时顺路的店。《{CONTEST_VIDEO}》保留赛道要求的 AI 协作过程，供正式视频栏使用。\n\n"
            "技术文档\n《作品说明.pdf》解释排名、点位和开发取舍。"
            "源码根目录的 README.md 给出复现步骤。docs/prompts/ 含三项功能的原始对话、截图和提交对照。\n\n"
            f"离线查看历史\ngit clone \"{HISTORY}\" food-up-map\n"
            "git -C food-up-map log --reverse --oneline\n",
            encoding="utf-8-sig",
        )
        with ZipFile(stage / SOURCE) as archive:
            assert archive.testzip() is None
            assert {".env.example", "README.md", "requirements.txt", "docs/prompts/核心对话导出.json"} <= set(archive.namelist())
            video_counts = {city: len(json.loads(archive.read(f"data/{city}.json"))["catalog"]) for city in ("fuzhou", "wuhan")}
            assert video_counts == {"fuzhou": 293, "wuhan": 359}
        manifest = stage / "校验值SHA256.txt"
        files = sorted(stage.iterdir())
        manifest.write_text("".join(f"{digest(p)}  {p.name}\n" for p in files), encoding="utf-8")
        with ZipFile(stage / FINAL_ZIP, "w") as archive:
            for p in [*files, manifest]:
                compression = ZIP_STORED if p.suffix in {".mp4", ".pdf", ".zip", ".bundle"} else ZIP_DEFLATED
                archive.write(p, p.name, compress_type=compression)
        with ZipFile(stage / FINAL_ZIP) as archive:
            assert archive.testzip() is None
        for p in stage.iterdir():
            p.replace(delivery / p.name)
    return delivery / FINAL_ZIP


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", help="已经核实的 GitHub 或 Gitee 参赛仓库地址")
    print(package(parser.parse_args().repository))
