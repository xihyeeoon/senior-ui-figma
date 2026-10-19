r"""탐색용 시안 — 조립 설계 전. (가) 규칙 시안: 정한 규칙으로만 놓는다 (유료 호출 없음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/sketch/rule_assemble.py
        → results/detect/20261019-sketch/rule.html

입력은 common.py (단위 13 - 요소 · 의미 층 · 구역 나무 · 흐름 짝 · 이름표). 규칙:

  화면      단위마다 <section> 하나 (가로 390, 세로 = 캡처 높이 × 390/824). 바탕은 캡처에서 가장 흔한 색
  띠        가로 95% 이상 구역 → 화면 너비 바탕 띠 (data-band). 요소의 부모가 되지 않는다
  구역      구역 → div (data-region). 바탕 = 구역 안쪽 가장자리(안으로 4px)의 중앙값 색, 테두리 = 맨 바깥 한 줄이
            안쪽 바탕과 다르면 1px 그 색, 둥근 모서리 = 모서리에서 대각선으로 바탕색이 나올 때까지의 거리로 대략
  요소      의미 층 kind 로 - button · link · back_close · tab · choice · keypad_key → <button>, input → 테두리
            있는 div, image → div.pic role="img" aria-label=image_name, text → 글 (span). 글 크기 = OCR 글 높이 ×
            0.75 (CSS px), 글 색 = 글 상자 안에서 바탕과 가장 다른 화소들의 중앙값
  부모      글 줄은 자기가 든 박스(in_box) 안, 그 밖의 요소는 중심을 감싼 가장 작은 (더 큰) 박스 요소 안, 없으면
            구역 나무의 구역 안, 없으면 화면 바로 아래. 자리는 부모 안의 절대 위치 (캡처 좌표 그대로 줄임)
  겹친 버튼  누를 수 있는 것 안의 누를 수 있는 것(은행 칸 안의 글 줄 등)은 <div role="button"> (HTML 은 버튼 안에
            버튼을 허락하지 않는다)
  아이콘    누를 수 있는데 글도 그림 후보도 품지 않은 박스(머리 아이콘 등)는 회색 X 상자(.pic, role 없음 -
            이름이 없다)를 안에 그린다. 그림 후보를 품은 버튼은 그 .pic 이 버튼 안에 들어간다 (부모 규칙)
  이동      흐름 짝(kind tap)의 누른 요소에 data-go="<다음 화면 section id>" - 누르면 그 화면으로
  추적      모든 요소에 data-src="<요소 id>". 상태바(의미 층 system)는 넣지 않는다
  strict    --inputs strict (스크린샷만, 2026-10-19): results/detect/20261019-strict/ 의 입력 (단위 이름 = 캡처 파일
            이름, 의미 층 v2, 흐름 strict) → 20261019-strict/rule.html. 이름표(data-label)를 넣지 않는다. v2 칸 -
            icon 이 있으면 그 요소 안에 .pic role="img" aria-label=icon.name (누를 수 있으면 버튼 안),
            text_is_icon 이면 글 대신 그림 자리만, text_fixed 가 있으면 고친 글 + data-ocr="<원래 글>"
규칙 밖 꾸밈(그림자 · 굵기 · 정렬 다듬기)은 하지 않는다.
"""
import html
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common as K  # noqa: E402

FONT_K = 0.75


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


def ring(arr, box, inset):
    import numpy as np
    x, y, w, h = box
    H, W = arr.shape[:2]
    x0, y0 = max(0, x + inset), max(0, y + inset)
    x1, y1 = min(W - 1, x + w - 1 - inset), min(H - 1, y + h - 1 - inset)
    if x1 <= x0 or y1 <= y0:
        return None
    px = np.concatenate([arr[y0, x0:x1], arr[y1, x0:x1], arr[y0:y1, x0], arr[y0:y1, x1]])
    return np.median(px, axis=0)


