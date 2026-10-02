#!/usr/bin/env python3
"""photo-remix：按 plan.json 选 prompt、填参数，生成 Codex 任务文件。

用法: make_jobs.py --run <run_dir>
读:  <run>/plan.json   （Claude 看图分类后写入，格式见 SKILL.md）
写:  <run>/jobs/<key>__<id>.prompt  与  <run>/jobs.txt（每行 "<key> <id>"）
     并把最终选择回写到 plan.json 的 selected / skipped 字段，供报告展示
"""
import argparse, json, pathlib

SKILL = pathlib.Path(__file__).resolve().parent.parent
HEADER = ("用图片生成工具（image_gen）对附图做图生图编辑，严格按下面的提示词生成1张图，"
          "并把结果保存为 {out}。只用图片生成工具出图，不要写代码绘制或模拟。"
          "若提示词要求 recaption，把 recaption 文字写入 {rc}。完成后只回复保存路径。\n\n提示词：\n")


def select(photo, idx):
    """返回 (选中 id 列表, {跳过 id: 原因})"""
    t, routes = photo["type"], idx["routes"]
    order = routes[t]
    pmeta = {p["id"]: p for p in idx["prompts"]}
    skipped = {}
    mode = photo.get("mode", "top")
    if mode == "ids":
        chosen = list(photo["ids"])
    elif mode == "all":
        chosen = list(order)
    else:
        chosen = order[: photo.get("top_n", idx["default_top_n"])]
    if photo.get("no_filter"):   # 用户明确要求不过滤（如做全量对比测试）
        return chosen + [r for r in photo.get("repairs", []) if r not in chosen], skipped
    # 硬规则：合照不跑只认单人身份的 prompt；没人物的照片不跑人物类
    for pid in list(chosen):
        m = pmeta[pid]
        if photo.get("persons", 0) >= 2 and m["single_person_only"]:
            chosen.remove(pid); skipped[pid] = "合照：该 prompt 只保留一个人物"
        elif photo.get("persons", 0) == 0 and m["needs_person"]:
            chosen.remove(pid); skipped[pid] = "照片里没有人物"
    if t == "group":
        for pid in ("02", "05", "08"):
            skipped.setdefault(pid, "合照：该 prompt 只保留一个人物")
    for r in photo.get("repairs", []):
        if r not in chosen:
            chosen.append(r)
    return chosen, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    run = pathlib.Path(ap.parse_args().run).expanduser()
    idx = json.loads((SKILL / "prompts/index.json").read_text())
    pmeta = {p["id"]: p for p in idx["prompts"]}
    plan = json.loads((run / "plan.json").read_text())
    (run / "jobs").mkdir(exist_ok=True)
    lines = []
    for ph in plan["photos"]:
        chosen, skipped = select(ph, idx)
        ph["selected"], ph["skipped"] = chosen, skipped
        params = ph.get("params", {})
        for pid in chosen:
            m = pmeta[pid]
            text = (SKILL / m["file"]).read_text()
            for k in m["params"]:
                if k not in params:
                    raise SystemExit(f"{ph['key']} 的 prompt {pid} 需要参数 {k}，请写进 plan.json 的 params")
                text = text.replace("{{" + k + "}}", params[k])
            out = run / "photos" / ph["key"] / "outputs" / f"{pid}.png"
            rc = out.with_suffix(".recaption.txt")
            (run / "jobs" / f"{ph['key']}__{pid}.prompt").write_text(HEADER.format(out=out, rc=rc) + text)
            lines.append(f"{ph['key']} {pid}")
    (run / "jobs.txt").write_text("\n".join(lines) + "\n")
    (run / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    for ph in plan["photos"]:
        print(ph["key"], ph["type"], "选中", " ".join(ph["selected"]), "| 跳过", ph["skipped"] or "-")
    print("jobs:", len(lines))


if __name__ == "__main__":
    main()
