r"""탐색용 시안 — 조립 설계 전. 견주기 페이지: 캡처 | 옛 원본 재현 HTML | (가) 규칙 시안 | (나) LLM 시안 (유료 호출 없음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/sketch/compare_page.py
        → results/detect/20261019-sketch/compare.html, renders/<쪽>/<화면>.png, counts.json

줄 = 단위(이은 화면 3 + 낱장 10). 짝은 captures.json 의 label 로 잇는다 - label → 정답 상태는 compare_flow.state_of
(D4 와 같은 규칙). 렌더는 truth.py 와 같은 방식 (Playwright chromium, 폭 390 · 창 높이 844):
  옛 원본    truth.py 의 걷기 그대로 (Walk.keep 만 감싼다) - 상태마다 화면 안 스크롤 칸이 다 보이도록 #phone 높이를
             844 + (가장 긴 스크롤 칸의 넘친 높이) 로 잠깐 늘려 찍고 되돌린다
  시안       rule.html · llm.html 을 열어 화면(section)마다 show() 하고 그 section 을 찍는다
  캡처       단위 그림 (이은 화면은 이은 그림) 을 폭 390 으로 줄인 것
줄마다 셈 (시안): 들어간 요소 (공통 입력) · 시안에 나온 요소 (data-src 의 서로 다른 id 중 입력에 있는 것) ·
빠진 id · 새로 생긴 글 (data-src 를 단 요소 밖의 보이는 글 조각 - LLM 시안만 의미가 있다) · 그림 자리
([role=img][aria-label]) · 누를 수 있는 것 (button · [role=button] · [data-action] · [data-go]). 옛 원본은 정답지(truth.json)의
그 상태에서 그림 자리 · 누를 수 있는 data-action · 선택지 값 수.
"""
import asyncio
import html
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common as K  # noqa: E402

sys.path.insert(0, K.TOOLS)
import compare_flow as CF  # noqa: E402
import truth as TR  # noqa: E402

TRUTH = os.path.join(K.ROOT, "results", "detect", "20261013-d3b", "truth.json")
SIDES = [("capture", "캡처"), ("original", "옛 원본 재현 HTML"), ("rule", "(가) 규칙 시안"), ("llm", "(나) LLM 시안")]

EXTRA = r"""() => {
  const on = document.querySelector('.screen.on') || document.body;
  let extra = 0;
  on.querySelectorAll('*').forEach(n => {
    const cs = getComputedStyle(n);
    if (/(auto|scroll)/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 1)
      extra = Math.max(extra, n.scrollHeight - n.clientHeight);
  });
  return extra;
}"""

COUNT = r"""(id) => {
  const s = document.getElementById(id);
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const src = new Set();
  s.querySelectorAll('[data-src]').forEach(e => { if (vis(e)) src.add(e.getAttribute('data-src')); });
  const stray = [];
  const w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n.nodeValue.replace(/\s+/g, ' ').trim();
    if (!t || !n.parentElement || n.parentElement.closest('[data-src]')) continue;
    if (/^(STYLE|SCRIPT)$/.test(n.parentElement.tagName) || !vis(n.parentElement)) continue;
    stray.push(t);
  }
  const press = new Set();
  s.querySelectorAll('button, [role="button"], [data-action], [data-go]').forEach(e => { if (vis(e)) press.add(e); });
  const imgs = Array.from(s.querySelectorAll('[role="img"][aria-label]')).filter(vis).length;
  return {src: Array.from(src), stray: stray, images: imgs, pressable: press.size};
}"""


def safe(name):
    return name.replace(":", "_").replace("+", "_").replace("#", "_").replace("~", "_")


async def shoot_original(out):
    """옛 원본을 걸으며 상태마다 늘린 화면을 찍는다 → {상태: 그림 경로}."""
    shots = {}
    orig_keep = TR.Walk.keep

    async def keep(self, name, via):
        snap = await orig_keep(self, name, via)
        if snap["state"] == name and name not in shots:
            page = self.page
            extra = await page.evaluate(EXTRA)
            h = 844 + int(extra)
            await page.set_viewport_size({"width": 390, "height": h})
            await page.add_style_tag(content="#phone{height:%dpx !important}" % h)
            await asyncio.sleep(0.2)
            path = os.path.join(out, "%s.png" % safe(name))
            await page.locator("#phone").screenshot(path=path)
            await page.evaluate("() => { const t = document.querySelectorAll('style'); t[t.length - 1].remove(); }")
            await page.set_viewport_size({"width": 390, "height": 844})
            await asyncio.sleep(0.1)
            shots[name] = path
        return snap
    TR.Walk.keep = keep
    task = TR.T.load_task("transfer")
    flow = TR.load_flow(None, task="transfer")
    html_path = TR.T.abs_path(task["original"])
    await TR.walk("file:///" + html_path.replace("\\", "/"), flow)
    TR.Walk.keep = orig_keep
    return shots


async def shoot_sketch(path, units, out):
    """시안 HTML 의 화면마다 그림과 셈."""
    from playwright.async_api import async_playwright
    res = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.goto("file:///" + path.replace("\\", "/"))
            await page.evaluate("() => document.body.classList.add('shot')")
            for u in units:
                if not await page.evaluate("(id) => !!document.getElementById(id)", u["section"]):
                    continue
                await page.evaluate("(id) => show(id)", u["section"])
                await asyncio.sleep(0.1)
                p = os.path.join(out, "%s.png" % u["section"])
                await page.locator("#" + u["section"]).screenshot(path=p)
                res[u["unit"]] = dict(await page.evaluate(COUNT, u["section"]), png=p)
        finally:
            await browser.close()
    return res


