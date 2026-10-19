r"""조립 1 · 2단계 - 목록 대조 도구 (채점 쪽 - 사람 파일을 읽는다, strict 를 켜지 않는다). 유료 호출 없음.

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/assemble/list_compare.py
        [--dir results/detect/20261019-assembly2/rule] → <dir>/lists.json, lists.md

옛 원본과 새 원본에서 같은 목록을 뽑아 이름이 아니라 글 · 뜻으로 견준다. 목록은 파이프라인 검사기가 원본에서 읽는 것에
맞춘다 (origin/feat/db-principles 의 senior_ui/audit - 인수인계 기록):
  I  선택지 - 같은 data-action · 같은 부모 아래 형제 2개 이상, 값은 첫 data-* (없으면 글), 지금 보이는 것만 (CHOICE_SHOWN)
  L  그림 자리 - 보이는 [role=img][aria-label] 의 이름
  K  과제 밖 입구 - 옛: 과제 파일 entrances 의 oos-* 가운데 보이는 것 (글 · aria). 새: 누를 수 있는데 이동에 쓰이지 않은 것
  J  오류 경로 - 흐름 JSON 의 error_paths
  + 입력칸, 화면 수와 짝, 과제 길 (첫 화면 → 끝 화면까지 이동이 이어지나)
옛 쪽: 상태마다의 목록은 truth.py 가 옛 원본 (inputs/original_transfer.html) 을 옛 흐름 (flows/original.json) 대로 걸으며
같은 probe 로 모은 results/detect/20261013-d3b/truth.json 을 쓰고, error_paths · steps 는 git show
origin/feat/db-principles:flows/original.json 으로 읽는다. 새 쪽: original.html 을 헤드리스 chromium 으로 열어 화면마다
show() 하고 같은 규칙의 JS 로 모은다.
화면 짝: 옛 상태마다 그 보이는 글이 가장 많이 찾아지는 새 화면 (compare.Pool, 찾은 비율 0.3 이상). 같은 새 화면에 짝지어진
옛 상태들의 목록은 합쳐 견준다. 글 비교는 지금의 새 셈 - compare.norm (띄어쓰기 · 기호) 과 그림 이름은 compare.name_key
(끝말 로고/아이콘 같게).
나눔: 같음 / 다름 (입력칸 - 같은 화면 짝에서 서로 남은 것끼리 차례로 짝지은 것, 과제 길 - 짝지은 화면 사이에 이동이 이어지지
않음) / 새에만 / 옛에만 / 캡처 없음
(옛에만 있고 그 상태를 찍은 캡처가 없는 것 - captures.json 의 이름표가 가리키지 않는 상태).
"""
import argparse
import asyncio
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TOOLS))
sys.path.insert(0, TOOLS)

import compare as C  # noqa: E402
import compare_flow as CF  # noqa: E402

TRUTH = os.path.join(ROOT, "results", "detect", "20261013-d3b", "truth.json")
REF = "origin/feat/db-principles"
PAIR_MIN = 0.3
CATS = ["같음", "다름", "새에만", "옛에만", "캡처 없음"]

NEW = r"""([id, inputs]) => {
  const s = document.querySelector('.screen[data-screen="' + id + '"]');
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim();
  const texts = clean(s.innerText).length ? s.innerText.split('\n').map(clean).filter(Boolean) : [];
  const images = Array.from(s.querySelectorAll('[role="img"][aria-label]')).filter(vis).map(e => e.getAttribute('aria-label'));
  const groups = {};
  s.querySelectorAll('[data-action]').forEach(el => { if (vis(el)) (groups[el.dataset.action] = groups[el.dataset.action] || []).push(el); });
  const choices = {};
  for (const a in groups) {
    const byParent = new Map();
    groups[a].forEach(el => { const p = el.parentElement; if (!byParent.has(p)) byParent.set(p, []); byParent.get(p).push(el); });
    let els = []; byParent.forEach(sibs => { if (sibs.length >= 2) els = els.concat(sibs); });
    if (els.length < 2) continue;
    const vals = [];
    els.forEach(el => { let v = null; for (const k in el.dataset) { if (k === 'action') continue; const x = (el.dataset[k] || '').trim(); if (x) { v = x; break; } }
      if (!v) v = clean(el.textContent); if (v && v.length <= 40) vals.push(v); });
    choices[a] = Array.from(new Set(vals));
  }
  const press = Array.from(s.querySelectorAll('[data-action]')).filter(vis).map(el => {
    const img = el.querySelector('[role="img"]');
    return {action: el.dataset.action, v: el.dataset.v || null, text: clean(el.innerText),
            aria: el.getAttribute('aria-label') || (img ? img.getAttribute('aria-label') : null)};
  });
  // 입력칸 = .input (규칙 마크업) 또는 의미 층 kind input 인 data-src 요소 (LLM 마크업은 class 를 짓지 않는다)
  const fl = new Set(Array.from(s.querySelectorAll('.input')));
  s.querySelectorAll('[data-src]').forEach(e => { if (inputs.includes(e.dataset.src)) fl.add(e); });
  const fields = Array.from(fl).filter(vis).map(e => clean(e.innerText));
  return {texts, images, choices, press, fields};
}"""


