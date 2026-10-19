r"""조립 1 · 2단계 - 견주기 페이지: 새 원본 (조립) 화면과 짝지은 옛 원본 화면을 나란히 (채점 쪽, 유료 호출 없음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/assemble/compare_page.py
        [--dir results/detect/20261019-assembly2/rule] → <dir>/compare.html, <dir>/renders/new/<화면>.png
    2단계 (캡처 · 옛 원본 · 규칙 판 · LLM 판 네 열):
        ... compare_page.py --dir results/detect/20261019-assembly2/rule --also "LLM 판=results/detect/20261019-assembly2/llm"
            --captures --page results/detect/20261019-assembly2/compare.html

짝은 list_compare.py 의 lists.json (옛 상태마다 글이 가장 많이 찾아지는 새 화면). 옛 원본 그림은 sketch/compare_page.py 가
truth.py 와 같은 걷기로 찍어 둔 results/detect/20261019-sketch/renders/original/<상태>.png 를 쓴다. 새 원본은 화면마다 show()
하고 화면 안 스크롤이 다 보이게 #phone 을 잠깐 늘려 그 화면의 canvas 를 찍는다 (폭 390).
"""
import argparse
import asyncio
import html
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OLD = os.path.join(ROOT, "results", "detect", "20261019-sketch", "renders", "original")
CAPS = os.path.join(ROOT, "inputs", "captures", "transfer")


def safe(name):
    return name.replace(":", "_").replace("+", "_").replace("#", "_").replace("~", "_")


