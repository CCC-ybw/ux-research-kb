#!/usr/bin/env python3
"""
build_bundle.py — 把仓库里所有 md/txt/html 文件打包成一个 JSON。

在 GitHub Actions 里运行（仓库已 checkout），遍历当前目录下所有支持的文件，
提取标题和纯文本，合并成 kb_bundle.json。

用法（在仓库根目录执行）:
    python scripts/build_bundle.py
"""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt", ".html", ".htm"}

# 跳过的目录/文件前缀
SKIP_PREFIXES = (".", "node_modules", "scripts", "__pycache__", "cache")

GITHUB_REPO = "CCC-ybw/ux-research-kb"
GITHUB_BLOB_BASE = f"https://github.com/{GITHUB_REPO}/blob/main/"


def extract_title(filename, content):
    """从内容前几行提取标题。"""
    for line in content.split("\n")[:10]:
        m = re.match(r"^#{1,3}\s+(.+)", line.strip())
        if m:
            return m.group(1).strip()
    m = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")


def strip_html(text):
    """简单去除 HTML 标签，保留文本。"""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_file(path):
    """读取文件，返回 (title, plain_text)。"""
    content = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()

    if ext in (".html", ".htm"):
        title = extract_title(path.name, content)
        text = strip_html(content)
    elif ext == ".md":
        title = extract_title(path.name, content)
        # 去掉 markdown 符号，保留纯文本用于检索
        text = re.sub(r"[#*`~\[\]()>]", "", content)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        title = path.name
        text = content

    return title, text.strip()


def main():
    root = Path(".")
    files = []

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        rel = str(p).replace("\\", "/")

        # 跳过隐藏目录、scripts 等
        parts = rel.split("/")
        if any(part.startswith(SKIP_PREFIXES) for part in parts):
            continue

        try:
            title, text = parse_file(p)
            files.append({
                "file": rel,
                "title": title,
                "content": text,
                "char_count": len(text),
                "github_url": GITHUB_BLOB_BASE + rel,
            })
        except Exception as e:
            print(f"  skip {rel}: {e}")

    tz = timezone(timedelta(hours=8))
    bundle = {
        "generated_at": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S CST"),
        "source_repo": GITHUB_REPO,
        "file_count": len(files),
        "total_chars": sum(f["char_count"] for f in files),
        "files": files,
    }

    out = Path("kb_bundle.json")
    out.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    print(f"OK: {len(files)} files, {bundle['total_chars']} chars -> {out}")
    for f in files:
        print(f"  - {f['file']} ({f['char_count']} chars)")


if __name__ == "__main__":
    main()
