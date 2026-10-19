r"""조립 2단계 - 규칙 부분 (만드는 줄, --inputs strict). 2026-10-19 조립 설계 v0 + 연구자 결정 a · c · d (10/19).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/assemble/build.py --inputs strict
        → results/detect/20261019-assembly2/rule/{original.html, flow.json, trace.json, limits.md, check.json}
        (1단계 결과 20261019-assembly 는 a · c · d 전의 이 파일)

설계 v0 (연구자 확정): 생김새는 LLM, 동작 · 이름 · 처리기 · 흐름 파일 · 추적표는 규칙 (이 파일). 이 파일만 돌리면 LLM
마크업 자리에 규칙 시안 마크업 (sketch/rule_assemble 의 규칙 - 구역 div · 절대 위치 · 캡처 색) 을 넣는다 (규칙 판).
LLM 판은 llm_build.py 가 plan() 을 그대로 쓰고 마크업만 바꿔 write() 한다.

입력 (strict3, 모두 스크린샷에서 나온 것): 검출 20261019-strict2/detect (이어 붙이기 13단위 포함), 의미 층
20261019-strict3/semantic (v2 strict, 은행은 strict3 에서 다시), 흐름 짝 20261019-strict3/flow (그림 포함), 구역 나무는 같은
M1 (색 차이 2) 으로 그 자리에서. 사람 파일은 읽지 않는다 (감사 훅).

규칙
  화면      단위 하나 = section.screen[data-screen="sNN"] 하나 (단위 차례 = 파일 이름 순). 이은 단위는 긴 한 화면 (화면 안
            스크롤). 같은 화면의 상태 변화로 따로 찍힌 캡처도 각각 다른 화면
  마크업    규칙 시안과 같은 놓기 + strict3 의미 층 - 꺾쇠 (icon.shape · image_shape 에 "꺾쇠") 는 글자 › (아래 ⌄ · 위 ⌃ ·
            왼쪽 ‹), icon 은 그 요소 안 .pic[role=img][aria-label] (누를 수 있으면 button 안), text_is_icon 은 그림 자리만,
            text_fixed 는 고친 글 + data-ocr. 모든 요소에 data-src
  이름      누를 수 있는 요소 (의미 층 pressable · button 류 kind · input) 마다 data-action="a-<화면>-<차례>" (위→아래 ·
            왼→오 차례, 뜻 이름 없음). 선택지 무리 (의미 층 group 이 같은 choice · keypad_key 2개 이상) 는 같은 부모 아래
            형제로 모으고 무리 하나에 data-action="a-<화면>-g<차례>" 하나, 값은 data-v (그 글. 글이 없으면 그림 이름 - 자기
            icon.name · image_name, 없으면 안에 든 첫 그림 자리 이름, 그것도 없으면 요소 id). 검사 I 가 "같은 data-action ·
            같은 부모 · 형제 2개 이상" 을 무리로 보기 때문이다 (data-v 는 data-src 보다 앞 - 값은 첫 data-*)
  이동      흐름 짝 kind = tap 이고 누른 요소가 있으면 그 요소의 data-action → 다음 화면 show (무리 안 요소면 data-v 까지 본다).
            via = "tap". 끊긴 짝 (skipped · unknown) 은 연구자 결정 a (10/19) 의 두 근거로만 잇는다 - 입력이 과제 순서대로
            찍은 캡처라 이웃한 캡처 사이에 이동이 있었다는 것은 입력에서 온 사실이다. 사이 상태는 짓지 않는다
              (가) 짝이 처음 누른 것을 적었고 그 요소가 앞 화면의 누를 것이면 → 그 요소가 다음 캡처 화면을 show,
                   via = "skipped-states"
              (나) 누른 것이 없고 앞 화면에 숫자판 무리 (값이 숫자 하나인 키 3개 이상) 가 있으면 → 그 무리의 어느 키든
                   다음 캡처 화면 (data-v 를 보지 않음), via = "keypad-advance"
            둘 다 아니면 이동을 만들지 않고 limits 에 적는다
  처리기    #phone 위임 처리기 하나 (a==='…' → show('sNN')), 시작 화면 s01. window.__screen() 은 지금 화면
  오류      kind = error_path 짝 → flow.json error_paths (from_step = 앞 화면, expect_screen = 오류 화면). 오류 화면의 누를 것이
            있으면 recover 로 그것을 누르고 back_to = 앞 화면 (처리기에도 그 이동). 오류 조건 · 입력은 만들지 않는다
  입력칸    kind = input → 테두리 있는 div.input. 입력 검사 동작은 없다
  과제 밖   누를 수 있는데 흐름에 쓰이지 않은 요소 → data-action 만, 이동 없음
"""
import argparse
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TOOLS))
sys.path.insert(0, os.path.join(TOOLS, "sketch"))
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import check_markup as CM  # noqa: E402
import common as K  # noqa: E402
import rule_assemble as RA  # noqa: E402