def main():
    from PIL import Image
    units = list(K.load_units().values())
    truth = json.load(io.open(TRUTH, encoding="utf-8"))
    states = {s["state"]: s for s in truth["states"]}
    rd = os.path.join(K.OUT, "renders")
    for side, _ in SIDES:
        os.makedirs(os.path.join(rd, side), exist_ok=True)
    cap = {}
    for u in units:
        im = K.unit_image(u)
        p = os.path.join(rd, "capture", "%s.png" % u["section"])
        im.resize((K.WIDTH, round(im.height * K.WIDTH / im.width)), Image.LANCZOS).save(p)
        cap[u["unit"]] = p
    shots = asyncio.run(shoot_original(os.path.join(rd, "original")))
    sk = {}
    for side in ("rule", "llm"):
        f = os.path.join(K.OUT, "%s.html" % side)
        sk[side] = asyncio.run(shoot_sketch(f, units, os.path.join(rd, side))) if os.path.exists(f) else {}

    rows, counts = [], {}
    for u in units:
        st = CF.state_of(u["label"] or "", truth["states"])
        s = states.get(st) or {}
        orig = {"state": st, "images": len(s.get("image_slots") or []), "pressable": len(s.get("actions") or []),
                "choices": sum(len(v) for v in (s.get("choices") or {}).values()), "png": shots.get(st)}
        ids = [e["id"] for e in u["elements"]]
        c = {"unit": u["unit"], "label": u["label"], "inputs": len(ids), "original": orig}
        for side in ("rule", "llm"):
            r = sk[side].get(u["unit"])
            if r:
                got = [i for i in r["src"] if i in set(ids)]
                c[side] = {"shown": len(got), "missing": [i for i in ids if i not in set(r["src"])],
                           "unknown": [i for i in r["src"] if i not in set(ids)], "stray": r["stray"],
                           "images": r["images"], "pressable": r["pressable"], "png": r["png"]}
        counts[u["unit"]] = c
        rows.append(c)

    rel = lambda p: os.path.relpath(p, K.OUT).replace("\\", "/") if p else None

    def cell(side, c):
        if side == "capture":
            return '<img src="%s">' % rel(cap[c["unit"]]), "들어간 요소 %d" % c["inputs"]
        if side == "original":
            o = c["original"]
            img = '<img src="%s">' % rel(o["png"]) if o["png"] else "<p>(상태 없음)</p>"
            return img, "상태 %s · 그림 자리 %d · 누를 것 %d · 선택지 값 %d" % (o["state"], o["images"], o["pressable"],
                                                                 o["choices"])
        r = c.get(side)
        if not r:
            return "", ""
        note = "나온 요소 %d/%d · 빠진 id %d" % (r["shown"], c["inputs"], len(r["missing"]))
        if side == "llm":
            note += " · 새로 생긴 글 %d" % len(r["stray"])
        note += " · 그림 자리 %d · 누를 것 %d" % (r["images"], r["pressable"])
        return '<img src="%s">' % rel(r["png"]), note
    trs = []
    for c in rows:
        tds = []
        for side, _ in SIDES:
            img, note = cell(side, c)
            tds.append('<td><div class="n">%s</div>%s</td>' % (html.escape(note), img))
        trs.append('<tr><th colspan="4">%s — %s</th></tr><tr>%s</tr>' % (html.escape(c["unit"]),
                                                                        html.escape(c["label"] or ""), "".join(tds)))
    doc = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조립 시안 견주기</title>
<!-- 탐색용 시안 — 조립 설계 전. 만든 것: tools/screen_detect/sketch/compare_page.py -->
<style>body{font-family:"Malgun Gothic",sans-serif; margin:12px; background:#f4f5f7;}
table{border-collapse:collapse;} th{text-align:left; padding:10px 4px 4px; font-size:15px;}
td{vertical-align:top; padding:4px; width:400px;} td img{width:390px; border:1px solid #ccc; background:#fff;}
.n{font-size:12px; color:#333; min-height:32px;} thead th{position:sticky; top:0; background:#f4f5f7; z-index:2;}</style>
</head><body><h1>조립 시안 견주기 (탐색용)</h1>
<p>캡처 | 옛 원본 재현 HTML (truth.py 와 같은 걷기 · 폭 390) | (가) 규칙 시안 rule.html | (나) LLM 시안 llm.html.
짝은 captures.json 의 label. 시안은 직접 열어 눌러 볼 수 있다: <a href="rule.html">rule.html</a> · <a href="llm.html">llm.html</a>.</p>
<table><thead><tr>%s</tr></thead>%s</table></body></html>""" % (
        "".join("<th>%s</th>" % t for _, t in SIDES), "".join(trs))
    with io.open(os.path.join(K.OUT, "compare.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    with io.open(os.path.join(K.OUT, "counts.json"), "w", encoding="utf-8") as f:
        json.dump({u: {k: (dict((kk, rel(vv) if kk == "png" else vv) for kk, vv in v.items())
                           if isinstance(v, dict) else v) for k, v in c.items()} for u, c in counts.items()},
                  f, ensure_ascii=False, indent=1)
    for c in rows:
        print(c["unit"], c["inputs"], {s: (c[s]["shown"], len(c[s]["missing"]), len(c[s]["stray"]), c[s]["images"],
                                          c[s]["pressable"]) for s in ("rule", "llm") if s in c},
              c["original"]["state"], c["original"]["images"], c["original"]["pressable"])


if __name__ == "__main__":
    main()