def git_json(path):
    out = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (REF, path)], capture_output=True, check=True)
    return json.loads(out.stdout.decode("utf-8"))


async def new_lists(folder, screens):
    from playwright.async_api import async_playwright
    out = {}
    trace = json.load(io.open(os.path.join(folder, "trace.json"), encoding="utf-8"))
    inputs = {}
    for t in trace.values():
        if (t["semantic"] or {}).get("kind") == "input":
            inputs.setdefault(t["screen"], []).append(t["element"])
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto("file:///" + os.path.join(folder, "original.html").replace("\\", "/"))
        for s in screens:
            await page.evaluate("(s) => show(s)", s)
            out[s] = await page.evaluate(NEW, [s, inputs.get(s, [])])
        await browser.close()
    return out


def same_text(a, b):
    na, nb = C.norm(a), C.norm(b)
    if not na or not nb:
        return False
    return na == nb or C.ratio(na, nb) >= C.FOUND or (min(len(na), len(nb)) >= 2 and (na in nb or nb in na))


def match(olds, news, eq, pair_rest=False):
    """(같음 [(옛, 새)], 다름 [(옛, 새)], 옛에만 [옛], 새에만 [새])."""
    news = list(news)
    same, rest_old = [], []
    for o in olds:
        k = next((i for i, n in enumerate(news) if eq(o, n)), None)
        if k is None:
            rest_old.append(o)
        else:
            same.append((o, news.pop(k)))
    diff = []
    if pair_rest:
        while rest_old and news:
            diff.append((rest_old.pop(0), news.pop(0)))
    return same, diff, rest_old, news


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261019-assembly2", "rule"))
    a = ap.parse_args(argv)
    truth = json.load(io.open(TRUTH, encoding="utf-8"))
    old_flow = git_json("flows/original.json")
    caps = git_json("inputs/captures/transfer/captures.json")
    captured = {CF.state_of(im["label"], truth["states"]) for im in caps["images"]}
    flow = json.load(io.open(os.path.join(a.dir, "flow.json"), encoding="utf-8"))
    screens = [s["screen"] for s in flow["screens"]]
    new = asyncio.run(new_lists(a.dir, screens))
    moved = {(m["from"], m["action"], m["v"]) for m in flow["transitions"]}
    group_actions = {g for s in flow["screens"] for g in s["groups"].values()}
    for s in screens:
        new[s]["entrances"] = [p for p in new[s]["press"] if (s, p["action"], p["v"]) not in moved
                               and p["action"] not in group_actions]
    # 화면 짝
    pairs = {}
    for st in truth["states"]:
        ns = [C.norm(t) for t in st["texts"] if C.norm(t)]
        best = max(screens, key=lambda s: sum(C.Pool(new[s]["texts"]).has(n) for n in ns) / max(1, len(ns)))
        score = sum(C.Pool(new[best]["texts"]).has(n) for n in ns) / max(1, len(ns))
        pairs[st["state"]] = (best if score >= PAIR_MIN else None, round(score, 2))
    old_by_new = {}
    for st in truth["states"]:
        if pairs[st["state"]][0]:
            old_by_new.setdefault(pairs[st["state"]][0], []).append(st)
    tally = {k: {c: 0 for c in CATS} for k in ("선택지 값", "그림 자리 이름", "과제 밖 입구", "입력칸", "오류 경로", "과제 길")}
    detail = {k: [] for k in tally}

    def add(kind, cat, what, where):
        tally[kind][cat] += 1
        if cat != "같음":
            detail[kind].append([cat, where, what])
    for s in screens:
        olds = old_by_new.get(s, [])
        where = "%s ↔ %s" % (s, " · ".join(o["state"] for o in olds) or "-")
        oc = list(dict.fromkeys(v for o in olds for vs in o["choices"].values() for v in vs))
        nc = list(dict.fromkeys(v for vs in new[s]["choices"].values() for v in vs))
        sm, df, oo, no = match(oc, nc, same_text)
        for _ in sm:
            add("선택지 값", "같음", "", where)
        for x in oo:
            add("선택지 값", "옛에만", x, where)
        for x in no:
            add("선택지 값", "새에만", x, where)
        oi = list(dict.fromkeys(sl["label"] for o in olds for sl in o["image_slots"]))
        sm, df, oo, no = match(oi, new[s]["images"], lambda x, y: C.name_key(x) == C.name_key(y))
        for _ in sm:
            add("그림 자리 이름", "같음", "", where)
        for x, y in df:
            add("그림 자리 이름", "다름", "%s ↔ %s" % (x, y), where)
        for x in oo:
            add("그림 자리 이름", "옛에만", x, where)
        for x in no:
            add("그림 자리 이름", "새에만", x, where)
        oe = list(dict.fromkeys((e.get("text") or e.get("aria") or e["action"]) for o in olds for e in o["entrances"]))
        ne = [p["text"] or p["aria"] or p["action"] for p in new[s]["entrances"]]
        sm, df, oo, no = match(oe, ne, same_text)
        for _ in sm:
            add("과제 밖 입구", "같음", "", where)
        for x in oo:
            add("과제 밖 입구", "옛에만", x, where)
        for x in no:
            add("과제 밖 입구", "새에만", x, where)
        of = list(dict.fromkeys((f.get("text") or f.get("placeholder") or "(빈 칸)") for o in olds for f in o["fields"]))
        sm, df, oo, no = match(of, new[s]["fields"], same_text, pair_rest=True)
        for _ in sm:
            add("입력칸", "같음", "", where)
        for x, y in df:
            add("입력칸", "다름", "%s ↔ %s" % (x, y), where)
        for x in oo:
            add("입력칸", "옛에만", x, where)
        for x in no:
            add("입력칸", "새에만", x, where)
    for st in truth["states"]:
        if pairs[st["state"]][0]:
            continue
        cat = "캡처 없음" if st["state"] not in captured else "옛에만"
        where = "%s ↔ (짝 없음)" % st["state"]
        for vs in st["choices"].values():
            for v in vs:
                add("선택지 값", cat, v, where)
        for sl in st["image_slots"]:
            add("그림 자리 이름", cat, sl["label"], where)
        for e in st["entrances"]:
            add("과제 밖 입구", cat, e.get("text") or e.get("aria"), where)
        for f in st["fields"]:
            add("입력칸", cat, f.get("text") or f.get("placeholder"), where)
    # 오류 경로
    new_err = {e["expect_screen"]: e for e in flow["error_paths"]}
    for ep in old_flow.get("error_paths") or []:
        st = "error:%s" % ep["id"]
        ns = pairs.get(st, (None,))[0]
        if ns and ns in new_err:
            add("오류 경로", "같음", "%s (%s ↔ %s)" % (ep["id"], ep["expect_screen"], ns), st)
            new_err.pop(ns)
        else:
            add("오류 경로", "캡처 없음" if st not in captured else "옛에만", "%s → %s" % (ep["id"], ep["expect_screen"]), st)
    for s, e in new_err.items():
        add("오류 경로", "새에만", "%s → %s" % (e["id"], s), s)
    # 과제 길 - 옛 steps 의 이웃한 방문마다, 짝지은 새 화면 사이에 이동이 있나
    sys.path.insert(0, ROOT)
    from senior_ui.audit.flow import visit_keys      # 방문 이름 (account · account#2 …) - truth.py 와 같다
    seq = visit_keys(old_flow["steps"])
    trans = {(m["from"], m["to"]) for m in flow["transitions"]}

    def reaches(x, y):
        seen, todo = {x}, [x]
        while todo:
            c = todo.pop()
            for f, t in trans:
                if f == c and t not in seen:
                    seen.add(t)
                    todo.append(t)
        return y in seen
    for sx, sy in zip(seq, seq[1:]):
        x, y = sx, sy
        nx, ny = pairs.get(sx, (None,))[0], pairs.get(sy, (None,))[0]
        what = "%s → %s (새 %s → %s)" % (x, y, nx, ny)
        if nx and ny and (nx == ny or reaches(nx, ny)):
            add("과제 길", "같음", what, what)
        elif nx and ny:
            add("과제 길", "다름", what + " - 이동 없음", what)
        else:
            add("과제 길", "캡처 없음" if (sx not in captured or sy not in captured) else "옛에만", what, what)
    out = {"pairs": pairs, "captured": sorted(x for x in captured if x), "tally": tally, "detail": detail,
           "old_screens": len(truth["states"]), "new_screens": len(screens), "new": new}
    with io.open(os.path.join(a.dir, "lists.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = ["# 목록 대조 - 옛 원본 대 새 원본 (%s)\n" % os.path.relpath(a.dir, ROOT).replace(os.sep, "/"),
          "옛: `results/detect/20261013-d3b/truth.json` (옛 원본을 옛 흐름대로 걸은 목록) + `git show %s:flows/original.json`. "
          "새: `original.html` · `flow.json`. 화면 짝은 글이 가장 많이 찾아지는 것 (찾은 비율 %.1f 이상).\n" % (REF, PAIR_MIN),
          "## 화면 짝 (옛 상태 %d · 새 화면 %d)\n" % (len(truth["states"]), len(screens)),
          C.table(["옛 상태", "캡처 있음", "새 화면", "찾은 비율"],
                  [[st, "예" if st in captured else "아니오", pairs[st][0] or "-", pairs[st][1]] for st in pairs]),
          "\n## 항목별\n",
          C.table(["항목", *CATS], [[k, *[tally[k][c] for c in CATS]] for k in tally]),
          "\n## 다름 · 옛에만 · 새에만 · 캡처 없음 상세\n"]
    for k, rows in detail.items():
        if rows:
            md.append("\n### %s\n" % k)
            md.append(C.table(["나눔", "화면", "무엇"], rows))
    with io.open(os.path.join(a.dir, "lists.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[:6]))


if __name__ == "__main__":
    main()