async def shoot(folder, screens):
    from playwright.async_api import async_playwright
    out = os.path.join(folder, "renders", "new")
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto("file:///" + os.path.join(folder, "original.html").replace("\\", "/"))
        await page.add_style_tag(content="#phone{height:auto !important;overflow:visible !important}"
                                         ".screen.on{position:relative !important;overflow:visible !important}")
        for s in screens:
            await page.evaluate("(s) => show(s)", s)
            await page.locator(".screen.on .canvas").screenshot(path=os.path.join(out, s + ".png"))
        await browser.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261019-assembly2", "rule"),
                    help="첫 판 (옛 화면 짝 · 이동은 이 판의 lists.json · flow.json)")
    ap.add_argument("--label", default="규칙 판")
    ap.add_argument("--also", nargs="*", default=[], help="같은 화면 id 의 다른 판 - 이름=폴더 (열을 더한다)")
    ap.add_argument("--captures", action="store_true", help="맨 앞에 캡처 열 (inputs/captures/transfer)")
    ap.add_argument("--page", help="쓸 쪽 (기본 <dir>/compare.html)")
    a = ap.parse_args(argv)
    sides = [(a.label, a.dir)] + [tuple(x.split("=", 1)) for x in a.also]
    page_path = a.page or os.path.join(a.dir, "compare.html")
    base = os.path.dirname(page_path)
    flow = json.load(io.open(os.path.join(a.dir, "flow.json"), encoding="utf-8"))
    lists = json.load(io.open(os.path.join(a.dir, "lists.json"), encoding="utf-8"))
    screens = [s["screen"] for s in flow["screens"]]
    for _, d in sides:
        asyncio.run(shoot(d, screens))
    rel = lambda p: os.path.relpath(p, base).replace("\\", "/")
    olds = {}
    for st, (ns, score) in lists["pairs"].items():
        olds.setdefault(ns, []).append((st, score))
    moves = {}
    for m in flow["transitions"]:
        moves.setdefault(m["from"], []).append("%s → %s (%s)" % (m["click"], m["to"], m.get("via") or "tap"))
    marks = {}
    for name, d in sides:
        p = os.path.join(d, "trace.json")
        if os.path.exists(p):
            t = json.load(io.open(p, encoding="utf-8"))
            for v in t.values():
                marks.setdefault((name, v["screen"]), v.get("markup"))
    old_cell = lambda st, score: '<div class="o"><div class="n">옛 %s (글 %.2f)%s</div>%s</div>' % (
        html.escape(st), score, "" if st in lists["captured"] else " · 캡처 없음",
        '<img src="%s">' % rel(os.path.join(OLD, safe(st) + ".png")) if os.path.exists(os.path.join(OLD, safe(st) + ".png"))
        else "(그림 없음)")
    head = (["캡처"] if a.captures else []) + ["옛 원본"] + [n for n, _ in sides]
    rows = []
    for s in flow["screens"]:
        sid = s["screen"]
        n = lists["new"][sid]
        note = "캡처 %s · 요소 %d · 누를 것 %d · 그림 자리 %d · 선택지 무리 %d · 나가는 이동: %s" % (
            "+".join(c[:-4] for c in s["captures"]), s["elements"], s["pressable"], len(n["images"]), len(n["choices"]),
            "; ".join(moves.get(sid, [])) or "없음")
        cells = []
        if a.captures:
            cells.append('<td class="cap">%s</td>' % "".join(
                '<img src="%s">' % rel(os.path.join(CAPS, c)) for c in s["captures"]))
        cells.append('<td class="olds">%s</td>' % ("".join(old_cell(st, sc) for st, sc in olds.get(sid, []))
                                                    or "(짝지은 옛 화면 없음)"))
        for name, d in sides:
            cells.append('<td><div class="n">%s%s</div><img src="%s"></td>' % (
                html.escape(name), " · " + html.escape(marks.get((name, sid)) or "") if marks.get((name, sid)) else "",
                rel(os.path.join(d, "renders", "new", sid + ".png"))))
        rows.append('<tr><th colspan="%d">%s — %s</th></tr><tr>%s</tr>' % (len(head), sid, html.escape(note), "".join(cells)))
    for st, score in olds.get(None, []):
        rows.append('<tr><th colspan="%d">(새 화면 없음) — 옛 %s</th></tr><tr>%s<td class="olds">%s</td>%s</tr>' % (
            len(head), html.escape(st), "<td></td>" if a.captures else "", old_cell(st, score), "<td></td>" * len(sides)))
    links = " · ".join('%s: <a href="%s">original.html</a> (<a href="%s">lists.md</a> · <a href="%s">walk.md</a> · '
                       '<a href="%s">limits.md</a>)' % (html.escape(nm), rel(os.path.join(d, "original.html")),
                                                       rel(os.path.join(d, "lists.md")), rel(os.path.join(d, "walk.md")),
                                                       rel(os.path.join(d, "limits.md"))) for nm, d in sides)
    doc = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조립 견주기</title>
<!-- 만든 것: tools/screen_detect/assemble/compare_page.py -->
<style>body{font-family:"Malgun Gothic",sans-serif;margin:12px;background:#f4f5f7;} th{text-align:left;padding:12px 4px 4px;font-size:14px;}
td{vertical-align:top;padding:4px;} img{width:300px;border:1px solid #ccc;background:#fff;display:block;} .olds{display:flex;gap:8px;flex-wrap:wrap;max-width:620px;}
.cap img{margin-bottom:4px;} .n{font-size:12px;color:#333;margin-bottom:2px;max-width:300px;} thead th{position:sticky;top:0;background:#f4f5f7;}</style></head><body>
<h1>조립 견주기 - 스크린샷에서 조립한 원본 대 옛 원본</h1>
<p>열: %s. 옛 원본 그림은 truth.py 와 같은 걷기로 찍은 것, 짝은 글이 가장 많이 겹치는 것 (%s 의 lists.json). 새 판 그림은 화면마다
show() 하고 화면 안 스크롤이 다 보이게 찍은 것 (폭 390).</p><p>%s</p>
<table><thead><tr>%s</tr></thead>%s</table></body></html>""" % (
        " · ".join(head), html.escape(a.label), links, "".join("<th>%s</th>" % html.escape(h) for h in head), "".join(rows))
    with io.open(page_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print(page_path)


if __name__ == "__main__":
    main()