R = os.path.join(ROOT, "results", "detect")
INPUTS = {"final": os.path.join(R, "20261019-strict2", "detect"),
          "semantic": os.path.join(R, "20261019-strict3", "semantic"),
          "flow": os.path.join(R, "20261019-strict3", "flow", "flow.proposed.json")}
OUT = os.path.join(R, "20261019-assembly2", "rule")
PRESS_KINDS = set(K.BUTTONS) | {"input"}
GROUP_KINDS = {"choice", "keypad_key"}


def chevron_of(shape):
    """꺾쇠 모양이면 그 글자, 아니면 None."""
    if not shape or "꺾쇠" not in shape:
        return None
    if "아래" in shape:
        return "⌄"
    if "위" in shape:
        return "⌃"
    if "왼" in shape:
        return "‹"
    return "›"


def shown_text(e):
    return e.get("text_fixed") or e.get("text") or ""


def build_screen(sid, u, arr, sem, actions):
    """한 화면의 section. actions: 요소 id → (data-action, data-v 또는 None) 를 채운다. 기대값 (출력 검사) 도 돌려준다."""
    els = sorted(u["elements"], key=lambda e: (e["box"][1], e["box"][0]))
    byid = {e["id"]: e for e in els}
    boxes = {e["id"]: e for e in els if e["det"] == "box"}
    for e in els:
        e["image_shape"] = (sem.get(e["id"]) or {}).get("image_shape")
    # 부모 - 규칙 시안과 같다 (글 줄은 든 박스, 그 밖은 감싼 가장 작은 박스, 없으면 구역, 없으면 화면)
    parent = {}
    for e in els:
        p = e["in_box"] if e["det"] == "text" and e.get("in_box") in boxes else None
        if p is None:
            cand = [b for b in boxes.values() if b["id"] != e["id"] and RA.contains(b["box"], e["box"])]
            p = min(cand, key=lambda b: b["box"][2] * b["box"][3])["id"] if cand else None
        parent[e["id"]] = ("el", p) if p else (("rg", e["region"]) if e["region"] else ("sec", None))
    # 선택지 무리 - 같은 group 의 choice · keypad_key 2개 이상을 무리 그릇 아래 형제로
    groups = {}
    for e in els:
        if e["kind"] in GROUP_KINDS and e.get("group"):
            groups.setdefault(e["group"], []).append(e["id"])
    groups = {g: ids for g, ids in groups.items() if len(ids) >= 2}

    def ancestors(i):
        out, k = [], parent[i]
        while k[0] == "el":
            out.append(k[1])
            k = parent[k[1]]
        return out
    gid = {}
    for n, (g, ids) in enumerate(sorted(groups.items(), key=lambda kv: byid[kv[1][0]]["box"][1]), 1):
        for i in ids:
            if not any(a in ids for a in ancestors(i)):      # 같은 무리 요소 안에 든 것은 그 자리에 둔다
                parent[i] = ("grp", n)
                gid[i] = n
    # 이름 - 무리 요소의 값 (data-v) 은 그 글, 글이 없으면 그림 이름 (자기 icon.name · image_name, 없으면 안에 든 첫 그림
    # 자리의 이름 - 연구자 결정 c), 그것도 없으면 요소 id
    pic_name = lambda x: (x.get("icon") or {}).get("name") or x.get("image_name")
    k = 0
    for e in els:
        if e["id"] in gid:
            inner = next((pic_name(x) for x in els if e["id"] in ancestors(x["id"]) and pic_name(x)), None)
            actions[(sid, e["id"])] = ("a-%s-g%d" % (sid, gid[e["id"]]),
                                       shown_text(e).strip() or pic_name(e) or inner or e["id"])
        elif e["pressable"] or e["kind"] in PRESS_KINDS:
            k += 1
            actions[(sid, e["id"])] = ("a-%s-%02d" % (sid, k), None)
    regs = {r["id"]: r for r in u["regions"]}
    kids = {}
    for r in u["regions"]:
        kids.setdefault(("rg", r["parent"]) if r["parent"] else ("sec", None), []).append(("rg", r["id"]))
    for n in sorted(set(gid.values())):
        kids.setdefault(("sec", None), []).append(("grp", n))
    for e in els:
        kids.setdefault(parent[e["id"]], []).append(("el", e["id"]))
    expected = {}

    def origin(key):
        if key[0] in ("sec", "grp"):
            return 0, 0
        b = regs[key[1]]["box_css"] if key[0] == "rg" else byid[key[1]]["box_css"]
        return b[0], b[1]

    def place(b, base):
        return {"position": "absolute", "left": "%dpx" % (b[0] - base[0]), "top": "%dpx" % (b[1] - base[1]),
                "width": "%dpx" % b[2], "height": "%dpx" % b[3]}

    def render(key, in_btn=False):
        order = {"rg": 0, "el": 1, "grp": 2}
        return "".join(render_one(c, origin(key), in_btn) for c in sorted(kids.get(key, []), key=lambda c: order[c[0]]))

    def render_one(c, base, in_btn):
        if c[0] == "rg":
            r = regs[c[1]]
            st = dict(place(r["box_css"], base), **RA.region_style(arr, r["box"]))
            return '<div data-region="%s" style="%s">%s</div>' % (r["id"], RA.style(st), render(c, in_btn))
        if c[0] == "grp":
            # 무리 그릇 - 크기 0 (누름을 가리지 않는다), 안의 요소는 화면 좌표로 놓는다
            return '<div data-group="g%d" style="position:absolute; left:0; top:0">%s</div>' % (c[1], render(c, in_btn))
        e = byid[c[1]]
        b = e["box_css"]
        st = place(b, base)
        act = actions.get((sid, e["id"]))
        attrs = ""
        if act:
            attrs += ' data-action="%s"' % act[0]
            if act[1] is not None:
                attrs += ' data-v="%s"' % html.escape(act[1])
        attrs += ' data-src="%s"' % html.escape(e["id"])
        is_btn = bool(act) and e["kind"] != "input"
        inner = render(c, in_btn or is_btn)
        shape = (e.get("icon") or {}).get("shape") or e.get("image_shape")
        chev = chevron_of(shape)
        own = html.escape(e["text"] or "") if e["det"] == "text" else ""
        want_text = (e["text"] or "") if e["det"] == "text" else None
        pic = ""
        if chev:
            own, want_text, inner_pic = chev, None, False
            st.update({"font-size": "%dpx" % max(10, round(b[3] * 0.8)), "line-height": "%dpx" % b[3],
                       "color": "#8a8f98", "text-align": "center"})
            expected[(sid, e["id"])] = {"text": None, "chevron": chev}
        else:
            name = (e.get("icon") or {}).get("name") or e.get("image_name") or ""
            if e.get("text_is_icon"):
                own, want_text = "", ""
            elif own and e.get("text_fixed"):
                attrs += ' data-ocr="%s"' % html.escape(e["text"])
                own, want_text = html.escape(e["text_fixed"]), e["text_fixed"]
            if e["kind"] != "image" and (e.get("icon") or e.get("text_is_icon")) and name:
                pst = "position:absolute; inset:10%" if not own else \
                    "position:absolute; left:0; top:0; width:%dpx; height:%dpx" % (b[3], b[3])
                pic = '<div class="pic" role="img" aria-label="%s" style="%s"></div>' % (html.escape(name), pst)
            expected[(sid, e["id"])] = {"text": want_text if e["kind"] != "image" else "", "chevron": None}
            if own and not chev:
                st.update({"font-size": "%dpx" % max(8, round(b[3] * RA.FONT_K)), "line-height": "%dpx" % b[3],
                           "color": RA.text_color(arr, e["box"]), "white-space": "nowrap"})
        if e["kind"] == "image" and not chev:
            name = e.get("image_name") or (e.get("icon") or {}).get("name") or ""
            return '<div class="pic" role="img" aria-label="%s"%s style="%s">%s</div>' % (
                html.escape(name), attrs, RA.style(st), inner)
        if is_btn:
            tag = "div" if in_btn else "button"
            role = ' role="button"' if in_btn else ""
            return '<%s%s%s style="%s">%s%s%s</%s>' % (tag, role, attrs, RA.style(st), pic, own, inner, tag)
        if e["kind"] == "input":
            st["border"] = "1px solid #8a8f98"
            return '<div class="input"%s style="%s">%s%s%s</div>' % (attrs, RA.style(st), pic, own, inner)
        return '<div%s style="%s">%s%s%s</div>' % (attrs, RA.style(st), pic, own, inner)

    bands = "".join('<div data-band="%s" style="%s"></div>' % (
        r["id"], RA.style(dict(place([0, K.css(r["box"][1]), K.WIDTH, K.css(r["box"][3])], (0, 0)),
                               background=RA.region_style(arr, r["box"]).get("background", "transparent"))))
        for r in u["bands"])
    sec = ('<section class="screen" data-screen="%s" data-captures="%s"><div class="canvas" style="height:%dpx; '
           'background:%s">%s%s</div></section>' % (sid, "+".join(u["captures"]), u["size_css"][1], RA.page_bg(arr),
                                                    bands, render(("sec", None))))
    return sec, expected, {g: n for g, n in ((g, gid[ids[0]]) for g, ids in groups.items() if ids[0] in gid)}


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>스크린샷에서 조립한 원본 (2단계 %(which)s)</title>
<!-- 조립 2단계 - 규칙 부분 + %(markup)s. 만든 것: tools/screen_detect/assemble/%(maker)s (스크린샷만, strict) -->
<style>
  html,body{margin:0;padding:0;background:#DFE3EA;font-family:"Malgun Gothic",-apple-system,sans-serif;}
  body{display:flex;justify-content:center;}
  #phone{width:390px;height:844px;position:relative;overflow:hidden;background:#fff;}
  .screen{position:absolute;inset:0;display:none;overflow-y:auto;overflow-x:hidden;}
  .screen.on{display:block;}
  .canvas{position:relative;width:390px;overflow:hidden;}
  button{all:unset;box-sizing:border-box;cursor:pointer;}
  [data-action]{cursor:pointer;}
  .pic{box-sizing:border-box;border-radius:3px;box-shadow:inset 0 0 0 1px #B8BDC7;background:
    linear-gradient(to top right, transparent calc(50%% - .75px), #9AA0A8 calc(50%% - .75px), #9AA0A8 calc(50%% + .75px), transparent calc(50%% + .75px)),
    linear-gradient(to bottom right, transparent calc(50%% - .75px), #9AA0A8 calc(50%% - .75px), #9AA0A8 calc(50%% + .75px), transparent calc(50%% + .75px)), #E4E7EC;}
%(css)s</style></head><body>
<div id="phone">
%(sections)s
</div>
<script>
function show(name){
  document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.dataset.screen === name));
  window.__task = {screen: name};
}
window.__screen = () => (document.querySelector('.screen.on') || {dataset: {}}).dataset.screen;
document.getElementById('phone').addEventListener('click', function(e){
  const el = e.target.closest('[data-action]'); if(!el) return;
  const a = el.dataset.action;
%(branches)s
});
show('s01');
</script>
</body></html>
"""


def selector(act):
    a, v = act
    return "[data-action='%s']" % a + ("[data-v='%s']" % v.replace("'", "\\'") if v is not None else "")


def plan(out):
    """규칙 부분 - 화면 · 이름 · 이동 · 오류 경로 · steps · 추적표, 그리고 규칙 마크업 (sections). 마크업만 바꿔 끼우는
    판 (2단계 LLM) 도 이것을 그대로 쓴다 - write() 에 sections · markup 을 넘긴다."""
    import numpy as np
    K.STRICT_PATHS.update(final=INPUTS["final"], semantic=INPUTS["semantic"], flow=INPUTS["flow"], out=out)
    units = list(K.load_units(strict=True).values())
    sems, _ = K.C.load_semantic(INPUTS["semantic"])
    flow = json.load(io.open(INPUTS["flow"], encoding="utf-8"))
    sid_of = {u["unit"]: "s%02d" % n for n, u in enumerate(units, 1)}
    cap_screen = {c + ".png": sid_of[u["unit"]] for u in units for c in u["captures"]}
    screen_of_el = {}
    actions, expected, sections, screens = {}, {}, [], []
    for u in units:
        sid = sid_of[u["unit"]]
        arr = np.asarray(K.unit_image(u)).astype(np.int16)
        sec, exp, groups = build_screen(sid, u, arr, sems.get(u["unit"]) or {}, actions)
        sections.append(sec)
        expected.update(exp)
        screens.append({"screen": sid, "captures": [c + ".png" for c in u["captures"]], "elements": len(u["elements"]),
                        "pressable": sum(1 for e in u["elements"] if (sid, e["id"]) in actions),
                        "groups": {g: "a-%s-g%d" % (sid, n) for g, n in groups.items()}})
    # 이동 · 오류 경로 · 못 이은 짝
    # 숫자판 무리 - 화면마다 값 (data-v) 이 숫자 하나인 키가 3개 이상인 무리 (가장 많은 것)
    keypad = {}
    for (s_, i), (act, v) in actions.items():
        if v is not None and re.fullmatch(r"\d", v):
            keypad.setdefault(s_, {}).setdefault(act, []).append(i)
    keypad = {s_: max(g.items(), key=lambda kv: len(kv[1])) for s_, g in keypad.items()
              if max(len(x) for x in g.values()) >= 3}
    moves, errors, unlinked = [], [], []
    for p in flow["pairs"]:
        src, dst = cap_screen[p["from"]], cap_screen[p["to"]]
        pair = "%s → %s" % (p["from"], p["to"])
        if p["kind"] == "error_path":
            errors.append({"pair": pair, "from": src, "to": dst})
        elif p["kind"] == "scroll" and src == dst:
            continue
        elif p["kind"] != "scroll" and p.get("tap") and (src, p["tap"]) in actions:
            # tap 짝, 또는 (가) 끊긴 짝이지만 처음 누른 것이 적혔고 앞 화면에 있다 - 사이 상태는 짓지 않는다
            act = actions[(src, p["tap"])]
            moves.append({"from": src, "to": dst, "element": p["tap"], "text": p.get("tap_text"),
                          "click": selector(act), "action": act[0], "v": act[1], "pair": pair,
                          "via": "tap" if p["kind"] == "tap" else "skipped-states", "kind": p["kind"]})
        elif p["kind"] != "scroll" and not p.get("tap") and src in keypad:
            # (나) 누른 것이 적히지 않았고 앞 화면에 숫자판 무리가 있다 - 그 무리의 어느 키든 다음 화면 (어느 키인지 정하지 않음)
            act, keys = keypad[src]
            moves.append({"from": src, "to": dst, "element": None, "keys": keys, "text": None,
                          "click": selector((act, None)), "action": act, "v": None, "pair": pair,
                          "via": "keypad-advance", "kind": p["kind"]})
        else:
            why = {"skipped": "사이 상태가 캡처에 없고 (skipped) 처음 누른 것도 앞 화면 숫자판도 없다",
                   "unknown": "누른 것을 모르고 (unknown) 앞 화면에 숫자판도 없다"}.get(p["kind"], "kind %s" % p["kind"])
            if p.get("tap") and (src, p["tap"]) not in actions:
                why = "누른 요소 %s 가 앞 화면의 누를 것 목록에 없다" % p["tap"]
            elif p["kind"] == "tap" and not p.get("tap"):
                why = "tap 인데 누른 요소가 없고 앞 화면에 숫자판도 없다"
            if p["kind"] == "scroll":
                why = "scroll 인데 다른 화면이다"
            unlinked.append({"pair": pair, "from": src, "to": dst, "kind": p["kind"], "tap": p.get("tap"),
                             "tap_text": p.get("tap_text"), "why": why})
    error_paths = []
    for n, e in enumerate(errors, 1):
        rec = [x for x in units if sid_of[x["unit"]] == e["to"]][0]
        press = [x for x in sorted(rec["elements"], key=lambda x: (x["box"][1], x["box"][0])) if (e["to"], x["id"]) in actions]
        recover = [{"click": selector(actions[(e["to"], press[0]["id"])])}] if press else []
        if press:
            act = actions[(e["to"], press[0]["id"])]
            moves.append({"from": e["to"], "to": e["from"], "element": press[0]["id"], "text": shown_text(press[0]),
                          "click": recover[0]["click"], "action": act[0], "v": act[1],
                          "pair": "오류 화면에서 되돌아감 (%s 의 반대)" % e["pair"], "via": "error-recover",
                          "kind": "error_path"})
        error_paths.append({"id": "e%d" % n, "about": "", "condition": "", "uses": [], "notice_any": [],
                            "from_step": e["from"], "inputs": [], "expect_screen": e["to"], "recover": recover,
                            "back_to": e["from"] if press else None, "pair": e["pair"]})
    # 닿는 화면 (s01 부터 이동을 따라) · 과제 길
    reach, frontier = {"s01"}, ["s01"]
    while frontier:
        s = frontier.pop()
        for m in moves:
            if m["from"] == s and m["to"] not in reach:
                reach.add(m["to"])
                frontier.append(m["to"])
    # steps - s01 에서 캡처 차례 (흐름 짝 차례) 대로 이동을 따라간다 (연구자 결정 d). 오류 짝 · 되돌아감은 넣지 않는다
    steps, cur = [{"screen": "s01"}], "s01"
    for m in moves:
        if m["via"] != "error-recover" and m["from"] == cur:
            steps.append({"screen": m["to"], "click": m["click"], "via": m["via"]})
            cur = m["to"]
    task_last = max((cap_screen[p["to"]] for p in flow["pairs"] if p["kind"] != "error_path"), key=lambda s: int(s[1:]))
    blank = {"truth": "정답 값 (은행 · 계좌번호 · 금액 · 틀린 값) - 스크린샷에 '정답' 은 없다",
             "required_ids": "꼭 있어야 할 DOM id - 규칙 마크업에는 id 를 짓지 않았다 (요소는 data-src · data-action)",
             "expect": "화면마다 확인할 값 - 정답 값이 없어 비움",
             "done_amount": "완료 화면의 금액 선택자 - 정답 값이 없어 넣지 않음",
             "error_paths[].about · condition · uses · notice_any · inputs": "오류 조건 · 입력 - 스크린샷에 보이지 않는다 (만들지 않는다)"}
    if cur != task_last:
        blank["steps (%s 다음)" % cur] = "%s 에서 나가는 이동이 없다 - 과제 길이 %s 에서 끊긴다 (마지막 과제 화면 %s)" % (
            cur, cur, task_last)
    flow_out = {"name": "screenshot-assembly-v0", "task": None,
                "note": "스크린샷 19장 (파일 이름 순) 에서 조립한 원본 (조립 2단계, 규칙 부분 + 규칙 시안 마크업). 화면 = 이어 붙이기 "
                        "단위, 이동 = 흐름 추정 strict3 의 tap 짝 + 끊긴 짝을 규칙 a 로 이은 것 (via). steps 는 s01 에서 "
                        "캡처 차례대로 이동을 따라간 과제 길 - 오류 되돌아감은 transitions 에 있다. 비운 칸은 blank 에.",
                "derived_from_original": True, "truth": {}, "required_ids": [], "steps": steps, "expect": {},
                "error_paths": error_paths, "screens": screens, "transitions": moves, "blank": blank}
    trace = {}
    for u in units:
        sem = sems.get(u["unit"]) or {}
        sid = sid_of[u["unit"]]
        for e in u["elements"]:
            g = sem.get(e["id"]) or {}
            act = actions.get((sid, e["id"]))
            trace["%s:%s" % (sid, e["id"])] = {"screen": sid, "element": e["id"],
                              "selector": "[data-screen='%s'] [data-src='%s']" % (sid, e["id"]),
                              "data_action": act[0] if act else None, "data_v": act[1] if act else None,
                              "detector": {"kind": e["det"], "box": e["box"], "text": e.get("text")},
                              "semantic": {k: g.get(k) for k in ("kind", "pressable", "group", "image_name", "image_shape",
                                                                 "icon", "text_is_icon", "text_fixed")},
                              "chevron": (expected.get((sid, e["id"])) or {}).get("chevron"),
                              "markup": None,
                              "flow": [m["pair"] for m in moves if m["from"] == sid and
                                       (m["element"] == e["id"] or e["id"] in m.get("keys", []))]}
    warns = [(u, w) for u, r in ((u, json.load(io.open(os.path.join(INPUTS["semantic"], u + ".semantic.json"),
                                                         encoding="utf-8"))) for u in sid_of) for w in r.get("warnings") or []]
    limits = ["# 조립 2단계 - 한계 (이번 실행)\n",
              "## 못 이은 흐름 짝 (이동을 만들지 않음)\n",
              K.C.table(["짝", "화면", "kind", "누른 것", "까닭"],
                        [[x["pair"], "%s → %s" % (x["from"], x["to"]), x["kind"], x["tap_text"] or x["tap"] or "-", x["why"]]
                         for x in unlinked] or [["-"] * 5]),
              "\n## s01 에서 닿지 않는 화면\n",
              ", ".join(s["screen"] for s in screens if s["screen"] not in reach) or "없음",
              "\n## flow.json 에서 비운 칸\n",
              K.C.table(["칸", "까닭"], [[k, v] for k, v in blank.items()]),
              "\n## 끊긴 짝을 규칙 a 로 이은 것 (사이 상태는 짓지 않았다)\n",
              K.C.table(["짝", "화면", "kind", "via", "누르는 것", "모르는 것"],
                        [[m["pair"], "%s → %s" % (m["from"], m["to"]), m["kind"], m["via"],
                          ("%s (%s)" % (m["text"], m["element"])) if m["element"] else
                          "숫자판 무리 %s 의 아무 키 (%d개)" % (m["action"], len(m["keys"])),
                          "사이 상태 (캡처 없음) - 앞 화면에서 처음 누른 것 다음은 모른다" if m["via"] == "skipped-states" else
                          "몇 번 · 어느 키를 눌러야 넘어가는지 (키 하나로 넘어가게 했다. 무리의 숫자 아닌 키 - 지우기 · "
                          "재배열 등 - 도 넘어간다)"]
                         for m in moves if m["via"] in ("skipped-states", "keypad-advance")] or [["-"] * 6]),
              "\n## 찍지 않은 상태로 보이는 것 (skipped 짝)\n",
              ", ".join([m["pair"] for m in moves if m["kind"] == "skipped"] +
                        [x["pair"] for x in unlinked if x["kind"] == "skipped"]) or "없음",
              "\n## 검출 · 의미 층 쪽\n",
              "- 의미 층 경고 (칸 짝 검사): %s\n" % (", ".join("%s %s" % (u, w["id"]) for u, w in warns) or "없음"),
              "- 검출 놓침은 만드는 줄에서는 알 수 없다 (정답과 견주는 것은 채점 쪽 - list_compare.py).\n"
              "- 오류 경로의 recover 는 오류 화면의 첫 누를 것, back_to 는 그 짝의 앞 화면이다 - 실제로 어느 화면에서 오류가 났는지는 "
              "스크린샷에 없다.\n"]
    return {"units": units, "sid_of": sid_of, "sems": sems, "actions": actions, "expected": expected,
            "sections": sections, "screens": screens, "moves": moves, "error_paths": error_paths, "unlinked": unlinked,
            "reach": reach, "flow": flow_out, "trace": trace, "limits": limits,
            "markup": {s["screen"]: "규칙 시안 (sketch/rule_assemble 의 놓기 규칙)" for s in screens}}


def handler(moves):
    """값을 보는 갈래가 먼저 - 값 없이 무리 전체를 보는 갈래 (keypad-advance) 가 같은 data-action 의 다른 갈래를 가리지 않게."""
    lines = []
    for m in sorted(moves, key=lambda m: m["v"] is None):
        cond = "a==='%s'" % m["action"] + (" && el.dataset.v===%s" % json.dumps(m["v"], ensure_ascii=False)
                                         if m["v"] is not None else "")
        lines.append("  %sif(%s) show('%s');" % ("else " if lines else "", cond, m["to"]))
    return lines


def check_sections(S, sections):
    """출력 검사는 화면마다 (요소 id 는 단위 안에서만 하나다)."""
    chk = {"ok": True, "problems": []}
    for sec, s in zip(sections, S["screens"]):
        sid = s["screen"]
        r = CM.check("<body>%s</body>" % sec, {i: v for (s_, i), v in S["expected"].items() if s_ == sid})
        chk["problems"] += [dict(x, screen=sid) for x in r["problems"]]
    chk["ok"] = not chk["problems"]
    return chk


def write(S, out, sections=None, markup=None, page_vars=None, more_limits=()):
    """original.html · flow.json · trace.json · limits.md · check.json. sections · markup (화면 → 마크업 출처) 를 넘기면
    그 마크업으로 (동작 · 흐름 · 추적표는 S 그대로). page_vars: 쪽 제목 (which · markup · maker) 과 덧붙일 css."""
    sections = sections or S["sections"]
    markup = dict(S["markup"], **(markup or {}))
    page = PAGE % dict({"which": "규칙 판", "markup": "규칙 시안 마크업", "maker": "build.py", "css": ""},
                       **(page_vars or {}), sections="\n".join(sections),
                       branches="\n".join(handler(S["moves"])) or "  // 이동 없음")
    trace = {k: dict(v, markup=markup[v["screen"]]) for k, v in S["trace"].items()}
    chk = check_sections(S, sections)
    os.makedirs(out, exist_ok=True)
    w = lambda name, text: io.open(os.path.join(out, name), "w", encoding="utf-8", newline="\n").write(text)
    w("original.html", page)
    w("flow.json", json.dumps(S["flow"], ensure_ascii=False, indent=1))
    w("trace.json", json.dumps(trace, ensure_ascii=False, indent=1))
    w("limits.md", "\n".join(S["limits"] + list(more_limits)) + "\n")
    w("check.json", json.dumps(dict(chk, rules=["① data-src 한 번씩", "② data-src 없는 보이는 글 · 버튼 · 그림 자리 없음",
                                                  "③ 글은 text · text_fixed 그대로", "④ 그림 자리 .pic[role=img][aria-label]",
                                                  "⑤ 꺾쇠는 글자"]), ensure_ascii=False, indent=1))
    return chk


def main(argv=None):
    ap = argparse.ArgumentParser()
    K.ST.add_arg(ap)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    if not K.ST.from_args(a):
        raise SystemExit("조립은 --inputs strict 로만 돈다 (스크린샷만)")
    S = plan(a.out)
    chk = write(S, a.out)
    screens, moves, reach = S["screens"], S["moves"], S["reach"]
    print("화면 %d · 이동 %d · 오류 경로 %d · 못 이은 짝 %d · 닿는 화면 %s · 검사 %s (%d)" % (
        len(screens), len(moves), len(S["error_paths"]), len(S["unlinked"]), sorted(reach), chk["ok"],
        len(chk["problems"])))
    for s in screens:
        print(s["screen"], "+".join(c[:-4] for c in s["captures"]), s["elements"], s["pressable"],
              sum(1 for m in moves if m["from"] == s["screen"]))


if __name__ == "__main__":
    main()
