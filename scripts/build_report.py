#!/usr/bin/env python3
"""photo-remix：生成自包含的 report.html（图片内嵌，可离线打开、单张一键下载、全部打包下载）。

用法: build_report.py --run <run_dir> [--title 标题]
读:  plan.json、photos/<key>/{source.jpg, meta.json, notes.json, outputs/*.png, outputs/*.recaption.txt}
     notes.json（Claude 看图后写）: {"<id>": {"score": "★★★★☆", "note": "..."}, "<id>_<后缀>": {...变体...}}
"""
import argparse, base64, html, io, json, pathlib, datetime
from PIL import Image

SKILL = pathlib.Path(__file__).resolve().parent.parent


def data_url(path, max_side=None, quality=90):
    """PNG 有透明就保留 PNG，否则转高质量 JPEG 以控制体积。返回 (data_url, 扩展名)"""
    im = Image.open(path)
    if max_side:
        im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    has_alpha = im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255
    if has_alpha:
        im.save(buf, "PNG", optimize=True); mime, ext = "image/png", "png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=quality); mime, ext = "image/jpeg", "jpg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode(), ext


def esc(s):
    return html.escape(str(s or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--title", default="照片 AI 二创结果")
    a = ap.parse_args()
    run = pathlib.Path(a.run).expanduser()
    idx = json.loads((SKILL / "prompts/index.json").read_text())
    pmeta = {p["id"]: p for p in idx["prompts"]}
    plan = json.loads((run / "plan.json").read_text())
    sections, total, done = [], 0, 0
    for ph in plan["photos"]:
        d = run / "photos" / ph["key"]
        meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
        notes = json.loads((d / "notes.json").read_text()) if (d / "notes.json").exists() else {}
        stem = pathlib.Path(meta.get("original", ph["key"])).stem[:40]
        src_url, _ = data_url(d / "source.jpg", max_side=1400, quality=85)
        cards = []
        for pid in ph.get("selected", []):
            total += 1
            m = pmeta[pid]
            outs = sorted(d.glob(f"outputs/{pid}.png")) + sorted(d.glob(f"outputs/{pid}_*.png"))
            if not outs:
                cards.append(f'<article class="card miss"><div class="ph">未生成</div><h3>{esc(pid)} · {esc(m["title"])}</h3></article>')
                continue
            done += 1
            for o in outs:
                variant = o.stem[len(pid):].lstrip("_")
                n = notes.get(o.stem, notes.get(pid, {})) if variant else notes.get(pid, {})
                url, ext = data_url(o)
                fname = f"{stem}_{o.stem}_{m['title']}.{ext}".replace("/", "-").replace(" ", "")
                rc = o.with_suffix(".recaption.txt")
                rc_html = f'<p class="rc">recaption：{esc(rc.read_text())}</p>' if rc.exists() and not variant else ""
                label = f'<span class="tag">{esc(n.get("label", variant))}</span>' if variant else ""
                cards.append(f'''<article class="card">
<img src="{url}" alt="{esc(m['title'])}" data-name="{esc(fname)}" onclick="zoom(this)">
<div class="meta"><h3>{esc(pid)} · {esc(m['title'])} {label}</h3><span class="score">{esc(n.get('score',''))}</span></div>
<p class="note">{esc(n.get('note',''))}</p>{rc_html}
<div class="btns"><button onclick="dl(this)">⬇ 下载</button>
<details><summary>prompt</summary><pre>{esc((SKILL / m['file']).read_text())}</pre></details></div>
</article>''')
        skipped = "；".join(f"{k} {pmeta[k]['title']}（{v}）" for k, v in ph.get("skipped", {}).items())
        sections.append(f'''<section class="photo">
<div class="head"><img class="src" src="{src_url}" data-name="{esc(stem)}_原图.jpg" onclick="zoom(this)">
<div><h2>{esc(stem)}</h2>
<p>分类：<b>{esc(idx['types'].get(ph['type'], ph['type']))}</b> · 人数 {esc(ph.get('persons', '?'))}
{(' · 修复：' + esc(' '.join(ph.get('repairs', [])))) if ph.get('repairs') else ''}</p>
<p class="mut">{esc(ph.get('reason', ''))}</p>
{f'<p class="mut">跳过：{esc(skipped)}</p>' if skipped else ''}</div></div>
<div class="grid">{''.join(cards)}</div></section>''')
    today = datetime.date.today().isoformat()
    page = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(a.title)}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<style>
:root{{--bg:#f6f4ef;--card:#fff;--fg:#222;--mut:#777;--acc:#d9603b;--bd:#e5e1d8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16161a;--card:#202026;--fg:#eee;--mut:#999;--bd:#34343c}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"PingFang SC",sans-serif}}
main{{max-width:1200px;margin:auto;padding:24px 16px}}
.top{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:20px}}
h1{{font-size:24px;margin:0}} .mut{{color:var(--mut);font-size:13px;margin:2px 0}}
button{{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:6px 14px;font-size:14px;cursor:pointer}}
button.big{{padding:10px 18px;font-size:15px}}
.photo{{margin-bottom:36px}} .head{{display:flex;gap:16px;align-items:flex-start;margin-bottom:14px}}
.head .src{{width:140px;border-radius:8px;cursor:zoom-in}} h2{{font-size:19px;margin:0 0 4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.card{{background:var(--card);border:1px solid var(--bd);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}}
.card img{{width:100%;display:block;cursor:zoom-in;background:repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 50%/16px 16px}}
.meta{{display:flex;justify-content:space-between;gap:8px;padding:10px 12px 0}} h3{{font-size:15px;margin:0}}
.score{{color:var(--acc);white-space:nowrap}} .tag{{background:var(--acc);color:#fff;border-radius:4px;font-size:11px;padding:1px 6px}}
.note,.rc{{padding:0 12px;margin:6px 0;font-size:13px}} .rc{{color:var(--mut)}}
.btns{{padding:8px 12px 12px;margin-top:auto}} details{{margin-top:6px}} summary{{cursor:pointer;color:var(--mut);font-size:13px}}
pre{{white-space:pre-wrap;font-size:12px;color:var(--mut);max-height:240px;overflow:auto}}
.miss .ph{{padding:80px 0;text-align:center;color:var(--mut)}} .miss h3{{padding:10px 12px}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;align-items:center;justify-content:center;z-index:9;flex-direction:column;gap:12px}}
#lb img{{max-width:94vw;max-height:84vh}} #lb.on{{display:flex}}
@media (max-width:640px){{.head{{flex-direction:column}} .head .src{{width:100%}}}}
</style></head><body><main>
<div class="top"><div><h1>{esc(a.title)}</h1>
<p class="mut">{len(plan['photos'])} 张原图 · 成功 {done}/{total} 条 prompt · {today} · 点图放大，⬇ 下载单张</p></div>
<button class="big" onclick="dlAll(this)">⬇ 全部下载（ZIP）</button></div>
{''.join(sections)}</main>
<div id="lb" onclick="this.classList.remove('on')"><img><button onclick="event.stopPropagation();save(document.querySelector('#lb img'))">⬇ 下载这张</button></div>
<script>
function blobOf(src){{const [h,b]=src.split(',');const mime=h.match(/:(.*?);/)[1];const bin=atob(b);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new Blob([u],{{type:mime}})}}
function save(img){{const a=document.createElement('a');a.href=URL.createObjectURL(blobOf(img.src));a.download=img.dataset.name||'image';document.body.appendChild(a);a.click();setTimeout(()=>{{URL.revokeObjectURL(a.href);a.remove()}},1000)}}
function dl(btn){{save(btn.closest('.card').querySelector('img'))}}
function zoom(img){{const l=document.getElementById('lb');const t=l.querySelector('img');t.src=img.src;t.dataset.name=img.dataset.name;l.classList.add('on')}}
async function dlAll(btn){{const imgs=[...document.querySelectorAll('.card img')];
 if(window.JSZip){{btn.textContent='打包中…';const z=new JSZip();imgs.forEach(i=>z.file(i.dataset.name,blobOf(i.src)));
  const b=await z.generateAsync({{type:'blob'}});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='photo-remix-{today}.zip';a.click();btn.textContent='⬇ 全部下载（ZIP）'}}
 else{{for(const i of imgs){{save(i);await new Promise(r=>setTimeout(r,500))}}}}}}
</script></body></html>'''
    (run / "report.html").write_text(page)
    print(f"report.html  {done}/{total}  {(run / 'report.html').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
