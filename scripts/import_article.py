#!/usr/bin/env python3
"""photo-remix：从公众号文章导入新 prompt 进库。

1) 抓取:  import_article.py fetch <url> --out <dir>
   写 <dir>/article.txt（逐行正文，公众号会把一段 prompt 切成很多碎片行）和 meta.json
2) 入库:  import_article.py add <dir> --lines 15-57 --id 22 --slug my_style --title "标题"
          [--keep-newlines] [--needs-person] [--single-person-only] [--types group,food ...]
   按行号区间拼回 prompt（英文碎片之间自动补空格），写 prompts/<id>_<slug>.txt 并登记到 index.json
   --types 给出的类型会把新 id 追加到这些类型路由的末尾
"""
import argparse, json, pathlib, re, subprocess, sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def fetch(url, out):
    from bs4 import BeautifulSoup
    out.mkdir(parents=True, exist_ok=True)
    raw = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, url], capture_output=True).stdout
    s = BeautifulSoup(raw.decode("utf-8", "ignore"), "lxml")
    c = s.find(id="js_content")
    if not c:
        sys.exit("没找到正文 js_content（可能被风控/需要验证），换浏览器抓取")
    title = s.find(id="activity-name"); acct = s.find(id="js_name")
    meta = {"url": url, "title": title.get_text(strip=True) if title else "",
            "account": acct.get_text(strip=True) if acct else ""}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    lines = c.get_text("\n", strip=True).split("\n")
    (out / "article.txt").write_text("\n".join(lines))
    print(meta, "lines:", len(lines))
    for i, l in enumerate(lines, 1):
        if len(l) > 120:
            print(f"  可能是 prompt 的长行 {i}: {l[:40]}…")


def join(seg):
    out = seg[0]
    for s in seg[1:]:
        if (re.search(r"[A-Za-z]$", out) and re.match(r"[A-Za-z]", s)) or (out.endswith("No.") and s[:1].isdigit()):
            out += " " + s
        else:
            out += s
    return out.strip()


def add(a):
    d = pathlib.Path(a.dir)
    L = (d / "article.txt").read_text().split("\n")
    meta = json.loads((d / "meta.json").read_text())
    s, e = [int(x) for x in a.lines.split("-")]
    seg = L[s - 1:e]
    text = "\n".join(seg).strip() if a.keep_newlines else join(seg)
    f = SKILL / "prompts" / f"{a.id}_{a.slug}.txt"
    if f.exists():
        sys.exit(f"{f.name} 已存在")
    f.write_text(text)
    idx_f = SKILL / "prompts/index.json"
    idx = json.loads(idx_f.read_text())
    if any(p["id"] == a.id for p in idx["prompts"]):
        sys.exit(f"id {a.id} 已被占用")
    params = [p for p in ("location_cn", "location_en", "year") if "{{" + p + "}}" in text]
    idx["prompts"].append({"id": a.id, "file": f"prompts/{f.name}", "title": a.title,
                           "origin": f"{meta.get('account', '')}《{meta.get('title', '')}》 {meta.get('url', '')}",
                           "needs_person": a.needs_person, "single_person_only": a.single_person_only,
                           "params": params, "tested_score": "", "tested_note": "", "tested_on": ""})
    for t in (a.types.split(",") if a.types else []):
        idx["routes"][t].append(a.id)
    idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    print("added", f.name, len(text), "chars; params", params)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p1 = sp.add_parser("fetch"); p1.add_argument("url"); p1.add_argument("--out", required=True)
    p2 = sp.add_parser("add"); p2.add_argument("dir"); p2.add_argument("--lines", required=True)
    p2.add_argument("--id", required=True); p2.add_argument("--slug", required=True); p2.add_argument("--title", required=True)
    p2.add_argument("--keep-newlines", action="store_true"); p2.add_argument("--needs-person", action="store_true")
    p2.add_argument("--single-person-only", action="store_true"); p2.add_argument("--types")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.url, pathlib.Path(a.out).expanduser())
    else:
        add(a)


if __name__ == "__main__":
    main()