def region_style(arr, box):
    import numpy as np
    bg = ring(arr, box, 4)
    if bg is None:
        return {}
    st = {"background": hexc(bg)}
    edge = ring(arr, box, 1)
    if edge is not None and np.abs(edge - bg).max() > 10:
        st["border"] = "1px solid %s" % hexc(edge)
    # 둥근 모서리 - 왼쪽 위 모서리에서 대각선으로 바탕색이 나올 때까지
    x, y, w, h = box
    k = 0
    while k < min(w, h) // 2 and 0 <= y + k < arr.shape[0] and 0 <= x + k < arr.shape[1] \
            and np.abs(arr[y + k, x + k] - bg).max() > 6:
        k += 1
    r = K.css(k * 3.4)
    if r >= 2:
        st["border-radius"] = "%dpx" % min(r, K.css(min(w, h)) // 2)
    return st


def text_color(arr, box):
    import numpy as np
    x, y, w, h = box
    sub = arr[max(0, y):y + h, max(0, x):x + w].reshape(-1, 3)
    if not len(sub):
        return "#111111"
    bg = np.median(np.concatenate([arr[max(0, y), x:x + w], arr[min(arr.shape[0] - 1, y + h), x:x + w]]),
                   axis=0) if w > 0 else np.median(sub, axis=0)
    d = np.abs(sub - bg).max(axis=1)
    top = sub[d >= np.percentile(d, 85)]
    return hexc(np.median(top, axis=0)) if len(top) else "#111111"


def page_bg(arr):
    import numpy as np
    small = (arr[::8, ::8] // 4 * 4).reshape(-1, 3)
    vals, counts = np.unique(small, axis=0, return_counts=True)
    return hexc(vals[counts.argmax()])


def style(d):
    return "; ".join("%s: %s" % kv for kv in d.items())


def contains(a, b):
    """a 가 b 의 중심을 감싸고 b 보다 큰가."""
    cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
    return a[0] <= cx <= a[0] + a[2] and a[1] <= cy <= a[1] + a[3] and a[2] * a[3] > b[2] * b[3]


def build_section(u, arr):
    els = u["elements"]
    boxes = {e["id"]: e for e in els if e["det"] == "box"}
    go = {t["tap"]: t["to"] for t in u["taps"]}
    parent = {}
    for e in els:
        p = e["in_box"] if e["det"] == "text" and e.get("in_box") in boxes else None
        if p is None:
            cand = [b for b in boxes.values() if b["id"] != e["id"] and contains(b["box"], e["box"])]
            p = min(cand, key=lambda b: b["box"][2] * b["box"][3])["id"] if cand else None
        parent[e["id"]] = ("el", p) if p else (("rg", e["region"]) if e["region"] else ("sec", None))
    regs = {r["id"]: r for r in u["regions"]}
    kids = {}
    for r in u["regions"]:
        kids.setdefault(("rg", r["parent"]) if r["parent"] else ("sec", None), []).append(("rg", r["id"]))
    for e in els:
        kids.setdefault(parent[e["id"]], []).append(("el", e["id"]))
    byid = {e["id"]: e for e in els}

    def origin(key):
        if key[0] == "sec":
            return 0, 0
        b = regs[key[1]]["box_css"] if key[0] == "rg" else byid[key[1]]["box_css"]
        return b[0], b[1]

    def place(b, base):
        return {"position": "absolute", "left": "%dpx" % (b[0] - base[0]), "top": "%dpx" % (b[1] - base[1]),
                "width": "%dpx" % b[2], "height": "%dpx" % b[3]}

    def render(key, base, in_btn=False):
        out = []
        for k in sorted(kids.get(key, []), key=lambda k: (k[0] != "rg",)):
            out.append(render_one(k, base, in_btn))
        return "".join(out)

    def render_one(k, base, in_btn):
        if k[0] == "rg":
            r = regs[k[1]]
            st = dict(place(r["box_css"], base), **region_style(arr, r["box"]))
            return '<div data-region="%s" style="%s">%s</div>' % (r["id"], style(st),
                                                                 render(k, origin(k), in_btn))
        e = byid[k[1]]
        b = e["box_css"]
        st = place(b, base)
        is_btn = e["kind"] in K.BUTTONS
        inner = render(k, origin(k), in_btn or is_btn)
        attrs = 'data-src="%s"' % html.escape(e["id"])
        if e["id"] in go:
            attrs += ' data-go="%s"' % go[e["id"]]
        own_text = html.escape(e["text"] or "") if e["det"] == "text" else ""
        # 의미 층 v2 (strict) - 아이콘을 글자로 잘못 읽은 글은 글 대신 그림 자리만, 그림과 다르게 읽힌 글은 고친 글
        # (원래 글은 data-ocr), 아이콘 · 로고를 담은 요소는 그 안에 .pic role="img" aria-label=icon.name
        icon_v2 = e.get("icon") if e["kind"] != "image" else None
        if e.get("text_is_icon"):
            own_text = ""
        elif own_text and e.get("text_fixed"):
            attrs += ' data-ocr="%s"' % html.escape(e["text"])
            own_text = html.escape(e["text_fixed"])
        if icon_v2:
            pic_st = "position:absolute; inset:10%" if not own_text else                 "position:absolute; left:0; top:0; width:%dpx; height:%dpx" % (b[3], b[3])
            inner = '<div class="pic" role="img" aria-label="%s" style="%s"></div>' % (
                html.escape(icon_v2.get("name") or ""), pic_st) + inner
        if own_text:
            st.update({"font-size": "%dpx" % max(8, round(b[3] * FONT_K)), "line-height": "%dpx" % b[3],
                       "color": text_color(arr, e["box"]), "white-space": "nowrap"})
        kind = e["kind"]
        if kind == "image":
            return '<div class="pic" role="img" aria-label="%s" %s style="%s">%s</div>' % (
                html.escape(e["image_name"] or ""), attrs, style(st), inner)
        if kind in K.BUTTONS:
            icon = ""
            if e["det"] == "box" and not e["text"] and not inner and not icon_v2:
                icon = '<span class="pic" style="position:absolute; inset:15%"></span>'
            # 버튼 안의 버튼은 HTML 이 허락하지 않는다 (안쪽 <button> 이 바깥을 닫는다) - 안쪽은 role="button" div
            tag = '<div role="button" %s style="%s">%s%s%s</div>' if in_btn else                 '<button %s style="%s">%s%s%s</button>'
            return tag % (attrs, style(st), own_text, inner, icon)
        if kind == "input":
            st["border"] = "1px solid #8a8f98"
            return '<div class="input" %s style="%s">%s%s</div>' % (attrs, style(st), own_text, inner)
        return '<div %s style="%s">%s%s</div>' % (attrs, style(st), own_text, inner)

    bands = "".join('<div data-band="%s" style="%s"></div>' % (
        r["id"], style(dict(place([0, K.css(r["box"][1]), K.WIDTH, K.css(r["box"][3])], (0, 0)),
                            **{"background": region_style(arr, r["box"]).get("background", "transparent")})))
        for r in u["bands"])
    # 스크린샷만(strict) 에서는 연구자 이름표(data-label)를 넣지 않는다 - data-src · 캡처 파일 이름만
    label = "" if u.get("strict") else ' data-label="%s"' % html.escape(u["label"] or "")
    return ('<section class="screen" id="%s" data-unit="%s"%s style="height:%dpx; background:%s">'
            '%s%s</section>' % (u["section"], html.escape(u["unit"]), label,
                                u["size_css"][1], page_bg(arr), bands, render(("sec", None), (0, 0))))


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<!-- 탐색용 시안 — 조립 설계 전. 정식 조립 결과가 아니다. 만든 것: tools/screen_detect/sketch/%(script)s -->
<style>
  body{margin:0; background:#dfe3ea; font-family:"Malgun Gothic",-apple-system,sans-serif;}
  #nav{position:sticky; top:0; z-index:9; background:#222; color:#fff; font-size:12px; padding:6px; display:flex; flex-wrap:wrap; gap:4px;}
  #nav button{font-size:12px;} body.shot #nav{display:none;}
  #phone{width:390px; margin:0 auto; background:#fff;}
  .screen{display:none; position:relative; width:390px; overflow:hidden;}
  .screen.on{display:block;}
  .screen button{all:unset; box-sizing:border-box; cursor:pointer;}
  .screen [data-go]{cursor:pointer;}
  .pic{box-sizing:border-box; border-radius:3px; box-shadow:inset 0 0 0 1px #B8BDC7; background:
    linear-gradient(to top right, transparent calc(50%% - .75px), #9AA0A8 calc(50%% - .75px), #9AA0A8 calc(50%% + .75px), transparent calc(50%% + .75px)),
    linear-gradient(to bottom right, transparent calc(50%% - .75px), #9AA0A8 calc(50%% - .75px), #9AA0A8 calc(50%% + .75px), transparent calc(50%% + .75px)), #E4E7EC;}
%(extra_css)s
</style></head><body>
<div id="nav">%(nav)s</div>
<div id="phone">
%(sections)s
</div>
<script>
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.toggle('on', s.id===id)); window.scrollTo(0,0);}
document.addEventListener('click', function(e){
  const n = e.target.closest('#nav [data-show]'); if(n){ show(n.dataset.show); return; }
  const g = e.target.closest('.screen [data-go]'); if(g){ e.preventDefault(); show(g.dataset.go); }
});
show(location.hash ? location.hash.slice(1) : document.querySelector('.screen').id);
</script>
</body></html>
"""


def page(title, script, units, sections, extra_css=""):
    nav = "".join('<button data-show="%s">%s</button>' % (u["section"], html.escape(u["unit"])) for u in units)
    return PAGE % {"title": title, "script": script, "nav": nav, "sections": "\n".join(sections),
                   "extra_css": extra_css}


def main(argv=None):
    import argparse
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", help="고른 단위만 - 쉼표로")
    K.ST.add_arg(ap)
    a = ap.parse_args(argv)
    strict = K.ST.from_args(a)
    units = K.load_units(strict=strict, only=[x.strip() for x in (a.units or "").split(",") if x.strip()] or None)
    sections = []
    for u in units.values():
        arr = np.asarray(K.unit_image(u)).astype(np.int16)
        sections.append(build_section(u, arr))
    out = K.STRICT_PATHS["out"] if strict else K.OUT
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "rule.html")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page("규칙 시안", "rule_assemble.py", list(units.values()), sections))
    print(path, sum(len(u["elements"]) for u in units.values()), "요소")


if __name__ == "__main__":
    main()
