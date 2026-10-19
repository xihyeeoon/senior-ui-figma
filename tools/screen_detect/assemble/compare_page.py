r"""조립 1단계 - 견주기 페이지: 새 원본 (조립) 화면과 짝지은 옛 원본 화면을 나란히 (채점 쪽, 유료 호출 없음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/assemble/compare_page.py
        [--dir results/detect/20261019-assembly] → <dir>/compare.html, <dir>/renders/new/<화면>.png

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
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261019-assembly"))
    a = ap.parse_args(argv)
    flow = json.load(io.open(os.path.join(a.dir, "flow.json"), encoding="utf-8"))
    lists = json.load(io.open(os.path.join(a.dir, "lists.json"), encoding="utf-8"))
    screens = [s["screen"] for s in flow["screens"]]
    asyncio.run(shoot(a.dir, screens))
    rel = lambda p: os.path.relpath(p, a.dir).replace("\\", "/")
    olds = {}
    for st, (ns, score) in lists["pairs"].items():
        olds.setdefault(ns, []).append((st, score))
    moves = {}
    for m in flow["transitions"]:
        moves.setdefault(m["from"], []).append("%s → %s" % (m["click"], m["to"]))
    rows = []
    for s in flow["screens"]:
        sid = s["screen"]
        n = lists["new"][sid]
        note = "캡처 %s · 요소 %d · 누를 것 %d · 그림 자리 %d · 선택지 무리 %d · 나가는 이동: %s" % (
            "+".join(c[:-4] for c in s["captures"]), s["elements"], s["pressable"], len(n["images"]), len(n["choices"]),
            "; ".join(moves.get(sid, [])) or "없음")
        cells = []
        for st, score in olds.get(sid, []):
            p = os.path.join(OLD, safe(st) + ".png")
            cells.append('<div class="o"><div class="n">옛 %s (글 %.2f)%s</div>%s</div>' % (
                html.escape(st), score, "" if st in lists["captured"] else " · 캡처 없음",
                '<img src="%s">' % rel(p) if os.path.exists(p) else "(그림 없음)"))
        rows.append('<tr><th colspan="2">%s — %s</th></tr><tr><td><img src="%s"></td><td class="olds">%s</td></tr>' % (
            sid, html.escape(note), rel(os.path.join(a.dir, "renders", "new", sid + ".png")),
            "".join(cells) or "(짝지은 옛 화면 없음)"))
    for st, score in olds.get(None, []):
        p = os.path.join(OLD, safe(st) + ".png")
        rows.append('<tr><th colspan="2">(새 화면 없음) — 옛 %s%s</th></tr><tr><td></td><td class="olds">%s</td></tr>' % (
            html.escape(st), "" if st in lists["captured"] else " · 캡처 없음",
            '<img src="%s">' % rel(p) if os.path.exists(p) else ""))
    doc = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>조립 1단계 견주기</title>
<!-- 만든 것: tools/screen_detect/assemble/compare_page.py -->
<style>body{font-family:"Malgun Gothic",sans-serif;margin:12px;background:#f4f5f7;} th{text-align:left;padding:12px 4px 4px;font-size:14px;}
td{vertical-align:top;padding:4px;} img{width:390px;border:1px solid #ccc;background:#fff;} .olds{display:flex;gap:8px;flex-wrap:wrap;}
.n{font-size:12px;color:#333;margin-bottom:2px;}</style></head><body>
<h1>조립 1단계 - 새 원본 (스크린샷에서 조립) 대 옛 원본</h1>
<p>왼쪽: 새 원본 화면 (<a href="original.html">original.html</a>, 규칙 마크업). 오른쪽: 글이 가장 많이 겹쳐 짝지은 옛 원본 상태들
(truth.py 와 같은 걷기로 찍은 그림). 목록 대조: <code>lists.md</code>, 걷기 시험: <code>walk.md</code>, 한계: <code>limits.md</code>.</p>
<table>%s</table></body></html>""" % "".join(rows)
    with io.open(os.path.join(a.dir, "compare.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print(os.path.join(a.dir, "compare.html"))


if __name__ == "__main__":
    main()
